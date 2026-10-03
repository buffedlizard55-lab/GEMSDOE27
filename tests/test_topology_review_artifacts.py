import csv
import json
from pathlib import Path

from gems27.topology_classes import H27_5B_PRIORITY_CLASS, classify_review_class

ROOT = Path(__file__).resolve().parents[1]


def test_h27_5b_review_class_is_exact_exclusive_and_reproducible():
    summary = json.loads((ROOT / "evidence" / "structural_relay_classes.json").read_text())
    links = json.loads((ROOT / "registry" / "topology_candidates.json").read_text())["links"]
    assert summary["candidate_count"] == 345
    assert summary["priority_candidate_count"] == 81
    assert summary["files"]["priority_map_preview"] == "docs/assets/fig_map_h27_5b_priority.png"
    assert summary["priority_class"] == H27_5B_PRIORITY_CLASS
    assert "z>=3 deduplicated T-v2" in summary["priority_population"]
    assert "1-4 km gap" in summary["priority_population"]
    assert sum(summary["counts_by_exclusive_review_class"].values()) == 345

    counts = {}
    for row in links:
        expected = classify_review_class(row["same_fid"], row["same_name"], row["kinematic_compat"])
        assert row["review_class"] == expected
        counts[expected] = counts.get(expected, 0) + 1
    assert counts == summary["counts_by_exclusive_review_class"]
    assert counts[H27_5B_PRIORITY_CLASS] == 81
    basis = summary["priority_basis"]
    assert basis["graph_delta_P_used_for_priority"] is False
    assert "refuted" in basis["graph_value_ranking_status"]
    assert summary["priority_rule"] == (
        "different NBMG FID AND same non-unnamed NAME AND kinematic_compat=true"
    )
    assert "name_src != 'Unnamed fault'" in summary["same_name_semantics"]
    assert "Blank/Unspecified values" in summary["kinematic_compatibility_semantics"]


def test_focused_h27_5b_csv_and_geojson_are_81_sorted_source_linked_rows():
    csv_path = ROOT / "docs" / "data" / "topology_priority_h27_5b.csv"
    geojson_path = ROOT / "docs" / "data" / "topology_priority_h27_5b.geojson"
    with csv_path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 81
    assert all(row["review_class"] == H27_5B_PRIORITY_CLASS for row in rows)
    assert all(row["same_fid"] == "False" for row in rows)
    assert all(row["same_name"] == "True" for row in rows)
    assert all(row["kinematic_compat"] == "True" for row in rows)
    assert all(row["bridge"] == "True" for row in rows)
    assert all(row["nbmg_source_layer_url"].startswith("https://web2.nbmg.unr.edu/arcgis/rest/services/") for row in rows)
    assert all(row["setting_context_url"] == "https://www.osti.gov/servlets/purl/1724082" for row in rows)
    sort_keys = [(float(row["gap_km"]), row["link_id"]) for row in rows]
    assert sort_keys == sorted(sort_keys)
    assert {row["kind"] for row in rows} == {"end-to-end", "abutting", "tip-to-tip oblique"}

    geojson = json.loads(geojson_path.read_text())
    assert geojson["type"] == "FeatureCollection"
    assert geojson["crs_note"] == "WGS84 lon/lat"
    assert len(geojson["features"]) == 81
    for feature in geojson["features"]:
        assert feature["geometry"]["type"] == "LineString"
        props = feature["properties"]
        assert props["review_class"] == H27_5B_PRIORITY_CLASS
        assert props["fid_src"] != props["fid_tgt"]
        assert props["same_name"] is True and props["kinematic_compat"] is True
        assert "setting_hint" in props and "argument" in props
        assert "delta_second_moment_km2" in props


def test_h27_10_is_tested_failed_not_currently_untried_or_slot_authorized():
    screen = json.loads((ROOT / "registry" / "next_hypotheses.json").read_text())
    current_ids = {h["id"] for h in screen["hypotheses"]}
    assert 3 <= len(current_ids) <= 5
    assert "H27-10" not in current_ids
    tested = next(h for h in screen["tested_hypotheses"] if h["id"] == "H27-10")
    assert "FROZEN GATE FAILED" in tested["status"]
    assert "not eligible to justify a weekly slot" in tested["status"]

    initial = json.loads((ROOT / "evidence" / "h27_10_annulus_holdout_initial.json").read_text())
    corrected = json.loads((ROOT / "evidence" / "h27_10_annulus_holdout.json").read_text())
    assert initial["data_checks"]["all_additions_respect_minimum_spacing"] is False
    assert corrected["data_checks"]["all_additions_respect_minimum_spacing"] is True
    assert initial["candidate_minus_baseline_mean_gain"] == corrected["candidate_minus_baseline_mean_gain"]
    assert initial["gain_by_seed"] == corrected["gain_by_seed"]
    assert corrected["gate"]["pass"] is False
    assert corrected["gate"]["data_checks_passed"] is True


def test_topology_and_research_pages_disclose_review_only_and_refuted_signals():
    topology = (ROOT / "docs" / "topology.html").read_text()
    research = (ROOT / "docs" / "research.html").read_text()
    assert "Geologist-review priority class: H27-5b (81 / 345 links)" in topology
    assert "existing 345 shipped T-v2 links" in topology and "1–4 km" in topology
    assert "230 same-FID · 81 H27-5b · 22 other-name compatible · 12 conflict/unknown" in topology
    assert "data/topology_priority_h27_5b.csv" in topology
    assert "data/topology_priority_h27_5b.geojson" in topology
    assert "assets/fig_map_h27_5b_priority.png" in topology
    assert (ROOT / "docs" / "assets" / "fig_map_h27_5b_priority.png").is_file()
    assert "review class</th>" in topology
    assert "Current Session 5 untried screen (4 hypotheses)" in research
    assert "H27-10 annulus result — REJECTED; no weekly slot." in research
    assert "h27_10_annulus_holdout_initial.json" in research
    assert "not a score or proof of transfer" in topology
    assert "graph-ΔP ranking" in topology and "refuted as holdout-improvement signals" in topology
    assert "overlapping en-echelon step-over test" in topology
