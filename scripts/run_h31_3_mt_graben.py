#!/usr/bin/env python3
"""E1/E2 for frozen H31-3 MT clay-cap × asymmetric basement-margin coupling.

Preregistration: ``knowledge/28_preregistration_H31-3_mt_graben_2026-10-26.md`` at
commit 83ceee5, before this runner and its feature module were written. The candidate appends
eight label-free, signed cross-strike features to the shared H31 dual-regime template and is
compared only with the exact H31-S control under identical blinded emissions. Every performance
number written by this script is HOLDOUT-DTI, never a live organizer score.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import run_h31_s10_holdout as h31_base  # noqa: E402
from gems27 import geothermal_conduit_nis as h31  # noqa: E402
from gems27 import grid, holdout, metric, mt_graben, paths  # noqa: E402
from gems27 import hydrothermal_piedmont as h29  # noqa: E402

SEEDS = list(range(510, 520))
BUDGET_TOTAL = 37_654
B_EXCL = 2.0
CACHE_DIR = paths.DATA / "h313_mt_graben"
PREREG = ROOT / "knowledge" / "28_preregistration_H31-3_mt_graben_2026-10-26.md"
E1_PATH = paths.EVIDENCE / "h31_3_e1_canary_and_surface_510_519.json"
E2_PATH = paths.EVIDENCE / "h31_3_e2_holdout_510_519.json"


def sha256_file(path: Path) -> str:
    return hashlib.file_digest(path.open("rb"), "sha256").hexdigest()


def _feature_grids(foot: np.ndarray, names: list[str]) -> dict[str, np.ndarray]:
    X = np.load(paths.PREPARED_FEATURES, mmap_mode="r")
    out: dict[str, np.ndarray] = {}
    for name in mt_graben.REQUIRED_BANDS:
        a = np.full(grid.SHAPE, np.nan, dtype=np.float32)
        a[foot] = np.asarray(X[:, names.index(name)], dtype=np.float32)
        out[name] = a
    return out


def get_or_build_mt(foot: np.ndarray, names: list[str]) -> np.ndarray:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    dest = CACHE_DIR / "mt_graben_features.npy"
    if dest.exists():
        a = np.load(dest, mmap_mode="r")
        if a.shape == (int(foot.sum()), len(mt_graben.TRANSFORM_NAMES)) and np.isfinite(a).all():
            return a
        dest.unlink()
    grids = _feature_grids(foot, names)
    try:
        arr = mt_graben.build_transforms(grids, foot)
    finally:
        del grids
        gc.collect()
    np.save(dest, arr)
    del arr
    gc.collect()
    return np.load(dest, mmap_mode="r")


def load_common():
    foot, labels, lid_valid, names = h31_base.load_base()
    base_X = np.load(paths.PREPARED_FEATURES, mmap_mode="r")
    sub15_X = h31_base.get_or_build_subsurface15(foot, names)
    h29_X = h29.build_h29_feature_matrix(cache_path=h31_base.CACHE_DIR / "h29_features.npy")
    h31_X = h31.build_h31_feature_matrix(cache_path=h31_base.CACHE_DIR / "h31_features.npy")
    mt_X = get_or_build_mt(foot, names)
    return foot, labels, lid_valid, names, base_X, sub15_X, h29_X, h31_X, mt_X


def candidate_oof(
    base_X, sub15_X, h29_X, h31_X, mt_X, labels, foot, lid_valid, *,
    cache_tag: str, seed: int = 510, fold_masks: list[np.ndarray] | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    return h31_base.get_or_fit_h31_quad_oof(
        base_X, sub15_X, h29_X, h31_X, labels, foot, lid_valid,
        cache_dir=CACHE_DIR, cache_tag=cache_tag, seed=seed, extra_physics=mt_X,
        extra_mmap_path=CACHE_DIR / "mt_graben_features.npy", fold_masks=fold_masks,
    )


def _canary(vals_pos: np.ndarray, vals_neg: np.ndarray) -> tuple[float, float]:
    v = np.r_[vals_pos.astype(np.float64), vals_neg.astype(np.float64)]
    y = np.r_[np.ones(vals_pos.size, dtype=np.uint8), np.zeros(vals_neg.size, dtype=np.uint8)]
    finite = np.isfinite(v)
    raw = float(roc_auc_score(y[finite], v[finite]))
    return raw, max(raw, 1.0 - raw)


def _surface_spearman(surface: np.ndarray, foot: np.ndarray) -> dict[str, float]:
    rng = np.random.default_rng(510)
    sample = rng.choice(np.flatnonzero(foot.ravel()), size=min(400_000, int(foot.sum())), replace=False)
    s = surface.ravel()[sample]
    ans: dict[str, float] = {}
    for path in sorted((paths.DATA / "parallel_registry").glob("*.tif")):
        with rasterio.open(path) as ds:
            ref = np.nan_to_num(ds.read(1), nan=0.0).ravel()[sample]
        rho = float(spearmanr(s, ref).statistic)
        ans[path.stem] = 0.0 if not np.isfinite(rho) else rho
    if len(ans) != 12:
        raise RuntimeError(f"parallel registry incomplete: expected 12 rasters, got {len(ans)}")
    return ans


def run_e1() -> int:
    t0 = time.time()
    foot, labels, lid_valid, _, base_X, sub15_X, h29_X, h31_X, mt_X = load_common()
    fold = holdout.make_quadrant_folds(foot)
    hidden_any = np.zeros_like(labels)
    valid_any = np.zeros_like(labels)
    for seed in SEEDS:
        for f in range(4):
            split = holdout.make_split(labels, fold, f, seed=seed)
            hidden_any |= split.hidden
            valid_any |= holdout.buffered_scoring_mask(split, foot, buffer_px=6.0)

    scope = (hidden_any | valid_any)[foot]
    y = hidden_any[foot]
    scope_i = np.flatnonzero(scope)
    pos = scope_i[y[scope_i]]
    neg_all = scope_i[~y[scope_i]]
    neg = np.random.default_rng(510).choice(neg_all, size=min(250_000, neg_all.size), replace=False)
    canary = {}
    for j, name in enumerate(mt_graben.TRANSFORM_NAMES):
        raw, direction_invariant = _canary(np.asarray(mt_X[pos, j]), np.asarray(mt_X[neg, j]))
        canary[name] = {"raw_auc": raw, "direction_invariant_auc": direction_invariant}
    canary_max = max(v["direction_invariant_auc"] for v in canary.values())
    leakage_flags = {k: v for k, v in canary.items() if v["direction_invariant_auc"] > 0.90}

    _, _, surface = candidate_oof(base_X, sub15_X, h29_X, h31_X, mt_X, labels, foot, lid_valid, cache_tag="quad")
    rho = _surface_spearman(surface, foot)
    max_abs_rho = max(abs(v) for v in rho.values())
    pass_e1 = not leakage_flags and canary_max <= 0.90 and max_abs_rho <= 0.90
    out = {
        "experiment": "E1 H31-3 MT-graben leakage canary and pre-placement surface uniqueness",
        "preregistration": str(PREREG.relative_to(ROOT)),
        "preregistration_sha256": sha256_file(PREREG),
        "label": "HOLDOUT-DTI setup only; no organizer score",
        "seeds": SEEDS,
        "n_hidden_positive_union": int(pos.size),
        "n_negative_sample": int(neg.size),
        "canary_new_features": canary,
        "canary_max_direction_invariant_auc": canary_max,
        "leakage_flags": leakage_flags,
        "preplacement_surface_spearman_vs_12_peer_rasters": rho,
        "max_abs_preplacement_surface_spearman": max_abs_rho,
        "thresholds": {"canary_auc_max": 0.90, "surface_spearman_abs_max": 0.90},
        "gate_e1_pass": pass_e1,
        "runtime_s": round(time.time() - t0, 1),
    }
    E1_PATH.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({"canary_max": canary_max, "max_abs_surface_rho": max_abs_rho,
                      "flags": leakage_flags, "pass": pass_e1, "evidence": str(E1_PATH)}, indent=2))
    return 0 if pass_e1 else 2


def pooled(cells: list[dict]) -> float:
    tp = sum(c["TPw"] for c in cells)
    fp = sum(c["FPw"] for c in cells)
    fn = sum(c["FNw"] for c in cells)
    return float(tp / (tp + metric.ALPHA * fp + metric.BETA * fn + metric.EPS))


def paired(candidate: list[dict], control: list[dict]) -> dict:
    cand_seed = np.array([pooled(candidate[i * 4:(i + 1) * 4]) for i in range(len(SEEDS))])
    ctrl_seed = np.array([pooled(control[i * 4:(i + 1) * 4]) for i in range(len(SEEDS))])
    delta = cand_seed - ctrl_seed
    rng = np.random.default_rng(20261026)
    bs = delta[rng.integers(0, len(delta), size=(10_000, len(delta)))].mean(axis=1)
    per_fold = {}
    for f, name in enumerate(holdout.FOLD_NAMES):
        per_fold[name] = pooled([candidate[4 * i + f] for i in range(len(SEEDS))]) - pooled(
            [control[4 * i + f] for i in range(len(SEEDS))]
        )
    return {
        "pooled_delta_dti": float(pooled(candidate) - pooled(control)),
        "mean_seed_paired_delta_dti": float(delta.mean()),
        "ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
        "positive_seeds": int((delta > 0).sum()), "n_seeds": len(SEEDS),
        "positive_folds": int(sum(v > 0 for v in per_fold.values())), "n_folds": 4,
        "per_seed_pooled_delta_dti": delta.tolist(),
        "per_fold_pooled_delta_dti": per_fold,
    }


def score(dots: np.ndarray, split: holdout.HoldoutSplit, valid: np.ndarray) -> dict:
    rs, cs = holdout.crop(dots, split.fold_mask)
    r0, r1 = max(rs.start - 8, 0), min(rs.stop + 8, grid.SHAPE[0])
    c0, c1 = max(cs.start - 8, 0), min(cs.stop + 8, grid.SHAPE[1])
    sl = (slice(r0, r1), slice(c0, c1))
    return metric.dti_binary(
        dots[sl].astype(float), split.hidden[sl], valid=valid[sl] | split.hidden[sl], known=split.known[sl]
    )


def run_e2() -> int:
    if not E1_PATH.exists():
        code = run_e1()
        if code:
            return code
    e1 = json.loads(E1_PATH.read_text())
    if not e1["gate_e1_pass"]:
        print("E1 failed; refusing to spend the preregistered E2 seeds.")
        return 2
    t0 = time.time()
    foot, labels, lid_valid, _, base_X, sub15_X, h29_X, h31_X, mt_X = load_common()
    fold = holdout.make_quadrant_folds(foot)
    _, _, control_surface = h31_base.get_or_fit_h31_quad_oof(
        base_X, sub15_X, h29_X, h31_X, labels, foot, lid_valid
    )
    _, _, candidate_surface = candidate_oof(
        base_X, sub15_X, h29_X, h31_X, mt_X, labels, foot, lid_valid, cache_tag="quad"
    )
    shares = np.array([(fold == f).sum() for f in range(4)], dtype=float)
    budgets = np.rint(BUDGET_TOTAL * shares / shares.sum()).astype(int)
    budgets[-1] += BUDGET_TOTAL - int(budgets.sum())
    arms = {"H31-S": control_surface, "H31-3-S": candidate_surface}
    cells = {name: [] for name in arms}
    n_withheld = 0
    for seed in SEEDS:
        for f in range(4):
            split = holdout.make_split(labels, fold, f, seed=seed)
            domain = foot & split.fold_mask
            valid = holdout.buffered_scoring_mask(split, foot, buffer_px=6.0)
            n_withheld += int(split.hidden.sum())
            for name, surface in arms.items():
                dots = h31.emit_h31_celf(surface, domain, split.known, int(budgets[f]), b_excl=B_EXCL)
                if (dots & ~domain).any() or (dots & split.known).any():
                    raise AssertionError(f"{name} emitter observed outside its blind domain")
                cells[name].append(score(dots, split, valid))
        print(f"seed {seed}: " + " ".join(f"{a}={pooled(cells[a][-4:]):.5f}" for a in arms), flush=True)
    p = {name: pooled(rows) for name, rows in cells.items()}
    comparison = paired(cells["H31-3-S"], cells["H31-S"])
    per_fold = {
        holdout.FOLD_NAMES[f]: {a: pooled([cells[a][4 * i + f] for i in range(len(SEEDS))]) for a in arms}
        for f in range(4)
    }
    gate = {
        "pooled_candidate_gt_h31s": p["H31-3-S"] > p["H31-S"],
        "mean_seed_delta_ge_0_001": comparison["mean_seed_paired_delta_dti"] >= 0.001,
        "ci95_lower_gt_zero": comparison["ci95"][0] > 0.0,
        "positive_seeds_ge_7_of_10": comparison["positive_seeds"] >= 7,
        "positive_folds_ge_3_of_4": comparison["positive_folds"] >= 3,
    }
    gate_pass = bool(all(gate.values()))
    out = {
        "experiment": "E2 H31-3 versus H31-S paired spatial holdout",
        "preregistration": str(PREREG.relative_to(ROOT)),
        "preregistration_sha256": sha256_file(PREREG),
        "label": "HOLDOUT-DTI",
        "provenance_note": "Catalogue-internal whole-segment hide-and-recover; NOT a live organizer score.",
        "evaluator": "gems27.metric.dti_binary v1 (alpha=0.2, beta=0.8, R=3px triangular) + buffered quadrant holdout (buffer_px=6)",
        "seeds": SEEDS, "folds": holdout.FOLD_NAMES, "n_cells": 4 * len(SEEDS),
        "n_withheld_positives_total": n_withheld, "budget_total": BUDGET_TOTAL,
        "budget_per_fold": budgets.tolist(), "b_exclusion_px": B_EXCL,
        "pooled_holdout_dti_buffered": p, "per_fold_holdout_dti_buffered": per_fold,
        "paired_candidate_minus_B": comparison, "frozen_gate_clauses": gate,
        "gate_efficacy_pass": gate_pass, "verdict_stage_e2": "promote" if gate_pass else "negative",
        "runtime_s": round(time.time() - t0, 1),
    }
    E2_PATH.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({"pooled": p, "candidate_minus_h31s": comparison, "gate": gate,
                      "pass": gate_pass, "evidence": str(E2_PATH)}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("e1", "e2", "both"), default="both")
    args = parser.parse_args()
    if args.stage == "e1":
        return run_e1()
    if args.stage == "e2":
        return run_e2()
    rc = run_e1()
    return rc if rc else run_e2()


if __name__ == "__main__":
    raise SystemExit(main())
