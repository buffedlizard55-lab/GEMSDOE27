from __future__ import annotations

import numpy as np
import pytest

from gems27 import geothermal_conduit_nis as h31
from gems27 import mt_graben


def test_sample_along_normal_obeys_signed_direction():
    field = np.tile(np.arange(9, dtype=np.float32), (7, 1))
    urow = np.zeros_like(field)
    ucol = np.ones_like(field)
    plus = mt_graben.sample_along_normal(field, urow, ucol, 2.0, direction=1.0)
    minus = mt_graben.sample_along_normal(field, urow, ucol, 2.0, direction=-1.0)
    assert plus[3, 4] == pytest.approx(6.0)
    assert minus[3, 4] == pytest.approx(2.0)
    # nearest edge behavior is deliberate; it does not extrapolate a false anomaly.
    assert plus[3, -1] == pytest.approx(8.0)


def test_mt_graben_transforms_are_deterministic_finite_and_bounded():
    rows, cols = np.mgrid[:48, :64]
    foot = np.ones((48, 64), dtype=bool)
    # Deepening eastward, conductivity that rises farther east, and a separate gravity margin.
    depth = cols.astype(np.float32) + 0.03 * rows
    cond = np.maximum(0.0, cols - 24).astype(np.float32) ** 2
    grav = np.where(cols > 31, 10.0, 0.0).astype(np.float32)
    ext = np.where((cols > 27) & (cols < 38), 2.0, 0.0).astype(np.float32)
    grids = {
        "cond_surf": cond,
        "depth_to_base_surf": depth,
        "iso_grav_anom": grav,
        "geod_dilaterate": ext,
    }
    a = mt_graben.build_transforms(grids, foot)
    b = mt_graben.build_transforms(grids, foot)
    assert a.shape == (foot.sum(), len(mt_graben.TRANSFORM_NAMES))
    assert np.array_equal(a, b)
    assert np.isfinite(a).all()
    assert 0.0 <= a.min() <= a.max() <= 1.0
    # The east/deeper-side column must not collapse to a constant on an asymmetric synthetic field.
    assert np.unique(a[:, 4]).size > 10


def test_h31_expert_assembly_appends_shared_physics_without_changing_core_layout():
    n = 5
    idx = np.array([1, 4], dtype=np.int64)
    base = np.arange(n * 32, dtype=np.float32).reshape(n, 32)
    sub = np.arange(n * 15, dtype=np.float32).reshape(n, 15)
    h29 = np.arange(n * 20, dtype=np.float32).reshape(n, 20)
    h31_base = np.arange(n * 12, dtype=np.float32).reshape(n, 12)
    physics = np.full((n, 3), 77.0, dtype=np.float32)
    s2 = np.full((idx.size, 2), 88.0, dtype=np.float32)

    full_core = h31._assemble_expert_rows(idx, base, sub, h29, h31_base, mode="full")
    full_extra = h31._assemble_expert_rows(
        idx, base, sub, h29, h31_base, mode="full", extra_physics=physics, extra_s2=s2
    )
    assert full_core.shape == (2, 79)
    assert full_extra.shape == (2, 84)
    assert np.array_equal(full_extra[:, :79], full_core)
    assert np.array_equal(full_extra[:, 79:82], physics[idx])
    assert np.array_equal(full_extra[:, 82:], s2)

    sub_extra = h31._assemble_expert_rows(
        idx, base, sub, h29, h31_base, mode="sub", extra_physics=physics
    )
    assert sub_extra.shape == (2, 63)
    assert np.array_equal(sub_extra[:, 60:], physics[idx])
