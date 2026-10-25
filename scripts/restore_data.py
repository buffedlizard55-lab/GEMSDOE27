#!/usr/bin/env python3
"""Restore hash-pinned inputs into the (git-ignored) data cache.

The sandbox can reach github.com, codeload.github.com, and api.github.com. Under parallel runs,
`api.github.com` REST calls (`gh api repos/.../contents/...`) can hit the 5,000/hr user-token rate
limit (HTTP 403). Therefore, this script streams pinned commit tarballs directly from
`https://codeload.github.com/<repo>/tar.gz/<commit>` (zero REST API quota usage) and falls back to
`gh api` only if needed. Every extracted file and assembled artifact is verified against the exact
byte count and SHA-256 in `data/manifest.json`. Nothing here touches drivendata.org.

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
import tarfile
import time
import urllib.request
from collections import defaultdict
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


def _gh_token() -> str | None:
    try:
        r = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True)
        tok = r.stdout.strip()
        return tok or None
    except Exception:  # noqa: BLE001
        return None


def codeload_extract(
    repo: str,
    ref: str,
    wanted: dict[str, list[tuple[Path, int | None]]],
    retries: int = 3,
) -> set[str]:
    """Stream `codeload.github.com/<repo>/tar.gz/<ref>` once and extract requested repo paths.

    `wanted` maps repo-relative path -> list of `(dest_path, expected_bytes)`.
    Returns the set of repo-relative paths successfully extracted across all destinations.
    """
    if not wanted:
        return set()
    url = f"https://codeload.github.com/{repo}/tar.gz/{ref}"
    token = _gh_token()
    remaining = set(wanted.keys())
    extracted: set[str] = set()

    for attempt in range(1, retries + 1):
        if not remaining:
            break
        headers = {"User-Agent": "GEMSDOE27-restore/2.0"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                with tarfile.open(fileobj=resp, mode="r|gz") as tf:
                    for member in tf:
                        if not member.isfile():
                            continue
                        parts = member.name.split("/", 1)
                        if len(parts) != 2:
                            continue
                        rel = parts[1]
                        if rel not in remaining:
                            continue
                        fobj = tf.extractfile(member)
                        if fobj is None:
                            continue
                        targets = wanted[rel]
                        first_dest, first_want = targets[0]
                        first_dest.parent.mkdir(parents=True, exist_ok=True)
                        tmp = first_dest.with_suffix(first_dest.suffix + ".part")
                        if tmp.exists():
                            tmp.unlink()
                        with open(tmp, "wb") as out:
                            shutil.copyfileobj(fobj, out)
                        got = tmp.stat().st_size
                        if first_want is not None and got != first_want:
                            tmp.unlink()
                            raise IOError(f"truncated codeload member {rel}: {got} B != {first_want} B")
                        tmp.replace(first_dest)
                        for extra_dest, extra_want in targets[1:]:
                            extra_dest.parent.mkdir(parents=True, exist_ok=True)
                            extra_tmp = extra_dest.with_suffix(extra_dest.suffix + ".part")
                            shutil.copy2(first_dest, extra_tmp)
                            if extra_want is not None and extra_tmp.stat().st_size != extra_want:
                                extra_tmp.unlink()
                                raise IOError(f"copy size mismatch for {extra_dest}")
                            extra_tmp.replace(extra_dest)
                        remaining.remove(rel)
                        extracted.add(rel)
                        if not remaining:
                            break
        except Exception as e:  # noqa: BLE001
            print(f"  codeload attempt {attempt}/{retries} for {repo}@{ref[:8]} interrupted: {e}", flush=True)
            time.sleep(2 * attempt)
    return extracted


def gh_size(repo: str, path: str, ref: str) -> int:
    """Byte size GitHub reports for a blob, used to detect truncated downloads."""
    r = subprocess.run(["gh", "api", f"repos/{repo}/contents/{path}?ref={ref}", "--jq", ".size"],
                       capture_output=True, text=True, check=True)
    return int(r.stdout.strip())


def gh_raw(repo: str, path: str, ref: str, dest: Path, want_bytes: int | None = None, retries: int = 3) -> None:
    """Fallback single-blob fetch via `gh api`, verifying byte size and cleaning stale `.part` files."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    if tmp.exists():
        tmp.unlink()
    want = want_bytes if want_bytes is not None else gh_size(repo, path, ref)
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
                raise IOError(f"truncated download: {got} B, expected {want} B")
            tmp.replace(dest)
            return
        except Exception as e:  # noqa: BLE001 - retry any fetch failure
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

    if not args.verify:
        by_source: dict[tuple[str, str], dict[str, list[tuple[Path, int | None]]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for f in man["files"]:
            name = LOCAL_NAMES.get(f["path"], Path(f["path"]).name)
            dest = paths.DATA / name
            if not dest.exists():
                s = src[f["source"]]
                by_source[(s["repo"], s["commit"])][f["path"]].append((dest, f.get("bytes")))
        for a in man["assembled"]:
            dest = paths.DATA / a["assembled_name"]
            if not dest.exists():
                s = src[a["source"]]
                for p in a["parts"]:
                    pd = paths.DATA / "parts" / p
                    if not pd.exists():
                        by_source[(s["repo"], s["commit"])][f"{a['dir']}/{p}"].append((pd, None))

        for (repo, commit), wanted in by_source.items():
            print(f"stream {repo}@{commit[:8]} ({len(wanted)} missing paths via codeload)", flush=True)
            done = codeload_extract(repo, commit, wanted)
            for rel, targets in wanted.items():
                if rel in done:
                    continue
                for dest, want_b in targets:
                    if not dest.exists():
                        print(f"fallback gh api {repo}@{commit[:8]}:{rel} -> {dest.name}", flush=True)
                        gh_raw(repo, rel, commit, dest, want_bytes=want_b)

    bad = 0
    for f in man["files"]:
        name = LOCAL_NAMES.get(f["path"], Path(f["path"]).name)
        dest = paths.DATA / name
        ok = dest.exists() and sha256(dest) == f["sha256"]
        print(f"{'OK ' if ok else 'BAD'} {dest.name} {f['sha256'][:12]}")
        if not ok and dest.exists() and not args.verify:
            print(f"  removing corrupt {dest.name} so the next run refetches it")
            dest.unlink()
        bad += not ok
    for a in man["assembled"]:
        dest = paths.DATA / a["assembled_name"]
        if not dest.exists() and not args.verify:
            parts = [paths.DATA / "parts" / p for p in a["parts"]]
            if all(pd.exists() for pd in parts):
                with open(dest, "wb") as out:
                    for pd in parts:
                        with open(pd, "rb") as fh:
                            shutil.copyfileobj(fh, out)
        ok = dest.exists() and sha256(dest) == a["sha256"]
        print(f"{'OK ' if ok else 'BAD'} {dest.name} {a['sha256'][:12]}")
        if not ok and not args.verify:
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
