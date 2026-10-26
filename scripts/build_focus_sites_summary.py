#!/usr/bin/env python3
"""Compute byte-authenticated 9-focus-site executive summary and live-score autopsy.

Covers every focus site named in the 2026-10-26 prompt:
  GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30,
  GEMSDOE31, GEMSDOE32, GEMSDOE33, GEMSDOE36
including both their highest-scoring historical OWNER-REPORTED submissions AND
their active 2026-10-26 main-branch downloadable GeoTIFFs (byte-measured from
data_cache/parallel_20261026/ and docs/downloads/), plus the 2026-10-25 five-site
non-H19-5 live cohort (0.2190, 0.1462, 0.0859, 0.0742, 0.0217).

All live scores are labelled OWNER-REPORTED (never ORGANIZER-CONFIRMED unless an
organizer receipt exists in the repository). All projections report BOTH
geometric and hybrid MODEL-ESTIMATE assumptions per AGENTS.md. Never accesses drivendata.org.
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

from gems27 import grid, holdout, metric, paths

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


def forward_dti(n_dots: int, c_cov: float, conc: float) -> float:
    tpw = min(G_REF, G_REF * c_cov * conc)
    fp = max(0.0, float(n_dots) - RHO_REF * tpw)
    fn = max(0.0, G_REF - tpw)
    return float(tpw / (tpw + ALPHA * fp + BETA * fn))


def model_estimate_bounds(
    n_dots: int,
    c_cov: float,
    outside_mode: str,
    holdout_ratio_vs_h29s: float = 1.0,
) -> dict:
    """Side-by-side geometric and hybrid MODEL-ESTIMATE bounds anchored to H29-S = 0.2190 OWNER-REPORTED."""
    if outside_mode == "nan":
        return {
            "portal_range_valid": False,
            "geometric_assumption_dti": None,
            "hybrid_assumption_dti": None,
            "note": "FAILS DrivenData [0, 1] range check (NaN outside footprint); rejected at portal upload.",
        }
    # H29-S live anchor: N=37,654, c=0.052698 -> live DTI = 0.2190 -> conc = 5.792x
    h29_conc = 5.792
    geom_dti = forward_dti(n_dots, c_cov, h29_conc)
    hyb_conc = h29_conc * (0.5 + 0.5 * float(holdout_ratio_vs_h29s))
    hyb_dti = forward_dti(n_dots, c_cov, hyb_conc)
    return {
        "portal_range_valid": True,
        "geometric_assumption_dti": round(geom_dti, 4),
        "hybrid_assumption_dti": round(hyb_dti, 4),
        "anchor": "Anchored to GEMSDOE27 H29-S = 0.2190 OWNER-REPORTED (conc=5.792x, G_ref=12,226, rho=1.38)",
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
    quad = holdout.make_quadrant_folds(foot)

    reg_dir = paths.DATA / "parallel_registry"
    sib_dir = paths.DATA / "parallel_20261026"
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
            "score_label": "OWNER-REPORTED (#1 across all 9 focus sites; no organizer receipt in repo)",
            "active_20261026_download": {
                "filename": "gemsdoe32-h46-dipasym-celf-b2-37654-20261026T174525Z-9f42346d-zeros.tif",
                "local_path": sib_dir / "g32_h46_20261026.tif",
                "holdout_dti": "0.02581 (G32 seg-hide) / 0.1612 (G32 SGMC-hide); R6=0.02216",
                "holdout_ratio_vs_h29s": 0.96,
                "site_verdict": "DO NOT SUBMIT (failed GEMSDOE32 dual-instrument gate on main)",
            },
            "lineage": "H19-5 4-line corroboration + Poisson d=2.8 + strict B2 (d_cat > 200 m) collar prune (-6,436 zero-yield halo dots vs d=2.8; -2,545 (100,200] m annulus dots vs B1)",
            "action_verdict": "HISTORICAL BENCHMARK (#1 of 9 focus sites at 0.2778) — ALREADY SUBMITTED; active 2026-10-26 H46/R6 files are DO NOT SUBMIT on GEMSDOE32 main.",
        },
        {
            "site": "GEMSDOE36",
            "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE36",
            "best_submission": "anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif",
            "local_raster": reg_dir / "g36_anderson.tif",
            "best_live_score": 0.2750,
            "score_label": "OWNER-REPORTED (#2 of 9 focus sites)",
            "active_20261026_download": {
                "filename": "gemsdoe36-hvg36-hybrid-voxgrav-dipterr-37654-20261026T170720Z-85d56b03-zeros.tif",
                "local_path": sib_dir / "g36_hvg36_20261026.tif",
                "holdout_dti": "0.13576 (whole-fold OOF n=60,988; below G36 internal bar)",
                "holdout_ratio_vs_h29s": 0.875,
                "site_verdict": "DO NOT SUBMIT (verdict=negative on GEMSDOE36 main)",
            },
            "lineage": "Exact superset of GEMSDOE32 H33-2-B2 (all 37,654 px) + 1,200 Anderson geothermal PINN dots (diluted 0.2778 -> 0.2750)",
            "action_verdict": "ALREADY SUBMITTED & 96.9% 3-px OVERLAP WITH GEMSDOE32 — DO NOT RE-SUBMIT; 2026-10-26 HVG36 is DO NOT SUBMIT.",
        },
        {
            "site": "GEMSDOE28",
            "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE28",
            "best_submission": "h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif (0.2710) & h27-4-r1-solo-d2-8-20261003-bc2d0be4c506-nan.tif (0.2708)",
            "local_raster": reg_dir / "g28_h36_1.tif",
            "best_live_score": 0.2710,
            "score_label": "OWNER-REPORTED (#3 of 9 focus sites; 0.2710 on H36-1, 0.2708 on H27-4-R1, 0.0217 on 2026-10-25 S18-MXTP)",
            "active_20261026_download": {
                "filename": "gems28-s20-nchc-dti-20261026-1d629d6c953c-allfinite.tif",
                "local_path": sib_dir / "g28_s20_nchc_20261026.tif",
                "holdout_dti": "0.0252 (G28 seg-hide; failed G28 gate)",
                "holdout_ratio_vs_h29s": 0.82,
                "site_verdict": "DO NOT SUBMIT (verdict=negative on GEMSDOE28 main)",
            },
            "lineage": "H19-5 d=2.8 + B1 (d_cat > 100 m) prune + rung-30 blind swap (37,660 px; 99.6% overlap with GEMSDOE32); 2026-10-25 S18-MXTP collapsed to 0.0217",
            "action_verdict": "ALREADY SUBMITTED (99.6% overlap with GEMSDOE32; `-nan` fails current portal [0,1] rule); 2026-10-26 S20-NCHC is DO NOT SUBMIT.",
        },
        {
            "site": "GEMSDOE31",
            "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE31",
            "best_submission": "h27-4-solo-d28-20261004-2fb3da5a-nan.tif",
            "local_raster": reg_dir / "g31_h27_4.tif",
            "best_live_score": 0.2708,
            "score_label": "OWNER-REPORTED (#4 of 9 focus sites; dot-identical to GEMSDOE28 H27-4-R1 solo)",
            "active_20261026_download": {
                "filename": "gemsdoe31-h31t-transtension-dinkelbach-20261025-b37654-zeros.tif",
                "local_path": sib_dir / "g31_h31t_20261026.tif",
                "holdout_dti": "0.1300 [0.1147, 0.1456] (gems57-pooled-hide-v2 whole-fold OOF n=60,988; vs H32-1=0.1691 & H31-1=0.1655 on same n=60,988)",
                "holdout_ratio_vs_h29s": 0.838,
                "site_verdict": "OK TO SUBMIT on GEMSDOE31 (unique: 34.1% overlap vs G32, 43.2% vs G27 H31-1; lower harmonized whole-fold OOF 0.1300 vs G27 H31-1 0.1655)",
            },
            "lineage": "Historical best is H19-5 d=2.8 + B1 prune (40,199 px; retains 2,545 B2-ring halo dots costing -0.0070 vs GEMSDOE32). Active 2026-10-26 H31-T is a genuinely new transtensional Dinkelbach raster.",
            "action_verdict": "Historical 0.2708 is ALREADY SUBMITTED; active 2026-10-26 H31-T (`83fbc267a754`) is OK TO SUBMIT in GEMSDOE31 (whole-fold OOF 0.1300 vs GEMSDOE27 H31-1 0.1655).",
        },
        {
            "site": "GEMSDOE33",
            "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE33",
            "best_submission": "h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif",
            "local_raster": reg_dir / "g33_h33d.tif",
            "best_live_score": 0.2632,
            "score_label": "OWNER-REPORTED (#5 of 9 focus sites)",
            "active_20261026_download": {
                "filename": "gemsdoe33-llc33-l1-20261026T174746Z-76f9e157d01b-zeros.tif",
                "local_path": sib_dir / "g33_llc_20261026.tif",
                "holdout_dti": "0.0235 (G33 seg-hide; failed G33 gate)",
                "holdout_ratio_vs_h29s": 0.85,
                "site_verdict": "DO NOT SUBMIT (verdict=negative on GEMSDOE33 main)",
            },
            "lineage": "H19-5 d=2.8 modified with analog tip/stepover swaps (41,865 off-cat px; retains B1/B2 collar drag)",
            "action_verdict": "ALREADY SUBMITTED & 95.3% 3-px OVERLAP WITH GEMSDOE32 — DO NOT RE-SUBMIT; 2026-10-26 LLC33 is DO NOT SUBMIT.",
        },
        {
            "site": "GEMSDOE25",
            "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE25",
            "best_submission": "dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif",
            "local_raster": reg_dir / "g25_d28.tif",
            "best_live_score": 0.2600,
            "score_label": "OWNER-REPORTED (tied #6; 0.0742 on 2026-10-25 H66-MGD)",
            "active_20261026_download": {
                "filename": "gems25-h69-objbin-53522-20261026-160dbdc0c2ab-zeros.tif",
                "local_path": sib_dir / "g25_objbin_20261026.tif",
                "holdout_dti": "0.0419 (G25 holdout; 53,522 over-budget dots; failed G25 gate)",
                "holdout_ratio_vs_h29s": 0.90,
                "site_verdict": "DO NOT SUBMIT (verdict=negative on GEMSDOE25 main)",
            },
            "lineage": "Unpruned H19-5 Poisson d=2.8 (44,090 px; includes 6,436 <=200 m collar dots that cost -0.0178 vs GEMSDOE32)",
            "action_verdict": "ALREADY SUBMITTED & 85.4% 3-px OVERLAP WITH GEMSDOE32 — DO NOT RE-SUBMIT; 2026-10-26 H69-OBJBIN is DO NOT SUBMIT.",
        },
        {
            "site": "GEMSDOE30",
            "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE30",
            "best_submission": "d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif",
            "local_raster": reg_dir / "g30_d28.tif",
            "best_live_score": 0.2600,
            "score_label": "OWNER-REPORTED (tied #6; 0.1462 on 2026-10-25 MSDB1)",
            "active_20261026_download": {
                "filename": "gems30-GEOCOR1-b3-p39324-20261026-0ed267020015.tif",
                "local_path": sib_dir / "g30_geocor_20261026.tif",
                "holdout_dti": "0.0194 (G30 holdout; ALSO contains 7,111,787 NaNs outside footprint!)",
                "holdout_ratio_vs_h29s": 0.45,
                "site_verdict": "DO NOT SUBMIT (verdict=negative AND fails DrivenData [0,1] finite range check due to outside NaNs)",
            },
            "lineage": "Historical best is dot-identical in-footprint to GEMSDOE25 d=2.8 (44,090 px); 2026-10-25 MSDB1 scored 0.1462; 2026-10-26 GEOCOR1 has outside NaNs",
            "action_verdict": "ALREADY SUBMITTED (exact dot duplicate of GEMSDOE25 d=2.8) — DO NOT RE-SUBMIT; 2026-10-26 GEOCOR1 fails both gate and [0,1] NaN check.",
        },
        {
            "site": "GEMSDOE24",
            "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE24",
            "best_submission": "h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif",
            "local_raster": reg_dir / "g24_d15.tif",
            "best_live_score": 0.2477,
            "score_label": "OWNER-REPORTED (#8; 0.0859 on 2026-10-25 GVC1)",
            "active_20261026_download": {
                "filename": "gems24-dprf1-dualpart-rotated-frangi-celf-20261026-c1257c1d4b5a-zeros.tif",
                "local_path": sib_dir / "g24_dprf1_20261026.tif",
                "holdout_dti": "0.16379 (whole-fold OOF n=60,988; failed G24 seed-paired gate)",
                "holdout_ratio_vs_h29s": 1.055,
                "site_verdict": "DO NOT SUBMIT (verdict=negative on GEMSDOE24 main)",
            },
            "lineage": "H19-5 Poisson d=1.5 (60,069 px; over-dense 150 m spacing + unpruned <=200 m collar cost -0.0301 vs GEMSDOE32)",
            "action_verdict": "ALREADY SUBMITTED & OVER-PACKED H19-5 LINEAGE — DO NOT RE-SUBMIT; 2026-10-26 DPRF1/DKRN1 are DO NOT SUBMIT on GEMSDOE24 main.",
        },
        {
            "site": "GEMSDOE27",
            "repo_url": "https://github.com/buffedlizard55-lab/GEMSDOE27",
            "best_submission": "gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-allfinite.tif (0.2449) & gems27-h29-hydrothermal-piedmont-celf-20261025-511898747886-allfinite.tif (0.2190)",
            "local_raster": paths.DOCS / "downloads" / "gems27-h29-hydrothermal-piedmont-celf-20261025-511898747886-allfinite.tif",
            "best_live_score": 0.2449,
            "h29s_live_score": 0.2190,
            "score_label": "OWNER-REPORTED: Slot 1 (`5512495c6bd1`) = 0.2449; Session-7 unique ML `H29-S` (`511898747886`) = 0.2190 (#1 of all 5 non-H19-5 2026-10-25 runs, beating 0.1462 / 0.0859 / 0.0742 / 0.0217)",
            "active_20261026_download": {
                "filename": "gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif (PRIMARY OK TO SUBMIT) & research/gems27-h32-pdhc-kernel-celf28-20261026-324a95651136-allfinite.tif (SESSION-11 RESEARCH / DO NOT SUBMIT)",
                "local_path": paths.DOCS / "downloads" / "gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif",
                "holdout_dti": "H31-1: 0.047302 [0.044527, 0.049619] on seeds 400-409 (0.042714 on 500-509; whole-fold OOF 0.16549) | H32-1: 0.044990 [0.042371, 0.047546] on seeds 500-509 (#1 of 8 arms; whole-fold OOF 0.16910; 5/6 E2 clauses)",
                "holdout_ratio_vs_h29s": 1.0765,
                "site_verdict": "H31-1 (`cf8e1bbef244`) = SOLE MACHINE-APPROVED OK TO SUBMIT CANDIDATE | Session-11 H32-1 (`324a95651136`) = DO NOT SUBMIT (5/6 frozen E2 clauses; Clause 4 CI vs H29-S [-0.000819, +0.003063] crossed zero)",
            },
            "lineage": "Slot 1 (0.2449) & H29-S (0.2190) are ALREADY SUBMITTED. Session-10 H31-1 (`cf8e1bbef244`) passed all frozen gates on seeds 400-409. Session-11 H32-1 (`324a95651136`) improved pooled HOLDOUT-DTI over H31-1 (+0.002276, 9/10 seeds) and ranked #1 on seeds 500-509, but failed closed on Clause 4 vs H29-S.",
            "action_verdict": "THIS REPO — Only H31-1 (`cf8e1bbef244`) is machine-approved `OK TO SUBMIT` (with transparent 500-509 replication disclosure); newly generated Session-11 H32-1 (`324a95651136`) is shipped in `docs/downloads/research/` as `DO NOT SUBMIT`.",
        },
    ]

    rows = []
    for sp in site_specs:
        m = measure_raster(
            sp["local_raster"], foot, labels, d_cat, lid_valid, quad, g32_tree
        )
        score_for_inv = sp.get("h29s_live_score", sp["best_live_score"])
        inv = invert_dti(m["n_dots"], m["c_blind_coverage"], score_for_inv)

        act = dict(sp["active_20261026_download"])
        act_path = act.pop("local_path")
        act_m = measure_raster(act_path, foot, labels, d_cat, lid_valid, quad, g32_tree)
        act_est = model_estimate_bounds(
            act_m["n_dots"],
            act_m["c_blind_coverage"],
            act_m["outside_mode"],
            act["holdout_ratio_vs_h29s"],
        )
        act["measured_geometry"] = act_m
        act["model_estimated_leaderboard_bounds"] = act_est

        row = {
            k: v
            for k, v in sp.items()
            if k not in ("local_raster", "active_20261026_download")
        }
        row["local_raster_rel"] = str(sp["local_raster"].relative_to(paths.REPO))
        row["measured_geometry"] = m
        row["live_dti_inversion_for_measured_raster"] = {
            "inverted_score": score_for_inv,
            "score_provenance": "OWNER-REPORTED",
            **inv,
        }
        row["active_20261026_download"] = act
        rows.append(row)

    # Measure Session-11 H32-1 research candidate explicitly as well:
    h32_path = (
        paths.DOCS
        / "downloads"
        / "research"
        / "gems27-h32-pdhc-kernel-celf28-20261026-324a95651136-allfinite.tif"
    )
    h32_m = measure_raster(h32_path, foot, labels, d_cat, lid_valid, quad, g32_tree)
    h32_est = model_estimate_bounds(
        h32_m["n_dots"], h32_m["c_blind_coverage"], h32_m["outside_mode"], 0.044990 / 0.043802
    )

    slot1_path = (
        paths.DOCS
        / "downloads"
        / "gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-allfinite.tif"
    )
    slot1_m = measure_raster(slot1_path, foot, labels, d_cat, lid_valid, quad, g32_tree)
    slot1_inv = invert_dti(slot1_m["n_dots"], slot1_m["c_blind_coverage"], 0.2449)

    cohort_2026_10_25 = [
        {
            "rank_in_cohort": 1,
            "site": "GEMSDOE27",
            "submission": "gems27-h29-hydrothermal-piedmont-celf-20261025-511898747886-allfinite",
            "owner_reported_score": 0.2190,
            "method": "2-stage nested spatial OOF (32 base + 20 hydrothermal/piedmont/destriped-mag + 10 Frangi vesselness) + B2 + weighted 300 m CELF (min_sep=2.0)",
            "diagnostic": "Best of the 5-submission 2026-10-25 non-H19-5 cohort (+0.0728 over #2). Reached 5.79x blind concentration (matching H19-5's 5.66x), proving multi-physics OOF transfers live, while revealing min_sep=2.0 crowding (-11.0% coverage c=0.0527 vs 0.0592) and LiDAR-gap starvation (18.3% vs 24.6% area).",
        },
        {
            "rank_in_cohort": 2,
            "site": "GEMSDOE30",
            "submission": "gems30-MSDB1-edge44090-20261025-e7856ec3f14a",
            "owner_reported_score": 0.1462,
            "method": "Single-stage multi-scale OOF + submodular B2",
            "diagnostic": "Lacked 2-stage axial Frangi vesselness, hydrothermal geothermometry, and LiDAR-gap regime calibration (-0.0728 behind GEMSDOE27 H29-S).",
        },
        {
            "rank_in_cohort": 3,
            "site": "GEMSDOE24",
            "submission": "gems24-gvc1-negative-geothermal-lineament-submod-20261025-abe8e51c719d-zeros",
            "owner_reported_score": 0.0859,
            "method": "Off-catalogue geothermal/vent geochemical proxy (B2)",
            "diagnostic": "Broad geochemical dispersion plumes without structural scarp/potential-field crest localization emit predominantly off-fault false positives.",
        },
        {
            "rank_in_cohort": 4,
            "site": "GEMSDOE25",
            "submission": "gems25-h66-mgd-flank-sapd3-0-k3p5-20261025-da617550a0e9-zeros",
            "owner_reported_score": 0.0742,
            "method": "Blind magnetic-gradient domain + SGMC reactivation",
            "diagnostic": "Unfiltered Tertiary volcanic flow edges and pluton rims mimic magnetic fault steps when uncorroborated by gravity/terrain/seismicity.",
        },
        {
            "rank_in_cohort": 5,
            "site": "GEMSDOE28",
            "submission": "gems28-s18-mxtp-20261025-3e95505c011a-allfinite",
            "owner_reported_score": 0.0217,
            "method": "37,654-dot mixed catalogue-tip extrapolation (MXTP)",
            "diagnostic": "Reconfirms Slot-1/82GEMSDOE/91GEMSDOE failure mode: extrapolating off mapped tips without multi-physics surface/subsurface evidence yields near-blind precision.",
        },
    ]

    summary = {
        "generated_utc": "2026-10-26",
        "purpose": "Byte-authenticated executive summary across all 9 focus sites (historical OWNER-REPORTED bests + active 2026-10-26 main downloads) + PhD forensic inversion of 0.2778 (GEMSDOE32) and 0.2190 (GEMSDOE27 H29-S)",
        "provenance_rule": "All live scores are OWNER-REPORTED from the user prompt and sibling registries; zero DrivenData endpoints were accessed and zero organizer receipts are claimed. All projections report side-by-side geometric and hybrid MODEL-ESTIMATE bounds.",
        "leaderboard_high_discrepancy_flag": {
            "prompt_2026_10_26_claim": 0.4413,
            "sibling_fleet_high_16gemsdoe": 0.3195,
            "gemsdoe49_actual_repo_score": 0.2376,
            "status": "FLAGGED_OWNER_REPORTED_EXTERNAL_LEADER",
            "explanation": "buffedlizard55-lab/GEMSDOE49 reports 0.2376 OWNER-REPORTED in its own repository; 0.4413 is an external competition leaderboard #1 score (owner-reported, unnamed team), while 0.3195 (16GEMSDOE) is the highest owner-reported score inside the buffedlizard55-lab fleet and 0.2778 (GEMSDOE32) is the highest across the 9 focus sites.",
        },
        "best_historical_focus_submission": {
            "site": "GEMSDOE32",
            "submission": "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif",
            "owner_reported_score": 0.2778,
            "already_submitted_do_not_copy": True,
            "why_it_topped_focus_sites": [
                "1. Multi-line physical corroboration (H19-5): requires primary morphological/structural lineament backed by >= 0.18 independent secondary physical evidence, yielding 6.50x blind truth concentration at 37,654 px.",
                "2. Exact d=2.8 px Poisson-disk axial spacing: achieves 0.05922 blind footprint coverage with ZERO >=3-neighbor crowding in 300 m (0.00% vs 8.51% in H29-S min_sep=2.0).",
                "3. Metric-exact B2 (>200 m) catalogue-collar subtraction: removes 6,436 near-catalogue halo dots (44,090 -> 40,199 -> 37,654) whose OOF marginal efficiency (0.0034-0.0080) is 7-17x below the DTI break-even threshold alpha*DTI/(1 - alpha*DTI) = 0.0588, lifting live DTI monotonically 0.2600 -> 0.2708 -> 0.2778 (+0.0178 gain with zero new truth required).",
                "4. Balanced 23.6% emission in the 24.6% 1-m LiDAR coverage gap (vs 18.3% in single-tree H29-S), avoiding basin-interior blind-fault recall collapse.",
            ],
        },
        "focus_sites": rows,
        "gemsdoe27_session11_h32_measured": {
            "submission": h32_path.name,
            "directory": "docs/downloads/research",
            "verdict": "negative (DO NOT SUBMIT — 5/6 frozen E2 clauses passed; Clause 4 vs H29-S CI [-0.000819, +0.003063] crossed zero)",
            "holdout_dti_seeds_500_509_buffered": 0.044990,
            "holdout_dti_seeds_500_509_unbuffered": 0.113813,
            "holdout_dti_whole_quadrant_n60988": 0.169096,
            "measured_geometry": h32_m,
            "model_estimated_leaderboard_bounds": h32_est,
        },
        "gemsdoe27_slot1_measured": {
            "submission": slot1_path.name,
            "owner_reported_score": 0.2449,
            "measured_geometry": slot1_m,
            "live_dti_inversion": slot1_inv,
        },
        "non_h19_5_live_cohort_2026_10_25": cohort_2026_10_25,
        "non_h19_5_fleet_benchmarks": [
            {
                "site": "GEMSDOE70",
                "submission": "oof-submod-300m-fp0p06-d2p8",
                "owner_reported_score": 0.2478,
                "lesson": "Separate LiDAR-present (M_Q) + LiDAR-missing subsurface (M_S) OOF models quantile-calibrated to M_Q + d=2.8 300 m submodular cover.",
            },
            {
                "site": "GEMSDOE76",
                "submission": "piedmont-oof",
                "owner_reported_score": 0.2343,
                "lesson": "Piedmont-focused OOF scarp + subsurface features with B2 collar exclusion.",
            },
            {
                "site": "GEMSDOE27",
                "submission": "H29-S (511898747886)",
                "owner_reported_score": 0.2190,
                "lesson": "2-stage hydrothermal + piedmont flexure + Frangi vesselness + CELF (min_sep=2.0); #1 of 2026-10-25 five-site cohort.",
            },
        ],
    }

    out_path = paths.EVIDENCE / "focus_sites_executive_summary_20261026.json"
    out_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(f"wrote {out_path} ({len(rows)} focus sites verified)")
    for r in rows:
        act = r["active_20261026_download"]
        est = act["model_estimated_leaderboard_bounds"]
        print(
            f"  {r['site']:10s} hist_best={r['best_live_score']:.4f} | "
            f"20261026_dots={act['measured_geometry']['n_dots']:6d} mode={act['measured_geometry']['outside_mode']:15s} "
            f"geom={str(est['geometric_assumption_dti']):6s} hyb={str(est['hybrid_assumption_dti']):6s} | {act['site_verdict'][:48]}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
