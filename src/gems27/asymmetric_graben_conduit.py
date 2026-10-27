"""Hypothesis H33-1 (Lane L-S12-2026-10-26):
Asymmetric Graben-Margin Clay-Cap Dip-Coupling, Canyon-Mouth Range-Front Collinearity,
and End-to-End Dual-Regime Orthogonal-Radon CELF Allocation (AGMC-CM-CELF30).

Preregistered in `knowledge/28_preregistration_H33_2026-10-26.md` (commit `691fbdd`):
1. Cross-strike asymmetric half-graben dip-vector coupling (`H31-3` physics): along unit
   basinward normal u_hat = grad(G_4(depth_to_base_surf)) / ||grad(G_4(depth_to_base_surf))||,
   contrasts hanging-wall smectite/brine electrical conductivity (`cond_surf` at +400 m, +800 m)
   against resistive footwall horsts (-400 m, -800 m), cancelling flat interior playas while
   isolating dipping (`50-65 deg`) Basin-and-Range fault conduits, paired with normal-sense
   footwall-to-hanging-wall density (`iso_grav_anom`) and elevation (`det_elev`) throw.
2. Deep-crustal upward-continuation magnetic persistence (`TMI_up150` vs `rtp`), potassic
   metasomatism (`ThK` depletion along structural walls from `geodawn_extensions_u8.tif`),
   and sharp 900 m silica/cation geothermometer + Quaternary volcanic vent structural corridors.
3. Along-strike canyon-mouth knickpoint & fan-apex collinearity (`H29-5` physics): integrates
   piedmont profile concavity x transverse relief incision over +/- 1.2 km along regional
   range-front strike tangent t_hat perp grad(G_10(det_elev)), bridging Holocene alluvial fans.
4. End-to-end dual-regime Stage-1 + Stage-2 nested spatial cross-fitting (`M_Sub` on 50 pure
   LiDAR-free columns; `M_Full` trained strictly on `lidar_valid` pixels so zero `NaN`-LiDAR
   tree branches leak regional priors), 16-azimuth (`11.25 deg`) multi-kilometer (`+/-500 m`
   and `+/-1,100 m`) orthogonal Radon line-minus-cross anisotropy, and 1-D manifold-sharpened
   `min_sep_px = 3.00` (`300 m` exact kernel radius) submodular CELF cover.

Strictly zero access to `labels.tif`, `existing_faults.tif`, `qfaults_v2_in_footprint.json`,
`derived_sgmc_faults_100m_u8.tif`, `dist_known_fault_px`, or band 6 (`tc`) inside feature builders.
"""
from __future__ import annotations

import gc
import json
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from scipy.ndimage import distance_transform_edt, gaussian_filter, gaussian_gradient_magnitude
from sklearn.ensemble import HistGradientBoostingClassifier

from gems27 import coverage_thin, holdout, metric, paths
from gems27 import geothermal_conduit_nis as h31
from gems27 import hydrothermal_piedmont as h29

H33_FEATURE_NAMES: tuple[str, ...] = (
    # 15 LiDAR-free columns active on 100% of the 5,167,373-px footprint (indices 0..14)
    "h33_hw_fw_cond_jump_400m",
    "h33_hw_fw_cond_jump_800m",
    "h33_fw_hw_grav_throw_600m",
    "h33_fw_hw_elev_throw_600m",
    "h33_asymmetric_graben_conduit",
    "h33_destripe_rtp_tilt_hgm",
    "h33_tmi_up150_tilt_hgm",
    "h33_mag_crustal_persistence",
    "h33_isograv_flexure_crest",
    "h33_k_metasom_thk_depletion_edge",
    "h33_hydro_silica_vent_corridor",
    "h33_walker_transtension_index",
    "h33_piedmont_profile_concavity",
    "h33_canyon_mouth_knick_impulse",
    "h33_canyon_mouth_collinearity_1200m",
    # 4 LiDAR-regime columns active on 75.37% valid 1 m LiDAR footprint (indices 15..18)
    "h33_lidar_slope_norm_scarp",
    "h33_lidar_cross_contour_nis",
    "h33_lidar_wash_bridge_800m",
    "h33_lahontan_shoreline_indicator",
)

H33_S2_FEATURE_NAMES: tuple[str, ...] = (
    "s2_p_synth",
    "s2_p_sub",
    "s2_corrob_geom",
    "s2_frangi_s12",
    "s2_frangi_s28",
    "s2_axial_crest",
    "s2_line16_max_500m",
    "s2_line16_ortho_aniso_500m",
    "s2_line16_max_1100m",
    "s2_line16_ortho_aniso_1100m",
    "s2_halo_diff_700m",
)

BASE_NON_LIDAR_IDX: tuple[int, ...] = tuple(list(range(18)) + [30, 31])  # 20 non-LiDAR base cols
H33_NON_LIDAR_IDX: tuple[int, ...] = tuple(range(15))  # 15 non-LiDAR H33 cols
VENTS_ALLOWED_COLS: tuple[str, ...] = ("row", "col")

BUFFER_PX: float = 6.0
LIDAR_GAP_QUANTILE_SCALE: float = 0.86
CELF_GAMMA: float = 1.50
CELF_MIN_SEP_PX: float = 3.00

H33_2_EXTRA_NAMES: tuple[str, ...] = (
    # 3 LiDAR-free multi-elevation magnetic dip/verticality & Walker Lane seismic/redox cols (0..2)
    "h332_mag_up150_downdip_shift",
    "h332_mag_vertical_strike_slip",
    "h332_wl_seis_redox_corridor",
    # 1 deconfounded 1 m LiDAR local prominence ridge col (3)
    "h332_lidar_prominence_ridge",
)

CELF_GAMMA_H33_2: float = 1.30
CELF_MIN_SEP_PX_H33_2: float = 3.45


def _zpos_iqr(arr: np.ndarray, foot: np.ndarray) -> np.ndarray:
    v = arr[foot]
    med = float(np.median(v))
    iqr = float(np.percentile(v, 75) - np.percentile(v, 25))
    scale = max(iqr / 1.349, 1e-6)
    out = np.clip((arr - med) / scale, 0.0, 12.0).astype(np.float32)
    out[~foot] = 0.0
    return out


def _bilinear_sample_strip(
    field: np.ndarray, yy: np.ndarray, xx: np.ndarray
) -> np.ndarray:
    """Fast pure-NumPy clamped bilinear sample on a strip of float32 coordinates."""
    H, W = field.shape
    yc = np.clip(yy, 0.0, np.float32(H - 1.0001))
    xc = np.clip(xx, 0.0, np.float32(W - 1.0001))
    y0 = np.floor(yc).astype(np.int32)
    x0 = np.floor(xc).astype(np.int32)
    y1 = np.minimum(y0 + 1, H - 1)
    x1 = np.minimum(x0 + 1, W - 1)
    wy = (yc - y0).astype(np.float32)
    wx = (xc - x0).astype(np.float32)
    v00 = field[y0, x0]
    v01 = field[y0, x1]
    v10 = field[y1, x0]
    v11 = field[y1, x1]
    top = v00 * (np.float32(1.0) - wx) + v01 * wx
    bot = v10 * (np.float32(1.0) - wx) + v11 * wx
    return (top * (np.float32(1.0) - wy) + bot * wy).astype(np.float32)


def directional_asymmetric_diff(
    field: np.ndarray,
    uy: np.ndarray,
    ux: np.ndarray,
    step_px: float,
    *,
    strip_rows: int = 512,
) -> np.ndarray:
    """Compute [field(x + step*u) - field(x - step*u)]_+ in memory-bounded row strips."""
    H, W = field.shape
    f32 = field.astype(np.float32, copy=False)
    out = np.empty((H, W), dtype=np.float32)
    step = np.float32(step_px)
    xs_base = np.arange(W, dtype=np.float32)[None, :]
    for r0 in range(0, H, strip_rows):
        r1 = min(r0 + strip_rows, H)
        ys_base = np.arange(r0, r1, dtype=np.float32)[:, None]
        dy = step * uy[r0:r1]
        dx = step * ux[r0:r1]
        vp = _bilinear_sample_strip(f32, ys_base + dy, xs_base + dx)
        vm = _bilinear_sample_strip(f32, ys_base - dy, xs_base - dx)
        out[r0:r1] = np.maximum(np.float32(0.0), vp - vm)
    return out


def along_vector_integral(
    field: np.ndarray,
    ty: np.ndarray,
    tx: np.ndarray,
    offsets_px: tuple[float, ...],
    *,
    strip_rows: int = 512,
) -> np.ndarray:
    """Integrate `field(x + s * t_hat(x))` across `offsets_px` in memory-bounded row strips."""
    H, W = field.shape
    f32 = field.astype(np.float32, copy=False)
    out = np.zeros((H, W), dtype=np.float32)
    inv_k = np.float32(1.0 / max(len(offsets_px), 1))
    xs_base = np.arange(W, dtype=np.float32)[None, :]
    for r0 in range(0, H, strip_rows):
        r1 = min(r0 + strip_rows, H)
        ys_base = np.arange(r0, r1, dtype=np.float32)[:, None]
        ty_s = ty[r0:r1]
        tx_s = tx[r0:r1]
        acc = np.zeros((r1 - r0, W), dtype=np.float32)
        for s in offsets_px:
            sf = np.float32(s)
            acc += _bilinear_sample_strip(f32, ys_base + sf * ty_s, xs_base + sf * tx_s)
        out[r0:r1] = acc * inv_k
    return out


def tilt_derivative_hgm(field: np.ndarray, sigma_xy: float = 1.8) -> np.ndarray:
    """Horizontal gradient magnitude of Miller-Singh (1994) tilt derivative (scale-invariant edge)."""
    sm = gaussian_filter(field.astype(np.float32, copy=False), sigma=sigma_xy, mode="nearest")
    gy = gaussian_filter(sm, sigma=1.0, order=(1, 0), mode="nearest")
    gx = gaussian_filter(sm, sigma=1.0, order=(0, 1), mode="nearest")
    hgm = np.hypot(gy, gx)
    up = gaussian_filter(sm, sigma=2.6, mode="nearest")
    vdr = sm - up
    med_hgm = float(np.median(hgm))
    med_vdr = float(np.median(np.abs(vdr))) + 1e-8
    tilt = np.arctan2(vdr * np.float32(med_hgm / med_vdr), hgm + np.float32(1e-7)).astype(np.float32)
    return gaussian_gradient_magnitude(tilt, sigma=1.1, mode="nearest").astype(np.float32)


def _read_u8_band_clean(tif_path: Path, band: int, expected_desc: str, foot: np.ndarray) -> np.ndarray:
    with rasterio.open(tif_path) as ds:
        desc = (ds.descriptions[band - 1] or "").strip()
        if desc and desc != expected_desc:
            raise RuntimeError(f"{tif_path.name} band {band} mismatch: {desc!r} != {expected_desc!r}")
        raw = ds.read(band).astype(np.float32)
    valid = foot & (raw > 0) & np.isfinite(raw)
    return h29._nearest_fill(raw, valid)


def _sharp_hydro_vent_field(
    wellspring_path: Path,
    vents_path: Path,
    shape: tuple[int, int],
    foot: np.ndarray,
) -> np.ndarray:
    """Label-free 900 m silica/cation geothermometer excess + 1.4 km volcanic vent density."""
    df_w = pd.read_csv(wellspring_path, usecols=list(h29.WELLSPRING_ALLOWED_COLS))
    assert "dist_known_fault_px" not in df_w.columns
    H, W = shape
    rows = pd.to_numeric(df_w["row"], errors="coerce").to_numpy()
    cols = pd.to_numeric(df_w["col"], errors="coerce").to_numpy()
    ok = np.isfinite(rows) & np.isfinite(cols) & (rows >= 0) & (rows < H) & (cols >= 0) & (cols < W)
    df_w = df_w.loc[ok]
    ri = df_w["row"].astype(np.int32).to_numpy()
    ci = df_w["col"].astype(np.int32).to_numpy()

    def _cln(c: str) -> np.ndarray:
        v = pd.to_numeric(df_w[c], errors="coerce").to_numpy(dtype=np.float64, copy=True)
        v[(v < 5.0) | (v > 330.0)] = np.nan
        return v

    t_max = np.fmax(
        np.fmax(_cln("geothermquartz_c"), _cln("geothermchalc_c")),
        np.fmax(_cln("geothermcat_c"), _cln("temp_c")),
    )
    hot_excess = np.maximum(0.0, np.nan_to_num(t_max, nan=0.0) - 50.0).astype(np.float32)
    val_m = np.isfinite(t_max)

    cell_ex = np.zeros((H, W), dtype=np.float32)
    cell_wt = np.zeros((H, W), dtype=np.float32)
    np.maximum.at(cell_ex, (ri[val_m], ci[val_m]), hot_excess[val_m])
    cell_wt[ri[val_m], ci[val_m]] = 1.0
    num = gaussian_filter(cell_ex * cell_wt, sigma=9.0, mode="constant", cval=0.0)
    den = gaussian_filter(cell_wt, sigma=9.0, mode="constant", cval=0.0)
    nw_hot = (num / (den + np.float32(0.08))).astype(np.float32)
    del cell_ex, cell_wt, num, den

    df_v = pd.read_csv(vents_path, usecols=list(VENTS_ALLOWED_COLS))
    assert "dist_known_fault_px" not in df_v.columns
    vr = pd.to_numeric(df_v["row"], errors="coerce").to_numpy()
    vc = pd.to_numeric(df_v["col"], errors="coerce").to_numpy()
    vok = np.isfinite(vr) & np.isfinite(vc) & (vr >= 0) & (vr < H) & (vc >= 0) & (vc < W)
    vent_imp = np.zeros((H, W), dtype=np.float32)
    vent_imp[vr[vok].astype(np.int32), vc[vok].astype(np.int32)] = 1.0
    vent_kde = gaussian_filter(vent_imp, sigma=14.0, mode="constant", cval=0.0)
    vmax = float(vent_kde[foot].max()) if foot.any() else 1.0
    if vmax > 1e-9:
        vent_kde /= np.float32(vmax)
    out = _zpos_iqr(nw_hot, foot) + np.float32(1.5) * vent_kde.astype(np.float32)
    out[~foot] = 0.0
    return out.astype(np.float32)


def build_h33_feature_matrix(
    *,
    cache_path: Path | None = None,
    force: bool = False,
    tf_path: Path = paths.TRAINING,
    lidar_path: Path = paths.LIDAR,
    ext_path: Path = paths.EXTENSIONS,
    wellspring_path: Path = paths.WELLSPRING,
    vents_path: Path = paths.VOLCANIC_VENTS,
    template_path: Path = paths.TEMPLATE,
) -> np.ndarray:
    """Compute or load the 19-column float32 H33 physical feature matrix on footprint pixels."""
    if cache_path is not None and cache_path.exists() and not force:
        arr = np.load(cache_path, mmap_mode="r")
        if arr.ndim == 2 and arr.shape[1] == len(H33_FEATURE_NAMES):
            return arr

    with rasterio.open(template_path) as t:
        foot = np.isfinite(t.read(1))
    H, W = foot.shape
    n_foot = int(foot.sum())

    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        out = np.lib.format.open_memmap(
            cache_path, mode="w+", dtype=np.float32, shape=(n_foot, len(H33_FEATURE_NAMES))
        )
    else:
        out = np.empty((n_foot, len(H33_FEATURE_NAMES)), dtype=np.float32)

    tf = h29._read_tf_band_by_desc(tf_path, foot)
    # Read det_local_relief and ieq_n100a15 directly from prepared/features.npy (already verified & band-6-free)
    pnames: list[str] = json.loads(paths.PREPARED_META.read_text())["names"]
    X_prep = np.load(paths.PREPARED_FEATURES, mmap_mode="r")

    def _prep_grid(col_name: str) -> np.ndarray:
        g = np.full((H, W), np.nan, dtype=np.float32)
        g[foot] = X_prep[:, pnames.index(col_name)]
        return h29._nearest_fill(g, foot & np.isfinite(g))

    # --- Group A (0..4): Asymmetric Half-Graben Dip-Vector Coupling ---
    dbase = h29._nearest_fill(*tf["depth_to_base_surf"])
    db_sm = gaussian_filter(dbase, sigma=4.0, mode="nearest")
    du_y = gaussian_filter(db_sm, sigma=1.0, order=(1, 0), mode="nearest")
    du_x = gaussian_filter(db_sm, sigma=1.0, order=(0, 1), mode="nearest")
    unorm = np.hypot(du_y, du_x) + np.float32(1e-6)
    uy = (du_y / unorm).astype(np.float32)
    ux = (du_x / unorm).astype(np.float32)
    db_wall = _zpos_iqr(gaussian_gradient_magnitude(dbase, sigma=3.0, mode="nearest"), foot)
    del dbase, db_sm, du_y, du_x, unorm

    cond = h29._nearest_fill(*tf["cond_surf"])
    cj4 = directional_asymmetric_diff(cond, uy, ux, step_px=4.0)
    cj8 = directional_asymmetric_diff(cond, uy, ux, step_px=8.0)
    del cond
    out[:, 0] = cj4[foot]
    out[:, 1] = cj8[foot]

    grav = h29.destripe_ew_geodawn(*tf["iso_grav_anom"])
    # Footwall (-u) dense horst minus hanging-wall (+u) low-density basin fill:
    gt6 = directional_asymmetric_diff(grav, -uy, -ux, step_px=6.0) * (np.float32(0.35) + db_wall)
    out[:, 2] = gt6[foot]

    elev = h29._nearest_fill(*tf["det_elev"])
    et6 = directional_asymmetric_diff(elev, -uy, -ux, step_px=6.0) * (np.float32(0.35) + db_wall)
    out[:, 3] = et6[foot]
    del uy, ux

    z_cj8 = _zpos_iqr(cj8, foot)
    z_gt6 = _zpos_iqr(gt6, foot)
    ag_cond = np.sqrt(z_cj8 * z_gt6).astype(np.float32)
    out[:, 4] = ag_cond[foot]
    del cj4, cj8, gt6, et6, z_cj8, z_gt6, ag_cond
    gc.collect()

    # --- Group B (5..10): Upward-Continued Magnetic Persistence, Flexure, ThK Alteration & Hydro-Vent ---
    rtp_ds = h29.destripe_ew_geodawn(*tf["rtp"])
    rtp_thgm = tilt_derivative_hgm(rtp_ds, sigma_xy=1.8)
    del rtp_ds
    out[:, 5] = rtp_thgm[foot]

    tmi_up150_raw = _read_u8_band_clean(ext_path, 4, "TMI_up150", foot)
    tmi_up150_ds = h29.destripe_ew_geodawn(tmi_up150_raw, foot)
    del tmi_up150_raw
    up150_thgm = tilt_derivative_hgm(tmi_up150_ds, sigma_xy=2.2)
    del tmi_up150_ds
    out[:, 6] = up150_thgm[foot]

    mag_persist = np.sqrt(_zpos_iqr(rtp_thgm, foot) * _zpos_iqr(up150_thgm, foot)).astype(np.float32)
    out[:, 7] = mag_persist[foot]
    del rtp_thgm, up150_thgm

    grav_crest = h31.blakely_ridge_crest(grav, sigma_grad=2.0, sigma_curv=1.4)
    del grav
    flex_crest = (_zpos_iqr(grav_crest, foot) + np.float32(0.5) * db_wall).astype(np.float32)
    out[:, 8] = flex_crest[foot]
    del grav_crest

    struct_wall = np.maximum(mag_persist, flex_crest)
    del mag_persist, flex_crest, db_wall

    thk_raw = _read_u8_band_clean(ext_path, 1, "ThK", foot)
    thk_ds = h29.destripe_ew_geodawn(thk_raw, foot)
    del thk_raw
    # Potassic alteration lowers Th/K locally along permeable fault conduits:
    thk_depl = gaussian_filter(thk_ds, sigma=12.0, mode="nearest") - gaussian_filter(
        thk_ds, sigma=2.0, mode="nearest"
    )
    del thk_ds
    k_meta = (_zpos_iqr(thk_depl, foot) * (np.float32(0.30) + struct_wall)).astype(np.float32)
    out[:, 9] = k_meta[foot]
    del thk_depl, k_meta

    hv_field = _sharp_hydro_vent_field(wellspring_path, vents_path, (H, W), foot)
    hv_corr = (hv_field * (np.float32(0.35) + struct_wall)).astype(np.float32)
    out[:, 10] = hv_corr[foot]
    del hv_field, hv_corr, struct_wall
    gc.collect()

    # --- Group C (11): Walker Lane Transtensional Principal Strain & Seismicity ---
    shr = h29._nearest_fill(*tf["geod_shearrate"])
    dil_pos = np.maximum(0.0, h29._nearest_fill(*tf["geod_dilaterate"]))
    ieq = np.log1p(np.maximum(0.0, _prep_grid("ieq_n100a15")))
    transt = (
        np.hypot(_zpos_iqr(shr, foot), _zpos_iqr(dil_pos, foot))
        * (np.float32(1.0) + np.float32(0.5) * _zpos_iqr(ieq, foot))
    ).astype(np.float32)
    out[:, 11] = transt[foot]
    del shr, dil_pos, ieq, transt
    tf.clear()
    gc.collect()

    # --- Group D (12..14): Canyon-Mouth Knickpoint & Fan-Apex Collinearity (H29-5) ---
    elev_reg = gaussian_filter(elev, sigma=10.0, mode="nearest")
    ny = gaussian_filter(elev_reg, sigma=1.0, order=(1, 0), mode="nearest")
    nx = gaussian_filter(elev_reg, sigma=1.0, order=(0, 1), mode="nearest")
    nnorm = np.hypot(ny, nx) + np.float32(1e-6)
    ny = (ny / nnorm).astype(np.float32)
    nx = (nx / nnorm).astype(np.float32)
    ty = (-nx).astype(np.float32)
    tx = ny.astype(np.float32)
    del elev_reg, nnorm

    elev_s3 = gaussian_filter(elev, sigma=3.0, mode="nearest")
    hyy = gaussian_filter(elev_s3, sigma=1.0, order=(2, 0), mode="nearest")
    hxx = gaussian_filter(elev_s3, sigma=1.0, order=(0, 2), mode="nearest")
    hyx = gaussian_filter(elev_s3, sigma=1.0, order=(1, 1), mode="nearest")
    d2_nn = ny * ny * hyy + np.float32(2.0) * ny * nx * hyx + nx * nx * hxx
    prof_concav = np.maximum(np.float32(0.0), d2_nn).astype(np.float32)
    del hyy, hxx, hyx, d2_nn, ny, nx
    out[:, 12] = prof_concav[foot]

    loc_rel_abs = np.abs(_prep_grid("det_local_relief"))
    incis_anom = loc_rel_abs - gaussian_filter(loc_rel_abs, sigma=6.0, mode="nearest")
    del loc_rel_abs
    mouth_imp = (_zpos_iqr(incis_anom, foot) * _zpos_iqr(prof_concav, foot)).astype(np.float32)
    del incis_anom, prof_concav
    out[:, 13] = mouth_imp[foot]

    collin_1200 = along_vector_integral(
        mouth_imp, ty, tx, offsets_px=(-12.0, -10.0, -8.0, -6.0, -4.0, -2.0, 0.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0)
    )
    out[:, 14] = collin_1200[foot]
    del mouth_imp, collin_1200, ty, tx
    gc.collect()

    # --- Group E (15..18): Slope-Normalized Cross-Contour 1 m LiDAR, Wash Bridge & Lahontan Bench ---
    reg_slope = _zpos_iqr(gaussian_gradient_magnitude(elev_s3, sigma=1.5, mode="nearest"), foot)
    del elev_s3
    with rasterio.open(lidar_path) as ls:
        lid_valid = foot & (ls.read(12) > 0)
        ex_m = ls.read(1).astype(np.float32) / np.float32(255.0)
        step_m = ls.read(3).astype(np.float32) / np.float32(255.0)
        lappos_m = ls.read(5).astype(np.float32) / np.float32(255.0)
        down_m = ls.read(6).astype(np.float32) / np.float32(255.0)
        up_m = ls.read(7).astype(np.float32) / np.float32(255.0)
        c2s = ls.read(10).astype(np.float32) / np.float32(127.5) - np.float32(1.0)
        s2s = ls.read(11).astype(np.float32) / np.float32(127.5) - np.float32(1.0)

    raw_scarp = (
        np.float32(0.40) * step_m
        + np.float32(0.25) * (up_m + down_m)
        + np.float32(0.20) * lappos_m
        + np.float32(0.15) * ex_m
    )
    del ex_m, step_m, lappos_m, down_m, up_m
    norm_scarp = (raw_scarp / (np.float32(1.0) + np.float32(0.5) * reg_slope)).astype(np.float32)
    del raw_scarp, reg_slope

    obliq_sin2 = h31.contour_obliquity_sin2(elev, c2s, s2s, lid_valid, sigma_dem=2.5)
    nis_scarp = (norm_scarp * (np.float32(0.20) + np.float32(0.80) * obliq_sin2)).astype(np.float32)
    nis_clean = np.where(lid_valid, nis_scarp, np.float32(0.0)).astype(np.float32)

    # Scarp unit tangent from half-angle of (cos 2theta_s, sin 2theta_s) in (+col, +row) convention:
    theta_s = np.float32(0.5) * np.arctan2(
        np.where(lid_valid, s2s, np.float32(0.0)),
        np.where(lid_valid, c2s, np.float32(1.0)),
    )
    del c2s, s2s
    sty = np.sin(theta_s).astype(np.float32)
    stx = np.cos(theta_s).astype(np.float32)
    del theta_s
    wash_bridge = along_vector_integral(
        nis_clean, sty, stx, offsets_px=(-8.0, -6.0, -4.0, -2.0, 0.0, 2.0, 4.0, 6.0, 8.0)
    )
    del sty, stx, nis_clean

    # Explicit Pleistocene pluvial shoreline bench indicator (contour-parallel scarp inside basin floor det_elev < 0):
    shore_ind = (
        norm_scarp * (np.float32(1.0) - obliq_sin2) * (elev < np.float32(0.0)).astype(np.float32)
    ).astype(np.float32)
    del elev, obliq_sin2

    for col_j, arr_l in ((15, norm_scarp), (16, nis_scarp), (17, wash_bridge), (18, shore_ind)):
        g_nan = np.where(lid_valid, arr_l, np.nan).astype(np.float32)
        out[:, col_j] = g_nan[foot]
    del norm_scarp, nis_scarp, wash_bridge, shore_ind, lid_valid
    gc.collect()

    if isinstance(out, np.memmap):
        out.flush()
        return np.load(cache_path, mmap_mode="r")
    return out


def line16_max_and_ortho_aniso(
    prob: np.ndarray, half_len: int = 5
) -> tuple[np.ndarray, np.ndarray]:
    """Memory-lean 16-azimuth (`11.25 deg`) line-integral max & orthogonal cross-strike anisotropy.

    Evaluates the 8 orthogonal pairs `(theta_k, theta_k + pi/2)` for `k = 0..7` in one pass using
    only 4 grid-sized float32 buffers, returning `(L(theta*), [L(theta*) - L(theta* + pi/2)]_+)`.
    On isotropic 2-D blobs, `L(theta*) == L(theta* + pi/2)` so anisotropy cancels to 0; on 1-D
    fault strands (including steep N11-34E Basin-and-Range strikes), anisotropy approaches `L(theta*)`.
    """
    H, W = prob.shape
    pad = int(half_len)
    p_pad = np.pad(prob.astype(np.float32, copy=False), pad, mode="edge")
    t = np.arange(-half_len, half_len + 1, dtype=np.float64)
    inv_n = np.float32(1.0 / len(t))

    best_max = np.full((H, W), -np.inf, dtype=np.float32)
    best_aniso = np.zeros((H, W), dtype=np.float32)
    acc_a = np.empty((H, W), dtype=np.float32)
    acc_b = np.empty((H, W), dtype=np.float32)

    for k in range(8):
        th_a = k * (np.pi / 16.0)
        th_b = th_a + 0.5 * np.pi
        dya = np.rint(t * np.sin(th_a)).astype(np.int32)
        dxa = np.rint(t * np.cos(th_a)).astype(np.int32)
        dyb = np.rint(t * np.sin(th_b)).astype(np.int32)
        dxb = np.rint(t * np.cos(th_b)).astype(np.int32)

        acc_a.fill(0.0)
        for dy, dx in zip(dya.tolist(), dxa.tolist()):
            acc_a += p_pad[pad + dy : pad + dy + H, pad + dx : pad + dx + W]
        acc_a *= inv_n

        acc_b.fill(0.0)
        for dy, dx in zip(dyb.tolist(), dxb.tolist()):
            acc_b += p_pad[pad + dy : pad + dy + H, pad + dx : pad + dx + W]
        acc_b *= inv_n

        win_a = acc_a > best_max
        if win_a.any():
            best_max[win_a] = acc_a[win_a]
            best_aniso[win_a] = np.maximum(np.float32(0.0), acc_a[win_a] - acc_b[win_a])

        win_b = acc_b > best_max
        if win_b.any():
            best_max[win_b] = acc_b[win_b]
            best_aniso[win_b] = np.maximum(np.float32(0.0), acc_b[win_b] - acc_a[win_b])

    del p_pad, acc_a, acc_b
    return best_max, best_aniso


def synthesize_regimes(
    p_full_grid: np.ndarray,
    p_sub_grid: np.ndarray,
    domain_mask: np.ndarray,
    lidar_valid: np.ndarray,
    gap_scale: float = LIDAR_GAP_QUANTILE_SCALE,
) -> tuple[np.ndarray, np.ndarray]:
    """Synthesize `M_Full` (fit strictly on `lidar_valid`) + `M_Sub` and return `(p_synth, p_corrob)`."""
    p_synth = np.zeros_like(p_full_grid, dtype=np.float32)
    p_corrob = np.zeros_like(p_full_grid, dtype=np.float32)
    lv_dom = domain_mask & lidar_valid
    gap_dom = domain_mask & (~lidar_valid)
    if lv_dom.any():
        pf = np.clip(p_full_grid[lv_dom], 0.0, 1.0)
        ps = np.clip(p_sub_grid[lv_dom], 0.0, 1.0)
        geom = np.sqrt(pf * ps).astype(np.float32)
        comb = np.float32(0.62) * pf + np.float32(0.22) * ps + np.float32(0.16) * geom
        p_synth[lv_dom] = np.clip(comb, 0.0, 1.0).astype(np.float32)
        p_corrob[lv_dom] = geom
    if gap_dom.any():
        ref_s = p_synth[lv_dom] if lv_dom.any() else np.clip(p_sub_grid[gap_dom], 0.0, 1.0)
        p_synth[gap_dom] = h31.quantile_calibrate_gap(p_sub_grid[gap_dom], ref_s, scale=gap_scale)
        ref_c = p_corrob[lv_dom] if lv_dom.any() else np.clip(p_sub_grid[gap_dom], 0.0, 1.0)
        p_corrob[gap_dom] = h31.quantile_calibrate_gap(p_sub_grid[gap_dom], ref_c, scale=gap_scale)
    return p_synth, p_corrob


def stage2_manifold_features(
    p_synth: np.ndarray,
    p_sub: np.ndarray,
    p_corrob: np.ndarray,
    valid_mask: np.ndarray,
) -> np.ndarray:
    """11-channel multi-kilometer 16-azimuth orthogonal-Radon & vesselness matrix on `valid_mask`."""
    n_v = int(valid_mask.sum())
    out = np.empty((n_v, len(H33_S2_FEATURE_NAMES)), dtype=np.float32)
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
    ps_c = np.where(vm, p_synth[sl], np.float32(0.0)).astype(np.float32)
    out[:, 0] = ps_c[vm]
    out[:, 1] = np.where(vm, p_sub[sl], np.float32(0.0))[vm].astype(np.float32)
    out[:, 2] = np.where(vm, p_corrob[sl], np.float32(0.0))[vm].astype(np.float32)

    for col_i, sig in ((3, 1.2), (4, 2.8)):
        fr = h29._frangi_2d(ps_c, sigma=sig, valid_mask=vm)
        out[:, col_i] = fr[vm]
        del fr

    crest = h31.axial_crest_measure(ps_c, vm, sigma=1.2)
    out[:, 5] = crest[vm]
    del crest

    l5, a5 = line16_max_and_ortho_aniso(ps_c, half_len=5)
    out[:, 6] = l5[vm]
    out[:, 7] = a5[vm]
    del l5, a5

    l11, a11 = line16_max_and_ortho_aniso(ps_c, half_len=11)
    out[:, 8] = l11[vm]
    out[:, 9] = a11[vm]
    del l11, a11

    num7 = gaussian_filter(ps_c, sigma=7.0, mode="constant", cval=0.0)
    den7 = gaussian_filter(vm.astype(np.float32), sigma=7.0, mode="constant", cval=0.0)
    bg7 = np.where(den7 > 1e-4, num7 / np.maximum(den7, 1e-4), 0.0).astype(np.float32)
    del num7, den7
    out[:, 10] = (ps_c[vm] - bg7[vm]).astype(np.float32)
    del bg7, ps_c, vm
    gc.collect()
    return out


def _assemble_h33_rows(
    idx: np.ndarray,
    base_X: np.ndarray,
    sub15_X: np.ndarray,
    h33_X: np.ndarray,
    *,
    mode: str,
    extra_s2: np.ndarray | None = None,
) -> np.ndarray:
    """Build compact float32 slice for `M_Sub` (`50` cols) or `M_Full` (`66` cols) (+ optional Stage-2)."""
    n = int(idx.size)
    extra_c = 0 if extra_s2 is None else int(extra_s2.shape[1])
    if mode == "sub":
        out = np.empty((n, 20 + 15 + 15 + extra_c), dtype=np.float32)
        out[:, 0:20] = base_X[idx][:, BASE_NON_LIDAR_IDX]
        out[:, 20:35] = sub15_X[idx]
        out[:, 35:50] = h33_X[idx][:, H33_NON_LIDAR_IDX]
        if extra_s2 is not None:
            out[:, 50:] = extra_s2
        return out
    if mode == "full":
        out = np.empty((n, 32 + 15 + 19 + extra_c), dtype=np.float32)
        out[:, 0:32] = base_X[idx]
        out[:, 32:47] = sub15_X[idx]
        out[:, 47:66] = h33_X[idx]
        if extra_s2 is not None:
            out[:, 66:] = extra_s2
        return out
    raise ValueError(f"Unknown mode: {mode}")


def _predict_h33_chunked(
    clf: HistGradientBoostingClassifier,
    idx: np.ndarray,
    base_X: np.ndarray,
    sub15_X: np.ndarray,
    h33_X: np.ndarray,
    *,
    mode: str,
    extra_s2: np.ndarray | None = None,
    chunk: int = 200_000,
) -> np.ndarray:
    out = np.empty(idx.size, dtype=np.float32)
    if idx.size == 0:
        return out
    for s in range(0, idx.size, chunk):
        sl = idx[s : s + chunk]
        s2_sl = None if extra_s2 is None else extra_s2[s : s + chunk]
        X_sl = _assemble_h33_rows(sl, base_X, sub15_X, h33_X, mode=mode, extra_s2=s2_sl)
        out[s : s + chunk] = clf.predict_proba(X_sl)[:, 1].astype(np.float32)
        del X_sl
    return out


def _sample_pos_neg(
    mask_bool: np.ndarray,
    y_bool: np.ndarray,
    max_neg: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    pos_idx = np.flatnonzero(mask_bool & y_bool)
    neg_all = np.flatnonzero(mask_bool & (~y_bool))
    neg_idx = (
        np.sort(rng.choice(neg_all, size=max_neg, replace=False))
        if neg_all.size > max_neg
        else neg_all
    )
    tr_idx = np.concatenate([pos_idx, neg_idx])
    y_tr = np.r_[np.ones(pos_idx.size, dtype=np.int8), np.zeros(neg_idx.size, dtype=np.int8)]
    return tr_idx, y_tr


def fit_predict_h33_dual_regime_oof(
    base_X: np.ndarray,
    sub15_X: np.ndarray,
    h33_X: np.ndarray,
    labels: np.ndarray,
    foot: np.ndarray,
    lidar_valid: np.ndarray,
    *,
    fold_masks: list[np.ndarray] | None = None,
    buffer_px: float = BUFFER_PX,
    max_neg_s1: int = 340_000,
    max_neg_s2: int = 320_000,
    s1_max_iter: int = 240,
    s2_max_iter: int = 160,
    seed: int = 600,
    cache_dir: Path | None = None,
    cache_tag: str = "quad",
    mmap_paths: tuple[Path, ...] = (),
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """End-to-end dual-regime (`M_Sub` + `lidar_valid`-only `M_Full`) 2-stage nested spatial cross-fit.

    Every pixel in fold k is predicted strictly out-of-fold (> buffer_px = 600 m guard).
    Stage 1 AND Stage 2 train `M_Full` exclusively on `lidar_valid` pixels (eliminating `NaN`-LiDAR
    tree splits) and `M_Sub` on 100% of buffered training pixels, aligning inner 1-pair marginal
    quantiles to outer 3-pair marginal quantiles before Stage-2 spatial manifold extraction.
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
    lid_foot = lidar_valid[foot]
    fold_id_foot = np.full(int(foot.sum()), -1, dtype=np.int8)
    for k, fm in enumerate(fold_masks):
        fold_id_foot[fm[foot]] = k

    pair_preds_sub: dict[tuple[int, int], dict[int, np.ndarray]] = {}
    pair_preds_full: dict[tuple[int, int], dict[int, np.ndarray]] = {}

    for i, j in combinations(range(4), 2):
        rem = [k for k in range(4) if k not in (i, j)]
        ckpt_p = cache_dir / f"ckpt_h33_{cache_tag}_pair_{i}_{j}.npz" if cache_dir is not None else None
        if ckpt_p is not None and ckpt_p.exists():
            with np.load(ckpt_p) as z:
                pair_preds_sub[(i, j)] = {k: z[f"sub_{k}"] for k in rem}
                pair_preds_full[(i, j)] = {k: z[f"full_{k}"] for k in rem}
            print(f"    loaded cached H33 stage1 pair ({i},{j})", flush=True)
            continue

        union_ij = fold_masks[i] | fold_masks[j]
        comp_ij = foot & (~union_ij)
        guard_tr = distance_transform_edt(~comp_ij) > buffer_px
        tr_foot = (union_ij & guard_tr)[foot]
        del union_ij, comp_ij, guard_tr

        rng = np.random.default_rng(seed * 1000 + i * 10 + j)
        tr_sub_idx, y_tr_sub = _sample_pos_neg(tr_foot, y_foot, max_neg_s1, rng)

        X_tr_sub = _assemble_h33_rows(tr_sub_idx, base_X, sub15_X, h33_X, mode="sub")
        clf_sub = HistGradientBoostingClassifier(
            max_iter=s1_max_iter,
            learning_rate=0.055,
            max_leaf_nodes=63,
            min_samples_leaf=90,
            max_features=0.72,
            l2_regularization=2.5,
            random_state=seed + i * 17 + j,
        )
        clf_sub.fit(X_tr_sub, y_tr_sub)
        del X_tr_sub, tr_sub_idx, y_tr_sub
        gc.collect()
        h31.drop_file_page_cache(*mmap_paths)

        # M_Full trained STRICTLY on lidar_valid buffered pixels (zero NaN LiDAR splits!)
        tr_full_idx, y_tr_full = _sample_pos_neg(tr_foot & lid_foot, y_foot, max_neg_s1, rng)
        del tr_foot
        X_tr_full = _assemble_h33_rows(tr_full_idx, base_X, sub15_X, h33_X, mode="full")
        clf_full = HistGradientBoostingClassifier(
            max_iter=s1_max_iter,
            learning_rate=0.055,
            max_leaf_nodes=63,
            min_samples_leaf=90,
            max_features=0.72,
            l2_regularization=2.5,
            random_state=seed + 50 + i * 17 + j,
        )
        clf_full.fit(X_tr_full, y_tr_full)
        del X_tr_full, tr_full_idx, y_tr_full
        gc.collect()
        h31.drop_file_page_cache(*mmap_paths)

        pair_preds_sub[(i, j)] = {}
        pair_preds_full[(i, j)] = {}
        save_dict: dict[str, np.ndarray] = {}
        for k in rem:
            k_idx = np.flatnonzero(fold_id_foot == k)
            pair_preds_sub[(i, j)][k] = _predict_h33_chunked(
                clf_sub, k_idx, base_X, sub15_X, h33_X, mode="sub"
            )
            # Only need M_Full predictions on lidar_valid pixels; store zeros on gap for compactness
            pf_k = np.zeros(k_idx.size, dtype=np.float32)
            lid_k_local = lid_foot[k_idx]
            if lid_k_local.any():
                pf_k[lid_k_local] = _predict_h33_chunked(
                    clf_full, k_idx[lid_k_local], base_X, sub15_X, h33_X, mode="full"
                )
            pair_preds_full[(i, j)][k] = pf_k
            save_dict[f"sub_{k}"] = pair_preds_sub[(i, j)][k]
            save_dict[f"full_{k}"] = pf_k
        if ckpt_p is not None:
            np.savez(ckpt_p, **save_dict)
        del clf_sub, clf_full, save_dict
        gc.collect()
        h31.drop_file_page_cache(*mmap_paths)
        print(f"    H33 stage1 pair ({i},{j}) done", flush=True)

    prob_sub_oof = np.zeros(foot.shape, dtype=np.float32)
    prob_full_oof = np.zeros(foot.shape, dtype=np.float32)
    prob_s1_oof = np.zeros(foot.shape, dtype=np.float32)
    prob_corrob_oof = np.zeros(foot.shape, dtype=np.float32)
    foot_flat_idx = np.flatnonzero(foot)

    for k in range(4):
        k_idx = np.flatnonzero(fold_id_foot == k)
        valid_pairs = [pair for pair in combinations(range(4), 2) if k not in pair]
        ps = sum(pair_preds_sub[pair][k] for pair in valid_pairs) / np.float32(3.0)
        pf = sum(pair_preds_full[pair][k] for pair in valid_pairs) / np.float32(3.0)
        prob_sub_oof.ravel()[foot_flat_idx[k_idx]] = ps
        prob_full_oof.ravel()[foot_flat_idx[k_idx]] = pf
        s1_k, corr_k = synthesize_regimes(prob_full_oof, prob_sub_oof, fold_masks[k], lidar_valid)
        prob_s1_oof[fold_masks[k]] = s1_k[fold_masks[k]]
        prob_corrob_oof[fold_masks[k]] = corr_k[fold_masks[k]]
        del s1_k, corr_k
    del prob_full_oof
    gc.collect()

    # Dual-Regime Stage-2 16-azimuth multi-km orthogonal Radon & vesselness refiner
    prob_s2_oof = np.zeros(foot.shape, dtype=np.float32)

    for f in range(4):
        te_global_idx = np.flatnonzero(fold_masks[f][foot])
        ckpt_s2 = cache_dir / f"ckpt_h33_{cache_tag}_s2_f{f}.npy" if cache_dir is not None else None
        if ckpt_s2 is not None and ckpt_s2.exists():
            prob_s2_oof.ravel()[foot_flat_idx[te_global_idx]] = np.load(ckpt_s2)
            print(f"    loaded cached H33 stage2 fold {f}", flush=True)
            continue

        test_mask = fold_masks[f]
        train_union = foot & (~test_mask)
        guard_f = distance_transform_edt(~test_mask) > buffer_px

        inner_sub = np.zeros(foot.shape, dtype=np.float32)
        inner_full = np.zeros(foot.shape, dtype=np.float32)
        rem_sectors = [m for m in range(4) if m != f]
        for m in rem_sectors:
            other_two = tuple(sorted(x for x in rem_sectors if x != m))
            m_idx = np.flatnonzero(fold_id_foot == m)
            inner_sub.ravel()[foot_flat_idx[m_idx]] = pair_preds_sub[other_two][m]
            inner_full.ravel()[foot_flat_idx[m_idx]] = pair_preds_full[other_two][m]

        inner_s1_raw, inner_corr_raw = synthesize_regimes(inner_full, inner_sub, train_union, lidar_valid)
        del inner_full

        # Unsupervised marginal quantile alignment of 1-pair inner surfaces to 3-pair outer test CDF
        inner_s1 = np.zeros_like(inner_s1_raw)
        inner_sub_al = np.zeros_like(inner_sub)
        inner_corr = np.zeros_like(inner_corr_raw)
        inner_s1[train_union] = h31.quantile_calibrate_gap(
            inner_s1_raw[train_union], prob_s1_oof[test_mask], scale=1.0
        )
        inner_sub_al[train_union] = h31.quantile_calibrate_gap(
            inner_sub[train_union], prob_sub_oof[test_mask], scale=1.0
        )
        inner_corr[train_union] = h31.quantile_calibrate_gap(
            inner_corr_raw[train_union], prob_corrob_oof[test_mask], scale=1.0
        )
        del inner_s1_raw, inner_sub, inner_corr_raw

        s2_train_mat = stage2_manifold_features(inner_s1, inner_sub_al, inner_corr, train_union)
        del inner_s1, inner_sub_al, inner_corr

        tu_foot = train_union[foot]
        s2_tu_guard = (train_union & guard_f)[foot][tu_foot]
        s2_tu_lid = lid_foot[tu_foot]
        del guard_f
        y_tu = labels[train_union]

        rng2 = np.random.default_rng(seed * 2000 + f)

        # Stage-2A: clf_s2_sub (pure LiDAR-free + 11 Stage-2 manifold cols across 100% of buffered train)
        take_sub, y_s2_sub = _sample_pos_neg(s2_tu_guard, y_tu, max_neg_s2, rng2)
        s2_take_sub = np.ascontiguousarray(s2_train_mat[take_sub], dtype=np.float32)
        tu_global_all = np.flatnonzero(tu_foot)
        X_s2_sub = _assemble_h33_rows(
            tu_global_all[take_sub], base_X, sub15_X, h33_X, mode="sub", extra_s2=s2_take_sub
        )
        del take_sub, s2_take_sub
        h31.drop_file_page_cache(*mmap_paths)

        clf_s2_sub = HistGradientBoostingClassifier(
            max_iter=s2_max_iter,
            learning_rate=0.05,
            max_leaf_nodes=35,
            min_samples_leaf=120,
            max_features=0.75,
            l2_regularization=4.0,
            random_state=seed + 500 + f,
        )
        clf_s2_sub.fit(X_s2_sub, y_s2_sub)
        del X_s2_sub, y_s2_sub
        gc.collect()

        # Stage-2B: clf_s2_full (strictly on lidar_valid buffered train — zero NaN LiDAR branch!)
        take_full, y_s2_full = _sample_pos_neg(s2_tu_guard & s2_tu_lid, y_tu, max_neg_s2, rng2)
        del s2_tu_guard, s2_tu_lid, y_tu, tu_foot
        s2_take_full = np.ascontiguousarray(s2_train_mat[take_full], dtype=np.float32)
        del s2_train_mat
        gc.collect()
        X_s2_full = _assemble_h33_rows(
            tu_global_all[take_full], base_X, sub15_X, h33_X, mode="full", extra_s2=s2_take_full
        )
        del tu_global_all, take_full, s2_take_full
        h31.drop_file_page_cache(*mmap_paths)

        clf_s2_full = HistGradientBoostingClassifier(
            max_iter=s2_max_iter,
            learning_rate=0.05,
            max_leaf_nodes=35,
            min_samples_leaf=120,
            max_features=0.75,
            l2_regularization=4.0,
            random_state=seed + 600 + f,
        )
        clf_s2_full.fit(X_s2_full, y_s2_full)
        del X_s2_full, y_s2_full
        gc.collect()

        # Predict on test_mask strictly out-of-fold and synthesize Stage-2 dual regimes:
        s2_test_mat = stage2_manifold_features(prob_s1_oof, prob_sub_oof, prob_corrob_oof, test_mask)
        preds_te_sub = _predict_h33_chunked(
            clf_s2_sub, te_global_idx, base_X, sub15_X, h33_X, mode="sub", extra_s2=s2_test_mat
        )
        preds_te_full = np.zeros(te_global_idx.size, dtype=np.float32)
        lid_te = lid_foot[te_global_idx]
        if lid_te.any():
            preds_te_full[lid_te] = _predict_h33_chunked(
                clf_s2_full,
                te_global_idx[lid_te],
                base_X,
                sub15_X,
                h33_X,
                mode="full",
                extra_s2=np.ascontiguousarray(s2_test_mat[lid_te], dtype=np.float32),
            )
        del clf_s2_sub, clf_s2_full, s2_test_mat

        g_sub_f = np.zeros(foot.shape, dtype=np.float32)
        g_full_f = np.zeros(foot.shape, dtype=np.float32)
        g_sub_f.ravel()[foot_flat_idx[te_global_idx]] = preds_te_sub
        g_full_f.ravel()[foot_flat_idx[te_global_idx]] = preds_te_full
        s2_syn_f, _ = synthesize_regimes(g_full_f, g_sub_f, test_mask, lidar_valid)
        preds_te = s2_syn_f[test_mask].astype(np.float32)
        del g_sub_f, g_full_f, s2_syn_f, preds_te_sub, preds_te_full

        if ckpt_s2 is not None:
            np.save(ckpt_s2, preds_te)
        prob_s2_oof.ravel()[foot_flat_idx[te_global_idx]] = preds_te
        del te_global_idx, preds_te
        gc.collect()
        h31.drop_file_page_cache(*mmap_paths)
        print(f"    H33 stage2 fold {f} done", flush=True)

    del pair_preds_sub, pair_preds_full, prob_corrob_oof
    gc.collect()
    return prob_sub_oof, prob_s1_oof, prob_s2_oof


def sharpen_1d_manifold_posterior(prob: np.ndarray, domain_mask: np.ndarray) -> np.ndarray:
    """Concentrate CELF kernel weight onto 1-D fault strands (`crest * ortho_aniso_500m`), suppressing 2-D blobs."""
    out = np.zeros_like(prob, dtype=np.float32)
    if not domain_mask.any():
        return out

    ys, xs = np.nonzero(domain_mask)
    pad = 16
    r0 = max(int(ys.min()) - pad, 0)
    r1 = min(int(ys.max()) + pad + 1, domain_mask.shape[0])
    c0 = max(int(xs.min()) - pad, 0)
    c1 = min(int(xs.max()) + pad + 1, domain_mask.shape[1])
    del ys, xs
    sl = (slice(r0, r1), slice(c0, c1))

    dm = domain_mask[sl]
    pc = np.where(dm, prob[sl], np.float32(0.0)).astype(np.float32)
    crest = h31.axial_crest_measure(pc, dm, sigma=1.0)
    _, aniso5 = line16_max_and_ortho_aniso(pc, half_len=5)
    score = crest[dm] * (np.float32(0.35) + np.float32(0.65) * aniso5[dm])
    del pc, crest, aniso5

    ranks = np.zeros(score.size, dtype=np.float32)
    pos = score > 0
    if pos.any():
        order = np.argsort(score[pos], kind="mergesort")
        r = np.empty(order.size, dtype=np.float32)
        r[order] = (np.arange(order.size, dtype=np.float32) + np.float32(0.5)) / np.float32(order.size)
        ranks[pos] = r

    out_sl = out[sl]
    out_sl[dm] = prob[sl][dm] * (np.float32(0.50) + np.float32(0.50) * ranks)
    return out


def emit_h33_celf(
    prob: np.ndarray,
    fold_domain: np.ndarray,
    known: np.ndarray,
    budget: int,
    *,
    b_excl: float = 2.0,
    gamma: float = CELF_GAMMA,
    min_sep_px: float = CELF_MIN_SEP_PX,
) -> np.ndarray:
    """Blind H33-1 1-D manifold-sharpened `min_sep_px = 3.00` 300 m CELF cover (zero hidden access)."""
    d_vis = distance_transform_edt(~known)
    dom = fold_domain & (~known)
    elig = dom & (d_vis > float(b_excl))
    p_man = sharpen_1d_manifold_posterior(prob, dom)
    return coverage_thin.weighted_celf_cover(
        p_man,
        elig,
        dom,
        budget=int(budget),
        radius_px=metric.RADIUS_PX,
        gamma=float(gamma),
        min_sep_px=float(min_sep_px),
    )


def build_h33_2_extra_matrix(
    h33_X: np.ndarray,
    *,
    cache_path: Path | None = None,
    force: bool = False,
    tf_path: Path = paths.TRAINING,
    ext_path: Path = paths.EXTENSIONS,
    lidar_path: Path = paths.LIDAR,
    template_path: Path = paths.TEMPLATE,
) -> np.ndarray:
    """Compute or load the 4-column float32 H33-2 multi-elevation magnetic & Walker Lane matrix."""
    if cache_path is not None and cache_path.exists() and not force:
        arr = np.load(cache_path, mmap_mode="r")
        if arr.ndim == 2 and arr.shape[1] == len(H33_2_EXTRA_NAMES):
            return arr

    with rasterio.open(template_path) as t:
        foot = np.isfinite(t.read(1))
    H, W = foot.shape
    n_foot = int(foot.sum())

    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        out = np.lib.format.open_memmap(
            cache_path, mode="w+", dtype=np.float32, shape=(n_foot, len(H33_2_EXTRA_NAMES))
        )
    else:
        out = np.empty((n_foot, len(H33_2_EXTRA_NAMES)), dtype=np.float32)

    tf = h29._read_tf_band_by_desc(tf_path, foot)
    pnames: list[str] = json.loads(paths.PREPARED_META.read_text())["names"]
    X_prep = np.load(paths.PREPARED_FEATURES, mmap_mode="r")

    def _prep_grid(col_name: str) -> np.ndarray:
        g = np.full((H, W), np.nan, dtype=np.float32)
        g[foot] = X_prep[:, pnames.index(col_name)]
        return h29._nearest_fill(g, foot & np.isfinite(g))

    dbase = h29._nearest_fill(*tf["depth_to_base_surf"])
    db_sm = gaussian_filter(dbase, sigma=4.0, mode="nearest")
    du_y = gaussian_filter(db_sm, sigma=1.0, order=(1, 0), mode="nearest")
    du_x = gaussian_filter(db_sm, sigma=1.0, order=(0, 1), mode="nearest")
    unorm = np.hypot(du_y, du_x) + np.float32(1e-6)
    uy = (du_y / unorm).astype(np.float32)
    ux = (du_x / unorm).astype(np.float32)
    del dbase, db_sm, du_y, du_x, unorm

    rtp_ds = h29.destripe_ew_geodawn(*tf["rtp"])
    hgm_rtp = _zpos_iqr(gaussian_gradient_magnitude(rtp_ds, sigma=1.8, mode="nearest"), foot)
    del rtp_ds

    up150_raw = _read_u8_band_clean(ext_path, 4, "TMI_up150", foot)
    up150_ds = h29.destripe_ew_geodawn(up150_raw, foot)
    del up150_raw
    hgm_up150 = _zpos_iqr(gaussian_gradient_magnitude(up150_ds, sigma=2.2, mode="nearest"), foot)
    del up150_ds

    # Col 0: Down-dip upward-continuation gradient migration [HGM_up150(x + 3u) - HGM_rtp(x - 3u)]_+
    xs_base = np.arange(W, dtype=np.float32)[None, :]
    downdip_shift = np.empty((H, W), dtype=np.float32)
    up_sym_asym = np.empty((H, W), dtype=np.float32)
    for r0 in range(0, H, 512):
        r1 = min(r0 + 512, H)
        ys_b = np.arange(r0, r1, dtype=np.float32)[:, None]
        dy3 = np.float32(3.0) * uy[r0:r1]
        dx3 = np.float32(3.0) * ux[r0:r1]
        up_p = _bilinear_sample_strip(hgm_up150, ys_b + dy3, xs_base + dx3)
        up_m = _bilinear_sample_strip(hgm_up150, ys_b - dy3, xs_base - dx3)
        rtp_m = _bilinear_sample_strip(hgm_rtp, ys_b - dy3, xs_base - dx3)
        downdip_shift[r0:r1] = np.maximum(np.float32(0.0), up_p - rtp_m)
        up_sym_asym[r0:r1] = np.abs(up_p - up_m)
    del uy, ux
    out[:, 0] = downdip_shift[foot]
    del downdip_shift

    # Col 1: Sub-vertical strike-slip magnetic contact index (strong shallow+deep HGM with ~0 lateral shift)
    vert_ss = (np.sqrt(hgm_rtp * hgm_up150) * np.exp(-up_sym_asym)).astype(np.float32)
    out[:, 1] = vert_ss[foot]
    del hgm_rtp, hgm_up150, up_sym_asym, vert_ss
    gc.collect()

    # Col 2: Walker Lane seismic-fabric linear anisotropy x dextral shear x U/Th redox mobility
    ieq_log = np.log1p(np.maximum(0.0, _prep_grid("ieq_n100a15")))
    deq_neg = -_prep_grid("deq_n100a15")
    st_ieq = h31.structure_tensor_anisotropy(ieq_log, sigma_deriv=1.3, sigma_win=2.8)
    st_deq = h31.structure_tensor_anisotropy(deq_neg, sigma_deriv=2.0, sigma_win=4.5)
    del ieq_log, deq_neg
    shr_z = _zpos_iqr(h29._nearest_fill(*tf["geod_shearrate"]), foot)
    tf.clear()

    uth_raw = _read_u8_band_clean(ext_path, 3, "UTh", foot)
    uth_ds = h29.destripe_ew_geodawn(uth_raw, foot)
    del uth_raw
    uth_edge = _zpos_iqr(gaussian_gradient_magnitude(uth_ds, sigma=2.0, mode="nearest"), foot)
    del uth_ds
    wl_corridor = (
        np.float32(0.5) * (st_ieq + st_deq) * (np.float32(0.4) + shr_z) * (np.float32(0.6) + np.float32(0.4) * uth_edge)
    ).astype(np.float32)
    out[:, 2] = wl_corridor[foot]
    del st_ieq, st_deq, shr_z, uth_edge, wl_corridor
    gc.collect()

    # Col 3: Deconfounded 1 m LiDAR local prominence ridge (nis_scarp - G_6(nis_scarp))
    with rasterio.open(lidar_path) as ls:
        lid_valid = foot & (ls.read(12) > 0)
    nis_grid = np.zeros((H, W), dtype=np.float32)
    nis_col = np.asarray(h33_X[:, 16], dtype=np.float32)
    nis_grid[foot] = np.nan_to_num(nis_col, nan=0.0)
    num6 = gaussian_filter(nis_grid, sigma=6.0, mode="constant", cval=0.0)
    den6 = gaussian_filter(lid_valid.astype(np.float32), sigma=6.0, mode="constant", cval=0.0)
    bg6 = np.where(den6 > 1e-4, num6 / np.maximum(den6, 1e-4), 0.0).astype(np.float32)
    prom = np.where(lid_valid, nis_grid - bg6, np.nan).astype(np.float32)
    out[:, 3] = prom[foot]
    del nis_grid, num6, den6, bg6, prom, lid_valid
    gc.collect()

    if isinstance(out, np.memmap):
        out.flush()
        return np.load(cache_path, mmap_mode="r")
    return out


def _assemble_h33_2_rows(
    idx: np.ndarray,
    base_X: np.ndarray,
    sub15_X: np.ndarray,
    h33_X: np.ndarray,
    h33_2_X: np.ndarray,
    *,
    mode: str,
    extra_s2: np.ndarray | None = None,
) -> np.ndarray:
    """Assemble deconfounded H33-2 Stage-1/Stage-2 matrix (`53` sub cols; `58` full cols, zero raw u8 LiDAR)."""
    n = int(idx.size)
    extra_c = 0 if extra_s2 is None else int(extra_s2.shape[1])
    if mode == "sub":
        out = np.empty((n, 20 + 15 + 15 + 3 + extra_c), dtype=np.float32)
        out[:, 0:20] = base_X[idx][:, BASE_NON_LIDAR_IDX]
        out[:, 20:35] = sub15_X[idx]
        out[:, 35:50] = h33_X[idx][:, H33_NON_LIDAR_IDX]
        out[:, 50:53] = h33_2_X[idx][:, 0:3]
        if extra_s2 is not None:
            out[:, 53:] = extra_s2
        return out
    if mode == "full":
        out = np.empty((n, 53 + 5 + extra_c), dtype=np.float32)
        out[:, 0:20] = base_X[idx][:, BASE_NON_LIDAR_IDX]
        out[:, 20:35] = sub15_X[idx]
        out[:, 35:50] = h33_X[idx][:, H33_NON_LIDAR_IDX]
        out[:, 50:53] = h33_2_X[idx][:, 0:3]
        out[:, 53:57] = h33_X[idx][:, 15:19]
        out[:, 57:58] = h33_2_X[idx][:, 3:4]
        if extra_s2 is not None:
            out[:, 58:] = extra_s2
        return out
    raise ValueError(f"Unknown mode: {mode}")


def _predict_h33_2_chunked(
    clf: HistGradientBoostingClassifier,
    idx: np.ndarray,
    base_X: np.ndarray,
    sub15_X: np.ndarray,
    h33_X: np.ndarray,
    h33_2_X: np.ndarray,
    *,
    mode: str,
    extra_s2: np.ndarray | None = None,
    chunk: int = 200_000,
) -> np.ndarray:
    out = np.empty(idx.size, dtype=np.float32)
    if idx.size == 0:
        return out
    for s in range(0, idx.size, chunk):
        sl = idx[s : s + chunk]
        s2_sl = None if extra_s2 is None else extra_s2[s : s + chunk]
        X_sl = _assemble_h33_2_rows(sl, base_X, sub15_X, h33_X, h33_2_X, mode=mode, extra_s2=s2_sl)
        out[s : s + chunk] = clf.predict_proba(X_sl)[:, 1].astype(np.float32)
        del X_sl
    return out


def fit_predict_h33_2_dual_regime_oof(
    base_X: np.ndarray,
    sub15_X: np.ndarray,
    h33_X: np.ndarray,
    h33_2_X: np.ndarray,
    labels: np.ndarray,
    foot: np.ndarray,
    lidar_valid: np.ndarray,
    *,
    fold_masks: list[np.ndarray] | None = None,
    buffer_px: float = BUFFER_PX,
    max_neg_s1: int = 340_000,
    max_neg_s2: int = 320_000,
    s1_max_iter: int = 240,
    s2_max_iter: int = 160,
    seed: int = 610,
    cache_dir: Path | None = None,
    cache_tag: str = "quad",
    mmap_paths: tuple[Path, ...] = (),
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Deconfounded H33-2 end-to-end dual-regime nested spatial cross-fitting."""
    if fold_masks is None:
        qf = holdout.make_quadrant_folds(foot)
        fold_masks = [foot & (qf == k) for k in range(4)]
    else:
        fold_masks = [foot & np.asarray(fm, dtype=bool) for fm in fold_masks]
    assert len(fold_masks) == 4
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)

    y_foot = labels[foot]
    lid_foot = lidar_valid[foot]
    fold_id_foot = np.full(int(foot.sum()), -1, dtype=np.int8)
    for k, fm in enumerate(fold_masks):
        fold_id_foot[fm[foot]] = k

    pair_preds_sub: dict[tuple[int, int], dict[int, np.ndarray]] = {}
    pair_preds_full: dict[tuple[int, int], dict[int, np.ndarray]] = {}

    for i, j in combinations(range(4), 2):
        rem = [k for k in range(4) if k not in (i, j)]
        ckpt_p = cache_dir / f"ckpt_h332_{cache_tag}_pair_{i}_{j}.npz" if cache_dir is not None else None
        if ckpt_p is not None and ckpt_p.exists():
            with np.load(ckpt_p) as z:
                pair_preds_sub[(i, j)] = {k: z[f"sub_{k}"] for k in rem}
                pair_preds_full[(i, j)] = {k: z[f"full_{k}"] for k in rem}
            print(f"    loaded cached H33-2 stage1 pair ({i},{j})", flush=True)
            continue

        union_ij = fold_masks[i] | fold_masks[j]
        comp_ij = foot & (~union_ij)
        guard_tr = distance_transform_edt(~comp_ij) > buffer_px
        tr_foot = (union_ij & guard_tr)[foot]
        del union_ij, comp_ij, guard_tr

        rng = np.random.default_rng(seed * 1000 + i * 10 + j)
        tr_sub_idx, y_tr_sub = _sample_pos_neg(tr_foot, y_foot, max_neg_s1, rng)

        X_tr_sub = _assemble_h33_2_rows(tr_sub_idx, base_X, sub15_X, h33_X, h33_2_X, mode="sub")
        clf_sub = HistGradientBoostingClassifier(
            max_iter=s1_max_iter,
            learning_rate=0.055,
            max_leaf_nodes=63,
            min_samples_leaf=95,
            max_features=0.58,
            l2_regularization=3.0,
            random_state=seed + i * 17 + j,
        )
        clf_sub.fit(X_tr_sub, y_tr_sub)
        del X_tr_sub, tr_sub_idx, y_tr_sub
        gc.collect()
        h31.drop_file_page_cache(*mmap_paths)

        tr_full_idx, y_tr_full = _sample_pos_neg(tr_foot & lid_foot, y_foot, max_neg_s1, rng)
        del tr_foot
        X_tr_full = _assemble_h33_2_rows(tr_full_idx, base_X, sub15_X, h33_X, h33_2_X, mode="full")
        clf_full = HistGradientBoostingClassifier(
            max_iter=s1_max_iter,
            learning_rate=0.055,
            max_leaf_nodes=63,
            min_samples_leaf=95,
            max_features=0.58,
            l2_regularization=3.0,
            random_state=seed + 50 + i * 17 + j,
        )
        clf_full.fit(X_tr_full, y_tr_full)
        del X_tr_full, tr_full_idx, y_tr_full
        gc.collect()
        h31.drop_file_page_cache(*mmap_paths)

        pair_preds_sub[(i, j)] = {}
        pair_preds_full[(i, j)] = {}
        save_dict: dict[str, np.ndarray] = {}
        for k in rem:
            k_idx = np.flatnonzero(fold_id_foot == k)
            pair_preds_sub[(i, j)][k] = _predict_h33_2_chunked(
                clf_sub, k_idx, base_X, sub15_X, h33_X, h33_2_X, mode="sub"
            )
            pf_k = np.zeros(k_idx.size, dtype=np.float32)
            lid_k_local = lid_foot[k_idx]
            if lid_k_local.any():
                pf_k[lid_k_local] = _predict_h33_2_chunked(
                    clf_full, k_idx[lid_k_local], base_X, sub15_X, h33_X, h33_2_X, mode="full"
                )
            pair_preds_full[(i, j)][k] = pf_k
            save_dict[f"sub_{k}"] = pair_preds_sub[(i, j)][k]
            save_dict[f"full_{k}"] = pf_k
        if ckpt_p is not None:
            np.savez(ckpt_p, **save_dict)
        del clf_sub, clf_full, save_dict
        gc.collect()
        h31.drop_file_page_cache(*mmap_paths)
        print(f"    H33-2 stage1 pair ({i},{j}) done", flush=True)

    prob_sub_oof = np.zeros(foot.shape, dtype=np.float32)
    prob_full_oof = np.zeros(foot.shape, dtype=np.float32)
    prob_s1_oof = np.zeros(foot.shape, dtype=np.float32)
    prob_corrob_oof = np.zeros(foot.shape, dtype=np.float32)
    foot_flat_idx = np.flatnonzero(foot)

    for k in range(4):
        k_idx = np.flatnonzero(fold_id_foot == k)
        valid_pairs = [pair for pair in combinations(range(4), 2) if k not in pair]
        ps = sum(pair_preds_sub[pair][k] for pair in valid_pairs) / np.float32(3.0)
        pf = sum(pair_preds_full[pair][k] for pair in valid_pairs) / np.float32(3.0)
        prob_sub_oof.ravel()[foot_flat_idx[k_idx]] = ps
        prob_full_oof.ravel()[foot_flat_idx[k_idx]] = pf
        s1_k, corr_k = synthesize_regimes(prob_full_oof, prob_sub_oof, fold_masks[k], lidar_valid)
        prob_s1_oof[fold_masks[k]] = s1_k[fold_masks[k]]
        prob_corrob_oof[fold_masks[k]] = corr_k[fold_masks[k]]
        del s1_k, corr_k
    del prob_full_oof
    gc.collect()

    prob_s2_oof = np.zeros(foot.shape, dtype=np.float32)

    for f in range(4):
        te_global_idx = np.flatnonzero(fold_masks[f][foot])
        ckpt_s2 = cache_dir / f"ckpt_h332_{cache_tag}_s2_f{f}.npy" if cache_dir is not None else None
        if ckpt_s2 is not None and ckpt_s2.exists():
            prob_s2_oof.ravel()[foot_flat_idx[te_global_idx]] = np.load(ckpt_s2)
            print(f"    loaded cached H33-2 stage2 fold {f}", flush=True)
            continue

        test_mask = fold_masks[f]
        train_union = foot & (~test_mask)
        guard_f = distance_transform_edt(~test_mask) > buffer_px

        inner_sub = np.zeros(foot.shape, dtype=np.float32)
        inner_full = np.zeros(foot.shape, dtype=np.float32)
        rem_sectors = [m for m in range(4) if m != f]
        for m in rem_sectors:
            other_two = tuple(sorted(x for x in rem_sectors if x != m))
            m_idx = np.flatnonzero(fold_id_foot == m)
            inner_sub.ravel()[foot_flat_idx[m_idx]] = pair_preds_sub[other_two][m]
            inner_full.ravel()[foot_flat_idx[m_idx]] = pair_preds_full[other_two][m]

        inner_s1_raw, inner_corr_raw = synthesize_regimes(inner_full, inner_sub, train_union, lidar_valid)
        del inner_full

        inner_s1 = np.zeros_like(inner_s1_raw)
        inner_sub_al = np.zeros_like(inner_sub)
        inner_corr = np.zeros_like(inner_corr_raw)
        inner_s1[train_union] = h31.quantile_calibrate_gap(
            inner_s1_raw[train_union], prob_s1_oof[test_mask], scale=1.0
        )
        inner_sub_al[train_union] = h31.quantile_calibrate_gap(
            inner_sub[train_union], prob_sub_oof[test_mask], scale=1.0
        )
        inner_corr[train_union] = h31.quantile_calibrate_gap(
            inner_corr_raw[train_union], prob_corrob_oof[test_mask], scale=1.0
        )
        del inner_s1_raw, inner_sub, inner_corr_raw

        s2_train_mat = stage2_manifold_features(inner_s1, inner_sub_al, inner_corr, train_union)
        del inner_s1, inner_sub_al, inner_corr

        tu_foot = train_union[foot]
        s2_tu_guard = (train_union & guard_f)[foot][tu_foot]
        s2_tu_lid = lid_foot[tu_foot]
        del guard_f
        y_tu = labels[train_union]

        rng2 = np.random.default_rng(seed * 2000 + f)
        take_sub, y_s2_sub = _sample_pos_neg(s2_tu_guard, y_tu, max_neg_s2, rng2)
        s2_take_sub = np.ascontiguousarray(s2_train_mat[take_sub], dtype=np.float32)
        tu_global_all = np.flatnonzero(tu_foot)
        X_s2_sub = _assemble_h33_2_rows(
            tu_global_all[take_sub], base_X, sub15_X, h33_X, h33_2_X, mode="sub", extra_s2=s2_take_sub
        )
        del take_sub, s2_take_sub
        h31.drop_file_page_cache(*mmap_paths)

        clf_s2_sub = HistGradientBoostingClassifier(
            max_iter=s2_max_iter,
            learning_rate=0.05,
            max_leaf_nodes=35,
            min_samples_leaf=120,
            max_features=0.65,
            l2_regularization=4.0,
            random_state=seed + 500 + f,
        )
        clf_s2_sub.fit(X_s2_sub, y_s2_sub)
        del X_s2_sub, y_s2_sub
        gc.collect()

        take_full, y_s2_full = _sample_pos_neg(s2_tu_guard & s2_tu_lid, y_tu, max_neg_s2, rng2)
        del s2_tu_guard, s2_tu_lid, y_tu, tu_foot
        s2_take_full = np.ascontiguousarray(s2_train_mat[take_full], dtype=np.float32)
        del s2_train_mat
        gc.collect()
        X_s2_full = _assemble_h33_2_rows(
            tu_global_all[take_full], base_X, sub15_X, h33_X, h33_2_X, mode="full", extra_s2=s2_take_full
        )
        del tu_global_all, take_full, s2_take_full
        h31.drop_file_page_cache(*mmap_paths)

        clf_s2_full = HistGradientBoostingClassifier(
            max_iter=s2_max_iter,
            learning_rate=0.05,
            max_leaf_nodes=35,
            min_samples_leaf=120,
            max_features=0.65,
            l2_regularization=4.0,
            random_state=seed + 600 + f,
        )
        clf_s2_full.fit(X_s2_full, y_s2_full)
        del X_s2_full, y_s2_full
        gc.collect()

        s2_test_mat = stage2_manifold_features(prob_s1_oof, prob_sub_oof, prob_corrob_oof, test_mask)
        preds_te_sub = _predict_h33_2_chunked(
            clf_s2_sub, te_global_idx, base_X, sub15_X, h33_X, h33_2_X, mode="sub", extra_s2=s2_test_mat
        )
        preds_te_full = np.zeros(te_global_idx.size, dtype=np.float32)
        lid_te = lid_foot[te_global_idx]
        if lid_te.any():
            preds_te_full[lid_te] = _predict_h33_2_chunked(
                clf_s2_full,
                te_global_idx[lid_te],
                base_X,
                sub15_X,
                h33_X,
                h33_2_X,
                mode="full",
                extra_s2=np.ascontiguousarray(s2_test_mat[lid_te], dtype=np.float32),
            )
        del clf_s2_sub, clf_s2_full, s2_test_mat

        g_sub_f = np.zeros(foot.shape, dtype=np.float32)
        g_full_f = np.zeros(foot.shape, dtype=np.float32)
        g_sub_f.ravel()[foot_flat_idx[te_global_idx]] = preds_te_sub
        g_full_f.ravel()[foot_flat_idx[te_global_idx]] = preds_te_full
        s2_syn_f, _ = synthesize_regimes(g_full_f, g_sub_f, test_mask, lidar_valid)
        preds_te = s2_syn_f[test_mask].astype(np.float32)
        del g_sub_f, g_full_f, s2_syn_f, preds_te_sub, preds_te_full

        if ckpt_s2 is not None:
            np.save(ckpt_s2, preds_te)
        prob_s2_oof.ravel()[foot_flat_idx[te_global_idx]] = preds_te
        del te_global_idx, preds_te
        gc.collect()
        h31.drop_file_page_cache(*mmap_paths)
        print(f"    H33-2 stage2 fold {f} done", flush=True)

    del pair_preds_sub, pair_preds_full, prob_corrob_oof
    gc.collect()
    return prob_sub_oof, prob_s1_oof, prob_s2_oof


def emit_h33_2_celf(
    prob: np.ndarray,
    fold_domain: np.ndarray,
    known: np.ndarray,
    budget: int,
    *,
    b_excl: float = 2.0,
    gamma: float = CELF_GAMMA_H33_2,
    min_sep_px: float = CELF_MIN_SEP_PX_H33_2,
) -> np.ndarray:
    """Blind H33-2 zero-interior-overlap `min_sep_px = 3.45` (`gamma = 1.30`) 1-D manifold CELF."""
    return emit_h33_celf(
        prob,
        fold_domain,
        known,
        budget,
        b_excl=b_excl,
        gamma=gamma,
        min_sep_px=min_sep_px,
    )


# ======================================================================================
# Experiment 3 of 3 (H33-3 / AGMC-WL-CELF315):
# Full 69-column Stage-1 synthesis (restoring all 32 base_X cols + 15 sub15 + 19 H33 + 3 H33-2
# Walker-Lane/upward-continued magnetic cols), Basin-and-Range N22.5E + N67.5E OOF stitch,
# and zero-3px-overlap N18.4E-preserving min_sep_px = 3.15 (gamma = 1.48) manifold CELF.
# Preregistered in `knowledge/30_preregistration_H33_3_2026-10-26.md` (commit `97436c3`).
# ======================================================================================

CELF_MIN_SEP_PX_H33_3: float = 3.15
CELF_GAMMA_H33_3: float = 1.48


def sector_masks_angle(foot: np.ndarray, deg: float) -> list[np.ndarray]:
    """Partition `foot` into 4 spatial 90-deg wedges rotated by `deg` around footprint centroid."""
    ys, xs = np.nonzero(foot)
    cy = float(ys.mean())
    cx = float(xs.mean())
    rr, cc = np.indices(foot.shape, dtype=np.float32)
    ang = (np.degrees(np.arctan2(rr - cy, cc - cx)) - float(deg)) % 360.0
    sec = (ang // 90.0).astype(np.int8)
    return [foot & (sec == k) for k in range(4)]


def _assemble_h33_3_rows(
    idx: np.ndarray,
    base_X: np.ndarray,
    sub15_X: np.ndarray,
    h33_X: np.ndarray,
    h33_2_X: np.ndarray,
    *,
    mode: str,
    extra_s2: np.ndarray | None = None,
) -> np.ndarray:
    """Assemble H33-3 rows:
    - `sub` (53 LiDAR-free cols): 20 base non-LiDAR + 15 sub15 + 15 H33_SUB + 3 H33_2_SUB (+11 S2)
    - `full` (69 full cols): 32 base_X (incl. 12 1m LiDAR) + 15 sub15 + 19 H33 + 3 H33_2_SUB (+11 S2)
    """
    n = int(idx.size)
    if mode == "sub":
        c_extra = 0 if extra_s2 is None else extra_s2.shape[1]
        out = np.empty((n, 53 + c_extra), dtype=np.float32)
        out[:, 0:20] = base_X[idx][:, BASE_NON_LIDAR_IDX]
        out[:, 20:35] = sub15_X[idx]
        out[:, 35:50] = h33_X[idx][:, H33_NON_LIDAR_IDX]
        out[:, 50:53] = h33_2_X[idx][:, 0:3]
        if extra_s2 is not None:
            out[:, 53:] = extra_s2
        return out
    if mode == "full":
        c_extra = 0 if extra_s2 is None else extra_s2.shape[1]
        out = np.empty((n, 69 + c_extra), dtype=np.float32)
        out[:, 0:32] = base_X[idx]
        out[:, 32:47] = sub15_X[idx]
        out[:, 47:66] = h33_X[idx]
        out[:, 66:69] = h33_2_X[idx][:, 0:3]
        if extra_s2 is not None:
            out[:, 69:] = extra_s2
        return out
    raise ValueError(f"Unknown mode: {mode}")


def _predict_h33_3_chunked(
    clf: HistGradientBoostingClassifier,
    idx: np.ndarray,
    base_X: np.ndarray,
    sub15_X: np.ndarray,
    h33_X: np.ndarray,
    h33_2_X: np.ndarray,
    *,
    mode: str,
    extra_s2: np.ndarray | None = None,
    chunk: int = 200_000,
) -> np.ndarray:
    out = np.empty(idx.size, dtype=np.float32)
    for s in range(0, idx.size, chunk):
        e = min(idx.size, s + chunk)
        es = None if extra_s2 is None else extra_s2[s:e]
        Xc = _assemble_h33_3_rows(idx[s:e], base_X, sub15_X, h33_X, h33_2_X, mode=mode, extra_s2=es)
        out[s:e] = clf.predict_proba(Xc)[:, 1].astype(np.float32)
        del Xc
    return out


def fit_predict_h33_3_dual_regime_oof(
    base_X: np.ndarray,
    sub15_X: np.ndarray,
    h33_X: np.ndarray,
    h33_2_X: np.ndarray,
    labels: np.ndarray,
    foot: np.ndarray,
    lidar_valid: np.ndarray,
    *,
    fold_masks: list[np.ndarray] | None = None,
    buffer_px: float = BUFFER_PX,
    max_neg_s1: int = 330_000,
    max_neg_s2: int = 310_000,
    s1_max_iter: int = 220,
    s2_max_iter: int = 150,
    seed: int = 620,
    cache_dir: Path | None = None,
    cache_tag: str = "quad",
    mmap_paths: tuple[Path, ...] = (),
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """H33-3 end-to-end dual-regime nested spatial cross-fitting (53-col M_Sub + 69-col M_Full)."""
    if fold_masks is None:
        qf = holdout.make_quadrant_folds(foot)
        fold_masks = [foot & (qf == k) for k in range(4)]
    else:
        fold_masks = [foot & np.asarray(fm, dtype=bool) for fm in fold_masks]
    assert len(fold_masks) == 4
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)

    y_foot = labels[foot]
    lid_foot = lidar_valid[foot]
    fold_id_foot = np.full(int(foot.sum()), -1, dtype=np.int8)
    for k, fm in enumerate(fold_masks):
        fold_id_foot[fm[foot]] = k

    pair_preds_sub: dict[tuple[int, int], dict[int, np.ndarray]] = {}
    pair_preds_full: dict[tuple[int, int], dict[int, np.ndarray]] = {}

    for i, j in combinations(range(4), 2):
        rem = [k for k in range(4) if k not in (i, j)]
        ckpt_p = cache_dir / f"ckpt_h333_{cache_tag}_pair_{i}_{j}.npz" if cache_dir is not None else None
        if ckpt_p is not None and ckpt_p.exists():
            with np.load(ckpt_p) as z:
                pair_preds_sub[(i, j)] = {k: z[f"sub_{k}"] for k in rem}
                pair_preds_full[(i, j)] = {k: z[f"full_{k}"] for k in rem}
            print(f"    loaded cached H33-3 stage1 pair ({i},{j})", flush=True)
            continue

        union_ij = fold_masks[i] | fold_masks[j]
        comp_ij = foot & (~union_ij)
        guard_tr = distance_transform_edt(~comp_ij) > buffer_px
        tr_foot = (union_ij & guard_tr)[foot]
        del union_ij, comp_ij, guard_tr

        rng = np.random.default_rng(seed * 1000 + i * 10 + j)
        tr_sub_idx, y_tr_sub = _sample_pos_neg(tr_foot, y_foot, max_neg_s1, rng)
        X_tr_sub = _assemble_h33_3_rows(tr_sub_idx, base_X, sub15_X, h33_X, h33_2_X, mode="sub")
        clf_sub = HistGradientBoostingClassifier(
            max_iter=s1_max_iter,
            learning_rate=0.055,
            max_leaf_nodes=63,
            min_samples_leaf=95,
            max_features=0.62,
            l2_regularization=3.0,
            random_state=seed + i * 17 + j,
        )
        clf_sub.fit(X_tr_sub, y_tr_sub)
        del X_tr_sub, tr_sub_idx, y_tr_sub
        gc.collect()
        h31.drop_file_page_cache(*mmap_paths)

        tr_full_idx, y_tr_full = _sample_pos_neg(tr_foot & lid_foot, y_foot, max_neg_s1, rng)
        del tr_foot
        X_tr_full = _assemble_h33_3_rows(tr_full_idx, base_X, sub15_X, h33_X, h33_2_X, mode="full")
        clf_full = HistGradientBoostingClassifier(
            max_iter=s1_max_iter,
            learning_rate=0.055,
            max_leaf_nodes=63,
            min_samples_leaf=95,
            max_features=0.62,
            l2_regularization=3.0,
            random_state=seed + 50 + i * 17 + j,
        )
        clf_full.fit(X_tr_full, y_tr_full)
        del X_tr_full, tr_full_idx, y_tr_full
        gc.collect()
        h31.drop_file_page_cache(*mmap_paths)

        pair_preds_sub[(i, j)] = {}
        pair_preds_full[(i, j)] = {}
        save_dict: dict[str, np.ndarray] = {}
        for k in rem:
            k_idx = np.flatnonzero(fold_id_foot == k)
            pair_preds_sub[(i, j)][k] = _predict_h33_3_chunked(
                clf_sub, k_idx, base_X, sub15_X, h33_X, h33_2_X, mode="sub"
            )
            pf_k = np.zeros(k_idx.size, dtype=np.float32)
            lid_k_local = lid_foot[k_idx]
            if lid_k_local.any():
                pf_k[lid_k_local] = _predict_h33_3_chunked(
                    clf_full, k_idx[lid_k_local], base_X, sub15_X, h33_X, h33_2_X, mode="full"
                )
            pair_preds_full[(i, j)][k] = pf_k
            save_dict[f"sub_{k}"] = pair_preds_sub[(i, j)][k]
            save_dict[f"full_{k}"] = pf_k
        if ckpt_p is not None:
            np.savez(ckpt_p, **save_dict)
        del clf_sub, clf_full, save_dict
        gc.collect()
        h31.drop_file_page_cache(*mmap_paths)
        print(f"    H33-3 stage1 pair ({i},{j}) done", flush=True)

    prob_sub_oof = np.zeros(foot.shape, dtype=np.float32)
    prob_full_oof = np.zeros(foot.shape, dtype=np.float32)
    prob_s1_oof = np.zeros(foot.shape, dtype=np.float32)
    prob_corrob_oof = np.zeros(foot.shape, dtype=np.float32)
    foot_flat_idx = np.flatnonzero(foot)

    for k in range(4):
        k_idx = np.flatnonzero(fold_id_foot == k)
        valid_pairs = [pair for pair in combinations(range(4), 2) if k not in pair]
        ps = sum(pair_preds_sub[pair][k] for pair in valid_pairs) / np.float32(3.0)
        pf = sum(pair_preds_full[pair][k] for pair in valid_pairs) / np.float32(3.0)
        prob_sub_oof.ravel()[foot_flat_idx[k_idx]] = ps
        prob_full_oof.ravel()[foot_flat_idx[k_idx]] = pf
        s1_k, corr_k = synthesize_regimes(prob_full_oof, prob_sub_oof, fold_masks[k], lidar_valid)
        prob_s1_oof[fold_masks[k]] = s1_k[fold_masks[k]]
        prob_corrob_oof[fold_masks[k]] = corr_k[fold_masks[k]]
        del s1_k, corr_k
    del prob_full_oof
    gc.collect()

    prob_s2_oof = np.zeros(foot.shape, dtype=np.float32)

    for f in range(4):
        te_global_idx = np.flatnonzero(fold_masks[f][foot])
        ckpt_s2 = cache_dir / f"ckpt_h333_{cache_tag}_s2_f{f}.npy" if cache_dir is not None else None
        if ckpt_s2 is not None and ckpt_s2.exists():
            prob_s2_oof.ravel()[foot_flat_idx[te_global_idx]] = np.load(ckpt_s2)
            print(f"    loaded cached H33-3 stage2 fold {f}", flush=True)
            continue

        test_mask = fold_masks[f]
        train_union = foot & (~test_mask)
        guard_f = distance_transform_edt(~test_mask) > buffer_px

        inner_sub = np.zeros(foot.shape, dtype=np.float32)
        inner_full = np.zeros(foot.shape, dtype=np.float32)
        rem_sectors = [m for m in range(4) if m != f]
        for m in rem_sectors:
            other_two = tuple(sorted(x for x in rem_sectors if x != m))
            m_idx = np.flatnonzero(fold_id_foot == m)
            inner_sub.ravel()[foot_flat_idx[m_idx]] = pair_preds_sub[other_two][m]
            inner_full.ravel()[foot_flat_idx[m_idx]] = pair_preds_full[other_two][m]

        inner_s1_raw, inner_corr_raw = synthesize_regimes(inner_full, inner_sub, train_union, lidar_valid)
        del inner_full

        inner_s1 = np.zeros_like(inner_s1_raw)
        inner_sub_al = np.zeros_like(inner_sub)
        inner_corr = np.zeros_like(inner_corr_raw)
        inner_s1[train_union] = h31.quantile_calibrate_gap(
            inner_s1_raw[train_union], prob_s1_oof[test_mask], scale=1.0
        )
        inner_sub_al[train_union] = h31.quantile_calibrate_gap(
            inner_sub[train_union], prob_sub_oof[test_mask], scale=1.0
        )
        inner_corr[train_union] = h31.quantile_calibrate_gap(
            inner_corr_raw[train_union], prob_corrob_oof[test_mask], scale=1.0
        )
        del inner_s1_raw, inner_sub, inner_corr_raw

        s2_train_mat = stage2_manifold_features(inner_s1, inner_sub_al, inner_corr, train_union)
        del inner_s1, inner_sub_al, inner_corr

        tu_foot = train_union[foot]
        s2_tu_guard = (train_union & guard_f)[foot][tu_foot]
        s2_tu_lid = lid_foot[tu_foot]
        del guard_f
        y_tu = labels[train_union]

        rng2 = np.random.default_rng(seed * 2000 + f)
        take_sub, y_s2_sub = _sample_pos_neg(s2_tu_guard, y_tu, max_neg_s2, rng2)
        s2_take_sub = np.ascontiguousarray(s2_train_mat[take_sub], dtype=np.float32)
        tu_global_all = np.flatnonzero(tu_foot)
        X_s2_sub = _assemble_h33_3_rows(
            tu_global_all[take_sub], base_X, sub15_X, h33_X, h33_2_X, mode="sub", extra_s2=s2_take_sub
        )
        del take_sub, s2_take_sub
        h31.drop_file_page_cache(*mmap_paths)

        clf_s2_sub = HistGradientBoostingClassifier(
            max_iter=s2_max_iter,
            learning_rate=0.05,
            max_leaf_nodes=35,
            min_samples_leaf=120,
            max_features=0.65,
            l2_regularization=4.0,
            random_state=seed + 500 + f,
        )
        clf_s2_sub.fit(X_s2_sub, y_s2_sub)
        del X_s2_sub, y_s2_sub
        gc.collect()

        take_full, y_s2_full = _sample_pos_neg(s2_tu_guard & s2_tu_lid, y_tu, max_neg_s2, rng2)
        s2_take_full = np.ascontiguousarray(s2_train_mat[take_full], dtype=np.float32)
        del s2_train_mat, tu_foot, s2_tu_guard, s2_tu_lid, y_tu
        X_s2_full = _assemble_h33_3_rows(
            tu_global_all[take_full], base_X, sub15_X, h33_X, h33_2_X, mode="full", extra_s2=s2_take_full
        )
        del tu_global_all, take_full, s2_take_full
        h31.drop_file_page_cache(*mmap_paths)

        clf_s2_full = HistGradientBoostingClassifier(
            max_iter=s2_max_iter,
            learning_rate=0.05,
            max_leaf_nodes=35,
            min_samples_leaf=120,
            max_features=0.65,
            l2_regularization=4.0,
            random_state=seed + 600 + f,
        )
        clf_s2_full.fit(X_s2_full, y_s2_full)
        del X_s2_full, y_s2_full
        gc.collect()

        s2_test_mat = stage2_manifold_features(prob_s1_oof, prob_sub_oof, prob_corrob_oof, test_mask)
        preds_te = _predict_h33_3_chunked(
            clf_s2_sub, te_global_idx, base_X, sub15_X, h33_X, h33_2_X, mode="sub", extra_s2=s2_test_mat
        )
        lid_te_local = lid_foot[te_global_idx]
        if lid_te_local.any():
            preds_te[lid_te_local] = _predict_h33_3_chunked(
                clf_s2_full,
                te_global_idx[lid_te_local],
                base_X,
                sub15_X,
                h33_X,
                h33_2_X,
                mode="full",
                extra_s2=s2_test_mat[lid_te_local],
            )
        del clf_s2_sub, clf_s2_full, s2_test_mat, lid_te_local

        if ckpt_s2 is not None:
            np.save(ckpt_s2, preds_te)
        prob_s2_oof.ravel()[foot_flat_idx[te_global_idx]] = preds_te
        del te_global_idx, preds_te
        gc.collect()
        h31.drop_file_page_cache(*mmap_paths)
        print(f"    H33-3 stage2 fold {f} done", flush=True)

    del pair_preds_sub, pair_preds_full, prob_corrob_oof
    gc.collect()
    return prob_sub_oof, prob_s1_oof, prob_s2_oof


def emit_h33_3_celf(
    prob: np.ndarray,
    fold_domain: np.ndarray,
    known: np.ndarray,
    budget: int,
    *,
    b_excl: float = 2.0,
    gamma: float = CELF_GAMMA_H33_3,
    min_sep_px: float = CELF_MIN_SEP_PX_H33_3,
) -> np.ndarray:
    """Blind H33-3 zero-3px-overlap N18.4E-preserving `min_sep_px = 3.15` (`gamma = 1.48`) CELF."""
    return emit_h33_celf(
        prob,
        fold_domain,
        known,
        budget,
        b_excl=b_excl,
        gamma=gamma,
        min_sep_px=min_sep_px,
    )
