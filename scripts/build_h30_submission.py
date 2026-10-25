#!/usr/bin/env python3
"""E3: build the H30 unique submission GeoTIFF + protocol run card.

Preregistration: knowledge/20_preregistration_H30.md. Full-fit Arm-D surface (32 bands + 15
subsurface transforms), chemistry re-rank (bounded multiplier), deconflicted priority Poisson-disk
(<=65% of the 38,000-dot budget on candidates within 3 px of this repo's shipped rasters), B2
(>2 px from the catalogue), binary {0,1}, all-finite primary file (nodata=None, every cell in
[0,1]) — the fix for the portal error "Predicted values must be in range [0, 1]".

ok_to_submit = E2 holdout gate PASS AND uniqueness PASS (surface Spearman <= 0.90 and final-dot
3-px directed overlap <= 0.70 vs every raster in registry/parallel_submission_registry.json — the
operative rule — AND vs every repo-shipped raster in docs/downloads/, reported under the same
thresholds) AND shared-validator hard PASS. Computed here into the run card; the website badge
reads that JSON. No human inspection, no live score claimed.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, gaussian_filter
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import grid, oof_detector, paths, submission  # noqa: E402
from gems27 import hydrochemistry as hc  # noqa: E402

BUDGET = 38_000
MIN_DIST = 2.8
B_EXCL = 2.0
CAP = 0.65
HOLD = paths.EVIDENCE / "h30_holdout.json"


def euclid_overlap(dots: np.ndarray, other: np.ndarray, r: float = 3.0) -> float:
    d = distance_transform_edt(~other)
    return float((d[dots] <= r).mean()) if dots.any() else 0.0


def main() -> int:
    hold = json.loads(HOLD.read_text())
    gate_ok = bool(hold.get("gate_efficacy_pass")) and not hold.get("canary_leak_flags")
    print(f"E2 gate from holdout: {gate_ok}", flush=True)

    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    T15 = np.load(paths.DATA / "h30" / "subsurface_transforms.npy")
    chem = hc.build_chemistry_field(paths.DATA / "gdr_wellspring_in_footprint.csv",
                                    grid.SHAPE, foot)

    cache = paths.DATA / "h30" / "full_prob_armD.npy"
    if cache.exists():
        prob = np.load(cache)
    else:
        prob = oof_detector.fit_predict_full_probabilities(foot, labels, extra=T15)
        np.save(cache, prob)

    score = hc.rerank(prob, chem)

    d_cat = distance_transform_edt(~labels)
    ridge = oof_detector.ridge_nms(score, foot)
    cand = ridge & foot & ~labels & (d_cat > B_EXCL)

    # deconfliction targets: every repo-shipped raster (-nan twins where they exist,
    # plus orphan -allfinite files; twins are content-identical inside the footprint).
    # This lane's OWN outputs are excluded so the build is reproducible: re-running must
    # regenerate the frozen E3 artifact, not deconflict against its own previous build.
    repo_paths = []
    for d in [paths.DOCS / "downloads", paths.DOCS / "downloads" / "research"]:
        nan = sorted(d.glob("gems27-*-nan.tif"))
        repo_paths.extend(nan)
        have = {p.name[: -len("-nan.tif")] for p in nan}
        for p in sorted(d.glob("gems27-*-allfinite.tif")):
            if p.name[: -len("-allfinite.tif")] not in have:
                repo_paths.append(p)
    repo_paths = [p for p in repo_paths if "gems27-h30-" not in p.name]
    repo_arrays = []
    for rp in repo_paths:
        with rasterio.open(rp) as s:
            repo_arrays.append(s.read(1))
    conflicted = hc.conflicted_mask(repo_arrays, grid.SHAPE)

    dots, place_info = hc.deconflicted_priority_poisson_disk(score, cand, conflicted,
                                                             MIN_DIST, BUDGET, cap=CAP)
    pred = dots.astype(np.float32)
    cid = submission.scored_content_id(pred, foot, labels)
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    stem = f"gems27-h30-chem-deconf-b2-38k-{date}-{cid}"

    # Pre-write placement assertions (fail loudly rather than ship a broken file).
    assert int(dots.sum()) == BUDGET, f"expected {BUDGET} dots, got {int(dots.sum())}"
    assert not (dots & labels).any(), "dot on catalogue pixel"
    assert float(d_cat[dots].min()) > B_EXCL, "B2 exclusion violated"
    assert not (dots & ~foot).any(), "dot outside footprint"

    # ---- uniqueness from the dot set itself, BEFORE choosing where files live ----
    overlaps = {}
    for rp in sorted((paths.DATA / "parallel_registry").glob("*.tif")):
        with rasterio.open(rp) as s:
            a = s.read(1)
        overlaps[f"peer:{rp.name}"] = euclid_overlap(dots, np.isfinite(a) & (a > 0))
    for rp, a in zip(repo_paths, repo_arrays):
        overlaps[f"repo:{rp.name}"] = euclid_overlap(dots, np.isfinite(a) & (a > 0))
    max_overlap = max(overlaps.values()) if overlaps else 0.0
    peer_max = max((v for k, v in overlaps.items() if k.startswith("peer:")), default=0.0)
    self_max = max((v for k, v in overlaps.items() if k.startswith("repo:")), default=0.0)
    worst = max(overlaps, key=overlaps.get) if overlaps else None

    # surface Spearman vs the 12 peers (before placement, protocol §1)
    rng = np.random.default_rng(11)
    sample = rng.choice(np.flatnonzero(foot.ravel()), size=300_000, replace=False)
    surf = {}
    for rp in sorted((paths.DATA / "parallel_registry").glob("*.tif")):
        with rasterio.open(rp) as s:
            a = s.read(1)
        dens = gaussian_filter((np.isfinite(a) & (a > 0)).astype(np.float32), 3.0)
        surf[rp.name] = float(spearmanr(score.ravel()[sample], dens.ravel()[sample]).statistic)
    max_surf = max(surf.values()) if surf else 0.0

    peer_ok = peer_max <= 0.70 and max_surf <= 0.90     # operative rule (12-peer registry)
    strict_ok = self_max <= 0.70                        # strict self-registry screen (reported)
    unique_ok = peer_ok and strict_ok

    promote = bool(gate_ok and unique_ok)
    out_dir = paths.DOCS / "downloads" if promote else paths.DOCS / "downloads" / "research"
    out_dir.mkdir(parents=True, exist_ok=True)
    zeros_tif = out_dir / f"{stem}-allfinite.tif"
    nan_tif = out_dir / f"{stem}-nan.tif"
    submission.write_geotiff(pred, paths.TEMPLATE, zeros_tif, outside="zero")
    submission.write_geotiff(pred, paths.TEMPLATE, nan_tif, outside="nan")
    zip_path = submission.zip_single(zeros_tif)
    v_zeros = submission.verify_geotiff(zeros_tif, paths.TEMPLATE)
    v_nan = submission.verify_geotiff(nan_tif, paths.TEMPLATE)
    (out_dir / f"checks-{stem}-allfinite.json").write_text(json.dumps(v_zeros, indent=2) + "\n")
    (out_dir / f"checks-{stem}-nan.json").write_text(json.dumps(v_nan, indent=2) + "\n")
    format_ok = bool(v_zeros["hard_checks_passed"])
    ok_to_submit = bool(promote and format_ok)
    verdict = "promote" if ok_to_submit else "negative"

    pooled = hold["pooled_holdout_dti"]
    lb = hold["paired_L_minus_B"]
    ld = hold["paired_L_minus_D"]
    note = (f"27GEMSDOE H30 chem-deconf B2 38k; HOLDOUT-DTI {pooled['L']:.4f} vs B {pooled['B']:.4f}; "
            f"UNSCORED | id {cid}")
    assert len(note) <= 140, len(note)
    card = {
        "run_card": "H30 chemistry-verified deconflicted emission (parallel-run protocol §5)",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis": "Faults missing from the surface-rupture-scoped USGS/INGENIOUS catalogue "
                      "include buried/older structures that channel geothermal fluids; a local "
                      "thermal-anomaly field from measured well/spring temperatures re-ranks the "
                      "confirmed Arm-D subsurface detector, and a deconflicted placement keeps "
                      "the emission unlike every shipped raster while holding the B2/38k optimum.",
        "mechanism": "Full-fit HGB on 32 bands + 15 subsurface transforms (gems27.subsurface_features); "
                     "bounded chemistry multiplier S=D*(1+0.4*(2C-1)) inside 1.7% station coverage, "
                     "S=D outside; ridge NMS; deconflicted priority Poisson-disk >=2.8px with <=65% "
                     "of dots on candidates within 3px of repo-shipped rasters; B2 (200m) catalogue "
                     "exclusion; 38,000-dot budget; binary {0,1}.",
        "named_non_fault_mimic": "Deep regional aquifer discharge unrelated to faulting; "
                                 "geothermometer scatter (silica loss, mixing); sampling bias "
                                 "(wells drilled where accessible, so coverage follows basins and "
                                 "known districts, not geology); duplicate stations; lithologic "
                                 "contacts/survey seams in the potential-field transforms.",
        "holdout": {"label": "HOLDOUT-DTI", "evaluator": hold["evaluator"],
                    "pooled_dti_L_lane": pooled["L"], "pooled_dti_D_control": pooled["D"],
                    "pooled_dti_B_control": pooled["B"],
                    "paired_candidate_minus_B": lb,
                    "paired_L_minus_B": lb, "paired_L_minus_D": ld,
                    "paired_D_minus_B": hold["paired_D_minus_B"],
                    "n_withheld_positives_total": hold["n_withheld_positives_total"],
                    "seeds": hold["seeds"], "canary_max_auc": max(hold["canary_auc"].values()),
                    "gate_efficacy_pass": gate_ok,
                    "gate_components": hold["gate_components"]},
        "uniqueness_vs_registry": {
            "max_dot_overlap_within_3px_euclidean": max_overlap,
            "max_dot_overlap_peers_operative": peer_max,
            "max_dot_overlap_repo_self_screen": self_max,
            "per_raster": overlaps,
            # schema key read by gems27.readiness (max_surface_spearman); L-specific alias kept
            "max_surface_spearman": max_surf,
            "max_surface_spearman_L": max_surf,
            "surface_spearman_per_peer": surf,
            "thresholds": {"dot_overlap": 0.70, "spearman": 0.90},
            "pass_operative_12peer_registry": bool(peer_ok),
            "pass_strict_self_registry": bool(strict_ok),
            "pass": bool(unique_ok)},
        "placement": place_info,
        "chemistry": hold["chemistry"],
        "raster": {"primary_allfinite": zeros_tif.name, "sha256": v_zeros["sha256"],
                   "bytes": v_zeros["bytes"], "dots": int(dots.sum()),
                   "content_id": cid, "zip": zip_path.name, "nan_twin": nan_tif.name,
                   "directory": str(out_dir.relative_to(paths.REPO))},
        "validator": {"zeros_hard_pass": format_ok, "zeros_checks": v_zeros["checks"],
                      "nan_hard_pass": bool(v_nan["hard_checks_passed"])},
        "submission_name": "GEMSDOE27-H30-CHEM-DECONF-B2-38K",
        "note_max_140_chars": note,
        "note_chars": len(note),
        "ok_to_submit": ok_to_submit,
        "verdict": verdict,
        "live_score": None,
        "live_score_label": "UNSCORED — no ORGANIZER-CONFIRMED score exists for this file",
    }
    (paths.EVIDENCE / "h30_run_card.json").write_text(json.dumps(card, indent=2) + "\n")
    manifest = {"stem": stem, **card}
    (out_dir / "h30_candidate_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (out_dir / f"note-{stem}-allfinite.txt").write_text(note + "\n")
    print(f"dots={int(dots.sum())} cid={cid} conflicted={place_info['conflicted_fraction']:.3f}")
    print(f"peer_max={peer_max:.3f} self_max={self_max:.3f} max_surf={max_surf:.3f} "
          f"gate={gate_ok} unique={unique_ok} format={format_ok} -> verdict={verdict} "
          f"ok={ok_to_submit} worst={worst}")
    print(f"wrote {zeros_tif} sha256={v_zeros['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
