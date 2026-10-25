import numpy as np
import pandas as pd
import pytest

from gems27.relay_consensus import convergent_tip_mask, summarize_convergence


def _links():
    return pd.DataFrame(
        [
            # Pair 1 and pair 2 are distinct component pairs, co-located and parallel.
            (1, 2, 10, 10, 30, 10, 0.0),
            (3, 4, 10, 12, 30, 12, 178.0),  # axial difference = 2 degrees
            # Same unordered pair as row 0: cannot corroborate row 0.
            (2, 1, 10, 11, 30, 11, 0.0),
            # Distinct pair, but too far away to support the first corridor.
            (5, 6, 10, 80, 30, 80, 1.0),
        ],
        columns=["comp_src", "comp_tgt", "e_row", "e_col", "q_row", "q_col", "strike"],
    )


def test_convergent_tip_support_requires_distinct_pair_and_corridor():
    links = _links()
    selected = convergent_tip_mask(links)
    # The third row cannot corroborate row 0 (same unordered pair), but is independently
    # corroborated by row 1 because its unordered pair is different.
    assert selected.tolist() == [True, True, True, False]
    assert summarize_convergence(links, selected) == {
        "eligible_links": 4,
        "convergent_links": 3,
        "distinct_component_pairs": 3,
    }


def test_axial_strike_and_midpoint_thresholds_are_frozen_and_strict():
    links = _links().iloc[:2].copy()
    links.loc[1, "strike"] = 160.0
    assert not convergent_tip_mask(links, strike_tolerance_deg=15.0).any()
    assert not convergent_tip_mask(links, midpoint_radius_px=1.0).any()


def test_empty_and_invalid_inputs():
    empty = _links().iloc[:0]
    assert not convergent_tip_mask(empty).any()
    with pytest.raises(ValueError, match="missing fields"):
        convergent_tip_mask(pd.DataFrame({"comp_src": [1]}))
    with pytest.raises(ValueError, match="tolerances"):
        convergent_tip_mask(_links(), midpoint_radius_px=0)
    with pytest.raises(ValueError, match="length"):
        summarize_convergence(_links(), np.zeros(2, dtype=bool))
