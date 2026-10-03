"""New-information feature bands and the overlapping-step-over link rule (Addendum D).

Three things live here, all label-free:

1. `directional_lineament_bands` - oriented line-integral context. A pixelwise tabular detector sees
   one 100 m cell at a time; a fault scarp is a *kilometre-scale linear* feature. For each input layer
   and each along-strike half-length L in {5, 10, 20} px (0.5, 1, 2 km) we average the layer along
   four orientations {0, 45, 90, 135} deg (across-strike smoothing sigma = 0.8 px applied first) and
   keep (a) the maximum over orientation and (b) the anisotropy (max - mean)/max. The maximum is the
   "is there a linear trend of high response here" evidence; the anisotropy is what separates a
   lineament from an isotropic blob (a volcanic cone, a playa rim, noise). This is the CPU-feasible
   part of the direction Hermant, Kiersnowski & Bellanger (2025) show matters - FaultSEG's advantage
   over siUNET comes from integrating evidence along the structure.

2. `aux_bands` - the restored official layers that no detector in this repo has ever used as features:
   GeoDawn airborne radiometrics (K, Th, U, TC) and extensions (Th/K, U/K, U/Th, TMI_up150), the USGS
   State Geologic Map Compilation fault mask, and the GDR 1391 Wellspring thermal/geochemical points
   (distance to any point, to `Hot` points only, to points whose quartz geothermometer is >= 150 C) and
   the 21 Great Basin Quaternary volcanic vents.

3. `steppover_links` - relay/en-echelon gap candidates the forward-cone rule cannot generate: two
   *parallel* strands (strikes agreeing within 20 deg) offset laterally by 0.3-3 km whose projections
   along the mean strike OVERLAP by >= 200 m, joined by the shortest breaching segment between the
   overlapping parts. Overlap, not tip alignment, is what identifies a step-over.

Nothing here reads labels, predictions or scores.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import rasterio
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

from . import paths
from .graph import FaultGraph
from .links import PX_KM, _azimuth_deg, local_strike_domain, strike_compat

# (drow, dcol, name) - integer steps so the oriented mean is exact (no interpolation)
ORIENTS = ((1, 0, "ns"), (1, 1, "ne"), (0, 1, "ew"), (1, -1, "nw"))
SCALES_PX = (5, 10, 20)          # along-strike half-length: 0.5, 1, 2 km
ACROSS_SIGMA = 0.8               # px, across-strike smoothing before line integration

# input layers for the directional bands: (band description in lidar_scarp_features_u8.tif, band name)
LIDAR_BANDS = ("lappos_max", "step_max", "ex_max")


def _shift(a: np.ndarray, dr: int, dc: int) -> np.ndarray:
    """Zero-filled translation by (dr, dc) rows/cols."""
    out = np.zeros_like(a)
    H, W = a.shape
    rs0, rs1 = max(0, dr), min(H, H + dr)
    cs0, cs1 = max(0, dc), min(W, W + dc)
    if rs0 >= rs1 or cs0 >= cs1:
        return out
    out[rs0:rs1, cs0:cs1] = a[rs0 - dr:rs1 - dr, cs0 - dc:cs1 - dc]
    return out


def oriented_means(img: np.ndarray, dr: int, dc: int, scales=SCALES_PX) -> dict[int, np.ndarray]:
    """Mean of `img` along the (dr, dc) direction over +-L px, for each L in `scales` (cumulative)."""
    acc = img.astype(np.float32).copy()
    k = 0
    out: dict[int, np.ndarray] = {}
    for L in sorted(scales):
        while k < L:
            k += 1
            acc += _shift(img, dr * k, dc * k)
            acc += _shift(img, -dr * k, -dc * k)
        out[L] = acc / np.float32(2 * L + 1)
    return out


def directional_lineament_bands(layers: dict[str, np.ndarray], scales=SCALES_PX) -> dict[str, np.ndarray]:
    """{`dir_<layer>_max_L<L>`: max over orientation, `dir_<layer>_aniso_L<L>`: orientation anisotropy}.

    Anisotropy definition (deviation disclosed in knowledge/03 Addendum D before the gate was run):
    * non-negative layers -> the pre-registered `(max - mean) / max`, in [0, 0.75];
    * signed layers (e.g. `det_local_relief`, 64.7% negative) -> the bounded, scale-free
      `(max - mean) / (max - min)`, in [0, 1]. The pre-registered form is unbounded for signed
      inputs (measured values up to 6.6e7), so it cannot be used there.
    nodata (NaN) is treated as 0 before line integration, and `lidar_*` inputs come from the uint8
    raster, where the 24.6% LiDAR-invalid footprint is 0 by construction.
    """
    bands: dict[str, np.ndarray] = {}
    for name, img in layers.items():
        filled = np.nan_to_num(img.astype(np.float32))
        signed = bool(filled.min() < 0)
        sm = ndi.gaussian_filter(filled, ACROSS_SIGMA)
        mx = {L: None for L in scales}
        mn = {L: None for L in scales}
        ms = {L: np.zeros_like(sm) for L in scales}
        n_or = len(ORIENTS)
        for dr, dc, _ in ORIENTS:
            om = oriented_means(sm, dr, dc, scales)
            for L, m in om.items():
                mx[L] = m.copy() if mx[L] is None else np.maximum(mx[L], m)
                mn[L] = m.copy() if mn[L] is None else np.minimum(mn[L], m)
                ms[L] += m
        for L in scales:
            mean_o = ms[L] / np.float32(n_or)
            bands[f"dir_{name}_max_L{L}"] = mx[L]
            denom = np.maximum(mx[L] - mn[L], 1e-6) if signed else np.maximum(mx[L], 1e-6)
            bands[f"dir_{name}_aniso_L{L}"] = ((mx[L] - mean_o) / denom).astype(np.float32)
        del filled, sm, mx, mn, ms
    return bands


def load_directional_input_layers(shape: tuple[int, int], foot: np.ndarray,
                                  prepared_features: np.ndarray | None = None) -> dict[str, np.ndarray]:
    """The four pre-registered input layers: 3 from the LiDAR raster, 1 from the prepared matrix."""
    layers: dict[str, np.ndarray] = {}
    with rasterio.open(paths.LIDAR) as src:
        desc = {d: i + 1 for i, d in enumerate(src.descriptions)}
        for key in LIDAR_BANDS:
            layers[f"lidar_{key}"] = src.read(desc[key]).astype(np.float32)
    if prepared_features is None:
        prepared_features = np.load(paths.PREPARED_FEATURES, mmap_mode="r")
    names = _prepared_names()
    j = names.index("det_local_relief")
    rel = np.zeros(shape, np.float32)
    rel[foot] = np.asarray(prepared_features[:, j], np.float32)
    layers["det_local_relief"] = rel
    return layers


def _prepared_names() -> list[str]:
    import json
    return json.loads(paths.PREPARED_META.read_text())["names"]


def _point_mask(rows, cols, shape) -> np.ndarray:
    m = np.zeros(shape, bool)
    r = np.clip(np.asarray(rows, int), 0, shape[0] - 1)
    c = np.clip(np.asarray(cols, int), 0, shape[1] - 1)
    m[r, c] = True
    return m


def _dist_band(mask: np.ndarray, clip: float = 60.0) -> np.ndarray:
    d = ndi.distance_transform_edt(~mask).astype(np.float32) if mask.any() else np.full(mask.shape, clip, np.float32)
    return np.minimum(d, clip)


def aux_bands(shape: tuple[int, int]) -> dict[str, np.ndarray]:
    """The +rad (8), +sgmc (3) and +thermal (5) pre-registered bands."""
    bands: dict[str, np.ndarray] = {}
    for path, prefix in ((paths.RAD, "rad"), (paths.EXTENSIONS, "ext")):
        with rasterio.open(path) as s:
            for i, d in enumerate(s.descriptions):
                bands[f"{prefix}_{d}"] = s.read(i + 1).astype(np.float32)
    with rasterio.open(paths.SGMC) as s:
        sgmc = s.read(1) > 0
    bands["sgmc_dist"] = _dist_band(sgmc, clip=20.0)
    bands["sgmc_on"] = sgmc.astype(np.float32)
    bands["sgmc_within_1km"] = ndi.binary_dilation(sgmc, ndi.generate_binary_structure(2, 2),
                                                   iterations=10).astype(np.float32)

    ws = pd.read_csv(paths.WELLSPRING)
    ws["thermalclass"] = ws.thermalclass.astype(str).str.strip()
    all_m = _point_mask(ws.row, ws.col, shape)
    hot = ws.thermalclass.isin(["Hot"])
    hot_m = _point_mask(ws.row[hot], ws.col[hot], shape)
    q = pd.to_numeric(ws.geothermquartz_c, errors="coerce")
    q150 = q >= 150.0
    q_m = _point_mask(ws.row[q150], ws.col[q150], shape)
    vents = pd.read_csv(paths.VOLCANIC_VENTS)
    v_m = _point_mask(vents.row, vents.col, shape)
    bands["ws_dist_all"] = _dist_band(all_m, clip=100.0)
    bands["ws_dist_hot"] = _dist_band(hot_m, clip=100.0)
    bands["ws_dist_q150"] = _dist_band(q_m, clip=100.0)
    bands["ws_log1p_hot"] = np.log1p(bands["ws_dist_hot"]).astype(np.float32)
    bands["vent_dist"] = _dist_band(v_m, clip=100.0)
    bands["_diag_n_hot"] = np.float32(shape[0] * shape[1]) * np.float32(0)   # placeholder, never used
    del bands["_diag_n_hot"]
    return bands


RAD_BANDS = ["rad_K", "rad_Th", "rad_U", "rad_TC", "ext_ThK", "ext_UK", "ext_UTh", "ext_TMI_up150"]
SGMC_BANDS = ["sgmc_dist", "sgmc_on", "sgmc_within_1km"]
THERMAL_BANDS = ["ws_dist_all", "ws_dist_hot", "ws_dist_q150", "ws_log1p_hot", "vent_dist"]


def variant_bands(variant: str, bands: dict[str, np.ndarray], scales=SCALES_PX) -> list[str]:
    """Ordered band names for an Addendum-D arm."""
    if variant == "base":
        return []
    if variant == "rad":
        return list(RAD_BANDS)
    if variant == "sgmc":
        return list(SGMC_BANDS)
    if variant == "thermal":
        return list(THERMAL_BANDS)
    if variant == "dir":
        return [f"dir_{lay}_{stat}_L{L}" for lay in ("lidar_lappos_max", "lidar_step_max",
                                                     "lidar_ex_max", "det_local_relief")
                for L in scales for stat in ("max", "aniso")]
    if variant == "all":
        return variant_bands("rad", bands) + variant_bands("sgmc", bands) + \
            variant_bands("thermal", bands) + variant_bands("dir", bands)
    raise ValueError(variant)


# ----------------------------------------------------------------------------------------------
# H27-2 / D-4: overlapping en-echelon step-over links
# ----------------------------------------------------------------------------------------------
def _component_pixels(fg: FaultGraph, min_px: int = 10) -> dict[int, np.ndarray]:
    py, px = np.nonzero(fg.skeleton)
    ids = fg.comp[py, px]
    out: dict[int, np.ndarray] = {}
    for cid in np.unique(ids):
        m = ids == cid
        if m.sum() >= min_px:
            out[int(cid)] = np.c_[py[m], px[m]].astype(float)
    return out


def _principal_strike(pix: np.ndarray) -> tuple[float, np.ndarray]:
    """Length-weighted principal-axis strike azimuth (deg, 0-180) and its unit vector (row, col)."""
    c = pix - pix.mean(axis=0)
    cov = (c.T @ c) / max(len(pix) - 1, 1)
    w, v = np.linalg.eigh(cov)
    axis = v[:, int(np.argmax(w))]
    az = float(_azimuth_deg(np.array([axis[0]]), np.array([axis[1]]))[0])
    return az, axis / np.maximum(np.linalg.norm(axis), 1e-12)


def steppover_links(fg: FaultGraph, *, strike_tol_deg: float = 20.0, lat_min_px: float = 3.0,
                    lat_max_px: float = 30.0, overlap_min_px: float = 2.0,
                    len_min_px: float = 3.0, len_max_px: float = 30.0, min_px: int = 10,
                    strike_window: tuple[float, float] = (0.0, 20.0),
                    region: np.ndarray | None = None) -> pd.DataFrame:
    """Relay/step-over candidates: parallel strands, lateral offset 0.3-3 km, along-strike overlap.

    `strike_window` = (min, max) allowed difference between the two principal-axis strikes, in
    degrees. (0, 20) is the pre-registered step-over rule; (70, 110) is the kinematically wrong
    *perpendicular* control of the same size and geometry, used only by the validation harness.

    Candidate pairs are found with a centroid KD-tree of radius lat_max + half the along-strike
    extent of each component (extent capped at 100 px = 10 km). That cap makes the search O(n log n)
    instead of quadratic in the number of skeleton pixels; the only pairs it can miss are step-overs
    between two systems each longer than 20 km that are offset along strike by more than 10 km,
    which is a conservative omission (such a pair would not be a step-over at 100 m resolution).
    """
    pix = _component_pixels(fg, min_px)
    ids = sorted(pix)
    if len(ids) < 2:
        return pd.DataFrame()
    strike, axis, along, lateral, cent, ext = {}, {}, {}, {}, {}, {}
    for cid in ids:
        az, ax = _principal_strike(pix[cid])
        n = np.array([-ax[1], ax[0]])
        strike[cid], axis[cid] = az, ax
        along[cid] = pix[cid] @ ax
        lateral[cid] = pix[cid] @ n
        cent[cid] = pix[cid].mean(axis=0)
        ext[cid] = float(along[cid].max() - along[cid].min())
    tree = cKDTree(np.array([cent[c] for c in ids]))
    rows = []
    for i, cid in enumerate(ids):
        r = lat_max_px + min(ext[cid], 100.0) / 2.0 + 50.0
        for j in tree.query_ball_point(cent[cid], r):
            if j <= i:
                continue
            oid = ids[int(j)]
            rj = lat_max_px + min(ext[oid], 100.0) / 2.0
            if float(np.hypot(*(cent[cid] - cent[oid]))) > r + rj - 50.0:
                continue
            daz = abs(strike[cid] - strike[oid])
            daz = min(daz, 180.0 - daz)
            if not (strike_window[0] <= daz <= strike_window[1]):
                continue
            u = axis[cid] if len(pix[cid]) >= len(pix[oid]) else axis[oid]
            nvec = np.array([-u[1], u[0]])
            pa, pb = pix[cid] @ u, pix[oid] @ u
            qa, qb = pix[cid] @ nvec, pix[oid] @ nvec
            overlap = float(min(pa.max(), pb.max()) - max(pa.min(), pb.min()))
            if overlap < overlap_min_px:
                continue
            lat = abs(float(qa.mean() - qb.mean()))
            if not (lat_min_px <= lat <= lat_max_px):
                continue
            lo, hi = max(pa.min(), pb.min()), min(pa.max(), pb.max())
            A, B = pix[cid][(pa >= lo) & (pa <= hi)], pix[oid][(pb >= lo) & (pb <= hi)]
            if len(A) == 0 or len(B) == 0:
                continue
            dist, idx = cKDTree(B).query(A)
            k = int(np.argmin(dist))
            (r1, c1), (r2, c2) = A[k], B[int(idx[k])]
            gap = float(dist[k])
            if not (len_min_px <= gap <= len_max_px):
                continue
            if region is not None and not region[int(round(r1)), int(round(c1))]:
                continue
            rows.append((int(r1), int(c1), cid, int(r2), int(c2), oid, gap, overlap, lat, daz))
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=["e_row", "e_col", "comp_src", "q_row", "q_col", "comp_tgt",
                                     "length_px", "overlap_px", "lateral_px", "strike_diff_deg"])
    d = np.c_[df.q_row - df.e_row, df.q_col - df.e_col].astype(float)
    df["strike"] = _azimuth_deg(d[:, 0], d[:, 1])
    df["kind"] = "en-echelon step-over"
    df["mutual"] = False
    df["tgt_is_tip"] = False
    df["ang_tgt"] = np.nan
    df["ang_src"] = np.nan
    df["size_src_km"] = fg.comp_length_px[df.comp_src.to_numpy(int)] * PX_KM
    df["size_tgt_km"] = fg.comp_length_px[df.comp_tgt.to_numpy(int)] * PX_KM
    df["merged_km"] = df.size_src_km + df.size_tgt_km + df.length_px * PX_KM
    df["gap_km"] = df.length_px * PX_KM
    tree_s, strk, wts = local_strike_domain(fg)
    df["strike_compat"] = strike_compat(tree_s, strk, wts, ((df.e_row + df.q_row) / 2).to_numpy(float),
                                        ((df.e_col + df.q_col) / 2).to_numpy(float), df.strike.to_numpy())
    return df


def dedupe_pairs(df: pd.DataFrame) -> pd.DataFrame:
    """One row per unordered component pair (a step-over is symmetric)."""
    if df.empty:
        return df
    key = np.minimum(df.comp_src, df.comp_tgt).astype(str) + "_" + np.maximum(df.comp_src, df.comp_tgt).astype(str)
    return df.assign(_k=key).sort_values("length_px").drop_duplicates("_k").drop(columns="_k").reset_index(drop=True)
