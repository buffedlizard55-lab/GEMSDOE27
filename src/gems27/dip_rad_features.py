"""Lane L-DCONFIRM new label-free transforms (preregistered in knowledge/15 §3).

Eight deterministic transforms of hash-pinned rasters only (prepared 32-band stack +
GeoDAWN radiometric/extension u8 grids). No labels, no catalogue distance, no scores are
read, so they are safe to compute once on the full grid and reuse inside spatial folds
(fold discipline lives in the detector). Outputs are percentile-ranked within the
footprint to [0, 1] float32, row-major footprint order, matching
``gems27.subsurface_features`` conventions (shared ``_rank01`` / ``_grad_mag`` / ``_fill``).

Physics: (1) dip-offset doublets — a dipping fault's potential-field / basement-step edge
is laterally offset 200–600 m from its surface scarp, so an edge with a scarp ridge in its
2–6 px annulus (or vice-versa) is one structure seen in two physics; the edge continues
under alluvium where the scarp dies and the surface-rupture catalogue stops.
(2) Radiometric alteration fronts — gradient-magnitude *fronts* of ratio grids mark
hydrothermal alteration boundaries along permeable structures (ratio *values* were tried
in Addendum D and refuted at +0.0007 PR-AUC; front geometry was not).
(3) Scarp polarity pairs — a real scarp pairs a convex break (lappos/upface) with the
concave break (lapneg/downface) 100–300 m away; amplitude-only detectors cannot see the
sign pattern once a buried scarp is subdued.
Named non-fault mimics: basin-margin lithologic contacts, radiometric provenance /
levelling seams, terrace risers and channel banks.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import maximum_filter

from .subsurface_features import _fill, _grad_mag, _rank01

NEW_TRANSFORM_NAMES = [
    "dip_edge_x_scarpann2_6",
    "dip_scarp_x_edgeann2_6",
    "dip_depthstep_x_scarpann2_6",
    "rad_front_ThK_s2",
    "rad_front_UK_s2",
    "rad_front_K_s2",
    "pol_lap_pair1_3",
    "pol_face_pair1_3",
]

# Prepared-stack bands read here (subset of the 32; everything else comes via arm D).
PREPARED_BANDS = [
    "rtp", "depth_to_base_surf",
    "lidar_step_max", "lidar_lappos_max", "lidar_lapneg_max",
    "lidar_upface_max", "lidar_downface_max",
]
# Radiometric grids: (file key, band description in the pinned u8 rasters).
RAD_GRIDS = ["ext_ThK", "ext_UK", "rad_K"]


def annulus_footprint(r_lo: float, r_hi: float) -> np.ndarray:
    """Boolean footprint of offsets with r_lo <= hypot(dy, dx) <= r_hi (centre excluded)."""
    r = int(np.ceil(r_hi))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    d = np.hypot(yy, xx)
    return (d >= r_lo) & (d <= r_hi)


def _annulus_max(grid_rank: np.ndarray, r_lo: float, r_hi: float) -> np.ndarray:
    return maximum_filter(grid_rank, footprint=annulus_footprint(r_lo, r_hi), mode="nearest")


def _to_rank_grid(vals_grid: np.ndarray, foot: np.ndarray) -> np.ndarray:
    """Percentile-rank a full-grid array over footprint cells; 0 outside the footprint."""
    out = np.zeros(vals_grid.shape, dtype=np.float32)
    v = vals_grid[foot].astype(np.float64)
    v = np.where(np.isfinite(v), v, np.nanmedian(v[np.isfinite(v)]))
    out[foot] = _rank01(v)
    return out


def _polarity_pair(a_rank: np.ndarray, b_rank: np.ndarray) -> np.ndarray:
    """Symmetric signed-break adjacency at 1–3 px: high where either break borders the other."""
    return np.maximum(
        np.minimum(a_rank, _annulus_max(b_rank, 1.0, 3.0)),
        np.minimum(b_rank, _annulus_max(a_rank, 1.0, 3.0)),
    ).astype(np.float32)


def build_new_transforms(
    prepared_grids: dict[str, np.ndarray],
    rad_grids: dict[str, np.ndarray],
    foot: np.ndarray,
) -> np.ndarray:
    """Return (n_footprint, 8) float32 ranks in ``NEW_TRANSFORM_NAMES`` order.

    ``prepared_grids`` holds full-grid arrays for ``PREPARED_BANDS`` (NaN allowed outside
    the footprint / in the LiDAR-invalid area; filled with the footprint mean for
    filtering only, as in ``subsurface_features._fill``). ``rad_grids`` holds full-grid
    ``RAD_GRIDS`` arrays from the pinned u8 radiometric rasters.
    """
    g = {k: _fill(prepared_grids[k], foot) for k in PREPARED_BANDS}
    rad = {k: _fill(rad_grids[k], foot) for k in RAD_GRIDS}

    edge_rtp_r = _to_rank_grid(_grad_mag(g["rtp"], 2.0), foot)
    scarp_r = _to_rank_grid(g["lidar_step_max"], foot)
    depthstep_r = _to_rank_grid(_grad_mag(g["depth_to_base_surf"], 3.0), foot)
    scarp_ann = _annulus_max(scarp_r, 2.0, 6.0)
    edge_ann = _annulus_max(edge_rtp_r, 2.0, 6.0)

    lappos_r = _to_rank_grid(g["lidar_lappos_max"], foot)
    lapneg_r = _to_rank_grid(g["lidar_lapneg_max"], foot)
    upface_r = _to_rank_grid(g["lidar_upface_max"], foot)
    downface_r = _to_rank_grid(g["lidar_downface_max"], foot)

    raw = {
        "dip_edge_x_scarpann2_6": (edge_rtp_r * scarp_ann).astype(np.float32),
        "dip_scarp_x_edgeann2_6": (scarp_r * edge_ann).astype(np.float32),
        "dip_depthstep_x_scarpann2_6": (depthstep_r * scarp_ann).astype(np.float32),
        "rad_front_ThK_s2": _grad_mag(rad["ext_ThK"], 2.0),
        "rad_front_UK_s2": _grad_mag(rad["ext_UK"], 2.0),
        "rad_front_K_s2": _grad_mag(rad["rad_K"], 2.0),
        "pol_lap_pair1_3": _polarity_pair(lappos_r, lapneg_r),
        "pol_face_pair1_3": _polarity_pair(upface_r, downface_r),
    }
    assert list(raw) == NEW_TRANSFORM_NAMES, "transform order drift"
    cols = []
    for name in NEW_TRANSFORM_NAMES:
        vals = raw[name][foot]
        vals = np.where(np.isfinite(vals), vals, np.nanmedian(vals[np.isfinite(vals)]))
        cols.append(_rank01(vals))
    out = np.stack(cols, axis=1).astype(np.float32)
    if not np.isfinite(out).all() or out.min() < 0.0 or out.max() > 1.0:
        raise ValueError("new transforms must be finite ranks in [0, 1]")
    return out
