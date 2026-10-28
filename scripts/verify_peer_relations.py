#!/usr/bin/env python3
"""Byte-level dot-set relations among the pinned peer rasters (descriptive audit, not a score).

Purpose: test, from the cached pinned peer files, the repository's account of why the owner-reported
GEMSDOE32 file (`h33-h33-2-b2`, 0.2778, OWNER-REPORTED) differs from its neighbours. The script answers:

* Which pinned peers are bit-identical in their in-footprint values (exact duplicates)?
* Which peers are strict subsets of which (same dot field minus some dots)?
* For a subset pair, how far from the catalogue (labels.tif == 1) were the removed dots?
* How much of the H33-1 candidate lies within 3 px of each peer (directed, shared repo helper)?

It reads only `data_cache/` (restored by `scripts/restore_data.py` and fetched by
`scripts/fetch_parallel_registry.py`) and `registry/parallel_submission_registry.json`. It never
contacts drivendata.org, never uploads anything, and writes only `evidence/peer_relations_*.json`.
Scores in the output are owner-reported labels copied from the registry; nothing here is ORGANIZER-CONFIRMED.

    python scripts/verify_peer_relations.py [--candidate PATH] [--out PATH]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems27 import grid, paths, uniqueness  # noqa: E402

REGISTRY = ROOT / "registry" / "parallel_submission_registry.json"
PEER_DIR = paths.DATA / "parallel_registry"
DEFAULT_CANDIDATE = (
    ROOT / "docs" / "downloads" / "research"
    / "gems27-h33-bss-complement-20261027-9ba8480691ed-allfinite.tif"
)
DEFAULT_OUT = ROOT / "evidence" / "peer_relations_20261028.json"
# Shared-tool convention (uniqueness.dot_comparison): directed 3 px overlap, footprint-masked.
NEAR_PX = (1.0, 2.0, 3.0)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_peers() -> dict[str, dict]:
    """Return {id: {...}} for every pinned peer whose cached file exists and matches the registry grid."""
    entries = json.loads(REGISTRY.read_text())["entries"]
    peers: dict[str, dict] = {}
    for e in entries:
        f = PEER_DIR / f"{e['id']}.tif"
        if not f.exists():
            raise FileNotFoundError(f"missing cached peer {f}; run scripts/fetch_parallel_registry.py")
        with rasterio.open(f) as s:
            vals = s.read(1)
            crs, shape, transform = s.crs, s.shape, s.transform
        peers[e["id"]] = {
            "entry": e,
            "file": f,
            "sha256": sha256_file(f),
            "values": vals,
            "crs": crs,
            "shape": shape,
            "transform": transform,
        }
    return peers


def _dot_mask(values: np.ndarray, foot: np.ndarray) -> np.ndarray:
    return (values == 1) & foot


def _subset_stats(parent: np.ndarray, child: np.ndarray, catalogue: np.ndarray) -> dict:
    """`child` is a subset of `parent` (both boolean dot masks inside the footprint).

    Removed dots = parent & ~child. Distances are Euclidean pixel distances to the nearest catalogue
    cell (labels.tif == 1), computed with the repo's footprint-agnostic distance transform.
    """
    dist_to_cat = distance_transform_edt(~catalogue)
    removed = parent & ~child
    out = {
        "parent_dots": int(parent.sum()),
        "child_dots": int(child.sum()),
        "removed_dots": int(removed.sum()),
        "removed_dots_catalogue_distance_px": {},
        "min_catalogue_distance_of_kept_dots_px": None,
    }
    for r in NEAR_PX:
        out["removed_dots_catalogue_distance_px"][f"<= {r:g}px"] = int((removed & (dist_to_cat <= r)).sum())
    if removed.any():
        out["removed_dots_catalogue_distance_px"]["max"] = round(float(dist_to_cat[removed].max()), 3)
    if child.any():
        out["min_catalogue_distance_of_kept_dots_px"] = round(float(dist_to_cat[child].min()), 3)
    return out


def analyse(peers: dict[str, dict], candidate: np.ndarray | None, foot: np.ndarray,
            label: np.ndarray) -> dict:
    ids = list(peers)
    dots = {i: _dot_mask(peers[i]["values"], foot) for i in ids}
    finite_in = {i: np.isfinite(peers[i]["values"]) & foot for i in ids}

    # 1) bit-level in-footprint value equality (exact duplicates after re-encoding)
    identical_in_footprint = []
    for x in range(len(ids)):
        for y in range(x + 1, len(ids)):
            a, b = ids[x], ids[y]
            va = np.where(foot, peers[a]["values"], -9.0)
            vb = np.where(foot, peers[b]["values"], -9.0)
            if np.array_equal(va, vb, equal_nan=True):
                identical_in_footprint.append([a, b])

    # 2) strict-subset relations on the dot field (child is a proper subset of parent)
    subsets = []
    for parent in ids:
        for child in ids:
            if parent == child:
                continue
            p_mask, c_mask = dots[parent], dots[child]
            if p_mask.sum() <= c_mask.sum():
                continue
            if (c_mask & ~p_mask).any():
                continue  # child has dots parent lacks: not a subset
            subsets.append({"parent": parent, "child": child,
                            **_subset_stats(p_mask, c_mask, label)})

    # 3) candidate relation to every peer (directed 3 px dot overlap; Spearman of binary surfaces)
    cand_rows = {}
    if candidate is not None:
        cand_dots = candidate & foot
        for i in ids:
            r = uniqueness.dot_comparison(cand_dots, dots[i], foot)
            cand_rows[i] = {
                "spearman": round(r["spearman"], 6),
                "dot_overlap_within_3px": round(r["dot_overlap_within_3px"], 6),
                "exact_overlap_dots": r["exact_overlap_dots"],
                "peer_dots": r["reference_dots"],
            }

    per_peer = {}
    for i in ids:
        p = peers[i]
        per_peer[i] = {
            "repo": p["entry"]["repo"],
            "commit": p["entry"]["commit"],
            "path": p["entry"]["path"],
            "manual_review_url": f"https://github.com/{p['entry']['repo']}/blob/{p['entry']['commit']}/{p['entry']['path']}",
            "cached_file": str(p["file"].relative_to(ROOT)) if p["file"].is_relative_to(ROOT) else str(p["file"]),
            "file_sha256": p["sha256"],
            "dots_in_footprint": int(dots[i].sum()),
            "nan_pixels_in_template_footprint": int((~finite_in[i] & foot).sum()),
            "owner_reported_score": p["entry"].get("claimed_score"),
            "score_label": p["entry"].get("score_label"),
        }

    return {
        "per_peer": per_peer,
        "identical_in_footprint_pairs": identical_in_footprint,
        "strict_subset_relations": subsets,
        "candidate_vs_peers": cand_rows or None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    foot = grid.load_footprint(paths.TEMPLATE)
    label = grid.load_labels(paths.LABELS)
    peers = load_peers()
    for i, p in peers.items():
        if p["shape"] != foot.shape or p["crs"] != rasterio.open(paths.TEMPLATE).crs:
            raise ValueError(f"{i}: grid differs from template; refusing to compare")

    candidate = None
    cand_info = None
    if args.candidate is not None and args.candidate.exists():
        with rasterio.open(args.candidate) as s:
            if s.shape != foot.shape or s.count != 1:
                raise ValueError("candidate shape/band mismatch")
            candidate = s.read(1) == 1
            cand_info = {"path": str(args.candidate.relative_to(ROOT)), "sha256": sha256_file(args.candidate),
                         "dots": int(candidate.sum())}

    result = analyse(peers, candidate, foot, label)
    result = {
        "created_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "purpose": "Descriptive byte-level dot-set audit of pinned peers. Not a score, not a receipt.",
        "label_convention": "owner-reported scores copied from registry; HOLDOUT-DTI not computed here",
        "registry_sha256": sha256_file(REGISTRY),
        "template_sha256": sha256_file(paths.TEMPLATE),
        "labels_sha256": sha256_file(paths.LABELS),
        "catalogue_cells": int(label.sum()),
        "candidate": cand_info,
        **result,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(f"wrote {args.out.relative_to(ROOT)}: {len(peers)} peers, "
          f"{len(result['identical_in_footprint_pairs'])} identical in-footprint pair(s), "
          f"{len(result['strict_subset_relations'])} strict-subset relation(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
