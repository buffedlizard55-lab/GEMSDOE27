"""Unit tests for H30-1 up-dip basement-step advection & hydrothermal relay features."""

from __future__ import annotations

import numpy as np

from gems27.updip_relay_features import (
    UPDIP_RELAY_FEATURE_NAMES,
    advect_subsurface_probability_updip,
    build_updip_relay_features,
    compute_downdip_basement_field,
)


def _synthetic_inputs(shape: tuple[int, int] = (48, 48)) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(301)
    foot = np.ones(shape, dtype=bool)
    foot[:3, :] = False
    foot[:, -3:] = False
    n_foot = int(foot.sum())
    X = rng.normal(size=(n_foot, 32)).astype(np.float32)

    # Plant a synthetic dipping basement fault ramp along column x = 20..28
    yy, xx = np.indices(shape, dtype=np.float32)
    z_base = np.clip((xx - 18.0) * 50.0, 0.0, 600.0)
    # Deep magnetic/gravity edge displaced down-dip at x = 25
    rtp = np.tanh((xx - 25.0) / 1.5) * 120.0
    grav = np.tanh((xx - 25.0) / 1.5) * 25.0

    X[:, 13] = z_base[foot]
    X[:, 1] = rtp[foot]
    X[:, 11] = grav[foot]
    return X, foot


def test_updip_relay_features_shape_and_bounds():
    X, foot = _synthetic_inputs()
    F, names = build_updip_relay_features(X, foot, wellspring_csv=None)
    assert names == list(UPDIP_RELAY_FEATURE_NAMES)
    assert F.shape == (int(foot.sum()), 8)
    assert F.dtype == np.float32
    assert np.isfinite(F).all()
    assert float(F.min()) >= 0.0
    assert float(F.max()) <= 1.0


def test_updip_advection_shifts_deep_edge_toward_footwall():
    X, foot = _synthetic_inputs((48, 48))
    uy, ux, bstep, depth = compute_downdip_basement_field(X[:, 13], foot)
    assert uy.shape == foot.shape and ux.shape == foot.shape
    assert np.isfinite(bstep[foot]).all() and np.isfinite(depth[foot]).all()

    # Deep subsurface anomaly centered at x = 26 should project up-dip toward x = 21..22
    yy, xx = np.indices(foot.shape, dtype=np.float32)
    prob_sub = np.exp(-0.5 * ((xx - 26.0) / 1.2) ** 2).astype(np.float32)
    prob_hyb = np.full(foot.shape, 0.2, dtype=np.float32)
    adv = advect_subsurface_probability_updip(
        prob_sub, prob_hyb, X, foot, shift_min_px=4.0, shift_max_px=4.5
    )
    assert adv.shape == foot.shape
    assert np.isfinite(adv).all()
    assert float(adv[~foot].max()) == 0.0
    assert 0.0 <= float(adv[foot].min()) <= float(adv[foot].max()) <= 1.0
    # Peak of advected probability along row 24 should move up-dip (smaller x) relative to x=26
    peak_x_raw = int(np.argmax(prob_sub[24, 10:35]) + 10)
    peak_x_adv = int(np.argmax(adv[24, 10:35]) + 10)
    assert peak_x_adv < peak_x_raw
