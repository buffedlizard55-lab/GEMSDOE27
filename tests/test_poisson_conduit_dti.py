from __future__ import annotations

import numpy as np
import pytest

from gems27 import poisson_conduit_dti as h32


def test_sediment_cover_blindness_monotone_and_bounded():
    foot = np.ones((4, 4), dtype=bool)
    foot[0, 0] = False
    dtb = np.full((4, 4), 50.0, dtype=np.float32)
    relief = np.full((4, 4), 60.0, dtype=np.float32)
    w_exposed = h32.compute_sediment_cover_blindness(dtb, relief, foot)

    dtb_deep = np.full((4, 4), 600.0, dtype=np.float32)
    relief_flat = np.full((4, 4), 5.0, dtype=np.float32)
    w_buried = h32.compute_sediment_cover_blindness(dtb_deep, relief_flat, foot)

    assert w_exposed[0, 0] == 0.0 and w_buried[0, 0] == 0.0
    assert 0.0 <= float(w_exposed[foot].max()) < 0.05
    assert 0.75 < float(w_buried[foot].min()) <= 1.0


def test_cover_aware_stage1_frees_buried_conduits_and_stays_in_unit_interval():
    rng = np.random.default_rng(42)
    H, W = 40, 40
    dom = np.ones((H, W), dtype=bool)
    lid = np.ones((H, W), dtype=bool)
    lid[:, 30:] = False

    pf = rng.uniform(0.0, 0.25, size=(H, W)).astype(np.float32)
    ps = rng.uniform(0.0, 0.25, size=(H, W)).astype(np.float32)
    # Inject a blind subsurface conduit inside lidar_valid where pf is silent (0.002)
    pf[10, 10] = 0.002
    ps[10, 10] = 0.24
    pf[20, 10] = 0.002
    ps[20, 10] = 0.24

    w_blind = np.zeros((H, W), dtype=np.float32)
    w_blind[10, 10] = 0.90  # deep flat basin cover
    w_blind[20, 10] = 0.02  # exposed bedrock (absence of LiDAR scarp is informative)

    s1, qsub = h32.synthesize_cover_aware_stage1(pf, ps, w_blind, dom, lid)
    assert np.isfinite(s1).all() and np.isfinite(qsub).all()
    assert float(s1.min()) >= 0.0 and float(s1.max()) <= 1.0
    assert float(s1[10, 10]) > 1.5 * float(s1[20, 10])
    assert float(s1[:, 30:].max()) > 0.0


def test_kernel_regression_sampler_importance_weights():
    rng = np.random.default_rng(7)
    n = 500
    tr = np.ones(n, dtype=bool)
    y = np.zeros(n, dtype=bool)
    y[:20] = True
    d = np.full(n, 10.0, dtype=np.float32)
    d[:20] = 0.0
    d[20:120] = 1.5  # 100 flank pixels with y_K = 0.5

    idx, yk, sw = h32._sample_kernel_regression_indices(
        tr, y, d, rng, max_flank=40, max_bg=100
    )
    assert idx.size == 20 + 40 + 100
    assert np.allclose(yk[:20], 1.0)
    assert np.allclose(yk[20:60], 0.5)
    assert np.allclose(yk[60:], 0.0)
    assert np.allclose(sw[20:60], 100.0 / 40.0)


def test_stage2_pdhc_features_finite_and_shape():
    H, W = 32, 32
    vm = np.zeros((H, W), dtype=bool)
    vm[6:26, 6:26] = True
    p_s1 = np.zeros((H, W), dtype=np.float32)
    p_s1[:, 15] = 0.8
    q_sub = p_s1 * np.float32(0.7)
    p_full = p_s1 * np.float32(0.9)
    w_blind = np.full((H, W), 0.3, dtype=np.float32)

    mat = h32.stage2_pdhc_features(p_s1, q_sub, p_full, w_blind, vm)
    assert mat.shape == (int(vm.sum()), len(h32.H32_S2_FEATURE_NAMES))
    assert np.isfinite(mat).all()


def test_anti_leakage_guards():
    assert h32.VENT_ALLOWED_COLS == ["row", "col"]
    assert len(h32.H32_FEATURE_NAMES) == 16
    assert len(h32.H32_NON_LIDAR_IDX) == 14
    with pytest.raises(ValueError, match="Band 6"):
        h32._read_extra_tf_band(None, 6, "tc", np.zeros((2, 2), dtype=bool))  # type: ignore[arg-type]
