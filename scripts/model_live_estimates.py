#!/usr/bin/env python3
"""MODEL (not-a-score) live estimates for unscored files, per knowledge/26 section 5.

Every live number consumed here is OWNER-REPORTED; every number produced is labelled MODEL with
its formula and inputs, so a projection is never written as a score (Parallel-Run Protocol 3).
Method (preregistered): within-detector-family anchoring on H29-S (live 0.2190 OWNER-REPORTED,
same 37,654-dot B2 operating point). Cross-family anchoring is forbidden: H29-S was holdout-best
in its session yet scored 0.2190 live against the H19-5 family's 0.2778, which proves holdout<->live
calibration does not transfer across detector classes. JSON-in / JSON-out; no rasters are read.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gems27 import paths

ALPHA, BETA = 0.2, 0.8
G_REF, RHO_REF = 12_226.0, 1.38
N_OP = 37_654
H29S_LIVE = 0.2190
CHAMPION_LIVE = 0.2778


def invert_tpw(n_dots: float, dti_live: float) -> float:
    """Invert DTI = TPw / (TPw + a*(N - rho*TPw) + b*(|G| - TPw)) (build_focus_sites_summary)."""
    denom_coeff = (1.0 - ALPHA * RHO_REF - BETA) * dti_live
    rhs = dti_live * (ALPHA * float(n_dots) + BETA * G_REF)
    return rhs / (1.0 - denom_coeff)


def forward_dti(n_dots: float, tpw: float) -> float:
    return tpw / (tpw + ALPHA * (n_dots - RHO_REF * tpw) + BETA * (G_REF - tpw))


def model_block(name: str, live_anchor: float, buf_ratio: float, unbuf_ratio: float) -> dict:
    central = live_anchor * buf_ratio
    opt = live_anchor * max(buf_ratio, unbuf_ratio)
    tpw_anchor = invert_tpw(N_OP, live_anchor)
    algebra_check = forward_dti(N_OP, tpw_anchor * buf_ratio)
    return {
        "file_label": name,
        "label": "MODEL (projection from stated formula; NOT a leaderboard score)",
        "anchor_live_owner_reported": live_anchor,
        "holdout_buffered_ratio_vs_anchor_arm": round(buf_ratio, 5),
        "holdout_unbuffered_ratio_vs_anchor_arm": round(unbuf_ratio, 5),
        "model_no_transfer": round(live_anchor, 4),
        "model_proportional_central": round(central, 4),
        "model_interval": [round(live_anchor, 4), round(opt, 4)],
        "model_algebra_crosscheck_tpw_scaled": round(algebra_check, 4),
        "formula": "central = anchor_live * (pooled buffered HOLDOUT-DTI ratio, same seeds/instrument)",
    }


def main() -> int:
    e2_s10 = json.loads((paths.EVIDENCE / "h31_s10_e2_holdout_400_409.json").read_text())
    buf = e2_s10["pooled_buffered_holdout_dti"]
    unb = e2_s10["pooled_unbuffered_diagnostic_holdout_dti"]
    h31_buf_ratio = buf["H31-S"] / buf["H29-S"]
    h31_unb_ratio = unb["H31-S"] / unb["H29-S"]

    tpw_h29s = invert_tpw(N_OP, H29S_LIVE)
    tpw_champ = invert_tpw(N_OP, CHAMPION_LIVE)
    rows = [
        model_block(
            "gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif (H31-1, UNSCORED)",
            H29S_LIVE, h31_buf_ratio, h31_unb_ratio,
        )
    ]
    rows[0].update({
        "anchor_arm": "H29-S on seeds 400-409 (same instrument)",
        "anchor_holdout_buffered": buf["H29-S"],
        "candidate_holdout_buffered": buf["H31-S"],
        "candidate_holdout_label": (
            f"HOLDOUT-DTI ({e2_s10['evaluator_version']}; "
            f"{e2_s10['n_withheld_positive_occurrences']} withheld positive occurrences)"
        ),
    })

    e2_s11_path = paths.EVIDENCE / "h31_2_e2_holdout_410_419.json"
    chained_note = None
    if e2_s11_path.exists():
        e2_s11 = json.loads(e2_s11_path.read_text())
        b11 = e2_s11["pooled_buffered_holdout_dti"]
        u11 = e2_s11["pooled_unbuffered_diagnostic_holdout_dti"]
        chain_buf = h31_buf_ratio * (b11["DEMAG"] / b11["H31S"])
        chain_unb = h31_unb_ratio * (u11["DEMAG"] / u11["H31S"])
        row = model_block(
            "H31-2 DEMAG candidate (UNSCORED; file name in evidence/h31_2_run_card.json)",
            H29S_LIVE, chain_buf, chain_unb,
        )
        row.update({
            "anchor_arm": "chained: H29-S (400-409) x H31S-arm (410-419); extra uncertainty",
            "anchor_holdout_buffered": buf["H29-S"],
            "candidate_holdout_buffered": b11["DEMAG"],
            "candidate_holdout_label": (
                f"HOLDOUT-DTI ({e2_s11['evaluator_version']}; "
                f"{e2_s11['n_withheld_positive_occurrences']} withheld positive occurrences)"
            ),
            "gate_e2_pass": e2_s11["gate_e2_pass"],
        })
        rows.append(row)
        chained_note = (
            "H31-2 row chains two same-instrument ratios across disjoint seed sets; treat its "
            "interval as optimistic-narrow and its no-transfer bound (0.2190) as the floor."
        )

    required_ratio = tpw_champ / tpw_h29s
    out = {
        "generated_utc": "2026-10-26",
        "purpose": "Executive-summary MODEL estimates for UNSCORED files (knowledge/26 section 5)",
        "provenance_rule": (
            "Live inputs are OWNER-REPORTED; outputs are MODEL projections, never scores. "
            "No ORGANIZER-CONFIRMED receipt exists in this repo."
        ),
        "constants": {"G_ref": G_REF, "rho_ref": RHO_REF, "alpha": ALPHA, "beta": BETA,
                      "operating_point_dots": N_OP},
        "beat_champion_arithmetic": {
            "champion": "GEMSDOE32 h33-h33-2-b2 = 0.2778 OWNER-REPORTED (already submitted)",
            "implied_tpw_h29s_at_0p2190": round(tpw_h29s, 1),
            "implied_credit_fraction_h29s": round(tpw_h29s / G_REF, 4),
            "required_tpw_for_0p2778_same_N": round(tpw_champ, 1),
            "required_credit_fraction_for_0p2778": round(tpw_champ / G_REF, 4),
            "required_tpw_ratio_vs_h29s": round(required_ratio, 4),
            "reading": (
                "Beating 0.2778 at the same 37,654-dot budget needs ~+26% more weighted credit "
                "than H29-S achieved live. A candidate whose same-instrument HOLDOUT-DTI ratio "
                "vs its H29-S anchor arm is below the required TPw ratio is MODEL-unlikely to "
                "beat 0.2778, however clean its holdout gate is."
            ),
        },
        "estimates": rows,
        "chaining_note": chained_note,
        "validation_of_method": (
            "The inversion constants reproduce the focus-site autopsy "
            "(evidence/focus_sites_executive_summary_20261026.json: H29-S credit fraction 0.305). "
            "The proportional-transfer assumption itself is unvalidated on live data (only one "
            "family member, H29-S, has both a same-instrument holdout and a live score); that is "
            "why the no-transfer bound is always reported alongside the central value."
        ),
    }
    dest = paths.EVIDENCE / "model_live_estimates_2026-10-26.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    for r in rows:
        print(f"MODEL {r['file_label']}: central={r['model_proportional_central']} "
              f"interval={r['model_interval']} algebra={r['model_algebra_crosscheck_tpw_scaled']}")
    print(f"required TPw ratio vs H29-S for 0.2778: {required_ratio:.3f} | wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
