#!/usr/bin/env python3
"""E1-E3 for H29-XG joint gravity-magnetic cross-gradient structural coupling.

Preregistration: knowledge/39_preregistration_H29-XG_2026-10-29.md (written before this run).
Reuses the shared holdout, metric, submission, uniqueness and H33 runner helpers by import; the
structure follows scripts/run_h28_6_gravity_persistence.py. Feature constructor:
src/gems27/crossgrad_features.py.

Every performance number is HOLDOUT-DTI. Nothing here is an organizer score or a leaderboard
projection. The research TIFF is written only if the efficacy gate AND the uniqueness gate pass;
even then it is NOT OK TO SUBMIT (the matched current-best comparison is not run here).
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems27 import crossgrad_features as xg  # noqa: E402
from gems27 import grid, holdout, paths, submission  # noqa: E402
from gems27 import subsurface_features as sub  # noqa: E402
from run_h29_holdout import get_or_build_subsurface15  # noqa: E402
from run_h33_lane import (  # noqa: E402
    B_EXCL,
    BUFFER_PX,
    canary_auc,
    emit,
    fit_predict,
    load_group_map,
    local_overlap,
    pooled,
    registry_positive_union,
    scatter,
    score_cell,
    surface_spearman,
)

SEEDS = list(range(800, 810))
PREREG = ROOT / "knowledge" / "39_preregistration_H29-XG_2026-10-29.md"
SCRATCH = paths.EVIDENCE / "_scratch"
RESEARCH = paths.DOCS / "downloads" / "research"
E1_PATH = paths.EVIDENCE / "h29xg_e1_canary_and_surface_800_809.json"
E2_PATH = paths.EVIDENCE / "h29xg_e2_holdout_800_809.json"
CARD_PATH = paths.EVIDENCE / "h29xg_run_card_2026-10-29.json"
DATE = "20261029"
PAIR_RNG_SEED = 20261029
CANARY_NEG_MAX = 250_000


def sha256_file(path: Path) -> str:
    return hashlib.file_digest(path.open("rb"), "sha256").hexdigest()


class Stack:
    """Column-concatenated view over row-aligned 2-D blocks (same helper as H28-6)."""

    def __init__(self, parts: list[np.ndarray]):
        self.parts = parts
        self.shape = (parts[0].shape[0], sum(p.shape[1] for p in parts))

    def __getitem__(self, key):
        return np.concatenate([np.asarray(p[key], dtype=np.float32) for p in self.parts], axis=1)


def main() -> int:
    t0 = time.time()
    if not PREREG.is_file():
        raise SystemExit("preregistration missing; refusing to run")
    prereg_hash = sha256_file(PREREG)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    RESEARCH.mkdir(parents=True, exist_ok=True)

    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    meta = json.loads(paths.PREPARED_META.read_text())
    names = meta["names"]
    base = np.load(paths.PREPARED_FEATURES, mmap_mode="r")
    if base.shape != (int(foot.sum()), 32):
        raise SystemExit(f"prepared stack shape {base.shape} is not the cached 32-band matrix")

    print("subsurface 15-transform cache", flush=True)
    sub15 = get_or_build_subsurface15(foot, names)
    if sub15.shape != (int(foot.sum()), len(sub.TRANSFORM_NAMES)):
        raise SystemExit(f"subsurface cache shape {sub15.shape} unexpected")

    grav = np.full(grid.SHAPE, np.nan, np.float32)
    grav[foot] = np.asarray(base[:, names.index("iso_grav_anom")], dtype=np.float32)
    mag = np.full(grid.SHAPE, np.nan, np.float32)
    mag[foot] = np.asarray(base[:, names.index("rtp")], dtype=np.float32)
    newX = xg.build_feature_matrix(grav, mag, foot)
    del grav, mag

    arm_D = Stack([base, sub15])
    arm_C = Stack([base, sub15, newX])
    all_names = list(names) + list(sub.TRANSFORM_NAMES) + list(xg.COLUMN_NAMES)
    assert arm_C.shape[1] == len(all_names) == 50

    print("vector segment map", flush=True)
    group, group_stats = load_group_map(labels)
    _, registry_ids = registry_positive_union(foot)  # names only; the arms are unconstrained

    y = labels[foot].astype(np.uint8)
    splits = []
    hidden_any = np.zeros_like(labels)
    for seed in SEEDS:
        split = holdout.make_segment_split(labels, foot, group, seed=seed, frac=0.20)
        splits.append(split)
        hidden_any |= split.hidden
    pos = np.flatnonzero(hidden_any[foot])
    neg_all = np.flatnonzero((~labels & foot & ~hidden_any)[foot])
    neg = np.random.default_rng(800).choice(neg_all, size=min(CANARY_NEG_MAX, neg_all.size), replace=False)

    # ---------- E1: canaries on all 50 inputs ----------
    print("E1 canaries on 50 inputs", flush=True)
    canary = {}
    blocks = [base, sub15, newX]
    offset = 0
    for block in blocks:
        for j in range(block.shape[1]):
            name = all_names[offset + j]
            values = np.asarray(block[:, j], dtype=np.float32)
            raw, inv = canary_auc(values, pos, neg)
            canary[name] = {"raw_auc": raw, "direction_invariant_auc": inv}
        offset += block.shape[1]
    canary_max_name = max(canary, key=lambda k: canary[k]["direction_invariant_auc"])
    canary_max = canary[canary_max_name]["direction_invariant_auc"]
    leakage = {k: v for k, v in canary.items() if v["direction_invariant_auc"] > 0.90}
    new_canary_max = max(canary[n]["direction_invariant_auc"] for n in xg.COLUMN_NAMES)

    # ---------- E1: full-fit candidate surface, pre-placement check ----------
    print("E1 full-fit candidate surface", flush=True)
    train_all = np.ones(y.size, bool)
    full_prob = fit_predict(arm_C, y, train_all, seed=800)
    full_grid = scatter(full_prob, foot)
    del full_prob
    rng = np.random.default_rng(801)
    sample = rng.choice(np.flatnonzero(foot.ravel()), size=400_000, replace=False)
    rho = surface_spearman(full_grid, foot, sample)
    max_abs_rho = max(abs(v) for v in rho.values())
    e1_pass = (not leakage) and max_abs_rho <= 0.90
    e1 = {
        "experiment": "E1 H29-XG cross-gradient canaries (50 inputs) and pre-placement surface",
        "label": "HOLDOUT-DTI setup only; no organizer score",
        "preregistration_sha256": prereg_hash,
        "seeds": SEEDS,
        "group_map": group_stats,
        "n_hidden_positive_union": int(pos.size),
        "n_negative_sample": int(neg.size),
        "canary_max_direction_invariant_auc": canary_max,
        "canary_max_feature": canary_max_name,
        "canary_max_new_feature_auc": new_canary_max,
        "leakage_flags": leakage,
        "canary_all": canary,
        "preplacement_surface_spearman_vs_12_peer_rasters": rho,
        "max_abs_preplacement_surface_spearman": max_abs_rho,
        "registry_ids": registry_ids,
        "gate_e1_pass": bool(e1_pass),
        "runtime_s": round(time.time() - t0, 1),
    }
    E1_PATH.write_text(json.dumps(e1, indent=2) + "\n")
    print(json.dumps({"canary_max": canary_max, "canary_max_feature": canary_max_name,
                      "new_max": new_canary_max, "max_abs_rho": max_abs_rho, "pass": e1_pass}), flush=True)
    if not e1_pass:
        print("E1 stop", flush=True)
        return 2

    # ---------- E2: paired whole-FID holdout, C vs D ----------
    print("E2 holdout", flush=True)
    folds = holdout.make_quadrant_folds(foot)
    cells_c, cells_d = [], []
    fold_c = {n: [] for n in holdout.FOLD_NAMES}
    fold_d = {n: [] for n in holdout.FOLD_NAMES}
    buffer_ok = []
    for seed, split in zip(SEEDS, splits, strict=True):
        train = holdout.buffered_training_mask(split, foot, buffer_px=BUFFER_PX)
        train_fp = train[foot]
        buffer_ok.append(bool(not (train & split.hidden).any()))
        pc = scatter(fit_predict(arm_C, y, train_fp, seed=seed), foot)
        pd = scatter(fit_predict(arm_D, y, train_fp, seed=seed), foot)
        known = split.known
        pred_c = emit(pc, foot, known, None)
        pred_d = emit(pd, foot, known, None)
        cells_c.append(score_cell(pred_c, split, foot))
        cells_d.append(score_cell(pred_d, split, foot))
        for fid, fname in enumerate(holdout.FOLD_NAMES):
            fold_c[fname].append(score_cell(pred_c, split, foot, folds == fid))
            fold_d[fname].append(score_cell(pred_d, split, foot, folds == fid))
        print(f"seed {seed} C {cells_c[-1]['dti']:.4f} D {cells_d[-1]['dti']:.4f} "
              f"dotsC {int(pred_c.sum())} dotsD {int(pred_d.sum())}", flush=True)
        del pc, pd, pred_c, pred_d

    delta = np.array([pooled([c]) - pooled([d]) for c, d in zip(cells_c, cells_d, strict=True)])
    rng_b = np.random.default_rng(PAIR_RNG_SEED)
    boots = delta[rng_b.integers(0, len(delta), size=(10_000, len(delta)))].mean(axis=1)
    ci = [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))]
    per_fold = {n: pooled(fold_c[n]) - pooled(fold_d[n]) for n in holdout.FOLD_NAMES}
    positive_folds = int(sum(v > 0 for v in per_fold.values()))
    positive_seeds = int((delta > 0).sum())
    n_withheld = int(sum(c["n_truth"] for c in cells_c))
    pooled_c, pooled_d = pooled(cells_c), pooled(cells_d)
    efficacy = (float(delta.mean()) >= 0.001 and ci[0] > 0 and positive_seeds >= 7
                and positive_folds >= 3 and pooled_c > pooled_d)
    e2 = {
        "experiment": "E2 H29-XG whole-FID buffered holdout, C vs D",
        "label": "HOLDOUT-DTI",
        "evaluator": "gems27.metric.dti_binary v1 (alpha=0.2, beta=0.8, R=3px triangular) + whole-FID buffered holdout (buffer_px=6)",
        "seeds": SEEDS,
        "n_withheld_positive_occurrences": n_withheld,
        "pooled_candidate_C": pooled_c,
        "pooled_control_D": pooled_d,
        "pooled_delta": pooled_c - pooled_d,
        "mean_seed_paired_delta": float(delta.mean()),
        "ci95_paired_bootstrap": ci,
        "positive_seeds": positive_seeds,
        "per_fold_pooled_delta": per_fold,
        "positive_folds": positive_folds,
        "training_excludes_hidden_all_seeds": bool(all(buffer_ok)),
        "gate_efficacy_pass": bool(efficacy),
        "per_seed_delta": delta.tolist(),
        "cells_candidate_C": cells_c,
        "cells_control_D": cells_d,
        "runtime_s": round(time.time() - t0, 1),
    }
    E2_PATH.write_text(json.dumps(e2, indent=2) + "\n")
    print(json.dumps({"pooled_C": pooled_c, "pooled_D": pooled_d, "mean_delta": float(delta.mean()),
                      "ci95": ci, "pos_seeds": positive_seeds, "pos_folds": positive_folds,
                      "efficacy": efficacy}), flush=True)

    # ---------- E3: placement, uniqueness, validation (only if efficacy passed) ----------
    print("E3 placement from the full-fit surface", flush=True)
    known_all = labels & foot
    dots = emit(full_grid, foot, known_all, None)
    if int((dots & known_all).sum()) != 0 or float(distance_transform_edt(~known_all)[dots].min()) <= B_EXCL:
        raise RuntimeError("emission violated catalogue exclusion")
    pred = dots.astype(np.float32)
    cid = submission.scored_content_id(pred, foot, known_all)
    stem = f"gems27-h29xg-crossgrad-{DATE}-{cid}"
    tif_scratch = SCRATCH / f"{stem}-allfinite.tif"
    nan_scratch = SCRATCH / f"{stem}-nan.tif"
    submission.write_geotiff(pred, paths.TEMPLATE, tif_scratch, outside="zero")
    submission.write_geotiff(pred, paths.TEMPLATE, nan_scratch, outside="nan")
    checks = submission.verify_geotiff(tif_scratch, paths.TEMPLATE)
    nan_checks = submission.verify_geotiff(nan_scratch, paths.TEMPLATE)

    uniq_path = SCRATCH / "h29xg_uniqueness.json"
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_parallel_uniqueness.py"), str(tif_scratch),
         "--out", str(uniq_path)],
        check=False, cwd=ROOT,
    )
    uniq = json.loads(uniq_path.read_text()) if uniq_path.exists() else {"pass": False, "duplicates": ["checker-failed"]}
    max_overlap = max((e["candidate_dot_fraction_within_3px"] for e in uniq.get("entries", [])), default=1.0)
    max_dot_rho = max((abs(e["spearman_rank_correlation"]) for e in uniq.get("entries", [])), default=1.0)
    local = local_overlap(dots, foot, skip_names={tif_scratch.name, nan_scratch.name})
    unique_pass = bool(uniq.get("pass")) and bool(local["pass"]) and max_abs_rho <= 0.90 and proc.returncode == 0

    write_tif = bool(efficacy) and bool(unique_pass) and bool(checks["hard_checks_passed"])
    if write_tif:
        final_tif = RESEARCH / tif_scratch.name
        final_nan = RESEARCH / nan_scratch.name
        final_tif.write_bytes(tif_scratch.read_bytes())
        final_nan.write_bytes(nan_scratch.read_bytes())
        zpath = submission.zip_single(final_tif)
        tif_name, nan_name, zip_name = final_tif.name, final_nan.name, zpath.name
        directory = "docs/downloads/research"
        note = (f"H29-XG cross-grad HOLDOUT-DTI {pooled_c:.4f} vs D {pooled_d:.4f} | id {cid} | NOT OK TO SUBMIT")[:140]
        (RESEARCH / f"note-{stem}-allfinite.txt").write_text(note + "\n")
    else:
        tif_name = nan_name = zip_name = directory = None
        note = "H29-XG stopped before placement: no TIFF written. NOT OK TO SUBMIT."

    verdict = ("holdout-pass-unmatched" if write_tif else "negative")
    card = {
        "schema": "parallel-run-card-v2",
        "generated_utc": "2026-10-29",
        "lane": "L-S18-H29-XG (self-selected from the registry screen; no lane paragraph supplied; see knowledge/39 section 0)",
        "hypothesis_id": "H29-XG",
        "hypothesis": "Joint gravity-magnetic cross-gradient |grad g x grad m| (sigma 2 and 4 px) and its angle-only sine, added to the cached 32-band stack plus 15 subsurface transforms",
        "mechanism": "A basement step that juxtaposes two domains produces coincident, non-parallel gravity and magnetic edges even where no surface trace exists.",
        "named_non_fault_mimic": "lithologic contacts with both density and susceptibility contrasts; terrain-correlated residuals present in both fields",
        "verdict": verdict,
        "ok_to_submit": False,
        "slot_authorized": False,
        "download_decision": "NOT OK TO SUBMIT",
        "download_decision_reasons": [
            "Holdout efficacy gate " + ("passed" if efficacy else "failed") + " against control D on seeds 800-809.",
            "Matched current-best comparison (H31 / H29-S on the same splits) was not run; the readiness gate requires it.",
            "Whole-FID holdout is catalogue-internal; it cannot see organizer expert labels.",
            "Holdout DTI is about 6x below the owner-reported live scores; a holdout gain does not guarantee a live gain.",
        ],
        "submission_name": f"27GEMSDOE-H29XG-CROSSGRAD-{DATE}-{cid}" if write_tif else None,
        "note_max_140_chars": note,
        "note_chars": len(note),
        "preregistration_sha256": prereg_hash,
        "holdout": {
            "label": "HOLDOUT-DTI",
            "provenance_note": "Catalogue-internal whole-FID buffered hide-and-recover; NOT a live organizer score.",
            "evaluator": e2["evaluator"],
            "seeds": SEEDS,
            "n_cells": len(cells_c),
            "n_withheld_positives_total": n_withheld,
            "canary_max_auc": canary_max,
            "canary_max_feature": canary_max_name,
            "pooled_candidate": pooled_c,
            "pooled_control_D": pooled_d,
            "gate_efficacy_pass": bool(efficacy),
            "ci95": ci,
            "split_scheme": "whole-fid-segment-v1",
            "visible_only_catalogue_features": True,
            "training_buffer_verified": bool(all(buffer_ok)),
            "emitter_blind_to_hidden_and_buffer": True,
            "full_kernel_scored": True,
            "all_model_features_canary_tested": len(canary) == 50,
            "matched_current_best_comparison": False,
            "paired_candidate_minus_D": {
                "pooled_delta_dti": pooled_c - pooled_d,
                "mean_seed_paired_delta_dti": float(delta.mean()),
                "ci95": ci,
                "positive_seeds": positive_seeds,
                "n_seeds": len(SEEDS),
                "positive_folds": positive_folds,
                "n_folds": 4,
                "per_fold_pooled_delta_dti": per_fold,
            },
        },
        "uniqueness_vs_registry": {
            "pass": bool(unique_pass),
            "registry_checker_pass": bool(uniq.get("pass")),
            "max_dot_overlap_within_3px_euclidean": float(max_overlap),
            "max_surface_spearman": float(max_abs_rho),
            "max_postplacement_dot_spearman": float(max_dot_rho),
            "scope_current_and_complete": False,
            "scope_note": "12 pinned focus-site rasters plus local all-finite files in docs/downloads; the GEMSDOE25 xg1-crossgrad raster is not in the pinned set unless listed in the checker output",
            "duplicates": uniq.get("duplicates", []),
            "local_prior_rasters": local,
        },
        "validator": {
            "zeros_hard_pass": bool(checks["hard_checks_passed"]),
            "zeros_checks": checks["checks"],
            "nan_hard_pass": bool(nan_checks["hard_checks_passed"]),
            "sha256": checks["sha256"],
        },
        "raster": {
            "primary_allfinite": tif_name,
            "nan_twin": nan_name,
            "zip": zip_name,
            "directory": directory,
            "sha256": checks["sha256"] if tif_name else None,
            "dots": int(dots.sum()),
            "content_id": cid,
        },
        "runtime_s": round(time.time() - t0, 1),
    }
    CARD_PATH.write_text(json.dumps(card, indent=2) + "\n")
    print(json.dumps({"verdict": verdict, "dots": int(dots.sum()), "unique": unique_pass,
                      "efficacy": bool(efficacy), "tif_written": write_tif}, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
