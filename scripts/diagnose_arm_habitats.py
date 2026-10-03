#!/usr/bin/env python3
"""Where does an arm's holdout gain actually come from? (Addendum D diagnostic, run after the gate.)

The Addendum-D holdout hides 20 % of the *catalogue* per cell. A dot can therefore earn credit in two
structurally different places:

* **Habitat A - `d_cat_full >= 3 px` (>= 300 m from the FULL published catalogue).** These dots can
  exist in a real submission (`scripts/verify_downloads.py` requires 0 pixels on catalogue cells). The
  only live measurement this programme has of this habitat is 16GEMSDOE H18-4, the SGMC-gap probe:
  57,783 px, all >= 300 m from the catalogue, owner-reported score 0.0360, inverted concentration
  1.62x blind (bracket 0.76-1.65x) against 5.3-6.0x for the H19-5 family
  (`evidence/sgmc_gap_inversion.json`).
* **Habitat B - `d_cat_full < 3 px` but `>= 3 px` from the cell's KNOWN catalogue.** These dots are
  only possible because the experiment hides part of the catalogue. A real submission cannot contain
  them: at prediction time the whole catalogue is known and is masked out of every emission. Any gain
  measured here is an artefact of catalogue-internal truth and cannot be shipped.

So the shippable part of an arm's improvement is its Habitat-A improvement, and this script measures
the two separately, plus the DTI of each arm after removing every Habitat-B dot (the emission a real
file could contain). It re-uses the exact cells of the registered gate (seeds 140-149) and the saved
out-of-fold probability/ridge arrays, so it trains nothing.

Usage: GEMS_DATA_DIR=/home/user/GEMSDOE27/data_cache .venv/bin/python scripts/diagnose_arm_habitats.py
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
from gems27 import grid, holdout, metric, oof_detector, paths  # noqa: E402


def eval_set(pred: np.ndarray, g: np.ndarray, active: np.ndarray, k_pt: np.ndarray):
    p = pred & active
    n_g = int(g.sum())
    if not p.any() or n_g == 0:
        return 0.0, (float((1.0 - k_pt[p]).sum()) if p.any() else 0.0), 0.0, int(p.sum())
    tp = float(metric.kernel_from_distance(distance_transform_edt(~p)[g]).sum())
    fp = float((1.0 - k_pt[p]).sum())
    return tp, fp, tp / (tp + 0.2 * fp + 0.8 * (n_g - tp) + 1e-7), int(p.sum())


def pooled(rows: list[dict], key: str) -> dict:
    if not rows or key not in rows[0]:
        return {}
    tp = sum(r[key]["tp"] for r in rows)
    fp = sum(r[key]["fp"] for r in rows)
    return {"credit_TP": tp, "fp_weight": fp, "efficiency": tp / fp if fp else 0.0,
            "mean_dti": float(np.mean([r[key]["dti"] for r in rows])),
            "n_dots": int(sum(r[key]["dots"] for r in rows))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="140-149")
    ap.add_argument("--arms", default="base,sgmc,all")
    ap.add_argument("--out", default=str(paths.EVIDENCE / "arm_habitat_decomposition.json"))
    args = ap.parse_args()
    a, _, b = args.seeds.partition("-")
    seeds = list(range(int(a), int(b) + 1)) if b else [int(a)]
    arms = [x.strip() for x in args.arms.split(",") if x.strip()]
    t0 = time.time()

    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    fold = holdout.make_quadrant_folds(foot)
    # distance to the FULL published catalogue: the line a real submission may not cross
    d_cat_full = distance_transform_edt(~labels)

    probs = {arm: np.load(paths.DATA / "prepared" / f"oof_prob_d_{arm}.npy", mmap_mode="r") for arm in arms}
    ridges = {arm: np.load(paths.DATA / "prepared" / f"oof_ridge_d_{arm}.npy") for arm in arms}

    cells: list[dict] = []
    for seed in seeds:
        for f in range(4):
            sp = holdout.make_split(labels, fold, f, seed)
            fm = sp.fold_mask
            sl = holdout.crop(None, fm)
            hid, kn, fmc = sp.hidden[sl], (sp.known & fm)[sl], fm[sl]
            g = hid & fmc & ~kn
            active = fmc & ~kn
            k_pt = metric.kernel_from_distance(distance_transform_edt(~g)) if g.any() else np.zeros_like(g, float)
            dc = d_cat_full[sl]
            habA = dc >= metric.RADIUS_PX          # shippable: >= 300 m from the whole catalogue
            habB = ~habA                           # artefact: only exists because truth is hidden
            bands = {"d0_on_spine": dc < 0.5, "d1_100m": (dc >= 0.5) & (dc < 1.5),
                     "d2_200m": (dc >= 1.5) & (dc < 2.5), "d3to10": (dc >= 2.5) & (dc < 10.5),
                     "dgt10": dc >= 10.5}

            row = {"seed": seed, "fold": sp.name, "n_truth": int(g.sum()),
                   "n_truth_habitat_A": int((g & habA).sum()), "n_truth_habitat_B": int((g & habB).sum()),
                   "n_truth_by_band": {k: int((g & m).sum()) for k, m in bands.items()}}
            for arm in arms:
                dots = oof_detector.build_oof_dotted_base(
                    np.asarray(probs[arm])[sl], ridges[arm][sl], fmc, kn,
                    budget_frac=oof_detector.PRE_THIN_FRAC, thin_d=1.5) & active
                for tag, m in (("", dots), ("_habitatA", dots & habA), ("_habitatB", dots & habB)):
                    tp, fp, dti, n = eval_set(m, g, active, k_pt)
                    row[f"{arm}{tag}"] = {"tp": tp, "fp": fp, "dti": dti, "dots": n}
                # the emission a real submission could contain: Habitat-A dots only
                tp, fp, dti, n = eval_set(dots & habA, g, active, k_pt)
                row[f"{arm}_shippable"] = {"tp": tp, "fp": fp, "dti": dti, "dots": n}
                for bn, bm in bands.items():
                    tp, fp, dti, n = eval_set(dots & bm, g, active, k_pt)
                    row[f"{arm}_band_{bn}"] = {"tp": tp, "fp": fp, "dti": dti, "dots": n}
            cells.append(row)
        print(f"seed {seed} done t={time.time()-t0:.0f}s", flush=True)

    out = {
        "preregistration": ("diagnostic, NOT a gate: it decomposes the registered Addendum-D result on "
                            "the same cells (seeds 140-149) into the habitat a real submission can "
                            "occupy (>= 300 m from the whole published catalogue) and the habitat that "
                            "exists only because the experiment hides catalogue pixels"),
        "seeds": seeds, "arms": arms, "seconds": time.time() - t0,
        "habitat_definition": {
            "A": "d(dot, FULL published catalogue) >= 3 px (300 m): shippable; live-measured once by "
                 "16GEMSDOE H18-4 (SGMC-gap probe, 0.0360, concentration 1.62x blind)",
            "B": "d(dot, FULL catalogue) < 3 px: cannot exist in a real file (verify_downloads.py "
                 "requires 0 pixels on catalogue cells); its credit is pure catalogue-internal truth",
        },
        "truth_split": {"habitat_A": int(sum(c["n_truth_habitat_A"] for c in cells)),
                        "habitat_B": int(sum(c["n_truth_habitat_B"] for c in cells)),
                        "by_band": {bn: int(sum(c["n_truth_by_band"][bn] for c in cells))
                                    for bn in ("d0_on_spine", "d1_100m", "d2_200m", "d3to10", "dgt10")},
                        "structural_note": ("Hidden truth in this proxy is made of catalogue pixels, so "
                                            "100% of it lies at d(full catalogue) = 0 and Habitat A "
                                            "contains no truth BY CONSTRUCTION. The proxy can therefore "
                                            "only ever reward dots placed next to the published "
                                            "catalogue; it is blind to the far-field habitat that the "
                                            "live scores say carries most of the real credit (81.4% of "
                                            "the 0.2477 emission's dots are >= 300 m from the "
                                            "catalogue). This is the quantitative form of the standing "
                                            "caveat 'catalogue-internal truth overstates real-world "
                                            "enrichment'.")},
        "pooled": {}, "per_arm": {}, "verdict": {},
    }
    band_names = ["d0_on_spine", "d1_100m", "d2_200m", "d3to10", "dgt10"]
    for arm in arms:
        for bn in band_names:
            out["pooled"][f"{arm}_band_{bn}"] = pooled(cells, f"{arm}_band_{bn}")
        for tag in ("", "_habitatA", "_habitatB", "_shippable"):
            out["pooled"][f"{arm}{tag}"] = pooled(cells, f"{arm}{tag}")
        gains = {fn: float(np.mean([c[f"{arm}"]["dti"] - c["base"]["dti"] for c in cells if c["fold"] == fn]))
                 for fn in sorted({c["fold"] for c in cells})} if arm != "base" else {}
        gains_A = {fn: float(np.mean([c[f"{arm}_habitatA"]["dti"] - c["base_habitatA"]["dti"]
                                      for c in cells if c["fold"] == fn]))
                   for fn in sorted({c["fold"] for c in cells})} if arm != "base" else {}
        out["per_arm"][arm] = {
            "mean_paired_gain_vs_base": (float(np.mean([c[arm]["dti"] - c["base"]["dti"] for c in cells]))
                                         if arm != "base" else 0.0),
            "per_fold_gain": gains,
            "mean_paired_gain_habitatA_only": (float(np.mean([c[f"{arm}_habitatA"]["dti"]
                                                              - c["base_habitatA"]["dti"] for c in cells]))
                                               if arm != "base" else 0.0),
            "per_fold_gain_habitatA_only": gains_A,
            "share_of_dots_in_habitat_B": float(out["pooled"][f"{arm}_habitatB"]["n_dots"]
                                                / max(out["pooled"][arm]["n_dots"], 1)),
            "share_of_credit_in_habitat_B": float(out["pooled"][f"{arm}_habitatB"]["credit_TP"]
                                                  / max(out["pooled"][arm]["credit_TP"], 1e-9)),
            "dots_by_band": {bn: out["pooled"][f"{arm}_band_{bn}"]["n_dots"] for bn in band_names},
            "credit_by_band": {bn: round(out["pooled"][f"{arm}_band_{bn}"]["credit_TP"], 1)
                               for bn in band_names},
            "efficiency_by_band": {bn: round(out["pooled"][f"{arm}_band_{bn}"]["efficiency"], 5)
                                   for bn in band_names},
        }
    out["verdict"] = {
        "shippable_habitat_A_efficiency": {arm: out["pooled"][f"{arm}_habitatA"]["efficiency"] for arm in arms},
        "shippable_habitat_A_mean_dti": {arm: out["pooled"][f"{arm}_habitatA"]["mean_dti"] for arm in arms},
        "note": ("Read the Habitat-A columns as the only part of an arm that could reach a submission, "
                 "and compare them with the live-anchored concentration of the H19-5 family (5.3-6.0x "
                 "blind) and of the SGMC-gap probe (1.62x blind)."),
    }
    Path(args.out).write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
