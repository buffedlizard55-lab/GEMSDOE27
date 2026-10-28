#!/usr/bin/env python3
"""Fetch the pinned peer rasters used by the parallel-run duplicate screen.

Inputs are GitHub owner-repository mirrors, not organizer submission receipts. Each immutable
repo/commit/path is read from registry/parallel_submission_registry.json, fetched from a codeload
archive (rather than repeatedly querying the API), and re-opened against the local template grid.
Downloads live only in GEMS_DATA_DIR, which is git-ignored. The cache manifest records the content
SHA-256 checked against the independently recorded registry pin. A pre-existing cache
is never silently trusted, even if a manifest from an earlier run exists.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tarfile
import tempfile
from collections import defaultdict
from pathlib import Path

import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems27 import paths  # noqa: E402

REGISTRY = ROOT / "registry" / "parallel_submission_registry.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_missing_from_archive(items: list[dict], cache: Path) -> None:
    """Fetch each repository once through allowed codeload, extracting only missing TIFFs."""
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for item in items:
        destination = cache / f"{item['id']}{Path(item['path']).suffix.lower()}"
        if not destination.exists():
            grouped[(item["repo"], item["commit"])].append(item)
    for (repo, commit), missing in grouped.items():
        name = repo.rsplit("/", 1)[-1]
        archive_url = f"https://codeload.github.com/{repo}/tar.gz/{commit}"
        with tempfile.TemporaryDirectory(prefix="gems27-parallel-") as tmp:
            archive = Path(tmp) / "source.tar.gz"
            print(f"fetch archive {repo}@{commit[:12]} ({len(missing)} target raster(s))")
            subprocess.run(
                ["curl", "--fail", "--location", "--silent", "--show-error", archive_url, "--output", str(archive)],
                check=True,
            )
            prefix = f"{name}-{commit}/"
            with tarfile.open(archive, "r:gz") as tar:
                members = {member.name: member for member in tar.getmembers()}
                for item in missing:
                    member_name = prefix + item["path"]
                    member = members.get(member_name)
                    if member is None or not member.isfile():
                        raise SystemExit(f"Pinned path missing from archive: {repo}@{commit}:{item['path']}")
                    destination = cache / f"{item['id']}{Path(item['path']).suffix.lower()}"
                    temporary = destination.with_suffix(destination.suffix + ".part")
                    stream = tar.extractfile(member)
                    if stream is None:
                        raise SystemExit(f"Cannot extract registry raster {item['id']}")
                    with stream, temporary.open("wb") as output:
                        while chunk := stream.read(1 << 20):
                            output.write(chunk)
                    temporary.replace(destination)


def main() -> int:
    registry = json.loads(REGISTRY.read_text())
    entries = registry.get("entries")
    if not isinstance(entries, list) or not entries:
        raise SystemExit("Peer registry is empty or malformed")
    ids = set()
    for item in entries:
        if (not isinstance(item, dict) or not isinstance(item.get("id"), str)
                or not re.fullmatch(r"[a-zA-Z0-9_-]+", item["id"])
                or item["id"] in ids or not isinstance(item.get("sha256"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"])):
            raise SystemExit("Peer registry contains invalid IDs or missing SHA-256 pins")
        ids.add(item["id"])
    cache = paths.DATA / "parallel_registry"
    cache.mkdir(parents=True, exist_ok=True)
    manifest_path = cache / "cache_manifest.json"
    old = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    with rasterio.open(paths.TEMPLATE) as template:
        expected = (template.crs, template.shape, template.transform)
    fetch_missing_from_archive(registry["entries"], cache)
    records = []
    for item in registry["entries"]:
        suffix = Path(item["path"]).suffix.lower()
        destination = cache / f"{item['id']}{suffix}"
        if sha256(destination) != item["sha256"]:
            raise SystemExit(f"Peer registry SHA-256 mismatch: {item['id']}; remove the bad cache file and fetch again")
        with rasterio.open(destination) as dataset:
            grid_ok = (dataset.crs, dataset.shape, dataset.transform) == expected and dataset.count == 1
            details = {
                "id": item["id"],
                "repo": item["repo"],
                "commit": item["commit"],
                "path": item["path"],
                "local": str(destination.relative_to(paths.DATA)),
                "manual_review_url": f"https://github.com/{item['repo']}/blob/{item['commit']}/{item['path']}",
                "bytes": destination.stat().st_size,
                "sha256": sha256(destination),
                "grid_matches_template": grid_ok,
                "dtype": dataset.dtypes[0],
                "count": dataset.count,
            }
        if not grid_ok:
            raise SystemExit(f"Peer registry raster grid mismatch: {item['id']}")
        records.append(details)
        print(f"OK {item['id']} {details['sha256'][:12]} {details['bytes']:,} B")
    result = {
        "registry_sha256": sha256(REGISTRY),
        "template_sha256": sha256(paths.TEMPLATE),
        "entries": records,
    }
    if old and old.get("registry_sha256") != result["registry_sha256"]:
        print("Registry content changed; cache was refreshed against the new pinned entries.")
    manifest_path.write_text(json.dumps(result, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
