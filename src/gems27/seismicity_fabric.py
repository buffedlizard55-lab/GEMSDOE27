"""Seismicity-fabric lineament transform (H28-4, untried hypothesis).

Builds directional lineament strength from earthquake-density bands and shear-rate:
  * deq_n100a15  - earthquake density (catalog A)
  * ieq_n100a15  - earthquake density (catalog B)
  * geod_shearrate - geodetic shear rate

A blind fault strand can expose itself as a persistent linear earthquake fabric aligned
with the local shear direction, even when no Quaternary surface trace is catalogued.
This targets faults missing from the USGS/INGENIOUS catalogue: the catalogue only lists
faults with evidence of Quaternary surface deformation (~1.6 Ma scope), whereas a
seismicity fabric marks *currently active* slip that may be blind or alluvium-covered.

Method:
  1. Stack and robust-scale the two earthquake-density bands.
  2. Compute the shear-rate gradient orientation field.
  3. For each of 8 orientations, compute a directional line-strength (morphological
     opening along that orientation) of the combined density.
  4. Take the maximum over orientations where the line direction agrees with the local
     shear direction (within 30 deg).
  5. Robust-scale to [0,1]; zero outside the footprint.

Differs from everything in the repo:
  * No previous candidate uses directional seismicity fabric (the refuted oriented
    LiDAR/geophysics line-integral arm used topography/geophysics bands, not seismicity).
  * It targets currently-active slip (seismicity) rather than Quaternary surface
    expression (catalogue) or topographic scarps (lidar).
  * Uses only hash-pinned bands already in the prepared 32-band matrix.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter, grey_opening

__all__ = ["SEISMICITY_FABRIC_NAMES", "seismicity_fabric_features"]

SEISMICITY_FABRIC_NAMES = (
    "seis_fabric_lineament_0",
    "seis_fabric_lineament_45",
    "seis_fabric_lineament_90",
    "seis_fabric_lineament_135",
    "seis_fabric_shear_aligned",
    "seis_fabric_combined",
)


def _robust_unit_scale(magnitude: np.ndarray, valid: np.ndarray) -> np.ndarray:
    values = magnitude[valid]
    if values.size == 0:
        return np.zeros(magnitude.shape, dtype=np.float32)
    lo, hi = np.percentile(values, (5.0, 95.0))
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        return np.zeros(magnitude.shape, dtype=np.float32)
    scaled = np.clip((magnitude - lo) / (hi - lo), 0.0, 1.0)
    scaled[~valid] = 0.0
    return scaled.astype(np.float32, copy=False)


def _directional_line_strength(score: np.ndarray, valid: np.ndarray,
                               angle_deg: float, length_px: int = 9) -> np.ndarray:
    """Line strength along `angle_deg` via grayscale opening with a line structuring element."""
    # Build a line SE: length_px long, 1 wide, rotated to angle_deg
    rad = np.deg2rad(angle_deg)
    # Line centered at origin, extending along the direction
    t = np.arange(-(length_px // 2), (length_px // 2) + 1)
    dy = np.round(-np.sin(rad) * t).astype(int)
    dx = np.round(np.cos(rad) * t).astype(int)
    se = np.zeros((length_px, length_px), dtype=bool)
    cy, cx = length_px // 2, length_px // 2
    for yy, xx in zip(dy, dx):
        se[cy + yy, cx + xx] = True
    s = np.where(valid & np.isfinite(score), score, 0.0).astype(np.float32)
    opened = grey_opening(s, structure=se, mode="constant", cval=0.0)
    return opened


def seismicity_fabric_features(deq: np.ndarray, ieq: np.ndarray, shear: np.ndarray,
                               valid: np.ndarray) -> np.ndarray:
    """Return six seismicity-fabric features, all in [0,1], zero outside `valid`.

    Parameters
    ----------
    deq, ieq, shear : 2-D arrays, same shape
        Earthquake-density catalog A, catalog B, and geodetic shear rate.
    valid : 2-D bool array
        Footprint cells that are valid for all inputs.

    Returns
    -------
    stack : (6, H, W) float32 array
        Features: 4 directional line strengths (0,45,90,135 deg), shear-aligned
        lineament strength, and combined score.
    """
    deq = np.asarray(deq, dtype=np.float32)
    ieq = np.asarray(ieq, dtype=np.float32)
    shear = np.asarray(shear, dtype=np.float32)
    mask = np.asarray(valid, dtype=bool)
    if deq.shape != ieq.shape or deq.shape != shear.shape or deq.shape != mask.shape:
        raise ValueError("deq, ieq, shear and valid must be same-shape 2-D arrays")
    mask = mask & np.isfinite(deq) & np.isfinite(ieq) & np.isfinite(shear)
    if not np.any(mask):
        raise ValueError("no cells valid for all seismicity inputs")

    # Combined density: robust-scale each then average
    d_s = _robust_unit_scale(deq, mask)
    i_s = _robust_unit_scale(ieq, mask)
    density = np.clip((d_s + i_s) / 2.0, 0.0, 1.0)

    # Shear gradient orientation
    s_filled = np.where(mask, shear, 0.0).astype(np.float32)
    s_smooth = gaussian_filter(s_filled, sigma=2.0, mode="nearest")
    sy, sx = np.gradient(s_smooth, 100.0, 100.0)
    shear_ori = np.mod(np.arctan2(sy, sx), np.pi)  # 0..pi, shear direction
    shear_mag = np.hypot(sx, sy)
    shear_s = _robust_unit_scale(shear_mag, mask)

    # Directional line strengths at 4 orientations
    line_strengths = []
    for angle in (0.0, 45.0, 90.0, 135.0):
        ls = _directional_line_strength(density, mask, angle_deg=angle, length_px=9)
        line_strengths.append(_robust_unit_scale(ls, mask))

    # Shear-aligned lineament: max over orientations whose direction agrees with shear
    # within 30 deg (pi/6). For each pixel, find best-aligned line strength.
    aligned = np.zeros(mask.shape, dtype=np.float32)
    for angle, ls in zip((0.0, 45.0, 90.0, 135.0), line_strengths):
        angle_rad = np.deg2rad(angle)
        # Angular difference between line orientation and shear direction (mod pi)
        diff = np.abs(np.mod(shear_ori - angle_rad, np.pi))
        diff = np.minimum(diff, np.pi - diff)
        agree = diff <= np.pi / 6.0  # within 30 deg
        aligned = np.where(mask & agree & (ls > aligned), ls, aligned)

    # Combined: density * shear-strength * alignment
    combined = np.clip(density * shear_s * (aligned > 0).astype(np.float32), 0.0, 1.0)

    stack = np.stack(
        (*line_strengths, aligned, combined), axis=0
    ).astype(np.float32, copy=False)
    stack[:, ~mask] = 0.0
    if not np.isfinite(stack).all():
        raise ValueError("seismicity-fabric transform produced non-finite values")
    if float(stack.min()) < 0.0 or float(stack.max()) > 1.0:
        raise ValueError("seismicity-fabric features escaped [0,1]")
    return stack


def band_indices(names: list[str]) -> dict[str, int]:
    """Map feature name -> column index in the prepared 32-band matrix."""
    return {name: idx for idx, name in enumerate(names)}