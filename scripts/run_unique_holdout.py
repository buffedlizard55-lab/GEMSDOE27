#!/usr/bin/env python3
"""Holdout validation of the unique GEMSDOE32-inspired emission rule.

Hypothesis (unique, not in this repo): emit on a *scatter-smoothed* detector surface
(gaussian sigma ~1.85 px, matching the inferred ~1.85 px scatter of hidden truth around
mapped traces), restricted to the *far field* (catalogue distance >= 3 px = 300 m), with
greedy credit-bar selection. Add validated T-v2 topology gap-closure dots that fall in the
far field.

This differs from everything in the repo:
- GEMSDOE27 slots emit ON the catalogue base (dotted H19-5) plus topology dots near it.
- GEMSDOE32's h33 emits far-from-catalogue dots but from a plain thinned base, not a
  scatter-smoothed field, not greedy credit-bar, not combined with topology links.
- The holdout's truth is catalogue-internal, so far-field behaviour is under-scored here;
  this run measures the catalogue-internal gate only (consistent with the repo's limits).

Uses the cached feature stack + holdout.py + submission.py (REUSE, DON'T REBUILD).
Fresh seeds 160-163 (140-149 and 150-159 are consumed).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import (  # noqa: E402
    candidates,
    grid,
    holdout,
    links,
    metric,
    oof_detector,
    paths,
    thinning,
)

SEEDS = (160, 161, 162, 163)  # fresh; 140-149 (H28-1) and 150-159 (H27-10) are consumed
SCATTER_SIGMA = 1.85  # px, matches the inferred truth scatter scale (GEMSDOE32 truth model)
FAR_D_PX = 3.0  # px: exclude catalogue + 0-300 m near field (off-catalogue-only emission)
THIN_D = 1.5  # px dot-thinning for the scatter-smoothed picks


def scatter_farfield_emission(oof_prob, ridge, foot, known, d_cat, fold_mask, budget_frac):
    """Top-K scatter-smoothed far-field picks, dot-thinned, off known catalogue."""
    active = fold_mask & ~known & (d_cat >= FAR_D_PX)
    cand = ridge & active
    sm = gaussian_filter(np.where(active & np.isfinite(oof_prob), oof_prob, 0.0).astype(np.float32),
                         sigma=SCATTER_SIGMA)
    k = int(round(budget_frac * int(fold_mask.sum())))
    ys, xs = np.nonzero(cand)
    out = np.zeros_like(fold_mask, bool)
    if len(ys) == 0 or k <= 0:
        return out
    if len(ys) > k:
        sc = sm[ys, xs]
        top = np.argpartition(-sc, k - 1)[:k]
        ys, xs = ys[top], xs[top]
    raw = np.zeros_like(fold_mask, bool)
    raw[ys, xs] = True
    return thinning.dot_thin(raw, THIN_D) & active


def tv2_farfield_dots(labels, foot, fold_mask, known, d_cat, base_dots, z_min=3):
    """T-v2 gap-closure links rasterised, restricted to far field and non-redundant."""
    from scipy.ndimage import distance_transform_edt

    from gems27 import graph
    fg = graph.build_graph(known)
    L = links.generate_links(fg, **candidates.RULE)
    L["z"] = candidates.evidence_score(L)
    sel = L[L.z >= z_min].copy()
    if sel.empty:
        return np.zeros_like(fold_mask, bool)
    sel = candidates.dedupe_mutual(sel)
    dots = links.rasterize_links(sel, labels.shape, candidates.SPACING) & foot & ~known
    # far field only, non-redundant with the scatter base, >=3 px from any kept base dot
    d_base = distance_transform_edt(~base_dots) if base_dots.any() else np.full(labels.shape, np.inf)
    return dots & (d_cat >= FAR_D_PX) & (d_base >= 3.0)


def eval_set(pred, g, active, k_pt):
    p = pred & active
    n_g = int(g.sum())
    if not p.any() or n_g == 0:
        return 0.0, 0.0, 0, 0
    tp = float(metric.kernel_from_distance(distance_transform_edt(~p)[g]).sum())
    fp = float((1.0 - k_pt[p]).sum())
    dti = tp / (tp + 0.2 * fp + 0.8 * (n_g - tp) + 1e-7)
    return tp, fp, dti, int(p.sum())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="160-163")
    ap.add_argument("--out", default=str(paths.EVIDENCE / "unique_scatter_holdout.json"))
    args = ap.parse_args()
    a, _, b = args.seeds.partition("-")
    seeds = list(range(int(a), int(b) + 1)) if b else [int(a)]

    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    fold = holdout.make_quadrant_folds(foot)
    d_cat = distance_transform_edt(~labels)  # distance to catalogue (px, 100 m/cell)

    print("Computing OOF probabilities (4-fold, reused across seeds)...", flush=True)
    oof_prob = oof_detector.fit_predict_oof_probabilities(foot, labels, fold)
    ridge_all = oof_detector.ridge_nms(oof_prob, foot, sigma=1.0)
    print(f"OOF done. ridges={int(ridge_all.sum()):,}", flush=True)

    budget_frac = oof_detector.PRE_THIN_FRAC
    variants = ["base_oof", "scatter_farfield", "scatter_farfield_plus_tv2"]
    cells = []
    t0 = time.time()
    for seed in seeds:
        for f in range(4):
            sp = holdout.make_split(labels, fold, f, seed)
            fm = sp.fold_mask
            hid, kn = sp.hidden, sp.known
            g = hid & fm & ~kn
            active = fm & ~kn
            k_pt = metric.kernel_from_distance(distance_transform_edt(~g)) if g.any() else np.zeros_like(g, float)

            # base OOF dotted base
            base_c = oof_detector.build_oof_dotted_base(
                oof_prob, ridge_all, fm, kn,
                budget_frac=budget_frac, thin_d=1.5,
            ) & active

            # unique: scatter-smoothed far field
            sf = scatter_farfield_emission(oof_prob, ridge_all, fm, kn,
                                           d_cat, fm, budget_frac)

            # unique + T-v2 far-field topology dots
            sf_tv2 = sf | tv2_farfield_dots(labels, foot, fm, kn, d_cat, sf)

            v_sets = {"base_oof": base_c, "scatter_farfield": sf,
                      "scatter_farfield_plus_tv2": sf_tv2}
            row = {"seed": seed, "fold": sp.name, "n_truth": int(g.sum())}
            for vn, s_mask in v_sets.items():
                tp, fp, dti, n_px = eval_set(s_mask, g, active, k_pt)
                row[vn] = {"tp": tp, "fp": fp, "dti": dti, "dots": n_px}
            cells.append(row)
        print(f"seed {seed} done (t={time.time()-t0:.0f}s)", flush=True)

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
        summary[vn] = {
            "mean_dti_gain": float(np.mean(gains_by_seed)),
            "min_seed_gain": float(np.min(gains_by_seed)),
            "max_seed_gain": float(np.max(gains_by_seed)),
            "fold_gains": gains_by_fold,
            "folds_improved": int(sum(v > 0 for v in gains_by_fold.values())),
            "mean_dots": float(np.mean([c[vn]["dots"] for c in cells])),
            "mean_base_dots": float(np.mean([c["base_oof"]["dots"] for c in cells])),
        }

    base_mean_dti = float(np.mean([c["base_oof"]["dti"] for c in cells]))
    out = {
        "hypothesis": "unique scatter-smoothed far-field greedy emission (+ T-v2 far-field dots)",
        "layers": ["OOF detector probabilities (32-band label-free feature stack)",
                   "scatter smoothing gaussian sigma=1.85 px",
                   "catalogue-distance far-field mask (d >= 3 px = 300 m)",
                   "T-v2 topology gap-closure links (z>=3, far field, non-redundant)"],
        "signature": "blurred detector surface matching ~1.85 px truth scatter; off-catalogue-only emission",
        "why_missing_fault": "emits where scattered hidden truth lives (around, not on, mapped traces); "
        "excludes catalogue pixels the holdout over-rewards; credit-per-pixel selection",
        "differs_from_repo": "GEMSDOE27 emits on the catalogue base; GEMSDOE32 h33 emits far-from-catalogue "
        "dots from a plain thinned base without scatter smoothing, credit-bar gating, or topology links",
        "seeds": seeds,
        "base_oof_mean_dti": base_mean_dti,
        "variants": summary,
        "seconds": time.time() - t0,
    }
    Path(args.out).write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
