"""Joint gravity–magnetic cross-gradient structural-coupling features for hypothesis H29-XG.

Preregistered in knowledge/39_preregistration_H29-XG_2026-10-29.md (frozen before scoring).

Reads only the label-free cached bands ``iso_grav_anom`` and ``rtp``. It never reads catalogue
labels, hidden-set masks, distances to catalogue traces, or any prediction.

For each field the footprint-normalized Gaussian gradient is taken at sigma in {2, 4} px. The
cross-gradient is t = g_x m_y - g_y m_x (Gallardo & Meju 2003, doi:10.1029/2003GL017370; 2004,
doi:10.1029/2003JB002716). Three footprint-ordered columns are returned:

* ``xg_amp_s2``  |t| at sigma = 2 px (amplitude-weighted coupling)
* ``xg_amp_s4``  |t| at sigma = 4 px
* ``xg_sin_s2``  |t| / (|grad g| |grad m|) at sigma = 2 px (angle only, amplitude removed)

Every column is divided by its footprint 99th percentile and clipped to [0, 1].
"""

from __future__ import annotations

import numpy as np

from .gravity_persistence import _normalized_smooth, _p99_clip01

SCALES_PX = (2.0, 4.0)
COLUMN_NAMES = ["xg_amp_s2", "xg_amp_s4", "xg_sin_s2"]
SIN_GUARD_REL = 1e-6  # weak-gradient cells (|grad g||grad m| < 1e-6 of its p99) map to zero


def _smooth_and_grad(values: np.ndarray, foot: np.ndarray, sigma: float) -> tuple[np.ndarray, np.ndarray]:
    finite = foot & np.isfinite(values)
    f = np.where(finite, values, 0.0).astype(np.float64)
    m = finite.astype(np.float64)
    g = _normalized_smooth(f, m, sigma)
    gy, gx = np.gradient(g)
    return gy, gx


def build_grids(grav: np.ndarray, mag: np.ndarray, foot: np.ndarray) -> dict[str, np.ndarray]:
    """Full-grid float32 arrays, zero outside the footprint.

    ``grav`` and ``mag`` are full-grid with NaN outside the footprint.
    """
    foot = np.asarray(foot, bool)
    out: dict[str, np.ndarray] = {}
    for sigma, name in zip(SCALES_PX, COLUMN_NAMES[:2], strict=True):
        gy, gx = _smooth_and_grad(grav, foot, sigma)
        my, mx = _smooth_and_grad(mag, foot, sigma)
        t = gx * my - gy * mx
        amp = np.where(foot, np.abs(t), 0.0)
        floor_amp = 1e-9 * max(float(np.nanmax(np.abs(amp))) if amp.size else 0.0, 1e-300)
        out[name] = _p99_clip01(np.where(amp > floor_amp, amp, 0.0), foot, floor=floor_amp)
        if sigma == 2.0:
            denom = np.hypot(gx, gy) * np.hypot(mx, my)
            denom = np.where(foot, denom, 0.0)
            p99 = float(np.percentile(denom[foot], 99)) if foot.any() else 0.0
            guard = SIN_GUARD_REL * p99 if p99 > 0 else np.inf
            sin = np.where(denom > guard, np.abs(t) / np.maximum(denom, 1e-300), 0.0)
            sin = np.where(foot, np.clip(sin, 0.0, 1.0), 0.0)
            out[COLUMN_NAMES[2]] = _p99_clip01(sin, foot, floor=0.0)
    return out


def build_feature_matrix(grav: np.ndarray, mag: np.ndarray, foot: np.ndarray) -> np.ndarray:
    """(n_footprint, 3) float32 matrix in row-major footprint order."""
    grids = build_grids(grav, mag, foot)
    return np.stack([grids[name][foot] for name in COLUMN_NAMES], axis=1).astype(np.float32)
