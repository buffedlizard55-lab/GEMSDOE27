"""Tests for the per-link graph-connectivity value (Addendum D, D-3)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import graph_value as gv  # noqa: E402
from gems27.graph import build_graph  # noqa: E402


def _two_strands(gap: int, length: int = 40) -> np.ndarray:
    """Two collinear north-south strands of `length` px separated by `gap` px."""
    m = np.zeros((3 * length + gap + 10, 40), bool)
    m[5:5 + length, 20] = True
    m[5 + length + gap:5 + 2 * length + gap, 20] = True
    return m


def _ends(fg) -> tuple[int, np.ndarray, int, np.ndarray]:
    """The northern component's southernmost pixel and the southern component's northernmost pixel."""
    ids = sorted(set(fg.comp[fg.skeleton].tolist()) - {0})
    a, b = int(ids[0]), int(ids[-1])
    pa, pb = np.argwhere(fg.comp == a), np.argwhere(fg.comp == b)
    if pa[:, 0].mean() > pb[:, 0].mean():
        a, b, pa, pb = b, a, pb, pa
    return a, pa[int(np.argmax(pa[:, 0]))], b, pb[int(np.argmin(pb[:, 0]))]


def _link(fg, gap_px: float, dcol: int = 0) -> pd.DataFrame:
    """One synthetic straight link between the two closest tips of the two components."""
    a, pa, b, pb = _ends(fg)
    return pd.DataFrame([{"e_row": int(pa[0]), "e_col": int(pa[1]) + dcol, "comp_src": a,
                          "q_row": int(pb[0]), "q_col": int(pb[1]) + dcol, "comp_tgt": b,
                          "length_px": gap_px}])


def test_connectivity_P_reproduces_the_published_value():
    # evidence/graph_report.json: n_ge_lmin = 988 systems >= 2 km -> P = 5.784491473419016
    lengths = np.full(988, 2000.0)
    assert gv.connectivity_P(lengths) == pytest.approx(5.784491473419016, rel=1e-12)
    # P is linear in the count of systems above lmin once a and D are held fixed
    assert gv.connectivity_P(np.full(989, 2000.0)) - gv.connectivity_P(lengths) == pytest.approx(
        gv.connectivity_P(lengths) / 988.0, rel=1e-9)


def test_delta_P_is_quantised_by_the_count_of_systems_above_lmin():
    """dP = dn * P/n_ge with dn = [lA+lB+gap >= lmin] - [lA >= lmin] - [lB >= lmin], lmin = 2 km."""
    # two 4 km strands -> one 8.4 km system: dn = 1 - 1 - 1 = -1, so P FALLS (fewer long systems)
    fg = build_graph(_two_strands(gap=4, length=40), with_edges=False)
    v = gv.link_connectivity_values(fg, _link(fg, 4.0))
    assert len(v) == 1
    assert bool(v.bridge.iloc[0])                     # the only link: it must be a bridge
    assert v.merge_len_km.iloc[0] == pytest.approx(8.4, abs=0.2)
    assert v.delta_P.iloc[0] < 0
    assert v.delta_second_moment_km2.iloc[0] > 0      # sum l^2 still rises: continuity, unlike dP
    assert v.delta_largest_share.iloc[0] > 0
    assert int(v.connectivity_rank.iloc[0]) == 1

    # two 1 km strands -> one 2.4 km system: dn = 1 - 0 - 0 = +1, so P RISES
    fg2 = build_graph(_two_strands(gap=4, length=10), with_edges=False)
    v2 = gv.link_connectivity_values(fg2, _link(fg2, 4.0))
    assert v2.merge_len_km.iloc[0] == pytest.approx(2.4, abs=0.2)
    assert v2.delta_P.iloc[0] > 0
    assert v2.delta_second_moment_km2.iloc[0] < v.delta_second_moment_km2.iloc[0]
    # both are single-count changes, so |dP| is the same quantum P/n_ge
    assert abs(v2.delta_P.iloc[0]) == pytest.approx(abs(v.delta_P.iloc[0]), rel=1e-6)


def test_a_redundant_parallel_link_is_not_a_bridge_and_has_zero_value():
    fg = build_graph(_two_strands(gap=4, length=40), with_edges=False)
    L = pd.concat([_link(fg, 4.0), _link(fg, 4.0, dcol=1)], ignore_index=True)   # two parallel edges
    v = gv.link_connectivity_values(fg, L)
    assert len(v) == 2
    assert not bool(v.bridge.iloc[0]) and not bool(v.bridge.iloc[1])
    # dropping one of two parallel closures changes nothing about the merged network
    assert v.delta_P.iloc[0] == 0.0 and v.delta_P.iloc[1] == 0.0
    assert v.delta_second_moment_km2.iloc[0] == 0.0


def test_rank_is_dense_and_lexsorted():
    fg = build_graph(_two_strands(gap=4, length=40), with_edges=False)
    L = pd.concat([_link(fg, 4.0)] * 3, ignore_index=True)
    v = gv.link_connectivity_values(fg, L)
    assert sorted(v.connectivity_rank.tolist()) == [1, 2, 3]
