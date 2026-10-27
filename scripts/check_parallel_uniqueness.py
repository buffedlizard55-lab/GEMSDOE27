#!/usr/bin/env python3
"""Compare a surface or final binary raster with the hash-bound parallel registry.

Use --surface-only before placement and run again without it for final dots. Undefined
correlations, missing or altered peers, a stale manifest, and grid mismatches fail closed.
This checks the pinned registry only; it cannot certify uniqueness against unknown or newer files.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems27 import paths, uniqueness  # noqa: E402

RANK_STOP = 0.90
OVERLAP_STOP = 0.70


def read_candidate(path: Path, template: Path) -> tuple[np.ndarray, np.ndarray]:
    with rasterio.open(template) as t:
        foot = np.isfinite(t.read(1))
        expected = (t.crs, t.shape, t.transform)
    with rasterio.open(path) as s:
        if (s.crs, s.shape, s.transform) != expected or s.count != 1:
            raise ValueError(f"candidate grid mismatch: {path}")
        data = s.read(1)
    inside = data[foot]
    if not np.isfinite(inside).all() or np.any((inside < 0) | (inside > 1)):
        raise ValueError("candidate contains non-finite or out-of-range values inside footprint")
    return data, foot


def validated_manifest(manifest_path: Path, template: Path, registry_path: Path) -> dict:
    manifest = json.loads(manifest_path.read_text())
    registry = json.loads(registry_path.read_text())
    if manifest.get("registry_sha256") != uniqueness.sha256_file(registry_path):
        raise ValueError("parallel cache manifest is stale for the registry")
    if manifest.get("template_sha256") != uniqueness.sha256_file(template):
        raise ValueError("parallel cache manifest uses a different template")
    entries = manifest.get("entries", [])
    required_entries = registry.get("entries", [])
    if not isinstance(entries, list) or not isinstance(required_entries, list) or not required_entries:
        raise ValueError("parallel registry or cache manifest is empty or malformed")
    if any(not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"]
           for row in entries + required_entries):
        raise ValueError("parallel registry or manifest has an invalid id")
    actual = [row["id"] for row in entries]
    required = [row["id"] for row in required_entries]
    if len(actual) != len(set(actual)) or len(required) != len(set(required)) or set(actual) != set(required):
        raise ValueError("parallel cache manifest is incomplete or has duplicate entries")
    for row in entries:
        if (not isinstance(row.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", row["sha256"])
                or not isinstance(row.get("local"), str) or not row["local"]
                or Path(row["local"]).is_absolute()):
            raise ValueError(f"missing or invalid reference hash/path: {row['id']}")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--cache-manifest", type=Path, default=paths.DATA / "parallel_registry" / "cache_manifest.json")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--surface-only", action="store_true")
    args = parser.parse_args()
    data, foot = read_candidate(args.candidate, paths.TEMPLATE)
    manifest = validated_manifest(args.cache_manifest, paths.TEMPLATE,
                                  paths.REGISTRY / "parallel_submission_registry.json")
    if not args.surface_only and np.any((data[foot] != 0) & (data[foot] != 1)):
        raise ValueError("final-dot screen requires an exact binary raster")
    ranks, mean, std = uniqueness.surface_ranks(data, foot)
    cache_root = args.cache_manifest.parent.parent.resolve()
    rows = []
    for item in manifest["entries"]:
        reference_path = (cache_root / item["local"]).resolve()
        if not reference_path.is_relative_to(cache_root):
            raise ValueError(f"unsafe registry cache path: {item['local']}")
        ref = uniqueness.read_reference(reference_path, paths.TEMPLATE, foot, item["sha256"])
        rho = uniqueness.surface_binary_spearman(ranks, mean, std, ref[foot])
        result = {"id": item["id"], "reference_sha256": item["sha256"],
                  "spearman_rank_correlation": rho}
        if not args.surface_only:
            result["candidate_dot_fraction_within_3px"] = uniqueness.dot_comparison(data == 1, ref, foot)[
                "dot_overlap_within_3px"]
        result["duplicate"] = abs(rho) > RANK_STOP or (
            not args.surface_only and result["candidate_dot_fraction_within_3px"] > OVERLAP_STOP
        )
        rows.append(result)
    duplicates = [r["id"] for r in rows if r["duplicate"]]
    report = {"candidate": args.candidate.name, "candidate_sha256": uniqueness.sha256_file(args.candidate),
              "surface_only": args.surface_only,
              "thresholds": {"abs_rank_correlation_gt": RANK_STOP,
                             "dot_overlap_within_3px_gt": OVERLAP_STOP},
              "entries": rows, "duplicates": duplicates, "pass": not duplicates,
              "scope": "Pinned registry only; not a current/global uniqueness guarantee"}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"candidate": report["candidate"], "duplicates": duplicates, "pass": report["pass"]}))
    return 0 if report["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
