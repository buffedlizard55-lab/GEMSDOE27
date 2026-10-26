from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree

from gems27 import geothermal_conduit_nis as h31


def test_blakely_ridge_crest_peaks_on_step_contact():
    grid = np.zeros((48, 48), dtype=np.float32)
    grid[:, 24:] = 10.0
    crest = h31.blakely_ridge_crest(grid, sigma_grad=1.5, sigma_curv=1.2)
    assert crest.dtype == np.float32
    assert np.all(np.isfinite(crest)) and float(crest.min()) >= 0.0
    mid_col = int(np.argmax(crest[24, :]))
    assert abs(mid_col - 24) <= 1
    assert float(crest[24, mid_col]) > 5.0 * float(crest[24, 12])


def test_contour_obliquity_distinguishes_shoreline_from_cross_contour_fault():
    # Elevation increases southward (+row): contours run E-W (theta_contour = 0 rad from +x col)
    yy, xx = np.mgrid[0:40, 0:40].astype(np.float32)
    elev = yy * 10.0 + 0.0 * xx
    valid = np.ones((40, 40), dtype=bool)
    valid[:5, :] = False

    # Case A: E-W Lake Lahontan shoreline parallel to contours (theta_s = 0 -> cos2=1, sin2=0)
    ob_parallel = h31.contour_obliquity_sin2(
        elev, np.ones_like(elev), np.zeros_like(elev), valid, sigma_dem=2.0
    )
    assert float(ob_parallel[20, 20]) < 1e-4
    assert float(ob_parallel[2, 20]) == 0.0  # outside valid_lid

    # Case B: N-S cross-contour tectonic fault (theta_s = pi/2 -> cos2=-1, sin2=0)
    ob_perp = h31.contour_obliquity_sin2(
        elev, -np.ones_like(elev), np.zeros_like(elev), valid, sigma_dem=2.0
    )
    assert abs(float(ob_perp[20, 20]) - 1.0) < 1e-4


def test_synthesize_stage1_regimes_calibrates_lidar_gap_into_unit_interval():
    rng = np.random.default_rng(42)
    foot = np.ones((30, 30), dtype=bool)
    lid_valid = np.ones((30, 30), dtype=bool)
    lid_valid[:, 20:] = False  # 1/3 LiDAR gap

    # Suppose M_Sub raw probabilities are 3x smaller in scale than M_Full
    p_full = rng.uniform(0.02, 0.60, size=(30, 30)).astype(np.float32)
    p_sub = rng.uniform(0.005, 0.20, size=(30, 30)).astype(np.float32)
    synth = h31.synthesize_stage1_regimes(p_full, p_sub, foot, lid_valid, gap_scale=0.94)

    assert synth.dtype == np.float32
    assert np.all(np.isfinite(synth))
    assert float(synth.min()) >= 0.0 and float(synth.max()) <= 1.0
    gap_med = float(np.median(synth[~lid_valid]))
    lid_med = float(np.median(synth[lid_valid]))
    assert abs(gap_med - 0.94 * lid_med) < 0.05


def test_emit_h31_celf_enforces_b2_collar_and_min_sep_2p8():
    foot = np.ones((50, 50), dtype=bool)
    known = np.zeros((50, 50), dtype=bool)
    known[25, 10:40] = True
    rng = np.random.default_rng(7)
    prob = rng.uniform(0.01, 0.3, size=(50, 50)).astype(np.float32)
    prob[10, 10:45] = 0.95  # strong unmapped fault ridge away from known

    dots = h31.emit_h31_celf(prob, foot, known, budget=25, b_excl=2.0, min_sep_px=2.8)
    assert int(dots.sum()) == 25
    assert not (dots & known).any()
    pts = np.argwhere(dots).astype(np.float64)
    nn, _ = cKDTree(pts).query(pts, k=2)
    assert float(nn[:, 1].min()) >= 2.8 - 1e-6


def test_fit_predict_dual_regime_oof_synthetic_no_nan():
    rng = np.random.default_rng(123)
    foot = np.ones((48, 48), dtype=bool)
    lid_valid = np.ones((48, 48), dtype=bool)
    lid_valid[:, 32:] = False
    n = int(foot.sum())

    base_X = rng.normal(size=(n, 32)).astype(np.float32)
    base_X[~lid_valid[foot], 18:30] = np.nan  # mimic real NaN LiDAR gap
    sub15_X = rng.normal(size=(n, 15)).astype(np.float32)
    h29_X = rng.normal(size=(n, 20)).astype(np.float32)
    h31_X = rng.normal(size=(n, 12)).astype(np.float32)

    labels = np.zeros((48, 48), dtype=bool)
    labels[10, 6:42] = True
    labels[36, 6:42] = True
    # Inject true subsurface signal in sub15_X[:, 0] on fault rows
    sub15_X[labels[foot], 0] += 3.5

    p_sub, p_s1, p_s2 = h31.fit_predict_dual_regime_oof(
        base_X,
        sub15_X,
        h29_X,
        h31_X,
        labels,
        foot,
        lid_valid,
        buffer_px=2.0,
        s1_max_iter=25,
        s2_max_iter=20,
        seed=400,
    )
    for arr in (p_sub, p_s1, p_s2):
        assert arr.shape == (48, 48) and arr.dtype == np.float32
        assert np.all(np.isfinite(arr))
        assert float(arr.min()) >= 0.0 and float(arr.max()) <= 1.0
    assert float(p_s2[labels].mean()) > float(p_s2[~labels].mean())


def test_rotated_unmasked_fold_masks_and_celf_min_sep_28_budget():
    from gems27 import coverage_thin
    from gems27 import hydrothermal_piedmont as h29

    rng = np.random.default_rng(77)
    H, W = 52, 52
    foot = np.ones((H, W), dtype=bool)
    foot[:4, :] = False  # irregular footprint boundary to exercise `foot & fm` normalization
    labels = np.zeros((H, W), dtype=bool)
    labels[10:42, 16] = True
    labels[12:40, 36] = True
    lid_valid = np.ones((H, W), dtype=bool)
    lid_valid[:, 26:] = False

    n_foot = int(foot.sum())
    base_X = rng.normal(0.0, 1.0, size=(n_foot, 32)).astype(np.float32)
    sub15_X = rng.normal(0.0, 1.0, size=(n_foot, 15)).astype(np.float32)
    h29_X = rng.normal(0.0, 1.0, size=(n_foot, 20)).astype(np.float32)
    h31_X = rng.normal(0.0, 1.0, size=(n_foot, 12)).astype(np.float32)
    y_foot = labels[foot]
    h31_X[y_foot, 0] += 3.0

    # `sector_masks_rotated45` returns full-grid masks not pre-intersected with `foot`
    rot_folds = h29.sector_masks_rotated45(foot)
    _, _, p_s2 = h31.fit_predict_dual_regime_oof(
        base_X,
        sub15_X,
        h29_X,
        h31_X,
        labels,
        foot,
        lid_valid,
        fold_masks=rot_folds,
        buffer_px=3.0,
        max_neg_s1=600,
        max_neg_s2=600,
        s1_max_iter=15,
        s2_max_iter=12,
        seed=401,
    )
    assert np.all(p_s2[~foot] == 0.0)
    assert float(p_s2[foot].max()) <= 1.0

    # Regression test for `coverage_thin.weighted_celf_cover` when `max_candidates` < `budget * 21`
    prob_grid = rng.uniform(0.05, 1.0, size=(80, 80)).astype(np.float32)
    elig = np.ones((80, 80), dtype=bool)
    dots = coverage_thin.weighted_celf_cover(
        prob_grid, elig, elig, budget=120, radius_px=3.0, gamma=1.35, min_sep_px=2.8, max_candidates=400
    )
    assert int(dots.sum()) == 120

