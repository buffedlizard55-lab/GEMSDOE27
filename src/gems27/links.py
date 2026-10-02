"""Gap-closure candidates ("links") between disconnected fault systems.

A link joins a free fault tip to the nearest pixel of a *different* mapped system that lies inside a
forward cone around the tip's strike. Each link carries the graph facts an expert needs to judge it:
gap length, alignment angles, type (end-to-end / abutting / en-echelon step-over), the lengths of the
two systems it would merge, mutual-nearest status, and agreement with the local strike domain of the
catalogue. Nothing here reads labels that are hidden in a validation fold or any prediction score.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from skimage.draw import line as sk_line

from .graph import FaultGraph

PX_KM = 0.1
DEFAULT = dict(cone_deg=30.0, rmin=3.0, rmax=40.0)


def _azimuth_deg(drow: np.ndarray, dcol: np.ndarray) -> np.ndarray:
    """Strike azimuth 0-180 degrees clockwise from north (rows grow southwards)."""
    return np.mod(np.degrees(np.arctan2(dcol, -drow)), 180.0)


def _angle_between(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Angle in degrees between row-wise 2-vectors (rows of a and b)."""
    na = np.linalg.norm(a, axis=1)
    nb = np.linalg.norm(b, axis=1)
    c = np.clip((a * b).sum(axis=1) / np.maximum(na * nb, 1e-12), -1.0, 1.0)
    return np.degrees(np.arccos(c))


def local_strike_domain(fg: FaultGraph, min_px: int = 10) -> tuple[cKDTree, np.ndarray, np.ndarray]:
    """Length-weighted principal-axis strike of each component >= min_px (centroid KD-tree)."""
    from scipy import ndimage as ndi

    n = fg.n_components
    ids = np.arange(1, n + 1)
    sizes = np.bincount(fg.comp[fg.skeleton], minlength=n + 1)[1:]
    sel = ids[sizes >= min_px]
    if len(sel) == 0:
        return cKDTree(np.zeros((1, 2))), np.zeros(1), np.zeros(1)
    cm = np.array(ndi.center_of_mass(fg.skeleton, fg.comp, sel))
    strikes = np.empty(len(sel))
    objs = ndi.find_objects(fg.comp)
    for i, c in enumerate(sel):
        sl = objs[c - 1]
        ys, xs = np.nonzero(fg.comp[sl] == c)
        pts = np.c_[ys, xs].astype(float)
        pts -= pts.mean(axis=0)
        w, v = np.linalg.eigh(pts.T @ pts)
        d = v[:, np.argmax(w)]
        strikes[i] = _azimuth_deg(np.array([d[0]]), np.array([d[1]]))[0]
    return cKDTree(cm), strikes, fg.comp_length_px[sel]


def strike_compat(tree: cKDTree, strikes: np.ndarray, weights: np.ndarray, rows, cols,
                  link_strike: np.ndarray, radius_px: float = 400.0, tol_deg: float = 20.0,
                  decay_px: float = 200.0) -> np.ndarray:
    """Share of nearby catalogued fault length (distance-weighted) whose strike is within tol of the link."""
    out = np.zeros(len(link_strike))
    for i, (r, c, s) in enumerate(zip(rows, cols, link_strike)):
        idx = tree.query_ball_point([r, c], radius_px)
        if not idx:
            continue
        idx = np.asarray(idx)
        d = np.hypot(tree.data[idx, 0] - r, tree.data[idx, 1] - c)
        w = weights[idx] * np.exp(-d / decay_px)
        diff = np.abs(((strikes[idx] - s) + 90.0) % 180.0 - 90.0)
        out[i] = float((w * (diff <= tol_deg)).sum() / max(w.sum(), 1e-12))
    return out


def generate_links(fg: FaultGraph, *, cone_deg: float = 30.0, rmin: float = 3.0, rmax: float = 40.0,
                   rotate_deg: float = 0.0, region: np.ndarray | None = None) -> pd.DataFrame:
    """One candidate per free tip with a tangent: the NEAREST other-system skeleton pixel inside the cone,
    accepted only if its distance lies in [rmin, rmax] (a nearer neighbour means a short gap: no link).

    `rotate_deg` rotates the cone away from the tip's strike and is used only to build control links
    (+-90 degrees) for the validation harness. `region` restricts tips to a boolean region.
    """
    ep = fg.endpoints[fg.endpoints.ty.notna()].reset_index(drop=True)
    if region is not None:
        ep = ep[region[ep.row.to_numpy(), ep.col.to_numpy()]].reset_index(drop=True)
    sk = fg.skeleton
    py, px = np.nonzero(sk)
    pc = fg.comp[py, px]
    tree = cKDTree(np.c_[py, px])
    ep_tree_rc = {(int(r), int(c)): i for i, (r, c) in enumerate(zip(fg.endpoints.row, fg.endpoints.col))}
    cos_cone = np.cos(np.deg2rad(cone_deg))
    rot = np.deg2rad(rotate_deg)
    cr, sr = np.cos(rot), np.sin(rot)
    rows = []
    for r in ep.itertuples(index=False):
        t = np.array([r.ty * cr - r.tx * sr, r.ty * sr + r.tx * cr])
        idx = np.asarray(tree.query_ball_point([r.row, r.col], rmax))
        if idx.size == 0:
            continue
        idx = idx[pc[idx] != r.comp]
        if idx.size == 0:
            continue
        d = np.c_[py[idx] - r.row, px[idx] - r.col].astype(float)
        dist = np.hypot(d[:, 0], d[:, 1])
        ok = (dist >= 1.0) & ((d @ t) / np.maximum(dist, 1e-9) >= cos_cone)
        if not ok.any():
            continue
        j = np.argmin(dist[ok])
        if dist[ok][j] < rmin:      # the NEAREST other-system pixel in the cone is closer than rmin:
            continue                # that is a short-gap case, not a rmin-rmax gap candidate
        k = idx[ok][j]
        rows.append((r.row, r.col, int(r.comp), r.ty, r.tx, int(py[k]), int(px[k]), int(pc[k]),
                     float(np.hypot(py[k] - r.row, px[k] - r.col))))
    df = pd.DataFrame(rows, columns=["e_row", "e_col", "comp_src", "ty", "tx", "q_row", "q_col",
                                     "comp_tgt", "length_px"])
    if df.empty:
        return df
    d = np.c_[df.q_row - df.e_row, df.q_col - df.e_col].astype(float)
    t = np.c_[df.ty, df.tx]
    df["ang_src"] = _angle_between(t, d)
    df["strike"] = _azimuth_deg(d[:, 0], d[:, 1])
    # target side: is the hit pixel a free tip with a tangent pointing back at us?
    tgt_ang = np.full(len(df), np.nan)
    tgt_end = np.zeros(len(df), bool)
    mutual = np.zeros(len(df), bool)
    for i, (qr, qc, er, ec) in enumerate(zip(df.q_row, df.q_col, df.e_row, df.e_col)):
        j = ep_tree_rc.get((int(qr), int(qc)))
        if j is None:
            continue
        q = fg.endpoints.iloc[j]
        if np.isnan(q.ty):
            continue
        tgt_end[i] = True
        back = np.array([[er - qr, ec - qc]], float)
        tgt_ang[i] = float(_angle_between(np.array([[q.ty, q.tx]]), back)[0])
    df["tgt_is_tip"] = tgt_end
    df["ang_tgt"] = tgt_ang
    # mutual nearest: the target tip's own best link points back within 2 px of this tip
    if tgt_end.any():
        key_src = {(int(a), int(b)): (int(c), int(e)) for a, b, c, e in
                   zip(df.e_row, df.e_col, df.q_row, df.q_col)}
        for i, (qr, qc, er, ec) in enumerate(zip(df.q_row, df.q_col, df.e_row, df.e_col)):
            back = key_src.get((int(qr), int(qc)))
            mutual[i] = bool(back and abs(back[0] - er) <= 2 and abs(back[1] - ec) <= 2)
    df["mutual"] = mutual
    df["kind"] = np.where(df.tgt_is_tip & (df.ang_tgt <= 35.0), "end-to-end",
                          np.where(df.tgt_is_tip, "tip-to-tip oblique", "abutting"))
    df["size_src_km"] = fg.comp_length_px[df.comp_src.to_numpy()] * PX_KM
    df["size_tgt_km"] = fg.comp_length_px[df.comp_tgt.to_numpy()] * PX_KM
    df["merged_km"] = df.size_src_km + df.size_tgt_km + df.length_px * PX_KM
    df["gap_km"] = df.length_px * PX_KM
    tree_s, strikes, wts = local_strike_domain(fg)
    mid_r = (df.e_row + df.q_row) / 2.0
    mid_c = (df.e_col + df.q_col) / 2.0
    df["strike_compat"] = strike_compat(tree_s, strikes, wts, mid_r.to_numpy(), mid_c.to_numpy(),
                                        df.strike.to_numpy())
    return df


def rasterize_links(df: pd.DataFrame, shape: tuple[int, int], spacing: int = 3) -> np.ndarray:
    """Dots every `spacing` px along each straight link, skipping the two pixels next to the tips."""
    m = np.zeros(shape, bool)
    for r in df.itertuples(index=False):
        rr, cc = sk_line(int(r.e_row), int(r.e_col), int(r.q_row), int(r.q_col))
        n = len(rr)
        keep = np.arange(0, n, spacing)
        keep = keep[(keep >= 1) & (keep <= n - 2)] if n > 3 else keep[:0]
        m[rr[keep], cc[keep]] = True
    return m


def link_dots(df: pd.DataFrame, shape: tuple[int, int], spacing: int = 3) -> np.ndarray:
    return rasterize_links(df, shape, spacing)
