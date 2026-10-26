#!/usr/bin/env python3
"""H31 E1+E2: complementary OOF-surface rank-ensemble holdout (Session 10, 2026-10-26).

Preregistered in knowledge/23_preregistration_H31_2026-10-26.md (committed before any run):
fresh seeds 260-269, arms ENS / H29S / D0S under identical blind weighted-CELF emission
(B2, gamma=1.5, min-sep 2.0 px, matched 37,654 full-map budget), buffered hide-and-recover
primary. Reuses the shared evaluator (`gems27.metric`, `gems27.holdout`) and the frozen H29
surface builders from `scripts/run_h29_holdout.py`; no private fork of any shared tool.
All numbers are HOLDOUT-DTI (catalogue-internal); no live score is claimed.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from scipy.ndimage import gaussian_filter  # noqa: E402
from scipy.stats import rankdata, spearmanr  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402

import run_h29_holdout as h29run  # noqa: E402
from gems27 import grid, holdout, paths  # noqa: E402
from gems27 import hydrothermal_piedmont as h29  # noqa: E402

SEEDS: list[int] = list(range(260, 270))
BUDGET_TOTAL = 37_654
ARMS = ["ENS", "H29S", "D0S"]
CACHE = paths.DATA / "h31"
E1_OUT = paths.EVIDENCE / "h31_e1_canary_and_surface.json"
E2_OUT = paths.EVIDENCE / "h31_e2_holdout_260_269.json"
R6_PATH = paths.DATA / "parallel_registry_extra" / "g32_r6_step.tif"


def percentile_rank_grid(prob: np.ndarray, foot: np.ndarray) -> np.ndarray:
    out = np.zeros(prob.shape, dtype=np.float32)
    vals = np.asarray(prob[foot], dtype=np.float64)
    out[foot] = (rankdata(vals, method="average") / vals.size).astype(np.float32)
    return out


def get_surfaces():
    """Build/load the two frozen quadrant-OOF surfaces and the 50/50 rank ensemble."""
    CACHE.mkdir(parents=True, exist_ok=True)
    ens_path = CACHE / "ens_rankmean_surface.npy"
    foot, labels, names = h29run.load_base()
    fold = holdout.make_quadrant_folds(foot)
    base_X = np.load(paths.PREPARED_FEATURES, mmap_mode="r")
    h29_X = h29.build_h29_feature_matrix(
        cache_path=paths.DATA / "h29" / "h29_features.npy")
    _, prob_h29 = h29run.get_or_fit_h29_quad_oof(base_X, h29_X, labels, foot)
    prob_d0 = h29run.get_or_fit_baseline_oof("D0", foot, labels, fold, names)
    if ens_path.exists():
        ens = np.load(ens_path)
    else:
        ens = 0.5 * percentile_rank_grid(prob_h29, foot) \
            + 0.5 * percentile_rank_grid(prob_d0, foot)
        ens = ens.astype(np.float32)
        np.save(ens_path, ens)
    return foot, labels, fold, {"ENS": ens, "H29S": prob_h29, "D0S": prob_d0}


def run_e1() -> int:
    t0 = time.time()
    foot, labels, fold, surf = get_surfaces()
    hidden_any = np.zeros_like(labels)
    valid_any = np.zeros_like(labels)
    for seed in SEEDS:
        for f in range(4):
            sp = holdout.make_split(labels, fold, f, seed=seed)
            hidden_any |= sp.hidden
            valid_any |= holdout.buffered_scoring_mask(sp, foot)
    scope = (valid_any | hidden_any) & foot
    y = hidden_any[scope]
    rng = np.random.default_rng(260)
    pos = np.flatnonzero(y)
    neg_all = np.flatnonzero(~y)
    neg = rng.choice(neg_all, size=min(250_000, neg_all.size), replace=False)
    y_eval = np.r_[np.ones(pos.size, np.int8), np.zeros(neg.size, np.int8)]
    canary = {}
    for arm in ARMS:
        v_full = surf[arm][scope]
        v = np.r_[v_full[pos], v_full[neg]].astype(float)
        raw = float(roc_auc_score(y_eval, v))
        canary[arm] = {"raw_auc": round(raw, 5),
                       "direction_invariant_auc": round(max(raw, 1 - raw), 5)}
        print(f"  canary {arm}: raw={raw:.4f}", flush=True)
    max_auc = max(d["direction_invariant_auc"] for d in canary.values())

    sample = rng.choice(np.flatnonzero(foot.ravel()), size=400_000, replace=False)
    ens_vec = surf["ENS"].ravel()[sample]
    peers = {}
    peer_paths = sorted((paths.DATA / "parallel_registry").glob("*.tif"))
    if R6_PATH.exists():
        peer_paths.append(R6_PATH)
    for rp in peer_paths:
        with rasterio.open(rp) as s:
            a = s.read(1)
        raw_bin = (np.isfinite(a) & (a > 0)).astype(np.float32)
        dens = gaussian_filter(raw_bin, sigma=3.0)
        r_raw = float(spearmanr(ens_vec, raw_bin.ravel()[sample]).statistic)
        r_den = float(spearmanr(ens_vec, dens.ravel()[sample]).statistic)
        peers[rp.stem] = {"raw_spearman": round(r_raw, 5),
                          "kernel3_spearman": round(r_den, 5),
                          "max_abs_spearman": round(max(abs(r_raw), abs(r_den)), 5)}
        print(f"  Spearman ENS vs {rp.stem}: raw={r_raw:.4f} k3={r_den:.4f}", flush=True)
    max_rho = max(d["max_abs_spearman"] for d in peers.values())
    gate = bool(max_auc <= 0.90 and max_rho <= 0.90)
    out = {"experiment": "E1_H31_canary_and_surface", "lane": "H31-ENS",
           "preregistration": "knowledge/23_preregistration_H31_2026-10-26.md",
           "seeds": SEEDS, "n_unique_withheld_positive_pixels": int(hidden_any.sum()),
           "canary_threshold_auc": 0.90, "canary_surfaces": canary,
           "canary_max_direction_invariant_auc": max_auc,
           "surface_spearman_threshold": 0.90, "n_peer_rasters_checked": len(peers),
           "peer_surface_spearman": peers, "max_peer_abs_spearman": max_rho,
           "gate_e1_pass": gate, "runtime_s": round(time.time() - t0, 1)}
    E1_OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(f"E1 PASS={gate} max_auc={max_auc:.4f} max_rho={max_rho:.4f} -> {E1_OUT}", flush=True)
    return 0 if gate else 2


def paired(cand, base, n_boot=10_000, rng_seed=20261026):
    n = len(SEEDS)
    sc = np.array([h29run.pooled_dti(cand[4 * i:4 * (i + 1)]) for i in range(n)])
    sb = np.array([h29run.pooled_dti(base[4 * i:4 * (i + 1)]) for i in range(n)])
    d = sc - sb
    rng = np.random.default_rng(rng_seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    boot = d[idx].mean(axis=1)
    per_fold, fwins = {}, 0
    for f, fnm in enumerate(holdout.FOLD_NAMES):
        fd = h29run.pooled_dti([cand[4 * i + f] for i in range(n)]) \
            - h29run.pooled_dti([base[4 * i + f] for i in range(n)])
        per_fold[fnm] = round(float(fd), 6)
        fwins += int(fd > 0)
    cell_d = np.array([a["dti"] - b["dti"] for a, b in zip(cand, base)])
    return {"pooled_delta_dti": round(float(h29run.pooled_dti(cand)
                                             - h29run.pooled_dti(base)), 6),
            "mean_seed_paired_delta_dti": round(float(d.mean()), 6),
            "seed_bootstrap_95_ci": [round(float(np.percentile(boot, 2.5)), 6),
                                     round(float(np.percentile(boot, 97.5)), 6)],
            "positive_seeds": int((d > 0).sum()), "n_seeds": n,
            "positive_folds": fwins, "n_folds": 4,
            "per_fold_pooled_delta_dti": per_fold,
            "positive_cells": int((cell_d > 0).sum()), "n_cells": len(cell_d)}


def run_e2() -> int:
    t0 = time.time()
    if not E1_OUT.exists():
        rc = run_e1()
        if rc != 0:
            return rc
    e1 = json.loads(E1_OUT.read_text())
    if not e1["gate_e1_pass"]:
        print("E1 failed; refusing E2.", flush=True)
        return 2
    foot, labels, fold, surf = get_surfaces()
    share = np.array([(fold == f).sum() for f in range(4)], dtype=np.float64)
    fold_budget = np.round(BUDGET_TOTAL * share / share.sum()).astype(int)
    fold_budget[int(np.argmax(share))] += BUDGET_TOTAL - int(fold_budget.sum())
    assert int(fold_budget.sum()) == BUDGET_TOTAL
    cells_buf = {a: [] for a in ARMS}
    cells_unb = {a: [] for a in ARMS}
    n_with = 0
    for seed in SEEDS:
        ts = time.time()
        for f in range(4):
            sp = holdout.make_split(labels, fold, f, seed=seed)
            fdom = foot & sp.fold_mask
            valid_buf = holdout.buffered_scoring_mask(sp, foot, buffer_px=6.0)
            n_with += int(sp.hidden.sum())
            for a in ARMS:
                dots = h29run.emit_weighted_celf(surf[a], fdom, sp.known,
                                                 int(fold_budget[f]))
                assert not (dots & ~fdom).any(), f"{a} outside fold domain"
                assert not (dots & sp.known).any(), f"{a} on known catalogue"
                cells_buf[a].append(h29run.score_cell(dots, sp, valid_buf))
                cells_unb[a].append(h29run.score_cell(dots, sp, fdom))
        print(f"seed {seed} ({time.time()-ts:.1f}s) buffered: " + " ".join(
            f"{a}={h29run.pooled_dti(cells_buf[a][-4:]):.4f}" for a in ARMS), flush=True)
    pooled_buf = {a: round(h29run.pooled_dti(cells_buf[a]), 6) for a in ARMS}
    pooled_unb = {a: round(h29run.pooled_dti(cells_unb[a]), 6) for a in ARMS}
    comps = {"ENS_minus_H29S": paired(cells_buf["ENS"], cells_buf["H29S"]),
             "ENS_minus_D0S": paired(cells_buf["ENS"], cells_buf["D0S"]),
             "D0S_minus_H29S": paired(cells_buf["D0S"], cells_buf["H29S"])}
    vs = comps["ENS_minus_H29S"]
    clauses = {
        "a_pooled_beats_both": bool(pooled_buf["ENS"] > pooled_buf["H29S"]
                                    and pooled_buf["ENS"] > pooled_buf["D0S"]),
        "b_mean_paired_vs_H29S_ge_0p0010": bool(vs["mean_seed_paired_delta_dti"] >= 0.0010),
        "c_ci95_lower_gt_zero_vs_H29S": bool(vs["seed_bootstrap_95_ci"][0] > 0.0),
        "d_folds_ge_3_of_4_vs_both": bool(vs["positive_folds"] >= 3
                                          and comps["ENS_minus_D0S"]["positive_folds"] >= 3),
        "e_seeds_ge_8_of_10_vs_H29S": bool(vs["positive_seeds"] >= 8),
        "f_e1_pass": bool(e1["gate_e1_pass"]),
    }
    gate = all(clauses.values())
    per_fold = {fnm: {a: round(h29run.pooled_dti(
        [cells_buf[a][4 * i + f] for i in range(len(SEEDS))]), 6) for a in ARMS}
        for f, fnm in enumerate(holdout.FOLD_NAMES)}
    per_seed = {str(s): {a: round(h29run.pooled_dti(cells_buf[a][4 * i:4 * (i + 1)]), 6)
                         for a in ARMS} for i, s in enumerate(SEEDS)}
    out = {"experiment": "E2_H31_paired_spatial_holdout", "lane": "H31-ENS",
           "preregistration": "knowledge/23_preregistration_H31_2026-10-26.md",
           "label": "HOLDOUT-DTI",
           "evaluator_version": "gems27.metric v1 + holdout-blind-buffered-v2 "
                                "(alpha=0.2, beta=0.8, R=3px triangular, buffer_px=6.0)",
           "provenance_label": "HOLDOUT-DTI (catalogue-internal hide-and-recover; "
                               "NOT a live organizer score)",
           "seeds": SEEDS, "folds": holdout.FOLD_NAMES, "n_cells": 40,
           "n_withheld_positive_occurrences": n_with,
           "matched_full_map_budget": BUDGET_TOTAL,
           "fold_budgets": fold_budget.tolist(), "b_exclusion_px": 2.0,
           "pooled_buffered_holdout_dti": pooled_buf,
           "pooled_unbuffered_diagnostic_holdout_dti": pooled_unb,
           "per_fold_buffered_holdout_dti": per_fold,
           "per_seed_buffered_holdout_dti": per_seed,
           "paired_comparisons_buffered": comps,
           "frozen_gate_clauses": clauses, "gate_e2_pass": bool(gate),
           "verdict_stage_e2": "promote" if gate else "negative",
           "grid_shape": list(grid.SHAPE),
           "runtime_s": round(time.time() - t0, 1)}
    E2_OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("POOLED BUFFERED:", json.dumps(pooled_buf), flush=True)
    print("POOLED UNBUFFERED:", json.dumps(pooled_unb), flush=True)
    print("CLAUSES:", json.dumps(clauses), f"GATE={gate} -> {E2_OUT}", flush=True)
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
    return rc if rc != 0 else run_e2()


if __name__ == "__main__":
    raise SystemExit(main())
