#!/usr/bin/env python3
"""Recover the owner's *scored* submission rasters, authenticated by SHA-256.

Why this exists
---------------
Every live score the owner has ever reported corresponds to a specific byte-identical raster that
still lives in one of the sibling repositories. `registry/live_scores.json` records
`(label, repo, sha256, owner_reported_public_score)` for those artifacts. This script downloads
candidate GeoTIFFs from the sibling repos through the GitHub API (never drivendata.org), hashes
them, and keeps **only** the files whose SHA-256 matches a registry row. The result is a corpus of
(raster, live score) pairs whose provenance is verified by hash rather than by name -- the input to
`scripts/invert_live_scores.py`.

Matching is by content hash, so a renamed or re-hosted file is still recognised, and a file whose
name merely *looks* right is rejected. Rows that cannot be matched are reported as `unmatched`
rather than guessed.

    python scripts/fetch_scored_corpus.py            # download + match (cached)
    python scripts/fetch_scored_corpus.py --list     # show what would be fetched
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import paths  # noqa: E402

OWNER = "buffedlizard55-lab"
# Directories that hold *submitted* artifacts (not inputs, fixtures or intermediates).
SEARCH_DIRS = ("docs/downloads", "inputs", "inputs/calibration", "data/evidence/runs", "docs/archive", "submissions")
MAX_BYTES = 12_000_000
HEX = re.compile(r"[0-9a-f]{8,40}")


def gh_json(args: list[str]):
    out = subprocess.run(["gh", "api", *args], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def wanted_hashes() -> dict[str, dict]:
    """sha256 -> registry row, merged from this repo and (optionally) the sibling registry."""
    rows: dict[str, dict] = {}
    live = json.loads((paths.REPO / "registry" / "live_scores.json").read_text())
    for a in live.get("artifacts", []):
        sha = a.get("sha256")
        score = a.get("owner_reported_public_score")
        if sha and score is not None:
            rows[sha] = {
                "label": a.get("label"),
                "repo": a.get("repo"),
                "score": score,
                "corroboration": a.get("corroboration"),
                "registry": "GEMSDOE27/registry/live_scores.json",
            }
    extra = paths.DATA / "sibling25_live_scores.json"
    if extra.exists():
        for a in json.loads(extra.read_text()).get("artifacts", []):
            sha = a.get("sha256")
            if sha and a.get("score") is not None and sha not in rows:
                rows[sha] = {
                    "label": a.get("label"),
                    "repo": f"{OWNER}/{a.get('project')}",
                    "score": a["score"],
                    "corroboration": a.get("status"),
                    "registry": "GEMSDOE25/registry/live_scores.json",
                }
    return rows


def candidate_paths(repo: str, tokens: set[str]) -> list[tuple[str, int]]:
    tree = gh_json([f"repos/{repo}/git/trees/HEAD?recursive=1"])["tree"]
    out = []
    for e in tree:
        p = e["path"]
        if not p.endswith(".tif") or e.get("size", 0) > MAX_BYTES:
            continue
        if not any(p.startswith(d + "/") for d in SEARCH_DIRS):
            continue
        name = Path(p).name.lower()
        hits = sum(1 for t in tokens if t in name)
        out.append((p, hits))
    out.sort(key=lambda x: (-x[1], x[0]))
    return out


def tokens_for(label: str) -> set[str]:
    lab = label.lower()
    toks = set(HEX.findall(lab))
    toks |= {w for w in re.split(r"[^a-z0-9]+", lab) if len(w) >= 5}
    return toks


def fetch(repo: str, path: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part")
    with open(tmp, "wb") as out:
        r = subprocess.run(
            ["gh", "api", f"repos/{repo}/contents/{path}?ref=HEAD",
             "-H", "Accept: application/vnd.github.raw"],
            stdout=out, stderr=subprocess.DEVNULL,
        )
    if r.returncode != 0:
        tmp.unlink(missing_ok=True)
        return False
    tmp.replace(dest)
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--max-per-repo", type=int, default=25,
                    help="cap on GeoTIFFs downloaded per repo (token-ranked first)")
    args = ap.parse_args()
    want = wanted_hashes()
    cache = paths.DATA / "scored_corpus"
    state_path = paths.DATA / "scored_corpus_state.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {"checked": {}, "found": {}}

    by_repo: dict[str, list[dict]] = {}
    for sha, row in want.items():
        if row["repo"] and "/" in str(row["repo"]):
            by_repo.setdefault(str(row["repo"]), []).append({"sha256": sha, **row})

    if args.list:
        for repo, rows in sorted(by_repo.items()):
            print(repo, [r["label"] for r in rows])
        return 0

    for repo, rows in sorted(by_repo.items()):
        tokens: set[str] = set()
        for r in rows:
            tokens |= tokens_for(r["label"])
        try:
            cands = candidate_paths(repo, tokens)
        except subprocess.CalledProcessError as exc:
            print(f"SKIP {repo}: tree listing failed ({exc.stderr.strip()[:120]})")
            continue
        # Prefer high-token-match candidates, but keep enough breadth to match by hash.
        ordered = ([p for p, h in cands if h > 0] + [p for p, h in cands if h == 0])[: args.max_per_repo]
        for p in ordered:
            key = f"{repo}:{p}"
            if key in state["checked"]:
                sha = state["checked"][key]
            else:
                dest = cache / repo.split("/")[1] / Path(p).name
                if not dest.exists() and not fetch(repo, p, dest):
                    continue
                sha = sha256(dest)
                state["checked"][key] = sha
            hit = next((r for r in rows if r["sha256"] == sha), None)
            if hit and sha not in state["found"]:
                state["found"][sha] = {**hit, "path": p, "local": str(
                    (cache / repo.split("/")[1] / Path(p).name).relative_to(paths.DATA))}
                print(f"MATCH {hit['score']:<7} {hit['label'][:64]:<64} <- {repo}/{p}")
            if len(state["found"]) >= len(rows) and all(r["sha256"] in state["found"] for r in rows):
                break
        state_path.write_text(json.dumps(state, indent=1))

    missing = [{"sha256": sha, **r} for sha, r in want.items() if sha not in state["found"]]
    out = {
        "note": "Scored submission rasters recovered from sibling repos and authenticated by SHA-256 "
                "against registry/live_scores.json. Scores are owner-reported, not DrivenData receipts.",
        "n_wanted": len(want),
        "n_matched": len(state["found"]),
        "matched": [state["found"][s] for s in sorted(state["found"], key=lambda s: -state["found"][s]["score"])],
        "unmatched": [{"label": m["label"], "repo": m["repo"], "sha256": m["sha256"], "score": m["score"]}
                      for m in missing],
    }
    (paths.REPO / "evidence" / "scored_corpus.json").write_text(json.dumps(out, indent=1))
    print(f"\nmatched {out['n_matched']}/{out['n_wanted']} scored rasters -> evidence/scored_corpus.json")
    for u in out["unmatched"]:
        print(f"  UNMATCHED {u['label']} ({u['repo']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
