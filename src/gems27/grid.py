"""Grid constants and template helpers for the DrivenData #306 (DOE GEMS) 100 m raster.

Constants were read from the owner's copy of the sample submission (see data/manifest.json) and match
the training-feature raster; they are re-checked on every load.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio

CRS_EPSG = 32611
SHAPE = (3730, 3292)
TRANSFORM = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
BOUNDS = (243350.0, 4135550.0, 572550.0, 4508550.0)
FOOTPRINT_PX = 5_167_373
OUTSIDE_PX = 7_111_787
PIXEL_M = 100.0
KERNEL_RADIUS_PX = 3.0  # 300 m / 100 m


def load_footprint(template: Path | str) -> np.ndarray:
    """Boolean footprint = finite pixels of the template; verifies the expected grid."""
    with rasterio.open(template) as s:
        if s.crs is None or s.crs.to_epsg() != CRS_EPSG or s.shape != SHAPE:
            raise ValueError("template CRS/shape differs from the competition grid")
        if tuple(round(v, 6) for v in tuple(s.transform)[:6]) != TRANSFORM:
            raise ValueError("template geotransform differs from the competition grid")
        foot = np.isfinite(s.read(1))
    if int(foot.sum()) != FOOTPRINT_PX:
        raise ValueError(f"template footprint {int(foot.sum())} != {FOOTPRINT_PX}")
    return foot


def load_labels(path: Path | str) -> np.ndarray:
    """Catalogue raster (INGENIOUS/USGS faults) as boolean; -1 outside footprint, 0 background, 1 fault."""
    with rasterio.open(path) as s:
        a = s.read(1)
    if a.shape != SHAPE:
        raise ValueError("labels shape mismatch")
    return a == 1


def rc_to_xy(rows: np.ndarray, cols: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Pixel-centre UTM 11N coordinates."""
    x = TRANSFORM[2] + (np.asarray(cols) + 0.5) * TRANSFORM[0]
    y = TRANSFORM[5] + (np.asarray(rows) + 0.5) * TRANSFORM[4]
    return x, y


def rc_to_lonlat(rows: np.ndarray, cols: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    from pyproj import Transformer

    x, y = rc_to_xy(rows, cols)
    t = Transformer.from_crs(CRS_EPSG, 4326, always_xy=True)
    lon, lat = t.transform(x, y)
    return np.asarray(lon), np.asarray(lat)
