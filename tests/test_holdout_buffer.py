import numpy as np
import pytest
from scipy.ndimage import distance_transform_edt

from gems27 import holdout


def _synthetic_split(buffer_px=2):
    labels = np.zeros((12, 12), dtype=bool)
    labels[1, 1] = labels[1, 4] = labels[2, 4] = labels[4, 1] = labels[4, 4] = labels[9, 9] = True
    fold = np.zeros_like(labels, dtype=np.int8)
    return labels, holdout.make_split(labels, fold, 0, 3, feature_buffer_px=buffer_px)


def test_feature_buffer_is_separate_from_pixel_exact_scoring_mask():
    labels, split = _synthetic_split()
    assert split.feature_buffer_px == 2
    assert np.array_equal(split.known, labels & ~split.hidden)
    assert not np.any(split.feature_known & split.hidden)
    assert np.all(split.feature_known <= split.known)

    distance = distance_transform_edt(~split.hidden)
    expected_feature_known = split.known & (distance > 2)
    assert np.array_equal(split.feature_known, expected_feature_known)
    # The test retains a true, hidden positive while excluding nearby visible fault pixels
    # from catalogue-derived features; those visible pixels remain masked from scoring.
    excluded_visible = split.known & ~split.feature_known
    assert excluded_visible.any()
    assert np.all(distance[excluded_visible] <= 2)


def test_zero_buffer_preserves_historical_known_mask():
    labels, split = _synthetic_split(buffer_px=0)
    assert split.feature_buffer_px == 0
    assert np.array_equal(split.feature_known, split.known)
    assert np.array_equal(split.known, labels & ~split.hidden)


def test_buffer_rejects_negative_and_shape_mismatch():
    labels, fold = np.zeros((4, 4), bool), np.zeros((4, 4), np.int8)
    with pytest.raises(ValueError, match="non-negative"):
        holdout.make_split(labels, fold, 0, 1, feature_buffer_px=-1)
    with pytest.raises(ValueError, match="equal shapes"):
        holdout.make_split(labels, np.zeros((3, 4), np.int8), 0, 1)
