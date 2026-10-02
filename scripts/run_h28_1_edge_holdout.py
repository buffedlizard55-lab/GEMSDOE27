#!/usr/bin/env python3
"""Frozen H28-1 test: multiscale magnetic/gravity edges on fresh spatial holdouts.

This script only writes an evidence JSON and a disposable feature cache. It never writes or replaces
submission rasters and never contacts DrivenData. Protocol: knowledge/08_preregistration_H28-1.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import grid, holdout, links, metric, oof_detector, paths, potential_edges  # noqa: E402
from gems27.candidates import RULE, SPACING, dedupe_mutual, evidence_score  # noqa: E402
from gems27.graph import build_graph  # noqa: E402

EXPECTED_INPUTS = {"magnetic": (2, "rtp"), "gravity": (13, "iso_grav_anom")}
EXPECTED_SOURCE_BANDS = {
    key: {"band": band, "description": description}
    for key, (band, description) in EXPECTED_INPUTS.items()
}
EDGE_PARAMETERS = {
    "pixel_size_m": 100.0,
    "sigmas_px": [3.0, 10.0],
    "gradient_percentiles": [5, 95],
    "orientation_threshold_percentile": 10,
    "outside_mask": 0.0,
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def distance_to(mask: np.ndarray) -> np.ndarray:
    return distance_transform_edt(~mask) if mask.any() else np.full(mask.shape, np.inf)


def eval_set(
    pred: np.ndarray, truth: np.ndarray, active: np.ndarray, truth_kernel: np.ndarray
) -> dict[str, float | int]:
    selected = pred & active
    n_truth = int(truth.sum())
    if not selected.any() or n_truth == 0:
        tp = 0.0
        fp = float((1.0 - truth_kernel[selected]).sum()) if selected.any() else 0.0
        score = 0.0
    else:
        tp = float(metric.kernel_from_distance(distance_transform_edt(~selected)[truth]).sum())
        fp = float((1.0 - truth_kernel[selected]).sum())
        score = tp / (tp + 0.2 * fp + 0.8 * (n_truth - tp) + 1e-7)
    return {"tp": tp, "fp": fp, "dti": score, "dots": int(selected.sum())}


def _input_hashes() -> dict[str, str]:
    return {
        "template": sha256_file(paths.TEMPLATE),
        "training_features": sha256_file(paths.TRAINING),
        "prepared_features": sha256_file(paths.PREPARED_FEATURES),
        "transform_code": sha256_file(
            Path(__file__).resolve().parents[1] / "src/gems27/potential_edges.py"
        ),
    }


def validate_prepared_feature_metadata(foot: np.ndarray) -> dict:
    """Require the OOF base matrix to carry the corrected LiDAR source-band names."""
    meta = json.loads(paths.PREPARED_META.read_text())
    sidecar = json.loads(paths.LIDAR_META.read_text())
    expected_lidar_names = [f"lidar_{name}" for name in sidecar["bands"][:10]]
    values = np.load(paths.PREPARED_FEATURES, mmap_mode="r")
    if meta.get("schema") != 2:
        raise SystemExit("Prepared-feature metadata is stale; rerun python scripts/prepare_data.py")
    if meta.get("names", [])[18:28] != expected_lidar_names:
        raise SystemExit(
            "Prepared LiDAR feature labels do not match the hash-pinned raster-band metadata"
        )
    if meta.get("lidar_band_descriptions") != sidecar.get("bands"):
        raise SystemExit("Prepared LiDAR descriptions do not match the hash-pinned sidecar")
    if meta.get("inputs", {}).get("lidar_scarp_features_metadata") != sha256_file(paths.LIDAR_META):
        raise SystemExit("Prepared-feature metadata does not pin the restored LiDAR sidecar")
    if values.shape != (int(foot.sum()), int(meta.get("n_features", -1))):
        raise SystemExit("Prepared-feature array shape does not match its metadata and footprint")
    if sha256_file(paths.PREPARED_FEATURES) != meta.get("sha256"):
        raise SystemExit("Prepared-feature array checksum does not match its metadata")
    return {
        "schema": meta["schema"],
        "n_features": meta["n_features"],
        "lidar_names": expected_lidar_names,
        "sha256": meta["sha256"],
    }


def load_or_build_edge_matrix(foot: np.ndarray, *, force: bool = False) -> tuple[np.ndarray, dict]:
    """Build the deterministic 6-column edge matrix in row-major footprint order."""
    out_dir = paths.PREPARED_FEATURES.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    matrix_path = out_dir / "h28_1_edge_features.npy"
    metadata_path = out_dir / "h28_1_edge_features.json"
    input_hashes = _input_hashes()
    expected_shape = (int(foot.sum()), len(potential_edges.EDGE_FEATURE_NAMES))

    if matrix_path.exists() and metadata_path.exists() and not force:
        try:
            meta = json.loads(metadata_path.read_text())
            arr = np.load(matrix_path, mmap_mode="r")
            if (
                meta.get("feature_names") == list(potential_edges.EDGE_FEATURE_NAMES)
                and meta.get("source_bands") == EXPECTED_SOURCE_BANDS
                and meta.get("parameters") == EDGE_PARAMETERS
                and meta.get("inputs") == input_hashes
                and meta.get("shape") == list(expected_shape)
                and arr.shape == expected_shape
                and arr.dtype == np.dtype("float32")
                and sha256_file(matrix_path) == meta.get("sha256")
            ):
                return arr, meta
        except (OSError, ValueError, json.JSONDecodeError):
            pass

    with rasterio.open(paths.TEMPLATE) as template, rasterio.open(paths.TRAINING) as source:
        if (
            source.shape != template.shape
            or source.crs != template.crs
            or source.transform != template.transform
        ):
            raise SystemExit(
                "Potential-field grid differs from the competition grid; refusing implicit resampling"
            )
        descriptions = tuple((d or "").split(" - ")[0].strip() for d in source.descriptions)
        for band, name in EXPECTED_INPUTS.values():
            if descriptions[band - 1] != name:
                raise SystemExit(
                    f"Expected potential-field band {band} {name!r}, got {descriptions[band - 1]!r}"
                )
        magnetic = source.read(EXPECTED_INPUTS["magnetic"][0], out_dtype="float32")
        gravity = source.read(EXPECTED_INPUTS["gravity"][0], out_dtype="float32")
        nodata = source.nodata

    valid = foot & np.isfinite(magnetic) & np.isfinite(gravity)
    valid &= (np.abs(magnetic) < 1e30) & (np.abs(gravity) < 1e30)
    if nodata is not None:
        valid &= (magnetic != np.float32(nodata)) & (gravity != np.float32(nodata))
    if int(valid.sum()) < int(0.95 * foot.sum()):
        raise SystemExit(
            f"Only {int(valid.sum()):,}/{int(foot.sum()):,} footprint cells have both fields"
        )

    full_stack = potential_edges.multiscale_potential_edge_features(
        magnetic, gravity, valid, pixel_size_m=100.0, sigmas_px=(3.0, 10.0)
    )
    matrix = np.ascontiguousarray(full_stack[:, foot].T, dtype=np.float32)
    del full_stack, magnetic, gravity
    if matrix.shape != expected_shape or not np.isfinite(matrix).all():
        raise SystemExit(
            f"Invalid H28-1 feature matrix: shape={matrix.shape}, expected={expected_shape}"
        )
    if float(matrix.min()) < 0.0 or float(matrix.max()) > 1.0:
        raise SystemExit("H28-1 feature scaling escaped [0,1]")

    partial = matrix_path.with_suffix(".partial.npy")
    np.save(partial, matrix, allow_pickle=False)
    partial.replace(matrix_path)
    meta = {
        "schema": 1,
        "feature_names": list(potential_edges.EDGE_FEATURE_NAMES),
        "shape": list(matrix.shape),
        "grid_shape": list(foot.shape),
        "crs": f"EPSG:{grid.CRS_EPSG}",
        "source_bands": EXPECTED_SOURCE_BANDS,
        "valid_cells": int(valid.sum()),
        "parameters": EDGE_PARAMETERS,
        "inputs": input_hashes,
        "sha256": sha256_file(matrix_path),
    }
    metadata_path.write_text(json.dumps(meta, indent=2) + "\n")
    return np.load(matrix_path, mmap_mode="r"), meta


def parse_seeds(value: str) -> list[int]:
    start, sep, end = value.partition("-")
    if not start.isdigit() or (sep and not end.isdigit()):
        raise argparse.ArgumentTypeError(
            "seeds must be an integer or inclusive range such as 140-149"
        )
    seeds = list(range(int(start), int(end) + 1)) if sep else [int(start)]
    if not seeds or len(seeds) > 100:
        raise argparse.ArgumentTypeError("seed range must contain 1 to 100 seeds")
    return seeds


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", default="140-149", type=parse_seeds)
    parser.add_argument("--out", default=str(paths.EVIDENCE / "h28_1_edge_holdout.json"))
    parser.add_argument("--force-edge-cache", action="store_true")
    parser.add_argument(
        "--overwrite", action="store_true", help="replace an existing evidence file"
    )
    args = parser.parse_args()
    out_path = Path(args.out)
    if out_path.exists() and not args.overwrite:
        raise SystemExit(
            f"Evidence file already exists: {out_path}; use --overwrite only for a documented rerun"
        )
    seeds: list[int] = args.seeds
    started = time.time()
    code_hashes = {
        "runner": sha256_file(Path(__file__).resolve()),
        "transform": sha256_file(
            Path(__file__).resolve().parents[1] / "src/gems27/potential_edges.py"
        ),
    }

    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    if labels.shape != foot.shape or not np.isin(labels, (False, True, 0, 1)).all():
        raise SystemExit("Labels have the wrong shape or non-binary values")
    fold = holdout.make_quadrant_folds(foot)
    if any(not np.any(fold == f) for f in range(4)):
        raise SystemExit("All four spatial folds must contain footprint cells")
    prepared_check = validate_prepared_feature_metadata(foot)

    print("Building/loading H28-1 potential-edge features...", flush=True)
    edge_matrix, edge_meta = load_or_build_edge_matrix(foot, force=args.force_edge_cache)
    if edge_matrix.shape[0] != int(foot.sum()):
        raise SystemExit("H28-1 matrix is not aligned to row-major footprint pixels")

    print("Training baseline 4-fold OOF detector...", flush=True)
    base_oof = oof_detector.fit_predict_oof_probabilities(foot, labels, fold, seed=2026)
    print("Training H28-1 4-fold OOF detector...", flush=True)
    edge_oof = oof_detector.fit_predict_oof_probabilities(
        foot, labels, fold, extra_features=edge_matrix, seed=2026
    )
    probabilities_valid = bool(
        np.isfinite(base_oof[foot]).all()
        and np.isfinite(edge_oof[foot]).all()
        and np.all((base_oof[foot] >= 0) & (base_oof[foot] <= 1))
        and np.all((edge_oof[foot] >= 0) & (edge_oof[foot] <= 1))
    )
    if not probabilities_valid:
        raise SystemExit("OOF classifier produced non-finite probabilities or values outside [0,1]")
    edge_values_valid = bool(
        np.isfinite(edge_matrix).all() and edge_matrix.min() >= 0 and edge_matrix.max() <= 1
    )
    if not edge_values_valid:
        raise SystemExit("H28-1 feature matrix is non-finite or outside [0,1]")
    base_ridges = oof_detector.ridge_nms(base_oof, foot, sigma=1.0)
    edge_ridges = oof_detector.ridge_nms(edge_oof, foot, sigma=1.0)

    variants = (
        "base_oof",
        "base_plus_Tv2",
        "base_prune_r1",
        "base_best_Tv2_prune_r1",
        "H28_edge_oof",
        "H28_edge_plus_Tv2",
        "H28_edge_prune_r1",
        "H28_edge_best_Tv2_prune_r1",
    )
    cells: list[dict] = []
    known_catalogue_overlap_pixels = 0
    for seed in seeds:
        for fold_id in range(4):
            split = holdout.make_split(labels, fold, fold_id, seed)
            fm = split.fold_mask
            sl = holdout.crop(None, fm)
            hidden = split.hidden[sl]
            known = (split.known & fm)[sl]
            fold_crop = fm[sl]
            truth = hidden & fold_crop & ~known
            active = fold_crop & ~known
            truth_kernel = (
                metric.kernel_from_distance(distance_transform_edt(~truth))
                if truth.any()
                else np.zeros_like(truth, float)
            )

            base = (
                oof_detector.build_oof_dotted_base(
                    base_oof[sl],
                    base_ridges[sl],
                    fold_crop,
                    known,
                    budget_frac=oof_detector.PRE_THIN_FRAC,
                    thin_d=1.5,
                )
                & active
            )
            edge = (
                oof_detector.build_oof_dotted_base(
                    edge_oof[sl],
                    edge_ridges[sl],
                    fold_crop,
                    known,
                    budget_frac=oof_detector.PRE_THIN_FRAC,
                    thin_d=1.5,
                )
                & active
            )
            d_known = distance_to(known)
            base_pruned = base & (d_known > 1.0)
            edge_pruned = edge & (d_known > 1.0)
            d_base = distance_to(base)
            d_edge = distance_to(edge)
            d_base_pruned = distance_to(base_pruned)
            d_edge_pruned = distance_to(edge_pruned)

            # Deterministic T-v2 graph-link dots are generated once per split and reused unchanged.
            graph = build_graph(split.known, with_edges=False)
            link_frame = links.generate_links(graph, region=fm, **RULE)
            link_evidence = evidence_score(link_frame)
            selected_links = dedupe_mutual(link_frame[link_evidence >= 3])
            topology = links.rasterize_links(selected_links, labels.shape, SPACING)[sl] & active
            base_best = base_pruned | (topology & (d_base_pruned >= metric.RADIUS_PX))
            edge_best = edge_pruned | (topology & (d_edge_pruned >= metric.RADIUS_PX))

            predictions = {
                "base_oof": base,
                "base_plus_Tv2": base | (topology & (d_base >= metric.RADIUS_PX)),
                "base_prune_r1": base_pruned,
                "base_best_Tv2_prune_r1": base_best,
                "H28_edge_oof": edge,
                "H28_edge_plus_Tv2": edge | (topology & (d_edge >= metric.RADIUS_PX)),
                "H28_edge_prune_r1": edge_pruned,
                "H28_edge_best_Tv2_prune_r1": edge_best,
            }
            overlap = sum(int((prediction & known).sum()) for prediction in predictions.values())
            if overlap:
                raise SystemExit(
                    f"A holdout prediction overlaps known catalogue labels by {overlap} pixels"
                )
            known_catalogue_overlap_pixels += overlap
            row = {
                "seed": seed,
                "fold": split.name,
                "n_truth": int(truth.sum()),
                "link_dots": int(topology.sum()),
            }
            for name in variants:
                row[name] = eval_set(predictions[name], truth, active, truth_kernel)
            cells.append(row)
        rows = [c for c in cells if c["seed"] == seed]
        print(
            f"seed {seed} complete: current-best={np.mean([r['base_best_Tv2_prune_r1']['dti'] for r in rows]):.4f}; "
            f"H28-1={np.mean([r['H28_edge_best_Tv2_prune_r1']['dti'] for r in rows]):.4f}; "
            f"elapsed={time.time() - started:.0f}s",
            flush=True,
        )

    baseline_name = "base_best_Tv2_prune_r1"
    candidate_name = "H28_edge_best_Tv2_prune_r1"
    deltas_by_seed = {
        str(seed): float(
            np.mean(
                [
                    r[candidate_name]["dti"] - r[baseline_name]["dti"]
                    for r in cells
                    if r["seed"] == seed
                ]
            )
        )
        for seed in seeds
    }
    deltas_by_fold = {
        name: float(
            np.mean(
                [
                    r[candidate_name]["dti"] - r[baseline_name]["dti"]
                    for r in cells
                    if r["fold"] == name
                ]
            )
        )
        for name in holdout.FOLD_NAMES
    }
    all_deltas = [r[candidate_name]["dti"] - r[baseline_name]["dti"] for r in cells]
    summary = {}
    for name in variants:
        summary[name] = {
            "mean_dti": float(np.mean([r[name]["dti"] for r in cells])),
            "mean_dots_per_seed": float(
                np.mean(
                    [sum(r[name]["dots"] for r in cells if r["seed"] == seed) for seed in seeds]
                )
            ),
            "mean_tp": float(np.mean([r[name]["tp"] for r in cells])),
            "mean_fp": float(np.mean([r[name]["fp"] for r in cells])),
        }
    data_checks = {
        "footprint_cells": int(foot.sum()),
        "label_positive_cells": int(labels[foot].sum()),
        "fold_cells": {holdout.FOLD_NAMES[f]: int((fold == f).sum()) for f in range(4)},
        "all_oof_probabilities_finite_and_in_0_1": probabilities_valid,
        "potential_feature_values_finite_and_in_0_1": edge_values_valid,
        "correct_source_band_descriptions": edge_meta["source_bands"],
        "prepared_feature_metadata": prepared_check,
        "known_catalogue_overlap_pixels_across_variants": known_catalogue_overlap_pixels,
        "no_known_catalogue_overlap": known_catalogue_overlap_pixels == 0,
        "submission_written": False,
    }
    data_checks_passed = bool(
        probabilities_valid
        and edge_values_valid
        and known_catalogue_overlap_pixels == 0
        and len(cells) == len(seeds) * 4
        and int(edge_meta["valid_cells"]) >= int(0.95 * foot.sum())
        and prepared_check["n_features"] == 32
        and edge_meta["source_bands"] == EXPECTED_SOURCE_BANDS
    )
    gate = {
        "mean_gain_at_least_0_001": bool(np.mean(all_deltas) >= 0.001),
        "at_least_3_of_4_folds_improve": bool(sum(x > 0 for x in deltas_by_fold.values()) >= 3),
        "at_least_8_of_10_seeds_improve": bool(
            len(seeds) == 10 and sum(x > 0 for x in deltas_by_seed.values()) >= 8
        ),
        "exactly_10_preregistered_seeds": bool(seeds == list(range(140, 150))),
        "data_checks_passed": data_checks_passed,
    }
    gate["pass"] = all(gate.values())
    result = {
        "preregistration": "knowledge/08_preregistration_H28-1.md",
        "candidate": "H28-1 multiscale magnetic/gravity edge coherence",
        "seeds": seeds,
        "fold_names": holdout.FOLD_NAMES,
        "baseline": baseline_name,
        "candidate_variant": candidate_name,
        "code_sha256": code_hashes,
        "edge_feature_cache": edge_meta,
        "data_checks": data_checks,
        "variants": summary,
        "candidate_minus_baseline_mean_gain": float(np.mean(all_deltas)),
        "gain_by_seed": deltas_by_seed,
        "gain_by_fold": deltas_by_fold,
        "positive_seed_count": int(sum(x > 0 for x in deltas_by_seed.values())),
        "improved_fold_count": int(sum(x > 0 for x in deltas_by_fold.values())),
        "gate": gate,
        "cell_results": cells,
        "seconds": time.time() - started,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "candidate_minus_baseline_mean_gain": result["candidate_minus_baseline_mean_gain"],
                "gain_by_seed": deltas_by_seed,
                "gain_by_fold": deltas_by_fold,
                "gate": gate,
                "variants": summary,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
