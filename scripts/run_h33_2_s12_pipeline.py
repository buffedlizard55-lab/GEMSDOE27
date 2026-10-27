#!/usr/bin/env python3
"""Frozen E1 + E2 + E3 pipeline for Experiment 2 of 3: Hypothesis H33-2 (Lane L-S12B-2026-10-26).

Preregistered in `knowledge/29_preregistration_H33_2_2026-10-26.md` (git commit `f3c4074`):
- Fresh unconsumed holdout seeds: 610..619 (10 seeds x 4 quadrants = 40 cells).
- Deconfounded Stage-1 feature bank (58 cols: 20 non-LiDAR base + 15 sub15 + 15 non-LiDAR H33
  + 3 non-LiDAR H33-2 + 5 deconfounded 1 m LiDAR structural transforms; zero raw u8 base LiDAR).
- Zero-interior-overlap 1-D manifold CELF cover (`min_sep_px = 3.45`, `gamma = 1.30`, `37,654` dots).
- Stage `e1` screens BOTH univariate leakage canary (`<= 0.90`) AND exact stitched (`0° + 45°`)
  surface Spearman (`<= 0.90`) + 3-px dot overlap (`<= 0.70`) vs all 12 peer rasters + Slot 1 + H29-S
  + Session-10 H31-1 (`cf8e1bbef244`) BEFORE running any holdout seed in `e2`.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

from gems27 import asymmetric_graben_conduit as h33
from gems27 import coverage_thin, grid, holdout, metric, oof_detector, paths, readiness, submission
from gems27 import geothermal_conduit_nis as h31
from gems27 import hydrothermal_piedmont as h29
from gems27 import subsurface_features as sub

SEEDS: list[int] = list(range(610, 620))
BUDGET_TOTAL: int = 37_654
B_EXCL: float = 2.0
POISSON_MIN_DIST: float = 2.8
DATE_TAG: str = "20261026"

CACHE_H33 = paths.DATA / "h33"
CACHE_H31 = paths.DATA / "h31"
DL_DIR = paths.DOCS / "downloads"
PREREG_PATH = paths.REPO / "knowledge" / "29_preregistration_H33_2_2026-10-26.md"

OPERATIVE_GEMS27_REFS: tuple[tuple[str, str], ...] = (
    (
        "gems27_slot1_5512495c6bd1_02449",
        "docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-allfinite.tif",
    ),
    (
        "gems27_h29s_511898747886_02190",
        "docs/downloads/gems27-h29-hydrothermal-piedmont-celf-20261025-511898747886-allfinite.tif",
    ),
    (
        "gems27_h31s10_cf8e1bbef244_unscored",
        "docs/downloads/gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif",
    ),
)


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


def _canary_auc(vals_pos: np.ndarray, vals_neg: np.ndarray) -> tuple[float, float]:
    v = np.r_[vals_pos.astype(np.float64), vals_neg.astype(np.float64)]
    y = np.r_[np.ones(vals_pos.size, dtype=np.int8), np.zeros(vals_neg.size, dtype=np.int8)]
    ok = np.isfinite(v)
    if ok.sum() < 10 or y[ok].min() == y[ok].max():
        return 0.5, 0.5
    raw = float(roc_auc_score(y[ok], v[ok]))
    return raw, float(max(raw, 1.0 - raw))


def get_or_fit_h33_2_oof(
    tag: str,
    seed: int,
    fold_masks: list[np.ndarray] | None,
    base_X: np.ndarray,
    sub15_X: np.ndarray,
    h33_X: np.ndarray,
    h33_2_X: np.ndarray,
    labels: np.ndarray,
    foot: np.ndarray,
    lid_valid: np.ndarray,
) -> np.ndarray:
    CACHE_H33.mkdir(parents=True, exist_ok=True)
    ps2_p = CACHE_H33 / f"prob_h332_s2_{tag}.npy"
    if ps2_p.exists():
        return np.load(ps2_p)
    print(f"fitting H33-2 dual-regime OOF ({tag})...", flush=True)
    t0 = time.time()
    mmap_ps = (
        paths.PREPARED_FEATURES,
        CACHE_H33 / "subsurface15.npy",
        CACHE_H33 / "h33_features.npy",
        CACHE_H33 / "h33_2_extra.npy",
    )
    p_sub, p_s1, p_s2 = h33.fit_predict_h33_2_dual_regime_oof(
        base_X,
        sub15_X,
        h33_X,
        h33_2_X,
        labels,
        foot,
        lid_valid,
        fold_masks=fold_masks,
        buffer_px=h33.BUFFER_PX,
        seed=seed,
        cache_dir=CACHE_H33,
        cache_tag=tag,
        mmap_paths=mmap_ps,
    )
    np.save(CACHE_H33 / f"prob_h332_sub_{tag}.npy", p_sub)
    np.save(CACHE_H33 / f"prob_h332_s1_{tag}.npy", p_s1)
    np.save(ps2_p, p_s2)
    del p_sub, p_s1
    gc.collect()
    h31.drop_file_page_cache(*mmap_ps)
    print(f"  finished H33-2 OOF ({tag}) in {time.time() - t0:.1f}s", flush=True)
    return p_s2


def dot_overlap_and_spearman(
    cand_pts: np.ndarray,
    cand_inside: np.ndarray,
    cand_surf_inside: np.ndarray,
    ref_tif: Path,
    foot: np.ndarray,
    labels: np.ndarray,
) -> dict[str, float | int]:
    with rasterio.open(ref_tif) as ds:
        arr = np.nan_to_num(ds.read(1), nan=0.0).astype(np.float32)
    ref_inside = arr[foot]
    ref_dots = (arr > 0.5) & foot & (~labels)
    ref_pts = np.argwhere(ref_dots).astype(np.float64)
    if ref_pts.shape[0] == 0:
        ov_cand_to_ref = 0.0
        ov_ref_to_cand = 0.0
    else:
        t_ref = cKDTree(ref_pts)
        d_c2r, _ = t_ref.query(cand_pts, k=1)
        ov_cand_to_ref = float((d_c2r <= 3.0 + 1e-9).mean())
        t_cand = cKDTree(cand_pts)
        d_r2c, _ = t_cand.query(ref_pts, k=1)
        ov_ref_to_cand = float((d_r2c <= 3.0 + 1e-9).mean())

    rng = np.random.default_rng(20261026)
    take = rng.choice(cand_inside.size, size=min(400_000, cand_inside.size), replace=False)
    rho_dots, _ = spearmanr(cand_inside[take], ref_inside[take])
    rho_surf, _ = spearmanr(cand_surf_inside[take], ref_inside[take])
    return {
        "ref_dots": int(ref_pts.shape[0]),
        "candidate_dot_fraction_within_3px": round(ov_cand_to_ref, 5),
        "reference_dot_fraction_within_3px": round(ov_ref_to_cand, 5),
        "postplacement_dot_spearman": round(float(0.0 if np.isnan(rho_dots) else rho_dots), 5),
        "preplacement_surface_spearman": round(float(0.0 if np.isnan(rho_surf) else rho_surf), 5),
    }


def run_e1() -> int:
    t0 = time.time()
    foot, labels, lid_valid, names = load_base()
    fold = holdout.make_quadrant_folds(foot)
    base_X = np.load(paths.PREPARED_FEATURES, mmap_mode="r")
    sub15_X = np.load(CACHE_H33 / "subsurface15.npy", mmap_mode="r")
    h33_X = h33.build_h33_feature_matrix(cache_path=CACHE_H33 / "h33_features.npy")
    print("building/loading H33-2 extra 4-ch feature matrix...", flush=True)
    h33_2_X = h33.build_h33_2_extra_matrix(h33_X, cache_path=CACHE_H33 / "h33_2_extra.npy")

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
    rng = np.random.default_rng(610)
    neg_idx = rng.choice(neg_all, size=min(250_000, neg_all.size), replace=False)

    canary_h332: dict[str, dict[str, float]] = {}
    for j, nm in enumerate(h33.H33_2_EXTRA_NAMES):
        raw, di = _canary_auc(np.asarray(h33_2_X[pos_idx, j]), np.asarray(h33_2_X[neg_idx, j]))
        canary_h332[nm] = {"raw_auc": round(raw, 5), "direction_invariant_auc": round(di, 5)}
        print(f"  canary H33-2 {nm:34s}: raw={raw:.4f} dir_inv={di:.4f}", flush=True)

    canary_h33 = {
        nm: round(_canary_auc(np.asarray(h33_X[pos_idx, j]), np.asarray(h33_X[neg_idx, j]))[1], 5)
        for j, nm in enumerate(h33.H33_FEATURE_NAMES)
    }
    canary_sub15 = {
        nm: round(_canary_auc(np.asarray(sub15_X[pos_idx, j]), np.asarray(sub15_X[neg_idx, j]))[1], 5)
        for j, nm in enumerate(sub.TRANSFORM_NAMES)
    }
    canary_base20 = {
        names[j]: round(_canary_auc(np.asarray(base_X[pos_idx, j]), np.asarray(base_X[neg_idx, j]))[1], 5)
        for j in h33.BASE_NON_LIDAR_IDX
    }

    max_h332_auc = max(d["direction_invariant_auc"] for d in canary_h332.values())
    max_all_58_auc = max(
        max_h332_auc,
        max(canary_h33.values()),
        max(canary_sub15.values()),
        max(canary_base20.values()),
    )
    leak_flags = {
        k: d["direction_invariant_auc"]
        for k, d in canary_h332.items()
        if d["direction_invariant_auc"] > 0.90
    }
    leak_flags.update({f"h33:{k}": v for k, v in canary_h33.items() if v > 0.90})
    leak_flags.update({f"sub15:{k}": v for k, v in canary_sub15.items() if v > 0.90})
    leak_flags.update({f"base20:{k}": v for k, v in canary_base20.items() if v > 0.90})
    n_pos_union = int(pos_idx.size)
    n_neg_sample = int(neg_idx.size)
    del hidden_any, valid_any, y_foot, scope, idx_scope, pos_idx, neg_all, neg_idx
    gc.collect()

    # Fit BOTH 0-deg Quadrant OOF and 45-deg Rotated OOF to screen EXACT stitched E3 uniqueness BEFORE E2!
    s2_quad = get_or_fit_h33_2_oof(
        "quad", 610, None, base_X, sub15_X, h33_X, h33_2_X, labels, foot, lid_valid
    )
    rot_folds = h29.sector_masks_rotated45(foot)
    s2_rot45 = get_or_fit_h33_2_oof(
        "rot45", 611, rot_folds, base_X, sub15_X, h33_X, h33_2_X, labels, foot, lid_valid
    )
    prob_stitched = (np.float32(0.5) * s2_quad + np.float32(0.5) * s2_rot45).astype(np.float32)
    prob_stitched[~foot] = 0.0
    np.save(CACHE_H33 / "prob_h332_stitched_oof.npy", prob_stitched)

    dots_stitched = h33.emit_h33_2_celf(prob_stitched, foot, labels, budget=BUDGET_TOTAL, b_excl=B_EXCL)
    np.save(CACHE_H33 / "dots_h332_stitched.npy", dots_stitched)

    cand_pts = np.argwhere(dots_stitched).astype(np.float64)
    cand_inside = dots_stitched[foot].astype(np.float32)
    surf_inside = prob_stitched[foot]

    peer_metrics: dict[str, dict] = {}
    for p_tif in sorted((paths.DATA / "parallel_registry").glob("*.tif")):
        peer_metrics[p_tif.name] = dot_overlap_and_spearman(
            cand_pts, cand_inside, surf_inside, p_tif, foot, labels
        )
    assert len(peer_metrics) == 12

    local_metrics: dict[str, dict] = {}
    for k_nm, p_rel in OPERATIVE_GEMS27_REFS:
        local_metrics[k_nm] = dot_overlap_and_spearman(
            cand_pts, cand_inside, surf_inside, paths.REPO / p_rel, foot, labels
        )

    max_peer_ov = max(float(v["candidate_dot_fraction_within_3px"]) for v in peer_metrics.values())
    max_g27_ov = max(float(v["candidate_dot_fraction_within_3px"]) for v in local_metrics.values())
    max_stitched_ov = max(max_peer_ov, max_g27_ov)

    max_abs_rho = max(
        max(abs(float(v["preplacement_surface_spearman"])) for v in peer_metrics.values()),
        max(abs(float(v["postplacement_dot_spearman"])) for v in peer_metrics.values()),
        max(abs(float(v["preplacement_surface_spearman"])) for v in local_metrics.values()),
        max(abs(float(v["postplacement_dot_spearman"])) for v in local_metrics.values()),
    )

    gate_e1_pass = (
        (len(leak_flags) == 0)
        and (max_all_58_auc <= 0.90)
        and (max_abs_rho <= 0.90)
        and (max_stitched_ov <= 0.70)
    )
    out = {
        "experiment": "E1_H33_2_leakage_canary_and_stitched_uniqueness_gate",
        "lane": "L-S12B-2026-10-26",
        "preregistration_doc": str(PREREG_PATH.relative_to(paths.REPO)),
        "preregistration_sha256": sha256_file(PREREG_PATH),
        "seeds": SEEDS,
        "n_withheld_positive_pixels_union": n_pos_union,
        "n_negative_sample": n_neg_sample,
        "n_features_checked": 58,
        "canary_h33_2_extra": canary_h332,
        "canary_h33_direction_invariant_auc": canary_h33,
        "canary_sub15_direction_invariant_auc": canary_sub15,
        "canary_base20_direction_invariant_auc": canary_base20,
        "max_h33_2_extra_direction_invariant_auc": round(max_h332_auc, 5),
        "max_all_58_direction_invariant_auc": round(max_all_58_auc, 5),
        "auc_stop_threshold": 0.90,
        "leakage_flags": leak_flags,
        "stitched_peer_uniqueness": peer_metrics,
        "stitched_operative_gems27_uniqueness": local_metrics,
        "max_stitched_peer_3px_overlap": round(max_peer_ov, 5),
        "max_stitched_operative_gems27_3px_overlap": round(max_g27_ov, 5),
        "max_stitched_3px_dot_overlap": round(max_stitched_ov, 5),
        "stitched_3px_overlap_vs_h31_cf8e1bbef244": local_metrics["gems27_h31s10_cf8e1bbef244_unscored"][
            "candidate_dot_fraction_within_3px"
        ],
        "max_abs_spearman": round(max_abs_rho, 5),
        "spearman_stop_threshold": 0.90,
        "dot_overlap_stop_threshold": 0.70,
        "gate_e1_pass": gate_e1_pass,
        "runtime_s": round(time.time() - t0, 1),
    }
    dest = paths.EVIDENCE / "h33_2_s12_e1_canary_and_stitched_uniqueness.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print(
        f"E1 PASS={gate_e1_pass} | max_AUC={max_all_58_auc:.4f} | max_|rho|={max_abs_rho:.4f} "
        f"| max_stitched_3px_ov={max_stitched_ov:.4f} "
        f"(vs_H31_cf8e={out['stitched_3px_overlap_vs_h31_cf8e1bbef244']:.4f}, vs_peers={max_peer_ov:.4f}) -> {dest}",
        flush=True,
    )
    return 0 if gate_e1_pass else 2


def emit_poisson(prob: np.ndarray, fold_domain: np.ndarray, known: np.ndarray, budget: int) -> np.ndarray:
    d_vis = distance_transform_edt(~known)
    ridge = oof_detector.ridge_nms(prob, fold_domain)
    cand = ridge & fold_domain & (~known) & (d_vis > B_EXCL)
    return sub.priority_poisson_disk(prob, cand, POISSON_MIN_DIST, budget)


def emit_uniform(fold_domain: np.ndarray, known: np.ndarray, budget: int, rng: np.random.Generator) -> np.ndarray:
    d_vis = distance_transform_edt(~known)
    elig = fold_domain & (~known) & (d_vis > B_EXCL)
    ys, xs = np.nonzero(elig)
    out = np.zeros(fold_domain.shape, dtype=bool)
    if ys.size == 0 or budget <= 0:
        return out
    take = rng.choice(ys.size, size=min(budget, ys.size), replace=False)
    out[ys[take], xs[take]] = True
    return out


def emit_h29_celf(prob: np.ndarray, fold_domain: np.ndarray, known: np.ndarray, budget: int) -> np.ndarray:
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
    n_seeds = len(SEEDS)
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
    e1_path = paths.EVIDENCE / "h33_2_s12_e1_canary_and_stitched_uniqueness.json"
    if not e1_path.exists():
        rc = run_e1()
        if rc != 0:
            return rc
    e1_data = json.loads(e1_path.read_text())
    if not e1_data["gate_e1_pass"]:
        print("E1 gate failed; refusing to run E2.", flush=True)
        return 2

    foot, labels, _, _ = load_base()
    fold = holdout.make_quadrant_folds(foot)

    prob_b0 = np.load(CACHE_H33 / "prob_B0_quad.npy")
    prob_d0 = np.load(CACHE_H33 / "prob_D0_quad.npy")
    prob_h29_s2 = np.load(CACHE_H31 / "prob_h29_s2_quad.npy")
    prob_h31_s2 = np.load(CACHE_H31 / "prob_h31_s2_quad.npy")
    prob_h332_s2 = np.load(CACHE_H33 / "prob_h332_s2_quad.npy")
    gc.collect()

    fold_share = np.array([(fold == f).sum() for f in range(4)], dtype=np.float64)
    fold_budget = np.round(BUDGET_TOTAL * fold_share / fold_share.sum()).astype(int)
    fold_budget[int(np.argmax(fold_share))] += BUDGET_TOTAL - int(fold_budget.sum())
    assert int(fold_budget.sum()) == BUDGET_TOTAL

    arms = ["U0", "B0", "D0", "H29-S", "H31-S", "H33_2-A", "H33_2-S"]
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
                "H29-S": emit_h29_celf(prob_h29_s2, fold_domain, sp.known, b_f),
                "H31-S": h31.emit_h31_celf(prob_h31_s2, fold_domain, sp.known, b_f),
                "H33_2-A": emit_poisson(prob_h332_s2, fold_domain, sp.known, b_f),
                "H33_2-S": h33.emit_h33_2_celf(prob_h332_s2, fold_domain, sp.known, b_f),
            }
            for a, dots in emitted.items():
                assert not (dots & ~fold_domain).any()
                assert not (dots & sp.known).any()
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

    per_fold_buf = {
        fnm: {a: round(pooled_dti([cells_buf[a][4 * i + f] for i in range(len(SEEDS))]), 6) for a in arms}
        for f, fnm in enumerate(holdout.FOLD_NAMES)
    }
    per_seed_buf = {
        str(seed): {a: round(pooled_dti(cells_buf[a][4 * i : 4 * (i + 1)]), 6) for a in arms}
        for i, seed in enumerate(SEEDS)
    }

    comparisons_buf = {
        "H33_2S_minus_B0": paired_seed_bootstrap(cells_buf["H33_2-S"], cells_buf["B0"]),
        "H33_2S_minus_D0": paired_seed_bootstrap(cells_buf["H33_2-S"], cells_buf["D0"]),
        "H33_2S_minus_H29S": paired_seed_bootstrap(cells_buf["H33_2-S"], cells_buf["H29-S"]),
        "H33_2S_minus_H31S": paired_seed_bootstrap(cells_buf["H33_2-S"], cells_buf["H31-S"]),
        "H33_2S_minus_H33_2A": paired_seed_bootstrap(cells_buf["H33_2-S"], cells_buf["H33_2-A"]),
        "H33_2S_minus_U0": paired_seed_bootstrap(cells_buf["H33_2-S"], cells_buf["U0"]),
        "H33_2A_minus_D0": paired_seed_bootstrap(cells_buf["H33_2-A"], cells_buf["D0"]),
    }

    vs_b0 = comparisons_buf["H33_2S_minus_B0"]
    vs_d0 = comparisons_buf["H33_2S_minus_D0"]
    vs_h29s = comparisons_buf["H33_2S_minus_H29S"]
    vs_h31s = comparisons_buf["H33_2S_minus_H31S"]

    gate_clauses = {
        "a_pooled_beats_all_including_H31S": bool(
            pooled_buf["H33_2-S"]
            > max(
                pooled_buf["U0"],
                pooled_buf["B0"],
                pooled_buf["D0"],
                pooled_buf["H29-S"],
                pooled_buf["H31-S"],
            )
        ),
        "b_paired_mean_gain_thresholds": bool(
            vs_d0["mean_seed_paired_delta_dti"] >= 0.0020
            and vs_h29s["mean_seed_paired_delta_dti"] >= 0.0010
            and vs_h31s["mean_seed_paired_delta_dti"] > 0.0
        ),
        "c_ci95_and_seed_consistency": bool(
            vs_b0["ci95"][0] > 0.0
            and vs_d0["ci95"][0] > 0.0
            and vs_h29s["ci95"][0] > 0.0
            and vs_b0["positive_seeds"] >= 8
            and vs_d0["positive_seeds"] >= 8
            and vs_h29s["positive_seeds"] >= 8
            and vs_h31s["positive_seeds"] >= 6
        ),
        "d_quadrant_and_western_graben_gain": bool(
            vs_b0["positive_folds"] >= 3
            and vs_d0["positive_folds"] >= 3
            and vs_h29s["positive_folds"] >= 3
            and (
                per_fold_buf["NW"]["H33_2-S"] > per_fold_buf["NW"]["H31-S"]
                or per_fold_buf["SW"]["H33_2-S"] > per_fold_buf["SW"]["H31-S"]
            )
        ),
        "e_e1_canary_and_stitched_uniqueness_pass": bool(e1_data["gate_e1_pass"]),
    }
    gate_e2_pass = all(gate_clauses.values())

    out = {
        "experiment": "E2_H33_2_paired_spatial_holdout",
        "lane": "L-S12B-2026-10-26",
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
        "celf_params": {"gamma": h33.CELF_GAMMA_H33_2, "min_sep_px": h33.CELF_MIN_SEP_PX_H33_2},
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
    dest = paths.EVIDENCE / "h33_2_s12_e2_holdout_610_619.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print("POOLED BUFFERED HOLDOUT-DTI:", json.dumps(pooled_buf), flush=True)
    print("PER-FOLD BUFFERED:", json.dumps(per_fold_buf), flush=True)
    print("VS B0:", json.dumps(vs_b0), flush=True)
    print("VS D0:", json.dumps(vs_d0), flush=True)
    print("VS H29-S:", json.dumps(vs_h29s), flush=True)
    print("VS H31-S:", json.dumps(vs_h31s), flush=True)
    print("GATE CLAUSES:", json.dumps(gate_clauses), flush=True)
    print(f"E2 PASS={gate_e2_pass} | wrote {dest}", flush=True)
    return 0


def run_e3() -> int:
    t0 = time.time()
    e1 = json.loads((paths.EVIDENCE / "h33_2_s12_e1_canary_and_stitched_uniqueness.json").read_text())
    e2 = json.loads((paths.EVIDENCE / "h33_2_s12_e2_holdout_610_619.json").read_text())

    foot, labels, lid_valid, _ = load_base()
    prob_stitched = np.load(CACHE_H33 / "prob_h332_stitched_oof.npy")
    dots = np.load(CACHE_H33 / "dots_h332_stitched.npy")

    d_cat = distance_transform_edt(~labels)
    dom = foot & (~labels)
    assert int(dots.sum()) == BUDGET_TOTAL
    assert not (dots & ~foot).any()
    assert not (dots & labels).any()
    assert float(d_cat[dots].min()) > B_EXCL

    pts = np.argwhere(dots).astype(np.float64)
    tree_self = cKDTree(pts)
    nn_d, _ = tree_self.query(pts, k=2)
    min_self_dist = float(nn_d[:, 1].min())
    assert min_self_dist >= h33.CELF_MIN_SEP_PX_H33_2 - 1e-6
    nbr_counts = np.array([len(v) - 1 for v in tree_self.query_ball_point(pts, r=3.0)])

    d_to_p = distance_transform_edt(~dots)
    c_blind = float(metric.kernel_from_distance(d_to_p[dom]).mean())
    lid_miss_share = float((~lid_valid[dots]).mean())
    quad_grid = holdout.make_quadrant_folds(foot)
    q_shares = {
        fnm: round(float((quad_grid[dots] == qi).mean()), 4)
        for qi, fnm in enumerate(holdout.FOLD_NAMES)
    }
    dc_dots = d_cat[dots]
    geom_diagnostics = {
        "n_dots": BUDGET_TOTAL,
        "nn_min_px": round(min_self_dist, 4),
        "nn_p10_px": round(float(np.percentile(nn_d[:, 1], 10)), 4),
        "nn_median_px": round(float(np.median(nn_d[:, 1])), 4),
        "nbr_le_3px_mean": round(float(nbr_counts.mean()), 4),
        "frac_ge_3nbr_in_3px": round(float((nbr_counts >= 3).mean()), 5),
        "c_blind_coverage": round(c_blind, 6),
        "c_gain_vs_h31s_006359": round(c_blind - 0.06359, 6),
        "lidar_missing_dot_share": round(lid_miss_share, 4),
        "footprint_lidar_missing_area_share": round(float((~lid_valid[foot]).mean()), 4),
        "d_cat_min_px": round(float(dc_dots.min()), 4),
        "d_cat_median_px": round(float(np.median(dc_dots)), 2),
        "d_cat_le_5_share": round(float((dc_dots <= 5.0 + 1e-9).mean()), 4),
        "d_cat_gt_15_share": round(float((dc_dots > 15.0).mean()), 4),
        "quadrant_shares": q_shares,
    }
    print("GEOMETRY DIAGNOSTICS:", json.dumps(geom_diagnostics), flush=True)

    pred = dots.astype(np.float32)
    cid = submission.scored_content_id(pred, foot, labels)
    slug = "h33-2-agmc-mdm-celf345"
    fn_allfinite = submission.make_filename("gems27", slug, DATE_TAG, cid, "allfinite")
    fn_nan = submission.make_filename("gems27", slug, DATE_TAG, cid, "nan")

    DL_DIR.mkdir(parents=True, exist_ok=True)
    tmp_af = DL_DIR / fn_allfinite
    tmp_nan = DL_DIR / fn_nan
    submission.write_geotiff(pred, paths.TEMPLATE, tmp_af, outside="zero")
    submission.write_geotiff(pred, paths.TEMPLATE, tmp_nan, outside="nan")
    tmp_zip = submission.zip_single(tmp_af)

    chk_af = submission.verify_geotiff(tmp_af, paths.TEMPLATE)
    chk_nan = submission.verify_geotiff(tmp_nan, paths.TEMPLATE)
    assert chk_af["hard_checks_passed"] and chk_nan["hard_checks_passed"]

    peer_uniq_path = paths.EVIDENCE / "h33_2_s12_uniqueness_vs_peers.json"
    subprocess.run(
        [
            sys.executable,
            str(paths.REPO / "scripts" / "check_parallel_uniqueness.py"),
            str(tmp_af),
            "--out",
            str(peer_uniq_path),
        ],
        check=True,
    )
    peer_uniq = json.loads(peer_uniq_path.read_text())

    cand_inside = pred[foot]
    surf_inside = prob_stitched[foot]

    peer_surface_spearman: dict[str, float] = {}
    for p_tif in sorted((paths.DATA / "parallel_registry").glob("*.tif")):
        m_p = dot_overlap_and_spearman(pts, cand_inside, surf_inside, p_tif, foot, labels)
        peer_surface_spearman[p_tif.name] = float(m_p["preplacement_surface_spearman"])

    operative_gems27_files = {k_nm: paths.REPO / p_rel for k_nm, p_rel in OPERATIVE_GEMS27_REFS}
    operative_gems27_uniq = {
        k_nm: dot_overlap_and_spearman(pts, cand_inside, surf_inside, p_tif, foot, labels)
        for k_nm, p_tif in operative_gems27_files.items()
    }

    extended_unscored_repo: dict[str, dict] = {}
    for p_tif in sorted(list(DL_DIR.glob("*-allfinite.tif")) + list((DL_DIR / "research").glob("*-allfinite.tif"))):
        if p_tif.name in (fn_allfinite, fn_nan) or p_tif in operative_gems27_files.values():
            continue
        extended_unscored_repo[p_tif.name] = dot_overlap_and_spearman(
            pts, cand_inside, surf_inside, p_tif, foot, labels
        )

    max_peer_overlap = max(float(e["candidate_dot_fraction_within_3px"]) for e in peer_uniq["entries"])
    max_g27_overlap = max(float(v["candidate_dot_fraction_within_3px"]) for v in operative_gems27_uniq.values())
    max_operative_overlap = max(max_peer_overlap, max_g27_overlap)

    max_peer_dot_rho = max(abs(float(e["spearman_rank_correlation"])) for e in peer_uniq["entries"])
    max_g27_dot_rho = max(abs(float(v["postplacement_dot_spearman"])) for v in operative_gems27_uniq.values())
    max_surf_rho = max(
        max(abs(v) for v in peer_surface_spearman.values()),
        max(abs(float(v["preplacement_surface_spearman"])) for v in operative_gems27_uniq.values()),
    )
    max_operative_spearman = max(max_peer_dot_rho, max_g27_dot_rho, max_surf_rho)

    max_extended_unscored_overlap = (
        max(float(v["candidate_dot_fraction_within_3px"]) for v in extended_unscored_repo.values())
        if extended_unscored_repo
        else 0.0
    )

    uniqueness_pass = (max_operative_overlap <= 0.70) and (max_operative_spearman <= 0.90)
    holdout_pass = bool(e1["gate_e1_pass"]) and bool(e2["gate_e2_pass"])
    validator_pass = bool(chk_af["hard_checks_passed"]) and bool(chk_nan["hard_checks_passed"])
    all_gates_pass = holdout_pass and uniqueness_pass and validator_pass

    target_dir = DL_DIR if all_gates_pass else (DL_DIR / "research")
    target_dir.mkdir(parents=True, exist_ok=True)
    if target_dir != DL_DIR:
        for p_move in (tmp_af, tmp_nan, tmp_zip):
            p_move.replace(target_dir / p_move.name)
        path_af = target_dir / fn_allfinite
        path_nan = target_dir / fn_nan
        path_zip = target_dir / tmp_zip.name
    else:
        path_af, path_nan, path_zip = tmp_af, tmp_nan, tmp_zip

    chk_af_path = target_dir / f"checks-{fn_allfinite[:-4]}.json"
    chk_nan_path = target_dir / f"checks-{fn_nan[:-4]}.json"
    submission.dump_json(chk_af, chk_af_path)
    submission.dump_json(chk_nan, chk_nan_path)

    status_tag = "validated-promote" if all_gates_pass else "hold-slot"
    submission_name = f"27GEMSDOE-H33-2-AGMC-MDM-{DATE_TAG}-{cid}"
    short_note = (
        f"27GEMSDOE H33-2 | asymGraben+magDipMig+orthoRadon+CELF3.45 B2 {BUDGET_TOTAL}px"
        f" | id {cid} | unscored {status_tag}"
    )
    assert 0 < len(short_note) <= 140
    note_path = target_dir / f"note-{fn_allfinite[:-4]}.txt"
    note_path.write_text(short_note + "\n")

    vs_b0 = e2["paired_comparisons_buffered"]["H33_2S_minus_B0"]
    vs_d0 = e2["paired_comparisons_buffered"]["H33_2S_minus_D0"]
    vs_h29s = e2["paired_comparisons_buffered"]["H33_2S_minus_H29S"]
    vs_h31s = e2["paired_comparisons_buffered"]["H33_2S_minus_H31S"]

    run_card = {
        "schema": "parallel-run-card-v2",
        "generated_utc": "2026-10-26",
        "lane": "L-S12B-2026-10-26",
        "hypothesis_id": "H33-2",
        "hypothesis": (
            "Asymmetric Graben-Margin Clay-Cap Dip-Coupling, Multi-Elevation Upward-Continued Magnetic "
            "Dip/Verticality Separation, Deconfounded Morphotectonic M_Full & Zero-Overlap min_sep=3.45 "
            "1-D Manifold CELF Allocation (AGMC-MDM-CELF345)"
        ),
        "mechanism": (
            "Combines cross-strike hanging-wall minus footwall electrical conductivity jumps (+400 m, +800 m) "
            "and footwall-to-hanging-wall density/elevation throws along grad(G_4(depth_to_base_surf)), "
            "+/-1.2 km along-strike canyon-mouth incision collinearity, multi-elevation TMI_up150 vs RTP "
            "down-dip migration (normal faults) and zero-shift vertical strike-slip persistence + seismic-fabric "
            "anisotropy (Walker Lane), and 5 deconfounded slope-normalized cross-contour 1 m LiDAR structural "
            "channels (dropping all 12 raw u8 LiDAR columns); fits end-to-end dual-regime nested spatial cross-fits "
            "(0-deg + 45-deg stitched) with 16-azimuth 2.3 km orthogonal Radon anisotropy; and places 37,654 B2 "
            "dots via 1-D manifold-sharpened min_sep_px=3.45 (nbr_le_3px=0.0000) 300 m CELF cover."
        ),
        "named_non_fault_mimic": (
            "Symmetric interior evaporative playa salt pans (directional HW-FW conductivity jump cancels to 0), "
            "Pleistocene Lake Lahontan contour-parallel shoreline benches and raw bedrock cliffs (raw u8 LiDAR "
            "excluded; isolated via sin^2(theta_scarp - theta_contour) and basin shoreline indicator), surficial "
            "volcanic boulder float (attenuated in TMI_up150), and 2-D diffuse piedmont aprons (cancelled by "
            "16-azimuth orthogonal Radon anisotropy L(theta*) - L(theta* + pi/2))."
        ),
        "verdict": "promote" if all_gates_pass else "negative",
        "ok_to_submit": bool(all_gates_pass),
        "submission_name": submission_name,
        "note_max_140_chars": short_note,
        "note_chars": len(short_note),
        "holdout": {
            "label": "HOLDOUT-DTI",
            "provenance_note": "Catalogue-internal whole-component hide-and-recover; NOT a live organizer score.",
            "evaluator": e2["evaluator_version"],
            "seeds": e2["seeds"],
            "n_cells": e2["n_cells"],
            "n_withheld_positives_total": int(e2["n_withheld_positive_occurrences"]),
            "canary_max_auc": float(e1["max_all_58_direction_invariant_auc"]),
            "canary_h33_2_extra_max_auc": float(e1["max_h33_2_extra_direction_invariant_auc"]),
            "pooled_dti_H33_2S_candidate": e2["pooled_buffered_holdout_dti"]["H33_2-S"],
            "pooled_dti_H33_2S_ci95": e2["pooled_buffered_ci95"]["H33_2-S"],
            "pooled_dti_H33_2A_detector_poisson_ablation": e2["pooled_buffered_holdout_dti"]["H33_2-A"],
            "pooled_dti_H31S_prior_best": e2["pooled_buffered_holdout_dti"]["H31-S"],
            "pooled_dti_H29S_control": e2["pooled_buffered_holdout_dti"]["H29-S"],
            "pooled_dti_D0_control": e2["pooled_buffered_holdout_dti"]["D0"],
            "pooled_dti_B0_control": e2["pooled_buffered_holdout_dti"]["B0"],
            "pooled_dti_U0_null": e2["pooled_buffered_holdout_dti"]["U0"],
            "pooled_unbuffered_diagnostic": e2["pooled_unbuffered_diagnostic_holdout_dti"],
            "per_fold_buffered": e2["per_fold_buffered_holdout_dti"],
            "paired_candidate_minus_B": vs_b0,
            "paired_candidate_minus_D0": vs_d0,
            "paired_candidate_minus_H29S": vs_h29s,
            "paired_candidate_minus_H31S": vs_h31s,
            "frozen_gate_clauses": e2["frozen_gate_clauses"],
            "gate_efficacy_pass": bool(holdout_pass),
        },
        "uniqueness_vs_registry": {
            "pass": bool(uniqueness_pass),
            "operative_scope": (
                "12 pinned focus-site peer rasters + Slot 1 (5512495c6bd1) + H29-S (511898747886) "
                "+ Session-10 H31-1 (cf8e1bbef244)"
            ),
            "max_dot_overlap_within_3px_euclidean": round(max_operative_overlap, 5),
            "max_dot_overlap_vs_12_peers": round(max_peer_overlap, 5),
            "max_dot_overlap_vs_operative_gems27": round(max_g27_overlap, 5),
            "dot_overlap_vs_h31_cf8e1bbef244": operative_gems27_uniq["gems27_h31s10_cf8e1bbef244_unscored"][
                "candidate_dot_fraction_within_3px"
            ],
            "max_surface_spearman": round(max_operative_spearman, 5),
            "max_preplacement_surface_spearman": round(max_surf_rho, 5),
            "max_postplacement_dot_spearman": round(max(max_peer_dot_rho, max_g27_dot_rho), 5),
            "peer_entries": peer_uniq["entries"],
            "peer_preplacement_surface_spearman": peer_surface_spearman,
            "operative_gems27_entries": operative_gems27_uniq,
            "extended_unscored_repo_max_3px_overlap": round(max_extended_unscored_overlap, 5),
            "extended_unscored_repo_entries": extended_unscored_repo,
        },
        "raster": {
            "directory": str(target_dir.relative_to(paths.REPO)),
            "primary_allfinite": path_af.name,
            "companion_nan": path_nan.name,
            "zip": path_zip.name,
            "content_id": cid,
            "sha256": chk_af["sha256"],
            "sha256_nan": chk_nan["sha256"],
            "sha256_zip": sha256_file(path_zip),
            "allfinite_bytes": chk_af["bytes"],
            "nan_bytes": chk_nan["bytes"],
            "zip_bytes": path_zip.stat().st_size,
            "dots": BUDGET_TOTAL,
            "b_exclusion_px": B_EXCL,
            "celf_min_sep_px": h33.CELF_MIN_SEP_PX_H33_2,
            "celf_gamma": h33.CELF_GAMMA_H33_2,
            "geometry_diagnostics": geom_diagnostics,
        },
        "validator": {
            "zeros_hard_pass": bool(chk_af["hard_checks_passed"]),
            "nan_hard_pass": bool(chk_nan["hard_checks_passed"]),
            "technical_validator_pass": bool(validator_pass),
            "inside_footprint_nan_count": 0,
            "whole_array_nan_count_allfinite": 0,
            "inside_footprint_range": [0.0, 1.0],
            "value_set_inside": chk_af["value_set_inside"],
            "crs": f"EPSG:{grid.CRS_EPSG}",
            "shape": list(grid.SHAPE),
            "transform": list(grid.TRANSFORM),
            "zeros_checks": chk_af["checks"],
            "checks_allfinite_json": str(chk_af_path.relative_to(paths.REPO)),
            "checks_nan_json": str(chk_nan_path.relative_to(paths.REPO)),
        },
        "runtime_s": round(time.time() - t0, 1),
    }

    rc_path = paths.EVIDENCE / "h33_2_s12_run_card_2026-10-26.json"
    rc_path.write_text(json.dumps(run_card, indent=2) + "\n")

    cand_man = {
        "lane": "L-S12B-2026-10-26",
        "hypothesis_id": "H33-2",
        "submission_name": submission_name,
        "content_id": cid,
        "directory": str(target_dir.relative_to(paths.REPO)),
        "allfinite": path_af.name,
        "nan": path_nan.name,
        "zip_allfinite": path_zip.name,
        "checks_allfinite": chk_af_path.name,
        "checks_nan": chk_nan_path.name,
        "note_file": note_path.name,
        "note": short_note,
        "sha256_allfinite": chk_af["sha256"],
        "sha256_nan": chk_nan["sha256"],
        "sha256_zip_allfinite": sha256_file(path_zip),
        "emitted_px": BUDGET_TOTAL,
        "b_exclusion_px": B_EXCL,
        "min_sep_px": h33.CELF_MIN_SEP_PX_H33_2,
        "ok_to_submit": bool(all_gates_pass),
        "verdict": run_card["verdict"],
        "technical_validator_pass": bool(validator_pass),
        "uniqueness_pass": bool(uniqueness_pass),
        "holdout_efficacy_pass": bool(holdout_pass),
        "run_card": str(rc_path.relative_to(paths.REPO)),
    }
    (target_dir / "h33_2_s12_candidate_manifest.json").write_text(json.dumps(cand_man, indent=2) + "\n")

    decision = readiness.publication_decision(run_card, paths.REPO)
    print("READINESS PUBLICATION DECISION:", json.dumps(decision), flush=True)
    assert decision["ok_to_publish_as_submission"] == all_gates_pass
    subprocess.run([sys.executable, str(paths.REPO / "scripts" / "audit_submission_readiness.py")], check=True)
    print(f"E3 COMPLETE | verdict={run_card['verdict']} | ok_to_submit={all_gates_pass} | tif={path_af}", flush=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["e1", "e2", "e3", "all"], default="all")
    args = ap.parse_args()
    if args.stage == "e1":
        return run_e1()
    if args.stage == "e2":
        return run_e2()
    if args.stage == "e3":
        return run_e3()
    rc = run_e1()
    if rc != 0:
        return rc
    rc = run_e2()
    if rc != 0:
        return rc
    return run_e3()


if __name__ == "__main__":
    raise SystemExit(main())
