#!/usr/bin/env python3
"""Lane L-2026-10-25 experiments E1 (leakage canary) + E2 (buffered hide-and-recover holdout).

Preregistration: knowledge/13_lane_and_hypotheses_2026-10-25.md §3 (frozen before this ran).
Arms: A = subsurface-only (lane), B = full-32 incumbent (control), D = full-32 + lane transforms
(control, never shipped), R = random-order placement on A's ridges (null). Matched per-fold budget.
All scores are HOLDOUT-DTI (evaluator gems27.metric v1: alpha 0.2, beta 0.8, 300 m triangular
kernel); pooled = TPw/FPw/FNw summed over cells before the ratio. Nothing here is a live score.
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
SEEDS = [200, 201, 202, 203, 204]
BUDGET_TOTAL = 38_000
MIN_DIST = 2.8
B_EXCL = 2.0  # B2: no dot within 2 px (200 m) of a visible fault


def load_base():
    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    meta = json.loads(paths.PREPARED_META.read_text())
    names = meta["names"]
    return foot, labels, names


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


def oof_for_arm(arm, foot, labels, fold, names, T):
    f = LANE_DIR / f"oof_prob_arm{arm}.npy"
    if f.exists():
        return np.load(f)
    sub_idx = np.array([names.index(b) for b in sub.SUBSURFACE_BANDS])
    if arm == "A":
        prob = oof_detector.fit_predict_oof_probabilities(foot, labels, fold, columns=sub_idx, extra=T)
    elif arm == "B":
        prob = oof_detector.fit_predict_oof_probabilities(foot, labels, fold)
    elif arm == "D":
        prob = oof_detector.fit_predict_oof_probabilities(foot, labels, fold, extra=T)
    else:
        raise ValueError(arm)
    np.save(f, prob)
    return prob


def emit(prob, fold_domain, known, budget, rng=None):
    """Blind candidate emission: sees ONLY fold_domain (foot & fold_mask) and known faults."""
    d_vis = distance_transform_edt(~known)
    ridge = oof_detector.ridge_nms(prob, fold_domain)
    cand = ridge & fold_domain & ~known & (d_vis > B_EXCL)
    return sub.priority_poisson_disk(prob, cand, MIN_DIST, budget, rng=rng)


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
    foot, labels, names = load_base()
    fold = holdout.make_quadrant_folds(foot)
    print("building subsurface transforms...", flush=True)
    T = build_or_load_transforms(foot, names)
    print(f"transforms {T.shape} in {time.time()-t0:.0f}s", flush=True)

    # ---------- E1: leakage canary (seed 200 splits; each transform alone) ----------
    rng = np.random.default_rng(7)
    hidden_any = np.zeros(grid.SHAPE, bool)
    valid_any = np.zeros(grid.SHAPE, bool)
    for f in range(4):
        sp = holdout.make_split(labels, fold, f, seed=200)
        hidden_any |= sp.hidden
        valid_any |= holdout.buffered_scoring_mask(sp, foot)
    y = hidden_any[foot]
    scope = (valid_any | hidden_any)[foot]
    idx_scope = np.flatnonzero(scope)
    pos = idx_scope[y[idx_scope]]
    neg = idx_scope[~y[idx_scope]]
    neg_s = rng.choice(neg, size=min(200_000, len(neg)), replace=False)
    canary = {}
    for j, nm in enumerate(sub.TRANSFORM_NAMES):
        col = T[:, j]
        auc = roc_auc_score(np.r_[np.ones(len(pos)), np.zeros(len(neg_s))],
                            np.r_[col[pos], col[neg_s]])
        canary[nm] = float(auc)
        print(f"canary {nm}: AUC {auc:.4f}", flush=True)
    X = np.load(paths.PREPARED_FEATURES, mmap_mode="r")
    for b in ["rtp", "lidar_lappos_max", "iso_grav_anom"]:
        col = np.asarray(X[:, names.index(b)], dtype=np.float32)
        v = np.r_[col[pos], col[neg_s]]
        ok = np.isfinite(v)
        canary[f"base:{b}"] = float(roc_auc_score(
            np.r_[np.ones(len(pos)), np.zeros(len(neg_s))][ok], v[ok]))
    leak = {k: v for k, v in canary.items() if v > 0.90}
    print("CANARY leak flags (>0.90):", leak or "none", flush=True)

    # ---------- surface uniqueness pre-check (before placement) ----------
    probs = {}
    for arm in ["A", "B", "D"]:
        print(f"OOF arm {arm}...", flush=True)
        probs[arm] = oof_for_arm(arm, foot, labels, fold, names, T)
    reg_dir = paths.DATA / "parallel_registry"
    sample = rng.choice(np.flatnonzero(foot.ravel()), size=300_000, replace=False)
    surf_corr = {}
    import rasterio
    for rp in sorted(reg_dir.glob("*.tif")):
        with rasterio.open(rp) as s:
            a = s.read(1)
        dens = gaussian_filter((np.isfinite(a) & (a > 0)).astype(np.float32), 3.0)
        surf_corr[rp.name] = {arm: float(spearmanr(probs[arm].ravel()[sample],
                                                   dens.ravel()[sample]).statistic)
                              for arm in ["A", "D"]}
        print("surface Spearman", rp.name, surf_corr[rp.name], flush=True)

    # ---------- E2: buffered hide-and-recover, seeds 200-204 ----------
    fold_share = np.array([(fold == f).sum() for f in range(4)], float)
    fold_budget = np.round(BUDGET_TOTAL * fold_share / fold_share.sum()).astype(int)
    cells = {"A": [], "B": [], "D": [], "R": []}
    n_withheld = 0
    for seed in SEEDS:
        for f in range(4):
            sp = holdout.make_split(labels, fold, f, seed=seed)
            fold_domain = foot & sp.fold_mask
            valid = holdout.buffered_scoring_mask(sp, foot)
            n_withheld += int(sp.hidden.sum())
            for arm in ["A", "B", "D"]:
                dots = emit(probs[arm], fold_domain, sp.known, int(fold_budget[f]))
                cells[arm].append(score_cell(dots, sp, valid))
            dots_r = emit(probs["A"], fold_domain, sp.known, int(fold_budget[f]),
                          rng=np.random.default_rng(seed * 10 + f))
            cells["R"].append(score_cell(dots_r, sp, valid))
            print(f"seed {seed} fold {f}: " +
                  " ".join(f"{a}={cells[a][-1]['dti']:.4f}" for a in cells), flush=True)

    pooled = {a: pooled_dti(c) for a, c in cells.items()}
    # paired bootstrap CI on (A-B) and (D-B) cell deltas of per-cell DTI
    def boot(x, y):
        d = np.array([a["dti"] - b["dti"] for a, b in zip(x, y)])
        bs = np.random.default_rng(11)
        means = [bs.choice(d, size=len(d), replace=True).mean() for _ in range(2000)]
        return {"mean_delta": float(d.mean()),
                "ci95": [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))],
                "cells_positive": int((d > 0).sum()), "n_cells": int(len(d))}
    out = {
        "experiment": "E1+E2 Lane L-2026-10-25",
        "evaluator": "gems27.metric v1 (alpha=0.2, beta=0.8, R=3px triangular)",
        "label": "HOLDOUT-DTI (catalogue-internal hide-and-recover; NOT a live score)",
        "seeds": SEEDS, "folds": holdout.FOLD_NAMES,
        "n_withheld_positives_total": int(n_withheld),
        "budget_per_fold": fold_budget.tolist(), "min_dist_px": MIN_DIST, "b_exclusion_px": B_EXCL,
        "canary_auc": canary, "canary_leak_flags": leak,
        "surface_spearman_vs_registry": surf_corr,
        "pooled_holdout_dti": pooled,
        "paired": {"A_minus_B": boot(cells["A"], cells["B"]),
                   "D_minus_B": boot(cells["D"], cells["B"]),
                   "A_minus_R": boot(cells["A"], cells["R"])},
        "per_cell": {a: [{k: c[k] for k in ("dti", "TPw", "FPw", "FNw", "n_truth", "n_emitted")}
                         for c in cs] for a, cs in cells.items()},
        "runtime_s": round(time.time() - t0, 1),
    }
    dest = paths.EVIDENCE / "lane_holdout_2026-10-25.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print("POOLED HOLDOUT-DTI:", pooled)
    print("paired A-B:", out["paired"]["A_minus_B"], "| D-B:", out["paired"]["D_minus_B"])
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
