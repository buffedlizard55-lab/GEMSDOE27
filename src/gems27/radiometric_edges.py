"""Multi-scale radiometric alteration-front edge features (H28-6).

The source rasters are uint8/rank-like relative products; edge magnitudes describe local spatial
change, not calibrated element concentration, alteration intensity, or fault probability. This module is
label-free and deliberately excludes all catalogue-derived fields.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter

SOURCE_FEATURE_NAMES = ("rad_source_thk_ratio", "rad_source_uth_ratio", "rad_source_tc")
EDGE_FEATURE_NAMES = (
    "rad_thk_edge_300m",
    "rad_thk_edge_800m",
    "rad_uth_edge_300m",
    "rad_uth_edge_800m",
    "rad_tc_edge_300m",
    "rad_tc_edge_800m",
    "rad_ratio_edge_orientation_agreement_300m",
    "rad_total_ratio_edge_orientation_agreement_300m",
)


def _nearest_fill(values: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Fill invalid pixels from nearest valid cell for convolution only."""
    if not np.any(valid):
        raise ValueError("radiometric raster has no valid in-footprint cells")
    if np.all(valid):
        return np.asarray(values, dtype=np.float32).copy()
    indices = distance_transform_edt(~valid, return_distances=False, return_indices=True)
    return np.asarray(values[tuple(indices)], dtype=np.float32)


def _robust_unit_scale(magnitude: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Linearly map in-footprint 5th/95th percentiles to [0,1], clipping both tails."""
    values = magnitude[valid]
    if values.size == 0:
        raise ValueError("cannot scale an edge magnitude without valid cells")
    lo, hi = np.percentile(values, (5.0, 95.0))
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        out = np.zeros(magnitude.shape, dtype=np.float32)
    else:
        out = np.clip((magnitude - lo) / (hi - lo), 0.0, 1.0).astype(np.float32)
    out[~valid] = 0.0
    return out


def multiscale_radiometric_edge_features(
    thk_ratio: np.ndarray,
    uth_ratio: np.ndarray,
    total_count: np.ndarray,
    valid: np.ndarray,
    *,
    pixel_size_m: float = 100.0,
    sigmas_px: tuple[float, float] = (3.0, 8.0),
) -> np.ndarray:
    """Return exactly eight finite float32 edge/coherence features, zero outside ``valid``.

    The first six columns are independently robust-scaled gradient magnitudes of Th/K, U/Th, and
    total-count rank-like grids at fixed Gaussian scales of 300 m and 800 m. The final two columns
    are absolute gradient-normal cosine similarity at 300 m for (Th/K, U/Th) and (total count, Th/K),
    zeroed unless both fields have local edge magnitude at or above their own 10th percentile.

    Inputs are not mutated. ``valid`` is intersected with finite values from all three fields. Invalid
    cells are nearest-filled only for convolution, and are always set to zero in every returned band.
    """
    fields = tuple(np.asarray(a, dtype=np.float32) for a in (thk_ratio, uth_ratio, total_count))
    mask = np.asarray(valid, dtype=bool).copy()
    if any(a.ndim != 2 for a in fields) or mask.ndim != 2:
        raise ValueError("all inputs must be 2-D arrays")
    if any(a.shape != mask.shape for a in fields):
        raise ValueError("all radiometric fields and valid mask must have the same shape")
    if min(mask.shape) < 2:
        raise ValueError("edge gradients require each spatial dimension to be at least 2")
    if not np.isfinite(pixel_size_m) or pixel_size_m <= 0:
        raise ValueError("pixel_size_m must be finite and positive")
    if len(sigmas_px) != 2 or any(not np.isfinite(s) or s <= 0 for s in sigmas_px):
        raise ValueError("sigmas_px must contain two finite positive values")

    mask &= np.logical_and.reduce([np.isfinite(a) for a in fields])
    if not mask.any():
        raise ValueError("no cells are valid in all radiometric inputs")
    filled = [_nearest_fill(a, mask) for a in fields]

    scaled: list[list[np.ndarray]] = [[], [], []]
    small_gradients: list[tuple[np.ndarray, np.ndarray]] = []
    small_magnitudes: list[np.ndarray] = []
    for field_idx, values in enumerate(filled):
        for sigma in sigmas_px:
            smoothed = gaussian_filter(values, sigma=float(sigma), mode="nearest")
            gy, gx = np.gradient(smoothed, pixel_size_m, pixel_size_m)
            magnitude = np.hypot(gx, gy)
            scaled[field_idx].append(_robust_unit_scale(magnitude, mask))
            if sigma == sigmas_px[0]:
                small_gradients.append((gx, gy))
                small_magnitudes.append(magnitude)

    thk_gx, thk_gy = small_gradients[0]
    uth_gx, uth_gy = small_gradients[1]
    tc_gx, tc_gy = small_gradients[2]

    def agreement(
        gx_a: np.ndarray,
        gy_a: np.ndarray,
        mag_a: np.ndarray,
        gx_b: np.ndarray,
        gy_b: np.ndarray,
        mag_b: np.ndarray,
    ) -> np.ndarray:
        threshold_a = float(np.percentile(mag_a[mask], 10.0))
        threshold_b = float(np.percentile(mag_b[mask], 10.0))
        strong = mask & (mag_a >= threshold_a) & (mag_b >= threshold_b)
        denom_a = np.maximum(mag_a, np.finfo(np.float32).tiny)
        denom_b = np.maximum(mag_b, np.finfo(np.float32).tiny)
        dot = (gx_a / denom_a) * (gx_b / denom_b) + (gy_a / denom_a) * (gy_b / denom_b)
        out = np.zeros(mask.shape, dtype=np.float32)
        out[strong] = np.clip(np.abs(dot[strong]), 0.0, 1.0)
        return out

    thk_mag, uth_mag, tc_mag = small_magnitudes
    thk_uth_agreement = agreement(thk_gx, thk_gy, thk_mag, uth_gx, uth_gy, uth_mag)
    tc_thk_agreement = agreement(tc_gx, tc_gy, tc_mag, thk_gx, thk_gy, thk_mag)
    stack = np.stack(
        (
            scaled[0][0], scaled[0][1],
            scaled[1][0], scaled[1][1],
            scaled[2][0], scaled[2][1],
            thk_uth_agreement, tc_thk_agreement,
        ),
        axis=0,
    ).astype(np.float32, copy=False)
    stack[:, ~mask] = 0.0
    if stack.shape[0] != len(EDGE_FEATURE_NAMES) or not np.isfinite(stack).all():
        raise ValueError("radiometric edge transform produced an invalid feature stack")
    if float(stack.min()) < 0.0 or float(stack.max()) > 1.0:
        raise ValueError("radiometric edge transform escaped [0,1]")
    return stack
