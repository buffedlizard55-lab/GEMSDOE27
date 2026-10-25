#!/usr/bin/env python3
"""Lane L-H30 confirmatory holdout (preregistration: knowledge/20).

E1 leakage canary (9 new H30 features alone, seed-240 splits) + E2a selection
(seeds 240-244) + E2b confirmation (seeds 245-254), frozen in knowledge/20
BEFORE this script was run. Arms: D = 32-band + 15 subsurface (control to
beat), DIP = D + 5 dip-advection features, GAP = D + 4 gap-flanking features,
SOFT = D surface with the H30-3 soft rank-taper emission. Binary emission is
identical across arms (ridge NMS -> B2 -> priority Poisson-disk 2.8 px,
matched per-fold budgets summing to 38,000); SOFT uses 2x support rescaled
to the same effective mass and is scored with the exact soft metric.
All scores are HOLDOUT-DTI (gems27.metric v1: alpha 0.2, beta 0.8, 300 m
triangular kernel); pooled = TPw/FPw/FNw summed over cells before the ratio.
Reuses shared tools unchanged; OOF probabilities cached under data_cache/lane/.
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
from gems27 import dip_gap_features as dg  # noqa: E402
from gems27 import grid, holdout, metric, oof_detector, paths  # noqa: E402
from gems27 import subsurface_features as sub  # noqa: E402

LANE_DIR = paths.DATA / "lane"
SELECTION_SEEDS = [240, 241, 242, 243, 244]
CONFIRMATION_SEEDS = list(range(245, 255))
BUDGET_TOTAL = 38_000
MIN_DIST = 2.8
B_EXCL = 2.0
ARMS = ["D", "DIP", "GAP", "SOFT"]


def build_or_load_subsurface(foot, names):
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


def build_or_load_dipgap(foot, names):
    f = LANE_DIR / "dip_gap_features.npy"
    if f.exists():
        return np.load(f)
    X = np.load(paths.PREPARED_FEATURES, mmap_mode="r")
    grids = {}
    for b in ("rtp", "iso_grav_anom", "depth_to_base_surf"):
        a = np.full(grid.SHAPE, np.nan, dtype=np.float32)
        a[foot] = np.asarray(X[:, names.index(b)], dtype=np.float32)
        grids[b] = a
    T = dg.build_dip_gap_features(grids, foot)
    np.save(f, T)
    return T


def oof_for_arm(arm, foot, labels, fold, extra):
    f = LANE_DIR / f"oof_prob_h30_{arm}.npy"
    if f.exists():
        return np.load(f)
    prob = oof_detector.fit_predict_oof_probabilities(foot, labels, fold, extra=extra)
    np.save(f, prob)
    return prob


def candidates(prob, valid_scoring, known, hidden):
    d_vis = distance_transform_edt(~known)
    scope = valid_scoring | hidden
    ridge = oof_detector.ridge_nms(prob, scope)
    return ridge & scope & ~known & (d_vis > B_EXCL)


def emit_binary(prob, valid_scoring, known, hidden, budget):
    return sub.priority_poisson_disk(
        prob, candidates(prob, valid_scoring, known, hidden), MIN_DIST, budget
    )


def emit_soft(prob, valid_scoring, known, hidden, budget):
    support = sub.priority_poisson_disk(
        prob, candidates(prob, valid_scoring, known, hidden), MIN_DIST, 2 * budget
    )
    return dg.soft_rank_taper(prob, support, float(budget))


def cell_slices(split):
    rs, cs = holdout.crop(split.fold_mask, split.fold_mask)
    r0, r1 = max(rs.start - 8, 0), min(rs.stop + 8, grid.SHAPE[0])
    c0, c1 = max(cs.start - 8, 0), min(cs.stop + 8, grid.SHAPE[1])
    return (slice(r0, r1), slice(c0, c1))


def score_binary(dots, split, valid):
    sl = cell_slices(split)
    return metric.dti_binary(dots[sl].astype(float), split.hidden[sl],
                             valid=valid[sl] | split.hidden[sl], known=split.known[sl])


def score_soft(pred, split, valid):
    sl = cell_slices(split)
    out = metric.dti_exact(pred[sl].astype(float), split.hidden[sl],
                            valid=valid[sl] | split.hidden[sl], known=split.known[sl])
    out["effective_mass"] = float(pred[sl][valid[sl] | split.hidden[sl]].sum())
    return out


def pooled_dti(cells):
    tp = sum(c["TPw"] for c in cells)
    fp = sum(c["FPw"] for c in cells)
    fn = sum(c["FNw"] for c in cells)
    return tp / (tp + metric.ALPHA * fp + metric.BETA * fn + metric.EPS)


def run_cells(seeds, arms, probs, labels, fold, foot, fold_budget):
    cells = {a: [] for a in arms}
    n_withheld = 0
    for seed in seeds:
        for f in range(4):
            sp = holdout.make_split(labels, fold, f, seed=seed)
            valid = holdout.buffered_scoring_mask(sp, foot)
            n_withheld += int(sp.hidden.sum())
            for arm in arms:
                if arm == "SOFT":
                    pred = emit_soft(probs["D"], valid, sp.known, sp.hidden, int(fold_budget[f]))
                    cells[arm].append(score_soft(pred, sp, valid))
                else:
                    dots = emit_binary(probs[arm], valid, sp.known, sp.hidden, int(fold_budget[f]))
                    cells[arm].append(score_binary(dots, sp, valid))
            print(
                " ".join([f"seed {seed} fold {f}"] +
                         [f"{a}={cells[a][-1]['dti']:.4f}" for a in arms]),
                flush=True,
            )
    return cells, n_withheld


def cell_records(cells):
    return {
        a: [{k: c[k] for k in ("dti", "TPw", "FPw", "FNw", "n_truth", "n_emitted")} for c in cs]
        for a, cs in cells.items()
    }


def main() -> int:
    t0 = time.time()
    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    names = json.loads(paths.PREPARED_META.read_text())["names"]
    fold = holdout.make_quadrant_folds(foot)
    print("building transforms...", flush=True)
    t15 = build_or_load_subsurface(foot, names)
    t9 = build_or_load_dipgap(foot, names)
    print(f"transforms 15:{t15.shape} 9:{t9.shape} in {time.time() - t0:.0f}s", flush=True)

    # ---------- E1 canary (seed 240) ----------
    rng = np.random.default_rng(7)
    hidden_any = np.zeros(grid.SHAPE, bool)
    valid_any = np.zeros(grid.SHAPE, bool)
    for f in range(4):
        sp = holdout.make_split(labels, fold, f, seed=SELECTION_SEEDS[0])
        hidden_any |= sp.hidden
        valid_any |= holdout.buffered_scoring_mask(sp, foot)
    y = hidden_any[foot]
    idx_scope = np.flatnonzero((valid_any | hidden_any)[foot])
    pos = idx_scope[y[idx_scope]]
    neg = idx_scope[~y[idx_scope]]
    neg_s = rng.choice(neg, size=min(200_000, len(neg)), replace=False)
    yv = np.r_[np.ones(len(pos)), np.zeros(len(neg_s))]
    canary = {}
    for j, nm in enumerate(dg.NEW_FEATURE_NAMES):
        col = t9[:, j]
        auc = float(roc_auc_score(yv, np.r_[col[pos], col[neg_s]]))
        canary[nm] = {"auc": auc, "auc_direction_invariant": max(auc, 1.0 - auc)}
        print(f"canary {nm}: AUC {auc:.4f}", flush=True)
    leak = {k: v for k, v in canary.items() if v["auc_direction_invariant"] > 0.90}
    print("CANARY leak flags (direction-invariant >0.90):", leak or "none", flush=True)
    if leak:
        dest = paths.EVIDENCE / "h30_dipgap_holdout.json"
        dest.write_text(json.dumps({
            "experiment": "H30 lane holdout (E1 canary STOP)",
            "preregistration": "knowledge/20_lane_h30_preregistration_2026-10-25.md",
            "evaluator": "gems27.metric v1 (alpha=0.2, beta=0.8, R=3px triangular)",
            "label": "HOLDOUT-DTI (catalogue-internal hide-and-recover; NOT a live score)",
            "canary_auc": canary, "canary_leak_flags": leak,
            "gate_efficacy_pass": False,
            "runtime_s": round(time.time() - t0, 1),
        }, indent=2) + "\n")
        print("STOP: leakage canary failed; verdict negative.")
        return 0

    # ---------- OOF surfaces + surface uniqueness pre-check ----------
    probs = {}
    probs["D"] = oof_for_arm("D", foot, labels, fold, t15)
    print(f"OOF D done {time.time() - t0:.0f}s", flush=True)
    dip_extra = np.concatenate([t15, t9[:, : len(dg.DIP_NAMES)]], axis=1).astype(np.float32)
    probs["DIP"] = oof_for_arm("DIP", foot, labels, fold, dip_extra)
    del dip_extra
    print(f"OOF DIP done {time.time() - t0:.0f}s", flush=True)
    gap_extra = np.concatenate([t15, t9[:, len(dg.DIP_NAMES):]], axis=1).astype(np.float32)
    probs["GAP"] = oof_for_arm("GAP", foot, labels, fold, gap_extra)
    del gap_extra
    print(f"OOF GAP done {time.time() - t0:.0f}s", flush=True)

    sample = np.random.default_rng(7).choice(
        np.flatnonzero(foot.ravel()), size=300_000, replace=False
    )
    surf_corr = {}
    for rp in sorted((paths.DATA / "parallel_registry").glob("*.tif")):
        with rasterio.open(rp) as s:
            a = s.read(1)
        vals = np.where(np.isfinite(a), a, 0.0).astype(np.float32)
        dens = gaussian_filter((np.isfinite(a) & (a > 0)).astype(np.float32), 3.0)
        surf_corr[rp.name] = {}
        for arm in ("D", "DIP", "GAP"):
            p = probs[arm].ravel()[sample]
            surf_corr[rp.name][arm] = {
                "vs_raster_value": float(spearmanr(p, vals.ravel()[sample]).statistic),
                "vs_density_sigma3": float(spearmanr(p, dens.ravel()[sample]).statistic),
            }
        del a, vals, dens
        print("surface Spearman", rp.name, surf_corr[rp.name], flush=True)

    fold_share = np.array([(fold == f).sum() for f in range(4)], float)
    fold_budget = np.round(BUDGET_TOTAL * fold_share / fold_share.sum()).astype(int)

    # ---------- E2a selection ----------
    sel_cells, sel_withheld = run_cells(
        SELECTION_SEEDS, ARMS, probs, labels, fold, foot, fold_budget
    )
    sel_pooled = {a: pooled_dti(c) for a, c in sel_cells.items()}
    print("SELECTION pooled HOLDOUT-DTI:", sel_pooled, flush=True)
    contenders = ["DIP", "GAP", "SOFT"]
    selected = max(contenders, key=lambda a: sel_pooled[a])
    if not sel_pooled[selected] > sel_pooled["D"]:
        selected = None
    print("SELECTED:", selected, flush=True)

    # ---------- E2b confirmation ----------
    conf = None
    if selected is not None:
        conf_cells, conf_withheld = run_cells(
            CONFIRMATION_SEEDS, ["D", selected], probs, labels, fold, foot, fold_budget
        )
        conf_pooled = {a: pooled_dti(c) for a, c in conf_cells.items()}
        d = np.array([a["dti"] - b["dti"]
                      for a, b in zip(conf_cells[selected], conf_cells["D"])])
        bs = np.random.default_rng(11)
        means = [bs.choice(d, size=len(d), replace=True).mean() for _ in range(2000)]
        paired = {
            "mean_delta": float(d.mean()),
            "ci95": [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))],
            "cells_positive": int((d > 0).sum()),
            "n_cells": int(len(d)),
            "folds_positive": int(sum(
                d.reshape(len(CONFIRMATION_SEEDS), 4).mean(axis=0) > 0)),
            "seeds_positive": int(sum(
                d.reshape(len(CONFIRMATION_SEEDS), 4).mean(axis=1) > 0)),
            "fold_mean_delta": {
                holdout.FOLD_NAMES[i]: float(v)
                for i, v in enumerate(d.reshape(len(CONFIRMATION_SEEDS), 4).mean(axis=0))
            },
        }
        gate_efficacy = bool(
            conf_pooled[selected] > conf_pooled["D"]
            and paired["mean_delta"] >= 0.0015
            and paired["ci95"][0] > 0
            and paired["cells_positive"] >= 24
            and paired["folds_positive"] >= 3
        )
        conf = {
            "seeds": CONFIRMATION_SEEDS,
            "n_withheld_positives_total": int(conf_withheld),
            "pooled_holdout_dti": {selected: conf_pooled[selected], "D_control": conf_pooled["D"]},
            "pooled_candidate": conf_pooled[selected],
            "pooled_control_D": conf_pooled["D"],
            "paired_candidate_minus_D": paired,
            "gate_efficacy_pass": gate_efficacy,
            "per_cell": cell_records(conf_cells),
        }
        print("CONFIRMATION pooled:", conf["pooled_holdout_dti"],
              "| paired:", paired, "| gate:", gate_efficacy, flush=True)
    else:
        gate_efficacy = False

    out = {
        "experiment": "H30 lane holdout (E1+E2a+E2b)",
        "preregistration": "knowledge/20_lane_h30_preregistration_2026-10-25.md (commit d87283f)",
        "evaluator": "gems27.metric v1 (alpha=0.2, beta=0.8, R=3px triangular)",
        "label": "HOLDOUT-DTI (catalogue-internal hide-and-recover; NOT a live score)",
        "folds": holdout.FOLD_NAMES,
        "budget_per_fold": fold_budget.tolist(), "min_dist_px": MIN_DIST,
        "b_exclusion_px": B_EXCL,
        "canary_auc": canary, "canary_leak_flags": leak,
        "canary_max_auc": max(v["auc"] for v in canary.values()),
        "canary_max_auc_direction_invariant": max(
            v["auc_direction_invariant"] for v in canary.values()),
        "surface_spearman_vs_registry": surf_corr,
        "selection": {
            "seeds": SELECTION_SEEDS,
            "n_withheld_positives_total": int(sel_withheld),
            "pooled_holdout_dti": sel_pooled,
            "selected_candidate": selected,
            "per_cell": cell_records(sel_cells),
        },
        "confirmation": conf,
        "gate_efficacy_pass": bool(gate_efficacy),
        "runtime_s": round(time.time() - t0, 1),
    }
    dest = paths.EVIDENCE / "h30_dipgap_holdout.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
