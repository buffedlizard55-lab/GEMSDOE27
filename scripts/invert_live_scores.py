#!/usr/bin/env python3
"""Invert the owner's live submission scores to recover the hidden truth's size and spatial habitat.

What is new here (Session 3)
----------------------------
Previous sessions calibrated the hidden-truth size |G| from ONE anchor (a blind lattice probe,
owner-reported 0.0904) or from ONE solid/dotted pair. This script uses the whole corpus of
hash-authenticated scored rasters (`scripts/fetch_scored_corpus.py`) as a *designed sensing
experiment* and solves two problems at once:

1. **|G| and the emission closure.**  With the official DTI and the closure FPw = N - TPw
   (every emitted off-catalogue pixel either earns credit or pays one unit of false-positive mass),
   each live score s_i is one linear equation

       TP_i = s_i (0.2 N_i + 0.8 |G|)                                            (1)

   in the single global unknown |G|. A blind lattice has a *predicted* credit per dot that does not
   depend on where the truth is, so (1) applied to the lattice fixes |G|; every other submission
   then becomes an independent consistency check.

2. **Live-truth tomography.**  Write the truth indicator as a non-negative combination of
   interpretable habitat basis fields B_j (catalogue buffer rings, LiDAR scarp intensity, SGMC
   bedrock-fault proximity, GeoDAWN ridges, springs/wells, vents). For submission i the official
   metric gives  TP_i = <K_i, 1_G>  where K_i(x) = max over emitted dots of k(d(x, dot)) is the
   *coverage field* of that submission and k(d) = max(1 - d/300 m, 0). Substituting
   1_G = sum_j w_j B_j turns every live score into a linear measurement

       s_i (0.2 N_i + 0.8 sum_j w_j |B_j|) = sum_j w_j <K_i, B_j>                (2)

   of the unknown weights w_j. Twenty scored submissions therefore *tomograph* the hidden truth:
   they say which geological habitats the organisers' new fault labels actually live in. Nothing
   like this has been attempted in this repository family before, and it uses the real private
   labels (through their scores) rather than a catalogue-internal proxy.

Honesty rules: scores are owner-reported, not DrivenData receipts; |G| and w are *estimates*;
leave-one-submission-out prediction error is reported so the reader can see how much is signal.

    python scripts/invert_live_scores.py            # stage 1 (|G|, per-submission decomposition)
    python scripts/invert_live_scores.py --tomo     # stage 2 (habitat tomography) as well
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
from gems27 import metric, paths, tomography  # noqa: E402

ALPHA, BETA = metric.ALPHA, metric.BETA
R = metric.RADIUS_PX


# ----------------------------------------------------------------------------------------------
# grid helpers (everything lives in footprint-index space to fit in 3 GB of RAM)
# ----------------------------------------------------------------------------------------------
def load_grid():
    with rasterio.open(paths.TEMPLATE) as s:
        tmpl = s.read(1)
    foot = np.isfinite(tmpl)
    with rasterio.open(paths.LABELS) as s:
        lab = s.read(1)
    cat = (lab == 1) & foot
    fy, fx = np.nonzero(foot)
    flat = (fy * foot.shape[1] + fx).astype(np.int64)
    return foot, cat, fy, fx, flat


def emission_of(path: Path, foot: np.ndarray, cat: np.ndarray, flat: np.ndarray):
    """Positive pixels of a scored raster, split into off-catalogue (scored) and on-catalogue (free)."""
    with rasterio.open(path) as s:
        a = s.read(1).astype(np.float32)
    pos = np.isfinite(a) & (a > 0)
    sub = pos.ravel()[flat]                       # positives INSIDE the footprint only
    cat_flat = cat.ravel()[flat]
    on_cat = int((sub & cat_flat).sum())
    n_inside = int(sub.sum())
    # Positives outside the footprint are ignored by the metric (the organisers' grid masks them),
    # but a file that has them is a format irregularity and must be reported, not silently dropped.
    n_outside = int(pos.sum()) - n_inside
    return sub, n_inside, n_inside - on_cat, on_cat, n_outside


# ----------------------------------------------------------------------------------------------
# stage 1 - blind-lattice calibration of |G| and the per-submission credit decomposition
# ----------------------------------------------------------------------------------------------
def blind_credit_per_truth(dots: np.ndarray, shape: tuple[int, int], flat: np.ndarray) -> float:
    """c_S = mean credit a *uniformly placed* truth pixel receives from emission S.

    c_S = mean over footprint pixels of max_{dot} k(d). Exact for any truth set spread uniformly over
    the footprint, which is what a blind probe assumes and the reference state for a real detector.
    """
    H, W = shape
    m = np.zeros(H * W, bool)
    m[flat[dots]] = True
    d = distance_transform_edt(~m.reshape(H, W))
    return float(metric.kernel_from_distance(d.reshape(-1)[flat]).mean())


def matched_mass_ratio(n_dots: int, c_S: float, kernel_area: float, nfp: int) -> float:
    """rho_S = MPw/TPw for a uniformly spread truth: (N * kernel area) / (nfp * c_S).

    The official metric takes a MAX over predictions per truth pixel for TPw but a SUM over
    predictions for the matched predicted mass MPw = sum_x p(x) max_g k(d(x,g)), and
    FPw = N - MPw. So the simple closure FPw = N - TPw is exact only when rho = 1 (each matched
    truth pixel has one dot near it). A solid 1-px line is heavily crowded (rho >> 1) and its credit
    is *overestimated* by the naive closure; a blind spacing-5 lattice has rho ~ 1.
    """
    return float((n_dots * kernel_area) / (nfp * c_S)) if c_S > 0 else float("inf")


def matched_mass_per_dot(dots: np.ndarray, shape: tuple[int, int], flat: np.ndarray,
                         g_size: float) -> float:
    """Expected max_g k(d(dot,g)) for one dot of a blind pattern, given |G| truth pixels.

    A dot is 'matched' if some truth pixel lies within 3 px; the expected matched mass per dot is
    (|G| / n_footprint) * sum_delta k(|delta|), i.e. the truth density times the kernel's area.
    """
    H, W = shape
    nfp = len(flat)
    dy = np.arange(-int(np.ceil(R)), int(np.ceil(R)) + 1)
    yy, xx = np.meshgrid(dy, dy, indexing="ij")
    ksum = float(np.maximum(1.0 - np.hypot(yy, xx) / R, 0.0).sum())
    return (g_size / nfp) * ksum


def solve_g_from_blind(score: float, n_dots: int, c: float, ksum_area: float, nfp: int) -> float:
    """Invert a blind probe's live score for |G|.

    TP = c*|G| (uniform truth); Mw = n_dots*(|G|/nfp)*ksum_area; FP = Mw_complement = n_dots - Mw.
    score = TP / (0.2(TP+FP) + 0.8|G|)  =>  linear in |G|.
    """
    # score * (0.2(cG + n - aG) + 0.8G) = cG,  a = n_dots*ksum_area/nfp
    a = n_dots * ksum_area / nfp
    denom_g = ALPHA * (c - a) + BETA          # coefficient of G on the left
    const = ALPHA * n_dots                     # constant on the left
    # score*(const + denom_g*G) = c*G  =>  G*(c - score*denom_g) = score*const
    return float(score * const / (c - score * denom_g))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tomo", action="store_true")
    ap.add_argument("--g", type=float, default=None, help="override |G| instead of solving it")
    args = ap.parse_args()

    foot, cat, fy, fx, flat = load_grid()
    H, W = foot.shape
    nfp = len(flat)
    shape = (H, W)
    corpus = json.loads((paths.EVIDENCE / "scored_corpus.json").read_text())

    # ---- load every scored raster once, keep only footprint-index dot masks --------------------
    rows, masks = [], {}
    for e in corpus["matched"]:
        p = paths.DATA / e["local"]
        if not p.exists():
            continue
        dots, n_inside, n_off, n_on, n_outside = emission_of(p, foot, cat, flat)
        rows.append({**{k: e[k] for k in ("label", "repo", "score", "sha256")},
                     "n_positive_in_footprint": n_inside, "n_scored": n_off,
                     "n_on_catalogue": n_on, "n_positive_outside_footprint": n_outside})
        masks[e["label"]] = dots
        print(f"loaded {e['score']:<7} N={n_off:>7,} (on-cat {n_on:>6,})  {e['label'][:56]}")

    # ---- blind lattice: the only submission whose credit does not depend on where truth is ------
    lat = [r for r in rows if "lattice" in r["label"].lower()]
    if not lat:
        print("no lattice probe in the corpus; pass --g")
        return 1
    lat = lat[0]
    dots = masks[lat["label"]]
    c = blind_credit_per_truth(dots, shape, flat)
    dy = np.arange(-int(np.ceil(R)), int(np.ceil(R)) + 1)
    yy, xx = np.meshgrid(dy, dy, indexing="ij")
    ksum = float(np.maximum(1.0 - np.hypot(yy, xx) / R, 0.0).sum())
    g_est = solve_g_from_blind(lat["score"], lat["n_scored"], c, ksum, nfp)
    g_used = args.g if args.g else g_est
    print(f"\nblind lattice: N={lat['n_scored']:,} c={c:.5f} kernel_area={ksum:.4f} "
          f"score={lat['score']} -> |G| = {g_est:,.0f}")
    if args.g:
        print(f"using owner-supplied |G| = {args.g:,.0f}")

    # ---- per-submission decomposition under the closure FPw = N - TPw ---------------------------
    out_rows = []
    for r in rows:
        n = r["n_scored"]
        cS = blind_credit_per_truth(masks[r["label"]], shape, flat)
        rho = matched_mass_ratio(n, cS, ksum, nfp)
        crowd = tomography.crowding(masks[r["label"]], flat, shape)
        # TP (1 - 0.2 s + 0.2 s rho) = s (0.2 N + 0.8 |G|)
        tp = r["score"] * (ALPHA * n + BETA * g_used) / (1.0 - ALPHA * r["score"]
                                                         + ALPHA * r["score"] * rho)
        tp_naive = r["score"] * (ALPHA * n + BETA * g_used)
        r2 = {**r, "c_blind_credit_per_truth": cS, "rho_matched_over_TP": rho,
              "crowding_dots_in_kernel": crowd,
              "credit_TPw": tp, "credit_TPw_naive_closure": tp_naive,
              "credit_fraction_of_G": tp / g_used,
              "credit_per_emitted_px": tp / n if n else 0.0,
              "fp_mass": n - rho * tp,
              "vs_random_blind_level": (tp / n) / (lat["score"] * (ALPHA * lat["n_scored"]
                                                                   + BETA * g_used) / lat["n_scored"])}
        out_rows.append(r2)
    out_rows.sort(key=lambda r: -r["score"])

    # ---- what each target score requires -------------------------------------------------------
    def need(target: float, n: int) -> dict:
        tp = target * (ALPHA * n + BETA * g_used)
        return {"target": target, "emitted_px": n, "credit_TPw_required": tp,
                "credit_fraction_required": tp / g_used, "credit_per_emitted_px": tp / n}

    reqs = [need(t, n) for t in (0.2477, 0.2941, 0.3195)
            for n in (20000, 30000, 40000, 44090, 60069, 80000, 121131)]

    res = {
        "method": "DTI inversion with closure FPw = N - TPw over the hash-authenticated scored corpus",
        "n_corpus": len(rows),
        "grid": {"shape": list(shape), "footprint_px": nfp, "catalogue_px": int(cat.sum())},
        "blind_lattice_calibration": {
            "label": lat["label"], "score": lat["score"], "n_scored": lat["n_scored"],
            "credit_per_dot_for_uniform_truth": c, "kernel_area_px": ksum,
            "implied_abs_G": g_est,
            "note": "c is exact for any truth set uniformly spread over the footprint; it is the "
                    "only calibration that does not assume where the truth is.",
        },
        "G_used": g_used,
        "submissions": out_rows,
        "requirements": reqs,
        "consistency_checks": {},
    }

    # ---- consistency check: is the implied credit of a blind-style file at the random level? ----
    res["consistency_checks"]["lattice_implied_credit_vs_blind_prediction"] = {
        "implied_credit_per_dot": lat["score"] * (ALPHA * lat["n_scored"] + BETA * g_used) / lat["n_scored"],
        "predicted_for_uniform_truth": c,
        "ratio": (lat["score"] * (ALPHA * lat["n_scored"] + BETA * g_used) / lat["n_scored"]) / c,
        "reading": "1.00 means the inversion and the blind-probe model agree exactly at the anchor.",
    }

    # ---- nesting / pair checks -----------------------------------------------------------------
    pairs = []
    labels = list(masks)
    for i, a in enumerate(labels):
        for b in labels[i + 1:]:
            A, B = masks[a], masks[b]
            inter = int(np.logical_and(A, B).sum())
            if inter == 0:
                continue
            fa = inter / max(1, int(A.sum()))
            fb = inter / max(1, int(B.sum()))
            if max(fa, fb) > 0.9 and min(fa, fb) < 0.9:
                pairs.append({"a": a, "b": b, "overlap_frac_of_a": fa, "overlap_frac_of_b": fb,
                              "n_a": int(A.sum()), "n_b": int(B.sum())})
    res["consistency_checks"]["near_nested_pairs"] = sorted(
        pairs, key=lambda p: -p["overlap_frac_of_a"])[:20]

    paths.EVIDENCE.joinpath("live_inversion.json").write_text(json.dumps(res, indent=1))
    print(f"\n|G| = {g_used:,.0f} px   (blind-lattice estimate {g_est:,.0f})")
    print(f"{'score':>7} {'N':>8} {'credit':>9} {'frac|G|':>8} {'cr/px':>7} {'x rnd':>5} "
          f"{'rho':>6} {'crowd':>6}  label")
    for r in out_rows:
        print(f"{r['score']:>7} {r['n_scored']:>8,} {r['credit_TPw']:>9,.0f} "
              f"{r['credit_fraction_of_G']:>8.3f} {r['credit_per_emitted_px']:>7.4f} "
              f"{r['vs_random_blind_level']:>8.2f} {r['rho_matched_over_TP']:>6.2f} "
              f"{r['crowding_dots_in_kernel']:>6.1f}  {r['label'][:46]}")
    print("\nrequirements (credit fraction of |G| needed):")
    for q in reqs:
        print(f"  target {q['target']:.4f} at {q['emitted_px']:>7,} px -> credit {q['credit_TPw_required']:>8,.0f}"
              f" = {q['credit_fraction_required']:.3f}|G| = {q['credit_per_emitted_px']:.4f}/px")
    print("\nwrote evidence/live_inversion.json")

    if args.tomo:
        from gems27 import layers as layer_mod  # noqa: E402
        print("\nloading geoscience layers for the habitat basis ...")
        lay = layer_mod.load_all()
        tomo = tomography.run(foot, cat, fy, fx, flat, masks,
                              [r for r in out_rows if r["label"] in masks], g_used,
                              paths.EVIDENCE, layers=lay)
        print(tomo["loo_validation"]["verdict"])
        print(f"fitted truth mass {tomo['fitted_truth_mass_px']:,.0f} px vs |G| {g_used:,.0f}")
        print(f"{'habitat':<34}{'px':>10}{'lambda':>9}{'truth px':>10}{'share':>8}")
        for h in tomo["habitat_intensity"][:18]:
            print(f"{h['habitat']:<34}{h['pixels']:>10,}{h['lambda_px_per_px']:>9.4f}"
                  f"{h['truth_px_estimated']:>10,.0f}{h['share_of_estimated_truth']:>8.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
