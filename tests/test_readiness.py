import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine

from gems27 import grid
from gems27.readiness import publication_decision


@pytest.fixture(autouse=True)
def tiny_grid(monkeypatch):
    monkeypatch.setattr(grid, "SHAPE", (4, 4))
    monkeypatch.setattr(grid, "BOUNDS", (243350.0, 4508150.0, 243750.0, 4508550.0))


def valid_card(tmp_path):
    f = tmp_path / "candidate.tif"
    with rasterio.open(f, "w", driver="GTiff", height=4, width=4, count=1,
                       dtype="float32", crs="EPSG:32611",
                       transform=Affine(*grid.TRANSFORM)) as dst:
        dst.write(np.zeros((4, 4), dtype=np.float32), 1)
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


@pytest.mark.parametrize("card", [None, [], True, "promote", 1])
def test_non_object_card_fails_closed(tmp_path, card):
    decision = publication_decision(card, tmp_path)
    assert not decision["ok_to_publish_as_submission"]
    assert "run card must be a JSON object" in decision["reasons"]
    assert decision["slot_authorized"] is False


@pytest.mark.parametrize("field", ["paired_delta_ci95", "pooled_delta", "baseline_ci"])
def test_impossible_dti_improvement_is_rejected(tmp_path, field):
    card = valid_card(tmp_path)
    comparison = card["holdout"]["current_best_comparison"]
    if field == "baseline_ci":
        card["holdout"]["paired_D_minus_B"]["ci95"] = [0.1, 1.01]
    elif field == "pooled_delta":
        comparison[field] = 1.01
    else:
        comparison[field] = [0.1, 1.01]
    assert not publication_decision(card, tmp_path)["ok_to_publish_as_submission"]


def test_audit_keeps_other_cards_when_evidence_is_malformed(tmp_path):
    import importlib.util

    script = Path(__file__).resolve().parents[1] / "scripts/audit_submission_readiness.py"
    spec = importlib.util.spec_from_file_location("audit_readiness", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "broken_run_card.json").write_text('{"verdict":')
    (evidence / "null_run_card.json").write_text('null')
    (evidence / "valid_run_card.json").write_text(json.dumps(valid_card(tmp_path)))
    report = module.audit_cards(tmp_path)
    assert len(report["results"]) == 3
    assert report["evidence_passed_not_slot_authorized"] == ["valid_run_card.json"]
    assert report["slot_authorized"] == []
    assert report["results"]["broken_run_card.json"]["reasons"] == [
        "unreadable run card: JSONDecodeError"
    ]
    assert not report["results"]["null_run_card.json"]["ok_to_publish_as_submission"]


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), -0.01, 1.01])
def test_self_reported_checks_cannot_hide_invalid_pixels(tmp_path, bad_value):
    card = valid_card(tmp_path)
    path = tmp_path / "candidate.tif"
    with rasterio.open(path, "r+") as dst:
        values = dst.read(1)
        values[-1, -1] = bad_value
        dst.write(values, 1)
    card["raster"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    result = publication_decision(card, tmp_path)
    assert "independent raster byte validation failed" in result["reasons"]


def test_matching_hash_and_forged_validator_cannot_approve_text(tmp_path):
    card = valid_card(tmp_path)
    path = tmp_path / "candidate.tif"
    path.write_bytes(b"not a GeoTIFF")
    card["raster"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    assert not publication_decision(card, tmp_path)["ok_to_publish_as_submission"]


def test_matching_hash_cannot_hide_wrong_crs(tmp_path):
    card = valid_card(tmp_path)
    path = tmp_path / "candidate.tif"
    with rasterio.open(path, "r+") as dst:
        dst.crs = "EPSG:4326"
    card["raster"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    assert not publication_decision(card, tmp_path)["ok_to_publish_as_submission"]


@pytest.mark.parametrize("name", ["bad\x00.tif", "../outside.tif"])
def test_invalid_raster_paths_fail_closed(tmp_path, name):
    card = valid_card(tmp_path)
    card["raster"]["primary_allfinite"] = name
    decision = publication_decision(card, tmp_path)
    assert not decision["ok_to_publish_as_submission"]
    assert "raster missing or outside repository" in decision["reasons"]
    assert decision["actual_sha256"] is None


def test_symlink_loop_fails_closed(tmp_path):
    card = valid_card(tmp_path)
    (tmp_path / "loop.tif").symlink_to("loop.tif")
    card["raster"]["primary_allfinite"] = "loop.tif"
    decision = publication_decision(card, tmp_path)
    assert not decision["ok_to_publish_as_submission"]
    assert "raster missing or outside repository" in decision["reasons"]
