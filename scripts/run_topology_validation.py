#!/usr/bin/env python3
"""Confirmatory validation of the topology gap-closure class T-v1 (see knowledge/03_preregistration_topology_gate.md).

Usage: python scripts/run_topology_validation.py [--seeds 100-109] [--out evidence/topology_validation.json]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import grid, holdout, links, metric, paths  # noqa: E402
from gems27.graph import build_graph  # noqa: E402

RULE = dict(cone_deg=30.0, rmin=10.0, rmax=40.0)
SPACING = 3
CONTROLS = (90.0, -90.0)


def parse_seeds(s: str) -> list[int]:
    if "-" in s:
        a, b = s.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in s.split(",")]


def load_base(foot):
    with rasterio.open(paths.DOTTED_0_2477) as s:
        return np.nan_to_num(s.read(1)) > 0


def cell(labels, foot, fold, base, fold_id, seed):
    sp = holdout.make_split(labels, fold, fold_id, seed)
    fm = sp.fold_mask
    sl = holdout.crop(None, fm)
    fg = build_graph(sp.known, with_edges=False)
    hid, kn, fmc = sp.hidden[sl], (sp.known & fm)[sl], fm[sl]
    base_c = (base & fm)[sl]
    d_truth = distance_transform_edt(~hid)
    kern = metric.kernel_from_distance(d_truth)
    res = {"seed": seed, "fold": sp.name, "n_hidden_px": int(hid.sum())}
    link_rows = []
    for name, rot in (("fwd", 0.0), ("ctrlA", CONTROLS[0]), ("ctrlB", CONTROLS[1])):
        L = links.generate_links(fg, rotate_deg=rot, region=fm, **RULE)
        dots_full = links.rasterize_links(L, labels.shape, SPACING)
        dots = dots_full[sl] & fmc & ~kn
        # redundancy with the base: drop dots closer than 3 px to a base dot
        d_base = distance_transform_edt(~base_c) if base_c.any() else np.full(base_c.shape, np.inf)
        nonred = dots & (d_base >= metric.RADIUS_PX)
        empty = np.zeros_like(dots)
        m_alone = metric.marginal_gain(empty, dots, hid, valid=fmc, known=kn)
        m_nonred = metric.marginal_gain(base_c, nonred, hid, valid=fmc, known=kn)
        res[name] = {
            "links": int(len(L)), "dots": int(dots.sum()), "dots_nonredundant": int(nonred.sum()),
            "dTP_alone": m_alone["dTP"], "dFP_alone": m_alone["dFP"],
            "dTP_vs_base": m_nonred["dTP"], "dFP_vs_base": m_nonred["dFP"],
            "dti_base": m_nonred["dti_base"], "dti_union": m_nonred["dti_union"],
        }
        if name == "fwd" and len(L):
            rr, cc = np.nonzero(dots_full[sl] & fmc)
            # per-link dot-level hit weight (for ranking diagnostics)
            for r in L.itertuples(index=False):
                one = links.rasterize_links(pd.DataFrame([r._asdict()]), labels.shape, SPACING)[sl] & fmc & ~kn
                if one.any():
                    link_rows.append({**r._asdict(), "seed": seed, "fold": sp.name,
                                      "y": float(kern[one].mean()), "n_dots": int(one.sum())})
    return res, link_rows


def pooled(rows, name, key_tp, key_fp):
    tp = sum(r[name][key_tp] for r in rows)
    fp = sum(r[name][key_fp] for r in rows)
    return tp, fp, (tp / fp if fp > 0 else float("nan"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="100-109")
    ap.add_argument("--out", default=str(paths.EVIDENCE / "topology_validation.json"))
    ap.add_argument("--links-csv", default=str(paths.EVIDENCE / "_scratch" / "topology_links_by_seed.csv"))
    args = ap.parse_args()
    seeds = parse_seeds(args.seeds)
    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    fold = holdout.make_quadrant_folds(foot)
    base = load_base(foot)
    t0 = time.time()
    rows, all_links = [], []
    for seed in seeds:
        for f in range(4):
            r, lr = cell(labels, foot, fold, base, f, seed)
            rows.append(r)
            all_links.extend(lr)
            print(f"seed {seed} fold {r['fold']:<17s} fwd dots {r['fwd']['dots']:5d} "
                  f"eff {r['fwd']['dTP_alone'] / max(r['fwd']['dFP_alone'], 1e-9):.3f} "
                  f"ctrl {(r['ctrlA']['dTP_alone'] + r['ctrlB']['dTP_alone']) / max(r['ctrlA']['dFP_alone'] + r['ctrlB']['dFP_alone'], 1e-9):.3f} "
                  f"dDTI {r['fwd']['dti_union'] - r['fwd']['dti_base']:+.4f}  t={time.time() - t0:.0f}s", flush=True)
    Path(args.links_csv).parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(all_links).to_csv(args.links_csv, index=False)

    tp_f, fp_f, eff_f = pooled(rows, "fwd", "dTP_alone", "dFP_alone")
    tpa, fpa, _ = pooled(rows, "ctrlA", "dTP_alone", "dFP_alone")
    tpb, fpb, _ = pooled(rows, "ctrlB", "dTP_alone", "dFP_alone")
    eff_c = (tpa + tpb) / (fpa + fpb)
    fold_names = holdout.FOLD_NAMES
    per_fold = {}
    for fn in fold_names:
        rr = [r for r in rows if r["fold"] == fn]
        a = pooled(rr, "fwd", "dTP_alone", "dFP_alone")[2]
        ca = sum(r["ctrlA"]["dTP_alone"] + r["ctrlB"]["dTP_alone"] for r in rr)
        cb = sum(r["ctrlA"]["dFP_alone"] + r["ctrlB"]["dFP_alone"] for r in rr)
        per_fold[fn] = {"fwd_eff": a, "ctrl_eff": ca / cb, "ratio": a / (ca / cb),
                        "dti_gain_vs_leaky_base": float(np.mean([r["fwd"]["dti_union"] - r["fwd"]["dti_base"] for r in rr]))}
    # mean-over-folds paired DTI gain (per seed average over folds, then mean over seeds)
    seed_gain = []
    worst = 0.0
    for s in seeds:
        rr = [r for r in rows if r["seed"] == s]
        g = [r["fwd"]["dti_union"] - r["fwd"]["dti_base"] for r in rr]
        seed_gain.append(float(np.mean(g)))
        worst = min(worst, min(g))
    m030 = metric.inclusion_threshold(0.30)
    gate = {
        "g1_enrichment_ge_2x": bool(eff_f >= 2.0 * eff_c),
        "g2_eff_ge_0.10": bool(eff_f >= 0.10),
        "g3_fold_wins_ge_3_of_4": bool(sum(v["fwd_eff"] > v["ctrl_eff"] for v in per_fold.values()) >= 3),
        "g4_paired_dti_gain_gt_0.001": bool(np.mean(seed_gain) > 0.001),
        "g4b_no_cell_loses_gt_0.01": bool(worst >= -0.01),
    }
    out = {
        "preregistration": "knowledge/03_preregistration_topology_gate.md", "seeds": seeds, "rule": RULE,
        "spacing": SPACING, "n_cells": len(rows),
        "pooled": {"fwd_eff": eff_f, "ctrl_eff": eff_c, "enrichment": eff_f / eff_c,
                   "fwd_dTP": tp_f, "fwd_dFP": fp_f, "inclusion_threshold_at_dti_0.30": m030,
                   "inclusion_threshold_at_dti_0.25": metric.inclusion_threshold(0.25),
                   "fwd_dots_per_seed": float(np.mean([sum(r["fwd"]["dots"] for r in rows if r["seed"] == s) for s in seeds])),
                   "fwd_dots_nonredundant_per_seed": float(np.mean([sum(r["fwd"]["dots_nonredundant"] for r in rows if r["seed"] == s) for s in seeds])),
                   "hidden_truth_px_per_seed": float(np.mean([sum(r["n_hidden_px"] for r in rows if r["seed"] == s) for s in seeds]))},
        "per_fold": per_fold,
        "paired_vs_leaky_dotted_h19_5": {"mean_gain_over_folds_and_seeds": float(np.mean(seed_gain)),
                                         "per_seed_mean_gain": seed_gain, "worst_cell": worst,
                                         "base_dti_mean": float(np.mean([r["fwd"]["dti_base"] for r in rows]))},
        "gate": gate, "gate_passed": bool(all(gate.values())),
        "cells": rows, "seconds": time.time() - t0,
    }
    Path(args.out).write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: out[k] for k in ("pooled", "per_fold", "paired_vs_leaky_dotted_h19_5", "gate", "gate_passed")}, indent=1, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
