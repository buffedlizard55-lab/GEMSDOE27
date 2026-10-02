"""Shared test guards.

The 16 hash-pinned competition inputs live in `data_cache/`, which `.gitignore` excludes by design
(they are several hundred MB and are restored with `scripts/restore_data.py`). CI checks out the repo
without them, and `GITHUB_TOKEN` cannot read the *sibling* repositories they come from, so any test
that opens a raster must be skipped there rather than fail.

This was a real, pre-existing defect: `tests/test_vector_and_oof.py::test_vector_attribution_and_evidence_files`
failed on the base commit `ce80ead` in CI for exactly this reason. Tests that need rasters are now
marked `requires_rasters` and skipped with the missing file names in the reason, so a red suite always
means a real failure. Locally, after `scripts/restore_data.py`, every test runs.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("GEMS_DATA_DIR", str(ROOT / "data_cache")))

REQUIRED_INPUTS = (
    "sample_submission.tif",
    "labels.tif",
    "h19_5_nan.tif",
    "dotted_h19_5_d1_5_nan.tif",
    "qfaults_v2_in_footprint.json",
)

MISSING = [n for n in REQUIRED_INPUTS if not (DATA / n).exists()]


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "requires_rasters: needs the hash-pinned data_cache inputs (skipped when they are absent)",
    )


def pytest_collection_modifyitems(config, items):
    if not MISSING:
        return
    reason = ("hash-pinned competition inputs are not restored in this environment (missing: "
              + ", ".join(MISSING) + "). Run `python scripts/restore_data.py` to execute these checks; "
              "CI builds the site and runs the pure-Python tests from JSON only.")
    skip = pytest.mark.skip(reason=reason)
    for item in items:
        if "requires_rasters" in item.keywords:
            item.add_marker(skip)
