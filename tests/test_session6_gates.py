"""Unit tests for Session 6 shared holdout, canary, uniqueness, and submission writer gates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from scipy.stats import spearmanr

from gems27 import canary_and_uniqueness as cu
from gems27 import evaluate_holdout as eh
from gems27 import grid, metric, submission_writer


def test_fast_binary_spearman_matches_scipy_exact() -> None:
    rng = np.random.default_rng(2026)
    s = rng.normal(size=25_000).astype(np.float32)
    b = (rng.uniform(size=25_000) < 0.015).astype(np.float32)
    u = cu._unit_rank_vector(s)
    fast = cu._corr_with_unit_rank(u, b)
    exact = float(spearmanr(s, b).statistic)
    assert abs(fast - exact) < 1e-13

    # Also test continuous-valued registry raster path
    c = rng.uniform(0.0, 1.0, size=25_000).astype(np.float32)
    fast_c = cu._corr_with_unit_rank(u, c)
    exact_c = float(spearmanr(s, c).statistic)
    assert abs(fast_c - exact_c) < 1e-13


def test_buffered_holdout_split_and_exact_block_accounting() -> None:
    foot = np.ones((240, 240), dtype=bool)
    cat = np.zeros((240, 240), dtype=bool)
    # Place 5 disconnected fault segments inside each quadrant away from boundaries
    for qy in (40, 150):
        for qx in (40, 150):
            for k in range(5):
                r0 = qy + k * 10
                cat[r0 : r0 + 4, qx + 5 : qx + 25] = True

    folds, quad = eh.buffered_component_draw(
        foot, cat, seed=200, hide_frac=0.25, buffer_px=3, boundary_px=15
    )
    assert len(folds) == 4
    for f in folds:
        assert not np.any(f["visible"] & f["truth"])
        assert f["receipt"]["nearest_visible_to_truth_px"] > 3.0

    rng = np.random.default_rng(7)
    pred_a = ((rng.uniform(size=foot.shape) < 0.02) & ~cat).astype(np.float32)
    pred_b = np.where(cat, 0.0, 0.0).astype(np.float32)
    # Put high precision dots near withheld truth for pred_b
    for f in folds:
        ty, tx = np.nonzero(f["truth"])
        pred_b[np.clip(ty + 1, 0, 239), tx] = 1.0
    pred_b[cat] = 0.0

    for f in folds:
        res, terms = eh.evaluate_fold(pred_b, f, foot, block_side=50)
        act = foot & f["region"] & ~f["masked_known"]
        direct = metric.dti_exact(np.where(act, pred_b, 0.0), act & f["truth"], valid=act)
        assert abs(res["dti"] - direct["dti"]) < 1e-7
        assert abs(eh.dti_from_terms(terms.sum(axis=0)) - res["dti"]) < 1e-12

    pooled = eh.evaluate_arms_pooled(
        {"cand": pred_b, "ctrl": pred_a}, folds, foot, candidate="cand", block_side=50, draws=200
    )
    assert pooled["evidence_class"] == "HOLDOUT-DTI"
    assert pooled["scores"]["cand"]["dti"] > pooled["scores"]["ctrl"]["dti"]
    assert pooled["paired_differences"]["ctrl"]["delta_dti"] > 0.0


def test_leakage_canary_flags_leaky_feature() -> None:
    foot = np.ones((160, 160), dtype=bool)
    cat = np.zeros((160, 160), dtype=bool)
    for qy in (30, 100):
        for qx in (30, 100):
            for k in range(4):
                cat[qy + k * 8 : qy + k * 8 + 3, qx : qx + 15] = True
    folds, _ = eh.buffered_component_draw(
        foot, cat, seed=201, hide_frac=0.25, buffer_px=3, boundary_px=10
    )
    rng = np.random.default_rng(9)
    clean_feat = rng.normal(size=(foot.sum(), 1)).astype(np.float32)
    res_ok = cu.run_leakage_canaries(clean_feat, ["clean"], foot, folds, auc_limit=0.90)
    assert res_ok["gate_passed"] is True

    leaky = folds[0]["hidden_all"][foot].astype(np.float32)[:, None]
    res_bad = cu.run_leakage_canaries(leaky, ["leaky_truth"], foot, folds, auc_limit=0.90)
    assert res_bad["gate_passed"] is False
    assert res_bad["max_symmetric_auc"] > 0.99


def test_submission_writer_text_and_value_guards(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        submission_writer.validate_text_limit("x" * 141, "note")
    with pytest.raises(ValueError):
        submission_writer.validate_text_limit("   ", "note")

    # Verify real template if present in data_cache
    tpl = Path("data_cache/sample_submission.tif")
    lbl = Path("data_cache/labels.tif")
    if tpl.is_file() and lbl.is_file():
        foot = grid.load_footprint(tpl)
        cat = grid.load_labels(lbl)
        pred = np.zeros(grid.SHAPE, dtype=np.float32)
        ay, ax = np.nonzero(foot & ~cat)
        pred[ay[:100], ax[:100]] = 1.0
        out = submission_writer.write_validated_submission_bundle(
            pred,
            template_path=tpl,
            footprint=foot,
            catalogue=cat,
            out_dir=tmp_path,
            family="27gemsdoe",
            slug="unit-test",
            date_tag="20261025",
            note_summary="unit test bundle",
            hypothesis_id="H29-TEST",
        )
        assert out["validator_output"]["all_hard_checks_passed"] is True
        assert out["emitted_dots"] == 100
        assert out["note_length"] <= 140

        # Catalogue overlap must fail closed
        bad = pred.copy()
        cy, cx = np.nonzero(foot & cat)
        bad[cy[0], cx[0]] = 1.0
        with pytest.raises(ValueError, match="catalogue"):
            submission_writer.write_validated_submission_bundle(
                bad,
                template_path=tpl,
                footprint=foot,
                catalogue=cat,
                out_dir=tmp_path,
                family="27gemsdoe",
                slug="bad-cat",
                date_tag="20261025",
                note_summary="bad",
                hypothesis_id="H29-TEST",
            )


def test_session6_promoted_run_card_downloads_and_site_contract() -> None:
    root = Path(__file__).resolve().parents[1]
    rc = json.loads((root / "evidence" / "run_card.json").read_text())
    for req_key in (
        "hypothesis",
        "mechanism",
        "mimic_process",
        "holdout_dti",
        "registry_correlation_overlap",
        "raster_sha256",
        "validator_output",
        "submission_name",
        "note",
        "verdict",
    ):
        assert req_key in rc, f"Missing Run Card key: {req_key}"

    assert rc["verdict"] == "promote"
    assert 0 < len(rc["note"]) <= 140
    assert rc["experiments_run"] <= rc["experiment_budget_limit"] == 3

    hd = rc["holdout_dti"]
    assert hd["evidence_class"] == "HOLDOUT-DTI"
    assert hd["evaluator_version"] == "gems27-pooled-hide-v2"
    assert hd["withheld_positive_pixels"] == 10892
    assert hd["ci"][0] < hd["dti"] < hd["ci"][1]
    assert hd["delta_vs_legacy_boof"] > 0.05 and hd["delta_vs_legacy_boof_ci95"][0] > 0.03

    lc = rc["leakage_canary"]
    assert lc["gate_passed"] is True and lc["max_symmetric_auc"] <= 0.90

    ug = rc["registry_correlation_overlap"]
    assert ug["gate_passed"] is True and ug["rasters_scanned"] >= 350
    assert ug["max_preplacement_surface_abs_spearman"] <= 0.90
    assert ug["max_final_dots_abs_spearman"] <= 0.90
    assert ug["max_mutual_3px_dot_overlap"] <= 0.70

    vo = rc["validator_output"]
    assert vo["all_hard_checks_passed"] is True
    assert vo["ok_to_download_and_submit"] is True
    assert vo["no_nan_inside_footprint"] is True
    assert vo["values_in_0_1"] is True
    assert vo["on_catalogue_positive_px"] == 0
    assert vo["emitted_dots"] == 37654

    dl = root / "docs" / "downloads"
    man = json.loads((dl / "manifest.json").read_text())["h29_1_recommended"]
    assert man["allfinite"] == rc["submission_name"]
    assert man["sha256_allfinite"] == rc["raster_sha256"]
    assert man["note"] == rc["note"]

    tif_all = dl / man["allfinite"]
    tif_nan = dl / man["nan"]
    assert tif_all.is_file() and tif_nan.is_file()
    assert hashlib.sha256(tif_all.read_bytes()).hexdigest() == rc["raster_sha256"]
    assert hashlib.sha256(tif_nan.read_bytes()).hexdigest() == rc["companion_nan_raster_sha256"]

    docs_idx = (root / "docs" / "index.html").read_text()
    root_idx = (root / "index.html").read_text()
    exec_sum = (root / "docs" / "executive-summary.html").read_text()
    research = (root / "docs" / "research.html").read_text()

    banner = "PASSED ALL AUTOMATED VALIDATION GATES — OK TO DOWNLOAD &amp; SUBMIT WITHOUT HUMAN INSPECTION"
    assert banner in docs_idx and banner in root_idx
    assert f'href="downloads/{man["allfinite"]}"' in docs_idx
    assert f'href="docs/downloads/{man["allfinite"]}"' in root_idx
    assert rc["note"] in docs_idx and rc["note"] in exec_sum
    assert "ORGANIZER-CONFIRMED" in docs_idx and "HOLDOUT-DTI" in docs_idx
    assert "0.2778" in research and "GEMSDOE32" in research and "session6_h29_forensics.svg" in research

