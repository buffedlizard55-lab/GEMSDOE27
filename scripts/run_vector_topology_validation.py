#!/usr/bin/env python3
"""Confirmatory run for Addendum B: three-tier vector holdout (`component`, `FID_trace`, `NAME_zone`)
and H27-5 kinematic attribute typing on fresh seeds 120-129."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import grid, holdout, links, metric, paths, vector_graph  # noqa: E402
from gems27.candidates import RULE, SPACING, build_set, dedupe_mutual, evidence_score  # noqa: E402
from gems27.graph import build_graph  # noqa: E402


def eval_dots(dots_crop: np.ndarray, g: np.ndarray, active: np.ndarray, k_pt: np.ndarray) -> tuple[float, float, int]:
    a = dots_crop & active
    if not a.any() or not g.any():
        return 0.0, float((1.0 - k_pt[a]).sum()) if a.any() else 0.0, int(a.sum())
    c = metric.kernel_from_distance(distance_transform_edt(~a)[g])
    return float(c.sum()), float((1.0 - k_pt[a]).sum()), int(a.sum())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="120-129")
    ap.add_argument("--out", default=str(paths.EVIDENCE / "vector_topology_validation.json"))
    args = ap.parse_args()
    a, _, b = args.seeds.partition("-")
    seeds = list(range(int(a), int(b) + 1)) if b else [int(a)]

    t0 = time.time()
    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    fold = holdout.make_quadrant_folds(foot)
    va = vector_graph.load_vector_attribution(labels, foot)
    full_set = build_set(labels, foot, np.zeros_like(labels, bool))
    full_vec_summary = vector_graph.component_vector_summary(full_set["fg"], va, full_set["links"])

    tier_defs = [
        ("component", None),
        ("FID_trace", va.pix_fid_idx),
        ("NAME_zone", va.pix_name_id),
    ]
    tiers_out = {}

    for tier_name, grp_map in tier_defs:
        variant_names = [
            "all",
            "z>=3 dedup",
            "z>=3 inter-FID",
            "z>=3 inter-FID + kinematic_compat (H27-5a)",
            "z>=3 inter-FID + same_name + kinematic_compat (H27-5b)",
            "z>=3 intra-FID",
            "ctrl",
        ]
        totals = {k: {"dTP": 0.0, "dFP": 0.0, "dots": 0, "links": 0} for k in variant_names}
        per_fold_tp_fp = {fn: {k: [0.0, 0.0] for k in variant_names} for fn in holdout.FOLD_NAMES}

        for seed in seeds:
            for f in range(4):
                fn = holdout.FOLD_NAMES[f]
                fm = fold == f
                if grp_map is None:
                    sp = holdout.make_split(labels, fold, f, seed)
                    hidden, known = sp.hidden, sp.known
                else:
                    hidden, known = vector_graph.make_group_split(labels, fold, grp_map, f, seed)
                sl = holdout.crop(None, fm)
                fg = build_graph(known, with_edges=False)
                hid, kn, fmc = hidden[sl], (known & fm)[sl], fm[sl]
                g = hid & fmc & ~kn
                active = fmc & ~kn
                k_pt = metric.kernel_from_distance(distance_transform_edt(~g)) if g.any() else np.zeros_like(g, float)

                L = links.generate_links(fg, region=fm, **RULE)
                z = evidence_score(L)
                Ld = vector_graph.annotate_links(dedupe_mutual(L[z >= 3]), va)

                sub_map = {
                    "all": L,
                    "z>=3 dedup": Ld,
                    "z>=3 inter-FID": Ld[~Ld.same_fid] if not Ld.empty else Ld,
                    "z>=3 inter-FID + kinematic_compat (H27-5a)": (
                        Ld[~Ld.same_fid & Ld.kinematic_compat] if not Ld.empty else Ld
                    ),
                    "z>=3 inter-FID + same_name + kinematic_compat (H27-5b)": (
                        Ld[~Ld.same_fid & Ld.same_name & Ld.kinematic_compat] if not Ld.empty else Ld
                    ),
                    "z>=3 intra-FID": Ld[Ld.same_fid] if not Ld.empty else Ld,
                }
                for vname, sub in sub_map.items():
                    dots = links.rasterize_links(sub, labels.shape, SPACING)[sl] & active
                    tp, fp, n_dots = eval_dots(dots, g, active, k_pt)
                    totals[vname]["dTP"] += tp
                    totals[vname]["dFP"] += fp
                    totals[vname]["dots"] += n_dots
                    totals[vname]["links"] += int(len(sub))
                    per_fold_tp_fp[fn][vname][0] += tp
                    per_fold_tp_fp[fn][vname][1] += fp

                for rot in (90.0, -90.0):
                    Lc = links.generate_links(fg, region=fm, rotate_deg=rot, **RULE)
                    dots = links.rasterize_links(Lc, labels.shape, SPACING)[sl] & active
                    tp, fp, n_dots = eval_dots(dots, g, active, k_pt)
                    totals["ctrl"]["dTP"] += tp
                    totals["ctrl"]["dFP"] += fp
                    totals["ctrl"]["dots"] += n_dots
                    totals["ctrl"]["links"] += int(len(Lc))
                    per_fold_tp_fp[fn]["ctrl"][0] += tp
                    per_fold_tp_fp[fn]["ctrl"][1] += fp

        pooled_eff = {
            k: (totals[k]["dTP"] / totals[k]["dFP"] if totals[k]["dFP"] > 0 else 0.0)
            for k in variant_names
        }
        per_fold_eff = {
            fn: {
                k: (per_fold_tp_fp[fn][k][0] / per_fold_tp_fp[fn][k][1] if per_fold_tp_fp[fn][k][1] > 0 else 0.0)
                for k in variant_names
            }
            for fn in holdout.FOLD_NAMES
        }
        tiers_out[tier_name] = {
            "efficiency_pooled": pooled_eff,
            "enrichment_z3_over_ctrl": (
                pooled_eff["z>=3 dedup"] / pooled_eff["ctrl"] if pooled_eff["ctrl"] > 0 else None
            ),
            "dots_per_seed": {k: totals[k]["dots"] / len(seeds) for k in variant_names},
            "links_per_seed": {k: totals[k]["links"] / len(seeds) for k in variant_names},
            "per_fold_efficiency": per_fold_eff,
        }
        print(
            f"tier {tier_name:10s}: z3_dedup={pooled_eff['z>=3 dedup']:.4f} "
            f"H27-5a={pooled_eff['z>=3 inter-FID + kinematic_compat (H27-5a)']:.4f} "
            f"H27-5b={pooled_eff['z>=3 inter-FID + same_name + kinematic_compat (H27-5b)']:.4f} "
            f"ctrl={pooled_eff['ctrl']:.4f}  t={time.time()-t0:.0f}s",
            flush=True,
        )

    fid_eff = tiers_out["FID_trace"]["efficiency_pooled"]
    m_030 = metric.inclusion_threshold(0.30)
    gate_b = {
        "g1_fid_trace_z3_gt_m030_and_ge_2x_ctrl": bool(
            fid_eff["z>=3 dedup"] > m_030 and fid_eff["z>=3 dedup"] >= 2.0 * fid_eff["ctrl"]
        ),
        "g2_h27_5_kinematic_typing_improves_on_fid_trace": bool(
            fid_eff["z>=3 inter-FID + kinematic_compat (H27-5a)"] > fid_eff["z>=3 dedup"]
            and fid_eff["z>=3 inter-FID + same_name + kinematic_compat (H27-5b)"] >= 0.10
        ),
    }
    out = {
        "preregistration": "knowledge/03_preregistration_topology_gate.md#addendum-b",
        "seeds": seeds,
        "vector_catalogue_summary": full_vec_summary,
        "tiers": tiers_out,
        "inclusion_threshold": {"dti_0.2477": metric.inclusion_threshold(0.2477), "dti_0.30": m_030},
        "gate_addendum_b": gate_b,
        "gate_passed": bool(all(gate_b.values())),
        "seconds": time.time() - t0,
    }
    Path(args.out).write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({"gate_addendum_b": gate_b, "gate_passed": out["gate_passed"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
