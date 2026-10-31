#!/usr/bin/env python3
"""E1-E3 for Lane L-2026-10-31-H35: weak-scarp continuity (WSC) augmentation of the arm-D emission.

Preregistration: knowledge/45_preregistration_H35_2026-10-31.md (written before this run).
Reuses the shared holdout, metric, submission and uniqueness tooling by import; the structure
follows scripts/run_h29xg_crossgrad.py and scripts/run_h33_lane.py. Feature constructor:
src/gems27/wsc_features.py (label-free).

Arms (one trained model per seed; deltas are label-free emission structure):
  B  = arm-D detector emission (control architecture)
  C0 = B + T-v2 catalogue-graph gap-closure dots (architecture context; T-v2 is already in-repo)
  C1 = C0 + WSC delta (the hypothesis under test): WSC ridges enter the candidate pool with
       fusion priority p' = prob + 0.5 * wsc_pct

Every performance number is HOLDOUT-DTI. Nothing here is an organizer score or a leaderboard
projection. The primary TIFF is chosen by the frozen file-choice rule in the preregistration and
is written in both all-finite and NaN-outside variants.
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
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems27 import grid, holdout, paths, submission  # noqa: E402
from gems27 import links as links_mod  # noqa: E402
from gems27 import wsc_features as wsc  # noqa: E402
from gems27.candidates import RULE, SPACING, dedupe_mutual, evidence_score  # noqa: E402
from gems27.graph import build_graph  # noqa: E402
from gems27.oof_detector import ridge_nms  # noqa: E402
from gems27.subsurface_features import priority_poisson_disk  # noqa: E402
from run_h29_holdout import get_or_build_subsurface15  # noqa: E402
from run_h33_lane import (  # noqa: E402
    B_EXCL,
    BUDGET,
    BUFFER_PX,
    MIN_DIST,
    canary_auc,
    emit,
    fit_predict,
    load_group_map,
    local_overlap,
    paired,
    pooled,
    registry_positive_union,
    scatter,
    score_cell,
    surface_spearman,
)

SEEDS = list(range(930, 940))
PREREG = ROOT / "knowledge" / "45_preregistration_H35_2026-10-31.md"
E1_PATH = paths.EVIDENCE / "h35_e1_canary_and_surface_930_939.json"
E2_PATH = paths.EVIDENCE / "h35_e2_holdout_930_939.json"
CARD_PATH = paths.EVIDENCE / "h35_run_card_2026-10-31.json"
RESEARCH = paths.DOCS / "downloads" / "research"
DATE = "20261031"
PAIR_RNG_SEED = 20261031
CANARY_NEG_MAX = 250_000
FUSION_LAMBDA = 0.5
FULL_FIT_SEED = 999


def sha256_file(path: Path) -> str:
    return hashlib.file_digest(path.open("rb"), "sha256").hexdigest()


class Stack:
    """Column-concatenated view over row-aligned 2-D blocks (same helper as H28-6/H29-XG)."""

    def __init__(self, parts: list[np.ndarray]):
        self.parts = parts
        self.shape = (parts[0].shape[0], sum(p.shape[1] for p in parts))

    def __getitem__(self, key):
        return np.concatenate([np.asarray(p[key], dtype=np.float32) for p in self.parts], axis=1)


def tv2_link_dots(known: np.ndarray, foot: np.ndarray) -> np.ndarray:
    """T-v2 gap-closure dots from VISIBLE catalogue geometry only (fold discipline)."""
    fg = build_graph(known, with_edges=False)
    L = links_mod.generate_links(fg, region=foot, **RULE)
    z = evidence_score(L)
    Ld = dedupe_mutual(L[z >= 3])
    if Ld.empty:
        return np.zeros_like(foot)
    t_raw = links_mod.rasterize_links(Ld, foot.shape, SPACING) & foot & ~known
    d_known = distance_transform_edt(~known)
    return t_raw & (d_known > B_EXCL)


def wsc_fused_priority(prob_grid: np.ndarray, wsc_grid: np.ndarray, foot: np.ndarray,
                       known: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(priority_grid, candidate_mask) for the C1 pool."""
    d_known = distance_transform_edt(~known)
    r_prob = ridge_nms(prob_grid, foot, sigma=1.0)
    r_wsc = wsc.wsc_ridges(wsc_grid, foot)
    cand = (r_prob | r_wsc) & foot & ~known & (d_known > B_EXCL)
    wsc_vals = np.where(cand, wsc_grid, 0.0)
    pct = np.zeros(foot.shape, np.float32)
    pos = cand & (wsc_vals > 0)
    if pos.any():
        ranks = rankdata(wsc_vals[pos], method="average")
        pct[pos] = (ranks / (ranks.size + 1.0)).astype(np.float32)
    prio = prob_grid + np.float32(FUSION_LAMBDA) * pct
    return prio.astype(np.float32), cand


def emit_c1(prob_grid: np.ndarray, wsc_grid: np.ndarray, foot: np.ndarray, known: np.ndarray) -> np.ndarray:
    prio, cand = wsc_fused_priority(prob_grid, wsc_grid, foot, known)
    return priority_poisson_disk(prio, cand, MIN_DIST, BUDGET)


def main() -> int:
    t0 = time.time()
    if not PREREG.is_file():
        raise SystemExit("preregistration missing; refusing to run")
    prereg_hash = sha256_file(PREREG)
    RESEARCH.mkdir(parents=True, exist_ok=True)

    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    meta = json.loads(paths.PREPARED_META.read_text())
    names = meta["names"]
    base = np.load(paths.PREPARED_FEATURES, mmap_mode="r")
    if base.shape != (int(foot.sum()), 32):
        raise SystemExit(f"prepared stack shape {base.shape} is not the cached 32-band matrix")
    sub15 = get_or_build_subsurface15(foot, names)
    X = Stack([base, sub15])
    y = labels[foot].astype(np.uint8)

    print("WSC surface (label-free)", flush=True)
    wsc_grid, r_u8, gate = wsc.wsc_score(grid.SHAPE)
    if not np.isfinite(wsc_grid[foot]).all() or float(wsc_grid[foot].max()) <= 0:
        raise SystemExit("WSC surface is degenerate")
    wsc_ridge_mask = wsc.wsc_ridges(wsc_grid, foot)

    group, group_stats = load_group_map(labels)
    _, registry_ids = registry_positive_union(foot)

    splits = []
    hidden_any = np.zeros_like(labels)
    for seed in SEEDS:
        split = holdout.make_segment_split(labels, foot, group, seed=seed, frac=0.20)
        splits.append(split)
        hidden_any |= split.hidden
    pos = np.flatnonzero(hidden_any[foot])
    rng = np.random.default_rng(930)
    neg_pool = np.flatnonzero((~hidden_any & ~labels)[foot])
    if neg_pool.size == 0:
        raise SystemExit("no background cells for canary")
    neg = rng.choice(neg_pool, size=min(CANARY_NEG_MAX, neg_pool.size), replace=False)

    # ---------------- E1: canary + pre-placement surface screen ----------------
    wsc_flat = np.zeros(grid.SHAPE, np.float32)
    wsc_flat[foot] = wsc_grid[foot]
    canary_wsc = canary_auc(wsc_grid[foot], pos, neg)
    canary_resp = canary_auc(np.where(gate > 0, r_u8, 0.0)[foot], pos, neg)
    canary_max = max(canary_wsc[1], canary_resp[1])
    leakage = canary_max > 0.90

    print("full-fit arm-D surface for the surface screen", flush=True)
    full_prob = fit_predict(X, y, np.ones(y.size, bool), seed=FULL_FIT_SEED)
    full_grid = scatter(full_prob, foot)
    sample = np.random.default_rng(11).choice(foot.size, size=min(300_000, foot.size), replace=False)
    rho_prob = surface_spearman(full_grid, foot, sample)
    rho_wsc = surface_spearman(wsc_flat, foot, sample)
    max_abs_rho = max(max(abs(v) for v in rho_prob.values()), max(abs(v) for v in rho_wsc.values()))
    e1_pass = bool((not leakage) and max_abs_rho <= 0.90)
    e1 = {
        "experiment": "E1 H35-1 canary and pre-placement surface screen",
        "label": "HOLDOUT-DTI instrument; canary AUC is direction-invariant",
        "preregistration_sha256": prereg_hash,
        "seeds": SEEDS,
        "canary_wsc_score_auc": canary_wsc,
        "canary_weak_response_auc": canary_resp,
        "canary_max_auc": canary_max,
        "leakage_stop_triggered": leakage,
        "preplacement_surface_spearman_vs_12_peer_rasters_prob": rho_prob,
        "preplacement_surface_spearman_vs_12_peer_rasters_wsc": rho_wsc,
        "max_abs_preplacement_surface_spearman": max_abs_rho,
        "n_withheld_positive_occurrences": int(pos.size),
        "wsc_ridge_px": int(wsc_ridge_mask.sum()),
        "group_map_stats": group_stats,
        "e1_pass": e1_pass,
    }
    E1_PATH.write_text(json.dumps(e1, indent=2, default=float) + "\n")
    print(json.dumps({"canary_max": canary_max, "max_abs_rho": max_abs_rho, "pass": e1_pass}), flush=True)
    if leakage or max_abs_rho > 0.90:
        card = {
            "schema": "parallel-run-card-v2",
            "hypothesis_id": "H35-1",
            "hypothesis": "weak-scarp continuity (WSC) augmentation of the arm-D emission",
            "mechanism": "orientation-coherent low-amplitude LiDAR scarp continuity enters the dot pool",
            "named_non_fault_mimic": "dip slopes and hogbacks, terrace risers, Lake Lahontan strandlines, avalanche chutes, graded-road berms",
            "verdict": "negative",
            "ok_to_submit": False,
            "stop_reason": "leakage" if leakage else "duplicate_surface",
            "holdout": {"label": "HOLDOUT-DTI", "evaluator": "not scored; stopped at E1",
                        "n_withheld_positives_total": int(pos.size), "canary_max_auc": canary_max,
                        "gate_efficacy_pass": False},
            "uniqueness_vs_registry": {"pass": False, "max_surface_spearman": max_abs_rho,
                                       "max_dot_overlap_within_3px_euclidean": None},
            "note_max_140_chars": "H35-1 stopped at E1; no TIFF placed. DO NOT SUBMIT.",
            "raster": None,
        }
        CARD_PATH.write_text(json.dumps(card, indent=2, default=float) + "\n")
        print("E1 stop; no dots placed", flush=True)
        return 2

    # ---------------- E2: frozen holdout, seeds 930-939, arms B / C0 / C1 ----------------
    print("E2 holdout", flush=True)
    cells = {"B": [], "C0": [], "C1": []}
    fold_cells = {a: {n: [] for n in holdout.FOLD_NAMES} for a in cells}
    folds = holdout.make_quadrant_folds(foot)
    for seed, split in zip(SEEDS, splits, strict=True):
        train = holdout.buffered_training_mask(split, foot, buffer_px=BUFFER_PX)[foot]
        prob = fit_predict(X, y, train, seed=seed)
        prob_grid = scatter(prob, foot)
        known = split.known
        dots_b = emit(prob_grid, foot, known, None)
        t_dots = tv2_link_dots(known, foot)
        d_b = distance_transform_edt(~dots_b) if dots_b.any() else np.full(grid.SHAPE, np.inf)
        t_kept = t_dots & (d_b >= 3.0)
        dots_c0 = dots_b | t_kept
        dots_c1 = emit_c1(prob_grid, wsc_grid, foot, known)
        for arm, dots in (("B", dots_b), ("C0", dots_c0), ("C1", dots_c1)):
            cells[arm].append(score_cell(dots, split, foot))
            for fid, fname in enumerate(holdout.FOLD_NAMES):
                fold_cells[arm][fname].append(score_cell(dots, split, foot, folds == fid))
        print(
            f"seed {seed} B {cells['B'][-1]['dti']:.4f} C0 {cells['C0'][-1]['dti']:.4f} "
            f"C1 {cells['C1'][-1]['dti']:.4f} dots {int(dots_b.sum())}/{int(dots_c0.sum())}/{int(dots_c1.sum())}",
            flush=True,
        )
        del prob, prob_grid, dots_b, dots_c0, dots_c1

    def comparison(cand: str, ctrl: str) -> dict:
        pair = paired(cells[cand], cells[ctrl])
        per_fold = {fn: pooled(fold_cells[cand][fn]) - pooled(fold_cells[ctrl][fn])
                    for fn in holdout.FOLD_NAMES}
        pair["per_fold_pooled_delta_dti"] = per_fold
        pair["positive_folds"] = int(sum(v > 0 for v in per_fold.values()))
        pair["n_folds"] = 4
        gate = bool(
            pair["mean_seed_paired_delta_dti"] >= 0.001
            and pair["ci95"][0] > 0
            and pair["positive_seeds"] >= 7
            and pair["positive_folds"] >= 3
            and pooled(cells[cand]) > pooled(cells[ctrl])
        )
        pair["gate_efficacy_pass"] = gate
        return pair

    pair_c1_c0 = comparison("C1", "C0")
    pair_c0_b = comparison("C0", "B")
    n_withheld = int(sum(c["n_truth"] for c in cells["C1"]))
    e2 = {
        "experiment": "E2 H35-1 whole-segment buffered holdout (B / C0 / C1)",
        "label": "HOLDOUT-DTI",
        "evaluator": "gems27.metric.dti_binary v1 (alpha=0.2, beta=0.8, R=3px triangular) + whole-FID buffered holdout (buffer_px=6)",
        "seeds": SEEDS,
        "n_cells": len(cells["C1"]),
        "n_withheld_positive_occurrences": n_withheld,
        "pooled_B": pooled(cells["B"]),
        "pooled_C0": pooled(cells["C0"]),
        "pooled_C1": pooled(cells["C1"]),
        "hypothesis_gate_C1_vs_C0": pair_c1_c0,
        "architecture_gate_C0_vs_B": pair_c0_b,
        "cells_B": cells["B"], "cells_C0": cells["C0"], "cells_C1": cells["C1"],
        "runtime_s": round(time.time() - t0, 1),
    }
    E2_PATH.write_text(json.dumps(e2, indent=2, default=float) + "\n")
    print(json.dumps({"pooled_B": e2["pooled_B"], "pooled_C0": e2["pooled_C0"], "pooled_C1": e2["pooled_C1"],
                      "gate_C1": pair_c1_c0["gate_efficacy_pass"], "gate_C0": pair_c0_b["gate_efficacy_pass"]}),
          flush=True)

    # ---------------- E3: placement, uniqueness, validation, run card ----------------
    print("E3 placement", flush=True)
    known_all = labels & foot
    dots_b_live = emit(full_grid, foot, known_all, None)
    t_live = tv2_link_dots(known_all, foot)
    d_bl = distance_transform_edt(~dots_b_live) if dots_b_live.any() else np.full(grid.SHAPE, np.inf)
    dots_c0_live = dots_b_live | (t_live & (d_bl >= 3.0))
    dots_c1_live = emit_c1(full_grid, wsc_grid, foot, known_all)

    hyp_pass = pair_c1_c0["gate_efficacy_pass"]
    arch_pass = pair_c0_b["gate_efficacy_pass"]

    def finalize(arm: str, dots: np.ndarray) -> dict:
        pred = dots.astype(np.float32)
        cid = submission.scored_content_id(pred, foot, known_all)
        stem = f"gems27-h35-wsc-{arm.lower()}-{DATE}-{cid}"
        tif = submission.write_geotiff(pred, paths.TEMPLATE, RESEARCH / f"{stem}-allfinite.tif", outside="zero")
        nan_tif = submission.write_geotiff(pred, paths.TEMPLATE, RESEARCH / f"{stem}-nan.tif", outside="nan")
        zpath = submission.zip_single(tif)
        checks = submission.verify_geotiff(tif, paths.TEMPLATE)
        nan_checks = submission.verify_geotiff(nan_tif, paths.TEMPLATE)
        (RESEARCH / f"checks-{stem}-allfinite.json").write_text(json.dumps(checks, indent=2) + "\n")
        (RESEARCH / f"checks-{stem}-nan.json").write_text(json.dumps(nan_checks, indent=2) + "\n")
        uniq_path = paths.EVIDENCE / f"h35_uniqueness_{arm.lower()}.json"
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "check_parallel_uniqueness.py"), str(tif),
             "--out", str(uniq_path)],
            check=False, cwd=ROOT, capture_output=True, text=True,
        )
        uniq = json.loads(uniq_path.read_text()) if uniq_path.exists() else {"pass": False}
        max_overlap = max((e.get("candidate_dot_fraction_within_3px", 1.0)
                           for e in uniq.get("entries", [])), default=1.0)
        max_rho_final = max((abs(e.get("spearman_rank_correlation", 1.0))
                             for e in uniq.get("entries", [])), default=1.0)
        local = local_overlap(dots, foot, skip_names={tif.name, nan_tif.name})
        unique_pass = bool(uniq.get("pass")) and local["pass"] and max_rho_final <= 0.90
        return {
            "arm": arm, "stem": stem, "cid": cid, "n_dots": int(dots.sum()),
            "tif": tif.name, "tif_path": str(tif.relative_to(ROOT)), "zip": zpath.name,
            "nan_tif": nan_tif.name, "sha256": sha256_file(tif), "nan_sha256": sha256_file(nan_tif),
            "checks": checks, "nan_checks": nan_checks,
            "uniqueness_registry": uniq, "uniqueness_local": local,
            "max_registry_overlap": float(max_overlap), "max_registry_dot_spearman": float(max_rho_final),
            "checker_returncode": proc.returncode,
            "unique_pass": bool(unique_pass),
        }

    res = {"B": finalize("B", dots_b_live), "C0": finalize("C0", dots_c0_live), "C1": finalize("C1", dots_c1_live)}

    # frozen file-choice rule
    if hyp_pass and res["C1"]["unique_pass"] and res["C1"]["checks"]["hard_checks_passed"]:
        primary, primary_label, arm_gate = "C1", "hypothesis arm C1 (B + T-v2 + WSC)", hyp_pass
    elif arch_pass and res["C0"]["unique_pass"] and res["C0"]["checks"]["hard_checks_passed"]:
        primary, primary_label, arm_gate = "C0", "architecture arm C0 (B + T-v2); WSC hypothesis negative", arch_pass
    else:
        primary, primary_label, arm_gate = "B", "base arm B (arm-D emission); no hypothesis gate passed", False
    pr = res[primary]
    # OK to submit requires the arm's own comparison gate to have passed plus uniqueness and validation.
    ok_submit = bool(arm_gate and pr["unique_pass"] and pr["checks"]["hard_checks_passed"])
    verdict = "promote" if ok_submit and primary == "C1" else "negative"
    tail = "OK TO DOWNLOAD AND SUBMIT" if ok_submit else "NOT OK TO SUBMIT"
    ctrl_for_note = "C0" if primary == "C1" else "B"
    note = (f"27GEMSDOE H35-1 WSC {primary} HOLDOUT-DTI {pooled(cells[primary]):.4f} "
            f"vs {pooled(cells[ctrl_for_note]):.4f} id {pr['cid']} {tail}")[:140]

    card = {
        "schema": "parallel-run-card-v2",
        "hypothesis_id": "H35-1",
        "hypothesis": "weak-scarp continuity (WSC) augmentation of the arm-D emission (candidate pool = detector ridges OR WSC ridges, priority = prob + 0.5*wsc_pct)",
        "mechanism": "orientation-coherent weak-moderate-amplitude LiDAR scarp continuity supplies ridge candidates the corroborated-ridge family never emitted on",
        "named_non_fault_mimic": "lithologic dip slopes and hogbacks, fluvial terrace risers, Lake Lahontan shoreline strandlines, avalanche chutes, graded-road berms",
        "layers": ["lidar_scarp_features_u8.tif step_max (band 3)", "lappos_max (band 5)", "ex_max (band 1)"],
        "verdict": verdict,
        "ok_to_submit": ok_submit,
        "ok_to_submit_reason": tail + " — " + primary_label,
        "holdout": {
            "label": "HOLDOUT-DTI",
            "evaluator": e2["evaluator"],
            "seeds": SEEDS,
            "n_withheld_positives_total": n_withheld,
            "pooled_B": e2["pooled_B"], "pooled_C0": e2["pooled_C0"], "pooled_C1": e2["pooled_C1"],
            "hypothesis_gate_C1_vs_C0": pair_c1_c0,
            "architecture_gate_C0_vs_B": pair_c0_b,
            "canary_max_auc": canary_max,
            "gate_efficacy_pass": hyp_pass,
        },
        "uniqueness_vs_registry": {
            "pass": pr["unique_pass"],
            "max_dot_overlap_within_3px_euclidean": pr["max_registry_overlap"],
            "max_postplacement_dot_spearman": pr["max_registry_dot_spearman"],
            "max_surface_spearman": float(max_abs_rho),
            "local_overlap": pr["uniqueness_local"],
        },
        "raster": {
            "primary_arm": primary, "primary_label": primary_label,
            "file": pr["tif"], "path": pr["tif_path"], "zip": pr["zip"], "nan_file": pr["nan_tif"],
            "sha256": pr["sha256"], "nan_sha256": pr["nan_sha256"], "n_dots": pr["n_dots"],
            "content_id": pr["cid"],
            "validator_allfinite": pr["checks"], "validator_nan": pr["nan_checks"],
        },
        "all_arms": {k: {"file": v["tif"], "sha256": v["sha256"], "n_dots": v["n_dots"],
                         "unique_pass": v["unique_pass"], "max_registry_overlap": v["max_registry_overlap"]}
                     for k, v in res.items()},
        "submission_name": f"27GEMSDOE-H35-{primary}-{DATE}-{pr['cid']}",
        "note_max_140_chars": note,
        "note_length": len(note),
        "preregistration_sha256": prereg_hash,
        "evidence": {"e1": str(E1_PATH.name), "e2": str(E2_PATH.name)},
        "projection_written_as_score": False,
    }
    CARD_PATH.write_text(json.dumps(card, indent=2, default=float) + "\n")
    print(json.dumps({"primary": primary, "ok_to_submit": ok_submit, "verdict": verdict,
                      "note": note}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
