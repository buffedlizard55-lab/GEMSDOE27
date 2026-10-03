import numpy as np
import pytest

from gems27.annulus import distance_annulus, select_score_ranked_spaced_candidates


def test_distance_annulus_uses_open_inner_and_closed_outer_bounds():
    distances = np.array([[0.0, 1.0, np.sqrt(2.0), 3.0, 3.01, np.inf]])
    mask = distance_annulus(distances)
    assert mask.tolist() == [[False, False, True, True, False, False]]


def test_distance_annulus_validates_shape_bounds_and_nan():
    with pytest.raises(ValueError, match="2-D"):
        distance_annulus(np.array([0.0, 2.0]))
    with pytest.raises(ValueError, match="bounds"):
        distance_annulus(np.zeros((2, 2)), inner_px=3.0, outer_px=2.0)
    with pytest.raises(ValueError, match="NaN"):
        distance_annulus(np.array([[np.nan]]))


def test_spaced_selector_uses_score_order_and_no_close_pairs():
    scores = np.array(
        [
            [10.0, 9.0, 8.0, 7.0],
            [6.0, 5.0, 4.0, 3.0],
            [2.0, 1.0, 0.0, -1.0],
        ],
        dtype=np.float32,
    )
    eligible = np.ones(scores.shape, dtype=bool)
    blocked = np.zeros(scores.shape, dtype=bool)
    before = (scores.copy(), eligible.copy(), blocked.copy())

    selected = select_score_ranked_spaced_candidates(scores, eligible, blocked, k=4)
    points = np.argwhere(selected)
    assert len(points) == 4
    for index, (row_a, col_a) in enumerate(points):
        for row_b, col_b in points[index + 1 :]:
            assert np.hypot(row_a - row_b, col_a - col_b) >= 1.5
    assert np.array_equal(scores, before[0])
    assert np.array_equal(eligible, before[1])
    assert np.array_equal(blocked, before[2])


def test_spaced_selector_respects_existing_emissions_and_row_major_ties():
    scores = np.ones((3, 4), dtype=np.float32)
    eligible = np.ones(scores.shape, dtype=bool)
    blocked = np.zeros(scores.shape, dtype=bool)
    blocked[2, 3] = True

    selected = select_score_ranked_spaced_candidates(scores, eligible, blocked, k=2)
    assert selected.sum() == 2
    assert not selected[2, 3]
    assert selected[0, 0]
    assert selected[0, 2]


def test_spaced_selector_excludes_candidates_too_close_to_blocked_pixels():
    scores = np.ones((5, 5), dtype=np.float32)
    eligible = np.ones(scores.shape, dtype=bool)
    blocked = np.zeros(scores.shape, dtype=bool)
    blocked[2, 2] = True

    selected = select_score_ranked_spaced_candidates(scores, eligible, blocked, k=1)
    assert selected.sum() == 1
    assert not selected[2, 2]
    assert np.linalg.norm(np.argwhere(selected)[0] - np.array([2, 2])) >= 1.5


def test_spaced_selector_returns_shortfall_without_relaxing_rule():
    scores = np.ones((5, 5), dtype=np.float32)
    eligible = np.ones(scores.shape, dtype=bool)
    blocked = np.ones(scores.shape, dtype=bool)
    blocked[:2, :2] = False

    selected = select_score_ranked_spaced_candidates(scores, eligible, blocked, k=2)
    assert selected.sum() == 1
    assert selected[0, 0]


def test_spaced_selector_handles_zero_k_and_invalid_inputs():
    scores = np.ones((2, 2), dtype=np.float32)
    masks = np.zeros(scores.shape, dtype=bool)
    assert not select_score_ranked_spaced_candidates(scores, masks, masks, k=0).any()
    with pytest.raises(ValueError, match="same 2-D shape"):
        select_score_ranked_spaced_candidates(scores, masks, np.zeros((1, 2)), k=1)
    with pytest.raises(ValueError, match="non-negative integer"):
        select_score_ranked_spaced_candidates(scores, masks, masks, k=-1)
    with pytest.raises(ValueError, match="positive"):
        select_score_ranked_spaced_candidates(scores, masks, masks, k=1, min_distance_px=0.0)
