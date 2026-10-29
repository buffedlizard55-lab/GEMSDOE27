"""Unit tests for the H29-XG joint gravity-magnetic cross-gradient features (no data needed)."""

import numpy as np

from gems27 import crossgrad_features as xg


def _foot(shape=(120, 120)):
    foot = np.zeros(shape, bool)
    foot[8:-8, 8:-8] = True
    return foot


def test_constant_fields_give_zero():
    foot = _foot()
    grav = np.where(foot, 2.0, np.nan)
    mag = np.where(foot, -5.0, np.nan)
    grids = xg.build_grids(grav, mag, foot)
    for name in xg.COLUMN_NAMES:
        assert np.all(grids[name][foot] == 0.0), name


def test_parallel_edges_score_lower_than_crossing_edges():
    foot = _foot()
    # Parallel: both fields step at the same column (normals are both along x), so sin ~ 0.
    grav_par = np.where(foot, 0.0, np.nan)
    grav_par[:, 60:] = np.where(foot[:, 60:], 1.0, np.nan)
    mag_par = np.where(foot, 0.0, np.nan)
    mag_par[:, 60:] = np.where(foot[:, 60:], 1.0, np.nan)
    # Crossing: magnetics step along rows (normals along y), gravity along columns (normals along x).
    mag_cross = np.where(foot, 0.0, np.nan)
    mag_cross[60:, :] = np.where(foot[60:, :], 1.0, np.nan)
    par = xg.build_grids(grav_par, mag_par, foot)["xg_sin_s2"]
    cross = xg.build_grids(grav_par, mag_cross, foot)["xg_sin_s2"]
    # Near the coincident edge column, parallel coupling is weak; at the crossing it is strong.
    assert cross[60, 60] > par[60, 60] + 0.2
    assert cross[60, 60] > 0.5


def test_outputs_bounded_finite_and_zero_outside_footprint():
    rng = np.random.default_rng(3)
    foot = _foot()
    grav = np.where(foot, rng.normal(size=foot.shape), np.nan)
    mag = np.where(foot, rng.normal(size=foot.shape), np.nan)
    grids = xg.build_grids(grav, mag, foot)
    for name in xg.COLUMN_NAMES:
        vals = grids[name][foot]
        assert np.all(np.isfinite(vals))
        assert vals.min() >= 0.0 and vals.max() <= 1.0 + 1e-6
        assert np.all(grids[name][~foot] == 0.0)


def test_feature_matrix_shape_and_order():
    foot = _foot()
    grav = np.where(foot, np.arange(foot.size, dtype=float).reshape(foot.shape) % 7, np.nan)
    mag = np.where(foot, np.arange(foot.size, dtype=float).reshape(foot.shape) % 5, np.nan)
    X = xg.build_feature_matrix(grav, mag, foot)
    assert X.shape == (int(foot.sum()), 3)
    grids = xg.build_grids(grav, mag, foot)
    for j, name in enumerate(xg.COLUMN_NAMES):
        assert np.array_equal(X[:, j], grids[name][foot])


def test_h29xg_run_card_is_fail_closed():
    """The H29-XG run card may never authorise a submission, and may list a raster only if every gate passed."""
    import json
    from pathlib import Path

    card_path = Path(__file__).resolve().parents[1] / "evidence" / "h29xg_run_card_2026-10-29.json"
    if not card_path.exists():
        return  # the card is produced by scripts/run_h29xg_crossgrad.py
    card = json.loads(card_path.read_text())
    assert card["ok_to_submit"] is False
    assert card["slot_authorized"] is False
    assert card["download_decision"] == "NOT OK TO SUBMIT"
    assert len(card["note_max_140_chars"]) <= 140
    if card["raster"]["primary_allfinite"] is not None:
        # A raster may exist only when efficacy and uniqueness both passed (preregistered writing rule).
        assert card["holdout"]["gate_efficacy_pass"] is True
        assert card["uniqueness_vs_registry"]["pass"] is True
    else:
        assert card["verdict"] == "negative"
