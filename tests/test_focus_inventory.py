import importlib.util
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import Affine

spec = importlib.util.spec_from_file_location(
    "focus_inventory", Path(__file__).resolve().parents[1] / "scripts/refresh_focus_inventory.py"
)
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


def test_stale_cached_tree_is_refreshed_and_partial_inventory_fails_closed(tmp_path, monkeypatch):
    template = tmp_path / "template.tif"
    with rasterio.open(template, "w", driver="GTiff", height=4, width=5, count=1, dtype="float32",
                       crs="EPSG:32611", transform=Affine(100, 0, 0, 0, -100, 500)) as dst:
        dst.write(np.zeros((4, 5), np.float32), 1)
    (tmp_path / "tree24.json").write_text(json.dumps({"repo": "buffedlizard55-lab/GEMSDOE24",
                                                       "head": "old", "truncated": False, "tifs": []}))
    monkeypatch.setattr(inventory, "SITES", (24,))
    monkeypatch.setattr(inventory, "CACHE", tmp_path / "focus")
    monkeypatch.setattr(inventory, "OUT", tmp_path / "inventory.json")
    monkeypatch.setattr(inventory.paths, "DATA", tmp_path)
    monkeypatch.setattr(inventory.paths, "TEMPLATE", template)
    calls = []

    def fake_gh(endpoint):
        calls.append(endpoint)
        if endpoint.endswith("commits/main"):
            return {"sha": "new-head"}
        return {"truncated": False, "tree": []}

    monkeypatch.setattr(inventory, "gh_json", fake_gh)
    assert inventory.main() == 2  # zero references is not a complete inventory
    assert calls == ["repos/buffedlizard55-lab/GEMSDOE24/commits/main",
                     "repos/buffedlizard55-lab/GEMSDOE24/git/trees/new-head?recursive=1"]
    report = json.loads((tmp_path / "inventory.json").read_text())
    assert report["sites"][0]["head"] == "new-head" and not report["complete"]
    assert json.loads((tmp_path / "tree24.json").read_text())["head"] == "new-head"
