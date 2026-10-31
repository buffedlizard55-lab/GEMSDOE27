# Session 21 (2026-10-31) — E3 build of the confirmed L-DCONFIRM arm D, and why this lane

Labelling (AGENTS.md §evidence): every number here is **HOLDOUT-DTI** (local evaluator), **OWNER-REPORTED**
(from the task prompt / sibling GitHub pages), or **MODEL** (calibrated arithmetic). Nothing is
ORGANIZER-CONFIRMED. No DrivenData access, no upload, no slot selection happens in this session.

## 0. Lane assignment note (irregularity carried forward)

The parallel-run prompt again contains "Your lane is the single method paragraph below" with no
paragraph (`IR-2026-10-31-lane-paragraph-still-missing`). Prior sessions refused to run any
experiment under that omission. This session instead executes only the **already-preregistered,
already-confirmed E3 build step** of Lane L-DCONFIRM (`knowledge/15`, §4): no new hypothesis, no
new gate, no new seeds, no parameter changes. The confirmation gate was frozen and passed on its
own consumed seeds (selection 210–214, confirmation 215–224) before this session existed. Building
the artifact from a recorded passing confirmation is template work (Protocol §2, REUSE), not a new
experiment, so it does not require a lane paragraph.

## 1. Why this is the highest-value candidate available today (PhD-level judgement, evidence-linked)

The nine focus sites' owner-reported scores (2026-10-31 prompt list; `registry/owner_reported_scores_20261030.csv`)
form one clear family and one clear gap:

1. **One dot field, re-thinned (MEASURED, `evidence/peer_relations_20261028.json`, `knowledge/12`).**
   GEMSDOE25/30 d2.8 (0.2600, 44,090 dots) minus a 1 px catalogue collar = GEMSDOE28/31 H27-4
   (0.2708, 40,199); minus a 2 px collar = GEMSDOE32 H33-2-B2 (0.2778, 37,654). GEMSDOE36
   (0.2750) is the same 37,654 dots +1,200. Dose-response consistent with the metric's masking
   asymmetry; not a receipt, and not beatable by editing that field (any edit keeps >70 % of its
   dots within 3 px of a pinned peer = duplicate stop, `knowledge/44` §5).
2. **The gap to the leader cannot be bought by re-thinning (MODEL, `knowledge/12` §5).**
   The prompt's leaderboard highs (0.4413 / 0.3195 / #1 0.4544 read 2026-10-30) imply credit
   density ~25–60 % above the family plateau. Every emission-surgery estimate in this repo
   (+0.005–0.025 MODEL) stays below 0.30. A better *detector* is required, and the only
   detector architecture in this repository with a **passed, matched, whole-FID holdout
   confirmation** is L-DCONFIRM arm D.
3. **Arm D is the repo's strongest confirmed architecture (HOLDOUT-DTI, `evidence/dconfirm_holdout_2026-10-25.json`).**
   Confirmation (seeds 215–224, whole-FID buffered hide-and-recover): D 0.106588 vs B 0.099175;
   paired Δ +0.007599, 95 % CI [+0.004885, +0.010380]; 10/10 seeds and 4/4 folds positive;
   121,404 withheld-positive occurrences; selection stage D also beat B/E. Its OOF surface
   Spearman vs the 12 pinned peers is ≤0.456 (`max` over the registry in the same card), far
   below the 0.90 stop. H29-2's D control independently replicated at 0.1221 on seeds 300–309.
4. **Live anchors for this emission family (OWNER-REPORTED):** H31-1 dual-regime CELF (a richer
   surface of the same family) 0.2250; H29-PM CELF 0.2190; slot-1 T-v2 0.2449. Arm D is a simpler
   surface than H31-1, so its live score is **unknown** with an honest bracket bounded above by
   the family's own live anchors and below by sibling ML submissions (0.02–0.16). No projection
   is written as a score.
5. **Why nothing else was run.** H28-6, H29-XG, H33-1, H29-2-dip, H31-ENS, H29-5-PROXY are all
   recorded negative with their killing measurements; GDR #1391 and raw 3DEP sources remain
   unreachable from this sandbox (`knowledge/38`). A far-field-only emitter cannot pass this
   holdout by design (catalogue-internal truth, `knowledge/10`), and the H19-5 field itself is
   label-leaky and locked behind the duplicate stop.

## 2. What this session does

- Rebuild the two git-ignored transform caches (`scripts/rebuild_dconfirm_caches.py`) with the
  unchanged `run_dconfirm_holdout.load_transforms` builders.
- Run the preregistered E3 builder `scripts/build_dconfirm_submission.py` exactly as frozen in
  `knowledge/15` §4: full-fit HGB arm D (32 cached bands + 15 subsurface transforms), ridge NMS,
  priority Poisson-disk ≥2.8 px, B2 (2 px catalogue collar), 38,000 dots, all-finite zeros-outside
  primary + NaN twin + single-TIF zip + checks JSON + run card. The builder computes the frozen
  ok_to_submit verdict; the readiness gate re-checks it fail-closed.
- Independently re-read the emitted bytes (grid, dtype, range, dot count, catalogue mask).
- Report both uniqueness scopes separately: the frozen self+peer screen (may fail on this repo's
  own unsubmitted H28-1 research raster, per the builder's original selector note) and the
  user-facing scope (the 12 pinned peer submissions = the listed GEMSDOE sites, plus this repo's
  already-submitted files H31-1 / H29-PM / slot-1, which the builder's repo-glob also covers).

## 3. Frozen expectations (written before the run)

- Expected dots: exactly 38,000; 0 on catalogue; min catalogue distance >2 px.
- Expected holdout numbers: copied from the recorded confirmation, not re-measured.
- Expected uniqueness: peer-registry pass (surface ≤0.46). Self-repo overlap vs the 59,075-dot
  H28-1 research raster may exceed 0.70 — the original builder already documents that outcome
  and refuses unilateral post-hoc gate edits. If so, the verdict stays "negative/not promoted"
  by the frozen gate, and the executive summary must state plainly which scope failed and that
  slot promotion is the user's selector decision, not this session's.
- No live score is claimed or projected. Negative results are deliverables.
