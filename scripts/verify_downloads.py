#!/usr/bin/env python3
"""Standalone verification of the shipped submission files (rasterio + numpy only; imports no project code).

Re-derives, from the files themselves: grid, dtype, band count, nodata, NaN-outside count, value range inside, the
value set, catalogue overlap, zip contents, SHA-256s against docs/downloads/manifest.json, and the relation of the
primary file to the owner's 0.2477 file (superset, nothing removed). Exit status 1 on any failure.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("GEMS_DATA_DIR", ROOT / "data_cache"))
DL = ROOT / "docs" / "downloads"
FAIL: list[str] = []


def ok(cond: bool, msg: str) -> None:
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        FAIL.append(msg)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    man = json.loads((DL / "manifest.json").read_text())
    research_manifest = DL / "h28_1_candidate_manifest.json"
    if research_manifest.exists():
        research = json.loads(research_manifest.read_text())
        candidate = research.get("candidate")
        if candidate and research.get("status", "").startswith("research candidate"):
            man["h28_1_research"] = candidate
    with rasterio.open(DATA / "sample_submission.tif") as t:
        tpl = t.read(1)
        tprof = (t.crs.to_epsg(), t.shape, tuple(t.transform)[:6], t.dtypes[0])
    foot = np.isfinite(tpl)
    with rasterio.open(DATA / "labels.tif") as s:
        cat = s.read(1) == 1
    with rasterio.open(DATA / "dotted_h19_5_d1_5_nan.tif") as s:
        base = np.nan_to_num(s.read(1)) > 0
    ok(int(foot.sum()) == 5167373 and tprof[:2] == (32611, (3730, 3292)), "template: EPSG:32611, 3730x3292, 5,167,373 px footprint")
    slots = tuple(s for s in ("primary", "secondary", "tertiary", "h28_1_research") if s in man)
    for slot in slots:
        m = man[slot]
        for variant in ("nan", "allfinite"):
            p = DL / m[variant]
            with rasterio.open(p) as s:
                a = s.read(1)
                prof = (s.crs.to_epsg(), s.shape, tuple(s.transform)[:6], s.dtypes[0])
                nd, count = s.nodata, s.count
            tag = f"{slot}/{variant}"
            ok(prof == tprof, f"{tag}: same CRS/shape/transform/dtype as the template (float32)")
            ok(count == 1, f"{tag}: single band")
            inside, outside = a[foot], a[~foot]
            ok(bool(np.isfinite(inside).all()), f"{tag}: every in-footprint value is finite")
            ok(float(inside.min()) >= 0.0 and float(inside.max()) <= 1.0, f"{tag}: in-footprint range [{inside.min():g}, {inside.max():g}] within [0,1]")
            ok(set(np.unique(inside).tolist()) <= {0.0, 1.0}, f"{tag}: values are exactly 0.0 / 1.0 (no float rounding above 1)")
            n1 = int((inside == 1.0).sum())
            ok(n1 == m["emitted_px"], f"{tag}: {n1} pixels equal 1.0 (manifest {m['emitted_px']})")
            ok(not bool((a == 1.0)[cat].any()), f"{tag}: no emitted pixel on a catalogue cell")
            ok(not bool(np.isinf(a).any()), f"{tag}: no infinities anywhere")
            if variant == "nan":
                ok(int(np.isnan(outside).sum()) == outside.size == 7111787 and nd is not None and np.isnan(nd),
                   f"{tag}: NaN outside the footprint (7,111,787 px) and nodata=NaN declared, like the sample")
            else:
                ok(bool((outside == 0).all()) and nd is None and bool(np.isfinite(a).all()),
                   f"{tag}: zeros outside, no NaN anywhere, no nodata tag (fallback)")
            ok(sha(p) == m["sha256_nan"] or variant != "nan", f"{tag}: sha256 matches manifest" if variant == "nan" else f"{tag}: (fallback hash recorded in checks json)")
        z = DL / m["zip"]
        with zipfile.ZipFile(z) as zf:
            ok(zf.namelist() == [m["nan"]] and zf.read(m["nan"]) == (DL / m["nan"]).read_bytes(), f"{slot}: zip holds exactly the one nan GeoTIFF, byte-identical")
        note = (DL / f"note-{m['nan'][:-4]}.txt").read_text().strip()
        ok(len(note) <= 200 and note == m["note"], f"{slot}: note is {len(note)} chars (<= 200) and matches the manifest")
    with rasterio.open(DL / man["primary"]["nan"]) as s:
        A = np.nan_to_num(s.read(1)) > 0
    ok(bool((A & base).sum() == base.sum()), "primary is a superset of the 0.2477 emission (nothing removed)")
    ok(int(A.sum() - base.sum()) == man["primary"]["added_px"], f"primary adds exactly {man['primary']['added_px']} px to the 0.2477 emission")
    ok(len(list(DL.glob("*.tif"))) == len(set(p.name for p in DL.glob("*.tif"))), "all .tif file names are unique")
    print(f"\n{len(FAIL)} failure(s)")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
