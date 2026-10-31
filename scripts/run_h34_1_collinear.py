#!/usr/bin/env python3
"""E1-E3 for H34-1 hot-station collinearity corridors (knowledge/45, Addendum A).

Preregistration: knowledge/45_preregistration_H34-1_2026-10-31.md (committed before this file ran).
Reuses the shared holdout, metric, emission, canary and writer code from scripts/run_h33_lane.py
and gems27.holdout / gems27.metric / gems27.submission. Nothing here forks the evaluator.

Every number is HOLDOUT-DTI (catalogue-internal, not an organizer score). Promotion requires the
registered E1-E3 gates AND the Addendum A cluster-preserving null (A2).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import time
from pathlib import Path
from subprocess import run

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems27 import grid, holdout, paths, submission  # noqa: E402
from gems27 import hot_station_lines as hsl  # noqa: E402

_spec = importlib.util.spec_from_file_location("run_h33_lane", ROOT / "scripts" / "run_h33_lane.py")
h33 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(h33)

SEEDS = list(range(900, 910))
BUFFER_PX = 6.0
NULL_SEED = 45
PREREG = ROOT / "knowledge" / "45_preregistration_H34-1_2026-10-31.md"
E1_PATH = paths.EVIDENCE / "h34_1_e1_canary_collinearity_900_909.json"
E2_PATH = paths.EVIDENCE / "h34_1_e2_holdout_900_909.json"
CARD_PATH = paths.EVIDENCE / "h34_1_run_card_2026-10-31.json"
UNIQ_PATH = paths.EVIDENCE / "h34_1_uniqueness_vs_registry.json"
RESEARCH = paths.DOCS / "downloads" / "research"
DATE = "20261031"


def sha256_file(path: Path) -> str:
    return hashlib.file_digest(path.open("rb"), "sha256").hexdigest()


def main() -> int:
    t0 = time.time()
    if not PREREG.is_file():
        raise SystemExit("preregistration missing; refusing to run")
    prereg_hash = sha256_file(PREREG)
    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    base = np.load(paths.PREPARED_FEATURES, mmap_mode="r")
    if base.shape != (int(foot.sum()), 32):
        raise SystemExit(f"prepared stack shape {base.shape} is not the cached 32-band matrix")

    group, group_stats = h33.load_group_map(labels)
    union, registry_ids = h33.registry_positive_union(foot)
    complement_block = distance_transform_edt(~union) <= 3.0

    # ---- H34-1 operator (label-free; uses only station coordinates and T) ----
    st = hsl.station_table(paths.WELLSPRING)
    rows, cols, temps = st["row"].to_numpy(), st["col"].to_numpy(), st["T"].to_numpy()
    lines = hsl.accepted_lines(rows, cols, temps)
    S, L = hsl.line_surface(lines, foot)
    n_hot = int((temps >= hsl.HOT_T_C).sum())
    n_ge3_real = sum(1 for ln in lines if ln["support"] >= 3)

    uniform_null = hsl.permuted_null_line_counts(len(st), temps, foot, n_perm=5, seed=NULL_SEED)
    jitter = hsl.jitter_null_counts(rows, cols, temps, foot, radius_px=10.0, n_draws=20, seed=NULL_SEED)
    jit_total = np.array([j[0] for j in jitter], float)
    jit_ge3 = np.array([j[1] for j in jitter], float)
    ratio_total = len(lines) / max(jit_total.mean(), 1e-9)
    ratio_ge3 = n_ge3_real / max(jit_ge3.mean(), 1e-9)
    a2_pass = bool(ratio_total > 1.5 and ratio_ge3 > 1.5)
    uniform_pass = bool(len(lines) > 1.5 * float(np.mean(uniform_null)))

    # ---- E1: canary + pre-placement surface ----
    hidden_any = np.zeros_like(labels)
    splits = []
    for seed in SEEDS:
        split = holdout.make_segment_split(labels, foot, group, seed=seed, frac=0.20)
        splits.append(split)
        hidden_any |= split.hidden
    pos = np.flatnonzero(hidden_any[foot])
    neg_all = np.flatnonzero((~labels & foot & ~hidden_any)[foot])
    neg = np.random.default_rng(900).choice(neg_all, size=min(250_000, neg_all.size), replace=False)
    raw_auc, canary_auc = h33.canary_auc(S[foot], pos, neg)
    sample = np.random.default_rng(46).choice(np.flatnonzero(foot.ravel()), size=400_000, replace=False)
    rho = h33.surface_spearman(S, foot, sample)
    max_abs_rho = max(abs(v) for v in rho.values())
    leak = canary_auc > 0.90
    dup = max_abs_rho > 0.90
    e1_pass = bool(uniform_pass and not leak and not dup)
    e1 = {
        "experiment": "E1 H34-1 canary, pre-placement surface, registered collinearity null",
        "label": "HOLDOUT-DTI setup only; no organizer score",
        "preregistration_sha256": prereg_hash,
        "seeds": SEEDS,
        "stations_after_qa": int(len(st)),
        "hot_stations": n_hot,
        "accepted_lines": len(lines),
        "accepted_lines_support_ge3": n_ge3_real,
        "uniform_null_line_counts": uniform_null,
        "uniform_null_pass_registered": uniform_pass,
        "addendum_a_jitter_radius_px": 10.0,
        "addendum_a_jitter_totals_mean": float(jit_total.mean()),
        "addendum_a_jitter_ge3_mean": float(jit_ge3.mean()),
        "addendum_a_ratio_total": ratio_total,
        "addendum_a_ratio_ge3": ratio_ge3,
        "addendum_a2_pass": a2_pass,
        "canary_auc_raw": raw_auc,
        "canary_auc_direction_invariant": canary_auc,
        "canary_leak": bool(leak),
        "surface_spearman_vs_12_pinned": rho,
        "max_abs_surface_spearman": max_abs_rho,
        "duplicate_stop": bool(dup),
        "group_map": group_stats,
        "gate_e1_pass_registered": e1_pass,
        "runtime_s": round(time.time() - t0, 1),
    }
    E1_PATH.write_text(json.dumps(e1, indent=2) + "\n")
    print(json.dumps({k: e1[k] for k in ["accepted_lines", "uniform_null_pass_registered",
                                          "addendum_a_ratio_total", "addendum_a_ratio_ge3",
                                          "canary_auc_direction_invariant", "max_abs_surface_spearman",
                                          "gate_e1_pass_registered"]}), flush=True)
    if not e1_pass:
        card = {"schema": "parallel-run-card-v2", "hypothesis_id": "H34-1", "verdict": "negative",
                "ok_to_submit": False, "slot_authorized": False, "stop_reason":
                "E1 registered gate failed (canary, duplicate or uniform null)", "raster": None}
        CARD_PATH.write_text(json.dumps(card, indent=2) + "\n")
        return 2

    # ---- E2: whole-FID buffered holdout, candidate vs matched control B_c (and B_u) ----
    cells_c, cells_bc, cells_bu = [], [], []
    fold_c = {n: [] for n in holdout.FOLD_NAMES}
    fold_bc = {n: [] for n in holdout.FOLD_NAMES}
    folds = holdout.make_quadrant_folds(foot)
    y = labels[foot].astype(np.uint8)
    for seed, split in zip(SEEDS, splits, strict=True):
        train = holdout.buffered_training_mask(split, foot, buffer_px=BUFFER_PX)[foot]
        pb = h33.scatter(h33.fit_predict(base, y, train, seed=seed), foot)
        known = split.known
        pred_c = h33.emit(S, foot, known, complement_block)
        pred_bc = h33.emit(pb, foot, known, complement_block)
        pred_bu = h33.emit(pb, foot, known, None)
        cells_c.append(h33.score_cell(pred_c, split, foot))
        cells_bc.append(h33.score_cell(pred_bc, split, foot))
        cells_bu.append(h33.score_cell(pred_bu, split, foot))
        for fid, fname in enumerate(holdout.FOLD_NAMES):
            fold_c[fname].append(h33.score_cell(pred_c, split, foot, folds == fid))
            fold_bc[fname].append(h33.score_cell(pred_bc, split, foot, folds == fid))
        print(f"seed {seed} C {cells_c[-1]['dti']:.4f} Bc {cells_bc[-1]['dti']:.4f} "
              f"Bu {cells_bu[-1]['dti']:.4f} dotsC {int(pred_c.sum())} dotsBc {int(pred_bc.sum())}",
              flush=True)
        del pb, pred_c, pred_bc, pred_bu

    pair = h33.paired(cells_c, cells_bc)
    pair_u = h33.paired(cells_c, cells_bu)
    per_fold = {n: h33.pooled(fold_c[n]) - h33.pooled(fold_bc[n]) for n in holdout.FOLD_NAMES}
    pair["per_fold_pooled_delta_dti"] = per_fold
    pair["positive_folds"] = int(sum(v > 0 for v in per_fold.values()))
    pair["n_folds"] = 4
    n_withheld = int(sum(c["n_truth"] for c in cells_c))
    efficacy = bool(
        pair["mean_seed_paired_delta_dti"] >= 0.001
        and pair["ci95"][0] > 0
        and pair["positive_seeds"] >= 7
        and pair["positive_folds"] >= 3
        and h33.pooled(cells_c) > h33.pooled(cells_bc)
    )
    e2 = {
        "experiment": "E2 H34-1 whole-segment buffered holdout",
        "label": "HOLDOUT-DTI",
        "evaluator": "gems27.metric.dti_binary v1 (alpha=0.2, beta=0.8, R=3px triangular) + whole-FID buffered holdout (buffer_px=6)",
        "seeds": SEEDS,
        "n_cells": len(cells_c),
        "n_withheld_positive_occurrences": n_withheld,
        "pooled_candidate_H34_1": h33.pooled(cells_c),
        "pooled_matched_control_Bc": h33.pooled(cells_bc),
        "pooled_secondary_control_Bu": h33.pooled(cells_bu),
        "paired_candidate_minus_Bc": pair,
        "paired_candidate_minus_Bu": pair_u,
        "gate_efficacy_pass": efficacy,
        "cells_candidate": cells_c,
        "cells_matched_control_Bc": cells_bc,
        "cells_secondary_control_Bu": cells_bu,
        "runtime_s": round(time.time() - t0, 1),
    }
    E2_PATH.write_text(json.dumps(e2, indent=2) + "\n")
    print(json.dumps({"pooled_C": e2["pooled_candidate_H34_1"], "pooled_Bc": e2["pooled_matched_control_Bc"],
                      "efficacy": efficacy}), flush=True)

    # ---- E3: placement, writer, uniqueness, promotion decision ----
    known_all = labels & foot
    dots = h33.emit(S, foot, known_all, complement_block)
    if int((dots & known_all).sum()) != 0 or float(distance_transform_edt(~known_all)[dots].min()) <= h33.B_EXCL:
        raise RuntimeError("emission violated catalogue exclusion")
    pred = dots.astype(np.float32)
    cid = submission.scored_content_id(pred, foot, known_all)
    # Write once to a temp stem to run the checks, then name the file with its verdict.
    tmp_stem = f"gems27-h34-1-hotline-tmp-{DATE}-{cid}"
    RESEARCH.mkdir(parents=True, exist_ok=True)
    tmp_tif = submission.write_geotiff(pred, paths.TEMPLATE, RESEARCH / f"{tmp_stem}-allfinite.tif", outside="zero")
    with tempfile.TemporaryDirectory() as tdir:
        surf_tif = Path(tdir) / "h34_1_surface.tif"
        with rasterio.open(paths.TEMPLATE) as tmpl:
            prof = tmpl.profile.copy()
        prof.update(driver="GTiff", count=1, dtype="float32", nodata=None, compress="deflate")
        with rasterio.open(surf_tif, "w", **prof) as dst:
            dst.write(np.where(foot, S, 0.0).astype(np.float32), 1)
        surf_json = paths.EVIDENCE / "h34_1_uniqueness_surface_only.json"
        proc_s = run([sys.executable, str(ROOT / "scripts" / "check_parallel_uniqueness.py"), str(surf_tif),
                      "--surface-only", "--out", str(surf_json)], check=False, cwd=ROOT)
    proc = run([sys.executable, str(ROOT / "scripts" / "check_parallel_uniqueness.py"), str(tmp_tif),
                "--out", str(UNIQ_PATH)], check=False, cwd=ROOT)
    uniq = json.loads(UNIQ_PATH.read_text()) if UNIQ_PATH.exists() else {"pass": False, "duplicates": ["checker-failed"], "entries": []}
    suniq = json.loads(surf_json.read_text()) if surf_json.exists() else {"pass": False, "entries": []}
    max_overlap = max((en["candidate_dot_fraction_within_3px"] for en in uniq.get("entries", [])), default=1.0)
    max_rho_final = max((abs(en["spearman_rank_correlation"]) for en in uniq.get("entries", [])), default=1.0)
    max_rho_surface = max((abs(en["spearman_rank_correlation"]) for en in suniq.get("entries", [])), default=1.0)
    surf_pass = bool(suniq.get("pass")) and proc_s.returncode == 0 and max_rho_surface <= 0.90
    local = h33.local_overlap(dots, foot, skip_names={tmp_tif.name})
    unique_pass = bool(uniq.get("pass")) and local["pass"] and surf_pass and proc.returncode == 0

    promote = bool(e1_pass and efficacy and unique_pass and a2_pass)
    verdict = "promote" if promote else "negative"
    label = "GATE-PASSED-SELECTOR-REQUIRED" if promote else "NOT-OK-TO-SUBMIT"
    stem = f"gems27-h34-1-hotline-{label}-{DATE}-{cid}"
    for p in RESEARCH.glob(f"gems27-h34-1-hotline-tmp-{DATE}-{cid}*"):
        p.unlink()
    tif = submission.write_geotiff(pred, paths.TEMPLATE, RESEARCH / f"{stem}-allfinite.tif", outside="zero")
    nan_tif = submission.write_geotiff(pred, paths.TEMPLATE, RESEARCH / f"{stem}-nan.tif", outside="nan")
    zpath = submission.zip_single(tif)
    checks = submission.verify_geotiff(tif, paths.TEMPLATE)
    nan_checks = submission.verify_geotiff(nan_tif, paths.TEMPLATE)
    (RESEARCH / f"checks-{stem}-allfinite.json").write_text(json.dumps(checks, indent=2) + "\n")
    local = h33.local_overlap(dots, foot, skip_names={tif.name, nan_tif.name})
    unique_pass = bool(uniq.get("pass")) and local["pass"] and surf_pass and proc.returncode == 0
    note = (f"H34-1 hot-station line {int(dots.sum())}px HOLDOUT-DTI {e2['pooled_candidate_H34_1']:.4f} "
            f"vs Bc {e2['pooled_matched_control_Bc']:.4f} | id {cid} | {'NOT OK TO SUBMIT' if not promote else 'selector required'}")[:140]
    (RESEARCH / f"note-{stem}-allfinite.txt").write_text(note + "\n")
    card = {
        "schema": "parallel-run-card-v2",
        "generated_utc": "2026-10-31",
        "lane": "self-selected H34-1 (lane paragraph absent: IR-2026-10-31-lane-paragraph-missing)",
        "hypothesis_id": "H34-1",
        "hypothesis": "Hot-station (quartz geothermometer >=120 C) collinearity lines, 1.5-6 km, >=3 hot stations within 300 m",
        "mechanism": "Hot fluid concentrates in permeable structure; stations aligned along it can mark a buried trace",
        "named_non_fault_mimic": "water-well alignments along roads, field boundaries, irrigation ditches; valley-axis regional aquifer discharge; sampling bias",
        "verdict": verdict,
        "ok_to_submit": bool(promote),
        "slot_authorized": False,
        "submission_name": f"27GEMSDOE-H34-1-HOTLINE-{DATE}-{cid}",
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
            "pooled_candidate": e2["pooled_candidate_H34_1"],
            "pooled_matched_control_Bc": e2["pooled_matched_control_Bc"],
            "pooled_secondary_control_Bu": e2["pooled_secondary_control_Bu"],
            "paired_candidate_minus_Bc": pair,
            "paired_candidate_minus_Bu_informational": pair_u,
            "gate_efficacy_pass": efficacy,
            "ci95": pair["ci95"],
        },
        "e1_gates": {
            "uniform_null_pass_registered": uniform_pass,
            "addendum_a2_cluster_null_pass": a2_pass,
            "addendum_a_ratio_total": ratio_total,
            "addendum_a_ratio_ge3": ratio_ge3,
            "canary_auc_direction_invariant": canary_auc,
            "max_abs_surface_spearman": max_abs_rho,
        },
        "uniqueness_vs_registry": {
            "pass": unique_pass,
            "registry_checker_pass": bool(uniq.get("pass")),
            "max_dot_overlap_within_3px_euclidean": max_overlap,
            "max_surface_spearman": max_rho_surface,
            "max_postplacement_dot_spearman": max_rho_final,
            "surface_mode_pass": surf_pass,
            "duplicates": uniq.get("duplicates", []),
            "local_prior_rasters": local,
            "scope": "12 pinned registry rasters plus local docs/downloads rasters only; not the 113 owner repositories",
        },
        "validator": {
            "zeros_hard_pass": bool(checks["hard_checks_passed"]),
            "zeros_checks": checks["checks"],
            "nan_hard_pass": bool(nan_checks["hard_checks_passed"]),
            "sha256": checks["sha256"],
        },
        "raster": {
            "primary_allfinite": tif.name,
            "nan_twin": nan_tif.name,
            "zip": zpath.name,
            "directory": "docs/downloads/research",
            "sha256": checks["sha256"],
            "dots": int(dots.sum()),
            "content_id": cid,
        },
        "download_decision": ("NOT OK TO SUBMIT. Research artifact only; a gate failed (see e1_gates and holdout)."
                              if not promote else
                              "All gates passed. A separate selector must still authorize a weekly slot; this session does not upload."),
        "runtime_s": round(time.time() - t0, 1),
    }
    CARD_PATH.write_text(json.dumps(card, indent=2) + "\n")
    print(json.dumps({"verdict": verdict, "dots": int(dots.sum()), "sha": checks["sha256"][:16],
                      "file": tif.name, "unique": unique_pass}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
