"""Unit tests for H31-2 demagnetization features + OOF stacker (knowledge/26, frozen)."""

import numpy as np
import pytest
from scipy.ndimage import gaussian_filter

from gems27.demagnetization import (
    DEMAG_FEATURE_NAMES,
    fit_predict_stacker_oof,
    local_poisson_residual_z,
)


def test_feature_names_frozen():
    assert len(DEMAG_FEATURE_NAMES) == 8
    assert DEMAG_FEATURE_NAMES[1] == "demag_resid_pos_s8"
    assert len(set(DEMAG_FEATURE_NAMES)) == 8


def test_residual_zero_for_exact_affine_poisson_relation():
    rng = np.random.default_rng(7)
    rtp = gaussian_filter(rng.standard_normal((60, 55)).astype(np.float32), 2.0)
    grav_vg = (2.5 * rtp + 3.0).astype(np.float32)
    z = local_poisson_residual_z(rtp, grav_vg, sigma=4.0)
    assert float(np.max(np.abs(z))) < 1e-3


def test_residual_positive_where_magnetics_flattened():
    rng = np.random.default_rng(11)
    base = gaussian_filter(rng.standard_normal((80, 80)).astype(np.float32), 2.5)
    grav_vg = (1.7 * base).astype(np.float32)
    rtp = base.copy()
    rtp[:, 48:] = np.float32(np.mean(base[:, 48:]))  # magnetite destroyed on the right
    z = local_poisson_residual_z(rtp, grav_vg, sigma=5.0)
    pos = np.maximum(z, 0.0)
    assert float(pos[10:-10, 58:].mean()) > float(pos[10:-10, :30].mean()) + 0.05
    assert np.isfinite(z).all()
    assert float(np.max(np.abs(z))) <= 10.0 + 1e-6


def test_residual_rejects_nonfinite_and_shape_mismatch():
    a = np.zeros((10, 10), dtype=np.float32)
    b = np.zeros((10, 9), dtype=np.float32)
    with pytest.raises(ValueError):
        local_poisson_residual_z(a, b, sigma=2.0)
    c = a.copy()
    c[0, 0] = np.nan
    with pytest.raises(ValueError):
        local_poisson_residual_z(c, a, sigma=2.0)


def test_stacker_oof_returns_valid_probabilities_and_uses_extra_signal():
    rng = np.random.default_rng(3)
    foot = np.ones((40, 40), dtype=bool)
    # Truth: diagonal band. Base surface is pure noise; the extra column carries the signal,
    # so a leak-free OOF stacker with extras must rank band pixels above background on average.
    yy, xx = np.mgrid[0:40, 0:40]
    labels = np.abs(yy - xx) <= 1
    noise_surf = rng.random((40, 40), dtype=np.float32) * np.float32(0.2)
    extra = np.zeros((int(foot.sum()), 1), dtype=np.float32)
    extra_grid = (np.abs(yy - xx) <= 2).astype(np.float32)
    extra[:, 0] = extra_grid[foot]
    prob = fit_predict_stacker_oof((noise_surf,), extra, labels, foot, seed=5, max_neg=10_000)
    assert prob.shape == foot.shape
    assert np.isfinite(prob).all()
    assert float(prob.min()) >= 0.0 and float(prob.max()) <= 1.0
    assert float(prob[labels].mean()) > float(prob[~labels].mean())
