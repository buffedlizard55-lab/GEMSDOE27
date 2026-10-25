#!/usr/bin/env python3
"""Frozen H28-6 radiometric-front screen, paired holdout, and research-only artifact builder.

Protocol: knowledge/16_preregistration_H28-6.md. Three phases only: (E1) feature-only leakage
canaries and OOF-surface uniqueness; (E2) paired, buffered holdout; (E3) review/research artifact plus
format and final peer-uniqueness checks. This script never accesses DrivenData, uploads, selects a
weekly slot, or marks any raster eligible for submission.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems27 import (  # noqa: E402
    grid,
    holdout,
    links,
    metric,
    oof_detector,
    paths,
    potential_edges,
    radiometric_edges,
)
from gems27.candidates import RULE, SPACING, dedupe_mutual, evidence_score  # noqa: E402
from gems27.graph import build_graph  # noqa: E402
from run_h28_1_edge_holdout import load_or_build_edge_matrix, validate_prepared_feature_metadata  # noqa: E402

EXPERIMENT = "H28-6 multiscale radiometric alteration-front edges"
SEEDS = tuple(range(210, 220))
BOOTSTRAP_DRAWS = 10_000
BOOTSTRAP_SEED = 20261025
MAX_NEGATIVE_SAMPLES_PER_CELL = 200_000
MAX_SECONDS = 7_200
PIXEL_SIZE_M = 100.0
SIGMAS_PX = (3.0, 8.0)
MIN_VALID_COVERAGE = 0.95
CANARY_THRESHOLD = 0.90
SURFACE_CORRELATION_STOP = 0.90
DOT_OVERLAP_STOP = 0.70
ARTIFACT_DIR = ROOT / "docs" / "downloads" / "research"
EVIDENCE_PATH = paths.EVIDENCE / "h28_6_radiometric_holdout.json"
RUN_CARD_PATH = paths.EVIDENCE / "h28_6_run_card.json"
PRECHECK_PATH = paths.EVIDENCE / "h28_6_preflight.json"

EXPECTED_RADIOMETRIC_BANDS = ("K", "Th", "U", "TC")
EXPECTED_EXTENSION_BANDS = ("ThK", "UK", "UTh", "TMI_up150")
USED_SOURCE_FIELDS = ("ThK", "UTh", "TC")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_array(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).view(np.uint8)).hexdigest()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")


def require_experiment_seeds_unused(seeds: tuple[int, ...]) -> dict:
    """Fail closed if any earlier evidence JSON already records one of these holdout seeds."""
    target = set(seeds)
    overlaps: list[dict] = []

    def visit(value, key: str, file: Path) -> None:
        if key in {"seeds", "seed_range", "holdout_seeds"}:
            vals: list[int] = []
            if isinstance(value, (list, tuple)):
                vals = [int(v) for v in value if isinstance(v, (int, np.integer))]
            elif isinstance(value, int):
                vals = [value]
            elif isinstance(value, str):
                left, sep, right = value.partition("-")
                if left.isdigit() and (not sep or right.isdigit()):
                    vals = list(range(int(left), int(right) + 1)) if sep else [int(left)]
            common = sorted(target.intersection(vals))
            if common:
                overlaps.append({"file": str(file.relative_to(ROOT)), "seeds": common})
        if isinstance(value, dict):
            for child_key, child in value.items():
                visit(child, str(child_key), file)
        elif isinstance(value, list):
            for child in value:
                visit(child, key, file)

    for file in sorted(paths.EVIDENCE.rglob("*.json")):
        try:
            visit(json.loads(file.read_text()), "", file)
        except (OSError, json.JSONDecodeError):
            continue
    if overlaps:
        raise SystemExit(f"Preregistered holdout seeds already occur in evidence: {overlaps}")
    return {"scanned_evidence_json_count": len(list(paths.EVIDENCE.rglob("*.json"))), "overlaps": []}


def _manifest_expected_hash(path: Path) -> str:
    manifest = json.loads(paths.MANIFEST.read_text())
    matches = [row for row in manifest.get("files", []) if Path(row.get("path", "")).name == path.name]
    if len(matches) != 1:
        raise SystemExit(f"Expected one data/manifest.json record for {path.name}; found {len(matches)}")
    actual = sha256_file(path)
    expected = matches[0]["sha256"]
    if actual != expected:
        raise SystemExit(f"SHA-256 mismatch for {path.name}: {actual} != manifest {expected}")
    return actual


def _read_radiometric_sources(foot: np.ndarray) -> tuple[dict[str, np.ndarray], np.ndarray, dict]:
    """Read exact radiometric bands and fail closed on source-grid, metadata, or hash differences."""
    hashes = {"rad": _manifest_expected_hash(paths.RAD), "extensions": _manifest_expected_hash(paths.EXTENSIONS)}
    source_fields: dict[str, np.ndarray] = {}
    with rasterio.open(paths.TEMPLATE) as template:
        expected_grid = (template.crs, template.shape, template.transform)
    with rasterio.open(paths.RAD) as rad, rasterio.open(paths.EXTENSIONS) as ext:
        for name, dataset, expected_names in (
            ("radiometric", rad, EXPECTED_RADIOMETRIC_BANDS),
            ("extensions", ext, EXPECTED_EXTENSION_BANDS),
        ):
            actual_grid = (dataset.crs, dataset.shape, dataset.transform)
            if actual_grid != expected_grid or dataset.count != len(expected_names):
                raise SystemExit(f"{name} raster grid/count does not match the competition template")
            descriptions = tuple((d or "").strip() for d in dataset.descriptions)
            if descriptions != expected_names:
                raise SystemExit(f"{name} band descriptions changed: expected {expected_names}, got {descriptions}")
        rad_tc = rad.read(4, out_dtype="float32")
        ext_thk = ext.read(1, out_dtype="float32")
        ext_uth = ext.read(3, out_dtype="float32")
        rad_nodata, ext_nodata = rad.nodata, ext.nodata
    source_fields = {"ThK": ext_thk, "UTh": ext_uth, "TC": rad_tc}
    valid = np.asarray(foot, dtype=bool).copy()
    for values, nodata in ((ext_thk, ext_nodata), (ext_uth, ext_nodata), (rad_tc, rad_nodata)):
        valid &= np.isfinite(values)
        if nodata is not None:
            valid &= values != np.float32(nodata)
    coverage = int(valid.sum()) / int(foot.sum())
    if coverage < MIN_VALID_COVERAGE:
        raise SystemExit(f"Radiometric common coverage {coverage:.5%} is below 95% of the footprint")
    return source_fields, valid, {
        "sha256": hashes,
        "band_descriptions": {"geodawn_rad_u8.tif": list(EXPECTED_RADIOMETRIC_BANDS),
                              "geodawn_extensions_u8.tif": list(EXPECTED_EXTENSION_BANDS)},
        "selected_inputs": {"ThK": "extensions band 1", "UTh": "extensions band 3", "TC": "radiometric band 4"},
        "nodata": {"radiometric": rad_nodata, "extensions": ext_nodata},
        "valid_cells": int(valid.sum()),
        "footprint_cells": int(foot.sum()),
        "valid_coverage": coverage,
        "official_source_note": "USGS GeoDAWN provenance is recorded in registry/sources.json; bytes here are owner-repository mirrors restored from data/manifest.json, not a fresh official download.",
    }


def load_or_build_radiometric_matrix(
    foot: np.ndarray, source_fields: dict[str, np.ndarray], valid: np.ndarray, source_meta: dict, *, force: bool = False
) -> tuple[np.ndarray, dict]:
    """Return a hash-pinned row-major 8-column radiometric edge/coherence matrix."""
    out_dir = paths.PREPARED_FEATURES.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    matrix_path = out_dir / "h28_6_radiometric_edge_features.npy"
    metadata_path = out_dir / "h28_6_radiometric_edge_features.json"
    expected_shape = (int(foot.sum()), len(radiometric_edges.EDGE_FEATURE_NAMES))
    inputs = {
        "template": sha256_file(paths.TEMPLATE),
        "radiometric": source_meta["sha256"]["rad"],
        "extensions": source_meta["sha256"]["extensions"],
        "transform_code": sha256_file(ROOT / "src" / "gems27" / "radiometric_edges.py"),
    }
    params = {"pixel_size_m": PIXEL_SIZE_M, "sigmas_px": list(SIGMAS_PX),
              "gradient_percentiles": [5.0, 95.0], "orientation_threshold_percentile": 10.0,
              "outside_mask": 0.0, "common_valid_coverage_minimum": MIN_VALID_COVERAGE}
    if matrix_path.exists() and metadata_path.exists() and not force:
        try:
            metadata = json.loads(metadata_path.read_text())
            matrix = np.load(matrix_path, mmap_mode="r")
            if (
                metadata.get("feature_names") == list(radiometric_edges.EDGE_FEATURE_NAMES)
                and metadata.get("shape") == list(expected_shape)
                and metadata.get("source_fields") == list(USED_SOURCE_FIELDS)
                and metadata.get("parameters") == params
                and metadata.get("inputs") == inputs
                and matrix.shape == expected_shape
                and matrix.dtype == np.dtype("float32")
                and sha256_file(matrix_path) == metadata.get("sha256")
            ):
                return matrix, metadata
        except (OSError, ValueError, json.JSONDecodeError):
            pass

    stack = radiometric_edges.multiscale_radiometric_edge_features(
        source_fields["ThK"], source_fields["UTh"], source_fields["TC"], valid,
        pixel_size_m=PIXEL_SIZE_M, sigmas_px=SIGMAS_PX,
    )
    matrix = np.ascontiguousarray(stack[:, foot].T, dtype=np.float32)
    del stack
    if matrix.shape != expected_shape or not np.isfinite(matrix).all():
        raise SystemExit(f"Invalid H28-6 feature matrix {matrix.shape}; expected {expected_shape}")
    if float(matrix.min()) < 0.0 or float(matrix.max()) > 1.0:
        raise SystemExit("H28-6 radiometric features escaped [0,1]")
    partial = matrix_path.with_suffix(".partial.npy")
    np.save(partial, matrix, allow_pickle=False)
    partial.replace(matrix_path)
    metadata = {
        "schema": 1,
        "feature_names": list(radiometric_edges.EDGE_FEATURE_NAMES),
        "source_fields": list(USED_SOURCE_FIELDS),
        "shape": list(matrix.shape),
        "grid_shape": list(foot.shape),
        "crs": f"EPSG:{grid.CRS_EPSG}",
        "valid_cells": source_meta["valid_cells"],
        "parameters": params,
        "inputs": inputs,
        "sha256": sha256_file(matrix_path),
    }
    write_json(metadata_path, metadata)
    return np.load(matrix_path, mmap_mode="r"), metadata


def load_or_build_augmented_matrix(edge_matrix: np.ndarray, rad_matrix: np.ndarray, edge_meta: dict,
                                   rad_meta: dict, *, force: bool = False) -> tuple[np.ndarray, dict]:
    """Build/reuse a disk-backed 14-column H28-1 + H28-6 arm, avoiding a large RAM concatenation."""
    path = paths.PREPARED_FEATURES.parent / "h28_6_augmented_features.npy"
    meta_path = paths.PREPARED_FEATURES.parent / "h28_6_augmented_features.json"
    names = list(potential_edges.EDGE_FEATURE_NAMES) + list(radiometric_edges.EDGE_FEATURE_NAMES)
    shape = (edge_matrix.shape[0], len(names))
    inputs = {"h28_1_edge_matrix": edge_meta["sha256"], "h28_6_rad_matrix": rad_meta["sha256"]}
    if path.exists() and meta_path.exists() and not force:
        try:
            meta = json.loads(meta_path.read_text())
            arr = np.load(path, mmap_mode="r")
            if (meta.get("feature_names") == names and meta.get("shape") == list(shape)
                    and meta.get("inputs") == inputs and arr.shape == shape
                    and arr.dtype == np.dtype("float32") and sha256_file(path) == meta.get("sha256")):
                return arr, meta
        except (OSError, ValueError, json.JSONDecodeError):
            pass
    partial = path.with_name(path.stem + ".partial.npy")
    out = np.lib.format.open_memmap(partial, mode="w+", dtype=np.float32, shape=shape)
    chunk = 200_000
    for start in range(0, shape[0], chunk):
        stop = min(start + chunk, shape[0])
        out[start:stop, :len(potential_edges.EDGE_FEATURE_NAMES)] = edge_matrix[start:stop]
        out[start:stop, len(potential_edges.EDGE_FEATURE_NAMES):] = rad_matrix[start:stop]
    out.flush()
    del out
    partial.replace(path)
    result = {"schema": 1, "feature_names": names, "shape": list(shape), "inputs": inputs,
              "sha256": sha256_file(path)}
    write_json(meta_path, result)
    return np.load(path, mmap_mode="r"), result


def _direction_invariant_auc(y: np.ndarray, values: np.ndarray) -> tuple[float, float, float]:
    auc = float(roc_auc_score(y, values))
    inverse = float(roc_auc_score(y, -values))
    return auc, inverse, max(auc, inverse)


def run_feature_canaries(foot: np.ndarray, labels: np.ndarray, fold: np.ndarray,
                         source_fields: dict[str, np.ndarray], source_valid: np.ndarray,
                         rad_matrix: np.ndarray) -> dict:
    """Test every selected source and derived feature alone on every buffered split."""
    features: dict[str, list[dict]] = {
        name: [] for name in (*USED_SOURCE_FIELDS, *radiometric_edges.EDGE_FEATURE_NAMES)
    }
    row_index = np.full(foot.shape, -1, dtype=np.int32)
    row_index[foot] = np.arange(int(foot.sum()), dtype=np.int32)
    src_flat = {name: arr.ravel() for name, arr in source_fields.items()}
    for seed in SEEDS:
        for fold_id in range(4):
            split = holdout.make_split(labels, fold, fold_id, seed)
            valid_score = holdout.buffered_scoring_mask(split, foot)
            eligible = valid_score & ~split.known & source_valid
            eligible_flat = np.flatnonzero(eligible.ravel())
            hidden_flat = split.hidden.ravel()
            positive_flat = eligible_flat[hidden_flat[eligible_flat]]
            negative_flat = eligible_flat[~hidden_flat[eligible_flat]]
            if len(positive_flat) == 0 or len(negative_flat) == 0:
                raise SystemExit(f"No positive or negative canary pixels for seed={seed}, fold={fold_id}")
            rng = np.random.default_rng(BOOTSTRAP_SEED + 1000 * seed + fold_id)
            if len(negative_flat) > MAX_NEGATIVE_SAMPLES_PER_CELL:
                negative_flat = rng.choice(negative_flat, size=MAX_NEGATIVE_SAMPLES_PER_CELL, replace=False)
            sample_flat = np.r_[positive_flat, negative_flat]
            y = np.r_[np.ones(len(positive_flat), dtype=np.uint8), np.zeros(len(negative_flat), dtype=np.uint8)]
            row_ids = row_index.ravel()[sample_flat]
            if np.any(row_ids < 0):
                raise SystemExit("Canary pixel-to-feature row mapping escaped the footprint")
            for name in USED_SOURCE_FIELDS:
                values = src_flat[name][sample_flat].astype(np.float32, copy=False)
                auc, inverse, invariant = _direction_invariant_auc(y, values)
                features[name].append({"seed": seed, "fold": holdout.FOLD_NAMES[fold_id],
                                       "roc_auc": auc, "inverse_roc_auc": inverse,
                                       "direction_invariant_roc_auc": invariant,
                                       "n_positive": len(positive_flat), "n_negative": len(negative_flat)})
            for index, name in enumerate(radiometric_edges.EDGE_FEATURE_NAMES):
                values = np.asarray(rad_matrix[row_ids, index], dtype=np.float32)
                auc, inverse, invariant = _direction_invariant_auc(y, values)
                features[name].append({"seed": seed, "fold": holdout.FOLD_NAMES[fold_id],
                                       "roc_auc": auc, "inverse_roc_auc": inverse,
                                       "direction_invariant_roc_auc": invariant,
                                       "n_positive": len(positive_flat), "n_negative": len(negative_flat)})
            print(f"E1 canary seed {seed} fold {fold_id}: max AUC=" +
                  f"{max(row[-1]['direction_invariant_roc_auc'] for row in features.values()):.4f}", flush=True)
    del row_index, src_flat
    maxima = {name: max(r["direction_invariant_roc_auc"] for r in rows) for name, rows in features.items()}
    leak = [name for name, value in maxima.items() if value > CANARY_THRESHOLD]
    return {"threshold_direction_invariant_auc_gt": CANARY_THRESHOLD,
            "max_direction_invariant_auc_by_feature": maxima,
            "leaking_features": leak, "features": features, "pass": not leak,
            "negative_sample_cap_per_cell": MAX_NEGATIVE_SAMPLES_PER_CELL,
            "n_seeds": len(SEEDS), "n_folds": 4,
            "interpretation": "Feature-only safety canary; not an efficacy score. Any value above 0.90 stops the efficacy test pending leakage review."}


def _registry_paths() -> tuple[dict, dict, Path]:
    registry_path = paths.REGISTRY / "parallel_submission_registry.json"
    cache_manifest_path = paths.DATA / "parallel_registry" / "cache_manifest.json"
    registry = json.loads(registry_path.read_text())
    cache = json.loads(cache_manifest_path.read_text())
    if cache.get("registry_sha256") != sha256_file(registry_path):
        raise SystemExit("Parallel-raster cache manifest does not pin the current registry JSON")
    by_id = {item["id"]: item for item in cache.get("entries", [])}
    if set(by_id) != {item["id"] for item in registry.get("entries", [])}:
        raise SystemExit("Parallel registry/cache entry set differs")
    return registry, cache, cache_manifest_path.parent.parent


def compare_surface_to_registry(surface: np.ndarray, foot: np.ndarray, *, label: str) -> dict:
    """Run the frozen full-footprint Spearman stop before any dots are placed."""
    registry, cache, cache_root = _registry_paths()
    if surface.shape != foot.shape or not np.isfinite(surface[foot]).all():
        raise SystemExit(f"{label} probability surface is non-finite or not on the template grid")
    entries = []
    for item in registry["entries"]:
        record = next(row for row in cache["entries"] if row["id"] == item["id"])
        ref_path = cache_root / record["local"]
        if sha256_file(ref_path) != record["sha256"]:
            raise SystemExit(f"Peer raster checksum changed: {item['id']}")
        with rasterio.open(ref_path) as ds:
            with rasterio.open(paths.TEMPLATE) as template:
                grid_ok = (ds.crs, ds.shape, ds.transform) == (template.crs, template.shape, template.transform)
            if not grid_ok or ds.count != 1:
                raise SystemExit(f"Peer raster grid mismatch: {item['id']}")
            reference = ds.read(1)
        inside = reference[foot]
        if not np.isfinite(inside).all() or float(inside.min()) < 0 or float(inside.max()) > 1:
            raise SystemExit(f"Invalid cached peer raster values inside footprint: {item['id']}")
        rho = float(spearmanr(surface[foot], inside).statistic)
        if not np.isfinite(rho):
            raise SystemExit(f"Undefined surface rank correlation against registry raster {item['id']}; fail closed")
        entries.append({"id": item["id"], "spearman_rank_correlation": rho,
                        "reference_sha256": record["sha256"], "duplicate": bool(rho > SURFACE_CORRELATION_STOP)})
        print(f"{label} pre-placement Spearman {item['id']}: {rho:.5f}", flush=True)
    duplicates = [row["id"] for row in entries if row["duplicate"]]
    return {"label": label, "method": "Spearman rank correlation of continuous probability surfaces over finite template footprint",
            "threshold_gt": SURFACE_CORRELATION_STOP, "entries": entries,
            "max_correlation": max(row["spearman_rank_correlation"] for row in entries),
            "duplicates": duplicates, "pass": not duplicates}


def _cache_oof_probabilities(arm: str, extra: np.ndarray, extra_sha: str, foot: np.ndarray,
                             labels: np.ndarray, fold: np.ndarray, *, force: bool = False) -> tuple[np.ndarray, dict]:
    path = paths.PREPARED_FEATURES.parent / f"h28_6_{arm}_oof_probabilities.npy"
    meta_path = paths.PREPARED_FEATURES.parent / f"h28_6_{arm}_oof_probabilities.json"
    inputs = {"prepared_features": sha256_file(paths.PREPARED_FEATURES),
              "prepared_metadata": sha256_file(paths.PREPARED_META),
              "labels": sha256_file(paths.LABELS), "template": sha256_file(paths.TEMPLATE),
              "extra_features": extra_sha, "fold_map": sha256_array(fold),
              "oof_detector_code": sha256_file(ROOT / "src" / "gems27" / "oof_detector.py"),
              "holdout_code": sha256_file(ROOT / "src" / "gems27" / "holdout.py"),
              "runner_code": sha256_file(Path(__file__).resolve())}
    if path.exists() and meta_path.exists() and not force:
        try:
            meta = json.loads(meta_path.read_text())
            prob = np.load(path, mmap_mode="r")
            if (meta.get("arm") == arm and meta.get("seed") == 2026 and meta.get("inputs") == inputs
                    and meta.get("shape") == list(foot.shape) and prob.shape == foot.shape
                    and prob.dtype == np.dtype("float32") and sha256_file(path) == meta.get("sha256")):
                return prob, meta
        except (OSError, ValueError, json.JSONDecodeError):
            pass
    print(f"E1 fitting cached 4-quadrant OOF probabilities for {arm}...", flush=True)
    prob = oof_detector.fit_predict_oof_probabilities(foot, labels, fold, extra=extra, seed=2026)
    if (not np.isfinite(prob[foot]).all() or np.any((prob[foot] < 0.0) | (prob[foot] > 1.0))):
        raise SystemExit(f"OOF model {arm} returned non-finite or out-of-range probabilities")
    partial = path.with_suffix(".partial.npy")
    np.save(partial, prob.astype(np.float32, copy=False), allow_pickle=False)
    partial.replace(path)
    meta = {"arm": arm, "seed": 2026, "shape": list(prob.shape), "inputs": inputs,
            "sha256": sha256_file(path), "probabilities_finite_and_in_0_1": True}
    write_json(meta_path, meta)
    return np.load(path, mmap_mode="r"), meta


def _distance_to(mask: np.ndarray) -> np.ndarray:
    return distance_transform_edt(~mask) if mask.any() else np.full(mask.shape, np.inf)


def _cell_score_crop(pred_crop: np.ndarray, split: holdout.Split, valid_scoring: np.ndarray,
                     crop_slice: tuple[slice, slice]) -> dict:
    """Score a fold-crop with the shared DTI implementation; masks are pixel-exact."""
    return metric.dti_binary(pred_crop.astype(np.uint8), split.hidden[crop_slice],
                             valid=valid_scoring[crop_slice], known=split.known[crop_slice])


def _pooled_dti(rows: list[dict]) -> float:
    tp = float(sum(row["TPw"] for row in rows))
    fp = float(sum(row["FPw"] for row in rows))
    fn = float(sum(row["FNw"] for row in rows))
    return tp / (tp + metric.ALPHA * fp + metric.BETA * fn + metric.EPS)


def _pooled_cell_summary(rows: list[dict], seeds: tuple[int, ...]) -> tuple[dict, dict, dict]:
    pooled = {arm: _pooled_dti([cell[arm] for cell in rows]) for arm in ("baseline", "candidate", "random_control")}
    seed_deltas: dict[str, float] = {}
    for seed in seeds:
        subset = [cell for cell in rows if cell["seed"] == seed]
        seed_deltas[str(seed)] = _pooled_dti([cell["candidate"] for cell in subset]) - _pooled_dti(
            [cell["baseline"] for cell in subset])
    deltas = np.array(list(seed_deltas.values()), dtype=float)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    boot = rng.choice(deltas, size=(BOOTSTRAP_DRAWS, len(deltas)), replace=True).mean(axis=1)
    paired = {"mean_seed_level_delta": float(deltas.mean()),
              "ci95_seed_resampling": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
              "n_seed_deltas": len(deltas), "bootstrap_draws": BOOTSTRAP_DRAWS,
              "bootstrap_seed": BOOTSTRAP_SEED, "seed_level_deltas": seed_deltas,
              "positive_seeds": int((deltas > 0).sum())}
    fold_deltas: dict[str, float] = {}
    for fold_name in holdout.FOLD_NAMES:
        subset = [cell for cell in rows if cell["fold"] == fold_name]
        fold_deltas[fold_name] = _pooled_dti([cell["candidate"] for cell in subset]) - _pooled_dti(
            [cell["baseline"] for cell in subset])
    return pooled, paired, fold_deltas


def run_paired_holdout(foot: np.ndarray, labels: np.ndarray, fold: np.ndarray,
                       baseline_prob: np.ndarray, candidate_prob: np.ndarray) -> dict:
    """E2: paired, spatially blocked holdout with shared evaluator and visible-catalogue masks."""
    baseline_ridges = oof_detector.ridge_nms(baseline_prob, foot, sigma=1.0)
    candidate_ridges = oof_detector.ridge_nms(candidate_prob, foot, sigma=1.0)
    cells: list[dict] = []
    hidden_occurrences = 0
    known_overlap_pixels = 0
    for seed in SEEDS:
        for fold_id in range(4):
            split = holdout.make_split(labels, fold, fold_id, seed)
            valid_scoring = holdout.buffered_scoring_mask(split, foot)
            hidden_occurrences += int(split.hidden.sum())
            fm = split.fold_mask
            sl_rows, sl_cols = holdout.crop(None, fm)
            sl = (sl_rows, sl_cols)
            fold_crop = fm[sl]
            # Use all visible catalogue pixels from split.known, including those just across a
            # quadrant boundary; only predictions in this fold are active.
            known = split.known[sl]
            active = fold_crop & ~known
            base = oof_detector.build_oof_dotted_base(
                baseline_prob[sl], baseline_ridges[sl], fold_crop, known,
                budget_frac=oof_detector.PRE_THIN_FRAC, thin_d=1.5,
            ) & active
            candidate = oof_detector.build_oof_dotted_base(
                candidate_prob[sl], candidate_ridges[sl], fold_crop, known,
                budget_frac=oof_detector.PRE_THIN_FRAC, thin_d=1.5,
            ) & active
            random_base = oof_detector.build_oof_dotted_base(
                candidate_prob[sl], candidate_ridges[sl], fold_crop, known,
                budget_frac=oof_detector.PRE_THIN_FRAC, thin_d=1.5,
                random_state=BOOTSTRAP_SEED + 1000 * seed + fold_id,
            ) & active
            d_known = _distance_to(split.known)[sl]
            base_pruned = base & (d_known > 1.0)
            candidate_pruned = candidate & (d_known > 1.0)
            random_pruned = random_base & (d_known > 1.0)

            graph = build_graph(split.known, with_edges=False)
            link_frame = links.generate_links(graph, region=fm, **RULE)
            selected = dedupe_mutual(link_frame[evidence_score(link_frame) >= 3])
            topology = links.rasterize_links(selected, labels.shape, SPACING)[sl] & active
            d_base = _distance_to(base_pruned)
            d_candidate = _distance_to(candidate_pruned)
            d_random = _distance_to(random_pruned)
            baseline_best = base_pruned | (topology & (d_base >= metric.RADIUS_PX))
            candidate_best = candidate_pruned | (topology & (d_candidate >= metric.RADIUS_PX))
            random_best = random_pruned | (topology & (d_random >= metric.RADIUS_PX))
            predictions = {"baseline": baseline_best, "candidate": candidate_best, "random_control": random_best}
            overlaps = {arm: int((prediction & known).sum()) for arm, prediction in predictions.items()}
            known_overlap_pixels += sum(overlaps.values())
            if any(overlaps.values()):
                raise SystemExit(f"A holdout prediction overlaps visible catalogue pixels: {overlaps}")

            row = {"seed": seed, "fold": holdout.FOLD_NAMES[fold_id],
                   "withheld_positive_pixels": int(split.hidden.sum()),
                   "baseline": _cell_score_crop(baseline_best, split, valid_scoring, sl),
                   "candidate": _cell_score_crop(candidate_best, split, valid_scoring, sl),
                   "random_control": _cell_score_crop(random_best, split, valid_scoring, sl),
                   "dots": {arm: int(prediction.sum()) for arm, prediction in predictions.items()},
                   "visible_label_overlap_pixels": overlaps}
            cells.append(row)
            print(f"E2 seed {seed} fold {fold_id}: " +
                  " ".join(f"{arm}={row[arm]['dti']:.5f}" for arm in predictions), flush=True)
    pooled, paired, fold_deltas = _pooled_cell_summary(cells, SEEDS)
    candidate_minus_baseline = pooled["candidate"] - pooled["baseline"]
    gate = {
        "all_40_cells_complete": len(cells) == len(SEEDS) * 4,
        "no_visible_catalogue_prediction_overlap": known_overlap_pixels == 0,
        "candidate_pooled_dti_exceeds_baseline": candidate_minus_baseline > 0.0,
        "mean_seed_delta_at_least_0_001": paired["mean_seed_level_delta"] >= 0.001,
        "seed_bootstrap_95_ci_lower_gt_zero": paired["ci95_seed_resampling"][0] > 0.0,
        "at_least_3_of_4_fold_pooled_deltas_positive": sum(delta > 0 for delta in fold_deltas.values()) >= 3,
        "at_least_8_of_10_seed_deltas_positive": paired["positive_seeds"] >= 8,
        "candidate_beats_same_count_random_control": pooled["candidate"] > pooled["random_control"],
    }
    return {"evaluator": "gems27.metric.dti_binary; alpha=0.2, beta=0.8, Euclidean 300 m triangular kernel",
            "holdout_label": "HOLDOUT-DTI (catalogue-internal whole-component hide-and-recover; not a leaderboard score)",
            "seeds": list(SEEDS), "folds": holdout.FOLD_NAMES,
            "withheld_positive_occurrences": hidden_occurrences,
            "n_cells": len(cells), "known_catalogue_overlap_pixels": known_overlap_pixels,
            "pooled_holdout_dti": pooled, "candidate_minus_baseline_pooled_dti": candidate_minus_baseline,
            "paired_seed_summary": paired, "candidate_minus_baseline_by_fold": fold_deltas,
            "gate": gate, "gate_pass": all(gate.values()), "cell_results": cells}


def _build_research_dots(surface: np.ndarray, foot: np.ndarray, labels: np.ndarray) -> tuple[np.ndarray, dict]:
    """Use the frozen ridge/budget/prune/T-v2 writer path for a visibly non-approved research raster."""
    ridges = oof_detector.ridge_nms(surface, foot, sigma=1.0)
    base = oof_detector.build_oof_dotted_base(
        surface, ridges, foot, labels, budget_frac=oof_detector.PRE_THIN_FRAC, thin_d=1.5,
    ) & foot & ~labels
    d_known = _distance_to(labels)
    pruned = base & (d_known > 1.0)
    graph = build_graph(labels, with_edges=False)
    link_frame = links.generate_links(graph, region=foot, **RULE)
    selected = dedupe_mutual(link_frame[evidence_score(link_frame) >= 3])
    topology = links.rasterize_links(selected, labels.shape, SPACING) & foot & ~labels
    d_base = _distance_to(pruned)
    final = pruned | (topology & (d_base >= metric.RADIUS_PX))
    final &= foot & ~labels
    if not final.any():
        raise SystemExit("Research artifact emission selected no pixels")
    return final.astype(np.float32), {"base_prethin_emitted": int(base.sum()),
                                    "base_after_h274_r1_prune": int(pruned.sum()),
                                    "topology_added_pixels": int((final & ~pruned).sum()),
                                    "emitted_pixels": int(final.sum()),
                                    "visible_catalogue_overlap_pixels": int((final & labels).sum())}


def _write_allfinite_geotiff(dots: np.ndarray, foot: np.ndarray, *, status_slug: str) -> dict:
    if dots.shape != foot.shape or not np.isfinite(dots).all() or not np.isin(dots, (0.0, 1.0)).all():
        raise SystemExit("Artifact values must be a finite binary full-grid array")
    if not ((dots > 0.5) & foot).any():
        raise SystemExit("Artifact has no in-footprint positive dots")
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    tmp = ARTIFACT_DIR / "h28_6_radiometric_research.partial.tif"
    with rasterio.open(paths.TEMPLATE) as template:
        profile = template.profile.copy()
        expected = (template.crs, template.shape, template.transform)
    # The sample template exposes full-width strip/block sizes; do not carry those into a tiled
    # writer (TIFF tile dimensions must be multiples of 16). The research artifact is a valid
    # compressed, untiled single-band GeoTIFF on the same grid.
    profile.pop("blockxsize", None)
    profile.pop("blockysize", None)
    profile.update(driver="GTiff", count=1, dtype="float32", nodata=None,
                   compress="deflate", predictor=3, tiled=False)
    with rasterio.open(tmp, "w", **profile) as dst:
        dst.write(dots.astype(np.float32, copy=False), 1)
        dst.set_band_description(1, "H28-6 radiometric-edge research emission; NOT APPROVED FOR SUBMISSION")
    digest = sha256_file(tmp)
    content_id = digest[:12]
    path = ARTIFACT_DIR / f"gems27-h28-6-radiometric-fronts-{status_slug}-20261025-{content_id}-allfinite.tif"
    if path.exists():
        if sha256_file(path) != digest:
            raise SystemExit(f"Content-id path collision at {path}")
        tmp.unlink()
    else:
        tmp.replace(path)
    with rasterio.open(path) as src:
        arr = src.read(1)
        actual = (src.crs, src.shape, src.transform)
        inside = arr[foot]
        outside = arr[~foot]
        checks = {
            "format": "GeoTIFF",
            "single_band": src.count == 1,
            "crs_shape_transform_match_template": actual == expected,
            "no_nan_inside_footprint": bool(np.isfinite(inside).all()),
            "all_values_finite_including_outside": bool(np.isfinite(arr).all()),
            "inside_range_0_1": bool(inside.min() >= 0 and inside.max() <= 1),
            "binary_values_only": bool(set(np.unique(arr).tolist()) <= {0.0, 1.0}),
            "outside_footprint_all_zero": bool((outside == 0).all()),
            "nodata_none": src.nodata is None,
            "positive_dot_count": int((arr[foot] > 0.5).sum()),
            "sha256": digest,
            "content_id": content_id,
        }
    if not all(value for key, value in checks.items() if key not in {"format", "sha256", "content_id", "positive_dot_count"}):
        raise SystemExit(f"Research artifact format verification failed: {checks}")
    return {"path": str(path.relative_to(ROOT)), "sha256": digest, "content_id": content_id,
            "positive_dots": checks["positive_dot_count"], "validator": checks}


def run_final_uniqueness(artifact_path: Path) -> dict:
    """Invoke the shared parallel uniqueness checker for the final emitted GeoTIFF."""
    report_path = paths.EVIDENCE / "h28_6_parallel_uniqueness.json"
    command = [sys.executable, str(ROOT / "scripts" / "check_parallel_uniqueness.py"),
               str(artifact_path), "--out", str(report_path)]
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    if not report_path.exists():
        raise SystemExit(f"Parallel uniqueness checker failed without a report: {proc.stderr}")
    report = json.loads(report_path.read_text())
    report["checker_returncode"] = proc.returncode
    report["checker_stdout"] = proc.stdout.strip()
    if proc.returncode not in (0, 2):
        raise SystemExit(f"Unexpected parallel uniqueness checker error: {proc.stderr}")
    return report


def main() -> int:
    started = time.time()
    seed_scan = require_experiment_seeds_unused(SEEDS)
    if EVIDENCE_PATH.exists() or RUN_CARD_PATH.exists():
        raise SystemExit(f"H28-6 evidence already exists; no same-seed rerun is permitted: {EVIDENCE_PATH}")
    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    if labels.shape != foot.shape or not np.isin(labels, (False, True, 0, 1)).all():
        raise SystemExit("Label grid is misaligned or non-binary")
    fold = holdout.make_quadrant_folds(foot)
    prepared_check = validate_prepared_feature_metadata(foot)
    source_fields, rad_valid, source_meta = _read_radiometric_sources(foot)
    rad_matrix, rad_meta = load_or_build_radiometric_matrix(foot, source_fields, rad_valid, source_meta)
    edge_matrix, edge_meta = load_or_build_edge_matrix(foot)
    if not np.isfinite(edge_matrix).all() or edge_matrix.min() < 0 or edge_matrix.max() > 1:
        raise SystemExit("Hash-pinned H28-1 edge matrix failed finite/range checks")
    augmented, augmented_meta = load_or_build_augmented_matrix(edge_matrix, rad_matrix, edge_meta, rad_meta)

    e1: dict = {"seeds": list(SEEDS), "seed_scan": seed_scan,
                "prepared_feature_metadata": prepared_check,
                "radiometric_sources": source_meta,
                "radiometric_feature_cache": rad_meta,
                "h28_1_edge_feature_cache": edge_meta,
                "augmented_matrix": augmented_meta}
    print("E1: running 11 feature-only canaries on 40 buffered split cells...", flush=True)
    canary = run_feature_canaries(foot, labels, fold, source_fields, rad_valid, rad_matrix)
    e1["feature_only_canary"] = canary
    if not canary["pass"]:
        preflight = {"experiment": EXPERIMENT, "status": "STOPPED: feature-only AUC exceeded 0.90",
                     "e1": e1, "runtime_seconds": time.time() - started}
        write_json(PRECHECK_PATH, preflight)
        card = {"hypothesis": EXPERIMENT, "mechanism": "Hydrothermal alteration fronts and element-ratio boundaries may persist where a buried/older structure lacks a mapped surface rupture.",
                "named_non_fault_mimic": "Lithologic/regolith contacts, flight-line seams, soil moisture, and non-tectonic hydrothermal alteration.",
                "holdout": None, "feature_only_canary": {"pass": False, "leaking_features": canary["leaking_features"]},
                "parallel_uniqueness": None, "raster": None, "validator": None,
                "submission": {"eligible": False, "status": "NO TIFF APPROVED FOR SUBMISSION"},
                "verdict": "negative", "stop_reason": "Leakage canary; no efficacy holdout run or artifact emitted."}
        write_json(RUN_CARD_PATH, card)
        return 2

    if time.time() - started >= MAX_SECONDS:
        raise SystemExit("Two-hour experiment budget reached before OOF model fitting")
    baseline, baseline_meta = _cache_oof_probabilities("baseline_h28_1", edge_matrix, edge_meta["sha256"],
                                                        foot, labels, fold)
    candidate, candidate_meta = _cache_oof_probabilities("candidate_h28_6", augmented,
                                                          augmented_meta["sha256"], foot, labels, fold)
    if time.time() - started >= MAX_SECONDS:
        raise SystemExit("Two-hour experiment budget reached before pre-placement uniqueness check")
    surface_uniqueness = compare_surface_to_registry(candidate, foot, label="H28-6 OOF candidate surface")
    e1.update({"baseline_oof_cache": baseline_meta, "candidate_oof_cache": candidate_meta,
               "preplacement_surface_uniqueness": surface_uniqueness})
    if not surface_uniqueness["pass"]:
        preflight = {"experiment": EXPERIMENT, "status": "STOPPED: OOF candidate surface duplicate",
                     "e1": e1, "runtime_seconds": time.time() - started}
        write_json(PRECHECK_PATH, preflight)
        card = {"hypothesis": EXPERIMENT, "mechanism": "Hydrothermal alteration fronts and element-ratio boundaries may persist where a buried/older structure lacks a mapped surface rupture.",
                "named_non_fault_mimic": "Lithologic/regolith contacts, flight-line seams, soil moisture, and non-tectonic hydrothermal alteration.",
                "holdout": None, "feature_only_canary": {"pass": True, "max_auc": canary["max_direction_invariant_auc_by_feature"]},
                "parallel_uniqueness": {"preplacement_surface": surface_uniqueness, "final_dots": None},
                "raster": None, "validator": None,
                "submission": {"eligible": False, "status": "NO TIFF APPROVED FOR SUBMISSION"},
                "verdict": "negative", "stop_reason": "Pre-placement surface duplicate; no holdout DTI was computed."}
        write_json(RUN_CARD_PATH, card)
        return 2

    if time.time() - started >= MAX_SECONDS:
        raise SystemExit("Two-hour experiment budget reached before paired holdout")
    print("E2: running frozen seeds 210-219 x four quadrants...", flush=True)
    holdout_result = run_paired_holdout(foot, labels, fold, baseline, candidate)
    # Persist E1/E2 before any artifact writer or final uniqueness check can fail.
    write_json(paths.EVIDENCE / "h28_6_holdout_checkpoint.json",
               {"experiment": EXPERIMENT, "preregistration": "knowledge/16_preregistration_H28-6.md",
                "e1": e1, "e2_holdout": holdout_result,
                "baseline_oof_sha256": baseline_meta["sha256"],
                "candidate_oof_sha256": candidate_meta["sha256"],
                "checkpoint_saved_before_e3": True})
    e2_pass = bool(holdout_result["gate_pass"])
    e3_surface = None
    artifact_source = "OOF candidate probabilities (negative research artifact; no full-fit model trained)"
    output_surface = np.asarray(candidate, dtype=np.float32)
    if e2_pass:
        if time.time() - started >= MAX_SECONDS:
            raise SystemExit("Two-hour experiment budget reached; no full-fit artifact will be emitted")
        print("E3: holdout gate passed; training the fixed full-map H28-6 model for selector review only...", flush=True)
        full_surface = oof_detector.fit_predict_full_probabilities(foot, labels, extra=augmented, seed=2026)
        if (not np.isfinite(full_surface[foot]).all() or np.any((full_surface[foot] < 0) | (full_surface[foot] > 1))):
            raise SystemExit("Full-fit candidate surface failed finite [0,1] checks")
        e3_surface = compare_surface_to_registry(full_surface, foot, label="H28-6 full-fit candidate surface")
        if e3_surface["pass"]:
            output_surface = full_surface
            artifact_source = "full-map H28-6 fit; research/selector review only, no weekly slot selected"
        else:
            artifact_source = "OOF candidate probabilities after full-fit surface duplicate; NOT APPROVED"
    else:
        print("E2 gate failed; E3 will make only a negative OOF research artifact (no full-fit model, no slot).", flush=True)

    if time.time() - started >= MAX_SECONDS:
        raise SystemExit("Two-hour experiment budget reached before research artifact verification")
    dots, emission_meta = _build_research_dots(output_surface, foot, labels)
    gate_status = "negative-research" if not e2_pass or (e3_surface is not None and not e3_surface["pass"]) else "review-only"
    artifact = _write_allfinite_geotiff(dots, foot, status_slug=gate_status)
    final_uniqueness = run_final_uniqueness(ROOT / artifact["path"])
    final_unique_pass = bool(final_uniqueness.get("pass", False))
    overall_pass = bool(e2_pass and final_unique_pass and (e3_surface is None or e3_surface["pass"]))
    verdict = "promote" if overall_pass else "negative"
    status = ("HOLDOUT GATE PASSED — SELECTOR REVIEW ONLY — NOT APPROVED FOR SUBMISSION" if overall_pass
              else "NEGATIVE RESEARCH ARTIFACT — NOT APPROVED FOR SUBMISSION")
    note = "H28-6 radiometric fronts; research only, not slot-approved."

    result = {
        "experiment": EXPERIMENT,
        "preregistration": "knowledge/16_preregistration_H28-6.md",
        "created_utc": "2026-10-25",
        "runtime_seconds": round(time.time() - started, 2),
        "phase_budget": {"max_experiments": 3, "phases_run": ["E1 feature canary + surface uniqueness", "E2 paired holdout", "E3 artifact + final uniqueness"],
                         "max_seconds": MAX_SECONDS, "within_two_hours": time.time() - started < MAX_SECONDS},
        "seed_scan": seed_scan,
        "data_and_feature_integrity": {"prepared_feature_metadata": prepared_check,
                                        "radiometric_source_metadata": source_meta,
                                        "radiometric_feature_matrix": rad_meta,
                                        "h28_1_edge_matrix": edge_meta,
                                        "augmented_matrix": augmented_meta},
        "e1": e1,
        "e2_holdout": holdout_result,
        "e3_full_fit_surface_uniqueness": e3_surface,
        "artifact_source": artifact_source,
        "emission": emission_meta,
        "artifact": artifact,
        "parallel_uniqueness_final": final_uniqueness,
        "eligibility": {"ok_to_submit": False, "status": status,
                         "reason": "No weekly slot or organizer-confirmed result is selected; holdout is catalogue-internal. Unique format-valid pixels do not establish submission approval."},
        "verdict": verdict,
        "submission_note_if_later_selector_approves": note,
        "competition_score": None,
        "score_claim": "No leaderboard score is claimed; any DTI in this record is HOLDOUT-DTI only.",
    }
    write_json(EVIDENCE_PATH, result)
    run_card = {
        "hypothesis": EXPERIMENT,
        "mechanism": "Hydrothermal alteration can redistribute mobile elements and form spatial fronts in airborne radiometric rank grids; cross-channel edge geometry may reveal a buried or older fault without a catalogued young surface rupture.",
        "named_non_fault_mimic": "Lithologic/regolith contacts, airborne flight-line or processing seams, soil moisture, and non-tectonic hydrothermal alteration can create radiometric boundaries without faults.",
        "holdout": {"label": holdout_result["holdout_label"],
                    "evaluator": holdout_result["evaluator"],
                    "withheld_positive_occurrences": holdout_result["withheld_positive_occurrences"],
                    "pooled_baseline": holdout_result["pooled_holdout_dti"]["baseline"],
                    "pooled_candidate": holdout_result["pooled_holdout_dti"]["candidate"],
                    "pooled_delta": holdout_result["candidate_minus_baseline_pooled_dti"],
                    "seed_level_mean_delta": holdout_result["paired_seed_summary"]["mean_seed_level_delta"],
                    "seed_bootstrap_95_ci": holdout_result["paired_seed_summary"]["ci95_seed_resampling"],
                    "positive_seeds": holdout_result["paired_seed_summary"]["positive_seeds"],
                    "positive_folds": sum(v > 0 for v in holdout_result["candidate_minus_baseline_by_fold"].values()),
                    "pooled_random_control": holdout_result["pooled_holdout_dti"]["random_control"],
                    "gate_pass": holdout_result["gate_pass"]},
        "leakage_canary": {"pass": canary["pass"], "threshold": CANARY_THRESHOLD,
                            "max_direction_invariant_auc_by_feature": canary["max_direction_invariant_auc_by_feature"]},
        "parallel_uniqueness": {"preplacement_oof_surface": {"max_spearman": surface_uniqueness["max_correlation"],
                                                               "duplicates": surface_uniqueness["duplicates"]},
                                "full_fit_surface": e3_surface,
                                "final_dots": {"pass": final_unique_pass,
                                               "duplicates": final_uniqueness.get("duplicates", []),
                                               "entries": final_uniqueness.get("entries", [])}},
        "raster": {"path": artifact["path"], "sha256": artifact["sha256"],
                   "content_id": artifact["content_id"], "dots": artifact["positive_dots"],
                   "artifact_source": artifact_source},
        "validator": artifact["validator"],
        "submission": {"ok_to_submit": False, "status": status,
                       "filename": Path(artifact["path"]).name,
                       "note_if_later_approved": note,
                       "maximum_note_characters": 140},
        "verdict": verdict,
        "limitations": ["Catalogue-internal holdout is not organizer-created expert truth.",
                        "The local GeoDAWN rasters are owner-repository mirrors; this session verified manifest hashes, not fresh official-source bytes.",
                        "No weekly slot was selected or spent; no upload, organizer receipt, or leaderboard score is claimed."],
    }
    write_json(RUN_CARD_PATH, run_card)
    print(json.dumps({"pooled_holdout_dti": holdout_result["pooled_holdout_dti"],
                      "paired_seed_summary": holdout_result["paired_seed_summary"],
                      "gate_pass": holdout_result["gate_pass"], "final_unique": final_unique_pass,
                      "eligibility": status, "artifact": artifact["path"], "verdict": verdict}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
