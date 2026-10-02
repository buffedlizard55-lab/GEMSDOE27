from __future__ import annotations

import numpy as np
import pytest

from gems27.potential_edges import EDGE_FEATURE_NAMES, multiscale_potential_edge_features


def test_multiscale_edge_features_are_finite_scaled_and_masked() -> None:
    rows, cols = np.mgrid[:41, :41]
    step = (cols >= 20).astype(np.float32)
    valid = np.ones(step.shape, dtype=bool)
    valid[0, :] = False
    valid[:, 0] = False
    magnetic = step.copy()
    gravity = step.copy()
    magnetic[~valid] = np.nan
    gravity[~valid] = np.nan

    features = multiscale_potential_edge_features(magnetic, gravity, valid)

    assert features.shape == (len(EDGE_FEATURE_NAMES), *step.shape)
    assert np.isfinite(features).all()
    assert features.min() >= 0.0
    assert features.max() <= 1.0
    assert np.all(features[:, ~valid] == 0.0)
    # Identical potential-field edges have unit absolute orientation agreement at the shared edge.
    assert features[-1, 20, 20] == pytest.approx(1.0)
    assert features[0, 20, 20] > 0.0
    assert features[1, 20, 20] > 0.0


def test_constant_fields_have_no_edge_response() -> None:
    magnetic = np.full((12, 13), 5.0, dtype=np.float32)
    gravity = np.full((12, 13), -2.0, dtype=np.float32)
    valid = np.ones(magnetic.shape, dtype=bool)

    features = multiscale_potential_edge_features(magnetic, gravity, valid)

    assert features.shape[0] == 6
    assert np.isfinite(features).all()
    assert not np.any(features)


def test_rejects_empty_or_mismatched_input() -> None:
    values = np.ones((5, 6), dtype=np.float32)
    with pytest.raises(ValueError, match="same-shape"):
        multiscale_potential_edge_features(values, np.ones((5, 5)), np.ones((5, 6), bool))
    with pytest.raises(ValueError, match="no cells"):
        multiscale_potential_edge_features(values, values, np.zeros(values.shape, bool))
