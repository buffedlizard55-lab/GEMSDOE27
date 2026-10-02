#!/usr/bin/env python3
"""Reproduce the model arithmetic quoted in knowledge/01 (credit per dot, operating point, requirements, payoff)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import metric, paths  # noqa: E402

G = 12631.65     # sibling lattice calibration (owner-reported 0.0904 -> truth-equivalent px); UNCONFIRMED
DTI0 = 0.2477    # owner-reported


def credit(s: int) -> float:
    d = np.array([min(i % s, s - (i % s)) for i in range(s)], float)
    return float(np.mean(np.maximum(1 - d / 3, 0)))


def recall_for(dti: float, f: float) -> float:
    """Weighted recall t = TP/|G| consistent with a DTI and FP/|G| = f."""
    return dti * (0.2 * f + 0.8) / (1 - 0.2 * dti)


def main() -> int:
    out: dict = {"assumptions": {"G_px_equivalent": G, "dti_0.2477_owner_reported": DTI0, "status": "model, unconfirmed"}}
    out["credit_per_dot"] = {str(s): {"credit_per_true_px": round(credit(s), 4), "credit_per_dot": round(credit(s) * s, 4)}
                             for s in range(1, 9)}
    out["operating_point"] = {str(f): {"recall_w": round(recall_for(DTI0, f), 4), "FP_px": round(f * G), "TP_px": round(recall_for(DTI0, f) * G)}
                              for f in (3.0, 3.5, 4.3, 5.0, 6.0)}
    f0 = 4.3
    t0 = recall_for(DTI0, f0)
    t_need = 0.3195 * (0.2 * f0 + 0.8) / (1 - 0.2 * 0.3195)
    f_need = (t0 / 0.3195 - 0.2 * t0 - 0.8) / 0.2
    out["to_reach_0.3195"] = {"at_FP_over_G": f0, "recall_now": round(t0, 4), "recall_needed_same_FP": round(t_need, 4),
                              "FP_px_needed_same_recall": round(f_need * G), "FP_reduction": round(1 - f_need / f0, 4)}
    out["denominator_shares_at_0.2477"] = {"0.2TP": round(0.2 * t0 / (0.2 * t0 + 0.2 * f0 + 0.8), 3),
                                           "0.2FP": round(0.2 * f0 / (0.2 * t0 + 0.2 * f0 + 0.8), 3),
                                           "0.8G": round(0.8 / (0.2 * t0 + 0.2 * f0 + 0.8), 3)}
    out["break_even_efficiency"] = {str(d): round(metric.inclusion_threshold(d), 4) for d in (0.10, 0.1922, 0.2477, 0.25, 0.30, 0.3195)}
    TP, FP = t0 * G, f0 * G
    cand = json.loads((paths.EVIDENCE / "candidate_summary.json").read_text())
    dots = cand["nonredundant_dots_vs_0_2477"]
    dF = 0.93 * dots    # mean off-truth weight of a link dot (dot-level y ~ 0.067 in the holdout)
    base = TP / (0.2 * TP + 0.2 * FP + 0.8 * G)
    out["payoff_of_shipped_addition"] = {"nonredundant_dots": dots, "assumed_dFP_per_dot": 0.93, "base_dti_model": round(base, 4),
                                         "by_efficiency": {str(e): round((TP + e * dF) / (0.2 * (TP + e * dF) + 0.2 * (FP + dF) + 0.8 * G) - base, 4)
                                                           for e in (0.0, 0.02, 0.0526, 0.10, 0.14, 0.20, 0.28)}}
    (paths.EVIDENCE / "operating_point_model.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out["payoff_of_shipped_addition"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
