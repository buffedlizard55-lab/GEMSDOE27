# 30 — Preregistration (2026-10-27, Lane L-S13-H33)

**Written before any H33 feature matrix was saved and before seeds 520–529 were scored.**
**Budget:** 3 experiments (E1 canary + pre-placement surface, E2 holdout, E3 raster + uniqueness) or 2 hours. No retune on these seeds.
**Lane note:** The parallel-run prompt says “your lane is the single method paragraph below,” and that paragraph is absent. This session does not invent a sibling’s method. It locks the hypothesis selected below and stops if the surface or the dots duplicate the pinned registry.

## Why 0.2778 is not a template we may copy

`h33-h33-2-b2` (OWNER-REPORTED 0.2778, not ORGANIZER-CONFIRMED) is the GEMSDOE25 d=2.8 H19-5 dot field after deleting dots within 2 px of the catalogue. That identity was measured in `knowledge/12_why_02778_won.md`. Re-emitting those dots fails the uniqueness rule (>70% of dots within 3 px of a registry raster). A projection is not a score. The prompt’s 0.4413 and 0.3195 leaderboard figures disagree with each other and were not read from drivendata.org (forbidden). They stay unresolved.

A same-day blocked-fold screen (NW quadrant held out, not seeds 520–529) is disclosed here so it cannot be mistaken for the confirmatory gate:

- 60.6% of catalogue pixels lie more than 3 px from the d=2.8 family dots (36,967 / 60,988). Those pixels are the only place a unique detector can earn kernel credit without sitting on the family.
- They are short and weak-scarp: lidar `step_max` median 45 vs 80 on family-covered catalogue pixels; `depth_to_base_surf` median 396 m vs 233 m.
- A 32-band HistGradientBoosting model trained on the other three quadrants scored direction-invariant AUC **0.787** on family-covered faults and **0.561** on the uncovered faults. The top 2% of that surface had **73.3%** of its pixels within 3 px of the d=2.8 dots, and covered only **9.1%** of the uncovered faults within 3 px.
- Uranium residual after a Th regression, the obvious blind-fluid alternative, had miss-vs-background AUC **0.506**. It is not the selected test.

So the family already occupies the faults these bands can see. A unique file has to live outside that occupancy. That is a hard constraint, not a styling choice.

## Ranked hypotheses considered

| Rank | ID | Layers | Signature | Why it would be a catalogue-missing fault | Difference from this repo | Prior paired ΔHOLDOUT-DTI / cost | Data gate |
|---|---|---|---|---|---|---|---|
| 1 selected | H33-1 short buried basement-step complement | Cached 32-band stack plus `depth_to_base_surf`, `lidar_step_max` (suppression only), `geod_shearrate` | Short-scale basement-depth gradient and coherence, down-weighted where the lidar step is high; dots kept only more than 3 px from every pinned registry raster | The uncovered catalogue mass is deeper and lower-relief than the scarp family. A surface-rupture catalogue and a long-line scarp emitter both skip it | Not an H19-5 re-thin. Not H32 demagnetization, H31-3 clay-cap asymmetry, H28-3 strain×conductivity, or piedmont flexure. Those lanes did not constrain emission to the registry complement | −0.010 to +0.002 vs unrestricted base-32 / low | PASS — hash-pinned local rasters |
| 2 rejected by screen | H33-2 U residual lineament | GeoDAWN K, Th, U | Positive uranium residual after Th regression, as a fluid-mobility ridge | Oxidizing groundwater along a blind fault mobilizes U; Th stays with lithology | Raw U/Th ratio bands exist; a residual ridge emission does not | ~0 / low | PASS, but miss-vs-background AUC 0.506 |
| 3 not selected | H33-3 quartz-geothermometer corridors | Well/spring CSV `geothermquartz_c`, `cond_surf`, depth gradient | 1.5–12 km segments joining springs with quartz geothermometer ≥ 120 °C along a conductive basement step | Blind upflow between discharge points, not a mapped scarp | H27-12 tested distance-to-any-spring and failed; corridor geometry was not the emission | 0 to +0.003 / medium | Local CSV is an owner mirror of GDR #1391. Example hot spring is 61.7 px from a mapped fault, so corridors are likely false positives |
| 4 not selected | H29-5 canyon-mouth knickpoints | `det_elev`, lidar relief, `cross_max` | Collinear fan-apex / knickpoint alignments | Aggrading bajadas bury inter-canyon scarps | Untried as an operator, but the uncovered class has *lower* relief, so this targets the family habitat | +0.001 to +0.005 / medium | PASS |
| 5 blocked | H27-16 sinter / 2 m probes / Quaternary volcanics | GDR #1391 packages not in this checkout | Sinter lineaments and shallow temperature residuals | Fossil sinter masks scarps while marking upflow | Never ingested | +0.001 to +0.008 / high | **Not viable here.** Official source `https://gdr.openei.org/submissions/1391` (DOI 10.15121/1881483) is outside the sandbox allowlist. Raw bytes were not fetched |

Named non-fault mimic for H33-1: roads, field boundaries, and airborne-survey seams that a tree can rank as short weak lineaments; also lithologic pinch-outs of basin fill that step the basement surface without a fault.

## Frozen method

- Features: prepared 32-band stack (`data_cache/prepared/features.npy`, schema 2) plus six label-free transforms in `src/gems27/buried_step.py`: depth-gradient magnitude at σ=2 and σ=6, depth structure-tensor coherence at σ=4, low-scarp rank `1 − rank(lidar_step_max)`, the product of ranked short depth-gradient, low-scarp, and shear, and 7 px anisotropy of the σ=2 depth gradient.
- Instrument: `HistGradientBoostingClassifier` with the shared `oof_detector` hyperparameters (`max_iter=100`, `max_leaf_nodes=31`, `learning_rate=0.08`, `l2_regularization=5.0`, 10× negative subsample). No private metric fork. Holdout and writer are `gems27.holdout` and `gems27.submission` (this repo has no files named `evaluate_holdout.py` / `submission_writer.py`).
- Split: withhold whole segments. Group IDs are NBMG Qfault FID assignments (nearest rasterized vector polyline). 20% of groups are hidden, stratified by group-centroid quadrant, using `holdout.make_segment_split`. Buffer 6 px. Visible faults are masked pixel-exactly. Distance-to-catalogue uses visible faults only.
- Emission, both arms: directional ridge NMS of the probability, exclude visible catalogue, exclude cells within 2 px of visible faults, Poisson-disk spacing 2.8 px, budget 37,654. Candidate arm additionally requires Euclidean distance > 3 px from every positive pixel of the 12 pinned registry rasters. Control arm B is base-32 with the same emission and **no** complement constraint.
- Seeds: **520–529**. Consumed by this run whatever the outcome.

## Gates

- **E1 canary:** direction-invariant ROC-AUC of each of the six new features on the union of withheld positives vs a background sample. Any value > 0.90 is leakage. Stop. Do not place dots from leaked features.
- **E1 surface, before placement:** absolute Spearman of the full-fit probability surface vs each pinned registry raster, on a fixed 400,000-pixel footprint sample. Any value > 0.90 is a duplicate lane. Log it and stop before placement. No submission TIFF from that surface.
- **E2:** pooled HOLDOUT-DTI, evaluator `gems27.metric.dti_binary` v1, α=0.2, β=0.8, 300 m triangular kernel, buffered whole-segment scoring. Promote only if candidate − control B has mean paired seed Δ ≥ +0.001, 95% seed-bootstrap CI lower bound > 0, ≥7/10 seeds positive, and ≥3/4 centroid-quadrant folds positive.
- **E3:** all-finite primary TIFF, zeros outside, nodata unset, values in [0, 1], CRS/shape/transform match. Final-dot overlap vs each of the 12 pinned registry rasters ≤ 0.70 and surface Spearman ≤ 0.90. The same 0.70 overlap stop is also applied to every pre-existing `*allfinite.tif` under `docs/downloads/` and `docs/downloads/research/` (this repo's own prior submissions). Note ≤ 140 characters.
- **Verdict:** `promote` only if E1, E2, and E3 all pass. Otherwise `negative`. A negative TIFF may be written only if the pre-placement surface check passed, and it is not authorized for a weekly slot. This session does not select a slot.

No number from E1–E3 is a leaderboard score.
