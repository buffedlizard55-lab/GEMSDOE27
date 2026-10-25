#!/usr/bin/env python3
"""Run Session 6 pre-registered `H29` 3-experiment holdout evaluation, uniqueness scan, & TIF build.

Supports deterministic stage checkpointing (`--stage all | holdout | finalize`) in git-ignored
`data_cache/prepared/h29_stage_cache/` so each stage completes well inside sandbox command limits
with identical seeds (`200..204`, `211..214`) and zero post-holdout retuning.
"""

from __future__ import annotations

import argparse
import gc
import json
import resource
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree

REPO = Path(__file__).resolve().parents[1]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from gems27 import canary_and_uniqueness as cu  # noqa: E402
from gems27 import evaluate_holdout as eh  # noqa: E402
from gems27 import grid, oof_detector, paths, submission_writer  # noqa: E402
from gems27 import h29_geothermal_piedmont as h29  # noqa: E402

DATE_TAG = "20261025"
TARGET_DOTS = 37_654
REGISTRY_RASTERS_DIR = paths.DATA / "registry_rasters"
STAGE_CACHE = paths.DATA / "prepared" / "h29_stage_cache"


def rss_mib() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def dot_geometry_diagnostics(
    dots_2d: np.ndarray, foot: np.ndarray, cat: np.ndarray
) -> dict[str, object]:
    b = (np.asarray(dots_2d) > 0.5) & foot & ~cat
    n = int(b.sum())
    d_pred = distance_transform_edt(~b)
    k_pred = np.maximum(1.0 - d_pred / 3.0, 0.0)
    active = foot & ~cat
    c_blind = float(k_pred[active].mean())
    sum_k = float(k_pred[active].sum())

    d_cat = distance_transform_edt(~cat)
    dc = d_cat[b]
    yy, xx = np.nonzero(b)
    if len(yy) >= 2:
        pts = np.column_stack([yy, xx]).astype(np.float32)
        dd, _ = cKDTree(pts).query(pts, k=2)
        nn_p10 = float(np.percentile(dd[:, 1], 10))
        nn_med = float(np.median(dd[:, 1]))
    else:
        nn_p10 = nn_med = 0.0

    quad = eh.holdout.make_quadrant_folds(foot)
    q_counts = {
        eh.holdout.FOLD_NAMES[q]: int((b & (quad == q)).sum()) for q in range(4)
    }
    return {
        "n_dots": n,
        "blind_kernel_coverage_c": round(c_blind, 6),
        "blind_kernel_sum_px": round(sum_k, 1),
        "nn_spacing_p10_px": round(nn_p10, 4),
        "nn_spacing_median_px": round(nn_med, 4),
        "d_cat_le_1px": int((dc <= 1.0001).sum()),
        "d_cat_1_to_2px": int(((dc > 1.0001) & (dc <= 2.0001)).sum()),
        "d_cat_2_to_3px": int(((dc > 2.0001) & (dc <= 3.0001)).sum()),
        "d_cat_gt_3px": int((dc > 3.0001).sum()),
        "far_field_fraction_gt_300m": round(float((dc > 3.0001).mean()) if n else 0.0, 6),
        "quadrant_dot_counts": q_counts,
    }


def build_legacy_controls_fold_safe(
    foot: np.ndarray, quad_grid: np.ndarray, visible_cat: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Build `GEMSDOE27`'s inherited 32-band `oof_detector` controls strictly on `visible_cat`."""
    p_leg = oof_detector.fit_predict_oof_probabilities(
        foot, visible_cat, quad_grid, seed=200
    )
    gc.collect()
    r_leg = oof_detector.ridge_nms(p_leg, valid=foot, sigma=1.0)
    dots_d15 = oof_detector.build_oof_dotted_base(p_leg, r_leg, foot, visible_cat, thin_d=1.5)
    d_vis = distance_transform_edt(~visible_cat)
    ctrl_legacy_boof = (dots_d15 & (d_vis > 1.0001)).astype(np.float32)

    ctrl_legacy_matched, _ = h29.priority_ridge_poisson_emit(
        p_leg, foot, visible_cat, n_dots=TARGET_DOTS, collar_px=2.0, min_dist=2.80
    )
    return ctrl_legacy_boof, ctrl_legacy_matched


def run_holdout_stage(t0: float) -> dict[str, object]:
    STAGE_CACHE.mkdir(parents=True, exist_ok=True)
    foot = grid.load_footprint(paths.TEMPLATE)
    cat = grid.load_labels(paths.LABELS)
    X_phys, phys_names = h29.ensure_h29_physical_features()

    folds, quad_grid = eh.buffered_component_draw(
        foot, cat, seed=200, hide_frac=0.20, buffer_px=3, boundary_px=20
    )
    visible_holdout = folds[0]["visible"]
    pied_col = h29.EXP1_FEATURE_NAMES.index("piedmont_habitat")
    pied_foot = np.asarray(X_phys[:, pied_col], dtype=np.float32)

    print(
        f"[{time.time()-t0:.1f}s] Building fold-safe Voronoi-jackknifed structural features "
        f"on `visible_holdout` (withheld_pos={sum(int(f['truth'].sum()) for f in folds)} px)...",
        flush=True,
    )
    S_tr_hold, S_ev_hold = h29.build_structural_features_train_and_eval(
        visible_holdout, foot, pied_foot, seed=201, n_splits=5
    )

    print(f"[{time.time()-t0:.1f}s] Running univariate leakage canaries on all 62 features...", flush=True)
    extra_2d = {}
    for j, sname in enumerate(h29.STRUCT_FEATURE_NAMES):
        a2d = np.zeros(grid.SHAPE, dtype=np.float32)
        a2d[foot] = S_ev_hold[:, j]
        extra_2d[sname] = a2d
    canary_report = cu.run_leakage_canaries(
        X_phys, phys_names, foot, folds, fold_extra_features=extra_2d, auc_limit=0.90
    )
    del extra_2d
    print(
        f"[{time.time()-t0:.1f}s] Canary gate_passed={canary_report['gate_passed']} "
        f"max_feature={canary_report['max_feature']} "
        f"max_symmetric_auc={canary_report['max_symmetric_auc']:.4f}",
        flush=True,
    )
    if not canary_report["gate_passed"]:
        raise RuntimeError(f"LEAKAGE CANARY HALT: {canary_report['flagged_features']}")

    print(f"[{time.time()-t0:.1f}s] Building random & legacy 32-band controls...", flush=True)
    rng_ctrl = np.random.default_rng(200)
    d_vis_hold = distance_transform_edt(~visible_holdout)
    elig_rand = np.flatnonzero(foot & (d_vis_hold > 2.0001))
    pick_rand = rng_ctrl.choice(elig_rand, size=TARGET_DOTS, replace=False)
    ctrl_random = np.zeros(grid.SHAPE, dtype=np.float32)
    ctrl_random.ravel()[pick_rand] = 1.0
    del d_vis_hold, elig_rand, pick_rand

    ctrl_legacy_boof, ctrl_legacy_matched = build_legacy_controls_fold_safe(
        foot, quad_grid, visible_holdout
    )

    exp1_cols = list(range(len(h29.EXP1_FEATURE_NAMES)))
    print(f"[{time.time()-t0:.1f}s] Running Exp 1 (`H29-1a` 49-ch pure physical + GDR #1391)...", flush=True)
    surf_exp1_hold = h29.fit_predict_loqo_surface(
        X_phys, foot, quad_grid, visible_holdout, col_indices=exp1_cols, seed=201
    )
    dots_exp1_hold, _ = h29.priority_ridge_poisson_emit(
        surf_exp1_hold, foot, visible_holdout, n_dots=TARGET_DOTS, collar_px=2.0, min_dist=2.80
    )
    del surf_exp1_hold
    gc.collect()

    print(f"[{time.time()-t0:.1f}s] Running Exp 2 (`H29-1` + fold-safe structural transfer)...", flush=True)
    surf_exp2_hold = h29.fit_predict_loqo_surface(
        X_phys,
        foot,
        quad_grid,
        visible_holdout,
        col_indices=exp1_cols,
        S_train_struct=S_tr_hold,
        S_eval_struct=S_ev_hold,
        seed=202,
    )
    dots_exp2_hold, _ = h29.priority_ridge_poisson_emit(
        surf_exp2_hold, foot, visible_holdout, n_dots=TARGET_DOTS, collar_px=2.0, min_dist=2.80
    )
    del surf_exp2_hold
    gc.collect()

    all_phys_cols = list(range(len(phys_names)))
    print(
        f"[{time.time()-t0:.1f}s] Running Exp 3 (`H29-1 + H29-2` 58-ch vesselness & 2*theta dual-head)...",
        flush=True,
    )
    surf_exp3_phys_hold = h29.fit_predict_loqo_surface(
        X_phys, foot, quad_grid, visible_holdout, col_indices=all_phys_cols, seed=203
    )
    surf_exp3_struct_hold = h29.fit_predict_loqo_surface(
        X_phys,
        foot,
        quad_grid,
        visible_holdout,
        col_indices=all_phys_cols,
        S_train_struct=S_tr_hold,
        S_eval_struct=S_ev_hold,
        seed=204,
    )
    surf_exp3_blend_hold = h29.blend_rank_surfaces(
        surf_exp3_struct_hold, surf_exp3_phys_hold, foot, weight_a=0.55
    )
    dots_exp3_hold, _ = h29.priority_ridge_poisson_emit(
        surf_exp3_blend_hold, foot, visible_holdout, n_dots=TARGET_DOTS, collar_px=2.0, min_dist=2.80
    )
    del S_tr_hold, S_ev_hold, surf_exp3_phys_hold, surf_exp3_struct_hold, surf_exp3_blend_hold
    gc.collect()

    print(f"[{time.time()-t0:.1f}s] Computing pooled HOLDOUT-DTI + 1,000-draw 20 km block CIs...", flush=True)
    arms_hold = {
        "ctrl_random_37654": ctrl_random,
        "ctrl_legacy_boof": ctrl_legacy_boof,
        "ctrl_legacy_matched_37654": ctrl_legacy_matched,
        "exp1_h29_1a_phys_gdr": dots_exp1_hold,
        "exp2_h29_1_full_struct": dots_exp2_hold,
        "exp3_h29_1_h29_2_dual": dots_exp3_hold,
    }
    prelim = eh.evaluate_arms_pooled(
        arms_hold, folds, foot, candidate="exp3_h29_1_h29_2_dual", block_side=200, draws=1000
    )
    exp_keys = ["exp1_h29_1a_phys_gdr", "exp2_h29_1_full_struct", "exp3_h29_1_h29_2_dual"]
    best_exp = max(exp_keys, key=lambda k: prelim["scores"][k]["dti"])
    pooled_eval = (
        prelim
        if best_exp == "exp3_h29_1_h29_2_dual"
        else eh.evaluate_arms_pooled(arms_hold, folds, foot, candidate=best_exp, block_side=200, draws=1000)
    )

    for k, srec in pooled_eval["scores"].items():
        print(
            f"  [HOLDOUT-DTI] {k:28s}: DTI={srec['dti']:.5f} "
            f"95%CI=[{srec['ci95'][0]:.5f}, {srec['ci95'][1]:.5f}] "
            f"TPw={srec['tpw']:.1f}/{srec['withheld_positive_pixels']}",
            flush=True,
        )
    print(f"  Selected top experiment (from budget=3): {best_exp}", flush=True)

    payload = {
        "best_exp": best_exp,
        "canary_report": canary_report,
        "pooled_eval": pooled_eval,
        "holdout_runtime_seconds": round(time.time() - t0, 1),
    }
    (STAGE_CACHE / "stage_holdout.json").write_text(json.dumps(payload, indent=2) + "\n")
    return payload


def _fit_full_for_arm(
    arm_key: str,
    X_phys: np.ndarray,
    phys_names: list[str],
    foot: np.ndarray,
    cat: np.ndarray,
    quad_grid: np.ndarray,
    pied_foot: np.ndarray,
) -> tuple[np.ndarray, str, str, str]:
    exp1_cols = list(range(len(h29.EXP1_FEATURE_NAMES)))
    all_phys_cols = list(range(len(phys_names)))
    if arm_key == "exp1_h29_1a_phys_gdr":
        raw_full_surf = h29.fit_predict_loqo_surface(
            X_phys, foot, quad_grid, cat, col_indices=exp1_cols, seed=211
        )
        return (
            raw_full_surf,
            "H29-1a",
            "h29-1a-piedmont-gdr-d28-b2",
            "piedmont+TMIup150+GDR1391 2mDAB/sinter ridge-Poisson d2.8 B2",
        )
    if arm_key == "exp2_h29_1_full_struct":
        S_tr_full, S_ev_full = h29.build_structural_features_train_and_eval(
            cat, foot, pied_foot, seed=211, n_splits=5
        )
        raw_full_surf = h29.fit_predict_loqo_surface(
            X_phys,
            foot,
            quad_grid,
            cat,
            col_indices=exp1_cols,
            S_train_struct=S_tr_full,
            S_eval_struct=S_ev_full,
            seed=212,
        )
        del S_tr_full, S_ev_full
        return (
            raw_full_surf,
            "H29-1",
            "h29-1-piedmont-gdr-struct-d28-b2",
            "piedmont+TMIup150+GDR1391+jackknife-tip ridge-Poisson d2.8 B2",
        )
    S_tr_full, S_ev_full = h29.build_structural_features_train_and_eval(
        cat, foot, pied_foot, seed=211, n_splits=5
    )
    surf_p = h29.fit_predict_loqo_surface(
        X_phys, foot, quad_grid, cat, col_indices=all_phys_cols, seed=213
    )
    surf_s = h29.fit_predict_loqo_surface(
        X_phys,
        foot,
        quad_grid,
        cat,
        col_indices=all_phys_cols,
        S_train_struct=S_tr_full,
        S_eval_struct=S_ev_full,
        seed=214,
    )
    raw_full_surf = h29.blend_rank_surfaces(surf_s, surf_p, foot, weight_a=0.55)
    del S_tr_full, S_ev_full, surf_p, surf_s
    return (
        raw_full_surf,
        "H29-1+H29-2",
        "h29-dual-vessel-gdr-piedmont-d28-b2",
        "dual Frangi+TMIup150+GDR1391 2mDAB/sinter+tip d2.8 B2",
    )


def run_finalize_stage(t0: float) -> int:
    stage_file = STAGE_CACHE / "stage_holdout.json"
    if not stage_file.is_file():
        raise RuntimeError(f"missing {stage_file}; run --stage holdout first")
    stage_a = json.loads(stage_file.read_text())
    canary_report = stage_a["canary_report"]
    pooled_eval_init = stage_a["pooled_eval"]

    foot = grid.load_footprint(paths.TEMPLATE)
    cat = grid.load_labels(paths.LABELS)
    X_phys, phys_names = h29.ensure_h29_physical_features()
    quad_grid = eh.holdout.make_quadrant_folds(foot)
    pied_col = h29.EXP1_FEATURE_NAMES.index("piedmont_habitat")
    pied_foot = np.asarray(X_phys[:, pied_col], dtype=np.float32)

    exp_keys_ranked = sorted(
        ["exp1_h29_1a_phys_gdr", "exp2_h29_1_full_struct", "exp3_h29_1_h29_2_dual"],
        key=lambda k: pooled_eval_init["scores"][k]["dti"],
        reverse=True,
    )
    uniqueness_attempts: list[dict[str, object]] = []
    chosen_exp = None
    final_dots = None
    geom_diag = None
    uniqueness_report = None
    hyp_label = slug = note_desc = ""

    for arm_key in exp_keys_ranked:
        print(f"[{time.time()-t0:.1f}s] Fitting full-catalogue 4-quadrant LOQO model for `{arm_key}`...", flush=True)
        raw_full_surf, hyp_label, slug, note_desc = _fit_full_for_arm(
            arm_key, X_phys, phys_names, foot, cat, quad_grid, pied_foot
        )
        gc.collect()
        cand_dots, cand_cont = h29.priority_ridge_poisson_emit(
            raw_full_surf, foot, cat, n_dots=TARGET_DOTS, collar_px=2.0, min_dist=2.80
        )
        del raw_full_surf
        cand_geom = dot_geometry_diagnostics(cand_dots, foot, cat)
        print(f"[{time.time()-t0:.1f}s] `{arm_key}` dot diagnostics: {json.dumps(cand_geom)}", flush=True)

        cand_uniq = cu.scan_registry_uniqueness(
            cand_cont,
            cand_dots,
            foot,
            cat,
            REGISTRY_RASTERS_DIR,
            rho_limit=0.90,
            overlap_limit=0.70,
        )
        print(
            f"[{time.time()-t0:.1f}s] `{arm_key}` uniqueness gate_passed={cand_uniq['gate_passed']} "
            f"max_surf_rho={cand_uniq['max_surface_spearman']['abs_rho']:.4f} "
            f"max_dots_rho={cand_uniq['max_dots_spearman']['abs_rho']:.4f} "
            f"max_mut_ov={cand_uniq['max_mutual_3px_overlap']['overlap']:.4f} "
            f"max_fwd_geol_ov={cand_uniq['max_forward_3px_overlap_geological']['overlap']:.4f}",
            flush=True,
        )
        uniqueness_attempts.append(
            {
                "arm": arm_key,
                "holdout_dti": pooled_eval_init["scores"][arm_key]["dti"],
                "gate_passed": cand_uniq["gate_passed"],
                "max_surface_spearman": cand_uniq["max_surface_spearman"],
                "max_dots_spearman": cand_uniq["max_dots_spearman"],
                "max_mutual_3px_overlap": cand_uniq["max_mutual_3px_overlap"],
                "max_forward_3px_overlap_geological": cand_uniq["max_forward_3px_overlap_geological"],
                "duplicates": cand_uniq["duplicates"],
            }
        )
        if cand_uniq["gate_passed"]:
            chosen_exp = arm_key
            final_dots = cand_dots
            geom_diag = cand_geom
            uniqueness_report = cand_uniq
            break
        print(
            f"  [LANE GATE] `{arm_key}` logged as duplicate collision against "
            f"{[d['name'] for d in cand_uniq['duplicates'][:2]]}; advancing to next pre-registered arm...",
            flush=True,
        )

    if chosen_exp is None or final_dots is None or uniqueness_report is None or geom_diag is None:
        (STAGE_CACHE / "uniqueness_attempts.json").write_text(json.dumps(uniqueness_attempts, indent=2) + "\n")
        raise RuntimeError(f"All 3 pre-registered arms collided on uniqueness: {uniqueness_attempts}")

    best_exp = chosen_exp
    pooled_eval = pooled_eval_init

    bundle = submission_writer.write_validated_submission_bundle(
        final_dots,
        template_path=paths.TEMPLATE,
        footprint=foot,
        catalogue=cat,
        out_dir=paths.DOCS / "downloads",
        family="27gemsdoe",
        slug=slug,
        date_tag=DATE_TAG,
        note_summary=note_desc,
        hypothesis_id=hyp_label,
    )

    best_score_rec = pooled_eval["scores"][best_exp]
    if best_exp == pooled_eval.get("candidate"):
        vs_leg = pooled_eval["paired_differences"]["ctrl_legacy_boof"]
        vs_leg_m = pooled_eval["paired_differences"]["ctrl_legacy_matched_37654"]
        vs_rnd = pooled_eval["paired_differences"]["ctrl_random_37654"]
    else:
        def _diff_summary(ctrl_key: str) -> dict[str, object]:
            c_rec = pooled_eval["scores"][ctrl_key]
            d = float(best_score_rec["dti"] - c_rec["dti"])
            # Conservative outer 95% interval from marginal block-bootstrap CIs
            hw_a = 0.5 * (best_score_rec["ci95"][1] - best_score_rec["ci95"][0])
            hw_b = 0.5 * (c_rec["ci95"][1] - c_rec["ci95"][0])
            hw = float(np.hypot(hw_a, hw_b))
            f_won = sum(
                1 for fa, fb in zip(best_score_rec["per_fold"], c_rec["per_fold"]) if fa["dti"] > fb["dti"]
            )
            return {
                "delta_dti": d,
                "ci95": [d - hw, d + hw],
                "folds_improved": f"{f_won}/4",
            }
        vs_leg = _diff_summary("ctrl_legacy_boof")
        vs_leg_m = _diff_summary("ctrl_legacy_matched_37654")
        vs_rnd = _diff_summary("ctrl_random_37654")

    promote_ok = (
        canary_report["gate_passed"]
        and uniqueness_report["gate_passed"]
        and bundle["validator_output"]["all_hard_checks_passed"]
        and vs_leg["delta_dti"] > 0.0
        and vs_leg["ci95"][0] > 0.0
        and vs_rnd["delta_dti"] > 0.0
        and vs_rnd["ci95"][0] > 0.0
    )
    verdict = "promote" if promote_ok else "negative"

    run_card = {
        "hypothesis": (
            f"{hyp_label}: Shallow magnetic vertical-continuation residual (TMI - TMI_up150) + "
            "seamless piedmont break-in-slope curvature + verified GDR #1391 2m temperature-probe "
            "(F2mDAB) & paleo-sinter self-seal synthesis + Voronoi-jackknifed crack-tip transfer, "
            "emitted via priority-ordered curvilinear ridge-NMS Poisson-disk (d=2.80 px, B=2.0 px "
            "catalogue-flank exclusion, N=37,654 binary dots)."
        ),
        "mechanism": (
            "Combines <150 m shallow magnetic susceptibility steps (Jacobsen upward-continuation "
            "difference), down-slope alluvial-fan piedmont curvature across 100% of the footprint "
            "(solving the 24.6% 1 m LiDAR gap), survey-debiased GDR #1391 thermal upflow & sinter "
            "seals, and Voronoi-jackknifed off-tip accommodation envelopes; priority curvilinear "
            "ridge-Poisson dotting preserves optimal 1D kernel reach while stripping the 0-200 m "
            "cartographic digitization-jitter shadow."
        ),
        "mimic_process": (
            "Pleistocene Lake Lahontan (~1332 m) contour-parallel wave-cut paleoshoreline benches, "
            "fluvial terrace risers, cold agricultural irrigation wells, and pre-Quaternary "
            "mountain-interior lithologic contacts."
        ),
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": eh.VERSION,
            "dti": round(best_score_rec["dti"], 6),
            "ci": [round(best_score_rec["ci95"][0], 6), round(best_score_rec["ci95"][1], 6)],
            "withheld_positive_pixels": best_score_rec["withheld_positive_pixels"],
            "delta_vs_legacy_boof": round(vs_leg["delta_dti"], 6),
            "delta_vs_legacy_boof_ci95": [round(vs_leg["ci95"][0], 6), round(vs_leg["ci95"][1], 6)],
            "delta_vs_legacy_matched_geometry": round(vs_leg_m["delta_dti"], 6),
            "delta_vs_legacy_matched_geometry_ci95": [
                round(vs_leg_m["ci95"][0], 6),
                round(vs_leg_m["ci95"][1], 6),
            ],
            "delta_vs_random_37654": round(vs_rnd["delta_dti"], 6),
            "folds_improved_vs_legacy": vs_leg["folds_improved"],
        },
        "leakage_canary": {
            "gate_passed": canary_report["gate_passed"],
            "features_tested": canary_report["n_features_tested"],
            "max_feature": canary_report["max_feature"],
            "max_symmetric_auc": canary_report["max_symmetric_auc"],
            "threshold": canary_report["auc_limit"],
        },
        "registry_correlation_overlap": {
            "gate_passed": uniqueness_report["gate_passed"],
            "rasters_scanned": uniqueness_report["rasters_scanned"],
            "max_preplacement_surface_abs_spearman": uniqueness_report["max_surface_spearman"]["abs_rho"],
            "max_preplacement_surface_peer": uniqueness_report["max_surface_spearman"]["raster"],
            "max_final_dots_abs_spearman": uniqueness_report["max_dots_spearman"]["abs_rho"],
            "max_final_dots_peer": uniqueness_report["max_dots_spearman"]["raster"],
            "max_mutual_3px_dot_overlap": uniqueness_report["max_mutual_3px_overlap"]["overlap"],
            "max_forward_geological_3px_dot_overlap": uniqueness_report[
                "max_forward_3px_overlap_geological"
            ]["overlap"],
            "overlap_with_gemsdoe32_02778": uniqueness_report["focus_reference_comparisons"]
            .get("gemsdoe32_02778_h33_2_b2", {})
            .get("forward_overlap_3px"),
            "overlap_with_gemsdoe70_02478": uniqueness_report["focus_reference_comparisons"]
            .get("gemsdoe70_02478_p5_submod", {})
            .get("forward_overlap_3px"),
        },
        "raster_sha256": bundle["raster_sha256"],
        "companion_nan_raster_sha256": bundle["nan_raster_sha256"],
        "scored_content_id": bundle["scored_content_id"],
        "validator_output": {
            **bundle["validator_output"],
            "ok_to_download_and_submit": bool(promote_ok),
        },
        "submission_name": bundle["submission_name"],
        "companion_nan_submission_name": bundle["nan_companion_name"],
        "note": bundle["note"],
        "experiments_run": 3,
        "experiment_budget_limit": 3,
        "finalize_runtime_seconds": round(time.time() - t0, 1),
        "holdout_runtime_seconds": stage_a.get("holdout_runtime_seconds"),
        "peak_rss_mib": round(rss_mib(), 1),
        "verdict": verdict,
    }

    full_evidence = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "run_card": run_card,
        "geometry_diagnostics": geom_diag,
        "leakage_canary_report": canary_report,
        "pooled_holdout_evaluation": pooled_eval,
        "uniqueness_attempts": uniqueness_attempts,
        "uniqueness_scan_report": uniqueness_report,
        "submission_bundle": bundle,
    }

    paths.EVIDENCE.mkdir(parents=True, exist_ok=True)
    (paths.EVIDENCE / "run_card.json").write_text(json.dumps(run_card, indent=2) + "\n")
    (paths.EVIDENCE / "session6_h29_holdout_and_gates.json").write_text(
        json.dumps(full_evidence, indent=2) + "\n"
    )
    print(f"[{time.time()-t0:.1f}s] COMPLETE! Verdict={verdict}, peak RSS={rss_mib():.0f} MiB.")
    print(json.dumps(run_card, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=("all", "holdout", "finalize"), default="all")
    args = ap.parse_args()
    t0 = time.time()
    if args.stage in ("all", "holdout"):
        run_holdout_stage(t0)
    if args.stage in ("all", "finalize"):
        run_finalize_stage(t0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
