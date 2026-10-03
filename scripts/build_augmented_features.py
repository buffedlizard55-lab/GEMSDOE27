#!/usr/bin/env python3
"""Build the Addendum-D augmented label-free band matrix (40 bands) as a float32 memmap.

Bands (names frozen in `knowledge/03_preregistration_topology_gate.md`, Addendum D):
  +rad     8   GeoDawn radiometrics K/Th/U/TC and extensions Th/K, U/K, U/Th, TMI_up150
  +sgmc    3   USGS State Geologic Map Compilation fault mask (distance clipped 20 px, on, within 1 km)
  +thermal 5   GDR 1391 Wellspring distances (all / Hot / quartz geothermometer >= 150 C, log1p hot)
               and distance to the 21 Great Basin Quaternary volcanic vents
  +dir    24   oriented line integrals: 4 input layers x 3 along-strike half-lengths (5/10/20 px)
               x {max over 4 orientations, anisotropy (max-mean)/max}

Written footprint-ordered so it can be column-concatenated with `data_cache/prepared/features.npy`
(32 bands, sha256 83ed2704...). Memory-bounded: bands are computed one layer at a time and written
straight into the memmap (the box has 3 GB RAM).

Usage: GEMS_DATA_DIR=/home/user/GEMSDOE27/data_cache .venv/bin/python scripts/build_augmented_features.py
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import grid, newinfo, paths  # noqa: E402

OUT = paths.DATA / "prepared" / "features_aug.npy"
META = paths.DATA / "prepared" / "features_aug.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def main() -> int:
    t0 = time.time()
    foot = grid.load_footprint(paths.TEMPLATE)
    shape = foot.shape
    n_fp = int(foot.sum())

    names = (newinfo.variant_bands("rad", {}) + newinfo.variant_bands("sgmc", {})
             + newinfo.variant_bands("thermal", {}) + newinfo.variant_bands("dir", {}))
    print(f"{len(names)} augmented bands, {n_fp:,} footprint pixels", flush=True)

    mm = np.lib.format.open_memmap(OUT, mode="w+", dtype=np.float32, shape=(n_fp, len(names)))
    col = {n: i for i, n in enumerate(names)}

    # ---- aux bands (cheap, small) -------------------------------------------------------------
    aux = newinfo.aux_bands(shape)
    for n, band in aux.items():
        j = col[n]
        mm[:, j] = band[foot]
        print(f"  {n:<20} mean={band[foot].mean():9.3f}  nonzero={float((band[foot] != 0).mean()):.4f}"
              f"  t={time.time()-t0:.0f}s", flush=True)
    del aux

    # ---- directional bands (one input layer at a time) ----------------------------------------
    layers = newinfo.load_directional_input_layers(shape, foot)
    for lay, img in layers.items():
        bands = newinfo.directional_lineament_bands({lay: img})
        for n, band in bands.items():
            mm[:, col[n]] = band[foot]
            print(f"  {n:<28} mean={band[foot].mean():9.3f}  t={time.time()-t0:.0f}s", flush=True)
        del bands
    del layers, img
    mm.flush()
    del mm

    # ---- verify by re-reading -----------------------------------------------------------------
    chk = np.load(OUT, mmap_mode="r")
    finite = bool(np.isfinite(np.asarray(chk[: min(n_fp, 200_000)])).all())
    meta = {
        "names": names, "n_features": len(names), "shape": [n_fp, len(names)],
        "dtype": "float32", "footprint_px": n_fp, "grid_shape": list(shape),
        "order": "footprint row-major, same as data_cache/prepared/features.npy",
        "sha256": sha256(OUT),
        "base_matrix_sha256": json.loads(paths.PREPARED_META.read_text())["sha256"],
        "inputs": {p.name: sha256(p) for p in (paths.LIDAR, paths.RAD, paths.EXTENSIONS, paths.SGMC,
                                               paths.WELLSPRING, paths.VOLCANIC_VENTS)},
        "scales_px": list(newinfo.SCALES_PX), "orientations": [o[2] for o in newinfo.ORIENTS],
        "across_strike_sigma_px": newinfo.ACROSS_SIGMA,
        "seconds": time.time() - t0,
        "note": ("Label-free. LiDAR-invalid pixels (24.7% of the footprint) carry 0 in every lidar_* "
                 "input, so their oriented means are low by construction - the detector also sees "
                 "geopotential/gravity channels there. No band uses labels, predictions or scores."),
        "finite_check_first_200k_rows": finite,
    }
    META.write_text(json.dumps(meta, indent=2) + "\n")
    print(f"wrote {OUT} ({OUT.stat().st_size/1e6:.0f} MB) and {META} in {meta['seconds']:.0f}s", flush=True)
    print(f"sha256 {meta['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
