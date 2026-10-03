"""Distance-annulus candidates for the preregistered H27-10 test.

This module contains only the frozen, label-safe spatial mask and deterministic score-ranked
spacing helper. The holdout runner supplies distances to known labels and strictly out-of-fold
scores; hidden labels are never inputs to candidate construction.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.ndimage import binary_dilation


def distance_annulus(
    distance_px: np.ndarray, *, inner_px: float = 1.0, outer_px: float = 3.0
) -> np.ndarray:
    """Return cells with ``inner_px < distance <= outer_px``.

    Infinite distances are allowed and fall outside the annulus. NaN distances are rejected so a
    broken distance field cannot silently become a candidate mask.
    """
    distance = np.asarray(distance_px, dtype=np.float64)
    if distance.ndim != 2:
        raise ValueError("distance_px must be a 2-D array")
    if not np.isfinite(inner_px) or not np.isfinite(outer_px) or inner_px < 0 or outer_px <= inner_px:
        raise ValueError("annulus bounds must be finite, non-negative, and strictly increasing")
    if np.isnan(distance).any():
        raise ValueError("distance_px cannot contain NaN")
    return (distance > inner_px) & (distance <= outer_px)


def _spacing_offsets(min_distance_px: float) -> list[tuple[int, int]]:
    radius = int(math.ceil(min_distance_px))
    squared = min_distance_px * min_distance_px
    return [
        (dr, dc)
        for dr in range(-radius, radius + 1)
        for dc in range(-radius, radius + 1)
        if dr * dr + dc * dc < squared
    ]


def select_score_ranked_spaced_candidates(
    scores: np.ndarray,
    eligible: np.ndarray,
    blocked: np.ndarray,
    *,
    k: int,
    min_distance_px: float = 1.5,
) -> np.ndarray:
    """Greedily take the top ``k`` eligible scores at fixed Euclidean spacing.

    ``blocked`` marks already-emitted cells that new picks must stay away from. Candidate ties are
    resolved in row-major order. The spacing rule matches ``thinning.dot_thin``: a pair is rejected
    only when its pixel-centre distance is strictly less than ``min_distance_px``. If fewer than k
    candidates can be selected, the returned mask contains the available subset; the caller must
    treat a shortfall as a failed data gate rather than silently changing k.

    Inputs are not modified. Non-finite candidate scores are excluded.
    """
    value = np.asarray(scores, dtype=np.float32)
    eligible_mask = np.asarray(eligible, dtype=bool)
    blocked_mask = np.asarray(blocked, dtype=bool)
    if value.ndim != 2 or value.shape != eligible_mask.shape or value.shape != blocked_mask.shape:
        raise ValueError("scores, eligible and blocked must have the same 2-D shape")
    if not isinstance(k, (int, np.integer)) or k < 0:
        raise ValueError("k must be a non-negative integer")
    if not np.isfinite(min_distance_px) or min_distance_px <= 0:
        raise ValueError("min_distance_px must be finite and positive")

    selected = np.zeros(value.shape, dtype=bool)
    if k == 0:
        return selected

    candidate_idx = np.flatnonzero(eligible_mask & np.isfinite(value) & ~blocked_mask)
    if candidate_idx.size == 0:
        return selected
    flat_scores = value.ravel()
    order = np.lexsort((candidate_idx, -flat_scores[candidate_idx]))
    candidate_idx = candidate_idx[order]

    offsets = _spacing_offsets(float(min_distance_px))
    structure = np.zeros((2 * int(math.ceil(min_distance_px)) + 1,) * 2, dtype=bool)
    center = structure.shape[0] // 2
    for dr, dc in offsets:
        structure[center + dr, center + dc] = True
    blocked_area = binary_dilation(blocked_mask, structure=structure, border_value=0)
    height, width = value.shape
    selected_count = 0

    for flat_idx in candidate_idx:
        row, col = divmod(int(flat_idx), width)
        if blocked_area[row, col]:
            continue
        selected[row, col] = True
        selected_count += 1
        for dr, dc in offsets:
            rr, cc = row + dr, col + dc
            if 0 <= rr < height and 0 <= cc < width:
                blocked_area[rr, cc] = True
        if selected_count == k:
            break
    return selected
