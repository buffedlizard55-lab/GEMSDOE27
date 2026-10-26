#!/usr/bin/env python3
"""Restore hash-pinned inputs into the (git-ignored) data cache.

The sandbox this project was built in can reach only github.com and codeload.github.com, so inputs
are pulled from the owner's sibling repositories at pinned commits and verified against SHA-256
values in data/manifest.json. Nothing here touches drivendata.org.

Template fix (2026-10-26, Protocol §2): parallel sessions sharing one GitHub user token exhausted
the 5,100 req/hr REST `contents/` API quota (`HTTP 403 API rate limit exceeded`) when fetching 21
blobs one by one via `gh api`. `restore_data.py` now streams each pinned `(repo, commit)` archive
once from `codeload.github.com` (same pattern as `scripts/fetch_parallel_registry.py`, 0 REST API
calls), verifies byte counts where declared, falls back to `gh api` only if archive extraction
fails, and verifies every output file's exact SHA-256 against `data/manifest.json`.

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
    r = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=False)
    tok = r.stdout.strip()
    return tok if r.returncode == 0 and tok else None


def fetch_group_from_codeload(
    repo: str,
    ref: str,
    wanted: dict[str, tuple[Path, int | None]],
    retries: int = 3,
) -> set[str]:
    """Stream one `codeload.github.com` tar.gz archive and extract all `wanted` repo-relative paths.

    `wanted` maps `repo_rel_path -> (dest_path, expected_bytes_or_None)`.
    Never writes a partial file to `dest_path`: extracts to `.part`, checks expected size, then
    atomically renames. Returns the set of `repo_rel_path` keys extracted cleanly.
    """
    if not wanted:
        return set()
    repo_name = repo.rsplit("/", 1)[-1]
    prefix = f"{repo_name}-{ref}/"
    url = f"https://codeload.github.com/{repo}/tar.gz/{ref}"
    token = _gh_token()
    extracted: set[str] = set()

    for attempt in range(1, retries + 1):
        remaining = {k: v for k, v in wanted.items() if k not in extracted}
        if not remaining:
            break
        for dest, _ in remaining.values():
            dest.parent.mkdir(parents=True, exist_ok=True)
            part = dest.with_suffix(dest.suffix + ".part")
            if part.exists():
                part.unlink()
        print(
            f"stream archive {repo}@{ref[:8]} ({len(remaining)} file(s), attempt {attempt}/{retries})",
            flush=True,
        )
        cmd = ["curl", "--fail", "--location", "--silent", "--show-error"]
        if token:
            cmd.extend(["-H", f"Authorization: Bearer {token}"])
        cmd.append(url)
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        try:
            assert proc.stdout is not None
            with tarfile.open(fileobj=proc.stdout, mode="r|gz") as tar:
                for member in tar:
                    if not member.isfile() or not member.name.startswith(prefix):
                        continue
                    rel = member.name[len(prefix) :]
                    if rel not in remaining:
                        continue
                    dest, want_bytes = remaining[rel]
                    tmp = dest.with_suffix(dest.suffix + ".part")
                    stream = tar.extractfile(member)
                    if stream is None:
                        continue
                    with stream, open(tmp, "wb") as out:
                        while chunk := stream.read(1 << 20):
                            out.write(chunk)
                    got = tmp.stat().st_size
                    if want_bytes is not None and got != want_bytes:
                        tmp.unlink(missing_ok=True)
                        raise OSError(f"truncated {rel}: {got} B != pinned {want_bytes} B")
                    tmp.replace(dest)
                    extracted.add(rel)
                    if len(extracted) == len(wanted):
                        # All needed blobs extracted; close stream early without reading trailing archive bytes.
                        proc.terminate()
                        break
            rc = proc.wait(timeout=15)
            # rc < 0 (SIGTERM after early stop) is expected once all targets are extracted.
            if len(extracted) == len(wanted):
                return extracted
            if rc != 0:
                raise RuntimeError(f"curl exited with {rc}")
        except Exception as exc:  # noqa: BLE001
            proc.kill()
            proc.wait()
            for dest, _ in wanted.items():
                if isinstance(dest, tuple):
                    continue
            for rel_key, (dest, _) in remaining.items():
                if rel_key not in extracted:
                    dest.with_suffix(dest.suffix + ".part").unlink(missing_ok=True)
            print(f"  codeload attempt {attempt}/{retries} incomplete for {repo}@{ref[:8]}: {exc}", flush=True)
            time.sleep(2 * attempt)
    return extracted


def gh_size(repo: str, path: str, ref: str) -> int:
    """Byte size GitHub reports for a blob, used to detect truncated downloads."""
    r = subprocess.run(
        ["gh", "api", f"repos/{repo}/contents/{path}?ref={ref}", "--jq", ".size"],
        capture_output=True,
        text=True,
        check=True,
    )
    return int(r.stdout.strip())


def gh_raw(
    repo: str,
    path: str,
    ref: str,
    dest: Path,
    expected_bytes: int | None = None,
    retries: int = 3,
) -> None:
    """Fallback single-blob fetch via `gh api`, verifying byte size and cleaning stale `.part`."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    if tmp.exists():
        tmp.unlink()
    want = expected_bytes if expected_bytes is not None else gh_size(repo, path, ref)
    last: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with open(tmp, "wb") as out:
                subprocess.run(
                    [
                        "gh",
                        "api",
                        f"repos/{repo}/contents/{path}?ref={ref}",
                        "-H",
                        "Accept: application/vnd.github.raw",
                    ],
                    stdout=out,
                    check=True,
                )
            got = tmp.stat().st_size
            if got != want:
                raise OSError(f"truncated download: {got} B, expected {want} B")
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
        grouped: dict[tuple[str, str], dict[str, tuple[Path, int | None]]] = defaultdict(dict)
        for f in man["files"]:
            name = LOCAL_NAMES.get(f["path"], Path(f["path"]).name)
            dest = paths.DATA / name
            if not dest.exists():
                s = src[f["source"]]
                grouped[(s["repo"], s["commit"])][f["path"]] = (dest, f.get("bytes"))
        for a in man["assembled"]:
            dest = paths.DATA / a["assembled_name"]
            if not dest.exists():
                s = src[a["source"]]
                for p in a["parts"]:
                    pd = paths.DATA / "parts" / p
                    if not pd.exists():
                        grouped[(s["repo"], s["commit"])][f"{a['dir']}/{p}"] = (pd, None)

        for (repo, commit), wanted in grouped.items():
            got = fetch_group_from_codeload(repo, commit, wanted)
            for rel_path, (dest, want_bytes) in wanted.items():
                if rel_path not in got and not dest.exists():
                    print(f"fallback gh_raw {repo}@{commit[:8]}:{rel_path} -> {dest.name}", flush=True)
                    gh_raw(repo, rel_path, commit, dest, expected_bytes=want_bytes)

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
                tmp = dest.with_suffix(dest.suffix + ".part")
                tmp.unlink(missing_ok=True)
                with open(tmp, "wb") as out:
                    for pd in parts:
                        with open(pd, "rb") as fh:
                            shutil.copyfileobj(fh, out)
                tmp.replace(dest)
        ok = dest.exists() and sha256(dest) == a["sha256"]
        print(f"{'OK ' if ok else 'BAD'} {dest.name} {a['sha256'][:12]}")
        if ok and not args.verify:
            # Free ~419 MB of duplicate part files once the assembled file passes SHA-256.
            for p in a["parts"]:
                (paths.DATA / "parts" / p).unlink(missing_ok=True)
        elif not ok and not args.verify:
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
