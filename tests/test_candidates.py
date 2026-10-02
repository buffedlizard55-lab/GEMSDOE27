import numpy as np
import pandas as pd

from gems27 import candidates


def frame(**kw):
    base = dict(e_row=0, e_col=0, q_row=0, q_col=10, mutual=False, kind="abutting", ang_src=25.0, strike_compat=0.1, merged_km=20.0)
    base.update(kw)
    return pd.DataFrame([base])


def test_evidence_score_counts_the_five_criteria():
    assert candidates.evidence_score(frame())[0] == 0
    best = frame(mutual=True, kind="end-to-end", ang_src=5.0, strike_compat=0.6, merged_km=4.0)
    assert candidates.evidence_score(best)[0] == 5
    edge = frame(ang_src=15.0, strike_compat=0.4, merged_km=8.0)           # boundaries are inclusive
    assert candidates.evidence_score(edge)[0] == 3


def test_dedupe_mutual_keeps_one_of_each_pair_and_all_one_sided_links():
    a = dict(e_row=10, e_col=10, q_row=10, q_col=40, mutual=True)
    b = dict(e_row=10, e_col=40, q_row=10, q_col=10, mutual=True)
    c = dict(e_row=50, e_col=50, q_row=50, q_col=80, mutual=False)
    L = pd.DataFrame([a, b, c])
    out = candidates.dedupe_mutual(L)
    assert len(out) == 2
    assert ((out.e_row == 10) & (out.e_col == 10)).sum() == 1 and ((out.e_row == 10) & (out.e_col == 40)).sum() == 0
    assert ((out.e_row == 50)).sum() == 1


def test_dedupe_tolerates_empty_and_returns_dataframe():
    assert candidates.dedupe_mutual(pd.DataFrame(columns=["e_row", "e_col", "q_row", "q_col", "mutual"])).empty
    assert isinstance(candidates.evidence_score(frame()), np.ndarray)
