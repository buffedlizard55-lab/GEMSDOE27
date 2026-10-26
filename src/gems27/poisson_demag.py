"""H32 (Session 11): Poisson-theorem demagnetization-residual features (label-free).

Physics: where a buried fault conduit has channelled hydrothermal fluid, magnetite is
oxidised/destroyed, so the magnetic (RTP) edge across the structure weakens or vanishes
while the density contrast (isostatic gravity edge) persists. Under Poisson's theorem a
uniformly magnetised/densified source predicts gravity from the magnetic potential; the
local regression residual of gravity on RTP therefore highlights sources whose magnetic
and density expressions disagree -- the demagnetised-conduit case that coincident-edge
features (subsurface_features.sub_crossfield_coherence = cos * min(gm_rtp, gm_grav))
actively suppress.

All transforms are deterministic functions of hash-pinned raster bands only (no labels,
no catalogue distance), percentile-ranked to [0, 1] inside the footprint, in row-major
footprint order to match `prepared/features.npy`. Preregistration:
knowledge/26_preregistration_H32_2026-10-26.md (feature list frozen before any run).

Named non-fault mimics: non-magnetic carbonate faulted against granite; reversely
magnetised Tertiary ash-flow tuffs; RTP flight-line levelling seams.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter

REQUIRED_BANDS = [
    "rtp", "tmi_hg", "tmi_vg",
    "iso_grav_anom", "iso_grav_anom_hg", "iso_grav_anom_vg",
]

TRANSFORM_NAMES = [
    "poi_resid_abs", "poi_resid_signed_pos", "poi_resid_grad_s2", "poi_resid_grad_s5",
    "poi_demag_edge", "poi_demag_vg", "poi_gravonly_coh", "poi_pseudograv_mismatch_grad",
]

LOCAL_SIGMA_PX = 15.0  # ~1.5 km local-regression window, frozen in preregistration


def _fill(grid_arr: np.ndarray, foot: np.ndarray) -> np.ndarray:
    a = grid_arr.astype(np.float32).copy()
    ok = foot & np.isfinite(a)
    bad = ~ok
    if bad.any():
        a[bad] = float(np.nanmean(a[ok])) if ok.any() else 0.0
    return a


def _rank01(vals: np.ndarray) -> np.ndarray:
    """Percentile rank in [0,1] with average ranks for ties (vectorised)."""
    v = np.asarray(vals, dtype=np.float64)
    _, inv, counts = np.unique(v, return_inverse=True, return_counts=True)
    ends = np.cumsum(counts).astype(np.float64)
    starts = ends - counts
    avg = starts + (counts - 1) / 2.0
    return (avg[inv] / max(len(v) - 1, 1)).astype(np.float32)


def _rank_grid(a: np.ndarray, foot: np.ndarray) -> np.ndarray:
    out = np.zeros(a.shape, dtype=np.float32)
    out[foot] = _rank01(a[foot])
    return out


def _grad_mag(a: np.ndarray, sigma: float) -> np.ndarray:
    s = gaussian_filter(a, sigma=sigma) if sigma > 0 else a
    gy, gx = np.gradient(s)
    return np.hypot(gy, gx).astype(np.float32)


def _local_regression_residual(grav: np.ndarray, mag: np.ndarray, sigma: float) -> np.ndarray:
    """Residual of Gaussian-weighted local linear regression grav ~ a*mag + b.

    Uses smoothed sufficient statistics; variance floor guards flat magnetic terrain
    (there the residual is just the locally-demeaned gravity, which is the honest
    "gravity structure with no magnetic explanation" signal).
    """
    w_mag = gaussian_filter(mag, sigma)
    w_grav = gaussian_filter(grav, sigma)
    cov = gaussian_filter(mag * grav, sigma) - w_mag * w_grav
    var = gaussian_filter(mag * mag, sigma) - w_mag * w_mag
    scale = float(np.nanmedian(var[var > 0])) if np.any(var > 0) else 1.0
    var_floor = max(scale * 1e-3, 1e-12)
    a = cov / np.maximum(var, var_floor)
    b = w_grav - a * w_mag
    pred = a * mag + b
    return (grav - pred).astype(np.float32)


def _structure_coherence(a: np.ndarray, sigma: float) -> np.ndarray:
    gy, gx = np.gradient(gaussian_filter(a, sigma=1.0))
    jxx = gaussian_filter(gx * gx, sigma=sigma)
    jyy = gaussian_filter(gy * gy, sigma=sigma)
    jxy = gaussian_filter(gx * gy, sigma=sigma)
    tr = jxx + jyy
    disc = np.sqrt(np.maximum((jxx - jyy) ** 2 + 4.0 * jxy**2, 0.0))
    return (disc / (tr + 1e-12)).astype(np.float32)


def build_transforms(grids: dict[str, np.ndarray], foot: np.ndarray) -> np.ndarray:
    """Return the 8 frozen H32 transforms in footprint-row order, each ranked [0,1]."""
    foot = np.asarray(foot, dtype=bool)
    missing = [n for n in REQUIRED_BANDS if n not in grids]
    if missing:
        raise ValueError(f"missing prepared bands required by H32 transforms: {missing}")
    if foot.ndim != 2 or not foot.any():
        raise ValueError("foot must be a non-empty 2-D boolean grid")
    for name in REQUIRED_BANDS:
        if np.asarray(grids[name]).shape != foot.shape:
            raise ValueError(f"prepared band {name!r} does not match footprint shape")

    cols = {n: i for i, n in enumerate(TRANSFORM_NAMES)}
    out = np.empty((int(foot.sum()), len(TRANSFORM_NAMES)), dtype=np.float32)

    def put(name: str, raw: np.ndarray) -> None:
        vals = raw[foot]
        finite = np.isfinite(vals)
        if not finite.any():
            raise ValueError(f"transform {name!r} has no finite footprint values")
        if not finite.all():
            vals = np.where(finite, vals, np.nanmedian(vals[finite]))
        out[:, cols[name]] = _rank01(vals)

    rtp = gaussian_filter(_fill(grids["rtp"], foot), 2.0)
    grav = gaussian_filter(_fill(grids["iso_grav_anom"], foot), 2.0)

    resid = _local_regression_residual(grav, rtp, LOCAL_SIGMA_PX)
    put("poi_resid_abs", np.abs(resid))
    put("poi_resid_signed_pos", np.maximum(resid, 0.0))
    put("poi_resid_grad_s2", _grad_mag(resid, 2.0))
    put("poi_resid_grad_s5", _grad_mag(resid, 5.0))
    del resid

    grav_hg_r = _rank_grid(_fill(grids["iso_grav_anom_hg"], foot), foot)
    tmi_hg_r = _rank_grid(_fill(grids["tmi_hg"], foot), foot)
    put("poi_demag_edge", np.clip(grav_hg_r - tmi_hg_r, 0.0, 1.0))

    grav_vg_r = _rank_grid(_fill(grids["iso_grav_anom_vg"], foot), foot)
    tmi_vg_r = _rank_grid(_fill(grids["tmi_vg"], foot), foot)
    put("poi_demag_vg", np.clip(grav_vg_r - tmi_vg_r, 0.0, 1.0))
    del grav_vg_r, tmi_vg_r

    coh = _structure_coherence(grav, 5.0)
    put("poi_gravonly_coh", coh * (1.0 - tmi_hg_r))
    del coh, grav_hg_r, tmi_hg_r

    mismatch = _rank_grid(grav, foot) - _rank_grid(rtp, foot)
    put("poi_pseudograv_mismatch_grad", _grad_mag(mismatch, 3.0))
    del mismatch, grav, rtp

    if not np.isfinite(out).all() or out.min() < 0.0 or out.max() > 1.0:
        raise ValueError("H32 transforms must be finite and ranked in [0,1]")
    return out
