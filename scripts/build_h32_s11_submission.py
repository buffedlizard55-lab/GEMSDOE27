#!/usr/bin/env python3
"""Experiment E3 (Lane L-S11-2026-10-26 / H32-1):
Build genuinely unique dual-partition stitched-OOF + cover-aware 300 m kernel-DTI axial-crest
min_sep=2.8 CELF GeoTIFF (`-allfinite.tif`), verify [0, 1] all-finite range across all 12,279,160
cells, verify uniqueness against all 12 peer rasters + all 10 2026-10-26 sibling focus-site rasters +
both live-scored GEMSDOE27 submissions (Slot 1 + H29-S) + extended repo rasters (including H31-1),
emit the PARALLEL-RUN PROTOCOL JSON Run Card, and run `scripts/audit_submission_readiness.py`.
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

from gems27 import grid, holdout, metric, paths, readiness, submission
from gems27 import hydrothermal_piedmont as h29
from gems27 import poisson_conduit_dti as h32

BUDGET_TOTAL: int = 37_654
B_EXCL: float = 2.0
DATE_TAG: str = "20261026"

CACHE_DIR = paths.DATA / "h32"
DL_DIR = paths.DOCS / "downloads"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def get_or_fit_rot45_oof(
    base_X: np.ndarray,
    sub15_X: np.ndarray,
    h29_X: np.ndarray,
    h31_X: np.ndarray,
    h32_X: np.ndarray,
    labels: np.ndarray,
    foot: np.ndarray,
    lid_valid: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    psub_p = CACHE_DIR / "prob_h32_sub_rot45.npy"
    ps1_p = CACHE_DIR / "prob_h32_s1_rot45.npy"
    ps2_p = CACHE_DIR / "prob_h32_s2_rot45.npy"
    if psub_p.exists() and ps1_p.exists() and ps2_p.exists():
        return np.load(psub_p), np.load(ps1_p), np.load(ps2_p)
    print("fitting H32-1 cover-aware dual-target 2-stage nested spatial OOF (45-deg Rotated 4-Sector)...", flush=True)
    t0 = time.time()
    rot_folds = h29.sector_masks_rotated45(foot)
    mmap_ps = (
        paths.PREPARED_FEATURES,
        CACHE_DIR / "subsurface15.npy",
        CACHE_DIR / "h29_features.npy",
        CACHE_DIR / "h31_features.npy",
        CACHE_DIR / "h32_features.npy",
    )
    p_sub, p_s1, p_s2 = h32.fit_predict_pdhc_oof(
        base_X,
        sub15_X,
        h29_X,
        h31_X,
        h32_X,
        labels,
        foot,
        lid_valid,
        fold_masks=rot_folds,
        buffer_px=h32.BUFFER_PX,
        seed=501,
        cache_dir=CACHE_DIR,
        cache_tag="rot45",
        mmap_paths=mmap_ps,
    )
    print(f"  finished H32-1 Rotated-45 OOF in {time.time() - t0:.1f}s", flush=True)
    np.save(psub_p, p_sub)
    np.save(ps1_p, p_s1)
    np.save(ps2_p, p_s2)
    return p_sub, p_s1, p_s2


def dot_overlap_and_spearman(
    cand_pts: np.ndarray,
    cand_inside: np.ndarray,
    cand_surf_inside: np.ndarray,
    ref_tif: Path,
    foot: np.ndarray,
    labels: np.ndarray,
) -> dict[str, float | int]:
    with rasterio.open(ref_tif) as ds:
        arr = np.nan_to_num(ds.read(1), nan=0.0).astype(np.float32)
    ref_inside = arr[foot]
    ref_dots = (arr > 0.5) & foot & (~labels)
    ref_pts = np.argwhere(ref_dots).astype(np.float64)
    if ref_pts.shape[0] == 0:
        ov_cand_to_ref = 0.0
        ov_ref_to_cand = 0.0
    else:
        t_ref = cKDTree(ref_pts)
        d_c2r, _ = t_ref.query(cand_pts, k=1)
        ov_cand_to_ref = float((d_c2r <= 3.0 + 1e-9).mean())
        t_cand = cKDTree(cand_pts)
        d_r2c, _ = t_cand.query(ref_pts, k=1)
        ov_ref_to_cand = float((d_r2c <= 3.0 + 1e-9).mean())

    rng = np.random.default_rng(20261026)
    take = rng.choice(cand_inside.size, size=min(400_000, cand_inside.size), replace=False)
    rho_dots, _ = spearmanr(cand_inside[take], ref_inside[take])
    rho_surf, _ = spearmanr(cand_surf_inside[take], ref_inside[take])
    return {
        "ref_dots": int(ref_pts.shape[0]),
        "candidate_dot_fraction_within_3px": round(ov_cand_to_ref, 5),
        "reference_dot_fraction_within_3px": round(ov_ref_to_cand, 5),
        "postplacement_dot_spearman": round(float(0.0 if np.isnan(rho_dots) else rho_dots), 5),
        "preplacement_surface_spearman": round(float(0.0 if np.isnan(rho_surf) else rho_surf), 5),
    }


def main() -> int:
    t0 = time.time()
    e1 = json.loads((paths.EVIDENCE / "h32_s11_e1_canary_and_surface.json").read_text())
    e2 = json.loads((paths.EVIDENCE / "h32_s11_e2_holdout_500_509.json").read_text())

    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS) & foot
    existing_faults = grid.load_labels(paths.DATA / "existing_faults.tif") & foot
    assert np.array_equal(labels, existing_faults), "labels.tif != existing_faults.tif"
    with rasterio.open(paths.LIDAR) as ls:
        lid_valid = foot & (ls.read(12) > 0)

    base_X = np.load(paths.PREPARED_FEATURES, mmap_mode="r")
    sub15_X = np.load(CACHE_DIR / "subsurface15.npy", mmap_mode="r")
    h29_X = np.load(CACHE_DIR / "h29_features.npy", mmap_mode="r")
    h31_X = np.load(CACHE_DIR / "h31_features.npy", mmap_mode="r")
    h32_X = np.load(CACHE_DIR / "h32_features.npy", mmap_mode="r")

    prob_quad = np.load(CACHE_DIR / "prob_h32_s2_quad.npy")
    _, _, prob_rot45 = get_or_fit_rot45_oof(
        base_X, sub15_X, h29_X, h31_X, h32_X, labels, foot, lid_valid
    )

    prob_stitched = (np.float32(0.5) * prob_quad + np.float32(0.5) * prob_rot45).astype(np.float32)
    prob_stitched[~foot] = 0.0
    np.save(CACHE_DIR / "prob_h32_stitched_oof.npy", prob_stitched)

    d_cat = distance_transform_edt(~labels)
    dom = foot & (~labels)

    print(
        f"placing {BUDGET_TOTAL} dots via H32-1 cover-aware axial-crest min_sep={h32.CELF_MIN_SEP_PX} 300 m CELF...",
        flush=True,
    )
    t_celf = time.time()
    dots = h32.emit_h32_celf(
        prob_stitched,
        foot,
        labels,
        budget=BUDGET_TOTAL,
        b_excl=B_EXCL,
        gamma=h32.CELF_GAMMA,
        min_sep_px=h32.CELF_MIN_SEP_PX,
    )
    print(f"  placed {int(dots.sum())} dots in {time.time() - t_celf:.2f}s", flush=True)

    assert int(dots.sum()) == BUDGET_TOTAL, f"Expected {BUDGET_TOTAL} dots, got {int(dots.sum())}"
    assert not (dots & ~foot).any(), "Emitted outside footprint"
    assert not (dots & labels).any(), "Emitted on catalogue fault"
    assert float(d_cat[dots].min()) > B_EXCL, "Violated B2 200 m collar"

    pts = np.argwhere(dots).astype(np.float64)
    tree_self = cKDTree(pts)
    nn_d, _ = tree_self.query(pts, k=2)
    min_self_dist = float(nn_d[:, 1].min())
    assert min_self_dist >= h32.CELF_MIN_SEP_PX - 1e-6, f"Violated min_sep_px: {min_self_dist}"
    nbr_counts = np.array([len(v) - 1 for v in tree_self.query_ball_point(pts, r=3.0)])

    d_to_p = distance_transform_edt(~dots)
    c_blind = float(metric.kernel_from_distance(d_to_p[dom]).mean())
    lid_miss_share = float((~lid_valid[dots]).mean())
    quad_grid = holdout.make_quadrant_folds(foot)
    q_shares = {
        fnm: round(float((quad_grid[dots] == qi).mean()), 4)
        for qi, fnm in enumerate(holdout.FOLD_NAMES)
    }
    dc_dots = d_cat[dots]
    geom_diagnostics = {
        "n_dots": BUDGET_TOTAL,
        "nn_min_px": round(min_self_dist, 4),
        "nn_p10_px": round(float(np.percentile(nn_d[:, 1], 10)), 4),
        "nn_median_px": round(float(np.median(nn_d[:, 1])), 4),
        "nbr_le_3px_mean": round(float(nbr_counts.mean()), 4),
        "frac_ge_3nbr_in_3px": round(float((nbr_counts >= 3).mean()), 5),
        "c_blind_coverage": round(c_blind, 6),
        "c_gain_vs_h29s_00527": round(c_blind - 0.052698, 6),
        "lidar_missing_dot_share": round(lid_miss_share, 4),
        "footprint_lidar_missing_area_share": round(float((~lid_valid[foot]).mean()), 4),
        "d_cat_min_px": round(float(dc_dots.min()), 4),
        "d_cat_median_px": round(float(np.median(dc_dots)), 2),
        "d_cat_le_5_share": round(float((dc_dots <= 5.0 + 1e-9).mean()), 4),
        "d_cat_gt_15_share": round(float((dc_dots > 15.0).mean()), 4),
        "quadrant_shares": q_shares,
    }
    print("GEOMETRY DIAGNOSTICS:", json.dumps(geom_diagnostics), flush=True)

    pred = dots.astype(np.float32)
    cid = submission.scored_content_id(pred, foot, labels)
    slug = "h32-pdhc-kernel-celf28"
    fn_allfinite = submission.make_filename("gems27", slug, DATE_TAG, cid, "allfinite")
    fn_nan = submission.make_filename("gems27", slug, DATE_TAG, cid, "nan")

    DL_DIR.mkdir(parents=True, exist_ok=True)
    tmp_af = DL_DIR / fn_allfinite
    tmp_nan = DL_DIR / fn_nan
    submission.write_geotiff(pred, paths.TEMPLATE, tmp_af, outside="zero")
    submission.write_geotiff(pred, paths.TEMPLATE, tmp_nan, outside="nan")
    tmp_zip = submission.zip_single(tmp_af)

    chk_af = submission.verify_geotiff(tmp_af, paths.TEMPLATE)
    chk_nan = submission.verify_geotiff(tmp_nan, paths.TEMPLATE)
    assert chk_af["hard_checks_passed"], f"allfinite hard fail: {chk_af['hard_failures']}"
    assert chk_nan["hard_checks_passed"], f"nan hard fail: {chk_nan['hard_failures']}"

    peer_uniq_path = paths.EVIDENCE / "h32_s11_uniqueness_vs_peers.json"
    subprocess.run(
        [
            sys.executable,
            str(paths.REPO / "scripts" / "check_parallel_uniqueness.py"),
            str(tmp_af),
            "--out",
            str(peer_uniq_path),
        ],
        check=True,
    )
    peer_uniq = json.loads(peer_uniq_path.read_text())

    cand_inside = pred[foot]
    surf_inside = prob_stitched[foot]

    peer_surface_spearman: dict[str, float] = {}
    for p_tif in sorted((paths.DATA / "parallel_registry").glob("*.tif")):
        m_p = dot_overlap_and_spearman(pts, cand_inside, surf_inside, p_tif, foot, labels)
        peer_surface_spearman[p_tif.name] = float(m_p["preplacement_surface_spearman"])

    sibling_20261026_uniq: dict[str, dict] = {}
    sib_dir = paths.DATA / "parallel_20261026"
    if sib_dir.exists():
        for p_tif in sorted(sib_dir.glob("*.tif")):
            sibling_20261026_uniq[p_tif.name] = dot_overlap_and_spearman(
                pts, cand_inside, surf_inside, p_tif, foot, labels
            )

    scored_gems27_files = {
        "gems27_slot1_5512495c6bd1_02449": DL_DIR / "gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-allfinite.tif",
        "gems27_h29s_511898747886_02190": DL_DIR / "gems27-h29-hydrothermal-piedmont-celf-20261025-511898747886-allfinite.tif",
    }
    scored_gems27_uniq: dict[str, dict] = {}
    for k_nm, p_tif in scored_gems27_files.items():
        scored_gems27_uniq[k_nm] = dot_overlap_and_spearman(
            pts, cand_inside, surf_inside, p_tif, foot, labels
        )

    extended_unscored_repo: dict[str, dict] = {}
    for p_tif in sorted(list(DL_DIR.glob("*-allfinite.tif")) + list((DL_DIR / "research").glob("*-allfinite.tif"))):
        if p_tif.name in (fn_allfinite, fn_nan):
            continue
        if p_tif in scored_gems27_files.values():
            continue
        extended_unscored_repo[p_tif.name] = dot_overlap_and_spearman(
            pts, cand_inside, surf_inside, p_tif, foot, labels
        )

    max_peer_overlap = max(float(e["candidate_dot_fraction_within_3px"]) for e in peer_uniq["entries"])
    max_sib_overlap = (
        max(float(v["candidate_dot_fraction_within_3px"]) for v in sibling_20261026_uniq.values())
        if sibling_20261026_uniq
        else 0.0
    )
    max_scored_g27_overlap = max(
        float(v["candidate_dot_fraction_within_3px"]) for v in scored_gems27_uniq.values()
    )
    max_operative_overlap = max(max_peer_overlap, max_sib_overlap, max_scored_g27_overlap)

    max_peer_dot_rho = max(abs(float(e["spearman_rank_correlation"])) for e in peer_uniq["entries"])
    max_sib_dot_rho = (
        max(abs(float(v["postplacement_dot_spearman"])) for v in sibling_20261026_uniq.values())
        if sibling_20261026_uniq
        else 0.0
    )
    max_scored_g27_dot_rho = max(abs(float(v["postplacement_dot_spearman"])) for v in scored_gems27_uniq.values())
    max_surf_rho = max(
        max(abs(v) for v in peer_surface_spearman.values()),
        max((abs(float(v["preplacement_surface_spearman"])) for v in sibling_20261026_uniq.values()), default=0.0),
        max(abs(float(v["preplacement_surface_spearman"])) for v in scored_gems27_uniq.values()),
    )
    max_operative_spearman = max(max_peer_dot_rho, max_sib_dot_rho, max_scored_g27_dot_rho, max_surf_rho)

    max_extended_unscored_overlap = (
        max(float(v["candidate_dot_fraction_within_3px"]) for v in extended_unscored_repo.values())
        if extended_unscored_repo
        else 0.0
    )

    uniqueness_pass = (max_operative_overlap <= 0.70) and (max_operative_spearman <= 0.90)
    holdout_pass = bool(e1["gate_e1_pass"]) and bool(e2["gate_e2_pass"])
    validator_pass = bool(chk_af["hard_checks_passed"]) and bool(chk_nan["hard_checks_passed"])
    all_gates_pass = holdout_pass and uniqueness_pass and validator_pass

    target_dir = DL_DIR if all_gates_pass else (DL_DIR / "research")
    target_dir.mkdir(parents=True, exist_ok=True)
    if target_dir != DL_DIR:
        for p_move in (tmp_af, tmp_nan, tmp_zip):
            dest_p = target_dir / p_move.name
            p_move.replace(dest_p)
        path_af = target_dir / fn_allfinite
        path_nan = target_dir / fn_nan
        path_zip = target_dir / tmp_zip.name
    else:
        path_af, path_nan, path_zip = tmp_af, tmp_nan, tmp_zip

    chk_af_path = target_dir / f"checks-{fn_allfinite[:-4]}.json"
    chk_nan_path = target_dir / f"checks-{fn_nan[:-4]}.json"
    submission.dump_json(chk_af, chk_af_path)
    submission.dump_json(chk_nan, chk_nan_path)

    submission_name = f"27GEMSDOE-H32-PDHC-K-{DATE_TAG}-{cid}"
    if all_gates_pass:
        short_note = (
            f"27GEMSDOE H32-1 PDHC-K | Poisson+clay+CELF2.8 B2 {BUDGET_TOTAL}px"
            f" | id {cid} | HOLDOUT-DTI 0.0450"
        )
    else:
        short_note = (
            f"27GEMSDOE H32-1 PDHC-K | {BUDGET_TOTAL}px B2 id {cid}"
            f" | HOLDOUT-DTI 0.0450 (5/6 E2) | DO NOT SUBMIT"
        )
    assert 0 < len(short_note) <= 140, f"Note length invalid: {len(short_note)}"
    note_path = target_dir / f"note-{fn_allfinite[:-4]}.txt"
    note_path.write_text(short_note + "\n")

    vs_b0 = e2["paired_comparisons_buffered"]["H32S_minus_B0"]
    vs_d0 = e2["paired_comparisons_buffered"]["H32S_minus_D0"]
    vs_h29s = e2["paired_comparisons_buffered"]["H32S_minus_H29S"]
    vs_h31s = e2["paired_comparisons_buffered"]["H32S_minus_H31S"]

    # Model-estimated leaderboard projections under BOTH required assumptions (AGENTS.md):
    # (1) Geometric assumption: DTI scales with coverage efficiency (c_blind / c_h29s) * (holdout_ratio)
    # Closed-form nonlinear Tversky MODEL-ESTIMATE anchored to OWNER-REPORTED H29-S = 0.2190
    # (N=37,654, c=0.052698 -> conc=5.792x, G_ref=12,226, rho=1.38; matches build_focus_sites_summary.py).
    g_ref, rho_ref = 12226.0, 1.38
    h29_conc = 5.792
    h32_over_h29_buf = e2["pooled_buffered_holdout_dti"]["H32-S"] / e2["pooled_buffered_holdout_dti"]["H29-S"]

    def _forward_dti(n_dots_f: int, c_cov_f: float, conc_f: float) -> float:
        tpw = min(g_ref, g_ref * c_cov_f * conc_f)
        fp = max(0.0, float(n_dots_f) - rho_ref * tpw)
        fn = max(0.0, g_ref - tpw)
        return float(tpw / (tpw + 0.2 * fp + 0.8 * fn))

    model_est_geometric = round(_forward_dti(int(dots.sum()), c_blind, h29_conc), 4)
    model_est_hybrid = round(_forward_dti(int(dots.sum()), c_blind, h29_conc * (0.5 + 0.5 * h32_over_h29_buf)), 4)

    run_card = {
        "schema": "parallel-run-card-v2",
        "generated_utc": "2026-10-26",
        "lane": "L-S11-2026-10-26",
        "hypothesis_id": "H32-1",
        "preregistration_commit": "92d63a3a10d225bb183bdd5a902e77bcd74109a7",
        "hypothesis": (
            "Poisson-Demagnetized Hydrothermal Conduit, Asymmetric Graben Clay-Cap Coupling & "
            "Cover-Aware 300 m Kernel-Expected-DTI Synthesis (PDHC-K)"
        ),
        "mechanism": (
            "Adds 16 label-free physical features (1.5 km Cordell-Taylor Poisson gravity-pseudogravity "
            "demagnetization residual gated by iso_grav_anom_hg and subdued tmi_vg, directed 400 m & 800 m "
            "basinward hanging-wall vs footwall playa-detrended MT cond_surf clay-cap asymmetry x basement hinge, "
            "1.2 km 8-azimuth canyon-mouth knickpoint collinearity, Quaternary volcanic vent strain corridors, "
            "and physical sediment-cover blindness w_blind(depth_to_base_surf, det_local_relief)), fits nested "
            "buffered dual-target (1-px core classifier + 300 m DTI-kernel Poisson regressor) Stage-1/Stage-2 "
            "experts across two 45-deg offset 4-sector partitions, and allocates 37,654 B2 (>200 m) dots via "
            "axial-crest min_sep_px=2.8 300 m CELF cover."
        ),
        "named_non_fault_mimic": (
            "Non-magnetic Paleozoic carbonate-on-granite pluton contacts and reversely magnetized Tertiary "
            "ash-flow tuffs (deconfounded via signed local Poisson slope alpha_loc and upward-continued TMI_up150 "
            "attenuation), conductive evaporative salt playas (deconfounded via 2 km background subtraction and "
            "directed cross-hinge asymmetry), and flat-lying bedrock hogbacks / Lake Lahontan shorelines "
            "(deconfounded via down-slope basin-fill thickening gate)."
        ),
        "verdict": "promote" if all_gates_pass else "negative",
        "ok_to_submit": bool(all_gates_pass),
        "ok_to_download_for_research": True,
        "gate_failure_disclosure": (
            None
            if all_gates_pass
            else (
                "FAIL-CLOSED PER COMMIT 92d63a3: H32-S ranked #1 of all 8 arms on pooled buffered HOLDOUT-DTI "
                "(0.044990), pooled unbuffered HOLDOUT-DTI (0.113813), and harmonized whole-quadrant OOF DTI "
                "(0.169096, n=60,988), and beat Session-10 champion H31-S on 9/10 seeds (+0.002276, 95% CI "
                "[+0.000776, +0.003667]), B0 on 10/10 seeds (+0.008537), and D0 on 10/10 seeds (+0.005631), "
                "but missed frozen E2 Clause 4 vs H29-S (+0.001188 pooled, 6/10 seeds, 95% CI [-0.000819, +0.003063] "
                "straddled zero due to H29-S min_sep=2.0 packing on isolated 600m-buffered NE fragments)."
            )
        ),
        "submission_name": submission_name,
        "note_max_140_chars": short_note,
        "note_chars": len(short_note),
        "model_estimated_leaderboard_bounds": {
            "provenance_label": "MODEL-ESTIMATE (anchored to OWNER-REPORTED H29-S=0.2190 & GEMSDOE32=0.2778; NOT a live organizer score)",
            "geometric_assumption": model_est_geometric,
            "hybrid_assumption": model_est_hybrid,
        },
        "holdout": {
            "label": "HOLDOUT-DTI",
            "provenance_note": "Catalogue-internal whole-component hide-and-recover; NOT a live organizer score.",
            "evaluator": e2["evaluator_version"],
            "seeds": e2["seeds"],
            "n_cells": e2["n_cells"],
            "n_withheld_positives_total": int(e2["n_withheld_positive_occurrences"]),
            "canary_max_auc": float(e1["max_all_95_direction_invariant_auc"]),
            "canary_h32_max_auc": float(e1["max_h32_direction_invariant_auc"]),
            "pooled_dti_H32S_candidate": e2["pooled_buffered_holdout_dti"]["H32-S"],
            "pooled_dti_H32S_ci95": e2["pooled_buffered_ci95"]["H32-S"],
            "pooled_dti_H32A_detector_poisson_ablation": e2["pooled_buffered_holdout_dti"]["H32-A"],
            "pooled_dti_H31S_control": e2["pooled_buffered_holdout_dti"]["H31-S"],
            "pooled_dti_H29S_control": e2["pooled_buffered_holdout_dti"]["H29-S"],
            "pooled_dti_D0_control": e2["pooled_buffered_holdout_dti"]["D0"],
            "pooled_dti_H28_1_B2_control": e2["pooled_buffered_holdout_dti"]["H28_1_B2"],
            "pooled_dti_B0_control": e2["pooled_buffered_holdout_dti"]["B0"],
            "pooled_dti_U0_null": e2["pooled_buffered_holdout_dti"]["U0"],
            "pooled_unbuffered_diagnostic": e2["pooled_unbuffered_diagnostic_holdout_dti"],
            "harmonized_whole_quadrant_oof_n60988": e2["harmonized_whole_quadrant_oof_dti_n60988"],
            "per_fold_buffered": e2["per_fold_buffered_holdout_dti"],
            "paired_candidate_minus_B": vs_b0,
            "paired_candidate_minus_D0": vs_d0,
            "paired_candidate_minus_H29S": vs_h29s,
            "paired_candidate_minus_H31S": vs_h31s,
            "frozen_gate_clauses": e2["frozen_gate_clauses"],
            "gate_efficacy_pass": bool(holdout_pass),
        },
        "uniqueness_vs_registry": {
            "pass": bool(uniqueness_pass),
            "operative_scope": (
                "12 pinned focus-site peer rasters + 10 2026-10-26 active sibling focus-site rasters + "
                "both live-scored GEMSDOE27 submissions (Slot 1 5512495c6bd1 & H29-S 511898747886)"
            ),
            "max_dot_overlap_within_3px_euclidean": round(max_operative_overlap, 5),
            "max_dot_overlap_vs_12_peers": round(max_peer_overlap, 5),
            "max_dot_overlap_vs_20261026_siblings": round(max_sib_overlap, 5),
            "max_dot_overlap_vs_scored_gems27": round(max_scored_g27_overlap, 5),
            "max_surface_spearman": round(max_operative_spearman, 5),
            "max_preplacement_surface_spearman": round(max_surf_rho, 5),
            "max_postplacement_dot_spearman": round(max(max_peer_dot_rho, max_sib_dot_rho, max_scored_g27_dot_rho), 5),
            "peer_entries": peer_uniq["entries"],
            "peer_preplacement_surface_spearman": peer_surface_spearman,
            "sibling_20261026_entries": sibling_20261026_uniq,
            "scored_gems27_entries": scored_gems27_uniq,
            "extended_unscored_repo_max_3px_overlap": round(max_extended_unscored_overlap, 5),
            "extended_unscored_repo_entries": extended_unscored_repo,
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
            "celf_min_sep_px": h32.CELF_MIN_SEP_PX,
            "celf_gamma": h32.CELF_GAMMA,
            "geometry_diagnostics": geom_diagnostics,
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

    rc_path = paths.EVIDENCE / "h32_s11_run_card_2026-10-26.json"
    rc_path.write_text(json.dumps(run_card, indent=2) + "\n")

    cand_man = {
        "lane": "L-S11-2026-10-26",
        "hypothesis_id": "H32-1",
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
        "min_sep_px": h32.CELF_MIN_SEP_PX,
        "ok_to_submit": bool(all_gates_pass),
        "ok_to_download_for_research": True,
        "verdict": run_card["verdict"],
        "technical_validator_pass": bool(validator_pass),
        "uniqueness_pass": bool(uniqueness_pass),
        "holdout_efficacy_pass": bool(holdout_pass),
        "run_card": str(rc_path.relative_to(paths.REPO)),
    }
    (DL_DIR / "h32_s11_candidate_manifest.json").write_text(json.dumps(cand_man, indent=2) + "\n")

    decision = readiness.publication_decision(run_card, paths.REPO)
    print("READINESS PUBLICATION DECISION:", json.dumps(decision), flush=True)
    assert decision["ok_to_publish_as_submission"] == all_gates_pass, (
        f"Readiness decision mismatch: {decision} vs {all_gates_pass}"
    )

    subprocess.run([sys.executable, str(paths.REPO / "scripts" / "audit_submission_readiness.py")], check=True)
    print(f"E3 COMPLETE | verdict={run_card['verdict']} | ok_to_submit={all_gates_pass} | tif={path_af}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
