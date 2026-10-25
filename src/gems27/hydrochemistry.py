"""H30 lane helpers: hydrothermal-chemistry re-ranking and deconflicted dot placement.

Everything here is deterministic and label-free: the chemistry field reads only station
coordinates and measured temperatures from the hash-pinned INGENIOUS/GDR wellspring CSV
(`data_cache/gdr_wellspring_in_footprint.csv`, sha256 122718e6…). The catalogue-derived
`dist_known_fault_px` column is deliberately NEVER read (fold discipline: any catalogue-based
quantity must come from visible faults only, and this field uses none at all).

Physics, briefly: a fault buried under alluvium or too old for the Quaternary surface-rupture
catalogue can still channel geothermal fluids, so wells/springs along it are warm and chemically
evolved. A local thermal-anomaly field therefore carries information the lidar-scarp regime cannot
see, and is used as a bounded multiplicative re-ranker of a detector surface (it can reorder
candidates inside sampling coverage, never invent or delete ridges).

Non-fault mimics (run-card copy): deep regional aquifer discharge unrelated to faulting;
geothermometer scatter from silica loss/mixing; sampling bias (wells drilled where accessible,
so coverage follows basins/districts, not geology); duplicate stations; non-fault heat sources.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.ndimage import distance_transform_edt, gaussian_filter, maximum_filter

NEIGHBOUR_RADIUS_PX = 15.0   # ~1.5 km local background window for the thermal anomaly
MIN_NEIGHBOURS = 5           # below this, fall back to the global median anomaly
SMOOTH_SIGMA_PX = 2.0        # 200 m smoothing of the rasterised anomaly
COVERAGE_DILATE_PX = 3       # coverage grows 300 m around any station
RERANK_GAMMA = 0.4           # bounded +/-40% multiplicative re-ranking


def _station_table(csv_path) -> pd.DataFrame:
    """One row per station cell: preferred temperature = geothermquartz_c else temp_c."""
    df = pd.read_csv(csv_path, low_memory=False)
    need = ["row", "col", "temp_c", "geothermquartz_c"]
    missing = [c for c in need if c not in df.columns]
    if missing:
        raise ValueError(f"wellspring CSV missing columns: {missing}")
    # Deliberate: `dist_known_fault_px` (catalogue-derived) is never read here.
    t = df[need].copy()
    t = t[pd.to_numeric(t["row"], errors="coerce").notna() & pd.to_numeric(t["col"], errors="coerce").notna()]
    t["temp"] = pd.to_numeric(t["geothermquartz_c"], errors="coerce")
    fallback = pd.to_numeric(t["temp_c"], errors="coerce")
    t["temp"] = t["temp"].fillna(fallback)
    t = t[t["temp"].notna()]
    t["row"] = t["row"].astype(int)
    t["col"] = t["col"].astype(int)
    if t.empty:
        raise ValueError("no usable temperature stations in wellspring CSV")
    # Deduplicate stations that share a grid cell: keep the median temperature.
    return t.groupby(["row", "col"], as_index=False)["temp"].median()


def build_chemistry_field(csv_path, shape: tuple[int, int], foot: np.ndarray) -> dict[str, np.ndarray]:
    """Return {'anomaly', 'coverage'} full-grid float32/bool arrays.

    anomaly: rank-normalised local thermal contrast in [0,1] inside coverage (0 elsewhere);
    coverage: True where the smoothed station support is non-zero (dilated 3 px).
    """
    st = _station_table(csv_path)
    inside = (
        (st["row"].to_numpy() >= 0) & (st["row"].to_numpy() < shape[0])
        & (st["col"].to_numpy() >= 0) & (st["col"].to_numpy() < shape[1])
    )
    st = st[inside]
    pts = np.c_[st["row"].to_numpy(), st["col"].to_numpy()].astype(float)
    temps = st["temp"].to_numpy(float)

    # Local background: median temperature of stations within NEIGHBOUR_RADIUS_PX.
    from scipy.spatial import cKDTree

    tree = cKDTree(pts)
    neigh = tree.query_ball_point(pts, r=NEIGHBOUR_RADIUS_PX)
    local_med = np.empty_like(temps)
    for i, nb in enumerate(neigh):
        if len(nb) >= MIN_NEIGHBOURS:
            local_med[i] = np.median(temps[nb])
        else:
            local_med[i] = np.median(temps)  # global fallback
    anomaly_station = temps - local_med

    # Rasterise (max-pool stations into the grid), smooth, dilate coverage.
    support = np.zeros(shape, np.float32)
    support[st["row"].to_numpy(), st["col"].to_numpy()] = 1.0
    raw = np.full(shape, -np.inf, np.float32)
    raw[st["row"].to_numpy(), st["col"].to_numpy()] = np.maximum(
        raw[st["row"].to_numpy(), st["col"].to_numpy()], anomaly_station.astype(np.float32))
    # max-pool any cell that holds several stations, then fill non-station cells by smoothing
    pooled = maximum_filter(np.where(np.isfinite(raw), raw, -np.inf), size=3)
    pooled = np.where(support > 0, pooled, 0.0).astype(np.float32)
    smooth = gaussian_filter(pooled, sigma=SMOOTH_SIGMA_PX)
    cover = maximum_filter(support > 0, size=2 * int(COVERAGE_DILATE_PX) + 1)
    cover &= np.asarray(foot, bool)

    vals = smooth[cover]
    finite = np.isfinite(vals)
    if finite.sum() < 2:
        raise ValueError("chemistry coverage too small to rank-normalise")
    # Percentile rank in [0,1] inside coverage (average ranks for ties).
    v = vals[finite].astype(np.float64)
    _, inv, counts = np.unique(v, return_inverse=True, return_counts=True)
    ends = np.cumsum(counts).astype(np.float64)
    starts = ends - counts
    avg = starts + (counts - 1) / 2.0
    ranks = (avg[inv] / max(len(v) - 1, 1)).astype(np.float32)
    field = np.zeros(shape, np.float32)
    field[cover] = np.where(finite, ranks, 0.0)
    return {"anomaly": field, "coverage": cover}


def rank_multiplier(chem: dict[str, np.ndarray], gamma: float = RERANK_GAMMA) -> np.ndarray:
    """Bounded re-ranking multiplier M in [1-gamma, 1+gamma]; exactly 1 outside coverage."""
    c = chem["anomaly"]
    m = np.ones_like(c, np.float32)
    inside = chem["coverage"]
    m[inside] = 1.0 + gamma * (2.0 * c[inside] - 1.0)
    return m


def rerank(prob: np.ndarray, chem: dict[str, np.ndarray], gamma: float = RERANK_GAMMA) -> np.ndarray:
    """S = D_prob * M, clipped to [0, +inf) for use as a pure ranking surface."""
    s = np.asarray(prob, np.float32) * rank_multiplier(chem, gamma)
    return np.clip(s, 0.0, None).astype(np.float32)


def conflicted_mask(repo_rasters: list[np.ndarray], shape: tuple[int, int]) -> np.ndarray:
    """True where a pixel lies within 3 px Euclidean of any positive pixel of any repo raster."""
    union = np.zeros(shape, bool)
    for a in repo_rasters:
        pos = np.isfinite(a) & (a > 0)
        if pos.any():
            union |= pos
    # 3-px Euclidean halo of the union of positives
    d = distance_transform_edt(~union)
    return d <= 3.0


def deconflicted_priority_poisson_disk(score: np.ndarray, candidates: np.ndarray,
                                       conflicted: np.ndarray, min_dist: float, budget: int,
                                       cap: float = 0.65) -> tuple[np.ndarray, dict]:
    """Priority Poisson-disk with a cap on dots placed on conflicted candidates.

    Single greedy pass over all candidates in descending-score order with >=min_dist spacing.
    A conflicted candidate is skipped once ceil(cap*budget) conflicted dots are already placed;
    clean candidates are always allowed. If the clean pool is exhausted before the budget is
    reached (measured by a completed pass with budget unfilled), one disclosed fallback pass
    re-admits conflicted candidates in priority order. The final overlap is measured and gated
    outside this function either way.
    """
    cand = np.asarray(candidates, bool)
    conf = np.asarray(conflicted, bool)
    n_conf_max = int(np.floor(cap * budget + 1e-9))
    dots = _greedy_capped(score, cand, conf, min_dist, budget, n_conf_max, allow_conf=True)
    shortfall = budget - int(dots.sum())
    if shortfall > 0:
        # clean pool exhausted before the budget: disclosed fallback, re-admit conflicted
        dots |= _greedy_capped(score, cand & ~dots, np.zeros_like(cand), min_dist,
                               shortfall, shortfall, allow_conf=True)
    info = {
        "dots_total": int(dots.sum()),
        "dots_conflicted": int((dots & conf).sum()),
        "conflicted_fraction": float((dots & conf).sum() / max(int(dots.sum()), 1)),
        "cap": cap,
        "budget": int(budget),
        "shortfall_after_fallback": max(0, budget - int(dots.sum())),
    }
    return dots, info


def _greedy_capped(score: np.ndarray, cand: np.ndarray, conf: np.ndarray, min_dist: float,
                   budget: int, n_conf_max: int, allow_conf: bool) -> np.ndarray:
    """Greedy priority placement honouring the conflicted-dot cap; spacing enforced globally."""
    H, W = cand.shape
    r = int(np.ceil(min_dist))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    disc = (yy * yy + xx * xx) < (min_dist * min_dist)
    dys, dxs = yy[disc], xx[disc]
    blocked = np.zeros((H, W), bool)
    out = np.zeros((H, W), bool)
    ys, xs = np.nonzero(cand)
    if len(ys) == 0 or budget <= 0:
        return out
    order = np.argsort(-score[ys, xs].astype(np.float64), kind="stable")
    kept = conf_kept = 0
    for idx in order:
        y, x = int(ys[idx]), int(xs[idx])
        if blocked[y, x]:
            continue
        if conf[y, x]:
            if not allow_conf or conf_kept >= n_conf_max:
                continue
            conf_kept += 1
        out[y, x] = True
        kept += 1
        if kept >= budget:
            break
        ny, nx = y + dys, x + dxs
        ok = (ny >= 0) & (nx >= 0) & (ny < H) & (nx < W)
        blocked[ny[ok], nx[ok]] = True
    return out
