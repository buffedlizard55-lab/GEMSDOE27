# Lane L-DCONFIRM result (2026-10-25B): detector gain CONFIRMED, promotion held by the duplicate rule

All detector numbers are **HOLDOUT-DTI** (`gems27.metric` v1, α=0.2 β=0.8, 300 m kernel;
buffered hide-and-recover). Leaderboard numbers are **OWNER-REPORTED**. Evidence:
`evidence/dconfirm_holdout_2026-10-25.json`, `evidence/dconfirm_run_card_2026-10-25.json`.
Preregistration: `knowledge/15 §4` (frozen before E1–E3). Budget used: 3/3 experiments.

## E1 — leakage canary: PASS
8 new transforms, AUC 0.492–0.609 (best: `dip_depthstep_x_scarpann2_6` 0.609; radiometric
fronts 0.492–0.524). None near the 0.90 leakage line.

## E2a — selection (seeds 210–214, 20 cells, 60,423+ withheld positives class)
Pooled HOLDOUT-DTI: **B (full-32) 0.10020 · D (+15 subsurface) 0.10879 · E (+15+8 new) 0.09903**.
The 8 new dip/rad/polarity transforms *hurt* as detector augmentation (E < B < D) — a clean
negative for that sub-hypothesis; do not re-propose them in this form. Frozen rule → candidate **D**.

## E2b — confirmation (seeds 215–224, 40 cells, 121,404 withheld positives): GATE PASS
Pooled HOLDOUT-DTI **D 0.10659 vs B 0.09917**; mean paired Δ **+0.00760, 95 % CI
[+0.00489, +0.01038]**; 32/40 cells, **4/4 folds** (NW +0.0086, NE_LidarGapHeavy +0.0012,
SW +0.0021, SE +0.0186), **10/10 seeds**. This replicates Lane L-2026-10-25's arm-D control
(+0.0045 on seeds 200–204) on two disjoint fresh seed sets with a larger effect. The
subsurface-transform increment on top of the full stack is now this repo's best-evidenced
detector improvement. It remains catalogue-internal evidence: the proxy cannot price
far-field placement (knowledge/10), and D's dots sit closer to the catalogue
(median 8.9 px) than the 0.2778 file's (19.6 px) — live transfer is unproven.

## E3 — unique file generated; frozen duplicate gate: FAIL (self-registry only)
`gems27-dconfirm-hybrid-armd-b2-38k-20261025-5ea0385b7e70-allfinite.tif`
(sha256 `40b88a64…`, 38,000 dots, B2 verified min distance 2.24 px, spacing ≥2.83 px,
all-finite, validator hard-PASS, independent re-read PASS). Uniqueness (directed 3-px
Euclidean overlap): **vs the 12 pinned peer rasters of GEMSDOE24/25/27/28/30/31/32/33/36:
41.3–46.6 % — PASS** (vs 0.2778: 41.3 %); surface Spearman max 0.446 — PASS. **Vs this
repo's own H28-1 research candidate (`1113fba5f6cb`, 59,075 dots, never submitted,
already demoted audit-only): 85.2 % — FAIL** under knowledge/15 §4, which included repo
shipped candidates in the registry (Lane L precedent; the H28-3 session used peers only —
conflicting precedents now flagged in `registry/irregularities.json`).

**Verdict (frozen gates, no post-hoc edits): `negative`, `ok_to_submit=false`.** The file
lives in `docs/downloads/research/` badged ⛔. Per protocol §6, promotion is a separate
selector step: the single action that could flip the badge — without touching a byte —
is a recorded selector decision retiring the audit-only H28-1 artifact from the
self-registry (arm D is its mechanism successor: potential-field/subsurface transforms on
the full stack, now at the B2/38 k emission optimum with confirmation evidence the H28-1
file never had). Re-running only the uniqueness screen after such a decision is not a new
experiment. Until then, the honest site badge is ⛔ DO NOT SUBMIT (selector gate).

## What this means for beating 0.2778 (judgement, labelled)
D at B2/38 k is the first GEMSDOE27 file that is simultaneously (i) independently
detected (not an H19-5 edit; ≤47 % dot overlap with every scored peer file), (ii) at the
live emission optimum, and (iii) backed by a confirmed holdout gain over the strongest
in-repo control. If holdout Δ transferred at face value to the 0.2778 operating point
(it will not transfer 1:1; proxy inflation is documented), the expected live range is
roughly 0.26–0.29 — competitive with, not guaranteed above, 0.2778. The 0.4413 leader
figure (vs 0.3195 elsewhere in the prompt; unresolved) remains out of reach of this
detector class. Recommended next lanes, in order: (1) selector decision above, then one
live A/B slot for arm D — the only measurement that can price proxy→live transfer;
(2) 1 m-DEM supervised scarp detector (the known route to a step-change in recall);
(3) H28-5 chemistry corridors once official GDR bytes are hash-verified.
