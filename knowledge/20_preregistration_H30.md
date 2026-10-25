# H30 preregistration — hydrothermal-chemistry-verified, conflict-cleared subsurface emission (frozen 2026-10-25, BEFORE E1–E3)

**Labelling.** Leaderboard numbers are **OWNER-REPORTED** (prompt / owner sites; no DrivenData receipt
exists in this repo). Detector numbers are **HOLDOUT-DTI** (`gems27.metric` v1, α=0.2 β=0.8, 300 m
triangular kernel; buffered hide-and-recover). Raster facts are **MEASURED**. Live-gain expectations
are **MODEL/priors**, never scores.

## 0. Session context and selector decision recorded (IR-2026-10-25-06 follow-up)

The current owner prompt (2026-10-25) states, as highest urgency: *generate a unique TIF submission;
do not copy a previous submission; it must be obvious whether it is OK to download and submit*, and
names the focus sites GEMSDOE24/25/27/28/30/31/32/33/36 — exactly the 12 pinned entries of
`registry/parallel_submission_registry.json`. **Recorded decision (selector instruction, this
prompt):** the *operative* duplicate screen for this session is the frozen 12-peer parallel registry
(Spearman ≤ 0.90; ≤ 3-px directed dot overlap ≤ 70 %). The stricter self-registry screen of
`knowledge/15` §4 (which additionally includes this repo's own shipped, unscored research rasters)
remains **reported in full** and is *designed for* (deconfliction targets it by construction), but
its historical failures were: H29-1 vs H28-1 (85.4 %) and H29-1b vs H29-1 (82.6 % — its own
same-session twin, generated minutes earlier in the same lane; the twin did not exist when that
screen was frozen). This session's file is built to pass **both** screens where physically possible;
the run card reports every number either way. No screen is silently waived: any miss is disclosed.

## 1. LANE L-H30 (the single method paragraph for this session)

> **H30 — hydrothermal-chemistry-verified, conflict-cleared subsurface emission.** Start from the
> twice-confirmed Arm-D detector (full 32-band prepared stack + the 15 label-free subsurface
> transforms of `gems27.subsurface_features`; HistGradientBoosting via the shared `gems27.oof_detector`,
> hyper-parameters unchanged). **New component 1 (new information):** a label-free hydrothermal
> chemistry field C(x) built ONLY from the hash-pinned INGENIOUS/GDR wellspring CSV's station
> coordinates and temperature measurements (`temp_c`, preferring `geothermquartz_c` where present;
> the catalogue-derived `dist_known_fault_px` column is never read): per-station local thermal
> anomaly versus the median temperature of stations within 15 px (fallback: global median where
> fewer than 5 neighbours), rasterised by max-pooling to the 100 m grid, Gaussian-smoothed σ=2 px,
> coverage dilated 3 px, rank-normalised to [0,1] inside the coverage mask. The emission priority
> score is S = D_prob · (1 + 0.4·(2C−1)) inside coverage and S = D_prob outside it (bounded ±40 %
> re-ranking of the detector ranking; the submitted values remain binary {0,1}). **New component 2
> (uniqueness by construction):** deconflicted placement — candidate ridge pixels are partitioned
> into *conflicted* (within 3 px Euclidean of any positive pixel of this repo's shipped rasters in
> `docs/downloads/`, including the unscored H28-1 / H29-1 / H29-1b / L-DCONFIRM research files) and
> *clean*; at most 65 % of the 38,000-dot budget may be placed on conflicted candidates (in priority
> order), the remainder refilled from clean candidates in priority order; if the clean pool cannot
> fill the budget, the remainder is taken from conflicted candidates in priority order and the final
> measured overlap is gated at 0.70 regardless. Emission otherwise unchanged from the confirmed
> optimum: ridge NMS, B2 (no dot within 2 px = 200 m of *visible* catalogue faults), priority
> Poisson-disk ≥ 2.8 px, 38,000 dots, binary {0,1}, all-finite primary file. Validation: shared
> hide-and-recover whole-segment buffered holdout (`gems27.holdout`), **fresh seeds 240–244** (never
> used; history consumed 130–159, 200–204, 210–214, 215–224, 230–231), arms **B** (full-32 control),
> **D** (+15 transforms control), **L** (lane), pooled DTI, leakage canary on the re-ranking
> multiplier alone, surface Spearman vs the 12-peer registry before placement, final-dot 3-px
> overlap vs every registry peer AND every repo-shipped raster after placement.

## 2. Geological hypothesis (the 3–5-hypothesis screen is in `knowledge/21`)

**Hypothesis.** Faults missing from the USGS/INGENIOUS catalogue (scope: evidence of coseismic
surface rupture in ~1.6 Ma) include buried and older structures that nevertheless channel
geothermal fluids; warm/chemically evolved wells and springs therefore align along them. A local
thermal-anomaly field derived from measured temperatures should *verify* (raise) subsurface-detector
candidates that pass near active fluid pathways and *demote* candidates with no fluid evidence,
improving dot ranking at the fixed B2/38 k optimum.

**Mechanism.** Multiplicative bounded re-ranking of the Arm-D probability surface before ridge NMS
and priority Poisson placement, so chemistry can only reorder candidates within sampling coverage
(~18 % of the footprint), never invent or delete ridges.

**Named non-fault processes that could mimic the signal** (run-card copy): deep regional aquifer
discharge unrelated to faulting; geothermometer scatter from silica loss/mixing; sampling bias
(wells drilled in basins and known districts, so coverage follows accessibility, not geology);
duplicate stations; non-fault heat sources.

**Why it could catch a catalogue-missing fault rather than a catalogued one:** the catalogue lists
surface-rupture structures; a buried/basement fault with active upflow hosts warm springs without
a young scarp, so the chemistry field carries information the lidar-scarp regime cannot see.

**How it differs from anything already implemented in this repo:** H27-12 tested *distance to
spring/well points* as detector features (measured ≈ 0 gain, refuted); no candidate has ever used
the measured temperature/geothermometer *values*, and none has used chemistry as a post-detector
re-ranker (which cannot dilute the HGB, the measured failure mode of the E2a feature-augmentation
route). The deconflicted placement is likewise new (H29-1b capped one raster only).

## 3. Frozen experiments and gates (budget: E1, E2, E3 = 3 experiments, then stop)

* **E1 — leakage canary.** The re-ranking multiplier M (1 outside coverage) alone against hidden
  truth on seed-240 splits, pooled AUC. **AUC > 0.90 ⇒ STOP (leakage until explained).** Also
  reported: C within coverage.
* **E2 — holdout (seeds 240–244 × 4 quadrants = 20 cells).** Arms B, D, L, identical per-fold dot
  budgets summing to 38,000; B2 from visible faults only; visible faults masked pixel-exactly;
  600 m train buffer; hidden segments' 6 px ring excluded from scoring.
  **Promote gate (ALL required):**
  1. pooled HOLDOUT-DTI(L) > pooled HOLDOUT-DTI(B);
  2. paired mean Δ(L−B) > 0 with 95 % bootstrap CI excluding 0;
  3. ≥ 12/20 cells positive (L vs B);
  4. canary clean;
  5. Δ(L−D) ≥ −0.004 (deconfliction + chemistry must not destroy more than ~half of D's
     twice-confirmed increment; D−B is also reported as a free fresh-seed replication);
  6. surface Spearman of the L surface ≤ 0.90 vs every one of the 12 pinned peers (before
     placement).
* **E3 — build + screens.** Full-fit Arm-D surface → chemistry re-rank → deconflicted Poisson →
  38,000-dot binary raster. **Uniqueness gate (all measured on final dots):** directed 3-px
  Euclidean overlap ≤ 0.70 vs **every** raster in `registry/parallel_submission_registry.json`
  (operative rule) AND ≤ 0.70 vs every repo-shipped raster in `docs/downloads/` (strict screen,
  targeted by construction). Validator hard-PASS (all-finite, [0,1], EPSG:32611, 3730×3292,
  transform match, no NaN in footprint, zip with exactly one GeoTIFF).
* **ok_to_submit = E2 gate AND E3 gates.** Verdict `promote`/`negative`; negative results are
  deliverables. Promotion to a real weekly slot remains the owner's separate selector step
  (protocol §6); this session only certifies gate status. No live score, no projection written as
  a score. No post-hoc tuning, no seed shopping; seeds 240–244 are frozen here.
* **Disclosed biases.** The deconfliction halos derive from full-fit (full-label) research rasters
  and only *remove* candidate positions, so the L arm's holdout is biased **downward**
  (conservative) — the same disclosure as H29-1b. The chemistry field is label-free and fold-safe.
  The catalogue-internal holdout cannot price far-field placement (`knowledge/10`).

## 4. Why this lane (one paragraph, PhD judgement)

0.2778 is the H19-5 family's emission-surgery ceiling (knowledge/12/17): every top file is one dot
field re-thinned, further thinning is capped ≈0.29, and the only route to 0.30+ is better *ranking*
at the fixed B2/38 k optimum. The best-evidenced ranking increment available is Arm D (+0.0076/+0.0086
on disjoint seeds), but every plain D emission duplicates the repo's own unscored research rasters
(>70 % ≤3 px). H30 keeps the confirmed detector, adds one genuinely new physical information source
(measured temperatures — the direct observable of the geothermal system the competition is about),
and buys strict uniqueness with a bounded, pre-registered placement cost whose size the holdout
measures directly (Δ(L−D)). Expected Δ(L−B) prior: +0.002…+0.008 (inherits D, minus deconfliction
cost, plus/minus chemistry). P(beating 0.2778 live if promoted) ≈ 0.35–0.5, expected margin
+0.000…+0.015 (MODEL). This is not a claim it will beat the leaderboard high (0.3195/0.4413,
conflicting — IR-2026-10-25-02).
