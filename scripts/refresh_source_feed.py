#!/usr/bin/env python3
"""Refresh the official-source feed WITHOUT touching drivendata.org; never fabricate a score.

DrivenData's Terms of Use (https://www.drivendata.org/termsofuse/) prohibit using "any robot, spider or other
automatic device, process or means to access the Website for any purpose, including monitoring or copying", so
this script refuses any drivendata.org host (hard guard below). Leaderboard and submission pages are listed on
the site as *links for a human to open*; nothing here fetches them, uploads files or reads scores.

What it does (run on a GitHub-hosted runner, because the build sandbox reaches only github.com):
  * for each feed-enabled row in registry/sources.json: HTTP status, Last-Modified, ETag, final URL, total bytes,
    content type, zip magic and a SHA-256 fingerprint of the first 64 KB (`feed_url` overrides `url` when the row
    points at a download); ArcGIS REST layers via ?f=pjson plus a record count; ScienceBase items via their JSON API (provenance.lastUpdated and a
    file-list hash); GitHub repos via the REST API (pushed_at and default-branch head);
  * compare with the previous docs/data/feed.json and flag `changed`;
  * write docs/data/feed.json (current) and docs/data/feed_history.json (changes only, last 200).
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = ("drivendata.org",)
UA = "GEMSDOE27-source-feed/1.0 (+https://github.com/buffedlizard55-lab/GEMSDOE27; official-source change detection)"
TIMEOUT = 25


def guard(url: str) -> None:
    host = (urlparse(url).hostname or "").lower()
    if any(host == h or host.endswith("." + h) for h in FORBIDDEN):
        raise SystemExit(f"refusing to request {host}: automated access is prohibited by its Terms of Use")


def fingerprint(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:16]


def check_http(url: str) -> dict:
    guard(url)
    try:
        r = requests.get(url, headers={"User-Agent": UA, "Range": "bytes=0-65535"}, timeout=TIMEOUT,
                         allow_redirects=True, stream=True)
        body = next(r.iter_content(65536), b"")
        guard(r.url)
        total = r.headers.get("Content-Range", "").split("/")[-1] or r.headers.get("Content-Length")
        return {"ok": r.status_code < 400, "http": r.status_code, "final_url": r.url,
                "last_modified": r.headers.get("Last-Modified"), "etag": r.headers.get("ETag"),
                "content_length": r.headers.get("Content-Range") or r.headers.get("Content-Length"),
                "total_bytes": int(total) if total and total.isdigit() else None,
                "content_type": r.headers.get("Content-Type"), "is_zip": body[:4] == b"PK\x03\x04",
                "fingerprint": fingerprint(body)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": repr(e)[:200]}


def check_sciencebase(url: str) -> dict:
    guard(url)
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
        j = r.json()
        files = sorted((f.get("name", ""), f.get("size")) for f in j.get("files", []))
        return {"ok": r.status_code < 400, "http": r.status_code, "title": j.get("title"),
                "last_updated": (j.get("provenance") or {}).get("lastUpdated"), "n_files": len(files),
                "fingerprint": fingerprint(json.dumps(files).encode())}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": repr(e)[:200]}


def check_arcgis(url: str) -> dict:
    """ArcGIS REST layer: metadata (?f=pjson) and a record count, to prove the layer is queryable."""
    guard(url)
    try:
        meta = requests.get(url, params={"f": "pjson"}, headers={"User-Agent": UA}, timeout=TIMEOUT).json()
        cnt = requests.get(url.rstrip("/") + "/query", params={"where": "1=1", "returnCountOnly": "true", "f": "json"},
                           headers={"User-Agent": UA}, timeout=TIMEOUT).json()
        return {"ok": "name" in meta, "http": 200, "layer_name": meta.get("name"), "geometry_type": meta.get("geometryType"),
                "n_fields": len(meta.get("fields", [])), "field_names": [f.get("name") for f in meta.get("fields", [])][:40],
                "max_record_count": meta.get("maxRecordCount"), "record_count": cnt.get("count"),
                "fingerprint": fingerprint(json.dumps([meta.get("name"), cnt.get("count")]).encode())}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": repr(e)[:200]}


def check_github(repo: str) -> dict:
    headers = {"User-Agent": UA, "Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    try:
        r = requests.get(f"https://api.github.com/repos/{repo}", headers=headers, timeout=TIMEOUT)
        j = r.json()
        b = requests.get(f"https://api.github.com/repos/{repo}/branches/{j.get('default_branch', 'main')}",
                         headers=headers, timeout=TIMEOUT).json()
        sha = (b.get("commit") or {}).get("sha")
        return {"ok": r.status_code < 400, "http": r.status_code, "pushed_at": j.get("pushed_at"),
                "head": sha, "fingerprint": fingerprint((sha or "").encode())}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": repr(e)[:200]}


def main() -> int:
    reg = json.loads((ROOT / "registry" / "sources.json").read_text())
    feed_path = ROOT / "docs" / "data" / "feed.json"
    hist_path = ROOT / "docs" / "data" / "feed_history.json"
    prev = {}
    if feed_path.exists():
        prev = {e["id"]: e for e in json.loads(feed_path.read_text()).get("entries", [])}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entries, events = [], []
    for s in reg["sources"]:
        if not s.get("feed"):
            continue
        kind = s.get("feed_kind", "http")
        if kind == "sciencebase":
            res = check_sciencebase(s["feed_url"])
        elif kind == "github":
            res = check_github(s["feed_repo"])
        elif kind == "arcgis":
            res = check_arcgis(s.get("feed_url") or s["url"])
        else:
            res = check_http(s.get("feed_url") or s["url"])
        old = prev.get(s["id"], {})
        changed = bool(old and old.get("fingerprint") and res.get("fingerprint") and old["fingerprint"] != res["fingerprint"])
        entry = {"id": s["id"], "title": s["title"], "url": s["url"], "kind": kind, "checked_utc": now,
                 "changed_since_previous_check": changed, **res}
        entries.append(entry)
        if changed or (old and old.get("ok") != res.get("ok")):
            events.append({"utc": now, "id": s["id"], "event": "changed" if changed else ("recovered" if res.get("ok") else "unreachable"),
                           "from": old.get("fingerprint"), "to": res.get("fingerprint")})
    feed = {"generated_utc": now, "policy": "Official sources only. drivendata.org is never requested by this feed; "
            "leaderboard, forum and submission pages are links for a human to open.", "entries": entries}
    feed_path.parent.mkdir(parents=True, exist_ok=True)
    feed_path.write_text(json.dumps(feed, indent=1) + "\n")
    hist = json.loads(hist_path.read_text()) if hist_path.exists() else []
    hist = (events + hist)[:200]
    hist_path.write_text(json.dumps(hist, indent=1) + "\n")
    print(f"checked {len(entries)} sources; {len(events)} change events; "
          f"{sum(1 for e in entries if e.get('ok'))} reachable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
