"""Up-Dip Basement-Step Advection, Cross-Field Strike Bridge, Listric Rollover,
and Quality-Filtered Hydrothermal Upflow features (Hypothesis H30-1).

All transforms are strictly label-free:
  * Never inspect ``labels.tif``, ``qfaults_v2_in_footprint.json``,
    ``derived_sgmc_faults_100m_u8.tif``, or ``dist_known_fault_px``.
  * Operate only on the hash-pinned 32-band prepared stack (``prepared/features.npy``)
    and the quality-screened thermal/geothermometer columns (``temp_c``,
    ``geothermquartz_c``, ``geothermchalc_c``, ``geothermcat_c``) of
    ``gdr_wellspring_in_footprint.csv``.
  * Every output feature is finite, rank-scaled to [0, 1] inside the valid
    footprint, and 0.0 outside the footprint.
"""

from __future__ import annotations

import csv
import gc
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter

from . import paths

# Column indices in data_cache/prepared/features.npy (schema 2)
IDX_RTP = 1
IDX_SHEAR = 5
IDX_DILAT = 6
IDX_ELEV = 10
IDX_GRAV = 11
IDX_BASE = 13
IDX_COND = 15

UPDIP_RELAY_FEATURE_NAMES: tuple[str, ...] = (
    "updip_rtp_edge_advected",
    "updip_grav_edge_advected",
    "updip_concordance_x_bstep",
    "crossfield_strike_bridge_s6",
    "listric_rollover_curv_x_bstep",
    "oblique_transfer_strike_rot",
    "hydrothermal_temp_upflow_x_bstep",
    "hydrothermal_geotherm_upflow_grad",
)


def _unflatten(col: np.ndarray, foot: np.ndarray, fill: float = 0.0) -> np.ndarray:
    out = np.full(foot.shape, fill, dtype=np.float32)
    out[foot] = np.nan_to_num(col, nan=fill, posinf=fill, neginf=fill).astype(np.float32)
    return out


def _nearest_fill(grid: np.ndarray, foot: np.ndarray) -> np.ndarray:
    """Fill outside-footprint cells from the nearest valid footprint cell."""
    if not np.any(foot):
        return np.zeros_like(grid, dtype=np.float32)
    if np.all(foot):
        return grid.astype(np.float32, copy=True)
    idx = distance_transform_edt(~foot, return_distances=False, return_indices=True)
    return grid[tuple(idx)].astype(np.float32, copy=False)


def _rank01(vals_1d: np.ndarray) -> np.ndarray:
    v = np.nan_to_num(vals_1d, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
    n = v.size
    if n <= 1 or float(v.max()) == float(v.min()):
        return np.zeros_like(v, dtype=np.float32)
    order = np.argsort(v, kind="mergesort")
    out = np.empty(n, dtype=np.float32)
    out[order] = np.linspace(0.0, 1.0, n, dtype=np.float32)
    return out


def _rank01_grid(grid: np.ndarray, foot: np.ndarray) -> np.ndarray:
    out = np.zeros(foot.shape, dtype=np.float32)
    out[foot] = _rank01(grid[foot])
    return out


def compute_downdip_basement_field(
    base_col: np.ndarray,
    foot: np.ndarray,
    *,
    sigma_vec_px: float = 4.0,
    sigma_step_px: float = 3.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return (uy, ux, bstep_rank_grid, depth_rank_grid) from depth_to_base_surf.

    Since ``depth_to_base_surf`` increases with basement depth into the hanging-wall
    basin, its spatial gradient ``(gy, gx)`` points down-dip into the basin, and
    sampling a deep field at ``(y + delta*uy, x + delta*ux)`` advects the hanging-wall
    subsurface anomaly *up-dip* to its surface rupture projection ``(y, x)``.
    """
    z_raw = _nearest_fill(_unflatten(base_col, foot), foot)
    z_smooth = gaussian_filter(z_raw, sigma=float(sigma_vec_px), mode="nearest")
    gy, gx = np.gradient(z_smooth)
    mag = np.hypot(gy, gx) + np.float32(1e-6)
    uy = (gy / mag).astype(np.float32)
    ux = (gx / mag).astype(np.float32)

    z_step = gaussian_filter(z_raw, sigma=float(sigma_step_px), mode="nearest")
    sy, sx = np.gradient(z_step)
    bstep_rank = _rank01_grid(np.hypot(sy, sx), foot)
    depth_rank = _rank01_grid(z_smooth, foot)
    return uy, ux, bstep_rank, depth_rank


def _load_quality_wellspring_grids(
    foot: np.ndarray,
    wellspring_csv: Path | None,
) -> tuple[np.ndarray, np.ndarray]:
    """Build station-max quality-filtered thermal and chemical geothermometer grids.

    Explicitly ignores ``dist_known_fault_px`` to preserve strict label independence.
    Sentinel/invalid temperatures (<= 0 C or > 350 C) are rejected.
    """
    H, W = foot.shape
    temp_excess = np.zeros((H, W), dtype=np.float32)
    chem_excess = np.zeros((H, W), dtype=np.float32)

    if wellspring_csv is None or not Path(wellspring_csv).exists() or (H, W) != (3730, 3292):
        return temp_excess, chem_excess

    with Path(wellspring_csv).open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                r = int(float(row["row"]))
                c = int(float(row["col"]))
            except (KeyError, ValueError, TypeError):
                continue
            if not (0 <= r < H and 0 <= c < W) or not foot[r, c]:
                continue

            # Measured well/spring temperature excess above 20 C ambient
            try:
                tc = float(row.get("temp_c", "") or "nan")
            except ValueError:
                tc = float("nan")
            if np.isfinite(tc) and 0.0 < tc <= 350.0:
                ex = float(np.clip(tc - 20.0, 0.0, 200.0))
                if ex > temp_excess[r, c]:
                    temp_excess[r, c] = ex

            # Chemical geothermometer excess above 50 C (quartz, chalcedony, cation)
            best_chem = 0.0
            for k in ("geothermquartz_c", "geothermchalc_c", "geothermcat_c"):
                try:
                    gv = float(row.get(k, "") or "nan")
                except ValueError:
                    gv = float("nan")
                if np.isfinite(gv) and 25.0 <= gv <= 350.0:
                    best_chem = max(best_chem, float(np.clip(gv - 50.0, 0.0, 250.0)))
            if best_chem > chem_excess[r, c]:
                chem_excess[r, c] = best_chem

    return temp_excess, chem_excess


def build_updip_relay_features(
    X_foot: np.ndarray,
    foot: np.ndarray,
    *,
    wellspring_csv: Path | None = paths.WELLSPRING,
    shift_min_px: float = 3.0,
    shift_max_px: float = 5.5,
) -> tuple[np.ndarray, list[str]]:
    """Compute the 8 preregistered H30-1 features on footprint pixels.

    Returns ``(F, names)`` where ``F`` has shape ``(N_foot, 8)`` in ``float32``
    with all values finite and in ``[0, 1]``.
    """
    foot = np.asarray(foot, dtype=bool)
    n_foot = int(foot.sum())
    if X_foot.shape[0] != n_foot or X_foot.shape[1] < 18:
        raise ValueError(f"X_foot shape {X_foot.shape} incompatible with footprint size {n_foot}")

    H, W = foot.shape
    F = np.empty((n_foot, 8), dtype=np.float32)
    yy, xx = np.indices((H, W), dtype=np.float32)

    uy, ux, bstep_rank, depth_rank = compute_downdip_basement_field(
        X_foot[:, IDX_BASE], foot, sigma_vec_px=4.0, sigma_step_px=3.0
    )
    bstep_1d = bstep_rank[foot].copy()
    delta_px = np.clip(
        float(shift_min_px) + (float(shift_max_px) - float(shift_min_px)) * depth_rank,
        float(shift_min_px),
        float(shift_max_px),
    )
    del bstep_rank, depth_rank
    y_src = np.clip(np.rint(yy + delta_px * uy).astype(np.int32), 0, H - 1)
    x_src = np.clip(np.rint(xx + delta_px * ux).astype(np.int32), 0, W - 1)
    del delta_px

    # 1-2. Up-dip advected magnetic (rtp) and gravity (iso_grav_anom) edges
    rtp_fill = _nearest_fill(_unflatten(X_foot[:, IDX_RTP], foot), foot)
    grav_fill = _nearest_fill(_unflatten(X_foot[:, IDX_GRAV], foot), foot)

    rtp_s25 = gaussian_filter(rtp_fill, sigma=2.5, mode="nearest")
    del rtp_fill
    r_gy, r_gx = np.gradient(rtp_s25)
    del rtp_s25
    rtp_edge = np.hypot(r_gy, r_gx)
    F[:, 0] = _rank01(rtp_edge[y_src, x_src][foot])

    grav_s25 = gaussian_filter(grav_fill, sigma=2.5, mode="nearest")
    g_gy, g_gx = np.gradient(grav_s25)
    del grav_s25, g_gy, g_gx
    grav_edge = np.hypot(*np.gradient(gaussian_filter(grav_fill, sigma=2.5, mode="nearest")))
    F[:, 1] = _rank01(grav_edge[y_src, x_src][foot])
    del y_src, x_src

    # 3. Up-dip cross-field concordance anchored to local basement step
    F[:, 2] = _rank01(np.cbrt(np.maximum(F[:, 0] * F[:, 1] * bstep_1d, 0.0)))

    # 4. Along-strike cross-field interruption bridge (+/- 6 px = +/- 600 m along strike)
    edge_comb = np.sqrt(_rank01_grid(rtp_edge, foot) * _rank01_grid(grav_edge, foot))
    del rtp_edge, grav_edge
    grav_s6 = gaussian_filter(grav_fill, sigma=6.0, mode="nearest")
    del grav_fill
    g6_y, g6_x = np.gradient(grav_s6)
    del grav_s6
    g6_mag = np.hypot(g6_y, g6_x) + np.float32(1e-6)
    sy = (-g6_x / g6_mag).astype(np.float32)
    sx = (g6_y / g6_mag).astype(np.float32)
    del g6_y, g6_x, g6_mag
    step_s = 6.0
    yp = np.clip(np.rint(yy + step_s * sy).astype(np.int32), 0, H - 1)
    xp = np.clip(np.rint(xx + step_s * sx).astype(np.int32), 0, W - 1)
    ym = np.clip(np.rint(yy - step_s * sy).astype(np.int32), 0, H - 1)
    xm = np.clip(np.rint(xx - step_s * sx).astype(np.int32), 0, W - 1)
    del sy, sx, yy, xx
    F[:, 3] = _rank01(np.sqrt(np.maximum(edge_comb[yp, xp][foot] * edge_comb[ym, xm][foot], 0.0)))
    del edge_comb, yp, xp, ym, xm
    gc.collect()

    # 5. Listric hanging-wall rollover curvature (300 m vs 900 m along down-dip vector) x basement step
    elev_fill = _nearest_fill(_unflatten(X_foot[:, IDX_ELEV], foot), foot)

    def _profile_curv(
        arr: np.ndarray, dy: np.ndarray, dx: np.ndarray, sigma: float
    ) -> np.ndarray:
        es = gaussian_filter(arr, sigma=sigma, mode="nearest")
        ey, ex = np.gradient(es)
        del es
        eyy, eyx = np.gradient(ey)
        del ey
        exy, exx = np.gradient(ex)
        del ex
        return dy * dy * eyy + 2.0 * dx * dy * 0.5 * (eyx + exy) + dx * dx * exx

    curv_diff = np.abs(
        _profile_curv(elev_fill, uy, ux, 3.0) - _profile_curv(elev_fill, uy, ux, 9.0)
    )
    del elev_fill, uy, ux
    F[:, 4] = _rank01(curv_diff[foot] * bstep_1d)
    del curv_diff
    gc.collect()

    # 6. Oblique transfer-zone orientation-rotation boundary weighted by geodetic shear rate
    rmag = np.hypot(r_gy, r_gx) + np.float32(1e-6)
    theta_m = np.arctan2(r_gy / rmag, r_gx / rmag)
    del r_gy, r_gx, rmag
    c2m = gaussian_filter(np.cos(2.0 * theta_m).astype(np.float32), sigma=3.0, mode="nearest")
    s2m = gaussian_filter(np.sin(2.0 * theta_m).astype(np.float32), sigma=3.0, mode="nearest")
    del theta_m
    c2_y, c2_x = np.gradient(c2m)
    s2_y, s2_x = np.gradient(s2m)
    del c2m, s2m
    rot_mag = np.sqrt(c2_y * c2_y + c2_x * c2_x + s2_y * s2_y + s2_x * s2_x)
    del c2_y, c2_x, s2_y, s2_x
    shear_1d = _rank01(X_foot[:, IDX_SHEAR])
    F[:, 5] = _rank01(rot_mag[foot] * (0.25 + 0.75 * shear_1d))
    del rot_mag, shear_1d
    gc.collect()

    # 7-8. Quality-filtered hydrothermal temperature & chemical geothermometer upflow corridors
    temp_grid, chem_grid = _load_quality_wellspring_grids(foot, wellspring_csv)
    cond_1d = _rank01(X_foot[:, IDX_COND])
    dilat_1d = _rank01(X_foot[:, IDX_DILAT])

    if float(temp_grid.max()) > 0.0:
        t_plume = 0.6 * gaussian_filter(temp_grid, sigma=8.0, mode="nearest") + 0.4 * gaussian_filter(
            temp_grid, sigma=20.0, mode="nearest"
        )
        t_plume_1d = _rank01(t_plume[foot])
        del t_plume
    else:
        t_plume_1d = np.sqrt(cond_1d * dilat_1d)
    del temp_grid
    F[:, 6] = _rank01(t_plume_1d * np.sqrt(np.maximum(bstep_1d * (0.2 + 0.8 * cond_1d), 0.0)))
    del t_plume_1d

    if float(chem_grid.max()) > 0.0:
        c_s10 = gaussian_filter(chem_grid, sigma=10.0, mode="nearest")
        cy, cx = np.gradient(c_s10)
        c_comb = 0.5 * _rank01(c_s10[foot]) + 0.5 * _rank01(np.hypot(cy, cx)[foot])
        del c_s10, cy, cx
    else:
        c_comb = 0.5 * cond_1d + 0.5 * dilat_1d
    del chem_grid, cond_1d, dilat_1d
    F[:, 7] = _rank01(c_comb * (0.25 + 0.75 * bstep_1d))
    del c_comb, bstep_1d
    gc.collect()

    F = np.clip(np.nan_to_num(F, nan=0.0, posinf=1.0, neginf=0.0), 0.0, 1.0)
    return F, list(UPDIP_RELAY_FEATURE_NAMES)


def advect_subsurface_probability_updip(
    prob_sub: np.ndarray,
    prob_hybrid: np.ndarray,
    X_foot: np.ndarray,
    foot: np.ndarray,
    *,
    shift_min_px: float = 3.8,
    shift_max_px: float = 5.5,
) -> np.ndarray:
    """Project a subsurface fault probability surface up-dip along -grad(Z_base).

    Weights toward sub-alluvial corridors where shallow scarp response is subdued,
    yielding a continuous [0, 1] surface on the footprint.
    """
    foot = np.asarray(foot, dtype=bool)
    H, W = foot.shape
    yy, xx = np.indices((H, W), dtype=np.float32)

    uy, ux, bstep_rank, depth_rank = compute_downdip_basement_field(
        X_foot[:, IDX_BASE], foot, sigma_vec_px=4.0, sigma_step_px=3.0
    )
    delta_px = np.clip(
        float(shift_min_px) + (float(shift_max_px) - float(shift_min_px)) * depth_rank,
        float(shift_min_px),
        float(shift_max_px),
    )
    y_src = np.clip(np.rint(yy + delta_px * uy).astype(np.int32), 0, H - 1)
    x_src = np.clip(np.rint(xx + delta_px * ux).astype(np.int32), 0, W - 1)

    sub_fill = _nearest_fill(np.where(foot, prob_sub, 0.0).astype(np.float32), foot)
    sub_smooth = gaussian_filter(sub_fill, sigma=1.2, mode="nearest")
    advected = sub_smooth[y_src, x_src]

    hyb_rank = _rank01_grid(np.where(foot, prob_hybrid, 0.0).astype(np.float32), foot)
    cover_weight = np.sqrt(np.clip(1.0 - 0.55 * hyb_rank, 0.20, 1.0)) * (0.40 + 0.60 * bstep_rank)

    out = np.zeros((H, W), dtype=np.float32)
    out[foot] = _rank01((advected * cover_weight)[foot])
    return np.clip(out, 0.0, 1.0)
