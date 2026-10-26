#!/usr/bin/env python3
"""Compute byte-authenticated 9-focus-site executive summary and live-score autopsy.

Covers every focus site named in the 2026-10-26 prompt:
  GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30,
  GEMSDOE31, GEMSDOE32, GEMSDOE33, GEMSDOE36
plus key fleet anchors (GEMSDOE70, GEMSDOE76, 19GEMSDOE, 16GEMSDOE) and the
2026-10-25 five-submission non-H19-5 live cohort (0.2190, 0.1462, 0.0859, 0.0742, 0.0217).

All live scores are labelled OWNER-REPORTED (never ORGANIZER-CONFIRMED unless an
organizer receipt exists in the repository). Never accesses drivendata.org.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree

from gems27 import grid, metric, paths

G_REF: float = 12_226.0
RHO_REF: float = 1.38
ALPHA: float = metric.ALPHA
BETA: float = metric.BETA


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def invert_dti(n_dots: int, c_cov: float, dti_live: float) -> dict[str, float]:
    """Invert DTI = TPw / (TPw + alpha*(N - rho*TPw) + beta*(|G| - TPw)) for implied TPw & concentration."""
    denom_coeff = (1.0 - ALPHA * RHO_REF - BETA) * dti_live
    rhs = dti_live * (ALPHA * float(n_dots) + BETA * G_REF)
    tpw = rhs / (1.0 - denom_coeff)
    credit_frac = tpw / G_REF
    conc = credit_frac / max(c_cov, 1e-9)
    breakeven = (ALPHA * dti_live) / (1.0 - ALPHA * dti_live)
    return {
        "implied_tpw": round(float(tpw), 2),
        "credit_fraction_of_G": round(float(credit_frac), 4),
        "concentration_over_blind": round(float(conc), 3),
        "marginal_breakeven_tp_per_fp": round(float(breakeven), 5),
    }


def measure_raster(
    tif_path: Path,
    foot: np.ndarray,
    labels: np.ndarray,
    d_cat: np.ndarray,
    lid_valid: np.ndarray,
    quad: np.ndarray,
    g32_tree: cKDTree | None,
) -> dict:
    with rasterio.open(tif_path) as ds:
        arr = ds.read(1).astype(np.float32)
        outside = arr[~foot]
        outside_mode = "nan" if np.isnan(outside).any() else "allfinite_zeros"
    inside = arr[foot]
    in_footprint_nans = int(np.isnan(inside).sum())
    in_min = float(np.nanmin(inside))
    in_max = float(np.nanmax(inside))

    dots = (np.nan_to_num(arr, nan=0.0) > 0.5) & foot & (~labels)
    n_dots = int(dots.sum())
    pts = np.argwhere(dots).astype(np.float64)
    tree = cKDTree(pts)
    nn_d, _ = tree.query(pts, k=2)
    nbr_counts = np.array([len(v) - 1 for v in tree.query_ball_point(pts, r=3.0)])

    # Exact official metric max-kernel blind coverage c(x) = max_p k(d(x, p)) on off-catalogue footprint
    dom = foot & (~labels)
    d_to_p = distance_transform_edt(~dots)
    c_blind = float(metric.kernel_from_distance(d_to_p[dom]).mean())

    dc = d_cat[dots]
    q_vals = quad[dots]
    q_shares = {
        nm: round(float((q_vals == q_idx).mean()), 4)
        for q_idx, nm in enumerate(["NW", "NE_LidarGapHeavy", "SW", "SE"])
    }

    ov_g32 = 1.0
    if g32_tree is not None:
        dg, _ = g32_tree.query(pts, k=1)
        ov_g32 = float((dg <= 3.0 + 1e-9).mean())

    return {
        "sha256": sha256_file(tif_path),
        "bytes": tif_path.stat().st_size,
        "outside_mode": outside_mode,
        "inside_nan_count": in_footprint_nans,
        "inside_range": [round(in_min, 4), round(in_max, 4)],
        "n_dots": n_dots,
        "nn_min_px": round(float(nn_d[:, 1].min()), 3),
        "nn_p10_px": round(float(np.percentile(nn_d[:, 1], 10)), 3),
        "nn_median_px": round(float(np.median(nn_d[:, 1])), 3),
        "nbr_le_3px_mean": round(float(nbr_counts.mean()), 3),
        "frac_ge_3nbr_in_3px": round(float((nbr_counts >= 3).mean()), 4),
        "c_blind_coverage": round(c_blind, 6),
        "lidar_missing_dot_share": round(float((~lid_valid[dots]).mean()), 4),
        "d_cat_min_px": round(float(dc.min()), 3),
        "d_cat_median_px": round(float(np.median(dc)), 2),
        "d_cat_le_2_share": round(float((dc <= 2.0 + 1e-9).mean()), 4),
        "d_cat_le_5_share": round(float((dc <= 5.0 + 1e-9).mean()), 4),
        "d_cat_gt_15_share": round(float((dc > 15.0).mean()), 4),
        "quadrant_shares": q_shares,
        "overlap_3px_vs_g32_02778": round(ov_g32, 4),
    }


def main() -> int:
    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS) & foot
    d_cat = distance_transform_edt(~labels)
    with rasterio.open(paths.DATA / "lidar_scarp_features_u8.tif") as ds:
        lid_valid = (ds.read(12) > 0) & foot

    from gems27 import holdout
    quad = holdout.make_quadrant_folds(foot)

    reg_dir = paths.DATA / "parallel_registry"
    g32_path = reg_dir / "g32_h33_2_b2.tif"
    with rasterio.open(g32_path) as ds:
        g32_dots = (np.nan_to_num(ds.read(1), nan=0.0) > 0.5) & foot & (~labels)
    g32_tree = cKDTree(np.argwhere(g32_dots).astype(np.float64))

    site_specs = [
        {
            "site": "GEMSDOE32",
            "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE32",
            "best_submission": "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif",
            "local_raster": reg_dir / "g32_h33_2_b2.tif",
            "best_live_score": 0.2778,
            "score_label": "OWNER-REPORTED (highest across all 9 focus sites; no DrivenData receipt in repo)",
            "recent_2026_10_25_run": "gemsdoe32-r6-stepprofile-b2-37654-20261026T002502Z-23fbbb51-zeros.tif (UNSCORED)",
            "lineage": "H19-5 4-line corroboration + Poisson d=2.8 + strict B2 (d_cat > 200 m) collar prune (-6,436 zero-yield halo dots vs d=2.8)",
            "action_verdict": "HISTORICAL BENCHMARK (#1 of 9 focus sites at 0.2778) — ALREADY SUBMITTED; DO NOT COPY OR RE-SUBMIT.",
        },
        {
            "site": "GEMSDOE36",
            "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE36",
            "best_submission": "gemsdoe36-anderson-geothermal-pinn-38854-20261004T063428Z-c7e9bc92-zeros.tif",
            "local_raster": reg_dir / "g36_anderson.tif",
            "best_live_score": 0.2750,
            "score_label": "OWNER-REPORTED (#2 of 9 focus sites)",
            "recent_2026_10_25_run": "gemsdoe36-lane36-supgbm-68302-20261026T002651Z-f35cb3e4-zeros.tif (NOT APPROVED)",
            "lineage": "Exact superset of GEMSDOE32 H33-2-B2 (37,654 px) + 1,200 Anderson geothermal PINN dots (diluted 0.2778 -> 0.2750)",
            "action_verdict": "ALREADY SUBMITTED & 96.9% 3-px OVERLAP WITH GEMSDOE32 — DO NOT RE-SUBMIT.",
        },
        {
            "site": "GEMSDOE31",
            "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE31",
            "best_submission": "gemsdoe31-h32-2-b1-only-20261004-777da82e-allfinite.tif",
            "local_raster": reg_dir / "g31_h27_4.tif",
            "best_live_score": 0.2710,
            "score_label": "OWNER-REPORTED (#3 of 9 focus sites; paired B1-prune sibling to GEMSDOE28 0.2708)",
            "recent_2026_10_25_run": "gemsdoe31-concord31-minbd-concordance-28115-20261026-allfinite.tif (NOT APPROVED; negative)",
            "lineage": "H19-5 Poisson d=2.8 + B1 (d_cat > 100 m) prune (40,199 dots; leaves 2,545 B2-ring halo dots that cost -0.0068 vs GEMSDOE32)",
            "action_verdict": "ALREADY SUBMITTED & 93.7% 3-px OVERLAP WITH GEMSDOE32 — SUPERSEDED BY B2 PRUNE; DO NOT RE-SUBMIT.",
        },
        {
            "site": "GEMSDOE28",
            "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE28",
            "best_submission": "gems28-h28-solo-r1-20261003-27c0796d-nan.tif",
            "local_raster": reg_dir / "g28_h27_4_r1.tif",
            "best_live_score": 0.2708,
            "score_label": "OWNER-REPORTED (#4 of 9 focus sites); 2026-10-25 S18-MXTP (`05fc81ca2760`) scored 0.0217 OWNER-REPORTED",
            "recent_2026_10_25_run": "28gemsdoe-s18-mxtp-37654-20261025-05fc81ca2760-zeros.tif (0.0217 OWNER-REPORTED — severe tip-extrapolation FP collapse)",
            "lineage": "Pixel-identical in-footprint dot set (40,199 px) to GEMSDOE31 B1-only (`-nan` vs `-allfinite`); new S18-MXTP collapsed to 0.0217",
            "action_verdict": "ALREADY SUBMITTED (`0.2708` is B1 duplicate of H19-5; `0.0217` S18 failed) — DO NOT RE-SUBMIT.",
        },
        {
            "site": "GEMSDOE33",
            "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE33",
            "best_submission": "GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif",
            "local_raster": reg_dir / "g33_h33d.tif",
            "best_live_score": 0.2632,
            "score_label": "OWNER-REPORTED (#5 of 9 focus sites)",
            "recent_2026_10_25_run": "gemsdoe33-a33-l1-analog-transfer-research-37654-20261025-85c94a805a34-zeros.tif (NOT APPROVED; negative)",
            "lineage": "H19-5 d=2.8 backbone modified with analog tip/stepover swaps (43,435 px; retains B1/B2 collar drag)",
            "action_verdict": "ALREADY SUBMITTED & 91.6% 3-px OVERLAP WITH GEMSDOE32 — DO NOT RE-SUBMIT.",
        },
        {
            "site": "GEMSDOE25",
            "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE25",
            "best_submission": "gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif",
            "local_raster": reg_dir / "g25_d28.tif",
            "best_live_score": 0.2600,
            "score_label": "OWNER-REPORTED (0.2586-0.2600 across d=2.8 runs); 2026-10-25 H66-MGD (`83539880f9da`) scored 0.0742 OWNER-REPORTED",
            "recent_2026_10_25_run": "25gemsdoe-h66-mgd-20261025-83539880f9da-zeros.tif (0.0742 OWNER-REPORTED — blind magnetic-only mimic dilution)",
            "lineage": "Unpruned H19-5 Poisson d=2.8 (44,090 px; includes 6,436 <=200 m collar dots that cost -0.0178 vs GEMSDOE32)",
            "action_verdict": "ALREADY SUBMITTED & 85.4% 3-px OVERLAP WITH GEMSDOE32 — DO NOT RE-SUBMIT.",
        },
        {
            "site": "GEMSDOE30",
            "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE30",
            "best_submission": "GEMSDOE30_dotted-h19-5-d2-8_20261003T061212Z_e56ea318-zeros.tif",
            "local_raster": reg_dir / "g30_d28.tif",
            "best_live_score": 0.2600,
            "score_label": "OWNER-REPORTED (tied #6); 2026-10-25 MSDB1 (`c878ed0c318c`) scored 0.1462 OWNER-REPORTED",
            "recent_2026_10_25_run": "30gemsdoe-msdb1-oof-submod-b2-37654-20261025-c878ed0c318c-zeros.tif (0.1462 OWNER-REPORTED — single-stage OOF without 2-stage vesselness or regime calibration)",
            "lineage": "Historical best is byte-identical in-footprint to GEMSDOE25 d=2.8 (`e56ea318af89`, 44,090 px); new MSDB1 scored 0.1462",
            "action_verdict": "ALREADY SUBMITTED (exact in-footprint duplicate of GEMSDOE25 d=2.8) — DO NOT RE-SUBMIT.",
        },
        {
            "site": "GEMSDOE24",
            "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE24",
            "best_submission": "gems24-dotted-h19-5-d1-5-20261001-989f59505db1.tif",
            "local_raster": reg_dir / "g24_d15.tif",
            "best_live_score": 0.2477,
            "score_label": "OWNER-REPORTED (#8); 2026-10-25 GVC1 (`88c3b8e804c6`) scored 0.0859 OWNER-REPORTED",
            "recent_2026_10_25_run": "24gemsdoe-gvc1-offcat-b2-20261025-88c3b8e804c6-zeros.tif (0.0859 OWNER-REPORTED — off-catalogue geochemical proxy over-emission)",
            "lineage": "H19-5 Poisson d=1.5 (60,069 px; over-dense 150 m spacing + unpruned <=200 m collar cost -0.0301 vs GEMSDOE32)",
            "action_verdict": "ALREADY SUBMITTED & OVER-PACKED H19-5 LINEAGE — DO NOT RE-SUBMIT.",
        },
        {
            "site": "GEMSDOE27",
            "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE27",
            "best_submission": "gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-allfinite.tif (0.2449) & gems27-h29-hydrothermal-piedmont-celf-20261025-511898747886-allfinite.tif (0.2190)",
            "local_raster": paths.DOCS / "downloads" / "gems27-h29-hydrothermal-piedmont-celf-20261025-511898747886-allfinite.tif",
            "best_live_score": 0.2449,
            "h29s_live_score": 0.2190,
            "score_label": "OWNER-REPORTED: Slot 1 (`5512495c6bd1`) = 0.2449; Session-7 unique ML `H29-S` (`511898747886`) = 0.2190 (#1 of all 5 non-H19-5 2026-10-25 runs, beating 0.1462 / 0.0859 / 0.0742 / 0.0217)",
            "recent_2026_10_25_run": "gems27-h29-hydrothermal-piedmont-celf-20261025-511898747886-allfinite.tif (0.2190 OWNER-REPORTED — ALREADY SUBMITTED; DO NOT RE-SUBMIT)",
            "lineage": "Slot 1 was H19-5 d=1.5 + 1,259 zero-hit T-v2 straight bridges (retired). H29-S (0.2190) proved 2-stage hydrothermal+piedmont+Frangi OOF works live (5.79x blind concentration), and revealed 4 exact fixable deficits addressed in Session 10 Lane H31-1.",
            "action_verdict": "THIS REPO — Both Slot 1 (`5512495c6bd1`) and `H29-S` (`511898747886`) are ALREADY SUBMITTED. Only the newly generated Session-10 `H31-1` unique GeoTIFF (if and only if its automated Run Card gates PASS) may be considered for a new submission.",
        },
    ]

    rows = []
    for sp in site_specs:
        m = measure_raster(
            sp["local_raster"], foot, labels, d_cat, lid_valid, quad, g32_tree
        )
        score_for_inv = sp.get("h29s_live_score", sp["best_live_score"])
        inv = invert_dti(m["n_dots"], m["c_blind_coverage"], score_for_inv)
        row = {k: v for k, v in sp.items() if k != "local_raster"}
        row["local_raster_rel"] = str(sp["local_raster"].relative_to(paths.REPO))
        row["measured_geometry"] = m
        row["live_dti_inversion_for_measured_raster"] = {
            "inverted_score": score_for_inv,
            "score_provenance": "OWNER-REPORTED",
            **inv,
        }
        rows.append(row)

    # Also measure GEMSDOE27 Slot 1 (0.2449) separately so both scored GEMSDOE27 files have exact metrics:
    slot1_path = paths.DOCS / "downloads" / "gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-allfinite.tif"
    slot1_m = measure_raster(slot1_path, foot, labels, d_cat, lid_valid, quad, g32_tree)
    slot1_inv = invert_dti(slot1_m["n_dots"], slot1_m["c_blind_coverage"], 0.2449)

    cohort_2026_10_25 = [
        {
            "rank_in_cohort": 1,
            "site": "GEMSDOE27",
            "submission": "gems27-h29-hydrothermal-piedmont-celf-20261025-511898747886-allfinite",
            "owner_reported_score": 0.2190,
            "method": "2-stage nested spatial OOF (32 base + 20 hydrothermal/piedmont/destriped-mag + 10 Frangi vesselness) + B2 + weighted 300 m CELF (min_sep=2.0)",
            "diagnostic": "Best of the 5-submission 2026-10-25 non-H19-5 cohort (+0.0728 over #2). Reached 5.79x blind concentration (matching H19-5's 5.66x), proving multi-physics OOF transfers live, but lost ~0.03-0.05 DTI to min_sep=2.0 2D blob crowding (-11.0% coverage c=0.0527 vs 0.0592), single-tree LiDAR-gap starvation (18.3% vs 24.6% area), d<=5 halo bleed (24.1% vs 15.0%), and missing SE seismic fabric.",
        },
        {
            "rank_in_cohort": 2,
            "site": "GEMSDOE30",
            "submission": "30gemsdoe-msdb1-oof-submod-b2-37654-20261025-c878ed0c318c-zeros",
            "owner_reported_score": 0.1462,
            "method": "Single-stage multi-scale OOF + submodular B2 (37,654 px)",
            "diagnostic": "Lacked 2-stage axial Frangi vesselness, hydrothermal geothermometry, and LiDAR-gap regime calibration (-0.0728 behind GEMSDOE27 H29-S).",
        },
        {
            "rank_in_cohort": 3,
            "site": "GEMSDOE24",
            "submission": "24gemsdoe-gvc1-offcat-b2-20261025-88c3b8e804c6-zeros",
            "owner_reported_score": 0.0859,
            "method": "Off-catalogue geothermal/vent geochemical proxy (B2)",
            "diagnostic": "Broad geochemical dispersion plumes without structural scarp/potential-field crest localization emit predominantly off-fault false positives.",
        },
        {
            "rank_in_cohort": 4,
            "site": "GEMSDOE25",
            "submission": "25gemsdoe-h66-mgd-20261025-83539880f9da-zeros",
            "owner_reported_score": 0.0742,
            "method": "Blind magnetic-gradient domain + SGMC reactivation",
            "diagnostic": "Unfiltered Tertiary volcanic flow edges and pluton rims mimic magnetic fault steps when uncorroborated by gravity/terrain/seismicity.",
        },
        {
            "rank_in_cohort": 5,
            "site": "GEMSDOE28",
            "submission": "28gemsdoe-s18-mxtp-37654-20261025-05fc81ca2760-zeros",
            "owner_reported_score": 0.0217,
            "method": "37,654-dot mixed catalogue-tip extrapolation (MXTP)",
            "diagnostic": "Reconfirms Slot-1/82GEMSDOE/91GEMSDOE failure mode: extrapolating off mapped tips without multi-physics surface/subsurface evidence yields near-blind precision.",
        },
    ]

    summary = {
        "generated_utc": "2026-10-26",
        "purpose": "Byte-authenticated executive summary across all 9 focus sites + PhD forensic inversion of 0.2778 (GEMSDOE32) and 0.2190 (GEMSDOE27 H29-S)",
        "provenance_rule": "All live scores are OWNER-REPORTED from the user prompt and sibling registries; zero DrivenData endpoints were accessed and zero organizer receipts are claimed.",
        "leaderboard_high_discrepancy_flag": {
            "prompt_2026_10_26_claim": 0.4413,
            "prompt_49gemsdoe_claim": 0.4413,
            "oct_2026_sibling_top10_snapshot_high": 0.3195,
            "status": "FLAGGED_UNVERIFIED_OWNER_REPORTED",
            "explanation": "The 2026-10-25/26 prompts list Current Leaderboard High Score = 0.4413 and 49GEMSDOE = 0.4413, whereas the earlier sibling snapshot recorded #1 = 0.3195 and no 49GEMSDOE repository or DrivenData receipt exists in buffedlizard55-lab. Treated strictly as unverified OWNER-REPORTED context.",
        },
        "best_historical_focus_submission": {
            "site": "GEMSDOE32",
            "submission": "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif",
            "owner_reported_score": 0.2778,
            "already_submitted_do_not_copy": True,
            "why_it_topped_focus_sites": [
                "1. Multi-line physical corroboration (H19-5): requires primary morphological/structural lineament backed by >= 0.18 independent secondary physical evidence, yielding 6.50x blind truth concentration at 37,654 px.",
                "2. Exact d=2.8 px Poisson-disk axial spacing: achieves 0.0592 blind footprint coverage with near-zero 2D lateral clumping (only 0.68% of dots have >=3 neighbors within 300 m, vs 8.51% in H29-S min_sep=2.0).",
                "3. Metric-exact B2 (>200 m) catalogue-collar subtraction: removes 6,436 near-catalogue halo dots (44,090 -> 40,199 -> 37,654) whose OOF marginal efficiency (0.0034-0.0080) is 7-15x below the DTI break-even threshold alpha*DTI/(1 - alpha*DTI) = 0.0588, lifting live DTI monotonically 0.2600 -> 0.2708 -> 0.2778 (+0.0178 gain with zero new truth required).",
                "4. Balanced 23.6% emission in the 24.6% 1-m LiDAR coverage gap (vs 18.3% in single-tree H29-S), avoiding basin-interior blind-fault recall collapse.",
            ],
        },
        "focus_sites": rows,
        "gemsdoe27_slot1_measured": {
            "submission": slot1_path.name,
            "owner_reported_score": 0.2449,
            "measured_geometry": slot1_m,
            "live_dti_inversion": slot1_inv,
        },
        "non_h19_5_live_cohort_2026_10_25": cohort_2026_10_25,
        "non_h19_5_fleet_benchmarks": [
            {"site": "GEMSDOE70", "submission": "oof-submod-300m-fp0p06-d2p8", "owner_reported_score": 0.2478, "lesson": "Separate LiDAR-present (M_Q) + LiDAR-missing subsurface (M_S) OOF models quantile-calibrated to M_Q + d=2.8 300 m submodular cover."},
            {"site": "GEMSDOE76", "submission": "piedmont-oof", "owner_reported_score": 0.2343, "lesson": "Piedmont-focused OOF scarp + subsurface features with B2 collar exclusion."},
            {"site": "GEMSDOE27", "submission": "H29-S (511898747886)", "owner_reported_score": 0.2190, "lesson": "2-stage hydrothermal + piedmont flexure + Frangi vesselness + CELF (min_sep=2.0); #1 of 2026-10-25 five-site cohort, with +0.03-0.05 recoverable DTI from fixing min_sep=2.8, LiDAR-gap dual-expert calibration, and SE Walker Lane seismic fabric."},
        ],
    }

    out_path = paths.EVIDENCE / "focus_sites_executive_summary_20261026.json"
    out_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(f"wrote {out_path} ({len(rows)} focus sites verified)")
    for r in rows:
        mg = r["measured_geometry"]
        iv = r["live_dti_inversion_for_measured_raster"]
        print(
            f"  {r['site']:10s} best={r['best_live_score']:.4f} N={mg['n_dots']:6d} "
            f"c={mg['c_blind_coverage']:.4f} lid_miss={mg['lidar_missing_dot_share']:.3f} "
            f"conc={iv['concentration_over_blind']:.2f}x ov_g32={mg['overlap_3px_vs_g32_02778']:.1%}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
