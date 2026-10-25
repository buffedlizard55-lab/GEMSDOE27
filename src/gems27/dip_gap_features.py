"""Lane L-H30 new label-free transforms (preregistered in knowledge/20).

Two families, both deterministic functions of hash-pinned raster bands only
(no labels, no catalogue distance), percentile-ranked within the footprint
to [0, 1] float32 in row-major footprint order, reusing the shared
``gems27.subsurface_features`` helpers (``_fill`` / ``_grad_mag`` / ``_rank01``).

H30-1 dip advection
-------------------
A dipping fault's potential-field / basement-step edge sits laterally offset
down-dip from its surface trace by roughly ``depth * cot(dip)``. The detector
is per-pixel, so without help it scores the pixel over the *deep edge*, not
over the trace. For each candidate pixel we therefore sample the ranked edge
strength at ``x + r * u`` where ``u`` is the unit gradient of the
depth-to-basement surface (toward deeper basement = down-dip for a normal
fault whose hanging wall subsides) and ``r = clip(max(depth,0) * cot(dip)
 / 100 m, 0, 8)`` px for dip in {50, 70} degrees. Named non-fault mimics:
dipping lithologic contacts and unfaulted basin-margin basement steps.

H30-2 gap flanking
------------------
Where sedimentary cover thickens along strike, one continuous buried fault's
potential-field edge fades and resumes. ``max_u min(E(x-d*u), E(x+d*u))`` over
four strikes ``u`` at lags d = 6/12 px is high in a low-amplitude interval
bounded by collinear edges in the same field. Mimic: lithologic contacts
interrupted by cover; chance collinearity of unrelated segments.

H30-3 soft rank-taper emission lives here too: graduated values on a
priority-Poisson support, rescaled to the binary budget's effective mass.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates
from scipy.ndimage import shift as ndi_shift

from .subsurface_features import _fill, _grad_mag, _rank01

DIP_NAMES = [
    "dipadv_rtp_dip50",
    "dipadv_rtp_dip70",
    "dipadv_grav_dip50",
    "dipadv_grav_dip70",
    "dipadv_depth_dip50",
]
GAP_NAMES = [
    "gapflank_rtp_lag6",
    "gapflank_rtp_lag12",
    "gapflank_grav_lag6",
    "gapflank_grav_lag12",
]
NEW_FEATURE_NAMES = DIP_NAMES + GAP_NAMES

COT_DIP50 = 0.83909963  # cot(50 degrees)
COT_DIP70 = 0.36397023  # cot(70 degrees)
MAX_OFFSET_PX = 8.0
PIXEL_M = 100.0

# (dy, dx) strike unit vectors: E-W, N-S, NE-SW diagonal, NW-SE diagonal.
_STRIKES = (
    (0.0, 1.0),
    (1.0, 0.0),
    (np.sqrt(0.5), np.sqrt(0.5)),
    (np.sqrt(0.5), -np.sqrt(0.5)),
)


def _rank_grid(raw_grid: np.ndarray, foot: np.ndarray) -> np.ndarray:
    """Percentile-rank a full-grid array over footprint cells; 0 outside."""
    out = np.zeros(raw_grid.shape, dtype=np.float32)
    vals = raw_grid[foot].astype(np.float64)
    finite = np.isfinite(vals)
    vals = np.where(finite, vals, np.nanmedian(vals[finite]))
    out[foot] = _rank01(vals)
    return out


def _advect(edge_rank: np.ndarray, depth_filled: np.ndarray, cot_dip: float) -> np.ndarray:
    """Sample ``edge_rank`` down-dip: at ``x + r*u`` per pixel (see module docstring)."""
    smoothed = gaussian_filter(depth_filled, sigma=5.0)
    gy, gx = np.gradient(smoothed)
    mag = np.hypot(gy, gx)
    uy = np.where(mag > 0, gy / (mag + 1e-12), 0.0).astype(np.float32)
    ux = np.where(mag > 0, gx / (mag + 1e-12), 0.0).astype(np.float32)
    offset = np.clip(np.maximum(depth_filled, 0.0) * cot_dip / PIXEL_M, 0.0, MAX_OFFSET_PX)
    h, w = edge_rank.shape
    base_y = np.arange(h, dtype=np.float32)[:, None]
    base_x = np.arange(w, dtype=np.float32)[None, :]
    sample_y = base_y + offset * uy
    sample_x = base_x + offset * ux
    sampled = map_coordinates(edge_rank, [sample_y, sample_x], order=1, mode="nearest")
    return sampled.astype(np.float32, copy=False)


def _gap_flank(edge_rank: np.ndarray, lag_px: float) -> np.ndarray:
    """``max_strike min(E(x-lag*u), E(x+lag*u))`` for the four frozen strikes."""
    best = np.zeros(edge_rank.shape, dtype=np.float32)
    for dy, dx in _STRIKES:
        plus = ndi_shift(edge_rank, shift=(-dy * lag_px, -dx * lag_px), order=1, mode="nearest")
        minus = ndi_shift(edge_rank, shift=(dy * lag_px, dx * lag_px), order=1, mode="nearest")
        best = np.maximum(best, np.minimum(plus, minus))
    return best.astype(np.float32, copy=False)


def build_dip_gap_features(
    grids: dict[str, np.ndarray], foot: np.ndarray
) -> np.ndarray:
    """Return (n_footprint, 9) float32 ranks in ``NEW_FEATURE_NAMES`` order.

    ``grids`` holds full-grid arrays for ``rtp``, ``iso_grav_anom`` and
    ``depth_to_base_surf`` (NaN allowed outside the footprint; filled with the
    footprint mean for filtering only, as in ``subsurface_features._fill``).
    """
    for key in ("rtp", "iso_grav_anom", "depth_to_base_surf"):
        if grids[key].shape != foot.shape:
            raise ValueError(f"grid {key} shape {grids[key].shape} != footprint {foot.shape}")
    rtp = _fill(grids["rtp"], foot)
    grav = _fill(grids["iso_grav_anom"], foot)
    depth = _fill(grids["depth_to_base_surf"], foot)

    e_rtp = _rank_grid(_grad_mag(rtp, 2.0), foot)
    e_grav = _rank_grid(_grad_mag(grav, 2.0), foot)
    e_depth = _rank_grid(_grad_mag(depth, 3.0), foot)

    raw: dict[str, np.ndarray] = {
        "dipadv_rtp_dip50": _advect(e_rtp, depth, COT_DIP50),
        "dipadv_rtp_dip70": _advect(e_rtp, depth, COT_DIP70),
        "dipadv_grav_dip50": _advect(e_grav, depth, COT_DIP50),
        "dipadv_grav_dip70": _advect(e_grav, depth, COT_DIP70),
        "dipadv_depth_dip50": _advect(e_depth, depth, COT_DIP50),
        "gapflank_rtp_lag6": _gap_flank(e_rtp, 6.0),
        "gapflank_rtp_lag12": _gap_flank(e_rtp, 12.0),
        "gapflank_grav_lag6": _gap_flank(e_grav, 6.0),
        "gapflank_grav_lag12": _gap_flank(e_grav, 12.0),
    }
    assert list(raw) == NEW_FEATURE_NAMES, "feature order drift"
    cols = []
    for name in NEW_FEATURE_NAMES:
        cols.append(_rank_grid(raw[name], foot)[foot])
    out = np.stack(cols, axis=1).astype(np.float32)
    if not np.isfinite(out).all() or out.min() < 0.0 or out.max() > 1.0:
        raise ValueError("H30 transforms must be finite ranks in [0, 1]")
    return out


def soft_rank_taper(prob: np.ndarray, support: np.ndarray, budget_mass: float) -> np.ndarray:
    """H30-3: graduated values on ``support`` ordered by descending ``prob``.

    Raw value for the k-th support pixel (0-based, stable raster-order ties)
    is ``1 - k/N``; all values are then scaled by ``budget_mass / sum`` and
    clipped to [0, 1], so the effective emitted mass equals the frozen binary
    budget whenever the support is at least that large. Returns a full-grid
    float32 array that is 0 off-support.
    """
    out = np.zeros(prob.shape, dtype=np.float32)
    ys, xs = np.nonzero(support)
    n = len(ys)
    if n == 0 or budget_mass <= 0:
        return out
    order = np.argsort(-prob[ys, xs].astype(np.float64), kind="stable")
    raw = 1.0 - np.arange(n, dtype=np.float64) / float(n)
    scale = float(budget_mass) / float(raw.sum())
    values = np.clip(raw * scale, 0.0, 1.0)
    out[ys[order], xs[order]] = values.astype(np.float32)
    return out
