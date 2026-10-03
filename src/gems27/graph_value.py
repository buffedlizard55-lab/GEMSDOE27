"""Per-link *graph-connectivity value* for gap-closure candidates.

A reviewing geologist should be able to judge a proposed gap on its structural consequence, not on a
pixel statistic. This module scores every candidate link by what it does to the fault **network**:

* `bridge`               - is this link the only connection between the two sides (a graph bridge of
                           the candidate-link graph)? Non-bridges are redundant: closing them changes
                           nothing about connectivity.
* `merge_len_km`         - length of the single mapped system the link would create
                           (len(A) + len(B) + gap), i.e. the size of the structure being asserted.
* `delta_largest_share`  - change in (largest-system length / total mapped fault length) when the link
                           is added to the full candidate set. Measures contribution to the emergence
                           of a through-going system.
* `delta_P`              - change in the Berkowitz-Bour-Davy-Odling (2000) connectivity parameter
                           P = beta * L**D * lmin**(1-a)/(a-1) integrated over the domain, computed
                           with this repo's own closed form (`topology_theory.percolation_parameter`,
                           unit-tested against the paper's numbers in `tests/test_topology_theory.py`).
                           A single merge changes the count of systems longer than `lmin` by
                           dn = [lA+lB+gap >= lmin] - [lA >= lmin] - [lB >= lmin], and P is linear in
                           that count once the exponent `a` and the correlation dimension `D` are held
                           at their fitted global values, so dn gives an exact first-order dP. Because
                           dn is an integer, dP is QUANTISED to {-1, 0, +1} x P/n_ge; it is therefore
                           an ordinal, not a fine-grained, ranking.
* `delta_second_moment_km2` - change in sum(l^2) over systems (km^2), the continuous second-moment
                           quantity that controls percolation in 2-D line networks, computed from the
                           system-length distribution with and without the link (so it is 0 for
                           non-bridges). Used as the documented tie-break inside equal |dP|.
                           NOTE: no critical value is quoted for it anywhere in this repo, because a
                           threshold could not be verified from an official source in this sandbox;
                           it is used only as a continuous relative measure. See knowledge/06.

Held constants come from `evidence/graph_report.json` (a = 2.5000 at lmin = 2 km, D = 1.5662,
P = 5.784 against the paper's Pc = 5.6-6.0) unless the caller passes others. Nothing here reads
labels hidden in a validation fold, predictions, or scores.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import topology_theory as tt
from .graph import FaultGraph

PX_KM = 0.1
PX_M = 100.0
# Fitted on the full catalogue graph (evidence/graph_report.json -> power_law_a['2km'],
# berkowitz_style_estimate, domain.equivalent_square_side_km). P is computed in METRES exactly as
# scripts/run_graph_report.py does, so it is directly comparable with the published P = 5.7845 and
# the paper's critical range Pc = 5.6-6.0.
A_FIT = 2.5000397052897463
D_FIT = 1.5662056977192493
LMIN_M = 2000.0
L_DOMAIN_M = 227318.56501394688
DOMAIN_AREA_KM2 = 51673.73       # footprint area, evidence/graph_report.json -> domain.area_km2


def merged_lengths(fg: FaultGraph, links: pd.DataFrame, drop: int | None = None) -> np.ndarray:
    """Length (metres) of every merged system after closing all links except index `drop`.

    Links are applied in ascending gap order (the same convention as `candidates._closure_effect`).
    A link contributes its gap length to a system ONLY if it actually joins two different systems at
    the moment it is applied; a redundant (non-bridge) closure adds nothing. That is what makes the
    per-link deltas 0 for non-bridges.
    """
    n = fg.n_components
    total = fg.comp_length_px.astype(float) * PX_M          # metres, index = component id
    parent = np.arange(n + 1)

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    if len(links):
        src = links.comp_src.to_numpy(int)
        tgt = links.comp_tgt.to_numpy(int)
        gap_m = (links.gap_km.to_numpy(float) * 1e3 if "gap_km" in links
                 else links.length_px.to_numpy(float) * PX_M)
        for i in np.argsort(links.length_px.to_numpy(float), kind="stable"):
            if drop is not None and int(i) == int(drop):
                continue
            a, b = find(int(src[i])), find(int(tgt[i]))
            if a == b:
                continue                                     # redundant closure: no length change
            lo, hi = (a, b) if a < b else (b, a)
            total[lo] += total[hi] + gap_m[i]
            total[hi] = 0.0
            parent[hi] = lo
    return total[total > 0]


def connectivity_P(lengths_m: np.ndarray, a: float = A_FIT, D: float = D_FIT,
                   lmin_m: float = LMIN_M, L_m: float = L_DOMAIN_M) -> float:
    """Berkowitz-style P for a set of system lengths (metres), a and D held at their fitted values."""
    n_ge = int((lengths_m >= lmin_m).sum())
    if n_ge == 0:
        return 0.0
    beta = tt.beta_from_counts(n_ge, a, lmin_m, L_m, D)
    return tt.percolation_parameter(L_m, a, D, beta, lmin_m)


def _reachable_without(adj: dict[int, set[tuple[int, int]]], u: int, v: int, blocked: int) -> bool:
    """BFS from u to v in the candidate-link graph, ignoring edge id `blocked`."""
    if u == v:
        return True
    seen = {u}
    stack = [u]
    while stack:
        x = stack.pop()
        for eid, y in adj[x]:
            if eid == blocked or y in seen:
                continue
            if y == v:
                return True
            seen.add(y)
            stack.append(y)
    return False


def link_connectivity_values(fg: FaultGraph, links: pd.DataFrame, *,
                             a: float = A_FIT, D: float = D_FIT, lmin_m: float = LMIN_M,
                             L_m: float = L_DOMAIN_M) -> pd.DataFrame:
    """Per-link network value for a set of candidate links (see module docstring)."""
    links = links.reset_index(drop=True)
    out = pd.DataFrame(index=links.index)
    out["merge_len_km"] = (fg.comp_length_px[links.comp_src.to_numpy(int)] * PX_KM
                           + fg.comp_length_px[links.comp_tgt.to_numpy(int)] * PX_KM
                           + links.length_px.to_numpy(float) * PX_KM)

    lengths_all = merged_lengths(fg, links)
    P_all = connectivity_P(lengths_all, a, D, lmin_m, L_m)
    total_km = float(lengths_all.sum())
    largest_all = float(lengths_all.max()) if len(lengths_all) else 0.0
    share_all = largest_all / total_km if total_km else 0.0

    # candidate-link graph (components as nodes, links as edges) for the bridge test
    adj: dict[int, set[tuple[int, int]]] = {}
    for eid, (s, t) in enumerate(zip(links.comp_src.to_numpy(int), links.comp_tgt.to_numpy(int))):
        adj.setdefault(int(s), set()).add((eid, int(t)))
        adj.setdefault(int(t), set()).add((eid, int(s)))

    bridges, d_share, d_P = [], [], []
    for i in range(len(links)):
        s, t = int(links.comp_src.iloc[i]), int(links.comp_tgt.iloc[i])
        bridges.append(not _reachable_without(adj, s, t, i))
        lengths_wo = merged_lengths(fg, links, drop=i)
        tot_wo = float(lengths_wo.sum())
        share_wo = float(lengths_wo.max()) / tot_wo if tot_wo else 0.0
        d_share.append(share_all - share_wo)
        d_P.append(P_all - connectivity_P(lengths_wo, a, D, lmin_m, L_m))
    out["bridge"] = np.asarray(bridges)
    out["delta_largest_share"] = np.asarray(d_share)
    out["delta_P"] = np.asarray(d_P)
    out["P_with_all_links"] = P_all
    out["largest_share_with_all_links"] = share_all

    # second-moment connectivity increment: sum l^2 over systems is the quantity that controls
    # percolation in 2-D line networks, and unlike dP (which counts systems above lmin = 2 km and is
    # therefore quantised to {-1, 0, +1} x P/n_ge) it is continuous. Computed exactly the same way as
    # dP - from the system-length distribution with and without this link - so it is 0 for non-bridges.
    sm2_all = float(((lengths_all / 1000.0) ** 2).sum())          # km^2
    d_sm2 = np.array([sm2_all - float(((merged_lengths(fg, links, drop=i) / 1000.0) ** 2).sum())
                      for i in range(len(links))])
    out["delta_second_moment_km2"] = d_sm2
    out["network_second_moment_km2"] = sm2_all
    out["second_moment_per_area"] = sm2_all / DOMAIN_AREA_KM2

    # documented rank: |dP| first (the paper's parameter), continuous second-moment increment as the
    # tie-break, then merged length. Disclosed in knowledge/03 Addendum D before Stage B was run.
    order = np.lexsort((-out.merge_len_km.to_numpy(), -np.abs(d_sm2), -out.delta_P.abs().to_numpy()))
    rank = np.empty(len(links), int)
    rank[order] = np.arange(1, len(links) + 1)
    out["connectivity_rank"] = rank
    out.attrs["P_all"] = P_all
    out.attrs["share_all"] = share_all
    out.attrs["sm2_all_km2"] = sm2_all
    return out


def graph_argument(row: pd.Series, attrs: dict | None = None) -> str:
    """One paragraph a reviewing geologist can evaluate without running anything."""
    a = attrs or {}
    bridge = ("It is a **graph bridge**: no other candidate link connects these two sides, so closing "
              "it is what actually merges them." if row.bridge else
              "It is **not** a bridge (another candidate link already joins these two sides), so its "
              "network value is redundant with that link.")
    return (
        f"Closing this {row.length_px * PX_KM:.2f} km gap joins two independently mapped systems "
        f"(NBMG FID {a.get('fid_src', '?')}/{a.get('fid_tgt', '?')}"
        f"{', zone ' + str(a.get('name')) if a.get('name') else ''}) of "
        f"{a.get('len_src_km', float('nan')):.2f} km and {a.get('len_tgt_km', float('nan')):.2f} km into a single "
        f"{row.merge_len_km:.2f} km structure, changing the network's Berkowitz connectivity parameter by "
        f"dP = {row.delta_P:+.4f} (P = {row.P_with_all_links:.3f} with all candidates, critical range "
        f"5.6-6.0) and the largest-system share of mapped fault length by "
        f"{row.delta_largest_share:+.5f}. {bridge} Strike compatibility with the local mapped strike "
        f"domain is {a.get('strike_compat', float('nan')):.2f} and slip sense is "
        f"{a.get('kinematic', 'unspecified')}."
    )
