#!/usr/bin/env python3
"""Frozen E1 + E2 evaluation runner for Hypothesis H31-1 (Lane L-S10-2026-10-26).

Preregistered in `knowledge/24_preregistration_H31_2026-10-26.md`:
- Fresh unconsumed holdout seeds: 400..409 (10 seeds x 4 quadrants = 40 cells).
- Off-catalogue rule & matched budget: B2 (`EDT(~known) > 2.0 px`), 37,654 full-map dots.
- Strict blind `emit(...)`: sees ONLY `fold_domain = foot & sp.fold_mask` and `sp.known`
  (zero access to `sp.hidden` or `valid_scoring`).
- Stage `e1`: univariate direction-invariant ROC-AUC leakage canary (<= 0.90) across all 79
  features + pre-placement OOF surface Spearman check (|rho| <= 0.90) vs all 12 peer rasters
  and live-scored GEMSDOE27 submissions (Slot 1 + H29-S).
- Stage `e2`: paired 40-cell buffered spatial holdout (`buffered_scoring_mask`, buffer_px=6.0)
  plus unbuffered diagnostic across U0, B0, H28_1_B2, D0, H29-S, H31-A, and H31-S.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

from gems27 import coverage_thin, grid, holdout, metric, oof_detector, paths, potential_edges
from gems27 import geothermal_conduit_nis as h31
from gems27 import hydrothermal_piedmont as h29
from gems27 import subsurface_features as sub

SEEDS: list[int] = list(range(400, 410))
BUDGET_TOTAL: int = 37_654
B_EXCL: float = 2.0
POISSON_MIN_DIST: float = 2.8

CACHE_DIR = paths.DATA / "h31"
PREREG_PATH = paths.REPO / "knowledge" / "24_preregistration_H31_2026-10-26.md"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_base() -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS) & foot
    with rasterio.open(paths.LIDAR) as ls:
        lid_valid = foot & (ls.read(12) > 0)
    meta = json.loads(paths.PREPARED_META.read_text())
    return foot, labels, lid_valid, meta["names"]


def get_or_build_subsurface15(foot: np.ndarray, names: list[str]) -> np.ndarray:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    p = CACHE_DIR / "subsurface15.npy"
    if p.exists():
        return np.load(p, mmap_mode="r")
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
    del stack, arr, rtp_g, grav_g
    gc.collect()
    return np.load(p, mmap_mode="r")


def get_or_fit_h31_quad_oof(
    base_X: np.ndarray,
    sub15_X: np.ndarray,
    h29_X: np.ndarray,
    h31_X: np.ndarray,
    labels: np.ndarray,
    foot: np.ndarray,
    lid_valid: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    psub_p = CACHE_DIR / "prob_h31_sub_quad.npy"
    ps1_p = CACHE_DIR / "prob_h31_s1_quad.npy"
    ps2_p = CACHE_DIR / "prob_h31_s2_quad.npy"
    if psub_p.exists() and ps1_p.exists() and ps2_p.exists():
        return np.load(psub_p), np.load(ps1_p), np.load(ps2_p)
    print("fitting H31-1 dual-regime 2-stage nested spatial cross-fit (Quadrant 4-fold)...", flush=True)
    t0 = time.time()
    mmap_ps = (
        paths.PREPARED_FEATURES,
        CACHE_DIR / "subsurface15.npy",
        CACHE_DIR / "h29_features.npy",
        CACHE_DIR / "h31_features.npy",
    )
    p_sub, p_s1, p_s2 = h31.fit_predict_dual_regime_oof(
        base_X,
        sub15_X,
        h29_X,
        h31_X,
        labels,
        foot,
        lid_valid,
        buffer_px=h31.BUFFER_PX,
        seed=400,
        cache_dir=CACHE_DIR,
        cache_tag="quad",
        mmap_paths=mmap_ps,
    )
    print(f"  finished H31-1 Quadrant OOF in {time.time() - t0:.1f}s", flush=True)
    np.save(psub_p, p_sub)
    np.save(ps1_p, p_s1)
    np.save(ps2_p, p_s2)
    return p_sub, p_s1, p_s2


def get_or_fit_h29_quad_oof(
    base_X: np.ndarray, h29_X: np.ndarray, labels: np.ndarray, foot: np.ndarray
) -> np.ndarray:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    p2_path = CACHE_DIR / "prob_h29_s2_quad.npy"
    if p2_path.exists():
        return np.load(p2_path)
    print("fitting H29-S 2-stage nested spatial cross-fit control...", flush=True)
    t0 = time.time()
    _, s2 = h29.fit_predict_two_stage_oof(
        base_X, h29_X, labels, foot, buffer_px=h29.BUFFER_PX, seed=210
    )
    print(f"  finished H29-S Quadrant OOF in {time.time() - t0:.1f}s", flush=True)
    np.save(p2_path, s2)
    return s2


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
        prob = oof_detector.fit_predict_oof_probabilities(foot, labels, fold)
    elif arm == "D0":
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


def _canary_auc(vals_pos: np.ndarray, vals_neg: np.ndarray) -> tuple[float, float]:
    v = np.r_[vals_pos.astype(np.float64), vals_neg.astype(np.float64)]
    y = np.r_[np.ones(vals_pos.size, dtype=np.int8), np.zeros(vals_neg.size, dtype=np.int8)]
    ok = np.isfinite(v)
    if ok.sum() < 10 or y[ok].min() == y[ok].max():
        return 0.5, 0.5
    raw = float(roc_auc_score(y[ok], v[ok]))
    return raw, float(max(raw, 1.0 - raw))


def run_e1() -> int:
    t0 = time.time()
    foot, labels, lid_valid, names = load_base()
    fold = holdout.make_quadrant_folds(foot)
    base_X = np.load(paths.PREPARED_FEATURES, mmap_mode="r")
    print("building/loading subsurface15, H29 (20 ch), and H31 (12 ch) feature matrices...", flush=True)
    sub15_X = get_or_build_subsurface15(foot, names)
    h29_X = h29.build_h29_feature_matrix(cache_path=CACHE_DIR / "h29_features.npy")
    h31_X = h31.build_h31_feature_matrix(cache_path=CACHE_DIR / "h31_features.npy")

    # Gather union of withheld positives & buffered scoring domain across frozen seeds 400..409:
    hidden_any = np.zeros_like(labels)
    valid_any = np.zeros_like(labels)
    for seed in SEEDS:
        for f in range(4):
            sp = holdout.make_split(labels, fold, f, seed=seed)
            hidden_any |= sp.hidden
            valid_any |= holdout.buffered_scoring_mask(sp, foot, buffer_px=6.0)

    y_foot = hidden_any[foot]
    scope = (valid_any | hidden_any)[foot]
    idx_scope = np.flatnonzero(scope)
    pos_idx = idx_scope[y_foot[idx_scope]]
    neg_all = idx_scope[~y_foot[idx_scope]]
    rng = np.random.default_rng(400)
    neg_idx = rng.choice(neg_all, size=min(250_000, neg_all.size), replace=False)

    canary_h31: dict[str, dict[str, float]] = {}
    for j, nm in enumerate(h31.H31_FEATURE_NAMES):
        raw, di = _canary_auc(np.asarray(h31_X[pos_idx, j]), np.asarray(h31_X[neg_idx, j]))
        canary_h31[nm] = {"raw_auc": round(raw, 5), "direction_invariant_auc": round(di, 5)}
        print(f"  canary H31 {nm:34s}: raw={raw:.4f} dir_inv={di:.4f}", flush=True)

    canary_h29: dict[str, float] = {}
    for j, nm in enumerate(h29.H29_FEATURE_NAMES):
        _, di = _canary_auc(np.asarray(h29_X[pos_idx, j]), np.asarray(h29_X[neg_idx, j]))
        canary_h29[nm] = round(di, 5)

    canary_sub15: dict[str, float] = {}
    for j, nm in enumerate(sub.TRANSFORM_NAMES):
        _, di = _canary_auc(np.asarray(sub15_X[pos_idx, j]), np.asarray(sub15_X[neg_idx, j]))
        canary_sub15[nm] = round(di, 5)

    canary_base: dict[str, float] = {}
    for j, nm in enumerate(names):
        _, di = _canary_auc(np.asarray(base_X[pos_idx, j]), np.asarray(base_X[neg_idx, j]))
        canary_base[nm] = round(di, 5)

    max_h31_auc = max(d["direction_invariant_auc"] for d in canary_h31.values())
    max_all_auc = max(
        max_h31_auc,
        max(canary_h29.values()),
        max(canary_sub15.values()),
        max(canary_base.values()),
    )
    leak_flags = {
        k: d["direction_invariant_auc"]
        for k, d in canary_h31.items()
        if d["direction_invariant_auc"] > 0.90
    }
    leak_flags.update({f"h29:{k}": v for k, v in canary_h29.items() if v > 0.90})
    leak_flags.update({f"sub15:{k}": v for k, v in canary_sub15.items() if v > 0.90})
    leak_flags.update({f"base:{k}": v for k, v in canary_base.items() if v > 0.90})
    n_pos_union = int(pos_idx.size)
    n_neg_sample = int(neg_idx.size)
    del hidden_any, valid_any, y_foot, scope, idx_scope, pos_idx, neg_all, neg_idx
    gc.collect()
    h31.drop_file_page_cache(
        paths.PREPARED_FEATURES,
        CACHE_DIR / "subsurface15.npy",
        CACHE_DIR / "h29_features.npy",
        CACHE_DIR / "h31_features.npy",
    )

    # Pre-placement Stage-2 OOF surface Spearman check against all 12 peer rasters + live-scored GEMSDOE27 rasters:
    _, _, s2_quad = get_or_fit_h31_quad_oof(base_X, sub15_X, h29_X, h31_X, labels, foot, lid_valid)
    sample_flat = rng.choice(np.flatnonzero(foot.ravel()), size=400_000, replace=False)
    surf_s = s2_quad.ravel()[sample_flat]

    peer_spearman: dict[str, float] = {}
    reg_dir = paths.DATA / "parallel_registry"
    for p in sorted(reg_dir.glob("*.tif")):
        with rasterio.open(p) as ds:
            arr = np.nan_to_num(ds.read(1), nan=0.0).ravel()[sample_flat]
        rho, _ = spearmanr(surf_s, arr)
        peer_spearman[p.name] = round(float(0.0 if np.isnan(rho) else rho), 5)
    assert len(peer_spearman) == 12, f"Expected 12 peer rasters, found {len(peer_spearman)}"

    scored_local_spearman: dict[str, float] = {}
    for p_rel in (
        "docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-allfinite.tif",
        "docs/downloads/gems27-h29-hydrothermal-piedmont-celf-20261025-511898747886-allfinite.tif",
    ):
        p = paths.REPO / p_rel
        with rasterio.open(p) as ds:
            arr = np.nan_to_num(ds.read(1), nan=0.0).ravel()[sample_flat]
        rho, _ = spearmanr(surf_s, arr)
        scored_local_spearman[p.name] = round(float(0.0 if np.isnan(rho) else rho), 5)

    max_abs_spearman = max(
        max(abs(v) for v in peer_spearman.values()),
        max(abs(v) for v in scored_local_spearman.values()),
    )

    gate_e1_pass = (len(leak_flags) == 0) and (max_all_auc <= 0.90) and (max_abs_spearman <= 0.90)
    out = {
        "experiment": "E1_H31_leakage_canary_and_surface_uniqueness",
        "lane": "L-S10-2026-10-26",
        "preregistration_doc": str(PREREG_PATH.relative_to(paths.REPO)),
        "preregistration_sha256": sha256_file(PREREG_PATH),
        "seeds": SEEDS,
        "n_withheld_positive_pixels_union": n_pos_union,
        "n_negative_sample": n_neg_sample,
        "n_features_checked": len(h31.H31_FEATURE_NAMES) + len(h29.H29_FEATURE_NAMES) + len(sub.TRANSFORM_NAMES) + len(names),
        "canary_h31_features": canary_h31,
        "canary_h29_direction_invariant_auc": canary_h29,
        "canary_sub15_direction_invariant_auc": canary_sub15,
        "canary_base32_direction_invariant_auc": canary_base,
        "max_h31_direction_invariant_auc": round(max_h31_auc, 5),
        "max_all_79_direction_invariant_auc": round(max_all_auc, 5),
        "auc_stop_threshold": 0.90,
        "leakage_flags": leak_flags,
        "preplacement_surface_spearman_vs_12_peers": peer_spearman,
        "preplacement_surface_spearman_vs_scored_gems27": scored_local_spearman,
        "max_abs_preplacement_spearman": round(max_abs_spearman, 5),
        "spearman_stop_threshold": 0.90,
        "gate_e1_pass": gate_e1_pass,
        "runtime_s": round(time.time() - t0, 1),
    }
    dest = paths.EVIDENCE / "h31_s10_e1_canary_and_surface.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print(
        f"E1 PASS={gate_e1_pass} | max_H31_AUC={max_h31_auc:.4f} max_all79_AUC={max_all_auc:.4f} "
        f"| max_|rho|={max_abs_spearman:.4f} | wrote {dest}",
        flush=True,
    )
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


def emit_h29_celf(
    prob: np.ndarray, fold_domain: np.ndarray, known: np.ndarray, budget: int
) -> np.ndarray:
    """Blind Session-7 H29-S emitter (gamma=1.5, min_sep_px=2.0)."""
    d_vis = distance_transform_edt(~known)
    dom = fold_domain & (~known)
    elig = dom & (d_vis > B_EXCL)
    return coverage_thin.weighted_celf_cover(
        prob, elig, dom, budget=budget, radius_px=metric.RADIUS_PX, gamma=1.5, min_sep_px=2.0
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


def seed_bootstrap_ci(cells: list[dict], n_boot: int = 10_000, rng_seed: int = 20261026) -> list[float]:
    n_seeds = len(SEEDS)
    vals = np.array([pooled_dti(cells[4 * i : 4 * (i + 1)]) for i in range(n_seeds)])
    rng = np.random.default_rng(rng_seed)
    idx = rng.integers(0, n_seeds, size=(n_boot, n_seeds))
    means = vals[idx].mean(axis=1)
    return [round(float(np.percentile(means, 2.5)), 6), round(float(np.percentile(means, 97.5)), 6)]


def paired_seed_bootstrap(
    cells_cand: list[dict], cells_base: list[dict], n_boot: int = 10_000, rng_seed: int = 20261026
) -> dict:
    """Deterministic paired bootstrap over the 10 seed-level pooled DTIs (4 quadrants pooled/seed)."""
    n_seeds = len(SEEDS)
    assert len(cells_cand) == 4 * n_seeds and len(cells_base) == 4 * n_seeds
    seed_cand = np.array([pooled_dti(cells_cand[4 * i : 4 * (i + 1)]) for i in range(n_seeds)])
    seed_base = np.array([pooled_dti(cells_base[4 * i : 4 * (i + 1)]) for i in range(n_seeds)])
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
    ci95 = [
        round(float(np.percentile(boot_means, 2.5)), 6),
        round(float(np.percentile(boot_means, 97.5)), 6),
    ]
    return {
        "pooled_delta_dti": round(float(pooled_dti(cells_cand) - pooled_dti(cells_base)), 6),
        "mean_delta": round(float(deltas.mean()), 6),
        "mean_seed_paired_delta_dti": round(float(deltas.mean()), 6),
        "ci95": ci95,
        "seed_bootstrap_95_ci": ci95,
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
    e1_path = paths.EVIDENCE / "h31_s10_e1_canary_and_surface.json"
    if not e1_path.exists():
        rc = run_e1()
        if rc != 0:
            return rc
    e1_data = json.loads(e1_path.read_text())
    if not e1_data["gate_e1_pass"]:
        print("E1 gate failed; refusing to run E2.", flush=True)
        return 2

    foot, labels, lid_valid, names = load_base()
    fold = holdout.make_quadrant_folds(foot)
    base_X = np.load(paths.PREPARED_FEATURES, mmap_mode="r")
    sub15_X = get_or_build_subsurface15(foot, names)
    h29_X = h29.build_h29_feature_matrix(cache_path=CACHE_DIR / "h29_features.npy")
    h31_X = h31.build_h31_feature_matrix(cache_path=CACHE_DIR / "h31_features.npy")

    _, _, prob_h31_s2 = get_or_fit_h31_quad_oof(
        base_X, sub15_X, h29_X, h31_X, labels, foot, lid_valid
    )
    mmap_ps = (
        paths.PREPARED_FEATURES,
        CACHE_DIR / "subsurface15.npy",
        CACHE_DIR / "h29_features.npy",
        CACHE_DIR / "h31_features.npy",
    )
    h31.drop_file_page_cache(*mmap_ps)
    prob_b0 = get_or_fit_baseline_oof("B0", foot, labels, fold, names)
    h31.drop_file_page_cache(*mmap_ps)
    prob_d0 = get_or_fit_baseline_oof("D0", foot, labels, fold, names)
    h31.drop_file_page_cache(*mmap_ps)
    prob_h28 = get_or_fit_baseline_oof("H28_1_B2", foot, labels, fold, names)
    h31.drop_file_page_cache(*mmap_ps)
    prob_h29_s2 = get_or_fit_h29_quad_oof(base_X, h29_X, labels, foot)
    h31.drop_file_page_cache(*mmap_ps)

    fold_share = np.array([(fold == f).sum() for f in range(4)], dtype=np.float64)
    fold_budget = np.round(BUDGET_TOTAL * fold_share / fold_share.sum()).astype(int)
    fold_budget[int(np.argmax(fold_share))] += BUDGET_TOTAL - int(fold_budget.sum())
    assert int(fold_budget.sum()) == BUDGET_TOTAL

    arms = ["U0", "B0", "H28_1_B2", "D0", "H29-S", "H31-A", "H31-S"]
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
                "H28_1_B2": emit_poisson(prob_h28, fold_domain, sp.known, b_f),
                "D0": emit_poisson(prob_d0, fold_domain, sp.known, b_f),
                "H29-S": emit_h29_celf(prob_h29_s2, fold_domain, sp.known, b_f),
                "H31-A": emit_poisson(prob_h31_s2, fold_domain, sp.known, b_f),
                "H31-S": h31.emit_h31_celf(prob_h31_s2, fold_domain, sp.known, b_f),
            }
            for a, dots in emitted.items():
                assert not (dots & ~fold_domain).any(), f"{a} emitted outside fold_domain!"
                assert not (dots & sp.known).any(), f"{a} overlapped known catalogue!"
                cells_buf[a].append(score_cell(dots, sp, valid_buf))
                cells_unbuf[a].append(score_cell(dots, sp, fold_domain))

        print(
            f"seed {seed} ({time.time() - t_seed:.1f}s) buffered pooled: "
            + " ".join(f"{a}={pooled_dti(cells_buf[a][-4:]):.4f}" for a in arms),
            flush=True,
        )

    pooled_buf = {a: round(pooled_dti(cells_buf[a]), 6) for a in arms}
    pooled_unbuf = {a: round(pooled_dti(cells_unbuf[a]), 6) for a in arms}
    arm_ci95_buf = {a: seed_bootstrap_ci(cells_buf[a]) for a in arms}

    per_fold_buf: dict[str, dict[str, float]] = {}
    for f, fnm in enumerate(holdout.FOLD_NAMES):
        per_fold_buf[fnm] = {
            a: round(pooled_dti([cells_buf[a][4 * i + f] for i in range(len(SEEDS))]), 6)
            for a in arms
        }

    per_seed_buf: dict[str, dict[str, float]] = {}
    for i, seed in enumerate(SEEDS):
        per_seed_buf[str(seed)] = {
            a: round(pooled_dti(cells_buf[a][4 * i : 4 * (i + 1)]), 6)
            for a in arms
        }

    comparisons_buf = {
        "H31S_minus_B0": paired_seed_bootstrap(cells_buf["H31-S"], cells_buf["B0"]),
        "H31S_minus_D0": paired_seed_bootstrap(cells_buf["H31-S"], cells_buf["D0"]),
        "H31S_minus_H28_1_B2": paired_seed_bootstrap(cells_buf["H31-S"], cells_buf["H28_1_B2"]),
        "H31S_minus_H29S": paired_seed_bootstrap(cells_buf["H31-S"], cells_buf["H29-S"]),
        "H31S_minus_H31A": paired_seed_bootstrap(cells_buf["H31-S"], cells_buf["H31-A"]),
        "H31S_minus_U0": paired_seed_bootstrap(cells_buf["H31-S"], cells_buf["U0"]),
        "H31A_minus_D0": paired_seed_bootstrap(cells_buf["H31-A"], cells_buf["D0"]),
        "H31A_minus_B0": paired_seed_bootstrap(cells_buf["H31-A"], cells_buf["B0"]),
    }

    vs_b0 = comparisons_buf["H31S_minus_B0"]
    vs_d0 = comparisons_buf["H31S_minus_D0"]
    vs_h29s = comparisons_buf["H31S_minus_H29S"]

    gate_clauses = {
        "pooled_beats_every_baseline": bool(
            pooled_buf["H31-S"]
            > max(
                pooled_buf["U0"],
                pooled_buf["B0"],
                pooled_buf["H28_1_B2"],
                pooled_buf["D0"],
                pooled_buf["H29-S"],
            )
        ),
        "ci95_gt_zero_and_9seeds_4folds_vs_B0": bool(
            vs_b0["ci95"][0] > 0.0 and vs_b0["positive_seeds"] >= 9 and vs_b0["positive_folds"] == 4
        ),
        "ci95_gt_zero_and_3folds_vs_D0": bool(
            vs_d0["ci95"][0] > 0.0 and vs_d0["positive_folds"] >= 3
        ),
        "ci95_gt_zero_and_8seeds_vs_H29S": bool(
            vs_h29s["ci95"][0] > 0.0 and vs_h29s["positive_seeds"] >= 8
        ),
        "detector_ablation_H31A_beats_D0": bool(pooled_buf["H31-A"] > pooled_buf["D0"]),
    }
    gate_e2_pass = all(gate_clauses.values())

    out = {
        "experiment": "E2_H31_paired_spatial_holdout",
        "lane": "L-S10-2026-10-26",
        "preregistration_doc": str(PREREG_PATH.relative_to(paths.REPO)),
        "preregistration_sha256": sha256_file(PREREG_PATH),
        "evaluator_version": "gems27.metric v1 + holdout-blind-buffered-v2 (alpha=0.2, beta=0.8, R=3px triangular, buffer_px=6.0)",
        "provenance_label": "HOLDOUT-DTI (catalogue-internal whole-component hide-and-recover; NOT a live organizer score)",
        "seeds": SEEDS,
        "folds": holdout.FOLD_NAMES,
        "n_cells": 4 * len(SEEDS),
        "n_withheld_positive_occurrences": n_withheld_occ,
        "matched_full_map_budget": BUDGET_TOTAL,
        "fold_budgets": fold_budget.tolist(),
        "b_exclusion_px": B_EXCL,
        "celf_params": {"gamma": h31.CELF_GAMMA, "min_sep_px": h31.CELF_MIN_SEP_PX},
        "pooled_buffered_holdout_dti": pooled_buf,
        "pooled_buffered_ci95": arm_ci95_buf,
        "pooled_unbuffered_diagnostic_holdout_dti": pooled_unbuf,
        "per_fold_buffered_holdout_dti": per_fold_buf,
        "per_seed_buffered_holdout_dti": per_seed_buf,
        "paired_comparisons_buffered": comparisons_buf,
        "frozen_gate_clauses": gate_clauses,
        "gate_e2_pass": gate_e2_pass,
        "verdict_stage_e2": "promote" if gate_e2_pass else "negative",
        "runtime_s": round(time.time() - t0, 1),
    }
    dest = paths.EVIDENCE / "h31_s10_e2_holdout_400_409.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print("POOLED BUFFERED HOLDOUT-DTI:", json.dumps(pooled_buf), flush=True)
    print("POOLED UNBUFFERED DIAGNOSTIC:", json.dumps(pooled_unbuf), flush=True)
    print("PER-FOLD BUFFERED:", json.dumps(per_fold_buf), flush=True)
    print("VS B0:", json.dumps(vs_b0), flush=True)
    print("VS D0:", json.dumps(vs_d0), flush=True)
    print("VS H29-S:", json.dumps(vs_h29s), flush=True)
    print("GATE CLAUSES:", json.dumps(gate_clauses), flush=True)
    print(f"E2 PASS={gate_e2_pass} | wrote {dest}", flush=True)
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
