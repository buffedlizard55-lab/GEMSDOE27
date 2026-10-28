# H28-6 result and three-pass review (2026-10-28)

**Decision: NOT OK TO SUBMIT. No new TIFF was published.** The candidate failed its frozen holdout efficacy gate, and its dots broke the 70% local overlap stop, so the preregistered rule wrote no raster. Nothing was uploaded, and no weekly slot was selected or claimed.

Preregistration (hash in the run card): `knowledge/36_preregistration_H28-6_2026-10-28.md`. Run card: `evidence/h28_6_run_card_2026-10-28.json`. Evidence: `evidence/h28_6_e1_canary_and_surface_700_709.json`, `evidence/h28_6_e2_holdout_700_709.json`. Run log: `evidence/_scratch/h28_6_run.log` (git-ignored).

Labels: every number below is **HOLDOUT-DTI** (evaluator `gems27.metric.dti_binary` v1, α=0.2, β=0.8, R=3 px triangular, whole-FID buffered holdout, buffer 6 px). None is an organizer score, a leaderboard estimate or a projection.

## Download decision (the answer the user asked for)

| File to download | Estimated score | Unique? | OK to submit? |
|---|---|---|---|
| None for H28-6. No valid TIFF was written. | HOLDOUT-DTI C 0.041238 vs control D 0.041574; mean paired Δ −0.000234, 95% CI [−0.002550, +0.002143]; 121,143 withheld-positive occurrences. No organizer estimate exists. | NO. Dots break the 70% local stop: 84.9% lie within 3 px of `gems27-h28-3-strain-conductivity-negative-research-20261025-27d6875f3b22-allfinite.tif`. Pinned-set max 46.8%. | **NOT OK TO SUBMIT** |
| `docs/downloads/research/gems27-h33-bss-complement-20261027-9ba8480691ed-allfinite.tif` (SHA-256 `1373358188a96b20414834b3e0159065d87470fe695153262ced7b46bc1eb492`) | HOLDOUT-DTI 0.025211 vs control 0.041446; paired 95% CI [−0.017576, −0.014449]; 134,150 withheld-positive occurrences. | YES vs the 12 pinned rasters (max overlap 0.000) and 21 local prior rasters (max 0.607, limit 0.70). Scope is limited to those files. | **NOT OK TO SUBMIT** (the holdout gate failed on every seed and fold) |
| Historical files for the nine sites | OWNER-REPORTED values only | Already in the registry, so not new | **NO**, do not resubmit |

The live table is generated into `EXECUTIVE_SUMMARY.md` and `docs/executive-summary.html` by `scripts/build_site.py` (`decision_board()`). It reads the run cards, so a stale hand-written row cannot survive a rebuild.

## Why H28-6 did not beat the control

- **Seeds are bimodal.** Per-seed Δ (C−D), seeds 700–709: +0.00397, +0.00562, −0.00417, −0.00526, −0.00516, −0.00126, −0.00103, −0.00128, +0.00360, +0.00263. Four of ten seeds favour the candidate (gate ≥7/10). The mean is about zero, and the 95% CI spans zero.
- **Folds are mixed.** Per-fold pooled Δ: NW +0.00206, NE_LidarGapHeavy +0.00146, SW −0.00216, SE −0.00080. Two of four folds are positive (gate ≥3/4).
- **Plausible reason:** the new columns are a gravity-gradient reduction. The 51-input model already holds `iso_grav_anom_hg`, `_vg` and `_slope`, so the persistence minimum adds little beyond the stack. The data cannot tell whether the gain is real or noise. The result is negative.

## Leakage canaries and surface

- Canary (all 51 model inputs, direction-invariant AUC, hidden positives vs 250,000 negatives): maximum **0.585** (`det_local_relief`); the four new columns peaked at **0.532**. Threshold 0.90. No leakage flag.
- The C full-fit surface has maximum |Spearman| **0.109** against the 12 pinned rasters (limit 0.90).
- The training mask excluded every hidden pixel on all ten seeds.

## Uniqueness (pre- and post-placement)

- Pinned 12-raster check: max directed 3 px overlap **0.468**, final-dot |Spearman| max **0.039**. Passes.
- Local check against 22 all-finite files in `docs/downloads` plus research: max overlap **0.849**. **Fails** the 0.70 stop.
- Rule applied as written: no TIFF written. Naming the failure is the point; a file that clears only the 12-raster set would overstate uniqueness.

## Answer to "can this beat 0.2778?"

Not shown. This run gave no evidence that the gravity-persistence features beat their matched control on catalogue-internal holdouts. A competitive score needs (a) a positive matched holdout, (b) a dot set unique against *both* the pinned rasters and the local research family, and (c) the matched H31/H29-S comparison. None of the three is met. The 0.2778 explanation (the d=2.8 family minus a 2 px collar) is unchanged from `knowledge/31` and `knowledge/34`. Those are owner-reported values; this session cannot verify the leaderboard.

## Three-pass review

**Pass 1 (implementation).** Set up the venv and restored hash-pinned inputs (`scripts/restore_data.py`, `scripts/prepare_data.py`). The first run stopped because `fetch_parallel_registry.py` had not been run. That was fixed by running it, which restored all 12 pinned rasters, each matching its pin. Wrote `src/gems27/gravity_persistence.py` and its tests. Wrote `scripts/run_h28_6_gravity_persistence.py`, which reuses the shared holdout, metric, writer and H33 helpers by import rather than forking them.

**Pass 2 (defects and edge cases).**
- A constant anomaly produced full-scale edges, because round-off gradients were normalized by an almost-zero 99th percentile. Caught by the unit test before any scoring. Fixed with a relative floor. Recorded as `IR-2026-10-28-gravity-constant-field-roundoff-fixed`.
- The full 51-column matrix would be about 1 GB on a 3 GB machine, so the runner streams batches from memory maps.
- The first E3 run was judged a duplicate by the local check, as designed. It wrote no TIFF. The uniqueness JSON is kept in scratch.
- Removed the unpublished scratch TIFFs, so no raster is left outside `research/` that could be mistaken for a download.
- Build-site defects found and fixed: an unescaped `|` in the Markdown table, a generic H33 reason, and a misleading "NO - NOT OK" wording.

**Pass 3 (requirement re-check).**
- Holdout reported as HOLDOUT-DTI with evaluator, withheld count and CI: done.
- Canary on every input: done (51 features).
- Pre- and post-placement uniqueness: done for the pinned set and the local set. The complete organizer-visible list was not available, so the uniqueness scope is stated as limited.
- Obvious OK/NOT OK per file: done in the generated table.
- Lane: the prompt omits its lane paragraph again. This session ran only the registry's own rank-3 hypothesis. Flagged `IR-2026-10-28-lane-paragraph-missing-again`.
- Budget: one experiment with three stages (E1, E2, E3), about 2 hours.

## Hypothesis screen (ranked; full table in the preregistration, section 1)

1. H28-6 scale-persistent gravity edges: run, negative.
2. H28-7 directional radiometric alteration continuity: not run. Radiometric ratios were weak in Addendum D.
3. Actual routed-drainage fan-apex collinearity: blocked. The raw DEM is not in the sandbox.
4. DOE GDR #1391 sinter/tufa and 2 m probes: blocked in bash. The metadata page is readable (fetch tool, 2026-10-28). The packages are not.
5. Magnetic multi-scale persistence: likely redundant with the existing `sub_tiltabs_rtp` and `sub_analytic_rtp`. Not run.

## Official sources (for manual review; not all were accessed by this agent)

- [GDR submission 1391, INGENIOUS compilation](https://gdr.openei.org/submissions/1391), DOI 10.15121/1881483. Read 2026-10-28 via the fetch tool, metadata only.
- [DrivenData competition 306](https://www.drivendata.org/competitions/306/competition-doe-gems/). Not accessed by this agent; the repository forbids automated access.
- [Official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution). Read in an earlier session through GitHub.
- [USGS 3DEP](https://www.usgs.gov/3d-elevation-program). Listed only; not read.
- Bash cannot reach gdr.openei.org or usgs.gov (TLS failure, 2026-10-28). Recorded as `IR-2026-10-28-gdr-bytes-blocked-in-sandbox`.

## Limits and next steps

1. **Supply the lane.** The prompt must name the single method paragraph. Until then, lane choice is a documented self-selection.
2. **Matched current-best comparison.** Re-run H31 or H29-S on the same whole-FID splits. Without it, no file can be OK to submit under the readiness gate.
3. **Local uniqueness.** A useful candidate needs dots that clear 0.70 against the local research family as well as the pinned set. H33-1 does this by construction (complement emission), at a holdout cost (0.025 vs 0.041).
4. **Independent geography.** Whole-FID catalogue holdouts are repeated hides of the same catalogue, not independent faults. Add an off-catalogue or externally sourced check before trusting any HOLDOUT-DTI difference.
5. **Data gap.** The GDR #1391 packages (sinter/tufa, 2 m probes, volcanics) need a verified copy. That source is the one that could add information the catalogue lacks.
6. **Registry completeness.** The uniqueness scope covers 12 pinned rasters plus local files. It does not cover the full organizer-visible submission list.
