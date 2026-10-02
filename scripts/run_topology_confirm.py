#!/usr/bin/env python3
"""Confirmatory run for T-v2 (z >= 3 evidence filter) on fresh seeds; see Addendum A of the pre-registration."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import grid, holdout, links, metric, paths  # noqa: E402
from gems27.candidates import dedupe_mutual, evidence_score  # noqa: E402
from gems27.graph import build_graph  # noqa: E402

RULE = dict(cone_deg=30.0, rmin=10.0, rmax=40.0)
SPACING = 3
N_RANDOM = 20


class CellEval:
    """Marginal TP/FP of added dots, with truth/base distance fields precomputed once per cell."""

    def __init__(self, hid, kn, fmc, base_c):
        self.g = hid & fmc & ~kn
        self.active = fmc & ~kn
        self.k_pt = metric.kernel_from_distance(distance_transform_edt(~self.g))
        self.base = base_c & self.active
        self.d_base = distance_transform_edt(~self.base) if self.base.any() else np.full(self.g.shape, np.inf)
        gi = self.g
        self.c_empty = np.zeros(int(gi.sum()))
        self.c_base = metric.kernel_from_distance(self.d_base[gi]) if self.base.any() else self.c_empty
        self.fp_base = float((1 - self.k_pt[self.base]).sum())
        self.n_truth = int(gi.sum())

    def alone(self, dots):
        a = dots & self.active
        if not a.any():
            return 0.0, 0.0, 0
        c = metric.kernel_from_distance(distance_transform_edt(~a)[self.g])
        return float(c.sum()), float((1 - self.k_pt[a]).sum()), int(a.sum())

    def vs_base(self, dots):
        a = dots & self.active & (self.d_base >= metric.RADIUS_PX)       # non-redundant w.r.t. the base
        u = self.base | a
        c1 = metric.kernel_from_distance(distance_transform_edt(~u)[self.g]) if u.any() else self.c_empty
        tp0, tp1 = float(self.c_base.sum()), float(c1.sum())
        fp1 = float((1 - self.k_pt[u]).sum())
        dti = lambda tp, fp: tp / (tp + 0.2 * fp + 0.8 * (self.n_truth - tp) + 1e-7)  # noqa: E731
        return tp1 - tp0, fp1 - self.fp_base, dti(tp0, self.fp_base), dti(tp1, fp1), int(a.sum())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="110-119")
    ap.add_argument("--out", default=str(paths.EVIDENCE / "topology_confirmation_v2.json"))
    args = ap.parse_args()
    a, _, b = args.seeds.partition("-")
    seeds = list(range(int(a), int(b) + 1)) if b else [int(a)]
    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    fold = holdout.make_quadrant_folds(foot)
    with rasterio.open(paths.DOTTED_0_2477) as s:
        base_full = np.nan_to_num(s.read(1)) > 0
    rng = np.random.default_rng(2026)
    t0 = time.time()
    cells = []
    for seed in seeds:
        for f in range(4):
            sp = holdout.make_split(labels, fold, f, seed)
            fm = sp.fold_mask
            sl = holdout.crop(None, fm)
            fg = build_graph(sp.known, with_edges=False)
            hid, kn, fmc = sp.hidden[sl], (sp.known & fm)[sl], fm[sl]
            ev = CellEval(hid, kn, fmc, (base_full & fm)[sl])
            L = links.generate_links(fg, region=fm, **RULE)
            z = evidence_score(L)
            res = {"seed": seed, "fold": sp.name, "n_hidden_px": ev.n_truth, "links_all": int(len(L))}

            def dots_of(sub, sl=sl, fmc=fmc, kn=kn):
                return links.rasterize_links(sub, labels.shape, SPACING)[sl] & fmc & ~kn

            variants = {"all": np.ones(len(L), bool), "z>=2": z >= 2, "z>=3": z >= 3, "z>=4": z >= 4}
            Ld = dedupe_mutual(L[z >= 3])
            variants_sub = {"z>=3 dedup": Ld}
            for name, m in variants.items():
                d = dots_of(L[m])
                tp, fp, n = ev.alone(d)
                dtp, dfp, d0, d1, nn = ev.vs_base(d)
                res[name] = {"links": int(m.sum()), "dots": n, "dTP": tp, "dFP": fp,
                             "dTP_b": dtp, "dFP_b": dfp, "dti_base": d0, "dti_union": d1, "dots_nonred": nn}
            for name, sub in variants_sub.items():
                d = dots_of(sub)
                tp, fp, n = ev.alone(d)
                dtp, dfp, d0, d1, nn = ev.vs_base(d)
                res[name] = {"links": int(len(sub)), "dots": n, "dTP": tp, "dFP": fp,
                             "dTP_b": dtp, "dFP_b": dfp, "dti_base": d0, "dti_union": d1, "dots_nonred": nn}
            # random subsets of the forward links with the size of the z>=3 set
            k = int((z >= 3).sum())
            rnd = []
            for _ in range(N_RANDOM):
                pick = np.zeros(len(L), bool)
                if k and len(L):
                    pick[rng.choice(len(L), size=min(k, len(L)), replace=False)] = True
                tp, fp, n = ev.alone(dots_of(L[pick]))
                rnd.append((tp, fp))
            res["random_same_size"] = rnd
            for name, rot in (("ctrlA", 90.0), ("ctrlB", -90.0)):
                Lc = links.generate_links(fg, region=fm, rotate_deg=rot, **RULE)
                tp, fp, n = ev.alone(dots_of(Lc))
                res[name] = {"links": int(len(Lc)), "dots": n, "dTP": tp, "dFP": fp}
            cells.append(res)
            print(f"seed {seed} {sp.name:<17s} links {len(L):4d} z3 {k:3d}  effAll {res['all']['dTP']/max(res['all']['dFP'],1e-9):.3f} "
                  f"effZ3 {res['z>=3']['dTP']/max(res['z>=3']['dFP'],1e-9):.3f}  t={time.time()-t0:.0f}s", flush=True)

    def pooled(name, a="dTP", b="dFP", rows=None):
        rows = cells if rows is None else rows
        tp = sum(r[name][a] for r in rows)
        fp = sum(r[name][b] for r in rows)
        return tp / fp if fp else float("nan")

    eff = {n: pooled(n) for n in ("all", "z>=2", "z>=3", "z>=4", "z>=3 dedup")}
    eff_ctrl = (sum(r["ctrlA"]["dTP"] + r["ctrlB"]["dTP"] for r in cells)
                / sum(r["ctrlA"]["dFP"] + r["ctrlB"]["dFP"] for r in cells))
    rand_eff = []
    for j in range(N_RANDOM):
        tp = sum(r["random_same_size"][j][0] for r in cells)
        fp = sum(r["random_same_size"][j][1] for r in cells)
        rand_eff.append(tp / fp if fp else float("nan"))
    per_fold = {}
    for fn in holdout.FOLD_NAMES:
        rr = [r for r in cells if r["fold"] == fn]
        per_fold[fn] = {"eff_all": pooled("all", rows=rr), "eff_z3": pooled("z>=3", rows=rr),
                        "eff_z2": pooled("z>=2", rows=rr), "eff_z4": pooled("z>=4", rows=rr)}
    def seed_gain(name):
        g = []
        for s in seeds:
            rr = [r for r in cells if r["seed"] == s]
            g.append(float(np.mean([r[name]["dti_union"] - r[name]["dti_base"] for r in rr])))
        worst = min(r[name]["dti_union"] - r[name]["dti_base"] for r in cells)
        return g, worst
    g3, w3 = seed_gain("z>=3")
    gate = {
        "g1_eff_z3_ge_0.15_and_ge_1.25x_all": bool(eff["z>=3"] >= 0.15 and eff["z>=3"] >= 1.25 * eff["all"]),
        "g2_exceeds_p95_of_random_same_size": bool(eff["z>=3"] > float(np.nanpercentile(rand_eff, 95))),
        "g3_fold_wins_ge_3_of_4": bool(sum(v["eff_z3"] > v["eff_all"] for v in per_fold.values()) >= 3),
        "g4_paired_gain_gt_0.001": bool(np.mean(g3) > 0.001),
        "g4b_no_cell_loses_gt_0.01": bool(w3 >= -0.01),
    }
    out = {"preregistration": "knowledge/03_preregistration_topology_gate.md#addendum-a", "seeds": seeds,
           "efficiency_pooled": eff, "control_pooled": eff_ctrl,
           "random_same_size": {"mean": float(np.nanmean(rand_eff)), "p95": float(np.nanpercentile(rand_eff, 95)),
                                "max": float(np.nanmax(rand_eff))},
           "per_fold": per_fold,
           "dots_per_seed": {n: float(np.mean([sum(r[n]["dots"] for r in cells if r["seed"] == s) for s in seeds]))
                             for n in ("all", "z>=2", "z>=3", "z>=4", "z>=3 dedup")},
           "dots_nonredundant_per_seed": {n: float(np.mean([sum(r[n]["dots_nonred"] for r in cells if r["seed"] == s) for s in seeds]))
                                          for n in ("all", "z>=2", "z>=3", "z>=4", "z>=3 dedup")},
           "paired_vs_leaky_dotted_h19_5": {n: {"mean_gain": float(np.mean(seed_gain(n)[0])), "per_seed": seed_gain(n)[0],
                                                "worst_cell": seed_gain(n)[1]} for n in ("all", "z>=2", "z>=3", "z>=4", "z>=3 dedup")},
           "inclusion_threshold": {"dti_0.25": metric.inclusion_threshold(0.25), "dti_0.30": metric.inclusion_threshold(0.30)},
           "gate": gate, "gate_passed": bool(all(gate.values())), "cells": cells, "seconds": time.time() - t0}
    Path(args.out).write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: out[k] for k in ("efficiency_pooled", "control_pooled", "random_same_size", "per_fold",
                                          "dots_per_seed", "dots_nonredundant_per_seed", "paired_vs_leaky_dotted_h19_5",
                                          "gate", "gate_passed")}, indent=1, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
