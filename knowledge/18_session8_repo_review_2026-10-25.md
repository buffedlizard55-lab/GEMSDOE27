# Session 8 repository review — 2026-10-25

## Outcome and evidence boundary

This was a review/triage pass, not a new model experiment. The working tree started clean. The root README and `AGENTS.md` were read first. Existing preregistrations, run cards, TIFF receipts, research status and source registry were checked. No competition site was accessed, no slot was used, and no score is newly claimed.

The most recent measured detector result remains the D-refill holdout confirmation recorded in `knowledge/17_h29_1_result_and_02778_answer.md` and the L-DCONFIRM results in `knowledge/16_dconfirm_result.md`: **HOLDOUT-DTI**, `gems27.metric` v1 (α=0.2, β=0.8, 300 m triangular kernel), D vs full-stack B = 0.10659 vs 0.09917, paired Δ=+0.00760, 95% CI [+0.00489,+0.01038], 121,404 withheld-positive occurrences, seeds 215–224. This does not certify a submission: the generated D-family TIFFs exceed the frozen 70% 3-pixel overlap threshold against the repo's unscored H28-1 research raster; cross-session D-family overlaps also exceed the threshold. Accordingly `ok_to_submit=false` remains correct.

### Current candidate screen (planning priors, not scores)

| Rank | Candidate | Specific layers/signature | Why it could locate an uncatalogued fault | Difference from this repo | Expected holdout ΔDTI / cost / gate |
|---:|---|---|---|---|---|
| 1 | **H29-2: dip-shifted basement-edge correction** | Potential-field analytic-signal/tilt/gradient ridges, `depth_to_base_surf`, and available NBMG `DIPDIRECT`/dip attributes; shift candidate edges by a physically bounded up-dip offset | A dipping fault's basement expression can be laterally displaced from its surface trace; a geometry correction may place predictions at the hidden surface-fault location rather than the raw geophysical edge | No dip-conditioned displacement transform appears in the inspected repository methods. It is not another threshold/thinning tweak | Prior 0 to +0.008; medium cost. Official/local source attributes must be hash-traced, and folds must derive catalogue distances from visible faults only. Needs fresh preregistered holdout; **not run this review** |
| 2 | **H29-3: soft-probability emission** | Arm-D detector probabilities, optimized as continuous values under the exact soft DTI rather than binary 38k dots | Calibrated uncertainty can reduce false-positive penalty in ambiguous regions while retaining fractional credit around plausible hidden faults | Existing competition rasters reviewed are binary; this changes decision/representation, not just spatial ranking | Prior −0.005 to +0.010; low-medium cost. Must compare against binary at a frozen operating point, evaluate canary per feature, and validate the true submitted-value range. **Not run this review** |
| 3 | **H28-4: anisotropic seismicity-fabric persistence** | `deq_n100a15`, `ieq_n100a15`, `geod_shearrate`; directional persistence across scales | A blind active strand may organize seismicity into a linear fabric in the absence of a young scarp | Prior audits used these bands as scalar predictors; directional persistence is a distinct transform, unlike refuted oriented terrain/geophysics line integration | Prior 0 to +0.002; low-medium cost, data already in restored feature stack. Fresh blocked test required. **Not run this review** |
| 4 | **H27-16/H28-5: quality-screened hydrothermal observations** | Official GDR sinter/travertine/altered-rock vectors, 2 m probe temperature, volcanics polygons; or deduplicated well/spring temperatures and geothermometers as short-scale gradients | Fluid chemistry/thermal anomalies may mark permeable structures missed by a surface-fault inventory | Prior thermal-distance feature was near-null; this tests independent observations, quality control and gradient geometry rather than isotropic distance | Prior 0 to +0.006; high cost and data-blocked. GDR raw packages are not present/hash-verified in this checkout; do not treat listing/pins as data obtained. **Not viable until bytes and provenance verify** |

These are method-level novelty claims relative to inspected repository code and records only. The sibling sites' complete code was not fetched here; global novelty is unknown. Values above are subjective experiment-planning priors, not measured DTI, organizer score projections, or promises.

## Verification / limitations observed

- `.venv/bin/python -m pytest -q`: **92 passed, 3 skipped**. Skips are the repository's marked unavailable-data checks; this does not restore input rasters.
- `.venv/bin/ruff check src scripts tests`: **All checks passed**.
- `.venv/bin/python scripts/verify_downloads.py`: could not complete because `data_cache/sample_submission.tif` is absent. It fails at the raster open with `RasterioIOError`; this is an input-availability failure, not a TIFF validation pass/fail. Do not claim a fresh end-to-end verification from this command. Existing per-file receipts under `docs/downloads/research/checks-*.json` and run cards are recorded evidence, not a replacement for re-reading the TIFFs with the competition template.
- `data/` contains only the small manifest; no `data_cache/` is available. The DrivenData download remains login-gated per prior verified project record. No DrivenData credentials or upload access are present/used.
- Existing candidate TIFFs are research artifacts with differing statuses. In particular, H29-1/D-confirm files pass recorded raster format checks but fail the extended uniqueness gate. **No file currently has permission/badge to download and submit as a unique candidate.** The artifact's existence is not an endorsement.
- The root README already retains the operative user task and Core Values, current STOP policy, and submission steps. It must continue to be read at session start. Site generation is JSON-driven; changing source records without rebuilding pages risks stale site text.

## Required next actions

1. Restore the hash-pinned `data_cache/` inputs through an authorized source/runner, then rerun `prepare_data.py`, `verify_downloads.py`, and raster-dependent tests. Do not claim the download script succeeded unless its logs and hashes prove it.
2. Resolve the selector's frozen-registry question (IR-2026-10-25-06) in a recorded decision. Do not silently waive H28-1 from the duplicate screen; any policy change must be a selector action, not a model-side edit.
3. Choose one of H29-2, H29-3, or H28-4 only after reviewing data readiness; freeze an exact preregistration and fresh seeds, then execute the leakage canary and paired holdout. Do not use exhausted seed ranges. Stay within the session's experiment/time budget.
4. Do not create a green “OK TO SUBMIT” badge or promote a file unless efficacy, canary, uniqueness and byte-level template validation all pass. Human upload and organizer receipt remain separate, owner-controlled steps.
5. Investigate the GDR workflow's prior zero-job runs or obtain package bytes from an authorized official source and verify SHA-256 before H27-16/H28-5.

## Review passes

1. **Pass 1 — implementation/status:** no new feature implementation warranted: the leading detector increment and its two-session confirmation already exist; available TIFF candidates are gated negative by uniqueness. Existing ranked hypotheses reviewed and refreshed here.
2. **Pass 2 — bugs/assumptions:** detected a verification limitation: the standalone download verifier currently aborts before checks when the competition template is absent. Reported accurately; did not mask this by bypassing template comparison or synthesizing a template. The three skipped tests likewise remain a data-coverage gap.
3. **Pass 3 — request fit:** prompt's requirement for an obvious unambiguous submission state is met by STOP/DO NOT SUBMIT language, not by an unsafe download button. A unique TIF exists as research output, but no one is certified to submit. No leaderboard score, live receipt, official source fetch, or external-data success was invented. Remaining work is listed above.
