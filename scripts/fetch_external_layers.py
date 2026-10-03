#!/usr/bin/env python3
"""Fetch, hash-verify, inventory and footprint-clip the official external layers this repo cannot reach.

Runs inside GitHub Actions (`.github/workflows/fetch-gdr-external-layers.yml`) because the agent
sandbox can only reach github.com / api.github.com / pypi.org. Every download is verified against a
SHA-256 and byte size recorded by an independent runner on 2026-09-30 in the sibling repository
`buffedlizard55-lab/16GEMSDOE`, `evidence/ci/external_verification.json` - so a silently changed or
truncated file fails loudly instead of becoming a "layer".

It writes:
  <out>/inventory.json                  provenance, hashes, layer schemas, in-footprint counts
  <out>/<dataset>_<layer>.csv           native attributes + EPSG:32611 x/y + 100 m grid row/col
and, with --availability-only true, HEAD-checks the larger sources (no download) so a future session
can say "obtainable, verified <date>" instead of guessing.

This script never contacts drivendata.org (competition Terms of Use prohibit automated access).
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

UA = "GEMSDOE27-research/1.0 (geothermal fault mapping; contact: repository owner)"

# Competition footprint grid, read from the organisers' own sample_submission.tif (SHA-256
# 2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc) inside a session and frozen here
# so the runner does not need the 590 MB data cache.
FOOTPRINT = {
    "crs": "EPSG:32611", "width": 3292, "height": 3730, "pixel_m": 100.0,
    "transform": [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0],
    "bounds_utm11n": [243350.0, 4135550.0, 572550.0, 4508550.0],
    "bounds_wgs84": [-120.03717095080793, 37.33119286569775, -116.14092181157623, 40.72787799633184],
    "template_sha256": "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc",
}

# Hash pins: sibling 16GEMSDOE evidence/ci/external_verification.json (runner-verified 2026-09-30).
PINS = {
    "paleo": {
        "title": "GDR 1391 paleo-geothermal (sinter/tufa, travertine, altered bedrock) regional points",
        "url": "https://gdr.openei.org/files/1391/paleo_geothermal_regional.zip",
        "bytes": 84008,
        "sha256": "faffcf697f32dbbf6cbb317cd1effb3e305538ce38eb239d72d0c6fa071e91ca",
        "why": "Surface geothermal evidence (sinter/tufa, hydrothermal alteration) marks fault-hosted "
               "fluid pathways that are Quaternary-active but need not be mapped as faults. Proposed as "
               "a detector FEATURE (never as an emission habitat: h18-4 refuted bedrock-map-gap "
               "emission at 1.6x blind, evidence/sgmc_gap_inversion.json).",
    },
    "probes": {
        "title": "GDR 1391 INGENIOUS 2 m temperature-probe regional data",
        "url": "https://gdr.openei.org/files/1391/2m_temperature_probe_INGENIOUS_regional_data.zip",
        "bytes": 1080530,
        "sha256": "1301f70d230058e616ea5d34d1c7a32fabf7d49198172f376c59c89bd652eca3",
        "why": "Shallow (2 m) soil/sediment temperature anomalies are a direct, independently measured "
               "signature of permeable fault zones; not present in any layer this repo holds.",
    },
    "volcanics": {
        "title": "GDR 1391 Great Basin Quaternary volcanics (polygons)",
        "url": "https://gdr.openei.org/files/1391/great_basin_q_volcanics.zip",
        "bytes": 9898770,
        "sha256": "c4a2d2dfd5c44f42e0aba37290948881631aff312b8b9ca7934b6dc1e451e5be",
        "why": "Quaternary volcanic units are cut by, and their vents sit on, young faults; unit "
               "boundaries and vent alignments are an independent map of Quaternary deformation. This "
               "repo currently holds only 21 vent points, not the polygons.",
    },
}

# Larger / other sources: HEAD-checked only, so a session can state obtainability without a download.
AVAILABILITY = [
    {"key": "wellspring_gdb", "url": "https://gdr.openei.org/files/1391/wellspringdata.gdb.zip",
     "bytes": 20810222, "sha256": "7222178427ce0634453846819e6482fd6867536534fe9600987099e3b356590f",
     "note": "already clipped into data_cache/gdr_wellspring_in_footprint.csv (27,092 rows)"},
    {"key": "qfaults_v2", "url": "https://gdr.openei.org/files/1391/qfaults_ingenious_nad83conus117_2023-06-27.zip",
     "sha256": "c7b091c9ac8bca140ad89ee6bb2bd63dd3ac12e3013acbfd8373d11c9faee59d",
     "note": "already clipped into data_cache/qfaults_v2_in_footprint.json (1,179 polylines)"},
    {"key": "qfaults_v1", "url": "https://gdr.openei.org/files/1391/faults_quaternary_INGENIOUS_regional_data.zip",
     "sha256": "13e851e3618486d1ce8cdcaf238cbf7c5e290805dacee698e479ba3052f53a2a", "note": "older release"},
    {"key": "sgmc_nv", "url": "https://mrdata.usgs.gov/geology/state/shp/NV.zip",
     "sha256": "3b333ac025e59aae7f0d827db45ba32c425cf867eb341561a788af1de186b76b",
     "note": "USGS State Geologic Map Compilation; emission on its gap is LIVE-REFUTED (h18-4, 0.0360)"},
    {"key": "sgmc_ca", "url": "https://mrdata.usgs.gov/geology/state/shp/CA.zip",
     "sha256": "78765ba4428df9f25a84f86e0b2529bd0508fc8a2cf65d2f41a830e82bccfd58", "note": "as above"},
    {"key": "siler_2022_doi", "url": "https://doi.org/10.5066/P9YL58W6",
     "note": "Siler et al. 2022 - fault slip/dilation tendency surfaces; landing page only"},
    {"key": "deangelo_2022_doi", "url": "https://doi.org/10.5066/P9BZPVUC",
     "note": "DeAngelo et al. 2022 - landing page only"},
    {"key": "sciencebase_657e1d85", "url": "https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7",
     "note": "GeoDAWN airborne geophysics item page"},
]


def fetch(url: str, dest: Path | None = None, timeout: int = 180, retries: int = 3) -> bytes:
    last: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read()
            if dest is not None:
                dest.write_bytes(data)
            return data
        except Exception as e:                                    # noqa: BLE001
            last = e
            print(f"  attempt {attempt}/{retries} failed for {url}: {e}", flush=True)
            time.sleep(3 * attempt)
    raise RuntimeError(f"could not fetch {url}") from last


def head_check(url: str, timeout: int = 60) -> dict:
    out: dict = {"url": url}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Range": "bytes=0-0"}, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            out["http_status"] = r.status
            out["content_type"] = r.headers.get("Content-Type")
            cr = r.headers.get("Content-Range")
            out["content_length_bytes"] = (int(cr.split("/")[-1]) if cr and "/" in cr
                                           else (int(r.headers["Content-Length"]) if r.headers.get("Content-Length") else None))
            out["last_modified"] = r.headers.get("Last-Modified")
            out["reachable"] = True
    except urllib.error.HTTPError as e:
        out.update({"http_status": e.code, "reachable": e.code < 500,
                    "content_length_bytes": (int(e.headers["Content-Length"])
                                             if e.headers.get("Content-Length") else None),
                    "last_modified": e.headers.get("Last-Modified"),
                    "note": f"HTTP {e.code} (a 403/405 on a range request still proves the object exists)"})
    except Exception as e:                                        # noqa: BLE001
        out.update({"reachable": False, "error": str(e)})
    return out


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def process_dataset(key: str, pin: dict, out_dir: Path) -> dict:
    rec = {"key": key, **{k: pin[k] for k in ("title", "url", "sha256")}, "why": pin["why"]}
    if "bytes" in pin:
        rec["bytes_expected"] = pin["bytes"]
    try:
        data = fetch(pin["url"])
    except Exception as e:                                        # noqa: BLE001
        rec.update({"ok": False, "error": f"download failed: {e}"})
        return rec
    rec["bytes_downloaded"] = len(data)
    rec["sha256_actual"] = sha256(data)
    rec["sha256_matches_pin"] = rec["sha256_actual"] == pin["sha256"]
    rec["bytes_match_pin"] = ("bytes" not in pin) or (len(data) == pin["bytes"])
    if not (rec["sha256_matches_pin"] and rec["bytes_match_pin"]):
        rec.update({"ok": False,
                    "error": "HASH/SIZE MISMATCH against the 2026-09-30 pin - refusing to use this file"})
        return rec
    rec["ok"] = True

    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
        rec["zip_entries"] = [{"name": i.filename, "bytes": i.file_size} for i in zf.infolist()]
    except Exception as e:                                        # noqa: BLE001
        rec.update({"ok": False, "error": f"not a readable zip: {e}"})
        return rec

    # read every vector layer with pyogrio (GDAL wheels: shapefile and FileGDB both work).
    # If the reader is unavailable the hash/size verification and the zip inventory above still stand:
    # that is the provenance part of this workflow, and it must not be lost to a dependency problem.
    try:
        from pyogrio import list_layers, read_dataframe, read_info
        from pyproj import Transformer
    except Exception as e:                                        # noqa: BLE001
        rec.update({"layers": [], "reader_error": f"pyogrio/pyproj unavailable: {e}",
                    "note": "hash and zip inventory verified; vector reading needs the workflow's pip step"})
        return rec

    tmp = out_dir / f"_zip_{key}"
    tmp.mkdir(parents=True, exist_ok=True)
    zf.extractall(tmp)
    # every vector layer in the archive: shapefiles and FileGDB directories
    targets = sorted({q for q in tmp.rglob("*") if q.suffix.lower() == ".shp"} |
                     {q for q in tmp.rglob("*.gdb") if q.is_dir()})
    rec["layers"] = []
    rec["clip_rule"] = ("feature kept if its CENTROID falls inside the footprint bounding box "
                        "(EPSG:32611 243350-572550 E, 4135550-4508550 N) and its 100 m grid row/col "
                        "is inside the 3730 x 3292 grid; polygon parts straddling the boundary are "
                        "therefore counted once, by centroid, and the CSV keeps native attributes only")
    tr = Transformer.from_crs("EPSG:4326", "EPSG:32611", always_xy=True)
    x0, y0, x1, y1 = FOOTPRINT["bounds_utm11n"]
    for t in targets:
        try:
            names = [n for n, _ in list_layers(str(t))]
        except Exception as e:                                    # noqa: BLE001
            rec["layers"].append({"path": str(t.relative_to(tmp)), "error": str(e)})
            continue
        for name in names:
            entry: dict = {"path": str(t.relative_to(tmp)), "layer": name}
            try:
                info = read_info(str(t), layer=name)
                entry.update({"features": info.get("features"), "crs": str(info.get("crs")),
                              "geometry_type": info.get("geometry_type"),
                              "columns": list(info.get("fields", []))})
                gdf = read_dataframe(str(t), layer=name)
                gdf = gdf.to_crs("EPSG:4326") if gdf.crs is not None else gdf
                xs, ys = zip(*[(g.x, g.y) for g in gdf.geometry.centroid])
                ux, uy = tr.transform(list(xs), list(ys))
                gdf = gdf.assign(utm11n_x=ux, utm11n_y=uy)
                gdf["grid_row"] = ((FOOTPRINT["transform"][5] - gdf.utm11n_y) / 100.0).astype("Int64")
                gdf["grid_col"] = ((gdf.utm11n_x - FOOTPRINT["transform"][2]) / 100.0).astype("Int64")
                inside = ((gdf.utm11n_x >= x0) & (gdf.utm11n_x < x1) & (gdf.utm11n_y >= y0)
                          & (gdf.utm11n_y < y1) & gdf.grid_row.between(0, FOOTPRINT["height"] - 1)
                          & gdf.grid_col.between(0, FOOTPRINT["width"] - 1))
                entry["features_in_footprint_bbox"] = int(inside.sum())
                csv_path = out_dir / f"{key}_{name.replace(':', '_').replace('/', '_')}.csv"
                gdf.loc[inside].drop(columns="geometry").to_csv(csv_path, index=False)
                entry["csv"] = csv_path.name
                entry["csv_rows"] = int(inside.sum())
            except Exception as e:                                # noqa: BLE001
                entry["error"] = f"{type(e).__name__}: {e}"
            rec["layers"].append(entry)
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", default="paleo,probes,volcanics")
    ap.add_argument("--availability-only", default="true")
    ap.add_argument("--out", required=True)
    ap.add_argument("--pins", default=None, help="write the pin table used (provenance for the log)")
    args = ap.parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    wanted = [d.strip() for d in args.datasets.split(",") if d.strip()]
    if wanted == ["all"]:
        wanted = list(PINS)
    unknown = [w for w in wanted if w not in PINS]
    if unknown:
        print(f"unknown dataset keys {unknown}; known: {list(PINS)}", file=sys.stderr)

    inv = {"generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "runner": "github-actions", "footprint": FOOTPRINT,
           "pin_provenance": ("SHA-256 and byte sizes recorded by an independent runner on 2026-09-30 in "
                              "buffedlizard55-lab/16GEMSDOE evidence/ci/external_verification.json"),
           "datasets": [], "availability": []}
    for key in wanted:
        if key not in PINS:
            continue
        print(f"=== {key}: {PINS[key]['title']}", flush=True)
        rec = process_dataset(key, PINS[key], out_dir)
        inv["datasets"].append(rec)
        print(f"    ok={rec.get('ok')} bytes={rec.get('bytes_downloaded')} "
              f"sha_match={rec.get('sha256_matches_pin')} layers={len(rec.get('layers', []))}", flush=True)

    if str(args.availability_only).lower() in ("true", "1", "yes"):
        for a in AVAILABILITY:
            print(f"--- availability: {a['key']}", flush=True)
            rec = head_check(a["url"])
            rec.update({"key": a["key"], "note": a.get("note")})
            if "sha256" in a:
                rec["sha256_pinned"] = a["sha256"]
            if "bytes" in a:
                rec["bytes_pinned"] = a["bytes"]
            inv["availability"].append(rec)

    (out_dir / "inventory.json").write_text(json.dumps(inv, indent=1))
    if args.pins:
        Path(args.pins).write_text(json.dumps({"pins": PINS, "availability": AVAILABILITY,
                                               "footprint": FOOTPRINT}, indent=1))
    ok = all(d.get("ok") for d in inv["datasets"]) if inv["datasets"] else False
    print(json.dumps({"datasets_ok": ok,
                      "summary": {d["key"]: {"ok": d.get("ok"), "sha256_matches_pin": d.get("sha256_matches_pin"),
                                             "layers": len(d.get("layers", []))} for d in inv["datasets"]}},
                     indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
