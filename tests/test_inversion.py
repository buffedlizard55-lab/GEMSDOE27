"""Tests for the Session-3 live-score inversion, budget model and coverage thinning.

The forward model must reproduce the two live anchors exactly; the retention rule must be a ratio of
blind coverages; the crowding factor of a sparse blind pattern must be ~1. Synthetic small grids are
used so the suite stays fast - no 12 M-pixel distance transforms here.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems27 import coverage_thin, metric, thinning  # noqa: E402

ALPHA, BETA = metric.ALPHA, metric.BETA
KAREA = 9.3803


def forward(tp, n, rho, g):
    return tp / (ALPHA * tp * (1.0 - rho) + ALPHA * n + BETA * g)


def test_kernel_area_constant_matches_direct_sum():
    r = int(np.ceil(metric.RADIUS_PX))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    assert float(np.maximum(1.0 - np.hypot(yy, xx) / metric.RADIUS_PX, 0.0).sum()) == pytest.approx(KAREA, rel=1e-3)


def test_naive_closure_is_the_rho_1_case_of_the_forward_model():
    """FPw = N - TPw (the closure used in knowledge/01) must equal the forward model at rho = 1."""
    for tp, n, g in [(5399, 60069, 12226), (4700, 44090, 12226), (1000, 20000, 12226)]:
        assert forward(tp, n, 1.0, g) == pytest.approx(tp / (ALPHA * n + BETA * g), rel=1e-12)


def test_forward_model_reproduces_both_live_anchors():
    """The two owner-reported anchors, from evidence/live_inversion.json (hash-authenticated rasters)."""
    p = ROOT / "evidence" / "live_inversion.json"
    if not p.exists():
        pytest.skip("run scripts/invert_live_scores.py first")
    inv = json.loads(p.read_text())
    by = {r["label"]: r for r in inv["submissions"]}
    for lbl, live in [("19GEMSDOE h19-5", 0.1922),
                      ("24GEMSDOE h25-1 dotted-h19-5-d1-5 (989f59505db1)", 0.2477)]:
        r = by[lbl]
        got = forward(r["credit_TPw"], r["n_scored"], r["rho_matched_over_TP"], inv["G_used"])
        assert got == pytest.approx(live, abs=2e-4), f"{lbl}: model {got:.4f} vs live {live}"


def test_blind_lattice_crowding_is_near_one():
    """A spacing-5 lattice has ~1 dot per matched truth pixel, so rho must be ~1 (the closure is exact)."""
    p = ROOT / "evidence" / "live_inversion.json"
    if not p.exists():
        pytest.skip("run scripts/invert_live_scores.py first")
    inv = json.loads(p.read_text())
    lat = [r for r in inv["submissions"] if "lattice" in r["label"]][0]
    assert lat["rho_matched_over_TP"] == pytest.approx(1.0, abs=0.05)
    assert lat["crowding_dots_in_kernel"] == pytest.approx(0.0, abs=0.05)


def test_g_estimate_is_inside_the_sibling_range():
    """|G| from the blind lattice must agree with the sibling's independent estimate to a few percent."""
    p = ROOT / "evidence" / "live_inversion.json"
    if not p.exists():
        pytest.skip("run scripts/invert_live_scores.py first")
    g = json.loads(p.read_text())["G_used"]
    assert 11_500 < g < 13_500, f"|G| = {g} outside the 11.5k-13.5k band agreed by three instruments"


def test_retention_rule_is_a_ratio_of_blind_coverages_and_matches_live():
    p = ROOT / "evidence" / "budget_optimum.json"
    if not p.exists():
        pytest.skip("run scripts/optimize_budget.py first")
    bo = json.loads(p.read_text())
    for v in bo["retention_validation"]:
        # the geometric prediction must be within 5% of the live-measured retention
        assert abs(v["relative_error"]) < 0.05, v
    assert len(bo["retention_validation"]) >= 2, "need two independent live pairs"


def test_coverage_thin_hits_budget_exactly_and_is_a_subset():
    rng = np.random.default_rng(0)
    mask = np.zeros((120, 120), bool)
    for _ in range(14):                      # synthetic 1-px ridge network
        y, x = rng.integers(10, 110, 2)
        yy = np.clip(y + np.arange(-18, 19), 0, 119)
        mask[yy, x] = True
    foot = np.ones(mask.shape, bool)
    for budget in (30, 80, 150):
        out = coverage_thin.coverage_thin(mask, budget, foot=foot)
        assert int(out.sum()) == budget
        assert bool((out & ~mask).sum() == 0), "selected pixels must come from the emission"


def test_coverage_thin_is_deterministic():
    rng = np.random.default_rng(1)
    mask = rng.random((80, 80)) < 0.05
    foot = np.ones(mask.shape, bool)
    a = coverage_thin.coverage_thin(mask, 60, foot=foot)
    b = coverage_thin.coverage_thin(mask, 60, foot=foot)
    assert np.array_equal(a, b)


def test_dot_thin_budget_is_monotone_in_distance():
    rng = np.random.default_rng(2)
    mask = rng.random((90, 90)) < 0.10
    counts = [int(thinning.dot_thin(mask, d).sum()) for d in (1.0, 1.5, 2.0, 3.0)]
    assert counts == sorted(counts, reverse=True), counts


def test_verify_downloads_still_passes_with_four_slots():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "verify_downloads.py")],
                       capture_output=True, text=True,
                       env={**__import__("os").environ, "GEMS_DATA_DIR": str(ROOT / "data_cache")})
    assert r.returncode == 0, r.stdout[-3000:]
    assert "0 failure(s)" in r.stdout
    for slot in ("primary", "secondary", "tertiary", "quaternary"):
        assert f"{slot}/nan" in r.stdout or slot in r.stdout, f"{slot} not verified"


def test_manifest_and_site_agree_on_four_slots():
    man = json.loads((ROOT / "docs" / "downloads" / "manifest.json").read_text())
    for k in ("primary", "secondary", "tertiary", "quaternary"):
        assert k in man and man[k]["emitted_px"] > 0
        assert (ROOT / "docs" / "downloads" / man[k]["nan"]).exists()
        assert (ROOT / "docs" / "downloads" / man[k]["zip"]).exists()
        assert len(man[k]["note"]) <= 200
    idx = (ROOT / "docs" / "index.html").read_text()
    assert man["quaternary"]["nan"] in idx, "slot 4 is not on the first screen"
