#!/usr/bin/env python3
"""E3: build the H29-1 (D-refill) unique submission + protocol run card.

Preregistration: knowledge/15_preregistration_H29-1.md. Full-fit Arm-D surface
(32-band stack + 15 subsurface transforms), ridge NMS, B2 (>2 px from catalogue),
priority Poisson-disk >= 2.8 px, 38,000 dots, binary {0,1}. Primary = all-finite
(nodata=None, every cell in [0,1]) — the fix for the portal error
"Predicted values must be in range [0, 1]". Uniqueness measured vs every raster in
registry/parallel_submission_registry.json (fetched to data_cache/parallel_registry)
plus this repo's shipped candidates. ok_to_submit = holdout gate PASS AND
uniqueness PASS AND validator hard-PASS. No live score is claimed.
Files land in docs/downloads/ only if ok_to_submit, else docs/downloads/research/.
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
    T = np.load(paths.DATA / "lane" / "subsurface_transforms.npy")
    hold = json.loads((paths.EVIDENCE / "h29_1_holdout.json").read_text())

    cache = paths.DATA / "lane" / "full_prob_armD.npy"
    if cache.exists():
        prob = np.load(cache)
    else:
        prob = oof_detector.fit_predict_full_probabilities(foot, labels, extra=T)
        np.save(cache, prob)

    d_cat = distance_transform_edt(~labels)
    ridge = oof_detector.ridge_nms(prob, foot)
    cand = ridge & foot & ~labels & (d_cat > B_EXCL)
    dots = sub.priority_poisson_disk(prob, cand, MIN_DIST, BUDGET)
    assert not (dots & labels).any(), "dot on catalogue"
    assert (d_cat[dots] > B_EXCL).all(), "dot inside B2 exclusion"
    pred = dots.astype(np.float32)
    cid = submission.scored_content_id(pred, foot, labels)
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    stem = f"gems27-h29-1-drefill-b2-38k-{date}-{cid}"

    # ---- uniqueness (dots) vs pinned peer registry + shipped repo candidates ----
    overlaps = {}
    for rp in sorted((paths.DATA / "parallel_registry").glob("*.tif")):
        with rasterio.open(rp) as s:
            a = s.read(1)
        overlaps[rp.name] = euclid_overlap(dots, np.isfinite(a) & (a > 0))
    for rp in sorted((paths.DOCS / "downloads").glob("gems27-*-nan.tif")):
        if stem in rp.name:
            continue
        with rasterio.open(rp) as s:
            a = s.read(1)
        overlaps[rp.name] = euclid_overlap(dots, np.isfinite(a) & (a > 0))
    max_overlap = max(overlaps.values()) if overlaps else 0.0
    surf = hold.get("surface_spearman_vs_registry", {})
    max_surf = max((v["D"] for v in surf.values()), default=0.0)
    unique_ok = max_overlap <= 0.70 and max_surf <= 0.90
    gate_ok = bool(hold.get("gate_efficacy_pass")) and not hold.get("canary_leak_flags")

    # ---- write to a staging name location, then decide final dir by gates ----
    # (validator must run before the verdict; write to research/ first if gate fails)
    provisional_dir = paths.DOCS / "downloads" if (gate_ok and unique_ok) else \
        paths.DOCS / "downloads" / "research"
    provisional_dir.mkdir(parents=True, exist_ok=True)
    zeros_tif = provisional_dir / f"{stem}-allfinite.tif"
    nan_tif = provisional_dir / f"{stem}-nan.tif"
    submission.write_geotiff(pred, paths.TEMPLATE, zeros_tif, outside="zero")
    submission.write_geotiff(pred, paths.TEMPLATE, nan_tif, outside="nan")
    zip_path = submission.zip_single(zeros_tif)
    v_zeros = submission.verify_geotiff(zeros_tif, paths.TEMPLATE)
    v_nan = submission.verify_geotiff(nan_tif, paths.TEMPLATE)
    (provisional_dir / f"checks-{stem}-allfinite.json").write_text(
        json.dumps(v_zeros, indent=2) + "\n")
    (provisional_dir / f"checks-{stem}-nan.json").write_text(
        json.dumps(v_nan, indent=2) + "\n")
    format_ok = bool(v_zeros["hard_checks_passed"])
    ok_to_submit = bool(gate_ok and unique_ok and format_ok)
    # If format unexpectedly failed, demote is handled by the badge/run card; bytes stay
    # where written and verify_downloads will flag them. Never badge invalid bytes OK.
    verdict = "promote" if ok_to_submit else "negative"

    pooled = hold["pooled_holdout_dti"]
    paired = hold["paired_D_minus_B"]
    note = (f"27GEMSDOE H29-1 D-refill B2 38k; HOLDOUT-DTI {pooled['D']:.4f} vs B "
            f"{pooled['B']:.4f}; UNSCORED | id {cid}")
    assert len(note) <= 140, len(note)
    card = {
        "run_card": "H29-1 D-refill (parallel-run protocol §5)",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis": "Faults missing from the surface-rupture-scoped USGS/INGENIOUS "
                      "catalogue include buried/older structures expressed in subsurface "
                      "physics; adding 15 label-free subsurface transforms to the full "
                      "32-band detector (Arm D) improves dot placement at the live-family "
                      "B2/38k optimum vs the frozen H19-5 detector behind 0.2778.",
        "mechanism": "Full-fit HGB on 32 bands + 15 transforms "
                     "(gems27.subsurface_features); ridge NMS; priority Poisson-disk "
                     ">=2.8px; B2 (200 m) catalogue exclusion; 38,000-dot budget.",
        "named_non_fault_mimic": "Lithologic contacts and survey seams in potential "
                                 "fields; clay-cap/basin conductivity highs; remanent "
                                 "magnetisation; alluvial-fan edges and shorelines in lidar.",
        "holdout": {"label": "HOLDOUT-DTI", "evaluator": hold["evaluator"],
                    "pooled_dti_D_lane": pooled["D"], "pooled_dti_B_control": pooled["B"],
                    "paired_D_minus_B": paired,
                    "n_withheld_positives_total": hold["n_withheld_positives_total"],
                    "seeds": hold["seeds"], "canary_max_auc": hold["canary_max_auc"],
                    "gate_efficacy_pass": gate_ok},
        "uniqueness_vs_registry": {"max_dot_overlap_within_3px_euclidean": max_overlap,
                                   "per_raster": overlaps,
                                   "max_surface_spearman_armD": max_surf,
                                   "thresholds": {"dot_overlap": 0.70, "spearman": 0.90},
                                   "pass": bool(unique_ok)},
        "raster": {"primary_allfinite": zeros_tif.name, "sha256": v_zeros["sha256"],
                   "bytes": v_zeros["bytes"], "dots": int(dots.sum()),
                   "content_id": cid, "zip": zip_path.name, "nan_twin": nan_tif.name,
                   "directory": str(provisional_dir.relative_to(paths.REPO))},
        "validator": {"zeros_hard_pass": format_ok, "zeros_checks": v_zeros["checks"],
                      "nan_hard_pass": bool(v_nan["hard_checks_passed"])},
        "submission_name": "GEMSDOE27-H29-1-DREFILL-B2-38K",
        "note_max_140_chars": note,
        "note_chars": len(note),
        "ok_to_submit": ok_to_submit,
        "verdict": verdict,
        "live_score": None,
        "live_score_label": "UNSCORED — no ORGANIZER-CONFIRMED score exists for this file",
    }
    (paths.EVIDENCE / "h29_1_run_card.json").write_text(json.dumps(card, indent=2) + "\n")
    manifest = {"stem": stem, **card}
    (provisional_dir / "h29_1_candidate_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n")
    (provisional_dir / f"note-{stem}-allfinite.txt").write_text(note + "\n")
    print(f"dots={int(dots.sum())} cid={cid}")
    print(f"max_overlap={max_overlap:.3f} max_surf={max_surf:.3f} gate={gate_ok} "
          f"unique={unique_ok} format={format_ok} -> verdict={verdict} ok={ok_to_submit}")
    print(f"wrote {zeros_tif} sha256={v_zeros['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
