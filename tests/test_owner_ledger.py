"""Checks for registry/owner_reported_scores_20261030.csv.

The ledger holds OWNER-REPORTED values copied from the 2026-10-30 task prompt. These tests guard
against transcription slips (out-of-range scores, mislabelled blanks, focus-site maxima that
disagree with the prompt) and against a copied value contradicting the byte-level peer audit.
None of these values is an organizer receipt or a leaderboard estimate.
"""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "registry" / "owner_reported_scores_20261030.csv"
PEERS = ROOT / "evidence" / "peer_relations_20261028.json"

FOCUS_MAX_FROM_PROMPT = {  # highest owner-reported value per site, as written in the 2026-10-30 prompt
    "GEMSDOE24": 0.2477,
    "GEMSDOE25": 0.2600,
    "GEMSDOE27": 0.2449,
    "GEMSDOE28": 0.2710,
    "GEMSDOE30": 0.2600,
    "GEMSDOE31": 0.2708,
    "GEMSDOE32": 0.2778,
    "GEMSDOE33": 0.2632,
    "GEMSDOE36": 0.2750,
}


def _rows():
    with LEDGER.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_ledger_scores_are_in_unit_interval_and_labelled():
    rows = _rows()
    assert len(rows) == 160
    for r in rows:
        if r["owner_reported_score"]:
            v = float(r["owner_reported_score"])
            assert 0.0 <= v <= 1.0, r
            assert r["evidence_label"] == "OWNER-REPORTED", r
        else:
            assert r["evidence_label"] == "BLANK-IN-PROMPT", r


def test_blank_rows_count_matches_review():
    rows = _rows()
    assert sum(1 for r in rows if not r["owner_reported_score"]) == 22


def test_focus_site_maxima_match_prompt():
    best = {}
    for r in _rows():
        if r["owner_reported_score"]:
            v = float(r["owner_reported_score"])
            best[r["site"]] = max(best.get(r["site"], -1.0), v)
    for site, expected in FOCUS_MAX_FROM_PROMPT.items():
        assert abs(best[site] - expected) < 1e-9, (site, best[site], expected)


def test_highest_owner_reported_value_is_gemsdoe32():
    scored = [(float(r["owner_reported_score"]), r["site"]) for r in _rows()
              if r["owner_reported_score"]]
    assert max(scored) == (0.2778, "GEMSDOE32")


def test_identical_dot_pairs_have_identical_owner_scores():
    """Byte-identical in-footprint dot sets (evidence/peer_relations_20261028.json) must carry
    the same owner-reported value. A mismatch would mean a transcription error or a file mix-up.
    """
    peers = json.loads(PEERS.read_text(encoding="utf-8"))
    pairs = peers["identical_in_footprint_pairs"]
    assert pairs, "expected recorded identical pairs"
    site_for_peer = {"g25_d28": "GEMSDOE25", "g30_d28": "GEMSDOE30",
                     "g28_h27_4_r1": "GEMSDOE28", "g31_h27_4": "GEMSDOE31"}
    file_for_peer = {"g25_d28": "dotted-h19-5-d2-8-20261002-e56ea318af89-nan",
                     "g30_d28": "d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca",
                     "g28_h27_4_r1": "h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan",
                     "g31_h27_4": "h27-4-solo-d28-20261004-8acb75e1-nan"}
    scores = {r["file_label_as_listed"]: r["owner_reported_score"] for r in _rows()}
    for a, b in pairs:
        assert site_for_peer[a] and site_for_peer[b]
        assert float(scores[file_for_peer[a]]) == float(scores[file_for_peer[b]]), (a, b)
