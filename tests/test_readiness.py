import hashlib
import json
from pathlib import Path

import pytest

from gems27.readiness import publication_decision


def valid_card(tmp_path):
    f = tmp_path / "candidate.tif"
    f.write_bytes(b"fixture; validator is separately tested with actual rasters")
    return {"ok_to_submit": True, "verdict": "promote",
            "holdout": {"label": "HOLDOUT-DTI", "evaluator": "test v1",
                        "n_withheld_positives_total": 100, "gate_efficacy_pass": True,
                        "paired_D_minus_B": {"ci95": [0.001, 0.01]}, "canary_max_auc": 0.6},
            "uniqueness_vs_registry": {"pass": True,
                "max_dot_overlap_within_3px_euclidean": 0.4, "max_surface_spearman": 0.5},
            "validator": {"zeros_hard_pass": True,
                          "zeros_checks": {"range": {"pass": True, "hard": True}}},
            "note_max_140_chars": "test",
            "raster": {"directory": ".", "primary_allfinite": f.name,
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


@pytest.mark.parametrize("value", [float("nan"), float("inf"), 0.90001, True, None])
def test_canary_fails_closed(tmp_path, value):
    card = valid_card(tmp_path)
    card["holdout"]["canary_max_auc"] = value
    assert not publication_decision(card, tmp_path)["ok_to_publish_as_submission"]


def test_duplicate_and_ci_gate(tmp_path):
    card = valid_card(tmp_path)
    card["uniqueness_vs_registry"]["max_dot_overlap_within_3px_euclidean"] = 0.700001
    assert not publication_decision(card, tmp_path)["ok_to_publish_as_submission"]
    card = valid_card(tmp_path)
    card["holdout"]["paired_D_minus_B"]["ci95"] = [-0.001, 0.01]
    assert not publication_decision(card, tmp_path)["ok_to_publish_as_submission"]


def test_all_existing_cards_remain_unapproved():
    root = Path(__file__).resolve().parents[1]
    for p in (root / "evidence").glob("*run_card*.json"):
        assert not publication_decision(json.loads(p.read_text()), root)["ok_to_publish_as_submission"]
