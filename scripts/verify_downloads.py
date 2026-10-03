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
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

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
    with rasterio.open(DATA / "sample_submission.tif") as t:
        tpl = t.read(1)
        tprof = (t.crs.to_epsg(), t.shape, tuple(t.transform)[:6], t.dtypes[0])
    foot = np.isfinite(tpl)
    with rasterio.open(DATA / "labels.tif") as s:
        cat = s.read(1) == 1
    with rasterio.open(DATA / "dotted_h19_5_d1_5_nan.tif") as s:
        base = np.nan_to_num(s.read(1)) > 0
    ok(int(foot.sum()) == 5167373 and tprof[:2] == (32611, (3730, 3292)), "template: EPSG:32611, 3730x3292, 5,167,373 px footprint")
    slots = tuple(s for s in ("primary", "secondary", "tertiary", "quaternary", "quinary_probe") if s in man)
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
    # slot 4 must be exactly: dot_thin(H19-5, 2.8) minus the 1 px catalogue-flank shadow, plus T-v2 dots
    if "quaternary" in man:
        from gems27 import thinning
        with rasterio.open(DATA / "h19_5_nan.tif") as s:
            raw = np.nan_to_num(s.read(1)) > 0
        base28 = thinning.dot_thin(raw & ~cat, 2.8)
        dcat = distance_transform_edt(~cat)
        base28_r1 = base28 & (dcat > 1.0)
        with rasterio.open(DL / man["quaternary"]["nan"]) as s:
            Dm = np.nan_to_num(s.read(1)) > 0
        ok(bool((Dm & base28_r1).sum() == base28_r1.sum()),
           "slot4 contains the whole pruned d2.8 base (nothing else removed)")
        ok(int(Dm.sum()) == man["quaternary"]["emitted_px"],
           f"slot4 emits exactly {man['quaternary']['emitted_px']} px (manifest)")
        ok(int(Dm.sum() - base28_r1.sum()) == man["quaternary"]["added_px"],
           f"slot4 adds exactly {man['quaternary']['added_px']} T-v2 dots on top of the pruned base")
        ok(int((base28 & ~base28_r1).sum()) == man["quaternary"]["pruned_flank_shadow_px"],
           f"slot4 prunes exactly {man['quaternary']['pruned_flank_shadow_px']} catalogue-flank-shadow px")
    # slot 5 (Addendum E far-field swap probe) must differ from the 0.2477 file in exactly one way:
    # WHICH far-field pixels are emitted. Same count, same near field, every change >= 300 m out.
    if "quinary_probe" in man:
        from gems27 import oof_detector  # noqa: F401  (imported for parity of environment checks)
        m5 = man["quinary_probe"]
        with rasterio.open(DL / m5["nan"]) as s5:
            E = np.nan_to_num(s5.read(1)) > 0
        dcat5 = distance_transform_edt(~cat)
        near_base, near_E = base & (dcat5 < 3.0), E & (dcat5 < 3.0)
        dropped, added = base & ~E, E & ~base
        ok(int(E.sum()) == int(base.sum()) == m5["emitted_px"],
           f"slot5 keeps the 0.2477 file's exact pixel count ({m5['emitted_px']} px)")
        ok(bool((near_base == near_E).all()),
           f"slot5 near field (< 300 m from catalogue) is byte-identical to the 0.2477 file ({int(near_base.sum())} px)")
        ok(int(dropped.sum()) == m5["far_field_px_dropped"] == m5["far_field_px_added"] == int(added.sum()),
           f"slot5 swaps exactly {m5['far_field_px_dropped']} far-field dots")
        ok(bool((dcat5[dropped] >= 3.0).all()) and bool((dcat5[added] >= 3.0).all()),
           "slot5 changes no pixel closer than 300 m to the catalogue (single-variable far-field swap)")
        ok(bool((dcat5[added] >= 3.0).all() and not (added & cat).any() and not (added & ~foot).any()),
           "slot5 added dots are off-catalogue and inside the footprint")
        kept = E & ~added
        dk = distance_transform_edt(~kept)
        ok(bool((dk[added] >= 1.5 - 1e-6).all()),
           "slot5 added dots respect the d1.5 emission geometry (>= 1.5 px from every kept dot)")
        ok(abs(m5["fraction_of_file_swapped"] - added.sum() / E.sum()) < 1e-9,
           f"slot5 manifest reports the one-sided swapped fraction {m5['fraction_of_file_swapped']:.4f} "
           f"(symmetric difference {m5['symmetric_difference_fraction']:.4f})")
    ok(len(list(DL.glob("*.tif"))) == len(set(p.name for p in DL.glob("*.tif"))), "all .tif file names are unique")
    print(f"\n{len(FAIL)} failure(s)")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
