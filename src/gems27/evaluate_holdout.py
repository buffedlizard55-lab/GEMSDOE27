"""Shared buffered hide-and-recover spatial holdout evaluator for GEMSDOE27.

Implements the Parallel-Run Protocol holdout specification while reusing `src/gems27/metric.py`
and `src/gems27/holdout.py`:
  1. Whole 8-connected fault segments inside label-blind eroded quadrants (`boundary_px = 20`, 2 km)
     are withheld (`hide_frac = 0.20`).
  2. A feature-context buffer (`buffer_px = 3`, 300 m) around withheld truth is removed from
     `visible` so every visible-catalogue feature is strictly separated from withheld positives.
  3. Non-withheld catalogue pixels (`masked_known = catalogue & ~hidden`) are pixel-exactly masked
     during scoring (neither credit nor false-positive penalty), matching the competition metric.
  4. Pooled DTI (`alpha = 0.2`, `beta = 0.8`, `300 m` triangular kernel) and 1,000-draw paired
     percentile 95% CIs are computed over globally aligned `20 km x 20 km` (`200 x 200` px)
     physical spatial clusters.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
from scipy import ndimage as ndi

from . import holdout, metric

VERSION = "gems27-pooled-hide-v2"
DOMAIN_ERODE_PX = 20  # 2.0 km erosion from quadrant & footprint boundaries
STRUCT3 = np.ones((3, 3), dtype=int)


def implementation_hashes() -> dict[str, str]:
    base = Path(__file__).parent
    return {
        name: hashlib.sha256((base / name).read_bytes()).hexdigest()
        for name in ("evaluate_holdout.py", "holdout.py", "metric.py")
    }


def _pick_components(
    rng: np.random.Generator, sizes: np.ndarray, eligible: np.ndarray, target_px: float
) -> np.ndarray:
    if len(eligible) == 0 or target_px <= 0:
        return np.empty(0, dtype=int)
    perm = rng.permutation(eligible)
    csum = np.cumsum(sizes[perm])
    k = int(np.searchsorted(csum, target_px, side="left")) + 1
    k = max(1, min(k, len(perm)))
    return perm[:k]


def buffered_component_draw(
    footprint: np.ndarray,
    catalogue: np.ndarray,
    *,
    seed: int = 200,
    hide_frac: float = 0.20,
    buffer_px: int = 3,
    boundary_px: int = DOMAIN_ERODE_PX,
) -> tuple[list[dict[str, Any]], np.ndarray]:
    """Create a 4-quadrant whole-component hide-and-recover split with strict context buffering."""
    if not (0.0 < hide_frac < 1.0) or buffer_px < 0 or boundary_px < buffer_px:
        raise ValueError("invalid holdout hide_frac/buffer_px/boundary_px")
    foot = np.asarray(footprint, dtype=bool)
    cat = np.asarray(catalogue, dtype=bool) & foot
    quad = holdout.make_quadrant_folds(foot)
    comp, count = ndi.label(cat, structure=STRUCT3)
    sizes = np.bincount(comp.ravel(), minlength=count + 1)

    hidden = np.zeros(cat.shape, dtype=bool)
    regions: list[np.ndarray] = []
    receipts: list[dict[str, Any]] = []

    for q, name in enumerate(holdout.FOLD_NAMES):
        qmask = quad == q
        region = ndi.binary_erosion(qmask, iterations=boundary_px) if boundary_px else qmask.copy()
        region &= foot
        cand = np.unique(comp[cat & region])
        clipped = np.unique(comp[cat & ~region])
        eligible = np.setdiff1d(cand[cand > 0], clipped, assume_unique=True)
        rng = np.random.default_rng(seed * 10_000 + q)
        chosen = _pick_components(rng, sizes, eligible, hide_frac * float((cat & region).sum()))
        withheld = np.isin(comp, chosen) & cat
        if (withheld & ~region).any():
            raise AssertionError("withheld component was clipped by quadrant boundary")
        hidden |= withheld
        regions.append(region)
        receipts.append(
            {
                "fold": name,
                "seed": int(seed),
                "held_components": int(len(chosen)),
                "withheld_positive_pixels": int(withheld.sum()),
                "eligible_components": int(len(eligible)),
                "boundary_buffer_px": int(boundary_px),
                "feature_buffer_px": int(buffer_px),
            }
        )

    if not hidden.any():
        raise ValueError("no eligible withheld components")

    collar = ndi.distance_transform_edt(~hidden) <= buffer_px
    visible = cat & ~collar
    masked_known = cat & ~hidden
    if not visible.any():
        raise ValueError("no visible catalogue context remaining")
    if (visible & hidden).any() or np.any(visible & collar):
        raise AssertionError("withheld truth or context buffer leaked into visible catalogue")
    min_dist = float(ndi.distance_transform_edt(~visible)[hidden].min())
    if min_dist <= buffer_px:
        raise AssertionError(f"context buffer violated: {min_dist} <= {buffer_px}")

    folds = [
        {
            "fold": i,
            "name": holdout.FOLD_NAMES[i],
            "region": regions[i],
            "truth": hidden & regions[i],
            "visible": visible,
            "masked_known": masked_known,
            "hidden_all": hidden,
            "receipt": {
                **receipts[i],
                "nearest_visible_to_truth_px": min_dist,
                "split_version": "buffered-whole-components-loqo-v2",
                "evaluation_region_label_blind": True,
            },
        }
        for i in range(4)
    ]
    return folds, quad


def _per_pixel_max_cover(pred: np.ndarray, truth: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return `(covers_on_truth, kernel_to_truth_grid)` matching `metric.dti_exact`."""
    H, W = pred.shape
    yy, xx = np.nonzero(truth)
    n_truth = len(yy)
    covers = np.zeros(n_truth, dtype=np.float64)
    r = int(np.ceil(metric.RADIUS_PX))
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            k = max(1.0 - float(np.hypot(dy, dx)) / metric.RADIUS_PX, 0.0)
            if k <= 0.0:
                continue
            ny, nx = yy + dy, xx + dx
            ok = (ny >= 0) & (nx >= 0) & (ny < H) & (nx < W)
            covers[ok] = np.maximum(covers[ok], pred[ny[ok], nx[ok]].astype(np.float64) * k)
    d_to_g = ndi.distance_transform_edt(~truth) if n_truth else np.full(pred.shape, np.inf)
    q_grid = metric.kernel_from_distance(d_to_g)
    return covers, q_grid


def evaluate_fold(
    prediction: np.ndarray,
    fold: dict[str, Any],
    valid: np.ndarray,
    *,
    block_side: int = 200,
) -> tuple[dict[str, Any], np.ndarray]:
    """Exact fold DTI plus additive `(TPw, FPw, FNw, n_truth)` terms on `block_side` spatial blocks."""
    if block_side <= 0:
        raise ValueError("block_side must be positive")
    p_raw = np.asarray(prediction)
    if p_raw.ndim != 2:
        raise ValueError("prediction must be 2-D")
    valid_b = np.asarray(valid, dtype=bool)
    region = np.asarray(fold["region"], dtype=bool)
    known = np.asarray(fold.get("masked_known", fold["visible"]), dtype=bool)
    truth_all = np.asarray(fold["truth"], dtype=bool)
    if any(a.shape != p_raw.shape for a in (valid_b, region, known, truth_all)):
        raise ValueError("fold/prediction grid shape mismatch")

    vals_valid = p_raw[valid_b]
    if not np.isfinite(vals_valid).all() or (vals_valid < 0.0).any() or (vals_valid > 1.0).any():
        raise ValueError("predictions inside footprint must be finite in [0, 1]")

    active = valid_b & region & ~known
    p = np.where(active, p_raw, 0.0).astype(np.float64)
    truth = active & truth_all
    if not truth.any():
        raise ValueError("holdout fold contains zero withheld positives")

    res = metric.dti_exact(p, truth, valid=active)
    covers, q_grid = _per_pixel_max_cover(p, truth)

    H, W = truth.shape
    ncols = (W + block_side - 1) // block_side
    nrows = (H + block_side - 1) // block_side
    terms = np.zeros((nrows * ncols, 4), dtype=np.float64)

    ty, tx = np.nonzero(truth)
    t_ids = (ty // block_side) * ncols + (tx // block_side)
    terms[:, 0] = np.bincount(t_ids, weights=covers, minlength=len(terms))
    terms[:, 2] = np.bincount(t_ids, weights=1.0 - covers, minlength=len(terms))
    terms[:, 3] = np.bincount(t_ids, weights=np.ones(len(ty)), minlength=len(terms))

    py, px = np.nonzero(p > 0.0)
    p_ids = (py // block_side) * ncols + (px // block_side)
    fp_weights = p[py, px] * (1.0 - q_grid[py, px])
    terms[:, 1] = np.bincount(p_ids, weights=fp_weights, minlength=len(terms))

    totals = terms.sum(axis=0)
    np.testing.assert_allclose(
        totals,
        [res["TPw"], res["FPw"], res["FNw"], float(res["n_truth"])],
        rtol=1e-10,
        atol=1e-6,
    )
    out = {
        "fold": fold["name"],
        "dti": float(res["dti"]),
        "tpw": float(res["TPw"]),
        "fpw": float(res["FPw"]),
        "fnw": float(res["FNw"]),
        "n_truth": int(res["n_truth"]),
        "n_emitted": int(res["n_emitted"]),
        "recall_w": float(res["recall_w"]),
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": VERSION,
        "spatial_bootstrap_cluster_m": int(block_side * 100),
    }
    return out, terms


def dti_from_terms(terms: np.ndarray) -> np.ndarray | float:
    a = np.asarray(terms, dtype=np.float64)
    tp, fp, fn = a[..., 0], a[..., 1], a[..., 2]
    den = tp + metric.ALPHA * fp + metric.BETA * fn + metric.EPS
    out = np.divide(tp, den, out=np.zeros_like(tp, dtype=np.float64), where=den > 0.0)
    return float(out) if out.ndim == 0 else out


def evaluate_arms_pooled(
    predictions_by_arm: dict[str, np.ndarray],
    folds: list[dict[str, Any]],
    valid: np.ndarray,
    *,
    candidate: str,
    block_side: int = 200,
    draws: int = 1000,
    seed: int = 520810,
) -> dict[str, Any]:
    """Evaluate multiple arms on identical buffered folds and compute paired 20 km block CIs."""
    if candidate not in predictions_by_arm or len(predictions_by_arm) < 1:
        raise ValueError("candidate must be present in predictions_by_arm")
    terms_by_arm: dict[str, np.ndarray] = {}
    per_fold_by_arm: dict[str, list[dict[str, Any]]] = {}

    for arm_name, pred in predictions_by_arm.items():
        fold_rows = []
        acc_terms = None
        for f in folds:
            f_res, f_terms = evaluate_fold(pred, f, valid, block_side=block_side)
            fold_rows.append(f_res)
            acc_terms = f_terms if acc_terms is None else (acc_terms + f_terms)
        assert acc_terms is not None
        terms_by_arm[arm_name] = acc_terms
        per_fold_by_arm[arm_name] = fold_rows

    ref_truth = terms_by_arm[candidate][:, 3]
    for arm_name, t in terms_by_arm.items():
        if not np.array_equal(t[:, 3], ref_truth):
            raise ValueError(f"spatial-block truth mismatch for {arm_name}")

    active = np.any(np.stack([t.sum(axis=1) > 0.0 for t in terms_by_arm.values()]), axis=0)
    arrays = {n: t[active] for n, t in terms_by_arm.items()}
    nb = int(active.sum())
    if nb < 2:
        raise ValueError("need at least 2 active spatial clusters for bootstrap")

    rng = np.random.default_rng(seed)
    picks = rng.integers(0, nb, size=(draws, nb))
    boot = {n: np.asarray(dti_from_terms(a[picks].sum(axis=1))) for n, a in arrays.items()}

    scores: dict[str, Any] = {}
    for n, a in arrays.items():
        tot = a.sum(axis=0)
        scores[n] = {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": VERSION,
            "dti": float(dti_from_terms(tot)),
            "ci95": [float(x) for x in np.quantile(boot[n], [0.025, 0.975])],
            "withheld_positive_pixels": int(round(tot[3])),
            "tpw": float(tot[0]),
            "fpw": float(tot[1]),
            "fnw": float(tot[2]),
            "per_fold": per_fold_by_arm[n],
        }

    controls = [n for n in predictions_by_arm if n != candidate]
    paired_differences: dict[str, Any] = {}
    for n in controls:
        delta_boot = boot[candidate] - boot[n]
        f_cand = [r["dti"] for r in per_fold_by_arm[candidate]]
        f_ctrl = [r["dti"] for r in per_fold_by_arm[n]]
        folds_won = sum(1 for a, b in zip(f_cand, f_ctrl) if a > b)
        paired_differences[n] = {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": VERSION,
            "delta_dti": float(scores[candidate]["dti"] - scores[n]["dti"]),
            "ci95": [float(x) for x in np.quantile(delta_boot, [0.025, 0.975])],
            "folds_improved": f"{folds_won}/{len(folds)}",
            "withheld_positive_pixels": scores[candidate]["withheld_positive_pixels"],
        }

    return {
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": VERSION,
        "implementation_hashes": implementation_hashes(),
        "alpha": metric.ALPHA,
        "beta": metric.BETA,
        "triangular_radius_m": int(metric.RADIUS_PX * 100),
        "spatial_cluster_km": round(block_side * 0.1, 1),
        "active_spatial_clusters": nb,
        "bootstrap_draws": int(draws),
        "bootstrap_seed": int(seed),
        "candidate": candidate,
        "scores": scores,
        "paired_differences": paired_differences,
    }
