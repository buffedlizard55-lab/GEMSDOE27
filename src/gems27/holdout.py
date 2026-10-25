"""Spatially blocked, component-masked holdout (sparse-truth regime) with multi-seed replicates.

Design follows the owner's sibling harness (GEMSDOE24 `src/gems/holdout.py`): four spatial quadrants of
the footprint; in each quadrant a random 20 % of 8-connected catalogue components are *hidden* and
act as truth, everything else in the catalogue is *known*. Hidden truth is ~12k px, close to the
~12.6k px the sibling inferred for the real hidden set (calibration from a lattice submission; unconfirmed).

Known limits (also stated on the site): the hidden pieces are catalogue-internal, so any structure
that makes catalogue pieces predictable from their neighbours (shared segmentation, belts) inflates
recall relative to genuinely new expert-mapped faults. Use paired comparisons and controls only.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import label as ndi_label

FOLD_NAMES = ["NW", "NE_LidarGapHeavy", "SW", "SE"]
HIDE_FRACTION = 0.20


def make_quadrant_folds(footprint: np.ndarray) -> np.ndarray:
    footprint = np.asarray(footprint, bool)
    yy, xx = np.nonzero(footprint)
    y_med, x_med = int(np.median(yy)), int(np.median(xx))
    H, W = footprint.shape
    gy, gx = np.ogrid[:H, :W]
    fold = np.full((H, W), -1, dtype=np.int8)
    fold[(gy < y_med) & (gx < x_med) & footprint] = 0
    fold[(gy < y_med) & (gx >= x_med) & footprint] = 1
    fold[(gy >= y_med) & (gx < x_med) & footprint] = 2
    fold[(gy >= y_med) & (gx >= x_med) & footprint] = 3
    return fold


def hide_components(truth: np.ndarray, frac: float, seed: int) -> np.ndarray:
    comp, n = ndi_label(truth, structure=np.ones((3, 3), int))
    if n == 0 or frac <= 0:
        return np.zeros_like(truth, bool)
    rng = np.random.default_rng(seed)
    keep = rng.choice(np.arange(1, n + 1), size=max(1, int(round(frac * n))), replace=False)
    return np.isin(comp, keep)


@dataclass
class Split:
    fold_id: int
    name: str
    seed: int
    fold_mask: np.ndarray   # full-grid bool, the quadrant
    hidden: np.ndarray      # full-grid bool, hidden truth (inside quadrant)
    known: np.ndarray       # all visible catalogue pixels; exact scoring mask
    feature_known: np.ndarray  # visible labels permitted for catalogue-derived features
    feature_buffer_px: int


def make_split(
    labels: np.ndarray,
    fold: np.ndarray,
    fold_id: int,
    seed: int,
    *,
    feature_buffer_px: int = 0,
) -> Split:
    """Hide whole 8-connected components and optionally buffer feature construction.

    `known` remains the pixel-exact visible-label mask used to exclude known positives from scoring.
    `feature_known` is stricter: visible fault pixels within `feature_buffer_px` of hidden truth are
    removed before constructing a graph, distance field, or other catalogue-derived predictor.
    Keeping these masks separate prevents a buffer from changing the scoring truth/mask.

    The zero-buffer default preserves historical preregistrations. New buffered experiments must
    pass their frozen buffer explicitly and record it in their evidence.
    """
    if feature_buffer_px < 0:
        raise ValueError("feature_buffer_px must be non-negative")
    labels = np.asarray(labels, dtype=bool)
    fm = np.asarray(fold == fold_id, dtype=bool)
    if labels.shape != fm.shape:
        raise ValueError("labels and fold grid must have equal shapes")
    hidden = hide_components(labels & fm, HIDE_FRACTION, seed=4242 + fold_id + 1000 * seed)
    known = labels & ~hidden
    if feature_buffer_px:
        from scipy.ndimage import distance_transform_edt

        d_hidden = distance_transform_edt(~hidden)
        feature_known = known & (d_hidden > feature_buffer_px)
    else:
        feature_known = known.copy()
    return Split(
        fold_id,
        FOLD_NAMES[fold_id],
        seed,
        fm,
        hidden,
        known,
        feature_known,
        int(feature_buffer_px),
    )


def crop(mask_or_arr: np.ndarray, fold_mask: np.ndarray) -> tuple[slice, slice]:
    r = np.nonzero(fold_mask.any(axis=1))[0][[0, -1]]
    c = np.nonzero(fold_mask.any(axis=0))[0][[0, -1]]
    return slice(r[0], r[1] + 1), slice(c[0], c[1] + 1)
