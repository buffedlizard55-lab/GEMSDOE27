#!/usr/bin/env python3
"""Persist the frozen H28-6 E1/E2 result and finish E3 after the first TIFF writer failed.

This is a recovery script, not a new hypothesis experiment. It reuses the exact SHA-verified OOF
probability caches from the first completed E1/E2 execution, reruns the deterministic canary/metric
functions only to reconstruct evidence that the first process did not flush before its E3 writer error,
verifies cell DTI against `evidence/h28_6_first_execution.log`, then writes the negative research TIFF
using the corrected untiled writer. No model is refit, no feature/gate is changed, and no new seeds are
introduced. See IR-2026-10-25-07 in registry/irregularities.json.
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import run_h28_6_radiometric_holdout as h28_6  # noqa: E402
from gems27 import grid, holdout, paths  # noqa: E402

FIRST_LOG = paths.EVIDENCE / "h28_6_first_execution.log"
BASELINE_OOF = paths.PREPARED_FEATURES.parent / "h28_6_baseline_h28_1_oof_probabilities.npy"
BASELINE_META = paths.PREPARED_FEATURES.parent / "h28_6_baseline_h28_1_oof_probabilities.json"
CANDIDATE_OOF = paths.PREPARED_FEATURES.parent / "h28_6_candidate_h28_6_oof_probabilities.npy"
CANDIDATE_META = paths.PREPARED_FEATURES.parent / "h28_6_candidate_h28_6_oof_probabilities.json"


def require_cached_probability(path: Path, meta_path: Path, expected_arm: str) -> tuple[np.ndarray, dict]:
    meta = json.loads(meta_path.read_text())
    prob = np.load(path, mmap_mode="r")
    if meta.get("arm") != expected_arm or meta.get("probabilities_finite_and_in_0_1") is not True:
        raise SystemExit(f"Cached OOF metadata is not the expected {expected_arm} run")
    if h28_6.sha256_file(path) != meta.get("sha256"):
        raise SystemExit(f"Cached OOF checksum mismatch for {path.name}")
    if prob.shape != grid.SHAPE or prob.dtype != np.dtype("float32"):
        raise SystemExit(f"Cached OOF grid/dtype mismatch for {path.name}")
    foot = grid.load_footprint(paths.TEMPLATE)
    if not np.isfinite(prob[foot]).all() or np.any((prob[foot] < 0) | (prob[foot] > 1)):
        raise SystemExit(f"Cached OOF values invalid for {path.name}")
    return prob, meta


def expected_initial_dti() -> dict[tuple[int, int], tuple[str, str, str]]:
    text = FIRST_LOG.read_text()
    pattern = re.compile(r"seed (\d+) fold (\d+): ([0-9.]+) / ([0-9.]+) / ([0-9.]+)")
    matches = {(int(a), int(b)): (c, d, e) for a, b, c, d, e in pattern.findall(text)}
    if len(matches) != 40:
        raise SystemExit(f"Initial stdout log has {len(matches)} scored cells; expected exactly 40")
    return matches


def main() -> int:
    started = time.time()
    if h28_6.EVIDENCE_PATH.exists() or h28_6.RUN_CARD_PATH.exists():
        raise SystemExit("Final H28-6 evidence/run card already exists; recovery is not repeatable")
    if not FIRST_LOG.exists():
        raise SystemExit("First-execution log is missing; cannot establish the recovery cross-check")
    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    fold = holdout.make_quadrant_folds(foot)
    baseline, baseline_meta = require_cached_probability(BASELINE_OOF, BASELINE_META, "baseline_h28_1")
    candidate, candidate_meta = require_cached_probability(CANDIDATE_OOF, CANDIDATE_META, "candidate_h28_6")

    source_fields, source_valid, source_meta = h28_6._read_radiometric_sources(foot)
    rad_path = paths.PREPARED_FEATURES.parent / "h28_6_radiometric_edge_features.npy"
    rad_meta_path = paths.PREPARED_FEATURES.parent / "h28_6_radiometric_edge_features.json"
    rad_meta = json.loads(rad_meta_path.read_text())
    rad_matrix = np.load(rad_path, mmap_mode="r")
    if h28_6.sha256_file(rad_path) != rad_meta.get("sha256"):
        raise SystemExit("Radiometric feature-cache checksum mismatch during recovery")
    if rad_matrix.shape != tuple(rad_meta.get("shape", ())) or rad_matrix.dtype != np.dtype("float32"):
        raise SystemExit("Radiometric feature-cache shape/dtype mismatch during recovery")
    edge_path = paths.PREPARED_FEATURES.parent / "h28_1_edge_features.npy"
    edge_meta_path = paths.PREPARED_FEATURES.parent / "h28_1_edge_features.json"
    edge_meta = json.loads(edge_meta_path.read_text())
    edge_matrix = np.load(edge_path, mmap_mode="r")
    if h28_6.sha256_file(edge_path) != edge_meta.get("sha256"):
        raise SystemExit("H28-1 edge feature-cache checksum mismatch during recovery")
    if edge_matrix.shape != tuple(edge_meta.get("shape", ())) or edge_matrix.dtype != np.dtype("float32"):
        raise SystemExit("H28-1 edge feature-cache shape/dtype mismatch during recovery")
    augmented_path = paths.PREPARED_FEATURES.parent / "h28_6_augmented_features.npy"
    augmented_meta_path = paths.PREPARED_FEATURES.parent / "h28_6_augmented_features.json"
    augmented_meta = json.loads(augmented_meta_path.read_text())
    augmented = np.load(augmented_path, mmap_mode="r")
    if h28_6.sha256_file(augmented_path) != augmented_meta.get("sha256"):
        raise SystemExit("Augmented feature-cache checksum mismatch during recovery")
    if augmented.shape != tuple(augmented_meta.get("shape", ())) or augmented.dtype != np.dtype("float32"):
        raise SystemExit("Augmented feature-cache shape/dtype mismatch during recovery")

    print("Recovery: replaying only deterministic E1 safety checks against cached inputs...", flush=True)
    canary = h28_6.run_feature_canaries(foot, labels, fold, source_fields, source_valid, rad_matrix)
    if not canary["pass"]:
        raise SystemExit("Recovery canary differs from the first run's passing canary log")
    surface = h28_6.compare_surface_to_registry(candidate, foot, label="H28-6 recovered OOF candidate surface")
    if not surface["pass"]:
        raise SystemExit("Recovered OOF surface failed the pre-placement uniqueness stop")
    original_surface = {}
    for line in FIRST_LOG.read_text().splitlines():
        m = re.match(r"(g\d+_[a-z0-9_]+) ([0-9.]+)$", line.strip())
        if m:
            original_surface[m.group(1)] = m.group(2)
    if len(original_surface) != 12:
        raise SystemExit(f"First-execution log contains {len(original_surface)} surface rows, expected 12")
    surface_match = all(
        f"{row['spearman_rank_correlation']:.5f}" == original_surface.get(row["id"])
        for row in surface["entries"]
    )
    if not surface_match:
        raise SystemExit("Recovered pre-placement Spearman values differ from first execution log")

    print("Recovery: replaying frozen E2 metrics from the exact first-run OOF caches...", flush=True)
    holdout_result = h28_6.run_paired_holdout(foot, labels, fold, baseline, candidate)
    original_cells = expected_initial_dti()
    cell_match = True
    for cell in holdout_result["cell_results"]:
        key = (cell["seed"], holdout.FOLD_NAMES.index(cell["fold"]))
        now = tuple(f"{cell[name]['dti']:.5f}" for name in ("baseline", "candidate", "random_control"))
        cell_match &= now == original_cells[key]
    if not cell_match:
        raise SystemExit("Recovered per-cell DTI does not reproduce the original first-execution log")

    dots, emission = h28_6._build_research_dots(candidate, foot, labels)
    artifact = h28_6._write_allfinite_geotiff(dots, foot, status_slug="negative-research")
    uniqueness = h28_6.run_final_uniqueness(ROOT / artifact["path"])
    final_unique = bool(uniqueness.get("pass", False))
    status = "NEGATIVE RESEARCH ARTIFACT — NOT APPROVED FOR SUBMISSION"
    result = {
        "experiment": h28_6.EXPERIMENT,
        "preregistration": "knowledge/16_preregistration_H28-6.md",
        "integrity_recovery": {
            "initial_attempt": "E1/E2 completed; the original E3 GeoTIFF writer failed before evidence persistence.",
            "writer_error": "Inherited template block width 3292 was reused with tiled=True; TIFF tile dimensions must be multiples of 16.",
            "recovery_method": "Replayed deterministic E1 canaries and E2 DTI using the original SHA-verified cached OOF arrays; no model refit, feature change, threshold change, or seed change.",
            "original_stdout_log": "evidence/h28_6_first_execution.log",
            "surface_values_match_first_execution_log": surface_match,
            "all_40_cell_dti_values_match_first_execution_log_to_5_decimals": cell_match,
            "this_is_not_a_new_confirmation_or_independent_replication": True,
            "artifact_writer_fixed_to_untiled_geotiff": True,
        },
        "runtime_seconds_recovery": round(time.time() - started, 2),
        "seed_scan": {"seeds": list(h28_6.SEEDS), "status": "already consumed in first E1/E2 execution; this script is recovery-only"},
        "data_and_feature_integrity": {
            "prepared_features_sha256": h28_6.sha256_file(paths.PREPARED_FEATURES),
            "radiometric_sources": source_meta,
            "radiometric_feature_matrix": rad_meta,
            "h28_1_edge_matrix": edge_meta,
            "augmented_matrix": augmented_meta,
            "baseline_oof_cache_sha256": baseline_meta["sha256"],
            "candidate_oof_cache_sha256": candidate_meta["sha256"],
        },
        "e1": {"feature_only_canary": canary, "preplacement_surface_uniqueness": surface},
        "e2_holdout": holdout_result,
        "e3": {"full_fit_model_trained": False, "artifact_source": "cached 4-quadrant OOF candidate surface; negative research only"},
        "emission": emission,
        "artifact": artifact,
        "parallel_uniqueness_final": uniqueness,
        "eligibility": {"ok_to_submit": False, "status": status,
                         "reason": "H28-6 failed its frozen efficacy gate. This research artifact is not eligible for a weekly slot."},
        "verdict": "negative",
        "competition_score": None,
        "score_claim": "No leaderboard score is claimed; all measured DTI values are HOLDOUT-DTI only.",
        "within_two_hour_budget": "The original process completed without timeout; exact elapsed seconds were lost when its evidence flush was skipped by the E3 writer error. Recovery used cached model outputs and no refit.",
    }
    h28_6.write_json(h28_6.EVIDENCE_PATH, result)
    card = {
        "hypothesis": h28_6.EXPERIMENT,
        "mechanism": "Hydrothermal alteration can redistribute mobile elements and form spatial fronts in airborne radiometric rank grids; cross-channel edge geometry may reveal a buried or older fault without a catalogued young surface rupture.",
        "named_non_fault_mimic": "Lithologic/regolith contacts, airborne flight-line or processing seams, soil moisture, and non-tectonic hydrothermal alteration can create radiometric boundaries without faults.",
        "holdout": {"label": holdout_result["holdout_label"], "evaluator": holdout_result["evaluator"],
                    "withheld_positive_occurrences": holdout_result["withheld_positive_occurrences"],
                    "pooled_baseline": holdout_result["pooled_holdout_dti"]["baseline"],
                    "pooled_candidate": holdout_result["pooled_holdout_dti"]["candidate"],
                    "pooled_delta": holdout_result["candidate_minus_baseline_pooled_dti"],
                    "seed_level_mean_delta": holdout_result["paired_seed_summary"]["mean_seed_level_delta"],
                    "seed_bootstrap_95_ci": holdout_result["paired_seed_summary"]["ci95_seed_resampling"],
                    "positive_seeds": holdout_result["paired_seed_summary"]["positive_seeds"],
                    "positive_folds": sum(v > 0 for v in holdout_result["candidate_minus_baseline_by_fold"].values()),
                    "pooled_random_control": holdout_result["pooled_holdout_dti"]["random_control"],
                    "gate_pass": holdout_result["gate_pass"]},
        "leakage_canary": {"pass": canary["pass"], "threshold": h28_6.CANARY_THRESHOLD,
                            "max_direction_invariant_auc_by_feature": canary["max_direction_invariant_auc_by_feature"]},
        "parallel_uniqueness": {"preplacement_oof_surface": {"max_spearman": surface["max_correlation"], "duplicates": surface["duplicates"]},
                                "final_dots": {"pass": final_unique, "duplicates": uniqueness.get("duplicates", []),
                                               "entries": uniqueness.get("entries", [])}},
        "raster": {"path": artifact["path"], "sha256": artifact["sha256"], "content_id": artifact["content_id"],
                   "dots": artifact["positive_dots"], "artifact_source": "cached OOF candidate surface"},
        "validator": artifact["validator"],
        "submission": {"ok_to_submit": False, "status": status, "filename": Path(artifact["path"]).name,
                       "note_if_later_reviewed": "H28-6 radiometric fronts; research only, not slot-approved.",
                       "maximum_note_characters": 140},
        "verdict": "negative",
        "integrity_recovery": result["integrity_recovery"],
        "limitations": ["Catalogue-internal holdout is not organizer-created expert truth.",
                        "GeoDAWN bytes are hash-pinned owner-repository mirrors, not freshly downloaded official bytes.",
                        "No weekly slot, upload, organizer receipt, or leaderboard score is claimed."],
    }
    h28_6.write_json(h28_6.RUN_CARD_PATH, card)
    print(json.dumps({"pooled_holdout_dti": holdout_result["pooled_holdout_dti"],
                      "paired_seed_summary": holdout_result["paired_seed_summary"],
                      "pooled_delta": holdout_result["candidate_minus_baseline_pooled_dti"],
                      "gate_pass": holdout_result["gate_pass"], "surface_match": surface_match,
                      "cell_match": cell_match, "final_unique": final_unique,
                      "artifact": artifact["path"], "eligibility": status}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
