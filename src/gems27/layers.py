"""Lazy, memory-capped loading of the on-hand geoscience layers for habitat tomography.

The sandbox has 3 GB of RAM and a 3730 x 3292 grid, so only the specific bands that the tomography
basis actually uses are read, and each is returned as the smallest dtype that preserves it.
Every layer here is a *free, official* source already restored by `scripts/restore_data.py`
(SHA-256 pinned in `data/manifest.json`); see `registry/sources.json` for provenance links.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import rasterio
from scipy.ndimage import distance_transform_edt

from . import grid, paths

LIDAR_BANDS = {"ex_max": 0, "step_max": 2, "lappos_max": 4, "coh100": 9, "relief": 8}
TRAINING_BANDS = {"tmi_hg": 2, "geod_2ndinv": 3, "iso_grav_anom_slope": 4, "det_elev": 11,
                  "cond_surf": 16, "depth_to_base_surf": 14}


def _read(path, bands: dict[str, int]) -> dict[str, np.ndarray]:
    out = {}
    with rasterio.open(path) as s:
        for name, i in bands.items():
            desc = (s.descriptions[i] or "")
            if desc and not desc.startswith(name):
                raise ValueError(f"band {i} of {path.name} is '{desc}', expected '{name}...'")
            out[name] = s.read(i + 1)
    return out


def load_lidar() -> dict[str, np.ndarray]:
    return _read(paths.LIDAR, LIDAR_BANDS)


def load_training() -> dict[str, np.ndarray]:
    return _read(paths.TRAINING, TRAINING_BANDS)


def load_sgmc() -> np.ndarray:
    with rasterio.open(paths.SGMC) as s:
        return s.read(1)


def points_to_distance(path, row_col: tuple[str, str], shape=grid.SHAPE) -> np.ndarray:
    """Distance (px) from every cell to the nearest point of a GDR CSV with grid row/col columns."""
    df = pd.read_csv(path)
    r = pd.to_numeric(df[row_col[0]], errors="coerce").to_numpy()
    c = pd.to_numeric(df[row_col[1]], errors="coerce").to_numpy()
    ok = np.isfinite(r) & np.isfinite(c)
    m = np.zeros(shape, bool)
    rr = np.clip(r[ok].astype(int), 0, shape[0] - 1)
    cc = np.clip(c[ok].astype(int), 0, shape[1] - 1)
    m[rr, cc] = True
    return distance_transform_edt(~m)


def load_wellsprings(shape=grid.SHAPE) -> np.ndarray:
    return points_to_distance(paths.WELLSPRING, ("row", "col"), shape)


def load_vents(shape=grid.SHAPE) -> np.ndarray:
    return points_to_distance(paths.VOLCANIC_VENTS, ("row", "col"), shape)


def load_vector_distance(shape=grid.SHAPE) -> np.ndarray:
    """Distance (px) to the NBMG INGENIOUS Qfaults vector polylines (1,179 features).

    Rasterised with the same Albers -> UTM 11N transform as `vector_graph.load_vector_attribution`,
    but without building the KD-tree (only the mask and its distance transform are needed here).
    """
    from pyproj import CRS, Transformer
    from skimage.draw import line as sk_line

    from .vector_graph import NBMG_ALBERS_WKT

    data = json.loads(paths.QFAULT_VECTORS.read_text())
    tf = Transformer.from_crs(CRS.from_wkt(NBMG_ALBERS_WKT), CRS.from_epsg(grid.CRS_EPSG), always_xy=True)
    mask = np.zeros(shape, bool)
    for feat in data["features"]:
        for path in feat["geometry"]["paths"]:
            pts = np.asarray(path, float)
            ux, uy = tf.transform(pts[:, 0], pts[:, 1])
            cols = np.floor((ux - grid.TRANSFORM[2]) / grid.PIXEL_M).astype(int)
            rows = np.floor((grid.TRANSFORM[5] - uy) / grid.PIXEL_M).astype(int)
            for i in range(len(rows) - 1):
                rr, cc = sk_line(int(rows[i]), int(cols[i]), int(rows[i + 1]), int(cols[i + 1]))
                ok = (rr >= 0) & (rr < shape[0]) & (cc >= 0) & (cc < shape[1])
                mask[rr[ok], cc[ok]] = True
    return distance_transform_edt(~mask), mask


def load_all() -> dict:
    """Everything the tomography basis needs, in one dict (call once; ~700 MB peak)."""
    d_vec, vec_mask = load_vector_distance()
    return {
        "lidar": load_lidar(),
        "training": load_training(),
        "sgmc": load_sgmc(),
        "d_vec": d_vec,
        "vec_mask": vec_mask,
        "d_well": load_wellsprings(),
        "d_vent": load_vents(),
    }
