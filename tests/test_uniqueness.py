import numpy as np
import pytest
from scipy.stats import spearmanr

from gems27 import uniqueness


def test_exact_tied_spearman_and_directed_overlap():
    foot = np.ones((10, 12), bool)
    surface = (np.arange(120).reshape(10, 12) // 4).astype(float)
    ref = np.zeros_like(foot)
    ref[2, 3] = ref[7, 8] = True
    ranks, mean, std = uniqueness.surface_ranks(surface, foot)
    rho = uniqueness.surface_binary_spearman(ranks, mean, std, ref[foot])
    assert rho == pytest.approx(spearmanr(surface[foot], ref[foot]).statistic)
    cand = np.zeros_like(foot)
    cand[2, 6] = cand[0, 0] = True
    cmp = uniqueness.dot_comparison(cand, ref, foot)
    assert cmp["dot_overlap_within_3px"] == 0.5  # one exactly three pixels away
    assert cmp["spearman"] == pytest.approx(spearmanr(cand[foot], ref[foot]).statistic)


def test_undefined_and_nonfinite_correlations_fail_closed():
    foot = np.ones((4, 4), bool)
    with pytest.raises(ValueError, match="constant"):
        uniqueness.surface_ranks(np.ones((4, 4)), foot)
    with pytest.raises(ValueError, match="non-finite"):
        uniqueness.surface_ranks(np.full((4, 4), np.nan), foot)
    with pytest.raises(ValueError, match="constant"):
        uniqueness.dot_comparison(np.zeros((4, 4)), np.ones((4, 4)), foot)
    with pytest.raises(ValueError, match="mismatch"):
        uniqueness.dot_comparison(np.ones((4, 1)), np.ones((4, 4)), foot)
    with pytest.raises(ValueError, match="undefined"):
        uniqueness.surface_binary_spearman(np.full(16, np.nan), 1.0, 1.0, np.arange(16) == 0)
