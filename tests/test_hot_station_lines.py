"""Unit tests for the H34-1 hot-station collinearity operator (knowledge/45)."""

from __future__ import annotations

import numpy as np

from gems27 import hot_station_lines as h


def _foot(shape=(200, 200)):
    return np.ones(shape, bool)


def test_three_collinear_hot_stations_form_a_line():
    # Three hot stations 20 px apart on one horizontal line (2 km), 1-px tolerance.
    rows = np.array([50, 50, 50])
    cols = np.array([40, 60, 80])
    temps = np.array([150.0, 150.0, 150.0])
    lines = h.accepted_lines(rows, cols, temps)
    assert lines, "three collinear hot stations must form a candidate line"
    assert max(ln["support"] for ln in lines) >= 1


def test_two_stations_are_not_a_line():
    lines = h.accepted_lines(np.array([50, 50]), np.array([40, 60]), np.array([150.0, 150.0]))
    assert lines == []


def test_cold_stations_do_not_count():
    rows = np.array([50, 50, 50])
    cols = np.array([40, 60, 80])
    temps = np.array([150.0, 60.0, 150.0])  # middle station is below the 120 C hot threshold
    assert h.accepted_lines(rows, cols, temps) == []


def test_distance_band_is_enforced():
    # Pair 5 px apart (below 15 px) and a third collinear station: no pair qualifies.
    rows = np.array([50, 50, 50])
    cols = np.array([40, 45, 50])
    temps = np.array([150.0, 150.0, 150.0])
    assert h.accepted_lines(rows, cols, temps) == []


def test_off_line_station_is_not_support():
    # Middle station 10 px off the line, beyond the 3 px tolerance.
    rows = np.array([50, 60, 50])
    cols = np.array([40, 60, 80])
    temps = np.array([150.0, 150.0, 150.0])
    lines = h.accepted_lines(rows, cols, temps)
    assert all(ln["support"] == 0 for ln in lines) or lines == []


def test_surface_is_bounded_and_zero_outside_footprint():
    foot = _foot()
    rows = np.array([50, 50, 50])
    cols = np.array([40, 60, 80])
    temps = np.array([150.0, 150.0, 150.0])
    lines = h.accepted_lines(rows, cols, temps)
    S, L = h.line_surface(lines, foot)
    assert S.min() >= 0.0 and S.max() <= 1.0
    foot2 = foot.copy()
    foot2[50, 60] = False
    S2, _ = h.line_surface(lines, foot2)
    assert S2[~foot2].max() == 0.0


def test_station_qa_rejects_nonphysical_values_and_never_reads_catalogue_column(tmp_path):
    csv = tmp_path / "w.csv"
    csv.write_text(
        "layer,name,thermalclass,row,col,utm_x,utm_y,dist_known_fault_px,temp_c,geothermquartz_c,geothermchalc_c,geothermcat_c\n"
        "x,a,Hot,10,10,0,0,999.0,80,150.0,0,0\n"
        "x,b,Hot,20,20,0,0,999.0,80,-34.4,0,0\n"
        "x,c,Hot,30,30,0,0,999.0,80,,0,0\n"
    )
    st = h.station_table(csv)
    assert list(st["row"]) == [10]
    assert list(st["T"]) == [150.0]


def test_jitter_null_is_reproducible_and_counts_match_real_at_zero_radius():
    rows = np.array([50, 50, 50, 120, 120, 120])
    cols = np.array([40, 60, 80, 40, 60, 80])
    temps = np.full(6, 150.0)
    foot = _foot((200, 200))
    real = h.accepted_lines(rows, cols, temps)
    null0 = h.jitter_null_counts(rows, cols, temps, foot, radius_px=0.0, n_draws=2, seed=45)
    assert null0 == [(len(real), sum(1 for ln in real if ln["support"] >= 3))] * 2
    a = h.jitter_null_counts(rows, cols, temps, foot, radius_px=10.0, n_draws=3, seed=45)
    b = h.jitter_null_counts(rows, cols, temps, foot, radius_px=10.0, n_draws=3, seed=45)
    assert a == b
