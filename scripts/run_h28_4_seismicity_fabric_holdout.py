#!/usr/bin/env python3
"""Frozen H28-4 test: seismicity-fabric lineaments as OOF detector features.

H28-4 (untried, rank 2 in next_hypotheses.json):
  Layers: deq_n100a15, ieq_n100a15, geod_shearrate (cols 8, 14, 5 of prepared matrix)
  Signature: Directional persistence of earthquake-density ridges aligned with
             local shear-rate gradient orientation over scales wider than
             individual hypocenters.
  Why it catches missing faults: currently-active slip may be blind or alluvium-covered
  and absent from the Quaternary (surface-deformation-scoped) catalogue, yet still
  localize seismicity along a linear fabric.

Protocol: knowledge/08_preregistration_H28-1.md pattern (fresh seeds 230-239).
This script only writes an evidence JSON. It never writes submission rasters and
never contacts DrivenData.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import (  # noqa: E402
    grid,
    holdout,
    metric,
    oof_detector,
    paths,
    seismicity_fabric,
)  # noqa: E402
from gems27.graph import build_graph  # noqa: E402

SEEDS = list(range(230, 240))  # fresh unused range (225-229 free too)
EXPECTED_BAND_NAMES = None  # filled from prepared metadata

SEISMICITY_BAND_NAMES = ("deq_n100a15", "ieq_n100a15", "geod_shearrate")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def distance_to(mask: np.ndarray) -> np.ndarray:
    return distance_transform_edt(~mask) if mask.any() else np.full(mask.shape, np.inf)


def eval_set(pred: np.ndarray, truth: np.ndarray, active: np.ndarray,
             truth_kernel: np.ndarray) -> dict[str, float | int]:
    selected = pred & active
    n_truth = int(truth.sum())
    if not selected.any() or n_truth == 0:
        tp = 0.0
        fp = float((1.0 - truth_kernel[selected]).sum()) if selected.any() else 0.0
        score = 0.0
    else:
        tp = float(metric.kernel_from_distance(
            distance_transform_edt(~selected)[truth]).sum())
        fp = float((1.0 - truth_kernel[selected]).sum())
        score = tp / (tp + 0.2 * fp + 0.8 * (n_truth - tp) + 1e-7)
    return {"tp": tp, "fp": fp, "dti": score, "dots": int(selected.sum())}


def load_or_build_seismicity_matrix(foot: np.ndarray,
                                    names: list[str]) -> tuple[np.ndarray, dict]:
    """Build the deterministic 6-column seismicity-fabric matrix in row-major footprint order."""
    out_dir = paths.PREPARED_FEATURES.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    matrix_path = out_dir / "h28_4_seismicity_fabric_features.npy"
    metadata_path = out_dir / "h28_4_seismicity_fabric_features.json"

    bi = seismicity_fabric.band_indices(names)
    missing = [b for b in SEISMICITY_BAND_NAMES if b not in bi]
    if missing:
        raise SystemExit(f"Prepared feature names missing seismicity bands: {missing}")
    col_idx = [bi[b] for b in SEISMICITY_BAND_NAMES]

    input_hashes = {
        "template": sha256_file(paths.TEMPLATE),
        "training_features": sha256_file(paths.TRAINING),
        "prepared_features": sha256_file(paths.PREPARED_FEATURES),
        "transform_code": sha256_file(
            Path(__file__).resolve().parents[1] / "src/gems27/seismicity_fabric.py"
        ),
    }
    expected_shape = (int(foot.sum()), len(seismicity_fabric.SEISMICITY_FABRIC_NAMES))

    if matrix_path.exists() and metadata_path.exists():
        try:
            meta = json.loads(metadata_path.read_text())
            arr = np.load(matrix_path, mmap_mode="r")
            if (meta.get("feature_names") == list(seismicity_fabric.SEISMICITY_FABRIC_NAMES)
                    and meta.get("source_band_names") == SEISMICITY_BAND_NAMES
                    and meta.get("source_col_idx") == col_idx
                    and meta.get("inputs") == input_hashes
                    and meta.get("shape") == list(expected_shape)
                    and arr.shape == expected_shape
                    and arr.dtype == np.dtype("float32")
                    and sha256_file(matrix_path) == meta.get("sha256")):
                return arr, meta
        except (OSError, ValueError, json.JSONDecodeError):
            pass

    X = np.load(paths.PREPARED_FEATURES, mmap_mode="r")
    foot_rc = np.argwhere(foot)
    if X.shape[0] != len(foot_rc):
        raise ValueError(
            f"prepared features have {X.shape[0]} rows for {len(foot_rc)} footprint cells"
        )
    # X rows are already in row-major footprint order; assign full-grid arrays
    deq_full = np.zeros(grid.SHAPE, dtype=np.float32)
    ieq_full = np.zeros(grid.SHAPE, dtype=np.float32)
    shear_full = np.zeros(grid.SHAPE, dtype=np.float32)
    deq_full[foot] = X[:, col_idx[0]]
    ieq_full[foot] = X[:, col_idx[1]]
    shear_full[foot] = X[:, col_idx[2]]
    del X

    stack = seismicity_fabric.seismicity_fabric_features(deq_full, ieq_full, shear_full, foot)
    matrix = np.ascontiguousarray(stack[:, foot].T, dtype=np.float32)
    del stack, deq_full, ieq_full, shear_full
    if matrix.shape != expected_shape or not np.isfinite(matrix).all():
        raise SystemExit(
            f"Invalid H28-4 feature matrix: shape={matrix.shape}, expected={expected_shape}"
        )
    if float(matrix.min()) < 0.0 or float(matrix.max()) > 1.0:
        raise SystemExit("H28-4 feature scaling escaped [0,1]")

    partial = matrix_path.with_suffix(".partial.npy")
    np.save(partial, matrix, allow_pickle=False)
    partial.replace(matrix_path)
    meta = {
        "schema": 1,
        "feature_names": list(seismicity_fabric.SEISMICITY_FABRIC_NAMES),
        "source_band_names": SEISMICITY_BAND_NAMES,
        "source_col_idx": col_idx,
        "shape": list(matrix.shape),
        "grid_shape": list(grid.SHAPE),
        "crs": f"EPSG:{grid.CRS_EPSG}",
        "valid_cells": int(foot.sum()),
        "inputs": input_hashes,
        "sha256": sha256_file(matrix_path),
    }
    metadata_path.write_text(json.dumps(meta, indent=2) + "\n")
    return np.load(matrix_path, mmap_mode="r"), meta


def parse_seeds(value: str) -> list[int]:
    start, sep, end = value.partition("-")
    if not start.isdigit() or (sep and not end.isdigit()):
        raise argparse.ArgumentTypeError(
            "seeds must be an integer or inclusive range such as 230-239"
        )
    seeds = list(range(int(start), int(end) + 1)) if sep else [int(start)]
    if not seeds or len(seeds) > 100:
        raise argparse.ArgumentTypeError("seed range must contain 1 to 100 seeds")
    return seeds


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", default="230-239", type=parse_seeds)
    parser.add_argument("--out",
                        default=str(paths.EVIDENCE / "h28_4_seismicity_holdout.json"))
    args = parser.parse_args()
    out_path = Path(args.out)
    if out_path.exists():
        raise SystemExit(
            f"Evidence file already exists: {out_path}; remove it for a documented rerun"
        )
    seeds = args.seeds
    started = time.time()
    code_hashes = {
        "runner": sha256_file(Path(__file__).resolve()),
        "transform": sha256_file(
            Path(__file__).resolve().parents[1] / "src/gems27/seismicity_fabric.py"
        ),
    }

    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    if labels.shape != foot.shape:
        raise SystemExit("Labels have the wrong shape")
    fold = holdout.make_quadrant_folds(foot)
    if any(not np.any(fold == f) for f in range(4)):
        raise SystemExit("All four spatial folds must contain footprint cells")

    # Read prepared feature names to locate seismicity bands
    import json as _json
    meta32 = _json.loads(paths.PREPARED_META.read_text())
    names = meta32["names"]

    print("Building seismicity-fabric feature matrix...", flush=True)
    seis_matrix, seis_meta = load_or_build_seismicity_matrix(foot, names)

    print("Training baseline 4-fold OOF detector...", flush=True)
    base_oof = oof_detector.fit_predict_oof_probabilities(foot, labels, fold, seed=2026)
    print("Training H28-4 4-fold OOF detector...", flush=True)
    seis_oof = oof_detector.fit_predict_oof_probabilities(
        foot, labels, fold, extra_features=seis_matrix, seed=2026
    )
    probabilities_valid = bool(
        np.isfinite(base_oof[foot]).all()
        and np.isfinite(seis_oof[foot]).all()
        and np.all((base_oof[foot] >= 0) & (base_oof[foot] <= 1))
        and np.all((seis_oof[foot] >= 0) & (seis_oof[foot] <= 1))
    )
    if not probabilities_valid:
        raise SystemExit("OOF classifier produced non-finite probabilities or outside [0,1]")
    seis_values_valid = bool(
        np.isfinite(seis_matrix).all()
        and seis_matrix.min() >= 0 and seis_matrix.max() <= 1
    )
    if not seis_values_valid:
        raise SystemExit("H28-4 feature matrix is non-finite or outside [0,1]")

    base_ridges = oof_detector.ridge_nms(base_oof, foot, sigma=1.0)
    seis_ridges = oof_detector.ridge_nms(seis_oof, foot, sigma=1.0)

    variants = ("base_oof", "base_plus_Tv2", "base_prune_r1", "base_best_Tv2_prune_r1",
                "seis_oof", "seis_plus_Tv2", "seis_prune_r1", "seis_best_Tv2_prune_r1")
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
                if truth.any() else np.zeros_like(truth, float)
            )

            base = (
                oof_detector.build_oof_dotted_base(
                    base_oof[sl], base_ridges[sl], fold_crop, known,
                    budget_frac=oof_detector.PRE_THIN_FRAC, thin_d=1.5,
                )
                & active
            )
            seis = (
                oof_detector.build_oof_dotted_base(
                    seis_oof[sl], seis_ridges[sl], fold_crop, known,
                    budget_frac=oof_detector.PRE_THIN_FRAC, thin_d=1.5,
                )
                & active
            )
            d_known = distance_to(known)
            base_pruned = base & (d_known > 1.0)
            seis_pruned = seis & (d_known > 1.0)
            d_base = distance_to(base)
            d_seis = distance_to(seis)
            d_base_pruned = distance_to(base_pruned)
            d_seis_pruned = distance_to(seis_pruned)

            from gems27 import candidates, links  # noqa: E402
            graph = build_graph(split.known, with_edges=False)
            link_frame = links.generate_links(graph, region=fm, **candidates.RULE)
            link_evidence = candidates.evidence_score(link_frame)
            selected_links = candidates.dedupe_mutual(link_frame[link_evidence >= 3])
            topology = links.rasterize_links(selected_links, labels.shape,
                                             candidates.SPACING)[sl] & active
            base_best = base_pruned | (topology & (d_base_pruned >= metric.RADIUS_PX))
            seis_best = seis_pruned | (topology & (d_seis_pruned >= metric.RADIUS_PX))

            predictions = {
                "base_oof": base,
                "base_plus_Tv2": base | (topology & (d_base >= metric.RADIUS_PX)),
                "base_prune_r1": base_pruned,
                "base_best_Tv2_prune_r1": base_best,
                "seis_oof": seis,
                "seis_plus_Tv2": seis | (topology & (d_seis >= metric.RADIUS_PX)),
                "seis_prune_r1": seis_pruned,
                "seis_best_Tv2_prune_r1": seis_best,
            }
            overlap = sum(int((p & known).sum()) for p in predictions.values())
            if overlap:
                raise SystemExit(
                    f"A holdout prediction overlaps known catalogue labels by {overlap} pixels"
                )
            known_catalogue_overlap_pixels += overlap
            row = {"seed": seed, "fold": split.name,
                   "n_truth": int(truth.sum()), "link_dots": int(topology.sum())}
            for name in variants:
                row[name] = eval_set(predictions[name], truth, active, truth_kernel)
            cells.append(row)
        rows = [c for c in cells if c["seed"] == seed]
        print(
            f"seed {seed} complete: current-best="
            f"{np.mean([r['base_best_Tv2_prune_r1']['dti'] for r in rows]):.4f}; "
            f"H28-4={np.mean([r['seis_best_Tv2_prune_r1']['dti'] for r in rows]):.4f}; "
            f"elapsed={time.time() - started:.0f}s",
            flush=True,
        )

    baseline_name = "base_best_Tv2_prune_r1"
    candidate_name = "seis_best_Tv2_prune_r1"
    deltas_by_seed = {
        str(seed): float(
            np.mean([r[candidate_name]["dti"] - r[baseline_name]["dti"]
                     for r in cells if r["seed"] == seed])
        ) for seed in seeds
    }
    deltas_by_fold = {
        name: float(
            np.mean([r[candidate_name]["dti"] - r[baseline_name]["dti"]
                     for r in cells if r["fold"] == name])
        ) for name in holdout.FOLD_NAMES
    }
    all_deltas = [r[candidate_name]["dti"] - r[baseline_name]["dti"] for r in cells]
    summary = {}
    for name in variants:
        summary[name] = {
            "mean_dti": float(np.mean([r[name]["dti"] for r in cells])),
            "mean_dots_per_seed": float(
                np.mean([sum(r[name]["dots"] for r in cells if r["seed"] == seed)
                         for seed in seeds])
            ),
            "mean_tp": float(np.mean([r[name]["tp"] for r in cells])),
            "mean_fp": float(np.mean([r[name]["fp"] for r in cells])),
        }
    data_checks = {
        "footprint_cells": int(foot.sum()),
        "label_positive_cells": int(labels[foot].sum()),
        "fold_cells": {holdout.FOLD_NAMES[f]: int((fold == f).sum()) for f in range(4)},
        "all_oof_probabilities_finite_and_in_0_1": probabilities_valid,
        "seismicity_feature_values_finite_and_in_0_1": seis_values_valid,
        "known_catalogue_overlap_pixels_across_variants": known_catalogue_overlap_pixels,
        "no_known_catalogue_overlap": known_catalogue_overlap_pixels == 0,
        "submission_written": False,
    }
    data_checks_passed = bool(
        probabilities_valid and seis_values_valid
        and known_catalogue_overlap_pixels == 0
        and len(cells) == len(seeds) * 4
    )
    gate = {
        "mean_gain_at_least_0_001": bool(np.mean(all_deltas) >= 0.001),
        "at_least_3_of_4_folds_improve": bool(sum(x > 0 for x in deltas_by_fold.values()) >= 3),
        "at_least_8_of_10_seeds_improve": bool(
            len(seeds) == 10 and sum(x > 0 for x in deltas_by_seed.values()) >= 8
        ),
        "exactly_10_preregistered_seeds": bool(seeds == list(range(230, 240))),
        "data_checks_passed": data_checks_passed,
    }
    gate["pass"] = all(gate.values())
    result = {
        "preregistration": "knowledge/08_preregistration_H28-1.md (pattern; fresh seeds 230-239)",
        "candidate": "H28-4 anisotropic seismicity-fabric lineaments",
        "seeds": seeds,
        "fold_names": holdout.FOLD_NAMES,
        "baseline": baseline_name,
        "candidate_variant": candidate_name,
        "code_sha256": code_hashes,
        "seismicity_feature_cache": seis_meta,
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
    print(json.dumps({
        "candidate_minus_baseline_mean_gain": result["candidate_minus_baseline_mean_gain"],
        "gain_by_seed": deltas_by_seed,
        "gain_by_fold": deltas_by_fold,
        "gate": gate,
        "variants": summary,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())