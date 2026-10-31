"""Tests for the H35-1 weak-scarp continuity (WSC) constructor (label-free)."""

from __future__ import annotations

import numpy as np
import pytest

from gems27 import wsc_features as wsc


@pytest.fixture(scope="module")
def wsc_full():
    from gems27 import grid, paths

    foot = grid.load_footprint(paths.TEMPLATE)
    score, r_u8, g = wsc.wsc_score(grid.SHAPE)
    return foot, score, r_u8, g


def test_weak_gate_band_pass_and_tapers() -> None:
    v = np.array([0, 8, 18, 28, 74, 120, 130, 140, 200], np.float32)
    g = wsc.weak_gate(v)
    assert g[0] == 0.0 and g[1] == 0.0
    assert g[2] == pytest.approx(0.5, abs=1e-6)  # 28 - 10: middle of the low taper
    assert g[3] == 1.0 and g[4] == 1.0 and g[5] == 1.0
    assert g[6] == pytest.approx(0.5, abs=1e-6)  # 120 + 10
    assert g[7] == 0.0 and g[8] == 0.0
    assert np.all((g >= 0) & (g <= 1))


def test_weak_gate_is_monotone_in_tapers() -> None:
    low = wsc.weak_gate(np.linspace(8, 28, 9, dtype=np.float32))
    assert np.all(np.diff(low) >= -1e-6)
    high = wsc.weak_gate(np.linspace(120, 140, 9, dtype=np.float32))
    assert np.all(np.diff(high) <= 1e-6)


@pytest.mark.requires_rasters
def test_wsc_score_is_label_free_finite_and_gated(wsc_full) -> None:
    foot, score, r_u8, g = wsc_full
    assert score.shape == r_u8.shape == g.shape
    assert np.isfinite(score[foot]).all()
    assert score[foot].min() >= 0
    # score must vanish where the gate is closed
    closed = (g == 0) & foot
    assert float(score[closed].max()) == 0.0
    # 0 = no LiDAR is gate-closed
    nolidar = (r_u8 == 0) & foot
    assert float(score[nolidar].max()) == 0.0
    # anisotropy construction keeps score <= maxm <= 1
    assert score[foot].max() <= 1.0 + 1e-6


@pytest.mark.requires_rasters
def test_wsc_ridges_are_inside_footprint_and_sparse(wsc_full) -> None:
    foot, score, _, _ = wsc_full
    ridges = wsc.wsc_ridges(score, foot)
    assert ridges.shape == score.shape
    assert not bool((ridges & ~foot).any())
    assert 0 < int(ridges.sum()) < 0.2 * int(foot.sum())
