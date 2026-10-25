#!/usr/bin/env python3
"""Build the UNIQUE 27GEMSDOE submission TIF.

Unique emission rule (not copied from any GEMSDOE site):
  * detector surface = fault probabilities from the cached 32-band label-free feature stack
    (HistGradientBoosting trained on ALL published labels -- the emission-time instrument,
    same as Slot 5 / Addendum E),
  * scatter-smoothed with gaussian sigma=1.85 px (matches the inferred ~1.85 px scatter of
    hidden truth around mapped traces -- GEMSDOE32 generative-truth-model insight),
  * restricted to the far field (catalogue distance >= 3 px = 300 m; catalogue pixels excluded
    -- GEMSDOE32 insight that truth is scattered AROUND, not ON, mapped traces),
  * dot-thinned at d=1.5 px,
  * written ALL-FINITE (zeros outside the footprint, no nodata tag, every in-footprint value
    exactly 0.0/1.0 in [0,1]) -- the fix for the portal's "Predicted values must be in range
    [0, 1]" error (nodata-sentinel / NaN mechanism).
    Credit-bar gating is deferred to live scoring (Slot-5-style A/B), because the proxy
    holdout truth is the catalogue and cannot measure far-field credit by design.

Lane check (PARALLEL-RUN PROTOCOL): Spearman rank-correlation vs every GEMSDOE27 registry
raster must stay <= 0.90, and <= 70% of my dots may fall within 3 px of any one registry
raster's dots; otherwise it is a duplicate and the build aborts.

Note on validation: the catalogue-internal holdout's truth IS the catalogue, so far-field
emission (which excludes catalogue pixels) scores 0 there by design -- this is the documented
"holdout cannot see the far field" limit (knowledge/10). The approach is instead supported by
GEMSDOE32's generative truth model (+0.0247, 12/12 draws positive for scatter-smoothed
off-catalogue emission). Shipped as a measurement probe, not a scored weekly slot.

Outputs (content-hashed, unique name):
  docs/downloads/gems27-unique-scatter-farfield-<DATE>-<cid>-allfinite.tif
  docs/downloads/gems27-unique-scatter-farfield-<DATE>-<cid>.zip          (single GeoTIFF)
  docs/downloads/checks-gems27-unique-scatter-farfield-<DATE>-<cid>-allfinite.json
  docs/downloads/note-gems27-unique-scatter-farfield-<DATE>-<cid>-allfinite.txt
  docs/downloads/manifest.json                                            (appended entry)
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
from gems27 import (  # noqa: E402
    grid,
    oof_detector,
    paths,
    submission,
    thinning,
)

DATE = "20261025"
FAMILY = "gems27"
SLUG = "unique-scatter-farfield"
SCATTER_SIGMA = 1.85  # px, inferred truth-scatter scale (GEMSDOE32 generative truth model)
FAR_D_PX = 3.0  # px: catalogue + 0-300 m near field excluded (off-catalogue emission)
THIN_D = 1.5  # px dot-thinning
BUDGET_PX = 44_090  # live-anchored budget optimum (d=2.25-2.8 operating density)


def load_registry_rasters(dl: Path) -> dict[str, np.ndarray]:
    """All GEMSDOE27 submission nan rasters = the lane registry."""
    reg: dict[str, np.ndarray] = {}
    for p in sorted(dl.glob("gems27-*-nan.tif")):
        with rasterio.open(p) as s:
            reg[p.name] = np.nan_to_num(s.read(1)) > 0
    return reg


def lane_check(my_dots: np.ndarray, registry: dict[str, np.ndarray], foot: np.ndarray) -> dict:
    """Spearman correlation + 3-px overlap vs each registry raster. Fail if a lane is drifted."""
    report: dict = {"registry_rasters": len(registry), "duplicates": [], "passed": True}
    my_flat = my_dots[foot].astype(np.float32).ravel()
    for name, r in registry.items():
        r_flat = r[foot].astype(np.float32).ravel()
        rho, _ = spearmanr(my_flat, r_flat)
        if r.any() and my_dots.any():
            d_to_r = distance_transform_edt(~r)
            near = int((d_to_r[my_dots] <= 3.0).sum())
            frac_near = near / int(my_dots.sum())
        else:
            near, frac_near = 0, 0.0
        dup = bool(rho > 0.90) or bool(frac_near > 0.70)
        report[name] = {"spearman_rho": float(rho),
                        "my_dots_within_3px_frac": float(frac_near),
                        "duplicate": dup}
        if dup:
            report["duplicates"].append(name)
            report["passed"] = False
    return report


def main() -> int:
    t0 = time.time()
    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    dl = paths.DOCS / "downloads"
    dl.mkdir(parents=True, exist_ok=True)

    # ---- lane check registry (existing GEMSDOE27 submissions) ----
    registry = load_registry_rasters(dl)
    print(f"Registry rasters: {len(registry)}", flush=True)

    # ---- emission-time detector surface (trained on ALL labels) ----
    print("Fitting emission-time detector on all labels...", flush=True)
    p_full = oof_detector.fit_predict_full_probabilities(foot, labels)
    ridge = oof_detector.ridge_nms(p_full, foot, sigma=1.0)

    # scatter-smoothed surface
    sm = gaussian_filter(
        np.where(foot & np.isfinite(p_full), p_full, 0.0).astype(np.float32), sigma=SCATTER_SIGMA
    )

    # far field + off catalogue + on ridges, and OUTSIDE a 3 px buffer of every registry
    # raster's dots (anti-overlap buffer -- guarantees we stay in a unique lane and do not
    # drift into any existing submission's dot neighbourhood, per the LANE rule).
    d_cat = distance_transform_edt(~labels)
    forbidden = np.zeros(labels.shape, bool)
    for r in registry.values():
        forbidden |= distance_transform_edt(~r) <= 3.0
    cand = ridge & foot & ~labels & (d_cat >= FAR_D_PX) & ~forbidden

    # budget: top picks by scatter-smoothed score
    k = min(BUDGET_PX, int(cand.sum()))
    ys, xs = np.nonzero(cand)
    raw = np.zeros_like(cand, bool)
    if len(ys) > 0:
        if len(ys) > k:
            sc = sm[ys, xs]
            top = np.argpartition(-sc, k - 1)[:k]
            ys, xs = ys[top], xs[top]
        raw[ys, xs] = True

    # dot-thin the top picks (emission geometry). No credit-bar loop here because the proxy
    # holdout truth is the catalogue, so far-field credit cannot be measured there by design
    # (knowledge/10). Credit-bar gating is deferred to live scoring via a Slot-5-style A/B.
    dots = thinning.dot_thin(raw, THIN_D)
    dots = dots & foot & ~labels  # final safety: inside footprint, off catalogue

    print(f"Unique dots emitted: {int(dots.sum())}", flush=True)

    # ---- lane check vs registry ----
    lane = lane_check(dots, registry, foot)
    print(f"Lane check passed={lane['passed']}, duplicates={lane['duplicates']}", flush=True)
    if not lane["passed"]:
        print("DUPLICATE DETECTED -- aborting build (parallel-run protocol LANE rule).", flush=True)
        return 1

    # ---- write all-finite GeoTIFF (fixes the [0,1] portal error) ----
    pred = dots.astype(np.float32)
    cid = submission.scored_content_id(pred, foot, labels)
    fn = submission.make_filename(FAMILY, SLUG, DATE, cid, "allfinite")
    p = submission.write_geotiff(pred, paths.TEMPLATE, dl / fn, outside="zero")
    rep = submission.verify_geotiff(p, paths.TEMPLATE)
    if not rep["hard_checks_passed"]:
        raise SystemExit(f"hard validation failure for {fn}: {rep['hard_failures']}")
    zpath = submission.zip_single(dl / fn)
    note = submission.make_note(
        "unique scatter-smoothed far-field",
        "UNIQUE submission (not copied from any GEMSDOE site): scatter-smoothed (sigma=1.85 px) "
        "off-catalogue far-field emission, dot-thinned d=1.5, all-finite [0,1]; catalogue-"
        "internal holdout cannot see far-field truth (blind by design, knowledge/10); supported "
        "by GEMSDOE32 truth model (+0.0247, 12/12 draws). MEASUREMENT PROBE -- not a scored "
        f"weekly slot. | id {cid} | not yet live-scored",
        cid,
    )
    note = note[:200]
    (dl / f"note-{fn[:-4]}.txt").write_text(note + "\n")

    # ---- checks JSON ----
    inside = pred[foot]
    checks = {
        "content_id": cid,
        "filename": fn,
        "note": note,
        "note_chars": len(note),
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "UNIQUE UNSCORED measurement probe; no leaderboard score claimed",
        "hypothesis": "scatter-smoothed off-catalogue far-field emission",
        "emitted_px": int(dots.sum()),
        "sha256_tif": rep["sha256"],
        "bytes_tif": rep["bytes"],
        "zip": {"file": zpath.name, "bytes": zpath.stat().st_size,
                "sha256": submission.sha256_file(zpath)},
        "validation": rep,
        "lane_check": lane,
        "format": {
            "single_band_float32": rep["checks"]["single_band_float32"]["pass"],
            "grid_matches_template": rep["checks"]["grid_matches_template"]["pass"],
            "inside_footprint_in_0_1": rep["checks"]["inside_footprint_in_0_1"]["pass"],
            "inside_footprint_all_finite": rep["checks"]["inside_footprint_all_finite"]["pass"],
            "no_infinities_anywhere": rep["checks"]["no_infinities_anywhere"]["pass"],
            "values_exactly_0_or_1": sorted(set(np.unique(inside).tolist())) == [0.0, 1.0],
            "no_dot_on_catalogue": bool(not ((dots & labels).any())),
            "no_dot_outside_footprint": bool(not ((dots & ~foot).any())),
        },
    }
    (dl / f"checks-{fn[:-4]}.json").write_text(json.dumps(checks, indent=2) + "\n")

    # ---- append to manifest ----
    man_path = dl / "manifest.json"
    man = json.loads(man_path.read_text())
    man["unique_scatter_farfield"] = {
        "file": fn,
        "zip": zpath.name,
        "content_id": cid,
        "note": note,
        "note_chars": len(note),
        "emitted_px": int(dots.sum()),
        "sha256_tif": rep["sha256"],
        "status": "UNSCORED unique measurement probe",
        "lane_check_passed": lane["passed"],
        "validation_hard_passed": rep["hard_checks_passed"],
        "generated_utc": checks["generated_utc"],
    }
    man_path.write_text(json.dumps(man, indent=1))

    print(json.dumps({"file": fn, "cid": cid, "emitted_px": int(dots.sum()),
                      "lane_passed": lane["passed"], "hard_passed": rep["hard_checks_passed"],
                      "seconds": round(time.time() - t0, 1)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
