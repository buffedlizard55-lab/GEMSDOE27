#!/usr/bin/env python3
"""Session 21: rebuild the dconfirm T15/T8 transform caches lost with the old workspace.

The E3 builder (`build_dconfirm_submission.py`) needs `data_cache/dconfirm/subsurface_transforms.npy`
and `new_transforms.npy`. Those git-ignored caches were not part of the checkout, so this script
recreates them with the exact builder closures from `run_dconfirm_holdout.load_transforms`
(same functions, same order, no parameter changes). Output is verified against the E1 canary
record only by shape/finiteness here; scientific validity rests on the unchanged builder code.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import rasterio  # noqa: E402

import run_dconfirm_holdout as m  # noqa: E402
from gems27 import dip_rad_features as drf  # noqa: E402
from gems27 import grid, paths  # noqa: E402
from gems27 import subsurface_features as sub  # noqa: E402


def main() -> None:
    t0 = time.time()
    foot = grid.load_footprint(paths.TEMPLATE)
    meta = json.loads(paths.PREPARED_META.read_text())
    names = meta["names"]
    X = np.load(paths.PREPARED_FEATURES, mmap_mode="r")

    def build15():
        # Identical to run_dconfirm_holdout.load_transforms.build15
        grids = {}
        for b in sub.SUBSURFACE_BANDS:
            a = np.full(grid.SHAPE, np.nan, dtype=np.float32)
            a[foot] = np.asarray(X[:, names.index(b)], dtype=np.float32)
            grids[b] = a
        return sub.build_transforms(grids, foot)

    def build8():
        # Identical to run_dconfirm_holdout.load_transforms.build8
        prep = {}
        for b in drf.PREPARED_BANDS:
            a = np.full(grid.SHAPE, np.nan, dtype=np.float32)
            a[foot] = np.asarray(X[:, names.index(b)], dtype=np.float32)
            prep[b] = a
        rad = {}
        with rasterio.open(paths.RAD) as s:
            rad["rad_K"] = s.read(list(s.descriptions).index("K") + 1).astype(np.float32)
        with rasterio.open(paths.EXTENSIONS) as s:
            rad["ext_ThK"] = s.read(list(s.descriptions).index("ThK") + 1).astype(np.float32)
            rad["ext_UK"] = s.read(list(s.descriptions).index("UK") + 1).astype(np.float32)
        return drf.build_new_transforms(prep, rad, foot)

    T15 = m.build_or_load("subsurface_transforms.npy", build15)
    print(
        f"T15 done shape={T15.shape} finite={float(np.isfinite(T15).mean()):.3f} "
        f"t={time.time() - t0:.0f}s",
        flush=True,
    )
    T8 = m.build_or_load("new_transforms.npy", build8)
    print(
        f"T8 done shape={T8.shape} finite={float(np.isfinite(T8).mean()):.3f} "
        f"t={time.time() - t0:.0f}s",
        flush=True,
    )


if __name__ == "__main__":
    main()
