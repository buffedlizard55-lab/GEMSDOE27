import itertools

import numpy as np

from gems27 import metric


def brute_force(pred, truth, valid, known):
    """Literal transcription of the official definition on a tiny grid (kernel radius 3 px)."""
    H, W = pred.shape
    act = valid & ~known
    P = np.where(act, pred, 0.0)
    G = truth & act
    gs = list(zip(*np.nonzero(G)))
    xs = list(itertools.product(range(H), range(W)))
    k = lambda d: max(1 - d / 3.0, 0.0)  # noqa: E731
    tp = sum(max([P[x] * k(np.hypot(x[0] - g[0], x[1] - g[1])) for x in xs] + [0.0]) for g in gs)
    fp = 0.0
    for x in xs:
        if P[x] > 0:
            m = max([k(np.hypot(x[0] - g[0], x[1] - g[1])) for g in gs] + [0.0])
            fp += P[x] * (1 - m)
    fn = len(gs) - tp
    return tp, fp, fn, tp / (tp + 0.2 * fp + 0.8 * fn + 1e-7)


def test_worked_example_from_problem_page():
    assert round(3.0 / (3.0 + 0.2 * 1.89 + 0.8 * 2.0), 2) == 0.60


def test_binary_and_exact_match_bruteforce_on_random_grids():
    rng = np.random.default_rng(3)
    for _ in range(6):
        H, W = 14, 17
        truth = rng.random((H, W)) < 0.08
        pred = (rng.random((H, W)) < 0.15).astype(float)
        valid = rng.random((H, W)) < 0.95
        known = rng.random((H, W)) < 0.05
        tp, fp, fn, dti = brute_force(pred, truth, valid, known)
        rb = metric.dti_binary(pred, truth, valid, known)
        re = metric.dti_exact(pred, truth, valid, known)
        for r in (rb, re):
            assert abs(r["TPw"] - tp) < 1e-9 and abs(r["FPw"] - fp) < 1e-9 and abs(r["dti"] - dti) < 1e-9


def test_soft_predictions_match_bruteforce():
    rng = np.random.default_rng(4)
    H, W = 12, 12
    truth = rng.random((H, W)) < 0.1
    pred = rng.random((H, W)) * (rng.random((H, W)) < 0.3)
    tp, fp, fn, dti = brute_force(pred, truth, np.ones((H, W), bool), np.zeros((H, W), bool))
    r = metric.dti_exact(pred, truth)
    assert abs(r["dti"] - dti) < 1e-9


def test_marginal_gain_matches_difference_of_scores_and_threshold_rule():
    rng = np.random.default_rng(5)
    H, W = 40, 40
    truth = rng.random((H, W)) < 0.05
    base = (rng.random((H, W)) < 0.10)
    add = (rng.random((H, W)) < 0.06)
    r = metric.marginal_gain(base.astype(float), add, truth)
    d0 = metric.dti_binary(base.astype(float), truth)
    d1 = metric.dti_binary((base | add).astype(float), truth)
    assert abs(r["dti_base"] - d0["dti"]) < 1e-9 and abs(r["dti_union"] - d1["dti"]) < 1e-9
    # inclusion rule: DTI rises iff dTP/dFP exceeds 0.2*DTI/(1-0.2*DTI)
    assert (r["dti_union"] > r["dti_base"]) == (r["eff"] > metric.inclusion_threshold(r["dti_base"]))


def test_known_pixels_are_masked_for_predictions_and_truth():
    truth = np.zeros((10, 10), bool)
    truth[5, 5] = True
    known = np.zeros_like(truth)
    known[5, 5] = True
    pred = np.zeros((10, 10))
    pred[5, 5] = 1.0
    r = metric.dti_binary(pred, truth, known=known)
    assert r["n_truth"] == 0 and r["FPw"] == 0
