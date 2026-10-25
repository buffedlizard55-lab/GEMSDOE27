"""Label-free H28-3 strain--conductivity corridor features.

The transform uses only five supplied numerical grids.  It deliberately does not inspect the fault
catalogue; labels are used by the separate OOF classifier and evaluator only.  Features are bounded
in [0, 1], zero outside the common valid mask, and deterministic given the raster inputs.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter

FEATURE_NAMES = (
    "strain_dilation_core",
    "strain_gradient_300m",
    "shear_gradient_300m",
    "conductivity_gradient_300m",
    "strain_conductivity_corridor",
    "shallow_basement_corridor",
)


def _nearest_fill(values: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Fill invalid cells from the nearest valid one solely to make filters edge-stable."""
    if not valid.any():
        raise ValueError("no valid cells available for strain-conductivity filtering")
    if valid.all():
        return values.astype(np.float32, copy=True)
    nearest = distance_transform_edt(~valid, return_distances=False, return_indices=True)
    return values[tuple(nearest)].astype(np.float32, copy=False)


def robust_unit_scale(values: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Map valid-cell 5th--95th percentiles to [0,1]; set invalid locations to zero."""
    v = np.asarray(values, dtype=np.float32)
    mask = np.asarray(valid, dtype=bool)
    if v.shape != mask.shape or v.ndim != 2:
        raise ValueError("values and valid must be same-shape 2-D arrays")
    sample = v[mask]
    if sample.size == 0 or not np.isfinite(sample).all():
        raise ValueError("robust scaling needs finite values in the valid mask")
    lo, hi = np.percentile(sample, (5.0, 95.0))
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        out = np.zeros(v.shape, dtype=np.float32)
    else:
        out = np.clip((v - lo) / (hi - lo), 0.0, 1.0).astype(np.float32, copy=False)
    out[~mask] = 0.0
    return out


def _gradient_magnitude_and_vector(
    scaled: np.ndarray, valid: np.ndarray, *, sigma_px: float, pixel_size_m: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return robust-scaled 300-m gradient magnitude plus unscaled x/y vectors."""
    filled = _nearest_fill(scaled, valid)
    smooth = gaussian_filter(filled, sigma=sigma_px, mode="nearest")
    gy, gx = np.gradient(smooth, pixel_size_m, pixel_size_m)
    magnitude = np.hypot(gx, gy)
    return robust_unit_scale(magnitude, valid), gx.astype(np.float32), gy.astype(np.float32)


def strain_conductivity_features(
    second_invariant: np.ndarray,
    shear_rate: np.ndarray,
    dilatation_rate: np.ndarray,
    conductivity: np.ndarray,
    depth_to_basement: np.ndarray,
    valid: np.ndarray,
    *,
    sigma_px: float = 3.0,
    pixel_size_m: float = 100.0,
) -> np.ndarray:
    """Create the six preregistered H28-3 features in ``FEATURE_NAMES`` order.

    ``sigma_px=3`` is the 300-m competition kernel scale, not a fitted tuning choice.  The
    orientation agreement is unsigned because either polarity of a conductivity boundary can be
    fault-related.  Positive dilatation is used because the physical hypothesis is opening / fluid
    pathway formation; contraction is not silently treated as equivalent evidence.
    """
    arrays = tuple(
        np.asarray(a, dtype=np.float32)
        for a in (second_invariant, shear_rate, dilatation_rate, conductivity, depth_to_basement)
    )
    shape = arrays[0].shape
    mask = np.asarray(valid, dtype=bool)
    if len(shape) != 2 or mask.shape != shape or any(a.shape != shape for a in arrays):
        raise ValueError("all H28-3 inputs and valid mask must be equal-shaped 2-D arrays")
    if not np.isfinite(sigma_px) or sigma_px <= 0 or not np.isfinite(pixel_size_m) or pixel_size_m <= 0:
        raise ValueError("sigma_px and pixel_size_m must be finite positive values")
    mask &= np.logical_and.reduce([np.isfinite(a) & (np.abs(a) < 1e30) for a in arrays])
    if not mask.any():
        raise ValueError("all H28-3 input cells are invalid")

    # These are exactly the five scalar definitions frozen in knowledge/13.
    inv = np.log1p(np.maximum(arrays[0], 0.0))
    shear = np.log1p(np.maximum(arrays[1], 0.0))
    dilation = np.maximum(arrays[2], 0.0)
    cond = np.log1p(np.maximum(arrays[3], 0.0))
    shallow = -np.log1p(np.maximum(arrays[4], 0.0))
    inv_s = robust_unit_scale(inv, mask)
    shear_s = robust_unit_scale(shear, mask)
    dilation_s = robust_unit_scale(dilation, mask)
    cond_s = robust_unit_scale(cond, mask)
    shallow_s = robust_unit_scale(shallow, mask)

    inv_g, inv_gx, inv_gy = _gradient_magnitude_and_vector(
        inv_s, mask, sigma_px=sigma_px, pixel_size_m=pixel_size_m
    )
    shear_g, _, _ = _gradient_magnitude_and_vector(
        shear_s, mask, sigma_px=sigma_px, pixel_size_m=pixel_size_m
    )
    cond_g, cond_gx, cond_gy = _gradient_magnitude_and_vector(
        cond_s, mask, sigma_px=sigma_px, pixel_size_m=pixel_size_m
    )

    inv_mag = np.hypot(inv_gx, inv_gy)
    cond_mag = np.hypot(cond_gx, cond_gy)
    inv_threshold = float(np.percentile(inv_mag[mask], 10.0))
    cond_threshold = float(np.percentile(cond_mag[mask], 10.0))
    strong = mask & (inv_mag >= inv_threshold) & (cond_mag >= cond_threshold)
    alignment = np.zeros(shape, dtype=np.float32)
    denom = np.maximum(inv_mag * cond_mag, np.finfo(np.float32).tiny)
    alignment[strong] = np.clip(
        np.abs((inv_gx[strong] * cond_gx[strong] + inv_gy[strong] * cond_gy[strong]) / denom[strong]),
        0.0,
        1.0,
    )

    strain_core = np.sqrt(inv_s * shear_s, dtype=np.float32) * dilation_s
    corridor = np.minimum(strain_core, cond_s) * np.sqrt(inv_g * cond_g) * alignment
    shallow_corridor = corridor * shallow_s
    stack = np.stack(
        (strain_core, inv_g, shear_g, cond_g, corridor, shallow_corridor), axis=0
    ).astype(np.float32, copy=False)
    stack[:, ~mask] = 0.0
    if not np.isfinite(stack).all() or float(stack.min()) < 0.0 or float(stack.max()) > 1.0:
        raise ValueError("H28-3 transform produced non-finite or out-of-range values")
    return stack
