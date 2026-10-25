#!/usr/bin/env python3
"""Build H28-3 only as an explicitly ineligible negative-result research TIFF.

The frozen H28-3 gate failed, so this script refuses to produce an upload recommendation or alter the
weekly-slot manifest. It exists to preserve a fully reproducible, format-validated negative result
when a separate duplicate screen confirms its pixels are not a copied registry raster. Output is
written only to a caller-selected research directory; it is never linked as a one-click submission.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from scripts.run_h28_1_edge_holdout import (  # noqa: E402
    load_or_build_edge_matrix,
    validate_prepared_feature_metadata,
)
from scripts.run_h28_3_strain_holdout import load_or_build_strain_matrix  # noqa: E402

from gems27 import candidates, grid, metric, oof_detector, paths, submission  # noqa: E402

DATE = "20261025"
SLUG = "h28-3-strain-conductivity-negative-research"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def build_prediction(foot: np.ndarray, labels: np.ndarray, probability: np.ndarray) -> tuple[np.ndarray, dict]:
    ridges = oof_detector.ridge_nms(probability, foot, sigma=1.0)
    base = oof_detector.build_oof_dotted_base(
        probability, ridges, foot, labels, budget_frac=oof_detector.PRE_THIN_FRAC, thin_d=1.5
    )
    active = foot & ~labels
    base &= active
    d_catalogue = distance_transform_edt(~labels)
    pruned = base & (d_catalogue > 1.0)
    d_pruned = distance_transform_edt(~pruned) if pruned.any() else np.full(foot.shape, np.inf)
    topology = candidates.build_set(labels, foot, pruned)
    additions = topology["dots_nonredundant"] & active & (d_pruned >= metric.RADIUS_PX)
    prediction = pruned | additions
    if np.any(prediction & labels) or np.any(prediction & ~foot):
        raise SystemExit("H28-3 research raster violates catalogue/footprint exclusion")
    return prediction, {
        "base_before_prune": int(base.sum()),
        "base_after_prune": int(pruned.sum()),
        "flank_pruned": int((base & ~pruned).sum()),
        "topology_added": int(additions.sum()),
        "emitted": int(prediction.sum()),
        "known_catalogue_overlap": int((prediction & labels).sum()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    evidence_path = paths.EVIDENCE / "h28_3_strain_holdout.json"
    if not evidence_path.exists():
        raise SystemExit("Missing H28-3 holdout evidence")
    evidence = json.loads(evidence_path.read_text())
    if evidence.get("gate", {}).get("pass"):
        raise SystemExit("H28-3 passed; use a separately preregistered candidate builder, not the negative builder")
    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    prepared = validate_prepared_feature_metadata(foot)
    edge, edge_meta = load_or_build_edge_matrix(foot)
    strain, strain_meta = load_or_build_strain_matrix(foot)
    extra = np.concatenate((np.asarray(edge), np.asarray(strain)), axis=1)
    probability = oof_detector.fit_predict_full_probabilities(foot, labels, extra=extra)
    if not np.isfinite(probability[foot]).all() or not ((probability[foot] >= 0) & (probability[foot] <= 1)).all():
        raise SystemExit("H28-3 full fit produced invalid probabilities")
    prediction, prediction_meta = build_prediction(foot, labels, probability)
    content_id = submission.scored_content_id(prediction.astype(np.float32), foot, labels)
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    nan_name = submission.make_filename("gems27", SLUG, DATE, content_id, "nan")
    finite_name = submission.make_filename("gems27", SLUG, DATE, content_id, "allfinite")
    note_name = f"note-{nan_name[:-4]}.txt"
    check_name = f"checks-{nan_name[:-4]}.json"
    manifest_name = "h28_3_negative_research_manifest.json"
    planned = (nan_name, finite_name, note_name, check_name, manifest_name)
    if any((out / name).exists() for name in planned):
        raise SystemExit("Negative-research output already exists; refusing replacement")
    note = submission.make_note(
        "H28-3 NEGATIVE — DO NOT SUBMIT",
        "failed frozen HOLDOUT-DTI gate; research-only, not slot-eligible",
        content_id,
        status="NOT APPROVED FOR SUBMISSION",
    )
    nan_path = submission.write_geotiff(prediction.astype(np.float32), paths.TEMPLATE, out / nan_name, outside="nan")
    finite_path = submission.write_geotiff(prediction.astype(np.float32), paths.TEMPLATE, out / finite_name, outside="zero")
    nan_report = submission.verify_geotiff(nan_path, paths.TEMPLATE)
    finite_report = submission.verify_geotiff(finite_path, paths.TEMPLATE)
    if not nan_report["hard_checks_passed"] or not finite_report["hard_checks_passed"]:
        raise SystemExit("Negative research GeoTIFF failed submission-format validator")
    zip_path = submission.zip_single(finite_path, finite_path.with_suffix(".zip"))
    (out / note_name).write_text(note + "\n")
    record = {
        "status": "NEGATIVE RESEARCH ARTIFACT — NOT APPROVED FOR SUBMISSION",
        "why_not_submit": "H28-3 failed its frozen holdout gate; format validity and uniqueness cannot substitute for predictive validation.",
        "holdout_evidence": evidence_path.name,
        "holdout_gate": evidence["gate"],
        "files": {
            "nan": nan_name,
            "allfinite": finite_name,
            "zip_of_allfinite": zip_path.name,
            "note": note_name,
            "checks": check_name,
        },
        "content_id": content_id,
        "note": note,
        "prediction": prediction_meta,
        "prepared": prepared,
        "edge_features": edge_meta,
        "strain_features": strain_meta,
        "checks": {"nan": nan_report, "allfinite": finite_report},
        "hashes": {
            "builder": sha256_file(Path(__file__).resolve()),
            "holdout_runner": sha256_file(Path(__file__).resolve().parent / "run_h28_3_strain_holdout.py"),
            "transform": sha256_file(Path(__file__).resolve().parents[1] / "src/gems27/strain_conductivity.py"),
        },
    }
    (out / check_name).write_text(json.dumps({"nan": nan_report, "allfinite": finite_report}, indent=2) + "\n")
    (out / manifest_name).write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"status": record["status"], "allfinite": finite_name, "content_id": content_id, "emitted": prediction_meta["emitted"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
