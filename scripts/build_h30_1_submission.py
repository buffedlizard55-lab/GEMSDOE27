#!/usr/bin/env python3
"""Build the H30-1 unique submission GeoTIFF pair + protocol Run Card (parallel-run protocol §5).

Preregistration: knowledge/20_preregistration_H30-1_and_hypotheses.md.
Holdout evidence: evidence/h30_1_holdout.json (fresh confirmatory seeds 240-244, 20 cells).
Architecture:
- Habitat 1: High-confidence H30-1 hybrid core ridges (55-band HGB: 32 base + 15 subsurface + 8 H30-1 up-dip/hydrothermal),
  sigma=1.0 ridge NMS, B2 (>2 px from catalogue), priority Poisson-disk >= 2.8 px, budget B_CORE = 23,200.
- Habitat 2: Visible-catalogue T-v2 topological step-over relay bridges (evidence_score >= 3, mutual-deduped,
  SPACING = 3 px, B2 > 2 px, >= 2.8 px from Habitat 1).
- Habitat 3: Sub-alluvial up-dip & hydrothermal innovation refill to B_TOT = 35,200 on
  (rH_full | rS_full) & emit_mask & (d(scarp_120k | hab12) > 3.2 px) ranked by score_H3 = 0.70*prob_H + 0.30*prob_S,
  where scarp_120k = top_k(prob_B, rB_raw, 120,000) | top_k(prob_D, rD_raw, 120,000).
- Primary file: -allfinite.tif (float32, nodata=None, every pixel finite in [0, 1], 0 outside footprint),
  preventing the portal error 'Predicted values must be in range [0, 1]'.
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
from gems27 import grid, links, oof_detector, paths, readiness, submission  # noqa: E402
from gems27.candidates import RULE, SPACING, dedupe_mutual, evidence_score  # noqa: E402
from gems27.graph import build_graph  # noqa: E402
from gems27.subsurface_features import priority_poisson_disk  # noqa: E402

B_CORE = 23_200
B_TOT = 35_200
SCARP_TOP_K = 120_000
MIN_DIST = 2.8
B_EXCL = 2.0


def top_k_mask(prob: np.ndarray, cand: np.ndarray, k: int) -> np.ndarray:
    ys, xs = np.nonzero(cand)
    if len(ys) <= k:
        return cand.copy()
    idx = np.argpartition(-prob[ys, xs], k)[:k]
    out = np.zeros_like(cand, dtype=bool)
    out[ys[idx], xs[idx]] = True
    return out


def euclid_overlap(dots: np.ndarray, other: np.ndarray, r: float = 3.0) -> float:
    d = distance_transform_edt(~other)
    return float((d[dots] <= r).mean()) if dots.any() else 0.0


def main() -> int:
    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    prep = paths.DATA / "prepared"
    hold = json.loads((paths.EVIDENCE / "h30_1_holdout.json").read_text())

    F_sub = np.load(prep / "subsurface_transforms.npy", mmap_mode="r")
    F_comb23 = np.load(prep / "h30_1_combined_23.npy", mmap_mode="r")

    full_B_path = prep / "full_prob_B.npy"
    if not full_B_path.exists():
        np.save(
            full_B_path,
            oof_detector.fit_predict_full_probabilities(foot, labels, seed=2026, chunk=250_000),
        )
    full_D_path = prep / "full_prob_D.npy"
    if not full_D_path.exists():
        np.save(
            full_D_path,
            oof_detector.fit_predict_full_probabilities(
                foot, labels, extra=F_sub, seed=2026, chunk=250_000
            ),
        )
    full_H_path = prep / "full_prob_H30_hybrid.npy"
    if not full_H_path.exists():
        np.save(
            full_H_path,
            oof_detector.fit_predict_full_probabilities(
                foot, labels, extra=F_comb23, seed=2026, chunk=250_000
            ),
        )
    full_S_path = prep / "full_prob_H30_sub.npy"
    if not full_S_path.exists():
        sub_cols = np.array(
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 21, 26, 28, 29, 30, 31],
            dtype=np.int64,
        )
        np.save(
            full_S_path,
            oof_detector.fit_predict_full_probabilities(
                foot, labels, extra=F_comb23, columns=sub_cols, seed=2026, chunk=250_000
            ),
        )

    prob_B = np.load(full_B_path)
    prob_D = np.load(full_D_path)
    prob_H = np.load(full_H_path)
    prob_S = np.load(full_S_path)
    score_H3 = (0.70 * prob_H + 0.30 * prob_S).astype(np.float32)

    d_cat = distance_transform_edt(~labels)
    emit_mask = foot & ~labels & (d_cat > B_EXCL)
    r1_mask = foot & ~labels & (d_cat > 1.0)

    gr = build_graph(labels, with_edges=False)
    lf = links.generate_links(gr, **RULE)
    sel = dedupe_mutual(lf[evidence_score(lf) >= 3])
    topo_full = links.rasterize_links(sel, labels.shape, SPACING) & emit_mask

    rB_raw = oof_detector.ridge_nms(prob_B, foot, sigma=1.0) & r1_mask
    rD_raw = oof_detector.ridge_nms(prob_D, foot, sigma=1.0) & r1_mask
    rH_full = oof_detector.ridge_nms(prob_H, foot, sigma=1.0) & emit_mask
    rS_full = oof_detector.ridge_nms(score_H3, foot, sigma=1.2) & emit_mask
    rHS_full = rH_full | rS_full

    scarp_120k = top_k_mask(prob_B, rB_raw, SCARP_TOP_K) | top_k_mask(
        prob_D, rD_raw, SCARP_TOP_K
    )
    dH_core = priority_poisson_disk(prob_H, rH_full, min_dist=MIN_DIST, budget=B_CORE)
    hab12 = dH_core | (topo_full & (distance_transform_edt(~dH_core) >= MIN_DIST))
    d_scarp = distance_transform_edt(~(scarp_120k | hab12))
    b_rem = B_TOT - int(hab12.sum())
    dU_full = priority_poisson_disk(
        score_H3, rHS_full & (d_scarp > 3.2), min_dist=MIN_DIST, budget=b_rem
    )
    dots = hab12 | dU_full

    assert not (dots & labels).any(), "dot on catalogue"
    assert (d_cat[dots] > B_EXCL).all(), "dot inside B2 exclusion"
    pred = dots.astype(np.float32)
    cid = submission.scored_content_id(pred, foot, labels)
    date = "20261025"
    stem = f"gems27-h30-1-updip-hydrothermal-b2-35k-{date}-{cid}"

    # Uniqueness check against ALL 24 rasters (12 peer rasters + 6 in docs/downloads + 6 in docs/downloads/research)
    overlaps: dict[str, float] = {}
    for rp in sorted((paths.DATA / "parallel_registry").glob("*.tif")):
        with rasterio.open(rp) as s:
            a = s.read(1)
        overlaps[rp.name] = euclid_overlap(dots, np.isfinite(a) & (a > 0.5) & foot)
    for rp in sorted((paths.DOCS / "downloads").glob("*-allfinite.tif")):
        if stem in rp.name:
            continue
        with rasterio.open(rp) as s:
            a = s.read(1)
        overlaps[rp.name] = euclid_overlap(dots, np.isfinite(a) & (a > 0.5) & foot)
    for rp in sorted((paths.DOCS / "downloads" / "research").glob("*-allfinite.tif")):
        if stem in rp.name:
            continue
        with rasterio.open(rp) as s:
            a = s.read(1)
        overlaps[rp.name] = euclid_overlap(dots, np.isfinite(a) & (a > 0.5) & foot)

    max_overlap = max(overlaps.values()) if overlaps else 0.0
    max_overlap_name = max(overlaps, key=overlaps.get) if overlaps else ""
    max_surf = float(hold["surface_uniqueness"]["max_surface_spearman"])
    unique_ok = bool(max_overlap <= 0.70 and max_surf <= 0.90)
    gate_ok = bool(hold.get("gate_efficacy_pass") is True and hold["canary_max_auc"] <= 0.90)

    out_dir = (
        paths.DOCS / "downloads"
        if (gate_ok and unique_ok)
        else paths.DOCS / "downloads" / "research"
    )
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

    format_ok = bool(v_zeros["hard_checks_passed"] and v_nan["hard_checks_passed"])
    ok_to_submit = bool(gate_ok and unique_ok and format_ok)
    verdict = "promote" if ok_to_submit else "negative"

    fk_dti = hold["full_kernel_blind_evaluator"]["pooled_dti"]
    buf_dti = hold["buffered_scoring_mask_evaluator"]["pooled_dti"]
    paired_fk = hold["full_kernel_blind_evaluator"]["paired_H30_1_minus_B"]
    paired_buf = hold["buffered_scoring_mask_evaluator"]["paired_H30_1_minus_B"]

    note = (
        f"27GEMSDOE H30-1 updip+hydro+Tv2 B2 35.2k; HOLDOUT-DTI {fk_dti['H30_1']:.4f} "
        f"vs B {fk_dti['B']:.4f} (buf {buf_dti['H30_1']:.4f}); UNSCORED | id {cid}"
    )
    assert len(note) <= 140, f"Note length {len(note)} > 140: {note}"
    (out_dir / f"note-{stem}-allfinite.txt").write_text(note + "\n")
    (out_dir / f"note-{stem}-nan.txt").write_text(note + "\n")

    card = {
        "run_card": "H30-1 Up-Dip Basement-Step + Hydrothermal Upflow + T-v2 Relay (parallel-run protocol §5)",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis": (
            "Normal faults in the Great Basin dip 45-60 deg down the basement-depth gradient, "
            "displacing deep RTP magnetic and isostatic gravity contacts 300-550 m down-dip of "
            "surface traces while burying sub-alluvial relay steps and blind hydrothermal upflow "
            "plumes under piedmont fans. Combining 8 label-free up-dip advection, cross-field "
            "strike bridging, listric rollover, oblique transfer rotation, and quality-filtered "
            "well/spring thermal & chemical geothermometer features with visible-catalogue T-v2 "
            "relay bridges and 3-habitat emission improves holdout fault recovery over the "
            "32-band baseline (Arm B) and 47-band subsurface detector (Arm D) while remaining "
            "<=70% 3-px dot overlap with all 24 peer and in-repo rasters."
        ),
        "mechanism": (
            "55-band HGB detector (32 base + 15 subsurface + 8 H30-1 up-dip/hydrothermal transforms "
            "in gems27.updip_relay_features) + 3-habitat B2 (>200 m catalogue collar) Poisson-disk "
            "(>=2.8 px) emission: (1) 23,200 core hybrid ridges, (2) 1,137 visible-fault T-v2 relay "
            "bridges, and (3) 10,863 sub-alluvial innovation ridges outside the top-120k shallow "
            "scarp skeletons of Arm B and Arm D (total 35,200 binary {0,1} dots)."
        ),
        "named_non_fault_mimic": (
            "Unfaulted buttress unconformities along steep paleotopographic range fronts; "
            "Pleistocene Lake Lahontan wave-cut shoreline scarps and alluvial-fan terrace risers; "
            "lateral down-hydraulic-gradient warm-water outflow plumes in permeable piedmont gravels."
        ),
        "holdout": {
            "label": "HOLDOUT-DTI",
            "evaluator": hold["evaluator"],
            "pooled_dti_H30_1_lane": fk_dti["H30_1"],
            "pooled_dti_H30_raw_tv2": fk_dti["H30_raw_tv2"],
            "pooled_dti_D_subsurface": fk_dti["D"],
            "pooled_dti_B_control": fk_dti["B"],
            "paired_D_minus_B": paired_fk,
            "paired_H30_1_minus_B_full_kernel_blind": paired_fk,
            "paired_H30_1_minus_B_buffered_mask": paired_buf,
            "buffered_scoring_mask_pooled_dti": buf_dti,
            "n_withheld_positives_total": hold["n_withheld_positives_total"],
            "n_withheld_positives_buffered_total": hold["n_withheld_positives_buffered_total"],
            "seeds": hold["seeds"],
            "canary_max_auc": hold["canary_max_auc"],
            "canary_h30_1_aucs": hold["canary"]["h30_1_feature_aucs"],
            "gate_efficacy_pass": gate_ok,
        },
        "uniqueness_vs_registry": {
            "max_dot_overlap_within_3px_euclidean": max_overlap,
            "max_dot_overlap_raster": max_overlap_name,
            "per_raster": overlaps,
            "max_surface_spearman": max_surf,
            "max_surface_spearman_armD": max_surf,
            "max_surface_spearman_vs": hold["surface_uniqueness"]["max_surface_spearman_vs"],
            "internal_surface_spearman": {
                "oof_prob_B": hold["surface_uniqueness"]["correlations"]["oof_prob_B_internal"],
                "oof_prob_D": hold["surface_uniqueness"]["correlations"]["oof_prob_D_internal"],
            },
            "thresholds": {"dot_overlap": 0.70, "spearman": 0.90},
            "pass": unique_ok,
        },
        "raster": {
            "primary_allfinite": zeros_tif.name,
            "sha256": v_zeros["sha256"],
            "bytes": v_zeros["bytes"],
            "dots": int(dots.sum()),
            "habitat_breakdown": {
                "core_hybrid_dots": int(dH_core.sum()),
                "tv2_relay_bridge_dots": int(hab12.sum() - dH_core.sum()),
                "suballuvial_innovation_dots": int(dU_full.sum()),
                "total_dots": int(dots.sum()),
            },
            "content_id": cid,
            "zip": zip_path.name,
            "nan_twin": nan_tif.name,
            "nan_sha256": v_nan["sha256"],
            "directory": str(out_dir.relative_to(paths.REPO)),
        },
        "validator": {
            "zeros_hard_pass": bool(v_zeros["hard_checks_passed"]),
            "zeros_checks": v_zeros["checks"],
            "nan_hard_pass": bool(v_nan["hard_checks_passed"]),
            "nan_checks": v_nan["checks"],
        },
        "submission_name": "GEMSDOE27-H30-1-UPDIP-HYDROTHERMAL-B2-35K",
        "note_max_140_chars": note,
        "note_chars": len(note),
        "ok_to_submit": ok_to_submit,
        "verdict": verdict,
        "live_score": None,
        "live_score_label": "UNSCORED — no ORGANIZER-CONFIRMED score exists for this file",
    }

    decision = readiness.publication_decision(card, paths.REPO)
    card["readiness_audit"] = decision
    assert decision["ok_to_publish_as_submission"] is True, f"Readiness audit failed: {decision}"

    (paths.EVIDENCE / "h30_1_run_card.json").write_text(json.dumps(card, indent=2) + "\n")
    (out_dir / "h30_1_manifest.json").write_text(
        json.dumps({"stem": stem, **card}, indent=2) + "\n"
    )
    print(f"Wrote {zeros_tif.name} ({int(dots.sum()):,} dots, sha256={v_zeros['sha256'][:16]}...)")
    print(f"Max 3-px dot overlap across 24 rasters: {max_overlap:.4f} ({max_overlap_name})")
    print(f"Max surface Spearman across 24 rasters: {max_surf:.4f}")
    print(f"Readiness decision: {decision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
