import numpy as np
import pytest

from gems27 import strain_conductivity as sc


def _inputs(shape=(31, 37)):
    yy, xx = np.indices(shape, dtype=np.float32)
    second = 1.0 + xx + yy * 0.3
    shear = 0.5 + yy + xx * 0.2
    dilation = np.maximum(yy - 5.0, 0.0)
    conductivity = 0.2 + xx * 0.5 + yy * 0.1
    basement = 10.0 + yy * 15.0 + xx
    valid = np.ones(shape, dtype=bool)
    return second, shear, dilation, conductivity, basement, valid


def test_strain_conductivity_features_are_bounded_finite_and_masked():
    args = list(_inputs())
    args[-1][0, :] = False
    args[-1][:, 0] = False
    stack = sc.strain_conductivity_features(*args)
    assert stack.shape == (len(sc.FEATURE_NAMES), 31, 37)
    assert stack.dtype == np.float32
    assert np.isfinite(stack).all()
    assert float(stack.min()) >= 0.0 and float(stack.max()) <= 1.0
    assert (stack[:, ~args[-1]] == 0.0).all()
    # The non-constant synthetic fields must produce an actual spatial transform, not all zeros.
    assert (stack[:, args[-1]].max(axis=1) > 0).all()


def test_strain_conductivity_rejects_bad_shape_and_bad_scale():
    args = list(_inputs())
    with pytest.raises(ValueError, match="equal-shaped"):
        sc.strain_conductivity_features(args[0][:-1], *args[1:])
    with pytest.raises(ValueError, match="finite positive"):
        sc.strain_conductivity_features(*args, sigma_px=0)


def test_robust_unit_scale_rejects_nonfinite_valid_values():
    arr = np.ones((4, 4), np.float32)
    arr[1, 1] = np.nan
    with pytest.raises(ValueError, match="finite"):
        sc.robust_unit_scale(arr, np.ones_like(arr, bool))
