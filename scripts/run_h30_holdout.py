#!/usr/bin/env python3
"""H30 experiments E1 (canary) + E2 (holdout), frozen in knowledge/20_preregistration_H30.md.

Arms (identical per-fold budgets summing to 38,000 dots, B2 from visible faults only):
  B = full-32 control (shared instrument, unchanged);
  D = full-32 + 15 subsurface transforms (the twice-confirmed increment; fresh-seed replication);
  L = lane: D surface re-ranked by the label-free hydrothermal-chemistry multiplier, emitted with
      deconflicted priority Poisson-disk (<=65% of dots within 3 px of this repo's shipped rasters).

Seeds 240-244 are fresh (history consumed 130-159, 200-204, 210-214, 215-224, 230-231).
All numbers are HOLDOUT-DTI (gems27.metric v1). Nothing here is a live score.
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
from gems27 import grid, holdout, metric, oof_detector, paths  # noqa: E402
from gems27 import hydrochemistry as hc  # noqa: E402
from gems27 import subsurface_features as sub  # noqa: E402

WORK = paths.DATA / "h30"
SEEDS = [240, 241, 242, 243, 244]
BUDGET_TOTAL = 38_000
MIN_DIST = 2.8
B_EXCL = 2.0
CAP = 0.65
CANARY_STOP = 0.90
D_TOLERANCE = -0.004  # promote requires mean paired L-D >= this (frozen, knowledge/20 §3)


def build_or_load(name: str, builder) -> np.ndarray:
    WORK.mkdir(parents=True, exist_ok=True)
    f = WORK / name
    if f.exists():
        return np.load(f)
    arr = builder()
    np.save(f, arr)
    return arr


def build15(foot, names):
    X = np.load(paths.PREPARED_FEATURES, mmap_mode="r")
    grids = {}
    for b in sub.SUBSURFACE_BANDS:
        a = np.full(grid.SHAPE, np.nan, dtype=np.float32)
        a[foot] = np.asarray(X[:, names.index(b)], dtype=np.float32)
        grids[b] = a
    return sub.build_transforms(grids, foot)


def _repo_raster_paths() -> list[Path]:
    """Every repo-shipped raster: -nan twins where they exist, plus orphan -allfinite files.

    This lane's own outputs are excluded so the frozen E2 numbers are reproducible.
    """
    out = []
    for d in [paths.DOCS / "downloads", paths.DOCS / "downloads" / "research"]:
        nan = sorted(d.glob("gems27-*-nan.tif"))
        out.extend(nan)
        have = {p.name[: -len("-nan.tif")] for p in nan}
        for p in sorted(d.glob("gems27-*-allfinite.tif")):
            if p.name[: -len("-allfinite.tif")] not in have:
                out.append(p)
    return [p for p in out if "gems27-h30-" not in p.name]


def repo_conflicted(foot) -> tuple[np.ndarray, list[str]]:
    """Union 3-px halo of every repo-shipped raster's positive pixels (deconfliction targets)."""
    names = []
    arrays = []
    for rp in _repo_raster_paths():
        with rasterio.open(rp) as s:
            a = s.read(1)
        arrays.append(a)
        names.append(rp.name)
    return hc.conflicted_mask(arrays, grid.SHAPE), names


def emit(prob, valid_scoring, known, hidden, budget):
    """Plain emission (arms B, D): ridge NMS, B2(visible), priority Poisson >=2.8 px."""
    d_vis = distance_transform_edt(~known)
    ridge = oof_detector.ridge_nms(prob, valid_scoring | hidden)
    cand = ridge & (valid_scoring | hidden) & ~known & (d_vis > B_EXCL)
    return sub.priority_poisson_disk(prob, cand, MIN_DIST, budget)


def emit_lane(score, valid_scoring, known, hidden, budget, conflicted):
    """Lane emission: same candidate rule, deconflicted priority Poisson with the frozen cap."""
    d_vis = distance_transform_edt(~known)
    ridge = oof_detector.ridge_nms(score, valid_scoring | hidden)
    cand = ridge & (valid_scoring | hidden) & ~known & (d_vis > B_EXCL)
    return hc.deconflicted_priority_poisson_disk(score, cand, conflicted, MIN_DIST, budget, cap=CAP)


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

    print("building transforms + chemistry field...", flush=True)
    T15 = build_or_load("subsurface_transforms.npy", lambda: build15(foot, names))
    chem = hc.build_chemistry_field(paths.DATA / "gdr_wellspring_in_footprint.csv",
                                    grid.SHAPE, foot)
    M = hc.rank_multiplier(chem)
    cover = chem["coverage"]
    print(f"T15 {T15.shape}; chemistry coverage {int(cover.sum()):,} px "
          f"({100*cover.sum()/foot.sum():.2f}% of footprint) in {time.time()-t0:.0f}s", flush=True)

    conflicted, repo_names = repo_conflicted(foot)
    print(f"deconfliction targets: {len(repo_names)} repo rasters; "
          f"conflicted px inside footprint: {int((conflicted & foot).sum()):,}", flush=True)

    # ---------- E1: leakage canary on the re-ranking multiplier (seed-240 splits) ----------
    rng = np.random.default_rng(7)
    hidden_any = np.zeros(grid.SHAPE, bool)
    valid_any = np.zeros(grid.SHAPE, bool)
    for f in range(4):
        sp = holdout.make_split(labels, fold, f, seed=SEEDS[0])
        hidden_any |= sp.hidden
        valid_any |= holdout.buffered_scoring_mask(sp, foot)
    y = hidden_any[foot]
    scope = (valid_any | hidden_any)[foot]
    idx = np.flatnonzero(scope)
    pos = idx[y[idx]]
    neg = idx[~y[idx]]
    neg_s = rng.choice(neg, size=min(200_000, len(neg)), replace=False)
    m_col = M[foot]
    canary = {
        "rerank_multiplier_M": float(roc_auc_score(
            np.r_[np.ones(len(pos)), np.zeros(len(neg_s))], np.r_[m_col[pos], m_col[neg_s]])),
    }
    # Secondary reading: C restricted to coverage (where the field is informative at all).
    c_col = chem["anomaly"][foot]
    cov_col = cover[foot]
    idxc = np.flatnonzero(scope & cov_col)
    if len(idxc) and y[idxc].any() and (~y[idxc]).any():
        canary["anomaly_C_within_coverage"] = float(roc_auc_score(y[idxc], c_col[idxc]))
    for k, v in canary.items():
        print(f"canary {k}: AUC {v:.4f}", flush=True)
    leak = {k: v for k, v in canary.items() if v > CANARY_STOP}
    if leak:
        print("CANARY LEAK — STOP:", leak, flush=True)
        return 2

    # ---------- OOF surfaces (shared instrument, unchanged hyper-parameters) ----------
    probs = {}
    probs["B"] = build_or_load("oof_prob_armB.npy",
                               lambda: oof_detector.fit_predict_oof_probabilities(foot, labels, fold))
    probs["D"] = build_or_load("oof_prob_armD.npy",
                               lambda: oof_detector.fit_predict_oof_probabilities(
                                   foot, labels, fold, extra=T15))
    probs["L"] = hc.rerank(probs["D"], chem)  # lane surface: D x bounded chemistry multiplier

    # ---------- surface uniqueness vs the 12 pinned peers (before placement) ----------
    sample = rng.choice(np.flatnonzero(foot.ravel()), size=300_000, replace=False)
    surf_corr = {}
    for rp in sorted((paths.DATA / "parallel_registry").glob("*.tif")):
        with rasterio.open(rp) as s:
            a = s.read(1)
        dens = gaussian_filter((np.isfinite(a) & (a > 0)).astype(np.float32), 3.0)
        surf_corr[rp.name] = {arm: float(spearmanr(
            probs[arm].ravel()[sample], dens.ravel()[sample]).statistic) for arm in ["L"]}
        print("surface Spearman", rp.name, surf_corr[rp.name], flush=True)
    max_surf = max(v["L"] for v in surf_corr.values())
    surf_ok = max_surf <= 0.90

    # ---------- E2: holdout cells, seeds 240-244 ----------
    fold_share = np.array([(fold == f).sum() for f in range(4)], float)
    fold_budget = np.round(BUDGET_TOTAL * fold_share / fold_share.sum()).astype(int)
    cells = {a: [] for a in ["B", "D", "L"]}
    meta = []
    n_withheld = 0
    lane_place_info = []
    for seed in SEEDS:
        for f in range(4):
            sp = holdout.make_split(labels, fold, f, seed=seed)
            valid = holdout.buffered_scoring_mask(sp, foot)
            n_withheld += int(sp.hidden.sum())
            meta.append({"seed": seed, "fold": holdout.FOLD_NAMES[f]})
            cells["B"].append(score_cell(emit(probs["B"], valid, sp.known, sp.hidden,
                                              int(fold_budget[f])), sp, valid))
            cells["D"].append(score_cell(emit(probs["D"], valid, sp.known, sp.hidden,
                                              int(fold_budget[f])), sp, valid))
            dots, info = emit_lane(probs["L"], valid, sp.known, sp.hidden,
                                   int(fold_budget[f]), conflicted)
            lane_place_info.append(info)
            cells["L"].append(score_cell(dots, sp, valid))
            print(f"  seed {seed} fold {holdout.FOLD_NAMES[f]}: "
                  + " ".join(f"{a}={cells[a][-1]['dti']:.4f}" for a in ["B", "D", "L"])
                  + f" | L conflicted {info['conflicted_fraction']:.2f}", flush=True)

    pooled = {a: pooled_dti(cells[a]) for a in cells}
    stats_LB = paired_stats(cells["L"], cells["B"], meta)
    stats_LD = paired_stats(cells["L"], cells["D"], meta)
    stats_DB = paired_stats(cells["D"], cells["B"], meta)
    print("pooled HOLDOUT-DTI:", pooled, flush=True)
    print("paired L-B:", stats_LB, flush=True)
    print("paired L-D:", stats_LD, flush=True)
    print("paired D-B (fresh-seed replication):", stats_DB, flush=True)

    gate = {
        "pooled_L_gt_B": bool(pooled["L"] > pooled["B"]),
        "paired_LB_mean_positive": bool(stats_LB["mean_delta"] > 0),
        "paired_LB_ci_excludes_zero": bool(stats_LB["ci95"][0] > 0),
        "cells_positive_ge_12_of_20": bool(stats_LB["cells_positive"] >= 12),
        "canary_clean": not leak,
        "LD_within_tolerance": bool(stats_LD["mean_delta"] >= D_TOLERANCE),
        "surface_spearman_ok": bool(surf_ok),
    }
    gate_pass = all(gate.values())
    print("E2 gate:", gate, "->", gate_pass, flush=True)

    out = {
        "experiment": "E1+E2 Lane L-H30 (knowledge/20)",
        "evaluator": "gems27.metric v1 (alpha=0.2, beta=0.8, R=3px triangular)",
        "label": "HOLDOUT-DTI (catalogue-internal hide-and-recover; NOT a live score)",
        "seeds": SEEDS,
        "budget_per_fold": fold_budget.tolist(), "min_dist_px": MIN_DIST, "b_exclusion_px": B_EXCL,
        "deconfliction": {"cap": CAP, "repo_rasters": repo_names,
                          "conflicted_px_in_footprint": int((conflicted & foot).sum()),
                          "mean_conflicted_fraction": float(
                              np.mean([i["conflicted_fraction"] for i in lane_place_info])),
                          "per_cell": lane_place_info},
        "chemistry": {"coverage_px": int(cover.sum()),
                      "coverage_fraction_of_footprint": float(cover.sum() / foot.sum()),
                      "gamma": hc.RERANK_GAMMA,
                      "source": "data_cache/gdr_wellspring_in_footprint.csv (sha256 122718e6...)",
                      "excluded_column": "dist_known_fault_px (catalogue-derived; never read)"},
        "canary_auc": canary, "canary_leak_flags": leak,
        "surface_spearman_vs_peer_registry": surf_corr,
        "max_surface_spearman_L": max_surf,
        "pooled_holdout_dti": pooled,
        "n_withheld_positives_total": n_withheld,
        "paired_L_minus_B": stats_LB,
        "paired_L_minus_D": stats_LD,
        "paired_D_minus_B": stats_DB,
        "gate_components": gate,
        "gate_efficacy_pass": bool(gate_pass),
        "per_cell": {a: [{k: c[k] for k in ("dti", "TPw", "FPw", "FNw",
                                            "n_truth", "n_emitted")} for c in cs]
                     for a, cs in cells.items()},
        "meta": meta,
        "runtime_s": round(time.time() - t0, 1),
    }
    dest = paths.EVIDENCE / "h30_holdout.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote {dest} (runtime {out['runtime_s']}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
