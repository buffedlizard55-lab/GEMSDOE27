import json

import numpy as np
import pandas as pd
import pytest

from gems27 import grid, oof_detector, paths, vector_graph


def test_kinematic_compatibility_rules():
    # Compatible: identical normal slip and synthetic W dip
    assert vector_graph.is_kinematically_compatible("N", "N", "W", "W")
    assert vector_graph.is_kinematically_compatible("N", "N", "W", "NW")
    # Conjugate normal fault graben/horsts (opposite E-W dips) are compatible in Basin and Range extension
    assert vector_graph.is_kinematically_compatible("N", "N", "W", "E")
    # Unspecified dip or empty slip sense is non-conflicting
    assert vector_graph.is_kinematically_compatible("N", "", "W", "Unspecified")
    # Conflicting slip sense (right-lateral vs left-lateral, or strike-slip vs pure normal) is rejected
    assert not vector_graph.is_kinematically_compatible("RL", "LL", "W", "W")
    assert not vector_graph.is_kinematically_compatible("RL", "N", "NW", "SE")
    # Opposite dip with one strike-slip and one unspecified slip sense is rejected
    assert not vector_graph.is_kinematically_compatible("RL", "", "W", "E")


def test_ridge_nms_and_filter_isolated_dots():
    valid = np.ones((25, 25), dtype=bool)
    score = np.zeros((25, 25), dtype=np.float32)
    # Vertical ridge along column 12
    score[3:22, 11:14] = 0.5
    score[3:22, 12] = 1.0
    ridges = oof_detector.ridge_nms(score, valid, sigma=0.8)
    assert ridges[10, 12]
    assert not ridges[10, 8]

    dots = np.zeros((25, 25), dtype=bool)
    dots[5, 5] = True   # isolated
    dots[15, 15] = True  # pair within 3 px
    dots[15, 18] = True
    kept = oof_detector.filter_isolated_dots(dots, radius_px=6.0)
    assert not kept[5, 5]
    assert kept[15, 15] and kept[15, 18]


@pytest.mark.requires_rasters
def test_vector_attribution_and_evidence_files():
    """Opens the hash-pinned template/labels rasters, so it is skipped when data_cache is absent.

    This test was failing in CI on `main` before Session 3: `.github/workflows/ci.yml` never restores
    `data_cache/` (and cannot - the inputs live in sibling repositories that the CI token cannot read),
    while this test opens `paths.TEMPLATE`. Marked rather than deleted: it still runs locally and
    asserts the real 1,179-feature NBMG attribution.
    """
    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    va = vector_graph.load_vector_attribution(labels, foot)
    assert va.alignment_stats["n_vector_features"] == 1179
    assert va.alignment_stats["share_labels_within_1px_100m"] > 0.98
    assert va.alignment_stats["share_labels_within_2px_200m"] > 0.999

    sample_links = pd.DataFrame([{"e_row": 1000, "e_col": 1000, "q_row": 1010, "q_col": 1010}])
    ann = vector_graph.annotate_links(sample_links, va)
    for col in ("fid_src", "fid_tgt", "same_fid", "name_src", "name_tgt", "same_name", "kinematic_compat"):
        assert col in ann.columns

    vval = json.loads((paths.EVIDENCE / "vector_topology_validation.json").read_text())
    assert vval["gate_passed"] is True
    assert vval["tiers"]["FID_trace"]["efficiency_pooled"]["z>=3 dedup"] > 0.08

    oof = json.loads((paths.EVIDENCE / "oof_hypothesis_gates.json").read_text())
    assert oof["gate_addendum_c"]["h27_1_tv2_on_oof_passed"] is True
    assert oof["gate_addendum_c"]["h27_4_prune_100m_on_oof_passed"] is True
    assert oof["gate_addendum_c"]["h27_3_coherence_on_oof_passed"] is False
