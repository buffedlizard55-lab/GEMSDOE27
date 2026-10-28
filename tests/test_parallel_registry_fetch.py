import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine

from gems27 import uniqueness

spec = importlib.util.spec_from_file_location(
    "fetch_parallel_registry", Path(__file__).resolve().parents[1] / "scripts/fetch_parallel_registry.py"
)
fetch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetch)


def write_raster(path):
    with rasterio.open(path, "w", driver="GTiff", height=2, width=2, count=1,
                       dtype="float32", crs="EPSG:32611", transform=Affine(100, 0, 0, 0, -100, 200)) as ds:
        ds.write(np.zeros((2, 2), dtype=np.float32), 1)


def test_fetch_rejects_altered_existing_cache_even_when_old_manifest_says_ok(tmp_path, monkeypatch):
    cache = tmp_path / "parallel_registry"
    cache.mkdir()
    template = tmp_path / "template.tif"
    reference = cache / "peer.tif"
    write_raster(template)
    write_raster(reference)
    pin = uniqueness.sha256_file(reference)
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({"entries": [{"id": "peer", "repo": "a/b", "commit": "c",
                                                 "path": "file.tif", "sha256": pin}]}))
    monkeypatch.setattr(fetch, "REGISTRY", registry)
    monkeypatch.setattr(fetch.paths, "DATA", tmp_path)
    monkeypatch.setattr(fetch.paths, "TEMPLATE", template)
    assert fetch.main() == 0
    # Recompute a plausible manifest for altered bytes, as the old script did on rerun.
    with reference.open("ab") as stream:
        stream.write(b"changed")
    with pytest.raises(SystemExit, match="SHA-256 mismatch"):
        fetch.main()
    assert json.loads((cache / "cache_manifest.json").read_text())["entries"][0]["sha256"] == pin


def test_fetch_rejects_missing_pin_before_any_fetch(tmp_path, monkeypatch):
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({"entries": [{"id": "peer"}]}))
    monkeypatch.setattr(fetch, "REGISTRY", registry)
    monkeypatch.setattr(fetch.paths, "DATA", tmp_path)
    with pytest.raises(SystemExit, match="missing SHA-256 pins"):
        fetch.main()
