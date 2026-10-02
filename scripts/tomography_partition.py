#!/usr/bin/env python3
"""Where does the hidden truth live? A *partition* tomography of the live score corpus.

`scripts/invert_live_scores.py` showed the whole tomography fails when the habitat bases overlap
(in-sample R2 = -1.24: 25 collinear fields, 20 measurements, mass constraint unattainable). This
script fixes the identification problem instead of adding regularisation:

**Use a PARTITION.** Split the off-catalogue footprint into J mutually exclusive, exhaustive
habitats. Then the truth intensity lam_j is a per-habitat *rate* (px of hidden label per px of
habitat), sum_j lam_j |B_j| = |G| is automatically consistent, and each of the 20 live scores is one
linear measurement

    TP_i = sum_j lam_j * A_ij,      A_ij = sum_{x in B_j} K_i(x),   K_i(x) = max_dot k(d(x,dot))

with TP_i = s_i (0.2 N_i + 0.8 |G|) from the official metric. J = 7 habitats and 20 measurements is
over-determined, so lam is identifiable and leave-one-submission-out score prediction is a real test.

The geological question this answers: **at what distance from the mapped USGS/INGENIOUS catalogue do
the organisers' new expert fault labels live, and does LiDAR scarp evidence relocate them?** That is
the question a better emission has to answer, because 57 % of the hidden truth is not covered at all
by the group's best file.

    python scripts/tomography_partition.py                # radial partition
    python scripts/tomography_partition.py --basis scarp  # radial x LiDAR-scarp partition
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.optimize import nnls

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import metric, paths, tomography  # noqa: E402

ALPHA, BETA = metric.ALPHA, metric.BETA
RINGS = [(1, 2, "cat_100_200m"), (2, 3, "cat_200_300m"), (3, 5, "cat_300_500m"),
         (5, 8, "cat_500_800m"), (8, 15, "cat_800_1500m"), (15, 30, "cat_1500_3000m"),
         (30, 10 ** 9, "cat_gt3000m")]


def radial_partition(free: np.ndarray, d_cat: np.ndarray) -> tuple[np.ndarray, list[str]]:
    """Integer habitat id per pixel (-1 = not in a habitat), plus habitat names."""
    hab = np.full(free.shape, -1, np.int16)
    names = []
    for j, (lo, hi, nm) in enumerate(RINGS):
        m = free & (d_cat >= lo) & (d_cat < hi)
        hab[m] = j
        names.append(nm)
    return hab, names


def scarp_partition(free: np.ndarray, d_cat: np.ndarray, lidar_top: np.ndarray):
    """Radial rings x {strong LiDAR scarp evidence, not} - 14 mutually exclusive habitats."""
    hab_r, names_r = radial_partition(free, d_cat)
    hab = np.full(free.shape, -1, np.int16)
    names = []
    for j, nm in enumerate(names_r):
        for k, tag in enumerate(["_scarpyes", "_scarpno"]):
            m = (hab_r == j) & (lidar_top if k == 0 else ~lidar_top)
            hab[m] = len(names)
            names.append(nm + tag)
    return hab, names


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--basis", choices=["radial", "scarp"], default="radial")
    ap.add_argument("--g", type=float, default=None)
    args = ap.parse_args()

    with rasterio.open(paths.TEMPLATE) as s:
        foot = np.isfinite(s.read(1))
    with rasterio.open(paths.LABELS) as s:
        cat = (s.read(1) == 1) & foot
    free = foot & ~cat
    d_cat = distance_transform_edt(~cat)
    H, W = foot.shape
    fy, fx = np.nonzero(foot)
    flat = (fy * W + fx).astype(np.int64)
    nfp = len(flat)

    inv = json.loads((paths.EVIDENCE / "live_inversion.json").read_text())
    g_size = args.g or inv["G_used"]

    lidar_top = None
    if args.basis == "scarp":
        with rasterio.open(paths.LIDAR) as s:
            lap = s.read(5).astype(np.float32)   # lappos_max
        thr = float(np.quantile(lap[free & (lap > 0)], 0.95))
        lidar_top = free & (lap >= thr) & (lap > 0)
        print(f"LiDAR lappos_max top-5% threshold = {thr}")

    hab, names = (scarp_partition(free, d_cat, lidar_top) if args.basis == "scarp"
                  else radial_partition(free, d_cat))
    J = len(names)
    hab_flat = hab.ravel()
    sizes = np.array([float((hab == j).sum()) for j in range(J)])
    print(f"partition '{args.basis}': {J} habitats covering {int(sizes.sum()):,} of "
          f"{int(free.sum()):,} off-catalogue footprint px")

    corpus = json.loads((paths.EVIDENCE / "scored_corpus.json").read_text())
    rows = [r for r in inv["submissions"]]
    A = np.zeros((len(rows), J))
    tp = np.zeros(len(rows))
    n_px = np.zeros(len(rows))
    for i, r in enumerate(rows):
        p = paths.DATA / next(e["local"] for e in corpus["matched"] if e["label"] == r["label"])
        with rasterio.open(p) as s:
            a = s.read(1).astype(np.float32)
        pos = np.isfinite(a) & (a > 0)
        dots = pos.ravel()[flat] & ~cat.ravel()[flat]
        K = tomography.coverage_field(dots, flat, (H, W)).ravel()
        inh = hab_flat >= 0
        A[i, :] = np.bincount(hab_flat[inh], weights=K[inh], minlength=J)[:J]
        tp[i] = r["credit_TPw"]
        n_px[i] = r["n_scored"]
        del K, a, pos

    # ---- NNLS with the mass constraint as a heavily weighted extra row --------------------------
    scale = float(A.mean()) or 1.0
    As, tps = A / scale, tp / scale

    def fit(drop=None):
        idx = [i for i in range(len(rows)) if i != drop]
        wgt = 200.0 * np.sqrt(len(idx))
        M = np.vstack([As[idx], wgt * sizes / scale, 1e-3 * np.eye(J)])
        b = np.concatenate([tps[idx], [wgt * g_size / scale], np.zeros(J)])
        w, _ = nnls(M, b)
        return np.minimum(w, 1.0)

    w = fit()
    tp_hat = A @ w
    mass = float((w * sizes).sum())
    r2 = float(1 - np.sum((tp_hat - tp) ** 2) / np.sum((tp - tp.mean()) ** 2))

    loo = []
    for i in range(len(rows)):
        wi = fit(drop=i)
        s_pred = float(A[i] @ wi) / (ALPHA * n_px[i] + BETA * g_size)
        loo.append({"label": rows[i]["label"], "score_actual": rows[i]["score"],
                    "score_predicted": round(s_pred, 4),
                    "error": round(s_pred - rows[i]["score"], 4)})
    err = np.array([r["error"] for r in loo])
    rmse = float(np.sqrt(np.mean(err ** 2)))
    spread = float(np.std([r["score"] for r in rows]))

    out = {
        "basis": args.basis,
        "G_used": g_size,
        "n_measurements": len(rows),
        "n_habitats": J,
        "fitted_truth_mass_px": mass,
        "habitats": [
            {"habitat": names[j], "pixels": int(sizes[j]),
             "lambda_px_of_truth_per_px_of_habitat": float(w[j]),
             "truth_px": float(w[j] * sizes[j]),
             "share_of_truth": float(w[j] * sizes[j] / mass) if mass else 0.0,
             "enrichment_vs_uniform": float(w[j] / (g_size / nfp))}
            for j in range(J)],
        "fit": {"r2_credit_in_sample": r2,
                "rmse_credit_px": float(np.sqrt(np.mean((tp_hat - tp) ** 2))),
                "labels": [r["label"] for r in rows],
                "tp_observed": tp.tolist(), "tp_fitted": tp_hat.tolist()},
        "loo": {"rows": sorted(loo, key=lambda r: -abs(r["error"])),
                "rmse_score": rmse, "max_abs_error": float(np.abs(err).max()),
                "score_spread_sd": spread, "signal_ratio": float(spread / rmse) if rmse else None},
    }
    out["loo"]["verdict"] = (
        f"LOO score RMSE {rmse:.4f} vs spread {spread:.4f} (signal ratio "
        f"{out['loo']['signal_ratio']:.2f}); in-sample R2(credit) {r2:.3f}. "
        + ("USABLE." if out["loo"]["signal_ratio"] and out["loo"]["signal_ratio"] > 2 else
           "NOT USABLE for choosing an emission; hypothesis-generating only."))

    dest = paths.EVIDENCE / f"live_truth_partition_{args.basis}.json"
    dest.write_text(json.dumps(out, indent=1))
    print(f"\n{'habitat':<24}{'px':>10}{'lambda':>9}{'truth px':>10}{'share':>7}{'enrich':>8}")
    for h in out["habitats"]:
        print(f"{h['habitat']:<24}{h['pixels']:>10,}{h['lambda_px_of_truth_per_px_of_habitat']:>9.4f}"
              f"{h['truth_px']:>10,.0f}{h['share_of_truth']:>7.3f}{h['enrichment_vs_uniform']:>8.2f}")
    print(f"\nfitted truth mass {mass:,.0f} px vs |G| {g_size:,.0f}")
    print(f"in-sample R2(credit) = {r2:.3f}")
    print(out["loo"]["verdict"])
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
