#!/usr/bin/env python3
"""Restore hash-pinned inputs into the (git-ignored) data cache.

The sandbox this project was built in can reach only github.com, so inputs are pulled from the
owner's sibling repositories at pinned commits with the GitHub CLI (`gh api`, raw media type) and
verified against SHA-256 values in data/manifest.json. Nothing here touches drivendata.org.

    python scripts/restore_data.py            # download what is missing, verify everything
    python scripts/restore_data.py --verify   # verify only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import paths  # noqa: E402

LOCAL_NAMES = {
    "data/bridge/labels.tif": "labels.tif",
    "data/bridge/existing_faults.tif": "existing_faults.tif",
    "data/bridge/sample_submission.tif": "sample_submission.tif",
    "inputs/gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif": "h19_5_nan.tif",
    "docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif": "dotted_h19_5_d1_5_nan.tif",
    "docs/downloads/gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif": "dotted_h19_5_d2_8_nan.tif",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def gh_raw(repo: str, path: str, ref: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with open(tmp, "wb") as out:
        subprocess.run(
            ["gh", "api", f"repos/{repo}/contents/{path}?ref={ref}",
             "-H", "Accept: application/vnd.github.raw"],
            stdout=out, check=True,
        )
    tmp.replace(dest)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()
    man = json.loads(paths.MANIFEST.read_text())
    src = man["sources"]
    paths.DATA.mkdir(parents=True, exist_ok=True)
    bad = 0
    for f in man["files"]:
        name = LOCAL_NAMES.get(f["path"], Path(f["path"]).name)
        dest = paths.DATA / name
        if not dest.exists() and not args.verify:
            s = src[f["source"]]
            print(f"fetch {s['repo']}@{s['commit'][:8]}:{f['path']} -> {dest.name}")
            gh_raw(s["repo"], f["path"], s["commit"], dest)
        ok = dest.exists() and sha256(dest) == f["sha256"]
        print(f"{'OK ' if ok else 'BAD'} {dest.name} {f['sha256'][:12]}")
        bad += not ok
    for a in man["assembled"]:
        dest = paths.DATA / a["assembled_name"]
        if not dest.exists() and not args.verify:
            s = src[a["source"]]
            parts = []
            for p in a["parts"]:
                pd = paths.DATA / "parts" / p
                if not pd.exists():
                    print(f"fetch part {p}")
                    gh_raw(s["repo"], f"{a['dir']}/{p}", s["commit"], pd)
                parts.append(pd)
            with open(dest, "wb") as out:
                for pd in parts:
                    with open(pd, "rb") as fh:
                        shutil.copyfileobj(fh, out)
        ok = dest.exists() and sha256(dest) == a["sha256"]
        print(f"{'OK ' if ok else 'BAD'} {dest.name} {a['sha256'][:12]}")
        bad += not ok
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
