#!/usr/bin/env python3
"""Experiment E3 (Lane L-S11-2026-10-26 / H31-2): build the unique DEMAG GeoTIFF.

Route is fail-closed: the file lands in ``docs/downloads/`` only if the frozen E2 gate passed,
the 3-px/Spearman uniqueness screen passes (12 pinned peers + both scored GEMSDOE27 files +
the promoted H31-1 file), and the all-finite [0,1] validator passes; otherwise it is a NEGATIVE
research artifact in ``docs/downloads/research/`` labelled DO NOT SUBMIT. The surface is the
quadrant-OOF DEMAG stacker surface from ``scripts/run_h31_2_holdout.py`` (disclosed in
``knowledge/26``: single quadrant partition, unlike H31-1's dual-partition stitch). Emission is
the identical frozen ``emit_h31_celf`` (B2, min-sep 2.8 px, 37,654 dots).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree
from scipy.stats import spearmanr

from gems27 import geothermal_conduit_nis as h31
from gems27 import grid, holdout, metric, paths, readiness, submission

BUDGET_TOTAL: int = 37_654
B_EXCL: float = 2.0
DATE_TAG: str = "20261026"
CACHE_DIR = paths.DATA / "h31_2"
DL_DIR = paths.DOCS / "downloads"
H31_1_FILE = DL_DIR / "gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def dot_overlap_and_spearman(cand_pts, cand_inside, cand_surf_inside, ref_tif, foot, labels):
    with rasterio.open(ref_tif) as ds:
        arr = np.nan_to_num(ds.read(1), nan=0.0).astype(np.float32)
    ref_inside = arr[foot]
    ref_dots = (arr > 0.5) & foot & (~labels)
    ref_pts = np.argwhere(ref_dots).astype(np.float64)
    if ref_pts.shape[0] == 0:
        ov_c2r = ov_r2c = 0.0
    else:
        d_c2r, _ = cKDTree(ref_pts).query(cand_pts, k=1)
        ov_c2r = float((d_c2r <= 3.0 + 1e-9).mean())
        d_r2c, _ = cKDTree(cand_pts).query(ref_pts, k=1)
        ov_r2c = float((d_r2c <= 3.0 + 1e-9).mean())
    rng = np.random.default_rng(20261026)
    take = rng.choice(cand_inside.size, size=min(400_000, cand_inside.size), replace=False)
    rho_d, _ = spearmanr(cand_inside[take], ref_inside[take])
    rho_s, _ = spearmanr(cand_surf_inside[take], ref_inside[take])
    return {
        "ref_dots": int(ref_pts.shape[0]),
        "candidate_dot_fraction_within_3px": round(ov_c2r, 5),
        "reference_dot_fraction_within_3px": round(ov_r2c, 5),
        "postplacement_dot_spearman": round(float(0.0 if np.isnan(rho_d) else rho_d), 5),
        "preplacement_surface_spearman": round(float(0.0 if np.isnan(rho_s) else rho_s), 5),
    }


def main() -> int:
    t0 = time.time()
    e1 = json.loads((paths.EVIDENCE / "h31_2_e1_canary.json").read_text())
    e1b = json.loads((paths.EVIDENCE / "h31_2_e1b_surface.json").read_text())
    e2 = json.loads((paths.EVIDENCE / "h31_2_e2_holdout_410_419.json").read_text())

    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS) & foot
    existing = grid.load_labels(paths.DATA / "existing_faults.tif") & foot
    assert np.array_equal(labels, existing), "labels.tif != existing_faults.tif"
    with rasterio.open(paths.LIDAR) as ls:
        lid_valid = foot & (ls.read(12) > 0)

    prob_dem = np.load(CACHE_DIR / "prob_demag_quad.npy")
    prob_dem = np.clip(prob_dem, 0.0, 1.0).astype(np.float32)
    prob_dem[~foot] = 0.0

    d_cat = distance_transform_edt(~labels)
    dom = foot & (~labels)
    print(f"placing {BUDGET_TOTAL} dots via emit_h31_celf on DEMAG surface...", flush=True)
    t_celf = time.time()
    dots = h31.emit_h31_celf(
        prob_dem, foot, labels, budget=BUDGET_TOTAL,
        b_excl=B_EXCL, gamma=h31.CELF_GAMMA, min_sep_px=h31.CELF_MIN_SEP_PX,
    )
    print(f"  placed {int(dots.sum())} dots in {time.time() - t_celf:.1f}s", flush=True)
    assert int(dots.sum()) == BUDGET_TOTAL
    assert not (dots & ~foot).any(), "Emitted outside footprint"
    assert not (dots & labels).any(), "Emitted on catalogue fault"
    assert float(d_cat[dots].min()) > B_EXCL, "Violated B2 200 m collar"

    pts = np.argwhere(dots).astype(np.float64)
    tree = cKDTree(pts)
    nn_d, _ = tree.query(pts, k=2)
    min_self = float(nn_d[:, 1].min())
    assert min_self >= h31.CELF_MIN_SEP_PX - 1e-6, f"Violated min_sep_px: {min_self}"
    nbr_counts = np.array([len(v) - 1 for v in tree.query_ball_point(pts, r=3.0)])
    c_blind = float(metric.kernel_from_distance(distance_transform_edt(~dots)[dom]).mean())
    quad_grid = holdout.make_quadrant_folds(foot)
    dc_dots = d_cat[dots]
    geom = {
        "n_dots": BUDGET_TOTAL,
        "nn_min_px": round(min_self, 4),
        "nn_p10_px": round(float(np.percentile(nn_d[:, 1], 10)), 4),
        "nn_median_px": round(float(np.median(nn_d[:, 1])), 4),
        "nbr_le_3px_mean": round(float(nbr_counts.mean()), 4),
        "frac_ge_3nbr_in_3px": round(float((nbr_counts >= 3).mean()), 5),
        "c_blind_coverage": round(c_blind, 6),
        "lidar_missing_dot_share": round(float((~lid_valid[dots]).mean()), 4),
        "d_cat_min_px": round(float(dc_dots.min()), 4),
        "d_cat_median_px": round(float(np.median(dc_dots)), 2),
        "d_cat_le_5_share": round(float((dc_dots <= 5.0 + 1e-9).mean()), 4),
        "d_cat_gt_15_share": round(float((dc_dots > 15.0).mean()), 4),
        "quadrant_shares": {
            fnm: round(float((quad_grid[dots] == qi).mean()), 4)
            for qi, fnm in enumerate(holdout.FOLD_NAMES)
        },
    }
    print("GEOMETRY:", json.dumps(geom), flush=True)

    pred = dots.astype(np.float32)
    cid = submission.scored_content_id(pred, foot, labels)
    slug = "h31-2-demag-stack-celf28"
    fn_af = submission.make_filename("gems27", slug, DATE_TAG, cid, "allfinite")
    fn_nan = submission.make_filename("gems27", slug, DATE_TAG, cid, "nan")
    DL_DIR.mkdir(parents=True, exist_ok=True)
    tmp_af, tmp_nan = DL_DIR / fn_af, DL_DIR / fn_nan
    submission.write_geotiff(pred, paths.TEMPLATE, tmp_af, outside="zero")
    submission.write_geotiff(pred, paths.TEMPLATE, tmp_nan, outside="nan")
    tmp_zip = submission.zip_single(tmp_af)
    chk_af = submission.verify_geotiff(tmp_af, paths.TEMPLATE)
    chk_nan = submission.verify_geotiff(tmp_nan, paths.TEMPLATE)
    assert chk_af["hard_checks_passed"], f"allfinite hard fail: {chk_af['hard_failures']}"
    assert chk_nan["hard_checks_passed"], f"nan hard fail: {chk_nan['hard_failures']}"

    peer_uniq_path = paths.EVIDENCE / "h31_2_uniqueness_vs_peers.json"
    subprocess.run(
        [sys.executable, str(paths.REPO / "scripts" / "check_parallel_uniqueness.py"),
         str(tmp_af), "--out", str(peer_uniq_path)],
        check=False,
    )
    peer_uniq = json.loads(peer_uniq_path.read_text())

    cand_inside, surf_inside = pred[foot], prob_dem[foot]
    peer_surface: dict[str, float] = {}
    for p_tif in sorted((paths.DATA / "parallel_registry").glob("*.tif")):
        m_p = dot_overlap_and_spearman(pts, cand_inside, surf_inside, p_tif, foot, labels)
        peer_surface[p_tif.name] = float(m_p["preplacement_surface_spearman"])

    scored_files = {
        "gems27_slot1_5512495c6bd1_02449": (
            DL_DIR / "gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-allfinite.tif"),
        "gems27_h29s_511898747886_02190": (
            DL_DIR / "gems27-h29-hydrothermal-piedmont-celf-20261025-511898747886-allfinite.tif"),
        "gems27_h31_1_cf8e1bbef244_promoted_unscored": H31_1_FILE,
    }
    scored_uniq = {
        k: dot_overlap_and_spearman(pts, cand_inside, surf_inside, p, foot, labels)
        for k, p in scored_files.items()
    }
    max_peer_ov = max(float(e["candidate_dot_fraction_within_3px"]) for e in peer_uniq["entries"])
    max_scored_ov = max(float(v["candidate_dot_fraction_within_3px"]) for v in scored_uniq.values())
    max_ov = max(max_peer_ov, max_scored_ov)
    max_rho = max(
        max(abs(float(e["spearman_rank_correlation"])) for e in peer_uniq["entries"]),
        max(abs(float(v["postplacement_dot_spearman"])) for v in scored_uniq.values()),
        max(abs(v) for v in peer_surface.values()),
        max(abs(float(v["preplacement_surface_spearman"])) for v in scored_uniq.values()),
    )
    uniqueness_pass = (max_ov <= 0.70) and (max_rho <= 0.90)
    holdout_pass = bool(e1["gate_e1_canary_pass"]) and bool(
        e1b["gate_surface_pass"]) and bool(e2["gate_e2_pass"])
    validator_pass = bool(chk_af["hard_checks_passed"]) and bool(chk_nan["hard_checks_passed"])
    all_pass = holdout_pass and uniqueness_pass and validator_pass

    target_dir = DL_DIR if all_pass else (DL_DIR / "research")
    target_dir.mkdir(parents=True, exist_ok=True)
    if target_dir != DL_DIR:
        for p_move in (tmp_af, tmp_nan, tmp_zip):
            p_move.replace(target_dir / p_move.name)
    path_af, path_nan = target_dir / fn_af, target_dir / fn_nan
    path_zip = target_dir / tmp_zip.name

    chk_af_path = target_dir / f"checks-{fn_af[:-4]}.json"
    chk_nan_path = target_dir / f"checks-{fn_nan[:-4]}.json"
    submission.dump_json(chk_af, chk_af_path)
    submission.dump_json(chk_nan, chk_nan_path)

    status_tag = "validated-promote" if all_pass else "hold-slot"
    submission_name = f"27GEMSDOE-H31-2-DEMAG-{DATE_TAG}-{cid}"
    short_note = (
        f"27GEMSDOE H31-2 | H31-1 surf + Poisson demag-resid stack CELF2.8 B2 {BUDGET_TOTAL}px"
        f" | id {cid} | unscored {status_tag}"
    )
    assert 0 < len(short_note) <= 140, f"Note length invalid: {len(short_note)}"
    note_path = target_dir / f"note-{fn_af[:-4]}.txt"
    note_path.write_text(short_note + "\n")

    comps = e2["paired_comparisons_buffered"]
    run_card = {
        "schema": "parallel-run-card-v2",
        "generated_utc": "2026-10-26",
        "lane": "L-S11-2026-10-26",
        "hypothesis_id": "H31-2",
        "hypothesis": (
            "Poisson-relation gravity-to-pseudogravity demagnetization residual stacker on the "
            "frozen H31-1 OOF surfaces (knowledge/26)"
        ),
        "mechanism": (
            "Local Gaussian-window (sigma 8/20 px) regression of iso_grav_anom_vg on RTP; the "
            "positive standardised residual (gravity step unexplained by magnetics), gravity-edge "
            "deficit and shallow magnetic quietness target hydrothermal conduits where magnetite "
            "was destroyed, which co-located magnetic+gravity edge coherence suppresses. The 8 "
            "label-free features enter a quadrant-OOF stacker over [p_s2,p_s1,p_sub]; identical "
            "axial-crest CELF B2 37,654-dot emission as H31-1."
        ),
        "named_non_fault_mimic": (
            "Non-magnetic Paleozoic carbonate on granite, reversely magnetised Tertiary ash-flow "
            "tuffs, and deep basement under thick basin fill (depth-decayed magnetics with no "
            "alteration)."
        ),
        "verdict": "promote" if all_pass else "negative",
        "ok_to_submit": bool(all_pass),
        "submission_name": submission_name,
        "note_max_140_chars": short_note,
        "note_chars": len(short_note),
        "holdout": {
            "label": "HOLDOUT-DTI",
            "provenance_note": "Catalogue-internal whole-component hide-and-recover; NOT a live organizer score.",
            "evaluator": e2["evaluator_version"],
            "seeds": e2["seeds"],
            "n_cells": e2["n_cells"],
            "n_withheld_positives_total": int(e2["n_withheld_positive_occurrences"]),
            "canary_max_auc": float(e1["max_direction_invariant_auc"]),
            "pooled_dti_DEMAG_candidate": e2["pooled_buffered_holdout_dti"]["DEMAG"],
            "pooled_dti_DEMAG_ci95": e2["pooled_buffered_ci95"]["DEMAG"],
            "pooled_dti_H31S_control": e2["pooled_buffered_holdout_dti"]["H31S"],
            "pooled_dti_STK0_control": e2["pooled_buffered_holdout_dti"]["STK0"],
            "pooled_dti_U0_null": e2["pooled_buffered_holdout_dti"]["U0"],
            "pooled_unbuffered_diagnostic": e2["pooled_unbuffered_diagnostic_holdout_dti"],
            "per_fold_buffered": e2["per_fold_buffered_holdout_dti"],
            "paired_candidate_minus_B": comps["DEMAG_minus_H31S"],
            "paired_candidate_minus_STK0": comps["DEMAG_minus_STK0"],
            "frozen_gate_clauses": e2["frozen_gate_clauses"],
            "gate_efficacy_pass": bool(holdout_pass),
        },
        "uniqueness_vs_registry": {
            "pass": bool(uniqueness_pass),
            "operative_scope": (
                "12 pinned focus-site peer rasters + scored GEMSDOE27 (Slot 1, H29-S) "
                "+ promoted unscored H31-1 (cf8e1bbef244)"
            ),
            "max_dot_overlap_within_3px_euclidean": round(max_ov, 5),
            "max_dot_overlap_vs_12_peers": round(max_peer_ov, 5),
            "max_dot_overlap_vs_scored_gems27": round(max_scored_ov, 5),
            "max_surface_spearman": round(max_rho, 5),
            "peer_entries": peer_uniq["entries"],
            "peer_preplacement_surface_spearman": peer_surface,
            "scored_gems27_entries": scored_uniq,
        },
        "raster": {
            "directory": str(target_dir.relative_to(paths.REPO)),
            "primary_allfinite": path_af.name,
            "companion_nan": path_nan.name,
            "zip": path_zip.name,
            "content_id": cid,
            "sha256": chk_af["sha256"],
            "sha256_nan": chk_nan["sha256"],
            "sha256_zip": sha256_file(path_zip),
            "allfinite_bytes": chk_af["bytes"],
            "nan_bytes": chk_nan["bytes"],
            "zip_bytes": path_zip.stat().st_size,
            "dots": BUDGET_TOTAL,
            "b_exclusion_px": B_EXCL,
            "celf_min_sep_px": h31.CELF_MIN_SEP_PX,
            "celf_gamma": h31.CELF_GAMMA,
            "geometry_diagnostics": geom,
        },
        "validator": {
            "zeros_hard_pass": bool(chk_af["hard_checks_passed"]),
            "nan_hard_pass": bool(chk_nan["hard_checks_passed"]),
            "technical_validator_pass": bool(validator_pass),
            "inside_footprint_nan_count": 0,
            "whole_array_nan_count_allfinite": 0,
            "inside_footprint_range": [0.0, 1.0],
            "value_set_inside": chk_af["value_set_inside"],
            "crs": f"EPSG:{grid.CRS_EPSG}",
            "shape": list(grid.SHAPE),
            "transform": list(grid.TRANSFORM),
            "zeros_checks": chk_af["checks"],
            "checks_allfinite_json": str(chk_af_path.relative_to(paths.REPO)),
            "checks_nan_json": str(chk_nan_path.relative_to(paths.REPO)),
        },
        "runtime_s": round(time.time() - t0, 1),
    }
    rc_path = paths.EVIDENCE / "h31_2_run_card.json"
    rc_path.write_text(json.dumps(run_card, indent=2) + "\n")

    cand_man = {
        "lane": "L-S11-2026-10-26",
        "hypothesis_id": "H31-2",
        "submission_name": submission_name,
        "content_id": cid,
        "directory": str(target_dir.relative_to(paths.REPO)),
        "allfinite": path_af.name,
        "nan": path_nan.name,
        "zip_allfinite": path_zip.name,
        "checks_allfinite": chk_af_path.name,
        "checks_nan": chk_nan_path.name,
        "note_file": note_path.name,
        "note": short_note,
        "sha256_allfinite": chk_af["sha256"],
        "sha256_nan": chk_nan["sha256"],
        "sha256_zip_allfinite": sha256_file(path_zip),
        "emitted_px": BUDGET_TOTAL,
        "b_exclusion_px": B_EXCL,
        "min_sep_px": h31.CELF_MIN_SEP_PX,
        "ok_to_submit": bool(all_pass),
        "verdict": run_card["verdict"],
        "technical_validator_pass": bool(validator_pass),
        "uniqueness_pass": bool(uniqueness_pass),
        "holdout_efficacy_pass": bool(holdout_pass),
        "run_card": str(rc_path.relative_to(paths.REPO)),
    }
    (DL_DIR / "h31_2_candidate_manifest.json").write_text(json.dumps(cand_man, indent=2) + "\n")

    decision = readiness.publication_decision(run_card, paths.REPO)
    print("READINESS:", json.dumps(decision), flush=True)
    assert decision["ok_to_publish_as_submission"] == all_pass, (
        f"Readiness mismatch: {decision} vs {all_pass}")
    print(f"E3 COMPLETE | verdict={run_card['verdict']} | ok={all_pass} | tif={path_af}",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
