"""Session 6 `H29-1` & `H29-2` multi-physics, GDR #1391 hydrothermal, & curvilinear piedmont detector.

Memory & hygiene guarantees:
  1. All 54 physical features (`44` for `H29-1a` / `Exp 1` + `10` for `H29-2` / `Exp 3`) are 100%
     label-free (zero catalogue/fault inputs; `dist_known_fault_px` in GDR CSVs is explicitly
     never read). Stored as a `float32` memory-mapped matrix (`~1.06 GiB` on disk, `< 1.8 GiB` peak
     RSS in a 3.8 GiB sandbox).
  2. Structural stress-transfer features (`4` channels for `Exp 2` & `Exp 3`) are computed strictly
     from `fold['visible']` on holdout (which already excludes withheld truth + a 300 m context
     collar) and via 5-way Voronoi component jackknifing during training so `y_train = 1` never
     memorizes `distance == 0`.
  3. Emission uses multi-scale curvilinear ridge skeletonization (`ridge_nms`), `B = 2.0 px`
     (`200 m`) visible-catalogue flank exclusion, and priority-ordered Poisson-disk placement at
     `min_dist = 2.80 px` (minimum lattice spacing `sqrt(8) = 2.828 px` on diagonals, `3.000 px`
     on axes), preventing `GEMSDOE70`'s 2D blob crowding (`-11.6%` blind coverage loss).
"""

from __future__ import annotations

import csv
import gc
import io
import json
import zipfile

import numpy as np
import rasterio
from pyproj import Transformer
from scipy.ndimage import distance_transform_edt, gaussian_filter, label
from scipy.stats import rankdata
from sklearn.ensemble import HistGradientBoostingClassifier

from . import grid, oof_detector, paths

H29_CACHE_DIR = paths.DATA / "prepared"
H29_PHYS_NPY = H29_CACHE_DIR / "h29_phys_features.npy"
H29_PHYS_META = H29_CACHE_DIR / "h29_phys_features.json"

# Clean 18 bands of training_features.tif (band 6 `tc` excluded as 97.6% NaN)
TF_CLEAN = [
    (1, "mag_anom"),
    (2, "rtp"),
    (3, "tmi_hg"),
    (4, "depth_to_base_boug"),
    (5, "iso_grav_anom_hg"),
    (7, "geod_2ndinv"),
    (8, "geod_shearrate"),
    (9, "tmi_vg"),
    (10, "geod_dilaterate"),
    (11, "iso_grav_anom"),
    (12, "det_elev"),
    (13, "iso_grav_anom_vg"),
    (14, "tmi"),
    (15, "depth_to_base_surf"),
    (16, "earthq_density"),
    (17, "cond_surf"),
    (18, "iso_grav_anom_slope"),
    (19, "det_elev_slope"),
]

EXP1_FEATURE_NAMES = [
    # Group A: De-regionalized potential fields & TMI_up150 shallow depth-slice (14)
    "mag_hp8",
    "rtp_hp8",
    "rtp_bp2_15",
    "tmi_hp8",
    "tmi_hg",
    "tmi_vg",
    "mag_tilt_angle",
    "mag_tilt_zero_prox",
    "tmi_shallow_up150_diff",
    "tmi_shallow_up150_hg",
    "grav_hp10",
    "iso_grav_anom_hg",
    "iso_grav_anom_vg",
    "iso_grav_anom_slope",
    # Group B: Basement, MT clay-cap edges, seismicity, & geodetic transtension (6)
    "basement_step_grad",
    "cond_surf_hp12",
    "cond_surf_grad",
    "earthq_density",
    "geod_2ndinv",
    "geod_transtension",
    # Group C: Radiometric hydrothermal alteration contrasts (4)
    "rad_thk_ratio",
    "rad_uk_ratio",
    "rad_k_potassic",
    "rad_thk_grad",
    # Group D: Seamless 100%-footprint piedmont curvature & Lahontan shoreline mimic (8)
    "det_elev_hp8",
    "det_elev_hp25",
    "det_elev_slope",
    "piedmont_habitat",
    "piedmont_break_in_slope",
    "det_elev_slope_grad",
    "topo_openness_diff",
    "lahontan_shoreline_mimic",
    # Group E: 1 m LiDAR scarp stack with native NaN in 24.6% gap + gap indicator (11)
    "lidar_valid",
    "lidar_ex_max",
    "lidar_step_max",
    "lidar_p95",
    "lidar_p50",
    "lidar_f2",
    "lidar_f4",
    "lidar_density",
    "lidar_planarity",
    "lidar_linearity",
    "lidar_coverage",
    # Group F: Verified GDR #1391 2m temperature probes (F2mDAB), sinter seals, & volcanics (6)
    "gdr_2m_dab_plume",
    "gdr_2m_hot_vs_cold",
    "gdr_paleo_sinter_seal",
    "gdr_wellspring_thermal_excess",
    "gdr_q_volcanics_margin",
    "gdr_hydrothermal_composite",
]  # 49 physical channels

H29_2_EXTRA_NAMES = [
    # Group G (`H29-2`): Multi-azimuth hillshade, Frangi curvilinear vesselness, & 2*theta concordance (9)
    "hillshade_multiaz_ridge",
    "vesselness_topo_s12",
    "vesselness_topo_s30",
    "vesselness_mag_s20",
    "vesselness_grav_s30",
    "topo_cos2strike",
    "topo_sin2strike",
    "strike_concord_topo_mag",
    "strike_concord_topo_grav",
]  # 49 + 9 = 58 physical channels total

STRUCT_FEATURE_NAMES = [
    "struct_dist_cap25",
    "struct_corridor_annular",
    "struct_crack_tip_lobe",
    "struct_piedmont_x_tip",
]


def _fill_footprint_smooth(arr: np.ndarray, foot: np.ndarray, sigma: float) -> np.ndarray:
    """Normalized-convolution Gaussian smoothing strictly inside `foot` (`float32`)."""
    valid = foot & np.isfinite(arr) & (np.abs(arr) < 1e20)
    w = valid.astype(np.float32)
    x = np.where(valid, arr, 0.0).astype(np.float32)
    num = gaussian_filter(x, sigma=sigma, mode="nearest")
    den = np.maximum(gaussian_filter(w, sigma=sigma, mode="nearest"), 1e-6)
    med = float(np.median(arr[valid])) if valid.any() else 0.0
    return np.where(den > 1e-4, num / den, med).astype(np.float32)


def _grad_mag(arr: np.ndarray, foot: np.ndarray, pre_sigma: float = 1.0) -> np.ndarray:
    s = _fill_footprint_smooth(arr, foot, max(pre_sigma, 0.5))
    gy = gaussian_filter(s, sigma=1.0, order=[1, 0], mode="nearest")
    gx = gaussian_filter(s, sigma=1.0, order=[0, 1], mode="nearest")
    return np.where(foot, np.hypot(gx, gy), 0.0).astype(np.float32)


def _zscore_in_foot(arr: np.ndarray, foot: np.ndarray) -> np.ndarray:
    valid = foot & np.isfinite(arr) & (np.abs(arr) < 1e20)
    v = arr[valid]
    med = float(np.median(v))
    mad = float(np.median(np.abs(v - med))) * 1.4826 + 1e-6
    z = np.where(valid, (arr - med) / mad, 0.0)
    return np.clip(z, -25.0, 25.0).astype(np.float32)


def _frangi_ridge_2d(
    field: np.ndarray, foot: np.ndarray, sigma: float, beta: float = 0.55
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """2-D curvilinear ridge vesselness + axial ridge strike `(cos 2*theta, sin 2*theta)`."""
    base = _fill_footprint_smooth(field, foot, max(0.5, sigma * 0.4))
    s2 = float(sigma * sigma)
    hyy = gaussian_filter(base, sigma=sigma, order=[2, 0], mode="nearest") * s2
    hxx = gaussian_filter(base, sigma=sigma, order=[0, 2], mode="nearest") * s2
    hxy = gaussian_filter(base, sigma=sigma, order=[1, 1], mode="nearest") * s2

    tr = hxx + hyy
    disc = np.hypot(hxx - hyy, 2.0 * hxy)
    e1 = 0.5 * (tr + disc)
    e2 = 0.5 * (tr - disc)
    # Ridge of a positive edge/scarp field has strongly negative principal curvature across strike
    swap = np.abs(e1) > np.abs(e2)
    lam2 = np.where(swap, e1, e2)  # dominant curvature (across fault)
    lam1 = np.where(swap, e2, e1)  # along-strike curvature (`|lam1| << |lam2|` on curvilinear faults)

    ridge_strength = np.maximum(-lam2, 0.0)
    rb = np.abs(lam1) / (np.abs(lam2) + 1e-6)
    vessel = ridge_strength * np.exp(-(rb * rb) / (2.0 * beta * beta))

    # Normal to the ridge has angle `phi = 0.5 * atan2(2*hxy, hxx - hyy)` when lam2 is negative;
    # strike angle `theta = phi + pi/2`, so `cos(2*theta) = -cos(2*phi)`, `sin(2*theta) = -sin(2*phi)`.
    # Use eigenvectors of negative curvature directly:
    nx = hxx - lam2
    ny = hxy
    use_alt = (nx * nx + ny * ny) < 1e-12
    nx = np.where(use_alt, hxy, nx)
    ny = np.where(use_alt, hyy - lam2, ny)
    nrm = np.hypot(nx, ny) + 1e-12
    nx /= nrm
    ny /= nrm
    # Strike vector `(sx, sy) = (-ny, nx)` in `(col, row)` coordinates
    sx, sy = -ny, nx
    cos2t = (sx * sx - sy * sy).astype(np.float32)
    sin2t = (2.0 * sx * sy).astype(np.float32)
    return vessel.astype(np.float32), cos2t, sin2t


def _build_gdr_hydrothermal_channels(foot: np.ndarray) -> dict[str, np.ndarray]:
    """Build the 6 strictly label-free GDR #1391 hydrothermal & volcanic channels."""
    from pyogrio.raw import read as raw_read

    H, W = grid.SHAPE
    ext_dir = paths.DATA / "external"

    # 1-2. Raw GDR #1391 2m temperature probes (`F2mDAB` = 2m Degrees Above Background)
    probe_zip = ext_dir / "2m_temperature_probe_INGENIOUS_regional_data.zip"
    dab_grid = np.zeros((H, W), dtype=np.float32)
    hot_mask = np.zeros((H, W), dtype=bool)
    cold_mask = np.zeros((H, W), dtype=bool)
    if probe_zip.is_file():
        shp_uri = (
            f"zip://{probe_zip}!2m_temperature_probe_INGENIOUS_regional_data/"
            "2m_temperature_probe_n83geo/2m_temperature_probe_n83geo.shp"
        )
        meta, _fids, wkb, field_arrays = raw_read(shp_uri)
        import shapely

        pts = shapely.from_wkb(wkb)
        lon = shapely.get_x(pts)
        lat = shapely.get_y(pts)
        tr = Transformer.from_crs(meta.get("crs") or "EPSG:4269", "EPSG:32611", always_xy=True)
        ux, uy = tr.transform(lon, lat)
        cols = np.floor((ux - grid.TRANSFORM[2]) / 100.0).astype(int)
        rows = np.floor((grid.TRANSFORM[5] - uy) / 100.0).astype(int)
        fmap = dict(zip(meta["fields"], field_arrays))
        dab = np.array([0.0 if v is None else float(v) for v in fmap["F2mDAB"]], dtype=np.float32)
        inb = (rows >= 0) & (rows < H) & (cols >= 0) & (cols < W) & np.isfinite(dab) & (dab > -40.0)
        for r, c, dv in zip(rows[inb], cols[inb], dab[inb]):
            if not foot[r, c]:
                continue
            if dv > 0.0:
                dab_grid[r, c] = max(dab_grid[r, c], min(float(dv), 20.0))
            if dv >= 2.0:
                hot_mask[r, c] = True
            elif dv <= 0.2:
                cold_mask[r, c] = True
    else:
        with rasterio.open(ext_dir / "derived_gdr_2m_probes_100m_u8.tif") as ds:
            hot_mask = (ds.read(1) > 0) & foot
            dab_grid = hot_mask.astype(np.float32) * 3.0

    plume_near = gaussian_filter(dab_grid, sigma=3.5, mode="constant") * 12.0
    plume_mid = gaussian_filter(dab_grid, sigma=11.0, mode="constant") * 35.0
    gdr_2m_dab_plume = np.log1p(np.maximum(plume_near, plume_mid)).astype(np.float32)

    d_hot = distance_transform_edt(~hot_mask).astype(np.float32) if hot_mask.any() else np.full((H, W), 200.0, np.float32)
    d_cold = distance_transform_edt(~cold_mask).astype(np.float32) if cold_mask.any() else np.full((H, W), 200.0, np.float32)
    # Debiased hot-vs-cold 2m probe contrast (cancels survey-footprint bias!)
    gdr_2m_hot_vs_cold = (np.exp(-d_hot / 12.0) - 0.65 * np.exp(-d_cold / 12.0)).astype(np.float32)

    # 3. Paleo-geothermal sinter / tufa / travertine self-sealed deposits (`Paleo_geothermal_final.csv`)
    paleo_mask = np.zeros((H, W), dtype=bool)
    sinter_weight = np.zeros((H, W), dtype=np.float32)
    paleo_tif = ext_dir / "derived_gdr_paleo_100m_u8.tif"
    if paleo_tif.is_file():
        with rasterio.open(paleo_tif) as ds:
            paleo_mask = (ds.read(1) > 0) & foot
            sinter_weight[paleo_mask] = 1.0
    paleo_zip = ext_dir / "paleo_geothermal_regional.zip"
    if paleo_zip.is_file():
        tr83 = Transformer.from_crs("EPSG:4269", "EPSG:32611", always_xy=True)
        with zipfile.ZipFile(paleo_zip) as zf:
            txt = zf.read("Paleo_geothermal_final.csv").decode("utf-8", errors="replace")
            for row_d in csv.DictReader(io.StringIO(txt)):
                try:
                    lo = float(row_d["Long_deg_NAD83"])
                    la = float(row_d["Lat_deg_NAD83"])
                except (KeyError, ValueError, TypeError):
                    continue
                ux, uy = tr83.transform(lo, la)
                c = int(np.floor((ux - grid.TRANSFORM[2]) / 100.0))
                r = int(np.floor((grid.TRANSFORM[5] - uy) / 100.0))
                if 0 <= r < H and 0 <= c < W and foot[r, c]:
                    paleo_mask[r, c] = True
                    dtype = str(row_d.get("Deposit_type", "")).lower()
                    w = 1.5 if "sinter" in dtype else (1.2 if "travertine" in dtype or "tufa" in dtype else 1.0)
                    sinter_weight[r, c] = max(sinter_weight[r, c], w)
    d_paleo = distance_transform_edt(~paleo_mask).astype(np.float32) if paleo_mask.any() else np.full((H, W), 200.0, np.float32)
    gdr_paleo_sinter_seal = (
        0.65 * np.exp(-d_paleo / 10.0)
        + 0.35 * np.exp(-d_paleo / 28.0)
        + gaussian_filter(sinter_weight, sigma=5.0, mode="constant") * 8.0
    ).astype(np.float32)

    # 4. Quality-screened thermal springs & wells (NEVER touching `dist_known_fault_px`!)
    hot_ws = np.zeros((H, W), dtype=np.float32)
    cold_ws = np.zeros((H, W), dtype=bool)
    if paths.WELLSPRING.is_file():
        with open(paths.WELLSPRING, newline="") as f:
            reader = csv.DictReader(f)
            # Explicit guard: verify we never read `dist_known_fault_px`
            allowed_cols = {"row", "col", "temp_c", "geothermquartz_c", "geothermchalc_c"}
            assert allowed_cols.issubset(set(reader.fieldnames or ()))
            for row_d in reader:
                r = int(row_d["row"])
                c = int(row_d["col"])
                if not (0 <= r < H and 0 <= c < W and foot[r, c]):
                    continue
                tc = float(row_d["temp_c"]) if row_d.get("temp_c") else np.nan
                qtz = float(row_d["geothermquartz_c"]) if row_d.get("geothermquartz_c") else np.nan
                chal = float(row_d["geothermchalc_c"]) if row_d.get("geothermchalc_c") else np.nan
                t_ex = max(0.0, (tc - 23.0) / 15.0) if np.isfinite(tc) else 0.0
                g_ex = 0.0
                if np.isfinite(qtz) and qtz < 320.0:
                    g_ex = max(g_ex, max(0.0, (qtz - 80.0) / 45.0))
                if np.isfinite(chal) and chal < 320.0:
                    g_ex = max(g_ex, max(0.0, (chal - 70.0) / 45.0))
                val = min(4.0, t_ex + 0.6 * g_ex)
                if val > 0.15:
                    hot_ws[r, c] = max(hot_ws[r, c], val)
                elif np.isfinite(tc) and tc <= 19.0:
                    cold_ws[r, c] = True

    d_cws = distance_transform_edt(~cold_ws).astype(np.float32) if cold_ws.any() else np.full((H, W), 200.0, np.float32)
    ws_plume = (
        gaussian_filter(hot_ws, sigma=4.0, mode="constant") * 16.0
        + gaussian_filter(hot_ws, sigma=14.0, mode="constant") * 45.0
    )
    gdr_wellspring_thermal_excess = (np.log1p(ws_plume) - 0.25 * np.exp(-d_cws / 8.0)).astype(np.float32)

    # 5. Quaternary volcanic flow margins + volcanic vents (`row, col` only)
    volc_edge = np.zeros((H, W), dtype=bool)
    volc_tif = ext_dir / "derived_gdr_volcanics_100m_u8.tif"
    if volc_tif.is_file():
        with rasterio.open(volc_tif) as ds:
            vm = (ds.read(1) > 0) & foot
        # Margin of Quaternary volcanic units (fault-controlled feeder dikes & flow boundaries)
        from scipy.ndimage import binary_erosion

        volc_edge |= vm & ~binary_erosion(vm, iterations=1)
    if paths.VOLCANIC_VENTS.is_file():
        with open(paths.VOLCANIC_VENTS, newline="") as f:
            for row_d in csv.DictReader(f):
                r, c = int(row_d["row"]), int(row_d["col"])
                if 0 <= r < H and 0 <= c < W and foot[r, c]:
                    volc_edge[r, c] = True
    d_volc = distance_transform_edt(~volc_edge).astype(np.float32) if volc_edge.any() else np.full((H, W), 200.0, np.float32)
    gdr_q_volcanics_margin = np.exp(-d_volc / 16.0).astype(np.float32)

    gdr_hydrothermal_composite = (
        0.35 * _zscore_in_foot(gdr_2m_dab_plume, foot)
        + 0.30 * _zscore_in_foot(gdr_paleo_sinter_seal, foot)
        + 0.25 * _zscore_in_foot(gdr_wellspring_thermal_excess, foot)
        + 0.10 * _zscore_in_foot(gdr_q_volcanics_margin, foot)
    ).astype(np.float32)

    return {
        "gdr_2m_dab_plume": gdr_2m_dab_plume,
        "gdr_2m_hot_vs_cold": gdr_2m_hot_vs_cold,
        "gdr_paleo_sinter_seal": gdr_paleo_sinter_seal,
        "gdr_wellspring_thermal_excess": gdr_wellspring_thermal_excess,
        "gdr_q_volcanics_margin": gdr_q_volcanics_margin,
        "gdr_hydrothermal_composite": gdr_hydrothermal_composite,
    }


def ensure_h29_physical_features(*, force: bool = False) -> tuple[np.ndarray, list[str]]:
    """Build or open memory-mapped `(5_167_373, 58)` label-free physical feature stack."""
    all_names = EXP1_FEATURE_NAMES + H29_2_EXTRA_NAMES
    if not force and H29_PHYS_NPY.is_file() and H29_PHYS_META.is_file():
        meta = json.loads(H29_PHYS_META.read_text())
        if meta.get("feature_names") == all_names and meta.get("n_rows") == grid.FOOTPRINT_PX:
            mm = np.load(H29_PHYS_NPY, mmap_mode="r")
            if mm.shape == (grid.FOOTPRINT_PX, len(all_names)):
                return mm, all_names

    H29_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    foot = grid.load_footprint(paths.TEMPLATE)
    mm = np.lib.format.open_memmap(
        H29_PHYS_NPY, mode="w+", dtype=np.float32, shape=(grid.FOOTPRINT_PX, len(all_names))
    )
    col_idx = {name: i for i, name in enumerate(all_names)}

    def write_col(name: str, arr2d: np.ndarray) -> None:
        mm[:, col_idx[name]] = np.asarray(arr2d, dtype=np.float32)[foot]

    # Read clean training_features bands sequentially to keep peak RAM < 1.5 GiB
    tf: dict[str, np.ndarray] = {}
    with rasterio.open(paths.TRAINING) as ds:
        for b, bname in TF_CLEAN:
            a = ds.read(b).astype(np.float32)
            ok = foot & np.isfinite(a) & (np.abs(a) < 1e20)
            med = float(np.median(a[ok]))
            tf[bname] = np.where(ok, a, med).astype(np.float32)

    # Group A: De-regionalized potential fields + shallow magnetic depth-slice (`TMI - TMI_up150`)
    write_col("mag_hp8", tf["mag_anom"] - _fill_footprint_smooth(tf["mag_anom"], foot, 8.0))
    rtp_s2 = _fill_footprint_smooth(tf["rtp"], foot, 2.0)
    rtp_s8 = _fill_footprint_smooth(tf["rtp"], foot, 8.0)
    rtp_s15 = _fill_footprint_smooth(tf["rtp"], foot, 15.0)
    write_col("rtp_hp8", tf["rtp"] - rtp_s8)
    write_col("rtp_bp2_15", rtp_s2 - rtp_s15)
    del rtp_s2, rtp_s8, rtp_s15

    write_col("tmi_hp8", tf["tmi"] - _fill_footprint_smooth(tf["tmi"], foot, 8.0))
    write_col("tmi_hg", tf["tmi_hg"])
    write_col("tmi_vg", tf["tmi_vg"])
    tilt = np.arctan2(tf["tmi_vg"], np.abs(tf["tmi_hg"]) + 1e-4).astype(np.float32)
    write_col("mag_tilt_angle", tilt)
    write_col("mag_tilt_zero_prox", np.exp(-np.abs(tilt) / 0.35).astype(np.float32))
    del tilt

    # Shallow magnetic vertical-continuation residual (`TMI` vs `TMI_up150` from geodawn_extensions)
    with rasterio.open(paths.EXTENSIONS) as ext_ds:
        thk_u8 = ext_ds.read(1)
        uk_u8 = ext_ds.read(2)
        tmi_up150_u8 = ext_ds.read(4)
    up_valid = foot & (tmi_up150_u8 > 0)
    up_f = np.where(up_valid, tmi_up150_u8.astype(np.float32), np.nan)
    if (~up_valid & foot).any():
        up_f = np.where(np.isnan(up_f), float(np.nanmedian(up_f[foot])), up_f)
    # Match standardized rank/scale inside footprint to isolate shallow <150 m susceptibility steps
    tmi_shallow = (_zscore_in_foot(tf["tmi"], foot) - _zscore_in_foot(up_f, foot)).astype(np.float32)
    tmi_shallow_hp = tmi_shallow - _fill_footprint_smooth(tmi_shallow, foot, 10.0)
    write_col("tmi_shallow_up150_diff", tmi_shallow_hp)
    tmi_sh_hg = _grad_mag(tmi_shallow_hp, foot, pre_sigma=1.0)
    write_col("tmi_shallow_up150_hg", tmi_sh_hg)
    del up_f, tmi_up150_u8, tmi_shallow, tmi_shallow_hp

    write_col("grav_hp10", tf["iso_grav_anom"] - _fill_footprint_smooth(tf["iso_grav_anom"], foot, 10.0))
    write_col("iso_grav_anom_hg", tf["iso_grav_anom_hg"])
    write_col("iso_grav_anom_vg", tf["iso_grav_anom_vg"])
    write_col("iso_grav_anom_slope", tf["iso_grav_anom_slope"])

    # Group B: Basement steps, MT clay-cap edges, seismicity, & geodetic transtension
    write_col("basement_step_grad", _grad_mag(tf["depth_to_base_surf"], foot, pre_sigma=1.5))
    write_col("cond_surf_hp12", tf["cond_surf"] - _fill_footprint_smooth(tf["cond_surf"], foot, 12.0))
    cond_grad = _grad_mag(tf["cond_surf"], foot, pre_sigma=1.2)
    write_col("cond_surf_grad", cond_grad)
    write_col("earthq_density", tf["earthq_density"])
    write_col("geod_2ndinv", tf["geod_2ndinv"])
    transtension = (
        _zscore_in_foot(tf["geod_shearrate"], foot)
        + 0.7 * np.maximum(_zscore_in_foot(tf["geod_dilaterate"], foot), -1.0)
    ).astype(np.float32)
    write_col("geod_transtension", transtension)
    del transtension, cond_grad

    # Group C: Radiometric hydrothermal alteration (`Th/K`, `U/K`, `K`, `|grad(Th/K)|`)
    thk_f = np.where(thk_u8 > 0, thk_u8.astype(np.float32) / 254.0, np.nan)
    uk_f = np.where(uk_u8 > 0, uk_u8.astype(np.float32) / 254.0, np.nan)
    thk_fill = np.where(np.isfinite(thk_f), thk_f, float(np.nanmedian(thk_f[foot]))).astype(np.float32)
    write_col("rad_thk_ratio", thk_f)
    write_col("rad_uk_ratio", uk_f)
    write_col("rad_thk_grad", _grad_mag(thk_fill, foot, pre_sigma=1.5))
    del thk_u8, uk_u8, thk_f, uk_f, thk_fill
    with rasterio.open(paths.RAD) as rad_ds:
        k_u8 = rad_ds.read(1)
    write_col("rad_k_potassic", np.where(k_u8 > 0, k_u8.astype(np.float32) / 254.0, np.nan))
    del k_u8

    # Group D: Seamless 100%-footprint piedmont toe curvature & Lake Lahontan shoreline mimic
    de = tf["det_elev"]
    des = tf["det_elev_slope"]
    de_s3 = _fill_footprint_smooth(de, foot, 3.0)
    de_s8 = _fill_footprint_smooth(de, foot, 8.0)
    de_s25 = _fill_footprint_smooth(de, foot, 25.0)
    de_hp8 = de - de_s8
    write_col("det_elev_hp8", de_hp8)
    write_col("det_elev_hp25", de - de_s25)
    write_col("det_elev_slope", des)

    # Alluvial-fan piedmont habitat peaks at moderate piedmont slopes (neither 0-slope playa nor 30-deg crag)
    des_med = float(np.percentile(des[foot], 62))
    des_scale = max(float(np.percentile(des[foot], 85) - np.percentile(des[foot], 35)), 1e-4)
    pied_hab = np.exp(-0.5 * ((des - des_med) / des_scale) ** 2).astype(np.float32)
    write_col("piedmont_habitat", pied_hab)

    # Down-slope profile curvature (`-div(grad(z)/|grad(z)|)`) + gradient of slope = piedmont break-in-slope
    zy = gaussian_filter(de, sigma=1.2, order=[1, 0], mode="nearest")
    zx = gaussian_filter(de, sigma=1.2, order=[0, 1], mode="nearest")
    zn = np.hypot(zx, zy) + 1e-3
    uy, ux = zy / zn, zx / zn
    prof_curv = -(
        gaussian_filter(uy, sigma=1.0, order=[1, 0], mode="nearest")
        + gaussian_filter(ux, sigma=1.0, order=[0, 1], mode="nearest")
    ).astype(np.float32)
    write_col("piedmont_break_in_slope", prof_curv)
    des_grad = _grad_mag(des, foot, pre_sigma=1.0)
    write_col("det_elev_slope_grad", des_grad)
    write_col("topo_openness_diff", (de_s3 - de_s8).astype(np.float32))

    # Pleistocene Lake Lahontan / pluvial shoreline mimic: sharp topographic step along near-constant
    # regional elevation bench WITHOUT subsurface magnetic or gravity horizontal gradient support
    pot_support = np.maximum(_zscore_in_foot(tf["tmi_hg"], foot), _zscore_in_foot(tf["iso_grav_anom_hg"], foot))
    pot_gate = np.exp(np.clip(pot_support, -2.0, 4.0) * 0.45)
    elev_low_band = np.exp(-0.5 * ((de - np.percentile(de[foot], 28)) / (np.std(de[foot]) * 0.45 + 1e-4)) ** 2)
    lahontan_mimic = (_zscore_in_foot(des, foot).clip(0.0, 5.0) * elev_low_band / (pot_gate + 0.35)).astype(np.float32)
    write_col("lahontan_shoreline_mimic", lahontan_mimic)
    del de_s3, de_s8, de_s25, zy, zx, zn, uy, ux, prof_curv, des_grad, pot_support, pot_gate, elev_low_band, lahontan_mimic

    # Group E: 1 m LiDAR scarp stack (preserving native NaN in the 24.6% gap + explicit gap flag)
    lidar_cos2 = None
    lidar_sin2 = None
    lidar_valid_2d = np.zeros(grid.SHAPE, dtype=bool)
    with rasterio.open(paths.LIDAR) as lds:
        cov_u8 = lds.read(10)
        lidar_valid_2d = foot & (cov_u8 > 0)
        write_col("lidar_valid", lidar_valid_2d.astype(np.float32))
        lidar_band_map = [
            (1, "lidar_ex_max"),
            (2, "lidar_step_max"),
            (3, "lidar_p95"),
            (4, "lidar_p50"),
            (5, "lidar_f2"),
            (6, "lidar_f4"),
            (7, "lidar_density"),
            (8, "lidar_planarity"),
            (9, "lidar_linearity"),
            (10, "lidar_coverage"),
        ]
        for b, lname in lidar_band_map:
            raw_u8 = lds.read(b)
            arr_l = np.where(lidar_valid_2d, raw_u8.astype(np.float32) / 255.0, np.nan).astype(np.float32)
            write_col(lname, arr_l)
        c11 = lds.read(11)
        c12 = lds.read(12)
        lidar_cos2 = np.where(lidar_valid_2d, c11.astype(np.float32) / 127.5 - 1.0, np.nan).astype(np.float32)
        lidar_sin2 = np.where(lidar_valid_2d, c12.astype(np.float32) / 127.5 - 1.0, np.nan).astype(np.float32)

    # Group F: Official GDR #1391 2m probes (`F2mDAB`), paleo sinter/tufa seals, & volcanics
    gdr_ch = _build_gdr_hydrothermal_channels(foot)
    for kname, karr in gdr_ch.items():
        write_col(kname, karr)
    del gdr_ch
    gc.collect()

    # Group G (`H29-2`): Multi-azimuth synthetic hillshade, Frangi curvilinear vesselness, & 2*theta concordance
    gy_e = gaussian_filter(de_hp8, sigma=1.2, order=[1, 0], mode="nearest")
    gx_e = gaussian_filter(de_hp8, sigma=1.2, order=[0, 1], mode="nearest")
    hs_max = np.zeros(grid.SHAPE, dtype=np.float32)
    for az_deg in (45.0, 90.0, 135.0, 315.0):
        az = np.deg2rad(az_deg)
        illum = np.abs(gx_e * np.sin(az) - gy_e * np.cos(az)).astype(np.float32)
        hs_max = np.maximum(hs_max, illum)
    write_col("hillshade_multiaz_ridge", hs_max)
    del gy_e, gx_e, hs_max

    v_t12, c2_t12, s2_t12 = _frangi_ridge_2d(des, foot, sigma=1.2)
    v_t30, c2_t30, s2_t30 = _frangi_ridge_2d(des, foot, sigma=3.0)
    write_col("vesselness_topo_s12", v_t12)
    write_col("vesselness_topo_s30", v_t30)

    # Fuse high-res 1 m LiDAR strike where available with seamless Hessian topographic strike in the 24.6% gap
    topo_c2 = np.where(lidar_valid_2d & np.isfinite(lidar_cos2), 0.65 * lidar_cos2 + 0.35 * c2_t12, c2_t30).astype(np.float32)
    topo_s2 = np.where(lidar_valid_2d & np.isfinite(lidar_sin2), 0.65 * lidar_sin2 + 0.35 * s2_t12, s2_t30).astype(np.float32)
    tnrm = np.hypot(topo_c2, topo_s2) + 1e-6
    topo_c2 /= tnrm
    topo_s2 /= tnrm
    write_col("topo_cos2strike", topo_c2)
    write_col("topo_sin2strike", topo_s2)
    del v_t12, v_t30, c2_t12, s2_t12, c2_t30, s2_t30, lidar_cos2, lidar_sin2

    mag_combo = 0.6 * _zscore_in_foot(tf["tmi_hg"], foot) + 0.4 * _zscore_in_foot(tmi_sh_hg, foot)
    v_mag, c2_mag, s2_mag = _frangi_ridge_2d(mag_combo, foot, sigma=2.2)
    write_col("vesselness_mag_s20", v_mag)
    del mag_combo, tmi_sh_hg

    v_grav, c2_grav, s2_grav = _frangi_ridge_2d(tf["iso_grav_anom_hg"], foot, sigma=3.0)
    write_col("vesselness_grav_s30", v_grav)

    # Axial 2*theta strike concordance (`cos(2*(theta_topo - theta_geophys))`) weighted by ridge prominence
    sc_w = np.clip(_zscore_in_foot(des, foot), -1.0, 4.0) + 1.0
    mg_w = np.clip(_zscore_in_foot(v_mag, foot), -1.0, 4.0) + 1.0
    gr_w = np.clip(_zscore_in_foot(v_grav, foot), -1.0, 4.0) + 1.0
    write_col("strike_concord_topo_mag", ((topo_c2 * c2_mag + topo_s2 * s2_mag) * np.sqrt(sc_w * mg_w)).astype(np.float32))
    write_col("strike_concord_topo_grav", ((topo_c2 * c2_grav + topo_s2 * s2_grav) * np.sqrt(sc_w * gr_w)).astype(np.float32))

    del tf, de, des, de_hp8, pied_hab, v_mag, c2_mag, s2_mag, v_grav, c2_grav, s2_grav, topo_c2, topo_s2
    mm.flush()
    H29_PHYS_META.write_text(
        json.dumps(
            {
                "n_rows": grid.FOOTPRINT_PX,
                "n_features": len(all_names),
                "feature_names": all_names,
                "exp1_count": len(EXP1_FEATURE_NAMES),
                "h29_2_count": len(H29_2_EXTRA_NAMES),
                "label_free": True,
                "gdr_1391_verified": True,
            },
            indent=2,
        )
        + "\n"
    )
    gc.collect()
    return np.load(H29_PHYS_NPY, mmap_mode="r"), all_names


def _structural_fields_for_mask(
    cat_mask: np.ndarray, piedmont_hab_2d: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Compute 4 structural accommodation fields from a given visible fault mask (`float32`)."""
    m_bool = np.asarray(cat_mask, dtype=bool)
    if not m_bool.any():
        z = np.zeros(grid.SHAPE, dtype=np.float32)
        return np.full(grid.SHAPE, 25.0, dtype=np.float32), z, z, z

    d_vis = distance_transform_edt(~m_bool).astype(np.float32)
    d_cap25 = np.minimum(d_vis, 25.0).astype(np.float32)

    mf = m_bool.astype(np.float32)
    # Hollow annular corridor density: sees regional fault corridors 400 m - 3.0 km away without
    # spiking solely at `d = 0`
    g_far = gaussian_filter(mf, sigma=16.0, mode="constant")
    g_near = gaussian_filter(mf, sigma=3.2, mode="constant")
    corridor = np.maximum(g_far - 0.18 * g_near, 0.0).astype(np.float32)

    # Vector-calculus fault-tip termination fan:
    # Along a continuous fault interior `t . grad(m_s) ~ 0`; at a fault tip `|t . grad(m_s)|` peaks!
    ms = gaussian_filter(mf, sigma=1.8, mode="constant")
    gy = gaussian_filter(ms, sigma=1.2, order=[1, 0], mode="constant")
    gx = gaussian_filter(ms, sigma=1.2, order=[0, 1], mode="constant")
    # Principal axis of the trace from structure tensor of `(gx, gy)`
    jxx = gaussian_filter(gx * gx, sigma=2.5, mode="constant")
    jyy = gaussian_filter(gy * gy, sigma=2.5, mode="constant")
    jxy = gaussian_filter(gx * gy, sigma=2.5, mode="constant")
    # Normal is major eigenvector of J; strike `t` is minor eigenvector!
    phi = 0.5 * np.arctan2(2.0 * jxy, jxx - jyy)
    # Tangent / strike direction `(tx, ty) = (-sin(phi), cos(phi))`
    tx, ty = -np.sin(phi), np.cos(phi)
    # Along-strike gradient magnitude marks fault tips (terminations)
    tip_seed = np.abs(tx * gx + ty * gy) * (ms > 0.02)
    tip_lobe = (
        gaussian_filter(tip_seed.astype(np.float32), sigma=12.0, mode="constant") * 30.0
        + gaussian_filter(tip_seed.astype(np.float32), sigma=24.0, mode="constant") * 60.0
    )
    # Suppress inside `d <= 2 px` collar so tip lobe specifically illuminates `300 m - 3.5 km` off-tip basin
    tip_lobe = (tip_lobe * (1.0 - 0.85 * np.exp(-(d_vis / 2.5) ** 2))).astype(np.float32)
    pied_x_tip = (piedmont_hab_2d * np.log1p(tip_lobe * 10.0)).astype(np.float32)
    return d_cap25, corridor, tip_lobe, pied_x_tip


def build_structural_features_train_and_eval(
    visible_mask: np.ndarray,
    foot: np.ndarray,
    piedmont_hab_foot: np.ndarray,
    *,
    seed: int = 201,
    n_splits: int = 5,
) -> tuple[np.ndarray, np.ndarray]:
    """Build self-leakage-free training structural features AND inference structural features.

    Why Voronoi 5-way component jackknifing matters:
      On `visible_mask`, every positive training pixel has `distance(~visible) == 0`. Passing raw
      `distance(~visible)` into training causes tree models to split trivially at `d < 0.5`.
      Partitioning `visible_mask`'s connected components into 5 random groups `V_0..V_4` and
      assigning every pixel `(y, x)` whose nearest `visible` pixel lies in `V_k` the structural
      fields of `W_k = visible \\ collar(V_k, 3 px)` ensures:
        - Every training positive (`V_k`) sees `80%` of other visible faults (`> 300 m` away),
          matching how withheld holdout faults see `visible_mask`!
        - Training negatives in `V_k`'s Voronoi cell see the exact same `W_k` (`80%` sub-catalogue),
          eliminating `d == 0` self-leakage and train/test density shift!
      For inference (`S_eval`), we average the 5 `80%`-sub-catalogue feature evaluations so test-time
      catalogue density (`80%` of `visible_mask`) matches training `W_k` density identically.
    """
    vis = np.asarray(visible_mask, dtype=bool) & foot
    pied_2d = np.zeros(grid.SHAPE, dtype=np.float32)
    pied_2d[foot] = piedmont_hab_foot

    comp, n_comp = label(vis, structure=np.ones((3, 3), dtype=int))
    rng = np.random.default_rng(seed)
    comp_group = np.zeros(n_comp + 1, dtype=np.int32)
    if n_comp > 0:
        comp_group[1:] = rng.integers(0, n_splits, size=n_comp)

    _, nearest_idx = distance_transform_edt(~vis, return_indices=True)
    nearest_comp = comp[nearest_idx[0], nearest_idx[1]]
    pixel_group = comp_group[nearest_comp][foot]

    S_train = np.zeros((grid.FOOTPRINT_PX, 4), dtype=np.float32)
    S_eval = np.zeros((grid.FOOTPRINT_PX, 4), dtype=np.float32)

    for k in range(n_splits):
        vk = vis & np.isin(comp, np.flatnonzero(comp_group == k))
        collar_k = distance_transform_edt(~vk) <= 3.0 if vk.any() else np.zeros(grid.SHAPE, dtype=bool)
        wk = vis & ~collar_k
        c0, c1, c2, c3 = _structural_fields_for_mask(wk, pied_2d)
        stack_k = np.column_stack([c0[foot], c1[foot], c2[foot], c3[foot]]).astype(np.float32)
        sel = pixel_group == k
        S_train[sel] = stack_k[sel]
        S_eval += stack_k * (1.0 / float(n_splits))
        del vk, collar_k, wk, c0, c1, c2, c3, stack_k

    return S_train, S_eval


def fit_predict_loqo_surface(
    X_phys: np.ndarray,
    foot: np.ndarray,
    quad_grid: np.ndarray,
    visible_catalogue: np.ndarray,
    *,
    col_indices: list[int],
    S_train_struct: np.ndarray | None = None,
    S_eval_struct: np.ndarray | None = None,
    seed: int = 201,
    neg_collar_px: float = 3.0,
    neg_per_pos: int = 10,
    buffer_px: int = 6,
) -> np.ndarray:
    """4-quadrant out-of-fold ensemble (`HGB` + depth-regularized `HGB`) with collar-clean PU sampling."""
    vis_2d = np.asarray(visible_catalogue, dtype=bool) & foot
    d_vis_2d = distance_transform_edt(~vis_2d).astype(np.float32)
    y_pos_foot = vis_2d[foot]
    # Digitization-collar-clean negatives: exclude `0 < d_vis <= 300 m` cartographic jitter shadow!
    clean_neg_foot = d_vis_2d[foot] > neg_collar_px
    lidar_valid_foot = X_phys[:, EXP1_FEATURE_NAMES.index("lidar_valid")] > 0.5

    oof_foot = np.zeros(grid.FOOTPRINT_PX, dtype=np.float32)
    rng = np.random.default_rng(seed)

    for q in range(4):
        test_2d = (quad_grid == q) & foot
        d_to_test = distance_transform_edt(~test_2d)
        train_foot = ((quad_grid != q) & foot & (d_to_test > buffer_px))[foot]
        test_foot = test_2d[foot]

        pos_idx = np.flatnonzero(train_foot & y_pos_foot)
        neg_pool = np.flatnonzero(train_foot & clean_neg_foot)
        n_neg = min(len(neg_pool), len(pos_idx) * neg_per_pos)
        neg_idx = np.sort(rng.choice(neg_pool, size=n_neg, replace=False))
        tr_idx = np.concatenate([pos_idx, neg_idx])
        y_tr = np.concatenate([np.ones(len(pos_idx), dtype=np.int8), np.zeros(len(neg_idx), dtype=np.int8)])

        X_tr = np.asarray(X_phys[tr_idx][:, col_indices], dtype=np.float32)
        if S_train_struct is not None:
            X_tr = np.hstack([X_tr, S_train_struct[tr_idx]])

        # Two complementary HistGradientBoosting configurations (fine interactions + smooth regularized)
        m1 = HistGradientBoostingClassifier(
            max_iter=340,
            learning_rate=0.045,
            max_leaf_nodes=47,
            min_samples_leaf=80,
            l2_regularization=2.5,
            random_state=seed * 10 + q,
            early_stopping=False,
        )
        m2 = HistGradientBoostingClassifier(
            max_iter=260,
            learning_rate=0.04,
            max_leaf_nodes=25,
            min_samples_leaf=160,
            l2_regularization=6.0,
            random_state=seed * 10 + q + 100,
            early_stopping=False,
        )
        m1.fit(X_tr, y_tr)
        m2.fit(X_tr, y_tr)
        del X_tr

        # Predict in chunks of 450,000 rows to cap transient RAM
        te_rows = np.flatnonzero(test_foot)
        preds_q = np.empty(len(te_rows), dtype=np.float32)
        chunk = 450_000
        for s0 in range(0, len(te_rows), chunk):
            sl = te_rows[s0 : s0 + chunk]
            X_te = np.asarray(X_phys[sl][:, col_indices], dtype=np.float32)
            if S_eval_struct is not None:
                X_te = np.hstack([X_te, S_eval_struct[sl]])
            p = 0.55 * m1.predict_proba(X_te)[:, 1] + 0.45 * m2.predict_proba(X_te)[:, 1]
            preds_q[s0 : s0 + chunk] = p.astype(np.float32)
            del X_te

        # Cross-regime (`LiDAR valid` vs `LiDAR gap`) prevalence-preserving calibration using ONLY
        # training-fold visible fault prevalence ratio (`r_gap / r_lid`)!
        tr_lid = train_foot & lidar_valid_foot
        tr_gap = train_foot & ~lidar_valid_foot
        prev_lid = float(y_pos_foot[tr_lid].mean()) if tr_lid.any() else 0.005
        prev_gap = float(y_pos_foot[tr_gap].mean()) if tr_gap.any() else prev_lid
        te_lid_mask = lidar_valid_foot[te_rows]
        if te_lid_mask.any() and (~te_lid_mask).any():
            # Align upper-tail quantiles (`98.5%`) between LiDAR-gap and LiDAR-valid modulated by true
            # training-quadrant prevalence ratio so NE_LidarGapHeavy is neither starved nor flooded
            q_lid = float(np.quantile(preds_q[te_lid_mask], 0.985))
            q_gap = float(np.quantile(preds_q[~te_lid_mask], 0.985))
            ratio_prev = np.clip(prev_gap / max(prev_lid, 1e-6), 0.70, 1.30)
            if q_gap > 1e-6:
                scale_gap = float(np.clip((q_lid / q_gap) * (ratio_prev ** 0.35), 0.75, 1.35))
                preds_q[~te_lid_mask] = np.clip(preds_q[~te_lid_mask] * scale_gap, 0.0, 1.0)

        oof_foot[te_rows] = preds_q
        del m1, m2, preds_q
        gc.collect()

    out_2d = np.zeros(grid.SHAPE, dtype=np.float32)
    out_2d[foot] = np.clip(oof_foot, 0.0, 1.0)
    return out_2d


def blend_rank_surfaces(
    surf_a: np.ndarray, surf_b: np.ndarray, foot: np.ndarray, *, weight_a: float = 0.55
) -> np.ndarray:
    """Monotone rank-percentile blend strictly inside `[0, 1]` on `foot`."""
    ra = rankdata(surf_a[foot], method="average").astype(np.float32) / float(grid.FOOTPRINT_PX)
    rb = rankdata(surf_b[foot], method="average").astype(np.float32) / float(grid.FOOTPRINT_PX)
    blended = weight_a * ra + (1.0 - weight_a) * rb
    #Sharpen gently onto `[0, 1]` while preserving exact rank order
    out = np.zeros(grid.SHAPE, dtype=np.float32)
    out[foot] = np.clip(blended, 0.0, 1.0)
    return out


def priority_ridge_poisson_emit(
    surface: np.ndarray,
    foot: np.ndarray,
    visible_catalogue: np.ndarray,
    *,
    n_dots: int = 37_654,
    collar_px: float = 2.0,
    min_dist: float = 2.80,
) -> tuple[np.ndarray, np.ndarray]:
    """Curvilinear multi-scale ridge skeleton + `B=2 px` collar + priority Poisson-disk placement.

    Returns `(binary_dots_float32, continuous_smoothed_surface_float32)`.
    """
    foot_b = np.asarray(foot, dtype=bool)
    vis_b = np.asarray(visible_catalogue, dtype=bool) & foot_b
    s1 = _fill_footprint_smooth(surface, foot_b, 1.0)
    s2 = _fill_footprint_smooth(surface, foot_b, 2.1)
    comb = np.where(foot_b, np.clip(0.65 * s1 + 0.35 * s2, 0.0, 1.0), 0.0).astype(np.float32)

    # Multi-scale curvilinear 1-px skeletons capture both 100 m piedmont scarps and 250 m magnetic steps
    r1 = oof_detector.ridge_nms(s1, valid=foot_b, sigma=0.0)
    r2 = oof_detector.ridge_nms(s2, valid=foot_b, sigma=0.0)
    skel = (r1 | r2) & foot_b

    d_vis = distance_transform_edt(~vis_b)
    elig = skel & (d_vis > float(collar_px) + 1e-6)

    ey, ex = np.nonzero(elig)
    scores = comb[ey, ex]
    # Deterministic priority order: highest score first, ties broken by `(row, col)`
    order = np.lexsort((ex, ey, -scores))
    ey = ey[order]
    ex = ex[order]

    H, W = grid.SHAPE
    pad = int(np.ceil(min_dist)) + 1
    Wp, Hp = W + 2 * pad, H + 2 * pad
    blocked = bytearray(Hp * Wp)
    r_int = int(np.ceil(min_dist))
    lim = float(min_dist * min_dist)
    disc = [
        dy * Wp + dx
        for dy in range(-r_int, r_int + 1)
        for dx in range(-r_int, r_int + 1)
        if dy * dy + dx * dx < lim
    ]

    out = np.zeros((H, W), dtype=np.float32)
    kept_count = 0
    target = int(n_dots)
    for y, x in zip(ey.tolist(), ex.tolist()):
        idx = (y + pad) * Wp + (x + pad)
        if not blocked[idx]:
            out[y, x] = 1.0
            kept_count += 1
            if kept_count >= target:
                break
            for o in disc:
                blocked[idx + o] = 1

    # Ensure strictly zero on visible_catalogue and outside footprint
    out[~foot_b] = 0.0
    out[vis_b] = 0.0
    return out, comb
