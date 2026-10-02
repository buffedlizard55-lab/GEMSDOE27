#!/usr/bin/env python3
"""Validate restored inputs and build a memory-mapped, label-free feature matrix.

Excludes the mislabelled `tc` band (band 6, rank-identical to radiometric total count; see
registry/irregularities.json) so that no downstream spatial-CV detector treats gamma-ray total count
as a magnetic derivative. Writes `data_cache/prepared/features.npy` and `evidence/data_preparation.json`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, gaussian_filter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import grid, paths  # noqa: E402

# Verified against rasterio.open(paths.TRAINING).descriptions (band 6 'tc' excluded).
TRAINING_BANDS: list[tuple[int, str]] = [
    (1, "mag_anom"),
    (2, "rtp"),
    (3, "tmi_hg"),
    (4, "geod_2ndinv"),
    (5, "iso_grav_anom_slope"),
    # band 6 ('tc') deliberately excluded: rank-identical to radiometric total count
    (7, "geod_shearrate"),
    (8, "geod_dilaterate"),
    (9, "tmi_vg"),
    (10, "deq_n100a15"),
    (11, "iso_grav_anom_vg"),
    (12, "det_elev"),
    (13, "iso_grav_anom"),
    (14, "tmi"),
    (15, "depth_to_base_surf"),
    (16, "ieq_n100a15"),
    (17, "cond_surf"),
    (18, "iso_grav_anom_hg"),
    (19, "det_elev_slope"),
]
LIDAR_BANDS: list[tuple[int, str]] = [
    (1, "lidar_scarp_p95"),
    (2, "lidar_scarp_max"),
    (3, "lidar_slope_p95"),
    (4, "lidar_lappos_p95"),
    (5, "lidar_lappos_max"),
    (6, "lidar_lapneg_p95"),
    (7, "lidar_lapneg_max"),
    (8, "lidar_rough_p95"),
    (9, "lidar_openness_neg"),
    (10, "lidar_lrm_abs"),
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    out_dir = paths.PREPARED_FEATURES.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = paths.PREPARED_FEATURES
    meta_path = paths.PREPARED_META
    ev_path = paths.EVIDENCE / "data_preparation.json"

    if dest.exists() and meta_path.exists() and not args.force:
        meta = json.loads(meta_path.read_text())
        ev_path.write_text(json.dumps(meta, indent=2) + "\n")
        print(json.dumps(meta, indent=2))
        return 0

    foot = grid.load_footprint(paths.TEMPLATE)
    idx = np.flatnonzero(foot.ravel())

    with rasterio.open(paths.TEMPLATE) as t, rasterio.open(paths.TRAINING) as s, rasterio.open(paths.LIDAR) as lid:
        for d in (s, lid):
            if d.shape != t.shape or d.crs != t.crs or d.transform != t.transform:
                raise SystemExit("Input grid mismatch; no silent reprojecting")
        if s.count != 19:
            raise SystemExit(f"Expected 19 competition training bands, got {s.count}")
        if lid.count != 12:
            raise SystemExit(f"Expected 12 lidar scarp descriptor bands, got {lid.count}")
        for b, expected_name in TRAINING_BANDS:
            actual = (s.descriptions[b - 1] or "").split(" - ")[0].strip()
            if actual != expected_name:
                raise SystemExit(f"Band {b} description mismatch: {actual!r} != {expected_name!r}")

    names = (
        [name for _, name in TRAINING_BANDS]
        + [name for _, name in LIDAR_BANDS]
        + ["lidar_cos2strike", "lidar_sin2strike", "det_local_relief", "det_gradient"]
    )
    partial = dest.with_name("features.partial.npy")
    arr = np.lib.format.open_memmap(partial, mode="w+", dtype=np.float32, shape=(len(idx), len(names)))

    col = 0
    dem = None
    with rasterio.open(paths.TRAINING) as s:
        nd = s.nodata
        for b, name in TRAINING_BANDS:
            a = s.read(b).astype(np.float32)
            valid = np.isfinite(a) & (np.abs(a) < 1e30) & foot
            if nd is not None:
                valid &= a != np.float32(nd)
            a[~valid] = np.nan
            arr[:, col] = a.ravel()[idx]
            if name == "det_elev":
                dem = a
            col += 1

    with rasterio.open(paths.LIDAR) as lid:
        valid = (lid.read(12) > 0) & foot
        for b, _ in LIDAR_BANDS:
            a = lid.read(b).astype(np.float32)
            a[~valid] = np.nan
            arr[:, col] = a.ravel()[idx]
            col += 1
        theta = (np.maximum(lid.read(11).astype(np.float32) - 1.0, 0.0) / 254.0) * np.pi
        for trig in (np.cos(2.0 * theta), np.sin(2.0 * theta)):
            a = trig.astype(np.float32)
            a[~valid] = np.nan
            arr[:, col] = a.ravel()[idx]
            col += 1

    assert dem is not None
    dv = np.isfinite(dem)
    inds = distance_transform_edt(~dv, return_distances=False, return_indices=True)
    dem_fill = dem[tuple(inds)]
    del inds
    local_relief = (dem_fill - gaussian_filter(dem_fill, 5.0)).astype(np.float32)
    gy, gx = np.gradient(gaussian_filter(dem_fill, 1.0), 100.0)
    grad = np.hypot(gx, gy).astype(np.float32)
    for a in (local_relief, grad):
        a[~dv] = np.nan
        arr[:, col] = a.ravel()[idx]
        col += 1

    if col != len(names):
        raise SystemExit(f"Feature column accounting error: {col} != {len(names)}")
    arr.flush()
    del arr
    partial.replace(dest)

    repo_data_prep = paths.REPO / "data" / "prepared"
    repo_data_prep.mkdir(parents=True, exist_ok=True)
    for p in (dest,):
        link = repo_data_prep / p.name
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(p)

    metadata = {
        "names": names,
        "n_features": len(names),
        "shape": [int(len(idx)), int(len(names))],
        "footprint_px": int(len(idx)),
        "grid_shape": list(grid.SHAPE),
        "crs": f"EPSG:{grid.CRS_EPSG}",
        "sha256": sha256_file(dest),
        "inputs": {
            "template": sha256_file(paths.TEMPLATE),
            "training_features": sha256_file(paths.TRAINING),
            "lidar_scarp_features_u8": sha256_file(paths.LIDAR),
            "labels": sha256_file(paths.LABELS),
            "qfaults_v2_in_footprint": sha256_file(paths.QFAULT_VECTORS),
            "dem_links": sha256_file(paths.DEM_LINKS),
        },
        "note": "Label-free feature matrix for spatial-CV detectors. Band 6 ('tc') is excluded because it is rank-identical to radiometric total count (Spearman 1.0000); all remaining 18 training bands are verified by embedded description.",
    }
    meta_path.write_text(json.dumps(metadata, indent=2) + "\n")
    ev_path.write_text(json.dumps(metadata, indent=2) + "\n")
    link_meta = repo_data_prep / meta_path.name
    if link_meta.exists() or link_meta.is_symlink():
        link_meta.unlink()
    link_meta.symlink_to(meta_path)
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
