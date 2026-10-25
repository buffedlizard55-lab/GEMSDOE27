#!/usr/bin/env python3
"""Lane L-DCONFIRM experiments E1 (canary) + E2a/E2b (selection/confirmation holdout).

Preregistration: knowledge/15_lane_dconfirm_preregistration.md §4 (frozen before this ran).
Arms: B = full-32 (control), D = full-32 + 15 subsurface transforms (fallback candidate),
E = full-32 + 15 + 8 new dip/rad/polarity transforms (primary candidate). Selection on
seeds 210-214; exactly one candidate is confirmed against B on untouched seeds 215-224.
All scores are HOLDOUT-DTI (evaluator gems27.metric v1). Nothing here is a live score.
Uses the shared template evaluator/holdout/detector unchanged.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, gaussian_filter
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import dip_rad_features as drf  # noqa: E402
from gems27 import grid, holdout, metric, oof_detector, paths  # noqa: E402
from gems27 import subsurface_features as sub

WORK = paths.DATA / "dconfirm"
SEL_SEEDS = [210, 211, 212, 213, 214]
CONF_SEEDS = list(range(215, 225))
BUDGET_TOTAL = 38_000
MIN_DIST = 2.8
B_EXCL = 2.0


def build_or_load(name: str, builder) -> np.ndarray:
    WORK.mkdir(parents=True, exist_ok=True)
    f = WORK / name
    if f.exists():
        return np.load(f)
    arr = builder()
    np.save(f, arr)
    return arr


def load_transforms(foot, names):
    def build15():
        X = np.load(paths.PREPARED_FEATURES, mmap_mode="r")
        grids = {}
        for b in sub.SUBSURFACE_BANDS:
            a = np.full(grid.SHAPE, np.nan, dtype=np.float32)
            a[foot] = np.asarray(X[:, names.index(b)], dtype=np.float32)
            grids[b] = a
        return sub.build_transforms(grids, foot)

    def build8():
        X = np.load(paths.PREPARED_FEATURES, mmap_mode="r")
        prep = {}
        for b in drf.PREPARED_BANDS:
            a = np.full(grid.SHAPE, np.nan, dtype=np.float32)
            a[foot] = np.asarray(X[:, names.index(b)], dtype=np.float32)
            prep[b] = a
        rad = {}
        with rasterio.open(paths.RAD) as s:
            rad["rad_K"] = s.read(list(s.descriptions).index("K") + 1).astype(np.float32)
        with rasterio.open(paths.EXTENSIONS) as s:
            rad["ext_ThK"] = s.read(list(s.descriptions).index("ThK") + 1).astype(np.float32)
            rad["ext_UK"] = s.read(list(s.descriptions).index("UK") + 1).astype(np.float32)
        return drf.build_new_transforms(prep, rad, foot)

    return (build_or_load("subsurface_transforms.npy", build15),
            build_or_load("new_transforms.npy", build8))


def oof_for_arm(arm, foot, labels, fold, T15, T8):
    def build():
        if arm == "B":
            return oof_detector.fit_predict_oof_probabilities(foot, labels, fold)
        if arm == "D":
            return oof_detector.fit_predict_oof_probabilities(foot, labels, fold, extra=T15)
        if arm == "E":
            extra = np.concatenate([T15, T8], axis=1).astype(np.float32)
            return oof_detector.fit_predict_oof_probabilities(foot, labels, fold, extra=extra)
        raise ValueError(arm)
    return build_or_load(f"oof_prob_arm{arm}.npy", build)


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


def run_cells(arms, probs, labels, fold, foot, seeds, fold_budget):
    cells = {a: [] for a in arms}
    meta = []  # (seed, fold) per cell, shared across arms
    n_withheld = 0
    for seed in seeds:
        for f in range(4):
            sp = holdout.make_split(labels, fold, f, seed=seed)
            valid = holdout.buffered_scoring_mask(sp, foot)
            n_withheld += int(sp.hidden.sum())
            meta.append({"seed": seed, "fold": holdout.FOLD_NAMES[f]})
            for a in arms:
                dots = emit(probs[a], valid, sp.known, sp.hidden, int(fold_budget[f]))
                cells[a].append(score_cell(dots, sp, valid))
            print(f"  seed {seed} fold {holdout.FOLD_NAMES[f]}: "
                  + " ".join(f"{a}={cells[a][-1]['dti']:.4f}" for a in arms), flush=True)
    return cells, meta, n_withheld


def paired_stats(cand_cells, base_cells, meta):
    d = np.array([c["dti"] - b["dti"] for c, b in zip(cand_cells, base_cells)])
    rng = np.random.default_rng(0)
    means = np.array([d[rng.integers(0, len(d), len(d))].mean() for _ in range(2000)])
    fold_mean, seed_mean = {}, {}
    for m, v in zip(meta, d):
        fold_mean.setdefault(m["fold"], []).append(v)
        seed_mean.setdefault(m["seed"], []).append(v)
    return {
        "mean_delta": float(d.mean()),
        "ci95": [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))],
        "cells_positive": int((d > 0).sum()), "n_cells": int(len(d)),
        "folds_positive": int(sum(np.mean(v) > 0 for v in fold_mean.values())),
        "seeds_positive": int(sum(np.mean(v) > 0 for v in seed_mean.values())),
        "n_seeds": len(seed_mean),
        "fold_mean_delta": {k: float(np.mean(v)) for k, v in fold_mean.items()},
    }


def main() -> int:
    t0 = time.time()
    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    names = json.loads(paths.PREPARED_META.read_text())["names"]
    fold = holdout.make_quadrant_folds(foot)
    print("building transforms...", flush=True)
    T15, T8 = load_transforms(foot, names)
    print(f"T15 {T15.shape} T8 {T8.shape} in {time.time()-t0:.0f}s", flush=True)

    # ---------- E1: leakage canary on the 8 new transforms (seed 210 splits) ----------
    rng = np.random.default_rng(7)
    hidden_any = np.zeros(grid.SHAPE, bool)
    valid_any = np.zeros(grid.SHAPE, bool)
    for f in range(4):
        sp = holdout.make_split(labels, fold, f, seed=210)
        hidden_any |= sp.hidden
        valid_any |= holdout.buffered_scoring_mask(sp, foot)
    y = hidden_any[foot]
    scope = (valid_any | hidden_any)[foot]
    idx = np.flatnonzero(scope)
    pos = idx[y[idx]]
    neg = idx[~y[idx]]
    neg_s = rng.choice(neg, size=min(200_000, len(neg)), replace=False)
    canary = {}
    for j, nm in enumerate(drf.NEW_TRANSFORM_NAMES):
        col = T8[:, j]
        canary[nm] = float(roc_auc_score(
            np.r_[np.ones(len(pos)), np.zeros(len(neg_s))], np.r_[col[pos], col[neg_s]]))
        print(f"canary {nm}: AUC {canary[nm]:.4f}", flush=True)
    leak = {k: v for k, v in canary.items() if v > 0.90}
    if leak:
        print("CANARY LEAK — STOP:", leak, flush=True)
        return 2

    # ---------- OOF surfaces + surface uniqueness (before placement) ----------
    probs = {}
    for arm in ["B", "D", "E"]:
        print(f"OOF arm {arm}...", flush=True)
        probs[arm] = oof_for_arm(arm, foot, labels, fold, T15, T8)
    sample = rng.choice(np.flatnonzero(foot.ravel()), size=300_000, replace=False)
    surf_corr = {}
    for rp in sorted((paths.DATA / "parallel_registry").glob("*.tif")):
        with rasterio.open(rp) as s:
            a = s.read(1)
        dens = gaussian_filter((np.isfinite(a) & (a > 0)).astype(np.float32), 3.0)
        surf_corr[rp.name] = {arm: float(spearmanr(
            probs[arm].ravel()[sample], dens.ravel()[sample]).statistic) for arm in ["D", "E"]}
        print("surface Spearman", rp.name, surf_corr[rp.name], flush=True)

    fold_share = np.array([(fold == f).sum() for f in range(4)], float)
    fold_budget = np.round(BUDGET_TOTAL * fold_share / fold_share.sum()).astype(int)

    # ---------- E2a: selection, seeds 210-214 ----------
    print("E2a selection...", flush=True)
    sel_cells, sel_meta, sel_n = run_cells(["B", "D", "E"], probs, labels, fold, foot,
                                           SEL_SEEDS, fold_budget)
    sel_pooled = {a: pooled_dti(c) for a, c in sel_cells.items()}
    print("selection pooled HOLDOUT-DTI:", sel_pooled, flush=True)
    if sel_pooled["E"] > sel_pooled["B"] and sel_pooled["E"] >= sel_pooled["D"] - 0.001:
        candidate = "E"
    elif sel_pooled["D"] > sel_pooled["B"]:
        candidate = "D"
    else:
        candidate = None
    print("selected candidate:", candidate, flush=True)

    # ---------- E2b: confirmation, seeds 215-224 (untouched until here) ----------
    conf = None
    if candidate:
        print(f"E2b confirmation of {candidate} vs B...", flush=True)
        conf_cells, conf_meta, conf_n = run_cells([candidate, "B"], probs, labels, fold, foot,
                                                  CONF_SEEDS, fold_budget)
        conf_pooled = {a: pooled_dti(c) for a, c in conf_cells.items()}
        stats = paired_stats(conf_cells[candidate], conf_cells["B"], conf_meta)
        gate = (conf_pooled[candidate] > conf_pooled["B"] and stats["mean_delta"] >= 0.002
                and stats["folds_positive"] >= 3 and stats["seeds_positive"] >= 6)
        conf = {"candidate": candidate, "pooled_holdout_dti": conf_pooled,
                "paired_candidate_minus_B": stats, "n_withheld_positives": conf_n,
                "gate_pass": bool(gate),
                "per_cell": {a: [{k: c[k] for k in ("dti", "TPw", "FPw", "FNw",
                                                     "n_truth", "n_emitted")}
                                  for c in cs] for a, cs in conf_cells.items()},
                "meta": conf_meta}
        print("confirmation pooled:", conf_pooled, "| gate:", gate, stats, flush=True)

    out = {
        "experiment": "E1+E2 Lane L-DCONFIRM (knowledge/15)",
        "evaluator": "gems27.metric v1 (alpha=0.2, beta=0.8, R=3px triangular)",
        "label": "HOLDOUT-DTI (catalogue-internal hide-and-recover; NOT a live score)",
        "canary_auc_new_transforms": canary, "canary_leak_flags": leak,
        "surface_spearman_vs_peer_registry": surf_corr,
        "budget_per_fold": fold_budget.tolist(), "min_dist_px": MIN_DIST, "b_exclusion_px": B_EXCL,
        "selection": {"seeds": SEL_SEEDS, "pooled_holdout_dti": sel_pooled,
                      "n_withheld_positives": sel_n, "candidate": candidate,
                      "per_cell": {a: [{k: c[k] for k in ("dti", "TPw", "FPw", "FNw",
                                                          "n_truth", "n_emitted")}
                                        for c in cs] for a, cs in sel_cells.items()},
                      "meta": sel_meta},
        "confirmation": conf,
        "runtime_s": round(time.time() - t0, 1),
    }
    dest = paths.EVIDENCE / "dconfirm_holdout_2026-10-25.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
