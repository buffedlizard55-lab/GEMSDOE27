#!/usr/bin/env python3
"""H31 E3: build the unique rank-ensemble GeoTIFF + protocol run card (Session 10).

Preregistration: knowledge/23_preregistration_H31_2026-10-26.md. Full-footprint emission
from the quadrant-OOF rank-mean surface cached by scripts/run_h31_holdout.py, weighted CELF
cover, B2, 37,654 dots, all-finite primary (nodata=None, every cell in {0,1}) — the fix for
the portal error "Predicted values must be in range [0, 1]".

ok_to_submit = E2 frozen gate PASS AND uniqueness PASS (operative screen: 12 pinned peers +
GEMSDOE32 R6; overlaps vs this repo's own rasters reported alongside) AND shared-validator
hard PASS. The verdict is computed here into the run card; `gems27.readiness` re-checks it
fail-closed for the website badge. No human inspection; no live score claimed.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from scipy.ndimage import distance_transform_edt  # noqa: E402

import run_h29_holdout as h29run  # noqa: E402
from gems27 import paths, submission  # noqa: E402

BUDGET = 37_654
B_EXCL = 2.0
ENS_PATH = paths.DATA / "h31" / "ens_rankmean_surface.npy"
E1 = paths.EVIDENCE / "h31_e1_canary_and_surface.json"
E2 = paths.EVIDENCE / "h31_e2_holdout_260_269.json"
R6_PATH = paths.DATA / "parallel_registry_extra" / "g32_r6_step.tif"


def overlap(dots: np.ndarray, other: np.ndarray, r: float = 3.0) -> float:
    return float((distance_transform_edt(~other)[dots] <= r).mean()) if dots.any() else 0.0


def main() -> int:
    e1 = json.loads(E1.read_text())
    e2 = json.loads(E2.read_text())
    gate_ok = bool(e2["gate_e2_pass"]) and bool(e1["gate_e1_pass"])
    foot, labels, _ = h29run.load_base()
    ens = np.load(ENS_PATH)
    dots = h29run.emit_weighted_celf(ens, foot, labels, BUDGET)
    d_cat = distance_transform_edt(~labels)
    assert int(dots.sum()) == BUDGET, f"expected {BUDGET} dots, got {int(dots.sum())}"
    assert not (dots & labels).any(), "dot on catalogue"
    assert float(d_cat[dots].min()) > B_EXCL, "B2 violated"
    assert not (dots & ~foot).any(), "dot outside footprint"
    pred = dots.astype(np.float32)
    cid = submission.scored_content_id(pred, foot, labels)
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    stem = f"gems27-h31-rankens-celf-b2-{date}-{cid}"

    overlaps: dict[str, float] = {}
    peer_paths = sorted((paths.DATA / "parallel_registry").glob("*.tif"))
    if R6_PATH.exists():
        peer_paths.append(R6_PATH)
    for rp in peer_paths:
        with rasterio.open(rp) as s:
            a = s.read(1)
        overlaps[f"peer:{rp.name}"] = overlap(dots, np.isfinite(a) & (a > 0))
    peer_max = max(overlaps.values()) if overlaps else 0.0
    repo_overlaps: dict[str, float] = {}
    for d in (paths.DOCS / "downloads", paths.DOCS / "downloads" / "research"):
        for rp in sorted(d.glob("gems27-*-nan.tif")):
            if "gems27-h31-" in rp.name:
                continue
            with rasterio.open(rp) as s:
                a = s.read(1)
            repo_overlaps[f"repo:{rp.name}"] = overlap(
                dots, np.isfinite(a) & (a > 0.5))
    self_max = max(repo_overlaps.values()) if repo_overlaps else 0.0
    max_surf = float(e1["max_peer_abs_spearman"])
    unique_ok = bool(peer_max <= 0.70 and max_surf <= 0.90)

    promote_pre_format = bool(gate_ok and unique_ok)
    out_dir = paths.DOCS / "downloads" if promote_pre_format \
        else paths.DOCS / "downloads" / "research"
    out_dir.mkdir(parents=True, exist_ok=True)
    zeros_tif = out_dir / f"{stem}-allfinite.tif"
    nan_tif = out_dir / f"{stem}-nan.tif"
    submission.write_geotiff(pred, paths.TEMPLATE, zeros_tif, outside="zero")
    submission.write_geotiff(pred, paths.TEMPLATE, nan_tif, outside="nan")
    zip_path = submission.zip_single(zeros_tif)
    v_zeros = submission.verify_geotiff(zeros_tif, paths.TEMPLATE)
    v_nan = submission.verify_geotiff(nan_tif, paths.TEMPLATE)
    (out_dir / f"checks-{stem}-allfinite.json").write_text(
        json.dumps(v_zeros, indent=2) + "\n")
    (out_dir / f"checks-{stem}-nan.json").write_text(json.dumps(v_nan, indent=2) + "\n")
    format_ok = bool(v_zeros["hard_checks_passed"])
    ok_to_submit = bool(promote_pre_format and format_ok)
    verdict = "promote" if ok_to_submit else "negative"

    vs = e2["paired_comparisons_buffered"]["ENS_minus_H29S"]
    paired_generic = {"mean_delta": vs["mean_seed_paired_delta_dti"],
                      "ci95": vs["seed_bootstrap_95_ci"],
                      "cells_positive": vs["positive_cells"],
                      "n_cells": vs["n_cells"],
                      "comparator": "H29S (current repo holdout best, identical CELF emission)"}
    pooled = e2["pooled_buffered_holdout_dti"]
    status_txt = "UNSCORED" if ok_to_submit else "RESEARCH NEGATIVE DO NOT SUBMIT UNSCORED"
    note = (f"27GEMSDOE H31 rankENS CELF B2 37654; HOLDOUT-DTI {pooled['ENS']:.4f} "
            f"vs H29S {pooled['H29S']:.4f}; {status_txt} | id {cid}")
    assert len(note) <= 140, len(note)
    card = {
        "run_card": "H31 complementary OOF-surface rank ensemble (parallel-run protocol §5)",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis": "Two validated detectors encoding different physics (H29 hydrothermal/"
                      "piedmont surface vs Arm-D subsurface transforms) make complementary "
                      "fold-level errors; a 50/50 percentile-rank ensemble of their OOF "
                      "surfaces places B2/CELF mass better than either alone, catching "
                      "blind/buried faults each physics sees only partially.",
        "mechanism": "Quadrant-OOF surfaces (frozen H29 two-stage; D0 = 32 bands + 15 "
                     "subsurface transforms); within-footprint percentile ranks averaged "
                     "50/50; weighted 300 m CELF cover (gamma=1.5, min-sep 2.0 px); B2 "
                     "(>200 m from catalogue); 37,654 binary dots.",
        "named_non_fault_mimic": "Shared base-32 false lineaments reinforced by ensembling: "
                                 "lithologic contacts, Lake Lahontan shoreline benches, "
                                 "GeoDAWN survey seams, alluvial-fan edges.",
        "holdout": {"label": "HOLDOUT-DTI", "evaluator": e2["evaluator_version"],
                    "pooled_dti_ENS_lane": pooled["ENS"],
                    "pooled_dti_H29S_comparator": pooled["H29S"],
                    "pooled_dti_D0S_ablation": pooled["D0S"],
                    "paired_candidate_minus_B": paired_generic,
                    "paired_candidate_minus_H29S": paired_generic,
                    "paired_ENS_minus_D0S": e2["paired_comparisons_buffered"]["ENS_minus_D0S"],
                    "n_withheld_positives_total": e2["n_withheld_positive_occurrences"],
                    "seeds": e2["seeds"],
                    "canary_max_auc": e1["canary_max_direction_invariant_auc"],
                    "gate_efficacy_pass": gate_ok,
                    "gate_components": e2["frozen_gate_clauses"]},
        "uniqueness_vs_registry": {
            "max_dot_overlap_within_3px_euclidean": peer_max,
            "max_dot_overlap_peers_operative_12_plus_R6": peer_max,
            "max_dot_overlap_repo_self_screen_reported": self_max,
            "per_raster": overlaps,
            "per_raster_repo_self_reported": repo_overlaps,
            "max_surface_spearman": max_surf,
            "surface_spearman_per_peer": e1["peer_surface_spearman"],
            "thresholds": {"dot_overlap": 0.70, "spearman": 0.90},
            "pass": unique_ok},
        "raster": {"primary_allfinite": zeros_tif.name, "sha256": v_zeros["sha256"],
                   "bytes": v_zeros["bytes"], "dots": int(dots.sum()),
                   "content_id": cid, "zip": zip_path.name, "nan_twin": nan_tif.name,
                   "directory": str(out_dir.relative_to(paths.REPO))},
        "validator": {"zeros_hard_pass": format_ok, "zeros_checks": v_zeros["checks"],
                      "nan_hard_pass": bool(v_nan["hard_checks_passed"])},
        "submission_name": "GEMSDOE27-H31-RANKENS-CELF-B2",
        "note_max_140_chars": note,
        "note_chars": len(note),
        "ok_to_submit": ok_to_submit,
        "verdict": verdict,
        "live_score": None,
        "live_score_label": "UNSCORED — no ORGANIZER-CONFIRMED score exists for this file",
    }
    (paths.EVIDENCE / "h31_run_card.json").write_text(json.dumps(card, indent=2) + "\n")
    (out_dir / "h31_candidate_manifest.json").write_text(
        json.dumps({"stem": stem, **card}, indent=2) + "\n")
    (out_dir / f"note-{stem}-allfinite.txt").write_text(note + "\n")
    print(f"dots={int(dots.sum())} cid={cid} peer_max={peer_max:.3f} self_max={self_max:.3f} "
          f"max_surf={max_surf:.3f} gate={gate_ok} unique={unique_ok} format={format_ok} "
          f"-> verdict={verdict} ok={ok_to_submit}")
    print(f"wrote {zeros_tif} sha256={v_zeros['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
