#!/usr/bin/env python3
"""Frozen H29-1 convergent-tip relay test; see knowledge/12_preregistration_H29-1.md."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from gems27 import grid, holdout, links, metric, oof_detector, paths  # noqa: E402
from gems27.candidates import RULE, SPACING, dedupe_mutual, evidence_score  # noqa: E402
from gems27.graph import build_graph  # noqa: E402
from gems27.relay_consensus import convergent_tip_mask  # noqa: E402
from run_h28_1_edge_holdout import load_or_build_edge_matrix  # noqa: E402

SEEDS = list(range(160, 170))
BUFFER_PX = 3
BOOTSTRAPS = 10_000
BOOTSTRAP_SEED = 20261025


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def evaluate(pred: np.ndarray, truth: np.ndarray, active: np.ndarray) -> dict[str, float | int]:
    pred = np.asarray(pred, bool) & active
    truth = np.asarray(truth, bool) & active
    stats = metric.dti_binary(pred.astype(np.uint8), truth, valid=active)
    # Exact counts are enough for the pooled binary DTI; FN is n_truth - TPw.
    return {
        "tpw": float(stats["TPw"]),
        "fpw": float(stats["FPw"]),
        "fnw": float(stats["FNw"]),
        "n_truth": int(stats["n_truth"]),
        "dots": int(stats["n_emitted"]),
    }


def dti_from_sums(rows: list[dict], name: str) -> float:
    tp = sum(float(r[name]["tpw"]) for r in rows)
    fp = sum(float(r[name]["fpw"]) for r in rows)
    fn = sum(float(r[name]["fnw"]) for r in rows)
    den = tp + metric.ALPHA * fp + metric.BETA * fn + metric.EPS
    return tp / den if den > 0 else 0.0


def seed_dti(rows: list[dict], seed: int, name: str) -> float:
    return dti_from_sums([r for r in rows if r["seed"] == seed], name)


def cluster_bootstrap(rows: list[dict]) -> dict[str, list[float] | float]:
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    by_seed = {s: [r for r in rows if r["seed"] == s] for s in SEEDS}
    out = {"baseline": [], "candidate": [], "paired_delta": []}
    for _ in range(BOOTSTRAPS):
        sampled = rng.choice(SEEDS, size=len(SEEDS), replace=True)
        sample = [r for s in sampled for r in by_seed[int(s)]]
        b, c = dti_from_sums(sample, "baseline"), dti_from_sums(sample, "candidate")
        out["baseline"].append(b)
        out["candidate"].append(c)
        out["paired_delta"].append(c - b)
    return {
        "method": "10,000 seed-cluster bootstrap resamples; each draw resamples 10 seeds with replacement and pools TPw/FPw/FNw over four folds",
        "seed": BOOTSTRAP_SEED,
        "baseline_ci95": [float(np.quantile(out["baseline"], 0.025)), float(np.quantile(out["baseline"], 0.975))],
        "candidate_ci95": [float(np.quantile(out["candidate"], 0.025)), float(np.quantile(out["candidate"], 0.975))],
        "paired_delta_ci95": [float(np.quantile(out["paired_delta"], 0.025)), float(np.quantile(out["paired_delta"], 0.975))],
    }


def main() -> int:
    started = time.time()
    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    fold = holdout.make_quadrant_folds(foot)
    if labels.shape != foot.shape:
        raise SystemExit("labels and template grid differ")

    print("Building/loading the hash-checked six-band H28-1 edge cache...", flush=True)
    edge_features, edge_meta = load_or_build_edge_matrix(foot)
    print("Fitting the existing spatial 4-fold OOF H28 detector (32 + 6 cached features)...", flush=True)
    edge_oof = oof_detector.fit_predict_oof_probabilities(foot, labels, fold, extra_features=edge_features)
    if not (np.isfinite(edge_oof[foot]).all() and np.all((edge_oof[foot] >= 0) & (edge_oof[foot] <= 1))):
        raise SystemExit("OOF probabilities are non-finite or outside [0,1]")
    ridge = oof_detector.ridge_nms(edge_oof, foot, sigma=1.0)

    rows: list[dict] = []
    feature_auc_counts = {"tp": 0, "fn": 0, "fp": 0, "tn": 0}
    overlap_known = 0
    for seed in SEEDS:
        for fold_id in range(4):
            split = holdout.make_split(labels, fold, fold_id, seed, feature_buffer_px=BUFFER_PX)
            fm = split.fold_mask
            sl = holdout.crop(None, fm)
            fold_crop = fm[sl]
            hidden = split.hidden[sl]
            known = split.known[sl]
            feature_known = split.feature_known
            known_feature_crop = (feature_known & fm)[sl]
            truth = hidden & fold_crop & ~known
            active = fold_crop & ~known

            # OOF model predictions are built without any labels in this quadrant. The emission
            # budget and visible-label mask are then formed using only this cell's training-visible mask.
            base = oof_detector.build_oof_dotted_base(
                edge_oof[sl], ridge[sl], fold_crop, known,
                budget_frac=oof_detector.PRE_THIN_FRAC, thin_d=1.5,
            ) & active
            d_known = distance_transform_edt(~known_feature_crop) if known_feature_crop.any() else np.full(known.shape, np.inf)
            base_pruned = base & (d_known > 1.0)
            d_base_pruned = distance_transform_edt(~base_pruned) if base_pruned.any() else np.full(known.shape, np.inf)

            # Every graph-derived feature is recomputed from buffered visible fault pixels only.
            graph = build_graph(feature_known, with_edges=False)
            all_links = links.generate_links(graph, region=fm, **RULE)
            if not all_links.empty:
                scores = evidence_score(all_links)
                eligible = dedupe_mutual(all_links.loc[scores >= 3].reset_index(drop=True))
                support = convergent_tip_mask(eligible)
                relay_links = eligible.loc[support].reset_index(drop=True)
            else:
                eligible = all_links
                relay_links = all_links
            topology_all = links.rasterize_links(eligible, labels.shape, SPACING)[sl] & active
            topology_relay = links.rasterize_links(relay_links, labels.shape, SPACING)[sl] & active

            # Baseline is the current-best recipe; treatment replaces its full T-v2 add-on with
            # the frozen convergent subset, not a second copy of pixels already in T-v2.
            baseline = base_pruned | (topology_all & (d_base_pruned >= metric.RADIUS_PX))
            candidate = base_pruned | (topology_relay & (d_base_pruned >= metric.RADIUS_PX))

            # Same-size null: random eligible links, one deterministic draw per cell.
            rng = np.random.default_rng(BOOTSTRAP_SEED + 100 * seed + fold_id)
            k = min(len(relay_links), len(eligible))
            if k and len(eligible):
                null_idx = np.sort(rng.choice(len(eligible), size=k, replace=False))
                null_links = eligible.iloc[null_idx]
                topology_null = links.rasterize_links(null_links, labels.shape, SPACING)[sl] & active
                null_pred = base_pruned | (topology_null & (d_base_pruned >= metric.RADIUS_PX))
            else:
                null_pred = base_pruned.copy()

            for name, pred in (("baseline", baseline), ("candidate", candidate), ("same_size_random", null_pred)):
                overlap = int((pred & known).sum())
                overlap_known += overlap
                if overlap:
                    raise SystemExit(f"prediction overlaps visible catalogue by {overlap} cells; split={seed}/{fold_id}/{name}")

            cand_only = topology_relay & (d_base_pruned >= metric.RADIUS_PX) & active
            pos = int((truth & cand_only).sum())
            neg = int((~truth & active & cand_only).sum())
            n_pos, n_neg = int(truth.sum()), int((active & ~truth).sum())
            feature_auc_counts["tp"] += pos
            feature_auc_counts["fn"] += n_pos - pos
            feature_auc_counts["fp"] += neg
            feature_auc_counts["tn"] += n_neg - neg

            row = {
                "seed": seed,
                "fold": split.name,
                "fold_id": fold_id,
                "n_withheld_positive_px": int(truth.sum()),
                "feature_buffer_px": split.feature_buffer_px,
                "visible_fault_pixels_for_features": int(feature_known.sum()),
                "eligible_links": int(len(eligible)),
                "convergent_links": int(len(relay_links)),
                "all_topology_dots": int(topology_all.sum()),
                "convergent_topology_dots": int(topology_relay.sum()),
                "candidate_feature_tp": pos,
                "candidate_feature_fp": neg,
                "baseline": evaluate(baseline, truth, active),
                "candidate": evaluate(candidate, truth, active),
                "same_size_random": evaluate(null_pred, truth, active),
            }
            rows.append(row)
        print(f"seed {seed} complete ({time.time()-started:.0f}s)", flush=True)

    seed_deltas = {str(s): seed_dti(rows, s, "candidate") - seed_dti(rows, s, "baseline") for s in SEEDS}
    fold_gains = {}
    for fold_name in holdout.FOLD_NAMES:
        fold_rows = [r for r in rows if r["fold"] == fold_name]
        fold_gains[fold_name] = dti_from_sums(fold_rows, "candidate") - dti_from_sums(fold_rows, "baseline")
    pooled_baseline = dti_from_sums(rows, "baseline")
    pooled_candidate = dti_from_sums(rows, "candidate")
    pooled_null = dti_from_sums(rows, "same_size_random")
    auc_denom_pos = feature_auc_counts["tp"] + feature_auc_counts["fn"]
    auc_denom_neg = feature_auc_counts["fp"] + feature_auc_counts["tn"]
    feature_auc = 0.5 * (
        feature_auc_counts["tp"] / max(auc_denom_pos, 1)
        + feature_auc_counts["tn"] / max(auc_denom_neg, 1)
    )
    bootstrap = cluster_bootstrap(rows)
    gates = {
        "mean_pooled_paired_delta_ge_0_001": pooled_candidate - pooled_baseline >= 0.001,
        "paired_delta_ci_lower_gt_0": bootstrap["paired_delta_ci95"][0] > 0,
        "at_least_3_of_4_pooled_fold_gains_positive": sum(v > 0 for v in fold_gains.values()) >= 3,
        "at_least_8_of_10_seed_gains_positive": sum(v > 0 for v in seed_deltas.values()) >= 8,
        "feature_only_pooled_auc_le_0_90": feature_auc <= 0.90,
        "known_catalogue_overlap_zero": overlap_known == 0,
        "exact_registered_seed_list": SEEDS == list(range(160, 170)) and len(rows) == 40,
    }
    n_withheld = sum(int(r["n_withheld_positive_px"]) for r in rows)
    out = {
        "schema": "GEMSDOE27-H29-1-v1",
        "preregistration": "knowledge/12_preregistration_H29-1.md",
        "evaluator": {
            "module": "src/gems27/holdout.py make_split(feature_buffer_px=3) + src/gems27/metric.py dti_binary",
            "holdout_sha256": sha256_file(ROOT / "src/gems27/holdout.py"),
            "metric_sha256": sha256_file(ROOT / "src/gems27/metric.py"),
            "buffer_px": BUFFER_PX,
            "seeds": SEEDS,
            "folds": holdout.FOLD_NAMES,
            "withheld_positive_cell_instances_across_40_cells": n_withheld,
            "mean_withheld_positive_px_per_seed": float(np.mean([sum(r["n_withheld_positive_px"] for r in rows if r["seed"] == s) for s in SEEDS])),
            "alpha": metric.ALPHA,
            "beta": metric.BETA,
            "kernel_radius_px": metric.RADIUS_PX,
            "kernel_metres": 300,
            "feature_generation_visible_labels_only": True,
        },
        "inputs": {
            "prepared_features_sha256": sha256_file(paths.PREPARED_FEATURES),
            "edge_feature_cache_sha256": edge_meta["sha256"],
            "edge_feature_metadata": edge_meta,
        },
        "leakage_canary": {
            "feature": "binary H29-1 convergent topology dots alone, after subtracting same-run baseline dots within 300 m",
            "pooled_auc_binary_tie_aware": float(feature_auc),
            "confusion_instances": feature_auc_counts,
            "canary_passed": bool(feature_auc <= 0.90),
        },
        "pooled_dti": {
            "baseline": pooled_baseline,
            "candidate": pooled_candidate,
            "same_size_random_control": pooled_null,
            "paired_delta": pooled_candidate - pooled_baseline,
            "ci95_seed_cluster_bootstrap": bootstrap,
            "seed_level_paired_deltas": seed_deltas,
            "fold_level_pooled_deltas": fold_gains,
        },
        "candidate_surface": {
            "preplacement_feature": "H29-1 convergent-tip corridor subset of visible-label-only z>=3 topology links",
            "buffered_feature_sources": "split.feature_known only",
            "candidate_links_mean_per_cell": float(np.mean([r["convergent_links"] for r in rows])),
            "eligible_links_mean_per_cell": float(np.mean([r["eligible_links"] for r in rows])),
            "candidate_dots_mean_per_cell": float(np.mean([r["convergent_topology_dots"] for r in rows])),
        },
        "gates": gates,
        "gate_passed": bool(all(gates.values())),
        "tiff_written": False,
        "cell_results": rows,
        "elapsed_seconds": time.time() - started,
    }
    out_path = paths.EVIDENCE / "h29_1_relay_consensus_holdout.json"
    out_path.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: out[k] for k in ("evaluator", "leakage_canary", "pooled_dti", "candidate_surface", "gates", "gate_passed")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
