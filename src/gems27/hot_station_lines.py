"""H34-1 hot-station collinearity corridors (preregistered in knowledge/45).

Label-free. Reads only station coordinates and the quartz geothermometer from the hash-pinned
INGENIOUS/GDR wellspring CSV. The catalogue-derived ``dist_known_fault_px`` column is never read.

Operator (exactly as preregistered):
  * stations: finite ``geothermquartz_c`` with 20 <= T <= 300 C, merged per (row, col) by median;
  * hot stations: T >= 120 C;
  * candidate line: a pair of hot stations 15-60 px apart (1.5-6 km at 100 m) that has at least
    one further hot station within 3 px (300 m) of the segment, inside the segment;
  * line raster: every accepted line fills the 1-px neighbourhood of its segment with weight =
    number of stations on it; L = max over lines; S = Gaussian(L, 1 px) / max, inside the footprint.

Non-fault mimics: water-well alignments along roads, field boundaries and irrigation ditches; valley-
axis regional aquifer discharge; geothermometer scatter; sampling bias (wells drilled where accessible).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter, maximum_filter
from skimage.draw import line as sk_line

MIN_T_C = 20.0
MAX_T_C = 300.0
HOT_T_C = 120.0
D_MIN_PX = 15.0  # 1.5 km at 100 m
D_MAX_PX = 60.0  # 6 km at 100 m
TOL_PX = 3.0     # 300 m perpendicular tolerance (= kernel radius)
MIN_SUPPORT = 1  # at least one extra hot station (3 in total)
LINE_HALO_PX = 1


def station_table(csv_path: Path | str) -> pd.DataFrame:
    """One row per (row, col) station with the quartz geothermometer after QA."""
    df = pd.read_csv(csv_path, low_memory=False, usecols=["row", "col", "geothermquartz_c"])
    t = pd.DataFrame({
        "row": pd.to_numeric(df["row"], errors="coerce"),
        "col": pd.to_numeric(df["col"], errors="coerce"),
        "T": pd.to_numeric(df["geothermquartz_c"], errors="coerce"),
    })
    t = t.dropna()
    t = t[(t["T"] >= MIN_T_C) & (t["T"] <= MAX_T_C)]
    t["row"] = t["row"].astype(int)
    t["col"] = t["col"].astype(int)
    return t.groupby(["row", "col"], as_index=False)["T"].median()


def accepted_lines(rows: np.ndarray, cols: np.ndarray, temps: np.ndarray) -> list[dict]:
    """Return accepted collinear hot-station lines as dicts (endpoints, support, weight)."""
    hot = np.asarray(temps) >= HOT_T_C
    P = np.column_stack([np.asarray(rows, float)[hot], np.asarray(cols, float)[hot]])
    n = len(P)
    out: list[dict] = []
    if n < 3:
        return out
    for i in range(n):
        diff = P[i + 1:] - P[i]
        dist = np.hypot(diff[:, 0], diff[:, 1])
        for off in np.flatnonzero((dist >= D_MIN_PX) & (dist <= D_MAX_PX)):
            j = i + 1 + int(off)
            d = P[j] - P[i]
            length = float(np.hypot(d[0], d[1]))
            perp = np.array([d[1], -d[0]]) / length  # unit normal, perp . d = 0
            rel = P - P[i]
            t = (rel @ d) / (length * length)
            s = np.abs(rel @ perp)
            inside = (t >= 0.0) & (t <= 1.0) & (s <= TOL_PX)
            inside[i] = False
            inside[j] = False
            support = int(inside.sum())
            if support >= MIN_SUPPORT:
                out.append({
                    "i": i, "j": j,
                    "y0": float(P[i, 0]), "x0": float(P[i, 1]),
                    "y1": float(P[j, 0]), "x1": float(P[j, 1]),
                    "support": support, "n_stations": support + 2,
                })
    return out


def line_surface(lines: list[dict], foot: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (S, L): S is the normalised surface in [0, 1] inside the footprint, L the raw weight."""
    foot = np.asarray(foot, bool)
    L = np.zeros(foot.shape, np.float32)
    H, W = foot.shape
    for ln in lines:
        rr, cc = sk_line(int(round(ln["y0"])), int(round(ln["x0"])),
                         int(round(ln["y1"])), int(round(ln["x1"])))
        ok = (rr >= 0) & (rr < H) & (cc >= 0) & (cc < W)
        rr, cc = rr[ok], cc[ok]
        w = np.float32(ln["n_stations"])
        L[rr, cc] = np.maximum(L[rr, cc], w)
    if LINE_HALO_PX > 0 and L.any():
        L = maximum_filter(L, size=2 * LINE_HALO_PX + 1)
    S = gaussian_filter(L.astype(np.float64), sigma=1.0)
    peak = float(S[foot].max()) if foot.any() else 0.0
    if peak > 0:
        S = S / peak
    S = np.where(foot, np.clip(S, 0.0, 1.0), 0.0).astype(np.float32)
    return S, L


def permuted_null_line_counts(
    n_stations: int, temps: np.ndarray, foot: np.ndarray, n_perm: int, seed: int
) -> list[int]:
    """Accepted-line counts after placing the same stations uniformly at random in the footprint."""
    rng = np.random.default_rng(seed)
    flat = np.flatnonzero(np.asarray(foot, bool).ravel())
    counts = []
    for _ in range(n_perm):
        pick = rng.choice(flat, size=n_stations, replace=False)
        rows, cols = np.divmod(pick, foot.shape[1])
        counts.append(len(accepted_lines(rows, cols, np.asarray(temps))))
    return counts


def jitter_null_counts(
    rows: np.ndarray, cols: np.ndarray, temps: np.ndarray, foot: np.ndarray,
    radius_px: float, n_draws: int, seed: int,
) -> list[tuple[int, int]]:
    """Cluster-preserving null (knowledge/45 Addendum A): displace every station uniformly inside a
    disk of ``radius_px``, keep only stations that stay in the footprint, and return
    ``(n_lines_total, n_lines_with_support_ge_3)`` per draw."""
    rng = np.random.default_rng(seed)
    foot = np.asarray(foot, bool)
    H, W = foot.shape
    rows = np.asarray(rows, float)
    cols = np.asarray(cols, float)
    temps = np.asarray(temps, float)
    out: list[tuple[int, int]] = []
    for _ in range(n_draws):
        ang = rng.uniform(0.0, 2.0 * np.pi, rows.size)
        rad = radius_px * np.sqrt(rng.uniform(0.0, 1.0, rows.size))
        r = np.rint(rows + rad * np.sin(ang)).astype(int)
        c = np.rint(cols + rad * np.cos(ang)).astype(int)
        ok = (r >= 0) & (r < H) & (c >= 0) & (c < W)
        ok[ok] &= foot[r[ok], c[ok]]
        lines = accepted_lines(r[ok], c[ok], temps[ok])
        out.append((len(lines), sum(1 for ln in lines if ln["support"] >= 3)))
    return out
