"""Unit tests for Lane L-H30 transforms (knowledge/20, frozen formulas)."""

from __future__ import annotations

import numpy as np

from gems27.dip_gap_features import (
    NEW_FEATURE_NAMES,
    _advect,
    _gap_flank,
    build_dip_gap_features,
    soft_rank_taper,
)


def test_build_shapes_and_range():
    rng = np.random.default_rng(3)
    shape = (40, 36)
    foot = np.ones(shape, bool)
    foot[:5] = False
    grids = {
        "rtp": rng.normal(size=shape).astype(np.float32),
        "iso_grav_anom": rng.normal(size=shape).astype(np.float32),
        "depth_to_base_surf": np.abs(rng.normal(size=shape)).astype(np.float32) * 500.0,
    }
    out = build_dip_gap_features(grids, foot)
    assert out.shape == (int(foot.sum()), len(NEW_FEATURE_NAMES))
    assert out.dtype == np.float32
    assert np.isfinite(out).all()
    assert float(out.min()) >= 0.0 and float(out.max()) <= 1.0


def test_gap_flank_fires_between_collinear_segments():
    edge = np.zeros((31, 31), dtype=np.float32)
    edge[15, 10] = 1.0
    edge[15, 22] = 1.0
    gap = _gap_flank(edge, 6.0)
    # midpoint (15,16) is flanked at +/-6 px along the E-W strike by both spikes
    assert gap[15, 16] > 0.99
    # a pixel far from any collinear pair stays zero
    assert gap[2, 2] == 0.0


def test_advect_samples_down_dip_along_depth_gradient():
    shape = (21, 41)
    # depth increases eastward at 100 m per pixel; down-dip unit vector ~ +x
    depth = (np.arange(shape[1], dtype=np.float32)[None, :] * 100.0).repeat(shape[0], axis=0)
    edge = np.zeros(shape, dtype=np.float32)
    edge[10, 18] = 1.0
    adv = _advect(edge, depth, cot_dip=0.83909963)
    # at column 10, depth = 1000 m -> offset = clip(1000*0.839/100, 0, 8) = 8 px,
    # so the candidate at column 10 samples the edge spike at column 18.
    assert adv[10, 10] > 0.5
    # without any spike down-dip, a western candidate samples background
    assert adv[10, 2] < 0.5


def test_soft_rank_taper_mass_and_order():
    prob = np.zeros((5, 5), dtype=np.float32)
    support = np.zeros((5, 5), bool)
    coords = [(0, 0), (0, 1), (0, 2), (0, 3)]
    for (y, x), p in zip(coords, [0.1, 0.9, 0.5, 0.3]):
        support[y, x] = True
        prob[y, x] = p
    out = soft_rank_taper(prob, support, budget_mass=2.0)
    vals = [float(out[y, x]) for y, x in coords]
    # descending-probability order: 0.9 -> largest value, then 0.5, 0.3, 0.1
    assert vals[1] > vals[2] > vals[3] > vals[0] > 0.0
    assert abs(float(out.sum()) - 2.0) < 1e-5
    assert float(out.max()) <= 1.0
    assert float(out[~support].sum()) == 0.0
