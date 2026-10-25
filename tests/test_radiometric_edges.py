import numpy as np

from gems27 import oof_detector, radiometric_edges


def test_radiometric_edge_transform_is_finite_bounded_and_does_not_mutate_inputs():
    yy, xx = np.mgrid[:48, :52]
    thk = (xx >= 24).astype(np.float32) * 120.0
    uth = thk * 2.0
    tc = (yy >= 25).astype(np.float32) * 80.0
    valid = np.ones(thk.shape, dtype=bool)
    valid[:3, :4] = False
    valid_before = valid.copy()
    thk[0, 0] = np.nan
    thk_before = thk.copy()

    stack = radiometric_edges.multiscale_radiometric_edge_features(thk, uth, tc, valid)

    assert stack.shape == (len(radiometric_edges.EDGE_FEATURE_NAMES), *thk.shape)
    assert stack.dtype == np.float32
    assert np.isfinite(stack).all()
    assert stack.min() >= 0.0 and stack.max() <= 1.0
    assert np.all(stack[:, :3, :4] == 0.0)
    assert np.array_equal(valid, valid_before)
    assert np.array_equal(thk, thk_before, equal_nan=True)
    # The two co-oriented ratio boundaries agree; the orthogonal TC boundary does not create
    # a directionally coherent TC/ThK signal where both are strong.
    assert stack[6].max() > 0.95
    assert stack[7].min() >= 0.0 and stack[7].max() <= 1.0


def test_random_ridge_control_uses_same_budget_and_thinning_reproducibly():
    shape = (24, 24)
    foot = np.ones(shape, dtype=bool)
    known = np.zeros(shape, dtype=bool)
    ridge = np.zeros(shape, dtype=bool)
    coords = [(2, 2 + 4 * i) for i in range(6)]
    for r, c in coords:
        ridge[r, c] = True
    score = np.zeros(shape, dtype=np.float32)
    for rank, (r, c) in enumerate(coords):
        score[r, c] = 1.0 - rank * 0.1

    top = oof_detector.build_oof_dotted_base(
        score, ridge, foot, known, budget_frac=3 / foot.sum(), thin_d=1.5
    )
    random_a = oof_detector.build_oof_dotted_base(
        score, ridge, foot, known, budget_frac=3 / foot.sum(), thin_d=1.5, random_state=17
    )
    random_b = oof_detector.build_oof_dotted_base(
        score, ridge, foot, known, budget_frac=3 / foot.sum(), thin_d=1.5, random_state=17
    )

    assert int(top.sum()) == 3
    assert int(random_a.sum()) == 3
    assert np.array_equal(random_a, random_b)
    assert not np.array_equal(top, random_a)
    assert not (random_a & known).any()
