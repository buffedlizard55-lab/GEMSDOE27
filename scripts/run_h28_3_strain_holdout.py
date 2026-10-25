#!/usr/bin/env python3
"""Frozen H28-3 validation: dilatational-strain x conductivity corridors.

This is a holdout-only experiment defined in knowledge/13_preregistration_H28-3.md. It builds a
label-free cached feature matrix, runs the preregistered leakage canary, evaluates the paired
baseline/candidate on fresh seeds 160--169, and writes evidence only. It never writes a submission
GeoTIFF and never accesses DrivenData.
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
from sklearn.metrics import average_precision_score, roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from scripts.run_h28_1_edge_holdout import (  # noqa: E402
    EXPECTED_SOURCE_BANDS,
    load_or_build_edge_matrix,
    validate_prepared_feature_metadata,
)

from gems27 import (  # noqa: E402
    grid,
    holdout,
    links,
    metric,
    oof_detector,
    paths,
    strain_conductivity,
)
from gems27.candidates import RULE, SPACING, dedupe_mutual, evidence_score  # noqa: E402
from gems27.graph import build_graph  # noqa: E402

EVALUATOR_VERSION = "H28-3-holdout-v1"
SEEDS = list(range(160, 170))
SOURCE_BANDS = {
    "geod_2ndinv": 4,
    "geod_shearrate": 7,
    "geod_dilaterate": 8,
    "depth_to_base_surf": 15,
    "cond_surf": 17,
}
SOURCE_ORDER = tuple(SOURCE_BANDS)
FEATURE_PARAMETERS = {
    "pixel_size_m": 100.0,
    "sigma_px": 3.0,
    "scalar_percentiles": [5.0, 95.0],
    "orientation_magnitude_percentile": 10.0,
    "outside_mask": 0.0,
}
BOOTSTRAP_DRAWS = 10_000
BOOTSTRAP_SEED = 20261025


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def parse_seeds(value: str) -> list[int]:
    left, sep, right = value.partition("-")
    if not left.isdigit() or (sep and not right.isdigit()):
        raise argparse.ArgumentTypeError("seeds must be an integer or inclusive range such as 160-169")
    answer = list(range(int(left), int(right) + 1)) if sep else [int(left)]
    if not answer or len(answer) > 100:
        raise argparse.ArgumentTypeError("seed range must contain 1 to 100 values")
    return answer


def _load_source_grids(foot: np.ndarray) -> tuple[dict[str, np.ndarray], np.ndarray, dict]:
    """Read exact named source bands and fail closed on any grid/description mismatch."""
    with rasterio.open(paths.TEMPLATE) as template, rasterio.open(paths.TRAINING) as source:
        if source.shape != template.shape or source.crs != template.crs or source.transform != template.transform:
            raise SystemExit("H28-3 source raster does not match the competition template grid")
        descriptions = tuple((d or "").split(" - ")[0].strip() for d in source.descriptions)
        values: dict[str, np.ndarray] = {}
        for name, band in SOURCE_BANDS.items():
            if descriptions[band - 1] != name:
                raise SystemExit(f"Expected source band {band} {name!r}, got {descriptions[band - 1]!r}")
            values[name] = source.read(band, out_dtype="float32")
        nodata = source.nodata
    valid = foot.copy()
    for arr in values.values():
        valid &= np.isfinite(arr) & (np.abs(arr) < 1e30)
        if nodata is not None:
            valid &= arr != np.float32(nodata)
    if int(valid.sum()) < int(0.95 * foot.sum()):
        raise SystemExit(f"Only {int(valid.sum()):,}/{int(foot.sum()):,} cells are valid across H28-3 inputs")
    return values, valid, {"source_bands": SOURCE_BANDS, "descriptions": descriptions, "nodata": nodata}


def load_or_build_strain_matrix(foot: np.ndarray, *, force: bool = False) -> tuple[np.ndarray, dict]:
    """Return a hash-pinned, row-major 6-column matrix of H28-3 features."""
    out_dir = paths.PREPARED_FEATURES.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    matrix_path = out_dir / "h28_3_strain_conductivity_features.npy"
    metadata_path = out_dir / "h28_3_strain_conductivity_features.json"
    expected_shape = (int(foot.sum()), len(strain_conductivity.FEATURE_NAMES))
    input_hashes = {
        "template": sha256_file(paths.TEMPLATE),
        "training_features": sha256_file(paths.TRAINING),
        "transform_code": sha256_file(Path(__file__).resolve().parents[1] / "src/gems27/strain_conductivity.py"),
    }
    if matrix_path.exists() and metadata_path.exists() and not force:
        try:
            metadata = json.loads(metadata_path.read_text())
            matrix = np.load(matrix_path, mmap_mode="r")
            if (
                metadata.get("feature_names") == list(strain_conductivity.FEATURE_NAMES)
                and metadata.get("shape") == list(expected_shape)
                and metadata.get("parameters") == FEATURE_PARAMETERS
                and metadata.get("source_bands") == SOURCE_BANDS
                and metadata.get("inputs") == input_hashes
                and matrix.shape == expected_shape
                and matrix.dtype == np.dtype("float32")
                and sha256_file(matrix_path) == metadata.get("sha256")
            ):
                return matrix, metadata
        except (OSError, ValueError, json.JSONDecodeError):
            pass

    source, valid, source_meta = _load_source_grids(foot)
    full_stack = strain_conductivity.strain_conductivity_features(
        source["geod_2ndinv"],
        source["geod_shearrate"],
        source["geod_dilaterate"],
        source["cond_surf"],
        source["depth_to_base_surf"],
        valid,
        sigma_px=FEATURE_PARAMETERS["sigma_px"],
        pixel_size_m=FEATURE_PARAMETERS["pixel_size_m"],
    )
    matrix = np.ascontiguousarray(full_stack[:, foot].T, dtype=np.float32)
    if matrix.shape != expected_shape or not np.isfinite(matrix).all():
        raise SystemExit(f"Invalid H28-3 matrix: {matrix.shape}, expected {expected_shape}")
    if float(matrix.min()) < 0.0 or float(matrix.max()) > 1.0:
        raise SystemExit("H28-3 feature matrix escaped [0,1]")
    partial = matrix_path.with_suffix(".partial.npy")
    np.save(partial, matrix, allow_pickle=False)
    partial.replace(matrix_path)
    metadata = {
        "schema": 1,
        "feature_names": list(strain_conductivity.FEATURE_NAMES),
        "shape": list(matrix.shape),
        "grid_shape": list(foot.shape),
        "crs": f"EPSG:{grid.CRS_EPSG}",
        "source_bands": SOURCE_BANDS,
        "source_description_check": source_meta["source_bands"],
        "valid_cells": int(valid.sum()),
        "parameters": FEATURE_PARAMETERS,
        "inputs": input_hashes,
        "sha256": sha256_file(matrix_path),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    return np.load(matrix_path, mmap_mode="r"), metadata


def _direction_invariant_auc(y: np.ndarray, x: np.ndarray) -> dict[str, float | int]:
    finite = np.isfinite(x)
    if not finite.any():
        return {"finite": 0, "roc_auc": float("nan"), "direction_invariant_roc_auc": float("nan"), "pr_auc": float("nan")}
    yy, xx = y[finite].astype(np.uint8), x[finite]
    roc_pos = float(roc_auc_score(yy, xx))
    roc_neg = float(roc_auc_score(yy, -xx))
    ap_pos = float(average_precision_score(yy, xx))
    ap_neg = float(average_precision_score(yy, -xx))
    return {
        "finite": int(finite.sum()),
        "roc_auc": roc_pos,
        "direction_invariant_roc_auc": max(roc_pos, roc_neg),
        "pr_auc": max(ap_pos, ap_neg),
    }


def canary_report(foot: np.ndarray, labels: np.ndarray, strain_matrix: np.ndarray) -> dict:
    """Full-catalogue AUC safety screen; not a holdout efficacy measurement."""
    prepared = np.load(paths.PREPARED_FEATURES, mmap_mode="r")
    prepared_meta = json.loads(paths.PREPARED_META.read_text())
    y = labels[foot].astype(bool)
    report: dict[str, dict] = {}
    for name in SOURCE_ORDER:
        index = prepared_meta["names"].index(name)
        report[name] = _direction_invariant_auc(y, np.asarray(prepared[:, index]))
        report[name]["kind"] = "source_scalar"
    for index, name in enumerate(strain_conductivity.FEATURE_NAMES):
        report[name] = _direction_invariant_auc(y, np.asarray(strain_matrix[:, index]))
        report[name]["kind"] = "derived_label_free"
    leaking = [name for name, row in report.items() if row["direction_invariant_roc_auc"] > 0.90]
    return {
        "threshold": 0.90,
        "features": report,
        "leaking_features": leaking,
        "pass": not leaking,
        "interpretation": "Safety screen only; these full-catalogue AUCs are not holdout performance or a score.",
    }


def eval_set(pred: np.ndarray, truth: np.ndarray, active: np.ndarray, truth_kernel: np.ndarray) -> dict:
    selected = np.asarray(pred, bool) & active
    n_truth = int(truth.sum())
    if not selected.any() or n_truth == 0:
        fp = float((1.0 - truth_kernel[selected]).sum()) if selected.any() else 0.0
        return {"tp": 0.0, "fp": fp, "dti": 0.0, "dots": int(selected.sum()), "n_truth": n_truth}
    tp = float(metric.kernel_from_distance(distance_transform_edt(~selected)[truth]).sum())
    fp = float((1.0 - truth_kernel[selected]).sum())
    dti = tp / (tp + metric.ALPHA * fp + metric.BETA * (n_truth - tp) + metric.EPS)
    return {"tp": tp, "fp": fp, "dti": float(dti), "dots": int(selected.sum()), "n_truth": n_truth}


def pooled_dti(rows: list[dict], key: str) -> float:
    tp = float(sum(r[key]["tp"] for r in rows))
    fp = float(sum(r[key]["fp"] for r in rows))
    truth = int(sum(r[key]["n_truth"] for r in rows))
    return tp / (tp + metric.ALPHA * fp + metric.BETA * (truth - tp) + metric.EPS) if truth else 0.0


def bootstrap_ci(seed_deltas: list[float]) -> list[float]:
    values = np.asarray(seed_deltas, dtype=float)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    draw_indices = rng.integers(0, len(values), size=(BOOTSTRAP_DRAWS, len(values)))
    samples = values[draw_indices].mean(axis=1)
    return [float(np.quantile(samples, 0.025)), float(np.quantile(samples, 0.975))]


def deterministic_uniform_control(active: np.ndarray, count: int, *, seed: int) -> np.ndarray:
    eligible = np.flatnonzero(active.ravel())
    if count > len(eligible):
        raise ValueError("uniform control requested more pixels than active region")
    rng = np.random.default_rng(seed)
    picked = rng.choice(eligible, size=count, replace=False)
    out = np.zeros(active.size, dtype=bool)
    out[picked] = True
    return out.reshape(active.shape)


def _summarise_cells(cells: list[dict], name: str) -> dict:
    return {
        "pooled_dti": pooled_dti(cells, name),
        "mean_cell_dti": float(np.mean([r[name]["dti"] for r in cells])),
        "mean_dots_per_seed": float(np.mean([sum(r[name]["dots"] for r in cells if r["seed"] == s) for s in SEEDS])),
        "pooled_tp_w": float(sum(r[name]["tp"] for r in cells)),
        "pooled_fp_w": float(sum(r[name]["fp"] for r in cells)),
        "withheld_positives_total": int(sum(r[name]["n_truth"] for r in cells)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=parse_seeds, default=SEEDS)
    parser.add_argument("--out", default=str(paths.EVIDENCE / "h28_3_strain_holdout.json"))
    parser.add_argument("--canary-only", action="store_true")
    parser.add_argument("--force-feature-cache", action="store_true")
    parser.add_argument("--overwrite", action="store_true", help="documented reruns only")
    args = parser.parse_args()
    if args.seeds != SEEDS:
        raise SystemExit(f"H28-3 seeds are frozen to {SEEDS}; got {args.seeds}")
    started = time.time()
    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    if labels.shape != foot.shape or not np.isin(labels, (False, True, 0, 1)).all():
        raise SystemExit("Labels must be a binary raster matching the template")
    prepared_check = validate_prepared_feature_metadata(foot)
    strain_matrix, strain_meta = load_or_build_strain_matrix(foot, force=args.force_feature_cache)
    canary = canary_report(foot, labels, strain_matrix)
    if args.canary_only:
        print(json.dumps(canary, indent=2))
        return 0 if canary["pass"] else 2

    out_path = Path(args.out)
    if out_path.exists() and not args.overwrite:
        raise SystemExit(f"Evidence file already exists: {out_path}; refusing to replace it")
    edge_matrix, edge_meta = load_or_build_edge_matrix(foot)
    if edge_meta.get("source_bands") != EXPECTED_SOURCE_BANDS:
        raise SystemExit("H28-1 feature cache does not match the frozen source-band contract")
    combined = np.concatenate((np.asarray(edge_matrix), np.asarray(strain_matrix)), axis=1)
    if combined.shape != (int(foot.sum()), 12) or not np.isfinite(combined).all():
        raise SystemExit("H28-3 combined feature stack is malformed")

    fold = holdout.make_quadrant_folds(foot)
    print("Fitting paired OOF detectors (H28-1 baseline, then baseline + H28-3) ...", flush=True)
    baseline_prob = oof_detector.fit_predict_oof_probabilities(foot, labels, fold, extra=edge_matrix)
    candidate_prob = oof_detector.fit_predict_oof_probabilities(foot, labels, fold, extra=combined)
    if not (
        np.isfinite(baseline_prob[foot]).all()
        and np.isfinite(candidate_prob[foot]).all()
        and ((baseline_prob[foot] >= 0) & (baseline_prob[foot] <= 1)).all()
        and ((candidate_prob[foot] >= 0) & (candidate_prob[foot] <= 1)).all()
    ):
        raise SystemExit("OOF probabilities are non-finite or outside [0,1]")
    baseline_ridges = oof_detector.ridge_nms(baseline_prob, foot, sigma=1.0)
    candidate_ridges = oof_detector.ridge_nms(candidate_prob, foot, sigma=1.0)

    cells: list[dict] = []
    for seed in SEEDS:
        for fold_id in range(4):
            split = holdout.make_split(labels, fold, fold_id, seed)
            fold_mask = split.fold_mask
            crop = holdout.crop(None, fold_mask)
            hidden = split.hidden[crop]
            known = (split.known & fold_mask)[crop]
            fold_crop = fold_mask[crop]
            truth = hidden & fold_crop & ~known
            active = fold_crop & ~known
            truth_kernel = metric.kernel_from_distance(distance_transform_edt(~truth)) if truth.any() else np.zeros_like(truth, float)

            baseline = oof_detector.build_oof_dotted_base(
                baseline_prob[crop], baseline_ridges[crop], fold_crop, known,
                budget_frac=oof_detector.PRE_THIN_FRAC, thin_d=1.5,
            ) & active
            candidate = oof_detector.build_oof_dotted_base(
                candidate_prob[crop], candidate_ridges[crop], fold_crop, known,
                budget_frac=oof_detector.PRE_THIN_FRAC, thin_d=1.5,
            ) & active
            d_known = distance_transform_edt(~known) if known.any() else np.full(known.shape, np.inf)
            baseline_pruned = baseline & (d_known > 1.0)
            candidate_pruned = candidate & (d_known > 1.0)

            graph = build_graph(split.known, with_edges=False)
            frames = links.generate_links(graph, region=fold_mask, **RULE)
            selected_links = dedupe_mutual(frames[evidence_score(frames) >= 3])
            topology = links.rasterize_links(selected_links, labels.shape, SPACING)[crop] & active
            db = distance_transform_edt(~baseline_pruned) if baseline_pruned.any() else np.full(known.shape, np.inf)
            dc = distance_transform_edt(~candidate_pruned) if candidate_pruned.any() else np.full(known.shape, np.inf)
            baseline_best = baseline_pruned | (topology & (db >= metric.RADIUS_PX))
            candidate_best = candidate_pruned | (topology & (dc >= metric.RADIUS_PX))
            control = deterministic_uniform_control(active, int(candidate_best.sum()), seed=seed * 10 + fold_id + 91_000)

            predictions = {"baseline": baseline_best, "candidate": candidate_best, "uniform_control": control}
            overlap = {key: int((value & known).sum()) for key, value in predictions.items()}
            if any(overlap.values()):
                raise SystemExit(f"Known-catalogue prediction overlap: {overlap}")
            row = {"seed": seed, "fold": split.name, "link_dots": int(topology.sum())}
            for name, prediction in predictions.items():
                row[name] = eval_set(prediction, truth, active, truth_kernel)
            cells.append(row)
        seed_rows = [r for r in cells if r["seed"] == seed]
        print(
            f"seed {seed}: base={pooled_dti(seed_rows, 'baseline'):.6f} "
            f"candidate={pooled_dti(seed_rows, 'candidate'):.6f} "
            f"control={pooled_dti(seed_rows, 'uniform_control'):.6f} elapsed={time.time()-started:.0f}s",
            flush=True,
        )

    baseline_summary = _summarise_cells(cells, "baseline")
    candidate_summary = _summarise_cells(cells, "candidate")
    control_summary = _summarise_cells(cells, "uniform_control")
    seed_delta = [
        pooled_dti([r for r in cells if r["seed"] == seed], "candidate")
        - pooled_dti([r for r in cells if r["seed"] == seed], "baseline")
        for seed in SEEDS
    ]
    fold_delta = {
        name: pooled_dti([r for r in cells if r["fold"] == name], "candidate")
        - pooled_dti([r for r in cells if r["fold"] == name], "baseline")
        for name in holdout.FOLD_NAMES
    }
    pooled_delta = candidate_summary["pooled_dti"] - baseline_summary["pooled_dti"]
    pooled_control_delta = candidate_summary["pooled_dti"] - control_summary["pooled_dti"]
    ci = bootstrap_ci(seed_delta)
    integrity = {
        "n_cells": len(cells),
        "expected_cells": len(SEEDS) * 4,
        "footprint_cells": int(foot.sum()),
        "withheld_positive_occurrences": int(sum(r["candidate"]["n_truth"] for r in cells)),
        "prepared_features": prepared_check,
        "h28_1_edge_features": edge_meta,
        "h28_3_features": strain_meta,
        "probabilities_finite_in_0_1": True,
        "known_catalogue_overlap": 0,
        "submission_written": False,
    }
    gate = {
        "leakage_canary_passed": bool(canary["pass"]),
        "candidate_pooled_dti_exceeds_baseline": bool(pooled_delta > 0),
        "mean_paired_gain_at_least_0_001": bool(float(np.mean(seed_delta)) >= 0.001),
        "bootstrap_95_ci_lower_above_zero": bool(ci[0] > 0),
        "at_least_3_of_4_folds_improve": bool(sum(v > 0 for v in fold_delta.values()) >= 3),
        "at_least_8_of_10_seeds_improve": bool(sum(v > 0 for v in seed_delta) >= 8),
        "beats_same_count_uniform_control_by_0_001": bool(pooled_control_delta >= 0.001),
        "integrity_passed": bool(integrity["n_cells"] == integrity["expected_cells"] and integrity["known_catalogue_overlap"] == 0),
    }
    gate["pass"] = all(gate.values())
    result = {
        "preregistration": "knowledge/13_preregistration_H28-3.md",
        "evaluator_version": EVALUATOR_VERSION,
        "candidate": "H28-3 dilatational-strain x conductivity corridors",
        "seeds": SEEDS,
        "holdout_definition": "20% whole 8-connected catalogue components hidden within each fixed quadrant; 600-m train/test collar; catalogue-derived topology from visible faults only; 300-m triangular DTI alpha=0.2 beta=0.8.",
        "leakage_canary": canary,
        "baseline": "H28-1 edges + T-v2 + H27-4 r1",
        "candidate_variant": "baseline + six H28-3 strain-conductivity features",
        "control": "same-count uniform active-region replacement; deterministic seed + 91000",
        "HOLDOUT_DTI": {
            "baseline": baseline_summary,
            "candidate": candidate_summary,
            "uniform_control": control_summary,
            "candidate_minus_baseline_pooled": float(pooled_delta),
            "candidate_minus_uniform_control_pooled": float(pooled_control_delta),
            "seed_level_paired_mean": float(np.mean(seed_delta)),
            "seed_level_paired_deltas": {str(seed): float(delta) for seed, delta in zip(SEEDS, seed_delta)},
            "fold_pooled_deltas": fold_delta,
            "bootstrap_95_ci_seed_resampling": ci,
            "ci_note": "10,000 deterministic bootstrap resamples of ten seed-level pooled paired differences; not a claim that cells are independent.",
        },
        "integrity": integrity,
        "code_sha256": {
            "runner": sha256_file(Path(__file__).resolve()),
            "transform": sha256_file(Path(__file__).resolve().parents[1] / "src/gems27/strain_conductivity.py"),
            "oof_detector": sha256_file(Path(__file__).resolve().parents[1] / "src/gems27/oof_detector.py"),
        },
        "gate": gate,
        "cell_results": cells,
        "seconds": time.time() - started,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"HOLDOUT_DTI": result["HOLDOUT_DTI"], "gate": gate}, indent=2))
    return 0 if gate["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
