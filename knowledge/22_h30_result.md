# H30 result (Session 9, 2026-10-25): strict uniqueness is now MEASURED to cost more than the detector gain — negative verdict, unique bytes retained

**Labelling.** Detector numbers are **HOLDOUT-DTI** (`gems27.metric` v1, α=0.2 β=0.8, 300 m
triangular kernel; buffered hide-and-recover; seeds 240–244, first use). Leaderboard numbers are
**OWNER-REPORTED**. Raster facts are **MEASURED**. Evidence: `evidence/h30_holdout.json`,
`evidence/h30_run_card.json`; preregistration `knowledge/20` (frozen before E1–E3); hypothesis
screen `knowledge/21`. Budget: E1+E2+E3 = 3 experiments, then stop (protocol §6).

## E1 — leakage canary: PASS

Re-ranking multiplier M alone: AUC **0.4993**; anomaly C within coverage: **0.4861**. Both far
below the 0.90 stop line. The chemistry field carries no catalogue-internal signal (consistent
with H27-12's near-zero distance-feature result) and is bounded to ±40 % on 1.68 % of the
footprint, so it can neither leak nor move the needle much by construction.

## E2 — holdout (20 cells, 59,372 withheld positives): GATE FAIL

| arm | pooled HOLDOUT-DTI | paired vs B |
|---|---|---|
| B (full-32 control) | 0.10031 | — |
| D (+15 subsurface transforms) | 0.10234 | **+0.00217** [−0.00126, +0.00531], 15/20 cells, 5/5 seeds |
| L (H30 lane: chemistry re-rank + 65 % deconfliction cap) | 0.09608 | **−0.00445** [−0.00800, −0.00112], 7/20 cells |

Paired **L−D = −0.00662** [−0.00845, −0.00463] — far beyond the frozen −0.004 tolerance.
Every frozen gate component for L failed except canary and surface Spearman (≤0.445 vs all 12
peers). **Verdict: negative.** No post-hoc tuning; seeds 240–244 are now consumed.

### What the measurement means (the session's real deliverable)

1. **The D increment replicates in sign on a third fresh seed set** (seeds 200–204: +0.0045;
   215–224: +0.0076; 240–244: +0.0022 — 15/20, 32/40, 15/20 cells). Three disjoint seed sets,
   same sign. Arm D remains the best-evidenced detector improvement in this repo.
2. **Buying strict self-registry uniqueness costs more than the D gain.** Displacing 35 % of the
   38 k budget from halo'd top-ranked candidates to the best halo-free candidates costs
   −0.0066 HOLDOUT-DTI vs D and turns the net L−B significantly negative. IR-2026-10-25-06
   suspected this ("near-unavoidable without destroying score"); it is now a measured number.
   The D-surface's ranking is informative deep into the list — the halo-free refill dots (rank
   ≈40–90 k territory) sit well below the internal break-even.
3. **The chemistry component is exonerated by bound, not by measurement**: with 1.68 % coverage
   and a ±40 % multiplier its maximum possible effect is an order of magnitude smaller than the
   observed −0.0066; the cost is the deconfliction. (Stated as bound + canary, not as a
   demonstrated zero.)

## E3 — build: unique vs EVERY screened raster, but ⛔ NOT certified

`docs/downloads/research/gems27-h30-chem-deconf-b2-38k-20261025-ad5a68bb0535-allfinite.tif`
(sha256 `047f383d9f76…`, 826,444 B, content id `ad5a68bb0535`, 38,000 dots, conflicted fraction
exactly 0.650, B2 verified, spacing ≥2.8 px, all-finite [0,1], validator hard-PASS, independent
re-read receipt beside the bytes).

Uniqueness (directed ≤3 px Euclidean dot overlap, MEASURED):
- **vs the 12 pinned peers (operative registry): max 0.320** — PASS with margin (prior D-family
  files: 0.41–0.47).
- **vs all 12 repo-shipped rasters including H28-1, H29-1, H29-1b, L-DCONFIRM (strict
  self-registry): max 0.648** — PASS. **This is the first file in this repo's history to clear
  both screens simultaneously.**
- Surface Spearman vs peers: max 0.465 — PASS (0.90 line).

**But `ok_to_submit = false`, verdict `negative`, badge ⛔ DO NOT SUBMIT**: format and uniqueness
pass, and the efficacy gate fails (L−B is significantly negative). A file that is merely unique
and valid is not an eligible competition candidate — the same rule that gated H28-3 out.

## Consequence for the selector (the decision this measurement forces)

The uniqueness/efficacy conflict is now quantified, so the selector's screen choice IS the
strategy choice:

- **If the 12-peer parallel registry governs** (the operative reading of the current owner prompt,
  recorded in `knowledge/20` §0): the holdout-passed D-refill family (H29-1: pooled 0.1088 vs B
  0.1002, paired +0.00857 [+0.00513, +0.01249], 18/20 cells, canary 0.557, ≤46.2 % vs all 12
  peers, validator PASS) is eligible. Its badge flip is a recorded selector action that touches
  no bytes and needs no new experiment (`knowledge/16` §E3). Cross-session caveat stands: H29-1,
  H29-1b and L-DCONFIRM are one candidate family (IR-2026-10-25-09).
- **If the strict self-registry governs**: no member of the arm-D family can be both unique and
  efficacious (this session's measurement), and the H30 bytes are the unique-but-not-certified
  ceiling of that route. The next certifiable file then requires a detector whose *ridges* differ
  from every shipped raster by mechanism — the untested H28-6 standalone gravity-invariant lane
  is the cheapest such candidate, with standalone live scores historically 0.03–0.15.

Either way, beating 0.2778 (OWNER-REPORTED) live still most plausibly requires new detector
information at the B2/38 k optimum; this session's fresh-seed D−B (+0.0022) tempers the expected
margin of the D family (MODEL: live 0.26–0.29 band unchanged).

## Irregularities flagged this session

- **IR-2026-10-25-10**: H30's frozen promote gate failed on the deconfliction cost; the negative
  is retained (no cap relaxation, no seed shopping).
- **IR-2026-10-25-11**: selector decision recorded (operative screen = 12-peer registry per the
  current prompt; strict screen reported alongside); the H29-1 badge flip remains a separate,
  explicit owner action and was NOT taken here.
- Leaderboard-high conflict (0.4413 vs 0.3195) remains IR-2026-10-25-02 (unresolved).


## Post-merge addendum (recorded during the PR #24 merge, not part of frozen E1-E3)

The parallel Lane L-S7 session (PR #22) landed on `main` while this session ran. Its H29-S
hydrothermal-piedmont CELF raster (cid `511898747886`, 37,654 px) is a new repo-shipped raster and a
same-data-family neighbour (hydrothermal chemistry). **Post-merge re-screen (MEASURED):** H30 vs H29-S
directed 3-px dot overlap **0.3021** (exact shared pixels 1,812/38,000; Jaccard 0.0245) - PASS with
margin; the merged-state screen is 12 peers + 13 repo rasters and no maximum changed (peers 0.320,
repo 0.648). "First file to clear both screens" is therefore amended: H29-S cleared the 24-raster
screen first (IR-2026-10-25-13); H30 clears all 25 with larger margins vs the peers.

Cross-session numbering and instruments: this session's irregularities were renumbered
IR-2026-10-25-14/-15 (the parallel session consumed -10..-13). H30's E2 used the pre-fix `emit()`
candidate domain (`valid | hidden`, identical to H29-1/L-DCONFIRM); the parallel session's whole-fold
`emit()` fix post-dates the frozen run. All three arms (B, D, L) shared the same instrument, so the
paired deltas stand as frozen; no re-run was performed (it would be a 4th experiment against the
protocol budget). The parallel session's H29-S evidence (seeds 210-219, buffered-v2 evaluator) is NOT
numerically comparable to H30's (seeds 240-244, unbuffered pooled) - different masks, different seeds.
