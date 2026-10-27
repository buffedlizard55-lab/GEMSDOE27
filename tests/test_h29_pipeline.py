"""Unit tests for H29-1 (Lane L-S7-2026-10-25): weighted CELF submodular cover,
E-W flight-line destriping, GDR wellspring leakage firewall, and strict 600 m
buffer zero-leakage invariance of 2-stage nested spatial cross-fitting.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist

from gems27.coverage_thin import (
    coverage_thin,
    expected_weighted_coverage,
    weighted_celf_cover,
)
from gems27.hydrothermal_piedmont import (
    BUFFER_PX,
    S2_VESSELNESS_NAMES,
    compute_stage2_vesselness,
    destripe_ew_geodawn,
    fit_predict_two_stage_oof,
    load_wellspring_geotherm_grids,
)


def test_weighted_celf_cover_beats_unweighted_on_high_prob_ridge() -> None:
    """Fixes H27-6: narrow high-posterior fault ridge must beat broad low-prob plateau."""
    H, W = 48, 48
    dom = np.ones((H, W), dtype=bool)
    prob = np.full((H, W), 0.01, dtype=np.float32)
    # Wide low-probability plateau in left half:
    prob[8:40, 4:20] = 0.04
    # Narrow high-probability NNE fault trace in right half:
    for r in range(6, 42):
        c = 32 + (r - 24) // 4
        prob[r, c] = 0.75
        prob[r, c - 1] = 0.25

    elig = dom.copy()
    cand_unweighted = prob >= 0.03
    budget = 10

    sel_w = weighted_celf_cover(prob, elig, dom, budget=budget, gamma=1.5, min_sep_px=2.0)
    sel_u = coverage_thin(cand_unweighted, budget=budget, foot=dom, block=2.0)

    assert int(sel_w.sum()) == budget
    assert not (sel_w & ~elig).any()
    pts = np.argwhere(sel_w).astype(np.float64)
    assert float(pdist(pts).min()) >= 2.0 - 1e-9

    # Determinism check:
    sel_w2 = weighted_celf_cover(prob, elig, dom, budget=budget, gamma=1.5, min_sep_px=2.0)
    assert np.array_equal(sel_w, sel_w2)

    cov_w = expected_weighted_coverage(sel_w, prob, dom, gamma=1.5)
    cov_u = expected_weighted_coverage(sel_u, prob, dom, gamma=1.5)
    assert cov_w > cov_u * 2.0


def test_destripe_ew_geodawn_removes_ew_corrugation_preserves_nne_step() -> None:
    H, W = 80, 80
    valid = np.ones((H, W), dtype=bool)
    yy, xx = np.indices((H, W), dtype=np.float32)
    # Tectonic NNE fault step:
    step = np.tanh((xx - 40.0 - 0.25 * (yy - 40.0)) / 2.0) * 10.0
    # Artificial 200 m E-W flight-line corrugation:
    corrugation = (np.where((yy.astype(int) % 2) == 0, 3.0, -3.0)).astype(np.float32)
    noisy = step + corrugation
    cleaned = destripe_ew_geodawn(noisy, valid)
    err_before = float(np.sqrt(np.mean((noisy - step) ** 2)))
    err_after = float(np.sqrt(np.mean((cleaned - step) ** 2)))
    assert err_after < err_before * 0.25


def test_wellspring_geotherm_firewall_ignores_dist_known_fault_px(tmp_path: Path) -> None:
    """Poisoning `dist_known_fault_px` must have zero effect on H29 geotherm grids."""
    H, W = 40, 40
    foot = np.ones((H, W), dtype=bool)
    csv_a = tmp_path / "ws_a.csv"
    csv_b = tmp_path / "ws_b.csv"
    rows = [
        {"row": 10, "col": 12, "temp_c": 24.0, "geothermquartz_c": 145.0, "geothermchalc_c": 115.0, "geothermcat_c": 138.0, "dist_known_fault_px": 0.0},
        {"row": 28, "col": 30, "temp_c": 68.0, "geothermquartz_c": 160.0, "geothermchalc_c": np.nan, "geothermcat_c": 152.0, "dist_known_fault_px": 0.0},
        {"row": 20, "col": 20, "temp_c": 15.0, "geothermquartz_c": np.nan, "geothermchalc_c": np.nan, "geothermcat_c": np.nan, "dist_known_fault_px": 999.0},
    ]
    df_a = pd.DataFrame(rows)
    df_b = df_a.copy()
    df_b["dist_known_fault_px"] = [99999.0, -12345.0, 0.0]
    df_a.to_csv(csv_a, index=False)
    df_b.to_csv(csv_b, index=False)

    ga = load_wellspring_geotherm_grids(csv_a, (H, W), foot)
    gb = load_wellspring_geotherm_grids(csv_b, (H, W), foot)
    for a, b in zip(ga, gb):
        assert np.all(np.isfinite(a))
        assert np.array_equal(a, b)
    # Cold well (24 C) with 145 C quartz geothermometer must show strong positive disequilibrium:
    assert float(ga[1][10, 12]) > float(ga[1][20, 20])


def test_two_stage_oof_strict_zero_leakage_across_600m_buffer() -> None:
    """Mutating ALL labels inside fold 0 AND its 600 m buffer must change fold 0 predictions by 0.0."""
    rng = np.random.default_rng(42)
    H, W = 64, 64
    foot = np.ones((H, W), dtype=bool)
    n = int(foot.sum())
    base_X = rng.normal(size=(n, 6)).astype(np.float32)
    h29_X = rng.normal(size=(n, 4)).astype(np.float32)

    labels_a = np.zeros((H, W), dtype=bool)
    # Plant synthetic faults in all 4 quadrants:
    labels_a[8:22, 12] = True
    labels_a[8:22, 48] = True
    labels_a[40:56, 14] = True
    labels_a[40:56, 50] = True
    base_X[labels_a[foot], 0] += 2.0

    s1_a, s2_a = fit_predict_two_stage_oof(
        base_X, h29_X, labels_a, foot, buffer_px=BUFFER_PX, max_neg=5000, seed=210
    )
    assert s1_a.shape == (H, W) and s2_a.shape == (H, W)
    assert np.all((s2_a >= 0.0) & (s2_a <= 1.0))

    # Corrupt 100% of labels inside NW quadrant AND inside the 6-px buffer around NW!
    from scipy.ndimage import distance_transform_edt

    from gems27.holdout import make_quadrant_folds

    nw = make_quadrant_folds(foot) == 0
    nw_plus_buf = nw | (distance_transform_edt(~nw) <= BUFFER_PX)
    labels_b = labels_a.copy()
    labels_b[nw_plus_buf] = ~labels_b[nw_plus_buf]

    s1_b, s2_b = fit_predict_two_stage_oof(
        base_X, h29_X, labels_b, foot, buffer_px=BUFFER_PX, max_neg=5000, seed=210
    )
    assert np.array_equal(s1_a[nw], s1_b[nw]), "Leakage detected in Stage-1 OOF!"
    assert np.array_equal(s2_a[nw], s2_b[nw]), "Leakage detected in Stage-2 Vesselness OOF!"

    v = compute_stage2_vesselness(s1_a, foot, foot)
    assert v.shape == (n, len(S2_VESSELNESS_NAMES))
    assert np.all(np.isfinite(v))


def test_h29_site_gate_and_run_card_integrity() -> None:
    """Verify H29-1 JSON Run Card, candidate manifest, and front-page/executive-summary automated status."""
    import json

    root = Path(__file__).resolve().parents[1]
    rc = json.loads((root / "evidence" / "h29_run_card_2026-10-25.json").read_text())
    man = json.loads((root / "docs" / "downloads" / "h29_candidate_manifest.json").read_text())

    assert rc["hypothesis_id"] == "H29-1"
    assert rc["canary_leakage"]["pass"] is True and rc["canary_leakage"]["max_h29_direction_invariant_auc"] <= 0.90
    assert rc["uniqueness_vs_registry"]["pass"] is True
    assert rc["uniqueness_vs_registry"]["n_peer_rasters_checked"] == 12
    assert rc["uniqueness_vs_registry"]["max_surface_spearman_preplacement"] <= 0.90
    assert rc["uniqueness_vs_registry"]["max_postplacement_spearman_vs_peers"] <= 0.90
    assert rc["uniqueness_vs_registry"]["max_dot_overlap_within_3px_vs_peers"] <= 0.70
    assert rc["validator"]["technical_validator_pass"] is True
    assert rc["validator"]["whole_array_nan_count_allfinite"] == 0
    assert rc["validator"]["range_in_0_1"] is True
    assert len(rc["note_max_140_chars"]) <= 140
    assert rc["verdict"] in ("promote", "negative")
    assert rc["ok_to_submit"] == man["ok_to_submit"]

    tif_path = root / "docs" / "downloads" / man["allfinite"]
    zip_path = root / "docs" / "downloads" / man["zip_allfinite"]
    assert tif_path.is_file() and zip_path.is_file()

    # H29-S is an owner-reported prior submission; the current pages must not
    # offer it as a new candidate, regardless of historic technical checks.
    assert man["ok_to_submit"] is False and "DO NOT RESUBMIT" in man["note"]
    for page_path in (root / "index.html", root / "docs" / "index.html", root / "docs" / "executive-summary.html"):
        html = page_path.read_text()
        assert "DO NOT SUBMIT" in html
        assert "NOT AUTHORIZED FOR A WEEKLY SLOT" in html
        assert man["allfinite"] not in html

