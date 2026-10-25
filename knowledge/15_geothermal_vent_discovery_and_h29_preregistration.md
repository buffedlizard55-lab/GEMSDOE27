# 15 — Geothermal Vent & Blind Fault Discovery, Live Cross-Fleet Forensics, Ranked Untried Hypotheses (`H29-1..5`), and Frozen Preregistration (`Lane L-S7-2026-10-25`)

**Date (UTC):** 2026-10-25  
**Session / Branch:** Session 7 (`arena/f611593b-gemsdoe27`)  
**Status:** **FROZEN PREREGISTRATION PRIOR TO EXPERIMENT EXECUTION** (committed before running `E1`, `E2`, or `E3`; unused holdout seeds `210–219`, 40 quadrant×seed cells; strict `<= 3` experiment budget).

---

## 1. Deep Scientific Synthesis: Structural Controls on Blind Geothermal Vents & Unmapped Faults in the NW Great Basin

All physical claims below are verified first-hand against official public releases inspected during this session (`registry/sources.json`):

1. **USGS GeoDAWN Airborne Magnetic & Radiometric Survey Physics (`doi:10.5066/P93LGLVQ`; Glen & Earney, 2024):**
   - Covers **51,857 km²** across four survey blocks (Winnemucca, Fallon, Hawthorne, Tonopah; **149,030 line-km** flown Nov 2021–Nov 2022).
   - **Survey geometry & sensor-drape confounding:** Flight lines were flown strictly **East–West (`azimuth = 90°`)** at **200 m** spacing (`100–150 m` nominal terrain clearance, Area 1) and **400 m** spacing (`150–200 m` nominal clearance, Area 2), with N–S (`azimuth = 0°`) tie lines every `2,000 m` / `4,000 m` and aircraft climb/descent rates capped at `<= 22°`.
   - **Implication for fault detection:** Raw `100 m` gridded magnetic (`rtp`, `tmi`) and gamma-ray spectrometric (`K`, `Th`, `U`, `ThK`) rasters contain residual **200–400 m E–W (`row`-periodic) flight-line corrugation** AND terrain-clearance attenuation over steep canyon walls (`> 22°` relief where the fixed-wing aircraft rides high above valleys and scrapes ridges). Removing short-vertical-wavelength E–W corrugation before computing horizontal derivatives prevents `90°` flight-line stripes from masquerading as E–W stepover faults.
   - **Shallow hydrothermal demagnetization (`TMI - TMI_up150`):** Upward continuation to `150 m` (`TMI_up150`) attenuates shallow `< 400 m` magnetic sources (`e^{-k \Delta z}`) while preserving deeper plutonic/basement anomalies. Along active hydrothermal fault conduits, ascending acidic/neutral-chloride fluids alter primary titanomagnetite to non-magnetic pyrite,hematite, clays, and leucoxene in the top `100–500 m`, producing narrow linear **shallow demagnetization troughs** paired with **potassium metasomatism / adularia-illite alteration fronts** (`|\nabla(\text{rank}(K) - \text{rank}(Th))|`, where immobile `Th` normalizes lithologic background).

2. **UNR Great Basin Center for Geothermal Energy (GBCGE) INGENIOUS Hidden-System Physics (`DE-EE0009254`; Ayling et al., 2022 `doi:10.15121/1881483`; Siler et al., 2022; Kraal et al., 2022; Faulds & Hinz, 2015):**
   - Roughly **75% of hydrothermal systems in the Great Basin are blind** (no boiling surface hot springs or geysers), controlled by structurally permeable fault terminations, horse-tail splays, fault intersections, accommodation zones, and releasing stepovers under WNW–ESE Basin-and-Range extension coupled with NW-striking Walker Lane dextral shear.
   - **Case archetype inside the GEMS footprint — Northern Granite Springs Valley (Siler et al., 2022):** Gravity, magnetics, 2 m shallow temperature surveys, LiDAR, and thermal-gradient drilling revealed a blind `95.5°C` (`150–250 m` depth) hydrothermal system controlled NOT by the high-relief mountain-interior cliffs, but by:
     1. **Subtle piedmont-toe / alluvial-fan fault splays** along the range-front break-in-slope, AND
     2. **A buried ~6 km × 4 km intra-basin shallow-basement horst** (`100–230 m` depth to Mesozoic basement, down-dropped to `1.0–2.5 km` in flanking sub-basins) bounded by N- to NNE-striking right-stepping normal faults beneath flat basin fill!
   - **Chemical geothermometer disequilibrium (`Kraal et al., 2022` & GDR #1391 `gdr_wellspring_in_footprint.csv`):** Cold shallow phreatic aquifers (`median T_meas = 32.0°C` across `8,718` measured wells/springs in the GEMS footprint) dilute and laterally advect rising thermal waters, masking surface temperatures (`+2.5–3°C` subtle 2 m anomalies). However, dissolved silica (`geothermquartz_c`, `973` wells, `median = 96.7°C`, `p90 = 163.2°C`) and Na-K-Ca (`geothermcat_c`, `1,185` wells, `median = 75.9°C`, `p90 = 155.0°C`) preserve chemical memory of deeper `100–220°C` fault-hosted reservoir equilibration! High **thermal disequilibrium** $\Delta T_{\text{diseq}} = \max(0,\, T_{\text{eq}} - T_{\text{meas}})$ and sharp **inter-well equilibration-temperature gradients** $\|\nabla T_{\text{eq}}\|$ pinpoint concealed hydrothermal fault conduits and cross-fault permeability barriers without touching any fault-catalogue label.

3. **Why Raw Slope & Single-Pixel Trees Fail on 1 m LiDAR Scarps (`Hermant et al., 2025`; Cross-Fleet Diagnostic `GEMSDOE76`):**
   - Across the GeoDAWN footprint, pixelwise gradient boosted trees assign ~`70%` of their off-catalogue dot budget to steep mountain-interior erosional cliffs (`det_elev_slope > p75`), whereas **only `31.75%` of real mapped faults** occupy steep interior slopes — the remaining **`68.25%` sit along piedmont toes, alluvial-fan mouths, stepovers, and low-slope basin margins**!
   - Physically, an erosional canyon wall has high regional slope (`bg_slope_1500m` large) on BOTH sides of the channel, whereas a **Quaternary range-front or piedmont normal fault scarp** occurs specifically at the **upward-concave flexural break-in-slope** ($\nabla^2 z_{\sigma} > 0$) where steep footwall relief transitions abruptly into low-slope hanging-wall alluvium, OR manifests as a **linear 1 m LiDAR scarp (`step_max`, `lappos_max`, `ex_max`) that stands sharply above a low-slope alluvial background** (`scarp / (bg_slope_1500m + c)`).
   - Furthermore, real faults are **anisotropic 0.5–5 km curvilinear strands**, not isolated spots or circular blobs: applying **multi-scale 2D Hessian / Frangi ridge vesselness and 8-azimuth line-integral persistence** across a cross-fitted Stage-1 fault-probability field gives a CPU pipeline an effective **2.4 km structural receptive field** analogous to `FaultSEG`/U-Net without overfitting training-catalogue collars.

---

## 2. PhD Forensic Analysis: Why `GEMSDOE32` (`0.2778`) Won, What Live Slot 1 (`0.2449`) Proved, and What Separates `0.2778` from `0.3195+`

### 2.1 Exact Byte-Level Mechanism of `GEMSDOE32` `h33-h33-2-b2` (`0.2778` [`OWNER-REPORTED`])
Byte-identical verification (`SHA-256 = c55bafc4dfbc2a1e2dc6a8687f24fa01fd8a1c69c5b20d567289cfda6fa63827`, `37,654` binary `1.0` pixels) proves:
$$\mathbf{1}_{\text{GEMSDOE32}}(p) \equiv \mathbf{1}_{\text{GEMSDOE25\_D2.8}}(p) \wedge \big(\text{EDT}(\neg\text{existing\_faults})(p) > 2.0\text{ px}\big).$$
Under the organizer's Distance-Tolerant Tversky Index ($\alpha = 0.2, \beta = 0.8, R = 300\text{ m}$ triangular kernel, scored strictly on `footprint & ~existing_faults`):
1. Every nested thinning of `H19-5` (`GEMSDOE20` `0.2287` at `103,726` px; `GEMSDOE24` `0.2477` at `60,069` px; `GEMSDOE25` `0.2586` at `45,519` px; `GEMSDOE26` `0.2610` at `40,860` px [all `ORGANIZER-CONFIRMED` in `evidence/scored_corpus.json`]) achieves **identical weighted true-positive coverage** $\text{TP}_w \approx 5,474\text{ px}$ (`R² = 0.999993`) because `300 m` triangular kernels already saturate along linear ridges once inter-dot spacing is `<= 280 m`.
2. Within `d_cat <= 2.0 px` (`200 m`) of `existing_faults`, `GEMSDOE25` still spent **`7,865` dots** (`45,519 - 37,654 = 7,865`) on full-fit training-catalogue memorization halos (`H19-5` was fit on 100% of pixels without spatial OOF!). Because newly mapped organizer faults are distinct unmapped structures rather than parallel duplicates `< 200 m` from existing lines, deleting those `7,865` collar dots sacrificed `~0` $\text{TP}_w$ while removing `0.2 × 7,865 = 1,573` denominator FP penalty — pushing DTI from `0.2586` straight to **`0.2778` (`+0.0192`)** [`OWNER-REPORTED`].

### 2.2 Exact Live A/B Inversion of `GEMSDOE27` Slot 1 (`5512495c6bd1` = `0.2449` [`OWNER-REPORTED`])
In the 2026-10-25 prompt, the owner reported `27GEMSDOE = 0.2449` alongside `24GEMSDOE = 0.2477`. Byte comparison (`evidence/slot1_live_ab_inversion.json`) confirms `5512495c6bd1` (`61,328` dots) is an **exact superset** of `GEMSDOE24`'s `989f59505db1` (`60,069` dots), adding **only the `1,259` `T-v2` straight-line catalogue-tip gap-closure dots** (`min distance to base = 3.0 px = 300 m`).
- Under pure **zero-hit FP dilution** ($\Delta\text{TP}_w = 0, \Delta N = +1,259$), the exact DTI denominator formula predicts:
  $$\text{DTI}_{\text{zero-hit}} = \frac{5,474.46}{5,474.46 \times 0.2(1 - 0.72) + 0.2(61,328) + 0.8(12,226)} = \mathbf{0.24491}.$$
- Observed owner-reported score: **`0.2449`** (empirical marginal efficiency **$-0.00018\text{ credit/dot}$**, i.e., $0 \pm 2\text{ px}$ across `1,259` dots vs `0.05024` break-even!).
- **Definitive empirical verdict:** Straight-line geometric bridging across 0.3–4 km tips of known USGS/INGENIOUS faults (`T-v2`, `GEMSDOE82` `0.1555`, `GEMSDOE91` `0.0041`) produces **zero live true positives** because obvious collinear aerial-photo scarp continuations were already compiled by human mappers.

### 2.3 Cross-Fleet Live Validation of Independent OOF + Submodular Allocation & Why `0.3195`–`0.4413` Requires Both Better Physics AND Weighted Submodular Cover
- **Independent non-`H19-5` validation (`OWNER-REPORTED`):** `GEMSDOE70` (**`0.2478`**) and `GEMSDOE76` (**`0.2343`**) independently matched `GEMSDOE24` (`0.2477`) using spatially cross-fitted OOF detectors + `300 m` submodular kernel placement (`~37,654` dots outside `B2`), with only `~40–48%` 3-px overlap against `GEMSDOE32` (well below the `70%` parallel uniqueness ceiling!).
- **Why `0.2778` is the `H19-5` ceiling (`knowledge/12_why_02778_won.md`) and how to surpass `0.2778` / `0.3195`:**
  - `H19-5` thinning alone hits an analytic ceiling near `~0.281` (`B3 = 300 m` collar) because `H19-5` used pixelwise full-fit GBDTs on raw elevation/slope + un-destriped potential fields without geothermal disequilibrium or multi-scale spatial ridge context.
  - Note on `49GEMSDOE` (`0.4413` vs `0.3195` [`OWNER-REPORTED`], logged as `IR-2026-10-25-02`): no submission artifact exists in `GEMSDOE49`'s git tree (`HEAD` builds a negative research raster `HOLDOUT-DTI = 0.0887`). Mathematically, achieving `> 0.3195` at `B = 37,654` requires raising $\text{TP}_w$ from `~5,474 px` (`~45%` recall of `|G| ≈ 12,226`) to `~6,700+ px` (`~55%+` recall) by reallocating the ~`70%` of dots currently wasted on steep erosional mountain walls onto **piedmont-toe scarps, buried intra-basin horst edges, and hydrothermal fault conduits**, placed via **probability-weighted 300 m CELF submodular cover**.
- **Root cause & permanent fix for `"Predicted values must be in range [0, 1]"`:**
  1. `training_features.tif` stores `-3.4028235e+38` sentinels in `3,061` in-footprint pixels (confirmed in Cell 5 of Prof. John Lipor's official reference notebook `unet-mc-cv-reference-solution.ipynb`: `X_orig[X_orig < -1e38] = np.nan`).
  2. Cell 19 of `unet-mc-cv-reference-solution.ipynb` initializes `y_out = np.zeros(...)` and writes `predicted_faults_example.tif` with **`nodata=None` and finite `[0.0, 1.0]` values across every pixel of the `3730 × 3292` raster** (zeros outside footprint, NO `NaN` anywhere!). Emitting all-finite `{0.0, 1.0}` `float32` GeoTIFFs (`outside="zero"`, `nodata=None`) matches the official reference notebook byte-convention and guarantees `(arr >= 0).all() and (arr <= 1).all()` under every NumPy/GDAL validator.

---

## 3. Single-Paragraph Method-Lane Declaration (`PARALLEL-RUN PROTOCOL §1`)

> **Declared Lane (`L-S7-2026-10-25`):** Label-free **Hydrothermal Upflow Disequilibrium × Piedmont-Toe Concave Flexure × Flight-Line-Destriped Shallow Geophysical Edge Detector + Cross-Fitted Multi-Scale Hessian/Line-Integral Fault-Ridge Vesselness + Probability-Weighted 300 m CELF Submodular Cover (`H29-HPVC`)** at matched `B2` (`d_vis > 200 m`) off-catalogue budget (`37,654` binary `{0.0, 1.0}` pixels, all-finite `EPSG:32611` `3730×3292` `float32`). This lane never loads `h19_5_nan.tif` or any sibling submission raster, never uses fault-tip continuation (`T-v2`) or `SGMC`, never reads `dist_known_fault_px`, fixes the shared holdout `emit()` ring-leak bug (`IR-2026-10-25-06`) and unweighted `coverage_thin` bug (`H27-6`), checks pre-placement surface Spearman (`<= 0.90`) AND post-placement 3-px dot overlap (`<= 70%`) against all 12 peer rasters in `registry/parallel_submission_registry.json`, and stays strictly inside this single lane across `<= 3` experiments (`E1`, `E2`, `E3`).

---

## 4. Five Untried Candidate Geological Hypotheses (`H29-1` to `H29-5`), Ranked by Expected DTI Gain vs Cost

None of `H29-1..5` has been implemented or tested anywhere in `GEMSDOE27` (`knowledge/02`, `knowledge/07`, `knowledge/13`, `registry/hypotheses.json`).

| Rank | ID | Hypothesis & Layers Used | Physical Signature & Named Non-Fault Mimics | Why Missing from USGS/INGENIOUS & How It Differs from Repo | Expected Holdout ΔDTI | Cost & Official Source |
|---:|---|---|---|---|---|---|
| **1 (Selected)** | **`H29-1`** | **Hydrothermal Disequilibrium × Piedmont-Toe Flexure × Destriped Shallow Geophysical Vesselness + Weighted 300 m CELF Cover (`H29-HPVC`)**<br>Layers: `gdr_wellspring_in_footprint.csv` (`temp_c`, `geothermquartz_c`, `geothermchalc_c`, `geothermcat_c` ONLY), `geodawn_extensions_u8.tif` (`TMI_up150`, `ThK`, `UK`), `geodawn_rad_u8.tif` (`K`, `Th`), `training_features.tif`, `lidar_scarp_features_u8.tif`. | **(a)** Piedmont-toe upward concave break-in-slope ($\nabla^2 z_\sigma > 0$) + background-slope-deconfounded 1 m LiDAR scarps (`scarp / (bg_slope_1500m + p25)`); **(b)** 90° E–W flight-line-destriped shallow magnetic demagnetization (`rank(TMI) - rank(TMI_up150)`) + `K/Th` alteration fronts + low-slope intra-basin `depth_to_base_surf` horst steps; **(c)** GDR chemical geothermometer disequilibrium $\Delta T_{\text{diseq}} = \max(0, T_{\text{eq}} - T_{\text{meas}})$ & $\|\nabla T_{\text{eq}}\|$; **(d)** Stage-2 cross-fitted multi-scale Frangi/Hessian vesselness (`150–700 m`) + 8-azimuth `1.2 km` line-integral persistence + weighted `300 m` CELF submodular cover.<br>*Mimics:* Lake Lahontan wave-cut shorelines; stratiform felsic ash-flow tuff contacts; lateral alluvial-fan outflow plumes. | Published compilations over-represent bare-rock scarps and miss subtle `<2 m` piedmont scarps, buried intra-basin horst faults (`Siler et al. 2022`), and cold-masked hydrothermal conduits (`Kraal et al. 2022`). Differs from all prior `GEMSDOE27` runs: zero `H19-5`, zero `T-v2`, adds E–W GeoDAWN destriping, `TMI - TMI_up150`, $\Delta T_{\text{diseq}}$, slope-deconfounded scarps, 2-stage nested spatial cross-fitting with Frangi vesselness, and probability-weighted CELF cover. | **`+0.008` to `+0.025`** over Control `B0` (`+0.004` to `+0.020` over `D0`) | **Medium** (~15 min CPU; 100% locally verified hash-pinned inputs: USGS `doi:10.5066/P93LGLVQ`, GDR `doi:10.15121/1881483`). |
| **2** | **`H29-2`** | **Andersonian 60°-Dip Hanging-Wall Geophysical-to-Scarp Doublet Pairing**<br>Layers: Destriped `rtp` & `iso_grav_anom` horizontal-gradient crests, `depth_to_base_surf`, `lidar_step_max`, `lidar_cos2strike`, `lidar_sin2strike`. | Directed cross-correlation between a surface scarp at $(y,x)$ and a parallel basement/magnetic gradient crest shifted `200–700 m` perpendicular to strike into the down-dropped hanging wall ($60^\circ$ normal-fault dip geometry).<br>*Mimics:* Tilted volcanic hogbacks dipping into valleys. | Eroded range-front segments lose continuous surface scarp expression while the down-dip basement step persists `300–600 m` basinward. All prior repo features (`H28-1`, `H28-3`) test only `0 m` co-located overlap. | `+0.002` to `+0.008` | **Medium** (hash-pinned local rasters; deferred behind `H29-1`). |
| **3** | **`H29-3`** | **Pleistocene Lake Lahontan Shoreline Contour-Parallelism Deconfounder**<br>Layers: `det_elev`, `lidar_step_max`, `lidar_lappos_max`, `lidar_cos2strike`, `lidar_sin2strike` (+ raw USGS 3DEP DEM absolute elevation `1,200–1,340 m` for full version). | Measures $\sin^2(\theta_{\text{scarp}} - \theta_{\text{contour}})$ to suppress horizontal wave-cut paleo-shoreline benches (`~1,330–1,338 m` Sehoo highstand) whose strike wraps strictly parallel to elevation contours with zero cross-basin throw.<br>*Mimics:* Low-angle detachment toes parallel to basin contours. | Eliminates non-tectonic wave-cut shoreline FPs across Winnemucca/Fallon/Carson Sink sub-basins, freeing budget for oblique tectonic piedmont faults. Never tested in `GEMSDOE27`. | `+0.002` to `+0.007` | **Medium** (partial local via `det_elev`; exact `1,335 m` mask requires USGS 3DEP `prd-tnm` S3 tiles in `dem_links.json`, public domain). |
| **4** | **`H29-4`** | **GDR #1391 Paleo-Geothermal Sinter/Tufa/Travertine & 2 m Probe Conduit Corridors** (Carry-forward `H27-16` refined with `Kraal et al. 2022` elevation/albedo residual)<br>Layers: Official GDR #1391 `paleo_geothermal` (`faffcf69…`), `2m_temp` (`1301f70d…`), `Quaternary_volcanics` (`c4a2d2df…`). | Linear alignments of siliceous sinter, carbonate tufa, and silicified sand/conglomerate (`Siler et al. 2022` Granite Springs 6 km horst trend) paired with local `> +2.5°C` 2 m temperature residuals.<br>*Mimics:* Lacustrine tufa mounds along Lake Lahontan shorelines (`Kraal et al. 2022`). | Fossil sinter/tufa aprons cement fault traces and mask young coseismic scarps while directly marking Quaternary hydrothermal upflow conduits. Never ingested into a detector in `GEMSDOE27`. | `+0.001` to `+0.008` | **Medium-High / Data-Gated** (official free DOE GDR `https://gdr.openei.org/submissions/1391`, CC-BY-4.0; blocked on raw-byte fetch outside sandbox allowlist). |
| **5** | **`H29-5`** | **Transverse Range-Front Canyon-Mouth Knickpoint & Fan-Apex Collinearity**<br>Layers: `det_elev`, `det_local_relief`, `det_gradient`, `lidar_relief`, `lidar_cross_max`. | Collinear alignments of steepened transverse stream-channel outlets ($k_{sn}$ spikes / fan apexes) spaced `0.5–2 km` along active footwall range fronts where Holocene fan aggradation buries inter-canyon scarps.<br>*Mimics:* Resistant bedrock hogbacks crossed by transverse streams. | Catches active range-front faults across rapidly aggrading debris-flow bajadas where surface scarps were erased between canyons. Never tested in `GEMSDOE27`. | `+0.001` to `+0.005` | **Medium** (existing DEM bands locally; higher precision with external USGS 3DEP 10 m DEM). |

---

## 5. Shared-Tool Bug Fix Disclosed Before Execution (`PARALLEL-RUN PROTOCOL §2`)

Line-by-line inspection of `scripts/run_lane_holdout.py` uncovered a subtle candidate-mask bug (`IR-2026-10-25-06`):
- `holdout.buffered_scoring_mask(sp, foot)` returns `foot & sp.fold_mask & ~ring`, where `ring = (EDT(~sp.hidden) <= 6.0) & ~sp.hidden`.
- Passing `valid_scoring | sp.hidden` into `emit(...)` set candidate eligibility to `True` at `d_hidden == 0` (`on hidden`) and `d_hidden > 6`, while setting `False` on `0 < d_hidden <= 6` — leaking the complement of the 6-px ring around `hidden` into dot placement (inflating even random arm `R` to `0.0680`).
- **Fix applied across ALL arms (`U0`, `B0`, `D0`, `H28_1_B2`, `H29-A`, `H29-S`):** `emit(...)` receives **ONLY** `fold_domain = foot & sp.fold_mask` and `sp.known` (zero access to `sp.hidden` or `valid_scoring`!). Only after `emit(...)` blindly returns binary predictions `dots` does the evaluator score `dots` on `valid = buffered_scoring_mask(sp, foot) | sp.hidden` (primary Protocol §2 metric) AND on unbuffered `foot & sp.fold_mask` (secondary diagnostic metric).

---

## 6. Frozen Preregistration of `H29-1` (`Lane L-S7-2026-10-25`)

### 6.1 Unused Holdout Split & Budget
- **Evaluator:** `gems27.holdout` + `gems27.metric.dti` (`v1`, $\alpha=0.2, \beta=0.8, R=300\text{ m}$ triangular kernel, `buffer_px=6.0` on training folds AND `buffer_px=6.0` on `buffered_scoring_mask`, plus secondary unbuffered full-quadrant diagnostic).
- **Frozen unused seeds:** **`210, 211, 212, 213, 214, 215, 216, 217, 218, 219`** (`10` seeds × `4` quadrants = **`40` fold×seed cells**; zero overlap with consumed seeds `100–169` and `200–204`).
- **Off-catalogue rule & matched dot budget:** `B2` exclusion collar `EDT(~known) > 2.0 px` (`200 m`); total full-map budget **`B_TOTAL = 37,654` dots** (matching `GEMSDOE32`'s exact operating budget), allocated per quadrant proportionally to `int(round(37654 * fold_domain.sum() / foot.sum()))`.

### 6.2 Frozen Feature Specification (Zero Label Columns Touched)
- **Stage-1 `H29` Physics Features (`20` label-free columns concatenated to the 32 base features = `52` columns):**
  1. `h29_piedmont_concave_s3`: upward concave break-in-slope $\max(0, \nabla^2 z_{\sigma=3}) \cdot \text{rank}(\|\nabla z_{\sigma=15}\|)$
  2. `h29_piedmont_concave_s8`: broader piedmont flexure $\max(0, \nabla^2 z_{\sigma=8}) \cdot \text{rank}(\|\nabla z_{\sigma=18}\|)$
  3. `h29_deconf_lappos`: slope-deconfounded LiDAR positive Laplacian `lidar_lappos_max / (bg_slope_15 + p25_slope)`
  4. `h29_deconf_step`: slope-deconfounded LiDAR scarp step `lidar_step_max / (bg_slope_15 + p25_slope)`
  5. `h29_deconf_ex`: slope-deconfounded LiDAR vertical excursion `lidar_ex_max / (bg_slope_15 + p25_slope)`
  6. `h29_piedmont_scarp_coh`: coherent piedmont scarp `(h29_deconf_step + h29_deconf_lappos) * (lidar_coh100 / 255.0)`
  7. `h29_rtp_destripe_hgm`: horizontal gradient magnitude of E–W (`90°`) flight-line-destriped `rtp` ($\sigma = 2.0\text{ px}$)
  8. `h29_rtp_destripe_tilt0`: Verduzco tilt-angle zero-crossing sharpness $\exp(-|\theta_{\text{tilt}}(\text{rtp}_{\text{destripe}})| / 0.35)$
  9. `h29_mag_shallow_res`: shallow-crustal magnetic residual `rank(tmi) - rank(TMI_up150)` (negative = shallow magnetite destruction)
  10. `h29_mag_shallow_grad`: horizontal gradient of shallow magnetic residual $\|\nabla(\text{rank}(tmi) - \text{rank}(TMI_{up150}))\|_{\sigma=2.5}$
  11. `h29_grav_tilt0`: Verduzco tilt-angle zero-crossing sharpness on `iso_grav_anom` $\exp(-|\theta_{\text{tilt}}(g)| / 0.35)$
  12. `h29_basin_horst_step`: intra-basin basement step $\|\nabla(\text{depth\_to\_base\_surf})\|_{\sigma=2.5} / (\text{bg\_slope}_{15} + p_{25})$ (`Siler et al. 2022` mechanism)
  13. `h29_basin_horst_relief`: local shallow-basement horst prominence $(G_{18}(\text{depth\_to\_base}) - \text{depth\_to\_base}) \cdot \text{piedmont\_basin\_weight}$
  14. `h29_k_th_alter_grad`: destriped radiometric potassium-vs-thorium alteration-front gradient $\|\nabla(\text{rank}(K) - \text{rank}(Th))\|_{\sigma=3.0}$
  15. `h29_thk_mag_coupled`: hydrothermal alteration × shallow magnetic edge `zpos(h29_k_th_alter_grad) * zpos(h29_mag_shallow_grad)`
  16. `h29_cond_strain_piedmont`: electrical conductivity gradient × geodetic dilation/shear in low-slope basins `zpos(||∇ log1p(cond)||) * zpos(hypot(dilate, shear)) / (1 + bg_slope_z)`
  17. `h29_gdr_teq_nw_s12`: Nadaraya–Watson ($\sigma=12\text{ px}$) chemical equilibration temperature $T_{\text{eq}} = \max(T_{\text{quartz}}, T_{\text{chalc}}, T_{\text{cat}}, T_{\text{meas}})$ from `gdr_wellspring_in_footprint.csv` (`dist_known_fault_px` strictly unread!)
  18. `h29_gdr_diseq_nw_s12`: Nadaraya–Watson ($\sigma=12\text{ px}$) chemical thermal disequilibrium $\Delta T_{\text{diseq}} = \max(0,\, \max(T_{\text{quartz}}, T_{\text{chalc}}, T_{\text{cat}}) - T_{\text{meas}})$
  19. `h29_gdr_teq_grad`: lateral barrier/conduit gradient $\|\nabla T_{\text{eq,NW}}\|_{\sigma=3.0}$
  20. `h29_gdr_upflow_prox`: multi-scale proximity $\frac{1}{2}\exp(-d_{\text{upflow}}/15) + \frac{1}{2}\exp(-d_{\text{upflow}}/40)$ to hydrothermal upflow wells ($T_{\text{meas}} \ge 35^\circ\text{C}$ or $T_{\text{eq}} \ge 90^\circ\text{C}$ or $\Delta T_{\text{diseq}} \ge 40^\circ\text{C}$).

- **Stage-2 Nested Cross-Fitted Spatial-Ridge / Vesselness Features (`10` columns computed strictly from out-of-fold Stage-1 probabilities via the $\binom{4}{2}=6$ pairwise-quadrant cross-fit with `600 m` buffer masking):**
  1. `s2_p1`: cross-fitted Stage-1 probability $P_1$
  2. `s2_smooth_s15`, `s2_smooth_s40`, `s2_smooth_s90`: multi-scale smoothed probability ($\sigma = 1.5, 4.0, 9.0\text{ px}$)
  3. `s2_ridge_tophat`: local ridge contrast $G_{1.0}(P_1) - G_{6.0}(P_1)$
  4. `s2_frangi_s15`, `s2_frangi_s35`, `s2_frangi_s70`: 2D Hessian / Frangi ridge vesselness at $\sigma \in \{1.5, 3.5, 7.0\}\text{ px}$ ($\beta_F = 0.5$)
  5. `s2_line8_max`, `s2_line8_aniso`: 8-azimuth `1.3 km` (`13 px`) oriented line-integral maximum $L_{\max}$ and orthogonal contrast $(L_{\max} - L_{\perp}) / (L_{\max} + 10^{-5})$.

- **Frozen Allocation Operator (`gems27.coverage_thin.weighted_celf_cover`):**
  - Maximizes $F_w(S) = \sum_{p \in \mathcal{D}} P_2(p)^{\gamma} \max_{y \in S} \max(0, 1 - \|p - y\|_2 / 3.0)$ via exact lazy-heap CELF with frozen $\gamma = 1.5$, minimum inter-dot separation `min_sep = 2.0 px` (`200 m`), and `B2` collar `EDT(~known) > 2.0 px`.

### 6.3 Frozen 3-Experiment Budget & Hard Promotion Gates (`E1`, `E2`, `E3`)
1. **`E1` — Univariate Holdout Leakage Canary + Pre-Placement Stitched-OOF Surface Uniqueness Gate (`scripts/run_h29_holdout.py --stage e1`):**
   - **Hard Gate 1a:** Direction-invariant single-feature ROC-AUC on withheld fault segments across all `20` `H29` features (and all `32` base features) must satisfy `AUC <= 0.90` (`> 0.90` = immediate leakage halt).
   - **Hard Gate 1b:** Pre-placement stitched cross-fitted Stage-2 probability surface must satisfy `|Spearman rho| <= 0.90` against every one of the 12 peer rasters in `registry/parallel_submission_registry.json` and every historical `GEMSDOE27` raster.
2. **`E2` — Paired 40-Cell Spatial Holdout on Frozen Seeds `210–219` (`scripts/run_h29_holdout.py --stage e2`):**
   - Evaluates 6 arms on identical splits & matched `37,654` (`B2`) budget using blind `emit(prob, fold_domain, known, budget)`:
     - `U0`: matched-budget uniform random eligible off-catalogue null;
     - `B0`: `full-32` Stage-1 OOF + `ridge_nms` + `priority_poisson_disk(d=2.8)`;
     - `D0`: `full-32 + 15 subsurface` Stage-1 OOF + `ridge_nms` + `priority_poisson_disk(d=2.8)` (Session 6 candidate);
     - `H28_1_B2`: `full-32 + 6 potential_edges` Stage-1 OOF + `ridge_nms` + `priority_poisson_disk(d=2.8)`;
     - `H29-A` (detector-only ablation): `full-32 + 20 H29 + 10 S2 vesselness` OOF + `ridge_nms` + `priority_poisson_disk(d=2.8)`;
     - **`H29-S` (primary preregistered candidate)**: `full-32 + 20 H29 + 10 S2 vesselness` OOF + `weighted_celf_cover(gamma=1.5, min_sep=2.0)`.
   - **Hard Gate 2 (Promotion Rule):** `H29-S` promotes to weekly-slot recommendation **if and only if**:
     1. Pooled buffered `HOLDOUT-DTI(H29-S)` strictly exceeds `max(B0, D0, H28_1_B2, U0)`;
     2. Mean paired seed $\Delta\text{DTI}(\text{H29-S} - \text{best\_baseline}) \ge +0.0020$ with 10,000-draw seed-bootstrap 95% CI lower bound strictly `> 0.0`;
     3. `H29-S` wins at least `3/4` spatial quadrants (including a positive check on `NE_LidarGapHeavy` reported explicitly) and at least `8/10` seeds against every baseline (`B0`, `D0`, `H28_1_B2`);
     4. Detector-only ablation `H29-A` strictly exceeds `B0` (`pooled Δ > 0`), proving the geological feature + vesselness representation contributes real detection lift prior to submodular placement.
3. **`E3` — Stitched-OOF Submission Build, 12-Peer Post-Placement Uniqueness Gate, Standalone Format Verification & JSON Run Card (`scripts/build_h29_submission.py`):**
   - Emits unique all-finite `[0, 1]` GeoTIFF (`outside="zero"`, `nodata=None`) + single-GeoTIFF `.zip` from dual-partition stitched cross-fitted Stage-2 OOF probabilities (averaging Quadrant 4-fold buffered OOF + Checkerboard/Shifted 4-fold buffered OOF so zero pixel is predicted in-sample!).
   - **Hard Gate 3:** `<= 70%` 3-px dot overlap and `<= 0.90` Spearman against all 12 peer rasters + all historical `GEMSDOE27` rasters; 100% pass on `gems27.submission.verify_geotiff` and `scripts/verify_downloads.py`; JSON Run Card (`evidence/h29_run_card_2026-10-25.json`) with note `<= 140` characters and automatic site gate banner (`READY TO SUBMIT` iff Gates 1–3 all pass, else `DO NOT SUBMIT — RESEARCH / NEGATIVE RESULT`).
