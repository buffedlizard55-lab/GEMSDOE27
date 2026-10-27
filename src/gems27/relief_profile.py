"""Label-free detrended-relief profile features for the preregistered H29-5 proxy.

`det_elev` is *detrended* elevation, not a conditioned DEM. Its positive gradient is
not guaranteed to point uphill on the real terrain; these features are only a proxy
for relief breaks, not a drainage network, fan-apex inventory or fault map.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates

FEATURE_NAMES = (
    "relief_slope_side_contrast",
    "relief_transverse_concavity",
    "relief_contrast_x_concavity",
    "relief_tangent_support",
)


def _normalise_positive(field: np.ndarray, valid: np.ndarray) -> np.ndarray:
    vals = field[valid & np.isfinite(field)]
    if not vals.size:
        return np.zeros_like(field, dtype=np.float32)
    p99 = float(np.percentile(vals, 99))
    if not np.isfinite(p99) or p99 <= 0:
        return np.zeros_like(field, dtype=np.float32)
    return np.clip(np.nan_to_num(field, nan=0.0) / p99, 0.0, 1.0).astype(np.float32)


def _sample(field: np.ndarray, ny: np.ndarray, nx: np.ndarray, distance: float,
            valid: np.ndarray, chunk_rows: int = 128) -> np.ndarray:
    """Bilinear sampling in row chunks; samples outside valid support contribute zero."""
    height, width = field.shape
    out = np.empty_like(field, dtype=np.float32)
    x = np.arange(width, dtype=np.float32)[None, :]
    src = np.where(valid, field, np.float32(0)).astype(np.float32, copy=False)
    for first in range(0, height, chunk_rows):
        last = min(first + chunk_rows, height)
        y = np.arange(first, last, dtype=np.float32)[:, None]
        coords = np.array((y + distance * ny[first:last], x + distance * nx[first:last]),
                          dtype=np.float32)
        out[first:last] = map_coordinates(src, coords, order=1, mode="constant", cval=0.0,
                                           prefilter=False)
    return out


def build_features(elevation: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Four finite [0,1] columns, in row-major footprint order; does not read labels."""
    elev = np.asarray(elevation, dtype=np.float32)
    foot = np.asarray(footprint, dtype=bool)
    if elev.ndim != 2 or elev.shape != foot.shape or not foot.any():
        raise ValueError("elevation and nonempty footprint must be equal-shaped 2-D arrays")
    valid = foot & np.isfinite(elev)
    if not valid.any():
        raise ValueError("no finite detrended elevation inside the footprint")

    weighted = gaussian_filter(np.where(valid, elev, np.float32(0)), 2.0, mode="constant")
    weights = gaussian_filter(valid.astype(np.float32), 2.0, mode="constant")
    smooth = np.divide(weighted, weights, out=np.zeros_like(weighted), where=weights > 1e-4)
    # Avoid interpreting the edge of the footprint or missing data as a real relief break.
    support = foot & (weights > 0.99)
    del weighted, weights
    gy, gx = np.gradient(smooth)
    slope = np.hypot(gy, gx).astype(np.float32)
    ny = np.divide(gy, slope, out=np.zeros_like(gy), where=slope > 1e-6)
    nx = np.divide(gx, slope, out=np.zeros_like(gx), where=slope > 1e-6)
    plus = _sample(slope, ny, nx, 3.0, support)
    minus = _sample(slope, ny, nx, -3.0, support)
    contrast = _normalise_positive(np.maximum(plus - minus, 0), support)
    del plus, minus, slope

    # Hessian of the smoothed field in row/column coordinates.
    hyy, hyx = np.gradient(gy)
    _, hxx = np.gradient(gx)
    del gy, gx, smooth
    # Tangent is perpendicular to the increasing-detrended-elevation normal.
    ty, tx = -nx, ny
    concavity = _normalise_positive(
        np.maximum(ty * ty * hyy + 2 * ty * tx * hyx + tx * tx * hxx, 0), support
    )
    del hyy, hyx, hxx
    joint = np.sqrt(contrast * concavity).astype(np.float32)
    along_plus = _sample(joint, ty, tx, 10.0, support)
    along_minus = _sample(joint, ty, tx, -10.0, support)
    tangent = np.minimum(along_plus, along_minus)

    out = np.empty((int(foot.sum()), len(FEATURE_NAMES)), dtype=np.float32)
    for i, feature in enumerate((contrast, concavity, joint, tangent)):
        feature[~support] = 0.0
        out[:, i] = feature[foot]
    if not np.isfinite(out).all() or np.any((out < 0) | (out > 1)):
        raise ValueError("non-finite or out-of-range relief-profile output")
    return out
