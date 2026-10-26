# Pre-Registration: Hypothesis `H31-1` (`Lane L-S10-2026-10-26`) — Dual-Regime Corroborated Geothermal Conduit & Walker Lane Transtensional Ridge Synthesis (`DRCG-WL`) with `min_sep_px = 2.8` Axial-Crest 300 m CELF Allocation

**Date Frozen:** `2026-10-26` (written and frozen prior to writing `src/gems27/geothermal_conduit_nis.py` or executing `E1`, `E2`, or `E3`)  
**Declared Single Method Lane (Protocol §1):** `L-S10-2026-10-26` (`H31-1` only)  
**Fresh Unconsumed Holdout Seeds:** `400, 401, 402, 403, 404, 405, 406, 407, 408, 409` (`10` seeds × `4` quadrants = `40` cells; verified disjoint from all previously consumed/reserved repo seeds `0–2`, `100–169`, `200–204`, `210–224`, `240–254`, `300–309`)  
**Experiment Cap (Protocol §6):** Strictly `≤ 3` experiments (`E1` leakage canary + surface uniqueness, `E2` 40-cell blind buffered spatial holdout, `E3` full-map dual-partition stitched-OOF GeoTIFF + 28-raster uniqueness + automated validator + JSON Run Card) and `≤ 2` hours wall clock.

---

## 1. Scientific Motivation & Exact Live-Score Bugs Targeted

Forensic inversion of `GEMSDOE27`'s newly `OWNER-REPORTED` live score (`gems27-h29-hydrothermal-piedmont-celf-20261025-511898747886-allfinite.tif` = **`0.2190`**, #1 of the five `2026-10-25` non-`H19-5` submissions) alongside `GEMSDOE70` (`0.2478`) and `GEMSDOE32` (`0.2778`) (`knowledge/23_focus_sites_and_02778_phd_autopsy_20261026.md`) identified four exact quantitative deficits in `H29-S`:

1. **`min_sep_px = 2.0` 2D Blob Clustering (`-11.0%` coverage loss, `c = 0.0527` vs `0.0592`):** Allowing `200 m` minimum dot separation on `400–900 m` smoothed surfaces caused `8.51%` of dots to have `≥ 3` neighbors within `300 m` (`12.5×` worse than `GEMSDOE32`'s `0.68%`). Enforcing **`min_sep_px = 2.8`** on axial-crest-sharpened probabilities eliminates 2D blob crowding while preserving 300 m submodular junction/tip placement.
2. **Single-Tree Starvation of the `24.63%` 1 m LiDAR Gap (`18.3%` dot share):** Fitting a single HGB across LiDAR-present (`75.37%`) and LiDAR-missing (`24.63%`) pixels starved blind basin faults where `lidar_* == 0`. `H31-1` fits a dedicated **LiDAR-free Subsurface/Seismic/Hydrothermal Expert (`M_Sub`, 61 non-LiDAR columns)** across 100% of buffered training faults, uses `M_Sub` to corroborate `M_Full` inside LiDAR tiles, and **monotone-quantile-calibrates `M_Sub` onto the combined OOF distribution** inside the `24.63%` LiDAR gap (`× 0.94` conservative playa damping).
3. **`SE` Walker Lane Seismogenic Deficit (`-0.0057` detector gap vs `D0`):** `H29` omitted `subsurface_features.py`'s `15` potential-field/strain/MT/seismicity transforms. `H31-1` fuses `subsurface15` + multi-scale `ieq_n100a15`/`deq_n100a15` structure-tensor anisotropy + transtensional `geod_shearrate × geod_dilaterate` + Blakely–Simpson Hessian contact crests (`-λ_min(H(‖∇F‖))`).
4. **Lake Lahontan Wave-Cut Shoreline Mimics & `200–500 m` Halo Bleed (`24.1%` at `d_cat ≤ 5`):** `H31-1` introduces exact algebraic **contour-obliquity (`sin²(θ_scarp - θ_contour) = 0.5(1 - cos 2Δθ)`)** from `∇det_elev` vs `(lidar_cos2strike, lidar_sin2strike)` to suppress contour-parallel Pleistocene shoreline benches (`~1,330–1,338 m`), and replaces `H29`'s broad `s2_smooth_s40` / `s2_smooth_s90` Gaussians with narrow axial vesselness (`σ = 1.0, 2.0, 3.5 px`) plus local halo subtraction (`p_s1 - G_8.0(p_s1)`).

---

## 2. Frozen Feature Specification (`100%` Label-Free; Zero Catalogue Distance)

All inputs come strictly from hash-verified files in `data/manifest.json` (`training_features.tif` excluding mislabelled band 6 `tc`, `lidar_scarp_features_u8.tif`, `geodawn_rad_u8.tif`, `geodawn_extensions_u8.tif`, `gdr_wellspring_in_footprint.csv` using only `[row, col, temp_c, geothermquartz_c, geothermchalc_c, geothermcat_c]`):

- **`base_X` (`32` ch):** 20 GeoDAWN bands (`0..19`) + 12 1-m LiDAR scarp bands (`20..31`, index `31 = lidar_valid`).
- **`subsurface15` (`15` ch, non-LiDAR):** `gems27.subsurface_features.build_transforms` (`rtp_edge_s1/s2/s4`, `grav_edge_s1/s2/s4`, `vg_edge_s1/s2`, `joint_edge_s2/s4`, `base_grad_s2`, `cond_grad_s2`, `strain_dil_x_2inv`, `seis_aniso_s3`, `seis_grad_s2`).
- **`h29_X` (`20` ch):** `gems27.hydrothermal_piedmont.build_h29_feature_matrix` (`0..16` non-LiDAR hydrothermal/piedmont/destriped-mag; `17..19` LiDAR-coupled piedmont scarp).
- **`h31_X` (`12` new ch in `src/gems27/geothermal_conduit_nis.py`):**
  - *Non-LiDAR (`0..8`, 9 ch):* `h31_blakely_rtp_crest_s15`, `h31_blakely_grav_crest_s20`, `h31_joint_blakely_crest`, `h31_wl_ieq_aniso_s2`, `h31_wl_deq_aniso_s4`, `h31_wl_transtension_shear_x_dil`, `h31_wl_seis_x_shear`, `h31_dem_breakline_crest`, `h31_hydro_conduit_corrob`.
  - *LiDAR Contour-Obliquity (`9..11`, 3 ch):* `h31_contour_obliquity_sin2`, `h31_oblique_scarp_step`, `h31_oblique_piedmont_scarp`.

---

## 3. Frozen Dual-Regime Cross-Fitting & Placement Parameters (Zero Tuning Allowed)

- **Spatial Cross-Fitting:** 4-quadrant folds (`NW`, `NE_LidarGapHeavy`, `SW`, `SE`) with `buffer_px = 6.0` (`600 m` exclusion around training/test boundaries and hidden segments). In `E3`, full-map emission averages the 4-quadrant OOF surface (`0.5`) with the 45°-rotated 4-sector OOF surface (`0.5`) so every pixel is strictly out-of-fold (`> 600 m` buffer) with zero seam artifacts.
- **Stage-1 Experts (`C(4,2) = 6` pairwise buffered models each; `HistGradientBoostingClassifier(max_iter=240, learning_rate=0.055, max_leaf_nodes=63, min_samples_leaf=80, l2_regularization=2.0)`):**
  - `M_Sub`: trained on `61` non-LiDAR columns (`base_X[:,:20] + subsurface15 + h29_X[:,:17] + h31_X[:,:9]`).
  - `M_Full_S1`: trained on all `79` columns (`base_X + subsurface15 + h29_X + h31_X`).
  - **Synthesis `p_s1`:** On `lidar_valid == 1`: `0.65 * p_full + 0.20 * p_sub + 0.15 * sqrt(p_full * p_sub)`. On `lidar_valid == 0`: `0.94 * quantile_calibrate(p_sub[~lv], ref=p_s1[lv], n_knots=1001)` computed strictly within each fold's domain.
- **Stage-2 Narrow Axial Refiner (`8` S2 features: `p_s1`, `p_sub`, `frangi_s10/s20/s35`, `line_max_500m`, `axial_crest`, `p_s1 - G_8.0(p_s1)`; `max_iter=150, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=120, l2_regularization=4.0`):** outputs `p_s2`.
- **Blind Off-Catalogue Placement (`H31-S`):**
  - Eligibility: `fold_domain & (~known) & (EDT(~known) > 2.0)` (`B2 > 200 m`), matched full-map budget **`37,654` dots** (`fold_budget` proportional to quadrant footprint area).
  - Axial crest weighting: `P_crest = p_s2 * (0.65 + 0.35 * rank_norm(clip(-λ_min(H(G_1.0(p_s2))), 0, ∞)))` computed strictly inside `fold_domain` (holdout) or `foot` (full map), zero access to `hidden` or `valid_scoring`.
  - Submodular 300 m CELF cover: `weighted_celf_cover(P_crest, elig, dom, budget=B, radius_px=3.0, gamma=1.35, min_sep_px=2.8)`.

---

## 4. Frozen Three-Experiment Budget & Fail-Closed Promotion Gates

### Experiment `E1` — Leakage Canary & Pre-Placement Surface Uniqueness (`scripts/run_h31_holdout.py --stage e1`)
- **Gate E1.1 (Leakage Canary, Protocol §4):** Every one of the `12` new `H31` features (and all `32` base + `15` subsurface + `20` `H29` features) must have direction-invariant univariate `ROC-AUC ≤ 0.90` on withheld hidden fault segments across seeds `400..409`. Any feature `> 0.90` halts immediately as leakage.
- **Gate E1.2 (Surface Uniqueness, Protocol §1):** Pre-placement OOF surface `p_s2` must satisfy `|Spearman ρ| ≤ 0.90` against all `12` pinned focus-site peer rasters AND against `GEMSDOE27` `Slot 1` (`5512495c6bd1`) and `H29-S` (`511898747886`).

### Experiment `E2` — Blind Paired 40-Cell Buffered Holdout on Fresh Seeds `400..409` (`scripts/run_h31_holdout.py --stage e2`)
Evaluated on `gems27.metric.dti_binary` (`α=0.2, β=0.8, R=3 px` triangular) with `holdout.buffered_scoring_mask(sp, foot, buffer_px=6.0)` across arms `U0` (uniform null), `B0` (full-32 + Poisson `d=2.8`), `H28_1_B2` (potential edges + Poisson `d=2.8`), `D0` (full-32 + 15 subsurface + Poisson `d=2.8`), `H29-S` (Session-7 champion, live `0.2190`), `H31-A` (`H31` detector + Poisson `d=2.8`), and **`H31-S`** (`H31` detector + crest-sharpened `CELF min_sep=2.8`):
1. **Pooled Superiority Over Every Baseline:** `pooled_buf["H31-S"] > max(pooled_buf["U0"], pooled_buf["B0"], pooled_buf["H28_1_B2"], pooled_buf["D0"], pooled_buf["H29-S"])`.
2. **Strict Paired Bootstrap 95% CI vs Full-32 Control `B0`:** `paired_H31S_minus_B0.ci95[0] > 0.0`, `positive_seeds ≥ 9/10`, `positive_folds == 4/4`.
3. **Strict Paired Bootstrap 95% CI vs Strongest Prior Control `D0` (the exact clause `H29-S` failed in Session 7):** `paired_H31S_minus_D0.ci95[0] > 0.0` AND `positive_folds ≥ 3/4`.
4. **Strict Paired Improvement vs Live-Scored `H29-S` (`0.2190`):** `paired_H31S_minus_H29S.ci95[0] > 0.0` AND `positive_seeds ≥ 8/10`.
5. **Detector Ablation Sanity:** `pooled_buf["H31-A"] > pooled_buf["D0"]` (proving the `H31` dual-regime detector itself beats `D0` at identical Poisson `d=2.8` placement!).

*Fail-closed rule:* If **any** clause 1–5 fails, `verdict = "negative"` and `ok_to_submit = False` — no threshold relaxation, no seed shopping, no refit.

### Experiment `E3` — Full-Map Unique GeoTIFF, 28-Raster Duplicate Screen & Automated Run Card (`scripts/build_h31_submission.py`)
- **Gate E3.1 (Format & `[0, 1]` Compliance):** Single-band `float32`, `EPSG:32611`, `3730 × 3292`, exact geotransform, `0` NaNs across all `12,279,160` cells (`-allfinite.tif`), values strictly in `[0.0, 1.0]` (`{0.0, 1.0}`), `0` catalogue overlap, `d_cat > 2.0 px` on all `37,654` dots, `min_self_dist ≥ 2.8 px`, single-member `.zip` verified.
- **Gate E3.2 (Uniqueness, Protocol §1):** Directed 3-px dot overlap `≤ 0.70` AND post-placement `|Spearman ρ| ≤ 0.90` against **every one of the 12 pinned focus-site peer rasters** (`registry/parallel_submission_registry.json`) **AND** against **both live-scored `GEMSDOE27` submissions** (`Slot 1` `5512495c6bd1` AND `H29-S` `511898747886`). Extended overlaps against all unscored research files in `docs/downloads/` and `docs/downloads/research/` are also measured and recorded in the Run Card.
- **Gate E3.3 (Machine Readiness Audit):** `gems27.readiness.publication_decision(run_card, ROOT)["ok_to_publish_as_submission"]` must evaluate to `True` **if and only if** `E1 + E2 + E3.1 + E3.2` all pass; if negative, the artifact is routed to `docs/downloads/research/` and flagged unmistakably as **`DO NOT SUBMIT / HOLD`** on Screen 1.
