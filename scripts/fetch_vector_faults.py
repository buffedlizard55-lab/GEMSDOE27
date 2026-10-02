#!/usr/bin/env python3
"""Verify or fetch the NBMG INGENIOUS Quaternary Faults vector dataset (`Qfaults [INGENIOUS 6-27-2023]`).

In the sandboxed container, `--verify-local` (default) verifies `data_cache/qfaults_v2_in_footprint.json`
against `data/manifest.json` and writes `docs/data/vector_faults_status.json`.
On a GitHub-hosted runner (`.github/workflows/fetch-vector-faults.yml`), `--fetch-arcgis` queries the public
NBMG ArcGIS REST endpoint (`MapServer/0/query`, `outSR=32611`) in 1,000-record pages for the GeoDAWN envelope.
Never requests drivendata.org.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = ("drivendata.org",)
ARCGIS_LAYER = "https://web2.nbmg.unr.edu/arcgis/rest/services/Qfaults/Qfaults_INGENIOUS/MapServer/0"
BBOX_32611 = "243350,4135550,572550,4508550"
OUT_FIELDS = "FID,FTYPE_,NAME,AGE,SLIPRATE,SLIPSENSE,DIPDIRECT,MAPPEDSCAL,NUM, Shape_Leng"
UA = "GEMSDOE27-vector-faults/1.0 (+https://github.com/buffedlizard55-lab/GEMSDOE27)"


def guard(url: str) -> None:
    host = (urlparse(url).hostname or "").lower()
    if any(host == h or host.endswith("." + h) for h in FORBIDDEN):
        raise SystemExit(f"refusing to request {host}")


def fetch_arcgis_bbox() -> dict:
    guard(ARCGIS_LAYER)
    features = []
    offset = 0
    fields = []
    while True:
        params = {
            "geometry": BBOX_32611,
            "geometryType": "esriGeometryEnvelope",
            "inSR": "32611",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": OUT_FIELDS,
            "returnGeometry": "true",
            "outSR": "32611",
            "resultOffset": str(offset),
            "resultRecordCount": "1000",
            "f": "json",
        }
        url = f"{ARCGIS_LAYER}/query?{urlencode(params)}"
        guard(url)
        req = Request(url, headers={"User-Agent": UA})
        with urlopen(req, timeout=30) as resp:  # noqa: S310
            payload = json.loads(resp.read().decode("utf-8"))
        if not fields and "fields" in payload:
            fields = payload["fields"]
        batch = payload.get("features", [])
        features.extend(batch)
        if not payload.get("exceededTransferLimit") or not batch:
            break
        offset += len(batch)
    return {"fields": fields, "features": features}


def summarize_local(path: Path) -> dict:
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    data = json.loads(raw)
    feats = data.get("features", [])
    ftype = Counter((f.get("attributes") or {}).get("FTYPE_", "") for f in feats)
    slipsense = Counter((f.get("attributes") or {}).get("SLIPSENSE", "") for f in feats)
    dipdirect = Counter((f.get("attributes") or {}).get("DIPDIRECT", "") for f in feats)
    names = {
        ((f.get("attributes") or {}).get("NAME") or "").strip()
        for f in feats
        if ((f.get("attributes") or {}).get("NAME") or "").strip()
    }
    return {
        "verified_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_endpoint": ARCGIS_LAYER,
        "local_file": str(path.relative_to(ROOT)),
        "bytes": len(raw),
        "sha256": sha,
        "feature_count": len(feats),
        "distinct_named_fault_zones": len(names),
        "ftype_counts": dict(ftype),
        "slipsense_counts": dict(slipsense),
        "dipdirect_counts": dict(dipdirect),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch-arcgis", action="store_true", help="Fetch fresh features from NBMG ArcGIS REST")
    args = ap.parse_args()

    cache_path = ROOT / "data_cache" / "qfaults_v2_in_footprint.json"
    if args.fetch_arcgis:
        payload = fetch_arcgis_bbox()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(payload))

    if not cache_path.exists():
        raise SystemExit(f"missing {cache_path}; run python3 scripts/restore_data.py first")

    man = json.loads((ROOT / "data" / "manifest.json").read_text())
    expected_sha = next(
        f["sha256"]
        for f in man["files"]
        if (f.get("local") or Path(f["path"]).name) == "qfaults_v2_in_footprint.json"
    )
    status = summarize_local(cache_path)
    status["matches_manifest_sha256"] = status["sha256"] == expected_sha
    if not args.fetch_arcgis and not status["matches_manifest_sha256"]:
        raise SystemExit(f"SHA-256 mismatch on {cache_path}: {status['sha256']} != {expected_sha}")

    out_path = ROOT / "docs" / "data" / "vector_faults_status.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps(status, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
