"""Weak-scarp continuity (WSC) score and ridge set — Lane L-2026-10-31-H35 (H35-1).

Label-free. Physical idea (preregistration: knowledge/45): faults missing from the
USGS/INGENIOUS Quaternary catalogue are preferentially the ones whose scarps are degraded,
partially buried, or otherwise below the corroborated-ridge bar that produced the H19-5 dot
family. Such traces keep *kilometre-scale linear continuity* even at low amplitude, so a
directional line-integral statistic restricted to the weak-moderate amplitude band responds to
them while suppressing (a) the noise floor and (b) the strong ridge echoes the family already
owns. Non-fault mimics to keep in mind: lithologic dip slopes and hogbacks, fluvial terrace
risers, Lake Lahontan shoreline strandlines, avalanche chutes, graded-road berms.

Construction (frozen at preregistration):

* response ``r = max(step_max, lappos_max, ex_max)`` from the 12-band 100 m LiDAR descriptor
  raster (bands 3/5/1; u8 quantisation q = 1 + round(254 t(x/xmax)), 0 = no LiDAR);
* weak-moderate gate ``g``: 1 on u8 [28, 120], cosine tapers of width 20 outside;
* across-strike smoothing sigma 0.8 px, oriented means at half-lengths {5, 10, 20} px over the
  four integer orientations (``gems27.newinfo.oriented_means``);
* per scale: ``maxm`` = max over orientations, ``meanm`` = mean over orientations,
  ``a = (maxm - meanm) / (maxm + 1e-6)``;
* WSC score = ``max over scales(maxm * a) * g``.

``wsc_ridges`` extracts 1-px ridge lines with the shared ``ridge_nms`` operator so WSC
candidates enter the same Poisson-dot pipeline as detector ridges. Nothing here reads labels,
predictions or scores.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter

from . import paths
from .newinfo import ORIENTS, oriented_means
from .oof_detector import ridge_nms

SCALES = (5, 10, 20)
ACROSS_SIGMA = 0.8
GATE_LO, GATE_HI = 28.0, 120.0
TAPER = 20.0

# band order in lidar_scarp_features_u8.tif (see lidar_scarp_features.json "bands")
_STEP_BAND, _LAPPOS_BAND, _EX_BAND = 3, 5, 1


def weak_gate(resp_u8: np.ndarray) -> np.ndarray:
    """Cosine-tapered band-pass on the u8 response: 1 on [28, 120], taper 20 outside."""
    v = np.asarray(resp_u8, np.float32)
    g = np.zeros_like(v)
    inside = (v >= GATE_LO) & (v <= GATE_HI)
    g[inside] = 1.0
    low = (v >= GATE_LO - TAPER) & (v < GATE_LO)
    g[low] = 0.5 * (1.0 + np.cos(np.pi * (GATE_LO - v[low]) / TAPER))
    high = (v > GATE_HI) & (v <= GATE_HI + TAPER)
    g[high] = 0.5 * (1.0 + np.cos(np.pi * (v[high] - GATE_HI) / TAPER))
    return g


def load_response(shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    """(r_u8, g) full-grid arrays: combined scarp response and the weak-moderate gate."""
    import rasterio

    with rasterio.open(paths.LIDAR) as ds:
        if ds.count < 5 or ds.shape != shape:
            raise ValueError("LiDAR descriptor raster has an unexpected shape or band count")
        step = ds.read(_STEP_BAND)
        lappos = ds.read(_LAPPOS_BAND)
        ex = ds.read(_EX_BAND)
    r_u8 = np.maximum(np.maximum(step, lappos), ex).astype(np.float32)
    return r_u8, weak_gate(r_u8)


def wsc_score(shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Full-grid (score, r_u8, gate). Score is 0 where there is no LiDAR response."""
    r_u8, g = load_response(shape)
    img = (r_u8 / 255.0) * g
    sm = gaussian_filter(img.astype(np.float32), ACROSS_SIGMA)
    # max over scales of (maxm * a), with maxm/meanm over the four orientations
    best = np.zeros(shape, np.float32)
    mx = {L: None for L in SCALES}
    ms = {L: np.zeros(shape, np.float32) for L in SCALES}
    for dr, dc, _ in ORIENTS:
        om = oriented_means(sm, dr, dc, SCALES)
        for L in SCALES:
            mx[L] = om[L].copy() if mx[L] is None else np.maximum(mx[L], om[L])
            ms[L] += om[L]
    for L in SCALES:
        mean_o = ms[L] / float(len(ORIENTS))
        a = (mx[L] - mean_o) / (mx[L] + 1e-6)
        best = np.maximum(best, (mx[L] * a).astype(np.float32))
    score = (best * g).astype(np.float32)
    return score, r_u8, g


def wsc_ridges(score: np.ndarray, foot: np.ndarray) -> np.ndarray:
    """1-px ridge lines of the WSC score (shared NMS operator, sigma 1.0)."""
    return ridge_nms(score, foot, sigma=1.0)
