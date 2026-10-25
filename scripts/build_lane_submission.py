#!/usr/bin/env python3
"""E3: build the Lane L-2026-10-25 unique submission from the full-fit subsurface detector.

Uses the shared submission writer (gems27.submission) unchanged. Primary download is the
all-finite ZEROS variant (nodata=None, every cell in [0,1]) — the fix for the portal error
"Predicted values must be in range [0, 1]" (knowledge/12 §6). NaN twin is secondary.
Uniqueness is MEASURED against every registry raster (Euclidean <=3 px dot overlap; surface
Spearman from E2) and the run card's ok_to_submit flag requires: validator hard-PASS on the
zeros file AND max dot-overlap < 0.70 AND surface Spearman < 0.90 AND holdout gate not failed.
No live score is claimed anywhere.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import grid, oof_detector, paths, submission  # noqa: E402
from gems27 import subsurface_features as sub

BUDGET = 38_000
MIN_DIST = 2.8
B_EXCL = 2.0


def euclid_overlap(dots: np.ndarray, other: np.ndarray, r: float = 3.0) -> float:
    d = distance_transform_edt(~other)
    return float((d[dots] <= r).mean()) if dots.any() else 0.0


def main() -> int:
    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    meta = json.loads(paths.PREPARED_META.read_text())
    names = meta["names"]
    sub_idx = np.array([names.index(b) for b in sub.SUBSURFACE_BANDS])
    T = np.load(paths.DATA / "lane" / "subsurface_transforms.npy")
    hold = json.loads((paths.EVIDENCE / "lane_holdout_2026-10-25.json").read_text())

    cache = paths.DATA / "lane" / "full_prob_armA.npy"
    if cache.exists():
        prob = np.load(cache)
    else:
        prob = oof_detector.fit_predict_full_probabilities(
            foot, labels, columns=sub_idx, extra=T)
        np.save(cache, prob)

    d_cat = distance_transform_edt(~labels)
    ridge = oof_detector.ridge_nms(prob, foot)
    cand = ridge & foot & ~labels & (d_cat > B_EXCL)
    dots = sub.priority_poisson_disk(prob, cand, MIN_DIST, BUDGET)
    pred = dots.astype(np.float32)
    cid = submission.scored_content_id(pred, foot, labels)
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    stem = f"gems27-lane-subsurface-buried-fault-{date}-{cid}"
    out_dir = paths.DOCS / "downloads"
    zeros_tif = out_dir / f"{stem}-allfinite.tif"  # PRIMARY (all-finite; repo naming convention)
    nan_tif = out_dir / f"{stem}-nan.tif"          # twin (competition-sample convention)
    submission.write_geotiff(pred, paths.TEMPLATE, zeros_tif, outside="zero")
    submission.write_geotiff(pred, paths.TEMPLATE, nan_tif, outside="nan")
    zip_path = submission.zip_single(zeros_tif)
    v_zeros = submission.verify_geotiff(zeros_tif, paths.TEMPLATE)
    v_nan = submission.verify_geotiff(nan_tif, paths.TEMPLATE)
    (out_dir / f"checks-{stem}-allfinite.json").write_text(json.dumps(v_zeros, indent=2) + "\n")
    (out_dir / f"checks-{stem}-nan.json").write_text(json.dumps(v_nan, indent=2) + "\n")

    # ---- uniqueness vs registry (fetched top files + this repo's shipped candidates) ----
    overlaps = {}
    for rp in sorted((paths.DATA / "registry").glob("*.tif")):
        with rasterio.open(rp) as s:
            a = s.read(1)
        overlaps[rp.name] = euclid_overlap(dots, np.isfinite(a) & (a > 0))
    for rp in sorted(out_dir.glob("gems27-*-nan.tif")):
        if stem in rp.name:
            continue
        with rasterio.open(rp) as s:
            a = s.read(1)
        overlaps[rp.name] = euclid_overlap(dots, np.isfinite(a) & (a > 0))
    max_overlap = max(overlaps.values()) if overlaps else 0.0
    surf = hold["surface_spearman_vs_registry"]
    max_surf = max(v["A"] for v in surf.values()) if surf else 0.0

    paired = hold["paired"]
    pooled = hold["pooled_holdout_dti"]
    gate_clean = paired["A_minus_B"]["mean_delta"] > 0
    gate_exploratory = (paired["A_minus_B"]["mean_delta"] > -0.01
                        and paired["A_minus_R"]["mean_delta"] > 0.05)
    unique_ok = max_overlap < 0.70 and max_surf < 0.90
    format_ok = bool(v_zeros["hard_checks_passed"])
    verdict = ("promote" if (gate_clean and unique_ok and format_ok)
               else "promote-exploratory" if (gate_exploratory and unique_ok and format_ok)
               else "negative")
    note = (f"27GEMSDOE Lane-A subsurface-only buried-fault detector, B2, 38k dots; "
            f"HOLDOUT-DTI {pooled['A']:.4f} vs full {pooled['B']:.4f}; UNSCORED | id {cid}")
    assert len(note) <= 140, len(note)
    card = {
        "run_card": "Lane L-2026-10-25 (single-lane parallel run)",
        "hypothesis": "Faults missing from the surface-rupture-scoped USGS/INGENIOUS catalogue are "
                      "preferentially buried/older structures visible in subsurface physics "
                      "(potential-field edges, basement steps, strain, conductivity, seismicity "
                      "fabric) but not in lidar scarps; a subsurface-only detector at B2/38k "
                      "therefore places credit where the H19-5 family cannot.",
        "mechanism": "OOF/full HGB on 16 subsurface bands + 15 label-free transforms "
                     "(gems27.subsurface_features); ridge NMS; priority Poisson-disk >=2.8px; "
                     "B2 (200 m) catalogue exclusion; 38,000-dot budget (live-family optimum).",
        "named_non_fault_mimic": "Lithologic contacts and survey seams in potential fields; "
                                 "clay-cap/basin conductivity highs; remanent magnetisation.",
        "holdout": {"label": "HOLDOUT-DTI", "evaluator": hold["evaluator"],
                    "pooled_dti_lane_A": pooled["A"], "pooled_dti_full_B": pooled["B"],
                    "pooled_dti_hybrid_D_control": pooled["D"],
                    "paired_A_minus_B": paired["A_minus_B"],
                    "paired_A_minus_Random": paired["A_minus_R"],
                    "n_withheld_positives_total": hold["n_withheld_positives_total"],
                    "seeds": hold["seeds"], "canary_max_auc": max(hold["canary_auc"].values())},
        "uniqueness_vs_registry": {"max_dot_overlap_within_3px_euclidean": max_overlap,
                                   "per_raster": overlaps,
                                   "max_surface_spearman": max_surf,
                                   "thresholds": {"dot_overlap": 0.70, "spearman": 0.90},
                                   "pass": bool(unique_ok)},
        "raster": {"primary_allfinite": zeros_tif.name, "sha256": v_zeros["sha256"],
                   "bytes": v_zeros["bytes"], "dots": int(dots.sum()),
                   "content_id": cid, "zip": zip_path.name, "nan_twin": nan_tif.name,
                   "nan_twin_sha256": v_nan["sha256"]},
        "validator": {"zeros_hard_pass": format_ok, "zeros_checks": v_zeros["checks"],
                      "nan_hard_pass": bool(v_nan["hard_checks_passed"])},
        "submission_name": "GEMSDOE27-LANE-A-SUBSURFACE-B2-38K",
        "note_max_140_chars": note, "note_chars": len(note),
        "ok_to_submit": bool(format_ok and unique_ok and verdict != "negative"),
        "verdict": verdict,
        "live_score": None,
        "live_score_label": "UNSCORED — no ORGANIZER-CONFIRMED score exists for this file",
    }
    (paths.EVIDENCE / "lane_run_card_2026-10-25.json").write_text(json.dumps(card, indent=2) + "\n")
    (out_dir / f"note-{stem}-allfinite.txt").write_text(note + "\n")
    lane_manifest = {"generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                     "stem": stem, "run_card": "evidence/lane_run_card_2026-10-25.json", **card}
    (out_dir / "lane_candidate_manifest.json").write_text(json.dumps(lane_manifest, indent=2) + "\n")
    print(json.dumps({"dots": int(dots.sum()), "cid": cid, "max_overlap": max_overlap,
                      "max_surface_spearman": max_surf, "format_ok": format_ok,
                      "verdict": verdict, "ok_to_submit": card["ok_to_submit"],
                      "sha256": v_zeros["sha256"], "note": note}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
