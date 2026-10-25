"""Topology-only relay corroboration for H29-1.

A candidate link is retained only when a distinct, z-qualified link between another unordered pair of
visible fault components converges into the same short corridor. This is a hypothesis about graph
geometry, not independent fault evidence; all inputs must be built from the current split's buffered
visible-fault mask.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree


def convergent_tip_mask(
    links: pd.DataFrame,
    *,
    midpoint_radius_px: float = 5.0,
    strike_tolerance_deg: float = 15.0,
) -> np.ndarray:
    """Return a boolean mask of links with an independent convergent-link corroborator.

    Two links corroborate one another when their unordered component pairs differ, their endpoint
    pairs are not identical, their midpoints are within ``midpoint_radius_px``, and their axial
    strikes differ by no more than ``strike_tolerance_deg``. Axial strike is 180-degree periodic.
    Reciprocal/mirror links must already be removed by the caller.
    """
    if midpoint_radius_px <= 0 or not 0 <= strike_tolerance_deg <= 90:
        raise ValueError("invalid convergence tolerances")
    n = len(links)
    keep = np.zeros(n, dtype=bool)
    required = {"comp_src", "comp_tgt", "e_row", "e_col", "q_row", "q_col", "strike"}
    missing = required.difference(links.columns)
    if missing:
        raise ValueError(f"link table missing fields: {sorted(missing)}")
    if n < 2:
        return keep

    midpoints = np.column_stack(
        ((links.e_row.to_numpy(float) + links.q_row.to_numpy(float)) / 2.0,
         (links.e_col.to_numpy(float) + links.q_col.to_numpy(float)) / 2.0)
    )
    tree = cKDTree(midpoints)
    comp_a = links.comp_src.to_numpy(int)
    comp_b = links.comp_tgt.to_numpy(int)
    strike = links.strike.to_numpy(float)
    ends = links[["e_row", "e_col", "q_row", "q_col"]].to_numpy(int)

    for i, neighbors in enumerate(tree.query_ball_point(midpoints, r=midpoint_radius_px)):
        pair_i = tuple(sorted((int(comp_a[i]), int(comp_b[i]))))
        for j in neighbors:
            if j == i:
                continue
            pair_j = tuple(sorted((int(comp_a[j]), int(comp_b[j]))))
            if pair_i == pair_j or np.array_equal(ends[i], ends[j]) or np.array_equal(ends[i], ends[j][[2, 3, 0, 1]]):
                continue
            diff = abs((strike[i] - strike[j] + 90.0) % 180.0 - 90.0)
            if diff <= strike_tolerance_deg:
                keep[i] = True
                break
    return keep


def summarize_convergence(links: pd.DataFrame, selected: np.ndarray) -> dict[str, int]:
    """Small auditable counts for the pre-registered holdout record."""
    selected = np.asarray(selected, dtype=bool)
    if selected.shape != (len(links),):
        raise ValueError("selected mask length does not match links")
    return {
        "eligible_links": int(len(links)),
        "convergent_links": int(selected.sum()),
        "distinct_component_pairs": int(
            len({tuple(sorted((int(a), int(b)))) for a, b in zip(links.comp_src, links.comp_tgt)})
        ) if len(links) else 0,
    }
