"""Deterministic geodesic Poisson-disk dot thinning of a binary emission.

Why it matters: a solid 1-px line pays ~3x the false-positive mass of a dotted line (spacing ~3 px)
while earning only ~1.3x the on-line credit under the 300 m kernel, so thinning a solid emission
raises DTI without any new geology. This is how the owner's group obtained the 0.2477 file from the
0.1922 H19-5 emission (24GEMSDOE, `dot_thin(min_dist=1.5)`).

Credit: algorithm and determinism contract follow buffedlizard55-lab/GEMSDOE24 `src/gems/thinning.py`
(re-written here; byte-identity with the sibling output is verified in tests when data are present).
Guarantees: output is a subset of the input; no labels or scores are read; seeds are the lowest raster
index of each 8-connected component; traversal is FIFO breadth-first, so runs are byte-identical.
"""

from __future__ import annotations

from collections import deque

import numpy as np
from scipy.ndimage import label


def _disc_offsets(min_dist: float, width: int) -> list[int]:
    r = int(np.ceil(min_dist))
    lim = min_dist * min_dist
    return [dy * width + dx for dy in range(-r, r + 1) for dx in range(-r, r + 1)
            if dy * dy + dx * dx < lim]


def dot_thin(mask: np.ndarray, min_dist: float) -> np.ndarray:
    """Keep a pixel iff no already-kept pixel is closer than `min_dist` (Euclidean, pixels)."""
    mask = np.asarray(mask, bool)
    if mask.ndim != 2:
        raise ValueError("2-D mask required")
    if min_dist <= 1.0 or not mask.any():
        return mask.copy()
    H, W = mask.shape
    pad = int(np.ceil(min_dist)) + 1
    Wp, Hp = W + 2 * pad, H + 2 * pad
    padded = np.zeros((Hp, Wp), bool)
    padded[pad:pad + H, pad:pad + W] = mask
    flat = bytearray(padded.tobytes())
    visited, blocked, kept = bytearray(Hp * Wp), bytearray(Hp * Wp), bytearray(Hp * Wp)
    disc = _disc_offsets(min_dist, Wp)
    nbr = (-Wp - 1, -Wp, -Wp + 1, -1, 1, Wp - 1, Wp, Wp + 1)
    comp, _ = label(padded, structure=np.ones((3, 3), int))
    fc = comp.ravel()
    order = np.flatnonzero(fc)
    _, first = np.unique(fc[order], return_index=True)
    for seed in order[np.sort(first)].tolist():
        if visited[seed]:
            continue
        visited[seed] = 1
        q = deque((seed,))
        while q:
            c = q.popleft()
            if not blocked[c]:
                kept[c] = 1
                for o in disc:
                    blocked[c + o] = 1
            for o in nbr:
                n = c + o
                if flat[n] and not visited[n]:
                    visited[n] = 1
                    q.append(n)
    out = np.frombuffer(bytes(kept), dtype=np.uint8).reshape(Hp, Wp).astype(bool)
    return out[pad:pad + H, pad:pad + W]
