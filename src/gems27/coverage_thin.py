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

import heapq

import numpy as np
from scipy.ndimage import correlate, distance_transform_edt, maximum_filter

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


def _triangular_kernel(radius_px: float = R) -> tuple[np.ndarray, int]:
    """Exact 2-D positive-support kernel k(d) = max(0, 1 - d / radius_px)."""
    if radius_px <= 0:
        raise ValueError(f"radius_px must be > 0, got {radius_px}")
    rad = int(np.floor(np.nextafter(float(radius_px), 0.0)))
    dy, dx = np.mgrid[-rad:rad + 1, -rad:rad + 1]
    k = np.maximum(0.0, 1.0 - np.hypot(dy, dx) / float(radius_px)).astype(np.float32)
    return k, rad


def expected_weighted_coverage(
    selected: np.ndarray,
    prob: np.ndarray,
    domain_mask: np.ndarray,
    *,
    radius_px: float = R,
    gamma: float = 1.5,
) -> float:
    """Evaluate F_w(S) = sum_{p in domain} prob(p)^gamma * max(0, 1 - d(p, S)/radius_px)."""
    sel = np.asarray(selected, bool)
    dom = np.asarray(domain_mask, bool)
    if not sel.any() or not dom.any():
        return 0.0
    p = np.where(dom & np.isfinite(prob), np.clip(prob, 0.0, 1.0), 0.0).astype(np.float64)
    w = np.power(p, float(gamma))
    d = distance_transform_edt(~sel)
    k = np.maximum(0.0, 1.0 - d / float(radius_px))
    return float(np.sum(w[dom] * k[dom]))


def weighted_celf_cover(
    prob: np.ndarray,
    eligible_mask: np.ndarray,
    domain_mask: np.ndarray,
    budget: int,
    *,
    radius_px: float = R,
    gamma: float = 1.5,
    min_sep_px: float = 2.0,
    max_candidates: int = 320_000,
) -> np.ndarray:
    """Exact lazy-heap CELF maximization of probability-weighted DTI kernel coverage.

    Maximizes the monotone submodular expected true-positive coverage functional
        F_w(S) = sum_{p in domain_mask} prob(p)**gamma * max_{y in S} max(0, 1 - ||p - y||_2 / radius_px)
    subject to S <= eligible_mask, |S| <= budget, and pairwise Euclidean spacing >= min_sep_px.

    Fixes H27-6 (unweighted coverage_thin, where flat interior plateaus outperformed high-posterior
    fault ridges): high-probability fault ridges receive proportionally larger marginal gain while
    coverage saturation inside radius_px automatically suppresses redundant same-ridge clumping.
    """
    elig = np.asarray(eligible_mask, bool)
    dom = np.asarray(domain_mask, bool)
    H, W = elig.shape
    if prob.shape != (H, W) or dom.shape != (H, W):
        raise ValueError(f"shape mismatch: prob={prob.shape}, eligible={elig.shape}, domain={dom.shape}")
    out = np.zeros((H, W), dtype=bool)
    if budget <= 0 or not elig.any() or not dom.any():
        return out

    p_clean = np.where(dom & np.isfinite(prob), np.clip(prob, 0.0, 1.0), 0.0).astype(np.float32)
    w = np.power(p_clean, np.float32(gamma)).astype(np.float32)
    K, rad = _triangular_kernel(radius_px)

    init_gain = correlate(w, K, mode="constant", cval=0.0)
    cand_mask = elig & (init_gain > 0.0)
    ys, xs = np.nonzero(cand_mask)
    if ys.size == 0:
        return out

    gains = init_gain[ys, xs]
    block_area = max(3, int(np.ceil(np.pi * max(float(min_sep_px), 1.0) ** 2 * 1.35)))
    if ys.size > max_candidates:
        keep_n = max(int(max_candidates), int(budget) * block_area)
        if ys.size > keep_n:
            idx = np.argpartition(-gains, keep_n - 1)[:keep_n]
            ys, xs, gains = ys[idx], xs[idx], gains[idx]

    # Deterministic initial heap ordering: (-gain, row, col, eval_epoch=0)
    heap: list[tuple[float, int, int, int]] = [
        (-float(g), int(y), int(x), 0) for y, x, g in zip(ys, xs, gains)
    ]
    heapq.heapify(heap)

    Hp, Wp = H + 2 * rad, W + 2 * rad
    w_pad = np.zeros((Hp, Wp), dtype=np.float32)
    w_pad[rad:rad + H, rad:rad + W] = w
    cov_pad = np.zeros((Hp, Wp), dtype=np.float32)
    dirty_epoch = np.zeros((Hp, Wp), dtype=np.int32)
    blocked = ~elig.copy()

    sep_offsets: tuple[np.ndarray, np.ndarray] | None = None
    if min_sep_px > 1.0:
        sr = int(np.floor(np.nextafter(float(min_sep_px), 0.0)))
        if sr >= 1:
            sdy, sdx = np.mgrid[-sr:sr + 1, -sr:sr + 1]
            sm = np.hypot(sdy, sdx) < float(min_sep_px)
            sep_offsets = (sdy[sm].astype(np.int32), sdx[sm].astype(np.int32))

    selected = 0
    cur_epoch = 0
    dirty_reach = 2 * rad

    while heap and selected < budget:
        neg_g, y, x, ep = heapq.heappop(heap)
        if blocked[y, x]:
            continue
        yp = y + rad
        xp = x + rad
        if ep < dirty_epoch[yp, xp]:
            patch_w = w_pad[yp - rad:yp + rad + 1, xp - rad:xp + rad + 1]
            patch_c = cov_pad[yp - rad:yp + rad + 1, xp - rad:xp + rad + 1]
            diff = K - patch_c
            new_g = float(np.sum(patch_w * np.maximum(diff, 0.0)))
            if new_g <= 1e-12:
                blocked[y, x] = True
                continue
            heapq.heappush(heap, (-new_g, y, x, cur_epoch))
            continue

        out[y, x] = True
        blocked[y, x] = True
        selected += 1

        patch_c = cov_pad[yp - rad:yp + rad + 1, xp - rad:xp + rad + 1]
        np.maximum(patch_c, K, out=patch_c)

        cur_epoch += 1
        y0d = max(0, yp - dirty_reach)
        y1d = min(Hp, yp + dirty_reach + 1)
        x0d = max(0, xp - dirty_reach)
        x1d = min(Wp, xp + dirty_reach + 1)
        dirty_epoch[y0d:y1d, x0d:x1d] = cur_epoch

        if sep_offsets is not None:
            by = y + sep_offsets[0]
            bx = x + sep_offsets[1]
            ok = (by >= 0) & (by < H) & (bx >= 0) & (bx < W)
            blocked[by[ok], bx[ok]] = True

    return out
