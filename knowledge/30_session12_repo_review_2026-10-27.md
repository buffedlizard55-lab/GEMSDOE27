# Session 12 — repository audit, focus-site comparison, and hypothesis screen (2026-10-27)

## Executive decision

**No new TIFF was generated, and no file is authorized for a competition slot in this session.** The user's parallel-run instruction requires one assigned method paragraph; none identifying a single method is present in the current task. At session start, `data_cache/` was absent. I restored the hash-pinned shared inputs from the repository's GitHub mirrors and built the 32-column prepared stack (`5,167,373 × 32`, SHA-256 `83ed2704ee2de03cf8b1c8f2966fcf71813501df97c1c35400e6c0415393f6dc`); it is now available in ignored local cache. Data availability does not itself assign a method lane. Selecting a method or fabricating a score/raster would violate the protocol. No experiment or weekly slot was consumed.

The saved H31-1 file remains a historical, evidence-qualified research artifact, not this session's submission recommendation. Its saved HOLDOUT-DTI is 0.047302 under `gems27.metric v1 + holdout-blind-buffered-v2` (alpha 0.2, beta 0.8, 300 m triangular kernel, 6 px buffer), with 120,778 withheld-positive occurrences over seeds 400–409. The paired HOLDOUT-DTI improvement versus B0 has 95% CI [+0.0080,+0.0112]. This is catalogue-internal holdout evidence, not organizer-confirmed performance. The anchor-transfer estimate near 0.235 is a **PROJECTION**, not a score, and is not evidence that H31-1 beats the reported 0.2778.

## Scope and method of this audit

Read `README.md`, `AGENTS.md`, the latest audit and H31-3 result, the current hypothesis registry, relevant run cards, the submission-readiness implementation, and the generated executive-summary source. Checked the recorded focus-site evidence and repository status. No DrivenData page was accessed; repository policy prohibits automated access to `drivendata.org`. No official web source was newly fetched in this session; links below are provided for direct review and their current statuses remain those recorded in `registry/sources.json`.

## Nine focus sites — best recorded entry per site

All listed scores are **OWNER-REPORTED historical results**, not ORGANIZER-CONFIRMED receipts in this repository. They are not predictions for a new file. Existing peer files are for audit/education only and must not be copied or resubmitted.

| Site | Highest recorded submission | Reported result | New-file uniqueness / use |
|---|---|---:|---|
| GEMSDOE32 | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` | 0.2778 | Historical benchmark; do not copy/resubmit |
| GEMSDOE36 | `anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros` | 0.2750 | Historical; do not copy/resubmit |
| GEMSDOE28 | `h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan` | 0.2710 | User-supplied snapshot; repository's saved nine-site ranking gives 0.2708 for a different H28 entry. Conflict unresolved; do not treat as verified rank |
| GEMSDOE31 | `h27-4-solo-d28-20261004-8acb75e1-nan` | 0.2708 | User-supplied snapshot; repository's saved ranking gives 0.2710 for a different H31 entry. Conflict unresolved |
| GEMSDOE33 | `h33d-analog-tip-stepover-r30-20261004-cb490425926e` | 0.2632 | Historical; do not copy/resubmit |
| GEMSDOE25 | `dotted-h19-5-d2-8-20261002-e56ea318af89-nan` | 0.2600 | Historical H19-5 family; do not copy/resubmit |
| GEMSDOE30 | `d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca` | 0.2600 | Historical H19-5 family; do not copy/resubmit |
| GEMSDOE24 | `h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan` | 0.2477 | Historical H19-5 family; do not copy/resubmit |
| GEMSDOE27 | `topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan` | 0.2449 | Historical; no new file authorized |

The table is a reconciliation of the owner-supplied snapshot and saved repository evidence, not a fresh crawl. The GEMSDOE28/GEMSDOE31 rank/value mismatch is explicitly unresolved. Reported leaderboard maxima `0.3195` and `0.4413` conflict in the prompt and have no organizer receipt here; neither is confirmed.

### Current new-file decision (estimate and uniqueness are separate from permission)

| File | Score estimate | Unique vs the nine sites? | OK to download and submit now? |
|---|---|---|---|
| Existing H31-1 `docs/downloads/gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif` | **PROJECTION ~0.235** by single-anchor transfer; planning range 0.19–0.26 is not a confidence interval. No organizer score. | The saved historical 12-peer screen passed at max 57.7% 3-px overlap / surface Spearman ≤0.17; **not a current-registry uniqueness guarantee**. | **NO.** Research/audit download only. No selector authorization, current peer registry, or current cap record. No new TIFF generated in this session.

### Why GEMSDOE32 is the highest focus-site result

Saved byte-level evidence (`knowledge/12_why_02778_won.md`, `knowledge/18_why_02778_won_phd_analysis.md`, and `evidence/peer_h33_2_raster_recheck_2026-10-25.json`) reports exact pixel identity between the GEMSDOE32 submission and the GEMSDOE25 d=2.8 emission after removing catalogue-collar pixels within the stated distance threshold. The interpretation is a false-positive-budget improvement: nearby catalogue echoes can incur FP cost while offering little recoverable credit in a catalogue-derived test. This is a measured pixel relationship plus a plausible metric mechanism; it does **not** prove the organizer's hidden-label distribution or establish that the collar filter generalizes. It is exhausted as a method family and copying it would violate the explicit uniqueness rule.

## Candidate hypotheses screened before implementation

These are hypotheses, not results. The expected ΔDTI intervals below are **subjective planning priors only** (where copied from the existing hypothesis registry, they are attributed to that registry); they are not HOLDOUT-DTI measurements, leaderboard score estimates, or confidence intervals. Novelty means only “no matching experiment found in this checkout's code/evidence search,” not global novelty across competitors.

| Rank by nominal expected gain | Candidate, layers, and target signature | Why a catalogue-missing fault could be detected | Difference from tested repository work; named non-fault mimic | Expected ΔDTI prior / implementation cost / data gate |
|---:|---|---|---|---|
| 1 (blocked) | **H27-16: joint paleo-geothermal evidence.** GDR #1391 paleo-sinter/tufa/travertine/altered-rock vectors, 2 m temperature observations, and Quaternary-volcanic polygons. Target: multi-source spatial alignment of hydrothermal deposits, temperature residuals, and vent/volcanic context. | Fossil or active upflow deposits and shallow thermal anomalies may mark a buried permeable conduit even where no young surface rupture is catalogued. | These are independent observation geometries, not another catalogue-distance ring or raster edge feature. **Mimics:** lacustrine tufa/shoreline deposits, groundwater outflow, non-fault volcanic contacts. | Registry prior **+0.001 to +0.008**; medium-high. Official source recorded as DOE GDR submission 1391, DOI 10.15121/1881483. Raw bytes are absent; `gdr.openei.org` is outside this environment's outbound allowlist, so obtainability cannot be newly tested here. **Not viable until an authorized retrieval and SHA-256 verification succeed.** |
| 2 (top locally actionable if assigned) | **H29-5: transverse canyon-mouth knickpoint and fan-apex collinearity.** Existing DEM/LiDAR bands: `det_elev`, `det_local_relief`, `det_gradient`, `lidar_relief`, `lidar_cross_max`. Target: multi-canyon, 0.5–2 km along-front collinearity of channel-outlet knickpoints and fan apices. | Episodic fan aggradation can bury inter-canyon scarps, while topographic channel response and adjacent fan apexes can preserve a range-front alignment at a scale not represented by pixelwise scarp scores. | A multi-object geomorphic alignment operator, unlike existing per-pixel relief/curvature and ridge/edge transforms. **Mimic:** resistant stratiform hogbacks crossed by transverse streams; also drainage/lithology changes unrelated to faults. | Existing registry prior **+0.001 to +0.005**; medium implementation. The required local 32-column cache is now restored and hash-verified; an assigned lane and preregistered gate are still prerequisites. |
| 3 | **H28-6: gravity analytic-signal scale persistence.** `iso_grav_anom`, `iso_grav_anom_vg`, `iso_grav_anom_hg`, `iso_grav_anom_slope`. Target: persistence of edge/analytic-signal ridges across multiple smoothing scales, rather than raw anomaly amplitude. | A buried density boundary may remain coherent in gravity derivatives beneath alluvium where surface mapping and LiDAR scarp evidence are weak. | Exact standalone multiscale persistence transform was not found in the executed experiment ledger; H28-1 and H32 did test related potential-field combinations, so independence is limited. **Mimic:** basin-fill density transitions and lithologic contacts. | **Provisional expert prior 0 to +0.002**, low-medium implementation; no repo-measured gain. Cached feature matrix is restored and hash-verified. Lower priority because related geophysics were already tested. |
| 4 | **H28-7: directional radiometric-alteration lineament continuity.** GeoDAWN K/Th/U and ratio bands plus `TMI_up150`. Target: orientation-coherent, scale-persistent alteration fronts, not pixelwise ratio ranks. | Fault-controlled fluid flow can produce elongated alteration patterns beyond mapped surface traces. | The exact directional lineament operator was not found as an executed gate. However, Addendum D's radiometric-ratio feature arm was already negative (+0.0007 PR-AUC versus a +0.005 screen threshold); this is a new transform of a weakly supported signal, not a wholly untested data source. **Mimic:** lithologic/soil contrast, soil moisture and drainage. | **Provisional expert prior 0 to +0.002**, low implementation; no repo-measured gain. Lower priority than H29-5 because the additive ratio result was negative. |

**Selection:** H27-16 has the largest nominal upside but is data-blocked. H29-5 is the highest-ranked *locally testable* candidate in the saved registry, but this session did not implement or validate it: the assigned lane paragraph is absent, although the shared cache is now restored and prepared. Do not read this table as permission to implement or to spend a weekly slot. No candidate is shown to beat the current saved H31-S holdout benchmark.

### Required experiment if a method lane is later assigned

1. Restore and hash-verify the shared cached feature stack and template inputs; do not construct a private evaluator or writer.
2. Freeze one candidate transform, mimic, and expected direction in a preregistration; choose an unused seed range after auditing all prior seed reservations.
3. Run each feature alone through the leakage canary before trusting any model; use the direction-invariant criterion `max(AUC, 1-AUC) <= 0.90`.
4. Compare candidate and frozen baseline under identical whole-fault-segment, buffered hides; derive catalogue-based features only from visible faults, mask visible catalogue cells exactly, and use the shared pooled DTI evaluator (alpha 0.2, beta 0.8, 300 m triangular kernel). Report evaluator version, withheld-positive occurrence count, paired 95% CI, and per-fold/seed results.
5. Stop if pre-placement rank-correlation exceeds 0.90 or final dot overlap exceeds 70% within 3 px of any registry raster; log the duplicate and stop.
6. Require a preregistered holdout improvement over the frozen best before considering candidate generation. A separate selector must authorize a weekly slot; do not auto-select or upload.
7. Write a run card even for a negative. Only then may a new TIF be built; validate values `[0,1]`, no NaN inside the footprint, and exact CRS/shape/transform, then hash the new bytes and check all registry peers again.

## Repository review findings and fixes in this session

1. **Critical publication-language inconsistency:** README and generated executive page called H31-1 “OK TO DOWNLOAD AND SUBMIT” / “approved,” while `docs/data/submission_readiness_audit.json`, `evidence/readiness_audit_run_card_2026-10-26.json`, and `knowledge/28_submission_readiness_audit_2026-10-26.md` all state `slot_authorized: false` and no selector/cap evidence. The site generator now requires explicit selector authorization before presenting any submission download. H31-1, whose manifest has no such authorization, is clearly research/audit-only; the page says **NOT OK TO SUBMIT NOW**.
2. **Readiness JSON label:** `scripts/audit_submission_readiness.py` used a top-level `approved` list for passing machine evidence even though the slot remained unauthorized. It now separates `evidence_passed_not_slot_authorized` from `slot_authorized`.
3. **Stale comparison conflicts:** the owner prompt and saved evidence disagree on which of GEMSDOE28/GEMSDOE31 is 0.2710 vs 0.2708. Preserved as an explicit unresolved discrepancy; no guessed reconciliation.
4. **Training/cache restoration:** a local `.venv` was populated from `requirements.txt`; `scripts/restore_data.py` verified all 17 pinned inputs and assembled `training_features.tif` (418,912,844 bytes; SHA-256 `4371c82e…`); `scripts/prepare_data.py` created the 5,167,373 × 32 prepared feature matrix (SHA-256 `83ed2704…`). The 1.2 GB cache is ignored and not committed. `scripts/verify_downloads.py` then passed with 0 failures. No holdout rerun was performed because there was no assigned method lane. No new external official-source fetch or DrivenData access occurred.
5. **No new candidate TIFF:** correct under the current lane and evidence constraints. Creating a random, copied, re-thinned, or unvalidated GeoTIFF would be a false completion of the scientific requirement.

## Sources for review

These are the repository's recorded source links; source status is in `registry/sources.json`. They were not re-fetched during this session:

- [DOE GEMS competition problem statement](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) — no automated access in this session; project policy blocks `drivendata.org` requests.
- [DOE/NLR official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) — recorded in the source registry; reread date/status is shown there.
- [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution).
- [DOE Geothermal Data Repository / INGENIOUS submission 1391](https://gdr.openei.org/submissions/1391) — required for H27-16; raw package availability is not verified in this session.
- [USGS 3DEP 1-m DEM catalog record](https://data.usgs.gov/datacatalog/data/USGS:77ae0551-c61e-4979-aedd-d797abdcde0e) — source record for DEM context; this session did not test direct download availability.
- [Berkowitz et al. 2000, publisher record](https://agupubs.onlinelibrary.wiley.com/doi/10.1029/1999GL011241) — fracture-network scaling context, not evidence for any individual fault candidate.
- [Faulds & Hinz 2015, OSTI-hosted paper](https://www.osti.gov/servlets/purl/1724082) — Great Basin structural settings context; not a source of ground truth for the proposed candidates.

## Run card — this audit session

```json
{
  "hypothesis": "No assigned geological method paragraph was provided in the current parallel-run prompt; do not select a new method unilaterally.",
  "mechanism": "Repository and evidence audit only. Screened four candidate hypotheses; no new predictor, TIFF, or holdout score was produced.",
  "named_non_fault_process_that_could_mimic_it": "For the top locally actionable candidate H29-5: resistant stratiform hogbacks and drainage/lithology controls may align transverse channels without a fault.",
  "holdout_dti": "No new HOLDOUT-DTI. Saved comparator only: H31-S HOLDOUT-DTI=0.047302; evaluator gems27.metric v1 + holdout-blind-buffered-v2 (alpha=0.2, beta=0.8, 300 m triangular kernel, 6 px buffer), seeds 400-409, 120778 withheld-positive occurrences; paired delta vs B0 95% CI [+0.0080,+0.0112]. Not organizer-confirmed.",
  "correlation_overlap_vs_registry": "No candidate raster generated; no new surface or final-dot comparison. Historical H31 comparisons are stale relative to a current registry refresh.",
  "raster_sha256": null,
  "validator_output": "No new raster to validate. Existing H31-1 historical validator evidence is not slot authorization.",
  "submission_name_and_note": "None. No new TIF generated; submission note not assigned.",
  "verdict": "negative"
}
```
