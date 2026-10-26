#!/usr/bin/env python3
"""Frozen H29-2 experiments E1–E3; no upload or slot selection.

See knowledge/21_preregistration_H29-2_20261025.md. This runner uses the shared
whole-FID split, buffered masks, visible-label detector, DTI evaluator and GeoTIFF
writer. It records negative outcomes and stops at the first frozen integrity,
leakage, uniqueness, or two-hour gate. All large arrays/caches are under data_cache/.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, gaussian_filter
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems27 import dip_shift, grid, holdout, metric, oof_detector, paths, submission  # noqa: E402
from gems27 import subsurface_features as sub  # noqa: E402
from gems27.vector_graph import load_vector_attribution  # noqa: E402

SEEDS = tuple(range(300, 310))
BUFFER_PX = 6.0
B_EXCL_PX = 2.0
MIN_DIST_PX = 2.8
BUDGET = 38_000
NEG_RATIO = 10
MAX_RUNTIME_S = 2 * 60 * 60
CANARY_NEG_MAX = 200_000
BOOTSTRAPS = 10_000
BOOTSTRAP_SEED = 11
FULL_FIT_SEED = 3026
HOLDOUT_OUT = paths.EVIDENCE / "h29_2_holdout_2026-10-25.json"
RUN_CARD_OUT = paths.EVIDENCE / "h29_2_run_card_2026-10-25.json"
WORK = paths.DATA / "h29_2"
NOTE = (
    "H29-2 DIPDIRECT up-dip edge projection; HOLDOUT-DTI gate; "
    "unscored research artifact; not approved to submit."
)
SUBMISSION_NAME = "GEMSDOE27-H29-2-DIPDIRECT-EDGE-UPDIP-38K"
HYPOTHESIS = (
    "Among the D-detector's line candidates, RTP or basement-depth gradient edges sampled "
    "100–300 m down-dip from a target pixel will better identify the corresponding surface-fault "
    "location when the locally visible NBMG DIPDIRECT field points down-dip; project that evidence "
    "up-dip by 1–3 pixels without assuming an unverified dip magnitude."
)
MECHANISM = (
    "Fit the shared HistGradientBoosting detector on the 32-band prepared cache plus 15 frozen "
    "subsurface transforms; the paired arm adds three visible-FID-only, DIPDIRECT-conditioned "
    "up-dip projections of sigma-2 RTP and basement-depth gradient ranks (offsets 1, 2, 3 px), "
    "their minimum/concordance, ridge NMS, B2 exclusion and priority Poisson placement at 38,000 dots."
)
NONFAULT_MIMIC = (
    "Basin-margin lithologic contacts or cover-induced edge termination combined with inaccurate "
    "or ambiguous mapped dip direction."
)


def sha256_file(path: Path | str) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_array(arr: np.ndarray) -> str:
    view = np.asarray(arr)
    return hashlib.sha256(memoryview(np.ascontiguousarray(view))).hexdigest()


def json_dump(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=float) + "\n")


def check_time(start: float) -> None:
    elapsed = time.time() - start
    if elapsed >= MAX_RUNTIME_S:
        raise TimeoutError(f"frozen two-hour experiment limit reached at {elapsed:.1f}s")


def verify_inputs() -> dict:
    """Fail closed on the pinned restored inputs and prepared feature matrix."""
    meta = json.loads(paths.PREPARED_META.read_text())
    expected_matrix = "83ed2704ee2de03cf8b1c8f2966fcf71813501df97c1c35400e6c0415393f6dc"
    if meta.get("sha256") != expected_matrix:
        raise ValueError("prepared feature metadata hash differs from the frozen matrix pin")
    actual_matrix = sha256_file(paths.PREPARED_FEATURES)
    if actual_matrix != expected_matrix:
        raise ValueError(f"prepared feature matrix SHA-256 mismatch: {actual_matrix}")

    input_paths = {
        "template": paths.TEMPLATE,
        "labels": paths.LABELS,
        "training_features": paths.TRAINING,
        "lidar_scarp_features_u8": paths.LIDAR,
        "qfaults_v2_in_footprint": paths.QFAULT_VECTORS,
        "dem_links": paths.DEM_LINKS,
    }
    checked = {"prepared_features": {"path": str(paths.PREPARED_FEATURES.relative_to(paths.REPO)),
                                      "sha256": actual_matrix}}
    for key, path in input_paths.items():
        expected = meta.get("inputs", {}).get(key)
        if expected is None or not Path(path).is_file():
            raise ValueError(f"required pinned input missing from cache: {key} ({path})")
        actual = sha256_file(path)
        if actual != expected:
            raise ValueError(f"pinned input SHA-256 mismatch for {key}: {actual} != {expected}")
        checked[key] = {"path": str(Path(path).relative_to(paths.REPO)), "sha256": actual}
    return {"prepared_features_sha256": actual_matrix, "inputs": checked,
            "feature_names": meta["names"], "n_features": meta["n_features"]}


def load_or_build_group_map(labels: np.ndarray, foot: np.ndarray, inputs: dict) -> tuple[np.ndarray, dict]:
    WORK.mkdir(parents=True, exist_ok=True)
    cache = WORK / "group_map.npy"
    meta_path = WORK / "group_map.json"
    expected = {"labels_sha256": inputs["inputs"]["labels"]["sha256"],
                "qfaults_sha256": inputs["inputs"]["qfaults_v2_in_footprint"]["sha256"]}
    if cache.is_file() and meta_path.is_file():
        cached_meta = json.loads(meta_path.read_text())
        if cached_meta.get("inputs") == expected and cached_meta.get("array_sha256") == sha256_file(cache):
            group_map = np.load(cache, mmap_mode="r")
            if group_map.shape == labels.shape:
                if np.all(np.asarray(group_map[labels]) > 0):
                    return group_map, cached_meta

    attribution = load_vector_attribution(labels, foot, paths.QFAULT_VECTORS)
    group_map = attribution.pix_fid_idx.astype(np.int32, copy=False)
    if np.any(group_map[labels] <= 0):
        raise ValueError("some positive catalogue pixels lack an NBMG Qfault FID mapping")
    np.save(cache, group_map)
    result = {
        "inputs": expected,
        "array_sha256": sha256_file(cache),
        "n_vector_features": int(len(attribution.features)),
        "n_positive_group_ids": int(len(np.unique(group_map[labels]))),
        "alignment_stats": attribution.alignment_stats,
        "group_id_convention": "one-based Qfaults feature index; zero is unmapped",
    }
    json_dump(meta_path, result)
    return np.load(cache, mmap_mode="r"), result


def build_or_load_subsurface(foot: np.ndarray, X: np.ndarray, names: list[str], inputs: dict) -> np.ndarray:
    cache = WORK / "subsurface_transforms.npy"
    meta_path = WORK / "subsurface_transforms.json"
    expected = {"prepared_features_sha256": inputs["prepared_features_sha256"],
                "transform_names": sub.TRANSFORM_NAMES}
    if cache.is_file() and meta_path.is_file():
        cached_meta = json.loads(meta_path.read_text())
        if (cached_meta.get("inputs") == expected
                and cached_meta.get("array_sha256") == sha256_file(cache)):
            matrix = np.load(cache, mmap_mode="r")
            if matrix.shape == (int(foot.sum()), len(sub.TRANSFORM_NAMES)):
                return matrix

    grids = {}
    for band in sub.SUBSURFACE_BANDS:
        arr = np.full(grid.SHAPE, np.nan, dtype=np.float32)
        arr[foot] = np.asarray(X[:, names.index(band)], dtype=np.float32)
        grids[band] = arr
    matrix = sub.build_transforms(grids, foot)
    del grids
    np.save(cache, matrix)
    json_dump(meta_path, {"inputs": expected, "array_sha256": sha256_file(cache),
                          "shape": list(matrix.shape), "dtype": str(matrix.dtype)})
    return np.load(cache, mmap_mode="r")


def build_or_load_edge_ranks(foot: np.ndarray, X: np.ndarray, names: list[str], inputs: dict) -> np.ndarray:
    cache = WORK / "edge_ranks.npy"
    meta_path = WORK / "edge_ranks.json"
    expected = {"prepared_features_sha256": inputs["prepared_features_sha256"],
                "source_bands": ["rtp", "depth_to_base_surf"], "sigma_px": 2.0}
    if cache.is_file() and meta_path.is_file():
        cached_meta = json.loads(meta_path.read_text())
        if cached_meta.get("inputs") == expected and cached_meta.get("array_sha256") == sha256_file(cache):
            edges = np.load(cache, mmap_mode="r")
            if edges.shape == (2, *grid.SHAPE):
                return edges
    rtp, depth = dip_shift.build_edge_ranks(X, names, foot, sigma_px=2.0, pixel_size_m=grid.PIXEL_M)
    edges = np.stack((rtp, depth), axis=0).astype(np.float32, copy=False)
    np.save(cache, edges)
    json_dump(meta_path, {"inputs": expected, "array_sha256": sha256_file(cache),
                          "shape": list(edges.shape), "dtype": str(edges.dtype)})
    return np.load(cache, mmap_mode="r")


def get_split(seed: int, labels: np.ndarray, foot: np.ndarray, group_map: np.ndarray):
    split = holdout.make_segment_split(labels, foot, group_map, seed=seed, frac=0.20)
    training = holdout.buffered_training_mask(split, foot, BUFFER_PX)
    scoring = holdout.buffered_scoring_mask(split, foot, BUFFER_PX)
    hidden_ring = (distance_transform_edt(~split.hidden) <= BUFFER_PX) & ~split.hidden
    if not split.hidden.any() or np.any(split.hidden & split.known):
        raise ValueError(f"seed {seed}: invalid whole-FID masks")
    if np.any(split.hidden & training) or np.any(hidden_ring & training) or np.any(hidden_ring & scoring):
        raise ValueError(f"seed {seed}: training/scoring mask crosses the 600 m hidden-FID buffer")
    if np.any(split.known & split.hidden):
        raise ValueError(f"seed {seed}: hidden and visible label masks overlap")
    if not np.array_equal(split.known | split.hidden, labels & foot):
        raise ValueError(f"seed {seed}: visible and hidden labels do not partition the catalogue")
    return split, training, scoring, hidden_ring


def visible_dip_features(seed: int, split, training: np.ndarray, hidden_ring: np.ndarray,
                         vector_features: list[dict], edges: np.ndarray,
                         inputs: dict) -> tuple[np.ndarray, dict]:
    cache = WORK / f"dip_features_seed{seed}.npy"
    meta_path = WORK / f"dip_features_seed{seed}.json"
    hidden_feature_indices = {int(group_id) - 1 for group_id in split.hidden_group_ids}
    visible_indices = set(range(len(vector_features))) - hidden_feature_indices
    visible_sha = hashlib.sha256(json.dumps(sorted(visible_indices)).encode()).hexdigest()
    expected = {
        "seed": int(seed), "prepared_features_sha256": inputs["prepared_features_sha256"],
        "qfaults_sha256": inputs["inputs"]["qfaults_v2_in_footprint"]["sha256"],
        "group_map_sha256": sha256_file(WORK / "group_map.npy"),
        "visible_feature_indices_sha256": visible_sha,
        "hidden_group_ids": list(split.hidden_group_ids),
    }
    if cache.is_file() and meta_path.is_file():
        cached_meta = json.loads(meta_path.read_text())
        if cached_meta.get("cache_key") == expected and cached_meta.get("array_sha256") == sha256_file(cache):
            matrix = np.load(cache, mmap_mode="r")
            if matrix.shape == (int(np.asarray(split.fold_mask, bool).sum()), len(dip_shift.FEATURE_NAMES)):
                return matrix, cached_meta["integrity"]

    hidden_feature_indices = {int(group_id) - 1 for group_id in split.hidden_group_ids}
    if visible_indices & hidden_feature_indices:
        raise ValueError(f"seed {seed}: hidden FID included in visible DIPDIRECT features")
    field = dip_shift.rasterize_visible_dip_directions(
        paths.QFAULT_VECTORS, visible_indices, split.fold_mask,
        exclude_source_mask=training, max_distance_px=50.0,
    )
    if set(field.source_feature_indices) & hidden_feature_indices:
        raise ValueError(f"seed {seed}: hidden FID leaked into direction-field source inventory")
    source_in_buffer = int((field.source_mask & hidden_ring).sum())
    source_outside_training = int((field.source_mask & ~training).sum())
    if source_in_buffer or source_outside_training or field.metadata["excluded_source_pixels"]:
        raise ValueError(f"seed {seed}: DIPDIRECT source pixels cross the hidden buffer")
    matrix, feature_meta = dip_shift.build_updip_edge_features(
        edges[0], edges[1], field, split.fold_mask
    )
    integrity = {
        "hidden_group_count": int(len(split.hidden_group_ids)),
        "hidden_group_ids": list(split.hidden_group_ids),
        "hidden_feature_indices_sha256": hashlib.sha256(
            json.dumps(sorted(hidden_feature_indices)).encode()).hexdigest(),
        "visible_feature_count": int(len(visible_indices)),
        "visible_feature_indices_sha256": visible_sha,
        "hidden_id_intersection_with_feature_inventory": 0,
        "specified_direction_features": int(field.metadata["specified_direction_feature_count"]),
        "source_pixels": int(field.source_mask.sum()),
        "source_pixels_within_600m_hidden_buffer": source_in_buffer,
        "source_pixels_outside_buffered_training_mask": source_outside_training,
        "direction_valid_pixels": int(field.valid.sum()),
        "feature_metadata": feature_meta,
    }
    np.save(cache, matrix)
    json_dump(meta_path, {"cache_key": expected, "array_sha256": sha256_file(cache),
                          "shape": list(matrix.shape), "integrity": integrity})
    return np.load(cache, mmap_mode="r"), integrity


def canary_auc(features: np.ndarray, split, scoring: np.ndarray, labels: np.ndarray,
               foot: np.ndarray, seed: int) -> dict:
    y = split.hidden[foot]
    valid_neg = scoring[foot] & ~labels[foot]
    positives = np.flatnonzero(y)
    negatives = np.flatnonzero(valid_neg)
    if not len(positives) or not len(negatives):
        raise ValueError(f"seed {seed}: leakage canary has no positive or valid negative samples")
    rng = np.random.default_rng(7000 + int(seed))
    sampled_neg = rng.choice(negatives, size=min(CANARY_NEG_MAX, len(negatives)), replace=False)
    result = {
        "seed": int(seed), "positive_count": int(len(positives)),
        "available_valid_negative_count": int(len(negatives)),
        "sampled_negative_count": int(len(sampled_neg)),
        "negative_source": "buffered scoring region outside every catalogue label",
        "direction_invariant_auc": {},
    }
    for j, name in enumerate(dip_shift.FEATURE_NAMES):
        col = np.asarray(features[:, j], dtype=np.float32)
        values = np.r_[col[positives], col[sampled_neg]]
        target = np.r_[np.ones(len(positives), dtype=np.uint8), np.zeros(len(sampled_neg), dtype=np.uint8)]
        raw_auc = 0.5 if np.ptp(values) == 0 else float(roc_auc_score(target, values))
        invariant = max(raw_auc, 1.0 - raw_auc)
        result["direction_invariant_auc"][name] = {
            "auc": invariant, "raw_auc": raw_auc,
            "leakage_threshold": 0.90, "pass": bool(invariant <= 0.90),
        }
    return result


def emit(prob: np.ndarray, split, scoring: np.ndarray, budget: int = BUDGET) -> np.ndarray:
    visible_distance = distance_transform_edt(~split.known)
    valid = scoring | split.hidden
    ridge = oof_detector.ridge_nms(prob, valid, sigma=1.0)
    candidates = ridge & valid & ~split.known & (visible_distance > B_EXCL_PX)
    dots = sub.priority_poisson_disk(prob, candidates, MIN_DIST_PX, budget)
    if int(dots.sum()) != budget:
        raise ValueError(f"emission integrity failure: requested {budget}, got {int(dots.sum())}")
    if np.any(dots & split.known) or np.any(dots & ~valid):
        raise ValueError("emission placed dots on visible labels or outside buffered scoring region")
    return dots


def score_split(dots: np.ndarray, split, scoring: np.ndarray) -> dict:
    valid = scoring | split.hidden
    result = metric.dti_binary(dots.astype(np.float32), split.hidden,
                               valid=valid, known=split.known)
    if int(result["n_emitted"]) != BUDGET:
        raise ValueError("DTI evaluator saw an unexpected emission count")
    return result


def aggregate(cells: list[dict]) -> float:
    tp = sum(float(c["TPw"]) for c in cells)
    fp = sum(float(c["FPw"]) for c in cells)
    fn = sum(float(c["FNw"]) for c in cells)
    return float(tp / (tp + metric.ALPHA * fp + metric.BETA * fn + metric.EPS))


def bootstrap_holdout(control: list[dict], candidate: list[dict]) -> dict:
    if len(control) != len(SEEDS) or len(candidate) != len(SEEDS):
        raise ValueError("bootstrap requires all 10 preregistered whole-segment seeds")
    c_dti = np.asarray([float(x["dti"]) for x in control])
    a_dti = np.asarray([float(x["dti"]) for x in candidate])
    paired = a_dti - c_dti
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    draws = rng.integers(0, len(SEEDS), size=(BOOTSTRAPS, len(SEEDS)))
    pooled_control = np.empty(BOOTSTRAPS, dtype=np.float64)
    pooled_candidate = np.empty(BOOTSTRAPS, dtype=np.float64)
    pooled_delta = np.empty(BOOTSTRAPS, dtype=np.float64)
    mean_paired_delta = np.empty(BOOTSTRAPS, dtype=np.float64)
    for i, idx in enumerate(draws):
        pooled_control[i] = aggregate([control[j] for j in idx])
        pooled_candidate[i] = aggregate([candidate[j] for j in idx])
        pooled_delta[i] = pooled_candidate[i] - pooled_control[i]
        mean_paired_delta[i] = float(np.mean(paired[idx]))

    def ci(values):
        return [float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))]

    return {
        "pooled_control": aggregate(control),
        "pooled_candidate": aggregate(candidate),
        "paired_pooled_delta": aggregate(candidate) - aggregate(control),
        "pooled_control_ci95_seed_bootstrap": ci(pooled_control),
        "pooled_candidate_ci95_seed_bootstrap": ci(pooled_candidate),
        "paired_pooled_delta_ci95_seed_bootstrap": ci(pooled_delta),
        "mean_per_seed_paired_delta": float(paired.mean()),
        "mean_per_seed_paired_delta_ci95_seed_bootstrap": ci(mean_paired_delta),
        "seeds_improved": int((paired > 0).sum()),
        "n_seeds": int(len(SEEDS)),
        "n_withheld_positives_total": int(sum(int(c["n_truth"]) for c in candidate)),
        "bootstrap_replicates": BOOTSTRAPS,
        "bootstrap_seed": BOOTSTRAP_SEED,
    }


def candidate_rasters() -> list[tuple[str, Path]]:
    files: list[tuple[str, Path]] = []
    for path in sorted((paths.DATA / "parallel_registry").glob("*.tif")):
        files.append((f"peer:{path.name}", path))
    for path in sorted((paths.DOCS / "downloads").rglob("*.tif")):
        files.append((f"repo:{path.relative_to(paths.DOCS / 'downloads')}", path))
    for name in ("h19_5_nan.tif", "dotted_h19_5_d1_5_nan.tif", "dotted_h19_5_d2_8_nan.tif"):
        path = paths.DATA / name
        if path.is_file():
            files.append((f"repo-cache:{name}", path))
    # Deduplicate byte-identical files while retaining one stable label per content.
    seen: set[str] = set()
    unique: list[tuple[str, Path]] = []
    for label, path in files:
        digest = sha256_file(path)
        if digest not in seen:
            seen.add(digest)
            unique.append((label, path))
    return unique


def rank_correlations(prob: np.ndarray, foot: np.ndarray, references: list[tuple[str, Path]]) -> dict:
    rng = np.random.default_rng(1618)
    scope = np.flatnonzero(foot.ravel())
    sample = rng.choice(scope, size=min(300_000, len(scope)), replace=False)
    predicted = prob.ravel()[sample]
    result = {}
    for label, path in references:
        with rasterio.open(path) as src:
            if src.shape != grid.SHAPE or src.crs is None or src.crs.to_epsg() != grid.CRS_EPSG:
                raise ValueError(f"registry raster grid mismatch: {label}")
            raster = src.read(1)
        binary = (np.isfinite(raster) & (raster > 0)).astype(np.float32)
        density = gaussian_filter(binary, sigma=3.0)
        raw = spearmanr(predicted, binary.ravel()[sample]).statistic
        smooth = spearmanr(predicted, density.ravel()[sample]).statistic
        result[label] = {
            "binary_mask_spearman": None if not np.isfinite(raw) else float(raw),
            "density_3px_spearman": None if not np.isfinite(smooth) else float(smooth),
            "sha256": sha256_file(path),
            "source_path": str(path.relative_to(paths.REPO)),
        }
    return result


def maximum_spearman(correlations: dict) -> tuple[float, str | None]:
    vals = [(entry.get("density_3px_spearman"), name) for name, entry in correlations.items()]
    vals += [(entry.get("binary_mask_spearman"), name) for name, entry in correlations.items()]
    vals = [(float(value), name) for value, name in vals if value is not None and np.isfinite(value)]
    return max(vals, default=(0.0, None))


def overlap_within_3px(dots: np.ndarray, reference_path: Path) -> float:
    with rasterio.open(reference_path) as src:
        other = src.read(1)
    mask = np.isfinite(other) & (other > 0)
    if not dots.any():
        return 0.0
    distance = distance_transform_edt(~mask)
    return float((distance[dots] <= 3.0).mean())


def full_fit_and_candidate(inputs: dict, foot: np.ndarray, labels: np.ndarray,
                           X: np.ndarray, names: list[str], T: np.ndarray,
                           edges: np.ndarray, holdout_result: dict, start: float) -> dict:
    check_time(start)
    all_features_path = WORK / "dip_features_full.npy"
    all_features_meta = WORK / "dip_features_full.json"
    feature_cache_key = {
        "prepared_features_sha256": inputs["prepared_features_sha256"],
        "qfaults_sha256": inputs["inputs"]["qfaults_v2_in_footprint"]["sha256"],
        "all_vector_features_visible": True,
        "max_distance_px": 50.0,
    }
    payload = json.loads(paths.QFAULT_VECTORS.read_text())
    vector_features = payload["features"]
    if all_features_path.is_file() and all_features_meta.is_file():
        meta = json.loads(all_features_meta.read_text())
    else:
        meta = {}
    if meta.get("cache_key") == feature_cache_key and meta.get("array_sha256") == sha256_file(all_features_path):
        full_dip_features = np.load(all_features_path, mmap_mode="r")
    else:
        field = dip_shift.rasterize_visible_dip_directions(
            paths.QFAULT_VECTORS, set(range(len(vector_features))), foot,
            exclude_source_mask=foot, max_distance_px=50.0,
        )
        if field.metadata["excluded_source_pixels"] != 0:
            raise ValueError("full-fit dip source rasterization violates the footprint mask")
        full_dip_features, feature_meta = dip_shift.build_updip_edge_features(
            edges[0], edges[1], field, foot
        )
        np.save(all_features_path, full_dip_features)
        meta = {"cache_key": feature_cache_key, "array_sha256": sha256_file(all_features_path),
                "shape": list(full_dip_features.shape), "feature_metadata": feature_meta,
                "visible_feature_count": len(vector_features),
                "specified_direction_features": field.metadata["specified_direction_feature_count"],
                "source_pixels": field.metadata["source_pixels"]}
        json_dump(all_features_meta, meta)
        full_dip_features = np.load(all_features_path, mmap_mode="r")

    extra = np.concatenate((np.asarray(T, dtype=np.float32),
                            np.asarray(full_dip_features, dtype=np.float32)), axis=1)
    fit_cache = WORK / f"full_prob_seed{FULL_FIT_SEED}.npy"
    fit_meta_path = WORK / f"full_prob_seed{FULL_FIT_SEED}.json"
    fit_key = {"feature_matrix_sha256": inputs["prepared_features_sha256"],
               "subsurface_sha256": sha256_file(WORK / "subsurface_transforms.npy"),
               "dip_features_sha256": sha256_file(all_features_path),
               "seed": FULL_FIT_SEED, "training": "all catalogue labels in footprint"}
    if fit_cache.is_file() and fit_meta_path.is_file():
        cached_fit_meta = json.loads(fit_meta_path.read_text())
        if cached_fit_meta.get("cache_key") == fit_key and cached_fit_meta.get("array_sha256") == sha256_file(fit_cache):
            probability = np.load(fit_cache, mmap_mode="r")
        else:
            probability = None
    else:
        probability = None
    if probability is None:
        probability = oof_detector.fit_predict_visible_probabilities(
            foot, labels, foot, extra=extra, neg_ratio=NEG_RATIO,
            seed=FULL_FIT_SEED, base_features=X,
        )
        np.save(fit_cache, probability)
        json_dump(fit_meta_path, {"cache_key": fit_key, "array_sha256": sha256_file(fit_cache)})
        probability = np.load(fit_cache, mmap_mode="r")

    references = candidate_rasters()
    correlations = rank_correlations(probability, foot, references)
    max_surface, worst_surface = maximum_spearman(correlations)
    surface_duplicate = bool(max_surface > 0.90)
    result = {
        "full_fit_seed": FULL_FIT_SEED,
        "surface_comparison": "Spearman on 300,000 deterministic footprint pixels against each positive-mask raster and its sigma=3px Gaussian dot-density surface",
        "surface_correlations": correlations,
        "max_surface_spearman": max_surface,
        "worst_surface_reference": worst_surface,
        "surface_duplicate_threshold": 0.90,
        "surface_duplicate": surface_duplicate,
        "candidate_placement_attempted": False,
        "dot_overlap_by_reference": {},
        "max_dot_overlap_within_3px": None,
        "worst_dot_reference": None,
        "dot_duplicate_threshold": 0.70,
        "dot_duplicate": None,
        "raster": None,
        "validator": None,
        "status": "duplicate_surface_stop" if surface_duplicate else "surface_unique_preplacement",
    }
    if surface_duplicate:
        result["stop_reason"] = (
            f"full-fit surface Spearman {max_surface:.4f} exceeds 0.90 against {worst_surface}; "
            "registered as duplicate; no dot placement or TIFF created"
        )
        return result

    check_time(start)
    result["candidate_placement_attempted"] = True
    distance_to_catalogue = distance_transform_edt(~labels)
    ridge = oof_detector.ridge_nms(probability, foot, sigma=1.0)
    candidate_mask = ridge & foot & ~labels & (distance_to_catalogue > B_EXCL_PX)
    dots = sub.priority_poisson_disk(probability, candidate_mask, MIN_DIST_PX, BUDGET)
    if int(dots.sum()) != BUDGET:
        result["status"] = "emission_integrity_failure"
        result["stop_reason"] = f"fixed 38,000-dot emission yielded {int(dots.sum())} dots"
        return result
    if np.any(dots & labels) or np.any(dots & ~foot) or np.any(distance_to_catalogue[dots] <= B_EXCL_PX):
        raise ValueError("full-fit placement violates pixel-exact visible mask, B2, or footprint")

    overlaps = {label: overlap_within_3px(dots, path) for label, path in references}
    max_overlap, worst_overlap = max(((v, k) for k, v in overlaps.items()), default=(0.0, None))
    dot_duplicate = bool(max_overlap > 0.70)
    result.update({
        "dot_overlap_by_reference": overlaps,
        "max_dot_overlap_within_3px": max_overlap,
        "worst_dot_reference": worst_overlap,
        "dot_duplicate": dot_duplicate,
        "status": "duplicate_dots_stop" if dot_duplicate else "unique_candidate_ready_for_research_validation",
    })
    if dot_duplicate:
        result["stop_reason"] = (
            f"{max_overlap:.4%} of final dots lie within 3 px of {worst_overlap}, above the 70% gate; "
            "registered as duplicate; no TIFF created"
        )
        return result

    prediction = dots.astype(np.float32)
    content_id = submission.scored_content_id(prediction, foot, labels)
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    stem = f"gems27-h29-2-dipdirect-updip-b2-38k-{date}-{content_id}"
    output_dir = paths.DOCS / "downloads" / "research"
    output_dir.mkdir(parents=True, exist_ok=True)
    tif_path = output_dir / f"{stem}-allfinite.tif"
    zip_path = output_dir / f"{stem}-allfinite.zip"
    submission.write_geotiff(prediction, paths.TEMPLATE, tif_path, outside="zero")
    submission.zip_single(tif_path, zip_path)
    verified = submission.verify_geotiff(tif_path, paths.TEMPLATE)
    with rasterio.open(tif_path) as raster:
        array = raster.read(1)
        inside = array[foot]
        outside = array[~foot]
        grid_info = {
            "crs": raster.crs.to_string() if raster.crs else None,
            "shape": list(raster.shape),
            "transform": list(tuple(raster.transform)[:6]),
            "count": raster.count,
            "dtype": raster.dtypes[0],
            "nodata": raster.nodata,
        }
    checks = verified["checks"]
    hard_pass = bool(verified["hard_checks_passed"])
    validator = {
        "shared_verify_geotiff_hard_pass": hard_pass,
        "checks": checks,
        "inside_footprint_nan_count": int(np.isnan(inside).sum()),
        "outside_footprint_nan_count": int(np.isnan(outside).sum()),
        "inside_footprint_finite": bool(np.isfinite(inside).all()),
        "inside_footprint_min": float(inside.min()),
        "inside_footprint_max": float(inside.max()),
        "inside_footprint_range_0_1": bool(inside.min() >= 0.0 and inside.max() <= 1.0),
        "all_values_in_0_1": bool(np.isfinite(array).all() and array.min() >= 0.0 and array.max() <= 1.0),
        "crs_shape_transform": grid_info,
        "grid_matches_template": bool(checks["grid_matches_template"]["pass"]),
        "zip_single_tif_verified": True,
    }
    format_pass = hard_pass and validator["inside_footprint_nan_count"] == 0 and validator["all_values_in_0_1"]
    if not format_pass:
        result["status"] = "format_validation_failure"
        result["stop_reason"] = "shared GeoTIFF validator or explicit grid/range/NaN check failed"
    else:
        result["status"] = "research_artifact_validated_not_submittable"
    result["validator"] = validator
    result["raster"] = {
        "path": str(tif_path.relative_to(paths.REPO)),
        "sha256": verified["sha256"],
        "bytes": verified["bytes"],
        "dot_count": int(dots.sum()),
        "content_id": content_id,
        "zip_path": str(zip_path.relative_to(paths.REPO)),
        "zip_sha256": sha256_file(zip_path),
        "zip_bytes": zip_path.stat().st_size,
        "outside_footprint_convention": "all finite zero values",
    }
    result["candidate_manifest"] = str((paths.DOCS / "downloads" / "h29_2_candidate_manifest.json").relative_to(paths.REPO))
    result["candidate_path_for_download"] = str(tif_path.relative_to(paths.REPO))
    result["holdout_gate_pass"] = bool(holdout_result.get("gate_efficacy_pass"))
    result["verdict"] = (
        "promote" if format_pass and holdout_result.get("gate_efficacy_pass") and not surface_duplicate and not dot_duplicate
        else "negative"
    )
    result["ok_to_submit"] = False  # selector decision and weekly slot explicitly not authorized
    result["submission_status"] = "NOT OK TO SUBMIT — separate selector approval has not occurred"
    result["submission_name"] = SUBMISSION_NAME
    result["note_max_140_chars"] = NOTE
    result["note_chars"] = len(NOTE)

    manifest = {
        "hypothesis": HYPOTHESIS, "mechanism": MECHANISM,
        "named_non_fault_mimic": NONFAULT_MIMIC,
        "raster": result["raster"], "holdout_gate_pass": result["holdout_gate_pass"],
        "verdict": result["verdict"], "ok_to_submit": False,
        "submission_status": result["submission_status"],
        "submission_name": SUBMISSION_NAME, "note_max_140_chars": NOTE,
    }
    json_dump(paths.DOCS / "downloads" / "h29_2_candidate_manifest.json", manifest)
    return result


def write_run_card(inputs: dict | None, holdout_result: dict | None, e3: dict | None,
                   error: str | None = None) -> dict:
    hold = holdout_result or {}
    holdout_card = {
        "label": "HOLDOUT-DTI",
        "evaluator": "gems27.metric.dti_binary v1; alpha=0.2, beta=0.8, 300m triangular kernel; whole-FID seeds 300–309",
        "seeds": list(SEEDS),
        "n_withheld_positives_total": hold.get("bootstrap", {}).get("n_withheld_positives_total"),
        "pooled_candidate_dti": hold.get("bootstrap", {}).get("pooled_candidate"),
        "pooled_candidate_ci95": hold.get("bootstrap", {}).get("pooled_candidate_ci95_seed_bootstrap"),
        "pooled_control_dti": hold.get("bootstrap", {}).get("pooled_control"),
        "pooled_control_ci95": hold.get("bootstrap", {}).get("pooled_control_ci95_seed_bootstrap"),
        "paired_pooled_delta": hold.get("bootstrap", {}).get("paired_pooled_delta"),
        "paired_pooled_delta_ci95": hold.get("bootstrap", {}).get("paired_pooled_delta_ci95_seed_bootstrap"),
        "mean_per_seed_paired_delta": hold.get("bootstrap", {}).get("mean_per_seed_paired_delta"),
        "mean_per_seed_paired_delta_ci95": hold.get("bootstrap", {}).get("mean_per_seed_paired_delta_ci95_seed_bootstrap"),
        "seeds_improved": hold.get("bootstrap", {}).get("seeds_improved"),
        "gate_efficacy_pass": bool(hold.get("gate_efficacy_pass", False)),
        "status": hold.get("status", "not_run"),
        "per_seed": hold.get("per_seed", []),
        "canary_max_auc": hold.get("canary_max_auc"),
        "canary_leak_flags": hold.get("canary_leak_flags", {}),
    }
    raster = (e3 or {}).get("raster")
    validator = (e3 or {}).get("validator")
    if validator is None:
        validator = {
            "status": "not_run_no_tiff_written_duplicate_gate" if e3 else "not_run",
            "reason": (e3 or {}).get("stop_reason", "no E3 raster was created"),
            "inside_footprint_nan_count": None,
            "outside_footprint_nan_count": None,
            "inside_footprint_range_0_1": None,
            "all_values_in_0_1": None,
            "crs_shape_transform": None,
            "shared_verify_geotiff_hard_pass": None,
        }
    card = {
        "run_card": "H29-2 DIPDIRECT-conditioned up-dip edge projection; frozen preregistration",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "preregistration": "knowledge/21_preregistration_H29-2_20261025.md",
        "hypothesis": HYPOTHESIS,
        "mechanism": MECHANISM,
        "named_non_fault_mimic": NONFAULT_MIMIC,
        "holdout": holdout_card,
        "uniqueness_vs_registry": {
            "surface_correlations": (e3 or {}).get("surface_correlations", {}),
            "max_surface_spearman": (e3 or {}).get("max_surface_spearman"),
            "worst_surface_reference": (e3 or {}).get("worst_surface_reference"),
            "surface_threshold": 0.90,
            "surface_duplicate": (e3 or {}).get("surface_duplicate"),
            "dot_overlap_by_reference": (e3 or {}).get("dot_overlap_by_reference", {}),
            "max_dot_overlap_within_3px": (e3 or {}).get("max_dot_overlap_within_3px"),
            "worst_dot_reference": (e3 or {}).get("worst_dot_reference"),
            "dot_overlap_threshold": 0.70,
            "dot_duplicate": (e3 or {}).get("dot_duplicate"),
            "status": (e3 or {}).get("status", "not_run"),
        },
        "raster": raster,
        "raster_sha256": raster.get("sha256") if raster else None,
        "validator": validator,
        "submission_name": SUBMISSION_NAME,
        "note_max_140_chars": NOTE,
        "note_chars": len(NOTE),
        "ok_to_submit": False,
        "submission_status": "NOT OK TO SUBMIT — selector approval and weekly slot were not authorized",
        "verdict": (e3 or {}).get("verdict", "negative"),
        "verdict_reason": error or (e3 or {}).get("stop_reason") or (e3 or {}).get("status"),
        "live_score": None,
        "live_score_label": "UNSCORED — no ORGANIZER-CONFIRMED result or receipt exists for this file",
        "input_hashes": inputs,
        "holdout_evidence": str(HOLDOUT_OUT.relative_to(paths.REPO)),
        "candidate_path_for_download": (e3 or {}).get("candidate_path_for_download"),
        "experiment_budget": {"max_experiments": 3, "max_runtime_seconds": MAX_RUNTIME_S,
                              "experiments": ["E1 leakage/integrity canary", "E2 paired holdout", "E3 full-fit uniqueness/format"]},
    }
    json_dump(RUN_CARD_OUT, card)
    return card


def run(start: float) -> dict:
    inputs = verify_inputs()
    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    names = inputs["feature_names"]
    X = np.load(paths.PREPARED_FEATURES, mmap_mode="r")
    if X.shape != (int(foot.sum()), 32):
        raise ValueError(f"prepared feature matrix has unexpected shape {X.shape}")
    group_map, group_meta = load_or_build_group_map(labels, foot, inputs)
    vector_features = json.loads(paths.QFAULT_VECTORS.read_text())["features"]
    if len(vector_features) != int(group_meta["n_vector_features"]):
        raise ValueError("vector inventory size differs from attribution cache")
    print("building/reusing frozen 15-band transforms", flush=True)
    T = build_or_load_subsurface(foot, X, names, inputs)
    print("building/reusing RTP/depth edge ranks", flush=True)
    edges = build_or_load_edge_ranks(foot, X, names, inputs)
    integrity = {"group_map": group_meta, "seeds": []}
    canaries = []
    max_auc = 0.0
    leakage_flags = {}

    # E1: all whole-FID splits and feature-only canaries; no detector outcome is inspected here.
    for seed in SEEDS:
        check_time(start)
        split, training, scoring, hidden_ring = get_split(seed, labels, foot, group_map)
        features, feature_integrity = visible_dip_features(
            seed, split, training, hidden_ring, vector_features, edges, inputs
        )
        canary = canary_auc(features, split, scoring, labels, foot, seed)
        for name, result in canary["direction_invariant_auc"].items():
            max_auc = max(max_auc, float(result["auc"]))
            if not result["pass"]:
                leakage_flags[f"seed{seed}:{name}"] = float(result["auc"])
        record = {
            "seed": int(seed), "hidden_group_count": int(len(split.hidden_group_ids)),
            "hidden_positive_count": int(split.hidden.sum()),
            "visible_positive_count": int(split.known.sum()),
            "hidden_group_ids": list(split.hidden_group_ids),
            "hidden_ring_pixels": int(hidden_ring.sum()),
            "training_pixels": int(training.sum()),
            "scoring_pixels": int(scoring.sum()),
            "feature_integrity": feature_integrity,
            "canary": canary,
        }
        integrity["seeds"].append(record)
        canaries.append(canary)
        json_dump(HOLDOUT_OUT, {
            "experiment": "H29-2 E1 leakage/integrity canary",
            "status": "e1_in_progress",
            "preregistration": "knowledge/21_preregistration_H29-2_20261025.md",
            "seeds_tested": [x["seed"] for x in integrity["seeds"]],
            "integrity": integrity, "canary_by_seed": canaries,
            "canary_max_auc": max_auc, "canary_leak_flags": leakage_flags,
            "gate_efficacy_pass": False, "per_seed": [],
            "runtime_s": round(time.time() - start, 1),
        })
        print(f"E1 seed {seed}: hidden={record['hidden_positive_count']:,}; "
              f"max direction-invariant AUC="
              f"{max(v['auc'] for v in canary['direction_invariant_auc'].values()):.4f}", flush=True)
        if leakage_flags:
            result = {
                "experiment": "H29-2 E1 stopped on preregistered leakage canary",
                "status": "leakage_stop", "preregistration": "knowledge/21_preregistration_H29-2_20261025.md",
                "seeds_tested": [x["seed"] for x in integrity["seeds"]],
                "integrity": integrity, "canary_by_seed": canaries,
                "canary_max_auc": max_auc, "canary_leak_flags": leakage_flags,
                "gate_efficacy_pass": False, "per_seed": [],
                "runtime_s": round(time.time() - start, 1),
            }
            json_dump(HOLDOUT_OUT, result)
            return {"inputs": inputs, "holdout": result, "e3": None,
                    "error": "E1 stop: feature-only AUC exceeded 0.90"}

    json_dump(HOLDOUT_OUT, {
        "experiment": "H29-2 E1 leakage/integrity canary passed; E2 pending",
        "status": "e1_complete_e2_pending",
        "preregistration": "knowledge/21_preregistration_H29-2_20261025.md",
        "seeds_tested": list(SEEDS), "integrity": integrity,
        "canary_by_seed": canaries, "canary_max_auc": max_auc,
        "canary_leak_flags": leakage_flags, "gate_efficacy_pass": False,
        "per_seed": [], "runtime_s": round(time.time() - start, 1),
    })

    # E2: paired whole-FID D vs D+dip on the same visible labels, negative draws and emission budget.
    control_cells, candidate_cells, per_seed = [], [], []
    for seed in SEEDS:
        check_time(start)
        split, training, scoring, hidden_ring = get_split(seed, labels, foot, group_map)
        features, feature_integrity = visible_dip_features(
            seed, split, training, hidden_ring, vector_features, edges, inputs
        )
        base_cache = WORK / f"prob_seed{seed}_D.npy"
        cand_cache = WORK / f"prob_seed{seed}_Ddip.npy"
        model_key = {
            "seed": int(seed), "feature_hash": inputs["prepared_features_sha256"],
            "subsurface_hash": sha256_file(WORK / "subsurface_transforms.npy"),
            "dip_feature_hash": sha256_file(WORK / f"dip_features_seed{seed}.npy"),
            "training_mask": "whole-FID visible labels outside 600m buffer",
            "negative_ratio": NEG_RATIO,
        }
        for arm, cache in (("D", base_cache), ("D+dip", cand_cache)):
            extra = T if arm == "D" else np.concatenate(
                (np.asarray(T, dtype=np.float32), np.asarray(features, dtype=np.float32)), axis=1
            )
            meta_path = cache.with_suffix(".json")
            probability = None
            if cache.is_file() and meta_path.is_file():
                old = json.loads(meta_path.read_text())
                if old.get("cache_key") == model_key | {"arm": arm} and old.get("array_sha256") == sha256_file(cache):
                    probability = np.load(cache, mmap_mode="r")
            if probability is None:
                print(f"E2 seed {seed} fit {arm}", flush=True)
                probability = oof_detector.fit_predict_visible_probabilities(
                    foot, split.known, training, extra=extra, neg_ratio=NEG_RATIO,
                    seed=2026 + seed, base_features=X,
                )
                np.save(cache, probability)
                json_dump(meta_path, {"cache_key": model_key | {"arm": arm},
                                      "array_sha256": sha256_file(cache)})
                probability = np.load(cache, mmap_mode="r")
            dots = emit(probability, split, scoring, BUDGET)
            scored = score_split(dots, split, scoring)
            if arm == "D":
                control_cells.append(scored)
            else:
                candidate_cells.append(scored)
            del dots, probability, extra
        control = control_cells[-1]
        candidate = candidate_cells[-1]
        per_seed.append({
            "seed": int(seed), "hidden_group_count": int(len(split.hidden_group_ids)),
            "hidden_positive_count": int(split.hidden.sum()),
            "control": control, "candidate": candidate,
            "paired_dti_delta": float(candidate["dti"] - control["dti"]),
            "control_emitted": int(control["n_emitted"]),
            "candidate_emitted": int(candidate["n_emitted"]),
            "feature_source_integrity": feature_integrity,
        })
        json_dump(HOLDOUT_OUT, {
            "experiment": "H29-2 E1 clean; E2 paired whole-FID holdout in progress",
            "status": "e2_in_progress",
            "preregistration": "knowledge/21_preregistration_H29-2_20261025.md",
            "seeds_tested": list(SEEDS), "integrity": integrity,
            "canary_by_seed": canaries, "canary_max_auc": max_auc,
            "canary_leak_flags": leakage_flags, "per_seed": per_seed,
            "partial_pooled_control_dti": aggregate(control_cells),
            "partial_pooled_candidate_dti": aggregate(candidate_cells),
            "gate_efficacy_pass": False,
            "runtime_s": round(time.time() - start, 1),
        })
        print(f"E2 seed {seed}: D={control['dti']:.5f}, D+dip={candidate['dti']:.5f}, "
              f"delta={per_seed[-1]['paired_dti_delta']:+.5f}", flush=True)
        del features

    bootstrap = bootstrap_holdout(control_cells, candidate_cells)
    gate_efficacy = bool(
        bootstrap["pooled_candidate"] > bootstrap["pooled_control"]
        and bootstrap["mean_per_seed_paired_delta"] > 0.0
        and bootstrap["mean_per_seed_paired_delta_ci95_seed_bootstrap"][0] > 0.0
        and bootstrap["seeds_improved"] >= 8
        and not leakage_flags
    )
    holdout_result = {
        "experiment": "H29-2 E1 leakage/integrity and E2 paired whole-FID holdout",
        "status": "complete", "preregistration": "knowledge/21_preregistration_H29-2_20261025.md",
        "evaluator": "gems27.metric.dti_binary v1; alpha=0.2, beta=0.8, 300m triangular kernel",
        "label": "HOLDOUT-DTI (catalogue-internal whole-FID hide-and-recover; not an organizer score)",
        "split": {"unit": "complete NBMG Qfaults vector-feature index / FID",
                  "stratification": "group-positive-pixel centroid quadrant",
                  "hide_fraction_per_quadrant": 0.20, "buffer_px": BUFFER_PX,
                  "buffer_m": BUFFER_PX * grid.PIXEL_M,
                  "known_labels_masked_pixel_exactly": True,
                  "seeds": list(SEEDS)},
        "arms": {"control": "D: 32 cached bands + 15 shared subsurface transforms",
                 "candidate": "D+dip: control + 3 DIPDIRECT up-dip edge transforms"},
        "emission": {"budget_per_arm_seed": BUDGET, "min_distance_px": MIN_DIST_PX,
                     "visible_fault_exclusion_px": B_EXCL_PX,
                     "canary_negative_sample_max": CANARY_NEG_MAX},
        "canary_by_seed": canaries, "canary_max_auc": max_auc,
        "canary_leak_flags": leakage_flags,
        "integrity": integrity,
        "per_seed": per_seed,
        "bootstrap": bootstrap,
        "gate_efficacy_pass": gate_efficacy,
        "runtime_s": round(time.time() - start, 1),
    }
    json_dump(HOLDOUT_OUT, holdout_result)
    print(f"E2 pooled HOLDOUT-DTI: D={bootstrap['pooled_control']:.5f} "
          f"D+dip={bootstrap['pooled_candidate']:.5f}; paired seed-mean delta="
          f"{bootstrap['mean_per_seed_paired_delta']:+.5f}, 95% CI="
          f"{bootstrap['mean_per_seed_paired_delta_ci95_seed_bootstrap']}; "
          f"improved seeds={bootstrap['seeds_improved']}/10; gate={gate_efficacy}", flush=True)

    # E3: one full-fit surface-uniqueness check before placement, then one final-dot/format pass.
    check_time(start)
    e3 = full_fit_and_candidate(inputs, foot, labels, X, names, T, edges, holdout_result, start)
    print(f"E3 status={e3.get('status')} surface max={e3.get('max_surface_spearman')} "
          f"dot max={e3.get('max_dot_overlap_within_3px')}", flush=True)
    return {"inputs": inputs, "holdout": holdout_result, "e3": e3, "error": None}


def main() -> int:
    start = time.time()
    WORK.mkdir(parents=True, exist_ok=True)
    inputs = None
    holdout_result = None
    e3 = None
    error = None
    try:
        outcome = run(start)
        inputs, holdout_result, e3, error = outcome["inputs"], outcome["holdout"], outcome["e3"], outcome["error"]
    except TimeoutError as exc:
        error = str(exc)
        print(error, file=sys.stderr, flush=True)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        print(error, file=sys.stderr, flush=True)
        raise
    finally:
        if holdout_result is None and HOLDOUT_OUT.is_file():
            try:
                holdout_result = json.loads(HOLDOUT_OUT.read_text())
            except (OSError, json.JSONDecodeError):
                holdout_result = None
        card = write_run_card(inputs, holdout_result, e3, error)
        print(json.dumps({"run_card": str(RUN_CARD_OUT.relative_to(paths.REPO)),
                          "holdout": card["holdout"], "uniqueness": card["uniqueness_vs_registry"],
                          "raster": card["raster"], "validator": card["validator"],
                          "verdict": card["verdict"], "ok_to_submit": card["ok_to_submit"],
                          "error": error}, indent=2, default=float), flush=True)
    return 0 if holdout_result and holdout_result.get("status") == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
