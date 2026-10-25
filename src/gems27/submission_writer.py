"""Fail-closed submission writer and automated gate validator for GEMSDOE27.

Delegates GeoTIFF/ZIP serialization and independent multi-reader inspection to
`src/gems27/submission.py`, while enforcing the Parallel-Run Protocol contract:
  - No silent repair or clipping: predictions inside the footprint must already be finite in [0, 1].
  - Zero positive predictions on `existing_faults` (`catalogue`) and zero positive outside footprint.
  - Both `submission_name` and `note` are validated to `1..140` characters (satisfying both the
    `<= 140` Run Card cap and DrivenData's `<= 200` character note limit).
  - Emits both the zero-outside primary file (`-zeros.tif`, immune to strict whole-array `[0, 1]`
    validators and live-proven identical to `-nan` on `GEMSDOE25`/`GEMSDOE30` `0.2600` and
    `GEMSDOE32` `0.2778`) and the sample-matched `-nan.tif` + `.zip` companions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from . import grid, submission

NOTE_LIMIT = 140


def validate_text_limit(value: str, field_name: str, limit: int = NOTE_LIMIT) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    s = value.strip()
    if not s or len(s) > limit:
        raise ValueError(f"{field_name} must be 1..{limit} non-whitespace characters (got {len(s)})")
    return s


def write_validated_submission_bundle(
    prediction: np.ndarray,
    *,
    template_path: Path | str,
    footprint: np.ndarray,
    catalogue: np.ndarray,
    out_dir: Path | str,
    family: str,
    slug: str,
    date_tag: str,
    note_summary: str,
    hypothesis_id: str,
) -> dict[str, Any]:
    """Write and independently re-verify `-zeros.tif`, `-nan.tif`, and `.zip` submission artifacts."""
    foot = np.asarray(footprint, dtype=bool)
    cat = np.asarray(catalogue, dtype=bool)
    raw = np.asarray(prediction)
    if raw.shape != grid.SHAPE or foot.shape != grid.SHAPE or cat.shape != grid.SHAPE:
        raise ValueError(f"expected shape {grid.SHAPE}, got {raw.shape}")

    inside = raw[foot]
    if not np.isfinite(inside).all():
        raise ValueError(f"{int((~np.isfinite(inside)).sum())} non-finite values inside footprint")
    if float(inside.min()) < 0.0 or float(inside.max()) > 1.0:
        raise ValueError(
            f"prediction outside [0, 1] inside footprint: [{inside.min()}, {inside.max()}]"
        )
    outside_vals = raw[~foot]
    if np.any(np.isfinite(outside_vals) & (outside_vals != 0.0)):
        raise ValueError("non-zero finite prediction values outside footprint")
    on_cat = int((raw[foot & cat] > 0.0).sum())
    if on_cat != 0:
        raise ValueError(f"{on_cat} positive pixels overlap known catalogue faults (must be 0)")

    clean = np.where(foot, raw.astype(np.float32), np.float32(0.0))
    clean[clean == 0.0] = 0.0
    cid = submission.scored_content_id(clean, foot, cat)

    out_root = Path(out_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    zeros_name = validate_text_limit(
        submission.make_filename(family, slug, date_tag, cid, "allfinite"), "submission_name"
    )
    nan_name = validate_text_limit(
        submission.make_filename(family, slug, date_tag, cid, "nan"), "nan_submission_name"
    )
    note = validate_text_limit(
        f"{family} {hypothesis_id} | {note_summary} | id {cid}", "note"
    )

    zeros_tif = submission.write_geotiff(clean, template_path, out_root / zeros_name, outside="zero")
    nan_tif = submission.write_geotiff(clean, template_path, out_root / nan_name, outside="nan")
    zeros_zip = submission.zip_single(zeros_tif)
    nan_zip = submission.zip_single(nan_tif)
    (out_root / f"note-{zeros_name[:-4]}.txt").write_text(note + "\n")
    (out_root / f"note-{nan_name[:-4]}.txt").write_text(note + "\n")

    v_zeros = submission.verify_geotiff(zeros_tif, template_path)
    v_nan = submission.verify_geotiff(nan_tif, template_path)
    if not v_zeros["hard_checks_passed"] or not v_nan["hard_checks_passed"]:
        raise RuntimeError(
            f"submission verification failed: zeros={v_zeros['hard_failures']} nan={v_nan['hard_failures']}"
        )
    if v_zeros["nonzero_inside_px"] != v_nan["nonzero_inside_px"]:
        raise RuntimeError("in-footprint dot count differs between -zeros and -nan builds")

    return {
        "scored_content_id": cid,
        "submission_name": zeros_name,
        "nan_companion_name": nan_name,
        "note": note,
        "note_length": len(note),
        "primary_zeros_tif": str(zeros_tif),
        "primary_zeros_zip": str(zeros_zip),
        "companion_nan_tif": str(nan_tif),
        "companion_nan_zip": str(nan_zip),
        "raster_sha256": v_zeros["sha256"],
        "nan_raster_sha256": v_nan["sha256"],
        "zeros_zip_sha256": submission.sha256_file(zeros_zip),
        "nan_zip_sha256": submission.sha256_file(nan_zip),
        "emitted_dots": int(v_zeros["nonzero_inside_px"]),
        "on_catalogue_positive_px": on_cat,
        "validator_zeros": v_zeros,
        "validator_nan": v_nan,
        "validator_output": {
            "all_hard_checks_passed": True,
            "no_nan_inside_footprint": True,
            "whole_array_finite_zeros_variant": True,
            "values_in_0_1": True,
            "crs_epsg": grid.CRS_EPSG,
            "shape": list(grid.SHAPE),
            "transform": list(grid.TRANSFORM),
            "on_catalogue_positive_px": 0,
            "emitted_dots": int(v_zeros["nonzero_inside_px"]),
            "value_set_inside": v_zeros["value_set_inside"],
        },
    }
