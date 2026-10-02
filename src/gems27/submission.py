"""Write and independently verify DrivenData #306 submission GeoTIFFs.

Format facts (problem page, read 2026-10-02): single-band float32 GeoTIFF, values in [0, 1], same
bounds/CRS/grid as the training features, NaN or null outside the footprint; the form accepts a .tif or
a .zip containing exactly one GeoTIFF, plus an optional Note.

The cause of the portal message "Predicted values must be in range [0, 1]" that the owner saw is NOT
established (the validator is not public). We therefore (a) copy the sample submission's own raster
profile, including nodata = NaN, (b) write only exact 0.0/1.0 or sanitised probabilities, and (c) ship an
`allfinite` fallback with zeros outside the footprint, which passes every plausible reading of the rule.
The owner's sibling forensics (GEMSDOE24) found both outside-footprint conventions have scored live.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import rasterio

from . import grid


def sha256_file(path: Path | str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def check_probabilities(pred: np.ndarray, footprint: np.ndarray) -> None:
    v = np.asarray(pred)[footprint]
    if not np.isfinite(v).all():
        raise ValueError("non-finite value inside the footprint")
    if v.min() < 0.0 or v.max() > 1.0:
        raise ValueError(f"value outside [0,1] inside the footprint: min={v.min()}, max={v.max()}")


def write_geotiff(pred: np.ndarray, template: Path | str, out: Path | str, *, outside: str = "nan") -> Path:
    if outside not in ("nan", "zero"):
        raise ValueError("outside must be 'nan' or 'zero'")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(template) as t:
        profile = t.profile.copy()
        foot = np.isfinite(t.read(1))
    if foot.sum() != grid.FOOTPRINT_PX:
        raise ValueError("template footprint differs from the competition footprint")
    pred = np.asarray(pred)
    if pred.shape != foot.shape:
        raise ValueError("prediction shape differs from the template")
    check_probabilities(pred, foot)
    arr = np.where(foot, pred.astype(np.float32), np.float32(np.nan) if outside == "nan" else np.float32(0))
    arr = arr.astype(np.float32)
    arr[arr == 0] = 0.0  # canonicalise -0.0
    profile.update(driver="GTiff", dtype="float32", count=1,
                   nodata=(np.nan if outside == "nan" else None), compress="lzw")
    with rasterio.open(out, "w", **profile) as dst:
        dst.write(arr, 1)
        dst.update_tags(AREA_OR_POINT="Area")
    return out


def zip_single(tif: Path | str, zip_path: Path | str | None = None) -> Path:
    tif = Path(tif)
    zip_path = Path(zip_path) if zip_path else tif.with_suffix(".zip")
    if tif.suffix.lower() != ".tif" or not tif.is_file():
        raise ValueError("ZIP input must be an existing .tif")
    info = zipfile.ZipInfo(tif.name, date_time=(2026, 10, 2, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr(info, tif.read_bytes(), compresslevel=9)
    with zipfile.ZipFile(zip_path) as z:
        if z.namelist() != [tif.name] or z.read(tif.name) != tif.read_bytes():
            raise ValueError("ZIP does not contain exactly the single GeoTIFF")
    return zip_path


def verify_geotiff(path: Path | str, template: Path | str) -> dict[str, Any]:
    """Independent re-read of a submission file under several plausible validator interpretations."""
    path = Path(path)
    with rasterio.open(template) as t:
        t_arr = t.read(1)
        foot = np.isfinite(t_arr)
        t_prof = t.profile
    with rasterio.open(path) as s:
        a = s.read(1)
        ma = s.read(1, masked=True)
        info = dict(crs=s.crs, shape=s.shape, transform=tuple(s.transform)[:6], count=s.count,
                    dtype=s.dtypes[0], nodata=s.nodata, bounds=tuple(s.bounds),
                    compress=str(s.compression), driver=s.driver)
    inside, outside = a[foot], a[~foot]
    nodata_nan = info["nodata"] is not None and np.isnan(info["nodata"])
    checks: dict[str, dict[str, Any]] = {}

    def add(name: str, ok: bool, detail: str, hard: bool = True) -> None:
        checks[name] = {"pass": bool(ok), "detail": detail, "hard": hard}

    add("grid_matches_template", info["crs"] is not None and info["crs"].to_epsg() == grid.CRS_EPSG
        and info["shape"] == grid.SHAPE and info["transform"] == grid.TRANSFORM
        and info["bounds"] == grid.BOUNDS, f"{info['crs']} {info['shape']} {info['transform']}")
    add("single_band_float32", info["count"] == 1 and info["dtype"] == "float32",
        f"count={info['count']} dtype={info['dtype']}")
    add("inside_footprint_all_finite", bool(np.isfinite(inside).all()),
        f"{int((~np.isfinite(inside)).sum())} non-finite inside {inside.size} px")
    add("inside_footprint_in_0_1", bool(inside.size and inside.min() >= 0.0 and inside.max() <= 1.0),
        f"min={float(inside.min()):.8g} max={float(inside.max()):.8g}")
    add("no_infinities_anywhere", not bool(np.isinf(a).any()), "np.isinf(whole array) is empty")
    n_out_nan = int(np.isnan(outside).sum())
    if nodata_nan:
        add("outside_footprint_is_nan", n_out_nan == outside.size,
            f"{n_out_nan}/{outside.size} NaN outside the footprint (as in the sample)")
        add("nodata_tag_is_nan", True, "nodata=NaN declared, same as the sample submission")
        add("masked_read_in_0_1", bool(ma.count() == inside.size and ma.min() >= 0 and ma.max() <= 1),
            f"masked count={int(ma.count())}, min={float(ma.min()):g}, max={float(ma.max()):g}")
        add("nan_aware_range_in_0_1", bool(np.nanmin(a) >= 0.0 and np.nanmax(a) <= 1.0),
            f"nanmin={float(np.nanmin(a)):g} nanmax={float(np.nanmax(a)):g}")
        add("strict_whole_array_range_ignoring_nan_is_informational",
            bool(((a >= 0) & (a <= 1)).all()),
            "A validator that compares NaN directly would fail ANY file with NaN outside the footprint, "
            "including the sample. Informational only; use the allfinite fallback if the portal rejects.",
            hard=False)
    else:
        add("outside_footprint_is_zero_and_finite", bool(np.isfinite(outside).all() and (outside == 0).all()),
            "zeros outside the footprint, no NaN anywhere (fallback variant)")
        add("strict_whole_array_range", bool(np.isfinite(a).all() and a.min() >= 0 and a.max() <= 1),
            f"whole-array min={float(a.min()):g} max={float(a.max()):g}")
    add("profile_driver_gtiff", info["driver"] == "GTiff", info["driver"], hard=False)
    add("compression_like_sample", info["compress"].lower().endswith("lzw")
        or str(t_prof.get("compress", "")).lower() == "lzw", info["compress"], hard=False)
    hard_fail = [k for k, v in checks.items() if v["hard"] and not v["pass"]]
    return {"file": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path),
            "variant": "nan" if nodata_nan else "allfinite", "checks": checks,
            "hard_checks_passed": not hard_fail, "hard_failures": hard_fail,
            "nonzero_inside_px": int((inside > 0).sum()), "value_set_inside": sorted(set(np.unique(inside).tolist()))[:6]}


def scored_content_id(pred: np.ndarray, footprint: np.ndarray, catalogue: np.ndarray) -> str:
    v = np.asarray(pred)[np.asarray(footprint, bool) & ~np.asarray(catalogue, bool)].astype("<f4").copy()
    v[v == 0] = 0
    return hashlib.sha256(v.tobytes()).hexdigest()[:12]


def make_filename(family: str, slug: str, date: str, cid: str, outside: str) -> str:
    s = "".join(c if c.isalnum() else "-" for c in slug.lower()).strip("-")
    while "--" in s:
        s = s.replace("--", "-")
    return f"{family}-{s}-{date}-{cid}-{outside}.tif"


def make_note(hyp: str, summary: str, cid: str, family: str = "27GEMSDOE", status: str = "not yet live-scored") -> str:
    prefix, suffix = f"{family} {hyp} | ", f" | id {cid} | {status}"
    room = 200 - len(prefix) - len(suffix)
    if room < 1:
        raise ValueError("identifiers too long for a 200-character note")
    note = f"{prefix}{summary[:room]}{suffix}"
    assert len(note) <= 200
    return note


def dump_json(obj: Any, path: Path | str) -> None:
    Path(path).write_text(json.dumps(obj, indent=2, default=float) + "\n")
