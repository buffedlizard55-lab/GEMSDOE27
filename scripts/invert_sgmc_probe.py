#!/usr/bin/env python3
"""Invert the one live score that measures the *far-field* habitat: the H18-4 SGMC-gap probe.

Why this script exists (Session 4)
---------------------------------
`registry/live_scores.json` gained a 21st hash-authenticated (raster, score) pair this session:
16GEMSDOE **H18-4** `gems16-h18-4-usgs-geologic-map-faults-gap-20260930-aef8f42c-nan.tif`,
owner-reported public score **0.0360**. Its construction is recorded by the sibling repository
(`16GEMSDOE docs/data/submissions.json`, candidate key `sgmc-gap`):

    "Faults from the USGS State Geologic Map Compilation (Nevada and California) lying >300 m from
     every catalogue fault, thinned to 1-pixel lines. No model, no training."

That makes it the only submission in the group's history whose emitted pixels are, **by
construction, all at least 300 m from every catalogued fault**. Every other scored surface is a
scarp/ridge detector whose mass sits predominantly beside catalogued structure. So its score is a
direct live measurement of one habitat question that no catalogue-internal holdout can answer:

    Does the organisers' hidden truth G lie on independently-mapped bedrock structure that the
    Quaternary catalogue does not contain?

The answer is read off with the same inversion the corpus uses (`scripts/invert_live_scores.py`):
with the official metric and MPw = sum_x p(x) max_g k(d(x,g)),

    s = TP / (0.2 (TP + N - MP) + 0.8 |G|)   =>   TP(MP) = s (0.2 (N - MP) + 0.8 |G|) / (1 - 0.2 s)

which is *monotone decreasing* in MP, giving hard bounds TP in [TP(MP=N), TP(MP=0)] that need no
assumption about where the truth is, plus the repo's usual uniform-truth closure
(rho = MP/TP = N k_area / (nfp c_S)) as the central value. Concentration
`conc = (TP/|G|) / c_S` compares the probe with a blind (uniform) emission of the same size;
`conc = 1.00` is the lattice floor and the H19-5 family plateaus at 5.3-5.7.

Honesty rules: the score is owner-reported, not a DrivenData receipt; |G| = 12,226 px is the
blind-lattice calibration (an estimate, band 12.2-12.8k); the construction claim is verified here
*from the raster itself*, not trusted. Nothing in this file uploads or reads drivendata.org.

    python scripts/invert_sgmc_probe.py            # -> evidence/sgmc_gap_inversion.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import grid, metric, paths, thinning, tomography  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from optimize_budget import forward_score  # noqa: E402

ALPHA, BETA, R = metric.ALPHA, metric.BETA, metric.RADIUS_PX
PROBE_SHA = "736f62c2da585677ef472cab0f9bc63bd15c50c340beb4a0f4627fafd3d1c853"
PROBE_SCORE = 0.0360
SIBLING_CLAIMED_PX = 57783
# |G| candidates: this repo's blind-lattice calibration and the sibling's two independent estimates.
G_CANDIDATES = {"blind_lattice_this_repo": 12225.896194356133, "sibling_lattice": 12503.0,
                "sibling_pair": 12769.0}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def kernel_area_px() -> float:
    dy = np.arange(-int(np.ceil(R)), int(np.ceil(R)) + 1)
    yy, xx = np.meshgrid(dy, dy, indexing="ij")
    return float(np.maximum(1.0 - np.hypot(yy, xx) / R, 0.0).sum())


def blind_credit(dots_flat: np.ndarray, shape: tuple[int, int], flat: np.ndarray) -> float:
    """c_S = mean over footprint pixels of max_{dot in S} k(d): credit a uniformly spread truth earns."""
    m = np.zeros(shape[0] * shape[1], bool)
    m[flat[dots_flat]] = True
    d = distance_transform_edt(~m.reshape(shape))
    return float(metric.kernel_from_distance(d.reshape(-1)[flat]).mean())


def tp_given_matched_mass(score: float, n: int, mp: float, g: float) -> float:
    """Exact rearrangement of the official metric for a GIVEN matched predicted mass MP.

    s = TP / (0.2 (TP + N - MP) + 0.8 |G|)  =>  TP = s (0.2 (N - MP) + 0.8 |G|) / (1 - 0.2 s).
    Monotone decreasing in MP, so MP in [0, N] brackets TP without any assumption about the truth.
    """
    return score * (ALPHA * (n - mp) + BETA * g) / (1.0 - ALPHA * score)


def tp_uniform_closure(score: float, n: int, rho: float, g: float) -> float:
    """The corpus' central closure: MP = rho*TP with rho from the uniform-truth geometry model.

    Identical to `scripts/invert_live_scores.py` (TP = s(0.2N + 0.8|G|) / (1 - 0.2s + 0.2 s rho)),
    so probe and anchors are inverted with one instrument and are directly comparable.
    """
    return score * (ALPHA * n + BETA * g) / (1.0 - ALPHA * score + ALPHA * score * rho)


def verify_construction(path: Path, foot: np.ndarray, cat: np.ndarray, sgmc: np.ndarray) -> dict:
    """Check the sibling's construction claim from the raster bytes alone."""
    with rasterio.open(path) as s:
        a = s.read(1)
        prof = {"crs_epsg": s.crs.to_epsg() if s.crs else None, "shape": list(s.shape),
                "transform": [round(v, 6) for v in tuple(s.transform)[:6]], "dtype": s.dtypes[0],
                "nodata_is_nan": bool(s.nodata is None or np.isnan(s.nodata)), "count": s.count}
    pos = np.isfinite(a) & (a > 0)
    vals = np.unique(a[np.isfinite(a)])
    in_fp = pos & foot
    d_cat = distance_transform_edt(~cat)
    d = in_fp                      # boolean mask of scored (in-footprint) positives
    # 1-px thinness: no 2x2 block of positives anywhere
    p = pos.astype(np.uint8)
    blocks = (p[:-1, :-1] & p[:-1, 1:] & p[1:, :-1] & p[1:, 1:]).sum()
    sg = sgmc > 0
    d_sg = distance_transform_edt(~sg)
    return {
        "profile": prof,
        "value_set_finite": [float(v) for v in vals[:6]],
        "values_are_0_1_only": bool(np.all((vals == 0) | (vals == 1))),
        "n_positive_in_footprint": int(in_fp.sum()),
        "n_positive_outside_footprint": int((pos & ~foot).sum()),
        "n_positive_on_catalogue_pixels": int((pos & cat).sum()),
        "min_catalogue_distance_px_of_positives": float(d_cat[d].min()) if d.any() else None,
        "frac_positives_at_least_3px_from_catalogue": float((d_cat[d] >= 3.0).mean()) if d.any() else None,
        "frac_positives_at_least_4px_from_catalogue": float((d_cat[d] >= 4.0).mean()) if d.any() else None,
        "n_2x2_positive_blocks": int(blocks),
        "frac_positives_on_restored_sgmc_pixel": float(sg[d].mean()) if d.any() else None,
        "frac_positives_within_1px_of_restored_sgmc": float((d_sg[d] <= 1.0).mean()) if d.any() else None,
        "matches_sibling_claimed_scored_px": int(in_fp.sum()) == SIBLING_CLAIMED_PX,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(paths.EVIDENCE / "sgmc_gap_inversion.json"))
    args = ap.parse_args()

    corpus = json.loads((paths.EVIDENCE / "scored_corpus.json").read_text())
    row = next((m for m in corpus["matched"] if m["sha256"] == PROBE_SHA), None)
    if row is None:
        raise SystemExit(f"probe {PROBE_SHA[:12]} is not in the hash-authenticated corpus; "
                         "run scripts/fetch_scored_corpus.py first")
    probe = paths.DATA / row["local"]
    got = sha256(probe)
    if got != PROBE_SHA:
        raise SystemExit(f"hash mismatch for {probe}: {got}")
    if abs(float(row["score"]) - PROBE_SCORE) > 1e-12:
        raise SystemExit(f"registry score {row['score']} != {PROBE_SCORE}")

    foot = grid.load_footprint(paths.TEMPLATE)
    cat = grid.load_labels(paths.LABELS) & foot
    with rasterio.open(paths.SGMC) as s:
        sgmc = s.read(1)
    shape = grid.SHAPE
    fy, fx = np.nonzero(foot)
    flat = (fy * shape[1] + fx).astype(np.int64)
    nfp = len(flat)
    karea = kernel_area_px()

    checks = verify_construction(probe, foot, cat, sgmc)
    with rasterio.open(probe) as s:
        a = s.read(1)
    dots = (np.isfinite(a) & (a > 0) & foot).ravel()[flat]
    n = int(dots.sum())

    c_S = blind_credit(dots, shape, flat)
    rho_uniform = (n * karea) / (nfp * c_S) if c_S > 0 else float("inf")
    crowd = tomography.crowding(dots, flat, shape)

    # ---- inversion under every |G| candidate and both closures + hard bounds -------------------
    inversions = {}
    for gname, g in G_CANDIDATES.items():
        tp_rho = tp_uniform_closure(PROBE_SCORE, n, rho_uniform, g)
        tp_max = tp_given_matched_mass(PROBE_SCORE, n, 0.0, g)      # MP = 0 (no dot touches truth)
        tp_min = tp_given_matched_mass(PROBE_SCORE, n, float(n), g)  # MP = N (every dot touches truth)
        mp_implied = rho_uniform * tp_rho
        inversions[gname] = {
            "abs_G": g,
            "c_blind_credit_per_truth_px": c_S,
            "credit_if_truth_uniform_TPw": c_S * g,
            "rho_matched_over_TP_uniform_truth": rho_uniform,
            "MPw_implied": mp_implied,
            "TPw_central_uniform_closure": tp_rho,
            "TPw_upper_bound_MP0": tp_max,
            "TPw_lower_bound_MPN": tp_min,
            "concentration_central": (tp_rho / g) / c_S,
            "concentration_upper_bound": (tp_max / g) / c_S,
            "concentration_lower_bound": (tp_min / g) / c_S,
            "credit_fraction_central": tp_rho / g,
        }

    # ---- same instrument applied to the two live anchors, so the probe is read on one scale -----
    anchors = {}
    for label, path, score in (
        ("dotted_h19_5_d1_5 (0.2477)", paths.DOTTED_0_2477, 0.2477),
        ("h19_5_solid (0.1922)", paths.H19_5, 0.1922),
        ("dotted_h19_5_d2_8 (unscored)", paths.DOTTED_D2_8, None),
    ):
        with rasterio.open(path) as s:
            b = s.read(1)
        db = (np.isfinite(b) & (b > 0) & foot & ~cat).ravel()[flat]
        nb = int(db.sum())
        cb = blind_credit(db, shape, flat)
        d_cat = distance_transform_edt(~cat)
        pos_grid = (np.isfinite(b) & (b > 0) & foot & ~cat)
        ring = d_cat[pos_grid]
        rec = {
            "n_scored_px": nb, "c_blind": cb,
            "frac_dots_ge_3px_from_catalogue": float((ring >= 3.0).mean()),
            "frac_dots_ge_10px_from_catalogue": float((ring >= 10.0).mean()),
            "median_dot_catalogue_distance_px": float(np.median(ring)),
        }
        if score is not None:
            rho_b = (nb * karea) / (nfp * cb)
            tp_b = tp_uniform_closure(score, nb, rho_b, G_CANDIDATES["blind_lattice_this_repo"])
            rec["score"] = score
            rec["rho"] = rho_b
            rec["TPw"] = tp_b
            rec["credit_fraction"] = tp_b / G_CANDIDATES["blind_lattice_this_repo"]
            rec["concentration"] = (tp_b / G_CANDIDATES["blind_lattice_this_repo"]) / cb
        anchors[label] = rec

    # ---- instrument check: the same code must reproduce Session 3's published anchor table ------
    published = {"dotted_h19_5_d1_5 (0.2477)": {"credit": 5286.0, "conc": 5.67, "rho": 1.43},
                 "h19_5_solid (0.1922)": {"credit": 6189.0, "conc": 5.66, "rho": 2.46}}
    reproduction = {}
    for k, pub in published.items():
        got = anchors[k]
        reproduction[k] = {
            "credit_TPw_published_session3": pub["credit"], "credit_TPw_this_script": got["TPw"],
            "credit_rel_diff": abs(got["TPw"] - pub["credit"]) / pub["credit"],
            "concentration_published_session3": pub["conc"], "concentration_this_script": got["concentration"],
            "rho_published_session3": pub["rho"], "rho_this_script": got["rho"],
            "reproduced_within_2pct": bool(abs(got["TPw"] - pub["credit"]) / pub["credit"] < 0.02
                                           and abs(got["concentration"] - pub["conc"]) / pub["conc"] < 0.02),
        }

    central = inversions["blind_lattice_this_repo"]

    # ---- what the SGMC-gap habitat could score at ANY budget (live-validated retention rule) -----
    probe_mask = np.zeros(shape, bool)
    probe_mask.ravel()[flat[dots]] = True
    tp_solid = central["TPw_central_uniform_closure"]
    sweep = []
    for d in (1.0, 1.25, 1.5, 2.0, 2.25, 2.8, 3.0, 4.0):
        th = thinning.dot_thin(probe_mask, d) if d > 1.0 else probe_mask.copy()
        nd = int(th.sum())
        cd = blind_credit(th.ravel()[flat], shape, flat)
        rho_d = (nd * karea) / (nfp * cd) if cd > 0 else float("inf")
        tpd = tp_solid * (cd / c_S) if c_S > 0 else 0.0
        sweep.append({"min_dist_px": d, "n_px": nd, "c_blind": cd, "rho": rho_d,
                      "retention_vs_1px_lines": cd / c_S, "credit_TPw_model": tpd,
                      "model_score": forward_score(tpd, nd, rho_d, central["abs_G"])})
    best = max(sweep, key=lambda r: r["model_score"])

    band = (central["concentration_lower_bound"], central["concentration_upper_bound"])
    fam = (5.3, 6.0)
    verdict = (
        f"REFUTED as a route to a higher score. The probe's live score 0.0360 inverts to a credit "
        f"fraction of {central['credit_fraction_central']:.3f} of |G| and a concentration of "
        f"{central['concentration_central']:.2f}x blind (exact bracket {band[0]:.2f}-{band[1]:.2f}x over "
        f"MP in [0, N]), against {fam[0]}-{fam[1]}x for the H19-5 family that produced 0.2477. Even at "
        f"its own best thinning budget the habitat models to {best['model_score']:.4f} "
        f"(d = {best['min_dist_px']} px, {best['n_px']:,} px), i.e. {0.2477 / best['model_score']:.1f}x "
        f"below the 0.2477 file. Independently-mapped bedrock structure with no Quaternary-catalogue "
        f"counterpart is therefore only marginally denser in hidden truth than a uniform spray."
    )
    consequence = (
        "Do not spend a weekly slot on SGMC/geologic-map-gap emission, and do not re-propose it as a "
        "'new data source': the group already spent a slot on it and the score is now inverted. Two "
        "positive facts survive. (1) The far field is NOT empty of truth: 81.4% of the 0.2477 emission's "
        "dots lie >= 300 m from the catalogue and their median distance is 1.5 km, yet that file earns "
        "~6x blind - so what separates 6x from 1.6x is not distance from the catalogue but the detector "
        "that chose the pixels (geomorphic scarp evidence, not lithological map lines). (2) A 1-px line "
        "network has c_S = 0.0384 at N = 57,783, i.e. 2.7x BELOW a uniform spray of the same size: "
        "contiguous lines waste kernel coverage relative to spread dots, which is an independent "
        "confirmation of why dotting wins."
    )
    out = {
        "instrument_reproduction_of_session3_anchors": reproduction,
        "probe": {
            "label": row["label"], "repo": row["repo"], "file": str(probe.relative_to(paths.DATA)),
            "sha256": got, "sha256_matches_registry_and_sibling_record": True,
            "owner_reported_public_score": PROBE_SCORE,
            "score_provenance": "task statement + 16GEMSDOE site listing (owner-reported; not a DrivenData receipt)",
            "construction_claim": "USGS State Geologic Map Compilation (NV+CA) faults >300 m from every "
                                  "catalogue fault, thinned to 1-px lines; no model, no training",
            "external_source": ["https://mrdata.usgs.gov/geology/state/shp/NV.zip",
                                "https://mrdata.usgs.gov/geology/state/shp/CA.zip"],
        },
        "construction_verified_from_raster": checks,
        "emission": {"n_scored_px": n, "crowding_dots_in_kernel": crowd},
        "instrument": {"kernel_area_px": karea, "footprint_px": nfp, "catalogue_px": int(cat.sum()),
                       "restored_sgmc_px_in_footprint": int(((sgmc > 0) & foot).sum())},
        "inversion": inversions,
        "anchors_same_instrument": anchors,
        "probe_thinning_sweep_model": {"rule": "TP(d) = TP_1px * c(d)/c(1px), the retention rule "
                                              "validated live at -0.1% and +4.0% (evidence/budget_optimum.json)",
                                       "sweep": sweep, "best_budget": best,
                                       "status": "MODEL, not a leaderboard score"},
        "reading": {
            "concentration_band": [central["concentration_lower_bound"], central["concentration_upper_bound"]],
            "concentration_central": central["concentration_central"],
            "h19_5_family_concentration": list(fam),
            "verdict": verdict,
            "consequence": consequence,
        },
    }
    Path(args.out).write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({"reproduction": reproduction, "checks": {k: checks[k] for k in (
        "n_positive_in_footprint", "n_positive_on_catalogue_pixels",
        "min_catalogue_distance_px_of_positives", "n_2x2_positive_blocks",
        "frac_positives_on_restored_sgmc_pixel", "matches_sibling_claimed_scored_px")},
        "central_inversion": central, "anchors": {k: {kk: vv for kk, vv in v.items()
                                                      if kk in ("n_scored_px", "score", "concentration",
                                                                "frac_dots_ge_3px_from_catalogue",
                                                                "median_dot_catalogue_distance_px")}
                                                  for k, v in anchors.items()},
        "probe_sweep_best": best, "reading": out["reading"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
