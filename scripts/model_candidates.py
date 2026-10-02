#!/usr/bin/env python3
"""Score every shipped candidate with the live-anchored forward model, under BOTH truth assumptions.

Why two models
--------------
`scripts/optimize_budget.py` gives a forward model that reproduces the two live anchors exactly
(H19-5 solid -> 0.1922, dotted d1.5 -> 0.2477) and whose retention rule checks out on two
independent solid->dotted live pairs (-0.1 % and +4.0 %). Its retention rule is

    credit(S') = credit_solid * c(S') / c_solid,   c(S) = blind coverage = mean over the footprint
                                                     of max_{dot in S} k(d(.,dot))

i.e. it assumes the hidden truth is spread like a *uniform* field near the emission. That assumption
is exactly right for **geometric thinning** (Poisson-disk removal is spatially unbiased, and it is
what the two live pairs measured) but it is **biased against targeted pruning**: it charges the
removed pixels with average credit. The out-of-fold gate measured the H27-4 catalogue-flank pixels
directly and found them near-dead (removed efficiency 0.0034 against a live break-even of 0.0521),
so a uniform-truth model overstates what the prune costs.

This script therefore reports both:

* `geometric`  - uniform-truth retention for every change. Validated on live thinning pairs.
* `hybrid`     - geometric retention for the thinning step, plus the *measured* OOF marginal
                 efficiencies for the targeted steps (prune: 0.0034 credit/px removed;
                 T-v2 dots: 0.2251 credit/px added, from `evidence/oof_hypothesis_gates.json`).

Neither is a score. The gap between them IS the open question, and slot 1 vs slot 3 is the live A/B
that settles it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import metric, paths  # noqa: E402

ALPHA, BETA = metric.ALPHA, metric.BETA
KAREA = 9.3803
ANCHOR_LABEL = "19GEMSDOE h19-5"
# measured marginal efficiencies (evidence/oof_hypothesis_gates.json, 4-fold spatial CV, seeds 130-139)
EFF_PRUNE_REMOVED = 0.0034      # credit per px removed by the H27-4 r<=1 catalogue-flank prune
EFF_TV2_ADDED = 0.2251          # credit per px added by the H27-1 T-v2 gap-closure dots


def main() -> int:
    with rasterio.open(paths.TEMPLATE) as s:
        foot = np.isfinite(s.read(1))
    with rasterio.open(paths.LABELS) as s:
        cat = (s.read(1) == 1) & foot
    H, W = foot.shape
    fy, fx = np.nonzero(foot)
    flat = (fy * W + fx).astype(np.int64)
    nfp = len(flat)

    inv = json.loads((paths.EVIDENCE / "live_inversion.json").read_text())
    g = inv["G_used"]
    by = {r["label"]: r for r in inv["submissions"]}
    a = by[ANCHOR_LABEL]
    c_solid, tp_solid = a["c_blind_credit_per_truth"], a["credit_TPw"]

    def c_of(m):
        return float(metric.kernel_from_distance(
            distance_transform_edt(~m).reshape(-1)[flat]).mean())

    def forward(tp, n, rho):
        return tp / (ALPHA * tp * (1.0 - rho) + ALPHA * n + BETA * g)

    manifest = json.loads((paths.DOCS / "downloads" / "manifest.json").read_text())
    # (slot, manifest entry, thinning distance of the base, H19-5 solid px at that distance)
    specs = [("slot1_primary_A_B", manifest["primary"], 1.5),
             ("slot2_secondary_d2_8", manifest["secondary"], 2.8),
             ("slot3_tertiary_prune_d1_5", manifest["tertiary"], 1.5),
             ("slot4_quaternary_all_increments", manifest["quaternary"], 2.8)]

    from gems27 import thinning
    with rasterio.open(paths.H19_5) as s:
        raw = (np.nan_to_num(s.read(1)) > 0) & foot & ~cat
    base_ret = {}
    for d in (1.5, 2.8):
        bd = thinning.dot_thin(raw, d)
        base_ret[d] = {"n_px": int(bd.sum()), "c": c_of(bd), "retention": c_of(bd) / c_solid}
    print("\nbase thinnings of H19-5 (geometric retention, live-validated rule):")
    for d, v in base_ret.items():
        print(f"  d={d}: N={v['n_px']:,} c={v['c']:.5f} retention={v['retention']:.4f}")

    out = {"G_used": g, "anchor": {"label": ANCHOR_LABEL, "live_score": a["score"],
                                   "credit_TPw": tp_solid, "c_blind": c_solid},
           "base_thinnings": {str(k): v for k, v in base_ret.items()},
           "assumptions": {"eff_prune_removed_credit_per_px": EFF_PRUNE_REMOVED,
                           "eff_t_v2_added_credit_per_px": EFF_TV2_ADDED,
                           "geometric_model": "uniform-truth retention c(S')/c_solid charged for ALL "
                                              "pixel changes, including the targeted prune",
                           "hybrid_model": "geometric retention for the thinning step only; the "
                                           "targeted prune and T-v2 additions are charged at the "
                                           "marginal efficiencies the out-of-fold gate measured"},
           "candidates": []}

    print(f"\n{'candidate':<34}{'N':>8}{'reten':>7}{'geo':>8}{'hybrid':>8}"
          f"{'TP_geo':>8}{'TP_hyb':>8}")
    for slot, e, d in specs:
        p = paths.DOCS / "downloads" / e["nan"]
        with rasterio.open(p) as s:
            arr = s.read(1).astype(np.float32)
        m = (np.isfinite(arr) & (arr > 0)) & foot & ~cat
        n = int(m.sum())
        c = c_of(m)
        rho = n * KAREA / (nfp * c)
        ret = c / c_solid
        tp_geo = tp_solid * ret
        pruned = int(e.get("pruned_flank_shadow_px", 0))
        added = int(e.get("added_px", 0))
        tp_hyb = (tp_solid * base_ret[d]["retention"]
                  - pruned * EFF_PRUNE_REMOVED
                  + added * EFF_TV2_ADDED)
        out["candidates"].append({
            "slot": slot, "file": e["nan"], "content_id": e["content_id"], "emitted_px": n,
            "base_min_dist": d, "pruned_flank_shadow_px": pruned, "added_t_v2_px": added,
            "retention_vs_H19_5_solid": ret, "rho_matched_over_TP": rho,
            "model_score_geometric": forward(tp_geo, n, rho),
            "model_score_hybrid": forward(tp_hyb, n, rho),
            "credit_geometric": tp_geo, "credit_hybrid": tp_hyb,
        })
        print(f"{slot:<34}{n:>8,}{ret:>7.3f}{forward(tp_geo, n, rho):>8.4f}"
              f"{forward(tp_hyb, n, rho):>8.4f}{tp_geo:>8,.0f}{tp_hyb:>8,.0f}")

    for lbl in (ANCHOR_LABEL, "24GEMSDOE h25-1 dotted-h19-5-d1-5 (989f59505db1)"):
        r = by[lbl]
        out.setdefault("live_references", []).append(
            {"label": lbl, "live_score": r["score"], "emitted_px": r["n_scored"],
             "credit_TPw": r["credit_TPw"], "rho": r["rho_matched_over_TP"]})
        print(f"{'LIVE ' + lbl[:28]:<34}{r['n_scored']:>8,}"
              f"{r['credit_TPw'] / tp_solid:>7.3f}{r['score']:>8.4f}{r['score']:>8.4f}  "
              f"{r['credit_TPw']:>7,.0f}{r['credit_TPw']:>8,.0f}")

    out["reading"] = (
        "Both models reproduce the live anchors. They disagree only on the targeted H27-4 prune: the "
        "geometric model charges pruned flank pixels with average credit, the hybrid model charges "
        "them with the efficiency the out-of-fold gate actually measured (0.0034, ~15x below the "
        "0.0521 live break-even). Slot 1 vs slot 3 is the live A/B that settles which is right. "
        "Neither column is a leaderboard score.")
    (paths.EVIDENCE / "candidate_model_scores.json").write_text(json.dumps(out, indent=1))
    print("\nwrote evidence/candidate_model_scores.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
