# Session 20 repository review — 2026-10-30

## Decision

**No experiment was run, no candidate TIFF was generated, and no submission slot was used. No file is approved to download and submit.** The parallel-run prompt specifies a lane as “the single method paragraph below” but contains no method paragraph. Selecting a method ourselves would violate the lane restriction. The current repo's last recorded experimental decision remains negative: H29-XG failed its efficacy gate and duplicate stop; the H33-1 raster is research-only and failed its holdout gate.

This is a repository/quality review, not new scientific evidence and not an organizer score. The reported GEMSDOE32 value 0.2778 remains OWNER-REPORTED; it is not an organizer receipt. Neither the prompt's conflicting leaderboard highs (0.4413 and 0.3195) was independently read or verified. Do not claim a score projection or promise a higher score.

## GEMSDOE32 0.2778: evidence-based interpretation

The owner-mirror audit documented in [Session 19](41_session19_repo_review_2026-10-29.md) found the H33-2/B2 dot mask to be a strict subset of GEMSDOE25's d=2.8 mask, with 6,436 removed dots at catalogue distances no greater than two pixels. The remaining dots have minimum catalogue distance 2.236 pixels. The listed values 0.2600 → 0.2708 → 0.2778 are user-/owner-reported and do not establish that collar pruning caused the score increase. Such pruning is consistent with improving a precision-weighted DTI objective when removed candidates have low marginal utility, but causal credit requires blind labels or a valid matched holdout. Further narrowing that same raster family is not a distinct strategy and risks duplication. The audit also reports a sibling-source disagreement about whether the 0.2778 item was actually scored; resolve only from an organizer receipt, not inference.

Therefore, **the repo does not establish that a unique submission can beat 0.2778**, and it does not support estimating a leaderboard score from holdout DTI. The current documented local holdouts are diagnostics, not calibrated leaderboard projections.

## Ranked hypotheses to consider after a lane is assigned

This is a desk-screen only, drawn from the prior repo review/registry; it is not a new experiment or a claim of efficacy. “Potential” is qualitative because there is no validated mapping from holdout DTI to leaderboard score.

| Rank | Candidate; layers | Target signature and catalogue-missing rationale | Named non-fault mimic | Novelty relative to repo | Cost / gate |
|---|---|---|---|---|---|
| 1 | **Directional, multiscale radiometric alteration-front persistence** — GeoDAWN K, Th, U, Th/K, U/K. | Coherent, persistent directional ratio edges as a possible alteration halo along buried fluid pathways without a mapped young surface trace. | Lithology/soil boundaries, moisture/drainage, survey seams. | Related radiometric values/front gradients have occurred in broader arms; this exact orientation-coherent persistence operator is not documented as a separately validated test. Not a new data source. | Low–medium if pinned cached bands are available; proceed only with assigned lane, per-feature canaries, fresh blocked folds, matched control, uniqueness screen. Previous related negative arms lower priority. Official listing: [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and). |
| 2 | **Paleo-geothermal deposits plus shallow-temperature residuals** — DOE GDR #1391 sinter/tufa/travertine, shallow probes, Quaternary volcanic polygons. | Spatial association of fossil hydrothermal deposits and local temperature residuals could flag concealed upflow structures. | Lahontan shoreline tufa, groundwater discharge, volcanic contacts. | Distinct from existing well/spring chemistry features; exact official package has not been downloaded or hash-verified in this environment. | Medium–high; blocked until official package bytes, licensing, coverage and geometry are checked. Source metadata: [DOE GDR submission 1391](https://gdr.openei.org/submissions/1391). Not currently viable from this checkout. |
| 3 | **Routed drainage/fan-apex structural alignment** — conditioned USGS 3DEP elevation, flow direction/accumulation, stream outlets/knickpoints, fan apices. | Range-front discontinuities may be expressed by aligned outlets or knickpoints where aggradation conceals scarps. | Bedrock resistance/hogbacks, inherited drainage, roads, stratigraphic contacts. | Earlier H29-5 proxy used detrended relief; it is not equivalent to explicit routed drainage and fan-apex analysis. Raw conditioned DEM/observations are absent from this checkout. | Medium–high; blocked until the official DEM and required observations can be obtained and pinned. Source: [USGS 3DEP](https://www.usgs.gov/3d-elevation-program). |
| 4 | **Subsurface temperature-gradient residuals along mapped stratigraphic boundaries** — official shallow temperature / well logs and geologic map contacts. | Localized departures from regional thermal trend near permeable contacts could indicate concealed fluid pathways and faults. | Sampling bias, well construction/depth, groundwater circulation, lithologic conductivity. | Not established as a validated spatial residual surface in repo; overlaps existing chemistry/well evidence and requires new sourced records. | High; only consider after a specific official dataset with downloadable records and coordinate/depth metadata is verified. |
| 5 | **Magnetic analytic-signal edge + remanence-robust multiscale ridge agreement** — GeoDAWN magnetic channels and derivatives. | Scale-stable lineaments in analytic-signal amplitude may expose basement discontinuities irrespective of magnetization direction, including buried structures. | Lithologic contacts, dikes, cultural noise, flight-line artifacts. | Magnetic derivatives/edges already appear in the existing feature stack; this is a specific remanence-robust consensus operator, not a new source. | Medium if stack has channels; low expected novelty given related tested features. Must have an individual canary and fresh spatial blocks. Official source listing: [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and). |

Ranks describe experiment priority conditional on lane/data gates, not predicted scores. For candidates 2–4, data acquisition cannot be called successful based on a landing page alone. The host allowlist for this agent does not include USGS or GDR; this session did not verify current package bytes or availability. Official source links are provided for subsequent review.

## Repository review / three passes

### Pass 1 — baseline and scope

- Working tree started clean on `arena/1812ef2c-gemsdoe27`, based on the available shallow checkout at `bdbc3c9`.
- Read README operating brief, executive-summary artifacts, latest Session 19 review, scripts/tests layout, and current irregularities registry.
- Confirmed README says no current submission is approved and preserves the missing-lane constraint.
- No `data_cache/` files are present. `data/manifest.json` is metadata only; ignored data is not included in this checkout.

### Pass 2 — executable checks

- Created an ignored local virtual environment and installed declared requirements; no repository dependencies or tracked files were changed.
- `.venv/bin/pytest -q`: **226 passed, 3 skipped** (17.81 s). The skip count differs from prior full-cache reports; this checkout lacks the owner-mirror inputs and data-dependent tests are skipped. These results do not reproduce the prior 229-pass full-cache run.
- `.venv/bin/ruff check src scripts tests`: passed.
- `.venv/bin/python -m compileall -q src scripts`: passed.
- `git diff --check`: passed.
- `.venv/bin/python scripts/build_site.py`: built 6 pages, root index, and executive summary. It left no tracked changes.
- `.venv/bin/python scripts/verify_downloads.py`: **blocked/exit 2**, missing `data_cache/sample_submission.tif`, `labels.tif`, `dotted_h19_5_d1_5_nan.tif`, `h19_5_nan.tif`. It explicitly recommends restoring the owner-repository mirror; this is not organizer-authenticated data.
- `.venv/bin/python scripts/audit_submission_readiness.py`: completed; **zero evidence-passed files and zero slot authorizations**. Existing run cards fail closed for missing evidence, failed gates, or absent raster files. A byte-valid historical raster does not change that decision.

### Pass 3 — risk and requirements audit

- **Highest-priority protocol issue:** missing lane paragraph means no experiment or candidate selection can comply. Preserve the stop rather than generating an unvalidated TIFF.
- **Unique-download blocker:** no new TIFF has passed all pre-/post-placement screens and holdout efficacy gates. The H33-1 file remains a failed research artifact and must not be presented as submit-ready.
- **Score-estimation limitation:** historical numbers in user prompt are not organizer receipts; holdout DTI is not a leaderboard score estimator. Executive summary must keep these labels separate.
- **Peer scope:** historical uniqueness is limited to the pinned owner-mirror rasters; no claim of global uniqueness is justified. Current live registry completeness is unknown.
- **Data provenance:** local missing-data verifier is correctly fail-closed. Restoring owner mirrors would support local reproducibility but not establish organizer provenance.
- **Process wording:** user requests a PR and merge to main. The session must preserve Arena's assigned branch; PR creation can be considered from this branch, but direct merging is subject to repository policy and must not be represented as complete unless `gh` confirms it.

## Required next actions

1. Obtain the exact single-method lane paragraph; until then do not run an experiment or write a candidate TIFF.
2. Restore data using the documented `python scripts/restore_data.py`, then rerun `verify_downloads.py`; record source provenance accurately as owner-mirror, not organizer download.
3. Resolve the 0.2778 score/file attribution and current leaderboard figures from organizer receipts/page via permitted human review; update evidence with date and evidence source.
4. Refresh/expand pinned peer rasters and score provenance; compare both pre-placement surfaces and final dots where source rasters exist.
5. Once a lane is assigned, preregister one ranked hypothesis, use fresh whole-segment spatial folds with visible-only catalogue-derived features, run feature-by-feature leakage canaries, and compare to the current best on matched folds. Respect the three-experiment/two-hour budget.
6. Only after positive HOLDOUT-DTI efficacy with CI, full uniqueness scope, automated TIF validation and a separate selector authorization should a submission be marked **OK TO DOWNLOAD AND SUBMIT**. Never describe holdout DTI as a predicted organizer score.

## Run card

```json
{
  "hypothesis": "No experiment; candidate screen only because the assigned lane paragraph is absent.",
  "mechanism": "No new mechanism was evaluated this review.",
  "named_non_fault_process_that_could_mimic_it": "Not applicable to a no-experiment review; candidate mimics are listed in the ranked table.",
  "holdout_dti_and_ci": "Not measured this session; no withheld positives.",
  "correlation_overlap_vs_registry": "Not measured this session; no new surface or dots.",
  "raster_sha256": null,
  "validator_output": "No new raster. Existing readiness audit: zero evidence passes, zero slot authorizations. Download verifier blocked by missing local inputs.",
  "submission_name_and_note": "None; no candidate TIFF generated.",
  "verdict": "negative"
}
```

## Arena session 20 follow-up verification (2026-10-30)

A second review pass on the tracked Arena branch independently repeated the source checks after installing the declared requirements into an ignored `.venv`: `.venv/bin/python -m pytest -q` reported **226 passed, 3 skipped**; `.venv/bin/ruff check src scripts tests` passed; `scripts/build_site.py` built 6 pages and the executive summary without tracked generated-file changes; `scripts/audit_submission_readiness.py` completed with no slot authorizations. `scripts/verify_downloads.py` again exited 2 because the four local `data_cache/` inputs listed above are absent. No candidate raster or new experiment was produced.

Additional correction: the README previously asserted that the NaN-outside file caused the user's [0,1] submission error. The exact file used in that attempt is not identified, so causation is unknown. README now states this limitation and prefers all-finite output only as a precaution for a whole-raster range check; this is not evidence of organizer acceptance.
