"""H34-1: magnetic-gravity gradient ALIGNMENT (the parallel complement of H29-XG).

Preregistered in ``knowledge/46_session21_hypothesis_screen_2026-10-31.md`` (frozen before
scoring). This is a *new operator*, not a re-run of a tested family:

* H29-XG (``crossgrad_features``, tested negative, seeds 800-809) used the CROSS-PRODUCT
  magnitude ``|∇g × ∇m| = |∇g||∇m| sin θ``, which is large when the gravity and magnetic
  horizontal gradients are PERPENDICULAR.
* A single structural discontinuity -- a fault juxtaposing units of contrasting density and
  magnetic susceptibility -- makes BOTH horizontal-gradient vectors point across the
  structure. They are therefore PARALLEL (θ ≈ 0) and collocated, where the cross product
  vanishes and the DOT PRODUCT is the informative term.

This module returns the complementary operator

    score = min(|∇M|, |∇G|) * |cos θ|,     cos θ = (∇M·∇G) / (|∇M||∇G|)

i.e. the weaker of the two edge strengths weighted by the absolute alignment. A high value
requires BOTH fields to show a strong edge AND the two edges to be parallel -- the signature
of one coincident density/susceptibility contrast rather than two independent contrasts.

Named non-fault processes that could mimic it (recorded in the run card):
parallel lithologic contacts juxtaposing contrasting density and susceptibility; basin-margin
stratigraphic contacts; airborne-survey lineation seams; remanent-magnetisation stripes.

Label-free: reads only the cached GeoDAWN bands ``rtp`` and ``iso_grav_anom``. It never reads
catalogue labels, hidden masks, catalogue distance or any prediction, so it is safe to compute
once on the full grid and reuse inside spatial folds (fold discipline lives in the detector).
Outputs are percentile-ranked within the footprint to [0, 1] float32, in row-major footprint
order, matching ``gems27.subsurface_features`` conventions.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter

from .subsurface_features import _fill, _rank01

REQUIRED_BANDS = ["rtp", "iso_grav_anom"]
ALIGN_SIGMA = 2.0  # px smoothing before differentiation (100 m cells)


def _alignment_score(mag: np.ndarray, grav: np.ndarray, foot: np.ndarray,
                     sigma: float = ALIGN_SIGMA) -> np.ndarray:
    """Full-grid alignment score in [0, ~max(min-gradient)] (not yet ranked)."""
    Ms = gaussian_filter(_fill(mag, foot), sigma=sigma)
    Gs = gaussian_filter(_fill(grav, foot), sigma=sigma)
    gyM, gxM = np.gradient(Ms)
    gyG, gxG = np.gradient(Gs)
    dot = gyM * gyG + gxM * gxG
    magM = np.hypot(gyM, gxM)
    magG = np.hypot(gyG, gxG)
    cos = dot / (magM * magG + 1e-12)
    score = np.minimum(magM, magG) * np.abs(cos)
    return np.where(foot, score, 0.0).astype(np.float32)


def build_alignment_feature(mag: np.ndarray, grav: np.ndarray, foot: np.ndarray,
                            sigma: float = ALIGN_SIGMA) -> np.ndarray:
    """Footprint-ordered percentile rank of the H34-1 alignment score (single column)."""
    foot = np.asarray(foot, bool)
    score = _alignment_score(mag, grav, foot, sigma=sigma)
    vals = score[foot]
    finite = np.isfinite(vals)
    if not finite.any():
        raise ValueError("H34-1 alignment surface has no finite footprint values")
    if not finite.all():
        vals = np.where(finite, vals, float(np.nanmedian(vals[finite])))
    return _rank01(vals).reshape(-1, 1).astype(np.float32)


def build_alignment_surface(mag: np.ndarray, grav: np.ndarray, foot: np.ndarray,
                            sigma: float = ALIGN_SIGMA) -> np.ndarray:
    """Full-grid percentile-ranked H34-1 alignment surface (zero outside the footprint)."""
    foot = np.asarray(foot, bool)
    raw = _alignment_score(mag, grav, foot, sigma=sigma)
    ranked_foot = _rank01(_sanitize(raw[foot]))
    out = np.zeros(foot.shape, dtype=np.float32)
    out[foot] = ranked_foot
    return out


def _sanitize(vals: np.ndarray) -> np.ndarray:
    v = np.asarray(vals, dtype=np.float64)
    finite = np.isfinite(v)
    if not finite.any():
        return np.zeros_like(v)
    if not finite.all():
        v = np.where(finite, v, float(np.nanmedian(v[finite])))
    return v
