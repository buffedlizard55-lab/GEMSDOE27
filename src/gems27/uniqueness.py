"""Fail-closed, exact binary-registry comparisons for pre- and post-placement screens.

Spearman is calculated over every footprint pixel, not a random sample. Rank ties are
handled using average ranks. For a binary reference, Spearman is Pearson correlation
between candidate ranks and the reference's binary indicator. Overlap is directed:
the fraction of candidate dots within Euclidean 3 pixels of at least one reference dot.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import rasterio
from scipy.spatial import cKDTree
from scipy.stats import rankdata


def sha256_file(path: Path) -> str:
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def read_reference(path: Path, template: Path, foot: np.ndarray,
                   expected_hash: str | None = None) -> np.ndarray:
    """Reject wrong grid, corrupt/missing pin, nonbinary/constant/invalid reference."""
    path = Path(path)
    if expected_hash is not None and sha256_file(path) != expected_hash:
        raise ValueError(f"reference hash mismatch: {path}")
    with rasterio.open(template) as t, rasterio.open(path) as ds:
        if (ds.crs, ds.shape, ds.transform, ds.count) != (t.crs, t.shape, t.transform, 1):
            raise ValueError(f"reference grid mismatch: {path}")
        a = ds.read(1)
    vals = a[foot]
    if not np.isfinite(vals).all() or np.any((vals != 0) & (vals != 1)):
        raise ValueError(f"reference must be finite and binary inside footprint: {path}")
    pos = (a == 1) & foot
    if not pos.any() or pos.sum() == foot.sum():
        raise ValueError(f"constant reference has undefined correlation: {path}")
    return pos


def surface_ranks(surface: np.ndarray, foot: np.ndarray) -> tuple[np.ndarray, float, float]:
    surface, foot = np.asarray(surface), np.asarray(foot, bool)
    if surface.shape != foot.shape or not foot.any():
        raise ValueError("surface and footprint mismatch or empty footprint")
    vals = surface[foot]
    if not np.isfinite(vals).all():
        raise ValueError("surface has non-finite footprint values")
    ranks = rankdata(vals, method="average")
    mean, std = float(ranks.mean()), float(ranks.std())
    if std == 0 or not np.isfinite(std):
        raise ValueError("constant surface has undefined correlation")
    return ranks, mean, std


def surface_binary_spearman(ranks: np.ndarray, mean: float, std: float,
                            reference_inside: np.ndarray) -> float:
    reference_inside = np.asarray(reference_inside, dtype=bool)
    n = len(reference_inside)
    count = int(reference_inside.sum())
    if (len(ranks) != n or count == 0 or count == n or not np.isfinite(mean)
            or not np.isfinite(std) or std <= 0 or not np.isfinite(ranks).all()):
        raise ValueError("undefined Spearman correlation")
    rho = (float(ranks[reference_inside].mean()) - mean) / std * np.sqrt(count / (n - count))
    return float(np.clip(rho, -1.0, 1.0))


def dot_comparison(candidate: np.ndarray, reference: np.ndarray, foot: np.ndarray) -> dict:
    cand = np.asarray(candidate, dtype=bool)
    ref = np.asarray(reference, dtype=bool)
    foot = np.asarray(foot, dtype=bool)
    if cand.ndim != 2 or cand.shape != ref.shape or cand.shape != foot.shape:
        raise ValueError("candidate, reference and footprint mismatch")
    cand = cand & foot
    ref = ref & foot
    n, a, b = int(foot.sum()), int(cand.sum()), int(ref.sum())
    if a == 0 or b == 0 or a == n or b == n:
        raise ValueError("constant binary raster has undefined correlation")
    both = int((cand & ref).sum())
    denom = np.sqrt(float(a) * (n - a) * b * (n - b))
    rho = float((n * both - a * b) / denom)
    distances, _ = cKDTree(np.argwhere(ref)).query(np.argwhere(cand), k=1, distance_upper_bound=3.00000001)
    overlap = float(np.mean(distances <= 3.0))
    return {"spearman": rho, "dot_overlap_within_3px": overlap,
            "candidate_dots": a, "reference_dots": b, "exact_overlap_dots": both}
