#!/usr/bin/env python3
"""Check a candidate raster against every pinned peer raster in the parallel registry.

A candidate is a duplicate when either its finite-footprint Spearman rank correlation with a registry
raster is greater than 0.90, or more than 70% of the candidate's positive pixels lie within three
100-m cells of that raster's positive pixels. This is deliberately a *directed* dot-overlap measure:
it asks whether this candidate is mostly already represented by a registry emission.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems27 import paths  # noqa: E402

RANK_STOP = 0.90
OVERLAP_STOP = 0.70


def read_candidate(path: Path, template: Path) -> tuple[np.ndarray, np.ndarray]:
    with rasterio.open(template) as t:
        foot = np.isfinite(t.read(1))
        expected = (t.crs, t.shape, t.transform)
    with rasterio.open(path) as s:
        if (s.crs, s.shape, s.transform) != expected or s.count != 1:
            raise SystemExit(f"Candidate grid mismatch: {path}")
        data = s.read(1)
    inside = data[foot]
    if not np.isfinite(inside).all() or float(inside.min()) < 0.0 or float(inside.max()) > 1.0:
        raise SystemExit("Candidate contains non-finite or out-of-range values inside the footprint")
    return data, foot


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument(
        "--cache-manifest",
        type=Path,
        default=Path(os.environ.get("GEMS_DATA_DIR", paths.DATA)) / "parallel_registry" / "cache_manifest.json",
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    candidate, foot = read_candidate(args.candidate, paths.TEMPLATE)
    positive = (candidate > 0.5) & foot
    if not positive.any():
        raise SystemExit("Candidate has no positive pixels; no submission claim can be made")
    cache_manifest = json.loads(args.cache_manifest.read_text())
    cache_root = args.cache_manifest.parent.parent
    report_entries = []
    for item in cache_manifest["entries"]:
        reference_path = cache_root / item["local"]
        with rasterio.open(reference_path) as dataset:
            reference = dataset.read(1)
        ref_inside = reference[foot]
        if not np.isfinite(ref_inside).all() or float(ref_inside.min()) < 0.0 or float(ref_inside.max()) > 1.0:
            raise SystemExit(f"Registry raster invalid inside footprint: {item['id']}")
        correlation = float(spearmanr(candidate[foot], ref_inside).statistic)
        reference_positive = (reference > 0.5) & foot
        if reference_positive.any():
            within = distance_transform_edt(~reference_positive)[positive] <= 3.0
            directed_overlap = float(within.mean())
        else:
            directed_overlap = 0.0
        duplicate = bool(abs(correlation) > RANK_STOP or directed_overlap > OVERLAP_STOP)
        report_entries.append(
            {
                "id": item["id"],
                "reference_sha256": item["sha256"],
                "spearman_rank_correlation": correlation,
                "candidate_dot_fraction_within_3px": directed_overlap,
                "duplicate": duplicate,
            }
        )
    duplicates = [entry["id"] for entry in report_entries if entry["duplicate"]]
    report = {
        "candidate": args.candidate.name,
        "candidate_positive_dots": int(positive.sum()),
        "thresholds": {"rank_correlation_gt": RANK_STOP, "dot_overlap_within_3px_gt": OVERLAP_STOP},
        "entries": report_entries,
        "duplicates": duplicates,
        "pass": not duplicates,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"candidate": report["candidate"], "duplicates": duplicates, "pass": report["pass"]}, indent=2))
    return 0 if report["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
