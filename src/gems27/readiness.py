"""Fail-closed publication policy; format validity alone never authorizes a slot.

This checks recorded evidence and binds it to bytes. It does not rerun an evaluator,
prove scientific novelty, or replace the selector / current registry comparison.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path


def publication_decision(card: dict, root: Path) -> dict:
    reasons = []

    def require(condition, reason):
        if not condition:
            reasons.append(reason)

    require(card.get("ok_to_submit") is True, "run card does not authorize submission")
    require(card.get("verdict") == "promote", "verdict is not promote")
    hold = card.get("holdout", {})
    require(hold.get("label") == "HOLDOUT-DTI", "missing HOLDOUT-DTI label")
    require(bool(hold.get("evaluator")), "missing evaluator version")
    n = hold.get("n_withheld_positives_total")
    require(isinstance(n, int) and not isinstance(n, bool) and n > 0,
            "missing withheld positive count")
    require(hold.get("gate_efficacy_pass") is True, "efficacy gate not explicitly passed")
    paired = hold.get("paired_D_minus_B", hold.get("paired_A_minus_B", {}))
    ci = paired.get("ci95", [])
    require(isinstance(ci, list) and len(ci) == 2 and all(_finite(x) for x in ci)
            and 0 < ci[0] <= ci[1], "paired improvement CI missing or does not exclude zero")
    auc = hold.get("canary_max_auc")
    require(_finite(auc) and 0.5 <= auc <= 0.90, "canary missing or leakage threshold exceeded")
    uniqueness = card.get("uniqueness_vs_registry", {})
    require(uniqueness.get("pass") is True, "uniqueness gate not passed")
    overlap = uniqueness.get("max_dot_overlap_within_3px_euclidean")
    rho = uniqueness.get("max_surface_spearman_armD",
                         uniqueness.get("max_surface_spearman"))
    require(_finite(overlap) and 0 <= overlap <= 0.70, "dot overlap missing or exceeds threshold")
    require(_finite(rho) and -1 <= rho <= 0.90, "surface correlation missing or exceeds threshold")
    validator = card.get("validator", {})
    checks = validator.get("zeros_checks", {})
    require(validator.get("zeros_hard_pass") is True and bool(checks)
            and all(c.get("pass") is True for c in checks.values() if c.get("hard", True)),
            "all-finite validator not passed")
    note = card.get("note_max_140_chars")
    require(isinstance(note, str) and 0 < len(note) <= 140, "missing or overlong submission note")
    raster = card.get("raster", {})
    name = raster.get("primary_allfinite", "")
    directory = raster.get("directory", "docs/downloads/research")
    path = (root / directory / name).resolve()
    safe = path.is_relative_to(root.resolve()) and path.suffix.lower() == ".tif"
    require(safe and path.is_file(), "raster missing or outside repository")
    actual_hash = None
    if safe and path.is_file():
        with path.open("rb") as stream:
            actual_hash = hashlib.file_digest(stream, "sha256").hexdigest()
        require(actual_hash == raster.get("sha256"), "raster hash differs from evidence")
    return {"ok_to_publish_as_submission": not reasons, "reasons": reasons,
            "actual_sha256": actual_hash,
            "scope": "Recorded evidence audit only; selector and current-registry recheck still required"}


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
