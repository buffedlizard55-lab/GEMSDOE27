# Preregistration: H28-1 multiscale potential-field edge coherence

**Written:** 2026-10-02 UTC, before implementation or running the H28-1 gate. This file and the five-candidate inventory (`knowledge/07_untried_hypotheses.md`, `registry/next_hypotheses.json`) are to be committed before the validator is added or executed.

## Hypothesis

Magnetic and gravity gradients that persist across scale and share a local edge orientation may mark buried lithologic offsets or fault-zone boundaries not present in the USGS/INGENIOUS Quaternary-trace catalogue. A cross-field edge is a *fault candidate*, not proof: non-fault lithologic contacts, survey seams, remanent magnetization and depth differences can produce the same signature. The prediction target remains fault-location pixels, not vents or geothermal favorability.

## Data and provenance

Use only the existing, hash-pinned `training_features.tif` owner mirror (`data/manifest.json`): band 2 `rtp` (reduced-to-pole magnetic field) and band 13 `iso_grav_anom` (isostatic gravity anomaly); cross-check the embedded band descriptions before processing. These are the two base fields. Exclude training band 6 `tc` because the repository's earlier rank audit flagged it as inconsistent with the band name. Do not fetch new data. The official contextual source is the USGS GeoDAWN ScienceBase record, https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7; competition feature authenticity remains limited by the owner-mirror provenance recorded in `data/manifest.json`.

## Frozen feature transform

For each base field independently:

1. Read the full-resolution 100 m field and use the template footprint mask. Fail closed if the expected band name, shape, CRS or affine transform differs. Do not use labels in transform construction.
2. At Gaussian sigmas **3 and 10 pixels** (nominal 0.3 km and 1.0 km), smooth the field and calculate `gx, gy` by centered finite differences in metres. Compute edge magnitude `sqrt(gx^2 + gy^2)` and the unit gradient orientation `(gx, gy)/(magnitude + 1e-12)`.
3. Scale each edge-magnitude channel to a robust unit range using the fixed in-footprint 5th and 95th percentiles, then clip to `[0, 1]`. No percentile, scale, or band may be selected using holdout labels.
4. Add two cross-field features at the 1 km scale: `edge_concordance = min(mag_norm, grav_norm)` and `orientation_agreement = abs(dot(unit_grad_mag, unit_grad_grav))`. Set both to zero where either source is invalid or edge magnitude is below its own in-footprint 10th percentile. This tests co-located concordant edges; no spatial dilation/tolerance is tuned.
5. Append these six fixed features (four scale-specific edge magnitudes, concordance, orientation agreement) to the existing 32-feature matrix. Existing 32 numerical features and names remain unchanged in this experiment.

The expected number of new columns is six. The transformation must be deterministic and may not read `labels.tif`, candidate outputs, or any holdout selection.

## Spatial holdout and baseline

- Use the same four fixed quadrant folds and the existing 600 m train/test buffer in `src/gems27/oof_detector.py`.
- Fit paired baseline and augmented `HistGradientBoostingClassifier` models with the same existing parameters, positive/negative sampling rule (`neg_ratio=10`), and identical per-fold seed `2026 + fold`. For each fold, all test-quadrant labels and the 600 m buffer are excluded from training. The only model difference is the six appended features.
- Convert each fold's out-of-fold probability map to the same `ridge_nms(sigma=1)` one-pixel ridges, select `PRE_THIN_FRAC=0.0245` of the fold footprint, and apply deterministic `dot_thin(d=1.5)`.
- For each paired map, construct the in-fold T-v2 addition from the known catalogue using the already frozen T-v2 rule and the existing `z >= 3`, mutual-link de-duplication rule; prune the 100 m known-catalogue flank shadow using the already frozen H27-4 r1 rule. Do not modify T-v2 or H27-4 thresholds.
- Evaluate the baseline and augmented **stacked variants** against the same component-hidden, four-quadrant split for fresh seeds **140–149** (`holdout.make_split`), using the exact in-repo DTI implementation and active-area masks. The comparison target is the current OOF best, `B_oof + T-v2 + H27-4 r1`, not the weaker raw model. Report each seed and each quadrant, mean paired DTI difference, positive-seed count, positive-fold count, output count, TPw, FPw and hashes of input artifacts.

All derived input transforms are label-free; the split hides catalogue components only for evaluation. Results still test catalogue-internal held-out traces, not organizer-created expert labels.

## Gate and no-slot rule

**Pass only if all are true:**

1. mean paired DTI gain of augmented-stacked minus baseline-stacked is at least **+0.0010** across the 40 paired cells;
2. mean gain is positive in at least **3 of 4** geographic folds;
3. mean gain is positive in at least **8 of 10** seeds; and
4. no raster/grid/feature-description/hash checks fail and there is no catalogue overlap in emitted pixels.

These thresholds are fixed in advance. No threshold or hyperparameter tuning is allowed on seeds 140–149. If any condition fails, record H28-1 as **not validated / reject for submission**, retain all existing submission files unchanged, and do not spend a weekly slot. A pass permits building a uniquely content-hashed, unscored candidate for a *future* controlled A/B decision; it does not authorize automatic upload or claim a live-score gain.

## External-source check

No new external dataset is required for H28-1. The official GeoDAWN catalog page was fetched and read on 2026-10-02 and identifies the magnetic/radiometric release and derivative products. The current feature TIFF is still an owner-mirrored competition input; its identity is verified against this repository's hash manifest, not an organizer-authenticated download. No DrivenData endpoint is accessed.

## Implementation-freeze addendum (before H28-1 run)

- Preregistration record: commit `c5d40b7` (made before the H28 implementation and holdout run). No thresholds, holdout seeds or pass criteria below are changed by this addendum.
- Data audit before modeling found that the old `prepare_data.py` names did not match the first ten embedded LiDAR band descriptions. The sidecar is now hash-pinned and the preparation code asserts all 12 source names. Rebuilding corrected only metadata labels: the 32-column numerical matrix SHA-256 is unchanged at `83ed2704ee2de03cf8b1c8f2966fcf71813501df97c1c35400e6c0415393f6dc`, exactly matching the previous committed evidence. Thus H28 baseline and augmented models still consume identical positional base values; the corrected names are not a model intervention.
- Frozen implementation details: `scipy.ndimage.gaussian_filter(..., mode="nearest")`; sigmas `(3.0, 10.0)`; centered finite differences via `numpy.gradient` with 100 m spacing; independent in-footprint 5th/95th percentile scaling and clipping; absolute gradient orientation; zero-fill for the two concordance features below either field's in-footprint 10th-percentile gradient threshold or outside the common valid mask. Invalid/outside cells are nearest-filled only for filtering, then masked to zero in the six appended features. No label values enter the transform.
- The 600 m training buffer remains the existing frozen OOF split for both paired models. The 1 km Gaussian covariate transform is label-free, but field values can be spatially correlated across quadrant boundaries; this is a residual generalisation limitation, not a label leak. Report it with the result.
- `scripts/run_h28_1_edge_holdout.py` writes only cache/evidence JSON, verifies the prepared matrix sidecar and source bands, compares the same OOF base and graph additions/pruning, and does not generate a submission TIFF.
