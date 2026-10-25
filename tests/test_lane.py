"""Lane L-2026-10-25: transform primitives, buffered holdout mask, run-card integrity."""

import json
from pathlib import Path

import numpy as np

from gems27 import holdout
from gems27.subsurface_features import _rank01, priority_poisson_disk

ROOT = Path(__file__).resolve().parents[1]


def test_rank01_ties_and_range():
    r = _rank01(np.array([10.0, 20.0, 20.0, 30.0]))
    assert np.allclose(r, [0.0, 0.5, 0.5, 1.0])
    rng = np.random.default_rng(0)
    big = _rank01(rng.integers(0, 5, size=10_000).astype(float))
    assert big.min() >= 0.0 and big.max() <= 1.0


def test_priority_poisson_disk_spacing_budget_subset():
    rng = np.random.default_rng(1)
    prob = rng.random((60, 60)).astype(np.float32)
    cand = np.ones((60, 60), bool)
    cand[:5, :] = False
    out = priority_poisson_disk(prob, cand, 2.8, 50)
    assert out.sum() == 50 and (out <= cand).all()
    from scipy.spatial import cKDTree
    pts = np.argwhere(out)
    d, _ = cKDTree(pts).query(pts, k=2)
    assert d[:, 1].min() >= 2.8 - 1e-9
    # priority: kept set must contain the global argmax candidate
    yx = np.unravel_index(np.argmax(np.where(cand, prob, -1)), prob.shape)
    assert out[yx]


def test_buffered_scoring_mask_excludes_ring_not_truth():
    foot = np.ones((40, 40), bool)
    labels = np.zeros((40, 40), bool)
    labels[10:30, 20] = True
    fold = holdout.make_quadrant_folds(foot)
    sp = holdout.make_split(labels, fold, 0, seed=200)
    valid = holdout.buffered_scoring_mask(sp, foot, buffer_px=6.0)
    assert not (valid & sp.hidden).any()          # truth handled separately by caller
    assert valid.sum() < (foot & sp.fold_mask).sum()  # ring actually removed something


def test_lane_run_card_verdict_and_uniqueness():
    card = json.loads((ROOT / "evidence" / "lane_run_card_2026-10-25.json").read_text())
    assert card["verdict"] in ("promote", "promote-exploratory", "negative")
    assert card["ok_to_submit"] == (card["verdict"] != "negative"
                                    and card["validator"]["zeros_hard_pass"]
                                    and card["uniqueness_vs_registry"]["pass"])
    u = card["uniqueness_vs_registry"]
    assert u["max_dot_overlap_within_3px_euclidean"] < 0.70
    assert u["max_surface_spearman"] < 0.90
    assert card["live_score"] is None and "UNSCORED" in card["live_score_label"]
    assert len(card["note_max_140_chars"]) <= 140
    hold = json.loads((ROOT / "evidence" / "lane_holdout_2026-10-25.json").read_text())
    assert max(hold["canary_auc"].values()) <= 0.90  # leakage canary clean
    assert hold["n_withheld_positives_total"] > 0
