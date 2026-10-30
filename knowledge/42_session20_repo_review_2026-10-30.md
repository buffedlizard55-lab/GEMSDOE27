# Session 20 repository review — 2026-10-30

## Executive decision

**No geological experiment was run, no new TIFF was produced, and no submission slot was selected. The active prompt again omits the single-method paragraph required by its parallel-run protocol.** Choosing a new geology lane without that assignment would violate the protocol and the repository's preregistration rule. There is no newly generated file that is OK to download and submit.

This session completed a three-pass repository and safety review. It found and fixed one substantive technical validation gap in the fail-closed publication audit: the audit previously verified the candidate's CRS/grid/band/value range from TIFF bytes but relied on self-reported validator booleans for zero values outside the competition footprint and zero overlap with catalogue fault pixels. The audit now independently reads the local template and labels in bounded raster windows and checks those two invariants against the candidate bytes. Missing/mismatched reference rasters fail closed. Tests cover nonzero out-of-footprint values, catalogue-cell predictions and a wrong-shape TIFF.

The reference template and labels are hash-pinned copies from owner GitHub mirrors. This byte validation does not make those files organizer-authenticated and is not a DrivenData receipt.

## Pass 1 — task and repository inventory

- Read `README.md`, `AGENTS.md`, the Session 19 repository review and the latest research/decision records before changing code.
- Confirmed the nine requested focus sites appear in `EXECUTIVE_SUMMARY.md` and the generated executive-summary page. Their historical scores are labeled **OWNER-REPORTED**, organizer-score estimates remain unknown, and all nine selected historical files are not offered as a new authorized submission.
- Confirmed the strongest claim for GEMSDOE32 is **OWNER-REPORTED 0.2778**, not an organizer receipt. The repository's byte audit describes it as nested pruning of the d=2.8 family, removing 6,436 dots inside a two-pixel catalogue collar. The reported sequence 0.2600 → 0.2708 → 0.2778 is compatible with reduced low-utility predictions but does not establish causality; the hidden truth and a score-to-file receipt are unavailable. A subset of this field would fail the local directed-overlap uniqueness rule by construction.
- Confirmed that the prompt's competing current-high claims, 0.4413 and 0.3195, are not independently verified in this repository. The source registry and `AGENTS.md` prohibit automated DrivenData access.
- Read the current three-candidate screen in `knowledge/41_session19_repo_review_2026-10-29.md`. It ranks H28-7 (direction/scale-persistent radiometric alteration fronts) as the most testable from the cached bands; H27-16 (paleo-geothermal deposits plus shallow probes) and full H29-5 routed-drainage/fan-apex analysis require additional data. Those are hypotheses, not validated score predictions. No numerical score estimate is justified.

## Pass 2 — reproducibility and integrity checks

The checkout began clean on `arena/e3944b7f-gemsdoe27`. Python 3.11 environment dependencies were installed from PyPI. No DrivenData host was contacted.

| Check | Result |
|---|---|
| `python scripts/restore_data.py` | 17 owner-mirror input files restored; all recorded SHA-256 pins matched. |
| `python scripts/prepare_data.py` | Rebuilt 5,167,373 × 32 label-free feature matrix, EPSG:32611, cache SHA-256 `83ed2704ee2de03cf8b1c8f2966fcf71813501df97c1c35400e6c0415393f6dc`. |
| `python scripts/restore_data.py --verify` | 17/17 input checks passed. |
| `python scripts/fetch_parallel_registry.py` | All 12 pinned peer rasters matched SHA-256 pins and template grids. This is an incomplete owner-mirror peer set, not a census of submissions. |
| `python scripts/verify_peer_relations.py --out /tmp/peer_relations_review_20261030.json` | 12 peer rasters checked; two exact in-footprint dot pairs: GEMSDOE25/GEMSDOE30 and GEMSDOE28 H27-4/GEMSDOE31; 11 strict-subset relations. |
| `python scripts/verify_downloads.py` | 0 failures for configured historical downloads, format, hashes, and local reference checks. Passing this does not establish scientific efficacy or slot authorization. |
| `python scripts/audit_submission_readiness.py` | 25 cards reviewed; 0 evidence-passed files; 0 weekly-slot authorizations. |
| `python scripts/build_site.py` | Built six documentation pages, root index and executive summary. |
| Ruff and compile check | `ruff check src scripts tests` passed; `compileall` passed. |
| Full test suite before safety change | 229 passed. |

## Pass 3 — adversarial review, changes and final verification

### Finding fixed

`publication_decision()` used the run card's `zeros_checks` for two properties not re-derived from candidate bytes: (1) every cell outside the sample-submission footprint is zero, and (2) no predicted value is one on a catalogue cell. An otherwise in-range GeoTIFF could therefore claim those booleans while violating the documented output contract. The independent validator now compares candidate, template and labels on their shared grid, rejects a reference-grid mismatch, and checks all candidate blocks for: float32 single-band GeoTIFF format, exact grid, no nodata/mask, finite whole-array [0,1] values, zero outside the footprint, and zero on catalogue cells. A shape/band mismatch returns a failed result rather than aborting the whole-card audit.

Changed files: `src/gems27/readiness.py`, `tests/test_readiness.py`, and the regenerated `docs/data/submission_readiness_audit.json`. Added negative tests for an in-range one outside the footprint, a one on a catalogue cell, and wrong raster shape. All 25 existing run cards still fail closed; the technical hardening does not promote any historical result.

### Final checks after the change

- `python -m pytest -q`: **232 passed**.
- `ruff check src scripts tests`: **passed**.
- `python -m compileall -q src scripts tests`: **passed**.
- `python scripts/restore_data.py --verify`: **17/17 passed**.
- `python scripts/verify_downloads.py`: **0 failures**.
- Readiness audit: **25 cards; 0 evidence passes; 0 slot authorizations**.
- `build_site.py` completed; `git diff --check` passed.

## Nine-site summary and decision

Listed values are **OWNER-REPORTED** from the user-provided ledger, not organizer receipts. No justified conversion from these numbers or local HOLDOUT-DTI to an organizer score exists.

| Site | Highest listed historical file / reported value | Uniqueness / action |
|---|---|---|
| GEMSDOE24 | `h25-1-dotted-h19-5-d1-5`; 0.2477 | Duplicate stop vs pinned peers; do not resubmit. |
| GEMSDOE25 | `dotted-h19-5-d2-8`; 0.2600 (score/file attribution disputed) | Dot-identical to GEMSDOE30; do not resubmit. |
| GEMSDOE27 | `topo-gap-closure-t-v2-on-d1-5`; 0.2449 | Duplicate stop vs pinned peers; do not resubmit. |
| GEMSDOE28 | `h36-1-rung30-blind-r1`; 0.2710 | Duplicate stop; related H27-4 dots identical to GEMSDOE31; do not resubmit. |
| GEMSDOE30 | `d28-poisson300m-offcat-44090`; 0.2600 (attribution disputed) | Dot-identical to GEMSDOE25; do not resubmit. |
| GEMSDOE31 | `h27-4-solo-d28`; 0.2708 | Dot-identical to GEMSDOE28 H27-4; do not resubmit. |
| GEMSDOE32 | `h33-h33-2-b2`; 0.2778 | Owner-reported, peer audit calls the file unscored; nested subset; do not resubmit. |
| GEMSDOE33 | `h33d-analog-tip-stepover-r30`; 0.2632 | Duplicate stop vs pinned peers; do not resubmit. |
| GEMSDOE36 | `anderson-geothermal-pinn`; 0.2750 | Duplicate stop vs pinned peers; do not resubmit. |

Uniqueness here is limited to the 12 SHA-pinned final-dot rasters. The complete pre-placement surfaces and a complete global registry are not present; therefore this result cannot establish global uniqueness. Historical score attribution is not organizer-confirmed.

**Current download decision: NOT OK TO SUBMIT.** The available newly generated research TIFF H33-1 failed its frozen efficacy gate: HOLDOUT-DTI 0.025211 vs control 0.041446, paired 95% CI [−0.017576, −0.014449], 134,150 withheld-positive occurrences. It is also not a matched current-best result and not slot-authorized. H29-XG was negative and emitted no file. Passing a TIFF validator or being unique within a limited registry would not override these failures.

## Ranked candidate screen (hypotheses, not score promises)

The ranking below prioritizes testability and expected value per effort; none has a numerical predicted DTI gain. The full novelty limits and source statuses are documented in the linked Session 19 screen and `registry/next_hypotheses.json`.

1. **H28-7, directional and scale-persistent radiometric alteration fronts.** Layers: GeoDAWN K, Th, U and ratio grids. Target: orientation-coherent, multi-scale persistent ratio boundaries potentially caused by alteration along a buried fluid pathway, including where no young fault trace is mapped. Named mimics: lithologic and soil boundaries, soil moisture/drainage and survey seams. Novelty is limited: ratio/front features were included in earlier broad tests; this exact direction/persistence operator is not a wholly new source and still needs its own preregistered holdout. Raster bands are locally hash-pinned owner mirrors, not organizer-authenticated.
2. **H27-16, paleo-geothermal deposits plus shallow-temperature residual.** Layers: official DOE GDR #1391 sinter/tufa/travertine, shallow temperature probes and Quaternary volcanic polygons. Target: spatially aligned fossil hydrothermal deposits and local probe anomalies that could reveal buried upflow structures. Named mimics: Lake Lahontan shoreline tufa, groundwater outflow and volcanic contacts. Source listing is recorded, but raw packages were not obtained or hash-verified in this checkout; blocked until official bytes/coverage/license are checked.
3. **H29-5 full routed drainage and fan-apex collinearity.** Layers: official USGS 3DEP DEM, conditioned flow routing/accumulation and validated stream outlets/fan apices. Target: transverse range-front outlet/knickpoint alignments where bajada deposition could bury a continuous scarp. Named mimics: resistant bedrock hogbacks, inherited drainage, roads and stratigraphic contacts. Previous detrended-relief proxy is not a test of this full hypothesis. Required raw DEM/observations are not in the cache, so blocked pending acquisition and hash/coverage validation.

Because the protocol's specific assigned lane paragraph is absent, no top candidate was run. No weekly slot was considered. This review does not claim a score improvement.

## Limitations and work still required

1. The lane paragraph must be supplied before a new method can be selected and preregistered; do not invent an assignment.
2. An organizer-authorized human must resolve the 0.2778 score/file attribution and the conflicting 0.4413/0.3195 leaderboard claims. The agent must not access DrivenData or upload files.
3. The peer registry is incomplete. Add authenticated hash pins for new sibling submissions before claiming uniqueness; pre-placement continuous-surface comparisons are missing for historical peers.
4. H28-7 needs per-feature leakage canaries, fresh whole-segment buffered hide-and-recover splits, exact visible-fault masking, full-kernel pooled DTI and a matched current-best comparison before any raster emission.
5. H27-16/H29-5 require obtaining official source bytes, checking licence/coverage/grid, and recording hashes before either is considered viable.
6. The upload error's original file and cause remain unknown. Local all-finite validation mitigates the NaN/range ambiguity but cannot guarantee portal acceptance.
7. Keep the separate selector and weekly-cap checks distinct from technical and scientific validation; none is established by this session.

## Official/manual-review references

These references are cited in the repository source registry; this session did not fetch external source pages. Review using a browser if required:

- DrivenData competition overview (manual only): <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>
- DrivenData official rules (manual only): <https://www.drivendata.org/competitions/306/competition-doe-gems/>
- DOE GDR #1391 INGENIOUS: <https://gdr.openei.org/submissions/1391>
- USGS GeoDAWN airborne survey: <https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and>
- USGS 3DEP: <https://www.usgs.gov/3d-elevation-program>
- INGENIOUS project: <https://gbcge.org/current-projects/ingenious/>
- EPSG:32611: <https://epsg.io/32611>
- Reference solution: <https://github.com/drivendataorg/gems-prize-reference-solution>
- Source status and irregularities: `registry/sources.json`, `registry/irregularities.json`.

## Run card — review only, no experiment

```json
{
  "hypothesis": "No new hypothesis tested; Session 20 was a repository and submission-safety review. The current prompt omits the assigned method paragraph.",
  "mechanism": "No geological mechanism evaluated in this session. The existing highest reported GEMSDOE32 value is consistent with removing low-utility dots near the known catalogue, but does not prove a causal gain.",
  "named_non_fault_process_that_could_mimic_it": "For the leading untested H28-7 candidate: lithologic/soil boundaries, soil moisture and drainage, or survey/levelling seams can mimic radiometric alteration fronts.",
  "holdout_dti": {
    "status": "NOT RUN this session",
    "latest_prior_result_label": "HOLDOUT-DTI",
    "latest_prior_candidate": 0.043371801082373,
    "latest_prior_control": 0.04387770406333056,
    "latest_prior_paired_delta_ci95": [-0.001545779423320248, 0.0006137878023858685],
    "latest_prior_withheld_positive_occurrences": 126011,
    "evaluator": "gems27.metric.dti_binary v1; alpha=0.2, beta=0.8, 300 m triangular kernel; whole-FID buffered holdout; latest prior H29-XG result, not a Session 20 measurement"
  },
  "correlation_overlap_vs_registry": {
    "new_candidate": null,
    "scope": "No new raster. The 12 pinned peer rasters were rechecked; the registry is not a global census and continuous peer surfaces are unavailable."
  },
  "raster_sha256": null,
  "validator_output": {
    "new_candidate": "NOT APPLICABLE; no TIFF generated",
    "readiness_audit": "25 cards reviewed; 0 evidence passes; 0 slot authorizations",
    "historical_download_verifier": "0 failures; local owner-mirror checks only",
    "new_candidate_no_nan_inside_footprint": null,
    "new_candidate_values_in_0_1": null,
    "new_candidate_crs_shape_transform_match": null
  },
  "submission_name": null,
  "submission_note": "No new TIFF generated. Existing H33-1 is research-only and NOT OK TO SUBMIT.",
  "verdict": "negative"
}
```
