#!/usr/bin/env python3
"""Session 11 independent byte-level re-audit (no human inspection).

Recomputes from raster bytes only: dot counts, catalogue distance stats, 300 m kernel
coverage c, directed 3-px overlap vs GEMSDOE32 (0.2778 OWNER-REPORTED), exact set
identities among the H19-5 family, validator status and readiness decisions for the two
promote cards, H31-vs-H32/H29S overlaps, and PROJECTION sensitivity ranges (method +
assumptions recorded; projections are not scores). Writes evidence/session11_reaudit.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import grid, paths, readiness, submission  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
G_INFERRED = 12_226      # repo-inferred hidden-truth size (knowledge/23); UNCONFIRMED
RHO = 1.38               # repo-fitted FP/TP kernel-mass ratio (knowledge/23); assumption
CONC = [5.0, 5.8, 6.5]   # blind-concentration sensitivity (measured family range 5.67-6.50)


def dots(path: Path) -> np.ndarray:
    with rasterio.open(path) as ds:
        a = ds.read(1)
    return np.isfinite(a) & (a > 0.5)


def coverage_c(d: np.ndarray, active: np.ndarray) -> float:
    dist = distance_transform_edt(~d)
    return float(np.maximum(1.0 - dist / 3.0, 0.0)[active].mean())


def overlap3(mine: np.ndarray, other: np.ndarray) -> float:
    n = int(mine.sum())
    return float((distance_transform_edt(~other)[mine] <= 3.0).sum() / n) if n else 0.0


def projection(n_dots: int, c: float) -> dict:
    out = {}
    for conc in CONC:
        tp = conc * c * G_INFERRED
        dti = tp / (0.8 * G_INFERRED + 0.2 * n_dots + 0.2 * (1.0 - RHO) * tp)
        out[f"conc_{conc}x"] = round(float(dti), 4)
    return out


def main() -> int:
    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    active = foot & ~labels
    edt_cat = distance_transform_edt(~labels)

    peer_dir = paths.DATA / "parallel_registry"
    peers = {p.stem: dots(p) for p in sorted(peer_dir.glob("*.tif"))}
    g32 = peers["g32_h33_2_b2"]

    table = {}
    for name, d in peers.items():
        table[name] = {
            "n_dots": int(d.sum()), "kernel_coverage_c": coverage_c(d, active),
            "directed_overlap_3px_vs_g32": overlap3(d, g32),
            "dots_on_catalogue": int((d & labels).sum()),
            "min_catalogue_dist_px": float(edt_cat[d].min()) if d.any() else None,
            "dots_le_2px_from_catalogue": int((d & (edt_cat <= 2.0)).sum()),
        }

    identities = {
        "g32_equals_g25_and_edt_gt_2": bool((g32 == (peers["g25_d28"] & (edt_cat > 2.0))).all()),
        "g28_r1_equals_g25_and_edt_gt_1": bool(
            (peers["g28_h27_4_r1"] == (peers["g25_d28"] & (edt_cat > 1.0001))).all()),
        "g31_equals_g28_r1_in_footprint": bool(
            ((peers["g31_h27_4"] ^ peers["g28_h27_4_r1"]) & foot).sum() == 0),
        "g30_equals_g25_in_footprint": bool(((peers["g30_d28"] ^ peers["g25_d28"]) & foot).sum() == 0),
        "g36_minus_g32_dots": int((peers["g36_anderson"] & ~g32).sum()),
        "g32_minus_g36_dots": int((g32 & ~peers["g36_anderson"]).sum()),
    }

    candidates = {
        "H31-S10_cf8e1bbef244": ROOT / "docs/downloads/gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif",
        "H30-1_801dff07541d": ROOT / "docs/downloads/gems27-h30-1-updip-hydrothermal-b2-35k-20261025-801dff07541d-allfinite.tif",
        "H29-S_511898747886_scored_0.2190_owner_reported": ROOT / "docs/downloads/gems27-h29-hydrothermal-piedmont-celf-20261025-511898747886-allfinite.tif",
        "H32_1ac69a77008d_negative": ROOT / "docs/downloads/research/gems27-h32-poisson-demag-b2-20261026-1ac69a77008d-allfinite.tif",
    }
    cand = {}
    cand_dots = {}
    for name, p in candidates.items():
        d = dots(p)
        cand_dots[name] = d
        ver = submission.verify_geotiff(p, paths.TEMPLATE)
        checks = ver.get("checks", {})
        hard = all(c.get("pass") for c in checks.values() if c.get("hard", True)) if checks else None
        c = coverage_c(d, active)
        cand[name] = {
            "file": p.name, "sha256": submission.sha256_file(p), "bytes": p.stat().st_size,
            "n_dots": int(d.sum()), "kernel_coverage_c": c,
            "dots_on_catalogue": int((d & labels).sum()),
            "min_catalogue_dist_px": float(edt_cat[d].min()),
            "validator_hard_pass": bool(hard),
            "directed_overlap_3px_vs_peers": {k: overlap3(d, v) for k, v in peers.items()},
            "projection_sensitivity_not_a_score": projection(int(d.sum()), c),
        }
        cand[name]["max_peer_overlap_3px"] = max(cand[name]["directed_overlap_3px_vs_peers"].values())
    cand["H31_vs_H32_directed_overlap_3px"] = overlap3(
        cand_dots["H31-S10_cf8e1bbef244"], cand_dots["H32_1ac69a77008d_negative"])
    cand["H32_vs_H31_directed_overlap_3px"] = overlap3(
        cand_dots["H32_1ac69a77008d_negative"], cand_dots["H31-S10_cf8e1bbef244"])
    cand["H31_vs_H29S_directed_overlap_3px"] = overlap3(
        cand_dots["H31-S10_cf8e1bbef244"], cand_dots["H29-S_511898747886_scored_0.2190_owner_reported"])

    decisions = {}
    for card_name in ("h31_s10_run_card_2026-10-26.json", "h30_1_run_card.json",
                      "h32_run_card_2026-10-26.json"):
        card = json.loads((paths.EVIDENCE / card_name).read_text())
        decisions[card_name] = readiness.publication_decision(card, ROOT)

    out = {
        "audit": "Session 11 independent byte re-audit (machine only, no human inspection)",
        "template": {"footprint_px": int(foot.sum()), "catalogue_px": int(labels.sum())},
        "peer_table_measured_from_bytes": table,
        "h19_5_family_identities_measured": identities,
        "candidates": cand,
        "readiness_publication_decisions": decisions,
        "projection_method": {
            "formula": "DTI = TP/(0.8|G| + 0.2N + 0.2(1-rho)TP), TP = concentration * c * |G|",
            "assumptions": {"|G|": G_INFERRED, "rho": RHO, "concentrations": CONC,
                            "provenance": "knowledge/23 fitted model; |G| unconfirmed; PROJECTION only"},
            "holdout_ratio_anchor": {
                "H29S_owner_reported_live": 0.2190,
                "H29S_holdout_in_H31_experiment_seeds400_409": 0.044116,
                "ratio": round(0.2190 / 0.044116, 3),
                "H31_holdout_seeds400_409": 0.047302,
                "H31_ratio_projection": round(0.047302 * 0.2190 / 0.044116, 4),
                "warning": "single-anchor ratio; catalogue holdout is not the organizer label set",
            },
        },
    }
    dest = paths.EVIDENCE / "session11_reaudit.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({
        "identities": identities,
        "H31": {k: cand["H31-S10_cf8e1bbef244"][k] for k in
                ("sha256", "n_dots", "kernel_coverage_c", "validator_hard_pass",
                 "max_peer_overlap_3px", "projection_sensitivity_not_a_score")},
        "H31_vs_H29S": cand["H31_vs_H29S_directed_overlap_3px"],
        "decisions": {k: v["ok_to_publish_as_submission"] for k, v in decisions.items()},
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
