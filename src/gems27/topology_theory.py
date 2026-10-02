"""Connectivity scaling of a fault trace map after Berkowitz, Bour, Davy & Odling (GRL 27(14), 2000).

What the paper says (abstract + text, read 2026-10-02 from the Wiley abstract and the full text copy;
doi:10.1029/1999GL011241):
  * trace-length density  n(l, L) dl = beta L^D l^-a dl, with D the fractal dimension of fracture centres
    (two-point correlation integral C2(r) ~ r^D) and beta ~ constant;
  * connectivity behaviour depends on the scale of measurement for a < D+1 and is independent of scale for
    a > D+1; the percolation parameter P(L) is their eq. (1); the connectivity threshold is Pc ~ 5.6-6.0;
  * San Andreas example: a = 2.1, D = 1.65, beta = 0.0085 (L in metres), so a < D+1 and connectivity is
    reached only at a critical length scale (paper: L > 21 km for lmin ~ 1 km; sensitivity 10 < Lc < 50 km);
  * "the above results are statistical, and provide connectivity estimates on averages, rather than on
    particular realizations".

What this module adds (ours, not the paper's): the closed form of Lc below is *our re-derivation* from eq. (1)
(integrating the two terms for 1 < a, lmax >> L); with the paper's San Andreas numbers it gives 21.6 km
(lmin -> 0) or 26.7 km (lmin = 1 km), i.e. the paper's "21 km" within ~25 %. The paper does not claim that a
single mapped segment decides whether two particular faults are joined; that is a per-realization statement,
which the empirical single-linkage curve here can examine for the actual catalogue.
"""

from __future__ import annotations

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

PC_LOW, PC_HIGH = 5.6, 6.0


def fit_power_law_exponent(lengths: np.ndarray, lmin: float) -> dict:
    """Continuous MLE of the density exponent a for l >= lmin (Clauset, Shalizi & Newman 2009)."""
    x = np.asarray(lengths, float)
    x = x[x >= lmin]
    n = len(x)
    if n < 10:
        return {"a": float("nan"), "se": float("nan"), "n": n, "lmin": lmin, "ks": float("nan")}
    a = 1.0 + n / float(np.log(x / lmin).sum())
    se = (a - 1.0) / np.sqrt(n)
    xs = np.sort(x)
    cdf_emp = np.arange(1, n + 1) / n
    cdf_fit = 1.0 - (xs / lmin) ** (1.0 - a)
    ks = float(np.max(np.abs(cdf_emp - cdf_fit)))
    return {"a": float(a), "se": float(se), "n": n, "lmin": float(lmin), "ks": ks}


def correlation_dimension(points_xy: np.ndarray, r_lo: float, r_hi: float, n_r: int = 14) -> dict:
    """D from C2(r) = 2 Np(r) / N^2 ~ r^D over [r_lo, r_hi] (same units as points)."""
    pts = np.asarray(points_xy, float)
    n = len(pts)
    tree = cKDTree(pts)
    rs = np.geomspace(r_lo, r_hi, n_r)
    c2 = np.array([2.0 * len(tree.query_pairs(r)) / (n * n) for r in rs])
    ok = c2 > 0
    slope, intercept = np.polyfit(np.log(rs[ok]), np.log(c2[ok]), 1)
    resid = np.log(c2[ok]) - (slope * np.log(rs[ok]) + intercept)
    r2 = 1.0 - float((resid ** 2).sum() / ((np.log(c2[ok]) - np.log(c2[ok]).mean()) ** 2).sum())
    return {"D": float(slope), "r2": r2, "r_lo": float(r_lo), "r_hi": float(r_hi), "n": n,
            "r": rs.tolist(), "c2": c2.tolist()}


def beta_from_counts(n_ge_lmin: int, a: float, lmin: float, L: float, D: float) -> float:
    """beta such that  N(l >= lmin) = beta L^D lmin^(1-a)/(a-1)   (lmax -> infinity)."""
    return n_ge_lmin * (a - 1.0) * lmin ** (a - 1.0) / (L ** D)


def percolation_parameter(L: float, a: float, D: float, beta: float, lmin: float) -> float:
    """Paper eq. (1) integrated for lmax >> L (our integration).

    P = beta [ D L^(D+1-a) / ((D+1-a)(a-1)) - lmin^(D+1-a)/(D+1-a) ]   for a != D+1,
    P = beta [ ln(L/lmin) + 1/D ]                                       for a == D+1.
    """
    e = D + 1.0 - a
    if abs(e) < 1e-9:
        return float(beta * (np.log(L / lmin) + 1.0 / D))
    return float(beta * (D * L ** e / (e * (a - 1.0)) - lmin ** e / e))


def critical_length(a: float, D: float, beta: float, lmin: float, pc: float = PC_LOW) -> float:
    """Our closed form of the paper's L_c for 1 < a < D+1 (lmax >> L). Returns metres if inputs are metres."""
    e = D + 1.0 - a
    if e <= 0 or a <= 1:
        return float("nan")
    inner = e * (a - 1.0) * pc / (D * beta) + lmin ** e * (a - 1.0) / D
    return float(inner ** (1.0 / e))


def single_linkage_curve(skel_rc: np.ndarray, comp_ids: np.ndarray, comp_len_km: np.ndarray,
                         radii_px: list[float]) -> list[dict]:
    """Systems left after merging every pair of skeleton pixels closer than r (cross-system only)."""
    n_comp = int(comp_ids.max())
    tree = cKDTree(skel_rc)
    out = []
    for r in radii_px:
        pairs = tree.query_pairs(r, output_type="ndarray")
        ca, cb = comp_ids[pairs[:, 0]] - 1, comp_ids[pairs[:, 1]] - 1
        m = ca != cb
        if m.any():
            g = coo_matrix((np.ones(m.sum()), (ca[m], cb[m])), shape=(n_comp, n_comp))
            k, lab = connected_components(g, directed=False)
        else:
            k, lab = n_comp, np.arange(n_comp)
        tot = np.bincount(lab, weights=comp_len_km[1:], minlength=k)
        order = np.sort(tot)[::-1]
        out.append({"radius_px": float(r), "radius_km": float(r) * 0.1, "systems": int(k),
                    "largest_km": float(order[0]), "largest_share": float(order[0] / tot.sum()),
                    "top3_km": [float(v) for v in order[:3]],
                    "systems_ge_50km": int((tot >= 50).sum())})
    return out
