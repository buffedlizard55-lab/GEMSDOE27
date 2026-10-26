"""Unit tests for the H30 lane helpers (chemistry field, re-ranking, deconflicted placement)."""

from __future__ import annotations

import numpy as np
import pytest

from gems27 import hydrochemistry as hc


def _synthetic_csv(tmp_path, rows):
    import csv

    p = tmp_path / "wells.csv"
    with p.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["layer", "name", "thermalclass", "row", "col", "utm_x", "utm_y",
                    "dist_known_fault_px", "temp_c", "geothermquartz_c", "geothermchalc_c",
                    "geothermcat_c"])
        for i, (r, c, t, q) in enumerate(rows):
            w.writerow(["spring", f"s{i}", "NULL", r, c, 0.0, 0.0, 0.0, t, q, "", ""])
    return p


def test_chemistry_field_ranks_and_coverage(tmp_path):
    shape = (60, 60)
    foot = np.ones(shape, bool)
    # a cold block with ONE hot station inside it: local anomaly must peak at the hot station
    # (a homogeneous block correctly yields zero *local* contrast)
    rows = []
    for r in range(10, 16):
        for c in range(10, 16):
            rows.append((r, c, 10.0, ""))
    rows.append((12, 12, 90.0, ""))
    csv = _synthetic_csv(tmp_path, rows)
    chem = hc.build_chemistry_field(csv, shape, foot)
    assert chem["coverage"].sum() > 0
    # anomaly is ranked inside coverage only
    a = chem["anomaly"]
    assert a[~chem["coverage"]].max() == 0.0
    assert 0.0 <= a.min() and a.max() <= 1.0
    # the hot station's pixel must outrank a cold-block pixel
    assert a[12, 12] > a[10, 10]
    # geothermometer preferred over temp_c when present
    rows2 = list(rows) + [(30, 30, 5.0, 250.0)]  # quartz says hot though measured temp cold
    csv2 = _synthetic_csv(tmp_path, rows2)
    chem2 = hc.build_chemistry_field(csv2, shape, foot)
    assert chem2["anomaly"][30, 30] > chem2["anomaly"][10, 10]


def test_multiplier_bounds_and_neutrality():
    shape = (20, 20)
    cov = np.zeros(shape, bool)
    cov[5:8, 5:8] = True
    chem = {"anomaly": np.full(shape, 0.25, np.float32), "coverage": cov}
    m = hc.rank_multiplier(chem, gamma=0.4)
    assert m[~cov] == pytest.approx(1.0)
    assert m[cov].min() >= 0.6 - 1e-6
    assert m[cov].max() <= 1.4 + 1e-6
    # anomaly 0.25 -> 1 + 0.4*(2*0.25-1) = 0.8
    assert m[cov].mean() == pytest.approx(0.8, abs=1e-5)


def test_conflicted_mask_halo():
    shape = (20, 20)
    a = np.zeros(shape, np.float32)
    a[10, 10] = 1.0
    conf = hc.conflicted_mask([a], shape)
    assert conf[10, 10]
    assert conf[10, 13]  # exactly 3 px away
    assert not conf[10, 14]  # 4 px away is clean
    # union across rasters
    b = np.zeros(shape, np.float32)
    b[0, 0] = 1.0
    conf2 = hc.conflicted_mask([a, b], shape)
    assert conf2[0, 3] and conf2[10, 13]


def test_deconflicted_placement_respects_cap_and_spacing():
    shape = (80, 80)
    score = np.zeros(shape, np.float32)
    # conflicted candidates score high, clean candidates score lower
    for r in range(5, 75):
        for c in range(5, 75):
            score[r, c] = 0.9 if (r % 10 < 5) else 0.4
    conf = np.zeros(shape, bool)
    conf[:, :40] = True  # left half conflicted
    cand = np.ones(shape, bool)
    dots, info = hc.deconflicted_priority_poisson_disk(score, cand, conf, 2.8, 200, cap=0.65)
    assert info["dots_total"] == 200
    assert info["dots_conflicted"] <= int(0.65 * 200) + 1
    # spacing: no two dots within 2.8 px
    ys, xs = np.nonzero(dots)
    d2 = ((ys[:, None] - ys[None, :]) ** 2 + (xs[:, None] - xs[None, :]) ** 2).astype(float)
    np.fill_diagonal(d2, np.inf)
    assert d2.min() >= 2.8**2 - 1e-9


def test_deconflicted_fallback_when_clean_pool_tiny():
    shape = (40, 40)
    score = np.ones(shape, np.float32)
    conf = np.ones(shape, bool)  # everything conflicted
    cand = np.ones(shape, bool)
    dots, info = hc.deconflicted_priority_poisson_disk(score, cand, conf, 2.8, 50, cap=0.65)
    # clean pool is empty: disclosed fallback must still fill the budget
    assert info["dots_total"] == 50
    assert info["conflicted_fraction"] == 1.0
    assert info["shortfall_after_fallback"] == 0
