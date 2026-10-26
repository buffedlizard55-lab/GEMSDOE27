"""Hypothesis H31-2 (Lane L-S11-2026-10-26): Poisson-relation demagnetization residuals.

Preregistered in ``knowledge/26_preregistration_H31-2_2026-10-26.md`` (frozen before seeds
410-419 ran). All transforms are deterministic functions of the hash-pinned prepared stack and
the GeoDAWN ``TMI_up150`` extension band only: no labels, no catalogue distance, no lidar band
and no band 6 (``tc``) is read, so the matrix is safe to compute once on the full grid and
reuse inside spatial folds (fold discipline lives in the stacker). Disclosed caveat, same class
as H28-1's: Gaussian windows up to sigma=20 px share label-free covariates across the 6 px
scoring buffer.

Physics: under the Poisson relation a body's gravity field is (up to a constant factor given by
the magnetisation/density ratio) the directional derivative of its magnetic potential, so where
the local gravity/magnetic scaling holds, the gravity vertical gradient is a locally linear
function of the reduced-to-pole magnetic field. Hydrothermal alteration destroys titanomagnetite
along blind upflow conduits (``knowledge/15``), erasing the magnetic expression while the
basement density step persists: the local Poisson regression then shows a positive standardised
residual (gravity signal unexplained by magnetics) at a gravity edge with shallow magnetic
quietness. Existing repo transforms reward co-located magnetic+gravity edges
(``sub_crossfield_coherence``, H31 Blakely crests) and therefore suppress exactly this class.

Named non-fault mimics: non-magnetic Paleozoic carbonate on granite, reversely magnetised
Tertiary ash-flow tuffs, and deep basement under thick basin fill (magnetic decay with depth
without any alteration).
"""

from __future__ import annotations

import gc
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, gaussian_filter, gaussian_gradient_magnitude
from sklearn.ensemble import HistGradientBoostingClassifier

from gems27 import grid, holdout, paths
from gems27.geothermal_conduit_nis import _zpos
from gems27.subsurface_features import _rank01

DEMAG_FEATURE_NAMES: tuple[str, ...] = (
    "demag_resid_abs_s8",
    "demag_resid_pos_s8",
    "demag_resid_gated_s8",
    "demag_edge_deficit",
    "demag_edge_deficit_x_gE",
    "demag_shallow_quiet_x_gE",
    "demag_resid_pos_s20",
    "demag_up150_deficit_x_gE",
)

BUFFER_PX: float = 6.0
STACKER_MAX_NEG: int = 340_000
BASE_SURFACE_NAMES: tuple[str, ...] = ("p_s2_h31", "p_s1_h31", "p_sub_h31")


def _fill_mean(grid_arr: np.ndarray, foot: np.ndarray) -> np.ndarray:
    """Footprint-mean fill outside finite footprint values (``subsurface_features._fill`` parity)."""
    a = grid_arr.astype(np.float32).copy()
    ok = foot & np.isfinite(a)
    bad = ~foot | ~np.isfinite(a)
    if bad.any():
        a[bad] = float(np.mean(a[ok])) if ok.any() else 0.0
    return a


def local_poisson_residual_z(
    rtp: np.ndarray, grav_vg: np.ndarray, sigma: float, *, clip: float = 10.0
) -> np.ndarray:
    """Standardised residual of the local Gaussian-window regression ``grav_vg ~ a*rtp + b``.

    Moments are Gaussian-weighted (``E_w[R] = G_sigma(R)`` etc.); variances get a relative
    floor of ``1e-6 * median(positive variance)`` so flat windows cannot blow up, and the
    result is clipped to ``+/-clip``. If ``grav_vg`` is an exact pointwise affine function of
    ``rtp`` the residual is identically zero (unit-tested).
    """
    r = np.asarray(rtp, dtype=np.float32)
    y = np.asarray(grav_vg, dtype=np.float32)
    if r.shape != y.shape or r.ndim != 2:
        raise ValueError("rtp and grav_vg must be equal-shaped 2-D grids")
    if not (np.isfinite(r).all() and np.isfinite(y).all()):
        raise ValueError("local_poisson_residual_z needs finite inputs (fill first)")

    def g(a: np.ndarray) -> np.ndarray:
        return gaussian_filter(a, sigma=sigma, mode="nearest")

    m_r = g(r)
    m_y = g(y)
    var_r = g(r * r) - m_r * m_r
    var_y = g(y * y) - m_y * m_y
    cov = g(r * y) - m_r * m_y

    def floored(v: np.ndarray) -> np.ndarray:
        pos = v[v > 0]
        floor = np.float32(1e-6 * float(np.median(pos))) if pos.size else np.float32(1e-12)
        return np.maximum(v, np.maximum(floor, np.float32(1e-12)))

    alpha = cov / floored(var_r)
    resid = y - (m_y + alpha * (r - m_r))
    z = resid / np.sqrt(floored(var_y))
    return np.clip(z, -clip, clip).astype(np.float32)


def _prepared_grid(
    prepared_X: np.ndarray, names: list[str], band: str, foot: np.ndarray
) -> np.ndarray:
    g = np.full(foot.shape, np.nan, dtype=np.float32)
    g[foot] = np.asarray(prepared_X[:, names.index(band)], dtype=np.float32)
    return _fill_mean(g, foot)


def build_demag_feature_matrix(
    *,
    cache_path: Path | None = None,
    force: bool = False,
    prepared_path: Path = paths.PREPARED_FEATURES,
    prepared_meta: Path = paths.PREPARED_META,
    extensions_path: Path = paths.EXTENSIONS,
    template_path: Path = paths.TEMPLATE,
) -> np.ndarray:
    """Compute or load the 8-column float32 demagnetization matrix on footprint pixels.

    Column definitions are frozen in ``knowledge/26`` section 3.
    """
    import json

    if cache_path is not None and cache_path.exists() and not force:
        arr = np.load(cache_path, mmap_mode="r")
        if arr.ndim == 2 and arr.shape[1] == len(DEMAG_FEATURE_NAMES):
            return arr

    foot = grid.load_footprint(template_path)
    names: list[str] = json.loads(Path(prepared_meta).read_text())["names"]
    x = np.load(prepared_path, mmap_mode="r")
    n_foot = int(foot.sum())

    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        out = np.lib.format.open_memmap(
            cache_path, mode="w+", dtype=np.float32, shape=(n_foot, len(DEMAG_FEATURE_NAMES))
        )
    else:
        out = np.empty((n_foot, len(DEMAG_FEATURE_NAMES)), dtype=np.float32)

    rtp = _prepared_grid(x, names, "rtp", foot)
    grav_vg = _prepared_grid(x, names, "iso_grav_anom_vg", foot)
    z8 = local_poisson_residual_z(rtp, grav_vg, sigma=8.0)
    del grav_vg
    grav = _prepared_grid(x, names, "iso_grav_anom", foot)
    g_e = _zpos(gaussian_gradient_magnitude(grav, sigma=2.0, mode="nearest"), foot)
    del grav
    m_e = _zpos(gaussian_gradient_magnitude(rtp, sigma=2.0, mode="nearest"), foot)

    out[:, 0] = np.abs(z8)[foot]
    pos8 = np.maximum(z8, np.float32(0.0))
    out[:, 1] = pos8[foot]
    out[:, 2] = (pos8 * (np.float32(0.25) + g_e))[foot]
    del pos8, z8
    deficit = np.maximum(g_e - m_e, np.float32(0.0))
    out[:, 3] = deficit[foot]
    out[:, 4] = (deficit * g_e)[foot]
    del deficit, m_e

    tmi_vg = _prepared_grid(x, names, "tmi_vg", foot)
    shallow_mag = _zpos(np.abs(gaussian_filter(tmi_vg, sigma=2.0, mode="nearest")), foot)
    del tmi_vg
    out[:, 5] = (g_e / (np.float32(1.0) + shallow_mag))[foot]
    del shallow_mag

    grav_vg = _prepared_grid(x, names, "iso_grav_anom_vg", foot)
    z20 = local_poisson_residual_z(rtp, grav_vg, sigma=20.0)
    del grav_vg, rtp
    out[:, 6] = np.maximum(z20, np.float32(0.0))[foot]
    del z20

    # Feature 7: shallow TMI weaker than its 150 m upward continuation predicts, at a gravity edge.
    tmi_rank = np.zeros(foot.shape, dtype=np.float32)
    tmi_rank[foot] = _rank01(np.asarray(x[:, names.index("tmi")], dtype=np.float64))
    with rasterio.open(extensions_path) as src:
        desc = [d or "" for d in src.descriptions]
        if "TMI_up150" not in desc:
            raise RuntimeError(f"TMI_up150 band not found in {extensions_path}: {desc}")
        up_raw = src.read(desc.index("TMI_up150") + 1).astype(np.float32)
    up_rank = np.zeros(foot.shape, dtype=np.float32)
    up_rank[foot] = _rank01(up_raw[foot].astype(np.float64))
    del up_raw
    shallow_deficit = np.maximum(up_rank - tmi_rank, np.float32(0.0))
    del tmi_rank, up_rank
    out[:, 7] = (shallow_deficit * (np.float32(0.25) + g_e))[foot]
    del shallow_deficit, g_e
    gc.collect()

    assert np.all(np.isfinite(out)), "Non-finite value produced in demagnetization matrix"
    if isinstance(out, np.memmap):
        out.flush()
        return np.load(cache_path, mmap_mode="r")
    return out


def fit_predict_stacker_oof(
    base_surfaces: tuple[np.ndarray, ...],
    extra_X: np.ndarray | None,
    labels: np.ndarray,
    foot: np.ndarray,
    *,
    seed: int = 410,
    buffer_px: float = BUFFER_PX,
    max_neg: int = STACKER_MAX_NEG,
) -> np.ndarray:
    """Quadrant-OOF gradient-boosting stacker over honest OOF H31 surfaces (+ optional extras).

    ``base_surfaces`` are full-grid probability surfaces that are themselves out-of-fold at
    quadrant level (H31 ``p_s2, p_s1, p_sub``). For fold ``f`` the stacker trains only on
    pixels outside fold ``f`` and more than ``buffer_px`` from it, then predicts fold ``f``;
    every returned pixel is therefore out-of-fold for both the base detector and the stacker.
    Hyperparameters match the H31 stage-2 refiner (frozen in ``knowledge/26`` section 2).
    """
    if not base_surfaces:
        raise ValueError("at least one base surface is required")
    for s in base_surfaces:
        if np.asarray(s).shape != foot.shape:
            raise ValueError("base surface shape does not match footprint")
    if extra_X is not None and np.asarray(extra_X).shape[0] != int(foot.sum()):
        raise ValueError("extra_X must have one row per footprint pixel")

    fold = holdout.make_quadrant_folds(foot)
    y_foot = np.asarray(labels, bool)[foot]
    n_base = len(base_surfaces)
    surf_foot = [np.asarray(s, dtype=np.float32)[foot] for s in base_surfaces]
    out_foot = np.zeros(int(foot.sum()), dtype=np.float32)

    def assemble(idx: np.ndarray) -> np.ndarray:
        cols = n_base + (0 if extra_X is None else int(np.asarray(extra_X).shape[1]))
        m = np.empty((idx.size, cols), dtype=np.float32)
        for j, sf in enumerate(surf_foot):
            m[:, j] = sf[idx]
        if extra_X is not None:
            m[:, n_base:] = np.asarray(extra_X)[idx]
        return m

    for f in range(4):
        test_mask = foot & (fold == f)
        guard = distance_transform_edt(~test_mask) > buffer_px
        train_grid = foot & (~test_mask) & guard
        tr_foot = train_grid[foot]
        pos_idx = np.flatnonzero(tr_foot & y_foot)
        neg_all = np.flatnonzero(tr_foot & (~y_foot))
        rng = np.random.default_rng(seed * 100 + f)
        neg_idx = (
            np.sort(rng.choice(neg_all, size=max_neg, replace=False))
            if neg_all.size > max_neg
            else neg_all
        )
        tr_idx = np.concatenate([pos_idx, neg_idx])
        y_tr = np.r_[np.ones(pos_idx.size, dtype=np.int8), np.zeros(neg_idx.size, dtype=np.int8)]
        clf = HistGradientBoostingClassifier(
            max_iter=150,
            learning_rate=0.05,
            max_leaf_nodes=31,
            min_samples_leaf=120,
            l2_regularization=4.0,
            random_state=seed + f,
        )
        clf.fit(assemble(tr_idx), y_tr)
        del tr_idx, y_tr, pos_idx, neg_idx, neg_all, tr_foot
        te_idx = np.flatnonzero(test_mask[foot])
        for s0 in range(0, te_idx.size, 200_000):
            sl = te_idx[s0 : s0 + 200_000]
            out_foot[sl] = clf.predict_proba(assemble(sl))[:, 1].astype(np.float32)
        del clf, te_idx, test_mask, guard, train_grid
        gc.collect()
        print(f"    stacker fold {f} done", flush=True)

    out = np.zeros(foot.shape, dtype=np.float32)
    out[foot] = np.clip(out_foot, 0.0, 1.0)
    return out
