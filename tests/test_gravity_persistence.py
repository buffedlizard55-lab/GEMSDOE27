"""Unit tests for the H28-6 scale-persistent gravity edge features (no data needed)."""

import numpy as np

from gems27 import gravity_persistence as gp


def _foot(shape=(80, 90)):
    foot = np.zeros(shape, bool)
    foot[5:-5, 5:-5] = True
    return foot


def test_constant_field_gives_zero_edges():
    foot = _foot()
    anom = np.where(foot, 3.0, np.nan)
    grids = gp.build_grids(anom, foot)
    for name in gp.COLUMN_NAMES:
        assert np.all(grids[name][foot] == 0.0), name


def test_step_edge_is_persistent_and_bounded():
    foot = _foot()
    anom = np.where(foot, 0.0, np.nan)
    anom[:, 45:] = np.where(foot[:, 45:], 1.0, np.nan)
    grids = gp.build_grids(anom, foot)
    persist = grids["gpers_persist_min"]
    # The edge is at columns 44/45: the persistence response there beats a flat interior point.
    assert persist[40, 44] > persist[40, 20] + 0.1
    for name in gp.COLUMN_NAMES:
        vals = grids[name][foot]
        assert np.all(np.isfinite(vals))
        assert vals.min() >= 0.0 and vals.max() <= 1.0 + 1e-6
        # Outside the footprint nothing is emitted.
        assert np.all(grids[name][~foot] == 0.0)


def test_feature_matrix_shape_and_order():
    foot = _foot()
    anom = np.where(foot, np.arange(foot.size, dtype=float).reshape(foot.shape) % 7, np.nan)
    X = gp.build_feature_matrix(anom, foot)
    assert X.shape == (int(foot.sum()), 4)
    assert X.dtype == np.float32
    assert np.all(np.isfinite(X))
    # Persistence is never larger than any single scale column.
    assert np.all(X[:, 3] <= X[:, :3].min(axis=1) + 1e-6)
