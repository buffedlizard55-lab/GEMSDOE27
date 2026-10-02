"""Topology candidate class T-v2: evidence-scored gap-closure links, ready for emission and documentation."""

from __future__ import annotations

import numpy as np
import pandas as pd

RULE = dict(cone_deg=30.0, rmin=10.0, rmax=40.0)   # frozen in knowledge/03_preregistration_topology_gate.md
SPACING = 3
Z_MIN = 3


def evidence_score(L: pd.DataFrame) -> np.ndarray:
    """z in 0..5: [mutual] + [end-to-end] + [ang_src <= 15 deg] + [strike_compat >= 0.4] + [merged_km <= 8]."""
    return (L.mutual.astype(int) + (L.kind == "end-to-end").astype(int) + (L.ang_src <= 15).astype(int)
            + (L.strike_compat >= 0.4).astype(int) + (L.merged_km <= 8).astype(int)).to_numpy()


def dedupe_mutual(L: pd.DataFrame, tol: int = 2) -> pd.DataFrame:
    """Keep one link per mutual pair (A->B and B->A describe the same straight line)."""
    if L.empty:
        return L
    L = L.reset_index(drop=True)
    drop = np.zeros(len(L), bool)
    by_tip = {}
    for i, r in enumerate(L.itertuples(index=False)):
        by_tip.setdefault((int(r.e_row), int(r.e_col)), []).append(i)
    for i, r in enumerate(L.itertuples(index=False)):
        if drop[i] or not r.mutual:
            continue
        for j in by_tip.get((int(r.q_row), int(r.q_col)), []):
            if j == i or drop[j]:
                continue
            rj = L.iloc[j]
            if abs(int(rj.q_row) - int(r.e_row)) <= tol and abs(int(rj.q_col) - int(r.e_col)) <= tol:
                # keep the link whose source tip sorts first; drop its mirror
                if (int(r.e_row), int(r.e_col)) <= (int(rj.e_row), int(rj.e_col)):
                    drop[j] = True
                else:
                    drop[i] = True
                break
    return L[~drop].reset_index(drop=True)


def _closure_effect(fg, sel: pd.DataFrame) -> dict:
    """Systems before/after closing the selected links (ascending gap order, union-find on systems)."""
    n = fg.n_components
    parent = np.arange(n + 1)
    size = fg.comp_length_px.copy() * 0.1      # km, index = component id

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    after_km, joined = [], 0
    for r in sel.sort_values("gap_km").itertuples(index=False):
        a, b = find(int(r.comp_src)), find(int(r.comp_tgt))
        if a != b:
            parent[b] = a
            size[a] += size[b] + r.gap_km
            joined += 1
        after_km.append(float(size[find(int(r.comp_src))]))
    roots = {find(i) for i in range(1, n + 1)}
    tot = np.array([size[r] for r in roots])
    before = fg.comp_length_px[1:] * 0.1
    return {"systems_before": int(n), "systems_after": int(len(roots)), "systems_joined": int(joined),
            "largest_km_before": float(before.max()), "largest_km_after": float(tot.max()),
            "top5_km_after": [float(v) for v in np.sort(tot)[::-1][:5]],
            "cluster_km_after_each_link": dict(zip(sel.sort_values("gap_km").index.tolist(), after_km))}


def build_set(labels: np.ndarray, foot: np.ndarray, base: np.ndarray, h19_raw: np.ndarray | None = None, *,
              z_min: int = Z_MIN, dedupe: bool = True, extra_z2: bool = False) -> dict:
    """Full-catalogue candidate set. `base` = the dotted base emission (links redundant with it add nothing)."""
    from scipy.ndimage import distance_transform_edt

    from . import grid, links
    from .graph import build_graph, graph_summary

    fg = build_graph(labels)
    L = links.generate_links(fg, **RULE)
    L["z"] = evidence_score(L)
    n_all = len(L)
    sel = L[L.z >= z_min].copy()
    if dedupe:
        sel = dedupe_mutual(sel)
    sel = sel.sort_values(["z", "gap_km"], ascending=[False, True]).reset_index(drop=True)
    sel.insert(0, "link_id", [f"T27-{i + 1:04d}" for i in range(len(sel))])
    d_base = distance_transform_edt(~base)
    d_raw = distance_transform_edt(~h19_raw) if h19_raw is not None else None
    shape = labels.shape
    dots_all = np.zeros(shape, bool)
    rows = []
    for r in sel.itertuples(index=False):
        one = links.rasterize_links(sel.loc[sel.link_id == r.link_id], shape, SPACING) & foot & ~labels
        dots_all |= one
        n = int(one.sum())
        rows.append({
            "dots": n,
            "dots_near_base_px3": int((one & (d_base < 3)).sum()),
            "dots_near_h19_5_raw_px3": int((one & (d_raw < 3)).sum()) if d_raw is not None else None,
        })
    ex = pd.DataFrame(rows)
    sel = pd.concat([sel, ex], axis=1)
    sel["base_overlap"] = (sel.dots_near_base_px3 / sel.dots.clip(lower=1)).round(3)
    nonred = dots_all & (d_base >= 3)
    from skimage.draw import line as sk_line

    third = []
    for r in sel.itertuples(index=False):
        rr, cc = sk_line(int(r.e_row), int(r.e_col), int(r.q_row), int(r.q_col))
        hit = False
        for y, x in list(zip(rr, cc))[3:max(len(rr) - 3, 3)]:
            ids = set(np.unique(fg.comp[max(y - 1, 0):y + 2, max(x - 1, 0):x + 2]).tolist()) - {0, int(r.comp_src), int(r.comp_tgt)}
            if ids:
                hit = True
                break
        third.append(hit)
    sel["third_system_contact"] = third
    lon0, lat0 = grid.rc_to_lonlat(sel.e_row.to_numpy(), sel.e_col.to_numpy())
    lon1, lat1 = grid.rc_to_lonlat(sel.q_row.to_numpy(), sel.q_col.to_numpy())
    sel["lon_a"], sel["lat_a"], sel["lon_b"], sel["lat_b"] = lon0, lat0, lon1, lat1
    out = {"graph": graph_summary(fg), "links_all_forward": int(n_all), "z_counts": {int(k): int(v) for k, v in
           pd.Series(L.z).value_counts().sort_index().items()}, "links": sel, "dots": dots_all, "dots_nonredundant": nonred,
           "closure": _closure_effect(fg, sel), "fg": fg}
    return out
