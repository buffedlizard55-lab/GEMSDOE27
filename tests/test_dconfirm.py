"""Lane L-DCONFIRM: preregistered gate arithmetic and run-card integrity (no rasters needed)."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _hold():
    return json.loads((ROOT / "evidence" / "dconfirm_holdout_2026-10-25.json").read_text())


def _card():
    return json.loads((ROOT / "evidence" / "dconfirm_run_card_2026-10-25.json").read_text())


def test_canary_clean_and_selection_rule():
    hold = _hold()
    assert max(hold["canary_auc_new_transforms"].values()) <= 0.90
    assert hold["canary_leak_flags"] == {}
    sel = hold["selection"]["pooled_holdout_dti"]
    # frozen selection rule (knowledge/15 §4): E preferred only if it beats B and ~matches D
    expect = "E" if (sel["E"] > sel["B"] and sel["E"] >= sel["D"] - 0.001) else \
        ("D" if sel["D"] > sel["B"] else None)
    assert hold["selection"]["candidate"] == expect


def test_confirmation_gate_arithmetic():
    conf = _hold()["confirmation"]
    assert conf is not None and conf["n_withheld_positives"] > 0
    s = conf["paired_candidate_minus_B"]
    pooled = conf["pooled_holdout_dti"]
    gate = (pooled[conf["candidate"]] > pooled["B"] and s["mean_delta"] >= 0.002
            and s["folds_positive"] >= 3 and s["seeds_positive"] >= 6)
    assert conf["gate_pass"] == gate


def test_run_card_badge_is_gate_driven():
    card = _card()
    u = card["uniqueness_vs_registry"]
    expect_ok = bool(card["holdout"]["confirmation"]["gate_pass"] and u["pass"]
                     and card["validator"]["zeros_hard_pass"])
    assert card["ok_to_submit"] == expect_ok
    assert card["verdict"] == ("promote" if expect_ok else "negative")
    assert card["live_score"] is None and "UNSCORED" in card["live_score_label"]
    assert len(card["note_max_140_chars"]) <= 140
    # decomposition must be reported, never collapsed silently
    assert u["max_dot_overlap_peer_registry_12"] <= u["max_dot_overlap_within_3px_euclidean"]
    assert u["peer_registry_pass"] == bool(
        u["max_dot_overlap_peer_registry_12"] < 0.70 and u["max_surface_spearman"] < 0.90)
    # the raster named in the card exists where the card says it does
    assert (ROOT / card["raster"]["directory"] / card["raster"]["primary_allfinite"]).is_file()
    man = json.loads((ROOT / "docs" / "downloads" / "dconfirm_candidate_manifest.json").read_text())
    assert man["raster"]["sha256"] == card["raster"]["sha256"]
    assert man["ok_to_submit"] == card["ok_to_submit"]
