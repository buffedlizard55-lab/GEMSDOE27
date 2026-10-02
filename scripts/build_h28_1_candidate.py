#!/usr/bin/env python3
"""Build the preregistered H28-1 full-map research candidate after its OOF gate passed.

This creates an unscored research artifact only. It does not alter the three weekly-slot files, their
manifest, or any leaderboard entry. See knowledge/09_preregistration_H28-1_candidate.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt
from sklearn.ensemble import HistGradientBoostingClassifier

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from scripts.run_h28_1_edge_holdout import (  # noqa: E402
    load_or_build_edge_matrix,
    validate_prepared_feature_metadata,
)

from gems27 import candidates, grid, metric, oof_detector, paths, submission  # noqa: E402

DATE = "20261002"
SLUG = "h28-1-edge-coherence-plus-t-v2-h27-4"
NEG_RATIO = 10
SEED = 2026
PREDICT_CHUNK_ROWS = 100_000


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def train_full_probability_map(
    foot: np.ndarray,
    labels: np.ndarray,
    edge_features: np.ndarray,
    *,
    seed: int = SEED,
) -> tuple[np.ndarray, dict]:
    """Fit the frozen HGB configuration on all catalogue positives and 10:1 sampled negatives."""
    base_features = np.load(paths.PREPARED_FEATURES, mmap_mode="r")
    foot_rc = np.argwhere(foot)
    y = labels[foot].astype(bool)
    if base_features.shape[0] != len(foot_rc) or edge_features.shape[0] != len(foot_rc):
        raise ValueError("base/edge feature rows must match row-major footprint order")
    positive = np.flatnonzero(y)
    negative = np.flatnonzero(~y)
    if not len(positive) or not len(negative):
        raise ValueError("full-map training requires both positive and negative footprint labels")
    rng = np.random.default_rng(seed)
    n_negative = min(len(negative), len(positive) * NEG_RATIO)
    negative_sample = rng.choice(negative, size=n_negative, replace=False)
    train_idx = np.concatenate((positive, negative_sample))
    x_train = np.concatenate((base_features[train_idx], edge_features[train_idx]), axis=1)
    y_train = y[train_idx].astype(np.uint8)

    clf = HistGradientBoostingClassifier(
        max_iter=100,
        max_leaf_nodes=31,
        learning_rate=0.08,
        l2_regularization=5.0,
        random_state=seed,
    )
    clf.fit(x_train, y_train)

    probability = np.zeros(foot.shape, dtype=np.float32)
    for start in range(0, len(foot_rc), PREDICT_CHUNK_ROWS):
        stop = min(start + PREDICT_CHUNK_ROWS, len(foot_rc))
        rows = slice(start, stop)
        x_chunk = np.concatenate((base_features[rows], edge_features[rows]), axis=1)
        p = clf.predict_proba(x_chunk)[:, 1].astype(np.float32)
        if not np.isfinite(p).all() or np.any((p < 0.0) | (p > 1.0)):
            raise SystemExit(f"invalid full-model probabilities in footprint rows {start}:{stop}")
        rc = foot_rc[rows]
        probability[rc[:, 0], rc[:, 1]] = p
    if not np.isfinite(probability[foot]).all():
        raise SystemExit("full-map probabilities are non-finite inside the footprint")
    model_meta = {
        "estimator": "sklearn.ensemble.HistGradientBoostingClassifier",
        "parameters": {
            "max_iter": 100,
            "max_leaf_nodes": 31,
            "learning_rate": 0.08,
            "l2_regularization": 5.0,
            "random_state": seed,
        },
        "seed": seed,
        "positive_training_rows": int(len(positive)),
        "negative_training_rows": int(n_negative),
        "negative_to_positive_cap": NEG_RATIO,
        "prediction_chunk_rows": PREDICT_CHUNK_ROWS,
        "features": int(x_train.shape[1]),
    }
    del clf, x_train, y_train, base_features
    return probability, model_meta


def build_prediction(foot: np.ndarray, labels: np.ndarray, probability: np.ndarray) -> tuple[np.ndarray, dict]:
    """Apply the already-gated base, H27-4 r1 prune, and T-v2 nonredundant graph additions."""
    ridges = oof_detector.ridge_nms(probability, foot, sigma=1.0)
    base = oof_detector.build_oof_dotted_base(
        probability,
        ridges,
        foot,
        labels,
        budget_frac=oof_detector.PRE_THIN_FRAC,
        thin_d=1.5,
    )
    active = foot & ~labels
    base &= active
    distance_to_catalogue = distance_transform_edt(~labels)
    pruned = base & (distance_to_catalogue > 1.0)
    distance_to_pruned = (
        distance_transform_edt(~pruned) if pruned.any() else np.full(foot.shape, np.inf)
    )

    topology = candidates.build_set(labels, foot, pruned)
    additions = topology["dots_nonredundant"] & active
    additions &= distance_to_pruned >= metric.RADIUS_PX
    prediction = pruned | additions
    if np.any(prediction & labels) or np.any(prediction & ~foot):
        raise SystemExit("candidate overlaps known catalogue or leaves the template footprint")
    metadata = {
        "prethin_budget_fraction": oof_detector.PRE_THIN_FRAC,
        "dot_thin_distance_px": 1.5,
        "prune_catalogue_distance_px": 1.0,
        "topology_rule": "T-v2, z>=3, mutual links deduplicated, at least 300 m from pruned model",
        "catalogue_graph_components": int(topology["graph"]["components"]),
        "selected_links": int(len(topology["links"])),
        "base_pixels_before_prune": int(base.sum()),
        "base_pixels_after_prune": int(pruned.sum()),
        "base_pixels_pruned": int((base & ~pruned).sum()),
        "topology_pixels_nonredundant": int(additions.sum()),
        "emitted_pixels": int(prediction.sum()),
        "known_catalogue_overlap_pixels": int((prediction & labels).sum()),
        "outside_footprint_pixels": int((prediction & ~foot).sum()),
    }
    return prediction, metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=str(paths.DOCS / "downloads"))
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "h28_1_candidate_manifest.json"
    existing = list(out_dir.glob(f"gems27-{SLUG}-{DATE}-*-nan.tif"))
    if manifest_path.exists() or existing:
        raise SystemExit("H28-1 research candidate already exists; refusing to replace it")

    gate_path = paths.EVIDENCE / "h28_1_edge_holdout.json"
    if not gate_path.exists():
        raise SystemExit("H28-1 holdout evidence is missing; refusing candidate generation")
    gate = json.loads(gate_path.read_text())
    if not gate.get("gate", {}).get("pass") or gate.get("seeds") != list(range(140, 150)):
        raise SystemExit("H28-1 did not pass its exact frozen seed 140-149 gate")

    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    if labels.shape != foot.shape or not np.isin(labels, (False, True, 0, 1)).all():
        raise SystemExit("labels differ from the template grid or are not binary")
    prepared_meta = validate_prepared_feature_metadata(foot)
    edge_features, edge_meta = load_or_build_edge_matrix(foot)
    if edge_meta["feature_names"] != [
        "potential_mag_edge_300m",
        "potential_mag_edge_1000m",
        "potential_grav_edge_300m",
        "potential_grav_edge_1000m",
        "potential_edge_concordance_1000m",
        "potential_edge_orientation_agreement_1000m",
    ]:
        raise SystemExit("edge matrix feature order differs from the preregistration")

    probability, model_meta = train_full_probability_map(foot, labels, edge_features)
    prediction, prediction_meta = build_prediction(foot, labels, probability)
    content_id = submission.scored_content_id(prediction.astype(np.float32), foot, labels)
    note = submission.make_note(
        "H28-1 research",
        "OOF +0.0029 paired DTI; 3/4 folds, 9/10 seeds; no live score",
        content_id,
        status="research only; not yet live-scored",
    )
    nan_name = submission.make_filename("gems27", SLUG, DATE, content_id, "nan")
    allfinite_name = submission.make_filename("gems27", SLUG, DATE, content_id, "allfinite")
    zip_name = Path(nan_name).with_suffix(".zip").name
    note_name = f"note-{nan_name[:-4]}.txt"
    checks_name = f"checks-{nan_name[:-4]}.json"
    planned_outputs = (nan_name, allfinite_name, zip_name, note_name, checks_name)
    if any((out_dir / name).exists() for name in planned_outputs):
        raise SystemExit("A content-hashed H28-1 output path already exists; refusing to overwrite")
    nan_path = submission.write_geotiff(
        prediction.astype(np.float32), paths.TEMPLATE, out_dir / nan_name, outside="nan"
    )
    allfinite_path = submission.write_geotiff(
        prediction.astype(np.float32), paths.TEMPLATE, out_dir / allfinite_name, outside="zero"
    )
    nan_report = submission.verify_geotiff(nan_path, paths.TEMPLATE)
    allfinite_report = submission.verify_geotiff(allfinite_path, paths.TEMPLATE)
    if not nan_report["hard_checks_passed"] or not allfinite_report["hard_checks_passed"]:
        raise SystemExit(
            f"candidate GeoTIFF failed validation: nan={nan_report['hard_failures']}, "
            f"allfinite={allfinite_report['hard_failures']}"
        )
    zip_path = submission.zip_single(nan_path)
    note_path = out_dir / note_name
    note_path.write_text(note + "\n")
    checks_path = out_dir / checks_name

    code_hashes = {
        "builder": sha256_file(Path(__file__).resolve()),
        "transform": sha256_file(Path(__file__).resolve().parents[1] / "src/gems27/potential_edges.py"),
        "oof_detector": sha256_file(Path(__file__).resolve().parents[1] / "src/gems27/oof_detector.py"),
    }
    input_hashes = {
        "training_raster": sha256_file(paths.TRAINING),
        "template": sha256_file(paths.TEMPLATE),
        "labels": sha256_file(paths.LABELS),
        "prepared_features": sha256_file(paths.PREPARED_FEATURES),
        "prepared_metadata": sha256_file(paths.PREPARED_META),
        "edge_features": edge_meta["sha256"],
        "edge_metadata": sha256_file(paths.PREPARED_FEATURES.parent / "h28_1_edge_features.json"),
        "holdout_evidence": sha256_file(gate_path),
    }
    checks = {
        "status": "research-only full-map candidate; no weekly slot used; no live score",
        "holdout_gate_passed": True,
        "holdout_evidence": str(gate_path.relative_to(paths.REPO)),
        "holdout_mean_gain": gate["candidate_minus_baseline_mean_gain"],
        "holdout_folds_improved": gate["improved_fold_count"],
        "holdout_positive_seeds": gate["positive_seed_count"],
        "prepared_feature_metadata": prepared_meta,
        "edge_feature_metadata": edge_meta,
        "model": model_meta,
        "prediction": prediction_meta,
        "code_sha256": code_hashes,
        "input_sha256": input_hashes,
        "geotiff": {"nan": nan_report, "allfinite": allfinite_report},
        "zip": {"file": zip_path.name, "bytes": zip_path.stat().st_size, "sha256": sha256_file(zip_path)},
        "note": note,
        "note_chars": len(note),
        "content_id": content_id,
        "candidate_files_written": True,
        "leaderboard_upload": False,
        "weekly_slot_used": False,
    }
    checks_path.write_text(json.dumps(checks, indent=2) + "\n")
    manifest = {
        "schema": 1,
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "research candidate only; not one of the current three weekly slots; unscored",
        "holdout_evidence": str(gate_path.relative_to(paths.REPO)),
        "candidate": {
            "hypothesis": "H28-1 + T-v2 + H27-4 r1",
            "content_id": content_id,
            "nan": nan_name,
            "allfinite": allfinite_name,
            "zip": zip_path.name,
            "note": note,
            "sha256_nan": nan_report["sha256"],
            "bytes_nan": nan_report["bytes"],
            "emitted_px": int(prediction.sum()),
            "checks": checks_path.name,
            "format_verified": True,
            "holdout_mean_gain": gate["candidate_minus_baseline_mean_gain"],
            "holdout_folds_improved": gate["improved_fold_count"],
            "holdout_positive_seeds": gate["positive_seed_count"],
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
