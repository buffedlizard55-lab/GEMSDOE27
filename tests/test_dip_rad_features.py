"""Lane L-DCONFIRM new transforms: annulus geometry, polarity pairing, output contract."""

import numpy as np

from gems27.dip_rad_features import (
    NEW_TRANSFORM_NAMES,
    PREPARED_BANDS,
    RAD_GRIDS,
    _polarity_pair,
    annulus_footprint,
    build_new_transforms,
)


def test_annulus_footprint_excludes_centre_and_inner_disc():
    f = annulus_footprint(2.0, 6.0)
    c = f.shape[0] // 2
    assert not f[c, c]                      # centre excluded
    assert not f[c, c + 1]                  # r = 1 < 2 excluded
    assert f[c, c + 2] and f[c, c + 6]      # band edges included
    f13 = annulus_footprint(1.0, 3.0)
    c13 = f13.shape[0] // 2
    assert not f13[c13, c13] and f13[c13, c13 + 1] and f13[c13, c13 + 3] and f13.shape == (7, 7)


def test_polarity_pair_needs_both_breaks():
    a = np.zeros((21, 21), np.float32)
    b = np.zeros((21, 21), np.float32)
    a[10, 10] = 1.0
    assert _polarity_pair(a, b).max() == 0.0        # lone break: no pair
    b[10, 12] = 1.0                                  # partner 2 px away
    p = _polarity_pair(a, b)
    assert p[10, 10] == 1.0 and p[10, 12] == 1.0
    b2 = np.zeros((21, 21), np.float32)
    b2[10, 18] = 1.0                                 # partner 8 px away: outside 1-3 px
    assert _polarity_pair(a, b2).max() == 0.0


def test_build_new_transforms_contract_and_determinism():
    rng = np.random.default_rng(3)
    shape = (60, 55)
    foot = np.ones(shape, bool)
    foot[:4, :] = False
    prep = {k: rng.random(shape).astype(np.float32) * 100 for k in PREPARED_BANDS}
    prep["lidar_step_max"][20:25, :] = np.nan        # LiDAR-invalid style hole
    rad = {k: rng.integers(0, 256, shape).astype(np.float32) for k in RAD_GRIDS}
    out1 = build_new_transforms(prep, rad, foot)
    out2 = build_new_transforms(prep, rad, foot)
    assert out1.shape == (int(foot.sum()), len(NEW_TRANSFORM_NAMES))
    assert np.isfinite(out1).all() and out1.min() >= 0.0 and out1.max() <= 1.0
    assert np.array_equal(out1, out2)
