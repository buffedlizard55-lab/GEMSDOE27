# Submission evidence audit — 2026-10-25

## Scope and lane irregularity
The supplied prompt says a single method paragraph defines this session's lane, but
none is explicitly supplied. The original repo prompt defines topology-first research;
subsequent sessions separately tested subsurface-only, hybrid-refill, and radiometric
front methods. Do not silently treat all these as this session's lane. This session
is an **evidence/format audit**, not a new geological experiment. Zero model experiments,
zero new rasters, zero submission slots. No previous submission is renamed as unique.

Open parallel PR #18 was inspected using `gh pr view 18`: it reports H28-6 radiometric
fronts as negative. Its changes are not part of this branch and its data are not
independently re-evaluated here. Do not repeat that hypothesis as untried.

## Why the reported 0.2778 is not a demonstrated target we can exceed
The pixel reconstruction in knowledge/12 and knowledge/17 supports a mechanism:
sparse emissions reduce false-positive mass; excluding visible-catalogue echoes can
further improve precision. It does not authenticate the association with a portal
receipt or prove that no better detector exists. Nor can a finite set of emissions
prove the categorical ceilings in knowledge/17. Those ceilings, winning probabilities,
and claims that segmentation is the *only* route are speculative, not measured bounds.
The prompt reports both 0.3195 and 0.4413 as current highs. Neither is verified here.

H29-1's recorded **HOLDOUT-DTI**, `gems27.metric v1` (alpha .2, beta .8,
300 m triangular kernel), is 0.108786 versus paired control 0.100197,
59,362 withheld positives; paired mean improvement 0.008571, recorded 95% CI
[0.005129, 0.012489]. This is not a CI for the pooled DTI itself. Its directed dot
overlap with H28-1 is 0.854368, which fails the 0.70 rule. We do not waive that rule.
The existing canary/holdout outputs were read, not rerun. Proxy-label bias remains.

## Prospective hypothesis screen (not implemented; no score projections)
Novelty means absent from the method descriptions examined in this checkout, not a
claim of global or all-sibling novelty. Ranking is a qualitative research priority,
not a prediction of DTI improvement. All require a separately assigned lane, current
registry comparison, preregistration, and whole-segment buffered holdout.

| Priority | Geological hypothesis / layers | Signature and missing-fault rationale | Difference / non-fault mimic | Cost / viability |
|---|---|---|---|---|
| 1 | Along-strike interruption recovery, RTP + isostatic gravity | Detect a short low-amplitude interval bounded by collinear *cross-field* edges; extrapolate only when both independent fields resume with coherent polarity. A buried continuation can lack a surface scarp. | Edge interruption/polarity persistence, not graph closure between catalogue endpoints or scalar edge strength. Mimic: lithologic contact interrupted by cover. | Medium; pinned source bands exist in manifest, full feature cache not restored in this audit. Scientific and uniqueness viability untested. |
| 2 | Curved range-front rollovers, DEM + basement-depth surface | Test coherent signed curvature reversal across nested parallel profiles and an independently displaced basement step; hypothesized shallow listric roll-over rather than a straight scarp. | Profile-shape consistency, not ordinary scarp or dip-offset doublets. Mimic: alluvial-fan toes / lacustrine terraces. | Medium/high; requires resolving source resolution and missing-data coverage from cached stack before viable testing. |
| 3 | Oblique buried transfer boundaries, RTP + gravity + strain tensor bands | Localize spatial changes in potential-field edge azimuth coincident with strain principal-axis rotation, without using catalogue geometry. Might detect transfer structures absent from surface mapping. | Rotation of orientation across a boundary, not strain magnitude or alignment at a pixel. Mimic: intersecting lithologic contacts / noisy strain interpolation. | Medium; available bands named in manifest/prepared metadata, but tensor convention must be checked before deriving angles. Conditional, not validated. |

No new external dataset is required by these proposals; none is called submission viable.
A single scalar canary AUC is necessary but not sufficient to exclude leakage. Check
all base and derived features, sign-invariant AUC, buffers and visible-only features.

## Implemented fix
Previously green badges trusted `ok_to_submit` alone. `gems27.readiness` now refuses
publication if that boolean contradicts verdict, explicit efficacy, canary, paired
positive improvement CI, uniqueness thresholds, validator checks, note length, or
raster hash. Missing evidence fails closed. This is a recorded-evidence check, not
a substitute for rerunning the metric, validating raster bytes, or comparing a new
raster against the *current* registry. Future confirmation schemas must explicitly
map to the required fields; unsupported schemas cannot silently pass.

`python scripts/audit_submission_readiness.py` emits the public JSON audit linked
on every page. `research_format_reaudit_20261025.json` independently reopens all five
existing all-finite research TIFFs with the shared validator: all pass format. None
is thereby certified unique or eligible. No new unique TIFF is claimed.

## Three review passes
1. Implementation: shared fail-closed policy, public audit, badge integration.
2. Adversarial review: missing fields, stale file hash, NaN/Infinity, false green
   boolean, duplicate threshold, and CI crossing zero regression tests added.
3. Original-request reconciliation: retain STOP status, distinguish paired CI from
   pooled uncertainty, restore small hash-pinned inputs, independently reopen
   research rasters and run download checks. No upload, receipt, or new score.

## Sources and limitations
- Official reference repository README fetched via GitHub API, snapshot:
  `evidence/official_reference_readme_20261025.md`;
  https://github.com/drivendataorg/gems-prize-reference-solution
  explicitly supports CPU environments: GPU is a speed advantage, not a universal
  prerequisite. This does not establish that this repo's old training pipeline works.
- Competition problem (manual review link, not fetched this session):
  https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- Official external-data source links (not newly read / obtainable here):
  https://gdr.openei.org/submissions/1391 and
  https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
- Inputs restored through owner repositories are hash-pinned, not organizer-authenticated.
- Allowed outbound hosts exclude DrivenData, USGS, GDR and Dropbox. Do not claim
  current official leaderboard verification or a fresh external-data availability check.

Next: assign a non-overlapping geological lane; restore/verify the full cached stack;
freeze fresh seeds and paired controls; test each feature alone; compare surfaces
before dot placement and final dots against a freshly frozen all-raster registry.
Only a candidate beating the paired baseline and passing *all* gates proceeds to
separate selector review within the actual weekly cap. No human inspection gate
or rule waiver is substituted for machine validation.
