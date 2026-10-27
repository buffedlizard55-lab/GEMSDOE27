"""Label-free short buried basement-step transforms for lane H33-1.

A fault under thicker basin fill can step ``depth_to_base_surf`` without a young
lidar scarp. These six grids are deterministic functions of depth, lidar step,
and geodetic shear. They do not read labels, catalogue distance, or scores.
Outputs are percentile-ranked to [0, 1] inside the footprint.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter, uniform_filter

TRANSFORM_NAMES = [
    "bss_depth_grad_s2",
    "bss_depth_grad_s6",
    "bss_depth_coh_s4",
    "bss_lowscarp",
    "bss_buried_step",
    "bss_short_aniso",
]


def _finite_fill(arr: np.ndarray, foot: np.ndarray) -> np.ndarray:
    a = np.asarray(arr, dtype=np.float32).copy()
    bad = ~foot | ~np.isfinite(a) | (np.abs(a) > 1e30)
    if not bad.any():
        return a
    good = foot & ~bad
    fill = float(np.median(a[good])) if good.any() else 0.0
    a[bad] = fill
    return a


def _rank01(values: np.ndarray) -> np.ndarray:
    v = np.asarray(values, dtype=np.float64)
    order = np.argsort(v, kind="mergesort")
    ranks = np.empty(v.size, dtype=np.float64)
    ranks[order] = np.linspace(0.0, 1.0, v.size, endpoint=True)
    # Average ties so a constant grid is 0.5, not a ramp.
    _, inv, counts = np.unique(v, return_inverse=True, return_counts=True)
    if np.any(counts > 1):
        sum_ranks = np.bincount(inv, weights=ranks)
        ranks = (sum_ranks / counts)[inv]
    return ranks.astype(np.float32)


def _grad_mag(a: np.ndarray, sigma: float) -> np.ndarray:
    s = gaussian_filter(a, sigma=sigma) if sigma > 0 else a
    gy, gx = np.gradient(s)
    return np.hypot(gy, gx).astype(np.float32)


def _coherence(a: np.ndarray, sigma: float) -> np.ndarray:
    gy, gx = np.gradient(gaussian_filter(a, sigma=1.0))
    jxx = gaussian_filter(gx * gx, sigma=sigma)
    jyy = gaussian_filter(gy * gy, sigma=sigma)
    jxy = gaussian_filter(gx * gy, sigma=sigma)
    disc = np.sqrt(np.maximum((jxx - jyy) ** 2 + 4.0 * jxy * jxy, 0.0))
    return (disc / (jxx + jyy + 1e-12)).astype(np.float32)


def _anisotropy(a: np.ndarray, length: int = 7) -> np.ndarray:
    s = gaussian_filter(a, sigma=0.8)
    horizontal = uniform_filter(s, size=(1, length))
    vertical = uniform_filter(s, size=(length, 1))
    peak = np.maximum(horizontal, vertical)
    mean = 0.5 * (horizontal + vertical)
    return ((peak - mean) / (np.abs(peak) + 1e-3)).astype(np.float32)


def build_grids(depth: np.ndarray, step: np.ndarray, shear: np.ndarray, foot: np.ndarray) -> dict[str, np.ndarray]:
    """Return the six named grids on the full array, finite inside ``foot``."""
    if depth.shape != step.shape or depth.shape != shear.shape or depth.shape != foot.shape:
        raise ValueError("depth, step, shear, and footprint must share a shape")
    foot = np.asarray(foot, bool)
    d = _finite_fill(depth, foot)
    st = _finite_fill(step, foot)
    sh = _finite_fill(shear, foot)
    g2 = _grad_mag(d, 2.0)
    g6 = _grad_mag(d, 6.0)
    coh = _coherence(d, 4.0)
    aniso = _anisotropy(g2, 7)
    idx = np.flatnonzero(foot)
    low = 1.0 - _rank01(st.ravel()[idx])
    rg2 = _rank01(g2.ravel()[idx])
    rsh = _rank01(sh.ravel()[idx])
    buried = (rg2 * low * rsh).astype(np.float32)

    def paint(vals: np.ndarray) -> np.ndarray:
        out = np.zeros(foot.shape, np.float32)
        out.ravel()[idx] = _rank01(np.asarray(vals, dtype=np.float64))
        return out

    grids = {
        "bss_depth_grad_s2": paint(g2.ravel()[idx]),
        "bss_depth_grad_s6": paint(g6.ravel()[idx]),
        "bss_depth_coh_s4": paint(coh.ravel()[idx]),
        "bss_lowscarp": paint(low),
        "bss_buried_step": paint(buried),
        "bss_short_aniso": paint(aniso.ravel()[idx]),
    }
    for name in TRANSFORM_NAMES:
        v = grids[name][foot]
        if not np.isfinite(v).all() or float(v.min()) < 0.0 or float(v.max()) > 1.0:
            raise ValueError(f"{name} is not a finite [0, 1] footprint field")
    return grids


def build_feature_matrix(depth: np.ndarray, step: np.ndarray, shear: np.ndarray, foot: np.ndarray) -> np.ndarray:
    """Footprint-ordered (n, 6) float32 matrix matching ``prepared/features.npy`` row order."""
    grids = build_grids(depth, step, shear, foot)
    cols = [grids[name][foot].astype(np.float32) for name in TRANSFORM_NAMES]
    return np.column_stack(cols)
