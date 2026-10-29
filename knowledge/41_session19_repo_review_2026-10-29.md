# Session 19 repository review — 2026-10-29

## Executive decision

**No new experiment was run; no new TIFF was written; no submission or weekly slot was selected.** The prompt requires an assigned single-method lane, but supplies no lane paragraph. Inventing a lane would violate the stated parallel-run protocol and `AGENTS.md`. This was an evidence, data-integrity and documentation review only. No number below is an **ORGANIZER-CONFIRMED** score.

**There is no new TIFF that is OK to download and submit.** The only newly generated downloadable TIFF remains H33-1, marked research-only and **NOT OK TO SUBMIT** because its frozen HOLDOUT-DTI efficacy gate failed. H29-XG failed its holdout gate and local duplicate stop, so it correctly wrote no TIFF. Historical all-finite files that pass byte validators are not new submissions and are not approved for a slot.

## What the GEMSDOE32 0.2778 claim does and does not establish

The 0.2778 value is **OWNER-REPORTED** from the prompt, not an organizer receipt. The byte audit on the 12 SHA-pinned owner-mirror rasters (`evidence/peer_relations_20261028.json`, recomputed to `/tmp/peer_relations_review.json` in this review) finds that the GEMSDOE32 dot mask is a strict subset of the GEMSDOE25 d=2.8 mask: 6,436 dots are removed, all at catalogue distances ≤2 pixels; the kept dots have minimum catalogue distance 2.236 pixels. GEMSDOE25 → GEMSDOE31 → GEMSDOE32 is a nested-pruning lineage. The stated values 0.2600 → 0.2708 → 0.2778 are **OWNER-REPORTED**, and do not by themselves establish a causal score gain from the collar. The GEMSDOE32 attribution is disputed by sibling audit evidence, which labels the raster UNSCORED. There is no hidden-label observation here with which to measure the removed dots' marginal credit.

**Interpretation:** under the DTI loss, removing low-credit dots can improve precision-weighted utility if their expected gain is below the score's marginal break-even. The observed collar is consistent with that mechanism, but does not demonstrate it. A narrower version of the same field is a duplicate by construction and is not an acceptable unique strategy. The defensible answer to “can we beat 0.2778?” is **not yet shown**; the reported value itself is not organizer-confirmed, and no local holdout is a calibrated leaderboard estimator.

## Nine requested sites: reported result and uniqueness scope

All values below are **OWNER-REPORTED**, copied from the user-provided site ledger; they are not organizer receipts or prospective score estimates. The table is summarized from `EXECUTIVE_SUMMARY.md`, generated HTML and the pinned-raster audit.

| Site | Highest listed file / method | Reported value | Byte-level uniqueness result in this repository | Download/submit decision |
|---|---|---:|---|---|
| GEMSDOE24 | `gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif` | 0.2477 OWNER-REPORTED | Duplicate stop triggered against the 12-raster pinned set. | Historical; do not resubmit. Organizer estimate unknown. |
| GEMSDOE25 | `gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif` | 0.2600 OWNER-REPORTED; score/file attribution disputed | Exact in-footprint dot match to GEMSDOE30 in the pinned set. | Historical; do not resubmit. Organizer estimate unknown. |
| GEMSDOE27 | `gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif` | 0.2449 OWNER-REPORTED | Duplicate stop triggered against the pinned set. | Historical; do not resubmit. Organizer estimate unknown. |
| GEMSDOE28 | `gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif` | 0.2710 OWNER-REPORTED | Duplicate stop triggered; separate H27-4 raster is dot-identical to GEMSDOE31. | Historical; do not resubmit. Organizer estimate unknown. |
| GEMSDOE30 | `gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif` | 0.2600 OWNER-REPORTED; attribution disputed | Exact in-footprint dot match to GEMSDOE25 in the pinned set. | Historical; do not resubmit. Organizer estimate unknown. |
| GEMSDOE31 | `gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif` | 0.2708 OWNER-REPORTED | Exact in-footprint dot match to GEMSDOE28 H27-4 in the pinned set. | Historical; do not resubmit. Organizer estimate unknown. |
| GEMSDOE32 | `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` | 0.2778 OWNER-REPORTED in the prompt; peer audit calls file UNSCORED | Duplicate stop triggered; strict subset of GEMSDOE25's dot mask. | Historical; do not resubmit. Organizer estimate unknown. |
| GEMSDOE33 | `GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif` | 0.2632 OWNER-REPORTED | Duplicate stop triggered against the pinned set. | Historical; do not resubmit. Organizer estimate unknown. |
| GEMSDOE36 | `gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif` | 0.2750 OWNER-REPORTED | Duplicate stop triggered against the pinned set. | Historical; do not resubmit. Organizer estimate unknown. |

**Scope limitation:** the duplicate conclusions above are final binary-dot comparisons against the 12 currently pinned owner-mirror rasters. The associated pre-placement continuous surfaces for all historical peers are not available in this audit; the registry is not a census of every submission or every later sibling update. This is not proof of global uniqueness or a same-surface rank-correlation screen. The executive site labels this limited scope and provides file links for manual review.

## Ranked candidate screen (no numeric score projection)

Ranked for expected value of a *valid test per implementation effort*, not for a guaranteed live-score gain. DTI benefit is unknown for each. A high estimate cannot be justified: catalogue-internal holdout values are far below the reported live range and there is no organizer truth receipt. The exact geological hypotheses below were not run in this review.

| Rank | Hypothesis and layers | Physical signature / why it might find catalogue-missing faults | Named non-fault mimic | Difference from this repository and data gate | Cost / priority |
|---|---|---|---|---|---|
| 1 | **H28-7 directional, scale-persistent radiometric alteration fronts**: GeoDAWN K, Th, U plus Th/K and U/K extension grids. | Orientation-coherent, persistent ratio fronts may map alteration along buried fluid pathways even where no young surface trace is mapped. | Lithologic/soil boundaries, soil moisture, drainage and survey/levelling seams. | The repository already tested radiometric ratio values and gradient-magnitude front features as parts of wider augmentations, and those wider arms did not beat their controls. The specific direction-coherent, multi-scale persistence/line-integral operator is not shown as a separate holdout experiment. This is a related, lower-priority formulation—not a wholly new signal or source. Relevant rasters are present in the hash-pinned owner-mirror cache; they are not organizer-authenticated. Official source listing: [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) (source status is in `registry/sources.json`; no fresh retrieval was made in this review). | Low–medium, testable from cached inputs; low prior support after negative related ablations. **No numeric expected gain.** Not run: assigned lane absent. |
| 2 | **H27-16 paleo-geothermal deposits plus shallow-probe anomaly**: official DOE GDR #1391 sinter/tufa/travertine, 2 m temperature probes and Quaternary volcanic polygons. | Aligned fossil hydrothermal deposits with local positive probe residuals may mark upflow structures whose surface fault expression is absent or obscured. | Lacustrine tufa along Lake Lahontan shorelines; groundwater outflow plumes; volcanic contacts. | Uses data packages not present in the prepared feature stack; differs from the existing well/spring chemistry table. Metadata/listing is recorded at [DOE GDR #1391](https://gdr.openei.org/submissions/1391), but the package bytes were not obtained or independently hash-verified here. Earlier access checks recorded the GDR host as unreachable from this sandbox. **Blocked, not viable until official bytes and license/geometry are checked.** | Medium–high; external data acquisition and provenance required. No score estimate. |
| 3 | **H29-5 full routed-drainage/fan-apex collinearity**: unmodified USGS 3DEP elevation, conditioned flow directions/accumulation, stream outlet/knickpoint and fan-apex observations. | Transverse outlet/knickpoint alignments may preserve range-front structure where young bajada aggradation has buried a continuous scarp. | Resistant bedrock hogbacks crossed by streams; inherited drainage, roads and stratigraphic contacts. | The tested H29-5-PROXY used detrended relief and is explicitly not a routed-stream/fan-apex analysis; its negative result must not be represented as a test of this full hypothesis. The raw elevation and verified outlet observations are not in the restored cache. Official source: [USGS 3DEP](https://www.usgs.gov/3d-elevation-program). Earlier access checks recorded source retrieval as blocked here. **Blocked, not viable until DEM and conditioning inputs are obtained and pinned.** | Medium–high processing/data cost. No score estimate. |

### Gate decision

The protocol's lane paragraph is missing (`IR-2026-10-29-lane-paragraph-missing`). Therefore, although H28-7 is the only candidate in the table whose required raster bands are present in the restored cache, it cannot be run under this prompt without guessing a lane. No weekly slot was touched. If an authorized lane is later assigned to H28-7, the test must first be preregistered on fresh seeds; each input feature needs an individual leakage canary; compare against a matched current-best control on the exact same whole-FID buffered splits; and apply uniqueness screening before placement and after the final dots. A failed or unassigned experiment must not emit a submission-ready TIFF.

## Pass 1 — restore, inspect and audit

- Read `README.md`, `AGENTS.md`, the Session 18 review, H29-XG preregistration/run card and the current executive summary.
- Restored the 17 data-manifest inputs from immutable owner-repository GitHub commits; `scripts/restore_data.py --verify` reported all 17 hashes OK. The manifest explicitly says these are owner mirrors, **not organizer-authenticated downloads**.
- Ran `scripts/prepare_data.py`: recreated the ignored label-free prepared stack (32 features × 5,167,373 footprint cells; 100 m grid; EPSG:32611). The recorded SHA-256 is `83ed2704ee2de03cf8b1c8f2966fcf71813501df97c1c35400e6c0415393f6dc`.
- Restored 12 peer rasters from immutable GitHub commits and rechecked every SHA against `registry/parallel_submission_registry.json`; all 12 hashes and grids passed. The full output was directed to `/tmp/peer_relations_review.json`, leaving the checked-in historical evidence unchanged.
- Existing H29-XG evidence is negative: **HOLDOUT-DTI** candidate 0.0433718 vs control 0.0438777, paired mean Δ −0.0004685, 95% paired bootstrap CI [−0.0015458, +0.0006138], 126,011 withheld-positive occurrences, evaluator `gems27.metric.dti_binary` v1 (α=0.2, β=0.8, R=3 px triangular) on whole-FID buffered hides. Its pinned-set overlap maximum is 46.5%, but local overlap reaches 84.5%, above the 70% stop. It wrote no TIFF. No organizer score is estimated.

## Pass 2 — defect and completeness review

- Found a terminology inconsistency: an existing irregularity called H28-7 a duplicate of a tested family, while `registry/next_hypotheses.json` called its exact directional/persistence formulation untried. The evidence supports a nuanced distinction: radiometric value/front *features* appeared in earlier arms and those complete arms underperformed their controls; the exact orientation-coherent multi-scale lineament operator is not documented as a separate holdout. Updated the registry wording and recorded the distinction below. H28-7 remains low-priority and untested—not failed and not proven novel.
- The `0.2778` account and the 0.4413 / 0.3195 leaderboard figures are user/owner reports without organizer receipts. The project correctly has no numeric organizer-score estimate for any candidate. The exact file-to-score attribution for GEMSDOE32 is disputed in evidence.
- Existing broad candidate registry / historical summaries are finite snapshots. They cannot prove uniqueness against all public submissions; current conclusions must retain scope language.
- All values stated in this review are labelled by provenance. DTI figures are explicitly HOLDOUT-DTI; historical submissions are explicitly OWNER-REPORTED; no organizer-confirmed result is claimed.

## Pass 3 — full-request recheck and verification

The existing site/docs provide the requested executive summary, the nine-site file/score/uniqueness/submit table, and a bounded explanation of the GEMSDOE32 dot lineage. This review also records three candidate hypotheses and why the currently runnable one is not tested. However, no new top candidate was validated on holdout in this turn because the required lane paragraph is absent. An in-range, named, unique research TIFF exists (H33-1) but it failed efficacy and is explicitly **NOT OK TO SUBMIT**; H29-XG failed and wrote no TIFF. No candidate passed the combined scientific, uniqueness, matched-current-best and selector gates, so the requested approved submission does not exist. No numeric organizer-score estimate is defensible. The correct result is to withhold a file, not relabel an old or negative raster.

Verification run on restored cache:

- `.venv/bin/python -m pytest -q` after full cache restoration and the H28-7 regression test: **229 passed, 0 skipped**.
- `.venv/bin/ruff check src scripts tests`: **All checks passed**.
- `scripts/restore_data.py --verify`: **17/17 input hashes passed**.
- `scripts/fetch_parallel_registry.py`: **12/12 pinned peer hashes and grids passed**.
- `scripts/verify_peer_relations.py --out /tmp/peer_relations_review.json`: **12 peers read; two exact in-footprint duplicate pairs; 11 strict-subset relations**; no leaderboard scoring.
- `scripts/audit_submission_readiness.py`: **25 run cards reviewed; zero evidence-passed files and zero slot authorizations**.
- `scripts/build_site.py`: built six documentation pages, root index and executive summary.
- `scripts/verify_downloads.py`: **0 failures** for its existing configured artifacts. This verifies those historical bytes against local owner mirrors; it does not validate a new candidate or authorize submission.
- All repository JSON files parsed successfully; `ruff` and the test suite passed.

## Remaining work, in order

1. Obtain the actual assigned method paragraph before any new holdout experiment; otherwise protocol compliance prevents selecting a lane.
2. Resolve GEMSDOE32's score/file attribution and the conflicting current leaderboard figures using an organizer receipt/page screenshot supplied by the owner. Agent-side access to DrivenData remains prohibited by repository policy.
3. For any candidate, include the full and current peer registry (including the sibling GEMSDOE25 `xg1-crossgrad` file) with authenticated SHA pins and clarify whether uniqueness uses pre-placement continuous surfaces, final binary masks or both.
4. If H28-7 is assigned, use a fresh preregistration and seeds. Compare a matched current-best control on identical spatial blocks; report feature-alone AUCs, pooled HOLDOUT-DTI, paired confidence interval, seed/fold outcomes and complete duplication results.
5. Pursue H27-16 or full H29-5 only through permitted acquisition of their official source bytes; hash and validate geometry/coverage before calling either viable.
6. Align older research runners to the stricter policy of emitting a TIFF only after both efficacy and uniqueness gates pass. Keep selector/weekly-slot authorization separate.
7. Preserve all-finite [0,1] validation and the explicit download verdict; no unique filename or valid GeoTIFF is evidence of a high score.

## Run card — review only; no experiment

```json
{
  "hypothesis": "No new candidate tested; review-only session. H29-XG remains the latest experiment and is negative.",
  "mechanism": "Not applicable to this review; no feature or raster was generated.",
  "named_non_fault_process_that_could_mimic_it": "Not applicable; no new geological mechanism was tested.",
  "holdout_dti": {
    "status": "NOT RUN this session",
    "latest_prior_result_label": "HOLDOUT-DTI",
    "latest_prior_candidate": 0.043371801082373,
    "latest_prior_control": 0.04387770406333056,
    "latest_prior_paired_delta_ci95": [-0.001545779423320248, 0.0006137878023858685],
    "latest_prior_withheld_positive_occurrences": 126011,
    "evaluator": "gems27.metric.dti_binary v1; alpha=0.2, beta=0.8, R=3 px triangular; whole-FID buffered holdout"
  },
  "correlation_overlap_vs_registry": {
    "new_candidate": null,
    "scope": "No new candidate; latest prior H29-XG failed local 3-px overlap threshold. Historical site rasters only compared against the 12 pinned final-dot rasters."
  },
  "raster_sha256": null,
  "validator_output": {
    "new_candidate": "NOT APPLICABLE; no TIFF generated",
    "existing_configured_downloads": "scripts/verify_downloads.py passed with 0 failures after owner-mirror inputs restored",
    "new_candidate_no_nan_inside_footprint": null,
    "new_candidate_values_in_0_1": null,
    "new_candidate_crs_shape_transform_match": null
  },
  "submission_name": null,
  "submission_note": "No new TIFF produced; no download is approved for submission.",
  "verdict": "negative"
}
```
