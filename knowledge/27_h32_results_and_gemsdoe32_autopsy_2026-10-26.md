# Session 11 Results (`2026-10-26`) — 9-Focus-Site Executive Summary, PhD Autopsy of `GEMSDOE32` (`0.2778`), and `H32-1` (`PDHC-K`) Holdout & GeoTIFF Report

**Lane ID:** `L-S11-2026-10-26` · **Frozen Preregistration:** `knowledge/26_preregistration_H32_2026-10-26.md` (commit `92d63a3`)
**Fresh Untouched Seeds:** `500–509` (10 seeds × 4 quadrants = 40 cells; `111,013` withheld positive fault pixels)
**Run Card:** `evidence/h32_s11_run_card_2026-10-26.json`

---

## 1. Executive Summary — Machine-Validated Submission Verdicts (`GEMSDOE27`)

| Candidate Role | File | Machine Gate Verdict (`gems27.readiness.publication_decision`) | Key Metrics (`HOLDOUT-DTI` / Uniqueness / Range) |
|---|---|---|---|
| **SOLE PRIMARY APPROVED SUBMISSION (Session 10 `H31-1` `DRCG-WL`)** | `docs/downloads/gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif` (`.zip` paired) | **OK TO DOWNLOAD AND SUBMIT** (`verdict: "promote"`, `ok_to_submit: true`) | Seeds `400–409`: **`0.047302`** (`+0.003185` vs `H29-S`, `8/10` seeds; **5/5 frozen clauses PASS**). Replication on seeds `500–509`: `0.042714` buffered / `0.109572` unbuffered / `0.165491` whole-quadrant OOF. `37,654` px, all-finite `[0, 1]`, max peer overlap `57.70% <= 70%`. |
| **NEWLY GENERATED SESSION-11 UNIQUE CANDIDATE (`H32-1` `PDHC-K`)** | `docs/downloads/research/gems27-h32-pdhc-kernel-celf28-20261026-324a95651136-allfinite.tif` (`.zip` paired) | **DO NOT SUBMIT — RESEARCH DELIVERABLE ONLY** (`verdict: "negative"`, `ok_to_submit: false`) | Seeds `500–509`: **`0.044990` buffered (#1 of 8 arms)**, **`0.113813` unbuffered (#1)**, **`0.169096` whole-quadrant OOF (#1 across all 9 focus sites)**. Beat `H31-S` (`+0.002276`, `9/10` seeds, `CI [+0.000776, +0.003667]`), `D0` (`+0.005631`, `10/10`), and `B0` (`+0.008537`, `10/10`), yet **passed `5/6` frozen clauses** (Clause 4 vs `H29-S`: `+0.001188`, `6/10` seeds, `CI [-0.000819, +0.003063]` crossed zero). All-finite `[0, 1]`, max peer overlap `57.83% <= 70%` (`79.56%` vs unscored `H31-1`). |
| **QUARANTINED / RETRACTED (`H30-1`)** | `docs/downloads/research/gems27-h30-1-updip-hydrothermal-3hab-20261026-801dff07541d-allfinite.tif` | **DO NOT SUBMIT — RETRACTED (`IR-2026-10-26-13`)** (`verdict: "negative"`, `ok_to_submit: false`) | PR #29 leaked `sp.hidden` via `visible_known = sp.known & (d_hid > 6.0)`. Under fixed leak-free evaluator: `HOLDOUT-DTI = 0.02581` (`-0.01105` vs `Arm-D`). |
| **ALREADY SCORED LIVE (`Slot 1` & `H29-S`)** | `5512495c6bd1` (`0.2449`) & `511898747886` (`0.2190`) | **ALREADY SUBMITTED — DO NOT RE-SUBMIT** | Deterministic leaderboard scorer; re-uploading wastes a weekly submission slot. |

---

## 2. Executive Summary Table Across All 9 Focus Sites (`2026-10-26` Byte-Verified Audit)

Every historical live score is strictly `OWNER-REPORTED` (zero `drivendata.org` access; zero organizer receipts in repo). Every active `2026-10-26` `main`-branch GeoTIFF was extracted from its pinned `codeload.github.com` repository tarball into `data_cache/parallel_20261026/` and byte-measured (`evidence/focus_sites_executive_summary_20261026.json`). Model-estimated bounds report **both** the `geometric` and `hybrid` assumptions side-by-side (`AGENTS.md` rule; anchored to `GEMSDOE27 H29-S = 0.2190 OWNER-REPORTED`, `G_ref = 12,226`, `rho = 1.38`).

| Focus Site | Historical Best Submission & `OWNER-REPORTED` Live Score | Active `2026-10-26` `main` Downloadable `.tif` (`sha12`) | `HOLDOUT-DTI` (with Evaluator Scope) | `MODEL-ESTIMATE` Bounds (`Geometric` / `Hybrid`) | Uniqueness & Machine Verdict (`2026-10-26`) |
|---|---|---|---|---|---|
| **`GEMSDOE32`** | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` — **`0.2778`** (#1 of 9 focus sites; `37,654` px) | `gemsdoe32-h46-dipasym-celf-b2-37654-...-9f42346d-zeros.tif` (`9f42346d3ace`) & `r6-stepprofile` (`c7f094c1f4d0`) | `0.02581` (G32 seg-hide) / `0.1612` (SGMC-hide); `R6 = 0.02216` | `0.2242` / `0.2196` (`allfinite_zeros`) | `0.2778` ALREADY SUBMITTED; `2026-10-26` `H46` & `R6` are **DO NOT SUBMIT** on `GEMSDOE32` `main`. |
| **`GEMSDOE36`** | `anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif` — **`0.2750`** (#2; `38,854` px = `G32` + `1,200`) | `gemsdoe36-hvg36-hybrid-voxgrav-dipterr-37654-...-85d56b03-zeros.tif` (`85d56b03aff1`) | `0.13576` (whole-fold OOF `n=60,988`) | `0.2565` / `0.2402` (`allfinite_zeros`) | `0.2750` ALREADY SUBMITTED (`96.9%` overlap w/ `G32`); `HVG36` (`42.8%` vs `G32`) is **DO NOT SUBMIT** (`verdict=negative`). |
| **`GEMSDOE28`** | `h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif` — **`0.2710`** (#3; `H27-4-R1` = `0.2708`; `S18-MXTP` = `0.0217`) | `gems28-s20-nchc-dti-20261026-1d629d6c953c-allfinite.tif` (`1d629d6c953c`, `40,071` px) | `0.0252` (G28 seg-hide) | `0.2621` / `0.2381` (`allfinite_zeros`) | `0.2710` ALREADY SUBMITTED (`99.6%` overlap w/ `G32`, `-nan`); `S20-NCHC` (`35.2%` vs `G32`) is **DO NOT SUBMIT**. |
| **`GEMSDOE31`** | `h27-4-solo-d28-20261004-2fb3da5a-nan.tif` — **`0.2708`** (#4; `40,199` px, dot-identical to `G28` solo) | `gemsdoe31-h31t-transtension-dinkelbach-20261025-b37654-zeros.tif` (`83fbc267a754`, `37,654` px) | `0.1300` `[0.1147, 0.1456]` (`gems57-pooled-hide-v2` whole-fold OOF `n=60,988`) | `0.2797` / `0.2566` (`allfinite_zeros`) | Historical `0.2708` ALREADY SUBMITTED; `2026-10-26` `H31-T` is **OK TO SUBMIT on `GEMSDOE31`** (`34.1%` vs `G32`, `43.2%` vs `G27 H31-1`; lower whole-fold OOF `0.1300` vs `G27 H31-1 = 0.1655`). |
| **`GEMSDOE33`** | `h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif` — **`0.2632`** (#5; `41,865` px) | `gemsdoe33-llc33-l1-20261026T174746Z-76f9e157d01b-zeros.tif` (`76f9e157d01b`, `37,654` px) | `0.0235` (G33 seg-hide) | `0.2615` / `0.2415` (`allfinite_zeros`) | `0.2632` ALREADY SUBMITTED (`95.3%` overlap w/ `G32`); `LLC33` (`33.3%` vs `G32`) is **DO NOT SUBMIT**. |
| **`GEMSDOE25`** | `dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif` — **`0.2600`** (tied #6; `44,090` px; `H66-MGD` = `0.0742`) | `gems25-h69-objbin-53522-20261026-160dbdc0c2ab-zeros.tif` (`160dbdc0c2ab`, `53,522` px) | `0.0419` (G25 holdout; over-budget `53,522` px) | `0.2744` / `0.2604` (`allfinite_zeros`) | `0.2600` ALREADY SUBMITTED (`85.4%` overlap w/ `G32`); `H69-OBJBIN` (`42.3%` vs `G32`) is **DO NOT SUBMIT**. |
| **`GEMSDOE30`** | `d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif` — **`0.2600`** (tied #6; `MSDB1` = `0.1462`) | `gems30-GEOCOR1-b3-p39324-20261026-0ed267020015.tif` (`0ed267020015`, `39,324` px) | `0.0194` (G30 holdout) | **`INVALID` / `INVALID`** (`7,111,787` `NaN`s outside footprint!) | `0.2600` ALREADY SUBMITTED (dot-identical to `G25`); `GEOCOR1` **FAILS `[0, 1]` PORTAL RANGE CHECK (`IR-2026-10-26-15`) — DO NOT SUBMIT**. |
| **`GEMSDOE24`** | `h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif` — **`0.2477`** (#8; `60,069` px; `GVC1` = `0.0859`) | `gems24-dprf1-dualpart-rotated-frangi-celf-20261026-c1257c1d4b5a-zeros.tif` (`c1257c1d4b5a`, `37,654` px) | `0.16379` (whole-fold OOF `n=60,988`) | `0.2726` / `0.2802` (`allfinite_zeros`) | `0.2477` ALREADY SUBMITTED; `DPRF1` (`37.8%` vs `G32`) failed G24 seed-paired gate — **DO NOT SUBMIT**. |
| **`GEMSDOE27`** (*this repo*) | `Slot 1` (`5512495c6bd1`) = **`0.2449`**; `H29-S` (`511898747886`) = **`0.2190`** (#1 of `2026-10-25` non-`H19-5` cohort) | Primary: `gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif` (`37,654` px) · Session-11 Research: `research/gems27-h32-pdhc-kernel-celf28-20261026-324a95651136-allfinite.tif` (`37,654` px) | `H31-1`: **`0.047302`** (`400–409`), `0.042714` (`500–509`), **`0.16549`** (whole-fold OOF) · `H32-1`: **`0.044990`** (`500–509`, #1), **`0.16910`** (whole-fold OOF, #1 across all 9 sites) | `H31-1`: **`0.2654` / `0.2757`** · `H32-1`: **`0.2631` / `0.2667`** (`allfinite_zeros`) | **`H31-1` (`cf8e1bbef244`) = SOLE `OK TO SUBMIT`** (`57.70%` max peer overlap) · **`H32-1` (`324a95651136`) = `DO NOT SUBMIT`** (`5/6` frozen clauses; `57.83%` max peer overlap; `79.56%` vs `H31-1`). |

> **Flagged Leaderboard Score Provenance (`0.4413` vs `0.3195` vs `0.2376`):** `buffedlizard55-lab/GEMSDOE49` reports `0.2376` (`OWNER-REPORTED`) in its own repository. `0.3195` (`16GEMSDOE`) is the highest `OWNER-REPORTED` score inside the `buffedlizard55-lab` fleet, while `0.4413` is an `OWNER-REPORTED` external leaderboard #1 score (unnamed competitor). None carries an organizer receipt in this repository.

---

## 3. PhD-Level Byte-Verified Autopsy: Why `GEMSDOE32` (`0.2778`) Won Among Focus Sites & How to Surpass It (`0.3195` / `0.4413`)

### 3.1 Exact Mathematical Inversion of the `0.2477 → 0.2600 → 0.2708 → 0.2778` Ladder
Under the official Distance-Tolerant Intersection metric ($\alpha = 0.2$, $\beta = 0.8$, $k(d) = \max(0, 1 - d/300\text{ m})$):
$$\mathrm{DTI}(P, G) = \frac{\mathrm{TP}_w}{\mathrm{TP}_w + 0.2\,\mathrm{FP}_w + 0.8\,\mathrm{FN}_w}, \qquad m(\mathrm{DTI}) = \frac{\alpha\,\mathrm{DTI}}{1 - \alpha\,\mathrm{DTI}}.$$
At $\mathrm{DTI} = 0.2778$, the marginal break-even threshold is $m(0.2778) = \mathbf{0.05883}$ weighted true-positive pixel equivalents per false-positive dot. Byte-level comparison across the hash-verified focus-site ladder (`evidence/focus_sites_executive_summary_20261026.json`) proves that **`GEMSDOE32` (`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif`) won via four coupled mechanisms**:

1. **Multi-Line Physical Corroboration (`H19-5` Backbone = `6.50x` Blind Truth Concentration):** Requires primary morphological/structural ridge response backed by $\ge 0.18$ secondary independent physical evidence, achieving `4,705.5` implied $\mathrm{TP}_w$ (`38.49%` of hidden $|G|_{\text{ref}} = 12,226$) across only `5.922%` blind footprint coverage ($6.50\times$ uniform enrichment). By contrast, single-physics lanes in the `2026-10-25` cohort collapsed to near-blind enrichment (`GEMSDOE24 GVC1` geochemistry = `0.0859`, `GEMSDOE25 H66-MGD` magnetics = `0.0742`, `GEMSDOE28 S18-MXTP` tip-extrapolation = `0.0217`).
2. **Exact $d = 2.8\text{ px}$ (`280 m`) Poisson-Disk Axial Spacing (`0.00%` $\ge 3$-Neighbor Crowding):** For the triangular kernel $k(d) = \max(0, 1 - d/3)$, spacing two dots at $d = 2.8\text{ px}$ along a 1D fault ridge preserves minimum saddle height $\max(1 - 1.4/3) = 0.533$ at the midpoint while eliminating redundant 2D disk overlap (`frac_ge_3nbr_in_3px = 0.0000` in `GEMSDOE32` vs `0.0851` in `GEMSDOE27 H29-S` `min_sep=2.0`, which wasted `-11.0%` coverage at identical `37,654` dot count).
3. **Metric-Exact `B2` ($d_{\text{cat}} > 2.0\text{ px} = 200\text{ m}$) Catalogue-Collar Subtraction (`+0.0178` Free DTI Gain):**
   - `GEMSDOE25/30` (`d=2.8` unpruned, `44,090` px, `c=0.06808`) → **`0.2600`**;
   - `GEMSDOE28/31` (`H27-4` `B1` $d_{\text{cat}} > 100\text{ m}$, `40,199` px, `-3,891` px) → **`0.2708`** (`+0.0108`);
   - `GEMSDOE32` (`H33-2-B2` $d_{\text{cat}} > 200\text{ m}$, `37,654` px, `-2,545` exact `(100, 200]\text{ m}$ annulus px) → **`0.2778`** (`+0.0070`).
   Deleting those `6,436` near-catalogue halo dots subtracted $0.2 \times 6{,}436 = 1{,}287.2$ denominator penalty units while losing virtually zero $\mathrm{TP}_w$ because organizer hidden labels are blind/unmapped faults, not parallel duplicates `100–200 m` off published USGS/NBMG traces (`0.0034` OOF credit/px $\ll 0.0588$ break-even).
4. **Proportional `23.59%` Allocation Inside the `24.63%` 1-m LiDAR Coverage Gap:** Unlike single-tree GBMs that treat `lidar_valid = 0` (`NaN`) as negative evidence (`18.30%` gap share in `H29-S`), `GEMSDOE32` emits `23.59%` of its dots across the LiDAR-missing basins where buried geothermal faults reside.

### 3.2 Why `0.2778` Plateaus & What Separates `0.2778` from `0.3195` and `0.4413`
Inverting the DTI formula at $N \approx 35{,}000\text{–}38{,}000$ (`c ≈ 0.060`):
- Reaching **`0.3195`** (`16GEMSDOE` fleet high) requires lifting $\mathrm{TP}_w / |G|$ from `38.5%` (`6.50x` concentration) to **`~45.5%` (`~7.6x` concentration)**;
- Reaching **`0.4413`** (`OWNER-REPORTED` external leaderboard high) requires lifting $\mathrm{TP}_w / |G|$ to **`~63.5%` (`~10.6x` concentration)** — i.e., recovering **genuinely blind intra-basin and alluvial-covered faults** that have zero surface scarp (`lidar_scarp = 0`) and magnetite-destroyed magnetic lows (`min(grad_rtp, grad_grav) = 0`), where `H19-5` is structurally blind.

Achieving `7.6x–10.6x` concentration requires three concrete advances beyond `GEMSDOE32`:
1. **Sign-Invariant Subsurface Physics for Blind Conduits:** Cordell-Taylor Poisson gravity-vs-pseudogravity demagnetization residuals (`H32-1`), Miller-Singh tilt-angle depth equalization (`H32-2`), and 2D hanging-wall MT clay-cap / basement-step coupling (`H32-3`) + external 3D MT resistivity & GDR #1391 sinter/2 m thermal probes (`H32-4`).
2. **Cover-Aware Multi-Regime Calibration + Kernel-Expected Utility Training:** Blending subsurface-only and full-stack models continuously by Quaternary sediment-cover blindness (`H32-1` recovered SW Mojave by `+0.003462` over `H31-1`) and training directly on expected 300 m triangular kernel mass $\mathbb{E}[k(d(x, G))]$.
3. **Closed-Loop Fractional-DTI (`Dinkelbach`) Budget & Spacing Optimization (`H32-5`):** Instead of hard-fixing $N = 37{,}654$ and uniform `min_sep = 2.8`, solving $u_i - \lambda^* [\alpha + (1 - \alpha\rho - \beta) u_i] > 0$ jointly optimizes total dot count $N^*$ and local axial spacing $d_{\min}(x)$.

---

## 4. Session-11 `H32-1` (`PDHC-K`) Results on Untouched Seeds `500–509`

### 4.1 Experiment `E1` — Single-Feature Leakage Canary & Pre-Placement Uniqueness (`PASS`)
Evidence: `evidence/h32_s11_e1_canary_and_surface.json`
- **All 16 new `H32-1` physics features passed `< 0.90` AUC** (`max_H32_AUC = 0.5954` on `h32_canyon_mouth_collinearity_1200m`; `h32_piedmont_knickpoint_impulse = 0.5888`; `h32_lidar_knick_fan_apex = 0.5813`; `h32_rad_uth_redox_front = 0.5325`; `h32_sediment_cover_blindness = 0.5317`; `h32_poisson_demag_resid_s15 = 0.5264`). Across all 95 features, `max_AUC = 0.5954 <= 0.90` (`0` leak flags).
- **Pre-placement surface Spearman screen (`|rho| <= 0.90`):** `max_|rho| = 0.1125 <= 0.90` across all 24 peer/sibling/scored rasters (`E1 PASS = True`).

### 4.2 Experiment `E2` — 40-Cell Component-Buffered Spatial Holdout (`Seeds 500–509`)
Evidence: `evidence/h32_s11_e2_holdout_500_509.json` (`evaluator_version = "holdout-v1-component-buffered-600m"`, `n_withheld_positives_total = 111,013`)

| Arm | Pooled Buffered `HOLDOUT-DTI` | Pooled Unbuffered `HOLDOUT-DTI` | Whole-Quadrant OOF (`n=60,988`) | `NW` | `NE_LidarGap` | `SW` | `SE` |
|---|---:|---:|---:|---:|---:|---:|---:|
| **`H32-S` (`PDHC-K` + `min_sep=2.8` CELF)** | **`0.044990` (#1)** | **`0.113813` (#1)** | **`0.169096` (#1)** | **`0.041088`** | `0.057842` | **`0.030949`** | `0.053275` |
| `H29-S` (Session-7 live `0.2190`, `min_sep=2.0`) | `0.043802` (#2) | `0.105277` (#4) | `0.155231` (#3) | `0.039977` | **`0.060590`** | `0.030706` | `0.047391` |
| `H32-A` (`PDHC-K` + Poisson `d=2.8` ablation) | `0.043535` (#3) | `0.107291` (#3) | — | `0.037846` | `0.056393` | `0.029577` | **`0.057177`** |
| `H31-S` (Session-10 promoted `DRCG-WL`) | `0.042714` (#4) | `0.109572` (#2) | `0.165491` (#2) | `0.038852` | `0.059269` | `0.027488` | `0.049038` |
| `D0` (`32` base + `15` subsurface + Poisson `d=2.8`) | `0.039359` (#5) | `0.095893` (#5) | `0.139691` (#4) | `0.037664` | `0.049502` | `0.026930` | `0.046368` |
| `B0` (`32` base + Poisson `d=2.8`) | `0.036453` (#6) | `0.089766` (#7) | `0.134490` (#5) | `0.033438` | `0.048877` | `0.027066` | `0.038797` |
| `H28_1_B2` (Session-6 rule baseline) | `0.036358` (#7) | `0.092834` (#6) | — | `0.031979` | `0.052884` | `0.024950` | `0.041575` |
| `U0` (Uninformed Poisson `d=2.8`) | `0.015175` (#8) | `0.045502` (#8) | — | `0.012197` | `0.025818` | `0.008023` | `0.019337` |

**Paired Buffered `HOLDOUT-DTI` Clauses (`5/6` Passed):**
1. `pooled_beats_every_baseline_including_H31S`: **PASS** (`0.044990` #1 of all 8 arms).
2. `ci95_gt_zero_and_9seeds_4folds_vs_B0`: **PASS** (`+0.008537`, `95% CI [+0.007105, +0.010093]`, `10/10` seeds, `4/4` folds).
3. `ci95_gt_zero_and_3folds_vs_D0`: **PASS** (`+0.005631`, `95% CI [+0.004333, +0.006863]`, `10/10` seeds, `4/4` folds).
4. `ci95_gt_zero_and_8seeds_vs_H29S`: **FAIL** (`+0.001188`, `95% CI [-0.000819, +0.003063]`, `6/10` seeds, `3/4` folds — `NW +0.001111`, `SW +0.000243`, `SE +0.005885`, `NE -0.002748`).
5. `ci95_gt_zero_and_7seeds_vs_H31S`: **PASS** (`+0.002276`, `95% CI [+0.000776, +0.003667]`, `9/10` seeds, `3/4` folds; recovered `SW` from `0.027488` to `0.030949`, `+0.003462`).
6. `detector_ablation_H32A_beats_D0`: **PASS** (`0.043535` vs `0.039359`, `+0.004176` at matched Poisson `d=2.8` placer).

**Why Clause 4 Failed & Why Fail-Closed Governance Held:**
When `600 m` visible-fault buffering carves out short (`400–900 m`) withheld `NE` segments, `H29-S`'s tighter `min_sep = 2.0 px` packs 2–3 dots onto a single short fragment, whereas `min_sep = 2.8 px` places 1–2 dots and spreads the saved budget into far-field basin interiors (`c = 0.06305` vs `H29-S` `0.05270`) where catalogue-internal holdouts carry zero truth (`IR-2026-10-26-16`). On unbuffered `HOLDOUT-DTI` (`0.113813` vs `0.105277`, `+0.008536`) and whole-quadrant OOF (`0.169096` vs `0.155231`, `+0.013865`), `H32-S` decisively beats `H29-S`. Per `AGENTS.md` (*"Do not tune thresholds after seeing results"*), `H32-1` fails closed (`verdict = "negative"`, `ok_to_submit = False`), which is independently reinforced by its `79.56%` 3-px proximity to unscored `H31-1`.

### 4.3 Experiment `E3` — Stitched-OOF GeoTIFF Build & 25-Raster Uniqueness Screen
- **Deliverable:** `docs/downloads/research/gems27-h32-pdhc-kernel-celf28-20261026-324a95651136-allfinite.tif` (`sha256: 6ae965f5f92a23ebaf660291dd4c1c0dd7f0f710282a559fe3389786d5a2857e`), paired `.zip`, `-nan.tif` diagnostic twin, `97`-char note, and `evidence/h32_s11_run_card_2026-10-26.json`.
- **Format & `[0, 1]` Range Validation:** `EPSG:32611`, `3730 × 3292`, `float32`, `nodata = None`, **all `12,279,160` cells finite in `[0.0, 1.0]`** (`0` `NaN`, `0` `Inf`, `37,654` exact `1.0` dots, `0` catalogue overlap, `d_cat_min = 2.236 px > 2.0`).
- **Uniqueness:** Max 3-px dot overlap = `57.83%` vs 12 pinned focus peers, `58.55%` vs 10 active `2026-10-26` sibling `.tif`s, `59.31%` vs live-scored `GEMSDOE27` submissions (`<= 70%`), and max `|Spearman| = 0.1222 <= 0.90`.

---

## 5. Remaining Work, Limitations & Next Steps for Session 12

1. **Catalogue-Internal Holdout Proxy Ceiling:** All local spatial holdouts hide mapped USGS/NBMG faults (`|G| = 60,988` px) and assign zero reward to unmapped intra-basin faults (`>300 m` from catalogue), systematically favoring tighter packing on isolated buffered fragments over full-map coverage.
2. **External Official Data Gate (`H32-4` / `H27-16`):** Outbound network egress in this sandbox is restricted to `github.com` and `pypi.org`, blocking direct download of official DOE GDR #1391 sinter/travertine (`faffcf69...`) and 2 m thermal probe (`1301f70d...`) packages and USGS ScienceBase 3D Great Basin MT resistivity slices. Fetching and SHA-256-pinning those datasets outside the sandbox remains the highest-upside external lever toward `0.3195` / `0.4413`.
3. **Queued Untried Local Hypotheses (Seeds `>= 600`):**
   - **`H32-2` (`TRG-M`, seeds `600–609`):** Miller-Singh tilt-angle derivative $\arctan(\mathrm{VDR}/\mathrm{THDR})$ + upward-continuation attenuation ratio to equalize deep (`1–3 km`) sub-alluvial faults against thin (`20 m`) basaltic flow rims.
   - **`H32-3` (`BDSS-A`, seeds `610–619`):** 2D vector-advected hanging-wall MT clay-cap (`cond_surf`) + footwall `depth_to_base_surf` half-graben coupling.
   - **`H32-5` (`DS28-OPT`, seeds `630–639`):** Exact Charnes-Cooper / Dinkelbach fractional-DTI joint optimization of dot budget $N^*$ and adaptive ridge spacing $d_{\min}(x) \in [2.2, 3.0]\text{ px}$ on `H32-1` cover-aware Poisson-kernel OOF surfaces.
