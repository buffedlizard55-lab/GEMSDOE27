"""Scale-persistent gravity horizontal-gradient edges for hypothesis H28-6.

Preregistered in knowledge/36_preregistration_H28-6_2026-10-28.md (frozen before scoring).

Reads only the label-free cached band ``iso_grav_anom``. It never reads catalogue labels,
hidden-set masks, distances to catalogue traces, or any prediction. Four footprint-ordered
columns are returned: the single-scale normalized horizontal-gradient magnitudes at 1, 2 and
4 px, and their pointwise minimum (the scale-persistence column).

This is a deliberate reduction of an analytic signal: the vertical derivative term is omitted,
because ``iso_grav_anom_vg`` is already in the cached stack.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter

SCALES_PX = (1.0, 2.0, 4.0)
COLUMN_NAMES = ["gpers_h_s1", "gpers_h_s2", "gpers_h_s4", "gpers_persist_min"]


def _normalized_smooth(values: np.ndarray, mask: np.ndarray, sigma: float) -> np.ndarray:
    """Gaussian convolution of ``values`` restricted to ``mask`` (normalized convolution)."""
    num = gaussian_filter(values * mask, sigma=sigma, mode="nearest")
    den = gaussian_filter(mask.astype(np.float64), sigma=sigma, mode="nearest")
    return np.where(den > 1e-6, num / np.maximum(den, 1e-6), 0.0)


def _p99_clip01(h: np.ndarray, foot: np.ndarray, floor: float) -> np.ndarray:
    """Normalize by the footprint p99. Gradients below ``floor`` are float round-off, not edges."""
    vals = h[foot]
    scale = float(np.percentile(vals, 99)) if vals.size else 0.0
    if not np.isfinite(scale) or scale <= floor:
        return np.zeros_like(h, dtype=np.float32)
    return np.clip(h / scale, 0.0, 1.0).astype(np.float32)


def build_grids(anomaly: np.ndarray, foot: np.ndarray) -> dict[str, np.ndarray]:
    """Full-grid float32 arrays, zero outside the footprint.

    ``anomaly`` is the full-grid ``iso_grav_anom`` with NaN outside the footprint.
    """
    foot = np.asarray(foot, bool)
    finite = foot & np.isfinite(anomaly)
    f = np.where(finite, anomaly, 0.0).astype(np.float64)
    m = finite.astype(np.float64)
    # Relative floor: 1e-9 of the anomaly amplitude in the footprint. A constant field has
    # gradients at round-off level only, which must map to zero rather than to a full-scale edge.
    amp = float(np.max(np.abs(f[finite]))) if finite.any() else 0.0
    floor = 1e-9 * max(amp, 1e-300)
    out: dict[str, np.ndarray] = {}
    norm_stack = []
    for sigma, name in zip(SCALES_PX, COLUMN_NAMES[:3], strict=True):
        g = _normalized_smooth(f, m, sigma)
        gy, gx = np.gradient(g)
        h = np.sqrt(gy * gy + gx * gx)
        h = np.where(foot, h, 0.0)
        hn = _p99_clip01(h, foot, floor)
        out[name] = hn
        norm_stack.append(hn)
    out[COLUMN_NAMES[3]] = np.where(foot, np.minimum.reduce(norm_stack), 0.0).astype(np.float32)
    return out


def build_feature_matrix(anomaly: np.ndarray, foot: np.ndarray) -> np.ndarray:
    """(n_footprint, 4) float32 matrix in row-major footprint order."""
    grids = build_grids(anomaly, foot)
    return np.stack([grids[name][foot] for name in COLUMN_NAMES], axis=1).astype(np.float32)
