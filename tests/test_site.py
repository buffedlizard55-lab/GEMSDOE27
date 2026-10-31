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
    audit = json.loads((DOCS / "data/submission_readiness_audit.json").read_text())
    assert audit["slot_authorized"] == []
    assert audit["evidence_passed_not_slot_authorized"] == []
    assert "approved" not in audit
    for name in PAGES:
        text = (DOCS / name).read_text()
        assert "DO NOT SUBMIT" in text
        assert "NOT AUTHORIZED FOR A WEEKLY SLOT" in text
        assert "cf8e1bbef244" in text and "0.2250" in text and "OWNER-REPORTED" in text
        assert "best new unique submission to upload" not in text.lower()
        assert not re.search(r'<a[^>]+href="[^\"]*cf8e1bbef244[^\"]*"[^>]*download', text)
    root = (ROOT / "index.html").read_text()
    assert "DO NOT SUBMIT" in root
    assert "gems27-h33-bss-complement-20261027-9ba8480691ed-allfinite.tif" in root
    assert "NOT OK TO SUBMIT the generated TIFF" in root
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


def test_h28_7_novelty_is_nuanced_not_misclassified():
    registry = json.loads((ROOT / "registry/next_hypotheses.json").read_text())
    h28_7 = next(row for row in registry["hypotheses"] if row["id"] == "H28-7")
    assert "UNTESTED exact direction-coherent" in h28_7["status"]
    assert "related ratio/front features were already tested" in h28_7["status"]
    assert "not a new radiometric source" in h28_7["differs_from_repo"]
    assert "not organizer-authenticated" in h28_7["data_gate"]
    research = (DOCS / "research.html").read_text()
    assert "exact direction-coherent, scale-persistence operator" in research
    assert "not a new radiometric source or wholly untested signal" in research


def test_research_and_manual_instructions_are_explicit():
    research = (DOCS / "research.html").read_text()
    assert "30_lane_2026-10-27_preregistration.md" in research
    assert "not drainage" in research.lower()
    assert "quadrant-stratified" in research and "approximate" in research
    for hypothesis_id in ("H27-16", "H29-5", "H28-6", "H28-7"):
        assert hypothesis_id in research
    assert "current availability and hashes were not verified" in research
    assert "allowlist..<br>" not in research
    assert "restored here..<br>" not in research
    assert "has yet been run..<br>" not in research
    assert "no new lane has been assigned" in research.lower()
    sources = (DOCS / "sources.html").read_text()
    # The sources page shows only the two most recent dated irregularity batches (build_site.py).
    # Check the newest batch is displayed and the older record remains in the registry.
    assert "IR-2026-10-31-lane-paragraph-missing" in sources
    registry_ids = {x["id"] for x in json.loads((ROOT / "registry" / "irregularities.json").read_text())["items"]}
    assert "IR-2026-10-29-h28-6-stale-untried" in registry_ids
    assert "IR-2026-10-28-06-pairwise-final-dot-screen" in (ROOT / "registry/irregularities.json").read_text()
    assert "dated snapshots, not a live leaderboard" in sources
    how = (DOCS / "how-to-submit.html").read_text()
    assert "Predicted values must be in range [0, 1]" in how
    assert "does not guarantee organizer acceptance" in how
    assert "no approved new TIFF" in how


def test_executive_download_decision_table_is_explicit_and_fail_closed():
    expected = (
        "Download and submission decision",
        "No justified organizer-score estimate.",
        "No currently approved file",
        "frozen holdout gate failed.",
    )
    for path in (DOCS / "index.html", DOCS / "executive-summary.html",
                 ROOT / "EXECUTIVE_SUMMARY.md"):
        text = path.read_text()
        assert all(item in text for item in expected), path


def test_historical_table_reports_unknown_estimates_and_pairwise_duplicate_failures():
    summary = (DOCS / "executive-summary.html").read_text()
    markdown = (ROOT / "EXECUTIVE_SUMMARY.md").read_text()
    expected_sites = ("GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
                      "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36")
    for site in expected_sites:
        assert site in summary and site in markdown
    assert "Estimated organizer score" in summary
    assert "github.com/buffedlizard55-lab/GEMSDOE32/blob/" in summary
    assert "?raw=1" in summary and "?raw=1" in markdown
    assert "Download gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif" in markdown
    assert "Unknown; no justified conversion to organizer score" in markdown
    assert "NO — duplicate stop triggered vs 11/11 pinned rasters" in summary
    assert "Final-dot-only, pinned scope; not a global inventory" in markdown
    assert "Exact in-footprint dot match: GEMSDOE30" in summary
    assert "Exact in-footprint dot match: GEMSDOE25" in summary
    assert "vs GEMSDOE28 [g28_h38_1]" in summary  # disambiguate same-repository peer entries
    assert "Highest listed historical claim" in summary
    assert "OWNER-REPORTED in task; peer audit calls file UNSCORED" in summary


def test_session17_run_card_is_complete_and_fail_closed():
    card = json.loads((ROOT / "evidence/session17_run_card_20261028.json").read_text())
    assert card["new_geological_experiments"] == 0
    assert card["new_tiff_generated"] is False
    assert card["assigned_lane_status"].startswith("Missing")
    assert card["holdout_dti"]["label"] == "HOLDOUT-DTI"
    assert card["holdout_dti"]["withheld_positive_occurrences"] == 134150
    assert card["holdout_dti"]["frozen_efficacy_gate_pass"] is False
    assert card["registry_uniqueness"]["historical_best_screen"]["duplicate_stops"] == 9
    assert card["raster"]["sha256"] == card["registry_uniqueness"]["candidate_final_dot_recheck"]["candidate_raster_sha256"]
    assert len(card["raster"]["note"]) == card["raster"]["note_characters"] <= 140
    assert card["validator_output"]["independent_byte_validation_pass"] is True
    assert card["validator_output"]["readiness_audit"]["selector_authorized"] is False
    assert card["organizer_score_estimate"] is None
    assert card["verdict"] == "negative" and card["ok_to_submit"] is False
    assert card["slot_authorized"] is False


def test_generated_h33_tiff_is_shown_and_not_approved():
    name = "gems27-h33-bss-complement-20261027-9ba8480691ed-allfinite.tif"
    for page in ("index.html", "executive-summary.html", "how-to-submit.html"):
        text = (DOCS / page).read_text()
        assert name in text
        assert "NOT OK TO SUBMIT the generated TIFF" in text
        assert "Download research GeoTIFF — NOT APPROVED FOR SUBMISSION" in text
        assert "OK TO DOWNLOAD AND SUBMIT" not in text
    assert name in (ROOT / "EXECUTIVE_SUMMARY.md").read_text()


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


def test_markdown_research_download_resolves_and_is_not_approved():
    md = (ROOT / "EXECUTIVE_SUMMARY.md").read_text()
    match = re.search(r'\[\`H33-1 all-finite GeoTIFF[^]]+\]\(([^)]+\.tif)\)', md)
    assert match, "executive Markdown must link the verified research TIFF"
    assert (ROOT / match.group(1)).is_file(), "Markdown link must resolve from repository root"
    assert "DO NOT SUBMIT" in match.group(0)


def test_research_link_fail_closed_for_missing_or_mismatched_bytes(tmp_path, monkeypatch):
    import importlib.util

    spec = importlib.util.spec_from_file_location("site_builder", ROOT / "scripts/build_site.py")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    monkeypatch.setattr(builder, "ROOT", tmp_path)
    monkeypatch.setattr(builder, "DOCS", tmp_path / "docs")
    folder = tmp_path / "docs/downloads/research"
    folder.mkdir(parents=True)
    file = folder / "candidate.tif"
    card = {"raster": {"directory": "docs/downloads/research", "primary_allfinite": file.name,
                       "sha256": "expected"}}
    gate = {"actual_sha256": "expected", "independent_byte_validation": {"pass": True}}
    assert builder.verified_research_path(card, gate) is None  # missing
    file.write_bytes(b"bad")
    assert builder.verified_research_path(card, {**gate, "actual_sha256": "other"}) is None
    assert builder.verified_research_path(card, {**gate, "independent_byte_validation": {"pass": False}}) is None
    assert builder.verified_research_path(card, gate) == ("downloads/research/candidate.tif", "expected")
    card["raster"]["directory"] = "../outside"
    assert builder.verified_research_path(card, gate) is None


def test_untried_registry_does_not_recommend_a_tested_hypothesis():
    ledger = json.loads((ROOT / "registry/next_hypotheses.json").read_text())
    untried = {row["id"] for row in ledger["hypotheses"]}
    tested = {row["id"] for row in ledger["tested_hypotheses"]}
    assert not (untried & tested)
    assert "H28-6" in tested and "H28-6" not in untried
    assert "H28-6 gravity persistence: tested negative" in (DOCS / "research.html").read_text()
