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
        self.refs = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        for key in ("href", "src"):
            if key in d:
                self.refs.append(d[key])


def test_site_builds_and_is_deterministic():
    command = [sys.executable, str(ROOT / "scripts" / "build_site.py")]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    paths = [DOCS / p for p in PAGES] + [ROOT / "index.html", ROOT / "EXECUTIVE_SUMMARY.md"]
    assert all(p.is_file() and p.stat().st_size > 1000 for p in paths)
    before = [p.read_bytes() for p in paths]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert before == [p.read_bytes() for p in paths]


def test_all_internal_links_and_assets_resolve():
    for base, p in [(DOCS, q) for q in PAGES] + [(ROOT, "index.html")]:
        parser = Links()
        parser.feed((base / p).read_text())
        for ref in parser.refs:
            if re.match(r"^(https?:|mailto:|#|data:)", ref):
                continue
            assert (base / ref.split("#")[0]).exists(), f"{base.name}/{p}: broken reference {ref}"


def test_h31_reported_submitted_and_never_offered_as_new():
    for name in PAGES:
        text = (DOCS / name).read_text()
        assert "DO NOT SUBMIT" in text
        assert "NOT AUTHORIZED FOR A WEEKLY SLOT" in text
        assert "cf8e1bbef244" in text and "0.2250" in text and "OWNER-REPORTED" in text
        assert "best new unique submission to upload" not in text.lower()
        assert not re.search(r'<a[^>]+href="[^\"]*cf8e1bbef244[^\"]*"[^>]*download', text)
    assert "DO NOT SUBMIT" in (ROOT / "index.html").read_text()
    assert (ROOT / ".nojekyll").exists()


def test_executive_summary_qualifies_conflicting_historical_reports():
    summary = (DOCS / "executive-summary.html").read_text()
    md = (ROOT / "EXECUTIVE_SUMMARY.md").read_text()
    for site in ("GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
                 "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"):
        assert site in summary and site in md
    for text in (summary, md):
        assert "0.2778" in text and "not organizer-confirmed" in text.lower()
        assert "GEMSDOE28/GEMSDOE31" in text and "not a" in text.lower()
        assert "hidden truth" in text.lower() and "cannot" in text.lower()


def test_research_and_manual_instructions_are_explicit():
    research = (DOCS / "research.html").read_text()
    assert "30_lane_2026-10-27_preregistration.md" in research
    assert "not drainage" in research.lower()
    assert "quadrant-stratified" in research and "approximate" in research
    sources = (DOCS / "sources.html").read_text()
    assert "IR-2026-10-27-conflicting-score-file-attribution" in sources
    assert "dated snapshots, not a live leaderboard" in sources
    how = (DOCS / "how-to-submit.html").read_text()
    assert "Predicted values must be in range [0, 1]" in how
    assert "does not guarantee organizer acceptance" in how
    assert "no approved new TIFF" in how


def test_research_tif_is_never_advertised_as_approved():
    card_path = ROOT / "evidence/relief_profile_run_card_20261027.json"
    if card_path.exists():
        card = json.loads(card_path.read_text())
        if card.get("raster"):
            text = (DOCS / "research.html").read_text()
            assert card["raster"]["primary_allfinite"] in text
            assert "Download research GeoTIFF — NOT APPROVED FOR SUBMISSION" in text


def test_no_score_is_claimed_for_27gemsdoe_and_scripts_never_fetch_drivendata():
    scores = json.loads((ROOT / "registry" / "live_scores.json").read_text())
    assert all(x["score"] is None for x in scores["27GEMSDOE"])
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
