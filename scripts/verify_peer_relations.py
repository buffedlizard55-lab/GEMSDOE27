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
RANK_STOP = 0.90
OVERLAP_STOP = 0.70


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
        actual_hash = sha256_file(f)
        if actual_hash != e["sha256"]:
            raise ValueError(f"{e['id']}: cached peer SHA-256 differs from registry pin")
        with rasterio.open(f) as s:
            vals = s.read(1)
            crs, shape, transform = s.crs, s.shape, s.transform
        if sha256_file(f) != e["sha256"]:
            raise ValueError(f"{e['id']}: peer bytes changed while being read")
        peers[e["id"]] = {
            "entry": e,
            "file": f,
            "sha256": actual_hash,
            "values": vals,
            "crs": crs,
            "shape": shape,
            "transform": transform,
        }
    return peers


def _dot_mask(values: np.ndarray, foot: np.ndarray) -> np.ndarray:
    return (values == 1) & foot


def validate_binary_raster(values: np.ndarray, foot: np.ndarray, description: str) -> np.ndarray:
    """Require finite exact binary values inside the footprint before comparing a peer raster."""
    data = np.asarray(values)
    footprint = np.asarray(foot, dtype=bool)
    if data.shape != footprint.shape:
        raise ValueError(f"{description}: raster shape differs from the footprint")
    inside = data[footprint]
    if not np.isfinite(inside).all():
        raise ValueError(f"{description}: non-finite values inside the footprint")
    if np.any((inside != 0) & (inside != 1)):
        raise ValueError(f"{description}: in-footprint raster values are not binary")
    return _dot_mask(data, footprint)


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


def pairwise_final_dot_screen(dots: dict[str, np.ndarray], foot: np.ndarray) -> dict:
    """Screen every pinned raster against every other raster using the shared duplicate rule.

    These historical registry entries contain final binary rasters, not their pre-placement
    probability surfaces. The returned rank correlation is therefore binary-mask Spearman, and
    cannot stand in for a continuous pre-placement surface comparison.
    """
    per_candidate: dict[str, dict] = {}
    for candidate_id, candidate in dots.items():
        comparisons = []
        for reference_id, reference in dots.items():
            if candidate_id == reference_id:
                continue
            metrics = uniqueness.dot_comparison(candidate, reference, foot)
            rho = metrics["spearman"]
            overlap = metrics["dot_overlap_within_3px"]
            duplicate = abs(rho) > RANK_STOP or overlap > OVERLAP_STOP
            reasons = []
            if abs(rho) > RANK_STOP:
                reasons.append("absolute binary Spearman exceeds 0.90")
            if overlap > OVERLAP_STOP:
                reasons.append("directed 3-pixel dot overlap exceeds 70%")
            comparisons.append({
                "reference_id": reference_id,
                "binary_spearman": round(rho, 6),
                "candidate_dot_fraction_within_3px": round(overlap, 6),
                "exact_overlap_dots": metrics["exact_overlap_dots"],
                "candidate_dots": metrics["candidate_dots"],
                "reference_dots": metrics["reference_dots"],
                "duplicate": duplicate,
                "reasons": reasons,
            })
        max_overlap = max(comparisons, key=lambda row: row["candidate_dot_fraction_within_3px"], default=None)
        max_abs_rho = max(comparisons, key=lambda row: abs(row["binary_spearman"]), default=None)
        duplicate_peers = [row["reference_id"] for row in comparisons if row["duplicate"]]
        per_candidate[candidate_id] = {
            "dots": int(candidate.sum()),
            "duplicate_peers": duplicate_peers,
            "max_directed_overlap_within_3px": (
                max_overlap["candidate_dot_fraction_within_3px"] if max_overlap else None
            ),
            "worst_overlap_peer": max_overlap["reference_id"] if max_overlap else None,
            "max_abs_binary_spearman": round(abs(max_abs_rho["binary_spearman"]), 6) if max_abs_rho else None,
            "worst_correlation_peer": max_abs_rho["reference_id"] if max_abs_rho else None,
            "pass_within_pinned_peer_set": bool(comparisons) and not duplicate_peers,
            "comparisons": comparisons,
        }
    return {
        "scope": "Pinned peer rasters only; no claim of current/global registry completeness",
        "comparison_kind": "final binary dot rasters; pre-placement continuous surfaces are unavailable",
        "thresholds": {
            "absolute_binary_spearman_stop_gt": RANK_STOP,
            "directed_dot_overlap_within_3px_stop_gt": OVERLAP_STOP,
        },
        "per_candidate": per_candidate,
    }


def analyse(peers: dict[str, dict], candidate: np.ndarray | None, foot: np.ndarray,
            label: np.ndarray) -> dict:
    ids = list(peers)
    dots = {i: validate_binary_raster(peers[i]["values"], foot, i) for i in ids}
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
        "pairwise_final_dot_screen": pairwise_final_dot_screen(dots, foot),
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
    with rasterio.open(paths.TEMPLATE) as template:
        expected_grid = (template.crs, template.shape, template.transform, 1)
    for i, peer in peers.items():
        actual_grid = (peer["crs"], peer["shape"], peer["transform"], 1)
        if actual_grid != expected_grid:
            raise ValueError(f"{i}: grid differs from template; refusing to compare")
        validate_binary_raster(peer["values"], foot, i)

    candidate_path = args.candidate.resolve() if args.candidate is not None else None
    output_path = args.out.resolve()
    candidate = None
    cand_info = None
    if candidate_path is not None and candidate_path.is_file():
        candidate_hash = sha256_file(candidate_path)
        with rasterio.open(candidate_path) as s:
            candidate_grid = (s.crs, s.shape, s.transform, s.count)
            if candidate_grid != expected_grid:
                raise ValueError("candidate CRS/shape/transform/band count differs from template")
            candidate_values = s.read(1)
        if sha256_file(candidate_path) != candidate_hash:
            raise ValueError("candidate bytes changed while being read")
        candidate = validate_binary_raster(candidate_values, foot, "candidate")
        candidate_name = (candidate_path.relative_to(ROOT).as_posix()
                          if candidate_path.is_relative_to(ROOT) else str(candidate_path))
        cand_info = {"path": candidate_name, "sha256": candidate_hash,
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
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=1, allow_nan=False) + "\n")
    output_label = (output_path.relative_to(ROOT).as_posix()
                    if output_path.is_relative_to(ROOT) else str(output_path))
    print(f"wrote {output_label}: {len(peers)} peers, "
          f"{len(result['identical_in_footprint_pairs'])} identical in-footprint pair(s), "
          f"{len(result['strict_subset_relations'])} strict-subset relation(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
