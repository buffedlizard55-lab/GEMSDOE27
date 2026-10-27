import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine

from gems27 import uniqueness

spec = importlib.util.spec_from_file_location(
    "uniqueness_cli", Path(__file__).resolve().parents[1] / "scripts/check_parallel_uniqueness.py"
)
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


def write_raster(path, values, transform=None):
    transform = transform or Affine(100, 0, 0, 0, -100, 2000)
    with rasterio.open(path, "w", driver="GTiff", height=20, width=20, count=1, dtype="float32",
                       crs="EPSG:32611", transform=transform) as dst:
        dst.write(np.asarray(values, dtype=np.float32), 1)


@pytest.fixture
def setup_registry(tmp_path, monkeypatch):
    template = tmp_path / "template.tif"
    ref = tmp_path / "cache" / "ref.tif"
    ref.parent.mkdir()
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir()
    registry = registry_dir / "parallel_submission_registry.json"
    manifest = tmp_path / "cache" / "parallel_registry" / "cache_manifest.json"
    manifest.parent.mkdir()
    template_values = np.zeros((20, 20))
    ref_values = np.zeros((20, 20))
    ref_values[2, 2] = ref_values[3, 3] = 1
    write_raster(template, template_values)
    write_raster(ref, ref_values)
    registry.write_text(json.dumps({"entries": [{"id": "peer"}]}))
    data = {"registry_sha256": uniqueness.sha256_file(registry),
            "template_sha256": uniqueness.sha256_file(template),
            "entries": [{"id": "peer", "local": "ref.tif", "sha256": uniqueness.sha256_file(ref)}]}
    manifest.write_text(json.dumps(data))
    monkeypatch.setattr(cli.paths, "TEMPLATE", template)
    monkeypatch.setattr(cli.paths, "REGISTRY", registry_dir)
    return tmp_path, template, ref, manifest, data


def invoke(monkeypatch, candidate, manifest, out, *options):
    monkeypatch.setattr(sys, "argv", ["check_parallel_uniqueness.py", str(candidate), "--cache-manifest",
                                     str(manifest), "--out", str(out), *options])
    return cli.main()


def test_cli_detects_dot_duplicate_and_records_report(setup_registry, monkeypatch):
    root, _, ref, manifest, _ = setup_registry
    out = root / "report.json"
    assert invoke(monkeypatch, ref, manifest, out) == 2
    report = json.loads(out.read_text())
    assert report["duplicates"] == ["peer"]
    assert report["entries"][0]["candidate_dot_fraction_within_3px"] == 1.0
    assert not report["pass"]


def test_cli_checks_preplacement_surface_and_stops_on_hash_tampering(setup_registry, monkeypatch):
    root, _, ref, manifest, _ = setup_registry
    candidate = root / "surface.tif"
    write_raster(candidate, np.arange(400).reshape(20, 20) / 399)
    out = root / "surface.json"
    assert invoke(monkeypatch, candidate, manifest, out, "--surface-only") == 0
    assert json.loads(out.read_text())["surface_only"] is True
    with ref.open("ab") as f:
        f.write(b"tampered")
    with pytest.raises(ValueError, match="hash mismatch"):
        invoke(monkeypatch, candidate, manifest, out, "--surface-only")


def test_cli_rejects_missing_hash_manifest_and_shifted_reference(setup_registry, monkeypatch):
    root, _, ref, manifest, data = setup_registry
    candidate = root / "surface.tif"
    write_raster(candidate, np.arange(400).reshape(20, 20) / 399)
    data["entries"][0]["sha256"] = None
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="invalid reference hash"):
        invoke(monkeypatch, candidate, manifest, root / "bad.json", "--surface-only")
    a = np.zeros((20, 20))
    a[1, 1] = 1
    write_raster(ref, a, Affine(100, 0, 100, 0, -100, 2000))
    data["entries"][0]["sha256"] = uniqueness.sha256_file(ref)
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="reference grid mismatch"):
        invoke(monkeypatch, candidate, manifest, root / "bad.json", "--surface-only")


def test_cli_rejects_undefined_and_invalid_candidate(setup_registry, monkeypatch):
    root, _, _, manifest, _ = setup_registry
    candidate = root / "constant.tif"
    write_raster(candidate, np.zeros((20, 20)))
    with pytest.raises(ValueError, match="constant"):
        invoke(monkeypatch, candidate, manifest, root / "bad.json", "--surface-only")
    a = np.zeros((20, 20))
    a[1, 1] = np.nan
    write_raster(candidate, a)
    with pytest.raises(ValueError, match="non-finite"):
        invoke(monkeypatch, candidate, manifest, root / "bad.json", "--surface-only")
