"""Label-free Hydrothermal × Piedmont-Toe × Destriped Shallow Geophysical features +
2-Stage Nested Spatial Cross-Fitting with Multi-Scale Frangi/Line-Integral Vesselness
(Hypothesis H29-1 / Lane L-S7-2026-10-25).

Strict leakage firewall:
- Reads ONLY unlabeled survey grids (`training_features.tif`, `lidar_scarp_features_u8.tif`,
  `geodawn_extensions_u8.tif`, `geodawn_rad_u8.tif`) and chemical/temperature columns
  (`row, col, temp_c, geothermquartz_c, geothermchalc_c, geothermcat_c`) from
  `gdr_wellspring_in_footprint.csv`.
- NEVER opens `labels.tif` or `existing_faults.tif` inside feature construction, and
  explicitly forbids reading `dist_known_fault_px` from any CSV.
- Stage-2 spatial ridge/vesselness features are computed strictly on out-of-fold Stage-1
  probabilities with 600 m (`BUFFER_PX = 6`) fold-boundary nearest-fill masking.
"""
from __future__ import annotations

from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from scipy.ndimage import distance_transform_edt, gaussian_filter, gaussian_gradient_magnitude
from sklearn.ensemble import HistGradientBoostingClassifier

from . import holdout, paths

BUFFER_PX: int = 6

WELLSPRING_ALLOWED_COLS: tuple[str, ...] = (
    "row",
    "col",
    "temp_c",
    "geothermquartz_c",
    "geothermchalc_c",
    "geothermcat_c",
)

H29_FEATURE_NAMES: tuple[str, ...] = (
    "h29_piedmont_concave_s3",
    "h29_piedmont_concave_s8",
    "h29_deconf_lappos",
    "h29_deconf_step",
    "h29_deconf_ex",
    "h29_piedmont_scarp_coh",
    "h29_rtp_destripe_hgm",
    "h29_rtp_destripe_tilt0",
    "h29_mag_shallow_res",
    "h29_mag_shallow_grad",
    "h29_grav_tilt0",
    "h29_basin_horst_step",
    "h29_basin_horst_relief",
    "h29_k_th_alter_grad",
    "h29_thk_mag_coupled",
    "h29_cond_strain_piedmont",
    "h29_gdr_teq_nw_s12",
    "h29_gdr_diseq_nw_s12",
    "h29_gdr_teq_grad",
    "h29_gdr_upflow_prox",
)

S2_VESSELNESS_NAMES: tuple[str, ...] = (
    "s2_p1",
    "s2_smooth_s15",
    "s2_smooth_s40",
    "s2_smooth_s90",
    "s2_ridge_tophat",
    "s2_frangi_s15",
    "s2_frangi_s35",
    "s2_frangi_s70",
    "s2_line8_max",
    "s2_line8_aniso",
)


def _nearest_fill(arr: np.ndarray, valid: np.ndarray) -> np.ndarray:
    a = np.asarray(arr, dtype=np.float32).copy()
    good = np.asarray(valid, dtype=bool) & np.isfinite(a)
    if not good.any():
        return np.zeros_like(a, dtype=np.float32)
    if not good.all():
        idx = distance_transform_edt(~good, return_distances=False, return_indices=True)
        a = a[tuple(idx)]
    return a


def destripe_ew_geodawn(arr: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Suppress 200-400 m E-W (azimuth=90 deg) GeoDAWN flight-line corrugation (Glen & Earney 2024)."""
    g = _nearest_fill(arr, valid)
    high_y = g - gaussian_filter(g, sigma=(2.5, 0.0), mode="nearest")
    ew_corrugation = gaussian_filter(high_y, sigma=(0.0, 14.0), mode="nearest")
    return (g - ew_corrugation).astype(np.float32)


def rank01_grid(arr: np.ndarray, valid: np.ndarray, foot: np.ndarray) -> np.ndarray:
    """Scale-free uniform [0, 1] quantile transform over valid footprint pixels, nearest-filled."""
    g = _nearest_fill(arr, valid)
    vals = g[foot]
    order = np.argsort(vals, kind="mergesort")
    ranks = np.empty(vals.size, dtype=np.float32)
    denom = max(vals.size - 1, 1)
    ranks[order] = np.arange(vals.size, dtype=np.float32) / np.float32(denom)
    out = np.zeros(g.shape, dtype=np.float32)
    out[foot] = ranks
    return _nearest_fill(out, foot)


def _verduzco_tilt_zero_sharpness(field: np.ndarray, sigma_xy: float = 2.0, width_rad: float = 0.35) -> np.ndarray:
    """exp(-|tilt_angle| / width_rad) where tilt = arctan(VDR / (HGM + eps)) peaks at contact edges."""
    sm = gaussian_filter(field.astype(np.float64), sigma=sigma_xy, mode="nearest")
    gy = gaussian_filter(sm, sigma=1.0, order=(1, 0), mode="nearest")
    gx = gaussian_filter(sm, sigma=1.0, order=(0, 1), mode="nearest")
    hgm = np.hypot(gy, gx)
    # Second-derivative / vertical-gradient proxy via upward Laplace relation: d/dz ~ -Laplacian_smooth
    # smoothed difference across vertical continuation step:
    up = gaussian_filter(sm, sigma=2.5, mode="nearest")
    vdr = sm - up
    scale_ratio = float(np.median(hgm) / (np.median(np.abs(vdr)) + 1e-9) + 1e-9)
    tilt = np.arctan2(vdr * scale_ratio, hgm + 1e-9)
    return np.exp(-np.abs(tilt) / float(width_rad)).astype(np.float32)


def _zpos(arr: np.ndarray, foot: np.ndarray) -> np.ndarray:
    v = arr[foot]
    med = float(np.median(v))
    iqr = float(np.percentile(v, 75) - np.percentile(v, 25)) + 1e-6
    z = (arr - med) / iqr
    return np.clip(z, 0.0, 12.0).astype(np.float32)


def _read_tf_band_by_desc(tf_path: Path, foot: np.ndarray) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    out: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    band_map = {
        2: "rtp",
        7: "geod_shearrate",
        8: "geod_dilaterate",
        12: "det_elev",
        13: "iso_grav_anom",
        14: "tmi",
        15: "depth_to_base_surf",
        17: "cond_surf",
        19: "det_elev_slope",
    }
    with rasterio.open(tf_path) as src:
        for b, short_name in band_map.items():
            emb = (src.descriptions[b - 1] or "").strip()
            emb_prefix = emb.split(" - ", 1)[0].strip()
            if emb_prefix and emb_prefix != short_name:
                raise RuntimeError(f"Band {b} description mismatch: {emb!r} != {short_name!r}")
            raw = src.read(b).astype(np.float32)
            bad = (~np.isfinite(raw)) | (raw < -1e30) | (~foot)
            valid = foot & (~bad)
            raw[bad] = np.nan
            out[short_name] = (raw, valid)
    return out


def load_wellspring_geotherm_grids(
    csv_path: Path, shape: tuple[int, int], foot: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Build label-free chemical geothermometer & disequilibrium grids from GDR #1391 wells/springs.

    Strictly parses ONLY WELLSPRING_ALLOWED_COLS (`dist_known_fault_px` is never read).
    """
    df = pd.read_csv(csv_path, usecols=list(WELLSPRING_ALLOWED_COLS))
    assert "dist_known_fault_px" not in df.columns

    H, W = shape
    rows = pd.to_numeric(df["row"], errors="coerce").to_numpy()
    cols = pd.to_numeric(df["col"], errors="coerce").to_numpy()
    in_bounds = (
        np.isfinite(rows)
        & np.isfinite(cols)
        & (rows >= 0)
        & (rows < H)
        & (cols >= 0)
        & (cols < W)
    )
    df = df.loc[in_bounds].copy()
    r_idx = df["row"].astype(np.int32).to_numpy()
    c_idx = df["col"].astype(np.int32).to_numpy()

    def _clean_temp(col_name: str, lo: float, hi: float) -> np.ndarray:
        vals = pd.to_numeric(df[col_name], errors="coerce").to_numpy(dtype=np.float64, copy=True)
        vals[(vals < lo) | (vals > hi)] = np.nan
        return vals

    t_meas = _clean_temp("temp_c", 0.0, 320.0)
    t_qtz = _clean_temp("geothermquartz_c", 10.0, 320.0)
    t_chal = _clean_temp("geothermchalc_c", 10.0, 320.0)
    t_cat = _clean_temp("geothermcat_c", 10.0, 320.0)

    # Chemical reservoir equilibration temperature & cold-masked disequilibrium:
    t_chem = np.fmax(np.fmax(t_qtz, t_chal), t_cat)
    t_eq = np.fmax(t_chem, t_meas)
    diseq = np.where(
        np.isfinite(t_chem) & np.isfinite(t_meas),
        np.maximum(0.0, t_chem - t_meas),
        np.where(np.isfinite(t_chem), np.maximum(0.0, t_chem - 20.0), np.nan),
    )

    # Deduplicate to 100 m cell maximum (representing deepest/least-diluted fluid sample in cell):
    teq_cell = np.full((H, W), -np.inf, dtype=np.float32)
    teq_mask = np.zeros((H, W), dtype=np.float32)
    valid_eq = np.isfinite(t_eq)
    np.maximum.at(teq_cell, (r_idx[valid_eq], c_idx[valid_eq]), t_eq[valid_eq].astype(np.float32))
    teq_mask[r_idx[valid_eq], c_idx[valid_eq]] = 1.0
    teq_cell[~np.isfinite(teq_cell)] = 0.0

    diseq_cell = np.full((H, W), -np.inf, dtype=np.float32)
    diseq_mask = np.zeros((H, W), dtype=np.float32)
    valid_dis = np.isfinite(diseq)
    np.maximum.at(diseq_cell, (r_idx[valid_dis], c_idx[valid_dis]), diseq[valid_dis].astype(np.float32))
    diseq_mask[r_idx[valid_dis], c_idx[valid_dis]] = 1.0
    diseq_cell[~np.isfinite(diseq_cell)] = 0.0

    # Nadaraya-Watson smooth interpolation (sigma = 12 px = 1.2 km) with background Shrinkage prior:
    prior_teq = float(np.median(t_eq[valid_eq])) if valid_eq.any() else 25.0
    num_teq = gaussian_filter(teq_cell * teq_mask, sigma=12.0, mode="constant", cval=0.0)
    den_teq = gaussian_filter(teq_mask, sigma=12.0, mode="constant", cval=0.0)
    prior_w = np.float32(0.0025)
    teq_nw = ((num_teq + prior_w * prior_teq) / (den_teq + prior_w)).astype(np.float32)
    teq_nw = _nearest_fill(teq_nw, foot)

    num_dis = gaussian_filter(diseq_cell * diseq_mask, sigma=12.0, mode="constant", cval=0.0)
    den_dis = gaussian_filter(diseq_mask, sigma=12.0, mode="constant", cval=0.0)
    diseq_nw = (num_dis / (den_dis + prior_w)).astype(np.float32)
    diseq_nw = _nearest_fill(diseq_nw, foot)

    teq_grad = gaussian_gradient_magnitude(teq_nw, sigma=3.0, mode="nearest").astype(np.float32)

    # Multi-scale hydrothermal upflow conduit proximity (thermal OR chemical upflow anomaly):
    upflow_pts = np.zeros((H, W), dtype=bool)
    is_upflow = (
        (np.isfinite(t_meas) & (t_meas >= 35.0))
        | (np.isfinite(t_chem) & (t_chem >= 90.0))
        | (np.isfinite(diseq) & (diseq >= 40.0))
    )
    upflow_pts[r_idx[is_upflow], c_idx[is_upflow]] = True
    upflow_pts &= foot
    if upflow_pts.any():
        d_up = distance_transform_edt(~upflow_pts).astype(np.float32)
        upflow_prox = 0.5 * np.exp(-d_up / 15.0) + 0.5 * np.exp(-d_up / 40.0)
    else:
        upflow_prox = np.zeros((H, W), dtype=np.float32)

    return teq_nw, diseq_nw, teq_grad, upflow_prox.astype(np.float32)


def build_h29_feature_matrix(
    *,
    cache_path: Path | None = None,
    force: bool = False,
    tf_path: Path = paths.TRAINING,
    lidar_path: Path = paths.LIDAR,
    ext_path: Path = paths.EXTENSIONS,
    rad_path: Path = paths.RAD,
    wellspring_path: Path = paths.WELLSPRING,
    template_path: Path = paths.TEMPLATE,
) -> np.ndarray:
    """Compute or load the 20-column float32 H29 physics feature matrix on footprint pixels."""
    if cache_path is not None and cache_path.exists() and not force:
        arr = np.load(cache_path, mmap_mode="r")
        if arr.ndim == 2 and arr.shape[1] == len(H29_FEATURE_NAMES):
            return arr

    with rasterio.open(template_path) as t:
        foot = np.isfinite(t.read(1))
    H, W = foot.shape
    n_foot = int(foot.sum())

    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        out = np.lib.format.open_memmap(
            cache_path, mode="w+", dtype=np.float32, shape=(n_foot, len(H29_FEATURE_NAMES))
        )
    else:
        out = np.empty((n_foot, len(H29_FEATURE_NAMES)), dtype=np.float32)

    tf = _read_tf_band_by_desc(tf_path, foot)
    elev = _nearest_fill(*tf["det_elev"])
    slope = np.maximum(0.0, _nearest_fill(*tf["det_elev_slope"]))
    bg_slope15 = gaussian_filter(slope, sigma=15.0, mode="nearest")
    p25_slope = float(np.percentile(slope[foot], 25)) + 1e-3
    denom_slope = bg_slope15 + np.float32(p25_slope)

    # 1-2: Piedmont-toe upward concave flexure weighted by regional range-front slope relief
    lap_s3 = (
        gaussian_filter(elev, sigma=3.0, order=(2, 0), mode="nearest")
        + gaussian_filter(elev, sigma=3.0, order=(0, 2), mode="nearest")
    )
    reg_grad15 = rank01_grid(gaussian_gradient_magnitude(elev, sigma=15.0, mode="nearest"), foot, foot)
    out[:, 0] = (np.maximum(0.0, lap_s3) * reg_grad15)[foot].astype(np.float32)

    lap_s8 = (
        gaussian_filter(elev, sigma=8.0, order=(2, 0), mode="nearest")
        + gaussian_filter(elev, sigma=8.0, order=(0, 2), mode="nearest")
    )
    reg_grad18 = rank01_grid(gaussian_gradient_magnitude(elev, sigma=18.0, mode="nearest"), foot, foot)
    out[:, 1] = (np.maximum(0.0, lap_s8) * reg_grad18)[foot].astype(np.float32)

    # 3-6: Background-slope-deconfounded 1 m LiDAR scarp residuals & coherence
    with rasterio.open(lidar_path) as ls:
        valid_lid = foot & (ls.read(12) > 0)
        ex_max = _nearest_fill(ls.read(1).astype(np.float32), valid_lid)
        step_max = _nearest_fill(ls.read(3).astype(np.float32), valid_lid)
        lappos_max = _nearest_fill(ls.read(5).astype(np.float32), valid_lid)
        coh100 = _nearest_fill(ls.read(10).astype(np.float32), valid_lid) / np.float32(255.0)

    deconf_lap = (lappos_max / denom_slope).astype(np.float32)
    deconf_step = (step_max / denom_slope).astype(np.float32)
    deconf_ex = (ex_max / denom_slope).astype(np.float32)
    out[:, 2] = deconf_lap[foot]
    out[:, 3] = deconf_step[foot]
    out[:, 4] = deconf_ex[foot]
    out[:, 5] = ((deconf_step + deconf_lap) * coh100)[foot].astype(np.float32)

    # 7-11: E-W flight-line-destriped magnetic/gravity edges & shallow demagnetization (TMI - TMI_up150)
    rtp_ds = destripe_ew_geodawn(*tf["rtp"])
    out[:, 6] = gaussian_gradient_magnitude(rtp_ds, sigma=2.0, mode="nearest")[foot].astype(np.float32)
    out[:, 7] = _verduzco_tilt_zero_sharpness(rtp_ds, sigma_xy=2.0)[foot]

    tmi_ds = destripe_ew_geodawn(*tf["tmi"])
    with rasterio.open(ext_path) as exs:
        tmi_up150_raw = exs.read(4).astype(np.float32)
        valid_up = foot & (tmi_up150_raw > 0)
    tmi_up_ds = destripe_ew_geodawn(tmi_up150_raw, valid_up)
    mag_shallow_res = (rank01_grid(tmi_ds, foot, foot) - rank01_grid(tmi_up_ds, valid_up, foot)).astype(np.float32)
    mag_shallow_grad = gaussian_gradient_magnitude(mag_shallow_res, sigma=2.5, mode="nearest").astype(np.float32)
    out[:, 8] = mag_shallow_res[foot]
    out[:, 9] = mag_shallow_grad[foot]

    grav = _nearest_fill(*tf["iso_grav_anom"])
    out[:, 10] = _verduzco_tilt_zero_sharpness(grav, sigma_xy=2.5)[foot]

    # 12-13: Intra-basin shallow-basement horst steps (Siler et al. 2022 Granite Springs mechanism)
    dtb = _nearest_fill(*tf["depth_to_base_surf"])
    dtb_grad = gaussian_gradient_magnitude(dtb, sigma=2.5, mode="nearest")
    out[:, 11] = (dtb_grad / denom_slope)[foot].astype(np.float32)
    piedmont_basin_w = 1.0 / (1.0 + _zpos(bg_slope15, foot))
    horst_prom = (gaussian_filter(dtb, sigma=18.0, mode="nearest") - dtb) * piedmont_basin_w
    out[:, 12] = horst_prom[foot].astype(np.float32)

    # 14-16: Destriped K/Th alteration fronts & basin strain-conductivity corridors
    with rasterio.open(rad_path) as rs:
        k_raw = rs.read(1).astype(np.float32)
        th_raw = rs.read(2).astype(np.float32)
        valid_rad = foot & (k_raw > 0) & (th_raw > 0)
    k_ds = destripe_ew_geodawn(k_raw, valid_rad)
    th_ds = destripe_ew_geodawn(th_raw, valid_rad)
    k_th_diff = rank01_grid(k_ds, valid_rad, foot) - rank01_grid(th_ds, valid_rad, foot)
    k_th_grad = gaussian_gradient_magnitude(k_th_diff, sigma=3.0, mode="nearest").astype(np.float32)
    out[:, 13] = k_th_grad[foot]
    out[:, 14] = (_zpos(k_th_grad, foot) * _zpos(mag_shallow_grad, foot))[foot]

    cond = np.log1p(np.maximum(0.0, _nearest_fill(*tf["cond_surf"])))
    cond_grad = gaussian_gradient_magnitude(cond, sigma=3.0, mode="nearest").astype(np.float32)
    dil = _nearest_fill(*tf["geod_dilaterate"])
    shr = _nearest_fill(*tf["geod_shearrate"])
    strain_mag = np.hypot(dil, shr).astype(np.float32)
    out[:, 15] = (_zpos(cond_grad, foot) * _zpos(strain_mag, foot) * piedmont_basin_w)[foot].astype(np.float32)

    # 17-20: GDR #1391 chemical geothermometer disequilibrium & barrier gradients
    teq_nw, diseq_nw, teq_grad, upflow_prox = load_wellspring_geotherm_grids(wellspring_path, (H, W), foot)
    out[:, 16] = teq_nw[foot]
    out[:, 17] = diseq_nw[foot]
    out[:, 18] = teq_grad[foot]
    out[:, 19] = upflow_prox[foot]

    assert np.all(np.isfinite(out)), "Non-finite value produced in H29 feature matrix"
    if isinstance(out, np.memmap):
        out.flush()
        return np.load(cache_path, mmap_mode="r")
    return out


def _frangi_2d(prob: np.ndarray, sigma: float, valid_mask: np.ndarray, beta: float = 0.5) -> np.ndarray:
    p32 = prob.astype(np.float32, copy=False)
    s2_scale = np.float32(float(sigma) ** 2)
    hyy = s2_scale * gaussian_filter(p32, sigma=sigma, order=(2, 0), mode="nearest")
    hxx = s2_scale * gaussian_filter(p32, sigma=sigma, order=(0, 2), mode="nearest")
    hyx = s2_scale * gaussian_filter(p32, sigma=sigma, order=(1, 1), mode="nearest")

    tr = hyy + hxx
    rad = np.hypot(hyy - hxx, np.float32(2.0) * hyx)
    e1 = np.float32(0.5) * (tr - rad)
    e2 = np.float32(0.5) * (tr + rad)
    swap = np.abs(e2) > np.abs(e1)
    lam1 = np.where(swap, e2, e1)
    lam2 = np.where(swap, e1, e2)

    ridge = lam1 < -1e-6
    safe_l1 = np.where(ridge, lam1, np.float32(-1.0))
    rb2 = (lam2 / safe_l1) ** 2
    struct2 = lam1 * lam1 + lam2 * lam2
    c_val = float(np.percentile(np.sqrt(struct2[valid_mask]), 90)) if valid_mask.any() else 1e-3
    c_val = max(c_val, 1e-5)
    inv_2b2 = np.float32(1.0 / (2.0 * beta * beta))
    inv_2c2 = np.float32(1.0 / (2.0 * c_val * c_val))
    v = np.where(
        ridge,
        np.exp(-rb2 * inv_2b2) * (np.float32(1.0) - np.exp(-struct2 * inv_2c2)),
        np.float32(0.0),
    )
    return v.astype(np.float32)


def _oriented_line8_features(prob: np.ndarray, half_len: int = 6) -> tuple[np.ndarray, np.ndarray]:
    """8-azimuth 1.3 km (13 px) oriented line-integral max & orthogonal anisotropy."""
    H, W = prob.shape
    pad = half_len
    p_pad = np.pad(prob.astype(np.float32), pad, mode="edge")
    responses = np.empty((8, H, W), dtype=np.float32)
    t = np.arange(-half_len, half_len + 1, dtype=np.float64)
    inv_n = np.float32(1.0 / len(t))
    for k in range(8):
        theta = k * (np.pi / 8.0)
        dys = np.rint(t * np.sin(theta)).astype(np.int32)
        dxs = np.rint(t * np.cos(theta)).astype(np.int32)
        acc = np.zeros((H, W), dtype=np.float32)
        for dy, dx in zip(dys.tolist(), dxs.tolist()):
            acc += p_pad[pad + dy:pad + dy + H, pad + dx:pad + dx + W]
        responses[k] = acc * inv_n

    best_k = np.argmax(responses, axis=0)
    orth_k = (best_k + 4) & 7
    rows, cols = np.indices((H, W))
    l_max = responses[best_k, rows, cols]
    l_orth = responses[orth_k, rows, cols]
    aniso = (l_max - l_orth) / (l_max + np.float32(1e-5))
    return l_max.astype(np.float32), np.maximum(0.0, aniso).astype(np.float32)


def compute_stage2_vesselness(
    prob_grid: np.ndarray, valid_source_mask: np.ndarray, foot: np.ndarray
) -> np.ndarray:
    """Compute the 10 Stage-2 spatial ridge/vesselness features on footprint pixels.

    Pixels outside `valid_source_mask` are nearest-filled from `valid_source_mask` BEFORE
    any spatial convolution so zero information crosses a fold buffer.
    """
    p = _nearest_fill(np.clip(prob_grid, 0.0, 1.0).astype(np.float32), valid_source_mask)
    n_foot = int(foot.sum())
    s2 = np.empty((n_foot, len(S2_VESSELNESS_NAMES)), dtype=np.float32)
    s2[:, 0] = p[foot]
    sm15 = gaussian_filter(p, sigma=1.5, mode="nearest").astype(np.float32)
    sm40 = gaussian_filter(p, sigma=4.0, mode="nearest").astype(np.float32)
    sm90 = gaussian_filter(p, sigma=9.0, mode="nearest").astype(np.float32)
    s2[:, 1] = sm15[foot]
    s2[:, 2] = sm40[foot]
    s2[:, 3] = sm90[foot]
    tophat = (
        gaussian_filter(p, sigma=1.0, mode="nearest")
        - gaussian_filter(p, sigma=6.0, mode="nearest")
    ).astype(np.float32)
    s2[:, 4] = tophat[foot]
    s2[:, 5] = _frangi_2d(p, 1.5, valid_source_mask)[foot]
    s2[:, 6] = _frangi_2d(p, 3.5, valid_source_mask)[foot]
    s2[:, 7] = _frangi_2d(p, 7.0, valid_source_mask)[foot]
    l_max, l_aniso = _oriented_line8_features(p, half_len=6)
    s2[:, 8] = l_max[foot]
    s2[:, 9] = l_aniso[foot]
    return s2


def sector_masks_rotated45(footprint: np.ndarray) -> list[np.ndarray]:
    """45-degree rotated 4-sector partition (N, E, S, W diamonds around footprint median)."""
    ys, xs = np.nonzero(footprint)
    ym = float(np.median(ys))
    xm = float(np.median(xs))
    yy, xx = np.indices(footprint.shape, dtype=np.float32)
    u = (yy - ym) + (xx - xm)
    v = (yy - ym) - (xx - xm)
    return [
        (u < 0) & (v < 0),
        (u >= 0) & (v < 0),
        (u < 0) & (v >= 0),
        (u >= 0) & (v >= 0),
    ]


def _fit_hgb_on_indices(
    blocks: list[np.ndarray],
    y_foot: np.ndarray,
    train_idx: np.ndarray,
    *,
    neg_ratio: int = 10,
    max_neg: int = 450_000,
    seed: int,
    max_iter: int = 120,
    max_leaf_nodes: int = 31,
) -> HistGradientBoostingClassifier:
    rng = np.random.default_rng(seed)
    tr_y = y_foot[train_idx]
    pos_idx = train_idx[tr_y]
    neg_pool = train_idx[~tr_y]
    target_neg = min(int(neg_pool.size), max(int(pos_idx.size) * int(neg_ratio), 1), int(max_neg))
    if neg_pool.size > target_neg:
        neg_idx = rng.choice(neg_pool, size=target_neg, replace=False)
        neg_idx.sort()
    else:
        neg_idx = neg_pool
    sub = np.sort(np.concatenate([pos_idx, neg_idx]))
    X_tr = np.hstack([np.asarray(b[sub], dtype=np.float32) for b in blocks])
    y_tr = y_foot[sub].astype(np.int8)
    clf = HistGradientBoostingClassifier(
        max_iter=max_iter,
        learning_rate=0.08,
        max_leaf_nodes=max_leaf_nodes,
        l2_regularization=5.0,
        random_state=seed,
    )
    clf.fit(X_tr, y_tr)
    return clf


def _predict_hgb_on_indices(
    clf: HistGradientBoostingClassifier,
    blocks: list[np.ndarray],
    pred_idx: np.ndarray,
    *,
    chunk: int = 400_000,
) -> np.ndarray:
    out = np.empty(pred_idx.size, dtype=np.float32)
    for s in range(0, pred_idx.size, chunk):
        sl = pred_idx[s:s + chunk]
        X_sl = np.hstack([np.asarray(b[sl], dtype=np.float32) for b in blocks])
        out[s:s + chunk] = clf.predict_proba(X_sl)[:, 1].astype(np.float32)
    return out


def fit_predict_two_stage_oof(
    base_X: np.ndarray,
    h29_X: np.ndarray,
    labels: np.ndarray,
    foot: np.ndarray,
    *,
    fold_masks: list[np.ndarray] | None = None,
    buffer_px: int = BUFFER_PX,
    max_neg: int = 450_000,
    seed: int = 210,
) -> tuple[np.ndarray, np.ndarray]:
    """Leak-free 2-stage nested spatial cross-fitting returning (stage1_oof, stage2_oof) grids.

    Stage 1 fits all C(4, 2) = 6 buffered pairwise-sector models:
      - Inside outer fold `f`: for every training sector `g != f`, its Stage-1 probability is the
        mean of the 2 pairwise models trained on `{0,1,2,3} \\ {f, g}` (100% out-of-fold!).
      - On test sector `f`: its Stage-1 probability is the mean of the 3 pairwise models trained
        inside `{0,1,2,3} \\ {f}` (100% out-of-fold, matched 2-sector calibration!).
    Stage 2 computes multi-scale Frangi & 8-azimuth line-integral vesselness strictly inside
    `foot & ~fm & (d_to_f > buffer_px)` for training, and predicts on `foot & fm`.
    """
    foot_b = np.asarray(foot, dtype=bool)
    lab_b = np.asarray(labels, dtype=bool)
    if fold_masks is not None:
        folds = fold_masks
    else:
        qf = holdout.make_quadrant_folds(foot_b)
        folds = [qf == f for f in range(4)]
    if len(folds) != 4:
        raise ValueError(f"Expected 4 spatial folds, got {len(folds)}")

    foot_idx_grid = np.full(foot_b.shape, -1, dtype=np.int32)
    foot_idx_grid[foot_b] = np.arange(int(foot_b.sum()), dtype=np.int32)
    y_foot = lab_b[foot_b]
    s1_blocks = [base_X, h29_X]

    # Precompute buffered exclusion masks for each fold:
    excl: list[np.ndarray] = []
    for fm in folds:
        d_to_fm = distance_transform_edt(~(fm & foot_b))
        excl.append((fm & foot_b) | (d_to_fm <= buffer_px))

    # Fit C(4, 2) = 6 pairwise Stage-1 models and predict ONLY on their out-of-fold target domains:
    pair_preds: dict[tuple[int, int], np.ndarray] = {}
    for p_idx, (i, j) in enumerate(combinations(range(4), 2)):
        train_grid = foot_b & (~excl[i]) & (~excl[j])
        tr_idx = foot_idx_grid[train_grid]
        clf_ij = _fit_hgb_on_indices(
            s1_blocks, y_foot, tr_idx, max_neg=max_neg, seed=seed + 11 * p_idx
        )
        eval_grid = foot_b & (excl[i] | excl[j])
        ev_idx = foot_idx_grid[eval_grid]
        grid_pred = np.zeros(foot_b.shape, dtype=np.float32)
        grid_pred[eval_grid] = _predict_hgb_on_indices(clf_ij, s1_blocks, ev_idx)
        pair_preds[(i, j)] = grid_pred

    stage1_oof = np.zeros(foot_b.shape, dtype=np.float32)
    stage2_oof = np.zeros(foot_b.shape, dtype=np.float32)

    for f in range(4):
        fm = folds[f] & foot_b
        train_grid = foot_b & (~excl[f])
        tr_idx = foot_idx_grid[train_grid]
        te_idx = foot_idx_grid[fm]

        # Build fold-f strictly out-of-fold Stage-1 probability grid:
        # - For each training sector g != f: mean of pairs (f_a, g_b) excluding BOTH f and g
        #   Note: `pair_preds[(a, b)]` was trained by EXCLUDING sectors a and b!
        #   So `pair_preds[(f, g)]` (with a=min(f,g), b=max(f,g)) excluded BOTH f and g!
        p1_train_field = np.zeros(foot_b.shape, dtype=np.float32)
        test_accum = np.zeros(foot_b.shape, dtype=np.float32)
        n_test_models = 0
        for g in range(4):
            if g == f:
                continue
            key = (min(f, g), max(f, g))
            pred_fg = pair_preds[key]
            sec_g = folds[g] & foot_b
            p1_train_field[sec_g] = pred_fg[sec_g]
            test_accum += pred_fg
            n_test_models += 1

        p1_test_field = test_accum / np.float32(max(n_test_models, 1))
        stage1_oof[fm] = p1_test_field[fm]

        # Stage-2 training features: mask out excl[f] BEFORE spatial convolution so zero test-fold
        # signal leaks across the 600 m buffer into training vesselness!
        s2_train_foot = compute_stage2_vesselness(p1_train_field, train_grid, foot_b)
        clf_s2 = _fit_hgb_on_indices(
            [base_X, h29_X, s2_train_foot],
            y_foot,
            tr_idx,
            max_neg=max_neg,
            seed=seed + 101 + 17 * f,
            max_iter=120,
            max_leaf_nodes=31,
        )

        # Stage-2 test features: computed on p1_test_field (which never used fold f labels!)
        p1_full_for_test = p1_train_field.copy()
        p1_full_for_test[fm] = p1_test_field[fm]
        # Fill the 600 m buffer ring smoothly from p1_test_field so fold boundary has no seam:
        ring_mask = excl[f] & (~fm) & foot_b
        p1_full_for_test[ring_mask] = p1_test_field[ring_mask]
        s2_test_foot = compute_stage2_vesselness(p1_full_for_test, foot_b, foot_b)

        stage2_oof[fm] = _predict_hgb_on_indices(
            clf_s2, [base_X, h29_X, s2_test_foot], te_idx
        )

    return stage1_oof, stage2_oof
