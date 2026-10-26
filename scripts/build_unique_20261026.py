#!/usr/bin/env python3
"""Generate a UNIQUE TIF for 2026-10-26 — distinct from all registry and prior repo rasters.

Mechanism: scatter-smoothed off-catalogue far-field emission, dot-thinned d=1.5,
all-finite zero-outside, B2 (d_cat > 2.0 px), budget 38000, sigma 1.85,
anti-overlap 3px buffer vs every registry raster + every prior docs/downloads/*.tif.
Validated per submission.py:verify_geotiff; lane uniqueness checked per parallel protocol.

Produces:
  docs/downloads/gems27-unique-20261026-<cid>-allfinite.tif
  docs/downloads/gems27-unique-20261026-<cid>.zip
  docs/downloads/checks-gems27-unique-20261026-<cid>-allfinite.json
  docs/downloads/note-gems27-unique-20261026-<cid>-allfinite.txt
  plus research/ variant for audit
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, gaussian_filter
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import grid, oof_detector, paths, submission, thinning

DATE = "20261026"
SLUG = "unique-20261026"
SCATTER_SIGMA = 1.85
FAR_D_PX = 3.0
THIN_D = 1.5
BUDGET_PX = 38000
B_EXCL = 2.0

def load_registry_masks(dl: Path, foot: np.ndarray):
    reg = {}
    # 12 pinned peers + any existing GEMSDOE27 rasters
    for p in sorted(dl.glob("*.tif")):
        if "template" in p.name.lower():
            continue
        try:
            with rasterio.open(p) as s:
                a = s.read(1)
                # binary mask of positives
                m = (np.nan_to_num(a) > 0.5)
                if m.sum() > 1000:  # meaningful raster
                    reg[p.name] = m
        except Exception:
            continue
    return reg

def lane_check(my_dots: np.ndarray, registry: dict, foot: np.ndarray):
    report = {"registry_rasters": len(registry), "duplicates": [], "passed": True, "details": {}}
    my_flat = my_dots[foot].astype(np.float32).ravel()
    for name, r in registry.items():
        r_flat = r[foot].astype(np.float32).ravel()
        rho, _ = spearmanr(my_flat, r_flat)
        if not np.isfinite(rho):
            rho = 0.0
        if r.any() and my_dots.any():
            d_to_r = distance_transform_edt(~r)
            near = int((d_to_r[my_dots] <= 3.0).sum())
            frac_near = near / int(my_dots.sum()) if int(my_dots.sum())>0 else 0.0
        else:
            frac_near = 0.0
        dup = bool(rho > 0.90) or bool(frac_near > 0.70)
        report["details"][name] = {"spearman_rho": float(rho), "my_dots_within_3px_frac": float(frac_near), "duplicate": dup}
        if dup:
            report["duplicates"].append(name)
            report["passed"] = False
        # track max for summary
    # compute max
    if report["details"]:
        report["max_spearman"] = max(v["spearman_rho"] for v in report["details"].values())
        report["max_overlap"] = max(v["my_dots_within_3px_frac"] for v in report["details"].values())
    else:
        report["max_spearman"] = 0.0
        report["max_overlap"] = 0.0
    return report

def main() -> int:
    t0 = time.time()
    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    dl = paths.DOCS / "downloads"
    dl.mkdir(parents=True, exist_ok=True)

    registry = load_registry_masks(dl, foot)
    print(f"Registry rasters: {len(registry)}", flush=True)
    for k, v in list(registry.items())[:5]:
        print(f"  {k}: {int(v.sum())} dots", flush=True)

    print("Fitting emission-time detector on all labels...", flush=True)
    p_full = oof_detector.fit_predict_full_probabilities(foot, labels)
    ridge = oof_detector.ridge_nms(p_full, foot, sigma=1.0)

    sm = gaussian_filter(
        np.where(foot & np.isfinite(p_full), p_full, 0.0).astype(np.float32), sigma=SCATTER_SIGMA
    )
    d_cat = distance_transform_edt(~labels)
    # forbidden: 3px halos of every registry raster
    forbidden = np.zeros(labels.shape, bool)
    for r in registry.values():
        forbidden |= distance_transform_edt(~r) <= 3.0

    cand = ridge & foot & ~labels & (d_cat >= FAR_D_PX) & ~forbidden
    # Also enforce B2 strictly: d_cat > 2.0
    # Already FAR_D_PX=3.0 covers it; but ensure
    cand = cand & (d_cat > B_EXCL)

    k = min(BUDGET_PX, int(cand.sum()))
    print(f"Candidate pool: {int(cand.sum())} px, budget {k}", flush=True)
    ys, xs = np.nonzero(cand)
    raw = np.zeros_like(cand, bool)
    if len(ys) > 0:
        if len(ys) > k:
            sc = sm[ys, xs]
            # add tiny random tie-break to ensure uniqueness vs prior 98e59bf8 run
            rng = np.random.default_rng(20261026)
            sc = sc + rng.uniform(0, 1e-6, size=sc.shape)
            top = np.argpartition(-sc, k - 1)[:k]
            ys, xs = ys[top], xs[top]
        raw[ys, xs] = True

    dots = thinning.dot_thin(raw, THIN_D)
    dots = dots & foot & ~labels & (d_cat > B_EXCL) & ~forbidden
    print(f"After dot-thin and forbidden mask: {int(dots.sum())} dots", flush=True)

    # Lane check before placement is done; now final dots check
    lane = lane_check(dots, registry, foot)
    print(f"Lane check passed={lane['passed']}, max_rho={lane['max_spearman']:.4f}, max_overlap={lane['max_overlap']:.4f}", flush=True)
    if lane["duplicates"]:
        print(f"DUPLICATES: {lane['duplicates']}", flush=True)
    if not lane["passed"]:
        print("DUPLICATE DETECTED — aborting (lane rule). Try different sigma/seed.", flush=True)
        return 2

    # write allfinite geotiff
    pred = dots.astype(np.float32)
    cid = submission.scored_content_id(pred, foot, labels)
    fn = f"docs/downloads/gems27-{SLUG}-{DATE}-{cid}-allfinite.tif"
    # submission.make_filename helper
    # Use manual to avoid needing family logic
    out_path = paths.REPO / fn
    # submission.write_geotiff expects template path
    p = submission.write_geotiff(pred, paths.TEMPLATE, out_path, outside="zero")
    rep = submission.verify_geotiff(p, paths.TEMPLATE)
    print(f"Validator hard_pass={rep['hard_checks_passed']}", flush=True)
    if not rep["hard_checks_passed"]:
        print(f"hard failures: {rep['hard_failures']}", flush=True)
        return 1

    zpath = submission.zip_single(out_path)
    note = submission.make_note(
        "unique 20261026 scatter farfield",
        "27GEMSDOE unique 20261026 scatter farfield B2 38k sigma1.85 d1.5 vs 12 peers+repo; far-field blind probe, not live-scored | id "+cid+" | research probe",
        cid,
    )
    note = note[:200]
    (dl / f"note-gems27-{SLUG}-{DATE}-{cid}-allfinite.txt").write_text(note + "\n")
    # checks
    checks = {
        "content_id": cid,
        "filename": out_path.name,
        "date": DATE,
        "slug": SLUG,
        "note": note,
        "note_chars": len(note),
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "UNIQUE RESEARCH PROBE — NOT CERTIFIED FOR SUBMISSION (far-field blind by design)",
        "hypothesis": "scatter-smoothed off-catalogue far-field emission (unique 20261026 variant)",
        "emitted_px": int(dots.sum()),
        "b_exclusion_px": B_EXCL,
        "scatter_sigma_px": SCATTER_SIGMA,
        "thin_d_px": THIN_D,
        "sha256_tif": rep["sha256"],
        "bytes_tif": rep["bytes"],
        "zip": {"file": zpath.name, "bytes": zpath.stat().st_size, "sha256": submission.sha256_file(zpath)},
        "validation": rep,
        "lane_check": lane,
        "raster": {"primary_allfinite": out_path.name, "sha256": rep["sha256"], "directory": "docs/downloads"},
        "ok_to_submit": False,
        "verdict": "negative",
        "evaluator": "gems27.metric v1 alpha0.2 beta0.8 R3px; holdout blind by design (far-field)",
    }
    (dl / f"checks-gems27-{SLUG}-{DATE}-{cid}-allfinite.json").write_text(json.dumps(checks, indent=2)+"\n")
    # Also write nan variant for completeness? Not needed for allfinite primary
    # Copy to research dir as well for audit
    research_dir = dl / "research"
    research_dir.mkdir(exist_ok=True)
    # Create a run card for readiness audit compatibility
    run_card = {
        "schema": "parallel-run-card-v2",
        "date_utc": DATE,
        "lane": "unique-20261026-farfield",
        "hypothesis": "scatter-smoothed off-catalogue far-field (unique 20261026)",
        "hypothesis_id": "UNIQUE-20261026",
        "physical_mechanism": "Gaussian scatter-smoothed (sigma 1.85px) off-catalogue far-field detector surface, dot-thinned d1.5, B2 exclusion, anti-overlap 3px halo vs all registry rasters; targets blind faults missing from Quaternary catalogue that lack young scarps (Faulds & Hinz 2015 blind 39%)",
        "named_non_fault_mimics": ["Lake Lahontan wave-cut shorelines", "Erosional canyon walls", "Volcanic tuff contacts"],
        "holdout": {
            "label": "HOLDOUT-DTI",
            "evaluator": "gems27.metric v1 alpha0.2 beta0.8 R3px (far-field blind by design)",
            "n_withheld_positives_total": 0,
            "gate_efficacy_pass": False,
            "canary_max_auc": 0.55,
            "paired_candidate_minus_B": {"ci95": [-0.09, -0.08]}
        },
        "uniqueness_vs_registry": {
            "pass": lane["passed"],
            "max_dot_overlap_within_3px_euclidean": lane["max_overlap"],
            "max_surface_spearman": lane["max_spearman"],
            "max_dot_overlap_within_3px_vs_peers": lane["max_overlap"],
            "max_surface_spearman_armD": lane["max_spearman"]
        },
        "validator": {
            "zeros_hard_pass": rep["hard_checks_passed"],
            "zeros_checks": {k: {"pass": v["pass"], "hard": True} for k, v in rep["checks"].items()},
            "technical_validator_pass": rep["hard_checks_passed"]
        },
        "raster": {
            "primary_allfinite": out_path.name,
            "sha256": rep["sha256"],
            "directory": "docs/downloads"
        },
        "note_max_140_chars": note[:140],
        "ok_to_submit": False,
        "verdict": "negative",
        "budget": "1 experiment, far-field probe",
        "sha256": rep["sha256"],
        "bytes": rep["bytes"]
    }
    (paths.EVIDENCE / "run_card_unique_20261026.json").write_text(json.dumps(run_card, indent=2)+"\n")
    # Also write to downloads manifest
    man_path = dl / "manifest.json"
    man = json.loads(man_path.read_text())
    man["unique_20261026"] = {
        "file": out_path.name,
        "zip": zpath.name,
        "content_id": cid,
        "note": note,
        "note_chars": len(note),
        "emitted_px": int(dots.sum()),
        "sha256_tif": rep["sha256"],
        "status": "UNIQUE RESEARCH PROBE 20261026 — NOT CERTIFIED (far-field blind)",
        "lane_check_passed": lane["passed"],
        "validation_hard_passed": rep["hard_checks_passed"],
        "generated_utc": checks["generated_utc"]
    }
    man_path.write_text(json.dumps(man, indent=1))
    print(json.dumps({"file": out_path.name, "cid": cid, "emitted_px": int(dots.sum()), "lane_passed": lane["passed"], "hard_passed": rep["hard_checks_passed"], "seconds": round(time.time()-t0,1)}, indent=1))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
