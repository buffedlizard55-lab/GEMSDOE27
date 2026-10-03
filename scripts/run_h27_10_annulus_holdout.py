#!/usr/bin/env python3
"""Run the frozen H27-10 100-300 m annulus substitution on fresh seeds 150-159.

The runner writes evidence JSON only. It never emits a submission TIFF and never contacts
DrivenData. Protocol: knowledge/03_preregistration_topology_gate.md#addendum-f-h27-10.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import annulus, grid, holdout, links, metric, oof_detector, paths  # noqa: E402
from gems27.candidates import RULE, SPACING, dedupe_mutual, evidence_score  # noqa: E402
from gems27.graph import build_graph  # noqa: E402
from run_h28_1_edge_holdout import (  # noqa: E402
    EDGE_PARAMETERS,
    EXPECTED_SOURCE_BANDS,
    load_or_build_edge_matrix,
    parse_seeds,
    sha256_file,
    validate_prepared_feature_metadata,
)

M_LIVE = metric.inclusion_threshold(0.2477)
INNER_ANNULUS_PX = 1.0
OUTER_ANNULUS_PX = 3.0
MIN_DOT_DISTANCE_PX = 1.5
BASELINE_NAME = "H28_edge_best_Tv2_prune_r1"
CANDIDATE_NAME = "H27_10_annulus_reallocation"


def distance_to(mask: np.ndarray) -> np.ndarray:
    return distance_transform_edt(~mask) if mask.any() else np.full(mask.shape, np.inf)


def eval_set(
    pred: np.ndarray, truth: np.ndarray, active: np.ndarray, truth_kernel: np.ndarray
) -> dict[str, float | int]:
    selected = pred & active
    n_truth = int(truth.sum())
    if not selected.any() or n_truth == 0:
        tp = 0.0
        fp = float((1.0 - truth_kernel[selected]).sum()) if selected.any() else 0.0
        score = 0.0
    else:
        tp = float(metric.kernel_from_distance(distance_transform_edt(~selected)[truth]).sum())
        fp = float((1.0 - truth_kernel[selected]).sum())
        score = tp / (tp + 0.2 * fp + 0.8 * (n_truth - tp) + 1e-7)
    return {"tp": tp, "fp": fp, "dti": score, "dots": int(selected.sum())}


def pooled_efficiency(records: list[dict]) -> float | None:
    tp = sum(float(record["tp"]) for record in records)
    fp = sum(float(record["fp"]) for record in records)
    return tp / fp if fp > 0.0 else None


def finite_ratio(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator > 0.0 else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", default="150-159", type=parse_seeds)
    parser.add_argument("--out", default=str(paths.EVIDENCE / "h27_10_annulus_holdout.json"))
    parser.add_argument("--force-edge-cache", action="store_true")
    parser.add_argument("--overwrite", action="store_true", help="replace evidence only for a documented rerun")
    args = parser.parse_args()
    seeds: list[int] = args.seeds
    if seeds != list(range(150, 160)):
        raise SystemExit("Addendum F is frozen to fresh seeds 150-159; no other seed range is accepted")
    out_path = Path(args.out)
    if out_path.exists() and not args.overwrite:
        raise SystemExit(f"Evidence file already exists: {out_path}; use --overwrite only for a documented rerun")

    started = time.time()
    root = Path(__file__).resolve().parents[1]
    code_hashes = {
        "runner": sha256_file(Path(__file__).resolve()),
        "annulus_transform": sha256_file(root / "src/gems27/annulus.py"),
        "h28_runner_helpers": sha256_file(root / "scripts/run_h28_1_edge_holdout.py"),
        "oof_detector": sha256_file(root / "src/gems27/oof_detector.py"),
    }

    footprint = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    if labels.shape != footprint.shape or not np.isin(labels, (False, True, 0, 1)).all():
        raise SystemExit("Labels have the wrong shape or non-binary values")
    folds = holdout.make_quadrant_folds(footprint)
    if any(not np.any(folds == fold_id) for fold_id in range(4)):
        raise SystemExit("All four spatial folds must contain footprint cells")
    prepared_check = validate_prepared_feature_metadata(footprint)

    print("Building/loading the hash-validated H28-1 edge matrix...", flush=True)
    edge_matrix, edge_meta = load_or_build_edge_matrix(footprint, force=args.force_edge_cache)
    if edge_matrix.shape[0] != int(footprint.sum()):
        raise SystemExit("H28-1 matrix is not aligned to row-major footprint pixels")

    print("Training strictly 4-fold OOF H28-1 detector (seed 2026)...", flush=True)
    edge_oof = oof_detector.fit_predict_oof_probabilities(
        footprint, labels, folds, extra_features=edge_matrix, seed=2026
    )
    probabilities_valid = bool(
        np.isfinite(edge_oof[footprint]).all()
        and np.all((edge_oof[footprint] >= 0.0) & (edge_oof[footprint] <= 1.0))
    )
    edge_values_valid = bool(
        np.isfinite(edge_matrix).all()
        and float(edge_matrix.min()) >= 0.0
        and float(edge_matrix.max()) <= 1.0
    )
    if not probabilities_valid or not edge_values_valid:
        raise SystemExit("OOF probabilities or H28-1 features are non-finite or outside [0,1]")
    edge_ridges = oof_detector.ridge_nms(edge_oof, footprint, sigma=1.0)

    cells: list[dict] = []
    known_overlap_pixels = 0
    annulus_add_records: list[dict] = []
    farfield_drop_records: list[dict] = []
    for seed in seeds:
        for fold_id in range(4):
            split = holdout.make_split(labels, folds, fold_id, seed)
            fold_mask = split.fold_mask
            crop = holdout.crop(None, fold_mask)
            hidden = split.hidden[crop]
            known = (split.known & fold_mask)[crop]
            fold_crop = fold_mask[crop]
            truth = hidden & fold_crop & ~known
            active = fold_crop & ~known
            truth_kernel = (
                metric.kernel_from_distance(distance_transform_edt(~truth))
                if truth.any()
                else np.zeros_like(truth, dtype=float)
            )

            probabilities = edge_oof[crop]
            ridges = edge_ridges[crop]
            base = (
                oof_detector.build_oof_dotted_base(
                    probabilities,
                    ridges,
                    fold_crop,
                    known,
                    budget_frac=oof_detector.PRE_THIN_FRAC,
                    thin_d=1.5,
                )
                & active
            )
            distance_known = distance_to(known)
            base_pruned = base & (distance_known > 1.0)
            r1_removed = base & (distance_known <= 1.0)
            replacement_count = int(r1_removed.sum())

            # T-v2 candidates are reconstructed from the same hidden/known split and are held fixed.
            graph = build_graph(split.known, with_edges=False)
            link_frame = links.generate_links(graph, region=fold_mask, **RULE)
            link_evidence = evidence_score(link_frame)
            selected_links = dedupe_mutual(link_frame[link_evidence >= 3])
            topology_raw = links.rasterize_links(selected_links, labels.shape, SPACING)[crop] & active
            distance_base_pruned = distance_to(base_pruned)
            topology = topology_raw & (distance_base_pruned >= metric.RADIUS_PX)
            baseline = base_pruned | topology

            # Fixed-count H27-10 exchange: lowest-score >300 m base dots leave; top annulus ridges enter.
            source_pool = base_pruned & (distance_known > OUTER_ANNULUS_PX)
            source_indices = np.flatnonzero(source_pool)
            candidate_mask = annulus.distance_annulus(
                distance_known,
                inner_px=INNER_ANNULUS_PX,
                outer_px=OUTER_ANNULUS_PX,
            )
            candidate_mask &= ridges & active
            source_shortfall = max(0, replacement_count - int(source_indices.size))
            drop = np.zeros(base.shape, dtype=bool)
            if source_shortfall == 0 and replacement_count > 0:
                flat_scores = probabilities.ravel()
                source_order = np.lexsort((source_indices, flat_scores[source_indices]))
                drop.ravel()[source_indices[source_order[:replacement_count]]] = True

            kept = (base_pruned & ~drop) | topology
            additions = annulus.select_score_ranked_spaced_candidates(
                probabilities,
                candidate_mask,
                kept,
                k=replacement_count,
                min_distance_px=MIN_DOT_DISTANCE_PX,
            )
            annulus_shortfall = max(0, replacement_count - int(additions.sum()))
            build_ok = source_shortfall == 0 and annulus_shortfall == 0
            row: dict = {
                "seed": seed,
                "fold": split.name,
                "n_truth": int(truth.sum()),
                "link_dots": int(topology.sum()),
                "r1_dots_reallocated": replacement_count,
                "source_pool_dots": int(source_indices.size),
                "annulus_ridge_pool_dots": int(candidate_mask.sum()),
                "source_shortfall": source_shortfall,
                "annulus_shortfall": annulus_shortfall,
                "candidate_build_ok": build_ok,
            }
            if not build_ok:
                row["candidate_build_error"] = "exact preregistered K could not be selected; cell is invalid"
                cells.append(row)
                print(
                    f"seed {seed} {split.name}: frozen K={replacement_count} unavailable "
                    f"(source shortfall={source_shortfall}, annulus shortfall={annulus_shortfall})",
                    flush=True,
                )
                continue

            candidate = kept | additions
            baseline_stats = eval_set(baseline, truth, active, truth_kernel)
            candidate_stats = eval_set(candidate, truth, active, truth_kernel)
            additions_stats = eval_set(additions, truth, active, truth_kernel)
            drop_stats = eval_set(drop, truth, active, truth_kernel)
            overlap = int((baseline & known).sum() + (candidate & known).sum())
            known_overlap_pixels += overlap
            distances_to_kept = distance_to(kept)
            distances_to_additions = distance_to(additions)
            additions_spaced = bool(
                not additions.any()
                or (
                    np.all(distances_to_kept[additions] >= MIN_DOT_DISTANCE_PX)
                    and np.all(distances_to_additions[additions] >= MIN_DOT_DISTANCE_PX)
                )
            )
            additions_in_annulus = bool(
                not additions.any()
                or np.all(
                    (distance_known[additions] > INNER_ANNULUS_PX)
                    & (distance_known[additions] <= OUTER_ANNULUS_PX)
                )
            )
            same_dot_count = int(baseline.sum()) == int(candidate.sum())
            row.update(
                {
                    BASELINE_NAME: baseline_stats,
                    CANDIDATE_NAME: candidate_stats,
                    "annulus_additions": additions_stats,
                    "farfield_removed": drop_stats,
                    "same_dot_count": same_dot_count,
                    "no_known_overlap": overlap == 0,
                    "annulus_additions_in_band": additions_in_annulus,
                    "annulus_additions_spaced": additions_spaced,
                }
            )
            annulus_add_records.append(additions_stats)
            farfield_drop_records.append(drop_stats)
            cells.append(row)

        seed_rows = [cell for cell in cells if cell["seed"] == seed]
        valid_rows = [cell for cell in seed_rows if cell["candidate_build_ok"]]
        if valid_rows:
            baseline_mean = float(np.mean([r[BASELINE_NAME]["dti"] for r in valid_rows]))
            candidate_mean = float(np.mean([r[CANDIDATE_NAME]["dti"] for r in valid_rows]))
            print(
                f"seed {seed} complete: baseline={baseline_mean:.4f}; "
                f"H27-10={candidate_mean:.4f}; elapsed={time.time() - started:.0f}s",
                flush=True,
            )

    valid_cells = [cell for cell in cells if cell["candidate_build_ok"]]
    all_deltas = [cell[CANDIDATE_NAME]["dti"] - cell[BASELINE_NAME]["dti"] for cell in valid_cells]
    gains_by_seed = {
        str(seed): float(
            np.mean(
                [cell[CANDIDATE_NAME]["dti"] - cell[BASELINE_NAME]["dti"] for cell in valid_cells if cell["seed"] == seed]
            )
        )
        for seed in seeds
        if any(cell["candidate_build_ok"] and cell["seed"] == seed for cell in cells)
    }
    gains_by_fold = {
        name: float(
            np.mean(
                [cell[CANDIDATE_NAME]["dti"] - cell[BASELINE_NAME]["dti"] for cell in valid_cells if cell["fold"] == name]
            )
        )
        for name in holdout.FOLD_NAMES
        if any(cell["candidate_build_ok"] and cell["fold"] == name for cell in cells)
    }
    mean_gain = float(np.mean(all_deltas)) if all_deltas else None
    annulus_efficiency = pooled_efficiency(annulus_add_records)
    farfield_efficiency = pooled_efficiency(farfield_drop_records)

    baseline_summary = {
        "mean_dti": finite_ratio(sum(c[BASELINE_NAME]["dti"] for c in valid_cells), len(valid_cells)),
        "mean_dots": float(np.mean([c[BASELINE_NAME]["dots"] for c in valid_cells])) if valid_cells else None,
        "mean_tp": float(np.mean([c[BASELINE_NAME]["tp"] for c in valid_cells])) if valid_cells else None,
        "mean_fp": float(np.mean([c[BASELINE_NAME]["fp"] for c in valid_cells])) if valid_cells else None,
    }
    candidate_summary = {
        "mean_dti": finite_ratio(sum(c[CANDIDATE_NAME]["dti"] for c in valid_cells), len(valid_cells)),
        "mean_dots": float(np.mean([c[CANDIDATE_NAME]["dots"] for c in valid_cells])) if valid_cells else None,
        "mean_tp": float(np.mean([c[CANDIDATE_NAME]["tp"] for c in valid_cells])) if valid_cells else None,
        "mean_fp": float(np.mean([c[CANDIDATE_NAME]["fp"] for c in valid_cells])) if valid_cells else None,
    }
    data_checks = {
        "footprint_cells": int(footprint.sum()),
        "label_positive_cells": int(labels[footprint].sum()),
        "fold_cells": {holdout.FOLD_NAMES[f]: int((folds == f).sum()) for f in range(4)},
        "prepared_feature_metadata": prepared_check,
        "h28_edge_source_bands": edge_meta["source_bands"],
        "h28_edge_parameters": edge_meta["parameters"],
        "h28_edge_cache_sha256": edge_meta["sha256"],
        "all_oof_probabilities_finite_and_in_0_1": probabilities_valid,
        "h28_edge_values_finite_and_in_0_1": edge_values_valid,
        "cells_total": len(cells),
        "cells_with_exact_swap": len(valid_cells),
        "all_swaps_exact_K": len(valid_cells) == len(cells) and all(c["candidate_build_ok"] for c in cells),
        "same_dot_count_every_cell": len(valid_cells) == len(cells) and all(c.get("same_dot_count") for c in valid_cells),
        "no_known_catalogue_overlap": known_overlap_pixels == 0,
        "known_catalogue_overlap_pixels_across_variants": known_overlap_pixels,
        "all_additions_inside_annulus": len(valid_cells) == len(cells) and all(c.get("annulus_additions_in_band") for c in valid_cells),
        "all_additions_respect_minimum_spacing": len(valid_cells) == len(cells) and all(c.get("annulus_additions_spaced") for c in valid_cells),
        "submission_written": False,
    }
    data_checks_passed = bool(
        probabilities_valid
        and edge_values_valid
        and prepared_check.get("n_features") == 32
        and edge_meta.get("source_bands") == EXPECTED_SOURCE_BANDS
        and edge_meta.get("parameters") == EDGE_PARAMETERS
        and data_checks["cells_total"] == len(seeds) * 4
        and data_checks["all_swaps_exact_K"]
        and data_checks["same_dot_count_every_cell"]
        and data_checks["no_known_catalogue_overlap"]
        and data_checks["all_additions_inside_annulus"]
        and data_checks["all_additions_respect_minimum_spacing"]
    )
    gate = {
        "mean_gain_at_least_0_001": bool(mean_gain is not None and mean_gain >= 0.001),
        "at_least_3_of_4_folds_improve": bool(sum(value > 0.0 for value in gains_by_fold.values()) >= 3),
        "at_least_8_of_10_seeds_improve": bool(
            len(gains_by_seed) == 10 and sum(value > 0.0 for value in gains_by_seed.values()) >= 8
        ),
        "annulus_efficiency_at_least_m_live_0_2477": bool(
            annulus_efficiency is not None and annulus_efficiency >= M_LIVE
        ),
        "annulus_efficiency_exceeds_removed_farfield_efficiency": bool(
            annulus_efficiency is not None
            and farfield_efficiency is not None
            and annulus_efficiency > farfield_efficiency
        ),
        "exactly_10_preregistered_seeds": seeds == list(range(150, 160)),
        "data_checks_passed": data_checks_passed,
    }
    gate["pass"] = all(gate.values())
    result = {
        "preregistration": "knowledge/03_preregistration_topology_gate.md#addendum-f-h27-10",
        "candidate": "H27-10 model-ranked 100-300 m offset-scarp annulus substitution",
        "seeds": seeds,
        "fold_names": holdout.FOLD_NAMES,
        "baseline": BASELINE_NAME,
        "candidate_variant": CANDIDATE_NAME,
        "baseline_summary": baseline_summary,
        "candidate_summary": candidate_summary,
        "candidate_minus_baseline_mean_gain": mean_gain,
        "gain_by_seed": gains_by_seed,
        "gain_by_fold": gains_by_fold,
        "positive_seed_count": int(sum(value > 0.0 for value in gains_by_seed.values())),
        "improved_fold_count": int(sum(value > 0.0 for value in gains_by_fold.values())),
        "gross_annulus_add_efficiency": annulus_efficiency,
        "gross_removed_farfield_efficiency": farfield_efficiency,
        "m_live_0_2477": M_LIVE,
        "code_sha256": code_hashes,
        "edge_feature_cache": edge_meta,
        "data_checks": data_checks,
        "gate": gate,
        "cell_results": cells,
        "seconds": time.time() - started,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "candidate_minus_baseline_mean_gain": mean_gain,
                "gain_by_seed": gains_by_seed,
                "gain_by_fold": gains_by_fold,
                "gross_annulus_add_efficiency": annulus_efficiency,
                "gross_removed_farfield_efficiency": farfield_efficiency,
                "gate": gate,
                "baseline": baseline_summary,
                "candidate": candidate_summary,
            },
            indent=2,
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
