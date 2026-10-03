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
import time
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


def gh_size(repo: str, path: str, ref: str) -> int:
    """Byte size GitHub reports for a blob, used to detect truncated downloads."""
    r = subprocess.run(["gh", "api", f"repos/{repo}/contents/{path}?ref={ref}", "--jq", ".size"],
                       capture_output=True, text=True, check=True)
    return int(r.stdout.strip())


def gh_raw(repo: str, path: str, ref: str, dest: Path, retries: int = 3) -> None:
    """Fetch one blob, verifying its size. Never leaves a truncated `.part` behind.

    Session 4 irregularity `restore-part-truncation-bug`: a failed `gh api` download used to leave a
    truncated `<name>.part` on disk (transient HTTP/2 INTERNAL_ERROR on the ~94 MB bridge parts). Any
    later glob-based assembly then silently concatenated the truncated part, producing a corrupt
    `training_features.tif` (492,887,617 B, sha256 c0e9b856...) instead of the pinned 418,912,844 B,
    sha256 4371c82e.... The hash check at the end printed BAD but left the corrupt file in place, so
    the next run skipped it (`dest.exists()`). Now: remove any stale `.part` first, retry, verify the
    size against GitHub's own metadata, and on failure remove the partial file so a re-run refetches.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    if tmp.exists():
        tmp.unlink()
    want = gh_size(repo, path, ref)
    last: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with open(tmp, "wb") as out:
                subprocess.run(
                    ["gh", "api", f"repos/{repo}/contents/{path}?ref={ref}",
                     "-H", "Accept: application/vnd.github.raw"],
                    stdout=out, check=True,
                )
            got = tmp.stat().st_size
            if got != want:
                raise IOError(f"truncated download: {got} B, GitHub reports {want} B")
            tmp.replace(dest)
            return
        except Exception as e:                                   # noqa: BLE001 - retry any fetch failure
            last = e
            if tmp.exists():
                tmp.unlink()
            print(f"  attempt {attempt}/{retries} failed for {path}: {e}", flush=True)
            time.sleep(2 * attempt)
    raise RuntimeError(f"could not fetch {repo}@{ref}:{path} after {retries} attempts") from last


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
        if not ok and dest.exists() and not args.verify:
            print(f"  removing corrupt {dest.name} so the next run refetches it")
            dest.unlink()
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
        if not ok and not args.verify:
            # never leave a corrupt assembly (or a suspect part) where the next run would trust it
            if dest.exists():
                print(f"  removing corrupt {dest.name} so the next run reassembles it")
                dest.unlink()
            for pd_ in (paths.DATA / "parts").glob("*"):
                if pd_.is_file():
                    print(f"  removing part {pd_.name} (cannot be trusted after a bad assembly)")
                    pd_.unlink()
        bad += not ok
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
