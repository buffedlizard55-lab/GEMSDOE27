#!/usr/bin/env python3
"""Confirmatory run for Addendum D (fresh seeds 140-149), pre-registered in
`knowledge/03_preregistration_topology_gate.md` and committed BEFORE this script was run.

Stage A (D1/D2, PR-AUC screen): retrain the Addendum-C out-of-fold detector on the 32-band prepared
matrix plus each registered band group (`rad`, `sgmc`, `thermal`, `dir`, `all`) with identical
hyper-parameters, buffer, negative subsample and seeds, and measure out-of-fold PR-AUC against the
catalogue. Regression check: the `base` arm must reproduce Session 3's numbers.

Stage B (seeds 140-149, 40 cells): paired DTI for every arm that passed the PR-AUC criterion, plus
D3 (rank the T-v2 links by graph-connectivity value, `src/gems27/graph_value.py`) and D4 (overlapping
en-echelon step-over links, `src/gems27/newinfo.steppover_links`, with a perpendicular-strike control
of the same geometry).

Hidden truth is catalogue-internal in every cell; a pass is a reason to consider an arm, never a claim
about the leaderboard. Nothing is uploaded and no DrivenData host is contacted.

Usage: GEMS_DATA_DIR=/home/user/GEMSDOE27/data_cache .venv/bin/python scripts/run_addendum_d_gates.py
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import grid, graph_value, holdout, links, metric, newinfo, oof_detector, paths  # noqa: E402
from gems27.candidates import RULE, SPACING, dedupe_mutual, evidence_score  # noqa: E402
from gems27.graph import build_graph  # noqa: E402

AUG = paths.DATA / "prepared" / "features_aug.npy"
AUG_META = paths.DATA / "prepared" / "features_aug.json"
PR_AUC_MIN_GAIN = 0.005        # Addendum D, gate D1/D2 criterion 1
DTI_MIN_GAIN = 0.001           # Addendum D, gate D1/D2 criterion 2
BREAKEVEN_030 = 0.0638         # m(DTI = 0.30), from knowledge/03 Addendum B
ARMS = ("base", "rad", "sgmc", "thermal", "dir", "all")


def eval_set(pred: np.ndarray, g: np.ndarray, active: np.ndarray, k_pt: np.ndarray):
    """(credit TP, FP weight, DTI, n dots) - identical to Addendum C's `eval_set`."""
    p = pred & active
    n_g = int(g.sum())
    if not p.any() or n_g == 0:
        fp = float((1.0 - k_pt[p]).sum()) if p.any() else 0.0
        return 0.0, fp, 0.0, int(p.sum())
    tp = float(metric.kernel_from_distance(distance_transform_edt(~p)[g]).sum())
    fp = float((1.0 - k_pt[p]).sum())
    dti = tp / (tp + 0.2 * fp + 0.8 * (n_g - tp) + 1e-7)
    return tp, fp, dti, int(p.sum())


def pooled(rows: list[dict], key: str) -> dict:
    tp = sum(r[key]["tp"] for r in rows)
    fp = sum(r[key]["fp"] for r in rows)
    dti = [r[key]["dti"] for r in rows]
    return {"credit_TP": tp, "fp_weight": fp, "efficiency": tp / fp if fp else 0.0,
            "mean_dti": float(np.mean(dti)), "n_dots": sum(r[key]["dots"] for r in rows)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="140-149")
    ap.add_argument("--stage", default="AB")
    ap.add_argument("--arms", default=",".join(ARMS), help="comma-separated subset of Stage-A arms")
    ap.add_argument("--out", default=str(paths.EVIDENCE / "addendum_d_gates.json"))
    args = ap.parse_args()
    a, _, b = args.seeds.partition("-")
    seeds = list(range(int(a), int(b) + 1)) if b else [int(a)]
    t0 = time.time()

    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    fold = holdout.make_quadrant_folds(foot)
    aug_names = json.loads(AUG_META.read_text())["names"]
    aug = np.load(AUG, mmap_mode="r")
    prob_dir = paths.DATA / "prepared"
    out: dict = {"preregistration": "knowledge/03_preregistration_topology_gate.md#addendum-d",
                 "seeds": seeds, "thresholds": {"pr_auc_min_gain": PR_AUC_MIN_GAIN,
                                                "dti_min_gain": DTI_MIN_GAIN,
                                                "breakeven_m_0_30": BREAKEVEN_030},
                 "augmented_matrix": {"path": str(AUG), "sha256": json.loads(AUG_META.read_text())["sha256"],
                                      "n_bands": len(aug_names)}}

    # ------------------------------------------------------------------ Stage A: PR-AUC screen
    stage_a: dict[str, dict] = {}
    passed: list[str] = []
    if "A" in args.stage:
        arms_req = [x.strip() for x in args.arms.split(",") if x.strip()]
        if "base" not in arms_req:
            arms_req = ["base"] + arms_req
        for arm in arms_req:
            names = newinfo.variant_bands(arm, {})
            cols = [aug_names.index(n) for n in names]
            extra = aug[:, cols] if cols else None
            ts = time.time()
            prob = oof_detector.fit_predict_oof_probabilities(foot, labels, fold, extra=extra)
            ridge = oof_detector.ridge_nms(prob, foot, sigma=1.0)
            pr = oof_detector.oof_pr_auc(prob, labels, foot)
            np.save(prob_dir / f"oof_prob_d_{arm}.npy", prob)
            np.save(prob_dir / f"oof_ridge_d_{arm}.npy", ridge)
            stage_a[arm] = {"n_bands_added": len(names), "bands_added": names,
                            "oof_pr_auc": pr, "ridge_px": int(ridge.sum()),
                            "seconds": time.time() - ts}
            if arm != "base" and pr - stage_a["base"]["oof_pr_auc"] >= PR_AUC_MIN_GAIN:
                passed.append(arm)
                stage_a[arm]["pr_auc_criterion_1_passed"] = True
            elif arm != "base":
                stage_a[arm]["pr_auc_criterion_1_passed"] = False
            del prob, ridge, extra
            print(f"[A] {arm:<8} bands+{len(names):<3} PR-AUC={pr:.5f} ridges={stage_a[arm]['ridge_px']:,} "
                  f"({time.time()-ts:.0f}s, total {time.time()-t0:.0f}s)", flush=True)
            out["stage_a_pr_auc"] = stage_a
            out["arms_passing_pr_auc"] = passed
            Path(args.out).write_text(json.dumps(out, indent=2) + "\n")
        base_pr = stage_a["base"]["oof_pr_auc"]
        out["stage_a_summary"] = {
            "base_oof_pr_auc": base_pr,
            "gains": {k: v["oof_pr_auc"] - base_pr for k, v in stage_a.items() if k != "base"},
            "criterion_1_passing_arms": passed,
            "note": ("PR-AUC is measured strictly out-of-fold against catalogue pixels. It screens "
                     "detector quality only; the paired-DTI criterion is applied in Stage B."),
        }
        Path(args.out).write_text(json.dumps(out, indent=2) + "\n")

    # ------------------------------------------------------------------ Stage B: paired cells
    if "B" not in args.stage:
        print(json.dumps(out, indent=2))
        return 0
    if not passed and "A" in args.stage:
        print("[B] no arm passed the PR-AUC criterion; Stage B evaluates D3 and D4 on the base arm only.",
              flush=True)
    arms_b = ["base"] + passed
    probs = {arm: np.load(prob_dir / f"oof_prob_d_{arm}.npy", mmap_mode="r") for arm in arms_b}
    ridges = {arm: np.load(prob_dir / f"oof_ridge_d_{arm}.npy") for arm in arms_b}

    cells: list[dict] = []
    rng_global = np.random.default_rng(20260)
    for seed in seeds:
        for f in range(4):
            sp = holdout.make_split(labels, fold, f, seed)
            fm = sp.fold_mask
            sl = holdout.crop(None, fm)
            hid, kn, fmc = sp.hidden[sl], (sp.known & fm)[sl], fm[sl]
            g = hid & fmc & ~kn
            active = fmc & ~kn
            k_pt = metric.kernel_from_distance(distance_transform_edt(~g)) if g.any() else np.zeros_like(g, float)

            fg = build_graph(sp.known, with_edges=False)
            L = links.generate_links(fg, region=fm, **RULE)
            z = evidence_score(L)
            Ld = dedupe_mutual(L[z >= 3])

            # base emission + arm emissions (matched budget and geometry)
            dots = {}
            d_base = None
            for arm in arms_b:
                base_c = oof_detector.build_oof_dotted_base(
                    np.asarray(probs[arm])[sl], ridges[arm][sl], fmc, kn,
                    budget_frac=oof_detector.PRE_THIN_FRAC, thin_d=1.5) & active
                dots[arm] = base_c
                if arm == "base":
                    d_base = distance_transform_edt(~base_c) if base_c.any() else np.full(g.shape, np.inf)

            row = {"seed": seed, "fold": sp.name, "n_truth": int(g.sum())}
            for arm, m in dots.items():
                tp, fp, dti, n = eval_set(m, g, active, k_pt)
                row[arm] = {"tp": tp, "fp": fp, "dti": dti, "dots": n}
            # H27-1 reference: T-v2 dots on the base arm (recomputed for the record)
            t_raw = links.rasterize_links(Ld, labels.shape, SPACING)[sl] & active
            t_dots = t_raw & (d_base >= metric.RADIUS_PX)
            for nm, m in (("plus_T_v2_base", dots["base"] | t_dots),
                          ("T_v2_alone", t_dots)):
                tp, fp, dti, n = eval_set(m, g, active, k_pt)
                row[nm] = {"tp": tp, "fp": fp, "dti": dti, "dots": n}

            # ---- D3: rank the shipped T-v2 links by graph-connectivity value -------------------
            gv = graph_value.link_connectivity_values(fg, Ld) if len(Ld) else None
            if gv is not None and len(gv) >= 8:
                order = gv.connectivity_rank.to_numpy()          # 1 = largest |delta_P|
                half = len(gv) // 2
                top = Ld.iloc[order <= half]
                bot = Ld.iloc[order > len(gv) - half]
                # secondary (exploratory, disclosed): the signed direction and the continuous tie-break
                sgn = np.argsort(-gv.delta_P.to_numpy())
                sm2 = np.argsort(-gv.delta_second_moment_km2.to_numpy())
                sets = {"d3_top_half_by_delta_P": top, "d3_bottom_half_by_delta_P": bot,
                        "d3_all_T_v2": Ld, "d3_bridges_only": Ld.iloc[gv.bridge.to_numpy()],
                        "d3_top_half_by_signed_delta_P": Ld.iloc[sgn[:half]],
                        "d3_top_half_by_second_moment": Ld.iloc[sm2[:half]]}
                for i in range(5):
                    idx = rng_global.choice(len(gv), size=half, replace=False)
                    sets[f"d3_random_half_{i}"] = Ld.iloc[idx]
                for nm, sel in sets.items():
                    m = links.rasterize_links(sel, labels.shape, SPACING)[sl] & active
                    tp, fp, dti, n = eval_set(m, g, active, k_pt)
                    row[nm] = {"tp": tp, "fp": fp, "dti": dti, "dots": n, "links": int(len(sel))}
                row["d3_graph"] = {"n_links": int(len(gv)), "n_bridges": int(gv.bridge.sum()),
                                   "P_with_all_links": float(gv.P_with_all_links.iloc[0]),
                                   "largest_share_with_all_links": float(gv.largest_share_with_all_links.iloc[0]),
                                   "delta_P_range": [float(gv.delta_P.min()), float(gv.delta_P.max())],
                                   "median_merge_len_km": float(gv.merge_len_km.median())}

            # ---- D4: overlapping en-echelon step-overs (+ perpendicular control) ---------------
            so = newinfo.dedupe_pairs(newinfo.steppover_links(fg, region=fm))
            ctl = newinfo.dedupe_pairs(newinfo.steppover_links(fg, region=fm,
                                                               strike_window=(70.0, 110.0)))
            for nm, sel in (("d4_steppover", so), ("d4_steppover_control_perpendicular", ctl)):
                m = links.rasterize_links(sel, labels.shape, SPACING)[sl] & active if len(sel) else \
                    np.zeros(g.shape, bool)
                tp, fp, dti, n = eval_set(m, g, active, k_pt)
                row[nm] = {"tp": tp, "fp": fp, "dti": dti, "dots": n, "links": int(len(sel))}
            if len(so):
                m = links.rasterize_links(so, labels.shape, SPACING)[sl] & active
                tp, fp, dti, n = eval_set(dots["base"] | (m & (d_base >= metric.RADIUS_PX)),
                                          g, active, k_pt)
                row["d4_base_plus_steppover"] = {"tp": tp, "fp": fp, "dti": dti, "dots": n}
            else:
                row["d4_base_plus_steppover"] = dict(row["base"])
            row["d4_counts"] = {"steppover_links": int(len(so)), "control_links": int(len(ctl)),
                                "median_lateral_px": float(so.lateral_px.median()) if len(so) else None,
                                "median_overlap_px": float(so.overlap_px.median()) if len(so) else None,
                                "median_strike_diff_deg": float(so.strike_diff_deg.median()) if len(so) else None,
                                "median_gap_km": float(so.gap_km.median()) if len(so) else None}
            cells.append(row)
        print(f"[B] seed {seed} done (t={time.time()-t0:.0f}s) base="
              f"{np.mean([c['base']['dti'] for c in cells[-4:]]):.4f} "
              f"Tv2={'%.4f' % np.mean([c['plus_T_v2_base']['dti'] for c in cells[-4:]])} "
              f"d4links={np.mean([c['d4_counts']['steppover_links'] for c in cells[-4:]]):.0f}", flush=True)
        out["stage_b_cells"] = cells
        Path(args.out).write_text(json.dumps(out, indent=2) + "\n")

    # ------------------------------------------------------------------ verdicts
    per_fold = {}
    for arm in arms_b:
        if arm == "base":
            continue
        gains = {fn: float(np.mean([c[arm]["dti"] - c["base"]["dti"] for c in cells if c["fold"] == fn]))
                 for fn in sorted({c["fold"] for c in cells})}
        per_fold[arm] = gains
    out["stage_b_verdicts"] = {
        "base_mean_dti": float(np.mean([c["base"]["dti"] for c in cells])),
        "arms": {arm: {"mean_dti": float(np.mean([c[arm]["dti"] for c in cells])),
                       "mean_paired_gain_vs_base": float(np.mean([c[arm]["dti"] - c["base"]["dti"] for c in cells])),
                       "per_fold_gain": per_fold.get(arm, {}),
                       "folds_improved": int(sum(v > 0 for v in per_fold.get(arm, {}).values())),
                       "criterion_2_passed": bool(np.mean([c[arm]["dti"] - c["base"]["dti"] for c in cells]) > DTI_MIN_GAIN
                                                  and sum(v > 0 for v in per_fold.get(arm, {}).values()) >= 3)}
                 for arm in arms_b if arm != "base"},
        "d3": _d3_verdict(cells),
        "d4": _d4_verdict(cells),
        "h27_1_reference": {
            "mean_paired_gain_vs_base": float(np.mean([c["plus_T_v2_base"]["dti"] - c["base"]["dti"] for c in cells])),
            "T_v2_alone_pooled": pooled(cells, "T_v2_alone"),
        },
        "seconds": time.time() - t0,
    }
    Path(args.out).write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "stage_b_cells"}, indent=2))
    return 0


def _d3_verdict(cells: list[dict]) -> dict:
    top = pooled([c for c in cells if "d3_top_half_by_delta_P" in c], "d3_top_half_by_delta_P")
    bot = pooled([c for c in cells if "d3_bottom_half_by_delta_P" in c], "d3_bottom_half_by_delta_P")
    allv = pooled([c for c in cells if "d3_all_T_v2" in c], "d3_all_T_v2")
    br = pooled([c for c in cells if "d3_bridges_only" in c], "d3_bridges_only")
    sgn = pooled([c for c in cells if "d3_top_half_by_signed_delta_P" in c], "d3_top_half_by_signed_delta_P")
    sm2 = pooled([c for c in cells if "d3_top_half_by_second_moment" in c], "d3_top_half_by_second_moment")
    rnd = [pooled([c for c in cells if f"d3_random_half_{i}" in c], f"d3_random_half_{i}") for i in range(5)]
    rnd_eff = sorted(r["efficiency"] for r in rnd)
    p95 = rnd_eff[-1] if rnd_eff else 0.0
    return {"top_half_by_abs_delta_P": top, "bottom_half_by_abs_delta_P": bot, "all_T_v2": allv,
            "bridges_only": br, "random_halves": rnd,
            "top_half_by_signed_delta_P_exploratory": sgn,
            "top_half_by_second_moment_exploratory": sm2,
            "exploratory_note": ("the signed-dP and second-moment rankings were added as disclosed "
                                 "exploratory neighbours AFTER |dP| was found to be quantised to "
                                 "{-1,0,+1} x P/n_ge; the registered gate is the |dP| one and it is "
                                 "the one that decides"),
            "ratio_top_over_all": top["efficiency"] / allv["efficiency"] if allv["efficiency"] else None,
            "random_95th_percentile_efficiency": p95,
            "gate_passed": bool(top["efficiency"] >= 1.15 * allv["efficiency"] and top["efficiency"] > p95),
            "note": ("Pooled efficiency = credit gained / false-positive weight, set added to an empty "
                     "base (the Addendum-B definition). Hidden truth is catalogue-internal.")}


def _d4_verdict(cells: list[dict]) -> dict:
    so = pooled(cells, "d4_steppover")
    ctl = pooled(cells, "d4_steppover_control_perpendicular")
    add = pooled(cells, "d4_base_plus_steppover")
    base = pooled(cells, "base")
    gains = {fn: float(np.mean([c["d4_base_plus_steppover"]["dti"] - c["base"]["dti"]
                                for c in cells if c["fold"] == fn]))
             for fn in sorted({c["fold"] for c in cells})}
    return {"steppover_alone": so, "perpendicular_control_alone": ctl,
            "enrichment_vs_control": so["efficiency"] / ctl["efficiency"] if ctl["efficiency"] else None,
            "above_breakeven_m_0_30": bool(so["efficiency"] >= BREAKEVEN_030),
            "base_plus_steppover": add, "base": base,
            "mean_paired_gain_vs_base": float(np.mean([c["d4_base_plus_steppover"]["dti"] - c["base"]["dti"]
                                                       for c in cells])),
            "per_fold_gain": gains, "folds_improved": int(sum(v > 0 for v in gains.values())),
            "counts": {k: float(np.mean([c["d4_counts"][k] for c in cells if c["d4_counts"][k] is not None]))
                       if any(c["d4_counts"][k] is not None for c in cells) else None
                       for k in ("steppover_links", "control_links", "median_lateral_px",
                                 "median_overlap_px", "median_strike_diff_deg", "median_gap_km")},
            "gate_passed": bool(so["efficiency"] >= 2.0 * ctl["efficiency"]
                                and so["efficiency"] >= BREAKEVEN_030
                                and np.mean([c["d4_base_plus_steppover"]["dti"] - c["base"]["dti"]
                                             for c in cells]) > DTI_MIN_GAIN
                                and sum(v > 0 for v in gains.values()) >= 3)}


if __name__ == "__main__":
    raise SystemExit(main())
