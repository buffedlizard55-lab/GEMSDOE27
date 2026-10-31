# Preregistration — Lane L-2026-10-31-H35: weak-scarp continuity (WSC) augmentation

**Written before any H35 scoring run.** Seeds, arms, gates and file-choice rule below are frozen.
This document plus the hypothesis screen is `knowledge/45`; results land in `knowledge/46`.

**Lane-paragraph irregularity (logged, not silently accepted):** the parallel-run prompt again
promises "a single method paragraph below" and again omits it (`IR-2026-10-31-lane-paragraph-still-missing`).
The user's instruction this session is explicit and repeated at highest urgency: *a unique TIF must be
generated*. We therefore self-assign ONE lane inside the protocol's operative constraints (the
registry-raster duplicate stops), record the assignment here, and fail closed if any stop triggers.
The pre-placement calibration (`evidence/_scratch/calibrate_uniqueness.json`, a detector-family
measurement, not a hypothesis experiment) measured the arm-D emission family at max directed 3-px
overlap **0.475** vs the 12 pinned registry rasters and max |surface Spearman| **0.110** — inside both
stops, so this detector family does not belong to any registered parallel lane.

## 0. Instrument (unchanged, shared)

- Evaluator: `gems27.metric.dti_binary` v1 (alpha 0.2, beta 0.8, R = 3 px triangular), pooled DTI.
- Holdout: `gems27.holdout.make_segment_split` — whole vector-FID segments hidden per seed
  (frac 0.20), quadrant-stratified; `buffered_training_mask` / `buffered_scoring_mask`, buffer 6 px;
  visible faults masked pixel-exactly via `known=`.
- Emission: shared `run_h33_lane.emit` — `ridge_nms` (sigma 1.0) → candidates outside the visible
  catalogue collar (`d_known > 2.0` px) → `priority_poisson_disk(min_dist=2.8, budget=37,654)`.
- Control training: shared `run_h33_lane.fit_predict` (HistGradientBoostingClassifier, 100 iters,
  31 leaves, lr 0.08, l2 5.0; 10:1 negative subsample).
- Seeds: **930–939** (fresh; never used in any prior run in this repo).
- Per-seed arm surfaces share ONE trained model per seed (the delta under test is label-free
  emission structure), so paired comparisons are exact.

## 1. Hypothesis screen (five candidates; detailed table in knowledge/45)

Ranked by expected DTI improvement × implementation cost on the strict whole-FID instrument
(only dots that land ON hidden trace pixels earn credit; a 6 px buffer ring around hidden segments
is excluded from scoring, so off-trace haze is dead mass):

1. **H35-1 WSC — weak-scarp continuity augmentation** (this lane). Layers: LiDAR 100 m scarp
   descriptors `step_max`, `lappos_max`, `ex_max` (bands 3/5/1 of `lidar_scarp_features_u8.tif`).
   Signature: multi-scale orientation-coherent, ANISOTROPIC line-integral response restricted to
   the weak-moderate amplitude band (u8 28–120 of `max(step,lappos,ex)`, cosine taper 20).
   Why missing faults: degraded / partially buried young scarps fall below the corroborated-ridge
   bar that built the H19-5 family, so the family never emits on them; mappers omit them for the
   same reason. Named non-fault mimics: lithologic dip slopes and hogbacks, fluvial terrace risers,
   Lake Lahontan shoreline strandlines, avalanche chutes, graded-road berms.
   Differs from repo: `newinfo.directional_lineament_bands` fed the HGB as augmentation and was
   negative (dilution, `knowledge/21`); no standalone continuity emitter with the budget/collar
   recipe exists here. Sibling 7GEMSDOE `lidarscarp-ridge-top2pct` (OWNER-REPORTED 0.1461) emitted
   amplitude-percentile pixels without continuity, budget or collar. Cost: low (cached bands).
2. **H35-2 hydrothermal-discharge lineaments** — warm-spring thermal-residual field
   (`hydrochemistry.build_chemistry_field`, wells/springs CSV) × oriented continuity; emit along
   linear discharge alignments. Upflow conduits of blind faults; mimics: valley-bottom discharge
   lines, artesian trends, sampling bias. H29-1/H31 used chemistry as detector augmentation
   (OWNER-REPORTED 0.219/0.225); no pure emitter exists. Gate risk: springs sit near faults, not
   on traces — the strict instrument punishes that. Cost: low.
3. **H35-3 triple-concordance buried corridors** — thermal anomaly ∩ gravity analytic edge ∩
   magnetic edge co-locations (extends H29-XG cross-gradient with the thermal axis). Specificity
   beats H29-XG's failed two-axis form; support is small. Cost: medium.
4. **H35-4 SGMC-concordant young-expression conjunction** — off-catalogue SGMC fault traces ∩
   weak LiDAR continuity. Prior: SGMC-only emission scored OWNER-REPORTED 0.0512 (below floor);
   conjunction untested. Cost: low.
5. **H35-5 volcanic-vent transfer corridors** — 21 Quaternary vents (`gdr_volcanic_vents`), vent
   alignment corridors and conjugate transfer structures. Tiny support. Cost: low.

Blocked (recorded, not ranked): H27-16 GDR #1391 sinter/probe packages and H29-5 routed drainage
need bytes outside the sandbox allowlist (unchanged from `knowledge/38`).

**Validated this session: H35-1 only.** H35-2..5 remain ranked research ideas.

## 2. Arms (frozen)

- **B** = arm-D detector emission: 32-band prepared stack + 15 subsurface transforms → HGB →
  `emit` (control architecture).
- **C0** = B plus T-v2 catalogue-graph gap-closure dots: `build_graph(known)`, `links.generate_links`
  (cone 30°, r 10–40 px), `evidence_score z ≥ 3`, `dedupe_mutual`, `links.rasterize_links(Spacing=3)`,
  kept only where `d_known > 2` and `d_base ≥ 3` px. This is an *architecture context* arm: T-v2 is
  already implemented in this repo and is NOT the hypothesis under test.
- **C1** = C0 with the WSC delta: candidate pool = `ridge_nms(prob)` ∪ `wsc_ridges`; fusion
  priority `p' = prob + 0.5·wsc_pct` where `wsc_pct` is the percentile rank of the WSC score among
  candidate pixels (0 where WSC = 0); same Poisson budget and collar. λ = 0.5 and all WSC constants
  below are frozen at preregistration.

WSC constants (frozen): response `r = max(step_max, lappos_max, ex_max)` (u8 0–255; 0 = no LiDAR
excluded by the gate); weak-moderate gate `g = 1` on u8 ∈ [28, 120] with cosine tapers of width 20
outside that band; oriented means at half-lengths {5, 10, 20} px across-strike sigma 0.8
(`newinfo.oriented_means` machinery, integer shifts); anisotropy `a = (maxm − meanm)/(maxm + 1e−6)`;
WSC score `= maxm · a · g`; WSC ridges = `ridge_nms(wsc, sigma=1.0)`.

## 3. Gates (frozen)

E1 canary + surface: each new label-free feature alone vs hidden-vs-background AUC (direction
invariant) must stay < 0.90 (leakage stop). Pre-placement max |surface Spearman| vs the 12 pinned
registry rasters ≤ 0.90 for BOTH the prob surface and the WSC surface.

E2 efficacy (the hypothesis gate): C1 vs C0 on seeds 930–939, whole-FID buffered, paired by seed:
**pass iff** mean seed-paired Δ ≥ 0.001 **and** paired-bootstrap 95 % CI lower bound > 0 **and**
positive seeds ≥ 7/10 **and** positive folds ≥ 3/4 **and** pooled(C1) > pooled(C0).
C0 vs B is reported as the architecture comparison (same thresholds).

E3 placement + uniqueness: final dots must keep directed 3-px overlap ≤ 0.70 vs each of the 12
pinned registry rasters AND vs every local `*allfinite.tif` in `docs/downloads` and
`docs/downloads/research`, and |binary/dot Spearman| ≤ 0.90, checked by
`scripts/check_parallel_uniqueness.py` plus the local scanner. Automated validator
(`submission.verify_geotiff`) must report zero hard failures for both variants.

## 4. File-choice rule (frozen)

1. If C1 passes its E2 gate and its live dots pass E3 uniqueness → primary file = C1.
2. Else if C0 passes vs B and is unique → primary file = C0 (labelled architecture, not hypothesis).
3. Else primary file = B (best validated base emission; still unique and format-valid).

The primary file is written in BOTH variants: `-allfinite.tif` (zeros outside the footprint; the
fallback for the portal's strict "Predicted values must be in range [0, 1]" check) and `-nan.tif`
(sample-submission convention). The download box links the all-finite variant and its zip.
Verdict labels: gates pass → **"OK TO DOWNLOAD AND SUBMIT"** (a human submits; weekly-slot
authorization remains the user/selector's decision). Any gate fails → **"NOT OK TO SUBMIT"** with
the failing gate named. A projection is never written as a score.

## 5. Budget

Three experiments per session: E1 (canary + surface screen), E2 (frozen holdout run), E3 (placement,
uniqueness, validation, run card). Stop after them or at 2 h. Negative results are deliverables.
No DrivenData access; no upload; the run card is `evidence/h35_run_card_2026-10-31.json`.
