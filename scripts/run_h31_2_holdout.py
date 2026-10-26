#!/usr/bin/env python3
"""Frozen E1+E2 runner for Hypothesis H31-2 (Lane L-S11-2026-10-26).

Preregistered in ``knowledge/26_preregistration_H31-2_2026-10-26.md`` before seeds 410-419 ran:
- E1: direction-invariant ROC-AUC leakage canary (<=0.90) for the 8 demagnetization features on
  the union of withheld positives for seeds 410-419, then a pre-placement surface Spearman
  screen (<=0.90) of the DEMAG OOF surface vs the 12 pinned peers, both scored GEMSDOE27 files
  and the promoted H31-1 file.
- E2: paired 40-cell buffered spatial holdout (buffer 6 px) for arms U0 / H31S / STK0 / DEMAG,
  all emitted with the identical frozen ``emit_h31_celf`` (B2, min-sep 2.8 px, 37,654 budget).
Reuses the template's H31 quadrant-OOF builders from ``scripts/run_h31_s10_holdout.py``
(no private fork of the evaluator: scoring goes through ``gems27.metric.dti_binary``).
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
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import rasterio
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

import run_h31_s10_holdout as s10
from gems27 import demagnetization as demag
from gems27 import geothermal_conduit_nis as h31
from gems27 import grid, holdout, metric, paths
from gems27 import hydrothermal_piedmont as h29

SEEDS: list[int] = list(range(410, 420))
BUDGET_TOTAL: int = 37_654
CACHE_DIR = paths.DATA / "h31_2"
S10_CACHE = paths.DATA / "h31"
PREREG_PATH = paths.REPO / "knowledge" / "26_preregistration_H31-2_2026-10-26.md"
EVALUATOR = (
    "gems27.metric v1 + holdout-blind-buffered-v2 "
    "(alpha=0.2, beta=0.8, R=3px triangular, buffer_px=6.0)"
)
H31_1_FILE = (
    paths.DOCS
    / "downloads"
    / "gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif"
)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _canary_auc(vals_pos: np.ndarray, vals_neg: np.ndarray) -> tuple[float, float]:
    v = np.r_[vals_pos.astype(np.float64), vals_neg.astype(np.float64)]
    y = np.r_[np.ones(vals_pos.size, dtype=np.int8), np.zeros(vals_neg.size, dtype=np.int8)]
    ok = np.isfinite(v)
    if ok.sum() < 10 or y[ok].min() == y[ok].max():
        return 0.5, 0.5
    raw = float(roc_auc_score(y[ok], v[ok]))
    return raw, float(max(raw, 1.0 - raw))


def get_demag_X() -> np.ndarray:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return demag.build_demag_feature_matrix(cache_path=CACHE_DIR / "demag_features.npy")


def run_e1() -> int:
    t0 = time.time()
    foot, labels, _lid, _names = s10.load_base()
    fold = holdout.make_quadrant_folds(foot)
    print("building/loading 8 demagnetization features...", flush=True)
    demag_X = get_demag_X()

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
    rng = np.random.default_rng(410)
    neg_idx = rng.choice(neg_all, size=min(250_000, neg_all.size), replace=False)

    canary: dict[str, dict[str, float]] = {}
    for j, nm in enumerate(demag.DEMAG_FEATURE_NAMES):
        raw, di = _canary_auc(np.asarray(demag_X[pos_idx, j]), np.asarray(demag_X[neg_idx, j]))
        canary[nm] = {"raw_auc": round(raw, 5), "direction_invariant_auc": round(di, 5)}
        print(f"  canary {nm:28s}: raw={raw:.4f} dir_inv={di:.4f}", flush=True)

    max_auc = max(d["direction_invariant_auc"] for d in canary.values())
    leak_flags = {k: d["direction_invariant_auc"] for k, d in canary.items()
                  if d["direction_invariant_auc"] > 0.90}
    gate = (len(leak_flags) == 0) and (max_auc <= 0.90)
    out = {
        "experiment": "E1_H31-2_leakage_canary",
        "lane": "L-S11-2026-10-26",
        "hypothesis_id": "H31-2",
        "preregistration_doc": str(PREREG_PATH.relative_to(paths.REPO)),
        "preregistration_sha256": sha256_file(PREREG_PATH),
        "evaluator_version": EVALUATOR,
        "provenance_label": "HOLDOUT-DTI canary (catalogue-internal; NOT a live organizer score)",
        "seeds": SEEDS,
        "n_withheld_positive_pixels_union": int(pos_idx.size),
        "n_negative_sample": int(neg_idx.size),
        "canary_demag_features": canary,
        "max_direction_invariant_auc": round(max_auc, 5),
        "auc_stop_threshold": 0.90,
        "leakage_flags": leak_flags,
        "gate_e1_canary_pass": bool(gate),
        "runtime_s": round(time.time() - t0, 1),
    }
    dest = paths.EVIDENCE / "h31_2_e1_canary.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print(f"E1 CANARY PASS={gate} | max_AUC={max_auc:.4f} | wrote {dest}", flush=True)
    return 0 if gate else 2


def get_surfaces() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return (p_sub, p_s1, p_s2, prob_stk0, prob_demag), fitting/caching as needed."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    foot, labels, lid_valid, names = s10.load_base()
    base_X = np.load(paths.PREPARED_FEATURES, mmap_mode="r")
    sub15_X = s10.get_or_build_subsurface15(foot, names)
    h29_X = h29.build_h29_feature_matrix(cache_path=S10_CACHE / "h29_features.npy")
    h31_X = h31.build_h31_feature_matrix(cache_path=S10_CACHE / "h31_features.npy")
    p_sub, p_s1, p_s2 = s10.get_or_fit_h31_quad_oof(
        base_X, sub15_X, h29_X, h31_X, labels, foot, lid_valid
    )
    del base_X, sub15_X, h29_X, h31_X
    gc.collect()

    stk_p = CACHE_DIR / "prob_stk0_quad.npy"
    dem_p = CACHE_DIR / "prob_demag_quad.npy"
    if stk_p.exists():
        prob_stk = np.load(stk_p)
    else:
        print("fitting STK0 recalibration stacker [p_s2,p_s1,p_sub]...", flush=True)
        prob_stk = demag.fit_predict_stacker_oof(
            (p_s2, p_s1, p_sub), None, labels, foot, seed=410
        )
        np.save(stk_p, prob_stk)
    if dem_p.exists():
        prob_dem = np.load(dem_p)
    else:
        print("fitting DEMAG stacker [p_s2,p_s1,p_sub]+demag8...", flush=True)
        prob_dem = demag.fit_predict_stacker_oof(
            (p_s2, p_s1, p_sub), get_demag_X(), labels, foot, seed=411
        )
        np.save(dem_p, prob_dem)
    return p_sub, p_s1, p_s2, prob_stk, prob_dem


def surface_screen(prob_dem: np.ndarray, foot: np.ndarray) -> dict:
    rng = np.random.default_rng(410)
    sample_flat = rng.choice(np.flatnonzero(foot.ravel()), size=400_000, replace=False)
    surf = prob_dem.ravel()[sample_flat]
    entries: dict[str, float] = {}
    reg_dir = paths.DATA / "parallel_registry"
    for p in sorted(reg_dir.glob("*.tif")):
        with rasterio.open(p) as ds:
            arr = np.nan_to_num(ds.read(1), nan=0.0).ravel()[sample_flat]
        rho, _ = spearmanr(surf, arr)
        entries[f"peer:{p.name}"] = round(float(0.0 if np.isnan(rho) else rho), 5)
    assert sum(k.startswith("peer:") for k in entries) == 12, "expected 12 peer rasters"
    scored = {
        "scored:slot1_5512495c6bd1": (
            paths.DOCS / "downloads"
            / "gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-allfinite.tif"
        ),
        "scored:h29s_511898747886": (
            paths.DOCS / "downloads"
            / "gems27-h29-hydrothermal-piedmont-celf-20261025-511898747886-allfinite.tif"
        ),
        "promoted:h31_1_cf8e1bbef244": H31_1_FILE,
    }
    for k, p in scored.items():
        with rasterio.open(p) as ds:
            arr = np.nan_to_num(ds.read(1), nan=0.0).ravel()[sample_flat]
        rho, _ = spearmanr(surf, arr)
        entries[k] = round(float(0.0 if np.isnan(rho) else rho), 5)
    max_abs = float(max(abs(v) for v in entries.values()))
    return {
        "preplacement_surface_spearman": entries,
        "max_abs_preplacement_spearman": round(max_abs, 5),
        "spearman_stop_threshold": 0.90,
        "gate_surface_pass": bool(max_abs <= 0.90),
    }


def score_cell(dots: np.ndarray, sp: holdout.Split, valid_mask: np.ndarray) -> dict:
    rs, cs = holdout.crop(dots, sp.fold_mask)
    r0, r1 = max(rs.start - 8, 0), min(rs.stop + 8, grid.SHAPE[0])
    c0, c1 = max(cs.start - 8, 0), min(cs.stop + 8, grid.SHAPE[1])
    sl = (slice(r0, r1), slice(c0, c1))
    return metric.dti_binary(
        dots[sl].astype(float), sp.hidden[sl],
        valid=valid_mask[sl] | sp.hidden[sl], known=sp.known[sl],
    )


def pooled_dti(cells: list[dict]) -> float:
    tp = sum(c["TPw"] for c in cells)
    fp = sum(c["FPw"] for c in cells)
    fn = sum(c["FNw"] for c in cells)
    return float(tp / (tp + metric.ALPHA * fp + metric.BETA * fn + metric.EPS))


def seed_bootstrap_ci(cells: list[dict], n_boot: int = 10_000) -> list[float]:
    n = len(SEEDS)
    vals = np.array([pooled_dti(cells[4 * i : 4 * (i + 1)]) for i in range(n)])
    rng = np.random.default_rng(20261026)
    idx = rng.integers(0, n, size=(n_boot, n))
    means = vals[idx].mean(axis=1)
    return [round(float(np.percentile(means, 2.5)), 6),
            round(float(np.percentile(means, 97.5)), 6)]


def paired(cand: list[dict], base: list[dict], n_boot: int = 10_000) -> dict:
    n = len(SEEDS)
    sc = np.array([pooled_dti(cand[4 * i : 4 * (i + 1)]) for i in range(n)])
    sb = np.array([pooled_dti(base[4 * i : 4 * (i + 1)]) for i in range(n)])
    deltas = sc - sb
    rng = np.random.default_rng(20261026)
    idx = rng.integers(0, n, size=(n_boot, n))
    boot = deltas[idx].mean(axis=1)
    cell_d = np.array([a["dti"] - b["dti"] for a, b in zip(cand, base, strict=True)])
    per_fold: dict[str, float] = {}
    wins = 0
    for f, fnm in enumerate(holdout.FOLD_NAMES):
        fd = pooled_dti([cand[4 * i + f] for i in range(n)]) - pooled_dti(
            [base[4 * i + f] for i in range(n)])
        per_fold[fnm] = round(float(fd), 6)
        wins += int(fd > 0)
    ci = [round(float(np.percentile(boot, 2.5)), 6), round(float(np.percentile(boot, 97.5)), 6)]
    return {
        "pooled_delta_dti": round(float(pooled_dti(cand) - pooled_dti(base)), 6),
        "mean_delta": round(float(deltas.mean()), 6),
        "mean_seed_paired_delta_dti": round(float(deltas.mean()), 6),
        "ci95": ci,
        "seed_bootstrap_95_ci": ci,
        "positive_seeds": int((deltas > 0).sum()),
        "n_seeds": n,
        "positive_folds": wins,
        "n_folds": 4,
        "per_fold_pooled_delta_dti": per_fold,
        "positive_cells": int((cell_d > 0).sum()),
        "n_cells": int(cell_d.size),
    }


def run_e2() -> int:
    t0 = time.time()
    e1_path = paths.EVIDENCE / "h31_2_e1_canary.json"
    if not e1_path.exists():
        rc = run_e1()
        if rc != 0:
            return rc
    e1 = json.loads(e1_path.read_text())
    if not e1["gate_e1_canary_pass"]:
        print("E1 canary failed; refusing to run E2.", flush=True)
        return 2

    foot, labels, _lid, _names = s10.load_base()
    fold = holdout.make_quadrant_folds(foot)
    _p_sub, _p_s1, p_s2, prob_stk, prob_dem = get_surfaces()

    screen = surface_screen(prob_dem, foot)
    screen_path = paths.EVIDENCE / "h31_2_e1b_surface.json"
    screen_path.write_text(json.dumps({
        "experiment": "E1b_H31-2_preplacement_surface_screen",
        "lane": "L-S11-2026-10-26",
        "hypothesis_id": "H31-2",
        "preregistration_doc": str(PREREG_PATH.relative_to(paths.REPO)),
        "preregistration_sha256": sha256_file(PREREG_PATH),
        **screen,
    }, indent=2) + "\n")
    print(f"SURFACE SCREEN pass={screen['gate_surface_pass']} "
          f"max|rho|={screen['max_abs_preplacement_spearman']}", flush=True)
    if not screen["gate_surface_pass"]:
        print("Surface screen failed (lane drift); stopping before placement.", flush=True)
        return 2

    fold_share = np.array([(fold == f).sum() for f in range(4)], dtype=np.float64)
    fold_budget = np.round(BUDGET_TOTAL * fold_share / fold_share.sum()).astype(int)
    fold_budget[int(np.argmax(fold_share))] += BUDGET_TOTAL - int(fold_budget.sum())
    assert int(fold_budget.sum()) == BUDGET_TOTAL

    arms = ["U0", "H31S", "STK0", "DEMAG"]
    cells_buf: dict[str, list[dict]] = {a: [] for a in arms}
    cells_unbuf: dict[str, list[dict]] = {a: [] for a in arms}
    n_withheld = 0
    for seed in SEEDS:
        t_seed = time.time()
        for f in range(4):
            sp = holdout.make_split(labels, fold, f, seed=seed)
            fold_domain = foot & sp.fold_mask
            valid_buf = holdout.buffered_scoring_mask(sp, foot, buffer_px=6.0)
            b_f = int(fold_budget[f])
            n_withheld += int(sp.hidden.sum())
            emitted = {
                "U0": s10.emit_uniform(fold_domain, sp.known, b_f,
                                       np.random.default_rng(seed * 100 + f)),
                "H31S": h31.emit_h31_celf(p_s2, fold_domain, sp.known, b_f),
                "STK0": h31.emit_h31_celf(prob_stk, fold_domain, sp.known, b_f),
                "DEMAG": h31.emit_h31_celf(prob_dem, fold_domain, sp.known, b_f),
            }
            for a, dots in emitted.items():
                assert not (dots & ~fold_domain).any(), f"{a} emitted outside fold_domain!"
                assert not (dots & sp.known).any(), f"{a} overlapped known catalogue!"
                cells_buf[a].append(score_cell(dots, sp, valid_buf))
                cells_unbuf[a].append(score_cell(dots, sp, fold_domain))
        print(f"seed {seed} ({time.time() - t_seed:.1f}s) buffered pooled: "
              + " ".join(f"{a}={pooled_dti(cells_buf[a][-4:]):.4f}" for a in arms), flush=True)

    pooled_buf = {a: round(pooled_dti(cells_buf[a]), 6) for a in arms}
    pooled_unbuf = {a: round(pooled_dti(cells_unbuf[a]), 6) for a in arms}
    ci_buf = {a: seed_bootstrap_ci(cells_buf[a]) for a in arms}
    per_fold = {
        fnm: {a: round(pooled_dti([cells_buf[a][4 * i + f] for i in range(len(SEEDS))]), 6)
              for a in arms}
        for f, fnm in enumerate(holdout.FOLD_NAMES)
    }
    per_seed = {
        str(seed): {a: round(pooled_dti(cells_buf[a][4 * i : 4 * (i + 1)]), 6) for a in arms}
        for i, seed in enumerate(SEEDS)
    }
    comps = {
        "DEMAG_minus_H31S": paired(cells_buf["DEMAG"], cells_buf["H31S"]),
        "DEMAG_minus_STK0": paired(cells_buf["DEMAG"], cells_buf["STK0"]),
        "STK0_minus_H31S": paired(cells_buf["STK0"], cells_buf["H31S"]),
        "DEMAG_minus_U0": paired(cells_buf["DEMAG"], cells_buf["U0"]),
    }
    vs_h31 = comps["DEMAG_minus_H31S"]
    vs_stk = comps["DEMAG_minus_STK0"]
    clauses = {
        "a_pooled_beats_H31S_and_STK0": bool(
            pooled_buf["DEMAG"] > pooled_buf["H31S"] and pooled_buf["DEMAG"] > pooled_buf["STK0"]),
        "b_mean_paired_vs_H31S_ge_0p0010": bool(vs_h31["mean_delta"] >= 0.0010),
        "c_ci95_lower_gt_zero_vs_H31S_and_STK0": bool(
            vs_h31["ci95"][0] > 0.0 and vs_stk["ci95"][0] > 0.0),
        "d_folds_ge_3_of_4_vs_H31S": bool(vs_h31["positive_folds"] >= 3),
        "e_seeds_ge_8_of_10_vs_H31S": bool(vs_h31["positive_seeds"] >= 8),
        "f_e1_pass": bool(e1["gate_e1_canary_pass"] and screen["gate_surface_pass"]),
    }
    gate = all(clauses.values())
    out = {
        "experiment": "E2_H31-2_paired_spatial_holdout",
        "lane": "L-S11-2026-10-26",
        "hypothesis_id": "H31-2",
        "preregistration_doc": str(PREREG_PATH.relative_to(paths.REPO)),
        "preregistration_sha256": sha256_file(PREREG_PATH),
        "evaluator_version": EVALUATOR,
        "provenance_label": (
            "HOLDOUT-DTI (catalogue-internal whole-component hide-and-recover; "
            "NOT a live organizer score)"
        ),
        "seeds": SEEDS,
        "folds": holdout.FOLD_NAMES,
        "n_cells": 4 * len(SEEDS),
        "n_withheld_positive_occurrences": n_withheld,
        "matched_full_map_budget": BUDGET_TOTAL,
        "fold_budgets": fold_budget.tolist(),
        "b_exclusion_px": 2.0,
        "celf_params": {"gamma": h31.CELF_GAMMA, "min_sep_px": h31.CELF_MIN_SEP_PX},
        "pooled_buffered_holdout_dti": pooled_buf,
        "pooled_buffered_ci95": ci_buf,
        "pooled_unbuffered_diagnostic_holdout_dti": pooled_unbuf,
        "per_fold_buffered_holdout_dti": per_fold,
        "per_seed_buffered_holdout_dti": per_seed,
        "paired_comparisons_buffered": comps,
        "frozen_gate_clauses": clauses,
        "gate_e2_pass": bool(gate),
        "verdict_stage_e2": "promote" if gate else "negative",
        "runtime_s": round(time.time() - t0, 1),
    }
    dest = paths.EVIDENCE / "h31_2_e2_holdout_410_419.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print("POOLED BUFFERED HOLDOUT-DTI:", json.dumps(pooled_buf), flush=True)
    print("POOLED UNBUFFERED:", json.dumps(pooled_unbuf), flush=True)
    print("VS H31S:", json.dumps(vs_h31), flush=True)
    print("VS STK0:", json.dumps(vs_stk), flush=True)
    print("GATE CLAUSES:", json.dumps(clauses), flush=True)
    print(f"E2 PASS={gate} | wrote {dest}", flush=True)
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
