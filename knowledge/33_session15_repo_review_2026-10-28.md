# Session 15 repository review — 2026-10-28

## Executive decision

**No submission is approved. No new TIFF was generated and no competition slot was used.** The existing H33-1 raster is an independently byte-validated, unique *research artifact*, but its frozen holdout result is substantially below its control. The H29-5 relief-profile proxy also failed its paired efficacy gate and exceeded the directed-overlap stop against a local registry raster. The repo contains no evidence that a newly generated candidate can exceed GEMSDOE32's reported 0.2778, or any current organizer-confirmed leaderboard high.

The 0.2778 value remains **OWNER-REPORTED**, not ORGANIZER-CONFIRMED: no submission-page receipt is stored. The submitted file should not be copied or renamed. Its measured relationship to the GEMSDOE25/28 family is useful for understanding the reported result, but geometry alone cannot establish why it earned that score or forecast performance on undisclosed organizer labels. No calibrated organizer-score estimate exists for the negative H33-1 artifact.

## Pass 1 — repository, provenance and requirement audit

Read `README.md` first, then `AGENTS.md`, the generated executive summary, the nine-site registry, the most recent preregistration and run cards, the shared validation/readiness code, and CI. The current data/code architecture reuses shared holdout, metric, writer, readiness and uniqueness modules; the latest evidence does not justify starting another emission or tuning run in the completed H29-5-PROXY/H33-1 lanes.

### Focus-site decision table

Values and file links are recorded in `EXECUTIVE_SUMMARY.md` and `registry/focus_sites_2026-10-26.json`. All historical values below are **OWNER-REPORTED**, not organizer receipts. “Best reported” does not mean a recommended file to upload; all nine files are already in the measured peer registry and are not new submissions.

| Site | Best recorded historical file | OWNER-REPORTED value | Review action |
|---|---|---:|---|
| GEMSDOE24 | `h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan` | 0.2477 | Historical; do not resubmit |
| GEMSDOE25 | `dotted-h19-5-d2-8-20261002-e56ea318af89-nan` | 0.2600 | Historical; do not resubmit |
| GEMSDOE27 | `topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan` | 0.2449 | Historical; do not resubmit |
| GEMSDOE28 | `h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan` | 0.2710 | Historical family; do not resubmit |
| GEMSDOE30 | `d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca` | 0.2600 | Dot-identical to GEMSDOE25 according to recorded comparison; do not resubmit |
| GEMSDOE31 | `h27-4-solo-d28-20261004-8acb75e1-nan` | 0.2708 | Dot-identical to GEMSDOE28 solo according to recorded comparison; do not resubmit |
| GEMSDOE32 | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` | **0.2778** | Focus-set reported maximum; do not copy or resubmit |
| GEMSDOE33 | `h33d-analog-tip-stepover-r30-20261004-cb490425926e` | 0.2632 | Historical; do not resubmit |
| GEMSDOE36 | `anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros` | 0.2750 | Recorded exact-superset relation; do not resubmit |

The GEMSDOE28/GEMSDOE31 ownership/value pairing and several cross-site score-to-file associations have previously been reported inconsistently. The table preserves the current pinned registry interpretation, not independent organizer confirmation. The broader source inventory is snapshot-limited and cannot prove global uniqueness against every competition submission.

### Ranked future geological hypotheses

The order below is a qualitative research priority only; **prospective score gains are unknown**, not numerical estimates. These are already registered ideas, not claims of novelty against all sites or competitors. Candidate #1 from the prior preregistration (H29-5 *proxy*) has already been tested and was negative; it is not mislabeled as an untried method here.

| Priority | Layers and signature | Why it might find a catalogue-missing structure; named mimic | Difference from current code / cost | Data gate and status |
|---|---|---|---|---|
| 1 | **H27-16:** DOE GDR 1391 paleo-sinter/tufa/travertine vectors, shallow 2 m temperature-probe records and Quaternary volcanic polygons; test spatially aligned hydrothermal-deposit traces with local temperature residuals. | Fossil discharge deposits may persist where young surface rupture is absent; lacustrine tufa, groundwater outflow and volcanic/lithologic contacts can mimic the pattern. | Adds independent observation types rather than another transform of the existing GeoDAWN bands; medium-high implementation and provenance cost. | Official listing: [GDR submission 1391](https://gdr.openei.org/submissions/1391), DOI 10.15121/1881483. The repository records a prior page read, but raw packages are absent from this checkout and not re-fetched/rehash-verified in this review. **Blocked, not viable for a new holdout now.** Obtain and independently pin official bytes before preregistration. |
| 2 | **H28-6:** gravity anomaly, vertical derivative, horizontal gradient and slope; test scale-persistent analytic-signal/edge ridges rather than single-scale amplitude. | A buried density boundary could persist beneath alluvium when surface scarps are weak; basin-fill transitions, lithologic contacts and regional-field artifacts mimic it. | A stand-alone multiscale persistence ablation differs from prior mixed potential-field features; low-medium code cost. | Bands are described in the feature stack and hash-pinned inputs have now been restored into ignored `data_cache/`; the derived model matrix has not been prepared in this review. The data manifest identifies owner-mirror copies, not direct organizer-authenticated bytes. It is the most practical computational follow-up after preparing/checking the required arrays, selecting a lane, and preregistering fresh seeds. No holdout result exists. |
| 3 | **H29-5 actual drainage:** unmodified elevation plus a conditioned/routed drainage network; test aligned range-front outlet/knickpoint/fan-apex positions over 0.5–2 km. | Aggradation can hide a scarp while drainage outlets retain range-front geometry; inherited drainage, resistant bedrock, roads and stratigraphic contacts mimic it. | Different from the tested H29-5-PROXY (detrended-relief slope contrast/concavity), which did not calculate streams or fan apices; medium-high processing cost. | Official source link: [USGS 3DEP](https://www.usgs.gov/3d-elevation-program). The repo's source record says unmodified DEM/routing inputs were not retrieved and the listing was not freshly checked. **Not viable until raw DEM and conditioning inputs are obtained and provenance checked.** Do not describe the proxy's result as a drainage result. |
| 4 | **H28-7:** K, Th, U, their ratios and TMI-upward-continuation band; test orientation-coherent, scale-persistent radiometric alteration fronts. | Fault-controlled fluid flow may make elongated alteration patterns beyond mapped traces; soil/weathering, lithology, moisture and survey seams mimic them. | Tests a directional/persistence operator, not just additive ratio ranks; low code cost but low prior support. | Existing radiometric layers are only represented here through owner-mirror data. The recorded additive-ratio ablation was weak/negative. Require independent feature canaries, fresh paired blocked holdout, and exact baseline before any promotion. |

**Top-candidate validation already performed:** H29-5-PROXY used cached detrended-relief features; it is materially narrower than the routed-drainage hypothesis. Its E1 canaries stayed below AUC 0.90 (maximum direction-invariant AUC 0.674327). On seeds 620–624, whole-FID buffered **HOLDOUT-DTI** was 0.101209 for the candidate versus 0.099957 for its control; paired delta +0.001252, paired 95% CI [−0.001141, +0.003342], 54,336 repeated withheld-positive occurrences. The interval includes zero, so it failed the frozen efficacy gate. Its attempted final-dot uniqueness screen also stopped: 79.71% candidate-directed overlap within 3 px of a local reference exceeds the 70% limit. No TIFF was written. This is not a comparison against the exact matched H31 control and is not comparable to a leaderboard score.

This negative result closes that experiment; do not tune it or reuse seeds 620–624. A future lane must explicitly state the method before code changes, use fresh preregistered seeds, test each feature alone, compare with a matched current-best architecture, and stop at three experiments or two hours. The H33-1 experiment is separately recorded in `knowledge/31_h33_result_2026-10-27.md`; it also lost its frozen holdout gate.

## Pass 2 — failure modes, edge cases and site readiness

1. **No valid recommendation to download and submit:** the current executive summary correctly labels H33-1 `NOT OK TO SUBMIT`; it lost against base-32 on its own holdout and its matched-current-best and global-registry scope are incomplete. Uniqueness and GeoTIFF format validity do not reverse that decision.
2. **No score projection:** 0.2778, 0.3195 and 0.4413 are not receipts in this checkout; user-supplied values conflict. Keep score estimates unknown until a calibrated evaluation or organizer receipt exists. Local HOLDOUT-DTI is never presented as a live score.
3. **Initial local-input gap, resolved for this checkout:** `data_cache/sample_submission.tif`, `labels.tif` and `dotted_h19_5_d1_5_nan.tif` were initially absent, so the first `verify_downloads.py` attempt exited 2 before auditing all historical rasters. I then ran `python scripts/restore_data.py`; all 17 declared inputs/assembled products passed their pinned SHA-256 checks. These are owner-repository mirrors, not organizer-authenticated downloads. The subsequent full verifier passed with zero failures.
4. **Uniqueness scope is bounded:** the peer inventory is a dated GitHub snapshot and local TIFF scan, not every external site or every organizer submission. No claim of globally unique competition content is justified.
5. **Submission authorization is separate:** no organizer receipt, current weekly cap or selector approval is present. No agent-side code should upload to DrivenData; follow the recorded Terms-of-Use guard and the repository's submission-policy gates.
6. **Source verification is time-bounded:** links to official GDR/USGS/DOE documents are useful for manual review, but several candidate-data sources were not reachable or freshly checked during this review. Preserve their honest `NOT READ` / missing-byte status rather than converting a link or prior listing into proof of current availability.

No source-feed or external-data refresh was run. The sandbox host allowlist does not include DrivenData, GDR/OpenEI, USGS or NLR; repository instructions also prohibit automated DrivenData access. This review did not make requests to those hosts.

## Pass 3 — reproducibility and final requirement check

- Installed the project's declared Python requirements into ignored `.venv/`; no tracked dependency files changed.
- Before restoring data, `python -m pytest -q`: **189 passed, 3 skipped**. After restoring the pinned local inputs, final `python -m pytest -q`: **192 passed, no skips**.
- `ruff check src scripts tests`: **passed**.
- `python scripts/build_site.py`: regenerated six pages, root index and executive summary; **no tracked output changes**.
- `python scripts/audit_submission_readiness.py`: completed; no candidate was authorized.
- Independent rasterio byte re-read of existing H33-1: one float32 band; EPSG:32611; 3730×3292; transform `(100, 0, 243350, 0, -100, 4508550)`; 12,279,160 finite cells within [0,1]; 37,654 positive cells; SHA-256 `1373358188a96b20414834b3e0159065d87470fe695153262ced7b46bc1eb492`. These byte checks do not establish an organizer score, global uniqueness or upload permission.
- `python scripts/restore_data.py`: restored all listed files from the hash-pinned sibling-repository mirrors; all expected byte hashes passed. These remain owner mirrors, not organizer-authenticated downloads.
- `python scripts/verify_downloads.py`: **passed, 0 failures** for the artifacts covered by its configured manifests, including raster geometry, value ranges, hashes, zip contents and gate-consistency checks. This does not authorize any submission.
- Final worktree checks show only this review record and the README link are tracked changes; data cache and `.venv/` are ignored. Tests/build generated no raster and used no weekly submission slot.

### Limitations and recommended next work

1. The hash-pinned owner-mirror cache is now restored and `verify_downloads.py` passed; future sessions should start with `python scripts/restore_data.py --verify` and preserve the non-organizer-authenticated provenance. Do not claim direct official-data authentication from a GitHub mirror.
2. In a new session, choose one explicit assigned lane and preregister a single hypothesis. H28-6 is the lowest-cost candidate with described inputs, but must not proceed until the cache is present and exact shared evaluator/baseline and fresh geographic blocks are defined.
3. For a potentially more orthogonal geothermal signal, request the official GDR #1391 raw package acquisition through an allowed runner; verify hashes, license, geometry/CRS and footprint coverage before considering H27-16 viable. Do not rely on this sandbox to fetch the blocked host.
4. Build stronger genuinely geographic validation and a matched current-best baseline. Current whole-FID splits repeatedly hide parts of one catalogue and do not emulate all expert-label omission mechanisms.
5. Keep the public site truthful: clearly label reported historical scores, display only files plus explicit `NOT OK TO SUBMIT`/selector status, and never publish a projected leaderboard value as a score.
6. Only after a candidate passes efficacy, leakage, byte-validation and complete pre-/post-placement duplicate gates should a separate selector consider a weekly slot. The selector decision and organizer receipt are not present here.

## Run card (the completed highest-priority candidate; negative result)

```json
{
  "hypothesis": "H29-5-PROXY detrended-relief range-front profile",
  "mechanism": "Signed higher/lower-side slope contrast plus transverse concavity and tangent support from cached det_elev",
  "named_non_fault_process_that_could_mimic_it": "Erosional valley edges, lithologic contacts, and engineered cuts",
  "holdout": {
    "label": "HOLDOUT-DTI",
    "evaluator": "gems27.metric.dti_binary v1 + whole-FID full-kernel relief-profile v1; alpha=0.2, beta=0.8, 300 m triangular kernel",
    "withheld_positive_occurrences": 54336,
    "seeds": [620, 621, 622, 623, 624],
    "candidate_pooled": 0.1012092148,
    "control_pooled": 0.0999568713,
    "paired_delta": 0.0012523435,
    "paired_delta_ci95": [-0.0011407041, 0.0033423612]
  },
  "canary_max_auc": 0.6743271642,
  "uniqueness_vs_registry": {
    "preplacement_surface_max_abs_spearman": 0.1727492651,
    "postplacement_max_directed_overlap_3px": 0.7971264673,
    "overlap_limit": 0.70,
    "verdict": "duplicate stop; no TIFF written"
  },
  "raster_sha256": null,
  "validator_output": "No H29-5 candidate TIFF emitted, so no raster-specific validator result exists; repository verifier passed its configured artifacts with 0 failures after owner-mirror restore", 
  "submission_name": "GEMSDOE27-H29-5-RELIEF-PROFILE-20261027",
  "note": "H29-5 detrended relief-profile proxy; whole-FID holdout; research only, not approved to submit.",
  "verdict": "negative"
}
```
