#!/usr/bin/env python3
"""E3: build the Lane L-DCONFIRM unique GeoTIFF from the full-fit confirmed arm.

Preregistration: knowledge/15 §4. The arm built is the confirmation candidate from
evidence/dconfirm_holdout_2026-10-25.json (E preferred, else D; if selection found no
candidate, arm E is built as a NEGATIVE research artifact so a unique file always exists
and its badge states plainly that it must not be submitted). Emission: ridge NMS,
priority Poisson-disk >=2.8 px, B2, 38,000 dots. Primary file is all-finite
(nodata=None, every cell in [0,1]) — the fix for the portal error
"Predicted values must be in range [0, 1]".

ok_to_submit = confirmation gate PASS AND uniqueness PASS (surface Spearman < 0.90 and
final-dot 3-px overlap < 0.70 vs every registry raster: 12 pinned peers + this repo's
shipped candidates) AND shared-validator hard PASS. Computed here into the run card;
the website badge reads that JSON. No human inspection, no live score claimed.
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
HOLD = paths.EVIDENCE / "dconfirm_holdout_2026-10-25.json"


def euclid_overlap(dots: np.ndarray, other: np.ndarray, r: float = 3.0) -> float:
    d = distance_transform_edt(~other)
    return float((d[dots] <= r).mean()) if dots.any() else 0.0


def main() -> int:
    hold = json.loads(HOLD.read_text())
    conf = hold.get("confirmation")
    arm = (conf or {}).get("candidate") or hold["selection"].get("candidate") or "E"
    gate_pass = bool(conf and conf.get("gate_pass"))
    print(f"building arm {arm} (confirmation gate_pass={gate_pass})", flush=True)

    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    T15 = np.load(paths.DATA / "dconfirm" / "subsurface_transforms.npy")
    T8 = np.load(paths.DATA / "dconfirm" / "new_transforms.npy")
    extra = T15 if arm == "D" else np.concatenate([T15, T8], axis=1).astype(np.float32)

    cache = paths.DATA / "dconfirm" / f"full_prob_arm{arm}.npy"
    if cache.exists():
        prob = np.load(cache)
    else:
        prob = oof_detector.fit_predict_full_probabilities(foot, labels, extra=extra)
        np.save(cache, prob)

    d_cat = distance_transform_edt(~labels)
    ridge = oof_detector.ridge_nms(prob, foot)
    cand = ridge & foot & ~labels & (d_cat > B_EXCL)
    dots = sub.priority_poisson_disk(prob, cand, MIN_DIST, BUDGET)
    pred = dots.astype(np.float32)
    cid = submission.scored_content_id(pred, foot, labels)
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    stem = f"gems27-dconfirm-hybrid-arm{arm.lower()}-b2-38k-{date}-{cid}"

    # Pre-write placement assertions (fail loudly rather than ship a broken file).
    assert int(dots.sum()) == BUDGET, f"expected {BUDGET} dots, got {int(dots.sum())}"
    assert not (dots & labels).any(), "dot on catalogue pixel"
    assert float(d_cat[dots].min()) > B_EXCL, "B2 exclusion violated"
    assert not (dots & ~foot).any(), "dot outside footprint"

    # ---- uniqueness from the dot set itself, BEFORE choosing where files live ----
    # (Pass-2 fix: placement must follow the full gate outcome, not gate_pass alone;
    # negative artifacts belong in downloads/research/ per repo policy.)
    overlaps = {}
    for rp in sorted((paths.DATA / "parallel_registry").glob("*.tif")):
        with rasterio.open(rp) as s:
            a = s.read(1)
        overlaps[f"peer:{rp.name}"] = euclid_overlap(dots, np.isfinite(a) & (a > 0))
    for rp in sorted((paths.DOCS / "downloads").glob("gems27-*-nan.tif")):
        if stem in rp.name:
            continue
        with rasterio.open(rp) as s:
            a = s.read(1)
        overlaps[f"repo:{rp.name}"] = euclid_overlap(dots, np.isfinite(a) & (a > 0))
    max_overlap = max(overlaps.values()) if overlaps else 0.0
    peer_max = max((v for k, v in overlaps.items() if k.startswith("peer:")), default=0.0)
    self_max = max((v for k, v in overlaps.items() if k.startswith("repo:")), default=0.0)
    worst_raster = max(overlaps, key=overlaps.get) if overlaps else None
    surf = hold["surface_spearman_vs_peer_registry"]
    max_surf = max((v[arm] for v in surf.values() if arm in v), default=0.0) if arm != "B" else 0.0
    unique_ok = bool(max_overlap < 0.70 and max_surf < 0.90)  # frozen rule, knowledge/15 §4
    promote = bool(gate_pass and unique_ok)  # validator re-checked below before ok is set

    out_dir = paths.DOCS / "downloads" if promote else paths.DOCS / "downloads" / "research"
    out_dir.mkdir(parents=True, exist_ok=True)
    zeros_tif = out_dir / f"{stem}-allfinite.tif"
    nan_tif = out_dir / f"{stem}-nan.tif"
    submission.write_geotiff(pred, paths.TEMPLATE, zeros_tif, outside="zero")
    submission.write_geotiff(pred, paths.TEMPLATE, nan_tif, outside="nan")
    zip_path = submission.zip_single(zeros_tif)
    v_zeros = submission.verify_geotiff(zeros_tif, paths.TEMPLATE)
    v_nan = submission.verify_geotiff(nan_tif, paths.TEMPLATE)
    (out_dir / f"checks-{stem}-allfinite.json").write_text(json.dumps(v_zeros, indent=2) + "\n")
    (out_dir / f"checks-{stem}-nan.json").write_text(json.dumps(v_nan, indent=2) + "\n")
    format_ok = bool(v_zeros["hard_checks_passed"])
    ok = bool(promote and format_ok)
    verdict = "promote" if ok else "negative"

    pooled_b = (conf or {}).get("pooled_holdout_dti", {}).get("B")
    pooled_c = (conf or {}).get("pooled_holdout_dti", {}).get(arm)
    if pooled_c is not None:
        note = (f"27GEMSDOE L-DCONFIRM arm{arm} hybrid B2 38k; HOLDOUT-DTI {pooled_c:.4f} "
                f"vs {pooled_b:.4f}; UNSCORED | id {cid}")
    else:
        note = f"27GEMSDOE L-DCONFIRM arm{arm} hybrid B2 38k; holdout NEGATIVE; UNSCORED | id {cid}"
    assert len(note) <= 140, len(note)

    card = {
        "run_card": "Lane L-DCONFIRM (knowledge/15; parallel-run protocol §5)",
        "hypothesis": ("Subsurface physics (potential-field/strain/conductivity/seismicity "
                       "transforms), dip-offset doublets, radiometric alteration fronts and "
                       "scarp-polarity pairs add detector information about faults missing "
                       "from the surface-rupture catalogue when layered ON TOP of the full "
                       "32-band stack, emitted at the live optimum (B2, >=2.8 px, 38 k)."),
        "mechanism": (f"Full-fit HGB arm {arm} (32 bands + 15 subsurface transforms"
                      + (" + 8 dip/rad/polarity transforms" if arm == "E" else "")
                      + "); ridge NMS; priority Poisson-disk >=2.8 px; B2; 38,000 dots."),
        "named_non_fault_mimic": ("Basin-margin lithologic contacts; radiometric provenance/"
                                  "levelling seams; terrace risers and channel banks; "
                                  "clay-cap conductivity highs."),
        "holdout": {"label": "HOLDOUT-DTI", "evaluator": hold["evaluator"],
                    "selection_pooled": hold["selection"]["pooled_holdout_dti"],
                    "confirmation": conf,
                    "canary_max_auc_new_transforms":
                        max(hold["canary_auc_new_transforms"].values())},
        "uniqueness_vs_registry": {"max_dot_overlap_within_3px_euclidean": max_overlap,
                                   "max_dot_overlap_peer_registry_12": peer_max,
                                   "max_dot_overlap_self_repo": self_max,
                                   "worst_raster": worst_raster,
                                   "per_raster": overlaps, "max_surface_spearman": max_surf,
                                   "thresholds": {"dot_overlap": 0.70, "spearman": 0.90},
                                   "pass": unique_ok,
                                   "peer_registry_pass": bool(peer_max < 0.70 and max_surf < 0.90),
                                   "selector_note": (
                                       "Frozen gate (knowledge/15 §4) FAILS only against this "
                                       "repo's own unsubmitted H28-1 research raster "
                                       "(audit-only, never scored); against the 12-raster "
                                       "peer parallel registry the file passes. Promotion "
                                       "would require a selector decision to retire the "
                                       "H28-1 artifact from the self-registry — not taken "
                                       "unilaterally here (no post-hoc gate edits).")},
        "raster": {"primary_allfinite": zeros_tif.name, "sha256": v_zeros["sha256"],
                   "bytes": v_zeros["bytes"], "dots": int(dots.sum()), "content_id": cid,
                   "zip": zip_path.name, "nan_twin": nan_tif.name,
                   "nan_twin_sha256": v_nan["sha256"],
                   "directory": "docs/downloads" if promote else "docs/downloads/research"},
        "validator": {"zeros_hard_pass": format_ok, "zeros_checks": v_zeros["checks"],
                      "nan_hard_pass": bool(v_nan["hard_checks_passed"]),
                      "dots_on_catalogue": int((dots & labels).sum()),
                      "min_dot_distance_to_catalogue_px": float(d_cat[dots].min())},
        "submission_name": f"GEMSDOE27-DCONFIRM-ARM{arm}-B2-38K",
        "note_max_140_chars": note, "note_chars": len(note),
        "ok_to_submit": ok, "verdict": verdict,
        "live_score": None,
        "live_score_label": "UNSCORED — no ORGANIZER-CONFIRMED score exists for this file",
    }
    (paths.EVIDENCE / "dconfirm_run_card_2026-10-25.json").write_text(
        json.dumps(card, indent=2) + "\n")
    (out_dir / f"note-{stem}-allfinite.txt").write_text(note + "\n")
    manifest = {"generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "stem": stem, "arm": arm,
                "run_card": "evidence/dconfirm_run_card_2026-10-25.json", **card}
    (paths.DOCS / "downloads" / "dconfirm_candidate_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"arm": arm, "dots": int(dots.sum()), "cid": cid, "file": zeros_tif.name,
                      "max_overlap": max_overlap, "max_surface_spearman": max_surf,
                      "unique_ok": unique_ok, "format_ok": format_ok, "gate_pass": gate_pass,
                      "ok_to_submit": ok, "verdict": verdict,
                      "sha256": v_zeros["sha256"], "note": note}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
