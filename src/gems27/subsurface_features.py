"""Lane L-2026-10-25 subsurface-physics feature transforms (label-free, fold-safe).

Every transform here is a deterministic function of the hash-pinned GeoDAWN raster bands only:
no labels, no catalogue distance, no lidar/topography band is read. They are therefore safe to
compute once on the full grid and reuse inside spatial folds (the fold discipline lives in the
detector, which never trains on the quadrant it predicts). Outputs are percentile-ranked within
the footprint to [0, 1] float32, in row-major footprint order to match `prepared/features.npy`.

Physics, briefly: a fault buried under alluvium or too old for the Quaternary surface-rupture
catalogue still juxtaposes units of contrasting magnetic susceptibility / density (potential-field
edges, tilt ridges), steps the basement surface, localises geodetic strain, and channels fluids
(conductive alteration). Dipping geometry laterally offsets these edges from any surface trace,
which is the mechanism expected to decorrelate this lane's dots from the H19-5 family.
Non-fault mimics: lithologic contacts, survey seams, remanent magnetisation, clay caps,
basin-margin conductivity — named here so the run card can cite them.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter

# Prepared-stack band names this lane is allowed to touch (subsurface regime only).
SUBSURFACE_BANDS = [
    "mag_anom", "rtp", "tmi_hg", "tmi_vg", "tmi",
    "iso_grav_anom", "iso_grav_anom_hg", "iso_grav_anom_vg", "iso_grav_anom_slope",
    "geod_2ndinv", "geod_shearrate", "geod_dilaterate",
    "cond_surf", "depth_to_base_surf", "deq_n100a15", "ieq_n100a15",
]
# Explicitly excluded (surface-scarp regime = the H19-5 family's physics):
EXCLUDED_BANDS = [
    "det_elev", "det_elev_slope", "det_local_relief", "det_gradient",
    "lidar_ex_max", "lidar_ex_mean", "lidar_step_max", "lidar_lapneg_max", "lidar_lappos_max",
    "lidar_downface_max", "lidar_upface_max", "lidar_cross_max", "lidar_relief",
    "lidar_coh100", "lidar_cos2strike", "lidar_sin2strike",
]

TRANSFORM_NAMES = [
    "sub_gm_rtp_s2", "sub_gm_rtp_s5", "sub_tiltabs_rtp", "sub_analytic_rtp",
    "sub_gm_grav_s2", "sub_gm_grav_s5", "sub_crossfield_coherence",
    "sub_gm_cond_s3", "sub_gm_depth_s3", "sub_gm_depth_s8",
    "sub_gm_dilate_s3", "sub_gm_2ndinv_s3", "sub_strain_x_cond",
    "sub_seismic_fabric_ieq", "sub_seismic_fabric_deq",
]


def _fill(grid_arr: np.ndarray, foot: np.ndarray) -> np.ndarray:
    a = grid_arr.astype(np.float32).copy()
    bad = ~foot | ~np.isfinite(a)
    if bad.any():
        a[bad] = float(np.nanmean(a[foot & np.isfinite(a)])) if (foot & np.isfinite(a)).any() else 0.0
    return a


def _grad_mag(a: np.ndarray, sigma: float) -> np.ndarray:
    s = gaussian_filter(a, sigma=sigma) if sigma > 0 else a
    gy, gx = np.gradient(s)
    return np.hypot(gy, gx).astype(np.float32)


def _structure_coherence(a: np.ndarray, sigma: float) -> np.ndarray:
    gy, gx = np.gradient(gaussian_filter(a, sigma=1.0))
    jxx = gaussian_filter(gx * gx, sigma=sigma)
    jyy = gaussian_filter(gy * gy, sigma=sigma)
    jxy = gaussian_filter(gx * gy, sigma=sigma)
    tr = jxx + jyy
    disc = np.sqrt(np.maximum((jxx - jyy) ** 2 + 4.0 * jxy**2, 0.0))
    return (disc / (tr + 1e-12)).astype(np.float32)  # (l1-l2)/(l1+l2) in [0,1]


def _rank01(vals_foot: np.ndarray) -> np.ndarray:
    """Percentile rank in [0,1] with average ranks for ties (vectorised)."""
    v = np.asarray(vals_foot, dtype=np.float64)
    _, inv, counts = np.unique(v, return_inverse=True, return_counts=True)
    ends = np.cumsum(counts).astype(np.float64)          # 1-based end rank of each tie group
    starts = ends - counts                               # 0-based start rank
    avg = starts + (counts - 1) / 2.0                    # mean 0-based rank within group
    return (avg[inv] / max(len(v) - 1, 1)).astype(np.float32)


def build_transforms(grids: dict[str, np.ndarray], foot: np.ndarray) -> np.ndarray:
    """grids: full-grid arrays for SUBSURFACE_BANDS. Returns (n_footprint, 15) float32 ranks."""
    n_foot = int(foot.sum())
    out = np.empty((n_foot, len(TRANSFORM_NAMES)), dtype=np.float32)

    def _put(col_idx: int, arr2d: np.ndarray) -> None:
        vals = arr2d[foot]
        vals = np.where(np.isfinite(vals), vals, np.nanmedian(vals[np.isfinite(vals)]))
        out[:, col_idx] = _rank01(vals)

    rtp = _fill(grids["rtp"], foot)
    grav = _fill(grids["iso_grav_anom"], foot)
    gm_rtp2 = _grad_mag(rtp, 2.0)
    _put(0, gm_rtp2)
    _put(1, _grad_mag(rtp, 5.0))

    tmi_vg = _fill(grids["tmi_vg"], foot)
    tmi_hg = _fill(grids["tmi_hg"], foot)
    tilt = np.abs(np.arctan2(tmi_vg, np.hypot(tmi_hg, 1e-12))).astype(np.float32)
    _put(2, np.pi / 2 - tilt)
    del tilt, tmi_hg
    analytic = np.sqrt(gm_rtp2**2 + gaussian_filter(tmi_vg, 2.0) ** 2).astype(np.float32)
    _put(3, analytic)
    del analytic, tmi_vg

    gm_grav2 = _grad_mag(grav, 2.0)
    _put(4, gm_grav2)
    _put(5, _grad_mag(grav, 5.0))

    ry, rx = np.gradient(gaussian_filter(rtp, 3.0))
    vy, vx = np.gradient(gaussian_filter(grav, 3.0))
    del rtp, grav
    cos_d = np.abs((rx * vx + ry * vy) / (np.hypot(rx, ry) * np.hypot(vx, vy) + 1e-12))
    del ry, rx, vy, vx
    _put(6, (cos_d * np.minimum(gm_rtp2, gm_grav2)).astype(np.float32))
    del cos_d, gm_rtp2, gm_grav2

    gm_cond3 = _grad_mag(_fill(grids["cond_surf"], foot), 3.0)
    _put(7, gm_cond3)
    dtb = _fill(grids["depth_to_base_surf"], foot)
    _put(8, _grad_mag(dtb, 3.0))
    _put(9, _grad_mag(dtb, 8.0))
    del dtb

    gm_dil3 = _grad_mag(_fill(grids["geod_dilaterate"], foot), 3.0)
    _put(10, gm_dil3)
    _put(11, _grad_mag(_fill(grids["geod_2ndinv"], foot), 3.0))
    _put(12, np.sqrt(np.maximum(gm_dil3, 0) * np.maximum(gm_cond3, 0)).astype(np.float32))
    del gm_dil3, gm_cond3

    _put(13, _structure_coherence(_fill(grids["ieq_n100a15"], foot), 5.0))
    _put(14, _structure_coherence(_fill(grids["deq_n100a15"], foot), 5.0))
    return out


def priority_poisson_disk(prob: np.ndarray, candidates: np.ndarray, min_dist: float,
                          budget: int, rng: np.random.Generator | None = None) -> np.ndarray:
    """Greedy dot placement in descending-probability order with >= min_dist spacing.

    Differs from `thinning.dot_thin` (component-BFS order): the highest-probability dots win,
    so placement follows the detector surface rather than raster scan order. With `rng` given,
    order is randomised instead (the matched-budget null control).
    """
    cand = np.asarray(candidates, bool)
    ys, xs = np.nonzero(cand)
    if len(ys) == 0 or budget <= 0:
        return np.zeros_like(cand)
    score = prob[ys, xs].astype(np.float64)
    order = rng.permutation(len(ys)) if rng is not None else np.argsort(-score, kind="stable")
    H, W = cand.shape
    r = int(np.ceil(min_dist))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    disc = (yy * yy + xx * xx) < (min_dist * min_dist)
    dys, dxs = yy[disc], xx[disc]
    blocked = np.zeros((H, W), bool)
    out = np.zeros((H, W), bool)
    kept = 0
    for idx in order:
        y, x = int(ys[idx]), int(xs[idx])
        if blocked[y, x]:
            continue
        out[y, x] = True
        kept += 1
        if kept >= budget:
            break
        ny, nx = y + dys, x + dxs
        ok = (ny >= 0) & (nx >= 0) & (ny < H) & (nx < W)
        blocked[ny[ok], nx[ok]] = True
    return out
