# Preregistration: H28-6 multiscale radiometric alteration-front ridges

**Written:** 2026-10-25 UTC, before implementing the transform and before evaluation on seeds 210–219. **Pre-run execution addendum:** deterministic negative-sample cap was specified after the code skeleton but before any canary/holdout evaluation; it does not change the transform, seeds, evaluator, duplicate threshold, or promotion gate. **Status:** frozen before E1. Any deviation will be recorded, not silently tuned.

## Hypothesis and named non-fault mimic

A hydrothermal fluid pathway can alter radioelement distributions and produce spatial fronts in airborne radiometric grids even where a fault is buried or has no mapped Quaternary surface trace. Multi-scale edge strength and agreement between radiometric channels may be more fault-informative than radiometric pixel values or ratios alone.

**Named non-fault mimic:** lithologic/regolith contacts and airborne flight-line or processing seams can create coincident K/Th/U/total-count boundaries without a fault; shallow soil moisture and non-tectonic hydrothermal alteration can also modify the radiometric response.

This is an exploratory detector-feature hypothesis. It does not map geothermal vents, establish a fault, or assert that any radiometric edge is tectonic.

## Inputs and provenance gate

Use only the hash-pinned local owner-mirror raster files:

- `data_cache/geodawn_rad_u8.tif`, expected SHA-256 `c22420f75999030d7cc65c9e31e50d232ea6158423bca051613a18a8b20ba682`; descriptions `K`, `Th`, `U`, `TC`.
- `data_cache/geodawn_extensions_u8.tif`, expected SHA-256 `a35a9c6d2a14786f4dab85481ee59769213072f5dab5b2535ea82ae4d9bb7d9b`; descriptions `ThK`, `UK`, `UTh`, `TMI_up150`.
- Grid template: `data_cache/sample_submission.tif`, SHA-256 `2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc`.
- Prepared feature cache: `data_cache/prepared/features.npy`, validated against its metadata and input hashes by `scripts/prepare_data.py`.

`registry/sources.json` identifies the official provenance as USGS GeoDAWN (Glen & Earney, DOI 10.5066/P93LGLVQ), with manual review URL https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7. The source metadata was previously read and verified in this repository; the binaries used here are owner-repository mirrors restored from pinned GitHub commits, not newly downloaded official bytes. All source rasters must match the template's CRS, shape, and transform; the expected GeoDAWN nodata value is 0. Fail closed on description, checksum, grid, or valid-cell-count mismatch.

## Frozen transform (label-free)

Use bands `ThK`, `UTh`, and `TC`; do not include labels, known-fault distance, catalogue-derived features, lidar/topography, source-score fields, or submission rasters in feature construction.

1. Intersect finite/nonzero cells in all three bands with the template footprint. Require at least 95% common in-footprint coverage. Nearest-fill invalid cells only for convolution; set every output feature to zero at invalid cells.
2. Treat the uint8 bands as rank-like relative fields (not calibrated concentrations). For each field, Gaussian smooth at fixed sigma 3 and 8 pixels on the 100 m grid (nominal 300 m and 800 m scale-space); compute physical gradient magnitude using 100 m pixel spacing.
3. Independently robust-scale each magnitude with in-footprint 5th/95th percentiles and clip to [0,1]. This yields six fixed-order features: `rad_thk_edge_300m`, `rad_thk_edge_800m`, `rad_uth_edge_300m`, `rad_uth_edge_800m`, `rad_tc_edge_300m`, `rad_tc_edge_800m`.
4. At sigma 3, compute absolute cosine agreement between normalized gradients for `ThK` and `UTh`, and between `TC` and `ThK`. Zero agreement unless both local magnitudes are at or above their own in-footprint 10th percentile. Append `rad_ratio_edge_orientation_agreement_300m` and `rad_total_ratio_edge_orientation_agreement_300m`.
5. The final feature matrix has exactly eight finite float32 columns, in the order above, stored in footprint-row-major order. Features are computed once from label-free rasters and reused across folds. Record transform-code and input-file SHA-256 hashes in cache metadata.

The intended signature is a ridge of radiometric rank-change/edge strength, with co-oriented channel fronts. It is deliberately not interpreted as absolute K enrichment, alteration intensity, or fault probability.

## Leakage canary and surface-uniqueness stop

Before the paired DTI run, evaluate each of the 3 source fields (`ThK`, `UTh`, `TC`) and each of the 8 derived features alone on hidden holdout segments for each of the four spatial quadrants and seeds 210–219. The evaluation mask is `holdout.buffered_scoring_mask(split, footprint)`; visible catalogue pixels are excluded with `split.known`. Use direction-invariant ROC-AUC, `max(AUC(x), AUC(-x))`, for each source/derived field. The frozen safety threshold is **0.90**: any feature above it aborts the efficacy test until leakage is explained. For computational reproducibility, include every eligible hidden-positive pixel and a uniform deterministic sample of at most 200,000 eligible negative pixels per seed/fold cell, with RNG seed `20261025 + 1000*seed + fold_index`; use the same sampled pixel indices for all 11 fields in that cell. The canary is a safety diagnostic, not an efficacy result.

Fit the baseline and candidate with `oof_detector.fit_predict_oof_probabilities` (the shared 4-quadrant, 600 m training buffer and fixed HistGradientBoosting configuration). Before converting either continuous probability surface to ridges/dots, compute candidate-surface Spearman rank correlation against all entries in `registry/parallel_submission_registry.json`, using their cached, SHA-verified rasters and the finite footprint. If any coefficient is >0.90, log the candidate as a duplicate and stop before placement.

## Paired holdout design

- **Evaluator:** `gems27.metric` binary DTI implementation (alpha 0.2, beta 0.8, Euclidean triangular radius 3 pixels = 300 m); `gems27.holdout` supplies quadrant folds, component hiding, pixel-exact visible-fault masking, and the 600 m buffered scoring mask.
- **Splits:** seeds 210–219, all four fixed quadrants, 20% of whole 8-connected catalogue components hidden per quadrant. These seeds were selected as unused in the checkout: earlier registered seed ranges include 100–169 and 200–204. Verify the repository-wide seed search before execution; abort if any seed overlaps a prior H28-6 run or an existing experiment that would invalidate the pre-registration.
- **Label discipline:** all catalogue-derived quantities are computed only from `split.known`. Every visible fault pixel is masked pixel-exactly. Hidden components and their 600 m surrounding background ring are excluded from detector training and scoring; label-free rasters may be transformed on the full grid.
- **Baseline:** frozen H28-1 six-band magnetic/gravity edge matrix + the 32-band prepared feature matrix; OOF ridge emission, H27-4 `d_known > 1 px` pruning, and T-v2 `z >= 3` link additions built from `split.known`, with additions at least 3 px from existing retained predictions.
- **Candidate:** same feature stack, estimator, random seeds, OOF partitions, ridge extraction, budget, prune, topology, and placement rules; append only the eight H28-6 radiometric features. No tuning, threshold search, or post-hoc substitutions.
- **Per-cell measures:** exact DTI parts (`TPw`, `FPw`, `FNw`), number of withheld positive pixels, candidate/baseline emitted count, feature canary, and integrity checks. Pool TPw/FPw/FNw across cells before computing pooled DTI. Report both pooled DTI and seed-level paired candidate-minus-baseline DTI; bootstrap the 10 seed-level differences with 10,000 deterministic resamples and fixed RNG seed 20261025 for a percentile 95% interval. The interval is a seed-resampling summary, not proof of spatial independence.
- **Controls:** the paired H28-1+T-v2+H27-4 r1 baseline is the frozen current-best control. Also report candidate minus same-count random selection from the identical candidate ridge pool as a ranking/placement control: select the same pre-thinning budget `k` with a seeded uniform sample, then call the same `thinning.dot_thin` and the same prune/link/spacing logic. Use one frozen control RNG per fold/seed derived from `20261025 + 1000*seed + fold_index`. Do not interpret it as a live score.

## Frozen promotion gate and stop rule

All conditions must pass before a full-map research candidate may be called eligible for a separate selector review:

1. All 8 feature-only holdout canaries have direction-invariant AUC <=0.90.
2. Candidate pooled HOLDOUT-DTI exceeds baseline pooled HOLDOUT-DTI.
3. Mean seed-paired ΔHOLDOUT-DTI is at least +0.0010 and its bootstrap 95% lower bound is >0.
4. Candidate improves in at least 3/4 pooled fold means and at least 8/10 seed means.
5. Candidate beats the same-count random-order ridge control in pooled HOLDOUT-DTI.
6. Integrity: all 40 cells are complete; no prediction overlaps visible catalogue pixels; probabilities are finite in [0,1]; transform/source hashes and grid match.
7. Surface Spearman correlation is <=0.90 for every pinned registry raster before placement, and final directed Euclidean-3-pixel dot overlap is <=70% for every registry raster.

If any efficacy condition fails, the verdict is **negative**. A unique all-finite GeoTIFF may be generated only as a reproducibility artifact under `docs/downloads/research/`, and must say **NEGATIVE RESEARCH ARTIFACT — NOT APPROVED FOR SUBMISSION**. It cannot use a weekly slot. If all internal gates pass, a candidate artifact may be prepared for review, but this test does not select a weekly slot or establish performance on organizer-created expert labels. No upload, slot selection, or public-score claim is automated.

## Experiment budget

Maximum three experiments and two hours: (E1) feature-only canary plus pre-placement surface uniqueness; (E2) frozen 10-seed paired holdout/control; (E3) full-fit artifact build and independent format/final-uniqueness audit only if E2 passes, otherwise negative-research artifact or stop. No tuning or fourth experiment.
