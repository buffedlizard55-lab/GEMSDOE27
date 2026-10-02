import numpy as np

from gems27 import topology_theory as tt


def test_paper_san_andreas_numbers_reproduce_21km_order():
    # Berkowitz et al. 2000: a=2.1, D=1.65, beta=0.0085 (L in metres), Pc=5.6; paper text: L > 21 km
    lc_no_lmin = tt.critical_length(2.1, 1.65, 0.0085, lmin=1e-9) / 1e3
    lc_1km = tt.critical_length(2.1, 1.65, 0.0085, lmin=1000.0) / 1e3
    assert 20.0 < lc_no_lmin < 23.0
    assert 24.0 < lc_1km < 29.0
    assert abs(lc_no_lmin - 21.0) / 21.0 < 0.05


def test_percolation_parameter_equals_pc_at_lc():
    a, D, beta, lmin = 2.1, 1.65, 0.0085, 1000.0
    lc = tt.critical_length(a, D, beta, lmin)
    assert abs(tt.percolation_parameter(lc, a, D, beta, lmin) - tt.PC_LOW) < 1e-6


def test_power_law_mle_recovers_exponent():
    rng = np.random.default_rng(0)
    a_true, lmin = 2.4, 1.0
    x = lmin * (1 - rng.random(20000)) ** (-1.0 / (a_true - 1.0))
    fit = tt.fit_power_law_exponent(x, lmin)
    assert abs(fit["a"] - a_true) < 0.05


def test_correlation_dimension_of_uniform_points_is_two():
    rng = np.random.default_rng(1)
    pts = rng.random((4000, 2)) * 100.0
    d = tt.correlation_dimension(pts, 1.0, 10.0)
    assert 1.8 < d["D"] < 2.1


def test_single_linkage_merges_close_systems():
    rc = np.array([[0, 0], [0, 1], [0, 5], [0, 6]])
    comp = np.array([1, 1, 2, 2])
    out = tt.single_linkage_curve(rc, comp, np.array([0, 1.0, 1.0]), [2.0, 4.5])
    assert out[0]["systems"] == 2 and out[1]["systems"] == 1


def test_percolation_parameter_self_similar_limit_is_continuous():
    a, D, beta, lmin, L = 2.65, 1.65, 0.01, 1000.0, 50000.0
    p_exact = tt.percolation_parameter(L, a, D, beta, lmin)
    p_near = tt.percolation_parameter(L, a - 1e-5, D, beta, lmin)
    assert abs(p_exact - p_near) / p_exact < 1e-3
