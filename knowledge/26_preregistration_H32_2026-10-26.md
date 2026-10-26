# Pre-Registration & Ranked Untried Hypotheses: `H32-1` (`Lane L-S11-2026-10-26`) — Poisson-Demagnetized Hydrothermal Conduit, Asymmetric Graben Clay-Cap Coupling & Cover-Aware 300 m Kernel-Expected-DTI Synthesis (`PDHC-K`)

**Date Frozen:** `2026-10-26` (written and git-committed *prior* to implementing `src/gems27/poisson_conduit_dti.py` or running `E1`, `E2`, or `E3` on seeds `500–509`)  
**Declared Single Method Lane (Protocol §1):** `L-S11-2026-10-26` (`H32-1` / `PDHC-K` only)  
**Fresh Unconsumed Holdout Seeds:** `500, 501, 502, 503, 504, 505, 506, 507, 508, 509` (`10` seeds × `4` quadrants = `40` cells; verified 100% disjoint from all prior repo seed blocks `0–2`, `100–169`, `200–204`, `210–224`, `230–231`, `240–254`, `260–269`, `300–309`, `400–409`)  
**Experiment Cap (Protocol §6):** Strictly `≤ 3` experiments (`E1` 95-feature leakage canary + pre-placement surface uniqueness, `E2` 40-cell blind `600 m`-buffered paired spatial holdout vs `U0`, `B0`, `H28_1_B2`, `D0`, `H29-S`, and Session-10 champion `H31-S`, `E3` dual-partition stitched-OOF `[0, 1]` GeoTIFF + 25-raster cross-fleet uniqueness screen + automated validator + JSON Run Card) within `≤ 2` hours wall clock.

---

## 1. Ranked Pre-Implementation Screen of Four Genuinely Untried Geological Hypotheses

Checked against `registry/hypotheses.json`, `registry/next_hypotheses.json`, `knowledge/01`–`25`, and every module in `src/gems27/` (`subsurface_features.py`, `hydrothermal_piedmont.py`, `geothermal_conduit_nis.py`, `dip_rad_features.py`, `seismicity_fabric.py`, `updip_relay_features.py`, `hydrochemistry.py`). None of the four mechanisms below has been implemented or evaluated in `GEMSDOE27`:

| Rank | ID | Geological Hypothesis & Specific Input Layers | Physical Transform / Spatial Signature | Why Missing from USGS / INGENIOUS Catalogues | Differentiation from Prior Repo Work & Named Non-Fault Mimic | Expected Buffered `HOLDOUT-DTI` Gain | Cost & Data Status |
|---:|---|---|---|---|---|---|---|
| **1** | **`H32-1`** *(Selected for Session 11)* | **Poisson-Demagnetized Hydrothermal Conduit + Asymmetric Graben Clay-Cap Coupling + Canyon-Mouth Collinearity + Cover-Aware 300 m Kernel-DTI Synthesis (`PDHC-K`)**<br>Layers: `iso_grav_anom_vg`, `iso_grav_anom_hg`, `rtp`, `tmi_vg`, `TMI_up150`, `ThK`, `UTh`, `depth_to_base_surf`, `cond_surf`, `geod_shearrate`, `geod_dilaterate`, `det_elev`, `det_gradient`, `det_local_relief`, `gdr_volcanic_vents_in_footprint.csv` (`row, col` only) | (A) Local `1.5 km` Gaussian-weighted Cordell–Taylor Poisson regression residual $\lvert g_{zz} - (\alpha_{\text{loc}} M_{\text{RTP}} + \beta_{\text{loc}})\rvert$ gated by $|\nabla_h g_z|$ and $\partial_z T \le 0$; (B) directed basinward ($\pm 400\text{ m}, \pm 800\text{ m}$ along $+\nabla D_b / \|\nabla D_b\|$) hanging-wall vs footwall playa-detrended MT `cond_surf` clay-cap asymmetry $\times \log(1 + \|\nabla D_b\|)$; (C) `1.2 km` 8-azimuth collinearity of piedmont canyon-mouth slope breaks + Quaternary volcanic vent strain corridors; (D) sediment-cover blindness gate $w_{\text{blind}}(D_b, R_{\text{loc}})$ inside `lidar_valid` + hybrid core-classifier / `300 m` DTI-kernel Poisson-deviance regressor | Ascending $150\text{–}260^\circ\text{C}$ $\text{H}_2\text{S}$ fluids oxidize crustal magnetite to hematite/pyrite (`erasing magnetic edges`) and form hanging-wall smectite clay caps beneath flat playas/bajadas (`erasing 1 m LiDAR scarps` even where 3DEP LiDAR was flown, e.g., `SW` Carson Sink / Bradys / Desert Peak / Soda Lake / Dixie Valley) | `subsurface_features.py` used $\min(\|\nabla \text{RTP}\|, \|\nabla g\|)$ (**zeroing** magnetite-destroyed conduits); `H28-3` multiplied co-located `dil × cond` (`-0.0026`); `H31-1` weighted `0.65 * p_full` everywhere `lidar_valid == 1`, suppressing buried `SW` basin conduits by `78%` (`SW = 0.02872 < H29-S 0.02967`).<br>*Mimics:* Non-magnetic carbonate-on-granite contacts / reversed tuffs ($\alpha_{\text{loc}} < 0$), evaporative salt playas (`2 km` background subtracted), hogbacks ($\nabla D_b \cdot \hat{\mathbf{u}}_{\text{down}} \le 0$). | **`+0.0008` to `+0.0035`** over `H31-S` (`+0.0040` to `+0.0065` over `H29-S`) | Low–medium (`~8 min` compute, `<1.2 GiB` RAM); 100% hash-pinned local stack |
| **2** | **`H32-2`** | **3-D Euler Deconvolution Structural-Index ($N=0$ Fault Step vs $N=1$ Sill/Flow Edge) Depth-Continuity Tracker (`Reid et al. 1990`)**<br>Layers: `rtp`, `tmi_hg`, `tmi_vg`, `iso_grav_anom`, `iso_grav_anom_hg`, `iso_grav_anom_vg` | Sliding `11×11 px` (`1.1 km`) least-squares inversion of $(x - x_0)\partial_x F + (y - y_0)\partial_y F + (z - z_0)\partial_z F = N(B - F)$ comparing structural index $N = 0$ (subvertical fault contact) against $N = 1$ (thin Tertiary basalt sill/flow edge), retaining tight horizontal $(x_0, y_0)$ solution clusters ($\sigma_{xy} \le 150\text{ m}$) | Distinguishes deep-rooted subvertical basement faults ($z_0 = 0.3\text{–}2.5\text{ km}$, $N = 0$) concealed under Miocene–Quaternary basin fill from shallow volcanic flow margins that dominate raw `RTP` gradients | `H31-1` used Miller–Singh tilt angle $\tan^{-1}(V / \|\nabla_h F\|)$, never 3-D Euler $(x_0, y_0, z_0)$ spatial clustering or $N=0$ vs $N=1$ sill rejection.<br>*Mimic:* Steep pluton walls (deconfounded via gravity/magnetic colinearity length `>3 km`). | `+0.0005` to `+0.0025` | Medium (`11×11` linear solver across `5.17M` cells); hash-pinned local stack |
| **3** | **`H32-3`** | **Multi-Ratio Gamma-Ray Spectrometric Redox (`U/Th`) & Adularia–Sericite (`K/Th`) Conduit Ridge Detector**<br>Layers: `geodawn_extensions_u8.tif` (`ThK`, `UK`, `UTh`), `geodawn_rad_u8.tif` (`K`, `Th`, `U`), `det_gradient`, `cond_surf` | Axial Hessian crests of `U/Th` uranyl-reduction fronts and `K/Th` potassic alteration halos residualized against `det_gradient` and `det_elev` to strip granitic-detritus alluvial fan aprons | Soluble $\text{U}^{6+}$ precipitates as $\text{U}^{4+}$ where reducing $\text{H}_2\text{S}/\text{CH}_4$ fault gases seep through thin Quaternary cover, marking active leaky fault traces lacking topographic scarps | `H29-2` (`dip_rad_features.py`, negative) tested only `100–300 m` dip-advected `K/Th/U` differences, never `geodawn_extensions_u8` (`ThK`, `UK`, `UTh`) redox/potassic axial crests.<br>*Mimic:* Uraniferous rhyolite ash-flow tuffs and granitic bajadas (`<50 cm` gamma penetration). | `+0.0003` to `+0.0018` | Low; hash-pinned local stack |
| **4** | **`H32-4`** (`H27-16`) | **Official DOE GDR #1391 Regional Paleo-Geothermal Sinter/Tufa/Travertine Vectors + 2 m Temperature-Probe Residuals (`Kraal et al. 2022`; `Siler et al. 2022`)**<br>Layers: GDR #1391 `paleo_geothermal_sinter_tufa` (`faffcf69...`), `ingenious_2m_temp_probes` (`1301f70d...`) | Anisotropic `1–6 km` sinter/tufa terrace alignments (e.g., Granite Springs `6 km` horst lineament) corroborated by local `> +2.5 °C` 2 m temperature-probe anomalies residualized against elevation and albedo | Siliceous sinter and travertine aprons cement fault scarps and mask Holocene rupture morphology while directly mapping Quaternary hydrothermal upflow conduits | `H29-1` and `H31-1` used `gdr_wellspring_in_footprint.csv` (`27,092` wells/springs), whereas the separate GDR #1391 sinter/tufa vector and 2 m probe packages are not yet in `data_cache/`.<br>*Mimic:* Pleistocene Lake Lahontan shoreline tufa mounds (`~1,330 m` contour). | `+0.0010` to `+0.0060` | **External-data-gated** (`gdr.openei.org`, DOI `10.15121/1881483`, CC-BY-4.0; blocked by sandbox egress allowlist) |

---

## 2. Exact Diagnosis of Session-10 `H31-1` Deficit Targeted by `H32-1`

Quadrant diagnostic inspection of `H31-1` (`evidence/h31_s10_e2_holdout_400_409.json`) revealed a striking physical asymmetry:
- In **`NE_LidarGapHeavy`** (`45.8%` `~lidar_valid`, `dtb_med = 204.4 m`), `H31-S` surged **`+0.00843`** over `H29-S` (`0.06629` vs `0.05786`) because `~lidar_valid` routed authority to the calibrated subsurface expert `M_Sub`.
- In **`SW`** (`83.4%` `lidar_valid`, `20,534` catalogue fault px = **`33.7%` of all faults**, **`dtb_med = 454.7 m` deepest Cenozoic basins**, `8` of `21` Quaternary volcanic vents — Carson Sink, Bradys, Desert Peak, Soda Lake, Salt Wells, Dixie–Fallon), `H31-S` **regressed `-0.00095` below `H29-S`** (`0.02872` vs `0.02967`)!
- **Root physical & statistical causes:**
  1. **`lidar_valid` $\neq$ scarp preservation:** Over thick, low-relief Holocene playas and bajadas ($D_b > 250\text{ m}$, $R_{\text{loc}} < 30\text{ m}$), USGS 3DEP 1 m LiDAR was flown (`lidar_valid == 1`) yet unconsolidated sediment buries active faults (`pf ≈ 0`). `H31-1`'s fixed `0.65 * pf + 0.20 * ps + 0.15 * sqrt(pf * ps)` suppressed `M_Sub` by **`78%`** across all LiDAR-flown sediment basins!
  2. **Missing hydrothermal demagnetization & asymmetric clay-cap physics:** `SW` and `NE` blind geothermal conduits destroy titanomagnetite (`Cordell–Taylor` breakdown) and form `300–900 m` basinward smectite clay caps (`cond_surf`) down-dip of `depth_to_base_surf` footwall hinges.
  3. **1-pixel binary label starvation of `300 m` subsurface conduits:** Training `M_Sub` only on 1-pixel `y ∈ {0, 1}` labelled `1 <= d < 3 px` fault-zone pixels (`true DTI credit = 0.33–0.67`) as hard negatives (`y = 0`), throwing away `80%` of the `300 m` geophysical conduit support.

---

## 3. Frozen `H32-1` (`PDHC-K`) Feature, Cross-Fitting & Placement Specification (Zero Tuning Allowed)

### 3.1 `16` New Label-Free `H32` Channels (`src/gems27/poisson_conduit_dti.py`, `95` Total Features)
Built strictly from hash-pinned `training_features.tif` (excluding band 6 `tc`), `prepared_features.npy`, `geodawn_extensions_u8.tif`, and `gdr_volcanic_vents_in_footprint.csv` (`[row, col]` ONLY — `dist_known_fault_px` asserted unread):
- **Non-LiDAR Subsurface & Piedmont Channels (`0..13`, 14 ch):**
  0. `h32_poisson_demag_resid_s15`: $|z(g_{zz}) - (\mu_G + \alpha_{\text{loc}}(z(\text{rtp}) - \mu_M))|$ ($\sigma = 15\text{ px}$).
  1. `h32_poisson_alpha_slope_s15`: $\text{clip}(\text{Cov}_{15}(z(g_{zz}), z(\text{rtp})) / \max(\text{Var}_{15}(z(\text{rtp})), 0.05), -3, 3)$.
  2. `h32_hydro_demag_conduit_idx`: `col0 * log1p(max(z(iso_grav_anom_hg), 0)) * sigmoid(-z(tmi_vg))`.
  3. `h32_shallow_mag_attenuation`: `z(TMI_up150) - z(tmi_vg)`.
  4. `h32_rad_potassic_alteration`: `-z(ThK) * log1p(max(z(iso_grav_anom_hg), 0))`.
  5. `h32_rad_uth_redox_front`: `max(z(UTh), 0) * axial_crest(z(UTh), sigma=1.5)`.
  6. `h32_mt_local_clay_excess`: $\tilde{\sigma}_{\text{MT}} = \log(1 + \max(\text{cond\_surf}, 0)) - \mathcal{G}_{20}(\log(1 + \max(\text{cond\_surf}, 0)))$.
  7. `h32_clay_cap_asym_400m`: $\tilde{\sigma}_{\text{MT}}(x + 4\hat{\mathbf{n}}) - \tilde{\sigma}_{\text{MT}}(x - 4\hat{\mathbf{n}})$, $\hat{\mathbf{n}} = \nabla D_b / (\|\nabla D_b\| + 10^{-4})$.
  8. `h32_clay_cap_asym_800m`: $\tilde{\sigma}_{\text{MT}}(x + 8\hat{\mathbf{n}}) - \tilde{\sigma}_{\text{MT}}(x - 8\hat{\mathbf{n}})$.
  9. `h32_graben_clay_conduit_idx`: $\log(1 + \|\nabla D_b\|) \cdot \max(0, A_{\text{clay}, 4}, A_{\text{clay}, 8})$.
  10. `h32_dtb_hinge_axial_crest`: `axial_crest(log1p(|∇depth_to_base_surf|), sigma=1.8)`.
  11. `h32_qvent_strain_corridor`: $\log(1 + 10^4 V_{\text{vent}}) \cdot \log(1 + \max(z(\text{shear}) + z(\text{dil}), 0))$.
  12. `h32_piedmont_knickpoint_impulse`: down-slope `det_gradient` drop gated by down-slope basin thickening ($\nabla D_b \cdot \hat{\mathbf{u}}_{\text{down}} > 0$).
  13. `h32_canyon_mouth_collinearity_1200m`: `_line8_max_lowmem(col12, half_len=6) - G_6(col12)`.
- **Full-Stack Cover-Coupled Channels (`14..15`, 2 ch):**
  14. `h32_lidar_knick_fan_apex`: `max(col13, 0) * log1p(lidar_step_max * lidar_coh100)`.
  15. `h32_sediment_cover_blindness`: $w_{\text{blind}}(x) = \sigma((D_b - 250)/150)\cdot\sigma((30 - R_{\text{loc}})/12) \in [0, 1]$.

### 3.2 Frozen Dual-Target Cover-Aware Nested Spatial Cross-Fitting
- **Spatial Guards:** 4-quadrant folds (`NW`, `NE_LidarGapHeavy`, `SW`, `SE`) with strict `buffer_px = 6.0` (`600 m`) guard between training and test cells. Full-map submission (`E3`) averages the 4-quadrant OOF surface (`0.5`) with the 45°-rotated 4-sector OOF surface (`0.5`).
- **Stage-1 Pairwise Buffered Experts (`C(4,2) = 6` pairs):**
  - Inside each buffered training pair `train_grid`, compute training-only distance $d_{\text{tr}} = \text{EDT}(\neg(\text{labels} \land \text{train\_grid}))$ and continuous `300 m` DTI kernel target $y_K = \text{clip}(1 - d_{\text{tr}}/3.0, 0, 1)$ (compact `300 m` support strictly inside the `>600 m`-buffered training fold — zero test-fold dependence).
  - **Subsurface Conduit Expert (`74` non-LiDAR cols = `20 base + 15 sub15 + 16 h29 + 9 h31 + 14 h32`):**
    - `clf_sub`: `HistGradientBoostingClassifier(max_iter=240, learning_rate=0.055, max_leaf_nodes=63, min_samples_leaf=80, l2_regularization=2.0)` on `y ∈ {0, 1}`.
    - `reg_sub`: `HistGradientBoostingRegressor(loss="poisson", max_iter=240, learning_rate=0.055, max_leaf_nodes=63, min_samples_leaf=80, l2_regularization=2.0)` on continuous `y_K ∈ [0, 1]` (`d_tr == 0` weight `1.0`, `80k` subsampled `0 < d_tr < 3` with importance weight `N_flank / n_flank`, `260k` subsampled `d_tr >= 3` weight `1.0`), quantile-matched inside each target sector onto `clf_sub`'s marginal scale (`reg_sub_cal`) so $p_{\text{sub}} = 0.55\,p_{\text{sub,clf}} + 0.45\,p_{\text{sub,reg\_cal}}$.
  - **Full Multi-Physics Expert (`95` cols = `32 base + 15 sub15 + 20 h29 + 12 h31 + 16 h32`):**
    - `clf_full`: `HistGradientBoostingClassifier` (same hyperparameters) + `reg_full`: `HistGradientBoostingRegressor(loss="poisson")` quantile-matched onto `clf_full` so $p_{\text{full}} = 0.70\,p_{\text{full,clf}} + 0.30\,p_{\text{full,reg\_cal}}$.
  - **Cover-Aware Regime Synthesis (`synthesize_cover_aware_stage1`):**
    - On `lidar_valid == 1`: let $q_s = \text{quantile\_calibrate\_gap}(p_{\text{sub}}, \text{ref}=p_{\text{full}}[\text{lv}], \text{scale}=0.92)$ and $\eta(x) = 0.50\,w_{\text{blind}}(x) \in [0, 0.50]$:
      $$p_{\text{s1}}(x) = (1 - \eta(x))\bigl(0.62\,p_{\text{full}} + 0.22\,q_s + 0.16\sqrt{p_{\text{full}} q_s}\bigr) + \eta(x)\max(p_{\text{full}},\, 0.88\,q_s)$$
    - On `lidar_valid == 0`: $p_{\text{s1}}(x) = \text{quantile\_calibrate\_gap}(p_{\text{sub}}[\neg\text{lv}], \text{ref}=p_{\text{s1}}[\text{lv}], \text{scale}=0.94)$.
- **Stage-2 Cover-Aware Dual-Objective Axial Refiner (`106` cols = `95` features + `11` axial/cover context channels: `[p_s1, q_sub, p_full, w_blind, frangi_s1(1.0, 2.0, 3.5), line8_max_s1, crest_s1, crest_sub_s20, p_s1 - bg8]`):**
  - Fits `clf_s2` (`HistGradientBoostingClassifier(max_iter=160, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=120, l2_regularization=4.0)`) and `reg_s2` (`HistGradientBoostingRegressor(loss="poisson", ...)` quantile-matched onto `clf_s2`) on strictly inner-OOF Stage-1 surfaces, outputting $p_{\text{s2}} = 0.60\,p_{\text{s2,clf}} + 0.40\,p_{\text{s2,reg\_cal}}$.
- **Blind Off-Catalogue Placement (`H32-S`):**
  - Eligibility: `fold_domain & (~known) & (EDT(~known) > 2.0)` (`B2 > 200 m`), matched full-map budget **`37,654` dots** (`fold_budget` proportional to quadrant footprint area in `E2`).
  - Axial crest weighting: `sharpen_probability_crest(p_s2, fold_domain)` (`0.65 + 0.35 * rank(crest)`).
  - Submodular 300 m CELF cover: `weighted_celf_cover(p_sharp, elig, dom, budget=B, radius_px=3.0, gamma=1.35, min_sep_px=2.8)`.

---

## 4. Frozen Fail-Closed Promotion & Successor Gates

### Experiment `E1` — 95-Feature Leakage Canary & Pre-Placement Surface Uniqueness
1. **Gate E1.1 (Leakage Canary, Protocol §4):** Every one of the `16` new `H32` features (and all `79` prior features = `95` total) must have direction-invariant univariate `ROC-AUC ≤ 0.90` on withheld hidden fault segments across fresh seeds `500..509`.
2. **Gate E1.2 (Surface Uniqueness, Protocol §1):** Pre-placement OOF surface `p_s2` must satisfy `|Spearman ρ| ≤ 0.90` against all `12` pinned focus-site peer rasters, all `10` `2026-10-26` active sibling focus-site `.tif`s, and both live-scored `GEMSDOE27` submissions (`Slot 1` + `H29-S`).

### Experiment `E2` — Blind Paired 40-Cell Buffered Holdout on Untouched Seeds `500..509`
Evaluated on `gems27.metric.dti_binary` (`α=0.2, β=0.8, R=3 px` triangular) with `holdout.buffered_scoring_mask(sp, foot, buffer_px=6.0)` across `U0`, `B0`, `H28_1_B2`, `D0`, `H29-S` (live `0.2190`), **`H31-S`** (Session-10 `0.047302` champion), `H32-A` (`H32` detector + Poisson `d=2.8`), and **`H32-S`** (`H32` detector + axial `CELF min_sep=2.8`):
1. **Pooled Superiority Over ALL Baselines Including `H31-S`:** `pooled_buf["H32-S"] > max(pooled_buf["U0"], pooled_buf["B0"], pooled_buf["H28_1_B2"], pooled_buf["D0"], pooled_buf["H29-S"], pooled_buf["H31-S"])`.
2. **Strict Paired Bootstrap 95% CI vs `B0` & `D0`:** `paired_H32S_minus_B0.ci95[0] > 0.0` (`≥ 9/10` seeds, `4/4` folds) AND `paired_H32S_minus_D0.ci95[0] > 0.0` (`≥ 3/4` folds).
3. **Strict Paired Bootstrap 95% CI vs Live-Scored `H29-S` (`0.2190`):** `paired_H32S_minus_H29S.ci95[0] > 0.0` (`≥ 8/10` seeds).
4. **Strict Paired Successor Gate vs Session-10 Champion `H31-S`:** `paired_H32S_minus_H31S.ci95[0] > 0.0` AND `positive_seeds ≥ 7/10`.
5. **Detector Ablation Sanity:** `pooled_buf["H32-A"] > pooled_buf["D0"]`.

*Fail-closed successor rule:*
- If **ALL** clauses `E1 + E2.1–E2.5 + E3.1–E3.3` pass: `H32-1` promotes (`verdict = "promote"`, `ok_to_submit = True`) and supersedes unscored Session-10 `H31-1` (`h31_s10_run_card_2026-10-26.json` updated to `superseded_by: "H32-1"`, `ok_to_submit = False`) so **at most ONE unscored submission is ever marked `OK TO SUBMIT`**.
- If **ANY** clause fails: `H32-1` is shipped in `docs/downloads/research/` with `verdict = "negative"` and `ok_to_submit = False`, and `H31-1` remains the sole machine-approved `OK TO SUBMIT` candidate.

### Experiment `E3` — Full-Map Unique `[0, 1]` GeoTIFF, 25-Raster Duplicate Screen & Automated Run Card
1. **Gate E3.1 (Format & `[0, 1]` Range):** Single-band `float32`, `EPSG:32611`, `3730 × 3292`, exact geotransform `(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)`, `0` NaNs across all `12,279,160` cells (`-allfinite.tif`), values strictly in `[0.0, 1.0]` (`{0.0, 1.0}`), `0` catalogue overlap, `d_cat > 2.0 px` on all `37,654` dots, `min_self_dist ≥ 2.8 px`, single-member `.zip` byte-identical.
2. **Gate E3.2 (Uniqueness, Protocol §1):** Directed 3-px dot overlap `≤ 0.70` AND post-placement `|Spearman ρ| ≤ 0.90` against **all 12 pinned focus-site peer rasters**, **all 10 `2026-10-26` active sibling focus-site `.tif`s** (including `GEMSDOE31 H31-T` `83fbc267a754` and `GEMSDOE24 DPRF1` `c1257c1d4b5a`), and **both live-scored `GEMSDOE27` submissions** (`Slot 1` `5512495c6bd1` + `H29-S` `511898747886`). Overlap vs unscored `H31-1` (`cf8e1bbef244`) is also computed and reported transparently in the Run Card.
3. **Gate E3.3 (Automated Machine Readiness):** `gems27.readiness.publication_decision(run_card, ROOT)["ok_to_publish_as_submission"]` matches the gate outcome with zero human intervention.
