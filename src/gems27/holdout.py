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
    fold_mask: np.ndarray   # full-grid bool, the evaluation domain
    hidden: np.ndarray      # full-grid bool, withheld positive pixels
    known: np.ndarray       # full-grid bool, visible catalogue pixels
    hidden_group_ids: tuple[int, ...] = ()  # vector-segment groups; empty for legacy component splits


def make_segment_split(
    labels: np.ndarray,
    footprint: np.ndarray,
    group_map: np.ndarray,
    seed: int,
    frac: float = 0.20,
) -> Split:
    """Withhold complete vector-fault groups, stratified by group-centroid quadrant.

    ``group_map`` is a positive integer ID per catalogue pixel (for example, the nearest
    NBMG Qfaults feature/FID index from ``VectorAttribution.pix_fid_idx``); zero is reserved
    for pixels without a mapped segment. A selected group is hidden on the *entire* grid,
    including any portions outside the quadrant containing its centroid. The returned
    ``fold_mask`` is the footprint, so callers must use ``buffered_scoring_mask`` and
    ``buffered_training_mask`` to enforce the registered exclusion zone.

    This is deliberately separate from ``make_split``: historical component-level results
    remain reproducible, while new whole-segment gates can use the protocol-compliant split.
    """
    labels = np.asarray(labels, bool)
    footprint = np.asarray(footprint, bool)
    groups = np.asarray(group_map)
    if labels.ndim != 2 or labels.shape != footprint.shape or labels.shape != groups.shape:
        raise ValueError("labels, footprint and group_map must have the same 2-D shape")
    if not np.isfinite(frac) or not 0.0 < frac < 1.0:
        raise ValueError("frac must be finite and strictly between 0 and 1")
    positive = labels & footprint
    if not positive.any():
        raise ValueError("cannot split a catalogue with no positive footprint pixels")
    if np.any(groups[positive] <= 0):
        raise ValueError("every positive catalogue pixel must have a positive segment group ID")

    ids, inverse = np.unique(groups[positive].astype(np.int64), return_inverse=True)
    rows, cols = np.nonzero(positive)
    counts = np.bincount(inverse, minlength=len(ids)).astype(np.float64)
    row_centres = np.rint(np.bincount(inverse, weights=rows, minlength=len(ids)) / counts).astype(int)
    col_centres = np.rint(np.bincount(inverse, weights=cols, minlength=len(ids)) / counts).astype(int)
    folds = make_quadrant_folds(footprint)
    centre_fold = folds[row_centres, col_centres]
    rng_folds = []
    for fold_id in range(4):
        fold_ids = ids[centre_fold == fold_id]
        if len(fold_ids) == 0:
            continue
        n_hide = max(1, int(round(frac * len(fold_ids))))
        rng = np.random.default_rng(4242 + fold_id + 1000 * int(seed))
        rng_folds.extend(rng.choice(fold_ids, size=min(n_hide, len(fold_ids)), replace=False).tolist())
    hidden_ids = tuple(sorted(set(int(group_id) for group_id in rng_folds)))
    if not hidden_ids:
        raise ValueError("segment split selected no groups")
    hidden = positive & np.isin(groups, np.asarray(hidden_ids, dtype=np.int64))
    known = positive & ~hidden
    if not hidden.any() or np.any(hidden & known):
        raise RuntimeError("invalid whole-segment split")
    return Split(-1, "whole-FID", int(seed), footprint.copy(), hidden, known, hidden_ids)


def make_split(labels: np.ndarray, fold: np.ndarray, fold_id: int, seed: int) -> Split:
    fm = fold == fold_id
    hidden = hide_components(labels & fm, HIDE_FRACTION, seed=4242 + fold_id + 1000 * seed)
    return Split(fold_id, FOLD_NAMES[fold_id], seed, fm, hidden, labels & ~hidden)


def buffered_training_mask(split: "Split", footprint: np.ndarray, buffer_px: float = 6.0) -> np.ndarray:
    """Training cells outside the hidden-segment core and its spatial buffer."""
    from scipy.ndimage import distance_transform_edt

    if not np.isfinite(buffer_px) or buffer_px < 0:
        raise ValueError("buffer_px must be finite and non-negative")
    hidden = np.asarray(split.hidden, bool)
    foot = np.asarray(footprint, bool)
    if hidden.shape != foot.shape:
        raise ValueError("hidden mask and footprint must have the same shape")
    d_hidden = distance_transform_edt(~hidden)
    return foot & (d_hidden > buffer_px)


def buffered_scoring_mask(split: "Split", footprint: np.ndarray, buffer_px: float = 6.0) -> np.ndarray:
    """Pixels eligible for scoring under the parallel-run protocol.

    Pixels within ``buffer_px`` of a hidden segment but not on it are excluded from scoring
    (neither truth nor valid prediction area). Hidden positive cells remain scoreable. Visible
    catalogue cells stay masked pixel-exactly by passing ``split.known`` as ``known=`` to the
    metric. For a whole-FID split, ``split.fold_mask`` is the entire footprint; for historical
    component holdouts it is the evaluation quadrant.
    """
    from scipy.ndimage import distance_transform_edt

    if not np.isfinite(buffer_px) or buffer_px < 0:
        raise ValueError("buffer_px must be finite and non-negative")
    hidden = np.asarray(split.hidden, bool)
    foot = np.asarray(footprint, bool)
    if hidden.shape != foot.shape or split.fold_mask.shape != foot.shape:
        raise ValueError("split masks and footprint must have the same shape")
    d_hidden = distance_transform_edt(~hidden)
    ring = (d_hidden <= buffer_px) & ~hidden
    return foot & split.fold_mask & ~ring


def crop(mask_or_arr: np.ndarray, fold_mask: np.ndarray) -> tuple[slice, slice]:
    r = np.nonzero(fold_mask.any(axis=1))[0][[0, -1]]
    c = np.nonzero(fold_mask.any(axis=0))[0][[0, -1]]
    return slice(r[0], r[1] + 1), slice(c[0], c[1] + 1)
