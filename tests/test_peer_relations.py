"""Synthetic tests for scripts/verify_peer_relations.py (no restored rasters needed).

The script's subset and identity logic is what establishes the GEMSDOE32 collar account, so it is
tested on a tiny hand-built grid where every removed dot and its catalogue distance is known.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("verify_peer_relations", ROOT / "scripts" / "verify_peer_relations.py")
vpr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vpr)


def _peer(pid: str, values: np.ndarray) -> dict:
    return {
        "entry": {"id": pid, "repo": "owner/" + pid, "commit": "0" * 40, "path": f"{pid}.tif",
                  "claimed_score": None, "score_label": "test"},
        "file": Path(f"/nonexistent/{pid}.tif"),
        "sha256": "0" * 64,
        "values": values,
        "crs": None,
        "shape": values.shape,
        "transform": None,
    }


def _grid():
    foot = np.ones((9, 9), dtype=bool)
    foot[8, 8] = False  # one cell outside the footprint
    catalogue = np.zeros((9, 9), dtype=bool)
    catalogue[4, 0] = True  # single catalogue cell
    return foot, catalogue


def _values(dots: list[tuple[int, int]], foot: np.ndarray, outside: float) -> np.ndarray:
    v = np.zeros((9, 9), dtype=np.float32)
    for r, c in dots:
        v[r, c] = 1.0
    v[~foot] = outside
    return v


def test_subset_stats_counts_removed_dots_by_catalogue_distance():
    foot, cat = _grid()
    parent = np.zeros((9, 9), bool)
    child = np.zeros((9, 9), bool)
    parent[4, 1] = parent[4, 4] = parent[0, 8] = True  # distances 1, 4, ~8 from (4,0)
    child[4, 4] = child[0, 8] = True                   # (4,1) removed
    st = vpr._subset_stats(parent, child, cat)
    assert st["parent_dots"] == 3 and st["child_dots"] == 2 and st["removed_dots"] == 1
    assert st["removed_dots_catalogue_distance_px"]["<= 1px"] == 1
    assert st["removed_dots_catalogue_distance_px"]["<= 2px"] == 1
    assert st["min_catalogue_distance_of_kept_dots_px"] == 4.0


def test_analyse_finds_identity_across_nan_and_zero_encodings_and_strict_subset():
    foot, cat = _grid()
    a_dots = [(4, 1), (4, 4), (0, 8)]
    peers = {
        "A_nan": _peer("A_nan", _values(a_dots, foot, np.nan)),
        "A_zero": _peer("A_zero", _values(a_dots, foot, 0.0)),   # same in-footprint values
        "B_sub": _peer("B_sub", _values([(4, 4), (0, 8)], foot, np.nan)),  # A minus (4,1)
    }
    res = vpr.analyse(peers, None, foot, cat)
    assert ["A_nan", "A_zero"] in res["identical_in_footprint_pairs"]
    subs = [s for s in res["strict_subset_relations"] if s["child"] == "B_sub"]
    assert subs and subs[0]["parent"] in {"A_nan", "A_zero"}
    assert subs[0]["removed_dots"] == 1
    # a child never reports itself as parent: B_sub is not a superset of anything
    assert not [s for s in res["strict_subset_relations"] if s["parent"] == "B_sub"]


def test_candidate_overlap_is_directed_and_identical_candidate_scores_full_overlap():
    foot, cat = _grid()
    dots = [(4, 1), (4, 4), (0, 8)]
    peers = {"A": _peer("A", _values(dots, foot, np.nan))}
    cand = _values(dots, foot, 0.0) == 1
    res = vpr.analyse(peers, cand, foot, cat)
    row = res["candidate_vs_peers"]["A"]
    assert row["exact_overlap_dots"] == 3
    assert row["dot_overlap_within_3px"] == 1.0
