import numpy as np

from gems27 import subsurface_features as sub


def _reference_batch_build(grids, foot):
    """Small-grid copy of the pre-streaming formula for numerical regression coverage."""
    g = {key: sub._fill(grids[key], foot) for key in sub.SUBSURFACE_BANDS}
    rtp, grav = g["rtp"], g["iso_grav_anom"]
    gm_rtp2, gm_rtp5 = sub._grad_mag(rtp, 2.0), sub._grad_mag(rtp, 5.0)
    gm_grav2, gm_grav5 = sub._grad_mag(grav, 2.0), sub._grad_mag(grav, 5.0)
    tilt = np.abs(np.arctan2(g["tmi_vg"], np.hypot(g["tmi_hg"], 1e-12))).astype(np.float32)
    analytic = np.sqrt(gm_rtp2**2 + sub.gaussian_filter(g["tmi_vg"], 2.0) ** 2).astype(np.float32)
    ry, rx = np.gradient(sub.gaussian_filter(rtp, 3.0))
    vy, vx = np.gradient(sub.gaussian_filter(grav, 3.0))
    cos_d = np.abs((rx * vx + ry * vy) / (np.hypot(rx, ry) * np.hypot(vx, vy) + 1e-12))
    gm_cond3 = sub._grad_mag(g["cond_surf"], 3.0)
    gm_dil3 = sub._grad_mag(g["geod_dilaterate"], 3.0)
    raw = {
        "sub_gm_rtp_s2": gm_rtp2,
        "sub_gm_rtp_s5": gm_rtp5,
        "sub_tiltabs_rtp": np.pi / 2 - tilt,
        "sub_analytic_rtp": analytic,
        "sub_gm_grav_s2": gm_grav2,
        "sub_gm_grav_s5": gm_grav5,
        "sub_crossfield_coherence": (cos_d * np.minimum(gm_rtp2, gm_grav2)).astype(np.float32),
        "sub_gm_cond_s3": gm_cond3,
        "sub_gm_depth_s3": sub._grad_mag(g["depth_to_base_surf"], 3.0),
        "sub_gm_depth_s8": sub._grad_mag(g["depth_to_base_surf"], 8.0),
        "sub_gm_dilate_s3": gm_dil3,
        "sub_gm_2ndinv_s3": sub._grad_mag(g["geod_2ndinv"], 3.0),
        "sub_strain_x_cond": np.sqrt(
            np.maximum(gm_dil3, 0) * np.maximum(gm_cond3, 0)
        ).astype(np.float32),
        "sub_seismic_fabric_ieq": sub._structure_coherence(g["ieq_n100a15"], 5.0),
        "sub_seismic_fabric_deq": sub._structure_coherence(g["deq_n100a15"], 5.0),
    }
    columns = []
    for name in sub.TRANSFORM_NAMES:
        vals = raw[name][foot]
        vals = np.where(np.isfinite(vals), vals, np.nanmedian(vals[np.isfinite(vals)]))
        columns.append(sub._rank01(vals))
    return np.stack(columns, axis=1).astype(np.float32)


def test_streaming_transform_builder_matches_batch_formulas():
    rng = np.random.default_rng(43)
    foot = np.ones((28, 24), dtype=bool)
    foot[:2, :] = False
    foot[:, :3] = False
    grids = {}
    for name in sub.SUBSURFACE_BANDS:
        values = rng.normal(size=foot.shape).astype(np.float32)
        values[~foot] = np.nan
        grids[name] = values

    expected = _reference_batch_build(grids, foot)
    actual = sub.build_transforms(grids, foot)

    assert actual.shape == (int(foot.sum()), len(sub.TRANSFORM_NAMES))
    assert np.isfinite(actual).all()
    assert actual.min() >= 0.0 and actual.max() <= 1.0
    np.testing.assert_allclose(actual, expected, rtol=0.0, atol=1e-7)
