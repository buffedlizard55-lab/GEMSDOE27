from __future__ import annotations

import json
from pathlib import Path

from scripts.prepare_data import LIDAR_BANDS, LIDAR_EXPECTED_DESCRIPTIONS

ROOT = Path(__file__).resolve().parents[1]


def test_lidar_feature_names_follow_verified_raster_band_order() -> None:
    assert LIDAR_BANDS == [
        (1, "ex_max"),
        (2, "ex_mean"),
        (3, "step_max"),
        (4, "lapneg_max"),
        (5, "lappos_max"),
        (6, "downface_max"),
        (7, "upface_max"),
        (8, "cross_max"),
        (9, "relief"),
        (10, "coh100"),
    ]
    assert LIDAR_EXPECTED_DESCRIPTIONS == tuple(name for _, name in LIDAR_BANDS) + (
        "strike",
        "valid",
    )


def test_sidecar_metadata_is_hash_pinned_in_data_manifest() -> None:
    manifest = json.loads((ROOT / "data/manifest.json").read_text())
    matches = [
        entry
        for entry in manifest["files"]
        if entry["path"] == "data/external/lidar_scarp_features.json"
    ]
    assert len(matches) == 1
    assert matches[0]["source"] == "sibling24"
    assert (
        matches[0]["sha256"] == "9ef0df6e87598a8b0cd52fe821661e5fdb3a00568c5d9b1c5d61fd6b242dcd41"
    )
