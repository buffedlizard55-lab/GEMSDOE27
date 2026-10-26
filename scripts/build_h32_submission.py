#!/usr/bin/env python3
"""Session 11 / Lane L-S11, H32 experiment E3: full-fit build + uniqueness + run card.

Reads the frozen E2 verdict from evidence/h32_e2_holdout_500_509.json (never re-decides it),
fits the P arm (base-32 + subsurface-15 + Poisson-8) on ALL published labels, emits with the
identical blind instrument used in E2 (ridge_nms -> B2 > 2 px -> priority Poisson disk 2.8 px,
37,654 dots), writes all-finite (primary) + NaN-twin GeoTIFFs and a single-TIFF ZIP, screens
uniqueness against the 12 pinned peer rasters AND every in-repo allfinite raster, and writes
the protocol run card. `ok_to_submit` is true only if E2 gate + uniqueness + validator all pass.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, gaussian_filter
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import grid, oof_detector, paths, submission  # noqa: E402
from gems27 import subsurface_features as sub  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
H32_DIR = paths.DATA / "h32"
BUDGET = 37_654
MIN_DIST = 2.8
B_EXCL = 2.0
DATE = "20261026"


def sha256_bytes_of_dots(dots: np.ndarray) -> str:
    return hashlib.sha256(np.packbits(dots).tobytes()).hexdigest()


def read_dots(path: Path) -> np.ndarray:
    with rasterio.open(path) as ds:
        a = ds.read(1)
    return np.isfinite(a) & (a > 0.5)


def directed_overlap_3px(mine: np.ndarray, other: np.ndarray) -> float:
    n = int(mine.sum())
    if n == 0:
        return 0.0
    d = distance_transform_edt(~other)
    return float((d[mine] <= 3.0).sum() / n)


def main() -> int:
    t0 = time.time()
    ev_path = paths.EVIDENCE / "h32_e2_holdout_500_509.json"
    if not ev_path.exists():
        print("E2 evidence missing; run scripts/run_h32_holdout.py first", flush=True)
        return 2
    e2 = json.loads(ev_path.read_text())
    gate_pass = bool(e2.get("gate_efficacy_pass"))

    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    T = np.load(H32_DIR / "subsurface_transforms.npy")
    P8 = np.load(H32_DIR / "poisson_transforms.npy")
    DP = np.concatenate([T, P8], axis=1)

    full_prob_f = H32_DIR / "full_prob_armP.npy"
    if full_prob_f.exists():
        prob = np.load(full_prob_f)
    else:
        print("fitting full-fit P detector on all labels...", flush=True)
        prob = oof_detector.fit_predict_full_probabilities(foot, labels, extra=DP)
        np.save(full_prob_f, prob)
    print(f"surface ready in {time.time()-t0:.0f}s", flush=True)

    d_cat = distance_transform_edt(~labels)
    ridge = oof_detector.ridge_nms(prob, foot)
    cand = ridge & foot & ~labels & (d_cat > B_EXCL)
    dots = sub.priority_poisson_disk(prob, cand, MIN_DIST, BUDGET)
    n_dots = int(dots.sum())
    assert int((dots & labels).sum()) == 0, "dot on catalogue pixel"
    assert float(d_cat[dots].min()) > B_EXCL, "B2 violation"
    content_id = sha256_bytes_of_dots(dots)[:12]
    slug = f"gems27-h32-poisson-demag-b2-{DATE}-{content_id}"
    out_dir = ROOT / "docs" / "downloads"
    pred = dots.astype(np.float32)
    tif_finite = submission.write_geotiff(pred, paths.TEMPLATE, out_dir / f"{slug}-allfinite.tif", outside="zero")
    tif_nan = submission.write_geotiff(pred, paths.TEMPLATE, out_dir / f"{slug}-nan.tif", outside="nan")
    zpath = submission.zip_single(tif_finite)
    checks_finite = submission.verify_geotiff(tif_finite, paths.TEMPLATE)
    checks_nan = submission.verify_geotiff(tif_nan, paths.TEMPLATE)
    (out_dir / f"checks-{slug}-allfinite.json").write_text(json.dumps(checks_finite, indent=2, default=str) + "\n")
    (out_dir / f"checks-{slug}-nan.json").write_text(json.dumps(checks_nan, indent=2, default=str) + "\n")
    sha_finite = submission.sha256_file(tif_finite)
    print(f"built {tif_finite.name} dots={n_dots} sha={sha_finite[:16]}", flush=True)

    # ---- uniqueness screen: peers (12 pinned) + every in-repo allfinite raster ----
    rng = np.random.default_rng(3)
    sample = rng.choice(np.flatnonzero(foot.ravel()), size=300_000, replace=False)
    screen: dict[str, dict] = {}

    def screen_one(key: str, path: Path, my_dots: np.ndarray):
        other = read_dots(path)
        ov = directed_overlap_3px(my_dots, other)
        dens = gaussian_filter(other.astype(np.float32), 3.0)
        rho = float(spearmanr(prob.ravel()[sample], dens.ravel()[sample]).statistic)
        exact = int((my_dots & other).sum())
        screen[key] = {"path": str(path), "directed_overlap_3px": ov,
                       "surface_spearman_vs_density": rho, "exact_shared_dots": exact,
                       "other_dots": int(other.sum())}

    peer_dir = paths.DATA / "parallel_registry"
    for rp in sorted(peer_dir.glob("*.tif")):
        screen_one(f"peer:{rp.stem}", rp, dots)
    repo_rasters = sorted((ROOT / "docs" / "downloads").glob("*allfinite.tif")) + \
        sorted((ROOT / "docs" / "downloads" / "research").glob("*allfinite.tif"))
    for rp in repo_rasters:
        if rp.resolve() == tif_finite.resolve():
            continue
        screen_one(f"repo:{rp.name}", rp, dots)
    max_peer_ov = max((v["directed_overlap_3px"] for k, v in screen.items() if k.startswith("peer:")), default=0.0)
    max_repo_ov = max((v["directed_overlap_3px"] for k, v in screen.items() if k.startswith("repo:")), default=0.0)
    max_ov = max(max_peer_ov, max_repo_ov)
    max_rho = max((abs(v["surface_spearman_vs_density"]) for v in screen.values()), default=0.0)
    uniq_pass = bool(max_ov <= 0.70 and max_rho <= 0.90)
    (paths.EVIDENCE / "h32_uniqueness_vs_registry.json").write_text(json.dumps({
        "candidate": tif_finite.name, "sha256": sha_finite, "n_dots": n_dots,
        "max_directed_overlap_3px_peers": max_peer_ov,
        "max_directed_overlap_3px_repo": max_repo_ov,
        "max_abs_surface_spearman": max_rho, "pass": uniq_pass, "screen": screen,
    }, indent=2) + "\n")
    print(f"uniqueness: max peer overlap {max_peer_ov:.4f}, max repo overlap {max_repo_ov:.4f}, "
          f"max |rho| {max_rho:.4f}, pass={uniq_pass}", flush=True)

    # ---- kernel coverage c (exact, for PROJECTION sensitivity only) ----
    dist_dots = distance_transform_edt(~dots)
    kern = np.maximum(1.0 - dist_dots / 3.0, 0.0)
    active = foot & ~labels
    c_cov = float(kern[active].mean())

    hard_finite = all(c.get("pass") for c in checks_finite.get("checks", {}).values() if c.get("hard", True)) \
        if isinstance(checks_finite.get("checks"), dict) else bool(checks_finite.get("hard_pass"))
    ok = bool(gate_pass and uniq_pass and hard_finite)
    note = f"27GEMSDOE H32 PoissonDemag B2 {n_dots}px HOLDOUT-DTI +vsD | id {content_id} | {'unscored validated-promote' if ok else 'RESEARCH NEGATIVE DO NOT SUBMIT'}"
    note = note[:140]
    (out_dir / f"note-{slug}-allfinite.txt").write_text(note + "\n")

    card = {
        "schema": "parallel-run-card-v2",
        "generated_utc": "2026-10-26",
        "lane": "L-S11-2026-10-26",
        "hypothesis_id": "H32",
        "hypothesis": "Poisson-theorem gravity-to-pseudogravity hydrothermal demagnetization residual features (8) added to base-32 + subsurface-15 detector; blind B2 Poisson-2.8 emission, 37,654 dots",
        "mechanism": "Hydrothermal magnetite destruction along blind fault conduits erases the RTP magnetic edge while the isostatic-gravity density step persists; local (sigma=15px) gravity-on-RTP regression residual + gravity-edge-without-magnetic-edge contrasts expose conduits that coincident-edge features suppress.",
        "named_non_fault_mimic": "Non-magnetic Paleozoic carbonate faulted against granite and reversely magnetised Tertiary ash-flow tuffs (gravity edge, no magnetic edge, no conduit); RTP flight-line levelling seams.",
        "verdict": "promote" if ok else "negative",
        "ok_to_submit": ok,
        "submission_name": f"27GEMSDOE-H32-POISSON-{DATE}-{content_id}",
        "note_max_140_chars": note, "note_chars": len(note),
        "holdout": {
            "label": "HOLDOUT-DTI",
            "provenance_note": "Catalogue-internal buffered hide-and-recover; NOT a live organizer score.",
            "evaluator": e2.get("evaluator"),
            "seeds": e2.get("seeds"), "n_cells": e2.get("n_cells"),
            "n_withheld_positives_total": e2.get("n_withheld_positives_total"),
            "canary_max_auc": e2.get("canary_max_direction_invariant_auc"),
            "pooled_holdout_dti_buffered": e2.get("pooled_holdout_dti_buffered"),
            "paired_candidate_minus_B": e2.get("paired_P_minus_B"),
            "paired_P_minus_D": e2.get("paired_P_minus_D"),
            "paired_D_minus_B": e2.get("paired_D_minus_B"),
            "frozen_gate_clauses": e2.get("frozen_gate_clauses"),
            "gate_efficacy_pass": gate_pass,
            "oof_pr_auc_catalogue_descriptive": e2.get("oof_pr_auc_catalogue_descriptive"),
        },
        "uniqueness_vs_registry": {
            "pass": uniq_pass,
            "max_dot_overlap_within_3px_euclidean": max_ov,
            "max_dot_overlap_within_3px_vs_peers": max_peer_ov,
            "max_dot_overlap_within_3px_vs_repo": max_repo_ov,
            "max_surface_spearman": float(max(
                (v["surface_spearman_vs_density"] for v in screen.values()), default=0.0)),
            "max_surface_spearman_armD": float(max(
                (v["surface_spearman_vs_density"] for v in screen.values()), default=0.0)),
            "n_rasters_screened": len(screen),
            "detail_file": "evidence/h32_uniqueness_vs_registry.json",
        },
        "validator": {
            "zeros_hard_pass": bool(hard_finite),
            "zeros_checks": checks_finite.get("checks", {}),
            "technical_validator_pass": bool(hard_finite),
        },
        "raster": {"primary_allfinite": tif_finite.name, "sha256": sha_finite,
                   "directory": "docs/downloads", "nan_twin": tif_nan.name, "zip": zpath.name},
        "sha256": sha_finite, "bytes": tif_finite.stat().st_size,
        "n_dots": n_dots, "kernel_coverage_c_active_footprint": c_cov,
        "min_catalogue_distance_px": float(d_cat[dots].min()),
        "budget": "3 experiments (E1 canary, E2 holdout seeds 500-509, E3 build)",
        "runtime_s": round(time.time() - t0, 1),
    }
    card_path = paths.EVIDENCE / "h32_run_card_2026-10-26.json"
    card_path.write_text(json.dumps(card, indent=2) + "\n")
    manifest = {"candidate": slug, "content_id": content_id, "run_card": str(card_path),
                "files": {"allfinite": tif_finite.name, "nan": tif_nan.name, "zip": zpath.name},
                "sha256_allfinite": sha_finite, "n_dots": n_dots, "ok_to_submit": ok,
                "verdict": card["verdict"], "note": note}
    (out_dir / "h32_candidate_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"verdict": card["verdict"], "ok_to_submit": ok, "file": tif_finite.name,
                      "sha256": sha_finite, "n_dots": n_dots, "c": c_cov,
                      "gate_efficacy_pass": gate_pass, "uniqueness_pass": uniq_pass,
                      "validator_hard_pass": bool(hard_finite)}, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
