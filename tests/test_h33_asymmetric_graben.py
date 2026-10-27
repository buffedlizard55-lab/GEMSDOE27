from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter
from scipy.spatial import cKDTree

from gems27 import asymmetric_graben_conduit as h33


def test_directional_asymmetric_diff_cancels_flat_playa_and_detects_hw_step():
    H, W = 80, 80
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    # Basement deepens from West (col 0) to East (col 79) -> unit basinward normal u = (0, +1)
    uy = np.zeros((H, W), dtype=np.float32)
    ux = np.ones((H, W), dtype=np.float32)

    # Conductive hanging-wall step across fault at x = 30, followed by flat playa for x >= 45
    cond = np.where(xx >= 30.0, np.float32(3.8), np.float32(1.5))
    cond = gaussian_filter(cond, sigma=1.2)

    jump4 = h33.directional_asymmetric_diff(cond, uy, ux, step_px=4.0)
    assert jump4.shape == (H, W) and jump4.dtype == np.float32
    fault_zone_val = float(jump4[40, 30])
    flat_playa_val = float(jump4[40, 60])
    footwall_val = float(jump4[40, 12])
    assert fault_zone_val > 2.0
    assert flat_playa_val < 1e-5
    assert footwall_val < 1e-5


def test_along_vector_integral_bridges_collinear_canyon_mouths():
    H, W = 64, 64
    imp = np.zeros((H, W), dtype=np.float32)
    # Three collinear canyon mouths along x = 32 at y = 20, 32, 44 with empty fan gaps at y = 26, 38
    for r in (20, 32, 44):
        imp[r - 1 : r + 2, 31:34] = 4.0
    # One isolated bedrock gully off-strike at (32, 10)
    imp[31:34, 9:12] = 4.0

    # Range-front strike tangent points N-S: (ty, tx) = (1, 0)
    ty = np.ones((H, W), dtype=np.float32)
    tx = np.zeros((H, W), dtype=np.float32)
    offsets = (-12.0, -10.0, -8.0, -6.0, -4.0, -2.0, 0.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0)
    collin = h33.along_vector_integral(imp, ty, tx, offsets)

    buried_fan_gap = float(collin[26, 32])  # raw imp[26, 32] == 0, bridged by adjacent mouths!
    collinear_mouth = float(collin[32, 32])
    isolated_gully = float(collin[32, 10])
    assert buried_fan_gap > 0.5
    assert collinear_mouth > 2.5 * isolated_gully


def test_line16_ortho_aniso_suppresses_2d_blob_and_preserves_steep_fault():
    H, W = 60, 60
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    # 2-D isotropic circular blob centered at (30, 18)
    blob = np.exp(-((yy - 30.0) ** 2 + (xx - 18.0) ** 2) / (2.0 * 9.0 ** 2)).astype(np.float32)
    # Steep N18.4E 1-D Basin-and-Range fault line passing through (30, 44): (x - 44) + 0.333*(y - 30) = 0
    dist_line = np.abs((xx - 44.0) + 0.3333 * (yy - 30.0)) / np.hypot(1.0, 0.3333)
    line = np.exp(-(dist_line ** 2) / (2.0 * 0.9 ** 2)).astype(np.float32)

    l_blob, a_blob = h33.line16_max_and_ortho_aniso(blob, half_len=5)
    l_line, a_line = h33.line16_max_and_ortho_aniso(line, half_len=5)

    assert float(a_blob[30, 18]) < 0.05
    assert float(l_line[30, 44]) > 0.80
    assert float(a_line[30, 44]) > 0.60


def test_sharp_hydro_vent_field_never_reads_dist_known_fault_px(tmp_path: Path):
    ws = tmp_path / "wells.csv"
    vt = tmp_path / "vents.csv"
    ws.write_text(
        "row,col,temp_c,geothermquartz_c,geothermchalc_c,geothermcat_c,dist_known_fault_px\n"
        "10,12,85.0,165.0,140.0,155.0,0.0\n"
    )
    vt.write_text("name,rock_type,age,row,col,dist_known_fault_px\nv1,Basalt,Q,15,15,0.0\n")
    foot = np.ones((32, 32), dtype=bool)
    f1 = h33._sharp_hydro_vent_field(ws, vt, (32, 32), foot)

    # Mutate forbidden column wildly — output MUST be bitwise identical:
    ws.write_text(
        "row,col,temp_c,geothermquartz_c,geothermchalc_c,geothermcat_c,dist_known_fault_px\n"
        "10,12,85.0,165.0,140.0,155.0,9999999.0\n"
    )
    vt.write_text("name,rock_type,age,row,col,dist_known_fault_px\nv1,Basalt,Q,15,15,9999999.0\n")
    f2 = h33._sharp_hydro_vent_field(ws, vt, (32, 32), foot)
    assert np.array_equal(f1, f2)
    assert float(f1[10, 12]) > float(f1[0, 0])


def test_dual_regime_oof_and_celf_emission_end_to_end():
    rng = np.random.default_rng(600)
    H, W = 72, 72
    foot = np.ones((H, W), dtype=bool)
    foot[:2, :] = False
    n_f = int(foot.sum())

    # 25% synthetic LiDAR gap in NE quadrant
    lid_valid = foot.copy()
    lid_valid[2:36, 36:] = False

    labels = np.zeros((H, W), dtype=bool)
    labels[8:64, 22] = True
    labels[10:62, 50] = True

    base_X = rng.normal(0.0, 1.0, size=(n_f, 32)).astype(np.float32)
    # Inject NaNs on the 12 LiDAR columns inside ~lid_valid
    lid_cols = [i for i in range(32) if i not in h33.BASE_NON_LIDAR_IDX]
    gap_rows = ~lid_valid[foot]
    base_X[np.ix_(gap_rows, lid_cols)] = np.nan

    sub15_X = rng.normal(0.0, 1.0, size=(n_f, 15)).astype(np.float32)
    h33_X = rng.normal(0.0, 1.0, size=(n_f, len(h33.H33_FEATURE_NAMES))).astype(np.float32)
    # Inject real signal in non-LiDAR col 0 on labels so both regimes learn
    y_f = labels[foot]
    h33_X[y_f, 0] += 3.5
    h33_X[np.ix_(gap_rows, [15, 16, 17, 18])] = np.nan

    p_sub, p_s1, p_s2 = h33.fit_predict_h33_dual_regime_oof(
        base_X,
        sub15_X,
        h33_X,
        labels,
        foot,
        lid_valid,
        buffer_px=3.0,
        max_neg_s1=2000,
        max_neg_s2=2000,
        s1_max_iter=25,
        s2_max_iter=20,
        seed=600,
    )
    for arr in (p_sub, p_s1, p_s2):
        assert np.isfinite(arr[foot]).all()
        assert float(arr[foot].min()) >= 0.0 and float(arr[foot].max()) <= 1.0
        assert float(arr[foot & (~lid_valid)].max()) > 0.0

    known = np.zeros((H, W), dtype=bool)
    known[10:25, 22] = True
    dots = h33.emit_h33_celf(p_s2, foot, known, budget=25, b_excl=2.0, gamma=1.50, min_sep_px=3.00)
    assert int(dots.sum()) == 25
    assert not (dots & (~foot)).any()
    assert not (dots & known).any()
    assert float(distance_transform_edt(~known)[dots].min()) > 2.0
    pts = np.argwhere(dots).astype(np.float64)
    nn, _ = cKDTree(pts).query(pts, k=2)
    assert float(nn[:, 1].min()) >= 3.00 - 1e-6


def test_h33_2_deconfounded_full_ignores_raw_base_lidar_and_enforces_sep345():
    rng = np.random.default_rng(610)
    H, W = 72, 72
    foot = np.ones((H, W), dtype=bool)
    lid_valid = foot.copy()
    lid_valid[:36, 36:] = False
    n_f = int(foot.sum())

    labels = np.zeros((H, W), dtype=bool)
    labels[8:64, 20] = True
    labels[10:62, 52] = True

    base_X = rng.normal(0.0, 1.0, size=(n_f, 32)).astype(np.float32)
    sub15_X = rng.normal(0.0, 1.0, size=(n_f, 15)).astype(np.float32)
    h33_X = rng.normal(0.0, 1.0, size=(n_f, len(h33.H33_FEATURE_NAMES))).astype(np.float32)
    h33_2_X = rng.normal(0.0, 1.0, size=(n_f, len(h33.H33_2_EXTRA_NAMES))).astype(np.float32)
    h33_2_X[labels[foot], 1] += 3.5

    # Verify _assemble_h33_2_rows ignores raw base_X LiDAR columns completely:
    raw_lid_cols = [i for i in range(32) if i not in h33.BASE_NON_LIDAR_IDX]
    idx = np.arange(50, dtype=np.int64)
    m1 = h33._assemble_h33_2_rows(idx, base_X, sub15_X, h33_X, h33_2_X, mode="full")
    base_X_mut = base_X.copy()
    base_X_mut[:, raw_lid_cols] = 999999.0
    m2 = h33._assemble_h33_2_rows(idx, base_X_mut, sub15_X, h33_X, h33_2_X, mode="full")
    assert m1.shape == (50, 58)
    assert np.array_equal(m1, m2)

    _, _, p_s2 = h33.fit_predict_h33_2_dual_regime_oof(
        base_X,
        sub15_X,
        h33_X,
        h33_2_X,
        labels,
        foot,
        lid_valid,
        buffer_px=3.0,
        max_neg_s1=2000,
        max_neg_s2=2000,
        s1_max_iter=20,
        s2_max_iter=15,
        seed=610,
    )
    known = np.zeros((H, W), dtype=bool)
    dots = h33.emit_h33_2_celf(p_s2, foot, known, budget=20)
    assert int(dots.sum()) == 20
    pts = np.argwhere(dots).astype(np.float64)
    tree = cKDTree(pts)
    nn, _ = tree.query(pts, k=2)
    assert float(nn[:, 1].min()) >= h33.CELF_MIN_SEP_PX_H33_2 - 1e-6
    nbr3 = [len(v) - 1 for v in tree.query_ball_point(pts, r=3.0)]
    assert max(nbr3) == 0


def test_h33_3_sector_masks_and_celf315() -> None:
    from scipy.spatial import cKDTree

    rng = np.random.default_rng(620)
    H, W = 72, 72
    foot = np.ones((H, W), dtype=bool)
    for deg in (22.5, 67.5):
        masks = h33.sector_masks_angle(foot, deg)
        assert len(masks) == 4
        total = sum(m.astype(np.int32) for m in masks)
        assert np.array_equal(total, np.ones((H, W), dtype=np.int32))
        assert min(int(m.sum()) for m in masks) > 500

    N = int(foot.sum())
    base_X = rng.normal(size=(N, 32)).astype(np.float32)
    sub15_X = rng.normal(size=(N, 15)).astype(np.float32)
    h33_X = rng.normal(size=(N, 19)).astype(np.float32)
    h33_2_X = rng.normal(size=(N, 4)).astype(np.float32)
    labels = np.zeros((H, W), dtype=bool)
    labels[10:62, 22] = True
    labels[10:62, 50] = True
    lid_valid = np.ones((H, W), dtype=bool)
    lid_valid[:, :36] = False

    _, _, p_s2 = h33.fit_predict_h33_3_dual_regime_oof(
        base_X,
        sub15_X,
        h33_X,
        h33_2_X,
        labels,
        foot,
        lid_valid,
        fold_masks=h33.sector_masks_angle(foot, 22.5),
        buffer_px=3.0,
        max_neg_s1=1500,
        max_neg_s2=1500,
        s1_max_iter=15,
        s2_max_iter=12,
        seed=620,
    )
    assert p_s2.shape == (H, W)
    assert np.isfinite(p_s2).all()

    # Verify N18.4E ridge allows sqrt(10)=3.1623 px step while keeping <=3.0 px count strictly 0
    ridge = np.zeros((H, W), dtype=np.float32)
    for k in range(18):
        r, c = 6 + 3 * k, 12 + k
        ridge[r, c] = 0.95
    dots = h33.emit_h33_3_celf(ridge, foot, np.zeros((H, W), dtype=bool), budget=18)
    pts = np.argwhere(dots).astype(np.float64)
    tree = cKDTree(pts)
    nn, _ = tree.query(pts, k=2)
    assert abs(float(nn[:, 1].min()) - np.sqrt(10.0)) < 1e-5
    nbr3 = [len(v) - 1 for v in tree.query_ball_point(pts, r=3.0)]
    assert max(nbr3) == 0

