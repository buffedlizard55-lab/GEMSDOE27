import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PAGES = ["index.html", "executive-summary.html", "how-to-submit.html", "topology.html", "research.html", "sources.html"]


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs, self.ids = [], set()

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        for k in ("href", "src"):
            if k in d:
                self.refs.append(d[k])
        if "id" in d:
            self.ids.add(d["id"])


def test_site_builds_from_json_only_and_pages_exist():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_site.py")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    for p in PAGES:
        assert (DOCS / p).is_file() and (DOCS / p).stat().st_size > 2000


def test_all_internal_links_and_assets_resolve():
    for base, p in [(DOCS, q) for q in PAGES] + [(ROOT, "index.html")]:
        parser = Links()
        parser.feed((base / p).read_text())
        for ref in parser.refs:
            if re.match(r"^(https?:|mailto:|#|data:)", ref):
                continue
            target = ref.split("#")[0]
            assert (base / target).exists(), f"{base.name}/{p}: broken internal reference {ref}"


def test_repository_root_front_page_shows_current_submission_decision():
    root_idx = (ROOT / "index.html").read_text()
    assert "NO CURRENT TIFF IS AUTHORIZED FOR A WEEKLY SLOT" in root_idx
    assert "EVIDENCE PASS — NOT SLOT-AUTHORIZED — DO NOT SUBMIT" in root_idx
    assert "gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif" in root_idx
    assert "Download H31-1 for research/audit only (DO NOT UPLOAD)" in root_idx
    assert "DO NOT SUBMIT H28-3" in root_idx
    assert (ROOT / ".nojekyll").exists()


def test_front_page_does_not_authorize_h31_or_offer_failed_h28_3_as_submission():
    idx = (DOCS / "index.html").read_text()
    assert "NO CURRENT TIFF IS AUTHORIZED FOR A WEEKLY SLOT" in idx
    assert "EVIDENCE PASS — NOT SLOT-AUTHORIZED — DO NOT SUBMIT" in idx
    assert "Download H31-1 for research/audit only (DO NOT UPLOAD)" in idx
    assert "There is no one-click submission download for this run." in idx
    assert "NOT APPROVED FOR SUBMISSION" in idx
    assert "h28-3-strain-conductivity" not in idx or "h28-3-strain-conductivity" not in "\n".join(
        re.findall(r'<a[^>]+download[^>]*>', idx)
    )
    summary = (DOCS / "executive-summary.html").read_text()
    assert "NOT OK TO SUBMIT NOW" in summary
    assert "RESEARCH/AUDIT ONLY — NOT OK TO SUBMIT NOW" in summary
    assert "DOWNLOAD &amp; SUBMIT THIS ONE" not in summary
    assert "PROJECTION (anchor-transfer; not a score)" in summary
    audit = json.loads((DOCS / "data" / "submission_readiness_audit.json").read_text())
    assert audit["slot_authorized"] == []
    assert "approved" not in audit
    assert "how-to-submit.html" in summary
    for site_id in ("GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
                    "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"):
        assert site_id in summary
    how = (DOCS / "how-to-submit.html").read_text()
    assert "Predicted values must be in range [0, 1]" in how
    assert "No current submission file or note is authorized" in how
    assert "gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif" in how


def test_research_page_lists_preregistered_h28_hypotheses_and_evidence_link():
    research = (DOCS / "research.html").read_text()
    registry = json.loads((ROOT / "registry" / "next_hypotheses.json").read_text())
    for hypothesis in registry["hypotheses"]:
        assert hypothesis["id"] in research
    assert "knowledge/07_untried_hypotheses.md" in research
    assert "knowledge/08_preregistration_H28-1.md" in research
    evidence = ROOT / "evidence" / "h28_1_edge_holdout.json"
    if evidence.exists():
        assert "evidence/h28_1_edge_holdout.json" in research
        assert "leaderboard score" in research
    candidate_manifest = DOCS / "downloads" / "h28_1_candidate_manifest.json"
    if candidate_manifest.exists():
        candidate = json.loads(candidate_manifest.read_text())["candidate"]
        assert candidate["format_verified"] is True
        assert len(candidate["note"]) <= 200
        assert candidate["content_id"] in research
        assert candidate["nan"] not in research
        assert candidate["zip"] not in research
        assert candidate["allfinite"] not in research
        assert "audit only" in research
    h28_3 = ROOT / "evidence" / "h28_3_strain_holdout.json"
    if h28_3.exists():
        result = json.loads(h28_3.read_text())
        assert "H28-3" in research
        assert "NO NEW SUBMISSION IS APPROVED" in research
        assert result["gate"]["pass"] is False
        assert "NOT APPROVED FOR SUBMISSION" in (DOCS / "executive-summary.html").read_text()


def test_no_score_is_claimed_for_27gemsdoe_and_scripts_never_fetch_drivendata():
    sc = json.loads((ROOT / "registry" / "live_scores.json").read_text())
    assert all(x["score"] is None for x in sc["27GEMSDOE"])
    for py in list((ROOT / "scripts").glob("*.py")) + list((ROOT / "src").rglob("*.py")):
        txt = py.read_text()
        for m in re.finditer(r"requests\.(get|head|post)\(([^)]*)", txt):
            assert "drivendata" not in m.group(2).lower(), f"{py.name} requests drivendata.org"
    feed = (ROOT / "scripts" / "refresh_source_feed.py").read_text()
    assert 'FORBIDDEN = ("drivendata.org",)' in feed and "refusing to request" in feed


def test_downloads_have_unique_names_and_zip_single_member():
    import zipfile
    names = [p.name for p in (DOCS / "downloads").glob("*.tif")]
    assert len(names) == len(set(names)) and all(re.search(r"-[0-9a-f]{12}-(nan|allfinite)\.tif$", n) for n in names)
    for z in (DOCS / "downloads").glob("*.zip"):
        with zipfile.ZipFile(z) as zf:
            assert len(zf.namelist()) == 1 and zf.namelist()[0].endswith(".tif")


def test_slot_authorization_is_separate_from_evidence_pass():
    for name in PAGES:
        text = (DOCS / name).read_text()
        assert "NOT AUTHORIZED FOR A WEEKLY SLOT" in text
        badges = re.findall(r'<span class="badge[^"]*"[^>]*>(.*?)</span>', text)
        assert all("OK TO DOWNLOAD AND SUBMIT" not in badge for badge in badges)
