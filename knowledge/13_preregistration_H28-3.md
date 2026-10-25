# Preregistration: H28-3 dilatational-strain × conductivity corridors

**Written:** 2026-10-25 UTC **before** implementation and before using seeds 160–169.

## Hypothesis and non-fault alternative

A buried or alluvium-covered fault can localize deformation and fluid flow without preserving a catalogue-quality surface scarp. At the 100-m grid scale, a narrow co-location of strain-rate structure (second-invariant / shear / positive dilatation) and an electrical-conductivity anomaly or boundary could therefore rank a fault missing from the published USGS/INGENIOUS compilation.

The named non-fault process that could mimic this signal is a **conductive sedimentary/clay basin boundary coincident with smooth regional geodetic strain**, including the effects of coarse source resolution, interpolation, and unrelated lithologic contacts. The transform is a candidate detector feature, not a fault interpretation or a geothermal-vent map.

## Inputs, provenance, and readiness

Use only the restored, hash-pinned owner-mirror `training_features.tif` and its embedded descriptions, verified by `scripts/prepare_data.py` and `data/manifest.json`:

* `geod_2ndinv` — geodetic second invariant, strain-rate tensor magnitude;
* `geod_shearrate` — geodetic shear rate;
* `geod_dilaterate` — geodetic volumetric strain rate;
* `cond_surf` — subsurface electrical-conductivity surface; and
* `depth_to_base_surf` — depth to basement surface.

No new external data is needed. The science context and manual-review source links for the airborne/geophysical products are listed in `registry/sources.json`, especially the USGS companion Great Basin releases row. This run does **not** assert that the owner-mirror competition raster is organizer-authenticated.

### Leakage canary, frozen rule

For each of the five source columns and each derived H28-3 column, calculate direction-invariant full-catalogue ROC AUC (the larger of `AUC(x)` and `AUC(-x)`) before evaluating the paired candidate. **Any AUC > 0.90 is treated as leakage until proved otherwise and makes the gate fail closed.** The source-column values measured before implementation are all <=0.5702 and are repeated by the runner. A canary is only a safety screen, never an efficacy result.

## Frozen label-free transform

Every operation below is deterministic and uses no label, split, holdout truth, candidate score, or peer raster. The 100-m grid and all source fields must match the template exactly; otherwise fail closed.

1. Intersect the template footprint with finite, non-sentinel cells of all five inputs. For filtering only, nearest-fill invalid cells from this common valid mask. All output feature values at invalid cells are set to zero.
2. Define scalar fields: `I = log1p(max(geod_2ndinv, 0))`, `H = log1p(max(geod_shearrate, 0))`, `D = max(geod_dilaterate, 0)`, `C = log1p(max(cond_surf, 0))`, and `B = -log1p(max(depth_to_base_surf, 0))`. Apply the fixed in-footprint 5th/95th robust scaling and clip every scalar field to `[0,1]`.
3. At fixed Gaussian sigma **3 pixels (300 m)**, smooth `I`, `H`, and `C`; calculate centered finite-difference gradients at 100-m spacing. Robust-scale the gradient magnitudes `|∇I|`, `|∇H|`, and `|∇C|` using their own common-valid 5th/95th percentiles.
4. Define a strain-core surface `S = sqrt(I_scaled * H_scaled) * D_scaled`. Define a conductive core `C_scaled`. Define `alignment = abs(dot(unit∇I, unit∇C))`, zeroed unless both gradient magnitudes are at or above their own fixed in-footprint 10th percentile.
5. Append exactly six H28-3 features, in this immutable order:
   1. `strain_dilation_core = S`;
   2. `strain_gradient_300m = |∇I|_scaled`;
   3. `shear_gradient_300m = |∇H|_scaled`;
   4. `conductivity_gradient_300m = |∇C|_scaled`;
   5. `strain_conductivity_corridor = min(S, C_scaled) * sqrt(|∇I|_scaled * |∇C|_scaled) * alignment`;
   6. `shallow_basement_corridor = strain_conductivity_corridor * B_scaled`.

The model may learn how to weight the six appended features; no post-hoc threshold, spatial dilation, or emission-count adjustment is permitted.

## Paired holdout protocol

* **Evaluator:** `H28-3-holdout-v1`, implemented in `scripts/run_h28_3_strain_holdout.py`, using `gems27.metric` (triangular 300-m kernel, alpha=0.2, beta=0.8) and `gems27.holdout`.
* **Splits:** fixed NW, NE, SW, SE quadrants; each cell hides whole 8-connected catalogue components at the existing 20% fraction. The 600-m collar in `oof_detector` excludes training samples next to the held-out quadrant.
* **Catalogue discipline:** the supervised surface consumes only non-catalogue geophysical values. In each cell all topology links are constructed only from `split.known`, and predictions are pixel-exactly masked from `split.known`. No transform derives a feature from hidden labels.
* **Baseline:** the current holdout best, 32 prepared features + H28-1 six potential-field features + T-v2 additions + H27-4 one-pixel flank prune, with the frozen H28-1 configuration.
* **Candidate:** the identical baseline plus the six H28-3 features. The estimator, negative sampling, random seeds, ridge extraction, pre-thin fraction, dot thinning, T-v2 rule, and H27-4 prune are identical to the baseline.
* **Fresh seeds:** 160, 161, …, 169. Seeds 140–149 (H28-1) and 150–159 (H27-10) are never reused.
* **Control:** a deterministic, same-count uniform replacement control generated in the active region from `seed + 91_000`; it tests whether the H28-3 selector improves over emission geometry alone.
* **Reporting:** report per-cell DTI/TPw/FPw/dots, pooled DTI, withheld-positive count, seed-level paired mean difference and a non-parametric 95% bootstrap interval across the ten seed-level paired means (10,000 deterministic resamples, RNG seed 20261025). The interval is a resampling uncertainty summary, not evidence that spatial cells are independent.

## Frozen promotion gate and stop rule

H28-3 passes only if **all** are true:

1. no source or derived feature exceeds the 0.90 leakage-canary ROC-AUC threshold;
2. candidate pooled HOLDOUT-DTI exceeds baseline pooled HOLDOUT-DTI;
3. the mean paired HOLDOUT-DTI difference is at least +0.0010, with the bootstrap 95% lower bound > 0;
4. candidate minus baseline is positive in at least 3/4 folds and at least 8/10 seeds;
5. candidate beats the same-count uniform replacement control by at least +0.0010 pooled DTI;
6. all integrity checks pass: 40 cells, known-catalogue overlap 0, finite `[0,1]` probabilities, source descriptions / grid / hashes correct.

If any condition fails, record the negative result, create **no submission-ready TIFF**, retain existing slot files, and spend no weekly slot. If all conditions pass, a separate builder may create a unique content-hashed **unscored** TIFF. Before it is marked okay to submit, it must pass: (a) the GeoTIFF validator, (b) no-on-catalogue check, and (c) the parallel registry duplicate rule — Spearman raster rank correlation <=0.90 and <=70% of its dots within 3 pixels of every registry raster. The resulting run card must label every model result HOLDOUT-DTI and every score claim OWNER-REPORTED or ORGANIZER-CONFIRMED as appropriate.

A passed catalogue-internal gate never establishes performance on the organizer’s hidden expert labels and never authorizes an automated upload.
