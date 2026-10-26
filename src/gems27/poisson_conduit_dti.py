"""Hypothesis H32-1 (Lane L-S11-2026-10-26):
Poisson-Demagnetized Hydrothermal Conduit, Asymmetric Graben Clay-Cap Coupling &
Cover-Aware 300 m Kernel-Expected-DTI Synthesis (PDHC-K).

Preregistered in `knowledge/26_preregistration_H32_2026-10-26.md` prior to implementation
or evaluation on fresh unconsumed seeds 500..509.

Physical & statistical mechanisms:
1. Local 1.5 km Gaussian-weighted Cordell-Taylor (1971) Poisson gravity-to-pseudogravity
   regression residual |z(g_zz) - (mu_G + alpha_loc * (z(rtp) - mu_M))| gated by sharp
   isostatic gravity horizontal gradient and subdued shallow magnetic vertical gradient
   (hydrothermal titanomagnetite oxidation/sulfidization along blind upflow conduits).
2. Directed basinward (+grad depth_to_base_surf) 400 m & 800 m hanging-wall vs footwall
   playa-detrended magnetotelluric conductivity (`cond_surf`) asymmetry coupled to
   basement-hinge gradient crests (Wannamaker et al. 2014; Siler et al. 2019).
3. Multi-azimuth 1.2 km piedmont canyon-mouth slope-break knickpoint collinearity
   deconfounded against flat-lying hogbacks / Lake Lahontan shorelines via down-slope
   basin thickening, plus Quaternary volcanic vent strain corridors.
4. Cover-aware regime synthesis (`w_blind(depth_to_base_surf, det_local_relief)`) freeing
   blind intrabasin conduits under 3DEP LiDAR-covered Quaternary basins (`SW` Carson Sink /
   Bradys / Desert Peak / Soda Lake / Dixie-Fallon), paired with hybrid 1-px fault-core
   classification + 300 m triangular DTI-kernel Poisson-deviance regression.

Strictly zero access to `labels.tif`, `existing_faults.tif`, `SGMC`, `qfaults`,
`dist_known_fault_px`, or mislabelled band 6 (`tc`) anywhere inside feature construction.
"""
from __future__ import annotations

import gc
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from scipy.ndimage import distance_transform_edt, gaussian_filter
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

from gems27 import coverage_thin, holdout, metric, paths
from gems27 import geothermal_conduit_nis as h31
from gems27 import hydrothermal_piedmont as h29

H32_FEATURE_NAMES: tuple[str, ...] = (
    # 14 pure non-LiDAR subsurface / hydrothermal / piedmont geomorphic channels (0..13)
    "h32_poisson_demag_resid_s15",
    "h32_poisson_alpha_slope_s15",
    "h32_hydro_demag_conduit_idx",
    "h32_shallow_mag_attenuation",
    "h32_rad_potassic_alteration",
    "h32_rad_uth_redox_front",
    "h32_mt_local_clay_excess",
    "h32_clay_cap_asym_400m",
    "h32_clay_cap_asym_800m",
    "h32_graben_clay_conduit_idx",
    "h32_dtb_hinge_axial_crest",
    "h32_qvent_strain_corridor",
    "h32_piedmont_knickpoint_impulse",
    "h32_canyon_mouth_collinearity_1200m",
    # 2 full-stack cover-coupled channels (14..15)
    "h32_lidar_knick_fan_apex",
    "h32_sediment_cover_blindness",
)

H32_S2_FEATURE_NAMES: tuple[str, ...] = (
    "s2_p_s1",
    "s2_q_sub",
    "s2_p_full",
    "s2_w_blind",
    "s2_frangi_s10",
    "s2_frangi_s20",
    "s2_frangi_s35",
    "s2_line_max_700m",
    "s2_axial_crest_s1",
    "s2_axial_crest_sub",
    "s2_local_contrast_s80",
)

H32_NON_LIDAR_IDX: tuple[int, ...] = tuple(range(14))
VENT_ALLOWED_COLS: list[str] = ["row", "col"]

BUFFER_PX: float = 6.0
LIDAR_VALID_SUB_SCALE: float = 0.92
LIDAR_GAP_QUANTILE_SCALE: float = 0.94
CELF_GAMMA: float = 1.35
CELF_MIN_SEP_PX: float = 2.8


def _sigmoid(x: np.ndarray) -> np.ndarray:
    xc = np.clip(x.astype(np.float32, copy=False), -20.0, 20.0)
    return (np.float32(1.0) / (np.float32(1.0) + np.exp(-xc))).astype(np.float32)


def _zscore_foot(arr: np.ndarray, foot: np.ndarray, clip_abs: float = 10.0) -> np.ndarray:
    v = arr[foot]
    med = float(np.median(v))
    iqr = float(np.percentile(v, 75) - np.percentile(v, 25))
    scale = max(iqr / 1.349, 1e-6)
    z = np.clip((arr.astype(np.float32, copy=False) - np.float32(med)) / np.float32(scale), -clip_abs, clip_abs)
    z[~foot] = 0.0
    return z.astype(np.float32)


def _masked_gauss(arr: np.ndarray, valid: np.ndarray, sigma: float) -> np.ndarray:
    """Footprint-normalized Gaussian smoothing preventing study-boundary step artifacts."""
    vm = valid.astype(np.float32, copy=False)
    num = gaussian_filter(np.where(valid, arr, np.float32(0.0)).astype(np.float32), sigma=sigma, mode="constant", cval=0.0)
    den = gaussian_filter(vm, sigma=sigma, mode="constant", cval=0.0)
    out = np.where(den > 1e-4, num / np.maximum(den, 1e-4), 0.0).astype(np.float32)
    out[~valid] = 0.0
    return out


def compute_sediment_cover_blindness(dtb: np.ndarray, local_relief: np.ndarray, foot: np.ndarray) -> np.ndarray:
    """Physical sediment-burial blindness weight w_blind in [0, 1] from basin depth & low relief."""
    w = _sigmoid((dtb - np.float32(250.0)) / np.float32(150.0)) * _sigmoid(
        (np.float32(30.0) - local_relief) / np.float32(12.0)
    )
    w[~foot] = 0.0
    return np.clip(w, 0.0, 1.0).astype(np.float32)


def _read_extra_tf_band(src: rasterio.DatasetReader, band_idx: int, expected_prefix: str, foot: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if band_idx == 6:
        raise ValueError("Band 6 ('tc') is explicitly forbidden (mislabelled radiometric total count)")
    desc = (src.descriptions[band_idx - 1] or "").split(" - ", 1)[0].strip()
    if desc and desc != expected_prefix:
        raise RuntimeError(f"Band {band_idx} description mismatch: {desc!r} != {expected_prefix!r}")
    raw = src.read(band_idx).astype(np.float32)
    valid = foot & np.isfinite(raw) & (np.abs(raw) < 1e30)
    if src.nodata is not None:
        valid &= raw != np.float32(src.nodata)
    return raw, valid


def build_h32_feature_matrix(
    *,
    cache_path: Path | None = None,
    force: bool = False,
    tf_path: Path = paths.TRAINING,
    ext_path: Path = paths.EXTENSIONS,
    lidar_path: Path = paths.LIDAR,
    vents_path: Path = paths.VOLCANIC_VENTS,
    prepared_path: Path = paths.PREPARED_FEATURES,
    template_path: Path = paths.TEMPLATE,
) -> np.ndarray:
    """Compute or load the 16-column float32 H32 physics feature matrix on footprint pixels."""
    if cache_path is not None and cache_path.exists() and not force:
        arr = np.load(cache_path, mmap_mode="r")
        if arr.ndim == 2 and arr.shape[1] == len(H32_FEATURE_NAMES):
            return arr

    with rasterio.open(template_path) as t:
        foot = np.isfinite(t.read(1))
    H, W = foot.shape
    n_foot = int(foot.sum())

    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        out = np.lib.format.open_memmap(
            cache_path, mode="w+", dtype=np.float32, shape=(n_foot, len(H32_FEATURE_NAMES))
        )
    else:
        out = np.empty((n_foot, len(H32_FEATURE_NAMES)), dtype=np.float32)

    # --- Block A (cols 0..5): Poisson gravity-pseudogravity hydrothermal demagnetization & redox ---
    with rasterio.open(tf_path) as src_tf:
        rtp_raw, rtp_val = _read_extra_tf_band(src_tf, 2, "rtp", foot)
        tmi_vg_raw, tmi_vg_val = _read_extra_tf_band(src_tf, 9, "tmi_vg", foot)
        g_vg_raw, g_vg_val = _read_extra_tf_band(src_tf, 11, "iso_grav_anom_vg", foot)
        g_hg_raw, g_hg_val = _read_extra_tf_band(src_tf, 18, "iso_grav_anom_hg", foot)

    rtp_ds = h29.destripe_ew_geodawn(rtp_raw, rtp_val)
    del rtp_raw, rtp_val
    z_m = _zscore_foot(rtp_ds, foot)
    del rtp_ds

    g_vg = h29._nearest_fill(g_vg_raw, g_vg_val)
    del g_vg_raw, g_vg_val
    z_g = _zscore_foot(g_vg, foot)
    del g_vg

    mu_g = _masked_gauss(z_g, foot, sigma=15.0)
    mu_m = _masked_gauss(z_m, foot, sigma=15.0)
    cov_gm = _masked_gauss(z_g * z_m, foot, sigma=15.0) - mu_g * mu_m
    var_m = np.maximum(_masked_gauss(z_m * z_m, foot, sigma=15.0) - mu_m * mu_m, np.float32(0.05))
    alpha_loc = np.clip(cov_gm / var_m, -3.0, 3.0).astype(np.float32)
    alpha_loc[~foot] = 0.0
    r_poisson = np.abs(z_g - (mu_g + alpha_loc * (z_m - mu_m))).astype(np.float32)
    r_poisson[~foot] = 0.0
    del z_g, z_m, mu_g, mu_m, cov_gm, var_m

    g_hg = h29._nearest_fill(g_hg_raw, g_hg_val)
    del g_hg_raw, g_hg_val
    z_ghg_pos = np.maximum(np.float32(0.0), _zscore_foot(g_hg, foot))
    del g_hg

    tmi_vg = h29._nearest_fill(tmi_vg_raw, tmi_vg_val)
    del tmi_vg_raw, tmi_vg_val
    z_tmivg = _zscore_foot(tmi_vg, foot)
    del tmi_vg

    out[:, 0] = r_poisson[foot]
    out[:, 1] = alpha_loc[foot]
    demag_idx = r_poisson * np.log1p(z_ghg_pos) * _sigmoid(-z_tmivg)
    out[:, 2] = demag_idx[foot].astype(np.float32)
    del r_poisson, alpha_loc, demag_idx

    with rasterio.open(ext_path) as src_ext:
        thk_u8 = src_ext.read(1).astype(np.float32)
        uth_u8 = src_ext.read(3).astype(np.float32)
        tmi_up150_u8 = src_ext.read(4).astype(np.float32)

    val_up = foot & (tmi_up150_u8 > 0)
    z_up150 = _zscore_foot(h29.destripe_ew_geodawn(tmi_up150_u8, val_up), foot)
    del tmi_up150_u8, val_up
    out[:, 3] = (z_up150 - z_tmivg)[foot].astype(np.float32)
    del z_up150, z_tmivg

    val_thk = foot & (thk_u8 > 0)
    z_thk = _zscore_foot(h29.destripe_ew_geodawn(thk_u8, val_thk), foot)
    del thk_u8, val_thk
    out[:, 4] = (np.maximum(np.float32(0.0), -z_thk) * np.log1p(z_ghg_pos))[foot].astype(np.float32)
    del z_thk, z_ghg_pos

    val_uth = foot & (uth_u8 > 0)
    z_uth = _zscore_foot(h29.destripe_ew_geodawn(uth_u8, val_uth), foot)
    del uth_u8, val_uth
    uth_crest = h31.axial_crest_measure(np.maximum(np.float32(0.0), z_uth), foot, sigma=1.5)
    out[:, 5] = (np.maximum(np.float32(0.0), z_uth) * uth_crest)[foot].astype(np.float32)
    del z_uth, uth_crest
    gc.collect()

    # --- Block B (cols 6..10): Directed basinward MT clay-cap & basement-hinge coupling ---
    with rasterio.open(tf_path) as src_tf:
        dtb_raw, dtb_val = _read_extra_tf_band(src_tf, 15, "depth_to_base_surf", foot)
        cond_raw, cond_val = _read_extra_tf_band(src_tf, 17, "cond_surf", foot)
        shr_raw, shr_val = _read_extra_tf_band(src_tf, 7, "geod_shearrate", foot)
        dil_raw, dil_val = _read_extra_tf_band(src_tf, 8, "geod_dilaterate", foot)
        elev_raw, elev_val = _read_extra_tf_band(src_tf, 12, "det_elev", foot)

    dtb = np.maximum(np.float32(0.0), h29._nearest_fill(dtb_raw, dtb_val))
    del dtb_raw, dtb_val
    dtb_sm = _masked_gauss(dtb, foot, sigma=1.5)
    gy_dtb, gx_dtb = np.gradient(dtb_sm)
    gmag_dtb = np.hypot(gy_dtb, gx_dtb).astype(np.float32)
    ny = (gy_dtb / (gmag_dtb + np.float32(1e-4))).astype(np.float32)
    nx = (gx_dtb / (gmag_dtb + np.float32(1e-4))).astype(np.float32)
    del dtb_sm

    cond = np.log1p(np.maximum(np.float32(0.0), h29._nearest_fill(cond_raw, cond_val)))
    del cond_raw, cond_val
    mt_excess = (cond - _masked_gauss(cond, foot, sigma=20.0)).astype(np.float32)
    mt_excess[~foot] = 0.0
    del cond
    # Fill outside foot by nearest valid footprint value so +/- offset lookups near border never sample 0
    mt_filled = h29._nearest_fill(mt_excess, foot)
    out[:, 6] = mt_excess[foot]
    del mt_excess

    yy, xx = np.indices((H, W), dtype=np.int32)
    asym4 = np.empty((H, W), dtype=np.float32)
    asym8 = np.empty((H, W), dtype=np.float32)
    for d_px, target_arr in ((4.0, asym4), (8.0, asym8)):
        dy = np.rint(np.float32(d_px) * ny).astype(np.int32)
        dx = np.rint(np.float32(d_px) * nx).astype(np.int32)
        hw = mt_filled[np.clip(yy + dy, 0, H - 1), np.clip(xx + dx, 0, W - 1)]
        fw = mt_filled[np.clip(yy - dy, 0, H - 1), np.clip(xx - dx, 0, W - 1)]
        target_arr[:] = hw - fw
        del dy, dx, hw, fw
    del yy, xx, mt_filled, ny, nx

    out[:, 7] = asym4[foot]
    out[:, 8] = asym8[foot]
    log_gdtb = np.log1p(gmag_dtb).astype(np.float32)
    log_gdtb[~foot] = 0.0
    graben_conduit = log_gdtb * np.maximum(np.float32(0.0), np.maximum(asym4, asym8))
    out[:, 9] = graben_conduit[foot].astype(np.float32)
    del asym4, asym8, graben_conduit

    dtb_crest = h31.axial_crest_measure(log_gdtb, foot, sigma=1.8)
    out[:, 10] = dtb_crest[foot].astype(np.float32)
    del log_gdtb, dtb_crest, gmag_dtb
    gc.collect()

    # --- Block C (cols 11..15): Volcanic vent strain corridors, canyon-mouth knickpoints & cover ---
    vents_df = pd.read_csv(vents_path, usecols=VENT_ALLOWED_COLS)
    assert "dist_known_fault_px" not in vents_df.columns
    vent_imp = np.zeros((H, W), dtype=np.float32)
    vr = np.clip(vents_df["row"].to_numpy(dtype=np.int32), 0, H - 1)
    vc = np.clip(vents_df["col"].to_numpy(dtype=np.int32), 0, W - 1)
    np.add.at(vent_imp, (vr, vc), np.float32(1.0))
    vent_halo = (
        np.float32(0.6) * gaussian_filter(vent_imp, sigma=18.0, mode="constant", cval=0.0)
        + np.float32(0.4) * gaussian_filter(vent_imp, sigma=40.0, mode="constant", cval=0.0)
    )
    del vent_imp

    z_shr = _zscore_foot(h29._nearest_fill(shr_raw, shr_val), foot)
    z_dil = _zscore_foot(h29._nearest_fill(dil_raw, dil_val), foot)
    del shr_raw, shr_val, dil_raw, dil_val
    strain_pos = np.log1p(np.maximum(np.float32(0.0), z_shr + z_dil))
    out[:, 11] = (np.log1p(np.float32(1e4) * vent_halo) * strain_pos)[foot].astype(np.float32)
    del vent_halo, z_shr, z_dil, strain_pos

    prep = np.load(prepared_path, mmap_mode="r")
    local_relief = np.zeros((H, W), dtype=np.float32)
    det_grad = np.zeros((H, W), dtype=np.float32)
    local_relief[foot] = prep[:, 30]
    det_grad[foot] = prep[:, 31]
    local_relief = h29._nearest_fill(local_relief, foot)
    det_grad = h29._nearest_fill(det_grad, foot)

    elev = h29._nearest_fill(elev_raw, elev_val)
    del elev_raw, elev_val
    elev_sm = _masked_gauss(elev, foot, sigma=2.0)
    del elev
    gy_z, gx_z = np.gradient(elev_sm)
    del elev_sm
    znorm = np.hypot(gy_z, gx_z) + np.float32(1e-4)
    uy_down = (-gy_z / znorm).astype(np.float32)
    ux_down = (-gx_z / znorm).astype(np.float32)
    del gy_z, gx_z, znorm

    grad_sm = _masked_gauss(det_grad, foot, sigma=1.5)
    del det_grad
    gy_s, gx_s = np.gradient(grad_sm)
    del grad_sm
    # Positive where steep bedrock canyon gradient drops abruptly moving down-slope onto fan
    slope_drop_down = np.maximum(np.float32(0.0), -(gy_s * uy_down + gx_s * ux_down))
    del gy_s, gx_s
    # Gate by down-slope basin-fill thickening to reject flat-lying bedrock hogbacks & shorelines
    basin_thick_down = np.maximum(np.float32(0.0), gy_dtb * uy_down + gx_dtb * ux_down)
    del gy_dtb, gx_dtb, uy_down, ux_down

    knick_imp = np.log1p(slope_drop_down * np.log1p(basin_thick_down)).astype(np.float32)
    knick_imp[~foot] = 0.0
    del slope_drop_down, basin_thick_down
    out[:, 12] = knick_imp[foot]

    knick_line = h31._line8_max_lowmem(knick_imp, half_len=6) - _masked_gauss(knick_imp, foot, sigma=6.0)
    knick_line[~foot] = 0.0
    del knick_imp
    out[:, 13] = knick_line[foot].astype(np.float32)

    with rasterio.open(lidar_path) as src_lid:
        lid_step = src_lid.read(3).astype(np.float32) / np.float32(255.0)
        lid_coh = src_lid.read(10).astype(np.float32) / np.float32(255.0)
        lid_val = foot & (src_lid.read(12) > 0)
    lid_term = np.where(lid_val, np.log1p(np.float32(10.0) * lid_step * lid_coh), np.float32(0.0))
    out[:, 14] = (np.maximum(np.float32(0.0), knick_line) * lid_term)[foot].astype(np.float32)
    del knick_line, lid_step, lid_coh, lid_val, lid_term

    w_blind = compute_sediment_cover_blindness(dtb, local_relief, foot)
    out[:, 15] = w_blind[foot]
    del dtb, local_relief, w_blind

    if isinstance(out, np.memmap):
        out.flush()
        del out
        gc.collect()
        return np.load(cache_path, mmap_mode="r")
    return out


def synthesize_cover_aware_stage1(
    p_full_grid: np.ndarray,
    p_sub_grid: np.ndarray,
    w_blind_grid: np.ndarray,
    domain_mask: np.ndarray,
    lidar_valid: np.ndarray,
    *,
    sub_scale_lv: float = LIDAR_VALID_SUB_SCALE,
    gap_scale: float = LIDAR_GAP_QUANTILE_SCALE,
) -> tuple[np.ndarray, np.ndarray]:
    """Synthesize cover-aware Stage-1 probability p_s1 and calibrated subsurface q_sub on domain_mask."""
    p_s1 = np.zeros_like(p_full_grid, dtype=np.float32)
    q_sub = np.zeros_like(p_sub_grid, dtype=np.float32)
    lv_dom = domain_mask & lidar_valid
    gap_dom = domain_mask & (~lidar_valid)

    if lv_dom.any():
        pf = np.clip(p_full_grid[lv_dom], 0.0, 1.0).astype(np.float32)
        ps_raw = np.clip(p_sub_grid[lv_dom], 0.0, 1.0).astype(np.float32)
        qs = h31.quantile_calibrate_gap(ps_raw, pf, scale=sub_scale_lv)
        q_sub[lv_dom] = qs
        eta = np.float32(0.50) * np.clip(w_blind_grid[lv_dom], 0.0, 1.0).astype(np.float32)
        exposed = (
            np.float32(0.62) * pf
            + np.float32(0.22) * qs
            + np.float32(0.16) * np.sqrt(np.maximum(np.float32(0.0), pf * qs))
        )
        buried = np.maximum(pf, np.float32(0.88) * qs)
        comb = (np.float32(1.0) - eta) * exposed + eta * buried
        p_s1[lv_dom] = np.clip(comb, 0.0, 1.0).astype(np.float32)

    if gap_dom.any():
        ref = p_s1[lv_dom] if lv_dom.any() else np.clip(p_sub_grid[gap_dom], 0.0, 1.0)
        qg = h31.quantile_calibrate_gap(p_sub_grid[gap_dom], ref, scale=gap_scale)
        p_s1[gap_dom] = qg
        q_sub[gap_dom] = qg

    return p_s1, q_sub


def stage2_pdhc_features(
    p_s1: np.ndarray,
    q_sub: np.ndarray,
    p_full: np.ndarray,
    w_blind: np.ndarray,
    valid_mask: np.ndarray,
) -> np.ndarray:
    """11-channel cover-aware axial vesselness, subsurface crest & halo-subtracted context matrix."""
    n_v = int(valid_mask.sum())
    out = np.empty((n_v, len(H32_S2_FEATURE_NAMES)), dtype=np.float32)
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
    s1_c = np.where(vm, p_s1[sl], np.float32(0.0)).astype(np.float32)
    qs_c = np.where(vm, q_sub[sl], np.float32(0.0)).astype(np.float32)
    pf_c = np.where(vm, p_full[sl], np.float32(0.0)).astype(np.float32)

    out[:, 0] = s1_c[vm]
    out[:, 1] = qs_c[vm]
    out[:, 2] = pf_c[vm]
    out[:, 3] = np.where(vm, w_blind[sl], np.float32(0.0))[vm].astype(np.float32)
    del pf_c

    for col_i, sig in ((4, 1.0), (5, 2.0), (6, 3.5)):
        fr = h29._frangi_2d(s1_c, sigma=sig, valid_mask=vm)
        out[:, col_i] = fr[vm]
        del fr

    lmax = h31._line8_max_lowmem(s1_c, half_len=3)
    out[:, 7] = lmax[vm]
    del lmax

    crest_s1 = h31.axial_crest_measure(s1_c, vm, sigma=1.2)
    out[:, 8] = crest_s1[vm]
    del crest_s1

    crest_sub = h31.axial_crest_measure(qs_c, vm, sigma=2.0)
    out[:, 9] = crest_sub[vm]
    del crest_sub, qs_c

    num8 = gaussian_filter(s1_c, sigma=8.0, mode="constant", cval=0.0)
    den8 = gaussian_filter(vm.astype(np.float32), sigma=8.0, mode="constant", cval=0.0)
    bg8 = np.where(den8 > 1e-4, num8 / np.maximum(den8, 1e-4), 0.0).astype(np.float32)
    del num8, den8
    out[:, 10] = (s1_c[vm] - bg8[vm]).astype(np.float32)
    del bg8, s1_c, vm
    gc.collect()
    return out


def _assemble_h32_rows(
    idx: np.ndarray,
    base_X: np.ndarray,
    sub15_X: np.ndarray,
    h29_X: np.ndarray,
    h31_X: np.ndarray,
    h32_X: np.ndarray,
    *,
    mode: str,
    extra_s2: np.ndarray | None = None,
) -> np.ndarray:
    n = idx.size
    extra_c = 0 if extra_s2 is None else extra_s2.shape[1]
    if mode == "sub":
        # 20 + 15 + 16 + 9 + 14 = 74 pure non-LiDAR columns
        out = np.empty((n, 74 + extra_c), dtype=np.float32)
        b_all = base_X[idx]
        out[:, 0:20] = b_all[:, h31.BASE_NON_LIDAR_IDX]
        del b_all
        out[:, 20:35] = sub15_X[idx]
        h9_all = h29_X[idx]
        out[:, 35:51] = h9_all[:, h31.H29_NON_LIDAR_IDX]
        del h9_all
        out[:, 51:60] = h31_X[idx][:, h31.H31_NON_LIDAR_IDX]
        out[:, 60:74] = h32_X[idx][:, H32_NON_LIDAR_IDX]
        if extra_s2 is not None:
            out[:, 74:] = extra_s2
        return out
    if mode == "full":
        # 32 + 15 + 20 + 12 + 16 = 95 multi-physics columns
        out = np.empty((n, 95 + extra_c), dtype=np.float32)
        out[:, 0:32] = base_X[idx]
        out[:, 32:47] = sub15_X[idx]
        out[:, 47:67] = h29_X[idx]
        out[:, 67:79] = h31_X[idx]
        out[:, 79:95] = h32_X[idx]
        if extra_s2 is not None:
            out[:, 95:] = extra_s2
        return out
    raise ValueError(f"Unknown expert mode: {mode}")


def _predict_dual_chunked(
    clf: HistGradientBoostingClassifier,
    reg: HistGradientBoostingRegressor,
    clf_weight: float,
    idx: np.ndarray,
    base_X: np.ndarray,
    sub15_X: np.ndarray,
    h29_X: np.ndarray,
    h31_X: np.ndarray,
    h32_X: np.ndarray,
    *,
    mode: str,
    extra_s2: np.ndarray | None = None,
    chunk: int = 200_000,
) -> np.ndarray:
    p_clf = np.empty(idx.size, dtype=np.float32)
    p_reg = np.empty(idx.size, dtype=np.float32)
    for s in range(0, idx.size, chunk):
        sl = idx[s : s + chunk]
        s2_sl = None if extra_s2 is None else extra_s2[s : s + chunk]
        X_sl = _assemble_h32_rows(
            sl, base_X, sub15_X, h29_X, h31_X, h32_X, mode=mode, extra_s2=s2_sl
        )
        p_clf[s : s + chunk] = clf.predict_proba(X_sl)[:, 1].astype(np.float32)
        p_reg[s : s + chunk] = np.maximum(np.float32(0.0), reg.predict(X_sl).astype(np.float32))
        del X_sl
    p_reg_cal = h31.quantile_calibrate_gap(p_reg, p_clf, scale=1.0)
    w_c = np.float32(clf_weight)
    w_r = np.float32(1.0 - clf_weight)
    return np.clip(w_c * p_clf + w_r * p_reg_cal, 0.0, 1.0).astype(np.float32)


def _sample_kernel_regression_indices(
    tr_mask_vec: np.ndarray,
    y_vec: np.ndarray,
    d_tr_vec: np.ndarray,
    rng: np.random.Generator,
    *,
    max_flank: int = 80_000,
    max_bg: int = 260_000,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Importance-weighted 300 m DTI kernel regression sample strictly inside buffered train domain."""
    core_idx = np.flatnonzero(tr_mask_vec & y_vec)
    flank_all = np.flatnonzero(tr_mask_vec & (~y_vec) & (d_tr_vec < 3.0))
    bg_all = np.flatnonzero(tr_mask_vec & (d_tr_vec >= 3.0))

    if flank_all.size > max_flank:
        flank_idx = np.sort(rng.choice(flank_all, size=max_flank, replace=False))
        w_flank_val = np.float32(flank_all.size / float(max_flank))
    else:
        flank_idx = flank_all
        w_flank_val = np.float32(1.0)

    if bg_all.size > max_bg:
        bg_idx = np.sort(rng.choice(bg_all, size=max_bg, replace=False))
    else:
        bg_idx = bg_all

    idx = np.concatenate([core_idx, flank_idx, bg_idx])
    yk = np.clip(np.float32(1.0) - d_tr_vec[idx].astype(np.float32) / np.float32(3.0), 0.0, 1.0)
    yk[0 : core_idx.size] = np.float32(1.0)
    yk[core_idx.size + flank_idx.size :] = np.float32(0.0)
    sw = np.ones(idx.size, dtype=np.float32)
    sw[core_idx.size : core_idx.size + flank_idx.size] = w_flank_val
    return idx, yk, sw


def emit_h32_celf(
    prob: np.ndarray,
    fold_domain: np.ndarray,
    known: np.ndarray,
    budget: int,
    *,
    b_excl: float = 2.0,
    gamma: float = CELF_GAMMA,
    min_sep_px: float = CELF_MIN_SEP_PX,
) -> np.ndarray:
    """Blind H32-1 axial-crest-sharpened 300 m CELF cover (zero access to hidden or valid_scoring)."""
    d_vis = distance_transform_edt(~known)
    dom = fold_domain & (~known)
    elig = dom & (d_vis > b_excl)
    p_sharp = h31.sharpen_probability_crest(prob, fold_domain)
    return coverage_thin.weighted_celf_cover(
        p_sharp,
        elig,
        dom,
        budget=budget,
        radius_px=metric.RADIUS_PX,
        gamma=gamma,
        min_sep_px=min_sep_px,
    )


def fit_predict_pdhc_oof(
    base_X: np.ndarray,
    sub15_X: np.ndarray,
    h29_X: np.ndarray,
    h31_X: np.ndarray,
    h32_X: np.ndarray,
    labels: np.ndarray,
    foot: np.ndarray,
    lidar_valid: np.ndarray,
    *,
    fold_masks: list[np.ndarray] | None = None,
    buffer_px: float = BUFFER_PX,
    max_neg_s1: int = 320_000,
    max_neg_s2: int = 320_000,
    s1_max_iter: int = 240,
    s2_max_iter: int = 160,
    seed: int = 500,
    cache_dir: Path | None = None,
    cache_tag: str = "quad",
    mmap_paths: tuple[Path, ...] = (),
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Leak-free cover-aware dual-target (core classifier + 300 m DTI kernel regressor) nested OOF.

    Every pixel in sector k is predicted strictly from models trained outside sector k with a
    > buffer_px (600 m) spatial guard, and all 300 m DTI kernel training targets `y_K` are
    computed strictly from training-domain labels (`labels & train_grid`).
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

    w_blind_grid = np.zeros(foot.shape, dtype=np.float32)
    w_blind_grid[foot] = np.asarray(h32_X[:, 15], dtype=np.float32)

    pair_preds_sub: dict[tuple[int, int], dict[int, np.ndarray]] = {}
    pair_preds_full: dict[tuple[int, int], dict[int, np.ndarray]] = {}

    for i, j in combinations(range(4), 2):
        rem = [k for k in range(4) if k not in (i, j)]
        ckpt_p = cache_dir / f"ckpt_h32_{cache_tag}_pair_{i}_{j}.npz" if cache_dir is not None else None
        if ckpt_p is not None and ckpt_p.exists():
            with np.load(ckpt_p) as z:
                pair_preds_sub[(i, j)] = {k: z[f"sub_{k}"] for k in rem}
                pair_preds_full[(i, j)] = {k: z[f"full_{k}"] for k in rem}
            print(f"    loaded cached H32 stage1 pair ({i},{j})", flush=True)
            continue

        union_ij = fold_masks[i] | fold_masks[j]
        comp_ij = foot & (~union_ij)
        guard_tr = distance_transform_edt(~comp_ij) > buffer_px
        train_grid = union_ij & guard_tr
        tr_foot = train_grid[foot]

        # Strictly training-only EDT for continuous 300 m DTI kernel target (zero test labels)
        y_tr_grid = labels & train_grid
        d_tr_grid = (
            distance_transform_edt(~y_tr_grid)
            if y_tr_grid.any()
            else np.full(foot.shape, 999.0, dtype=np.float64)
        )
        d_tr_foot = d_tr_grid[foot].astype(np.float32)
        del union_ij, comp_ij, guard_tr, train_grid, y_tr_grid, d_tr_grid

        rng = np.random.default_rng(seed * 1000 + i * 10 + j)
        pos_idx = np.flatnonzero(tr_foot & y_foot)
        neg_all = np.flatnonzero(tr_foot & (~y_foot))
        neg_idx = (
            np.sort(rng.choice(neg_all, size=max_neg_s1, replace=False))
            if neg_all.size > max_neg_s1
            else neg_all
        )
        del neg_all
        clf_idx = np.concatenate([pos_idx, neg_idx])
        y_clf = np.r_[np.ones(pos_idx.size, dtype=np.int8), np.zeros(neg_idx.size, dtype=np.int8)]
        del pos_idx, neg_idx

        reg_idx, y_reg, sw_reg = _sample_kernel_regression_indices(tr_foot, y_foot, d_tr_foot, rng)
        del tr_foot, d_tr_foot

        # 1A: Subsurface Conduit Expert (74 pure non-LiDAR columns: core clf + 300 m kernel reg)
        X_clf_sub = _assemble_h32_rows(clf_idx, base_X, sub15_X, h29_X, h31_X, h32_X, mode="sub")
        clf_sub = HistGradientBoostingClassifier(
            max_iter=s1_max_iter,
            learning_rate=0.055,
            max_leaf_nodes=63,
            min_samples_leaf=80,
            l2_regularization=2.0,
            random_state=seed + i * 17 + j,
        )
        clf_sub.fit(X_clf_sub, y_clf)
        del X_clf_sub
        gc.collect()

        X_reg_sub = _assemble_h32_rows(reg_idx, base_X, sub15_X, h29_X, h31_X, h32_X, mode="sub")
        reg_sub = HistGradientBoostingRegressor(
            loss="poisson",
            max_iter=s1_max_iter,
            learning_rate=0.055,
            max_leaf_nodes=63,
            min_samples_leaf=80,
            l2_regularization=2.0,
            random_state=seed + 31 + i * 17 + j,
        )
        reg_sub.fit(X_reg_sub, y_reg, sample_weight=sw_reg)
        del X_reg_sub
        gc.collect()
        h31.drop_file_page_cache(*mmap_paths)

        # 1B: Full Multi-Physics Expert (95 columns: core clf + 300 m kernel reg)
        X_clf_full = _assemble_h32_rows(clf_idx, base_X, sub15_X, h29_X, h31_X, h32_X, mode="full")
        clf_full = HistGradientBoostingClassifier(
            max_iter=s1_max_iter,
            learning_rate=0.055,
            max_leaf_nodes=63,
            min_samples_leaf=80,
            l2_regularization=2.0,
            random_state=seed + 71 + i * 17 + j,
        )
        clf_full.fit(X_clf_full, y_clf)
        del X_clf_full, clf_idx, y_clf
        gc.collect()

        X_reg_full = _assemble_h32_rows(reg_idx, base_X, sub15_X, h29_X, h31_X, h32_X, mode="full")
        reg_full = HistGradientBoostingRegressor(
            loss="poisson",
            max_iter=s1_max_iter,
            learning_rate=0.055,
            max_leaf_nodes=63,
            min_samples_leaf=80,
            l2_regularization=2.0,
            random_state=seed + 101 + i * 17 + j,
        )
        reg_full.fit(X_reg_full, y_reg, sample_weight=sw_reg)
        del X_reg_full, reg_idx, y_reg, sw_reg
        gc.collect()
        h31.drop_file_page_cache(*mmap_paths)

        pair_preds_sub[(i, j)] = {}
        pair_preds_full[(i, j)] = {}
        save_dict: dict[str, np.ndarray] = {}
        for k in rem:
            k_idx = np.flatnonzero(fold_id_foot == k)
            pair_preds_sub[(i, j)][k] = _predict_dual_chunked(
                clf_sub, reg_sub, 0.55, k_idx, base_X, sub15_X, h29_X, h31_X, h32_X, mode="sub"
            )
            pair_preds_full[(i, j)][k] = _predict_dual_chunked(
                clf_full, reg_full, 0.70, k_idx, base_X, sub15_X, h29_X, h31_X, h32_X, mode="full"
            )
            save_dict[f"sub_{k}"] = pair_preds_sub[(i, j)][k]
            save_dict[f"full_{k}"] = pair_preds_full[(i, j)][k]
        if ckpt_p is not None:
            np.savez(ckpt_p, **save_dict)
        del clf_sub, reg_sub, clf_full, reg_full, save_dict
        gc.collect()
        h31.drop_file_page_cache(*mmap_paths)
        print(f"    H32 stage1 pair ({i},{j}) done", flush=True)

    # Assemble outer Stage-1 OOF surfaces per sector k (strictly fold-local quantile calibration)
    prob_sub_oof = np.zeros(foot.shape, dtype=np.float32)
    prob_full_oof = np.zeros(foot.shape, dtype=np.float32)
    prob_s1_oof = np.zeros(foot.shape, dtype=np.float32)
    q_sub_oof = np.zeros(foot.shape, dtype=np.float32)
    foot_flat_idx = np.flatnonzero(foot)

    for k in range(4):
        k_idx = np.flatnonzero(fold_id_foot == k)
        valid_pairs = [pair for pair in combinations(range(4), 2) if k not in pair]
        assert len(valid_pairs) == 3
        ps = sum(pair_preds_sub[pair][k] for pair in valid_pairs) / np.float32(3.0)
        pf = sum(pair_preds_full[pair][k] for pair in valid_pairs) / np.float32(3.0)
        prob_sub_oof.ravel()[foot_flat_idx[k_idx]] = ps
        prob_full_oof.ravel()[foot_flat_idx[k_idx]] = pf
        s1_k, qs_k = synthesize_cover_aware_stage1(
            prob_full_oof, prob_sub_oof, w_blind_grid, fold_masks[k], lidar_valid
        )
        prob_s1_oof[fold_masks[k]] = s1_k[fold_masks[k]]
        q_sub_oof[fold_masks[k]] = qs_k[fold_masks[k]]
        del s1_k, qs_k

    # Stage-2 Cover-Aware Dual-Objective Axial Refiner (106 columns)
    prob_s2_oof = np.zeros(foot.shape, dtype=np.float32)

    for f in range(4):
        te_global_idx = np.flatnonzero(fold_masks[f][foot])
        ckpt_s2 = cache_dir / f"ckpt_h32_{cache_tag}_s2_f{f}.npy" if cache_dir is not None else None
        if ckpt_s2 is not None and ckpt_s2.exists():
            prob_s2_oof.ravel()[foot_flat_idx[te_global_idx]] = np.load(ckpt_s2)
            print(f"    loaded cached H32 stage2 fold {f}", flush=True)
            continue

        test_mask = fold_masks[f]
        train_union = foot & (~test_mask)
        guard_f = distance_transform_edt(~test_mask) > buffer_px
        train_guarded = train_union & guard_f
        del guard_f

        inner_sub = np.zeros(foot.shape, dtype=np.float32)
        inner_full = np.zeros(foot.shape, dtype=np.float32)
        rem_sectors = [m for m in range(4) if m != f]
        for m in rem_sectors:
            other_two = tuple(sorted(x for x in rem_sectors if x != m))
            m_idx = np.flatnonzero(fold_id_foot == m)
            inner_sub.ravel()[foot_flat_idx[m_idx]] = pair_preds_sub[other_two][m]
            inner_full.ravel()[foot_flat_idx[m_idx]] = pair_preds_full[other_two][m]

        inner_s1, inner_qsub = synthesize_cover_aware_stage1(
            inner_full, inner_sub, w_blind_grid, train_union, lidar_valid
        )
        del inner_sub
        s2_train_mat = stage2_pdhc_features(
            inner_s1, inner_qsub, inner_full, w_blind_grid, train_union
        )
        del inner_s1, inner_qsub, inner_full

        y_tu_grid = labels & train_guarded
        d_tu_grid = (
            distance_transform_edt(~y_tu_grid)
            if y_tu_grid.any()
            else np.full(foot.shape, 999.0, dtype=np.float64)
        )
        d_tu_vec = d_tu_grid[train_union].astype(np.float32)
        del y_tu_grid, d_tu_grid

        tu_foot = train_union[foot]
        tu_global_all = np.flatnonzero(tu_foot)
        s2_tu_guard = train_guarded[train_union]
        y_tu = labels[train_union]
        del train_guarded, tu_foot

        rng2 = np.random.default_rng(seed * 2000 + f)
        pos_tu = np.flatnonzero(s2_tu_guard & y_tu)
        neg_tu_all = np.flatnonzero(s2_tu_guard & (~y_tu))
        neg_tu = (
            np.sort(rng2.choice(neg_tu_all, size=max_neg_s2, replace=False))
            if neg_tu_all.size > max_neg_s2
            else neg_tu_all
        )
        del neg_tu_all
        take_clf = np.concatenate([pos_tu, neg_tu])
        y_s2_clf = np.r_[np.ones(pos_tu.size, dtype=np.int8), np.zeros(neg_tu.size, dtype=np.int8)]
        del pos_tu, neg_tu

        take_reg, y_s2_reg, sw_s2_reg = _sample_kernel_regression_indices(
            s2_tu_guard, y_tu, d_tu_vec, rng2
        )
        del s2_tu_guard, y_tu, d_tu_vec

        s2_clf_extra = np.ascontiguousarray(s2_train_mat[take_clf], dtype=np.float32)
        s2_reg_extra = np.ascontiguousarray(s2_train_mat[take_reg], dtype=np.float32)
        del s2_train_mat
        gc.collect()

        X_s2_clf = _assemble_h32_rows(
            tu_global_all[take_clf],
            base_X,
            sub15_X,
            h29_X,
            h31_X,
            h32_X,
            mode="full",
            extra_s2=s2_clf_extra,
        )
        del take_clf, s2_clf_extra
        h31.drop_file_page_cache(*mmap_paths)

        clf_s2 = HistGradientBoostingClassifier(
            max_iter=s2_max_iter,
            learning_rate=0.05,
            max_leaf_nodes=31,
            min_samples_leaf=120,
            l2_regularization=4.0,
            random_state=seed + 500 + f,
        )
        clf_s2.fit(X_s2_clf, y_s2_clf)
        del X_s2_clf, y_s2_clf
        gc.collect()

        X_s2_reg = _assemble_h32_rows(
            tu_global_all[take_reg],
            base_X,
            sub15_X,
            h29_X,
            h31_X,
            h32_X,
            mode="full",
            extra_s2=s2_reg_extra,
        )
        del tu_global_all, take_reg, s2_reg_extra
        h31.drop_file_page_cache(*mmap_paths)

        reg_s2 = HistGradientBoostingRegressor(
            loss="poisson",
            max_iter=s2_max_iter,
            learning_rate=0.05,
            max_leaf_nodes=31,
            min_samples_leaf=120,
            l2_regularization=4.0,
            random_state=seed + 700 + f,
        )
        reg_s2.fit(X_s2_reg, y_s2_reg, sample_weight=sw_s2_reg)
        del X_s2_reg, y_s2_reg, sw_s2_reg
        gc.collect()

        s2_test_mat = stage2_pdhc_features(
            prob_s1_oof, q_sub_oof, prob_full_oof, w_blind_grid, test_mask
        )
        preds_te = _predict_dual_chunked(
            clf_s2,
            reg_s2,
            0.60,
            te_global_idx,
            base_X,
            sub15_X,
            h29_X,
            h31_X,
            h32_X,
            mode="full",
            extra_s2=s2_test_mat,
        )
        if ckpt_s2 is not None:
            np.save(ckpt_s2, preds_te)
        prob_s2_oof.ravel()[foot_flat_idx[te_global_idx]] = preds_te
        del clf_s2, reg_s2, s2_test_mat, te_global_idx, preds_te
        gc.collect()
        h31.drop_file_page_cache(*mmap_paths)
        print(f"    H32 stage2 fold {f} done", flush=True)

    del pair_preds_sub, pair_preds_full, prob_full_oof, q_sub_oof, w_blind_grid
    gc.collect()
    return prob_sub_oof, prob_s1_oof, prob_s2_oof
