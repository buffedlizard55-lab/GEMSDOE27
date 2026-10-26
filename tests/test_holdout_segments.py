import numpy as np
import pytest

from gems27 import holdout, oof_detector


def _segmented_grid():
    foot = np.ones((20, 20), dtype=bool)
    labels = np.zeros_like(foot)
    groups = np.zeros(foot.shape, dtype=np.int32)
    locations = {
        1: (1, 1), 2: (1, 3), 3: (3, 1), 4: (3, 3),
        5: (1, 11), 6: (1, 13), 7: (3, 11), 8: (3, 13),
        9: (11, 1), 10: (11, 3), 11: (13, 1), 12: (13, 3),
        13: (11, 11), 14: (11, 13), 15: (13, 11), 16: (13, 13),
    }
    for group_id, (row, col) in locations.items():
        labels[row, col] = True
        groups[row, col] = group_id
    # One FID crosses quadrant boundaries. Whole-segment splitting must hide both pieces.
    for row, col in ((2, 2), (18, 18)):
        labels[row, col] = True
        groups[row, col] = 100
    return foot, labels, groups


def test_segment_split_hides_whole_group_and_buffers_both_masks():
    foot, labels, groups = _segmented_grid()
    split = next(
        candidate
        for seed in range(50)
        if 100 in (candidate := holdout.make_segment_split(labels, foot, groups, seed, frac=0.5)).hidden_group_ids
    )

    assert split.name == "whole-FID"
    assert split.hidden_group_ids == tuple(sorted(split.hidden_group_ids))
    assert split.hidden[2, 2] and split.hidden[18, 18]
    assert not split.known[2, 2] and not split.known[18, 18]
    assert np.array_equal(split.known, labels & ~split.hidden)

    train = holdout.buffered_training_mask(split, foot, buffer_px=1.0)
    score = holdout.buffered_scoring_mask(split, foot, buffer_px=1.0)
    assert not train[2, 2] and not train[18, 18]
    assert not train[2, 3] and not train[18, 17]
    assert score[2, 2] and score[18, 18]
    assert not score[2, 3] and not score[18, 17]


def test_segment_split_rejects_unmapped_positive_group():
    foot = np.ones((8, 8), dtype=bool)
    labels = np.zeros_like(foot)
    labels[1, 1] = True
    groups = np.zeros(foot.shape, dtype=np.int32)
    with pytest.raises(ValueError, match="positive segment group ID"):
        holdout.make_segment_split(labels, foot, groups, seed=1)


def test_masked_probability_fit_uses_shared_classifier_and_returns_bounded_grid():
    foot = np.ones((20, 20), dtype=bool)
    visible = np.zeros_like(foot)
    visible[2:6, 2] = True
    visible[12:16, 15] = True
    y_signal = np.zeros(foot.shape, dtype=np.float32)
    y_signal[visible] = 1.0
    X = np.column_stack((y_signal.ravel(), np.linspace(0, 1, foot.size, dtype=np.float32)))
    extra = np.column_stack((np.cos(np.arange(foot.size)),)).astype(np.float32)
    training = foot.copy()
    training[8:12, 8:12] = False

    prob = oof_detector.fit_predict_visible_probabilities(
        foot, visible, training, extra=extra, seed=77, chunk=100, base_features=X
    )

    assert prob.shape == foot.shape
    assert np.isfinite(prob[foot]).all()
    assert prob[foot].min() >= 0.0
    assert prob[foot].max() <= 1.0
    assert np.all(prob[~foot] == 0.0)
