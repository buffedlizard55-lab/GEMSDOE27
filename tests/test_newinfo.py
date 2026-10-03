"""Tests for the Addendum-D new-information bands and the step-over link rule."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import newinfo  # noqa: E402
from gems27.graph import build_graph  # noqa: E402


def test_shift_is_zero_filled_and_exact():
    a = np.arange(25, dtype=np.float32).reshape(5, 5)
    s = newinfo._shift(a, 1, 2)
    assert s[0].sum() == 0 and s[:, :2].sum() == 0
    assert s[1, 2] == a[0, 0] and s[4, 4] == a[3, 2]
    assert newinfo._shift(a, 99, 0).sum() == 0


def test_oriented_mean_is_exact_over_the_line():
    a = np.zeros((9, 9), np.float32)
    a[4, :] = 10.0                      # an east-west line
    om = newinfo.oriented_means(a, 0, 1, scales=(3,))
    assert om[3][4, 4] == pytest.approx(10.0)          # all 7 samples on the line are 10
    om_ns = newinfo.oriented_means(a, 1, 0, scales=(3,))
    assert om_ns[3][4, 4] == pytest.approx(10.0 / 7.0)  # north-south sees one line pixel in 7


def test_directional_bands_pick_out_the_true_orientation_and_are_anisotropic():
    img = np.zeros((60, 60), np.float32)
    for k in range(-25, 26):            # a 45-degree lineament
        img[30 + k, 30 + k] = 100.0
    bands = newinfo.directional_lineament_bands({"t": img}, scales=(5,))
    mx = bands["dir_t_max_L5"]
    an = bands["dir_t_aniso_L5"]
    assert mx[30, 30] > 20.0
    # on the line the 45-degree orientation dominates strongly -> high anisotropy
    assert an[30, 30] > 0.5
    # an isotropic blob has near-zero anisotropy at its centre
    yy, xx = np.mgrid[0:60, 0:60]
    blob = np.exp(-((yy - 30) ** 2 + (xx - 30) ** 2) / 50.0).astype(np.float32)
    b2 = newinfo.directional_lineament_bands({"t": blob}, scales=(5,))
    assert b2["dir_t_aniso_L5"][30, 30] < 0.1


def test_band_names_match_the_preregistration():
    names = newinfo.variant_bands("dir", {})
    assert len(names) == 24
    assert len(set(names)) == 24
    assert names[0] == "dir_lidar_lappos_max_max_L5"
    assert len(newinfo.variant_bands("all", {})) == 8 + 3 + 5 + 24
    assert newinfo.variant_bands("base", {}) == []


def _two_parallel_strands():
    """Two NE-SW strands offset laterally by ~1 km with ~2 km of along-strike overlap."""
    m = np.zeros((120, 120), bool)
    for k in range(0, 60):
        m[20 + k, 20 + k] = True         # strand A
        m[28 + k, 20 + k] = True         # strand B: same strike, 8 px lateral offset
    return m


def test_steppover_links_finds_the_parallel_offset_pair():
    fg = build_graph(_two_parallel_strands(), with_edges=False)
    L = newinfo.steppover_links(fg, min_px=5)
    assert not L.empty
    r = L.iloc[0]
    assert r.kind == "en-echelon step-over"
    assert 3.0 <= r.lateral_px <= 30.0
    assert r.overlap_px >= 2.0
    assert 3.0 <= r.length_px <= 30.0
    assert r.strike_diff_deg <= 20.0
    # the breaching segment is short: it crosses the 8-px lateral offset, not the strand length
    assert r.length_px < 15.0
    assert newinfo.dedupe_pairs(L).shape[0] <= L.shape[0]


def test_steppover_links_rejects_a_collinear_pair():
    m = np.zeros((120, 120), bool)
    m[30, 10:50] = True                  # one east-west strand
    m[30, 56:96] = True                  # its collinear continuation, 6 px tip-to-tip gap
    fg = build_graph(m, with_edges=False)
    L = newinfo.steppover_links(fg, min_px=5, lat_min_px=3.0)
    # a collinear pair has ~zero lateral offset, so it cannot pass the step-over filter
    assert L.empty or bool((L.lateral_px.to_numpy() >= 3.0).all())


def test_steppover_links_rejects_perpendicular_strands():
    m = np.zeros((120, 120), bool)
    for k in range(0, 50):
        m[20 + k, 20 + k] = True         # NE-SW strand
    m[30:80, 60] = True                  # north-south strand crossing it laterally
    fg = build_graph(m, with_edges=False)
    L = newinfo.steppover_links(fg, min_px=5)
    assert L.empty or bool((L.strike_diff_deg.to_numpy() <= 20.0).all())


@pytest.mark.skipif(not (Path(__file__).resolve().parents[1] / "data_cache" / "geodawn_rad_u8.tif").exists(),
                    reason="restored input rasters not present")
def test_aux_bands_have_the_registered_names_and_ranges():
    from gems27 import grid
    bands = newinfo.aux_bands(grid.SHAPE)
    assert set(bands) == set(newinfo.RAD_BANDS + newinfo.SGMC_BANDS + newinfo.THERMAL_BANDS)
    assert len(bands) == 16
    for n, b in bands.items():
        assert b.shape == grid.SHAPE and np.isfinite(b).all(), n
    assert bands["sgmc_dist"].max() <= 20.0
    assert bands["ws_dist_hot"].max() <= 100.0
    assert set(np.unique(bands["sgmc_on"])) <= {0.0, 1.0}
    assert (bands["rad_K"] >= 0).all() and (bands["rad_K"] <= 255).all()
