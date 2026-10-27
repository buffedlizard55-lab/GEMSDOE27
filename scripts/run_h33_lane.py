#!/usr/bin/env python3
"""E1–E3 for frozen H33-1 short buried basement-step complement emission.

Preregistration: knowledge/30_preregistration_H33_2026-10-27.md, hashed before scoring.
Uses gems27.holdout, gems27.metric, gems27.submission, and gems27.oof_detector.ridge_nms.
Does not fork the metric. Every performance number is HOLDOUT-DTI, never a live score.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from pyproj import CRS, Transformer
from scipy.ndimage import distance_transform_edt
from scipy.stats import spearmanr
from skimage.draw import line as sk_line
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems27 import buried_step, grid, holdout, metric, paths, submission  # noqa: E402
from gems27.oof_detector import ridge_nms  # noqa: E402
from gems27.subsurface_features import priority_poisson_disk  # noqa: E402
from gems27.vector_graph import NBMG_ALBERS_WKT  # noqa: E402

SEEDS = list(range(520, 530))
BUDGET = 37_654
MIN_DIST = 2.8
B_EXCL = 2.0
BUFFER_PX = 6.0
PREREG = ROOT / "knowledge" / "30_preregistration_H33_2026-10-27.md"
E1_PATH = paths.EVIDENCE / "h33_e1_canary_and_surface_520_529.json"
E2_PATH = paths.EVIDENCE / "h33_e2_holdout_520_529.json"
CARD_PATH = paths.EVIDENCE / "h33_run_card_2026-10-27.json"
RESEARCH = paths.DOCS / "downloads" / "research"
DATE = "20261027"


def sha256_file(path: Path) -> str:
    return hashlib.file_digest(path.open("rb"), "sha256").hexdigest()


def load_group_map(labels: np.ndarray) -> tuple[np.ndarray, dict]:
    """Assign every catalogue pixel the FID of the nearest rasterized NBMG polyline."""
    data = json.loads(paths.QFAULT_VECTORS.read_text())
    tf = Transformer.from_crs(CRS.from_wkt(NBMG_ALBERS_WKT), CRS.from_epsg(grid.CRS_EPSG), always_xy=True)
    fid = np.zeros(labels.shape, np.int32)
    n_seg = 0
    for idx, feat in enumerate(data["features"], start=1):
        for path in feat["geometry"]["paths"]:
            pts = np.asarray(path, float)
            if len(pts) < 2:
                continue
            n_seg += 1
            ux, uy = tf.transform(pts[:, 0], pts[:, 1])
            cols = np.floor((ux - grid.TRANSFORM[2]) / grid.PIXEL_M).astype(int)
            rows = np.floor((grid.TRANSFORM[5] - uy) / grid.PIXEL_M).astype(int)
            for i in range(len(rows) - 1):
                rr, cc = sk_line(int(rows[i]), int(cols[i]), int(rows[i + 1]), int(cols[i + 1]))
                ok = (rr >= 0) & (rr < fid.shape[0]) & (cc >= 0) & (cc < fid.shape[1])
                fid[rr[ok], cc[ok]] = idx
    vec = fid > 0
    _, (iy, ix) = distance_transform_edt(~vec, return_indices=True)
    group = np.zeros(labels.shape, np.int32)
    group[labels] = fid[iy[labels], ix[labels]]
    if np.any(group[labels] <= 0):
        raise RuntimeError("catalogue pixel was not assigned a vector FID")
    dist = distance_transform_edt(~vec)
    stats = {
        "n_features": len(data["features"]),
        "n_segments_rasterized": n_seg,
        "n_fids_on_catalogue": int(len(np.unique(group[labels]))),
        "median_catalogue_to_vector_px": float(np.median(dist[labels])),
        "share_catalogue_within_3px": float((dist[labels] <= 3).mean()),
    }
    return group, stats


def registry_positive_union(foot: np.ndarray) -> tuple[np.ndarray, list[str]]:
    union = np.zeros(foot.shape, bool)
    names = []
    cache = paths.DATA / "parallel_registry"
    manifest = json.loads((cache / "cache_manifest.json").read_text())
    if len(manifest["entries"]) != 12:
        raise RuntimeError(f"expected 12 registry rasters, found {len(manifest['entries'])}")
    for item in manifest["entries"]:
        path = paths.DATA / item["local"]
        with rasterio.open(path) as ds:
            if ds.shape != foot.shape or ds.crs is None or ds.crs.to_epsg() != grid.CRS_EPSG:
                raise RuntimeError(f"registry grid mismatch: {item['id']}")
            arr = ds.read(1)
        union |= np.isfinite(arr) & (arr > 0.5) & foot
        names.append(item["id"])
    return union, names


def surface_spearman(surface: np.ndarray, foot: np.ndarray, sample_idx: np.ndarray) -> dict[str, float]:
    s = surface.ravel()[sample_idx]
    out = {}
    cache = paths.DATA / "parallel_registry"
    manifest = json.loads((cache / "cache_manifest.json").read_text())
    for item in manifest["entries"]:
        with rasterio.open(paths.DATA / item["local"]) as ds:
            ref = np.nan_to_num(ds.read(1), nan=0.0).ravel()[sample_idx]
        rho = spearmanr(s, ref).statistic
        out[item["id"]] = 0.0 if not np.isfinite(rho) else float(rho)
    return out


def canary_auc(values: np.ndarray, pos: np.ndarray, neg: np.ndarray) -> tuple[float, float]:
    v = np.r_[values[pos], values[neg]].astype(np.float64)
    y = np.r_[np.ones(pos.size, np.uint8), np.zeros(neg.size, np.uint8)]
    finite = np.isfinite(v)
    raw = float(roc_auc_score(y[finite], v[finite]))
    return raw, max(raw, 1.0 - raw)


def fit_predict(X: np.ndarray, y: np.ndarray, train: np.ndarray, seed: int) -> np.ndarray:
    pos = np.flatnonzero(train & (y == 1))
    neg = np.flatnonzero(train & (y == 0))
    if pos.size < 50 or neg.size < 50:
        raise RuntimeError(f"degenerate training split seed={seed}")
    rng = np.random.default_rng(seed)
    neg_sub = rng.choice(neg, size=min(neg.size, pos.size * 10), replace=False)
    idx = np.sort(np.r_[pos, neg_sub])
    clf = HistGradientBoostingClassifier(
        max_iter=100,
        max_leaf_nodes=31,
        learning_rate=0.08,
        l2_regularization=5.0,
        random_state=seed,
    )
    clf.fit(np.asarray(X[idx], dtype=np.float32), y[idx].astype(int))
    prob = np.empty(X.shape[0], np.float32)
    for a in range(0, X.shape[0], 400_000):
        b = min(a + 400_000, X.shape[0])
        prob[a:b] = clf.predict_proba(np.asarray(X[a:b], dtype=np.float32))[:, 1]
    return prob


def scatter(prob: np.ndarray, foot: np.ndarray) -> np.ndarray:
    grid_prob = np.zeros(foot.shape, np.float32)
    grid_prob[foot] = prob
    return grid_prob


def emit(prob_grid: np.ndarray, foot: np.ndarray, known: np.ndarray, extra_block: np.ndarray | None) -> np.ndarray:
    d_known = distance_transform_edt(~known)
    ridge = ridge_nms(prob_grid, foot, sigma=1.0)
    cand = ridge & foot & ~known & (d_known > B_EXCL)
    if extra_block is not None:
        cand &= ~extra_block
    return priority_poisson_disk(prob_grid, cand, MIN_DIST, BUDGET)


def score_cell(pred: np.ndarray, split, foot: np.ndarray, quadrant: np.ndarray | None = None) -> dict:
    valid = holdout.buffered_scoring_mask(split, foot, buffer_px=BUFFER_PX)
    hidden = split.hidden
    if quadrant is not None:
        valid = valid & quadrant
        hidden = hidden & quadrant
    out = metric.dti_binary(pred.astype(np.float32), hidden, valid=valid, known=split.known)
    out["n_truth"] = int(out["n_truth"])
    out["n_emitted"] = int(out["n_emitted"])
    return out


def pooled(cells: list[dict]) -> float:
    tp = sum(c["TPw"] for c in cells)
    fp = sum(c["FPw"] for c in cells)
    fn = sum(c["FNw"] for c in cells)
    return float(tp / (tp + metric.ALPHA * fp + metric.BETA * fn + metric.EPS))


def paired(candidate: list[dict], control: list[dict]) -> dict:
    delta = np.array([pooled([c]) - pooled([b]) for c, b in zip(candidate, control, strict=True)])
    rng = np.random.default_rng(20261027)
    boots = delta[rng.integers(0, len(delta), size=(10_000, len(delta)))].mean(axis=1)
    folds = holdout.make_quadrant_folds(np.ones(grid.SHAPE, bool))
    # Fold deltas are filled by the caller when quadrant cells exist; seed-level is the gate unit.
    return {
        "pooled_delta_dti": float(pooled(candidate) - pooled(control)),
        "mean_seed_paired_delta_dti": float(delta.mean()),
        "ci95": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
        "positive_seeds": int((delta > 0).sum()),
        "n_seeds": int(len(delta)),
        "per_seed_pooled_delta_dti": delta.tolist(),
        "fold_ids_unused_here": int(folds.max()),
    }


def local_overlap(dots: np.ndarray, foot: np.ndarray, skip_names: set[str] | None = None) -> dict:
    """Directed 3 px overlap against this repo's pre-existing all-finite rasters."""
    skip_names = skip_names or set()
    hits = []
    for folder in (paths.DOCS / "downloads", RESEARCH):
        if not folder.exists():
            continue
        for path in sorted(folder.glob("*allfinite.tif")):
            if path.name in skip_names:
                continue
            with rasterio.open(path) as ds:
                ref = ds.read(1)
            ref_pos = np.isfinite(ref) & (ref > 0.5) & foot
            if not ref_pos.any():
                continue
            frac = float((distance_transform_edt(~ref_pos)[dots] <= 3.0).mean())
            hits.append({"file": path.name, "dot_fraction_within_3px": frac})
    hits.sort(key=lambda r: r["dot_fraction_within_3px"], reverse=True)
    return {
        "n_local_rasters": len(hits),
        "max_dot_overlap_within_3px": hits[0]["dot_fraction_within_3px"] if hits else 0.0,
        "worst": hits[:5],
        "pass": (not hits) or hits[0]["dot_fraction_within_3px"] <= 0.70,
    }


def main() -> int:
    t0 = time.time()
    if not PREREG.is_file():
        raise SystemExit("preregistration missing; refusing to run")
    prereg_hash = sha256_file(PREREG)
    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    names = json.loads(paths.PREPARED_META.read_text())["names"]
    base = np.load(paths.PREPARED_FEATURES, mmap_mode="r")
    if base.shape != (int(foot.sum()), 32):
        raise SystemExit(f"prepared stack shape {base.shape} is not the cached 32-band matrix")

    print("building vector segment map", flush=True)
    group, group_stats = load_group_map(labels)
    print(json.dumps(group_stats), flush=True)
    union, registry_ids = registry_positive_union(foot)
    complement_block = distance_transform_edt(~union) <= 3.0
    print(f"registry dots {int(union.sum())} complement-blocked px {int((complement_block & foot).sum())}", flush=True)

    # Depth / step / shear from the cached stack, scattered once.
    def band(name: str) -> np.ndarray:
        arr = np.full(grid.SHAPE, np.nan, np.float32)
        arr[foot] = np.asarray(base[:, names.index(name)], dtype=np.float32)
        return arr

    extra = buried_step.build_feature_matrix(
        band("depth_to_base_surf"), band("lidar_step_max"), band("geod_shearrate"), foot
    )
    Xc = np.concatenate([np.asarray(base, dtype=np.float32), extra], axis=1)
    y = labels[foot].astype(np.uint8)

    hidden_any = np.zeros_like(labels)
    splits = []
    for seed in SEEDS:
        split = holdout.make_segment_split(labels, foot, group, seed=seed, frac=0.20)
        splits.append(split)
        hidden_any |= split.hidden
    pos = np.flatnonzero(hidden_any[foot])
    neg_all = np.flatnonzero((~labels & foot & ~hidden_any)[foot])
    neg = np.random.default_rng(520).choice(neg_all, size=min(250_000, neg_all.size), replace=False)
    canary = {}
    for j, name in enumerate(buried_step.TRANSFORM_NAMES):
        raw, inv = canary_auc(extra[:, j], pos, neg)
        canary[name] = {"raw_auc": raw, "direction_invariant_auc": inv}
    canary_max = max(v["direction_invariant_auc"] for v in canary.values())
    leakage = {k: v for k, v in canary.items() if v["direction_invariant_auc"] > 0.90}

    print("full-fit surface for pre-placement check", flush=True)
    train_all = np.ones(y.size, bool)
    full_prob = fit_predict(Xc, y, train_all, seed=520)
    full_grid = scatter(full_prob, foot)
    rng = np.random.default_rng(521)
    sample = rng.choice(np.flatnonzero(foot.ravel()), size=400_000, replace=False)
    rho = surface_spearman(full_grid, foot, sample)
    max_abs_rho = max(abs(v) for v in rho.values())
    e1_pass = (not leakage) and canary_max <= 0.90 and max_abs_rho <= 0.90
    e1 = {
        "experiment": "E1 H33-1 canary and pre-placement surface",
        "label": "HOLDOUT-DTI setup only; no organizer score",
        "preregistration_sha256": prereg_hash,
        "seeds": SEEDS,
        "group_map": group_stats,
        "n_hidden_positive_union": int(pos.size),
        "n_negative_sample": int(neg.size),
        "canary_new_features": canary,
        "canary_max_direction_invariant_auc": canary_max,
        "leakage_flags": leakage,
        "preplacement_surface_spearman_vs_12_peer_rasters": rho,
        "max_abs_preplacement_surface_spearman": max_abs_rho,
        "registry_ids": registry_ids,
        "gate_e1_pass": e1_pass,
        "duplicate_stop": bool(max_abs_rho > 0.90),
        "runtime_s": round(time.time() - t0, 1),
    }
    E1_PATH.write_text(json.dumps(e1, indent=2) + "\n")
    print(json.dumps({"canary_max": canary_max, "max_abs_rho": max_abs_rho, "pass": e1_pass}), flush=True)
    if leakage or max_abs_rho > 0.90:
        card = {
            "schema": "parallel-run-card-v2",
            "hypothesis_id": "H33-1",
            "hypothesis": "short buried basement-step complement",
            "mechanism": "basement-depth gradient under a weak lidar step, emitted outside registry dots",
            "named_non_fault_mimic": "roads, field boundaries, survey seams, lithologic basin-fill pinch-outs",
            "verdict": "negative",
            "ok_to_submit": False,
            "stop_reason": "leakage" if leakage else "duplicate_surface",
            "holdout": {
                "label": "HOLDOUT-DTI",
                "evaluator": "not scored; stopped at E1",
                "n_withheld_positives_total": int(pos.size),
                "canary_max_auc": canary_max,
                "gate_efficacy_pass": False,
            },
            "uniqueness_vs_registry": {
                "pass": False,
                "max_surface_spearman": max_abs_rho,
                "max_dot_overlap_within_3px_euclidean": None,
            },
            "note_max_140_chars": "H33-1 stopped at E1; no TIFF placed. DO NOT SUBMIT.",
            "raster": None,
        }
        CARD_PATH.write_text(json.dumps(card, indent=2) + "\n")
        print("E1 stop; no dots placed", flush=True)
        return 2

    print("E2 holdout", flush=True)
    cells_c, cells_b = [], []
    fold_cells_c: dict[str, list] = {n: [] for n in holdout.FOLD_NAMES}
    fold_cells_b: dict[str, list] = {n: [] for n in holdout.FOLD_NAMES}
    folds = holdout.make_quadrant_folds(foot)
    for seed, split in zip(SEEDS, splits, strict=True):
        train = holdout.buffered_training_mask(split, foot, buffer_px=BUFFER_PX)[foot]
        # Visible-fault labels only: hidden pixels are already outside the training mask.
        pc = scatter(fit_predict(Xc, y, train, seed=seed), foot)
        pb = scatter(fit_predict(base, y, train, seed=seed), foot)
        known = split.known
        pred_c = emit(pc, foot, known, complement_block)
        pred_b = emit(pb, foot, known, None)
        cells_c.append(score_cell(pred_c, split, foot))
        cells_b.append(score_cell(pred_b, split, foot))
        for fid, fname in enumerate(holdout.FOLD_NAMES):
            fold_cells_c[fname].append(score_cell(pred_c, split, foot, folds == fid))
            fold_cells_b[fname].append(score_cell(pred_b, split, foot, folds == fid))
        print(
            f"seed {seed} C {cells_c[-1]['dti']:.4f} B {cells_b[-1]['dti']:.4f} "
            f"dotsC {int(pred_c.sum())} dotsB {int(pred_b.sum())}",
            flush=True,
        )
        del pc, pb, pred_c, pred_b

    pair = paired(cells_c, cells_b)
    per_fold = {}
    for fname in holdout.FOLD_NAMES:
        per_fold[fname] = pooled(fold_cells_c[fname]) - pooled(fold_cells_b[fname])
    pair["per_fold_pooled_delta_dti"] = per_fold
    pair["positive_folds"] = int(sum(v > 0 for v in per_fold.values()))
    pair["n_folds"] = 4
    n_withheld = int(sum(c["n_truth"] for c in cells_c))
    efficacy = (
        pair["mean_seed_paired_delta_dti"] >= 0.001
        and pair["ci95"][0] > 0
        and pair["positive_seeds"] >= 7
        and pair["positive_folds"] >= 3
        and pooled(cells_c) > pooled(cells_b)
    )
    e2 = {
        "experiment": "E2 H33-1 whole-segment buffered holdout",
        "label": "HOLDOUT-DTI",
        "evaluator": "gems27.metric.dti_binary v1 (alpha=0.2, beta=0.8, R=3px triangular) + whole-FID buffered holdout (buffer_px=6)",
        "seeds": SEEDS,
        "n_cells": len(cells_c),
        "n_withheld_positive_occurrences": n_withheld,
        "pooled_candidate": pooled(cells_c),
        "pooled_control_B": pooled(cells_b),
        "paired_candidate_minus_B": pair,
        "gate_efficacy_pass": efficacy,
        "cells_candidate": cells_c,
        "cells_control_B": cells_b,
        "runtime_s": round(time.time() - t0, 1),
    }
    E2_PATH.write_text(json.dumps(e2, indent=2) + "\n")
    print(json.dumps({"pooled_C": e2["pooled_candidate"], "pooled_B": e2["pooled_control_B"], "efficacy": efficacy}), flush=True)

    print("E3 place dots from the already-checked full-fit surface", flush=True)
    known_all = labels & foot
    dots = emit(full_grid, foot, known_all, complement_block)
    if int((dots & known_all).sum()) != 0 or float(distance_transform_edt(~known_all)[dots].min()) <= B_EXCL:
        raise RuntimeError("emission violated catalogue exclusion")
    pred = dots.astype(np.float32)
    cid = submission.scored_content_id(pred, foot, known_all)
    stem = f"gems27-h33-bss-complement-{DATE}-{cid}"
    RESEARCH.mkdir(parents=True, exist_ok=True)
    tif = submission.write_geotiff(pred, paths.TEMPLATE, RESEARCH / f"{stem}-allfinite.tif", outside="zero")
    nan_tif = submission.write_geotiff(pred, paths.TEMPLATE, RESEARCH / f"{stem}-nan.tif", outside="nan")
    zpath = submission.zip_single(tif)
    checks = submission.verify_geotiff(tif, paths.TEMPLATE)
    nan_checks = submission.verify_geotiff(nan_tif, paths.TEMPLATE)
    (RESEARCH / f"checks-{stem}-allfinite.json").write_text(json.dumps(checks, indent=2) + "\n")
    # Registry uniqueness on the written file via the shared checker.
    uniq_path = paths.EVIDENCE / "h33_uniqueness_vs_registry.json"
    from subprocess import run
    proc = run(
        [sys.executable, str(ROOT / "scripts" / "check_parallel_uniqueness.py"), str(tif), "--out", str(uniq_path)],
        check=False,
        cwd=ROOT,
    )
    uniq = json.loads(uniq_path.read_text()) if uniq_path.exists() else {"pass": False, "duplicates": ["checker-failed"]}
    max_overlap = max((e["candidate_dot_fraction_within_3px"] for e in uniq.get("entries", [])), default=1.0)
    max_rho_final = max((abs(e["spearman_rank_correlation"]) for e in uniq.get("entries", [])), default=1.0)
    local = local_overlap(dots, foot, skip_names={tif.name, nan_tif.name})
    unique_pass = bool(uniq.get("pass")) and local["pass"] and max_abs_rho <= 0.90
    promote = bool(e1_pass and efficacy and unique_pass and checks["hard_checks_passed"] and proc.returncode == 0)
    verdict = "promote" if promote else "negative"
    tail = "GATE PASSED selector required" if promote else "DO NOT SUBMIT"
    note = (
        f"H33-1 buried-step complement B2 {int(dots.sum())}px "
        f"HOLDOUT-DTI {e2['pooled_candidate']:.4f} | id {cid} | {tail}"
    )[:140]
    (RESEARCH / f"note-{stem}-allfinite.txt").write_text(note + "\n")
    card = {
        "schema": "parallel-run-card-v2",
        "generated_utc": "2026-10-27",
        "lane": "L-S13-H33",
        "hypothesis_id": "H33-1",
        "hypothesis": "Short buried basement-step features added to the cached 32-band stack, emitted only outside the 3 px registry-dot neighborhood",
        "mechanism": "A basement-depth step under weak lidar relief can mark a short fault the long-line scarp family does not dot; complement emission is required because the same stack's high scores sit on that family.",
        "named_non_fault_mimic": "roads, field boundaries, airborne-survey seams, and lithologic basin-fill pinch-outs",
        "verdict": verdict,
        "ok_to_submit": False if not promote else True,
        "slot_authorized": False,
        "submission_name": f"27GEMSDOE-H33-BSS-{DATE}-{cid}",
        "note_max_140_chars": note,
        "note_chars": len(note),
        "preregistration_sha256": prereg_hash,
        "holdout": {
            "label": "HOLDOUT-DTI",
            "provenance_note": "Catalogue-internal whole-FID buffered hide-and-recover; NOT a live organizer score.",
            "evaluator": e2["evaluator"],
            "seeds": SEEDS,
            "n_cells": len(cells_c),
            "n_withheld_positives_total": n_withheld,
            "canary_max_auc": canary_max,
            "pooled_candidate": e2["pooled_candidate"],
            "pooled_control_B": e2["pooled_control_B"],
            "paired_candidate_minus_B": pair,
            "gate_efficacy_pass": efficacy,
            "ci95": pair["ci95"],
        },
        "uniqueness_vs_registry": {
            "pass": unique_pass,
            "registry_checker_pass": bool(uniq.get("pass")),
            "max_dot_overlap_within_3px_euclidean": max_overlap,
            "max_surface_spearman": max_abs_rho,
            "max_final_raster_spearman": max_rho_final,
            "duplicates": uniq.get("duplicates", []),
            "local_prior_rasters": local,
        },
        "validator": {
            "zeros_hard_pass": bool(checks["hard_checks_passed"]),
            "zeros_checks": checks["checks"],
            "nan_hard_pass": bool(nan_checks["hard_checks_passed"]),
            "sha256": checks["sha256"],
        },
        "raster": {
            "primary_allfinite": tif.name,
            "nan_twin": nan_tif.name,
            "zip": zpath.name,
            "directory": "docs/downloads/research",
            "sha256": checks["sha256"],
            "dots": int(dots.sum()),
            "content_id": cid,
        },
        "download_decision": "DO NOT SUBMIT" if not promote else "GATES PASSED — selector still required; this session does not upload",
        "runtime_s": round(time.time() - t0, 1),
    }
    # Promote still does not authorize a weekly slot. The user-facing flag is explicit.
    if promote:
        card["ok_to_submit"] = False
        card["download_decision"] = (
            "HOLDOUT GATE PASSED and raster is unique, but this session does not select a weekly slot. "
            "Do not upload until a separate selector confirms the weekly cap."
        )
        card["verdict"] = "promote"
        card["slot_authorized"] = False
    CARD_PATH.write_text(json.dumps(card, indent=2) + "\n")
    manifest = {
        "ok_to_submit": False,
        "slot_authorized": False,
        "verdict": card["verdict"],
        "download_decision": card["download_decision"],
        "primary_allfinite": tif.name,
        "sha256": checks["sha256"],
        "note": note,
        "dots": int(dots.sum()),
        "holdout_dti_label": "HOLDOUT-DTI",
        "pooled_holdout_dti": e2["pooled_candidate"],
        "paired_delta_vs_base32": pair["pooled_delta_dti"],
        "ci95": pair["ci95"],
        "n_withheld_positives": n_withheld,
        "evaluator": e2["evaluator"],
    }
    (RESEARCH / "h33_candidate_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"verdict": card["verdict"], "dots": int(dots.sum()), "sha": checks["sha256"][:16], "decision": card["download_decision"]}, indent=2))
    return 0 if not promote else 0


if __name__ == "__main__":
    raise SystemExit(main())
