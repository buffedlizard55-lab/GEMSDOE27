#!/usr/bin/env python3
"""Inventory and hash-check current download TIFFs from nine focus repositories.

Uses only GitHub/codeload, never DrivenData. Files stay in the git-ignored data cache;
small provenance/validation records are persisted. A partial/invalid inventory cannot
establish global uniqueness. Each recovered file must match GitHub's Git blob SHA-1.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
import restore_data  # noqa: E402
from gems27 import paths, uniqueness  # noqa: E402

SITES = (24, 25, 27, 28, 30, 31, 32, 33, 36)
CACHE = paths.DATA / "focus_current"
OUT = paths.EVIDENCE / "focus_inventory_20261027.json"


def gh_json(endpoint: str) -> dict:
    return json.loads(subprocess.run(["gh", "api", endpoint], check=True, capture_output=True, text=True).stdout)


def blob_sha1(p: Path) -> str:
    h = hashlib.sha1(f"blob {p.stat().st_size}\0".encode(), usedforsecurity=False)
    with p.open("rb") as f:
        while data := f.read(1024 * 1024):
            h.update(data)
    return h.hexdigest()


def save_report(report: dict) -> None:
    temporary = OUT.with_suffix(".json.part")
    temporary.write_text(json.dumps(report, indent=2) + "\n")
    temporary.replace(OUT)


def main() -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
    with rasterio.open(paths.TEMPLATE) as template:
        foot = np.isfinite(template.read(1))
        expected = (template.crs, template.shape, template.transform, 1)
    report = {"purpose": "GitHub head snapshot; not organizer receipts or global uniqueness",
              "snapshot_started_utc": datetime.now(timezone.utc).isoformat(),
              "template_sha256": uniqueness.sha256_file(paths.TEMPLATE), "sites": [], "complete": False}
    for n in SITES:
        repo = f"buffedlizard55-lab/GEMSDOE{n}"
        cached = paths.DATA / f"tree{n}.json"
        # A cached tree is reusable only if GitHub still reports the same head.
        head = gh_json(f"repos/{repo}/commits/main")["sha"]
        tree = json.loads(cached.read_text()) if cached.exists() else {}
        if (tree.get("repo") != repo or tree.get("head") != head or tree.get("truncated") is not False
                or not isinstance(tree.get("tifs"), list)):
            raw = gh_json(f"repos/{repo}/git/trees/{head}?recursive=1")
            tree = {"repo": repo, "head": head, "truncated": raw.get("truncated"),
                    "tifs": [v for v in raw["tree"] if v["path"].lower().endswith(".tif")
                             and v["path"].startswith("docs/downloads/")]}
            cached.write_text(json.dumps(tree))
        files = [v for v in tree["tifs"] if v["path"].startswith("docs/downloads/")]
        site = {"site": f"GEMSDOE{n}", "repo": repo, "head": tree["head"],
                "tree_truncated": tree["truncated"], "files": []}
        # Git blob-addressed names cannot accidentally reuse another path after a tree changes.
        wanted = {v["path"]: (CACHE / f"g{n}-{v['sha']}.tif", v.get("size")) for v in files}
        missing = {}
        for v in files:
            dest, size = wanted[v["path"]]
            if not dest.is_file() or (size is not None and dest.stat().st_size != size) or blob_sha1(dest) != v["sha"]:
                missing[v["path"]] = (dest, size)
        if missing:
            restore_data.fetch_group_from_codeload(repo, tree["head"], missing)
        for v in files:
            p = wanted[v["path"]][0]
            row = {"path": v["path"], "git_blob_sha1": v["sha"], "size": v.get("size"),
                   "cache": str(p.relative_to(paths.DATA)), "sha256": None,
                   "blob_verified": False, "binary_grid_valid": False, "error": None}
            try:
                if not p.is_file() or (v.get("size") is not None and p.stat().st_size != v["size"]):
                    raise ValueError("missing or truncated TIFF")
                row["blob_verified"] = blob_sha1(p) == v["sha"]
                if not row["blob_verified"]:
                    raise ValueError("Git blob hash mismatch")
                row["sha256"] = uniqueness.sha256_file(p)
                with rasterio.open(p) as ds:
                    if (ds.crs, ds.shape, ds.transform, ds.count) != expected:
                        raise ValueError("not a single-band template-grid TIFF")
                    a = ds.read(1)[foot]
                if not np.isfinite(a).all() or np.any((a != 0) & (a != 1)):
                    raise ValueError("not a finite binary field within footprint")
                if not (a == 1).any() or (a == 1).all():
                    raise ValueError("constant field; rank correlation undefined")
                row["binary_grid_valid"] = True
            except Exception as exc:  # inventory continues, but completeness fails closed
                row["error"] = f"{type(exc).__name__}: {exc}"
            site["files"].append(row)
        report["sites"].append(site)
        print(f"{repo}@{tree['head'][:12]}: {len(files)} files, "
              f"{sum(x['binary_grid_valid'] for x in site['files'])} valid", flush=True)
        save_report(report)
    report["complete"] = all(s["tree_truncated"] is False and s["files"] and
                             all(r["blob_verified"] and r["binary_grid_valid"] for r in s["files"])
                             for s in report["sites"])
    save_report(report)
    print(f"inventory complete: {report['complete']}", flush=True)
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
