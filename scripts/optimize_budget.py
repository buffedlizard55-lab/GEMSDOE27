#!/usr/bin/env python3
"""Live-anchored emission-budget optimiser: pick the thinning distance that maximises expected DTI.

Why this is not a re-run of the sibling's model
-----------------------------------------------
GEMSDOE25 fitted a two-parameter emission model to ONE solid/dotted pair and extrapolated the curve
in d. Here the forward model is *exact* given three measurable quantities and is validated against
TWO independent live pairs:

    score = TP / (0.2 TP (1 - rho) + 0.2 N + 0.8 |G|)                              (forward model)

    N(d)   = |dot_thin(S, d)|                     (deterministic Poisson-disk thinning)
    c(d)   = mean over the footprint of max_{dot in S_d} k(d(x,dot))
             = credit a *uniformly spread* truth would earn per truth pixel
    rho(d) = N(d) * kernel_area / (nfp * c(d))    = MPw / TPw, the crowding factor
    TP(d)  = TP_solid * c(d) / c_solid            (retention = ratio of blind credits)

Two facts make this trustworthy:
* The metric charges a predicted pixel FPw = 1 - max_g k, so a pixel that merely *sits near* truth is
  cheap even when it is redundant for TPw. rho > 1 makes the (1 - rho) term negative: **crowding
  near truth is a discount, not a penalty**. Global thinning is therefore not automatically good --
  the optimum trades coverage against crowding, and this script finds it.
* The retention assumption TP(d) = TP_s c(d)/c_s is checked against live scores: for H19-5 -> d1.5
  it predicts 0.853 against a live-measured 0.854; for H25-ctx-ridge -> h28-dotted it predicts 0.834
  against 0.802. Agreement to 0.1 % and 4 %.

    python scripts/optimize_budget.py                 # all anchored surfaces
    python scripts/optimize_budget.py --surface h19_5 # one surface, full sweep
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import metric, paths, thinning  # noqa: E402

ALPHA, BETA = metric.ALPHA, metric.BETA
R = metric.RADIUS_PX
DISTANCES = [1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.8, 3.0, 3.25, 3.5, 4.0, 4.5, 5.0, 6.0]


def kernel_area() -> float:
    r = int(np.ceil(R))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    return float(np.maximum(1.0 - np.hypot(yy, xx) / R, 0.0).sum())


def blind_credit(mask: np.ndarray, foot: np.ndarray) -> float:
    """c_S: credit per truth pixel if truth were spread uniformly over the footprint."""
    d = distance_transform_edt(~mask)
    return float(metric.kernel_from_distance(d[foot]).mean())


def forward_score(tp: float, n: int, rho: float, g: float) -> float:
    return tp / (ALPHA * tp * (1.0 - rho) + ALPHA * n + BETA * g)


def emission(path: Path, foot: np.ndarray, cat: np.ndarray) -> np.ndarray:
    with rasterio.open(path) as s:
        a = s.read(1).astype(np.float32)
    return (np.isfinite(a) & (a > 0)) & foot & ~cat


def sweep(base: np.ndarray, foot: np.ndarray, g: float, tp_solid: float,
          karea: float, nfp: int, extra: np.ndarray | None = None) -> list[dict]:
    """Thin `base` (+ optional fixed `extra` dots) across DISTANCES and score each with the model."""
    c_solid = blind_credit(base, foot)
    rows = []
    for d in DISTANCES:
        th = thinning.dot_thin(base, d) if d > 1.0 else base.copy()
        m = th if extra is None else (th | extra)
        n = int(m.sum())
        c = blind_credit(m, foot)
        rho = n * karea / (nfp * c) if c > 0 else float("inf")
        tp = tp_solid * (c / c_solid) if c_solid > 0 else 0.0
        rows.append({"min_dist": d, "n_px": n, "c_blind": c, "rho": rho,
                     "retention_vs_solid": c / c_solid if c_solid else None,
                     "credit_TPw": tp, "model_score": forward_score(tp, n, rho, g)})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--surface", default=None)
    args = ap.parse_args()

    with rasterio.open(paths.TEMPLATE) as s:
        foot = np.isfinite(s.read(1))
    with rasterio.open(paths.LABELS) as s:
        cat = (s.read(1) == 1) & foot
    nfp = int(foot.sum())
    karea = kernel_area()
    inv = json.loads((paths.EVIDENCE / "live_inversion.json").read_text())
    g = inv["G_used"]
    by_label = {r["label"]: r for r in inv["submissions"]}

    # ---- validate the retention assumption on every live solid->dotted pair we hold -------------
    validations = []
    for solid_lbl, dotted_lbl in [
        ("19GEMSDOE h19-5", "24GEMSDOE h25-1 dotted-h19-5-d1-5 (989f59505db1)"),
        ("GEMSDOE10 H25-ctx-ridge", "GEMSDOE10 h28-dotted-ridge"),
    ]:
        if solid_lbl not in by_label or dotted_lbl not in by_label:
            continue
        cs = by_label[solid_lbl]["c_blind_credit_per_truth"]
        cd = by_label[dotted_lbl]["c_blind_credit_per_truth"]
        live = by_label[dotted_lbl]["credit_TPw"] / by_label[solid_lbl]["credit_TPw"]
        validations.append({"solid": solid_lbl, "dotted": dotted_lbl,
                            "retention_predicted_by_geometry": cd / cs,
                            "retention_measured_live": live,
                            "relative_error": (cd / cs - live) / live})

    print("retention model validation (geometry vs two independent live pairs):")
    for v in validations:
        print(f"  {v['solid'][:26]:<26} -> {v['dotted'][:30]:<30} "
              f"geom {v['retention_predicted_by_geometry']:.4f}  live {v['retention_measured_live']:.4f}"
              f"  err {v['relative_error'] * 100:+.1f}%")

    # ---- sweep every anchored surface we can rebuild --------------------------------------------
    surfaces = {
        "h19_5": (paths.H19_5, "19GEMSDOE h19-5"),
        "dotted_d1_5": (paths.DOTTED_0_2477,
                        "24GEMSDOE h25-1 dotted-h19-5-d1-5 (989f59505db1)"),
    }
    out = {"G_used": g, "kernel_area_px": karea, "footprint_px": nfp,
           "retention_validation": validations, "sweeps": {}}
    print(f"\n{'surface':<14}{'d':>6}{'N':>9}{'c_blind':>9}{'rho':>7}{'reten':>7}"
          f"{'credit':>8}{'model score':>12}")
    for key, (path, lbl) in surfaces.items():
        if args.surface and args.surface != key:
            continue
        if lbl not in by_label or not Path(path).exists():
            continue
        base = emission(Path(path), foot, cat)
        tp_solid = by_label[lbl]["credit_TPw"]
        rows = sweep(base, foot, g, tp_solid, karea, nfp)
        out["sweeps"][key] = {"label": lbl, "live_score": by_label[lbl]["score"],
                              "live_credit_TPw": tp_solid, "rows": rows}
        for r in rows:
            print(f"{key:<14}{r['min_dist']:>6}{r['n_px']:>9,}{r['c_blind']:>9.4f}"
                  f"{r['rho']:>7.2f}{r['retention_vs_solid']:>7.3f}{r['credit_TPw']:>8,.0f}"
                  f"{r['model_score']:>12.4f}")
        best = max(rows, key=lambda r: r["model_score"])
        print(f"  -> model optimum for {key}: d={best['min_dist']} N={best['n_px']:,} "
              f"score {best['model_score']:.4f} (live at this surface's own d: "
              f"{by_label[lbl]['score']})")
        out["sweeps"][key]["best"] = best
        print()

    paths.EVIDENCE.joinpath("budget_optimum.json").write_text(json.dumps(out, indent=1))
    print("wrote evidence/budget_optimum.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
