import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PAGES = ["index.html", "executive-summary.html", "topology.html", "research.html", "sources.html"]


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
    assert "NO TIFF IS APPROVED TO SUBMIT" in root_idx
    assert "DO NOT SUBMIT H28-3" in root_idx
    assert (ROOT / ".nojekyll").exists()


def test_front_page_does_not_offer_failed_h28_3_as_submission():
    idx = (DOCS / "index.html").read_text()
    assert "NO TIFF IS APPROVED TO SUBMIT" in idx
    assert "No submission download is approved. One research-only TIFF is linked below." in idx
    assert "NOT APPROVED FOR SUBMISSION" in idx
    assert "h28_3_negative_research_manifest.json" not in idx or "NOT APPROVED" in idx
    assert 'download class="mono"' not in idx
    assert ".tif\" download" not in idx
    summary = (DOCS / "executive-summary.html").read_text()
    assert "NO TIFF IS APPROVED TO SUBMIT" in summary
    assert ".tif\" download" not in summary


def test_h28_6_json_run_card_and_public_eligibility_are_explicit():
    card = json.loads((ROOT / "evidence" / "h28_6_run_card.json").read_text())
    result = json.loads((ROOT / "evidence" / "h28_6_radiometric_holdout.json").read_text())
    assert card["holdout"]["pooled_delta"] == result["e2_holdout"]["candidate_minus_baseline_pooled_dti"]
    assert card["holdout"]["seed_bootstrap_95_ci"] == result["e2_holdout"]["paired_seed_summary"]["ci95_seed_resampling"]
    assert card["raster"]["sha256"] == result["artifact"]["sha256"]
    assert card["submission"]["ok_to_submit"] is result["eligibility"]["ok_to_submit"]
    assert card["verdict"] == "negative"
    assert card["holdout"]["label"].startswith("HOLDOUT-DTI")
    assert card["holdout"]["seed_bootstrap_95_ci"][0] < 0 < card["holdout"]["seed_bootstrap_95_ci"][1]
    assert card["holdout"]["withheld_positive_occurrences"] > 0
    assert card["parallel_uniqueness"]["preplacement_max_spearman"] < 0.90
    assert card["parallel_uniqueness"]["final_max_spearman"] < 0.90
    assert card["parallel_uniqueness"]["final_max_directed_dot_overlap_within_3px"] < 0.70
    assert card["raster"]["sha256"] == card["validator"]["sha256"]
    assert card["validator"]["no_nan_inside_footprint"] is True
    assert card["validator"]["inside_range_0_1"] is True
    assert card["validator"]["crs_shape_transform_match_template"] is True
    assert card["submission"]["ok_to_submit"] is False
    assert card["submission"]["note_characters"] == len(card["submission"]["note"])
    assert card["submission"]["note_characters"] <= 140

    research = (DOCS / "research.html").read_text()
    hypothesis_ledger = json.loads((ROOT / "registry" / "hypotheses.json").read_text())
    h28_6_entry = next(h for h in hypothesis_ledger["hypotheses"] if h["id"] == "H28-6")
    assert "FROZEN GATE FAILED" in h28_6_entry["status"]
    assert "NOT APPROVED FOR SUBMISSION" in h28_6_entry["status"]
    assert "DO NOT SUBMIT. NOT APPROVED FOR SUBMISSION" in research
    assert "Download research-only GeoTIFF" in research
    assert "NOT APPROVED TO SUBMIT" in research
    assert card["raster"]["path"].removeprefix("docs/") in research
    assert "da120b7ee1c8" in research
    assert card["submission"]["name"] == Path(card["raster"]["path"]).name
    summary = (DOCS / "executive-summary.html").read_text()
    assert "GEMSDOE32 H33-2-B2, reported 0.2778" in summary
    assert "OWNER-REPORTED, not organizer-confirmed" in summary
    assert "knowledge/12_why_02778_won.md" in summary
    for page in (DOCS / "index.html", DOCS / "executive-summary.html"):
        text = page.read_text()
        assert "DO NOT SUBMIT H28-6" in text
        assert "NO TIFF IS APPROVED TO SUBMIT" in text
        assert "NOT APPROVED FOR SUBMISSION" in text
        assert 'download class="mono"' not in text


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
