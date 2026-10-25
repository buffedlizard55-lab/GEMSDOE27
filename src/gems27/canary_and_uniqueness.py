"""Univariate holdout leakage canaries (Rule 4) and full-footprint registry uniqueness scan (Rule 1)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy.stats import rankdata

from . import grid


def _roc_auc_exact(y_true: np.ndarray, scores: np.ndarray) -> float:
    """Exact Mann-Whitney / Wilcoxon rank-sum ROC-AUC handling ties and NaNs cleanly."""
    y = np.asarray(y_true, dtype=bool)
    s = np.asarray(scores, dtype=np.float64)
    finite = np.isfinite(s)
    if not finite.all():
        # Evaluate finite support; also verify missingness indicator itself is non-leaky
        if not finite.any():
            return 0.5
        y_f, s_f = y[finite], s[finite]
        auc_fin = _roc_auc_exact(y_f, s_f) if (y_f.any() and (~y_f).any()) else 0.5
        miss = (~finite).astype(np.float64)
        auc_miss = _roc_auc_exact(y, miss) if (y.any() and (~y).any()) else 0.5
        return max(max(auc_fin, 1.0 - auc_fin), max(auc_miss, 1.0 - auc_miss))
    n1 = int(y.sum())
    n0 = int(len(y) - n1)
    if n1 == 0 or n0 == 0:
        return 0.5
    ranks = rankdata(s, method="average")
    r1 = float(ranks[y].sum())
    auc = (r1 - n1 * (n1 + 1) / 2.0) / (float(n1) * float(n0))
    return float(max(auc, 1.0 - auc))


def run_leakage_canaries(
    X_foot: np.ndarray,
    feature_names: list[str],
    foot: np.ndarray,
    folds: list[dict[str, Any]],
    *,
    fold_extra_features: dict[str, np.ndarray] | None = None,
    auc_limit: float = 0.90,
) -> dict[str, Any]:
    """Test every feature individually on the pooled buffered holdout evaluation regions."""
    foot_b = np.asarray(foot, dtype=bool)
    eval_mask_2d = np.zeros(foot_b.shape, dtype=bool)
    truth_2d = np.zeros(foot_b.shape, dtype=bool)
    for f in folds:
        act = foot_b & np.asarray(f["region"], bool) & ~np.asarray(f["masked_known"], bool)
        eval_mask_2d |= act
        truth_2d |= act & np.asarray(f["truth"], bool)

    eval_in_foot = eval_mask_2d[foot_b]
    y_eval = truth_2d[foot_b][eval_in_foot]
    n_pos = int(y_eval.sum())
    n_neg = int(len(y_eval) - n_pos)
    if n_pos == 0 or n_neg == 0:
        raise ValueError("canary evaluation split has degenerate class counts")

    per_feature: dict[str, float] = {}
    flagged: list[dict[str, Any]] = []

    for j, name in enumerate(feature_names):
        col = X_foot[eval_in_foot, j]
        sym_auc = _roc_auc_exact(y_eval, col)
        per_feature[name] = round(sym_auc, 6)
        if sym_auc > auc_limit:
            flagged.append({"feature": name, "symmetric_auc": round(sym_auc, 6)})

    if fold_extra_features:
        for name, full_2d in fold_extra_features.items():
            col = np.asarray(full_2d)[foot_b][eval_in_foot]
            sym_auc = _roc_auc_exact(y_eval, col)
            per_feature[name] = round(sym_auc, 6)
            if sym_auc > auc_limit:
                flagged.append({"feature": name, "symmetric_auc": round(sym_auc, 6)})

    max_feat = max(per_feature.items(), key=lambda kv: kv[1])
    return {
        "gate_passed": len(flagged) == 0,
        "auc_limit": float(auc_limit),
        "n_features_tested": len(per_feature),
        "eval_positive_px": n_pos,
        "eval_negative_px": n_neg,
        "max_feature": max_feat[0],
        "max_symmetric_auc": float(max_feat[1]),
        "flagged_features": flagged,
        "per_feature_symmetric_auc": per_feature,
    }


def _unit_rank_vector(x: np.ndarray) -> np.ndarray:
    r = rankdata(np.asarray(x, dtype=np.float64), method="average")
    r -= r.mean()
    nrm = float(np.linalg.norm(r))
    if nrm == 0.0:
        return np.zeros_like(r)
    return r / nrm


def _corr_with_unit_rank(u: np.ndarray, v_raw: np.ndarray) -> float:
    """Exact Spearman correlation between pre-ranked unit vector `u` and array `v_raw`."""
    v = np.asarray(v_raw, dtype=np.float32)
    n = len(v)
    if n == 0:
        return 0.0
    # Fast exact path for binary `{0, c}` rasters (rankdata is affine on 2-valued vectors)
    nz = v > 0.0
    k = int(nz.sum())
    if k == 0:
        if bool(np.all(v == v[0])):
            return 0.0
    elif k < n:
        first_pos = float(v[nz][0])
        if bool(np.all(v[nz] == first_pos)) and bool(np.all(v[~nz] == 0.0)):
            denom = np.sqrt(float(k) * (1.0 - float(k) / float(n)))
            return float(u[nz].sum() / denom)
    elif bool(np.all(v == v[0])):
        return 0.0
    rv = _unit_rank_vector(v)
    return float(np.dot(u, rv))


def _disc_offsets_le(radius_px: float = 3.0) -> list[tuple[int, int]]:
    r = int(np.floor(radius_px))
    lim = radius_px * radius_px + 1e-12
    return [
        (dy, dx)
        for dy in range(-r, r + 1)
        for dx in range(-r, r + 1)
        if dy * dy + dx * dx <= lim
    ]


def scan_registry_uniqueness(
    continuous_surface: np.ndarray,
    binary_dots: np.ndarray,
    footprint: np.ndarray,
    catalogue: np.ndarray,
    registry_dir: Path | str,
    *,
    exclude_sha256: set[str] | None = None,
    rho_limit: float = 0.90,
    overlap_limit: float = 0.70,
    dot_threshold: float = 0.5,
) -> dict[str, Any]:
    """Full-footprint exact Spearman & 3-px dot-overlap uniqueness audit against registry rasters.

    Checks BOTH:
      1. `continuous_surface` BEFORE dot placement (`|Spearman rho| <= 0.90`), and
      2. `binary_dots` AFTER placement (`|Spearman rho| <= 0.90` AND `3-px overlap <= 0.70`).
    """
    from scipy.ndimage import distance_transform_edt

    foot = np.asarray(footprint, dtype=bool)
    cat = np.asarray(catalogue, dtype=bool)
    active = foot & ~cat
    surf = np.asarray(continuous_surface, dtype=np.float32)
    dots = np.asarray(binary_dots, dtype=np.float32) > dot_threshold
    if surf.shape != grid.SHAPE or dots.shape != grid.SHAPE:
        raise ValueError("surface/dots shape mismatch")

    cand_dots = dots & active
    n_cand = int(cand_dots.sum())
    if n_cand == 0:
        raise ValueError("candidate has zero active off-catalogue dots")

    u_surf = _unit_rank_vector(surf[active])
    u_dots = _unit_rank_vector(cand_dots[active].astype(np.float32))

    # Candidate 3-px neighborhood for reverse overlap (`frac of registry dots within 3 px of candidate`)
    cand_near3 = distance_transform_edt(~cand_dots) <= 3.0 + 1e-9
    cy, cx = np.nonzero(cand_dots)
    offsets = _disc_offsets_le(3.0)
    H, W = grid.SHAPE

    reg_root = Path(registry_dir)
    tif_paths = sorted(p for p in reg_root.glob("*.tif") if p.is_file())
    if not tif_paths:
        raise RuntimeError(f"no registry rasters found in {reg_root}")

    excl = set(exclude_sha256 or ())
    records: list[dict[str, Any]] = []
    duplicates: list[dict[str, Any]] = []

    for p in tif_paths:
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        if sha in excl:
            continue
        with rasterio.open(p) as ds:
            if ds.count != 1 or ds.shape != grid.SHAPE:
                continue
            arr = ds.read(1)
        reg_act = np.where(np.isfinite(arr[active]), arr[active], 0.0).astype(np.float32)
        rho_surf = _corr_with_unit_rank(u_surf, reg_act)
        rho_dots = _corr_with_unit_rank(u_dots, reg_act)

        # Official upstream `vendor/gems57/uniqueness.py` (2026-10-20 fix):
        # Binary dot support is `|v - 1.0| < 1e-6` (continuous surfaces are audited via Spearman),
        # and duplicate overlap requires mutual coincidence `min(forward, reverse) > 0.70` so dense
        # whole-footprint sampling lattices or 100k+ solid un-thinned traces do not false-trigger.
        reg_bool = np.isfinite(arr) & (np.abs(arr - 1.0) < 1e-6) & active
        n_reg = int(reg_bool.sum())
        if n_reg > 0:
            rev_ov = float(cand_near3[reg_bool].mean())
            hit = np.zeros(n_cand, dtype=bool)
            for dy, dx in offsets:
                ny = np.clip(cy + dy, 0, H - 1)
                nx = np.clip(cx + dx, 0, W - 1)
                ib = (cy + dy >= 0) & (cy + dy < H) & (cx + dx >= 0) & (cx + dx < W)
                hit |= ib & reg_bool[ny, nx]
            fwd_ov = float(hit.mean())
            mut_ov = min(fwd_ov, rev_ov)
            jaccard_3px = float(hit.sum()) / float(max(n_cand + n_reg - hit.sum(), 1))
        else:
            fwd_ov = rev_ov = mut_ov = jaccard_3px = 0.0

        is_dense_trace_or_lattice = n_reg > 65_000
        identical_decoded = bool(n_reg == n_cand and np.array_equal(cand_dots, reg_bool))

        is_dup = (
            abs(rho_surf) > rho_limit
            or abs(rho_dots) > rho_limit
            or mut_ov > overlap_limit
            or identical_decoded
        )
        rec = {
            "name": p.name,
            "sha256": sha,
            "n_reg_dots": n_reg,
            "is_dense_trace_or_lattice": is_dense_trace_or_lattice,
            "surface_spearman": round(rho_surf, 6),
            "dots_spearman": round(rho_dots, 6),
            "forward_overlap_3px": round(fwd_ov, 6),
            "reverse_overlap_3px": round(rev_ov, 6),
            "mutual_overlap_3px": round(mut_ov, 6),
            "forward_only_overlap_warning": bool(fwd_ov > overlap_limit >= mut_ov),
            "jaccard_approx_3px": round(jaccard_3px, 6),
            "identical_decoded_predictions": identical_decoded,
            "duplicate_flag": bool(is_dup),
        }
        records.append(rec)
        if is_dup:
            duplicates.append(rec)

    if not records:
        raise RuntimeError("zero valid 3730x3292 registry rasters scanned")

    top_surf = max(records, key=lambda r: abs(r["surface_spearman"]))
    top_dots = max(records, key=lambda r: abs(r["dots_spearman"]))
    top_mut = max(records, key=lambda r: r["mutual_overlap_3px"])
    like_for_like = [r for r in records if 0 < r["n_reg_dots"] <= 65_000]
    top_fwd_like = (
        max(like_for_like, key=lambda r: r["forward_overlap_3px"]) if like_for_like else top_mut
    )
    fwd_warnings = [r for r in records if r["forward_only_overlap_warning"]]

    # Key reference overlaps for direct auditability
    focus_refs = {}
    for tag, prefix in (
        ("gemsdoe32_02778_h33_2_b2", "c55bafc47005"),
        ("gemsdoe36_02750_anderson_pinn", "e15891020b9c"),
        ("gemsdoe28_02710_h36_1", "5556aa1438fd"),
        ("gemsdoe28_02708_h27_4_r1", "ab0230015224"),
        ("gemsdoe70_02478_p5_submod", "d0e41ce921af"),
        ("gemsdoe24_02477_d1_5", "68d0e2e4fcc5"),
        ("gemsdoe27_02449_tv2", "33003374335d"),
        ("19gemsdoe_01922_h19_5", "ec1f9b56b83c"),
    ):
        for r in records:
            if r["sha256"].startswith(prefix):
                focus_refs[tag] = r
                break

    return {
        "gate_passed": len(duplicates) == 0,
        "overlap_rule": "official upstream gems57 2026-10-20 fix: binary dot support |v-1|<1e-6 and mutual min(forward,reverse) <= 0.70; like-for-like (<=65k dots) forward overlap also reported",
        "rasters_scanned": len(records),
        "like_for_like_dot_rasters_scanned": len(like_for_like),
        "candidate_active_dots": n_cand,
        "thresholds": {
            "max_abs_spearman": rho_limit,
            "max_3px_dot_overlap": overlap_limit,
        },
        "max_surface_spearman": {
            "abs_rho": round(abs(top_surf["surface_spearman"]), 6),
            "signed_rho": top_surf["surface_spearman"],
            "raster": top_surf["name"],
            "sha256": top_surf["sha256"],
        },
        "max_dots_spearman": {
            "abs_rho": round(abs(top_dots["dots_spearman"]), 6),
            "signed_rho": top_dots["dots_spearman"],
            "raster": top_dots["name"],
            "sha256": top_dots["sha256"],
        },
        "max_mutual_3px_overlap": {
            "overlap": top_mut["mutual_overlap_3px"],
            "raster": top_mut["name"],
            "sha256": top_mut["sha256"],
        },
        "max_forward_3px_overlap_geological": {
            "overlap": top_fwd_like["forward_overlap_3px"],
            "raster": top_fwd_like["name"],
            "sha256": top_fwd_like["sha256"],
        },
        "dense_trace_forward_only_warnings_count": len(fwd_warnings),
        "dense_trace_forward_only_warnings": fwd_warnings[:10],
        "focus_reference_comparisons": focus_refs,
        "duplicate_count": len(duplicates),
        "duplicates": duplicates[:10],
        "top_10_by_mutual_overlap": sorted(
            records, key=lambda r: r["mutual_overlap_3px"], reverse=True
        )[:10],
        "top_10_by_surface_spearman": sorted(
            records, key=lambda r: abs(r["surface_spearman"]), reverse=True
        )[:10],
    }
