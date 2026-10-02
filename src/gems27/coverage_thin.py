"""Coverage-optimal budget thinning (H27-6): choose *which* dots to keep by maximising coverage.

The problem with Poisson-disk thinning
--------------------------------------
`thinning.dot_thin` keeps a pixel iff no already-kept pixel is closer than `min_dist`. It is a
*packing* rule: it is blind to how much of the emission's own support the kept dots still cover.
Under the live-validated retention model (`scripts/optimize_budget.py`)

    credit(d) = credit_solid * c(d) / c_solid,   c(S') = mean over the footprint of max_{y in S'} k(d(.,y))

the score at a fixed budget is a monotone function of c(S'). So the right question is not "how far
apart are the dots?" but **"which N dots maximise c?"** -- a monotone submodular max-coverage problem
whose objective is exactly the metric's own credit functional.

Why this should beat packing: coverage holes form at ridge ends, junctions and high-curvature
bends, where isotropic blocking both wastes dots on redundant straight runs and leaves gaps.
Greedy max-coverage puts dots where coverage is deficient and skips redundant ones.

Algorithm (batched greedy, exact marginal gains)
------------------------------------------------
The marginal gain of adding a dot y is a *local* function of the current coverage map:

    gain(y) = sum_{|delta| < 3} max(0, k(delta) - cov(y + delta))

so it can be evaluated for every candidate simultaneously with 29 shifted-array operations. Each
batch accepts the local maxima of `gain` above a threshold (which enforces spacing), the coverage map
is rebuilt with one Euclidean distance transform, and the loop repeats until the budget is met.
Deterministic: no randomness, no labels, no scores are read.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import distance_transform_edt, maximum_filter

from . import metric

R = metric.RADIUS_PX
_OFFSETS = None
_FOOTPRINT_CACHE: dict[int, np.ndarray] = {}


def _offsets() -> list[tuple[int, int, float]]:
    global _OFFSETS
    if _OFFSETS is None:
        r = int(np.ceil(R))
        out = []
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                k = 1.0 - float(np.hypot(dy, dx)) / R
                if k > 0:
                    out.append((dy, dx, k))
        _OFFSETS = out
    return _OFFSETS


def coverage_map(selected: np.ndarray) -> np.ndarray:
    """cov(p) = max over selected dots of k(d(p, dot)), on the full grid (float32)."""
    if not selected.any():
        return np.zeros(selected.shape, np.float32)
    d = distance_transform_edt(~selected)
    return metric.kernel_from_distance(d).astype(np.float32)


def marginal_gain(candidates: np.ndarray, cov: np.ndarray) -> np.ndarray:
    """gain(y) for every pixel y: extra coverage y would add. Vectorised over the 29 kernel offsets."""
    gain = np.zeros(cov.shape, np.float32)
    for dy, dx, k in _offsets():
        shifted = np.roll(np.roll(cov, -dy, axis=0), -dx, axis=1)
        # outside the working window there is no selected dot, so coverage there is 0
        if dy > 0:
            shifted[-dy:, :] = 0.0
        elif dy < 0:
            shifted[:-dy, :] = 0.0
        if dx > 0:
            shifted[:, -dx:] = 0.0
        elif dx < 0:
            shifted[:, :-dx] = 0.0
        gain += np.maximum(np.float32(0.0), np.float32(k) - shifted)
    gain[~candidates] = 0.0
    return gain


def coverage_total(cov: np.ndarray, foot: np.ndarray) -> float:
    """The objective: sum of coverage over the footprint (= nfp * c)."""
    return float(cov[foot].sum())


def coverage_thin(mask: np.ndarray, budget: int, foot: np.ndarray | None = None,
                  footprint_radius: int = 4, max_batches: int = 200, block: float = 1.5,
                  batch_fraction: float = 0.06, verbose: bool = False) -> np.ndarray:
    """Select exactly `budget` pixels of `mask` maximising footprint coverage (batched greedy).

    `footprint_radius` bounds the working band to pixels within that many px of the emission, which
    is all the coverage objective can ever touch (the kernel has radius 3); this keeps the shifted
    array work on a small window instead of the whole 3730 x 3292 grid.
    """
    mask = np.asarray(mask, bool)
    if budget <= 0:
        return np.zeros_like(mask)
    if budget >= int(mask.sum()):
        return mask.copy()
    if foot is None:
        foot = np.ones(mask.shape, bool)

    ys, xs = np.nonzero(mask)
    pad = footprint_radius + 1
    y0, y1 = max(0, ys.min() - pad), min(mask.shape[0], ys.max() + pad + 1)
    x0, x1 = max(0, xs.min() - pad), min(mask.shape[1], xs.max() + pad + 1)
    sub_mask = mask[y0:y1, x0:x1]
    sub_foot = foot[y0:y1, x0:x1]
    # the band that coverage can ever reach
    band = distance_transform_edt(~sub_mask) <= footprint_radius
    band &= sub_foot

    selected = np.zeros(sub_mask.shape, bool)
    cand = sub_mask.copy()
    n_sel = 0
    r = int(np.ceil(block))
    dy, dx = np.mgrid[-r:r + 1, -r:r + 1]
    disc = (np.hypot(dy, dx) < block)
    Hs, Ws = sub_mask.shape
    for it in range(max_batches):
        if n_sel >= budget or not cand.any():
            break
        cov = coverage_map(selected)
        gain = marginal_gain(cand, cov)
        gain[~band] = 0.0
        loc = maximum_filter(gain, size=3, mode="constant", cval=0.0)
        peaks = cand & (gain >= loc) & (gain > 0)
        if not peaks.any():
            # fall back to any positive-gain candidate so the budget can still be filled
            peaks = cand & (gain > 0)
        if not peaks.any():
            break
        py, px = np.nonzero(peaks)
        order = np.lexsort((py, px, -gain[py, px]))
        py, px = py[order], px[order]
        # take only a slice of the remaining budget per batch so that coverage feedback (the whole
        # point of the method) is applied many times; each batch re-ranks by *current* marginal gain
        room = max(1, int(np.ceil((budget - n_sel) * batch_fraction)))
        blocked = np.zeros(sub_mask.shape, bool)
        taken = 0
        for y, x in zip(py.tolist(), px.tolist()):
            if taken >= room:
                break
            if blocked[y, x]:
                continue
            selected[y, x] = True
            cand[y, x] = False
            y0b, y1b = max(0, y - r), min(Hs, y + r + 1)
            x0b, x1b = max(0, x - r), min(Ws, x + r + 1)
            blocked[y0b:y1b, x0b:x1b] |= disc[y0b - y + r:y1b - y + r,
                                              x0b - x + r:x1b - x + r]
            taken += 1
        n_sel += taken
        if taken == 0:
            break
        if verbose and it % 10 == 0:
            print(f"  batch {it}: selected {n_sel:,}/{budget:,}")

    out = np.zeros(mask.shape, bool)
    out[y0:y1, x0:x1] = selected
    return out
