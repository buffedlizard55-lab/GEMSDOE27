import hashlib
import json
from pathlib import Path

import pytest

from gems27.readiness import publication_decision


def valid_card(tmp_path):
    f = tmp_path / "candidate.tif"
    f.write_bytes(b"fixture; actual TIFF validation is separately tested")
    registry = tmp_path / "registry"
    registry.mkdir(exist_ok=True)
    (registry / "submitted_rasters.json").write_text(json.dumps({"entries": [
        {"sha256": "old-hash", "content_id": "old-content"}
    ]}))
    required = ("grid_matches_template", "single_band_float32", "inside_footprint_all_finite",
                "inside_footprint_in_0_1", "no_infinities_anywhere",
                "outside_footprint_is_zero_and_finite", "strict_whole_array_range")
    return {
        "ok_to_submit": True, "verdict": "promote",
        "holdout": {"label": "HOLDOUT-DTI", "evaluator": "test v1",
                    "n_withheld_positives_total": 100, "gate_efficacy_pass": True,
                    "paired_D_minus_B": {"ci95": [0.001, 0.01]}, "canary_max_auc": 0.6,
                    "split_scheme": "whole-fid-segment-v1", "visible_only_catalogue_features": True,
                    "training_buffer_verified": True, "emitter_blind_to_hidden_and_buffer": True,
                    "full_kernel_scored": True, "all_model_features_canary_tested": True,
                    "matched_current_best_comparison": True,
                    "current_best_comparison": {"control_id": "H31", "same_splits_and_buffer": True,
                                                "pooled_delta": 0.003, "paired_delta_ci95": [0.001, 0.01]}},
        "uniqueness_vs_registry": {"pass": True, "max_dot_overlap_within_3px_euclidean": 0.4,
            "max_surface_spearman": 0.5, "max_postplacement_dot_spearman": 0.5,
            "all_registry_entries_checked": True, "scope_current_and_complete": True},
        "validator": {"zeros_hard_pass": True,
                      "zeros_checks": {key: {"pass": True, "hard": True} for key in required}},
        "note_max_140_chars": "test",
        "raster": {"directory": ".", "primary_allfinite": f.name, "content_id": "new-content",
                   "sha256": hashlib.sha256(f.read_bytes()).hexdigest()}}


def test_recorded_pass_and_tamper(tmp_path):
    card = valid_card(tmp_path)
    assert publication_decision(card, tmp_path)["ok_to_publish_as_submission"]
    (tmp_path / "candidate.tif").write_bytes(b"tampered")
    assert not publication_decision(card, tmp_path)["ok_to_publish_as_submission"]


@pytest.mark.parametrize("field", ["holdout", "uniqueness_vs_registry", "validator", "raster"])
def test_boolean_alone_never_approves(tmp_path, field):
    card = valid_card(tmp_path)
    del card[field]
    assert not publication_decision(card, tmp_path)["ok_to_publish_as_submission"]
    card[field] = None
    assert not publication_decision(card, tmp_path)["ok_to_publish_as_submission"]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), 0.90001, 0.09999, -0.1, 1.1, True, None])
def test_canary_fails_closed(tmp_path, value):
    card = valid_card(tmp_path)
    card["holdout"]["canary_max_auc"] = value
    assert not publication_decision(card, tmp_path)["ok_to_publish_as_submission"]


@pytest.mark.parametrize("field", ["split_scheme", "visible_only_catalogue_features", "training_buffer_verified",
                                   "emitter_blind_to_hidden_and_buffer", "full_kernel_scored",
                                   "all_model_features_canary_tested", "matched_current_best_comparison"])
def test_missing_protocol_evidence_blocks(tmp_path, field):
    card = valid_card(tmp_path)
    del card["holdout"][field]
    assert not publication_decision(card, tmp_path)["ok_to_publish_as_submission"]


def test_duplicate_correlation_ci_and_missing_validator_gate(tmp_path):
    card = valid_card(tmp_path)
    del card["holdout"]["current_best_comparison"]
    assert not publication_decision(card, tmp_path)["ok_to_publish_as_submission"]
    card = valid_card(tmp_path)
    card["holdout"]["current_best_comparison"]["paired_delta_ci95"] = [-0.001, 0.01]
    assert not publication_decision(card, tmp_path)["ok_to_publish_as_submission"]
    card = valid_card(tmp_path)
    card["uniqueness_vs_registry"]["max_dot_overlap_within_3px_euclidean"] = 0.700001
    assert not publication_decision(card, tmp_path)["ok_to_publish_as_submission"]
    card = valid_card(tmp_path)
    card["uniqueness_vs_registry"]["max_surface_spearman"] = -0.900001
    assert not publication_decision(card, tmp_path)["ok_to_publish_as_submission"]
    card = valid_card(tmp_path)
    card["holdout"]["paired_D_minus_B"]["ci95"] = [-0.001, 0.01]
    assert not publication_decision(card, tmp_path)["ok_to_publish_as_submission"]
    card = valid_card(tmp_path)
    del card["validator"]["zeros_checks"]["strict_whole_array_range"]
    assert not publication_decision(card, tmp_path)["ok_to_publish_as_submission"]
    card = valid_card(tmp_path)
    card["validator"]["zeros_checks"]["unexpected"] = None
    assert not publication_decision(card, tmp_path)["ok_to_publish_as_submission"]


def test_reported_submitted_and_missing_ledger_fail_closed(tmp_path):
    card = valid_card(tmp_path)
    ledger = tmp_path / "registry/submitted_rasters.json"
    ledger.write_text(json.dumps({"entries": [{"sha256": "other", "content_id": "new-content"}]}))
    assert "raster reported already submitted" in publication_decision(card, tmp_path)["reasons"]
    ledger.unlink()
    assert not publication_decision(card, tmp_path)["ok_to_publish_as_submission"]


def test_existing_h31_is_blocked_as_reported_submitted():
    root = Path(__file__).resolve().parents[1]
    card = json.loads((root / "evidence/h31_s10_run_card_2026-10-26.json").read_text())
    decision = publication_decision(card, root)
    assert not decision["ok_to_publish_as_submission"]
    assert "raster reported already submitted" in decision["reasons"]
    assert "whole-FID split evidence missing" in decision["reasons"]
    assert decision["slot_authorized"] is False


@pytest.mark.parametrize("value", [0.1, 0.3, 0.4993, 0.9])
def test_canary_checks_both_directions_without_arbitrary_floor(tmp_path, value):
    card = valid_card(tmp_path)
    card["holdout"]["canary_max_auc"] = value
    decision = publication_decision(card, tmp_path)
    assert decision["ok_to_publish_as_submission"]
    assert decision["slot_authorized"] is False
