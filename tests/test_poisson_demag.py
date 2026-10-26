"""H32 Poisson-demagnetization transforms: shape/range contract + a synthetic demag case."""
import numpy as np
import pytest

from gems27 import poisson_demag as poi


def _grids(shape=(60, 60), demag=False):
    rng = np.random.default_rng(0)
    base = rng.normal(size=shape).astype(np.float32)
    # a vertical "fault" step at col 30 in gravity
    grav = base.copy()
    grav[:, 30:] += 5.0
    # magnetics follow gravity unless demagnetised near the step
    rtp = (2.0 * grav + rng.normal(scale=0.1, size=shape)).astype(np.float32)
    if demag:
        rtp[:, 28:33] = rng.normal(scale=0.1, size=(shape[0], 5)).astype(np.float32)
    g = {
        "rtp": rtp,
        "tmi_hg": np.abs(np.gradient(rtp, axis=1)).astype(np.float32),
        "tmi_vg": np.gradient(rtp, axis=0).astype(np.float32),
        "iso_grav_anom": grav,
        "iso_grav_anom_hg": np.abs(np.gradient(grav, axis=1)).astype(np.float32),
        "iso_grav_anom_vg": np.gradient(grav, axis=0).astype(np.float32),
    }
    return g


def test_shapes_and_range():
    foot = np.ones((60, 60), bool)
    out = poi.build_transforms(_grids(), foot)
    assert out.shape == (3600, len(poi.TRANSFORM_NAMES))
    assert np.isfinite(out).all()
    assert out.min() >= 0.0 and out.max() <= 1.0


def test_missing_band_raises():
    foot = np.ones((60, 60), bool)
    g = _grids()
    del g["rtp"]
    with pytest.raises(ValueError):
        poi.build_transforms(g, foot)


def test_demagnetised_step_lights_up_residual():
    foot = np.ones((60, 60), bool)
    plain = poi.build_transforms(_grids(demag=False), foot)
    demag = poi.build_transforms(_grids(demag=True), foot)
    j = poi.TRANSFORM_NAMES.index("poi_resid_abs")
    # mean residual rank inside the demagnetised strip must exceed the coupled case
    strip = np.zeros((60, 60), bool)
    strip[:, 28:33] = True
    idx = np.flatnonzero(strip.ravel())
    assert demag[idx, j].mean() > plain[idx, j].mean()
