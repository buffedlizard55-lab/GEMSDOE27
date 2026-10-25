#!/usr/bin/env python3
"""H29-1 confirmatory holdout (preregistration: knowledge/15_preregistration_H29-1.md).

E1 leakage canary (15 subsurface transforms alone, seed-210 splits) + E2 buffered
hide-and-recover on FRESH seeds 210-214 (200-204 consumed by Lane L-2026-10-25).
Arms: B = full-32 control, D = full-32 + 15 subsurface transforms (lane surface).
Identical emission both arms (ridge NMS -> B2 -> priority Poisson-disk 2.8 px,
matched per-fold budgets summing to 38,000). All scores are HOLDOUT-DTI
(evaluator gems27.metric v1: alpha 0.2, beta 0.8, 300 m triangular kernel);
pooled = TPw/FPw/FNw summed over cells before the ratio. Not a live score.
Reuses shared tools unchanged (gems27.holdout / metric / oof_detector /
subsurface_features); OOF probabilities cached under data_cache/lane/.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import grid, holdout, metric, oof_detector, paths  # noqa: E402
from gems27 import subsurface_features as sub

LANE_DIR = paths.DATA / "lane"
SEEDS = [210, 211, 212, 213, 214]
BUDGET_TOTAL = 38_000
MIN_DIST = 2.8
B_EXCL = 2.0


def build_or_load_transforms(foot, names):
    LANE_DIR.mkdir(parents=True, exist_ok=True)
    f = LANE_DIR / "subsurface_transforms.npy"
    if f.exists():
        return np.load(f)
    X = np.load(paths.PREPARED_FEATURES, mmap_mode="r")
    grids = {}
    for b in sub.SUBSURFACE_BANDS:
        a = np.full(grid.SHAPE, np.nan, dtype=np.float32)
        a[foot] = np.asarray(X[:, names.index(b)], dtype=np.float32)
        grids[b] = a
    T = sub.build_transforms(grids, foot)
    np.save(f, T)
    return T


def oof_for_arm(arm, foot, labels, fold, T):
    f = LANE_DIR / f"oof_prob_arm{arm}.npy"
    if f.exists():
        return np.load(f)
    if arm == "B":
        prob = oof_detector.fit_predict_oof_probabilities(foot, labels, fold)
    elif arm == "D":
        prob = oof_detector.fit_predict_oof_probabilities(foot, labels, fold, extra=T)
    else:
        raise ValueError(arm)
    np.save(f, prob)
    return prob


def emit(prob, valid_scoring, known, hidden, budget):
    d_vis = distance_transform_edt(~known)
    ridge = oof_detector.ridge_nms(prob, valid_scoring | hidden)
    cand = ridge & (valid_scoring | hidden) & ~known & (d_vis > B_EXCL)
    return sub.priority_poisson_disk(prob, cand, MIN_DIST, budget)


def score_cell(dots, split, valid):
    rs, cs = holdout.crop(dots, split.fold_mask)
    r0, r1 = max(rs.start - 8, 0), min(rs.stop + 8, grid.SHAPE[0])
    c0, c1 = max(cs.start - 8, 0), min(cs.stop + 8, grid.SHAPE[1])
    sl = (slice(r0, r1), slice(c0, c1))
    return metric.dti_binary(dots[sl].astype(float), split.hidden[sl],
                             valid=valid[sl] | split.hidden[sl], known=split.known[sl])


def pooled_dti(cells):
    tp = sum(c["TPw"] for c in cells)
    fp = sum(c["FPw"] for c in cells)
    fn = sum(c["FNw"] for c in cells)
    return tp / (tp + metric.ALPHA * fp + metric.BETA * fn + metric.EPS)


def main() -> int:
    t0 = time.time()
    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    names = json.loads(paths.PREPARED_META.read_text())["names"]
    fold = holdout.make_quadrant_folds(foot)
    print("building subsurface transforms...", flush=True)
    T = build_or_load_transforms(foot, names)
    print(f"transforms {T.shape} in {time.time() - t0:.0f}s", flush=True)

    # ---------- E1 canary (seed 210) ----------
    rng = np.random.default_rng(7)
    hidden_any = np.zeros(grid.SHAPE, bool)
    valid_any = np.zeros(grid.SHAPE, bool)
    for f in range(4):
        sp = holdout.make_split(labels, fold, f, seed=210)
        hidden_any |= sp.hidden
        valid_any |= holdout.buffered_scoring_mask(sp, foot)
    y = hidden_any[foot]
    idx_scope = np.flatnonzero((valid_any | hidden_any)[foot])
    pos = idx_scope[y[idx_scope]]
    neg = idx_scope[~y[idx_scope]]
    neg_s = rng.choice(neg, size=min(200_000, len(neg)), replace=False)
    canary = {}
    for j, nm in enumerate(sub.TRANSFORM_NAMES):
        col = T[:, j]
        canary[nm] = float(roc_auc_score(
            np.r_[np.ones(len(pos)), np.zeros(len(neg_s))], np.r_[col[pos], col[neg_s]]))
        print(f"canary {nm}: AUC {canary[nm]:.4f}", flush=True)
    leak = {k: v for k, v in canary.items() if v > 0.90}
    print("CANARY leak flags (>0.90):", leak or "none", flush=True)

    # ---------- OOF surfaces + surface uniqueness pre-check ----------
    probs = {}
    for arm in ["B", "D"]:
        print(f"OOF arm {arm}...", flush=True)
        probs[arm] = oof_for_arm(arm, foot, labels, fold, T)
    sample = rng.choice(np.flatnonzero(foot.ravel()), size=300_000, replace=False)
    surf_corr = {}
    import rasterio
    reg_files = sorted((paths.DATA / "parallel_registry").glob("*.tif")) or \
        sorted((paths.DATA / "registry").glob("*.tif"))
    for rp in reg_files:
        with rasterio.open(rp) as s:
            a = s.read(1)
        dens = gaussian_filter((np.isfinite(a) & (a > 0)).astype(np.float32), 3.0)
        surf_corr[rp.name] = {arm: float(spearmanr(probs[arm].ravel()[sample],
                                                   dens.ravel()[sample]).statistic)
                              for arm in ["B", "D"]}
        print("surface Spearman", rp.name, surf_corr[rp.name], flush=True)

    # ---------- E2 fresh-seed holdout ----------
    fold_share = np.array([(fold == f).sum() for f in range(4)], float)
    fold_budget = np.round(BUDGET_TOTAL * fold_share / fold_share.sum()).astype(int)
    cells = {"B": [], "D": []}
    n_withheld = 0
    for seed in SEEDS:
        for f in range(4):
            sp = holdout.make_split(labels, fold, f, seed=seed)
            valid = holdout.buffered_scoring_mask(sp, foot)
            n_withheld += int(sp.hidden.sum())
            for arm in ["B", "D"]:
                dots = emit(probs[arm], valid, sp.known, sp.hidden, int(fold_budget[f]))
                cells[arm].append(score_cell(dots, sp, valid))
            print(f"seed {seed} fold {f}: B={cells['B'][-1]['dti']:.4f} "
                  f"D={cells['D'][-1]['dti']:.4f}", flush=True)

    pooled = {a: pooled_dti(c) for a, c in cells.items()}
    d = np.array([a["dti"] - b["dti"] for a, b in zip(cells["D"], cells["B"])])
    bs = np.random.default_rng(11)
    means = [bs.choice(d, size=len(d), replace=True).mean() for _ in range(2000)]
    paired = {"mean_delta": float(d.mean()),
              "ci95": [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))],
              "cells_positive": int((d > 0).sum()), "n_cells": int(len(d))}
    gate_efficacy = bool(pooled["D"] > pooled["B"] and paired["mean_delta"] > 0
                         and paired["cells_positive"] >= 12)
    out = {
        "experiment": "H29-1 D-refill confirmatory holdout (E1+E2)",
        "preregistration": "knowledge/15_preregistration_H29-1.md (frozen pre-run)",
        "evaluator": "gems27.metric v1 (alpha=0.2, beta=0.8, R=3px triangular)",
        "label": "HOLDOUT-DTI (catalogue-internal hide-and-recover; NOT a live score)",
        "seeds": SEEDS, "folds": holdout.FOLD_NAMES,
        "n_withheld_positives_total": int(n_withheld),
        "budget_per_fold": fold_budget.tolist(), "min_dist_px": MIN_DIST,
        "b_exclusion_px": B_EXCL,
        "canary_auc": canary, "canary_leak_flags": leak,
        "canary_max_auc": max(canary.values()) if canary else None,
        "surface_spearman_vs_registry": surf_corr,
        "pooled_holdout_dti": pooled,
        "paired_D_minus_B": paired,
        "gate_efficacy_pass": gate_efficacy,
        "per_cell": {a: [{k: c[k] for k in ("dti", "TPw", "FPw", "FNw", "n_truth", "n_emitted")}
                         for c in cs] for a, cs in cells.items()},
        "runtime_s": round(time.time() - t0, 1),
    }
    dest = paths.EVIDENCE / "h29_1_holdout.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print("POOLED HOLDOUT-DTI:", pooled)
    print("paired D-B:", paired, "| gate_efficacy:", gate_efficacy)
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
