"""Fail-closed publication policy; format validity alone never authorizes a slot.

This checks recorded evidence and binds it to bytes. It does not rerun an evaluator,
prove scientific novelty, or replace the selector / current registry comparison.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path


def publication_decision(card: dict, root: Path) -> dict:
    reasons = []

    def require(condition, reason):
        if not condition:
            reasons.append(reason)

    require(card.get("ok_to_submit") is True, "run card does not authorize submission")
    require(card.get("verdict") == "promote", "verdict is not promote")
    hold = card.get("holdout")
    hold = hold if isinstance(hold, dict) else {}
    require(hold.get("label") == "HOLDOUT-DTI", "missing HOLDOUT-DTI label")
    require(bool(hold.get("evaluator")), "missing evaluator version")
    n = hold.get("n_withheld_positives_total")
    require(isinstance(n, int) and not isinstance(n, bool) and n > 0,
            "missing withheld positive count")
    require(hold.get("gate_efficacy_pass") is True, "efficacy gate not explicitly passed")
    # Historical quadrant-component experiments are useful, but are not the whole-FID,
    # blind full-kernel protocol requested for prospective uploads.
    require(hold.get("split_scheme") == "whole-fid-segment-v1", "whole-FID split evidence missing")
    require(hold.get("visible_only_catalogue_features") is True, "visible-only catalogue features not proven")
    require(hold.get("training_buffer_verified") is True, "hidden-segment training buffer not proven")
    require(hold.get("emitter_blind_to_hidden_and_buffer") is True, "blind emission not proven")
    require(hold.get("full_kernel_scored") is True, "full 300m scoring kernel not proven")
    require(hold.get("all_model_features_canary_tested") is True, "not all input features have canaries")
    comparison = hold.get("current_best_comparison")
    comparison = comparison if isinstance(comparison, dict) else {}
    best_ci = comparison.get("paired_delta_ci95")
    require(hold.get("matched_current_best_comparison") is True
            and isinstance(comparison.get("control_id"), str) and bool(comparison["control_id"])
            and comparison.get("same_splits_and_buffer") is True
            and _finite(comparison.get("pooled_delta")) and comparison["pooled_delta"] > 0
            and isinstance(best_ci, list) and len(best_ci) == 2 and all(_finite(x) for x in best_ci)
            and 0 < best_ci[0] <= best_ci[1], "current-best matched control not proven")
    # Template fix (Session 9): lane arms are named per session (A, D, L, ...); accept the
    # generic "paired_candidate_minus_B" plus the historical arm-specific aliases.
    paired = hold.get("paired_candidate_minus_B",
                      hold.get("paired_D_minus_B", hold.get("paired_A_minus_B", {})))
    paired = paired if isinstance(paired, dict) else {}
    ci = paired.get("ci95", [])
    require(isinstance(ci, list) and len(ci) == 2 and all(_finite(x) for x in ci)
            and 0 < ci[0] <= ci[1], "paired improvement CI missing or does not exclude zero")
    auc = hold.get("canary_max_auc")
    # A feature and its negation carry the same information. Test both directions:
    # AUC 0.05 is as suspicious as 0.95; AUC 0.30 is not evidence of leakage.
    require(_finite(auc) and 0 <= auc <= 1 and max(auc, 1 - auc) <= 0.90,
            "canary missing or direction-invariant leakage threshold exceeded")
    uniqueness = card.get("uniqueness_vs_registry")
    uniqueness = uniqueness if isinstance(uniqueness, dict) else {}
    require(uniqueness.get("pass") is True, "uniqueness gate not passed")
    overlap = uniqueness.get("max_dot_overlap_within_3px_euclidean")
    rho = uniqueness.get("max_surface_spearman_armD",
                         uniqueness.get("max_surface_spearman"))
    require(_finite(overlap) and 0 <= overlap <= 0.70, "dot overlap missing or exceeds threshold")
    require(_finite(rho) and abs(rho) <= 0.90, "surface correlation missing or exceeds threshold")
    post_rho = uniqueness.get("max_postplacement_dot_spearman")
    require(_finite(post_rho) and abs(post_rho) <= 0.90,
            "post-placement correlation missing or exceeds threshold")
    require(uniqueness.get("all_registry_entries_checked") is True,
            "complete pre- and post-placement registry screen not proven")
    require(uniqueness.get("scope_current_and_complete") is True,
            "current, complete comparison scope not proven")
    validator = card.get("validator")
    validator = validator if isinstance(validator, dict) else {}
    checks = validator.get("zeros_checks", {})
    required_checks = ("grid_matches_template", "single_band_float32", "inside_footprint_all_finite",
                       "inside_footprint_in_0_1", "no_infinities_anywhere",
                       "outside_footprint_is_zero_and_finite", "strict_whole_array_range")
    require(validator.get("zeros_hard_pass") is True and isinstance(checks, dict)
            and all(isinstance(checks.get(name), dict) and checks[name].get("pass") is True
                    and checks[name].get("hard", True) is True for name in required_checks)
            and all(isinstance(c, dict) and isinstance(c.get("hard", True), bool)
                    and (c.get("hard", True) is False or c.get("pass") is True)
                    for c in checks.values()),
            "all-finite validator missing required checks or failed")
    note = card.get("note_max_140_chars")
    require(isinstance(note, str) and 0 < len(note) <= 140, "missing or overlong submission note")
    raster = card.get("raster")
    raster = raster if isinstance(raster, dict) else {}
    name = raster.get("primary_allfinite", "")
    directory = raster.get("directory", "docs/downloads/research")
    if not isinstance(name, str) or not isinstance(directory, str):
        name, directory = "", "docs/downloads/research"
    path = (root / directory / name).resolve()
    safe = path.is_relative_to(root.resolve()) and path.suffix.lower() == ".tif"
    require(safe and path.is_file(), "raster missing or outside repository")
    actual_hash = None
    if safe and path.is_file():
        with path.open("rb") as stream:
            actual_hash = hashlib.file_digest(stream, "sha256").hexdigest()
        require(actual_hash == raster.get("sha256"), "raster hash differs from evidence")
    # Owner reports are not organizer receipts, but are sufficient to block a possible
    # duplicate upload. Match both the content id and the actual bytes; never upgrade
    # an owner-reported value to an organizer-confirmed score.
    try:
        ledger = json.loads((root / "registry/submitted_rasters.json").read_text())
        entries = ledger["entries"]
        if not isinstance(entries, list) or not entries:
            raise ValueError("empty submitted-raster ledger")
        content_id = raster.get("content_id", "")
        for item in entries:
            if not isinstance(item, dict) or not item.get("sha256") or not item.get("content_id"):
                raise ValueError("malformed submitted-raster ledger entry")
            already = ((actual_hash is not None and actual_hash == item["sha256"])
                       or (content_id and content_id == item["content_id"])
                       or item["content_id"] in name)
            require(not already, "raster reported already submitted")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        require(False, "submitted-raster ledger missing or malformed")
    return {"ok_to_publish_as_submission": not reasons, "reasons": reasons,
            "actual_sha256": actual_hash,
            "slot_authorized": False,
            "scope": "Recorded evidence audit only; selector and current-registry recheck still required"}


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
