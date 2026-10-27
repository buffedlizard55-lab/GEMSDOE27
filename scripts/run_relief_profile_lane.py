#!/usr/bin/env python3
"""Run the preregistered relief-profile lane (max E1/E2/E3; never uploads).

Shared building blocks: gems27.holdout, vector_graph, oof_detector, metric,
subsurface_features, uniqueness, and submission. See knowledge/30 for frozen decisions.
"""
from __future__ import annotations

import gc
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
import run_h29_2 as base  # noqa: E402
from gems27 import (  # noqa: E402
    grid,
    holdout,
    metric,
    oof_detector,
    paths,
    relief_profile,
    submission,
    uniqueness,
)
from gems27 import subsurface_features as sub  # noqa: E402

SEEDS = (620, 621, 622, 623, 624)
BUDGET = 37_654
START = time.monotonic()
LIMIT = 7200.0
WORK = paths.DATA / "relief_profile_20261027"
CANARY = paths.EVIDENCE / "relief_profile_canary_20261027.json"
RESULT = paths.EVIDENCE / "relief_profile_holdout_20261027.json"
COMPARISONS = paths.EVIDENCE / "relief_profile_registry_20261027.json"
CARD = paths.EVIDENCE / "relief_profile_run_card_20261027.json"
PREREG = ROOT / "knowledge/30_lane_2026-10-27_preregistration.md"
NAME = "GEMSDOE27-H29-5-RELIEF-PROFILE-20261027"
NOTE = "H29-5 detrended relief-profile proxy; whole-FID holdout; research only, not approved to submit."
EVALUATOR = "gems27.metric.dti_binary v1 + whole-FID full-kernel relief-profile v1"


def dump(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def check_time() -> None:
    if time.monotonic() - START >= LIMIT:
        raise TimeoutError("preregistered two-hour experiment budget exhausted")


def prepare(foot: np.ndarray, inputs: dict) -> np.ndarray:
    WORK.mkdir(parents=True, exist_ok=True)
    target, meta = WORK / "relief_features.npy", WORK / "relief_features.json"
    key = {"input": inputs["prepared_features_sha256"],
           "code": uniqueness.sha256_file(ROOT / "src/gems27/relief_profile.py"),
           "preregistration": uniqueness.sha256_file(PREREG)}
    if target.exists() and meta.exists():
        existing = json.loads(meta.read_text())
        if existing.get("inputs") == key and uniqueness.sha256_file(target) == existing.get("sha256"):
            return np.load(target, mmap_mode="r")
    X = np.load(paths.PREPARED_FEATURES, mmap_mode="r")
    j = inputs["feature_names"].index("det_elev")
    elevation = np.full(foot.shape, np.nan, dtype=np.float32)
    elevation[foot] = X[:, j]
    print("E1: computing four label-free relief-profile features", flush=True)
    features = relief_profile.build_features(elevation, foot)
    del elevation
    np.save(target, features)
    dump(meta, {"inputs": key, "sha256": uniqueness.sha256_file(target),
                "shape": list(features.shape), "names": list(relief_profile.FEATURE_NAMES)})
    del features
    gc.collect()
    return np.load(target, mmap_mode="r")


def make_split(seed: int, labels: np.ndarray, foot: np.ndarray, groups: np.ndarray):
    split = holdout.make_segment_split(labels, foot, groups, seed, frac=0.2)
    train = holdout.buffered_training_mask(split, foot, buffer_px=6.0)
    if (np.any(split.hidden & split.known) or np.any(train & split.hidden)
            or not np.array_equal(split.hidden | split.known, labels & foot)):
        raise ValueError(f"invalid split partition/training buffer for seed {seed}")
    hidden_ids = np.unique(groups[split.hidden])
    if np.any(np.isin(groups[split.known], hidden_ids)):
        raise ValueError(f"hidden FID appears in visible labels for seed {seed}")
    return split, train


def auc_one(positive: np.ndarray, negative: np.ndarray) -> dict:
    positive = positive[np.isfinite(positive)]
    negative = negative[np.isfinite(negative)]
    if not len(positive) or not len(negative):
        raise ValueError("undefined single-feature AUC: no finite observations in one class")
    vals = np.concatenate((positive, negative)).astype(np.float64, copy=False)
    y = np.r_[np.ones(len(positive), dtype=np.uint8), np.zeros(len(negative), dtype=np.uint8)]
    auc = float(roc_auc_score(y, vals))
    if not np.isfinite(auc):
        raise ValueError("undefined single-feature AUC")
    return {"auc": auc, "direction_invariant_auc": max(auc, 1.0 - auc),
            "positive_observations": len(positive), "negative_observations": len(negative)}


def run_canary(foot, labels, groups, X, extra, names) -> dict:
    print("E1: testing every feature alone across five whole-FID splits", flush=True)
    negative = np.flatnonzero(~labels[foot])
    rows = []
    max_auc = 0.0
    for seed in SEEDS:
        check_time()
        split, _ = make_split(seed, labels, foot, groups)
        pos = np.flatnonzero(split.hidden[foot])
        neg = np.random.default_rng(seed).choice(negative, size=min(100_000, len(negative)), replace=False)
        features = {}
        for matrix, columns in ((X, names), (extra, relief_profile.FEATURE_NAMES)):
            for j, name in enumerate(columns):
                result = auc_one(np.asarray(matrix[pos, j]), np.asarray(matrix[neg, j]))
                features[name] = result
                max_auc = max(max_auc, result["direction_invariant_auc"])
        row = {"seed": seed, "withheld_positives": int(len(pos)),
               "hidden_group_count": len(split.hidden_group_ids), "features": features}
        rows.append(row)
        print(f"  seed {seed}: {len(pos)} positives, max direction-invariant AUC {max_auc:.4f}", flush=True)
    out = {"label": "single-feature leakage canary (not a score)", "seeds": list(SEEDS),
           "features_tested": len(names) + len(relief_profile.FEATURE_NAMES),
           "max_direction_invariant_auc": max_auc, "threshold": 0.90,
           "pass": max_auc <= 0.90, "per_seed": rows}
    dump(CANARY, out)
    return out


def emit(prob, foot, known):
    """Emitter has no argument containing hidden labels or the training/scoring buffer."""
    distance = distance_transform_edt(~known)
    ridge = oof_detector.ridge_nms(prob, foot)
    eligible = ridge & foot & (distance > 2.0)
    dots = sub.priority_poisson_disk(prob, eligible, 2.8, BUDGET)
    if int(dots.sum()) != BUDGET or np.any(dots & known):
        raise ValueError("emitter failed fixed dot budget or emitted on visible catalogue")
    return dots


def pooled(cells: list[dict]) -> float:
    tp = sum(c["TPw"] for c in cells)
    fp = sum(c["FPw"] for c in cells)
    fn = sum(c["FNw"] for c in cells)
    return float(tp / (tp + metric.ALPHA * fp + metric.BETA * fn + metric.EPS))


def bootstrap(cand: list[dict], control: list[dict]) -> dict:
    rng = np.random.default_rng(20261027)
    pick = rng.integers(0, len(cand), size=(10_000, len(cand)))
    def samples(cells):
        stats = np.array([[c["TPw"], c["FPw"], c["FNw"]] for c in cells])
        s = stats[pick].sum(axis=1)
        return s[:, 0] / (s[:, 0] + metric.ALPHA * s[:, 1] + metric.BETA * s[:, 2] + metric.EPS)
    a, b = samples(cand), samples(control)
    ci = lambda x: [float(v) for v in np.percentile(x, [2.5, 97.5])]  # noqa: E731
    return {"candidate_pooled": pooled(cand), "candidate_ci95": ci(a),
            "control_pooled": pooled(control), "control_ci95": ci(b),
            "pooled_delta": pooled(cand) - pooled(control), "paired_delta_ci95": ci(a - b),
            "positive_splits": sum(a["dti"] > b["dti"] for a, b in zip(cand, control))}


def run_holdout(foot, labels, groups, extra) -> dict:
    print("E2: paired full-kernel whole-FID holdout", flush=True)
    candidates, controls, rows = [], [], []
    for seed in SEEDS:
        check_time()
        t = time.monotonic()
        split, train = make_split(seed, labels, foot, groups)
        # Both arms use exactly the same training labels, mask, RNG and placement.
        cells = {}
        for name, features in (("control", None), ("candidate", extra)):
            p = oof_detector.fit_predict_visible_probabilities(
                foot, split.known, train, extra=features, seed=2026 + seed
            )
            dots = emit(p, foot, split.known)
            cells[name] = metric.dti_binary(dots, split.hidden, valid=foot, known=split.known)
            del p, dots
            gc.collect()
        candidates.append(cells["candidate"])
        controls.append(cells["control"])
        rows.append({"seed": seed, "hidden_groups": len(split.hidden_group_ids),
                     "withheld_positives": int(split.hidden.sum()), **cells})
        dump(RESULT, {"status": "in_progress", "label": "HOLDOUT-DTI", "evaluator": EVALUATOR,
                      "per_seed": rows})
        print(f"  seed {seed}: candidate={cells['candidate']['dti']:.5f} "
              f"control={cells['control']['dti']:.5f}; {time.monotonic() - t:.1f}s", flush=True)
    stats = bootstrap(candidates, controls)
    passed = (stats["candidate_pooled"] > stats["control_pooled"]
              and stats["paired_delta_ci95"][0] > 0 and stats["positive_splits"] >= 4)
    out = {"status": "complete", "label": "HOLDOUT-DTI", "evaluator": EVALUATOR,
           "metric": {"alpha": 0.2, "beta": 0.8, "radius_m": 300, "kernel": "triangular"},
           "seeds": list(SEEDS), "n_withheld_positives_total": sum(r["withheld_positives"] for r in rows),
           "bootstrap": "10000 paired pooled-statistic seed resamples; repeated hides are not independent faults",
           "statistics": stats, "screen_pass": passed,
           "h31_same_split_comparison": "not run; required for promotion even if screen passes",
           "gate_efficacy_pass": False, "per_seed": rows}
    dump(RESULT, out)
    return out


def references() -> tuple[list[dict], dict]:
    manifest_path = paths.DATA / "parallel_registry/cache_manifest.json"
    import check_parallel_uniqueness as checker
    manifest = checker.validated_manifest(manifest_path, paths.TEMPLATE,
                                          paths.REGISTRY / "parallel_submission_registry.json")
    cache_root = manifest_path.parent.parent.resolve()
    rows = []
    for item in manifest["entries"]:
        p = (cache_root / item["local"]).resolve()
        if not p.is_relative_to(cache_root):
            raise ValueError("unsafe parallel registry path")
        rows.append({"id": item["id"], "path": p, "sha256": item["sha256"], "kind": "pinned peer"})
    for p in sorted((ROOT / "docs/downloads").rglob("*.tif")):
        rows.append({"id": str(p.relative_to(ROOT)), "path": p,
                     "sha256": uniqueness.sha256_file(p), "kind": "local repository"})
    # Additional current-head focus-site coverage when the independent inventory is ready.
    # A partial inventory is useful for detecting duplicates but is never a global proof.
    inventory_path = paths.EVIDENCE / "focus_inventory_20261027.json"
    inventory_snapshot = {"sha256": None, "complete": False}
    if inventory_path.exists():
        # One immutable byte snapshot supplies both reference rows and completeness.
        inventory_bytes = inventory_path.read_bytes()
        inventory = json.loads(inventory_bytes)
        inventory_snapshot = {"sha256": hashlib.sha256(inventory_bytes).hexdigest(),
                              "complete": inventory.get("complete") is True}
        if inventory.get("template_sha256") != uniqueness.sha256_file(paths.TEMPLATE):
            raise ValueError("focus inventory template hash mismatch")
        for site in inventory.get("sites", []):
            for item in site.get("files", []):
                if item.get("blob_verified") and item.get("binary_grid_valid"):
                    p = (paths.DATA / item["cache"]).resolve()
                    if not p.is_relative_to(paths.DATA.resolve()):
                        raise ValueError("unsafe focus-inventory cache path")
                    rows.append({"id": f"{site['site']}@{site['head'][:12]}:{item['path']}",
                                 "path": p, "sha256": item["sha256"], "kind": "current focus site"})
    if not rows:
        raise ValueError("no uniqueness references")
    return rows, inventory_snapshot


def screen_surface(surface, foot, refs) -> dict:
    ranks, mean, std = uniqueness.surface_ranks(surface, foot)
    rows = []
    for row in refs:
        check_time()
        ref = uniqueness.read_reference(row["path"], paths.TEMPLATE, foot, row["sha256"])
        rho = uniqueness.surface_binary_spearman(ranks, mean, std, ref[foot])
        rows.append({"id": row["id"], "kind": row["kind"], "sha256": row["sha256"], "spearman": rho})
        if abs(rho) > 0.90:
            return {"pass": False, "duplicate": row["id"], "rows": rows}
    return {"pass": True, "duplicate": None, "rows": rows}


def screen_dots(dots, foot, refs) -> dict:
    rows = []
    for row in refs:
        check_time()
        ref = uniqueness.read_reference(row["path"], paths.TEMPLATE, foot, row["sha256"])
        result = uniqueness.dot_comparison(dots, ref, foot)
        rows.append({"id": row["id"], "kind": row["kind"], "sha256": row["sha256"], **result})
        if abs(result["spearman"]) > 0.90 or result["dot_overlap_within_3px"] > 0.70:
            return {"pass": False, "duplicate": row["id"], "rows": rows}
    return {"pass": True, "duplicate": None, "rows": rows}


def run_artifact(foot, labels, extra, card) -> None:
    print("E3: full-fit pre-placement and final-dot uniqueness screens", flush=True)
    p = oof_detector.fit_predict_visible_probabilities(foot, labels, foot, extra=extra, seed=20261027)
    refs, inventory_snapshot = references()
    surf = screen_surface(p, foot, refs)
    report = {"scope": "12 pinned peers, in-repository TIFFs, and available current focus-site TIFFs; not a global registry",
              "focus_inventory_sha256": inventory_snapshot["sha256"],
              "focus_inventory_complete": inventory_snapshot["complete"],
              "n_references_expected": len(refs), "surface": surf, "dots": None}
    dump(COMPARISONS, report)
    if not surf["pass"]:
        card["reason"] = f"duplicate pre-placement surface: {surf['duplicate']}"
        card["uniqueness_vs_registry"] = {"pass": False, "duplicate": surf["duplicate"]}
        return
    dots = emit(p, foot, labels)
    del p
    dot = screen_dots(dots, foot, refs)
    report["dots"] = dot
    dump(COMPARISONS, report)
    max_surface = max(abs(row["spearman"]) for row in surf["rows"])
    max_dot = max(row["dot_overlap_within_3px"] for row in dot["rows"])
    max_dot_rho = max(abs(row["spearman"]) for row in dot["rows"])
    card["uniqueness_vs_registry"] = {
        "pass": dot["pass"], "duplicate": dot["duplicate"], "reference_count": len(refs),
        "references_checked_before_stop": len(dot["rows"]), "max_surface_abs_spearman": max_surface,
        "max_dot_abs_spearman": max_dot_rho, "max_dot_overlap_within_3px_euclidean": max_dot,
        "detail_file": str(COMPARISONS.relative_to(ROOT)), "scope": report["scope"]}
    if not dot["pass"]:
        card["reason"] = f"duplicate final dots: {dot['duplicate']}"
        return
    content_id = hashlib.sha256(np.packbits(dots[foot]).tobytes()).hexdigest()[:12]
    filename = f"gems27-h29-5-relief-profile-20261027-{content_id}-allfinite.tif"
    directory = ROOT / "docs/downloads/research"
    path = submission.write_geotiff(dots.astype(np.float32), paths.TEMPLATE, directory / filename, outside="zero")
    verification = submission.verify_geotiff(path, paths.TEMPLATE)
    card["validator"] = {"zeros_hard_pass": verification["hard_checks_passed"],
                         "zeros_checks": verification["checks"],
                         "no_catalogue_dots": not bool(np.any(dots & labels))}
    if not verification["hard_checks_passed"] or not card["validator"]["no_catalogue_dots"]:
        raise ValueError("independent output validator failed")
    z = submission.zip_single(path)
    card["raster"] = {"directory": str(directory.relative_to(ROOT)), "primary_allfinite": filename,
                      "sha256": uniqueness.sha256_file(path), "content_id": content_id,
                      "dots": int(dots.sum()), "zip": z.name, "zip_sha256": uniqueness.sha256_file(z)}
    card["reason"] = "research-only: paired H31 comparison and separate selector are not complete"


def main() -> int:
    card = {"schema": "parallel-run-card-v3", "generated_utc": datetime.now(timezone.utc).isoformat(),
            "hypothesis": "H29-5 detrended-relief range-front profile proxy",
            "mechanism": "signed higher/lower-side slope contrast and transverse concavity with tangent support",
            "named_non_fault_mimic": "erosional valley edges, lithologic contacts and engineered cuts",
            "preregistration": str(PREREG.relative_to(ROOT)), "preregistration_sha256": uniqueness.sha256_file(PREREG),
            "submission_name": NAME, "note_max_140_chars": NOTE, "verdict": "negative",
            "ok_to_submit": False, "holdout": None, "uniqueness_vs_registry": None,
            "raster": None, "validator": None, "experiments_started": []}
    try:
        if len(NOTE) > 140:
            raise ValueError("submission note exceeds 140 characters")
        inputs = base.verify_inputs()
        foot = grid.load_footprint(paths.TEMPLATE)
        labels = grid.load_labels(paths.LABELS) & foot
        groups, group_meta = base.load_or_build_group_map(labels, foot, inputs)
        X = np.load(paths.PREPARED_FEATURES, mmap_mode="r")
        card["input_hashes"] = {"prepared_features": inputs["prepared_features_sha256"],
                                "group_map": group_meta["array_sha256"]}
        card["experiments_started"].append("E1 canary")
        extra = prepare(foot, inputs)
        canary = run_canary(foot, labels, groups, X, extra, inputs["feature_names"])
        card["canary"] = {"pass": canary["pass"], "max_auc": canary["max_direction_invariant_auc"],
                          "features_tested": canary["features_tested"], "detail": str(CANARY.relative_to(ROOT))}
        if not canary["pass"]:
            card["reason"] = "leakage canary failed; E2 and E3 stopped"
            return 2
        card["experiments_started"].append("E2 paired holdout")
        h = run_holdout(foot, labels, groups, extra)
        card["holdout"] = {"label": h["label"], "evaluator": h["evaluator"],
                           "n_withheld_positives_total": h["n_withheld_positives_total"],
                           "seeds": h["seeds"], "statistics": h["statistics"],
                           "canary_max_auc": canary["max_direction_invariant_auc"],
                           "screen_pass": h["screen_pass"], "gate_efficacy_pass": False,
                           "h31_same_split_comparison": h["h31_same_split_comparison"]}
        card["experiments_started"].append("E3 full-fit uniqueness and validator")
        run_artifact(foot, labels, extra, card)
        return 0
    except Exception as exc:  # fail closed and keep an auditable negative card
        card["reason"] = f"incomplete: {type(exc).__name__}: {exc}"
        print(card["reason"], file=sys.stderr, flush=True)
        return 2
    finally:
        card["runtime_seconds"] = round(time.monotonic() - START, 1)
        dump(CARD, card)
        print(f"wrote {CARD}; verdict={card['verdict']}; {card.get('reason', '')}", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
