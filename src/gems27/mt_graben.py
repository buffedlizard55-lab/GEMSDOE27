"""H31-3 label-free asymmetric conductive-clay-cap / basement-margin features.

This module is deliberately restricted to four hash-pinned numerical layers:
``cond_surf``, ``depth_to_base_surf``, ``iso_grav_anom`` and ``geod_dilaterate``.
It neither reads the fault catalogue nor a catalogue-distance derivative.  At a steep
basement-depth gradient it samples conductivity on both local normal sides at 300,
600 and 900 m.  The signed normal points toward *increasing* basement depth, the
hypothesized down-dropped basin side.  This tests an asymmetric clay/brine-cap
prediction, unlike H28-3's previously negative co-located strain--conductivity
intersection.

All returned columns are percentile ranked in [0, 1] only within the supplied
footprint and are in row-major footprint order to match ``prepared/features.npy``.
The implementation is deterministic and the feature parameters are frozen in
``knowledge/28_preregistration_H31-3_mt_graben_2026-10-26.md``.

The named non-fault mimic is conductive playa/evaporite basin fill alongside a
lithologic basement contact.  It can create the same asymmetric conductivity and
gravity pattern without a fault-hosted geothermal conduit.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates

REQUIRED_BANDS = (
    "cond_surf",
    "depth_to_base_surf",
    "iso_grav_anom",
    "geod_dilaterate",
)
TRANSFORM_NAMES = (
    "mt_depth_grad_s3",
    "mt_depth_cond_deep_3",
    "mt_depth_cond_deep_6",
    "mt_depth_cond_deep_9",
    "mt_cond_crossstrike_asym_6",
    "mt_cond_deep_persistence",
    "mt_grav_margin_cond",
    "mt_extension_margin_cond",
)
OFFSETS_PX = (3.0, 6.0, 9.0)  # exactly 300, 600 and 900 m on the competition grid


def _rank01(values: np.ndarray) -> np.ndarray:
    """Average-rank percentile transform with deterministic treatment of ties."""
    v = np.asarray(values, dtype=np.float64)
    _, inverse, counts = np.unique(v, return_inverse=True, return_counts=True)
    end = np.cumsum(counts, dtype=np.float64)
    start = end - counts
    average_zero_based_rank = start + (counts - 1.0) / 2.0
    return (average_zero_based_rank[inverse] / max(v.size - 1, 1)).astype(np.float32)


def _fill(values: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Replace invalid/outside cells only so filters and off-grid sampling are stable."""
    out = np.asarray(values, dtype=np.float32).copy()
    good = np.asarray(footprint, bool) & np.isfinite(out) & (np.abs(out) < 1e30)
    if not good.any():
        raise ValueError("H31-3 input has no finite values in the footprint")
    out[~good] = np.float32(np.median(out[good]))
    return out


def _zpos(values: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Robust non-negative scale; relative rank is applied later to every final column."""
    v = values[footprint]
    median = float(np.median(v))
    iqr = float(np.percentile(v, 75.0) - np.percentile(v, 25.0))
    scale = max(iqr / 1.349, 1e-6)
    out = np.maximum(np.float32(0.0), (values - median) / np.float32(scale)).astype(np.float32)
    out[~footprint] = np.float32(0.0)
    return out


def sample_along_normal(
    field: np.ndarray,
    unit_row: np.ndarray,
    unit_col: np.ndarray,
    offset_px: float,
    *,
    direction: float = 1.0,
) -> np.ndarray:
    """Bilinearly sample ``field`` a signed distance along local row/column normals.

    ``direction=+1`` is the increasing-depth side and ``-1`` the opposite side.
    Boundary behavior is nearest-neighbour because a missing outside-footprint value
    must not manufacture an extreme anomaly at the grid edge.
    """
    if field.ndim != 2 or unit_row.shape != field.shape or unit_col.shape != field.shape:
        raise ValueError("field and normal components must have a common 2-D shape")
    rr, cc = np.indices(field.shape, dtype=np.float32)
    coords = np.array(
        [rr + np.float32(direction * offset_px) * unit_row,
         cc + np.float32(direction * offset_px) * unit_col],
        dtype=np.float32,
    )
    return map_coordinates(field, coords, order=1, mode="nearest", prefilter=False).astype(np.float32)


def build_transforms(grids: dict[str, np.ndarray], footprint: np.ndarray) -> np.ndarray:
    """Build the eight preregistered H31-3 columns in footprint-row order."""
    foot = np.asarray(footprint, dtype=bool)
    if foot.ndim != 2 or not foot.any():
        raise ValueError("footprint must be a non-empty 2-D boolean array")
    missing = [name for name in REQUIRED_BANDS if name not in grids]
    if missing:
        raise ValueError(f"missing H31-3 bands: {missing}")
    for name in REQUIRED_BANDS:
        if np.asarray(grids[name]).shape != foot.shape:
            raise ValueError(f"H31-3 band {name!r} has a grid mismatch")

    depth = _fill(grids["depth_to_base_surf"], foot)
    cond = np.log1p(np.maximum(_fill(grids["cond_surf"], foot), np.float32(0.0))).astype(np.float32)
    grav = _fill(grids["iso_grav_anom"], foot)
    extension = np.maximum(_fill(grids["geod_dilaterate"], foot), np.float32(0.0))

    # A fixed three-pixel smoothing matches the 300-m scoring-kernel scale. The gradient
    # points toward increasing depth: by definition the candidate's down-dropped side.
    depth_s3 = gaussian_filter(depth, sigma=3.0, mode="nearest")
    drow, dcol = np.gradient(depth_s3)
    depth_grad = np.hypot(drow, dcol).astype(np.float32)
    denom = np.maximum(depth_grad, np.float32(1e-8))
    urow, ucol = drow / denom, dcol / denom
    urow[depth_grad <= np.float32(1e-8)] = 0.0
    ucol[depth_grad <= np.float32(1e-8)] = 0.0
    del drow, dcol, denom, depth_s3

    cond_s3 = gaussian_filter(cond, sigma=3.0, mode="nearest")
    c_plus = {
        int(r): sample_along_normal(cond_s3, urow, ucol, r, direction=1.0) for r in OFFSETS_PX
    }
    c_minus_6 = sample_along_normal(cond_s3, urow, ucol, 6.0, direction=-1.0)
    del cond_s3, urow, ucol

    # Positive robust quantities, before footprint percentile-ranking each final column.
    z_depth = _zpos(depth_grad, foot)
    z_c3 = _zpos(c_plus[3], foot)
    z_c6 = _zpos(c_plus[6], foot)
    z_c9 = _zpos(c_plus[9], foot)
    z_asym6 = _zpos(np.maximum(c_plus[6] - c_minus_6, 0.0), foot)
    z_persist = _zpos(np.minimum(np.minimum(c_plus[3], c_plus[6]), c_plus[9]), foot)
    grav_grad = np.hypot(*np.gradient(gaussian_filter(grav, sigma=3.0, mode="nearest"))).astype(np.float32)
    z_grav = _zpos(grav_grad, foot)
    z_extension = _zpos(extension, foot)
    del depth, cond, grav, extension, c_plus, c_minus_6, grav_grad

    raw = (
        depth_grad,
        z_depth * z_c3,
        z_depth * z_c6,
        z_depth * z_c9,
        z_depth * z_asym6,
        z_depth * z_persist,
        z_depth * z_grav * z_c6,
        z_depth * z_extension * z_c6,
    )
    n = int(foot.sum())
    out = np.empty((n, len(TRANSFORM_NAMES)), dtype=np.float32)
    for col, values in enumerate(raw):
        vals = np.asarray(values[foot], dtype=np.float32)
        if not np.isfinite(vals).all():
            raise ValueError(f"non-finite H31-3 values in {TRANSFORM_NAMES[col]}")
        out[:, col] = _rank01(vals)
    if not np.isfinite(out).all() or float(out.min()) < 0.0 or float(out.max()) > 1.0:
        raise ValueError("H31-3 transforms must be finite and bounded in [0,1]")
    return out
