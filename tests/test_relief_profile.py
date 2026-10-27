import numpy as np
import pytest

from gems27 import relief_profile


def test_features_are_bounded_finite_and_do_not_mutate_input():
    y, x = np.mgrid[-48:48, -48:48].astype(np.float32)
    elev = (0.05 * x ** 2 + 4 * np.tanh(y / 5)).astype(np.float32)
    foot = np.ones_like(elev, dtype=bool)
    foot[:5] = False
    elev[20, 20] = np.nan
    original = elev.copy()
    result = relief_profile.build_features(elev, foot)
    assert result.shape == (int(foot.sum()), 4)
    assert np.array_equal(elev, original, equal_nan=True)
    assert np.isfinite(result).all()
    assert (result >= 0).all() and (result <= 1).all()
    assert np.max(result[:, 1]) > 0  # transverse-curvature response exists


def test_constant_missing_and_shape_guards():
    foot = np.ones((32, 32), dtype=bool)
    flat = relief_profile.build_features(np.ones((32, 32), dtype=np.float32), foot)
    assert np.all(flat == 0)
    with pytest.raises(ValueError, match="no finite"):
        relief_profile.build_features(np.full((32, 32), np.nan), foot)
    with pytest.raises(ValueError, match="2-D"):
        relief_profile.build_features(np.ones((31, 32)), foot)
