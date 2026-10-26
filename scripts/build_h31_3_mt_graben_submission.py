#!/usr/bin/env python3
"""E3 builder for the preregistered H31-3 MT-graben candidate.

Runs exactly once after E2, irrespective of outcome, so a negative is byte-bound and reproducible.
It creates a two-partition stitched OOF surface, writes both GeoTIFF conventions, validates format,
screens the final dots and pre-placement surface against registry rasters, and emits the required
parallel-run JSON card. It never uploads or contacts DrivenData.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import run_h31_3_mt_graben as runner  # noqa: E402
from gems27 import geothermal_conduit_nis as h31  # noqa: E402
from gems27 import hydrothermal_piedmont as h29  # noqa: E402
from gems27 import paths, readiness, submission  # noqa: E402

DATE = "20261026"
E3_PATH = paths.EVIDENCE / "h31_3_run_card_2026-10-26.json"
UNIQ_PATH = paths.EVIDENCE / "h31_3_uniqueness_vs_registry.json"


def sha256_file(path: Path) -> str:
    with path.open("rb") as fh:
        return hashlib.file_digest(fh, "sha256").hexdigest()


def dots(path: Path) -> np.ndarray:
    with rasterio.open(path) as ds:
        a = ds.read(1)
    return np.isfinite(a) & (a > 0.5)


def overlap_3px(candidate: np.ndarray, reference: np.ndarray) -> float:
    n = int(candidate.sum())
    return 0.0 if n == 0 else float((distance_transform_edt(~reference)[candidate] <= 3.0).mean())


def surface_rho(surface: np.ndarray, reference: np.ndarray, sample: np.ndarray) -> float:
    rho = float(spearmanr(surface.ravel()[sample], reference.ravel()[sample]).statistic)
    return 0.0 if not np.isfinite(rho) else rho


def main() -> int:
    t0 = time.time()
    if not runner.E1_PATH.exists() or not runner.E2_PATH.exists():
        raise SystemExit("E1/E2 evidence missing; run scripts/run_h31_3_mt_graben.py first")
    e1 = json.loads(runner.E1_PATH.read_text())
    e2 = json.loads(runner.E2_PATH.read_text())

    foot, labels, lid_valid, _, base_X, sub15_X, h29_X, h31_X, mt_X = runner.load_common()
    _, _, p_quad = runner.candidate_oof(
        base_X, sub15_X, h29_X, h31_X, mt_X, labels, foot, lid_valid, cache_tag="quad"
    )
    rot_masks = h29.sector_masks_rotated45(foot)
    _, _, p_rot = runner.candidate_oof(
        base_X, sub15_X, h29_X, h31_X, mt_X, labels, foot, lid_valid,
        cache_tag="rot45", seed=511, fold_masks=rot_masks,
    )
    surface = (np.float32(0.5) * p_quad + np.float32(0.5) * p_rot).astype(np.float32)
    surface[~foot] = 0.0
    np.save(runner.CACHE_DIR / "prob_h31_3_stitched_oof.npy", surface)

    dots_grid = h31.emit_h31_celf(surface, foot, labels, runner.BUDGET_TOTAL, b_excl=runner.B_EXCL)
    dcat = distance_transform_edt(~labels)
    if int(dots_grid.sum()) != runner.BUDGET_TOTAL:
        raise RuntimeError(f"emission count {int(dots_grid.sum())} != {runner.BUDGET_TOTAL}")
    if (dots_grid & ~foot).any() or (dots_grid & labels).any() or float(dcat[dots_grid].min()) <= runner.B_EXCL:
        raise RuntimeError("blind B2 emission integrity failure")

    prediction = dots_grid.astype(np.float32)
    content_id = submission.scored_content_id(prediction, foot, labels)
    stem = f"gems27-h31-3-mt-graben-celf28-{DATE}-{content_id}"
    root_downloads = paths.DOCS / "downloads"
    root_downloads.mkdir(parents=True, exist_ok=True)
    provisional_af = root_downloads / f"{stem}-allfinite.tif"
    provisional_nan = root_downloads / f"{stem}-nan.tif"
    submission.write_geotiff(prediction, paths.TEMPLATE, provisional_af, outside="zero")
    submission.write_geotiff(prediction, paths.TEMPLATE, provisional_nan, outside="nan")
    provisional_zip = submission.zip_single(provisional_af)
    check_af = submission.verify_geotiff(provisional_af, paths.TEMPLATE)
    check_nan = submission.verify_geotiff(provisional_nan, paths.TEMPLATE)
    if not (check_af["hard_checks_passed"] and check_nan["hard_checks_passed"]):
        raise RuntimeError("submission validator failed")

    # Shared official peer screen assesses final dots/raster ranks. Run it even for a duplicate;
    # a non-zero exit is its expected fail-closed outcome rather than an execution failure.
    cmd = [sys.executable, str(ROOT / "scripts" / "check_parallel_uniqueness.py"), str(provisional_af),
           "--out", str(UNIQ_PATH)]
    screen_proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if screen_proc.returncode not in (0, 2):
        raise RuntimeError(f"parallel screen crashed: {screen_proc.stderr}")
    peer_screen = json.loads(UNIQ_PATH.read_text())

    rng = np.random.default_rng(20261026)
    sample = rng.choice(np.flatnonzero(foot.ravel()), size=min(400_000, int(foot.sum())), replace=False)
    local_entries = {}
    for tif in sorted(root_downloads.glob("**/*allfinite.tif")):
        if tif.resolve() == provisional_af.resolve():
            continue
        ref = dots(tif)
        local_entries[str(tif.relative_to(ROOT))] = {
            "directed_overlap_3px": overlap_3px(dots_grid, ref),
            "surface_spearman": surface_rho(surface, ref.astype(np.float32), sample),
            "reference_dots": int(ref.sum()),
        }
    peer_surface = {}
    for tif in sorted((paths.DATA / "parallel_registry").glob("*.tif")):
        ref = dots(tif)
        peer_surface[tif.stem] = surface_rho(surface, ref.astype(np.float32), sample)

    max_peer_surface = max((abs(v) for v in peer_surface.values()), default=0.0)
    max_peer_overlap = max((e["candidate_dot_fraction_within_3px"] for e in peer_screen["entries"]), default=0.0)
    max_peer_final_rho = max((abs(e["spearman_rank_correlation"]) for e in peer_screen["entries"]), default=0.0)
    max_local_overlap = max((v["directed_overlap_3px"] for v in local_entries.values()), default=0.0)
    max_local_surface = max((abs(v["surface_spearman"]) for v in local_entries.values()), default=0.0)
    registry_unique = bool(peer_screen["pass"] and max_peer_surface <= 0.90)
    extended_unique = bool(max_local_overlap <= 0.70 and max_local_surface <= 0.90)

    # A primary candidate must pass both E2 and the full registry screen; otherwise move every
    # generated payload to research before exposing its machine-readable manifest.
    gate_e1 = bool(e1["gate_e1_pass"])
    gate_e2 = bool(e2["gate_efficacy_pass"])
    gate_format = bool(check_af["hard_checks_passed"] and check_nan["hard_checks_passed"])
    ok_to_submit = bool(gate_e1 and gate_e2 and registry_unique and extended_unique and gate_format)
    target = root_downloads if ok_to_submit else root_downloads / "research"
    target.mkdir(parents=True, exist_ok=True)
    if target != root_downloads:
        for file in (provisional_af, provisional_nan, provisional_zip):
            file.replace(target / file.name)
    tif_af = target / provisional_af.name
    tif_nan = target / provisional_nan.name
    tif_zip = target / provisional_zip.name

    checks_af_path = target / f"checks-{stem}-allfinite.json"
    checks_nan_path = target / f"checks-{stem}-nan.json"
    submission.dump_json(check_af, checks_af_path)
    submission.dump_json(check_nan, checks_nan_path)
    status = "unscored validated-promote" if ok_to_submit else "RESEARCH NEGATIVE DO NOT SUBMIT"
    note = f"27GEMSDOE H31-3 MTgraben B2 CELF2.8 {runner.BUDGET_TOTAL}px | id {content_id} | {status}"[:140]
    note_path = target / f"note-{stem}-allfinite.txt"
    note_path.write_text(note + "\n")

    comparison = e2["paired_candidate_minus_B"]
    run_card = {
        "schema": "parallel-run-card-v2",
        "generated_utc": "2026-10-26",
        "lane": "L-S12-H31-3-MTGRABEN",
        "hypothesis_id": "H31-3",
        "hypothesis": "Asymmetric MT clay-cap / basement-margin coupling: conductivity sampled 300-900 m toward increasing basement depth is appended to the H31 dual-regime detector.",
        "mechanism": "At a steep depth-to-basement gradient, H31-3 ranks conductive, persistent and gravity/extension-corroborated anomalies on the increasing-depth side versus the opposite side; it then uses the unchanged H31 out-of-fold dual-regime and B2 axial-CELF emitter.",
        "named_non_fault_mimic": "Conductive playa or evaporite basin fill adjoining a lithologic basement contact, without a fault-hosted geothermal conduit.",
        "verdict": "promote" if ok_to_submit else "negative",
        "ok_to_submit": ok_to_submit,
        "submission_name": f"27GEMSDOE-H31-3-MTGRABEN-{DATE}-{content_id}",
        "note_max_140_chars": note,
        "note_chars": len(note),
        "holdout": {
            "label": "HOLDOUT-DTI",
            "provenance_note": "Catalogue-internal whole-segment hide-and-recover; NOT a live organizer score.",
            "evaluator": e2["evaluator"], "seeds": e2["seeds"], "n_cells": e2["n_cells"],
            "n_withheld_positives_total": e2["n_withheld_positives_total"],
            "canary_max_auc": e1["canary_max_direction_invariant_auc"],
            "pooled_holdout_dti_buffered": e2["pooled_holdout_dti_buffered"],
            "paired_candidate_minus_B": comparison,
            "frozen_gate_clauses": e2["frozen_gate_clauses"], "gate_efficacy_pass": gate_e2,
        },
        "uniqueness_vs_registry": {
            "pass": bool(registry_unique and extended_unique),
            "peer_gate_pass": peer_screen["pass"], "max_dot_overlap_within_3px_euclidean": max(max_peer_overlap, max_local_overlap),
            "max_dot_overlap_vs_12_peers": max_peer_overlap, "max_dot_overlap_vs_local_rasters": max_local_overlap,
            "max_surface_spearman_armD": max(max_peer_surface, max_local_surface),
            "max_final_raster_spearman_vs_12_peers": max_peer_final_rho,
            "peer_entries": peer_screen["entries"], "peer_surface_spearman": peer_surface,
            "local_entries": local_entries, "duplicate_peer_ids": peer_screen["duplicates"],
        },
        "raster": {"directory": str(target.relative_to(ROOT)), "primary_allfinite": tif_af.name,
                   "companion_nan": tif_nan.name, "zip": tif_zip.name, "content_id": content_id,
                   "sha256": check_af["sha256"], "sha256_nan": check_nan["sha256"],
                   "sha256_zip": sha256_file(tif_zip), "dots": int(dots_grid.sum()),
                   "min_catalogue_distance_px": float(dcat[dots_grid].min())},
        "validator": {"zeros_hard_pass": check_af["hard_checks_passed"],
                      "nan_hard_pass": check_nan["hard_checks_passed"],
                      "technical_validator_pass": gate_format, "zeros_checks": check_af["checks"],
                      "checks_allfinite_json": str(checks_af_path.relative_to(ROOT)),
                      "checks_nan_json": str(checks_nan_path.relative_to(ROOT))},
        "runtime_s": round(time.time() - t0, 1),
    }
    E3_PATH.write_text(json.dumps(run_card, indent=2) + "\n")
    manifest = {"hypothesis_id": "H31-3", "content_id": content_id, "directory": str(target.relative_to(ROOT)),
                "allfinite": tif_af.name, "nan": tif_nan.name, "zip_allfinite": tif_zip.name,
                "checks_allfinite": checks_af_path.name, "checks_nan": checks_nan_path.name,
                "note_file": note_path.name, "note": note, "sha256_allfinite": check_af["sha256"],
                "emitted_px": int(dots_grid.sum()), "ok_to_submit": ok_to_submit,
                "verdict": run_card["verdict"], "run_card": str(E3_PATH.relative_to(ROOT))}
    (root_downloads / "h31_3_candidate_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    decision = readiness.publication_decision(run_card, ROOT)
    if decision["ok_to_publish_as_submission"] != ok_to_submit:
        raise RuntimeError(f"readiness disagreement: {decision}")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "audit_submission_readiness.py")], check=True)
    print(json.dumps({"verdict": run_card["verdict"], "ok_to_submit": ok_to_submit, "file": str(tif_af),
                      "sha256": check_af["sha256"], "peer_overlap": max_peer_overlap,
                      "local_overlap": max_local_overlap, "runtime_s": run_card["runtime_s"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
