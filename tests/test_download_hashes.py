"""Historic fallback hashes must actually be checked, not merely mentioned."""
import hashlib
import json

import pytest
from scripts.verify_downloads import fallback_hash_matches


@pytest.mark.parametrize("key", ["variants", "geotiff"])
def test_fallback_hash_and_filename_are_verified(tmp_path, key):
    raster = tmp_path / "candidate-allfinite.tif"
    raster.write_bytes(b"valid original")
    row = {"nan": "candidate-nan.tif"}
    checks = tmp_path / "checks-candidate-nan.json"
    variant = {"file": raster.name, "sha256": hashlib.sha256(raster.read_bytes()).hexdigest()}
    checks.write_text(json.dumps({key: {"allfinite": variant}}))
    assert fallback_hash_matches(raster, row, tmp_path)
    raster.write_bytes(b"altered")
    assert not fallback_hash_matches(raster, row, tmp_path)
    raster.write_bytes(b"valid original")
    variant["file"] = "different.tif"
    checks.write_text(json.dumps({key: {"allfinite": variant}}))
    assert not fallback_hash_matches(raster, row, tmp_path)
    checks.write_text("{")
    assert not fallback_hash_matches(raster, row, tmp_path)
    checks.unlink()
    assert not fallback_hash_matches(raster, row, tmp_path)


def test_input_pin_failures_detects_missing_and_changed_inputs(tmp_path):
    from scripts.verify_downloads import input_pin_failures

    mapping = {
        "data/bridge/sample_submission.tif": "sample_submission.tif",
        "data/bridge/labels.tif": "labels.tif",
        "docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif": "dotted_h19_5_d1_5_nan.tif",
        "inputs/gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif": "h19_5_nan.tif",
    }
    pin = hashlib.sha256(b"pinned").hexdigest()
    manifest = {"files": [{"path": source, "sha256": pin} for source in mapping]}
    for name in mapping.values():
        (tmp_path / name).write_bytes(b"pinned")
    assert input_pin_failures(tmp_path, manifest) == []
    (tmp_path / "labels.tif").write_bytes(b"changed")
    (tmp_path / "h19_5_nan.tif").unlink()
    assert set(input_pin_failures(tmp_path, manifest)) == {"labels.tif", "h19_5_nan.tif"}
