# Session 13 readiness audit — 2026-10-27

## Decision first

**No new geological experiment was run and no weekly slot was selected.** The prompt's parallel-run requirement assigns one method paragraph as the lane, but no single paragraph is delimited in the supplied text. Guessing a method would violate the lane rule and make the uniqueness/effectiveness test uninterpretable. The existing H31-1 file is available for audit and separate selector review; this report does **not** authorize an upload.

- **Downloadable artifact:** [`gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif`](../docs/downloads/gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif)
- **Submission name:** `27GEMSDOE-H31-DRCG-WL-20261026-cf8e1bbef244`
- **Portal note:** `27GEMSDOE H31-1 | dualRegime MSub+MFull+WLseis+obliq+CELF2.8 B2 37654px | id cf8e1bbef244 | unscored validated-promote` (118 characters)
- **Verdict:** EVIDENCE PASS — SELECTOR REQUIRED. Download for audit/review; **not authorized to upload** until the separate selector records the current weekly-cap and registry decision. No DrivenData page was accessed and no upload or organizer score occurred.

## Completed in this session

1. Followed `README.md` and `AGENTS.md`; reviewed the current nine-focus-site summary, prior run cards, data manifest, README task prompt, score provenance, and current output-generator logic.
2. Restored hash-pinned inputs with `scripts/restore_data.py`. All 17 listed files reported `OK`; the sources are pinned sibling-repository mirrors, not newly acquired organizer-authenticated downloads.
3. Rebuilt the 32-band cached feature matrix with `scripts/prepare_data.py`: shape `5,167,373 x 32`, EPSG:32611, SHA-256 `83ed2704ee2de03cf8b1c8f2966fcf71813501df97c1c35400e6c0415393f6dc`.
4. Found a material UI contradiction: the executive page said H31-1 was the “best new unique submission to upload now” even while requiring a separate selector decision. Corrected `scripts/build_site.py` to label it the strongest repository evidence-qualified candidate, explicitly state it is **not authorized to upload**, and explain it is available for audit/selector review only. Added regression assertions in `tests/test_site.py` so the conflicting upload claim cannot return.
5. Rebuilt static Pages outputs through the existing project test/build path. The focus-sites table remains a comparison of historical owner-reported results, not a real-time leaderboard crawl.

## Focus-site executive comparison

Numbers below are the repository's saved historical comparisons and are **OWNER-REPORTED**, not copied from submission receipts. They are not fresh score estimates for a new file. These nine submissions are already historical; do not rename/re-submit them as novel work. Scores and file associations should be reviewed against the evidence links in the rendered executive page and `evidence/focus_sites_executive_summary_20261026.json`.

| Site | Highest saved result | Score provenance | Exact-duplicate status / useful interpretation |
|---|---|---|---|
| GEMSDOE24 | `h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan` | 0.2477 OWNER-REPORTED | Historical H19-5 family; overlaps later B2 outputs, not new. |
| GEMSDOE25 | `dotted-h19-5-d2-8-20261002-e56ea318af89-nan` | 0.2600 OWNER-REPORTED | Historical H19-5/d2.8 family; GEMSDOE32 is derived by collar deletion. |
| GEMSDOE27 | `topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan` | 0.2449 OWNER-REPORTED | Historical T-v2 slot; separate H29-S result 0.2190 also recorded. |
| GEMSDOE28 | `gems28-h28-solo-r1-20261003-27c0796d-nan` | 0.2708 OWNER-REPORTED in the saved nine-site ranking | The prompt additionally lists a 0.2710 H36-rung30 result under GEMSDOE28; do not assume the saved ranking is exhaustive. |
| GEMSDOE30 | `d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca` | 0.2600 OWNER-REPORTED | Same H19-5/d2.8 field family. |
| GEMSDOE31 | `gemsdoe31-h32-2-b1-only-20261004-777da82e-allfinite` | 0.2710 OWNER-REPORTED in the saved nine-site ranking | The prompt lists a different 0.2708 H27-4 result as GEMSDOE31's high; do not assume the saved ranking is exhaustive. |
| GEMSDOE32 | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` | 0.2778 OWNER-REPORTED | Highest saved focus-site value; exact pixel relationship to GEMSDOE25 d2.8 after catalogue-collar deletion is documented as measured. Not evidence that re-thinning creates new geological information. |
| GEMSDOE33 | `h33d-analog-tip-stepover-r30-20261004-cb490425926e` | 0.2632 OWNER-REPORTED | Historical analog-tip/stepover submission; saved site comparison records strong family overlap. |
| GEMSDOE36 | `anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros` | 0.2750 OWNER-REPORTED | Independently constructed PINN output, but saved byte comparison reports 96.9% 3-px overlap with GEMSDOE32. |

**Important irregularity:** the supplied prompt swaps/conflicts the GEMSDOE28 and GEMSDOE31 0.2708/0.2710 assignments relative to the repository's saved audit. This remains recorded in `registry/irregularities.json`; neither value is treated as organizer-confirmed. The prompt also cites leaderboard highs 0.3195 and 0.4413 without receipts. They are not used as verified outcomes.

## Why GEMSDOE32's reported 0.2778 is useful, and what it does not prove

The saved, hash-authenticated raster audit records an exact set relationship: GEMSDOE32's `37,654` emission pixels equal the GEMSDOE25 d2.8 field after deleting pixels within the saved two-pixel catalogue collar (symmetric difference zero; see `knowledge/12_why_02778_won.md` and `knowledge/18_why_02778_won_phd_analysis.md`). This is a byte/pixel-set observation. A plausible metric mechanism is that removing near-catalogue predictions that receive little credit reduces false-positive mass while preserving useful coverage under a distance-tapered score. The file comparison alone cannot prove why the organizer score changed; no receipt-level organizer evaluation or hidden-label audit is available here.

The H31-1 line is not a new confirmatory experiment in this session. Its already-saved catalogue-internal holdout is **HOLDOUT-DTI 0.047302**, 95% CI **[0.044527, 0.049619]**, with **120,778 withheld-positive occurrences**, evaluator `gems27.metric v1 + holdout-blind-buffered-v2 (alpha=0.2, beta=0.8, R=3px triangular, buffer_px=6.0)`, seeds 400–409. This supports the pre-registered local detection claim only; it is not a leaderboard score.

The existing one-anchor transfer arithmetic is a **PROJECTION**, not a score: `0.2190 x (0.047302 / 0.044116) = 0.2348`, rounded to approximately 0.235. The anchor is owner-reported and the transfer assumes proportional holdout-to-hidden-test improvement; that assumption is not calibrated and may fail. Therefore the evidence does **not** establish that H31-1 beats the reported GEMSDOE32 0.2778 or either reported overall-leaderboard high (0.3195/0.4413). A defensible new live-score interval is not available.

## H31-1 machine evidence (saved result, byte-checked this session)

- Saved holdout gate: 5/5, seeds 400–409; independent evaluator and withheld-positive count above.
- Leakage canary: direction-invariant maximum AUC 0.58947, below the 0.90 rule.
- Unique screen: pre-placement surface maximum rank correlation 0.13031; final surface maximum rank correlation 0.16452; max directed 3-px dot overlap 62.798% across the recorded screen (57.704% vs the 12 pinned focus-site peers). Both are below the declared 0.90 / 70% stop thresholds. This is uniqueness only against the recorded registry, not every current submission in every sibling site.
- Raster validator: no NaN inside footprint; single-band float32; values in `[0,1]`; EPSG:32611; shape `3730 x 3292`; transform `[100,0,243350,0,-100,4508550]`; 37,654 one-valued pixels; zeros outside and no nodata tag for the all-finite file.
- Raster SHA-256: `2c002b02792419864bd3b29a218e543cb41e3f07b3b57c29ef35c6e39e184bfe`.
- No experiment was run this turn; no seed range was consumed.

## Source and access status

Official manual-review links are listed in `registry/sources.json` and [`docs/sources.html`](../docs/sources.html), including the DrivenData competition description, reference solution, USGS GeoDAWN metadata, the GDR submission listing and the official rules PDF. This session did not freshly fetch official sites: outbound networking is restricted to GitHub/codeload/API/npm/PyPI hosts, and the stored source feed is not a live verification. The repository policy also prohibits automated requests to `drivendata.org`. Consequently, no statement here claims a fresh current leaderboard, current weekly-cap state, submission receipt, or current external-data availability.

## Three-pass review and verification

- **Pass 1 — implement:** restored pinned data, rebuilt the cached feature stack, and fixed the conflicting site copy in the shared builder with regression tests.
- **Pass 2 — bug/assumption review:** preserved the explicit selector requirement; distinguished HOLDOUT-DTI from projections and owner-reported historical results; documented the GEMSDOE28/31 mismatch and limited registry coverage; did not invent a lane or consume seeds.
- **Pass 3 — acceptance review:** regenerated the site; `pytest` **151 passed**; `ruff check src scripts tests` passed; `compileall` passed; `scripts/verify_downloads.py` reported **0 failures** across the registered download package; data inputs and cached matrix hashes verified. No DrivenData access or upload occurred.

## Carry-forward priorities

1. Keep H31-1 as the strongest currently evidence-qualified file, but do not upload without a separate selector record confirming live cap and registry scope.
2. Before any fresh experiment, delimit/select a single lane and preregister the feature(s), controls, fresh seed range, holdout-DTI gate, feature-alone leakage canaries, and pre-/post-placement uniqueness thresholds. Respect the three-experiment/two-hour cap.
3. Obtain organizer receipts (through the owner) to resolve historic rankings and calibrate any transfer model; don't use a projection as a score.
4. Refresh official-source checks only in an authorized environment that can reach those source hosts; maintain the prohibition on automated DrivenData access.
5. Continue to treat blind-fault prediction as a proxy for mapped missing faults, not validated geothermal vents or a field-confirmed resource.
