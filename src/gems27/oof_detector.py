"""Strictly out-of-fold (OOF) spatial-CV fault detector for honest hypothesis gating (Addendum C).

Trains a 4-fold quadrant HistGradientBoostingClassifier on the 32-band label-free feature matrix
(`data_cache/prepared/features.npy`, which excludes the mislabelled `tc` band), with a 600 m (6 px)
spatial buffer outside each evaluation quadrant so no 300 m DTI kernel or local filter crosses the
train/test boundary. Extracts 1-px ridges via directional non-maximum suppression (`ridge_nms`).
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter
from scipy.spatial import cKDTree
from sklearn.ensemble import HistGradientBoostingClassifier

from . import grid, paths, thinning

BUFFER_PX = 6           # 600 m buffer around each test quadrant
PRE_THIN_FRAC = 0.0245  # pre-thinning ridge budget matching the H19-5 -> d1.5 operating density


def ridge_nms(score: np.ndarray, valid: np.ndarray, sigma: float = 1.0) -> np.ndarray:
    """1-px ridges of a continuous score surface via directional non-maximum suppression."""
    s = np.where(valid & np.isfinite(score), score, 0.0).astype(np.float32)
    sm = gaussian_filter(s, sigma=sigma) if sigma > 0 else s
    gy, gx = np.gradient(sm)
    theta = np.mod(np.arctan2(gy, gx), np.pi)
    # Quantise normal direction to 4 axes: E-W (0), NE-SW (1), N-S (2), NW-SE (3)
    sector = np.floor(((theta + np.pi / 8.0) % np.pi) / (np.pi / 4.0)).astype(int)
    p = np.pad(sm, 1, mode="constant", constant_values=-np.inf)
    c = p[1:-1, 1:-1]
    n_ew = (c >= p[1:-1, :-2]) & (c > p[1:-1, 2:])
    n_ns = (c >= p[:-2, 1:-1]) & (c > p[2:, 1:-1])
    n_nesw = (c >= p[:-2, 2:]) & (c > p[2:, :-2])
    n_nwse = (c >= p[:-2, :-2]) & (c > p[2:, 2:])
    ridge = (
        ((sector == 0) & n_ew)
        | ((sector == 2) & n_ns)
        | ((sector == 1) & n_nesw)
        | ((sector == 3) & n_nwse)
    )
    return ridge & valid & (sm > 0)


def fit_predict_oof_probabilities(
    foot: np.ndarray,
    labels: np.ndarray,
    fold: np.ndarray,
    *,
    neg_ratio: int = 10,
    seed: int = 2026,
    extra: np.ndarray | None = None,
    chunk: int = 400_000,
) -> np.ndarray:
    """Predict strictly out-of-fold fault probabilities across all 4 spatial quadrants.

    `extra` optionally appends further label-free bands (shape (n_footprint_px, k), footprint order,
    may be a memmap) to the 32-band prepared matrix; everything else - hyper-parameters, buffer,
    negative subsample, seeds - is identical, so arms are directly comparable (Addendum D).
    Rows are assembled and predicted in chunks: the box has 3 GB of RAM and the full augmented
    matrix would not fit resident.
    """
    X_foot = np.load(paths.PREPARED_FEATURES, mmap_mode="r")
    foot_rc = np.argwhere(foot)
    y_foot = labels[foot]
    oof_prob = np.zeros(grid.SHAPE, dtype=np.float32)

    def assemble(idx: np.ndarray) -> np.ndarray:
        base = np.asarray(X_foot[idx], dtype=np.float32)
        if extra is None:
            return base
        return np.concatenate([base, np.asarray(extra[idx], dtype=np.float32)], axis=1)

    for f in range(4):
        fm = fold == f
        d_to_fold = distance_transform_edt(~fm)
        train_grid = foot & (~fm) & (d_to_fold > BUFFER_PX)
        tr_foot = train_grid[foot]
        pos = np.flatnonzero(tr_foot & y_foot)
        neg = np.flatnonzero(tr_foot & ~y_foot)
        rng = np.random.default_rng(seed + f)
        neg_sub = rng.choice(neg, size=min(len(neg), len(pos) * neg_ratio), replace=False)
        idx = np.sort(np.r_[pos, neg_sub])

        clf = HistGradientBoostingClassifier(
            max_iter=100,
            max_leaf_nodes=31,
            learning_rate=0.08,
            l2_regularization=5.0,
            random_state=seed + f,
        )
        clf.fit(assemble(idx), y_foot[idx].astype(int))
        te_foot = np.flatnonzero(fm[foot])
        prob = np.empty(len(te_foot), np.float32)
        for a in range(0, len(te_foot), chunk):
            b = min(a + chunk, len(te_foot))
            prob[a:b] = clf.predict_proba(assemble(te_foot[a:b]))[:, 1].astype(np.float32)
        rc = foot_rc[te_foot]
        oof_prob[rc[:, 0], rc[:, 1]] = prob

    return oof_prob


def oof_pr_auc(oof_prob: np.ndarray, labels: np.ndarray, foot: np.ndarray) -> float:
    """Out-of-fold PR-AUC (average precision) against catalogue pixels, over footprint pixels."""
    from sklearn.metrics import average_precision_score
    return float(average_precision_score(labels[foot].astype(int), oof_prob[foot]))


def build_oof_dotted_base(
    oof_prob: np.ndarray,
    ridge_mask: np.ndarray,
    fold_mask: np.ndarray,
    known: np.ndarray,
    *,
    budget_frac: float = PRE_THIN_FRAC,
    thin_d: float = 1.5,
) -> np.ndarray:
    """Select top-budget OOF ridge pixels outside `known` in `fold_mask` and dot-thin them."""
    active = fold_mask & ~known
    cand = ridge_mask & active
    k = int(round(budget_frac * int(fold_mask.sum())))
    ys, xs = np.nonzero(cand)
    if len(ys) == 0 or k <= 0:
        return np.zeros_like(fold_mask, bool)
    if len(ys) > k:
        sc = oof_prob[ys, xs]
        top = np.argpartition(-sc, k - 1)[:k]
        ys, xs = ys[top], xs[top]
    raw = np.zeros_like(fold_mask, bool)
    raw[ys, xs] = True
    return thinning.dot_thin(raw, thin_d)


def filter_isolated_dots(dots: np.ndarray, radius_px: float = 6.0) -> np.ndarray:
    """Keep only dots that have at least one other dot within `radius_px` (H27-3 coherence filter)."""
    ys, xs = np.nonzero(dots)
    if len(ys) <= 1:
        return np.zeros_like(dots, bool)
    pts = np.c_[ys, xs].astype(float)
    tree = cKDTree(pts)
    d, _ = tree.query(pts, k=2, distance_upper_bound=radius_px + 1e-6)
    keep = np.isfinite(d[:, 1])
    out = np.zeros_like(dots, bool)
    out[ys[keep], xs[keep]] = True
    return out
