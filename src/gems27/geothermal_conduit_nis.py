"""Hypothesis H31-1 (Lane L-S10-2026-10-26):
Dual-Regime Corroborated Geothermal Conduit & Walker Lane Transtensional Ridge Synthesis
(DRCG-WL) with Axial-Crest-Sharpened min_sep_px = 2.8 300 m CELF Allocation.

Addresses the four live-score deficits measured in Session-7 H29-S (0.2190 OWNER-REPORTED):
1. min_sep_px = 2.8 axial-crest 300 m CELF cover (eliminating min_sep=2.0 2D blob crowding
   and restoring -11.0% lost footprint coverage c: 0.0527 -> ~0.0595).
2. Dual-regime cross-fitting: LiDAR-free Subsurface/Seismogenic/Hydrothermal Expert M_Sub
   (60 pure non-LiDAR columns across 100% of footprint) corroborates M_Full inside 1 m LiDAR
   coverage and is monotone-quantile-calibrated onto the combined distribution across the
   24.63% LiDAR coverage gap (fixing the 18.3% LiDAR-gap starvation).
3. Multi-scale Walker Lane seismic-fabric structure-tensor coherence (ieq_n100a15, deq_n100a15)
   coupled with dextral/transtensional geod_shearrate x geod_dilaterate and Blakely-Simpson
   Hessian potential-field contact crests (-lambda_min(H(||grad F||))).
4. Algebraic contour-obliquity shoreline deconfounding sin^2(theta_scarp - theta_contour)
   separating cross-contour piedmont scarps from contour-parallel Pleistocene Lake Lahontan
   wave-cut benches, plus Stage-2 local halo subtraction (p_s1 - G_8(p_s1)).

Strictly zero access to existing_faults.tif, labels.tif, dist_known_fault_px, or band 6 ('tc')
anywhere inside feature construction.
"""
from __future__ import annotations

import gc
import os
from itertools import combinations
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, gaussian_filter, gaussian_gradient_magnitude
from sklearn.ensemble import HistGradientBoostingClassifier

from gems27 import coverage_thin, holdout, metric, paths
from gems27 import hydrothermal_piedmont as h29

H31_FEATURE_NAMES: tuple[str, ...] = (
    # 9 non-LiDAR subsurface / Walker Lane / hydrothermal conduit features (indices 0..8)
    "h31_blakely_rtp_crest_s15",
    "h31_blakely_grav_crest_s20",
    "h31_joint_blakely_crest",
    "h31_wl_ieq_aniso_s2",
    "h31_wl_deq_aniso_s4",
    "h31_wl_transtension_shear_x_dil",
    "h31_wl_seis_x_shear",
    "h31_dem_breakline_crest",
    "h31_hydro_conduit_corrob",
    # 3 LiDAR contour-obliquity shoreline deconfounding features (indices 9..11)
    "h31_contour_obliquity_sin2",
    "h31_basin_oblique_scarp",
    "h31_lahontan_mimic_score",
)

H31_S2_FEATURE_NAMES: tuple[str, ...] = (
    "s2_p_s1",
    "s2_p_sub",
    "s2_frangi_s10",
    "s2_frangi_s20",
    "s2_frangi_s35",
    "s2_line_max_500m",
    "s2_axial_crest",
    "s2_local_contrast_s80",
)

# Verified non-LiDAR column indices in prepared/features.npy (32 cols) and h29_features.npy (20 cols)
BASE_NON_LIDAR_IDX: tuple[int, ...] = tuple(list(range(18)) + [30, 31])
H29_NON_LIDAR_IDX: tuple[int, ...] = (0, 1, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19)
H31_NON_LIDAR_IDX: tuple[int, ...] = tuple(range(9))

BUFFER_PX: float = 6.0
LIDAR_GAP_QUANTILE_SCALE: float = 0.94
CELF_GAMMA: float = 1.35
CELF_MIN_SEP_PX: float = 2.8


def blakely_ridge_crest(field: np.ndarray, sigma_grad: float, sigma_curv: float = 1.2) -> np.ndarray:
    """Blakely-Simpson (1986) potential-field contact crest via -lambda_min(Hessian(||grad F||)).

    Concentrates maximum horizontal gradient onto sharp 1-pixel structural contact spines
    rather than broad 400-800 m Gaussian gradient shoulders.
    """
    gmag = gaussian_gradient_magnitude(field.astype(np.float32, copy=False), sigma=sigma_grad, mode="nearest")
    s2 = np.float32(sigma_curv ** 2)
    hyy = gaussian_filter(gmag, sigma=sigma_curv, order=(2, 0), mode="nearest") * s2
    hxx = gaussian_filter(gmag, sigma=sigma_curv, order=(0, 2), mode="nearest") * s2
    hyx = gaussian_filter(gmag, sigma=sigma_curv, order=(1, 1), mode="nearest") * s2
    tr = 0.5 * (hxx + hyy)
    disc = np.hypot(0.5 * (hxx - hyy), hyx)
    lam_min = tr - disc  # most negative curvature across the gradient ridge
    return np.maximum(np.float32(0.0), -lam_min).astype(np.float32)


def structure_tensor_anisotropy(field: np.ndarray, sigma_deriv: float, sigma_win: float) -> np.ndarray:
    """Multi-scale linear structure-tensor coherence (lambda_1 - lambda_2)/(lambda_1 + lambda_2 + eps)."""
    f32 = field.astype(np.float32, copy=False)
    gy = gaussian_filter(f32, sigma=sigma_deriv, order=(1, 0), mode="nearest")
    gx = gaussian_filter(f32, sigma=sigma_deriv, order=(0, 1), mode="nearest")
    jyy = gaussian_filter(gy * gy, sigma=sigma_win, mode="nearest")
    jxx = gaussian_filter(gx * gx, sigma=sigma_win, mode="nearest")
    jyx = gaussian_filter(gy * gx, sigma=sigma_win, mode="nearest")
    tr = jxx + jyy
    diff = np.hypot(jxx - jyy, np.float32(2.0) * jyx)
    return (diff / (tr + np.float32(1e-6))).astype(np.float32)


def contour_obliquity_sin2(
    elev: np.ndarray, cos2_scarp: np.ndarray, sin2_scarp: np.ndarray, valid_lid: np.ndarray, sigma_dem: float = 2.5
) -> np.ndarray:
    """Exact branch-free sin^2(theta_scarp - theta_contour) in [0, 1].

    Uses double-angle identity cos(2(theta_s - theta_c)) = cos2s*cos2c + sin2s*sin2c,
    where contour tangent t = (-d_y elev, d_x elev) follows the same (+col, +row) angle
    convention verified on lidar_scarp_features_u8.tif band 11.
    Returns 0.0 outside valid_lid.
    """
    sm = gaussian_filter(elev.astype(np.float32, copy=False), sigma=sigma_dem, mode="nearest")
    gy, gx = np.gradient(sm)
    # Tangent vector (tx, ty) = (-gy, gx) -> cos(2*theta_c) = (tx^2 - ty^2)/r^2 = (gy^2 - gx^2)/r^2,
    # sin(2*theta_c) = 2*tx*ty/r^2 = -2*gx*gy/r^2
    r2 = gx * gx + gy * gy + np.float32(1e-8)
    cos2c = (gy * gy - gx * gx) / r2
    sin2c = (np.float32(-2.0) * gx * gy) / r2

    c2s = np.where(valid_lid & np.isfinite(cos2_scarp), cos2_scarp, np.float32(0.0))
    s2s = np.where(valid_lid & np.isfinite(sin2_scarp), sin2_scarp, np.float32(0.0))
    cos_2delta = np.clip(c2s * cos2c + s2s * sin2c, -1.0, 1.0)
    sin2 = np.float32(0.5) * (np.float32(1.0) - cos_2delta)
    sin2[~valid_lid] = 0.0
    return np.clip(sin2, 0.0, 1.0).astype(np.float32)


def _zpos(arr: np.ndarray, foot: np.ndarray) -> np.ndarray:
    v = arr[foot]
    med = float(np.median(v))
    iqr = float(np.percentile(v, 75) - np.percentile(v, 25))
    scale = max(iqr / 1.349, 1e-6)
    out = np.maximum(0.0, (arr - med) / scale).astype(np.float32)
    out[~foot] = 0.0
    return out


def build_h31_feature_matrix(
    *,
    cache_path: Path | None = None,
    force: bool = False,
    tf_path: Path = paths.TRAINING,
    lidar_path: Path = paths.LIDAR,
    rad_path: Path = paths.RAD,
    wellspring_path: Path = paths.WELLSPRING,
    template_path: Path = paths.TEMPLATE,
) -> np.ndarray:
    """Compute or load the 12-column float32 H31 physics feature matrix on footprint pixels."""
    if cache_path is not None and cache_path.exists() and not force:
        arr = np.load(cache_path, mmap_mode="r")
        if arr.ndim == 2 and arr.shape[1] == len(H31_FEATURE_NAMES):
            return arr

    with rasterio.open(template_path) as t:
        foot = np.isfinite(t.read(1))
    H, W = foot.shape
    n_foot = int(foot.sum())

    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        out = np.lib.format.open_memmap(
            cache_path, mode="w+", dtype=np.float32, shape=(n_foot, len(H31_FEATURE_NAMES))
        )
    else:
        out = np.empty((n_foot, len(H31_FEATURE_NAMES)), dtype=np.float32)

    tf = h29._read_tf_band_by_desc(tf_path, foot)
    with rasterio.open(tf_path) as src_eq:
        nd_eq = src_eq.nodata
        for b_eq, nm_eq in ((10, "deq_n100a15"), (16, "ieq_n100a15")):
            emb = (src_eq.descriptions[b_eq - 1] or "").split(" - ", 1)[0].strip()
            if emb and emb != nm_eq:
                raise RuntimeError(f"Band {b_eq} description mismatch: {emb!r} != {nm_eq!r}")
            raw_eq = src_eq.read(b_eq).astype(np.float32)
            v_eq = foot & np.isfinite(raw_eq) & (np.abs(raw_eq) < 1e30)
            if nd_eq is not None:
                v_eq &= raw_eq != np.float32(nd_eq)
            tf[nm_eq] = (raw_eq, v_eq)

    # 0-2: Blakely-Simpson Hessian potential-field contact crests on destriped RTP & isostatic gravity
    rtp_ds = h29.destripe_ew_geodawn(*tf["rtp"])
    c_rtp = blakely_ridge_crest(rtp_ds, sigma_grad=1.5, sigma_curv=1.2)
    del rtp_ds
    grav = h29._nearest_fill(*tf["iso_grav_anom"])
    c_grav = blakely_ridge_crest(grav, sigma_grad=2.0, sigma_curv=1.4)
    del grav

    out[:, 0] = c_rtp[foot]
    out[:, 1] = c_grav[foot]
    z_rtp_c = _zpos(c_rtp, foot)
    z_grav_c = _zpos(c_grav, foot)
    out[:, 2] = np.sqrt(z_rtp_c * z_grav_c)[foot].astype(np.float32)
    del c_rtp, c_grav

    # 3-6: Walker Lane multi-scale seismic-fabric anisotropy & transtensional shear coupling
    ieq = np.log1p(np.maximum(0.0, h29._nearest_fill(*tf["ieq_n100a15"])))
    ieq_aniso = structure_tensor_anisotropy(ieq, sigma_deriv=1.2, sigma_win=2.5)
    deq = h29._nearest_fill(*tf["deq_n100a15"])
    neg_deq = -deq
    deq_aniso = structure_tensor_anisotropy(neg_deq, sigma_deriv=2.0, sigma_win=4.5)

    shr = h29._nearest_fill(*tf["geod_shearrate"])
    dil = h29._nearest_fill(*tf["geod_dilaterate"])
    z_shr = _zpos(shr, foot)
    z_dil = _zpos(dil, foot)
    z_prox_eq = _zpos(neg_deq, foot)

    out[:, 3] = ieq_aniso[foot]
    out[:, 4] = deq_aniso[foot]
    out[:, 5] = (z_shr * (np.float32(0.5) + z_dil))[foot].astype(np.float32)
    out[:, 6] = (ieq_aniso * z_shr * (np.float32(0.35) + z_prox_eq))[foot].astype(np.float32)
    del ieq, ieq_aniso, deq, neg_deq, deq_aniso, shr, dil, z_shr, z_dil, z_prox_eq

    # 7: 100 m DEM breakline ridge crest (100% footprint coverage across the 24.63% LiDAR gap)
    elev = h29._nearest_fill(*tf["det_elev"])
    slope = np.maximum(0.0, h29._nearest_fill(*tf["det_elev_slope"]))
    s2 = np.float32(1.5 ** 2)
    hyy = gaussian_filter(slope, sigma=1.5, order=(2, 0), mode="nearest") * s2
    hxx = gaussian_filter(slope, sigma=1.5, order=(0, 2), mode="nearest") * s2
    hyx = gaussian_filter(slope, sigma=1.5, order=(1, 1), mode="nearest") * s2
    dem_crest = np.maximum(np.float32(0.0), -(0.5 * (hxx + hyy) - np.hypot(0.5 * (hxx - hyy), hyx)))
    out[:, 7] = dem_crest[foot].astype(np.float32)
    del hyy, hxx, hyx, dem_crest

    # 8: Blind geothermal conduit multi-line corroboration (structural contact x hydrothermal/MT upflow)
    dtb = h29._nearest_fill(*tf["depth_to_base_surf"])
    z_dtb_grad = _zpos(gaussian_gradient_magnitude(dtb, sigma=2.5, mode="nearest"), foot)
    del dtb
    cond = np.log1p(np.maximum(0.0, h29._nearest_fill(*tf["cond_surf"])))
    z_cond = _zpos(cond, foot)
    del cond

    with rasterio.open(rad_path) as rs:
        k_raw = rs.read(1).astype(np.float32)
        th_raw = rs.read(2).astype(np.float32)
        valid_rad = foot & (k_raw > 0) & (th_raw > 0)
    k_th_diff = h29.rank01_grid(h29.destripe_ew_geodawn(k_raw, valid_rad), valid_rad, foot) - h29.rank01_grid(
        h29.destripe_ew_geodawn(th_raw, valid_rad), valid_rad, foot
    )
    z_kth = _zpos(gaussian_gradient_magnitude(k_th_diff, sigma=3.0, mode="nearest"), foot)
    del k_raw, th_raw, valid_rad, k_th_diff

    teq_nw, diseq_nw, _, upflow_prox = h29.load_wellspring_geotherm_grids(wellspring_path, (H, W), foot)
    z_hydro = np.maximum(_zpos(teq_nw, foot), np.maximum(_zpos(diseq_nw, foot), _zpos(upflow_prox, foot)))
    del teq_nw, diseq_nw, upflow_prox

    struct_line = np.maximum(z_grav_c, np.maximum(z_rtp_c, z_dtb_grad))
    fluid_line = np.maximum(z_hydro, np.maximum(z_kth, z_cond))
    out[:, 8] = np.sqrt(struct_line * fluid_line)[foot].astype(np.float32)
    del z_rtp_c, z_grav_c, z_dtb_grad, z_cond, z_kth, z_hydro, struct_line, fluid_line

    # 9-11: Lake Lahontan contour-obliquity shoreline deconfounding
    bg_slope15 = gaussian_filter(slope, sigma=15.0, mode="nearest")
    p25_slope = float(np.percentile(slope[foot], 25)) + 1e-3
    denom_slope = bg_slope15 + np.float32(p25_slope)
    piedmont_basin_w = (np.float32(1.0) / (np.float32(1.0) + _zpos(bg_slope15, foot))).astype(np.float32)

    with rasterio.open(lidar_path) as ls:
        valid_lid = foot & (ls.read(12) > 0)
        step_raw = ls.read(3).astype(np.float32)
        strike_u8 = ls.read(11).astype(np.float32)
    theta_s = (np.maximum(strike_u8 - np.float32(1.0), np.float32(0.0)) / np.float32(254.0)) * np.float32(np.pi)
    cos2s = np.cos(np.float32(2.0) * theta_s).astype(np.float32)
    sin2s = np.sin(np.float32(2.0) * theta_s).astype(np.float32)
    obliq_sin2 = contour_obliquity_sin2(elev, cos2s, sin2s, valid_lid, sigma_dem=2.5)

    deconf_step = np.where(valid_lid, step_raw / denom_slope, np.float32(0.0)).astype(np.float32)
    out[:, 9] = obliq_sin2[foot]
    out[:, 10] = (deconf_step * obliq_sin2 * piedmont_basin_w)[foot].astype(np.float32)
    out[:, 11] = (deconf_step * (np.float32(1.0) - obliq_sin2) * piedmont_basin_w)[foot].astype(np.float32)

    del tf, elev, slope, bg_slope15, denom_slope, piedmont_basin_w, step_raw, strike_u8, theta_s, cos2s, sin2s, obliq_sin2, deconf_step
    gc.collect()

    assert np.all(np.isfinite(out)), "Non-finite value produced in H31 feature matrix"
    if isinstance(out, np.memmap):
        out.flush()
        return np.load(cache_path, mmap_mode="r")
    return out


def quantile_calibrate_gap(
    p_sub_domain: np.ndarray,
    p_ref_lid: np.ndarray,
    scale: float = LIDAR_GAP_QUANTILE_SCALE,
    n_knots: int = 1001,
) -> np.ndarray:
    """Monotone empirical quantile calibration of M_Sub onto M_Full+M_Sub reference CDF."""
    if p_sub_domain.size == 0 or p_ref_lid.size == 0:
        return p_sub_domain.astype(np.float32, copy=True)
    qs = np.linspace(0.0, 1.0, n_knots, dtype=np.float64)
    src_q = np.quantile(p_sub_domain.astype(np.float64), qs)
    dst_q = np.quantile(p_ref_lid.astype(np.float64), qs) * float(scale)
    # Ensure strict monotonicity of xp for np.interp even if flat quantiles occur at 0:
    src_u, u_idx = np.unique(src_q, return_index=True)
    dst_u = dst_q[u_idx]
    mapped = np.interp(p_sub_domain.astype(np.float64), src_u, dst_u)
    return np.clip(mapped, 0.0, 1.0).astype(np.float32)


def synthesize_stage1_regimes(
    p_full_grid: np.ndarray,
    p_sub_grid: np.ndarray,
    domain_mask: np.ndarray,
    lidar_valid: np.ndarray,
    gap_scale: float = LIDAR_GAP_QUANTILE_SCALE,
) -> np.ndarray:
    """Combine M_Full and M_Sub on lidar_valid, and quantile-calibrate M_Sub on ~lidar_valid."""
    out = np.zeros_like(p_full_grid, dtype=np.float32)
    lv_dom = domain_mask & lidar_valid
    gap_dom = domain_mask & (~lidar_valid)
    if lv_dom.any():
        pf = np.clip(p_full_grid[lv_dom], 0.0, 1.0)
        ps = np.clip(p_sub_grid[lv_dom], 0.0, 1.0)
        comb = np.float32(0.65) * pf + np.float32(0.20) * ps + np.float32(0.15) * np.sqrt(pf * ps)
        out[lv_dom] = np.clip(comb, 0.0, 1.0).astype(np.float32)
    if gap_dom.any():
        ref = out[lv_dom] if lv_dom.any() else np.clip(p_sub_grid[gap_dom], 0.0, 1.0)
        out[gap_dom] = quantile_calibrate_gap(p_sub_grid[gap_dom], ref, scale=gap_scale)
    return out


def axial_crest_measure(prob: np.ndarray, valid_mask: np.ndarray, sigma: float = 1.2) -> np.ndarray:
    """Transverse Hessian crest convexity -lambda_min(H(G_sigma(prob))) >= 0."""
    p32 = np.where(valid_mask, prob, np.float32(0.0)).astype(np.float32)
    s2 = np.float32(sigma ** 2)
    hyy = gaussian_filter(p32, sigma=sigma, order=(2, 0), mode="constant", cval=0.0) * s2
    hxx = gaussian_filter(p32, sigma=sigma, order=(0, 2), mode="constant", cval=0.0) * s2
    hyx = gaussian_filter(p32, sigma=sigma, order=(1, 1), mode="constant", cval=0.0) * s2
    lam_min = 0.5 * (hxx + hyy) - np.hypot(0.5 * (hxx - hyy), hyx)
    crest = np.maximum(np.float32(0.0), -lam_min)
    crest[~valid_mask] = 0.0
    return crest.astype(np.float32)


def _line8_max_lowmem(prob: np.ndarray, half_len: int = 3) -> np.ndarray:
    """Memory-lean 8-azimuth line-integral maximum (1 grid buffer instead of 8x grid)."""
    H, W = prob.shape
    pad = half_len
    p_pad = np.pad(prob.astype(np.float32, copy=False), pad, mode="edge")
    t = np.arange(-half_len, half_len + 1, dtype=np.float64)
    inv_n = np.float32(1.0 / len(t))
    best = np.full((H, W), -np.inf, dtype=np.float32)
    acc = np.empty((H, W), dtype=np.float32)
    for k in range(8):
        theta = k * (np.pi / 8.0)
        dys = np.rint(t * np.sin(theta)).astype(np.int32)
        dxs = np.rint(t * np.cos(theta)).astype(np.int32)
        acc.fill(0.0)
        for dy, dx in zip(dys.tolist(), dxs.tolist()):
            acc += p_pad[pad + dy : pad + dy + H, pad + dx : pad + dx + W]
        acc *= inv_n
        np.maximum(best, acc, out=best)
    del p_pad, acc
    return best


def drop_file_page_cache(*file_paths: Path) -> None:
    """Advise Linux kernel to drop clean file-backed mmap pages from container memory."""
    if not hasattr(os, "posix_fadvise") or not hasattr(os, "POSIX_FADV_DONTNEED"):
        return
    for p in file_paths:
        if p is not None and p.exists():
            fd = os.open(str(p), os.O_RDONLY)
            try:
                os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
            finally:
                os.close(fd)


def stage2_axial_features(
    p_s1: np.ndarray, p_sub: np.ndarray, valid_mask: np.ndarray
) -> np.ndarray:
    """8-channel narrow axial vesselness & halo-subtracted crest matrix on `valid_mask`.

    Crops to valid_mask bounding box (+36 px pad > 4*sigma_max) and streams one column at a time
    so peak working RAM stays < 120 MB.
    """
    n_v = int(valid_mask.sum())
    out = np.empty((n_v, 8), dtype=np.float32)
    if n_v == 0:
        return out

    ys, xs = np.nonzero(valid_mask)
    pad = 36
    r0 = max(int(ys.min()) - pad, 0)
    r1 = min(int(ys.max()) + pad + 1, valid_mask.shape[0])
    c0 = max(int(xs.min()) - pad, 0)
    c1 = min(int(xs.max()) + pad + 1, valid_mask.shape[1])
    del ys, xs
    sl = (slice(r0, r1), slice(c0, c1))

    vm = valid_mask[sl]
    p_clean = np.where(vm, p_s1[sl], np.float32(0.0)).astype(np.float32)
    out[:, 0] = p_clean[vm]
    out[:, 1] = np.where(vm, p_sub[sl], np.float32(0.0))[vm].astype(np.float32)

    for col_i, sig in ((2, 1.0), (3, 2.0), (4, 3.5)):
        fr = h29._frangi_2d(p_clean, sigma=sig, valid_mask=vm)
        out[:, col_i] = fr[vm]
        del fr

    lmax5 = _line8_max_lowmem(p_clean, half_len=3)
    out[:, 5] = lmax5[vm]
    del lmax5

    crest = axial_crest_measure(p_clean, vm, sigma=1.2)
    out[:, 6] = crest[vm]
    del crest

    # Local halo subtraction: explicitly suppresses 800 m off-fault Gaussian shoulders
    num8 = gaussian_filter(p_clean, sigma=8.0, mode="constant", cval=0.0)
    den8 = gaussian_filter(vm.astype(np.float32), sigma=8.0, mode="constant", cval=0.0)
    bg8 = np.where(den8 > 1e-4, num8 / np.maximum(den8, 1e-4), 0.0).astype(np.float32)
    del num8, den8
    out[:, 7] = (p_clean[vm] - bg8[vm]).astype(np.float32)
    del bg8, p_clean, vm
    gc.collect()
    return out


def sharpen_probability_crest(prob: np.ndarray, domain_mask: np.ndarray) -> np.ndarray:
    """Blind axial-crest probability enhancement concentrating weight onto 1-px spines."""
    out = np.zeros_like(prob, dtype=np.float32)
    if not domain_mask.any():
        return out
    crest = axial_crest_measure(prob, domain_mask, sigma=1.0)
    vals = crest[domain_mask]
    pos = vals > 0
    ranks = np.zeros(vals.size, dtype=np.float32)
    if pos.any():
        order = np.argsort(vals[pos], kind="mergesort")
        r = np.empty(order.size, dtype=np.float32)
        r[order] = (np.arange(order.size, dtype=np.float32) + np.float32(0.5)) / np.float32(order.size)
        ranks[pos] = r
    out[domain_mask] = prob[domain_mask] * (np.float32(0.65) + np.float32(0.35) * ranks)
    return out


def emit_h31_celf(
    prob: np.ndarray,
    fold_domain: np.ndarray,
    known: np.ndarray,
    budget: int,
    *,
    b_excl: float = 2.0,
    gamma: float = CELF_GAMMA,
    min_sep_px: float = CELF_MIN_SEP_PX,
) -> np.ndarray:
    """Blind H31-1 axial-crest-sharpened 300 m CELF cover (zero access to hidden or valid_scoring)."""
    d_vis = distance_transform_edt(~known)
    dom = fold_domain & (~known)
    elig = dom & (d_vis > b_excl)
    p_sharp = sharpen_probability_crest(prob, fold_domain)
    return coverage_thin.weighted_celf_cover(
        p_sharp,
        elig,
        dom,
        budget=budget,
        radius_px=metric.RADIUS_PX,
        gamma=gamma,
        min_sep_px=min_sep_px,
    )


def _assemble_expert_rows(
    idx: np.ndarray,
    base_X: np.ndarray,
    sub15_X: np.ndarray,
    h29_X: np.ndarray,
    h31_X: np.ndarray,
    *,
    mode: str,
    extra_s2: np.ndarray | None = None,
) -> np.ndarray:
    n = idx.size
    extra_c = 0 if extra_s2 is None else extra_s2.shape[1]
    if mode == "sub":
        out = np.empty((n, 20 + 15 + 16 + 9 + extra_c), dtype=np.float32)
        b_all = base_X[idx]
        out[:, 0:20] = b_all[:, BASE_NON_LIDAR_IDX]
        del b_all
        out[:, 20:35] = sub15_X[idx]
        h9_all = h29_X[idx]
        out[:, 35:51] = h9_all[:, H29_NON_LIDAR_IDX]
        del h9_all
        out[:, 51:60] = h31_X[idx][:, H31_NON_LIDAR_IDX]
        if extra_s2 is not None:
            out[:, 60:] = extra_s2
        return out
    if mode == "full":
        out = np.empty((n, 32 + 15 + 20 + 12 + extra_c), dtype=np.float32)
        out[:, 0:32] = base_X[idx]
        out[:, 32:47] = sub15_X[idx]
        out[:, 47:67] = h29_X[idx]
        out[:, 67:79] = h31_X[idx]
        if extra_s2 is not None:
            out[:, 79:] = extra_s2
        return out
    raise ValueError(f"Unknown expert mode: {mode}")


def _predict_chunked(
    clf: HistGradientBoostingClassifier,
    idx: np.ndarray,
    base_X: np.ndarray,
    sub15_X: np.ndarray,
    h29_X: np.ndarray,
    h31_X: np.ndarray,
    *,
    mode: str,
    extra_s2: np.ndarray | None = None,
    chunk: int = 200_000,
) -> np.ndarray:
    out = np.empty(idx.size, dtype=np.float32)
    for s in range(0, idx.size, chunk):
        sl = idx[s : s + chunk]
        s2_sl = None if extra_s2 is None else extra_s2[s : s + chunk]
        X_sl = _assemble_expert_rows(sl, base_X, sub15_X, h29_X, h31_X, mode=mode, extra_s2=s2_sl)
        out[s : s + chunk] = clf.predict_proba(X_sl)[:, 1].astype(np.float32)
        del X_sl
    return out


def fit_predict_dual_regime_oof(
    base_X: np.ndarray,
    sub15_X: np.ndarray,
    h29_X: np.ndarray,
    h31_X: np.ndarray,
    labels: np.ndarray,
    foot: np.ndarray,
    lidar_valid: np.ndarray,
    *,
    fold_masks: list[np.ndarray] | None = None,
    buffer_px: float = BUFFER_PX,
    max_neg_s1: int = 340_000,
    max_neg_s2: int = 340_000,
    s1_max_iter: int = 240,
    s2_max_iter: int = 150,
    seed: int = 400,
    cache_dir: Path | None = None,
    cache_tag: str = "quad",
    mmap_paths: tuple[Path, ...] = (),
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Leak-free dual-regime (M_Sub + M_Full) 2-stage nested spatial cross-fitting.

    Returns (prob_sub_oof, prob_s1_synth_oof, prob_s2_oof) as float32 grids of shape foot.shape.
    Every pixel in fold k is predicted strictly from models trained outside fold k with a
    >= buffer_px (600 m) spatial guard.
    """
    if fold_masks is None:
        qf = holdout.make_quadrant_folds(foot)
        fold_masks = [foot & (qf == k) for k in range(4)]
    else:
        fold_masks = [foot & np.asarray(fm, dtype=bool) for fm in fold_masks]
    assert len(fold_masks) == 4, "Nested pairwise cross-fitting requires 4 spatial sectors"
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)

    y_foot = labels[foot]
    fold_id_foot = np.full(int(foot.sum()), -1, dtype=np.int8)
    for k, fm in enumerate(fold_masks):
        fold_id_foot[fm[foot]] = k

    # Pairwise C(4, 2) = 6 buffered Stage-1 models for BOTH M_Sub (non-LiDAR) and M_Full
    pair_preds_sub: dict[tuple[int, int], dict[int, np.ndarray]] = {}
    pair_preds_full: dict[tuple[int, int], dict[int, np.ndarray]] = {}

    for i, j in combinations(range(4), 2):
        rem = [k for k in range(4) if k not in (i, j)]
        ckpt_p = cache_dir / f"ckpt_{cache_tag}_pair_{i}_{j}.npz" if cache_dir is not None else None
        if ckpt_p is not None and ckpt_p.exists():
            with np.load(ckpt_p) as z:
                pair_preds_sub[(i, j)] = {k: z[f"sub_{k}"] for k in rem}
                pair_preds_full[(i, j)] = {k: z[f"full_{k}"] for k in rem}
            print(f"    loaded cached stage1 pair ({i},{j})", flush=True)
            continue

        union_ij = fold_masks[i] | fold_masks[j]
        comp_ij = foot & (~union_ij)
        guard_tr = distance_transform_edt(~comp_ij) > buffer_px
        train_grid = union_ij & guard_tr
        tr_foot = train_grid[foot]
        del union_ij, comp_ij, guard_tr, train_grid

        pos_idx = np.flatnonzero(tr_foot & y_foot)
        neg_all = np.flatnonzero(tr_foot & (~y_foot))
        del tr_foot
        rng = np.random.default_rng(seed * 1000 + i * 10 + j)
        neg_idx = (
            np.sort(rng.choice(neg_all, size=max_neg_s1, replace=False))
            if neg_all.size > max_neg_s1
            else neg_all
        )
        del neg_all
        tr_idx = np.concatenate([pos_idx, neg_idx])
        y_tr = np.r_[np.ones(pos_idx.size, dtype=np.int8), np.zeros(neg_idx.size, dtype=np.int8)]

        # 1A: M_Sub (60 pure non-LiDAR columns)
        X_tr_sub = _assemble_expert_rows(tr_idx, base_X, sub15_X, h29_X, h31_X, mode="sub")
        clf_sub = HistGradientBoostingClassifier(
            max_iter=s1_max_iter,
            learning_rate=0.055,
            max_leaf_nodes=63,
            min_samples_leaf=80,
            l2_regularization=2.0,
            random_state=seed + i * 17 + j,
        )
        clf_sub.fit(X_tr_sub, y_tr)
        del X_tr_sub
        gc.collect()
        drop_file_page_cache(*mmap_paths)

        # 1B: M_Full (79 columns with contour-obliquity shoreline deconfounding)
        X_tr_full = _assemble_expert_rows(tr_idx, base_X, sub15_X, h29_X, h31_X, mode="full")
        clf_full = HistGradientBoostingClassifier(
            max_iter=s1_max_iter,
            learning_rate=0.055,
            max_leaf_nodes=63,
            min_samples_leaf=80,
            l2_regularization=2.0,
            random_state=seed + 50 + i * 17 + j,
        )
        clf_full.fit(X_tr_full, y_tr)
        del X_tr_full, tr_idx, y_tr
        gc.collect()
        drop_file_page_cache(*mmap_paths)

        pair_preds_sub[(i, j)] = {}
        pair_preds_full[(i, j)] = {}
        save_dict: dict[str, np.ndarray] = {}
        for k in rem:
            k_idx = np.flatnonzero(fold_id_foot == k)
            pair_preds_sub[(i, j)][k] = _predict_chunked(
                clf_sub, k_idx, base_X, sub15_X, h29_X, h31_X, mode="sub"
            )
            pair_preds_full[(i, j)][k] = _predict_chunked(
                clf_full, k_idx, base_X, sub15_X, h29_X, h31_X, mode="full"
            )
            save_dict[f"sub_{k}"] = pair_preds_sub[(i, j)][k]
            save_dict[f"full_{k}"] = pair_preds_full[(i, j)][k]
        if ckpt_p is not None:
            np.savez(ckpt_p, **save_dict)
        del clf_sub, clf_full, save_dict
        gc.collect()
        drop_file_page_cache(*mmap_paths)
        print(f"    stage1 pair ({i},{j}) done", flush=True)

    # Assemble outer Stage-1 OOF surfaces (each sector k averages the 3 disjoint pairs)
    prob_sub_oof = np.zeros(foot.shape, dtype=np.float32)
    prob_full_oof = np.zeros(foot.shape, dtype=np.float32)
    prob_s1_oof = np.zeros(foot.shape, dtype=np.float32)
    foot_flat_idx = np.flatnonzero(foot)

    for k in range(4):
        k_idx = np.flatnonzero(fold_id_foot == k)
        valid_pairs = [pair for pair in combinations(range(4), 2) if k not in pair]
        assert len(valid_pairs) == 3
        ps = sum(pair_preds_sub[pair][k] for pair in valid_pairs) / np.float32(3.0)
        pf = sum(pair_preds_full[pair][k] for pair in valid_pairs) / np.float32(3.0)
        prob_sub_oof.ravel()[foot_flat_idx[k_idx]] = ps
        prob_full_oof.ravel()[foot_flat_idx[k_idx]] = pf
        # Synthesize per-fold so test fold k never sees other folds' quantiles
        s1_k = synthesize_stage1_regimes(prob_full_oof, prob_sub_oof, fold_masks[k], lidar_valid)
        prob_s1_oof[fold_masks[k]] = s1_k[fold_masks[k]]
        del s1_k
    del prob_full_oof
    gc.collect()

    # Stage-2 narrow axial vesselness & halo-subtracted crest refiner
    prob_s2_oof = np.zeros(foot.shape, dtype=np.float32)

    for f in range(4):
        te_global_idx = np.flatnonzero(fold_masks[f][foot])
        ckpt_s2 = cache_dir / f"ckpt_{cache_tag}_s2_f{f}.npy" if cache_dir is not None else None
        if ckpt_s2 is not None and ckpt_s2.exists():
            prob_s2_oof.ravel()[foot_flat_idx[te_global_idx]] = np.load(ckpt_s2)
            print(f"    loaded cached stage2 fold {f}", flush=True)
            continue

        test_mask = fold_masks[f]
        train_union = foot & (~test_mask)
        guard_f = distance_transform_edt(~test_mask) > buffer_px

        # Build leak-free inner Stage-1 surfaces on train_union (models never touch fold f or target sector m)
        inner_sub = np.zeros(foot.shape, dtype=np.float32)
        inner_full = np.zeros(foot.shape, dtype=np.float32)
        rem_sectors = [m for m in range(4) if m != f]
        for m in rem_sectors:
            other_two = tuple(sorted(x for x in rem_sectors if x != m))
            m_idx = np.flatnonzero(fold_id_foot == m)
            inner_sub.ravel()[foot_flat_idx[m_idx]] = pair_preds_sub[other_two][m]
            inner_full.ravel()[foot_flat_idx[m_idx]] = pair_preds_full[other_two][m]

        inner_s1 = synthesize_stage1_regimes(inner_full, inner_sub, train_union, lidar_valid)
        del inner_full
        s2_train_mat = stage2_axial_features(inner_s1, inner_sub, train_union)
        del inner_sub, inner_s1

        tu_foot = train_union[foot]
        s2_tu_guard = (train_union & guard_f)[foot][tu_foot]
        del guard_f
        y_tu = labels[train_union]

        pos_tu = np.flatnonzero(s2_tu_guard & y_tu)
        neg_tu_all = np.flatnonzero(s2_tu_guard & (~y_tu))
        del s2_tu_guard, y_tu
        rng2 = np.random.default_rng(seed * 2000 + f)
        neg_tu = (
            np.sort(rng2.choice(neg_tu_all, size=max_neg_s2, replace=False))
            if neg_tu_all.size > max_neg_s2
            else neg_tu_all
        )
        del neg_tu_all
        take_tu = np.concatenate([pos_tu, neg_tu])
        y_s2_tr = np.r_[np.ones(pos_tu.size, dtype=np.int8), np.zeros(neg_tu.size, dtype=np.int8)]

        s2_take = np.ascontiguousarray(s2_train_mat[take_tu], dtype=np.float32)
        del s2_train_mat
        gc.collect()

        tu_global_idx = np.flatnonzero(tu_foot)[take_tu]
        del tu_foot, take_tu
        X_s2_tr = _assemble_expert_rows(
            tu_global_idx, base_X, sub15_X, h29_X, h31_X, mode="full", extra_s2=s2_take
        )
        del tu_global_idx, s2_take
        drop_file_page_cache(*mmap_paths)

        clf_s2 = HistGradientBoostingClassifier(
            max_iter=s2_max_iter,
            learning_rate=0.05,
            max_leaf_nodes=31,
            min_samples_leaf=120,
            l2_regularization=4.0,
            random_state=seed + 500 + f,
        )
        clf_s2.fit(X_s2_tr, y_s2_tr)
        del X_s2_tr, y_s2_tr
        gc.collect()

        # Predict on test_mask strictly from fold-f OOF Stage-1 surfaces computed inside test_mask only
        s2_test_mat = stage2_axial_features(prob_s1_oof, prob_sub_oof, test_mask)
        preds_te = _predict_chunked(
            clf_s2, te_global_idx, base_X, sub15_X, h29_X, h31_X, mode="full", extra_s2=s2_test_mat
        )
        if ckpt_s2 is not None:
            np.save(ckpt_s2, preds_te)
        prob_s2_oof.ravel()[foot_flat_idx[te_global_idx]] = preds_te
        del clf_s2, s2_test_mat, te_global_idx, preds_te
        gc.collect()
        drop_file_page_cache(*mmap_paths)
        print(f"    stage2 fold {f} done", flush=True)

    del pair_preds_sub, pair_preds_full
    gc.collect()
    return prob_sub_oof, prob_s1_oof, prob_s2_oof
