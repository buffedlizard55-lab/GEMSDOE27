#!/usr/bin/env python3
"""Confirmatory spatially-blocked hide-and-recover holdout for Hypothesis H30-1.

Preregistration: knowledge/20_preregistration_H30-1_and_hypotheses.md
Confirmatory seeds: 240..244 (5 fresh seeds x 4 spatial folds = 20 cells).
Evaluates:
  * Gate E1 (Leakage Canary): single-feature ROC-AUC across all 55 features (<= 0.90).
  * Gate E2 (Holdout Efficacy): pooled HOLDOUT-DTI and 10,000-draw paired bootstrap
    95% CI on both the leak-free full-kernel blind evaluator and the legacy
    buffered_scoring_mask evaluator.
  * Gate E4a (Surface Uniqueness): Spearman rank correlation of the H30-1 surface
    against all 12 peer rasters and all 12 in-repo rasters (<= 0.90).
"""

from __future__ import annotations

import gc
import glob
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import grid, holdout, links, metric, oof_detector, paths  # noqa: E402
from gems27.candidates import RULE, SPACING, dedupe_mutual, evidence_score  # noqa: E402
from gems27.graph import build_graph  # noqa: E402
from gems27.subsurface_features import (  # noqa: E402
    SUBSURFACE_BANDS,
    TRANSFORM_NAMES,
    build_transforms,
    priority_poisson_disk,
)
from gems27.updip_relay_features import (  # noqa: E402
    UPDIP_RELAY_FEATURE_NAMES,
    _rank01,
    _rank01_grid,
    _unflatten,
    build_updip_relay_features,
)

SEEDS = (240, 241, 242, 243, 244)
B_CONTROL = 38_000
B_CORE = 23_200
B_TOT = 35_200
SCARP_TOP_K = 120_000
MIN_DIST_PX = 2.8
B2_COLLAR_PX = 2.0
EVALUATOR_VERSION = "gems27.holdout+metric@2026-10-25.v3-leakfree-and-buffered"


def top_k_mask(prob: np.ndarray, cand: np.ndarray, k: int) -> np.ndarray:
    ys, xs = np.nonzero(cand)
    if len(ys) <= k:
        return cand.copy()
    idx = np.argpartition(-prob[ys, xs], k)[:k]
    out = np.zeros_like(cand, dtype=bool)
    out[ys[idx], xs[idx]] = True
    return out


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def ensure_cached_arrays(foot: np.ndarray, labels: np.ndarray, fold: np.ndarray, meta: dict) -> None:
    prep = paths.DATA / "prepared"
    X_foot = np.load(paths.PREPARED_FEATURES, mmap_mode="r")

    sub_cache = prep / "subsurface_transforms.npy"
    if not sub_cache.exists():
        name_to_col = {n: i for i, n in enumerate(meta["names"])}
        grids = {}
        for b in SUBSURFACE_BANDS:
            arr = np.full(foot.shape, np.nan, dtype=np.float32)
            arr[foot] = X_foot[:, name_to_col[b]]
            grids[b] = arr
        np.save(sub_cache, build_transforms(grids, foot))
        del grids
        gc.collect()

    h30_cache = prep / "h30_1_updip_relay.npy"
    if not h30_cache.exists():
        F_h30, _ = build_updip_relay_features(X_foot, foot)
        np.save(h30_cache, F_h30)
        del F_h30
        gc.collect()

    comb_cache = prep / "h30_1_combined_23.npy"
    if not comb_cache.exists():
        F_sub = np.load(sub_cache, mmap_mode="r")
        F_h30 = np.load(h30_cache, mmap_mode="r")
        mm = np.lib.format.open_memmap(
            comb_cache, mode="w+", dtype=np.float32, shape=(F_sub.shape[0], 23)
        )
        mm[:, :15] = F_sub
        mm[:, 15:] = F_h30
        mm.flush()
        del mm

    if not (prep / "oof_prob_B.npy").exists():
        np.save(
            prep / "oof_prob_B.npy",
            oof_detector.fit_predict_oof_probabilities(foot, labels, fold, seed=2026, chunk=200_000),
        )
        gc.collect()

    if not (prep / "oof_prob_D.npy").exists():
        np.save(
            prep / "oof_prob_D.npy",
            oof_detector.fit_predict_oof_probabilities(
                foot,
                labels,
                fold,
                extra_features=np.load(sub_cache, mmap_mode="r"),
                seed=2026,
                chunk=200_000,
            ),
        )
        gc.collect()

    if not (prep / "oof_prob_H30_hybrid.npy").exists():
        np.save(
            prep / "oof_prob_H30_hybrid.npy",
            oof_detector.fit_predict_oof_probabilities(
                foot,
                labels,
                fold,
                extra_features=np.load(comb_cache, mmap_mode="r"),
                seed=2026,
                chunk=200_000,
            ),
        )
        gc.collect()

    if not (prep / "oof_prob_H30_sub.npy").exists():
        sub_idx = np.array([meta["names"].index(b) for b in SUBSURFACE_BANDS], dtype=int)
        np.save(
            prep / "oof_prob_H30_sub.npy",
            oof_detector.fit_predict_oof_probabilities(
                foot,
                labels,
                fold,
                extra_features=np.load(comb_cache, mmap_mode="r"),
                seed=2026,
                columns=sub_idx,
                chunk=200_000,
            ),
        )
        gc.collect()


def paired_bootstrap_ci(
    cells_cand: list[dict],
    cells_ref: list[dict],
    n_boot: int = 10_000,
    seed: int = 20261025,
) -> dict:
    n = len(cells_cand)
    tp_c = np.array([c["TPw"] for c in cells_cand], dtype=np.float64)
    fp_c = np.array([c["FPw"] for c in cells_cand], dtype=np.float64)
    fn_c = np.array([c["FNw"] for c in cells_cand], dtype=np.float64)

    tp_r = np.array([c["TPw"] for c in cells_ref], dtype=np.float64)
    fp_r = np.array([c["FPw"] for c in cells_ref], dtype=np.float64)
    fn_r = np.array([c["FNw"] for c in cells_ref], dtype=np.float64)

    def _pooled(tp: np.ndarray, fp: np.ndarray, fn: np.ndarray) -> float:
        t = float(tp.sum())
        f = float(fp.sum())
        m = float(fn.sum())
        return t / (t + 0.2 * f + 0.8 * m + 1e-7)

    obs_c = _pooled(tp_c, fp_c, fn_c)
    obs_r = _pooled(tp_r, fp_r, fn_r)
    obs_diff = obs_c - obs_r

    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    tc = tp_c[idx].sum(axis=1)
    fc = fp_c[idx].sum(axis=1)
    mc = fn_c[idx].sum(axis=1)
    dti_c = tc / (tc + 0.2 * fc + 0.8 * mc + 1e-7)

    tr = tp_r[idx].sum(axis=1)
    fr = fp_r[idx].sum(axis=1)
    mr = fn_r[idx].sum(axis=1)
    dti_r = tr / (tr + 0.2 * fr + 0.8 * mr + 1e-7)

    diffs = dti_c - dti_r
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    cell_deltas = [float(c["dti"] - r["dti"]) for c, r in zip(cells_cand, cells_ref)]
    return {
        "pooled_candidate": float(obs_c),
        "pooled_reference": float(obs_r),
        "pooled_delta": float(obs_diff),
        "ci95": [float(lo), float(hi)],
        "mean_cell_delta": float(np.mean(cell_deltas)),
        "cells_improved": int(sum(d > 0 for d in cell_deltas)),
        "total_cells": n,
    }


def main() -> int:
    t0 = time.time()
    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    fold = holdout.make_quadrant_folds(foot)
    meta = json.loads(paths.PREPARED_META.read_text())
    prep = paths.DATA / "prepared"

    ensure_cached_arrays(foot, labels, fold, meta)

    X_foot = np.load(paths.PREPARED_FEATURES, mmap_mode="r")
    F_sub = np.load(prep / "subsurface_transforms.npy", mmap_mode="r")
    F_h30 = np.load(prep / "h30_1_updip_relay.npy", mmap_mode="r")

    # 1. Gate E1: Single-feature leakage canary across all 55 features on seed 240 splits
    sp0 = holdout.make_split(labels, fold, 0, seed=SEEDS[0])
    valid_c = holdout.buffered_scoring_mask(sp0, foot) & ~sp0.known
    v_1d = valid_c[foot]
    y_1d = (sp0.hidden & valid_c)[foot][v_1d].astype(np.int8)
    rng_c = np.random.default_rng(20261025)
    sub_idx = np.sort(rng_c.choice(int(v_1d.sum()), size=min(250_000, int(v_1d.sum())), replace=False))
    y_sub = y_1d[sub_idx]

    canary_aucs: dict[str, float] = {}
    for j, nm in enumerate(meta["names"]):
        col = np.asarray(X_foot[:, j], dtype=np.float32)[v_1d][sub_idx]
        fin = np.isfinite(col)
        auc = float(roc_auc_score(y_sub[fin], col[fin]))
        canary_aucs[nm] = max(auc, 1.0 - auc)
    for j, nm in enumerate(TRANSFORM_NAMES):
        col = np.asarray(F_sub[:, j], dtype=np.float32)[v_1d][sub_idx]
        assert np.isfinite(col).all(), f"Non-finite values in subsurface transform {nm}"
        auc = float(roc_auc_score(y_sub, col))
        canary_aucs[nm] = max(auc, 1.0 - auc)
    for j, nm in enumerate(UPDIP_RELAY_FEATURE_NAMES):
        col = np.asarray(F_h30[:, j], dtype=np.float32)[v_1d][sub_idx]
        assert np.isfinite(col).all(), f"Non-finite values in H30-1 transform {nm}"
        auc = float(roc_auc_score(y_sub, col))
        canary_aucs[nm] = max(auc, 1.0 - auc)

    max_canary_name, max_canary_auc = max(canary_aucs.items(), key=lambda kv: kv[1])
    canary_pass = bool(0.5 <= max_canary_auc <= 0.90)
    print(f"Gate E1 (Canary): max AUC = {max_canary_auc:.4f} ({max_canary_name}), pass={canary_pass}", flush=True)

    # 2. Load OOF probabilities and build Sub-Alluvial Up-Dip / Hydrothermal surface
    scarp_1d = 0.7 * np.asarray(X_foot[:, 20], dtype=np.float32) + 0.3 * np.asarray(
        X_foot[:, 17], dtype=np.float32
    )
    scarp_rank = _rank01_grid(_unflatten(scarp_1d, foot), foot)
    cover_factor = (1.0 - 0.75 * scarp_rank).astype(np.float32)
    del scarp_1d, scarp_rank

    prob_B = np.load(prep / "oof_prob_B.npy")
    prob_D = np.load(prep / "oof_prob_D.npy")
    prob_H = np.load(prep / "oof_prob_H30_hybrid.npy")
    prob_S = np.load(prep / "oof_prob_H30_sub.npy")
    score_U = (prob_S * cover_factor).astype(np.float32)
    score_H3 = (0.70 * prob_H + 0.30 * prob_S).astype(np.float32)

    # 3. Gate E4a: Surface rank-correlation check BEFORE placement
    surf_1d = 0.65 * _rank01(prob_H[foot]) + 0.35 * _rank01(score_U[foot])
    s_idx = np.sort(rng_c.choice(surf_1d.size, size=250_000, replace=False))
    s_sample = surf_1d[s_idx]
    surface_corrs: dict[str, float] = {
        "oof_prob_B_internal": float(abs(spearmanr(s_sample, prob_B[foot][s_idx]).statistic)),
        "oof_prob_D_internal": float(abs(spearmanr(s_sample, prob_D[foot][s_idx]).statistic)),
    }
    reg_files = (
        sorted(glob.glob(str(paths.DATA / "parallel_registry" / "*.tif")))
        + sorted(glob.glob(str(paths.DOCS / "downloads" / "*-allfinite.tif")))
        + sorted(glob.glob(str(paths.DOCS / "downloads" / "research" / "*-allfinite.tif")))
    )
    max_reg_spearman = 0.0
    max_reg_spearman_name = ""
    for p in reg_files:
        with rasterio.open(p) as src:
            a = src.read(1)
        v = np.where(np.isfinite(a), a, 0.0)[foot][s_idx]
        rho = float(abs(spearmanr(s_sample, v).statistic))
        nm = os.path.basename(p)
        surface_corrs[nm] = rho
        if rho > max_reg_spearman:
            max_reg_spearman, max_reg_spearman_name = rho, nm
    del surf_1d, s_sample
    gc.collect()
    print(
        f"Gate E4a (Surface Spearman vs 24 rasters): max = {max_reg_spearman:.4f} ({max_reg_spearman_name})",
        flush=True,
    )

    # Precompute footprint-level ridge NMS skeletons (100% blind to split.hidden)
    rB_all = oof_detector.ridge_nms(prob_B, foot, sigma=1.0)
    rD_all = oof_detector.ridge_nms(prob_D, foot, sigma=1.0)
    rH_all = oof_detector.ridge_nms(prob_H, foot, sigma=1.0)
    rS_all = oof_detector.ridge_nms(score_H3, foot, sigma=1.2)
    rHS_union = rH_all | rS_all

    arms = ("B", "D", "H30_raw_tv2", "H30_1")
    cells_full: dict[str, list[dict]] = {k: [] for k in arms}
    cells_buf: dict[str, list[dict]] = {k: [] for k in arms}
    n_foot = float(foot.sum())
    n_withheld_full_total = 0
    n_withheld_buf_total = 0

    for seed in SEEDS:
        t_seed = time.time()
        for f in range(4):
            sp = holdout.make_split(labels, fold, f, seed=seed)
            fm = foot & sp.fold_mask
            frac = float(fm.sum()) / n_foot
            b_ctrl = max(1, int(round(B_CONTROL * frac)))
            b_core = max(1, int(round(B_CORE * frac)))
            b_tot = max(1, int(round(B_TOT * frac)))
            k_scarp = max(1, int(round(SCARP_TOP_K * frac)))

            # Leak-free full-kernel blind evaluation: visible_known excludes 6-px buffer around hidden
            vis_known = sp.known & (distance_transform_edt(~sp.hidden) > 6.0)
            d_vis = distance_transform_edt(~vis_known)
            emit_blind = fm & (d_vis > B2_COLLAR_PX)
            r1_blind = fm & (d_vis > 1.0)

            gr = build_graph(vis_known, with_edges=False)
            lf = links.generate_links(gr, region=sp.fold_mask, **RULE)
            sel = dedupe_mutual(lf[evidence_score(lf) >= 3])
            topo_blind = links.rasterize_links(sel, labels.shape, SPACING) & emit_blind

            dB_f = priority_poisson_disk(prob_B, rB_all & emit_blind, min_dist=MIN_DIST_PX, budget=b_ctrl)
            dD_f = priority_poisson_disk(prob_D, rD_all & emit_blind, min_dist=MIN_DIST_PX, budget=b_ctrl)
            dH_f = priority_poisson_disk(prob_H, rH_all & emit_blind, min_dist=MIN_DIST_PX, budget=b_ctrl)
            d_dH_f = distance_transform_edt(~dH_f)
            dH_tv2_f = dH_f | (topo_blind & (d_dH_f >= MIN_DIST_PX))

            dH_core_f = priority_poisson_disk(prob_H, rH_all & emit_blind, min_dist=MIN_DIST_PX, budget=b_core)
            d_core_f = distance_transform_edt(~dH_core_f)
            hab12_f = dH_core_f | (topo_blind & (d_core_f >= MIN_DIST_PX))
            scarp_f = (
                top_k_mask(prob_B, rB_all & r1_blind, k_scarp)
                | top_k_mask(prob_D, rD_all & r1_blind, k_scarp)
            )
            d_scarp_f = distance_transform_edt(~(scarp_f | hab12_f))
            b_rem_f = max(1, b_tot - int(hab12_f.sum()))
            dU_f = priority_poisson_disk(
                score_H3, rHS_union & emit_blind & (d_scarp_f > 3.2), min_dist=MIN_DIST_PX, budget=b_rem_f
            )
            dH30_f = hab12_f | dU_f

            buf_cat = labels & fm & ~sp.hidden & ~vis_known
            valid_full = fm & (distance_transform_edt(~buf_cat) > 3.0 if buf_cat.any() else fm)
            n_pos_full = int((sp.hidden & valid_full & ~vis_known).sum())
            n_withheld_full_total += n_pos_full

            for k, pred in [
                ("B", dB_f),
                ("D", dD_f),
                ("H30_raw_tv2", dH_tv2_f),
                ("H30_1", dH30_f),
            ]:
                m = metric.dti_binary(pred, sp.hidden, valid_full, known=vis_known)
                m["seed"] = seed
                m["fold"] = sp.name
                m["n_withheld"] = n_pos_full
                cells_full[k].append(m)

            # Legacy buffered_scoring_mask evaluation (for direct comparability with H29-1 / DCONFIRM)
            valid_buf = holdout.buffered_scoring_mask(sp, foot)
            d_known_std = distance_transform_edt(~sp.known)
            emit_buf = (valid_buf | sp.hidden) & (d_known_std > B2_COLLAR_PX)
            r1_buf = (valid_buf | sp.hidden) & (d_known_std > 1.0)
            topo_buf = topo_blind & emit_buf

            dB_b = priority_poisson_disk(prob_B, rB_all & emit_buf, min_dist=MIN_DIST_PX, budget=b_ctrl)
            dD_b = priority_poisson_disk(prob_D, rD_all & emit_buf, min_dist=MIN_DIST_PX, budget=b_ctrl)
            dH_b = priority_poisson_disk(prob_H, rH_all & emit_buf, min_dist=MIN_DIST_PX, budget=b_ctrl)
            d_dH_b = distance_transform_edt(~dH_b)
            dH_tv2_b = dH_b | (topo_buf & (d_dH_b >= MIN_DIST_PX))

            dH_core_b = priority_poisson_disk(prob_H, rH_all & emit_buf, min_dist=MIN_DIST_PX, budget=b_core)
            d_core_b = distance_transform_edt(~dH_core_b)
            hab12_b = dH_core_b | (topo_buf & (d_core_b >= MIN_DIST_PX))
            scarp_b = (
                top_k_mask(prob_B, rB_all & r1_buf, k_scarp)
                | top_k_mask(prob_D, rD_all & r1_buf, k_scarp)
            )
            d_scarp_b = distance_transform_edt(~(scarp_b | hab12_b))
            b_rem_b = max(1, b_tot - int(hab12_b.sum()))
            dU_b = priority_poisson_disk(
                score_H3, rHS_union & emit_buf & (d_scarp_b > 3.2), min_dist=MIN_DIST_PX, budget=b_rem_b
            )
            dH30_b = hab12_b | dU_b

            n_pos_buf = int((sp.hidden & valid_buf & ~sp.known).sum())
            n_withheld_buf_total += n_pos_buf
            for k, pred in [
                ("B", dB_b),
                ("D", dD_b),
                ("H30_raw_tv2", dH_tv2_b),
                ("H30_1", dH30_b),
            ]:
                m = metric.dti_binary(pred, sp.hidden, valid_buf, known=sp.known)
                m["seed"] = seed
                m["fold"] = sp.name
                m["n_withheld"] = n_pos_buf
                cells_buf[k].append(m)

        print(f"Seed {seed} complete in {time.time() - t_seed:.1f}s", flush=True)

    full_H30_vs_B = paired_bootstrap_ci(cells_full["H30_1"], cells_full["B"])
    full_raw_vs_B = paired_bootstrap_ci(cells_full["H30_raw_tv2"], cells_full["B"])
    full_raw_vs_D = paired_bootstrap_ci(cells_full["H30_raw_tv2"], cells_full["D"])
    full_D_vs_B = paired_bootstrap_ci(cells_full["D"], cells_full["B"])

    buf_H30_vs_B = paired_bootstrap_ci(cells_buf["H30_1"], cells_buf["B"])
    buf_H30_vs_D = paired_bootstrap_ci(cells_buf["H30_1"], cells_buf["D"])
    buf_raw_vs_B = paired_bootstrap_ci(cells_buf["H30_raw_tv2"], cells_buf["B"])
    buf_D_vs_B = paired_bootstrap_ci(cells_buf["D"], cells_buf["B"])

    gate_efficacy_pass = bool(
        full_H30_vs_B["ci95"][0] > 0.0
        and buf_H30_vs_B["ci95"][0] > 0.0
        and buf_H30_vs_D["ci95"][0] > 0.0
    )

    out = {
        "label": "HOLDOUT-DTI",
        "hypothesis": "H30-1 Up-Dip Basement-Step Projection + Cross-Field Strike Bridge + Listric Rollover + Quality-Filtered Hydrothermal Upflow + Visible-Fault T-v2 Structural Relay Network",
        "preregistration": "knowledge/20_preregistration_H30-1_and_hypotheses.md",
        "evaluator": EVALUATOR_VERSION,
        "seeds": list(SEEDS),
        "n_folds": 4,
        "n_cells": len(SEEDS) * 4,
        "n_withheld_positives_total": n_withheld_full_total,
        "n_withheld_positives_buffered_total": n_withheld_buf_total,
        "budgets": {
            "control_B": B_CONTROL,
            "H30_1_core": B_CORE,
            "H30_1_total": B_TOT,
            "min_dist_px": MIN_DIST_PX,
            "b2_collar_px": B2_COLLAR_PX,
        },
        "canary": {
            "pass": canary_pass,
            "max_auc": float(max_canary_auc),
            "max_feature": max_canary_name,
            "h30_1_feature_aucs": {k: float(canary_aucs[k]) for k in UPDIP_RELAY_FEATURE_NAMES},
        },
        "canary_max_auc": float(max_canary_auc),
        "surface_uniqueness": {
            "pass": bool(max_reg_spearman <= 0.90),
            "max_surface_spearman": float(max_reg_spearman),
            "max_surface_spearman_vs": max_reg_spearman_name,
            "correlations": surface_corrs,
        },
        "full_kernel_blind_evaluator": {
            "description": "Primary leak-free protocol-exact evaluator: emit() sees only fold_mask and visible_known (6-px buffered from hidden); full 300 m triangular kernel active on fold_mask & ~visible_known.",
            "pooled_dti": {
                "B": full_H30_vs_B["pooled_reference"],
                "D": full_D_vs_B["pooled_candidate"],
                "H30_raw_tv2": full_raw_vs_B["pooled_candidate"],
                "H30_1": full_H30_vs_B["pooled_candidate"],
            },
            "paired_H30_1_minus_B": full_H30_vs_B,
            "paired_H30_raw_tv2_minus_B": full_raw_vs_B,
            "paired_H30_raw_tv2_minus_D": full_raw_vs_D,
            "paired_D_minus_B": full_D_vs_B,
            "cells": cells_full,
        },
        "buffered_scoring_mask_evaluator": {
            "description": "Template holdout.buffered_scoring_mask evaluator for backward comparability with H29-1 and L-DCONFIRM.",
            "pooled_dti": {
                "B": buf_H30_vs_B["pooled_reference"],
                "D": buf_D_vs_B["pooled_candidate"],
                "H30_raw_tv2": buf_raw_vs_B["pooled_candidate"],
                "H30_1": buf_H30_vs_B["pooled_candidate"],
            },
            "paired_H30_1_minus_B": buf_H30_vs_B,
            "paired_H30_1_minus_D": buf_H30_vs_D,
            "paired_H30_raw_tv2_minus_B": buf_raw_vs_B,
            "paired_D_minus_B": buf_D_vs_B,
            "cells": cells_buf,
        },
        "paired_D_minus_B": full_H30_vs_B,
        "gate_efficacy_pass": gate_efficacy_pass,
        "elapsed_seconds": float(time.time() - t0),
    }

    out_path = paths.EVIDENCE / "h30_1_holdout.json"
    out_path.write_text(json.dumps(out, indent=2) + "\n")
    print(f"Wrote {out_path} in {out['elapsed_seconds']:.1f}s")
    print(
        f"Full-kernel blind pooled HOLDOUT-DTI: B={full_H30_vs_B['pooled_reference']:.5f}, "
        f"D={full_D_vs_B['pooled_candidate']:.5f}, "
        f"H30_raw_tv2={full_raw_vs_B['pooled_candidate']:.5f} (vs B CI95={full_raw_vs_B['ci95']}), "
        f"H30_1={full_H30_vs_B['pooled_candidate']:.5f} (vs B delta={full_H30_vs_B['pooled_delta']:+.5f}, CI95={full_H30_vs_B['ci95']})"
    )
    print(
        f"Buffered-mask pooled HOLDOUT-DTI: B={buf_H30_vs_B['pooled_reference']:.5f}, "
        f"D={buf_D_vs_B['pooled_candidate']:.5f}, "
        f"H30_1={buf_H30_vs_B['pooled_candidate']:.5f} (vs B delta={buf_H30_vs_B['pooled_delta']:+.5f}, CI95={buf_H30_vs_B['ci95']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
