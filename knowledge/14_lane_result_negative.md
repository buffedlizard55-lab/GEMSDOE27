# Lane L-2026-10-25 result: NEGATIVE (deliverable per protocol §5) — and one positive control

All detector numbers are **HOLDOUT-DTI** (evaluator `gems27.metric` v1, α=0.2 β=0.8, 300 m
kernel; buffered hide-and-recover, seeds 200–204 × 4 quadrants, 60,423 withheld positives).
Leaderboard numbers remain **OWNER-REPORTED**. Evidence: `evidence/lane_holdout_2026-10-25.json`,
`evidence/lane_run_card_2026-10-25.json`. Preregistration: `knowledge/13 §3` (frozen pre-run).

## Result

| arm | pooled HOLDOUT-DTI | paired vs B (mean, 95 % CI, cells +) |
|---|---|---|
| A — lane, subsurface-only | 0.0752 | **−0.0262 [−0.0368, −0.0163], 4/20** |
| B — full-32 control | 0.1001 | — |
| D — full-32 + lane transforms (control) | 0.1047 | **+0.0045 [+0.0003, +0.0090], 15/20** |
| R — random order on A's ridges | 0.0680 | A−R: +0.0096 [−0.0015, +0.0217], 10/20 |

* **Frozen gate: FAIL.** Clean promote required Δ(A−B) > 0; exploratory required > −0.01 AND
  A−R > 0.05. Neither close. → Lane TIF is generated, measured unique, format-valid, and
  badged **⛔ RESEARCH ONLY — DO NOT SUBMIT** and filed under `docs/downloads/research/` (aligned at merge with PR #11's STOP policy). No weekly slot may be spent on it.
* **Canary (E1): PASS.** All 15 transforms AUC 0.499–0.576 (no leakage; best = dilatation-rate
  gradient 0.576). Weak individually, as fault-edge physics predicts.
* **Uniqueness: PASS by mechanism.** Surface Spearman vs registry densities 0.088–0.100
  (limit 0.90); final-dot overlaps in the run card (limit 70 %). Subsurface edges really do
  decorrelate from scarp ridges — the lane is *different*, it is just not *sufficient*.
* **Interpretation (honest):** catalogue-internal truth favours lidar by construction, which
  inflates B relative to A — declared pre-run. But A also barely beats its own random-order
  control (+0.0096, CI spans 0; in the SW quadrant A's ranking is worthless), so the failure
  is not only proxy bias: at 100 m, these subsurface transforms rank hidden catalogue segments
  weakly. The buried-fault idea is NOT live-refuted (the proxy cannot see genuinely new
  faults — `knowledge/10`), but this session produced no evidence strong enough to spend a
  scarce slot on it. That is the gate working as designed.

## The positive control worth a future lane (NOT shipped here — lane discipline)

Arm D says the 15 subsurface transforms add real, significant signal **on top of** the full
stack (+0.0045 HOLDOUT-DTI, CI excludes 0). A future preregistered lane should test:
*full-32 + 15 transforms, priority Poisson-disk ≥2.8 px, B2, 38 k budget* — with its own
uniqueness measurement (its dots will sit nearer H19-5 ridges; surface Spearman here was
0.42–0.45, dot overlap unmeasured) and fresh seeds. Expected live value is unknowable from
this proxy; the family's live optimum (B2/38 k) is already priced in.

## Answer to the brief's question, updated

Can we beat 0.2778 (OWNER-REPORTED)? This session: **no promotable candidate**. The verified
path remains (i) the family's B2/38 k emission optimum (0.2778 recipe reconstructed
pixel-exactly, `knowledge/12`), and (ii) genuinely better detectors — the D-control is the
cheapest next increment, the 1 m-DEM supervised model the largest. Emission edits of the
0.2778 dots could plausibly add +0.003–0.010 (MODEL) but violate this session's uniqueness
rule and teach nothing. P(beat 0.2778) stands as estimated in `knowledge/12 §5`.
