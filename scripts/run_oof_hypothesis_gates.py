#!/usr/bin/env python3
"""Confirmatory run for Addendum C: honest out-of-fold spatial-CV detector ($B_{oof}$)
gating H27-1 (T-v2 topology gap-closure), H27-4 (tip-shadow pruning), and H27-3 (emission-graph
coherence filter) on fresh seeds 130-139."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import grid, holdout, links, metric, oof_detector, paths  # noqa: E402
from gems27.candidates import RULE, SPACING, dedupe_mutual, evidence_score  # noqa: E402
from gems27.graph import build_graph  # noqa: E402


def eval_set(pred: np.ndarray, g: np.ndarray, active: np.ndarray, k_pt: np.ndarray) -> tuple[float, float, float, int]:
    p = pred & active
    n_g = int(g.sum())
    if not p.any() or n_g == 0:
        fp = float((1.0 - k_pt[p]).sum()) if p.any() else 0.0
        return 0.0, fp, 0.0, int(p.sum())
    tp = float(metric.kernel_from_distance(distance_transform_edt(~p)[g]).sum())
    fp = float((1.0 - k_pt[p]).sum())
    dti = tp / (tp + 0.2 * fp + 0.8 * (n_g - tp) + 1e-7)
    return tp, fp, dti, int(p.sum())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="130-139")
    ap.add_argument("--out", default=str(paths.EVIDENCE / "oof_hypothesis_gates.json"))
    args = ap.parse_args()
    a, _, b = args.seeds.partition("-")
    seeds = list(range(int(a), int(b) + 1)) if b else [int(a)]

    t0 = time.time()
    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    fold = holdout.make_quadrant_folds(foot)

    print("Training 4-fold spatial-CV HistGradientBoostingClassifier (600 m buffer)...", flush=True)
    oof_prob = oof_detector.fit_predict_oof_probabilities(foot, labels, fold)
    ridge_all = oof_detector.ridge_nms(oof_prob, foot, sigma=1.0)
    print(f"OOF probabilities & ridges computed in {time.time()-t0:.1f}s (total ridges={int(ridge_all.sum()):,})", flush=True)

    variants = [
        "base_oof",
        "plus_T_v2",
        "prune_r1_100m",
        "prune_r2_200m",
        "prune_r3_300m",
        "plus_T_v2_and_prune_r1",
        "plus_T_v2_and_prune_r2",
        "coherence_h27_3",
    ]
    cells = []
    for seed in seeds:
        for f in range(4):
            sp = holdout.make_split(labels, fold, f, seed)
            fm = sp.fold_mask
            sl = holdout.crop(None, fm)
            hid, kn, fmc = sp.hidden[sl], (sp.known & fm)[sl], fm[sl]
            g = hid & fmc & ~kn
            active = fmc & ~kn
            k_pt = metric.kernel_from_distance(distance_transform_edt(~g)) if g.any() else np.zeros_like(g, float)

            base_c = oof_detector.build_oof_dotted_base(
                oof_prob[sl], ridge_all[sl], fmc, kn, budget_frac=oof_detector.PRE_THIN_FRAC, thin_d=1.5
            ) & active
            d_base = distance_transform_edt(~base_c) if base_c.any() else np.full(g.shape, np.inf)
            d_kn = distance_transform_edt(~kn) if kn.any() else np.full(g.shape, np.inf)

            # H27-1 / T-v2 on OOF base
            fg = build_graph(sp.known, with_edges=False)
            L = links.generate_links(fg, region=fm, **RULE)
            z = evidence_score(L)
            Ld = dedupe_mutual(L[z >= 3])
            t_raw = links.rasterize_links(Ld, labels.shape, SPACING)[sl] & active
            t_dots = t_raw & (d_base >= metric.RADIUS_PX)
            plus_tv2 = base_c | t_dots

            # H27-4 tip-shadow pruning (r = 1, 2, 3 px from known catalogue)
            p_r1 = base_c & (d_kn > 1.0)
            p_r2 = base_c & (d_kn > 2.0)
            p_r3 = base_c & (d_kn >= 3.0)
            d_p1 = distance_transform_edt(~p_r1) if p_r1.any() else np.full(g.shape, np.inf)
            d_p2 = distance_transform_edt(~p_r2) if p_r2.any() else np.full(g.shape, np.inf)
            plus_tv2_p1 = p_r1 | (t_raw & (d_p1 >= metric.RADIUS_PX))
            plus_tv2_p2 = p_r2 | (t_raw & (d_p2 >= metric.RADIUS_PX))

            # H27-3 emission-graph coherence filter (drop isolated dots with no neighbour within 6 px)
            coh = oof_detector.filter_isolated_dots(base_c, radius_px=6.0)

            v_sets = {
                "base_oof": base_c,
                "plus_T_v2": plus_tv2,
                "prune_r1_100m": p_r1,
                "prune_r2_200m": p_r2,
                "prune_r3_300m": p_r3,
                "plus_T_v2_and_prune_r1": plus_tv2_p1,
                "plus_T_v2_and_prune_r2": plus_tv2_p2,
                "coherence_h27_3": coh,
            }
            row = {"seed": seed, "fold": sp.name, "n_truth": int(g.sum())}
            for vn, s_mask in v_sets.items():
                tp, fp, dti, n_px = eval_set(s_mask, g, active, k_pt)
                row[vn] = {"tp": tp, "fp": fp, "dti": dti, "dots": n_px}
            cells.append(row)
        print(
            f"seed {seed} done (t={time.time()-t0:.0f}s): "
            f"base={np.mean([c['base_oof']['dti'] for c in cells if c['seed']==seed]):.4f} "
            f"+Tv2={np.mean([c['plus_T_v2']['dti'] for c in cells if c['seed']==seed]):.4f} "
            f"prune300m={np.mean([c['prune_r3_300m']['dti'] for c in cells if c['seed']==seed]):.4f} "
            f"coh={np.mean([c['coherence_h27_3']['dti'] for c in cells if c['seed']==seed]):.4f}",
            flush=True,
        )

    base_mean_dti = float(np.mean([c["base_oof"]["dti"] for c in cells]))
    m_oof = metric.inclusion_threshold(base_mean_dti)
    m_live = metric.inclusion_threshold(0.2477)

    summary = {}
    for vn in variants[1:]:
        gains_by_seed = [
            float(np.mean([c[vn]["dti"] - c["base_oof"]["dti"] for c in cells if c["seed"] == s]))
            for s in seeds
        ]
        gains_by_fold = {
            fn: float(np.mean([c[vn]["dti"] - c["base_oof"]["dti"] for c in cells if c["fold"] == fn]))
            for fn in holdout.FOLD_NAMES
        }
        dtp = sum(c[vn]["tp"] - c["base_oof"]["tp"] for c in cells)
        dfp = sum(c[vn]["fp"] - c["base_oof"]["fp"] for c in cells)
        d_dots = sum(c[vn]["dots"] - c["base_oof"]["dots"] for c in cells) / len(seeds)
        # For additions (dtp>=0, dfp>0), marginal_eff = dtp/dfp; for removals (dtp<=0, dfp<0), removed_eff = (-dtp)/(-dfp)
        eff = (dtp / dfp) if dfp > 0 else ((-dtp) / (-dfp) if dfp < 0 else 0.0)
        summary[vn] = {
            "mean_dti_gain": float(np.mean(gains_by_seed)),
            "min_seed_gain": float(np.min(gains_by_seed)),
            "max_seed_gain": float(np.max(gains_by_seed)),
            "fold_gains": gains_by_fold,
            "folds_improved": int(sum(v > 0 for v in gains_by_fold.values())),
            "delta_dots_per_seed": float(d_dots),
            "marginal_or_removed_efficiency": float(eff),
        }

    gate_c = {
        "h27_1_tv2_on_oof_passed": bool(
            summary["plus_T_v2"]["mean_dti_gain"] > 0.001
            and summary["plus_T_v2"]["folds_improved"] >= 3
        ),
        "h27_4_prune_300m_on_oof_passed": bool(
            summary["prune_r3_300m"]["marginal_or_removed_efficiency"] < m_oof
            and summary["prune_r3_300m"]["mean_dti_gain"] > 0.0005
            and summary["prune_r3_300m"]["folds_improved"] >= 3
        ),
        "h27_4_prune_100m_on_oof_passed": bool(
            summary["prune_r1_100m"]["marginal_or_removed_efficiency"] < m_oof
            and summary["prune_r1_100m"]["mean_dti_gain"] > 0.0005
            and summary["prune_r1_100m"]["folds_improved"] >= 3
        ),
        "h27_3_coherence_on_oof_passed": bool(
            summary["coherence_h27_3"]["marginal_or_removed_efficiency"] < m_oof
            and summary["coherence_h27_3"]["mean_dti_gain"] > 0.0005
            and summary["coherence_h27_3"]["folds_improved"] >= 3
        ),
    }

    out = {
        "preregistration": "knowledge/03_preregistration_topology_gate.md#addendum-c",
        "seeds": seeds,
        "base_oof_mean_dti": base_mean_dti,
        "base_oof_dots_per_seed": float(np.mean([sum(c["base_oof"]["dots"] for c in cells if c["seed"] == s) for s in seeds])),
        "inclusion_threshold_oof": m_oof,
        "inclusion_threshold_live_0_2477": m_live,
        "variants": summary,
        "gate_addendum_c": gate_c,
        "seconds": time.time() - t0,
    }
    Path(args.out).write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: out[k] for k in ("base_oof_mean_dti", "inclusion_threshold_oof", "inclusion_threshold_live_0_2477", "variants", "gate_addendum_c")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
