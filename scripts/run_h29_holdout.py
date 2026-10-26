"""Frozen E1 + E2 evaluation runner for Hypothesis H29-1 (Lane L-S7-2026-10-25).

Preregistered at commit 30accf8 (`knowledge/15_geothermal_vent_discovery_and_h29_preregistration.md`):
- Unused holdout seeds: 210..219 (10 seeds x 4 quadrants = 40 cells).
- Off-catalogue rule & budget: B2 (`EDT(~known) > 2.0 px`), matched full-map budget 37,654 dots.
- Bug-fixed blind `emit(...)`: sees ONLY `fold_domain = foot & sp.fold_mask` and `sp.known`
  (zero access to `sp.hidden` or `valid_scoring`).
- Stage `e1`: univariate direction-invariant ROC-AUC leakage canary (<= 0.90) + pre-placement
  stitched/OOF surface Spearman correlation (|rho| <= 0.90) vs all 12 peer rasters & repo rasters.
- Stage `e2`: paired 40-cell buffered spatial holdout (`buffered_scoring_mask`, buffer_px=6.0)
  plus secondary unbuffered full-quadrant diagnostic across arms U0, B0, D0, H28_1_B2, H29-A, H29-S.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, gaussian_filter
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

from gems27 import coverage_thin, grid, holdout, metric, oof_detector, paths, potential_edges
from gems27 import hydrothermal_piedmont as h29
from gems27 import subsurface_features as sub

SEEDS: list[int] = list(range(210, 220))
BUDGET_TOTAL: int = 37_654
B_EXCL: float = 2.0
POISSON_MIN_DIST: float = 2.8
CELF_GAMMA: float = 1.5
CELF_MIN_SEP: float = 2.0

CACHE_DIR = paths.DATA / "h29"


def load_base() -> tuple[np.ndarray, np.ndarray, list[str]]:
    with rasterio.open(paths.TEMPLATE) as t:
        foot = np.isfinite(t.read(1))
    with rasterio.open(paths.LABELS) as l:
        labels = (l.read(1) == 1) & foot
    meta = json.loads(paths.PREPARED_META.read_text())
    return foot, labels, meta["names"]


def get_or_build_subsurface15(foot: np.ndarray, names: list[str]) -> np.ndarray:
    import gc
    p = paths.DATA / "lane" / "subsurface_transforms.npy"
    if p.exists():
        return np.load(p, mmap_mode="r")
    p.parent.mkdir(parents=True, exist_ok=True)
    X = np.load(paths.PREPARED_FEATURES, mmap_mode="r")
    grids = {}
    for b in sub.SUBSURFACE_BANDS:
        g = np.full(grid.SHAPE, np.nan, dtype=np.float32)
        g[foot] = X[:, names.index(b)]
        grids[b] = g
    T = sub.build_transforms(grids, foot)
    del grids
    gc.collect()
    np.save(p, T)
    del T
    gc.collect()
    return np.load(p, mmap_mode="r")


def get_or_build_h28_edges6(foot: np.ndarray, names: list[str]) -> np.ndarray:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    p = CACHE_DIR / "h28_1_edges6.npy"
    if p.exists():
        return np.load(p, mmap_mode="r")
    X = np.load(paths.PREPARED_FEATURES, mmap_mode="r")
    rtp_g = np.full(grid.SHAPE, np.nan, dtype=np.float32)
    grav_g = np.full(grid.SHAPE, np.nan, dtype=np.float32)
    rtp_g[foot] = X[:, names.index("rtp")]
    grav_g[foot] = X[:, names.index("iso_grav_anom")]
    stack = potential_edges.multiscale_potential_edge_features(rtp_g, grav_g, foot)
    arr = np.ascontiguousarray(stack[:, foot].T, dtype=np.float32)
    np.save(p, arr)
    return np.load(p, mmap_mode="r")


def get_or_fit_h29_quad_oof(
    base_X: np.ndarray, h29_X: np.ndarray, labels: np.ndarray, foot: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    p1_path = CACHE_DIR / "prob_h29_s1_quad.npy"
    p2_path = CACHE_DIR / "prob_h29_s2_quad.npy"
    if p1_path.exists() and p2_path.exists():
        return np.load(p1_path), np.load(p2_path)
    print("fitting H29 2-stage nested spatial cross-fit (Quadrant 4-fold)...", flush=True)
    t0 = time.time()
    s1, s2 = h29.fit_predict_two_stage_oof(
        base_X, h29_X, labels, foot, buffer_px=h29.BUFFER_PX, seed=210
    )
    print(f"  finished H29 Quadrant OOF in {time.time() - t0:.1f}s", flush=True)
    np.save(p1_path, s1)
    np.save(p2_path, s2)
    return s1, s2


def get_or_fit_baseline_oof(
    arm: str,
    foot: np.ndarray,
    labels: np.ndarray,
    fold: np.ndarray,
    names: list[str],
) -> np.ndarray:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out_p = CACHE_DIR / f"prob_{arm}_quad.npy"
    if out_p.exists():
        return np.load(out_p)
    print(f"fitting baseline OOF arm {arm}...", flush=True)
    t0 = time.time()
    if arm == "B0":
        lane_b = paths.DATA / "lane" / "oof_arm_B.npy"
        if lane_b.exists():
            prob = np.load(lane_b)
        else:
            prob = oof_detector.fit_predict_oof_probabilities(foot, labels, fold)
    elif arm == "D0":
        lane_d = paths.DATA / "lane" / "oof_arm_D.npy"
        if lane_d.exists():
            prob = np.load(lane_d)
        else:
            T_sub = get_or_build_subsurface15(foot, names)
            prob = oof_detector.fit_predict_oof_probabilities(foot, labels, fold, extra=T_sub)
    elif arm == "H28_1_B2":
        T_e6 = get_or_build_h28_edges6(foot, names)
        prob = oof_detector.fit_predict_oof_probabilities(foot, labels, fold, extra=T_e6)
    else:
        raise ValueError(f"Unknown baseline arm: {arm}")
    print(f"  finished {arm} in {time.time() - t0:.1f}s", flush=True)
    np.save(out_p, prob)
    return prob


def run_e1() -> int:
    t0 = time.time()
    foot, labels, names = load_base()
    fold = holdout.make_quadrant_folds(foot)
    base_X = np.load(paths.PREPARED_FEATURES, mmap_mode="r")
    print("building/loading H29 20-feature physics matrix...", flush=True)
    h29_X = h29.build_h29_feature_matrix(cache_path=CACHE_DIR / "h29_features.npy")

    # Gather union of withheld positives & buffered scoring domain across frozen seeds 210..219:
    hidden_any = np.zeros_like(labels)
    valid_any = np.zeros_like(labels)
    for seed in SEEDS:
        for f in range(4):
            sp = holdout.make_split(labels, fold, f, seed=seed)
            hidden_any |= sp.hidden
            valid_any |= holdout.buffered_scoring_mask(sp, foot)

    y_foot = hidden_any[foot]
    scope = (valid_any | hidden_any)[foot]
    idx_scope = np.flatnonzero(scope)
    pos_idx = idx_scope[y_foot[idx_scope]]
    neg_all = idx_scope[~y_foot[idx_scope]]
    rng = np.random.default_rng(210)
    neg_idx = rng.choice(neg_all, size=min(250_000, neg_all.size), replace=False)
    y_eval = np.r_[np.ones(pos_idx.size, dtype=np.int8), np.zeros(neg_idx.size, dtype=np.int8)]

    canary_h29: dict[str, dict[str, float]] = {}
    for j, nm in enumerate(h29.H29_FEATURE_NAMES):
        v = np.r_[np.asarray(h29_X[pos_idx, j], float), np.asarray(h29_X[neg_idx, j], float)]
        raw_auc = float(roc_auc_score(y_eval, v))
        dir_inv = float(max(raw_auc, 1.0 - raw_auc))
        canary_h29[nm] = {"raw_auc": round(raw_auc, 5), "direction_invariant_auc": round(dir_inv, 5)}
        print(f"  canary H29 {nm:28s}: raw={raw_auc:.4f} dir_inv={dir_inv:.4f}", flush=True)

    canary_base: dict[str, float] = {}
    for j, nm in enumerate(names):
        v = np.r_[np.asarray(base_X[pos_idx, j], float), np.asarray(base_X[neg_idx, j], float)]
        ok = np.isfinite(v)
        raw_auc = float(roc_auc_score(y_eval[ok], v[ok]))
        canary_base[nm] = round(float(max(raw_auc, 1.0 - raw_auc)), 5)

    max_h29_auc = max(d["direction_invariant_auc"] for d in canary_h29.values())
    max_base_auc = max(canary_base.values())
    leak_flags = {
        k: d["direction_invariant_auc"]
        for k, d in canary_h29.items()
        if d["direction_invariant_auc"] > 0.90
    }
    leak_flags.update({f"base:{k}": v for k, v in canary_base.items() if v > 0.90})

    # Pre-placement Stage-2 OOF surface Spearman check against all 12 peer rasters + local rasters:
    _, s2_quad = get_or_fit_h29_quad_oof(base_X, h29_X, labels, foot)
    sample_flat = rng.choice(np.flatnonzero(foot.ravel()), size=400_000, replace=False)
    cand_vec = s2_quad.ravel()[sample_flat]

    reg_meta = json.loads((paths.DATA / "parallel_registry" / "cache_manifest.json").read_text())
    peer_spearman: dict[str, dict[str, float]] = {}
    for entry in reg_meta["entries"]:
        rp = paths.DATA / entry["local"]
        with rasterio.open(rp) as s:
            a = s.read(1)
        raw_bin = (np.isfinite(a) & (a > 0)).astype(np.float32)
        dens = gaussian_filter(raw_bin, sigma=3.0)
        rho_raw = float(spearmanr(cand_vec, raw_bin.ravel()[sample_flat]).statistic)
        rho_smooth = float(spearmanr(cand_vec, dens.ravel()[sample_flat]).statistic)
        peer_spearman[entry["id"]] = {
            "raw_spearman": round(rho_raw, 5),
            "kernel3_spearman": round(rho_smooth, 5),
            "max_abs_spearman": round(max(abs(rho_raw), abs(rho_smooth)), 5),
        }
        print(
            f"  surface Spearman vs {entry['id']:38s}: raw={rho_raw:.4f} k3={rho_smooth:.4f}",
            flush=True,
        )

    assert len(peer_spearman) == 12, f"Expected 12 peer rasters, checked {len(peer_spearman)}"
    max_peer_spearman = max(d["max_abs_spearman"] for d in peer_spearman.values())
    gate_e1_pass = (not leak_flags) and (max_peer_spearman <= 0.90)

    out = {
        "experiment": "E1_H29_canary_and_surface_uniqueness",
        "lane": "L-S7-2026-10-25",
        "preregistration_commit": "30accf8",
        "seeds": SEEDS,
        "n_unique_withheld_positive_pixels": int(hidden_any.sum()),
        "canary_threshold_auc": 0.90,
        "max_h29_direction_invariant_auc": max_h29_auc,
        "max_base_direction_invariant_auc": max_base_auc,
        "canary_h29_features": canary_h29,
        "canary_base_features_direction_invariant": canary_base,
        "canary_leak_flags": leak_flags,
        "surface_spearman_threshold": 0.90,
        "n_peer_rasters_checked": len(peer_spearman),
        "max_peer_abs_spearman": max_peer_spearman,
        "peer_surface_spearman": peer_spearman,
        "gate_e1_pass": gate_e1_pass,
        "runtime_s": round(time.time() - t0, 1),
    }
    dest = paths.EVIDENCE / "h29_e1_canary_and_surface.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print(f"E1 PASS={gate_e1_pass} | max_canary={max_h29_auc:.4f} | max_spearman={max_peer_spearman:.4f}")
    print(f"wrote {dest}")
    return 0 if gate_e1_pass else 2


def emit_poisson(
    prob: np.ndarray, fold_domain: np.ndarray, known: np.ndarray, budget: int
) -> np.ndarray:
    """Blind ridge NMS + priority Poisson disk (zero access to hidden or valid_scoring)."""
    d_vis = distance_transform_edt(~known)
    ridge = oof_detector.ridge_nms(prob, fold_domain)
    cand = ridge & fold_domain & (~known) & (d_vis > B_EXCL)
    return sub.priority_poisson_disk(prob, cand, POISSON_MIN_DIST, budget)


def emit_uniform(
    fold_domain: np.ndarray, known: np.ndarray, budget: int, rng: np.random.Generator
) -> np.ndarray:
    """Blind uniform random eligible off-catalogue null (U0)."""
    d_vis = distance_transform_edt(~known)
    elig = fold_domain & (~known) & (d_vis > B_EXCL)
    ys, xs = np.nonzero(elig)
    out = np.zeros(fold_domain.shape, dtype=bool)
    if ys.size == 0 or budget <= 0:
        return out
    take = rng.choice(ys.size, size=min(budget, ys.size), replace=False)
    out[ys[take], xs[take]] = True
    return out


def emit_weighted_celf(
    prob: np.ndarray, fold_domain: np.ndarray, known: np.ndarray, budget: int
) -> np.ndarray:
    """Blind H29-S probability-weighted 300 m CELF submodular cover."""
    d_vis = distance_transform_edt(~known)
    dom = fold_domain & (~known)
    elig = dom & (d_vis > B_EXCL)
    return coverage_thin.weighted_celf_cover(
        prob,
        elig,
        dom,
        budget=budget,
        radius_px=metric.RADIUS_PX,
        gamma=CELF_GAMMA,
        min_sep_px=CELF_MIN_SEP,
    )


def score_cell(dots: np.ndarray, sp: holdout.HoldoutSplit, valid_mask: np.ndarray) -> dict:
    rs, cs = holdout.crop(dots, sp.fold_mask)
    r0, r1 = max(rs.start - 8, 0), min(rs.stop + 8, grid.SHAPE[0])
    c0, c1 = max(cs.start - 8, 0), min(cs.stop + 8, grid.SHAPE[1])
    sl = (slice(r0, r1), slice(c0, c1))
    return metric.dti_binary(
        dots[sl].astype(float),
        sp.hidden[sl],
        valid=valid_mask[sl] | sp.hidden[sl],
        known=sp.known[sl],
    )


def pooled_dti(cells: list[dict]) -> float:
    tp = sum(c["TPw"] for c in cells)
    fp = sum(c["FPw"] for c in cells)
    fn = sum(c["FNw"] for c in cells)
    return float(tp / (tp + metric.ALPHA * fp + metric.BETA * fn + metric.EPS))


def paired_seed_bootstrap(
    cells_cand: list[dict], cells_base: list[dict], n_boot: int = 10_000, rng_seed: int = 20261025
) -> dict:
    """Deterministic paired bootstrap over the 10 seed-level pooled DTIs (4 quadrants pooled/seed)."""
    n_seeds = len(SEEDS)
    assert len(cells_cand) == 4 * n_seeds and len(cells_base) == 4 * n_seeds
    seed_cand = np.array([pooled_dti(cells_cand[4 * i:4 * (i + 1)]) for i in range(n_seeds)])
    seed_base = np.array([pooled_dti(cells_base[4 * i:4 * (i + 1)]) for i in range(n_seeds)])
    deltas = seed_cand - seed_base
    rng = np.random.default_rng(rng_seed)
    idx = rng.integers(0, n_seeds, size=(n_boot, n_seeds))
    boot_means = deltas[idx].mean(axis=1)
    cell_deltas = np.array([a["dti"] - b["dti"] for a, b in zip(cells_cand, cells_base)])
    fold_wins = 0
    per_fold_delta: dict[str, float] = {}
    for f, fnm in enumerate(holdout.FOLD_NAMES):
        fc = [cells_cand[4 * i + f] for i in range(n_seeds)]
        fb = [cells_base[4 * i + f] for i in range(n_seeds)]
        fd = pooled_dti(fc) - pooled_dti(fb)
        per_fold_delta[fnm] = round(float(fd), 6)
        if fd > 0:
            fold_wins += 1
    return {
        "pooled_delta_dti": round(float(pooled_dti(cells_cand) - pooled_dti(cells_base)), 6),
        "mean_seed_paired_delta_dti": round(float(deltas.mean()), 6),
        "seed_bootstrap_95_ci": [
            round(float(np.percentile(boot_means, 2.5)), 6),
            round(float(np.percentile(boot_means, 97.5)), 6),
        ],
        "positive_seeds": int((deltas > 0).sum()),
        "n_seeds": n_seeds,
        "positive_folds": fold_wins,
        "n_folds": 4,
        "per_fold_pooled_delta_dti": per_fold_delta,
        "positive_cells": int((cell_deltas > 0).sum()),
        "n_cells": len(cell_deltas),
    }


def run_e2() -> int:
    t0 = time.time()
    e1_path = paths.EVIDENCE / "h29_e1_canary_and_surface.json"
    if not e1_path.exists():
        rc = run_e1()
        if rc != 0:
            return rc
    e1_data = json.loads(e1_path.read_text())
    if not e1_data["gate_e1_pass"]:
        print("E1 gate failed; refusing to run E2.", flush=True)
        return 2

    foot, labels, names = load_base()
    fold = holdout.make_quadrant_folds(foot)
    base_X = np.load(paths.PREPARED_FEATURES, mmap_mode="r")
    h29_X = h29.build_h29_feature_matrix(cache_path=CACHE_DIR / "h29_features.npy")

    _, prob_h29_s2 = get_or_fit_h29_quad_oof(base_X, h29_X, labels, foot)
    prob_b0 = get_or_fit_baseline_oof("B0", foot, labels, fold, names)
    prob_d0 = get_or_fit_baseline_oof("D0", foot, labels, fold, names)
    prob_h28 = get_or_fit_baseline_oof("H28_1_B2", foot, labels, fold, names)

    fold_share = np.array([(fold == f).sum() for f in range(4)], dtype=np.float64)
    fold_budget = np.round(BUDGET_TOTAL * fold_share / fold_share.sum()).astype(int)
    # Adjust largest fold by +/-1 if rounding sum differs from BUDGET_TOTAL:
    fold_budget[int(np.argmax(fold_share))] += BUDGET_TOTAL - int(fold_budget.sum())
    assert int(fold_budget.sum()) == BUDGET_TOTAL

    arms = ["U0", "B0", "D0", "H28_1_B2", "H29-A", "H29-S"]
    cells_buf: dict[str, list[dict]] = {a: [] for a in arms}
    cells_unbuf: dict[str, list[dict]] = {a: [] for a in arms}
    n_withheld_occ = 0

    for seed in SEEDS:
        t_seed = time.time()
        for f in range(4):
            sp = holdout.make_split(labels, fold, f, seed=seed)
            fold_domain = foot & sp.fold_mask
            valid_buf = holdout.buffered_scoring_mask(sp, foot, buffer_px=6.0)
            b_f = int(fold_budget[f])
            n_withheld_occ += int(sp.hidden.sum())

            emitted = {
                "U0": emit_uniform(fold_domain, sp.known, b_f, np.random.default_rng(seed * 100 + f)),
                "B0": emit_poisson(prob_b0, fold_domain, sp.known, b_f),
                "D0": emit_poisson(prob_d0, fold_domain, sp.known, b_f),
                "H28_1_B2": emit_poisson(prob_h28, fold_domain, sp.known, b_f),
                "H29-A": emit_poisson(prob_h29_s2, fold_domain, sp.known, b_f),
                "H29-S": emit_weighted_celf(prob_h29_s2, fold_domain, sp.known, b_f),
            }
            for a, dots in emitted.items():
                assert not (dots & ~fold_domain).any(), f"{a} emitted outside fold_domain!"
                assert not (dots & sp.known).any(), f"{a} overlapped known catalogue!"
                cells_buf[a].append(score_cell(dots, sp, valid_buf))
                cells_unbuf[a].append(score_cell(dots, sp, fold_domain))

        print(
            f"seed {seed} ({time.time() - t_seed:.1f}s) buffered pooled: "
            + " ".join(
                f"{a}={pooled_dti(cells_buf[a][-4:]):.4f}" for a in arms
            ),
            flush=True,
        )

    pooled_buf = {a: round(pooled_dti(cells_buf[a]), 6) for a in arms}
    pooled_unbuf = {a: round(pooled_dti(cells_unbuf[a]), 6) for a in arms}

    per_fold_buf: dict[str, dict[str, float]] = {}
    for f, fnm in enumerate(holdout.FOLD_NAMES):
        per_fold_buf[fnm] = {
            a: round(pooled_dti([cells_buf[a][4 * i + f] for i in range(len(SEEDS))]), 6)
            for a in arms
        }

    per_seed_buf: dict[str, dict[str, float]] = {}
    for i, seed in enumerate(SEEDS):
        per_seed_buf[str(seed)] = {
            a: round(pooled_dti(cells_buf[a][4 * i:4 * (i + 1)]), 6)
            for a in arms
        }

    comparisons_buf = {
        "H29S_minus_B0": paired_seed_bootstrap(cells_buf["H29-S"], cells_buf["B0"]),
        "H29S_minus_D0": paired_seed_bootstrap(cells_buf["H29-S"], cells_buf["D0"]),
        "H29S_minus_H28_1_B2": paired_seed_bootstrap(cells_buf["H29-S"], cells_buf["H28_1_B2"]),
        "H29S_minus_H29A": paired_seed_bootstrap(cells_buf["H29-S"], cells_buf["H29-A"]),
        "H29S_minus_U0": paired_seed_bootstrap(cells_buf["H29-S"], cells_buf["U0"]),
        "H29A_minus_B0": paired_seed_bootstrap(cells_buf["H29-A"], cells_buf["B0"]),
        "H29A_minus_D0": paired_seed_bootstrap(cells_buf["H29-A"], cells_buf["D0"]),
    }

    best_baseline_name = max(("B0", "D0", "H28_1_B2"), key=lambda k: pooled_buf[k])
    vs_best = comparisons_buf[f"H29S_minus_{best_baseline_name}"]

    gate_clauses = {
        "pooled_beats_all_baselines": bool(
            pooled_buf["H29-S"] > max(pooled_buf["B0"], pooled_buf["D0"], pooled_buf["H28_1_B2"], pooled_buf["U0"])
        ),
        "mean_paired_delta_vs_best_ge_0p0020": bool(vs_best["mean_seed_paired_delta_dti"] >= 0.0020),
        "ci95_lower_gt_zero_vs_best": bool(vs_best["seed_bootstrap_95_ci"][0] > 0.0),
        "folds_ge_3_of_4_vs_every_baseline": bool(
            min(
                comparisons_buf["H29S_minus_B0"]["positive_folds"],
                comparisons_buf["H29S_minus_D0"]["positive_folds"],
                comparisons_buf["H29S_minus_H28_1_B2"]["positive_folds"],
            )
            >= 3
        ),
        "seeds_ge_8_of_10_vs_every_baseline": bool(
            min(
                comparisons_buf["H29S_minus_B0"]["positive_seeds"],
                comparisons_buf["H29S_minus_D0"]["positive_seeds"],
                comparisons_buf["H29S_minus_H28_1_B2"]["positive_seeds"],
            )
            >= 8
        ),
        "detector_ablation_H29A_beats_B0": bool(pooled_buf["H29-A"] > pooled_buf["B0"]),
    }
    gate_e2_pass = all(gate_clauses.values())

    out = {
        "experiment": "E2_H29_paired_spatial_holdout",
        "lane": "L-S7-2026-10-25",
        "preregistration_commit": "30accf8",
        "evaluator_version": "gems27.metric v1 + holdout-blind-buffered-v2 (alpha=0.2, beta=0.8, R=3px triangular, buffer_px=6.0)",
        "provenance_label": "HOLDOUT-DTI (catalogue-internal whole-component hide-and-recover; NOT a live organizer score)",
        "seeds": SEEDS,
        "folds": holdout.FOLD_NAMES,
        "n_cells": 4 * len(SEEDS),
        "n_withheld_positive_occurrences": n_withheld_occ,
        "matched_full_map_budget": BUDGET_TOTAL,
        "fold_budgets": fold_budget.tolist(),
        "b_exclusion_px": B_EXCL,
        "celf_params": {"gamma": CELF_GAMMA, "min_sep_px": CELF_MIN_SEP},
        "pooled_buffered_holdout_dti": pooled_buf,
        "pooled_unbuffered_diagnostic_holdout_dti": pooled_unbuf,
        "best_baseline_arm": best_baseline_name,
        "per_fold_buffered_holdout_dti": per_fold_buf,
        "per_seed_buffered_holdout_dti": per_seed_buf,
        "paired_comparisons_buffered": comparisons_buf,
        "frozen_gate_clauses": gate_clauses,
        "gate_e2_pass": gate_e2_pass,
        "verdict_stage_e2": "promote" if gate_e2_pass else "negative",
        "runtime_s": round(time.time() - t0, 1),
    }
    dest = paths.EVIDENCE / "h29_e2_holdout_210_219.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print("POOLED BUFFERED HOLDOUT-DTI:", json.dumps(pooled_buf))
    print("POOLED UNBUFFERED DIAGNOSTIC:", json.dumps(pooled_unbuf))
    print("VS BEST BASELINE:", best_baseline_name, json.dumps(vs_best))
    print("GATE CLAUSES:", json.dumps(gate_clauses))
    print(f"E2 PASS={gate_e2_pass} | wrote {dest}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["e1", "e2", "both"], default="both")
    args = ap.parse_args()
    if args.stage == "e1":
        return run_e1()
    if args.stage == "e2":
        return run_e2()
    rc = run_e1()
    if rc != 0:
        return rc
    return run_e2()


if __name__ == "__main__":
    raise SystemExit(main())
