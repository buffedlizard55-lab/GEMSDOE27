import numpy as np

from gems27.buried_step import TRANSFORM_NAMES, build_feature_matrix, build_grids


def test_buried_step_is_finite_ranked_and_label_free():
    rng = np.random.default_rng(3)
    foot = np.zeros((24, 28), bool)
    foot[2:22, 2:26] = True
    depth = rng.normal(200, 40, foot.shape).astype(np.float32)
    depth[8:12, :] += 80
    step = rng.integers(0, 80, foot.shape).astype(np.float32)
    step[10, 4:20] = 200
    shear = rng.random(foot.shape).astype(np.float32) * 10
    depth[0, 0] = -3.4e38
    grids = build_grids(depth, step, shear, foot)
    assert list(grids) == TRANSFORM_NAMES
    for name, grid in grids.items():
        inside = grid[foot]
        assert np.isfinite(inside).all(), name
        assert inside.min() >= 0 and inside.max() <= 1
        assert np.all(grid[~foot] == 0)
    mat = build_feature_matrix(depth, step, shear, foot)
    assert mat.shape == (int(foot.sum()), 6)
    assert mat.dtype == np.float32
    # A high step must not increase the low-scarp rank.
    high = step >= 200
    assert grids["bss_lowscarp"][high & foot].mean() < grids["bss_lowscarp"][foot & ~high].mean()
