# Session 13 — engineering review and hypothesis-screen supplement (2026-10-27)

**Branch:** `arena/e40840b3-gemsdoe27`  
**Scope:** three-pass repository review; restore the pinned local inputs; run the existing checks; fix an actionable clean-checkout failure.  
**No new geological experiment, candidate raster, leaderboard submission, or organizer score was produced in this review.** The prompt's parallel-run protocol refers to a single method paragraph/lane, but no uniquely specified method paragraph is present in the current task. I therefore did not invent a lane or consume holdout seeds. This is a deliberate stop, not a positive result.

## Executive decision

- **The repository already contains a unique, format-valid candidate GeoTIFF**: `docs/downloads/gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif`, SHA-256 `2c002b02792419864bd3b29a218e543cb41e3f07b3b57c29ef35c6e39e184bfe`. Its single-TIFF ZIP is beside it. The byte-level download verifier passes its CRS/grid, single-band, finite-value, `[0,1]`, catalogue exclusion, ZIP, and manifest checks.
- **This is not an organizer authorization or a demonstrated leaderboard winner.** The machine audit explicitly says `slot_authorized: false`; the weekly selector/cap and current global registry have not been checked. There is no DrivenData receipt in the repository and repository policy prohibits agent access to DrivenData. Do not claim this file scores higher than GEMSDOE32.
- H31-1's saved **HOLDOUT-DTI** is **0.047302**, 95% CI **[0.044527, 0.049619]**, with **120,778 withheld-positive occurrences**, evaluator `gems27.metric v1 + holdout-blind-buffered-v2` (`alpha=0.2`, `beta=0.8`, 300 m triangular kernel, `buffer_px=6`, seeds 400–409). It is a catalogue-internal proxy result, not a leaderboard score.
- The existing live-score estimate in `knowledge/27_session11_executive_summary_and_h32_result_2026-10-26.md` is **PROJECTION ~0.235** (not a score), and explicitly concludes that exceeding the owner-reported 0.2778 is not established. The 0.3195 and 0.4413 leaderboard values in the supplied prompt conflict and are not supported by organizer receipts here.
- The historical 9-site table and exact GEMSDOE32 raster-lineage analysis are already in that executive summary. Historical scores there are owner-reported; values are not independently confirmed by DrivenData.

## Candidate screen carried forward (not run in this review)

Planning ranges below are the repository's prior **expected HOLDOUT-DTI deltas**, not observed results, score predictions, or leaderboard scores. Layers and distinctions were checked against `registry/next_hypotheses.json` and its cited source/status records.

| Priority | Candidate | Layers and physical signature | Why it might identify an uncatalogued fault / difference from prior work | Planning prior and cost | Viability now |
|---:|---|---|---|---|---|
| 1 | **H27-16 — paleogeothermal sinter/tufa + temperature probes + Quaternary volcanics** | Official GDR #1391 packages for sinter/tufa/altered bedrock, 2 m temperature probes, and Quaternary volcanics; target aligned fossil hydrothermal deposits plus local positive temperature residuals. | Fossil deposits can preserve hydrothermal conduit traces where young cover obscures a modern scarp. Distinct from existing well/spring chemistry covariates. Named mimics include Lake Lahontan lacustrine tufa, groundwater outflow, and volcanic contacts. | Expected **HOLDOUT-DTI delta prior +0.001 to +0.008**; medium-high cost. | **Blocked / not verified obtainable here.** GDR #1391 is named in the source registry, but `gdr.openei.org` is outside this session's network allowlist and raw package bytes/hash verification are absent. Do not code/use this arm until official bytes are obtained and pins verified. |
| 2 | **H29-5 — range-front canyon-mouth knickpoint / fan-apex collinearity** | Existing DEM/LiDAR bands `det_elev`, `det_local_relief`, `det_gradient`, `lidar_relief`, `lidar_cross_max`; target multi-canyon outlet alignments at range fronts. | Alluvial aggradation may bury short inter-canyon scarps while aligned channel outlets preserve a broader structural signal. Distinct from local scarp height/curvature transforms. Named mimic: resistant stratiform bedrock hogbacks crossed by transverse streams. | Expected **HOLDOUT-DTI delta prior +0.001 to +0.005**; medium cost; existing layers. | **Feasible to preregister, not yet validated.** `registry/next_hypotheses.json` proposed fresh seeds >=440; this review did not consume them. |
| 3 | **H30-2 standalone ablation — quality-filtered thermal upflow + oblique transfer zones** | `gdr_wellspring_in_footprint.csv`, `cond_surf`, `depth_to_base_surf`, `rtp`, `iso_grav_anom`, `geod_shearrate`; target station-deduplicated thermal/geothermometer excess co-located with oblique strike-rotation boundaries. | Distinct test is an isolated, quality-filtered ablation, not the already-tested combined H30-1 model. Mimics include lateral warm-water plumes, clustered agricultural/municipal wells, and old pluton/thrust contacts. | Expected **HOLDOUT-DTI delta prior +0.001 to +0.004**; low incremental coding cost. | **Partially tested in a larger stack, standalone test still unvalidated.** The feature component is not wholly novel; preregister only the ablation/control contrast, using fresh seeds. |

The first-ranked idea has the highest prior but cannot be validated in this environment. H29-5 is the highest-ranked candidate that appears runnable using the restored layers. However, no new run should start until the method lane is explicitly pinned, seed availability is checked against every saved run, and the shared evaluator/feature pipeline is chosen. No slot has been selected or spent.

## Pass 1 — restore and verify

1. Read `README.md` and `AGENTS.md`, including the no-DrivenData-access rule and the current audit correction.
2. Ran `python scripts/restore_data.py`. All 17 manifest entries (16 inputs plus assembled `training_features.tif`) matched their pinned SHA-256 values. Inputs came from immutable owner sibling-repository GitHub commits; they are **not organizer-authenticated downloads**.
3. Ran `python scripts/prepare_data.py`. It produced the ignored `data_cache/prepared/features.npy` matrix: **5,167,373 footprint rows × 32 features**, `float32`, EPSG:32611, cache SHA-256 `83ed2704ee2de03cf8b1c8f2966fcf71813501df97c1c35400e6c0415393f6dc`.
4. Ran `python scripts/fetch_parallel_registry.py`. It fetched and grid-checked all **12** raster rows pinned in `registry/parallel_submission_registry.json`; these are owner-repository peer artifacts, not organizer receipts.
5. `python scripts/restore_data.py --verify` passed all pinned hashes. `python scripts/verify_downloads.py` then passed with **0 failures**, including H31-1's `[0,1]`, grid, ZIP and file-hash checks. The machine readiness audit approved publication evidence for H30-1 and H31-1, but reported `slot_authorized: false` for both.

## Pass 2 — bugs, assumptions, and edge cases

- On a clean checkout with no `data_cache/`, the standalone download verifier previously raised a rasterio traceback for missing `sample_submission.tif`. Fixed `scripts/verify_downloads.py` to fail closed with a concise prerequisite message and exit code 2, explicitly distinguishing cached sibling mirrors from organizer-authenticated inputs. Added `tests/test_verify_downloads_prereq.py` to cover this case.
- Found a contradictory executive-table action label that said “DOWNLOAD & SUBMIT THIS ONE” while the front-page gate correctly said selector approval was still required. Changed the generated action to “DOWNLOAD — SELECTOR REQUIRED,” linked the current review and retained the separate 9-site audit link, and added a site regression assertion.
- The verifier continues to check the raster bytes—not just a JSON readiness boolean. The project-level audit also separates evidence publication from selector authorization. No false assurance that a holdout score equals a live score was added.
- Existing limits remain: the peer registry is a pinned snapshot, not a current global uniqueness proof; a passing format check does not establish merit; H31's 0.235 projection is calibrated from limited owner-reported/live anchors and is uncertain; no submission receipt or weekly-cap state exists here.

## Pass 3 — re-check and verification

Commands run after installing the ignored project virtual environment:

- `.venv/bin/python -m pytest -q` — **152 passed** after restoring the cache (the earlier pre-cache run had 148 passed, 3 skipped).
- `.venv/bin/ruff check src scripts tests` — **all checks passed**.
- `.venv/bin/python scripts/restore_data.py --verify` — all pinned inputs passed.
- `.venv/bin/python scripts/verify_downloads.py` — **0 failures**.
- `.venv/bin/python scripts/audit_submission_readiness.py` — H30-1 and H31-1 evidence cards approved; **both have `slot_authorized: false`**.
- `.venv/bin/python scripts/build_site.py` — rebuilt the six Pages documents plus root mirror. The generated output continues to identify H31-1 as a candidate requiring a separate selector decision and explains submission steps.

The first test-suite run was performed before the project environment was installed and failed because `pytest` was absent; the initial verifier run also could not find `data_cache/sample_submission.tif`. These setup failures are preserved in the session transcript and were resolved by installing `requirements.txt` and restoring the documented hash-pinned cache. They are not counted as successful runs.

## Submission and score labels

- **Historical site scores:** OWNER-REPORTED, not ORGANIZER-CONFIRMED. The 9-site comparison is in the linked executive summary.
- **H31-1 evaluation:** HOLDOUT-DTI, with evaluator, withheld-positive count, seeds and CI given above.
- **Estimated leaderboard score:** PROJECTION ~0.235 only; never a score. No organizer-confirmed number is available.
- **Current downloadable file:** the H31-1 TIFF path at the start of this report. It is unique under the pinned focus-peer thresholds recorded by the prior evidence, but this review did not regenerate it and does not authorize its upload. Its existing name/note are already in the manifest and first-screen executive summary.
- **Newly generated candidate this session:** none. No weekly slot was used and no real submission was made.

## Official-source and access limits

Source records and review links are in `registry/sources.json`, `docs/sources.html`, and `knowledge/05_sources_and_verification.md`. This review did not fetch external official websites. Network policy permits GitHub/codeload/API and package registries only; in particular it prevents direct checks of DrivenData, GDR/OpenEI, USGS, NLR/OSTI, and GBCGE from this environment. The cached artifacts provide hashes and provenance to owner-repository commits, not fresh official-source verification. DrivenData's current score, latest leader, submission rules at the point of upload, weekly cap, and receipt all remain unverified here.

## Carry-forward

1. Keep H31-1 clearly downloadable but labelled **unscored; selector required**. Do not tell the user it beats 0.2778 or the conflicting leaderboard claims.
2. Assign a single explicit method paragraph/lane, then audit seed non-reuse and preregister H29-5 if it remains the selected viable hypothesis. Run feature-alone canaries and the template's buffered whole-segment holdout before creating any promotion candidate.
3. Obtain H27-16 raw official package bytes through an authorized route and verify the recorded pins before considering the higher-prior external-data arm.
4. Re-pin the peer registry before any future uniqueness verdict, because the existing 12-peer set is frozen to repository commits.
5. Any owner-submitted score must be transcribed from an actual submission receipt and labelled ORGANIZER-CONFIRMED; do not access or automate DrivenData from this project.

## Canonical run card

The single Session 13 audit run card is [`evidence/session13_run_card_2026-10-27.json`](../evidence/session13_run_card_2026-10-27.json). It records zero experiments, the saved (not rerun) H31-1 HOLDOUT-DTI, the pinned-registry overlap results, raster validator output, and the negative/no-promotion verdict. This supplement intentionally does not duplicate the JSON card.
