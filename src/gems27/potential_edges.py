"""Label-free multi-scale edges for gravity/magnetic potential fields (H28-1)."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter

EDGE_FEATURE_NAMES = (
    "potential_mag_edge_300m",
    "potential_mag_edge_1000m",
    "potential_grav_edge_300m",
    "potential_grav_edge_1000m",
    "potential_edge_concordance_1000m",
    "potential_edge_orientation_agreement_1000m",
)


def _nearest_fill(values: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Fill outside/nodata cells from the nearest valid in-footprint cell for filtering only."""
    if not np.any(valid):
        raise ValueError("potential-field raster has no finite in-footprint cells")
    if np.all(valid):
        return values.astype(np.float32, copy=True)
    indices = distance_transform_edt(~valid, return_distances=False, return_indices=True)
    return values[tuple(indices)].astype(np.float32, copy=False)


def _robust_unit_scale(magnitude: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Map in-footprint 5th/95th gradient percentiles to [0, 1], clipping tails."""
    values = magnitude[valid]
    if values.size == 0:
        raise ValueError("cannot scale an edge magnitude without valid cells")
    lo, hi = np.percentile(values, (5.0, 95.0))
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        return np.zeros(magnitude.shape, dtype=np.float32)
    scaled = np.clip((magnitude - lo) / (hi - lo), 0.0, 1.0)
    scaled[~valid] = 0.0
    return scaled.astype(np.float32, copy=False)


def multiscale_potential_edge_features(
    magnetic: np.ndarray,
    gravity: np.ndarray,
    valid: np.ndarray,
    *,
    pixel_size_m: float = 100.0,
    sigmas_px: tuple[float, float] = (3.0, 10.0),
) -> np.ndarray:
    """Return six finite, zero-outside-mask magnetic/gravity edge features.

    ``sigmas_px=(3, 10)`` corresponds to 300 m and 1 km Gaussian smoothing on the
    100 m competition grid. Gradient amplitudes are independently robust-scaled at
    the 5th/95th in-footprint percentiles. The cross-field concordance and absolute
    orientation agreement are set to zero unless both fields' 1 km gradient is at
    or above that field's in-footprint 10th percentile. Inputs are not modified.
    """
    mag = np.asarray(magnetic, dtype=np.float32)
    grav = np.asarray(gravity, dtype=np.float32)
    mask = np.asarray(valid, dtype=bool)
    if mag.ndim != 2 or mag.shape != grav.shape or mag.shape != mask.shape:
        raise ValueError("magnetic, gravity and valid must be same-shape 2-D arrays")
    if mag.shape[0] < 2 or mag.shape[1] < 2:
        raise ValueError("edge gradients require each spatial dimension to be at least 2")
    if not np.isfinite(pixel_size_m) or pixel_size_m <= 0:
        raise ValueError("pixel_size_m must be finite and positive")
    if len(sigmas_px) != 2 or any(not np.isfinite(s) or s <= 0 for s in sigmas_px):
        raise ValueError("sigmas_px must contain two finite positive values")

    mask = mask & np.isfinite(mag) & np.isfinite(grav)
    if not np.any(mask):
        raise ValueError("no cells are valid in both potential-field inputs")
    mag_filled = _nearest_fill(mag, mask)
    grav_filled = _nearest_fill(grav, mask)

    mag_norms: list[np.ndarray] = []
    grav_norms: list[np.ndarray] = []
    mag_gradients: tuple[np.ndarray, np.ndarray] | None = None
    grav_gradients: tuple[np.ndarray, np.ndarray] | None = None
    mag_magnitudes: np.ndarray | None = None
    grav_magnitudes: np.ndarray | None = None

    for sigma in sigmas_px:
        mag_smooth = gaussian_filter(mag_filled, sigma=float(sigma), mode="nearest")
        grav_smooth = gaussian_filter(grav_filled, sigma=float(sigma), mode="nearest")
        mag_gy, mag_gx = np.gradient(mag_smooth, pixel_size_m, pixel_size_m)
        grav_gy, grav_gx = np.gradient(grav_smooth, pixel_size_m, pixel_size_m)
        mag_magnitude = np.hypot(mag_gx, mag_gy)
        grav_magnitude = np.hypot(grav_gx, grav_gy)
        mag_norms.append(_robust_unit_scale(mag_magnitude, mask))
        grav_norms.append(_robust_unit_scale(grav_magnitude, mask))
        if sigma == sigmas_px[-1]:
            mag_gradients = (mag_gx, mag_gy)
            grav_gradients = (grav_gx, grav_gy)
            mag_magnitudes = mag_magnitude
            grav_magnitudes = grav_magnitude

    assert mag_gradients is not None and grav_gradients is not None
    assert mag_magnitudes is not None and grav_magnitudes is not None
    mag_gx, mag_gy = mag_gradients
    grav_gx, grav_gy = grav_gradients
    mag_threshold = float(np.percentile(mag_magnitudes[mask], 10.0))
    grav_threshold = float(np.percentile(grav_magnitudes[mask], 10.0))
    strong = mask & (mag_magnitudes >= mag_threshold) & (grav_magnitudes >= grav_threshold)

    mag_denom = np.maximum(mag_magnitudes, np.finfo(np.float32).tiny)
    grav_denom = np.maximum(grav_magnitudes, np.finfo(np.float32).tiny)
    mag_ux, mag_uy = mag_gx / mag_denom, mag_gy / mag_denom
    grav_ux, grav_uy = grav_gx / grav_denom, grav_gy / grav_denom
    orientation = np.zeros(mask.shape, dtype=np.float32)
    orientation[strong] = np.clip(
        np.abs(mag_ux[strong] * grav_ux[strong] + mag_uy[strong] * grav_uy[strong]), 0.0, 1.0
    )
    concordance = np.zeros(mask.shape, dtype=np.float32)
    concordance[strong] = np.minimum(mag_norms[-1][strong], grav_norms[-1][strong])

    stack = np.stack(
        (*mag_norms, *grav_norms, concordance, orientation),
        axis=0,
    ).astype(np.float32, copy=False)
    stack[:, ~mask] = 0.0
    if not np.isfinite(stack).all():
        raise ValueError("edge feature transform produced non-finite values")
    return stack
