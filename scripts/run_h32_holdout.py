#!/usr/bin/env python3
"""Session 11 / Lane L-S11, H32 experiments E1 (canary) + E2 (buffered hide-and-recover).

Preregistration: knowledge/26_preregistration_H32_2026-10-26.md (frozen before this ran).
Arms: B = base-32, D = base-32 + 15 subsurface transforms, P = D + 8 H32 Poisson features.
Identical blind emission for every arm (ridge_nms -> B2 > 2 px -> priority Poisson disk
2.8 px, 37,654-dot total budget by fold share). Every number written is HOLDOUT-DTI
(gems27.metric v1, alpha 0.2, beta 0.8, 300 m triangular kernel); nothing here is a live
or organizer score. Seeds 500-509 (fresh; consumed by this run).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import grid, holdout, metric, oof_detector, paths  # noqa: E402
from gems27 import poisson_demag as poi  # noqa: E402
from gems27 import subsurface_features as sub  # noqa: E402

H32_DIR = paths.DATA / "h32"
SEEDS = list(range(500, 510))
BUDGET_TOTAL = 37_654
MIN_DIST = 2.8
B_EXCL = 2.0


def load_base():
    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    names = json.loads(paths.PREPARED_META.read_text())["names"]
    return foot, labels, names


def _grids_for(foot, names, bands):
    X = np.load(paths.PREPARED_FEATURES, mmap_mode="r")
    grids = {}
    for b in bands:
        a = np.full(grid.SHAPE, np.nan, dtype=np.float32)
        a[foot] = np.asarray(X[:, names.index(b)], dtype=np.float32)
        grids[b] = a
    return grids


def build_or_load(fname, builder):
    H32_DIR.mkdir(parents=True, exist_ok=True)
    f = H32_DIR / fname
    if f.exists():
        return np.load(f)
    arr = builder()
    np.save(f, arr)
    return arr


def emit(prob, fold_domain, known, budget):
    d_vis = distance_transform_edt(~known)
    ridge = oof_detector.ridge_nms(prob, fold_domain)
    cand = ridge & fold_domain & ~known & (d_vis > B_EXCL)
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
    foot, labels, names = load_base()
    fold = holdout.make_quadrant_folds(foot)

    print("building subsurface transforms...", flush=True)
    T = build_or_load("subsurface_transforms.npy",
                      lambda: sub.build_transforms(_grids_for(foot, names, sub.SUBSURFACE_BANDS), foot))
    print("building H32 Poisson transforms...", flush=True)
    P8 = build_or_load("poisson_transforms.npy",
                       lambda: poi.build_transforms(_grids_for(foot, names, poi.REQUIRED_BANDS), foot))
    print(f"T {T.shape} P8 {P8.shape} in {time.time()-t0:.0f}s", flush=True)

    # ---- E1: leakage canary on seed-500 withheld positives ----
    rng = np.random.default_rng(7)
    hidden_any = np.zeros(grid.SHAPE, bool)
    valid_any = np.zeros(grid.SHAPE, bool)
    for f in range(4):
        sp = holdout.make_split(labels, fold, f, seed=500)
        hidden_any |= sp.hidden
        valid_any |= holdout.buffered_scoring_mask(sp, foot)
    y = hidden_any[foot]
    scope = (valid_any | hidden_any)[foot]
    idx_scope = np.flatnonzero(scope)
    pos = idx_scope[y[idx_scope]]
    neg = idx_scope[~y[idx_scope]]
    neg_s = rng.choice(neg, size=min(200_000, len(neg)), replace=False)
    yv = np.r_[np.ones(len(pos)), np.zeros(len(neg_s))]
    canary = {}
    for j, nm in enumerate(poi.TRANSFORM_NAMES):
        col = P8[:, j]
        auc = float(roc_auc_score(yv, np.r_[col[pos], col[neg_s]]))
        canary[nm] = {"auc": auc, "direction_invariant_auc": float(max(auc, 1.0 - auc))}
        print(f"canary {nm}: AUC {auc:.4f}", flush=True)
    canary_max = max(v["direction_invariant_auc"] for v in canary.values())
    leak = {k: v for k, v in canary.items() if v["direction_invariant_auc"] > 0.90}
    print("CANARY max dir-inv AUC", round(canary_max, 4), "leak flags:", leak or "none", flush=True)
    if leak:
        out = {"experiment": "E1 H32 HALTED (leakage canary)", "canary": canary,
               "canary_max_direction_invariant_auc": canary_max}
        (paths.EVIDENCE / "h32_e1_canary.json").write_text(json.dumps(out, indent=2) + "\n")
        print("HALTED: leakage canary > 0.90", flush=True)
        return 2

    # ---- OOF surfaces ----
    DP = np.concatenate([T, P8], axis=1)
    probs = {}
    probs["B"] = build_or_load("oof_prob_armB.npy",
                               lambda: oof_detector.fit_predict_oof_probabilities(foot, labels, fold))
    print("OOF B done", flush=True)
    probs["D"] = build_or_load("oof_prob_armD.npy",
                               lambda: oof_detector.fit_predict_oof_probabilities(foot, labels, fold, extra=T))
    print("OOF D done", flush=True)
    probs["P"] = build_or_load("oof_prob_armP.npy",
                               lambda: oof_detector.fit_predict_oof_probabilities(foot, labels, fold, extra=DP))
    print("OOF P done", flush=True)

    pr_auc = {a: float(oof_detector.oof_pr_auc(p, labels, foot)) for a, p in probs.items()}
    print("OOF PR-AUC (catalogue pixels, descriptive):", pr_auc, flush=True)

    # ---- E2: buffered hide-and-recover, seeds 500-509 ----
    fold_share = np.array([(fold == f).sum() for f in range(4)], float)
    fold_budget = np.round(BUDGET_TOTAL * fold_share / fold_share.sum()).astype(int)
    fold_budget[-1] += BUDGET_TOTAL - int(fold_budget.sum())
    cells: dict[str, list] = {"B": [], "D": [], "P": []}
    cell_index = []  # (seed, fold) per cell, aligned across arms
    n_withheld = 0
    for seed in SEEDS:
        for f in range(4):
            sp = holdout.make_split(labels, fold, f, seed=seed)
            fold_domain = foot & sp.fold_mask
            valid = holdout.buffered_scoring_mask(sp, foot)
            n_withheld += int(sp.hidden.sum())
            for arm in ("B", "D", "P"):
                dots = emit(probs[arm], fold_domain, sp.known, int(fold_budget[f]))
                cells[arm].append(score_cell(dots, sp, valid))
            cell_index.append((seed, f))
            print(f"seed {seed} fold {f} ({holdout.FOLD_NAMES[f]}): " +
                  " ".join(f"{a}={cells[a][-1]['dti']:.4f}" for a in cells), flush=True)

    pooled = {a: pooled_dti(c) for a, c in cells.items()}

    def seed_pooled(arm, seed):
        return pooled_dti([c for c, (s, _) in zip(cells[arm], cell_index) if s == seed])

    def fold_pooled(arm, f):
        return pooled_dti([c for c, (_, ff) in zip(cells[arm], cell_index) if ff == f])

    def paired(x_arm, y_arm):
        per_seed = np.array([seed_pooled(x_arm, s) - seed_pooled(y_arm, s) for s in SEEDS])
        bs = np.random.default_rng(11)
        means = np.array([bs.choice(per_seed, size=len(per_seed), replace=True).mean()
                          for _ in range(4000)])
        per_fold = {holdout.FOLD_NAMES[f]: float(fold_pooled(x_arm, f) - fold_pooled(y_arm, f))
                    for f in range(4)}
        cell_d = np.array([a["dti"] - b["dti"] for a, b in zip(cells[x_arm], cells[y_arm])])
        return {
            "pooled_delta_dti": float(pooled[x_arm] - pooled[y_arm]),
            "mean_seed_paired_delta_dti": float(per_seed.mean()),
            "ci95": [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))],
            "positive_seeds": int((per_seed > 0).sum()), "n_seeds": int(len(per_seed)),
            "positive_folds": int(sum(v > 0 for v in per_fold.values())), "n_folds": 4,
            "per_fold_pooled_delta_dti": per_fold,
            "per_seed_pooled_delta_dti": per_seed.tolist(),
            "positive_cells": int((cell_d > 0).sum()), "n_cells": int(len(cell_d)),
        }

    p_minus_d = paired("P", "D")
    p_minus_b = paired("P", "B")
    gate = {
        "pooled_P_gt_D_and_B": bool(pooled["P"] > pooled["D"] and pooled["P"] > pooled["B"]),
        "mean_seed_delta_P_minus_D_ge_0.0010": bool(p_minus_d["mean_seed_paired_delta_dti"] >= 0.0010),
        "ci95_lower_P_minus_D_gt_0": bool(p_minus_d["ci95"][0] > 0),
        "seeds_positive_P_minus_D_ge_7_of_10": bool(p_minus_d["positive_seeds"] >= 7),
        "folds_positive_P_minus_D_ge_3_of_4": bool(p_minus_d["positive_folds"] >= 3),
    }
    gate_pass = bool(all(gate.values()))

    out = {
        "experiment": "E1+E2 H32 Poisson demagnetization (Lane L-S11)",
        "preregistration": "knowledge/26_preregistration_H32_2026-10-26.md",
        "label": "HOLDOUT-DTI",
        "provenance_note": "Catalogue-internal buffered hide-and-recover; NOT a live/organizer score.",
        "evaluator": "gems27.metric.dti_binary v1 (alpha=0.2, beta=0.8, R=3px triangular) + buffered quadrant holdout (buffer 6px)",
        "seeds": SEEDS, "folds": holdout.FOLD_NAMES,
        "n_cells": len(cell_index), "n_withheld_positives_total": int(n_withheld),
        "budget_per_fold": fold_budget.tolist(), "min_dist_px": MIN_DIST, "b_exclusion_px": B_EXCL,
        "canary": canary, "canary_max_direction_invariant_auc": float(canary_max),
        "oof_pr_auc_catalogue_descriptive": pr_auc,
        "pooled_holdout_dti_buffered": pooled,
        "per_fold_pooled_holdout_dti_buffered": {
            a: {holdout.FOLD_NAMES[f]: float(fold_pooled(a, f)) for f in range(4)} for a in cells},
        "paired_P_minus_D": p_minus_d, "paired_P_minus_B": p_minus_b,
        "paired_D_minus_B": paired("D", "B"),
        "frozen_gate_clauses": gate, "gate_efficacy_pass": gate_pass,
        "per_cell": {a: [{k: float(c[k]) for k in ("dti", "TPw", "FPw", "FNw", "n_truth", "n_emitted")}
                         for c in cs] for a, cs in cells.items()},
        "cell_index": cell_index,
        "runtime_s": round(time.time() - t0, 1),
    }
    ev = paths.EVIDENCE / "h32_e2_holdout_500_509.json"
    ev.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({"pooled": pooled, "P-D": {k: p_minus_d[k] for k in
          ("pooled_delta_dti", "mean_seed_paired_delta_dti", "ci95", "positive_seeds", "positive_folds")},
          "gate": gate, "gate_pass": gate_pass, "evidence": str(ev)}, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
