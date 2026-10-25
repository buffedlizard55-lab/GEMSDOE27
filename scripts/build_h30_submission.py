#!/usr/bin/env python3
"""E3: build the single Lane L-H30 candidate TIFF + protocol run card (knowledge/20).

Exactly one new file is built: the E2a-selected arm (DIP / GAP / SOFT), or —
per the pre-result clarification in knowledge/20 — the highest-pooled
contender as a NEGATIVE research artifact if no contender beat the Arm-D
control. Emission is the frozen live optimum (ridge NMS -> B2 -> priority
Poisson-disk >=2.8 px, 38,000 dots or 38,000 effective soft mass). Primary
file is all-finite (nodata=None, every cell in [0,1]) — the fix for the
portal error "Predicted values must be in range [0, 1]". Bytes are written
to docs/downloads/research/ first and only moved to docs/downloads/ when
every gate passes, so a top-level download is never an unapproved file.
ok_to_submit = E2b efficacy PASS AND canary clean AND protocol-registry
uniqueness PASS (12 pinned peers; extended self-overlaps vs unscored
research artifacts are reported, not gated — knowledge/20 section 5)
AND validator hard-PASS. No live score is claimed.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import dip_gap_features as dg  # noqa: E402
from gems27 import grid, oof_detector, paths, submission  # noqa: E402
from gems27 import subsurface_features as sub  # noqa: E402

LANE_DIR = paths.DATA / "lane"
BUDGET = 38_000
MIN_DIST = 2.8
B_EXCL = 2.0

ARM_SLUG = {"DIP": "dipadv", "GAP": "gapflank", "SOFT": "softrank"}
ARM_TEXT = {
    "DIP": {
        "hypothesis": "A dipping fault missing from the surface-rupture-scoped catalogue still "
                      "edges in magnetics/gravity/basement-depth, but hundreds of metres "
                      "down-dip from its surface trace; relocating that edge evidence up-dip "
                      "by a depth-scaled offset lets a per-pixel detector place dots on the "
                      "trace. Full 32-band + 15 subsurface + 5 dip-advection features (H30-1) "
                      "beat the Arm-D control ranking at B2/38k.",
        "mechanism": "Full-fit HGB on 32 bands + 15 subsurface transforms + 5 dip-advected "
                     "edge features (gems27.dip_gap_features, dip 50/70 deg); ridge NMS; "
                     "priority Poisson-disk >=2.8px; B2 (200 m) catalogue exclusion; "
                     "38,000-dot budget.",
    },
    "GAP": {
        "hypothesis": "Where alluvial cover thickens along strike, one continuous buried "
                      "fault's potential-field edge fades and resumes; locations flanked "
                      "+/-600 m / +/-1.2 km along strike by collinear RTP/gravity edges "
                      "continue a structure the surface catalogue cannot list. Full 32-band "
                      "+ 15 subsurface + 4 gap-flanking features (H30-2) beat the Arm-D "
                      "control ranking at B2/38k.",
        "mechanism": "Full-fit HGB on 32 bands + 15 subsurface transforms + 4 gap-flank "
                     "features (gems27.dip_gap_features); ridge NMS; priority Poisson-disk "
                     ">=2.8px; B2 (200 m) catalogue exclusion; 38,000-dot budget.",
    },
    "SOFT": {
        "hypothesis": "Graduated (soft) values on a 2x support, rescaled to the binary "
                      "38,000 effective mass under the exact soft DTI, hedge second-tier "
                      "candidates for uncatalogued faults at fractional false-positive cost "
                      "instead of the binary all-or-nothing cut (H30-3, on the Arm-D surface).",
        "mechanism": "Full-fit HGB on 32 bands + 15 subsurface transforms (Arm-D surface); "
                     "ridge NMS; priority Poisson-disk >=2.8px support of 76,000 px; values "
                     "1-k/N by descending-probability rank, rescaled to effective mass 38,000; "
                     "B2 (200 m) catalogue exclusion.",
    },
}
MIMIC = ("Dipping lithologic contacts and unfaulted basin-margin basement steps; "
         "survey seams and remanent magnetisation in potential fields; chance "
         "collinearity of unrelated edge segments; clay-cap conductivity highs.")


def euclid_overlap(dots: np.ndarray, other: np.ndarray, r: float = 3.0) -> float:
    if not dots.any():
        return 0.0
    d = distance_transform_edt(~other)
    return float((d[dots] <= r).mean())


def read_dots(path: Path, threshold: float = 0.5) -> np.ndarray:
    with rasterio.open(path) as s:
        a = s.read(1)
    return np.isfinite(a) & (a > threshold)


def main() -> int:
    hold = json.loads((paths.EVIDENCE / "h30_holdout.json").read_text())
    sel = hold["selection"]
    contenders = ["DIP", "GAP", "SOFT"]
    selected = sel["selected_candidate"]
    arm = selected or max(contenders, key=lambda a: sel["pooled_holdout_dti"][a])
    conf = hold.get("confirmation")
    gate_ok = bool(hold.get("gate_efficacy_pass")) and not hold.get("canary_leak_flags")
    canary_max = hold["canary_max_auc_direction_invariant"]

    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    t15 = np.load(LANE_DIR / "subsurface_transforms.npy")
    t9 = np.load(LANE_DIR / "dip_gap_features.npy")

    surface_arm = "D" if arm == "SOFT" else arm
    cache = LANE_DIR / f"full_prob_h30_{surface_arm}.npy"
    if cache.exists():
        prob = np.load(cache)
    else:
        if surface_arm == "D":
            extra = t15
        elif surface_arm == "DIP":
            extra = np.concatenate([t15, t9[:, : len(dg.DIP_NAMES)]], axis=1).astype(np.float32)
        else:
            extra = np.concatenate([t15, t9[:, len(dg.DIP_NAMES):]], axis=1).astype(np.float32)
        prob = oof_detector.fit_predict_full_probabilities(foot, labels, extra=extra)
        np.save(cache, prob)

    d_cat = distance_transform_edt(~labels)
    ridge = oof_detector.ridge_nms(prob, foot)
    cand = ridge & foot & ~labels & (d_cat > B_EXCL)
    if arm == "SOFT":
        support = sub.priority_poisson_disk(prob, cand, MIN_DIST, 2 * BUDGET)
        pred = dg.soft_rank_taper(prob, support, float(BUDGET))
        dots_hi = pred > 0.5  # shared uniqueness tool definition of a "dot"
        dots_any = pred > 0
    else:
        dots_any = sub.priority_poisson_disk(prob, cand, MIN_DIST, BUDGET)
        pred = dots_any.astype(np.float32)
        dots_hi = dots_any.copy()
    assert not (dots_any & labels).any(), "positive pixel on catalogue"
    assert (d_cat[dots_any] > B_EXCL).all(), "positive pixel inside B2 exclusion"
    if dots_any.sum() > 1:
        ys, xs = np.nonzero(dots_any)
        dist, _ = cKDTree(np.c_[ys, xs].astype(float)).query(np.c_[ys, xs].astype(float), k=2)
        min_spacing = float(dist[:, 1].min())
    else:
        min_spacing = None
    emission_checks = {
        "positives_gt_0": int(dots_any.sum()),
        "dots_gt_0_5": int(dots_hi.sum()),
        "effective_mass_sum": float(pred[foot].sum()),
        "min_distance_to_catalogue_px_gt0": float(d_cat[dots_any].min()),
        "median_distance_to_catalogue_px_gt0": float(np.median(d_cat[dots_any])),
        "min_nearest_neighbour_spacing_px_gt0": min_spacing,
        "on_catalogue_gt0": int((dots_any & labels).sum()),
    }
    print("emission checks:", emission_checks, flush=True)

    cid = submission.scored_content_id(pred, foot, labels)
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    stem = f"gems27-h30-{ARM_SLUG[arm]}-b2-38k-{date}-{cid}"

    # ---- uniqueness vs the 12 pinned parallel-registry peers ----
    sample = np.random.default_rng(13).choice(
        np.flatnonzero(foot.ravel()), size=500_000, replace=False
    )
    pred_flat_sample = pred.ravel()[sample]
    overlaps, overlaps_support, final_spearman = {}, {}, {}
    for rp in sorted((paths.DATA / "parallel_registry").glob("*.tif")):
        with rasterio.open(rp) as s:
            a = s.read(1)
        other = np.isfinite(a) & (a > 0.5)
        overlaps[rp.name] = euclid_overlap(dots_hi, other)
        if arm == "SOFT":
            overlaps_support[rp.name] = euclid_overlap(dots_any, other)
        vals = np.where(np.isfinite(a), a, 0.0).astype(np.float32)
        final_spearman[rp.name] = float(
            spearmanr(pred_flat_sample, vals.ravel()[sample]).statistic
        )
        del a, vals, other
    max_overlap = max(overlaps.values()) if overlaps else 0.0
    max_final_spearman = max(final_spearman.values()) if final_spearman else 0.0
    surf = hold.get("surface_spearman_vs_registry", {})
    max_preplacement = max(
        (max(v[surface_arm].values()) for v in surf.values()), default=0.0
    )
    max_spearman = max(max_final_spearman, max_preplacement)
    unique_ok = max_overlap <= 0.70 and max_spearman <= 0.90

    # ---- extended self-overlaps vs own unscored research artifacts (reported, not gated) ----
    extended: dict[str, float] = {}
    seen_stems: set[str] = set()
    for rp in sorted((paths.DOCS / "downloads").glob("*.tif")) + sorted(
        (paths.DOCS / "downloads" / "research").glob("*.tif")
    ):
        if stem in rp.name:
            continue
        base = rp.name.replace("-allfinite.tif", "").replace("-nan.tif", "")
        if base in seen_stems:
            continue
        seen_stems.add(base)
        extended[rp.name] = euclid_overlap(dots_hi, read_dots(rp))
    max_extended = max(extended.values()) if extended else 0.0
    print(f"max peer overlap={max_overlap:.3f} max spearman={max_spearman:.3f} "
          f"max extended-self overlap (reported)={max_extended:.3f}", flush=True)

    # ---- write to research/ staging, verify, then move only if fully approved ----
    stage_dir = paths.DOCS / "downloads" / "research"
    stage_dir.mkdir(parents=True, exist_ok=True)
    zeros_tif = stage_dir / f"{stem}-allfinite.tif"
    nan_tif = stage_dir / f"{stem}-nan.tif"
    submission.write_geotiff(pred, paths.TEMPLATE, zeros_tif, outside="zero")
    submission.write_geotiff(pred, paths.TEMPLATE, nan_tif, outside="nan")
    zip_path = submission.zip_single(zeros_tif)
    v_zeros = submission.verify_geotiff(zeros_tif, paths.TEMPLATE)
    v_nan = submission.verify_geotiff(nan_tif, paths.TEMPLATE)
    checks_zeros = stage_dir / f"checks-{stem}-allfinite.json"
    checks_nan = stage_dir / f"checks-{stem}-nan.json"
    checks_zeros.write_text(json.dumps(v_zeros, indent=2) + "\n")
    checks_nan.write_text(json.dumps(v_nan, indent=2) + "\n")
    format_ok = bool(v_zeros["hard_checks_passed"]) and bool(v_nan["hard_checks_passed"])
    ok_to_submit = bool(gate_ok and unique_ok and format_ok)
    verdict = "promote" if ok_to_submit else "negative"

    final_dir = paths.DOCS / "downloads" if ok_to_submit else stage_dir
    if ok_to_submit:
        for p in (zeros_tif, nan_tif, zip_path, checks_zeros, checks_nan):
            p.replace(final_dir / p.name)
        zeros_tif, nan_tif = final_dir / zeros_tif.name, final_dir / nan_tif.name
        zip_path = final_dir / zip_path.name

    if conf:
        holdout_block = {
            "label": "HOLDOUT-DTI",
            "evaluator": hold["evaluator"],
            "pooled_dti_candidate": conf["pooled_candidate"],
            "pooled_dti_control_D": conf["pooled_control_D"],
            "paired_A_minus_B": conf["paired_candidate_minus_D"],
            "n_withheld_positives_total": conf["n_withheld_positives_total"],
            "seeds_confirmation": conf["seeds"],
            "seeds_selection": sel["seeds"],
            "canary_max_auc": canary_max,
            "canary_max_auc_raw": hold["canary_max_auc"],
            "gate_efficacy_pass": bool(gate_ok),
            "selection_pooled_holdout_dti": sel["pooled_holdout_dti"],
        }
        note_pooled_c, note_pooled_d = conf["pooled_candidate"], conf["pooled_control_D"]
    else:
        holdout_block = {
            "label": "HOLDOUT-DTI",
            "evaluator": hold["evaluator"],
            "pooled_dti_candidate": sel["pooled_holdout_dti"][arm],
            "pooled_dti_control_D": sel["pooled_holdout_dti"]["D"],
            "paired_A_minus_B": {"mean_delta": None, "ci95": [],
                                  "note": "no confirmation ran: selection gate failed"},
            "n_withheld_positives_total": sel["n_withheld_positives_total"],
            "seeds_selection": sel["seeds"],
            "canary_max_auc": canary_max,
            "canary_max_auc_raw": hold["canary_max_auc"],
            "gate_efficacy_pass": False,
            "selection_pooled_holdout_dti": sel["pooled_holdout_dti"],
        }
        note_pooled_c = sel["pooled_holdout_dti"][arm]
        note_pooled_d = sel["pooled_holdout_dti"]["D"]
    if ok_to_submit:
        note = (f"27GEMSDOE H30-{arm} B2 38k; HOLDOUT-DTI {note_pooled_c:.4f} vs D "
                f"{note_pooled_d:.4f}; UNSCORED | id {cid}")
    else:
        note = (f"27GEMSDOE H30-{arm} RESEARCH NEGATIVE NOT APPROVED; "
                f"HOLDOUT-DTI {note_pooled_c:.4f} vs D {note_pooled_d:.4f} | id {cid}")
    assert len(note) <= 140, len(note)

    card = {
        "run_card": "Lane L-H30 (parallel-run protocol section 5)",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "preregistration": "knowledge/20_lane_h30_preregistration_2026-10-25.md",
        "arm": arm,
        "selected_by_E2a": selected,
        "hypothesis": ARM_TEXT[arm]["hypothesis"],
        "mechanism": ARM_TEXT[arm]["mechanism"],
        "named_non_fault_mimic": MIMIC,
        "holdout": holdout_block,
        "uniqueness_vs_registry": {
            "registry": "registry/parallel_submission_registry.json (12 pinned peers)",
            "max_dot_overlap_within_3px_euclidean": max_overlap,
            "max_dot_overlap_support_gt0_within_3px":
                max(overlaps_support.values()) if overlaps_support else max_overlap,
            "per_raster": overlaps,
            "per_raster_support_gt0": overlaps_support,
            "max_surface_spearman": max_spearman,
            "max_surface_spearman_final_raster_sampled": max_final_spearman,
            "max_surface_spearman_preplacement_oof": max_preplacement,
            "final_raster_spearman_per_peer_sampled": final_spearman,
            "thresholds": {"dot_overlap": 0.70, "spearman": 0.90},
            "pass": bool(unique_ok),
        },
        "extended_self_overlap_reported_not_gated": {
            "policy": "knowledge/20 section 5 (pre-result): overlaps vs this repo's own "
                      "UNSUBMITTED research artifacts are measured and reported, not gated; "
                      "selector review logged at IR-2026-10-25-06.",
            "max_dot_overlap_within_3px_euclidean": max_extended,
            "per_raster": extended,
        },
        "raster": {
            "primary_allfinite": zeros_tif.name, "sha256": v_zeros["sha256"],
            "bytes": v_zeros["bytes"], "dots": int(dots_hi.sum()),
            "positives_gt_0": int(dots_any.sum()),
            "effective_mass": float(pred[foot].sum()),
            "content_id": cid, "zip": zip_path.name, "nan_twin": nan_tif.name,
            "directory": str(final_dir.relative_to(paths.REPO)),
        },
        "emission_checks": emission_checks,
        "validator": {"zeros_hard_pass": bool(v_zeros["hard_checks_passed"]),
                      "zeros_checks": v_zeros["checks"],
                      "nan_hard_pass": bool(v_nan["hard_checks_passed"])},
        "submission_name": f"GEMSDOE27-H30-{arm}-B2-38K",
        "note_max_140_chars": note,
        "note_chars": len(note),
        "ok_to_submit": ok_to_submit,
        "verdict": verdict,
        "live_score": None,
        "live_score_label": "UNSCORED - no ORGANIZER-CONFIRMED score exists for this file",
    }
    (paths.EVIDENCE / "h30_run_card.json").write_text(json.dumps(card, indent=2) + "\n")
    manifest_name = "h30_candidate_manifest.json" if ok_to_submit else \
        "h30_negative_research_manifest.json"
    (final_dir / manifest_name).write_text(
        json.dumps({"stem": stem, **card}, indent=2) + "\n"
    )
    (final_dir / f"note-{stem}-allfinite.txt").write_text(note + "\n")
    print(f"arm={arm} dots(>0.5)={int(dots_hi.sum())} cid={cid}")
    print(f"gate={gate_ok} unique={unique_ok} format={format_ok} "
          f"-> verdict={verdict} ok_to_submit={ok_to_submit}")
    print(f"wrote {zeros_tif} sha256={v_zeros['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
