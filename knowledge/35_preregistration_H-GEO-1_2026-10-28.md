# Pre-registration: H-GEO-1 hydrothermal alteration-front coherence (frozen 2026-10-28)

**Lane:** Single-method lane per the PARALLEL-RUN PROTOCOL. Written before any H-GEO-1 feature matrix is saved
and before any holdout seeds are scored. Budget: 3 experiments (E1 canary + pre-placement surface, E2 holdout,
E3 raster + uniqueness) or 2 hours. No retune on these seeds.

## Hypothesis

H-GEO-1: Hydrothermal alteration-front coherence from radiometric ratios finds blind or covered faults that
the USGS/INGENIOUS surface-trace catalogue omits. Coherent NE–SW alteration fronts with elevated K/Th and U/Th
ratios mark clay-altered fault gouge and juxtaposed wallrock, producing a lateral ratio anomaly with no
Quaternary surface rupture.

## Layers

- `geodawn_extensions_u8.tif` bands Th/K, U/K, U/Th, TMI_up150 (float32, 0 = nodata)
- `geodawn_rad_u8.tif` bands K, Th, U, TC (float32, 0 = nodata)
- Catalogue raster `labels.tif` (visible faults only, used for masking and distance)
- Prepared 32-band feature stack `data_cache/prepared/features.npy` (for background AUC sampling)
- All hash-pinned and already restored in `data_cache/` (no external fetch required)

## Physical signature

K/Th and U/Th ratio elevation in a coherent NE–SW-trending corridor with cross-profile decay away from a
central axis. The front is detected as: (ratio anomaly at pixel) × (strike-parallel persistence over 3–8 px)
× (cross-profile confinement to ≤4 px half-width) × (elevation above local 25 px median). This is a structural
front detector, not a per-pixel classifier.

## Why it catches a catalogue-missing fault

Blind faults juxtaposing altered wallrock against unaltered host create ratio fronts with no surface trace.
The catalogue maps Quaternary surface ruptures; alteration fronts mark subsurface plumbing that the compilation
omits. Fault-hosted hydrothermal systems commonly have alteration halos hundreds of metres wide.

## How it differs from anything in this repo

H27-12 tested radiometric bands as per-pixel scalar detector features (+rad PR-AUC 0.02532, +0.00074 — failed
the +0.005 gate). No candidate in this repo builds spatially coherent alteration fronts with cross-profile decay
and orientation consistency. This is new to this checkout.

## Named non-fault mimics

Lithologic contacts (felsic vs mafic units), alluvial-fan apron contacts, survey flight-line residuals in the
radiometric data, playa/lake shorelines.

## Frozen method

**Feature construction (deterministic, no training):**

1. Read the 8 radiometric bands as float32; set nodata (0) to NaN.
2. Compute K/Th, U/Th, U/K, Th/K ratios where both bands are finite and non-zero; else NaN.
3. For each ratio, compute a 25 px Gaussian-smoothed local median and a local robust scale (MAD × 1.4826).
4. Anomaly score = (ratio − local_median) / local_scale, clipped to [−6, 6], NaN where either input is NaN.
5. Strike-parallel persistence: for each of 4 orientations {0, 45, 90, 135} deg, compute a Gaussian-weighted
   line mean along strike with half-length 4 px (0.4 km) and across-strike sigma 1 px. Take max over orientation.
6. Cross-profile confinement: compute the same line mean across strike with half-length 2 px; front strength
   = along-strike persistence − 0.5 × across-stripe mean.
7. Front map = max(0, front strength) where anomaly score > 1.0; else 0. Normalize to [0, 1] over the footprint.
8. Emission domain: footprint ∧ ~visible_catalogue ∧ (distance_to_visible_catalogue > 3.0 px).
9. Ridge extraction: 1-px directional NMS on the front map within the domain; Poisson-disk spacing 2.8 px;
   budget 37,654 dots; min self-spacing 1.5 px.

**Holdout (E2):** `gems27.holdout.make_segment_split` with NBMG Qfault FID group IDs, 20% of groups hidden,
stratified by group-centroid quadrant, buffer_px=6.0, fresh seeds 600–609 (10 draws × 4 folds = 40 cells).
Visible faults masked pixel-exactly via `split.known` as `known=` to the metric. Pooled DTI: α=0.2, β=0.8,
300 m triangular kernel (RADIUS_PX=3).

**Control B:** Same emission pipeline but using the raw front map without cross-profile confinement
(step 6 replaced by along-strike persistence alone). Same dots, spacing, budget.

## Gates

**E1 canary (before placement):** Direction-invariant ROC-AUC of the front map on withheld positives vs a
background sample of equal size drawn from the footprint. Any |AUC − 0.5| > 0.40 (i.e., AUC > 0.90 or < 0.10)
is leakage — stop, do not place dots.

**E1 surface (before placement):** Absolute Spearman rank correlation of the front map vs each pinned registry
raster on a fixed 400,000-pixel footprint sample. Any value > 0.90 is a duplicate lane — log and stop.

**E2 holdout:** Pooled HOLDOUT-DTI, evaluator `gems27.metric.dti_binary` v1. Promote only if candidate − control
B has mean paired seed Δ ≥ +0.001, 95% seed-bootstrap CI lower bound > 0, ≥7/10 seeds positive, ≥3/4 folds
positive.

**E3 raster:** All-finite primary TIFF, zeros outside footprint, values in [0, 1], CRS/shape/transform match
template. Final-dot overlap vs each of the 12 pinned registry rasters ≤ 0.70; surface Spearman ≤ 0.90. Same
0.70 overlap stop vs every pre-existing `*allfinite.tif` under `docs/downloads/` and `docs/downloads/research/`.
Note ≤ 140 characters.

**Verdict:** `promote` only if E1, E2, E3 all pass. Otherwise `negative`. A negative TIFF may be written only
if pre-placement surface check passed; it is not authorized for a weekly slot. This session does not select a
slot. No number from E1–E3 is a leaderboard score.

## Seed budget

Seeds 600–609 are consumed by this run whatever the outcome. Do not reuse for confirmation or tuning.

## Expected gain (planning prior, not a measurement)

0.000 to +0.005 on the catalogue-internal holdout. Transfer to organizer labels unknown.

## Sources (all official, free, publicly available, already hash-verified in data_cache)

- USGS GeoDAWN ScienceBase: https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7
- INGENIOUS GDR #1391: https://gdr.openei.org/submissions/1391
- NBMG Qfaults_INGENIOUS: https://web2.nbmg.unr.edu/arcgis/rest/services/Qfaults/Qfaults_INGENIOUS/MapServer/0
- EPSG:32611: https://epsg.io/32611
- Tversky index: https://en.wikipedia.org/wiki/Tversky_index
- DrivenData GEMS reference: https://github.com/drivendataorg/gems-prize-reference-solution