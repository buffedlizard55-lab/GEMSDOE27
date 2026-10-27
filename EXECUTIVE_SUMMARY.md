# Executive Summary: GEMSDOE Competition — Highest-Scoring Submissions Analysis, Session 12 Ablations & Unique Submission Strategy

**Repository:** `buffedlizard55-lab/GEMSDOE27`  
**Date:** `2026-10-26`  
**Session:** `12` (Lanes `L-S12` / `L-S12B` / `L-S12C`: `H33-1`, `H33-2`, `H33-3`; primary approved file `H31-1` `cf8e1bbef244` unchanged and byte-verified)  
**Status:** ✅ **OK TO DOWNLOAD AND SUBMIT: `docs/downloads/gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif` — ALL AUTOMATED MACHINE VALIDATION GATES PASSED (ZERO HUMAN INTERVENTION)**

---

## 1. Executive Decision Table: All 9 Focus Sites + Exact File to Download & Submit

Every live score below is strictly **`OWNER-REPORTED`** (no DrivenData organizer receipt is stored in this repository); every unobserved estimate is explicitly labeled **`PROJECTION (NOT A SCORE)`**; and every holdout figure is labeled **`HOLDOUT-DTI`** (`gems27.metric v1 + holdout-blind-buffered-v2`):

| Focus Site | Historical Best / Candidate File (SHA-256 Verified) | Score / Status (`Provenance Label`) | Dots (`N`) | Blind Coverage (`c`) | Implied Concentration (`MODEL`) | 3-px Overlap vs `GEMSDOE32` | 3-px Overlap vs **`H31-1`** (`cf8e1bbef244`) | Uniqueness & Actionable Guidance |
|------------|-----------------------------------------------------|-------------------------------------|-----------:|---------------------:|--------------------------------:|----------------------------:|---------------------------------------------:|----------------------------------|
| **`GEMSDOE27` (PRIMARY — SUBMIT THIS ONE)** | **`docs/downloads/gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif`** (`2c002b02…`) | **`UNSCORED`** (`HOLDOUT-DTI = 0.047302`, 95% CI `[0.0442, 0.0500]`, `120,778` withheld pos; **`PROJECTION ~0.235 [0.19–0.26], NOT A SCORE`**) | **37,654** | **0.0636** | — (unscored) | **50.2%** | **SELF (PRIMARY)** | ✅ **UNIQUE VS ALL 9 FOCUS SITES (`max 57.7% <= 70%`) — DOWNLOAD & SUBMIT THIS FILE** |
| **GEMSDOE32** | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` (`c55bafc4…`) | **0.2778** (`OWNER-REPORTED` live) | 37,654 | 0.0592 | 6.50× | 100.0% | **50.2%** | **HISTORICAL BENCHMARK (#1 of 9)** — ALREADY SUBMITTED; DO NOT COPY OR RE-SUBMIT. (`r6-stepprofile 23fbbb51` is unscored; `<=21.1%` peer overlap.) |
| **GEMSDOE36** | `anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif` (`e1589102…`) | **0.2750** (`OWNER-REPORTED` live) | 38,854 | 0.0610 | 6.34× | 97.4% | **50.5%** | ALREADY SUBMITTED (`G32` + 1,200 PINN dots; `97.4%` clone) — DO NOT RE-SUBMIT. |
| **GEMSDOE28** | `gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif` (`5556aa14…`) | **0.2710** (`OWNER-REPORTED` live; `S18-MXTP` = `0.0217`) | 37,660 | 0.0605 | 6.22× | 95.5% | **52.5%** | ALREADY SUBMITTED (`rung-3.0 + B1` `H19-5` clone; `h27-4-r1-solo` = `0.2708`) — DO NOT RE-SUBMIT. |
| **GEMSDOE31** | `gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif` (`07b6db44…`) | **0.2708** (`OWNER-REPORTED` live) | 40,199 | 0.0626 | 6.18× | 95.4% | **53.0%** | ALREADY SUBMITTED (`B1`-pruned `H19-5`, dot-identical in-footprint to `G28 h27-4-r1`) — DO NOT RE-SUBMIT. |
| **GEMSDOE33** | `h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif` (`87f857d5…`) | **0.2632** (`OWNER-REPORTED` live) | 41,865 | 0.0649 | 5.91× | 92.6% | **54.3%** | ALREADY SUBMITTED (`92.6%` `H19-5` variant) — DO NOT RE-SUBMIT. |
| **GEMSDOE25** | `gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif` (`91eae1ca…`) | **0.2600** (`OWNER-REPORTED` live; `H66-MGD` = `0.0742`) | 44,090 | 0.0668 | 5.80× | 88.2% | **55.9%** | ALREADY SUBMITTED (unpruned `H19-5` `d=2.8`) — DO NOT RE-SUBMIT. |
| **GEMSDOE30** | `d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca-zeros.tif` (`8cf893ea…`) | **0.2600** (`OWNER-REPORTED` live; `MSDB1` = `0.1462`) | 44,090 | 0.0668 | 5.80× | 88.2% | **55.9%** | ALREADY SUBMITTED (dot-identical in-footprint to `GEMSDOE25`) — DO NOT RE-SUBMIT. |
| **GEMSDOE24** | `h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif` (`68d0e2e4…`) | **0.2477** (`OWNER-REPORTED` live; `GVC1` = `0.0859`) | 60,069 | 0.0751 | 5.77× | 88.5% | **57.4%** | ALREADY SUBMITTED (over-dense `H19-5` `d=1.5`) — DO NOT RE-SUBMIT. |
| **GEMSDOE27 (Historical Scored)** | Slot 1 `5512495c6bd1` (`0.2449`) & Session-7 `H29-S` `511898747886` (`0.2190`) | **0.2449 / 0.2190** (`OWNER-REPORTED` live) | 61,328 / 37,654 | 0.0764 / 0.0527 | 5.67× / 5.79× | 86.7% / 56.1% | **57.7% / 62.8%** | ALREADY SUBMITTED (`H29-S` was #1 of the 2026-10-25 non-`H19-5` cohort) — DO NOT RE-SUBMIT. |
| **GEMSDOE27 (Session-12 Research Archive)** | `H33-1` (`423b1d431032`), `H33-2` (`91ba971e2f33`), `H33-3` (`99c013f6e930`) in `docs/downloads/research/` | **`UNSCORED` (`verdict=negative`, `ok_to_submit=false`)** | 37,654 each | 0.0622 / 0.0650 / 0.0631 | — | 51.4% / 48.2% / 47.4% | **71.2% / 66.9% / 62.5%** | ⛔ **DO NOT CO-SUBMIT WITH `cf8e1bbef244`** (`H33-1` hit all-time #1 `HOLDOUT-DTI = 0.049590` & `<=58.7%` peer overlap, held on `71.21%` intra-site overlap vs unscored `cf8e1bbef244`; `H33-2/3` held on `E2`). |

---

## 2. PhD-Level Forensic Analysis: Why `GEMSDOE32` Scored `0.2778` — and How to Beat `0.2778` & `0.3195`

### 2.1 Exact Pixel Identity (`MEASURED` from SHA-256-Pinned Rasters)
`GEMSDOE32`'s `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` (`37,654` dots, `c55bafc4…`) is pixel-exactly (`symdiff = 0`):
```text
(GEMSDOE25_d2.8 > 0) & (EDT(~existing_faults) > 2.0)
```
Starting from `GEMSDOE25`'s `H19-5` `d=2.8` raster (`44,090` dots, `0.2600` `OWNER-REPORTED`):
1. Deleting `3,891` dots with `d(catalogue) <= 1 px` (`100 m`) leaves `40,199` dots -> **`0.2708`** (`GEMSDOE31` / `GEMSDOE28 h27-4-r1`).
2. Deleting a further `2,545` dots with `1 < d(catalogue) <= 2 px` (`200 m`) leaves `37,654` dots -> **`0.2778`** (`GEMSDOE32`).
3. Adding `1,200` PINN dots back (`GEMSDOE36`, `38,854` dots) diluted the score to **`0.2750`**.

### 2.2 Why Deleting Near-Catalogue Collar Dots Raises DTI (`MODEL` from Official Metric)
Under the official Distance-Tolerant Tversky Index ($\alpha = 0.2, \beta = 0.8$, $300\text{ m}$ linear triangular kernel):
$$\text{DTI} = \frac{\text{TP}_w}{\text{TP}_w + 0.2\,\text{FP}_w + 0.8\,\text{FN}_w}, \qquad \tau^*(\text{DTI}) = \frac{0.2\,\text{DTI}}{1 - 0.2\,\text{DTI}}$$
At $\text{DTI} = 0.2778$, a dot must earn at least $\tau^*(0.2778) = \mathbf{0.0588}$ truth-credit/dot to avoid diluting the score. Known catalogue pixels are masked during scoring, while geophysical/topographic detectors fire strongly on the `100–200 m` halo of already-mapped faults (measured OOF efficiency `0.0034–0.0080`, `7–15×` below break-even). Removing those `6,436` zero-yield collar dots saved `0.2 × 6,436 = 1,287` denominator units for `+0.0178` live DTI without changing the detector.

### 2.3 Can We Beat `0.2778` and `0.3195` (`0.4413` Discrepancy Flagged)?
- **Why `H19-5` re-thinning is closed:** Eight of nine focus sites (`86.7%–100%` 3-px overlap with `GEMSDOE32`) are the same dot cloud; any further edit exceeds the `70%` duplicate threshold and caps near `~0.278`.
- **Why supervised multi-physics + 300 m CELF IS the viable path to `0.30+`:** Non-`H19-5` supervised OOF detectors (`GEMSDOE70 = 0.2478`, `GEMSDOE76 = 0.2343`, `GEMSDOE27 H29-S = 0.2190` `OWNER-REPORTED`) already achieved `5.79×` blind truth concentration at only `40–56%` overlap with `GEMSDOE32`.
- **What `H31-1` (`cf8e1bbef244`) and Session-12 `H33-1` (`423b1d431032`) add:** `H31-1` fixed `H29-S`'s `-11.0%` `min_sep=2.0` clumping loss (`c: 0.0527 -> 0.0636`, `+20.7%`), LiDAR-gap starvation (`NE: 0.0579 -> 0.0663`), and Walker Lane seismicity (`SE: 0.0541 -> 0.0589`), lifting `HOLDOUT-DTI` `+7.22%` (`0.044116 -> 0.047302`; anchor-transfer `PROJECTION ~0.235 [0.19–0.26]`, honest reading likely below `0.2778` on its own). Session-12 **`H33-1`** then lifted `HOLDOUT-DTI` a further **`+6.37%` over `H31-S` (`0.046622 -> 0.049590`, `+12.4%` over `H29-S`)** via asymmetric half-graben dip-vector coupling + canyon-mouth collinearity + `2.3 km` 16-azimuth orthogonal Radon integrals! Combining `H33-1`'s `max_features=0.72` detector with `H33-3`'s `N22.5°E/N67.5°E` stitch + `min_sep=3.15` (`H34-1`), 3-D Euler deconvolution (`H34-2`), and official GDR #1391 sinter/tufa + 2 m probe vectors (`H27-16`) is the scientifically grounded roadmap toward `0.3195+`. (Note: `0.4413` vs `0.3195` leaderboard high remains flagged as an unverified `OWNER-REPORTED` discrepancy in `registry/irregularities.json`.)

---

## 3. Session 12 Complete 3-Experiment Record (`H33-1`, `H33-2`, `H33-3` — Seeds `600..629`)

Per Parallel-Run Protocol §6 (`<= 3` experiments), Session 12 preregistered and executed three experiments on `30` fresh disjoint seeds (`120` blind quadrant-seed cells, `366,650` withheld positive occurrences):

1. **Experiment 1 (`H33-1` / `AGMC-CM-CELF30`, `423b1d431032`, seeds `600..609`, `evidence/h33_s12_run_card_2026-10-26.json`):**
   - **Mechanism:** Asymmetric hanging-wall minus footwall `cond_surf` clay-cap jumps (`+400 m`, `+800 m`) and density/elevation throws along $\hat{\mathbf{u}} = \nabla G_4(\text{depth\_to\_base\_surf}) / \|\nabla G_4\|$, `±1.2 km` canyon-mouth collinearity, `TMI_up150`, `ThK`, end-to-end `lidar_valid`-only `M_Full` (`66` cols, `max_features=0.72`) + `50`-col `M_Sub`, 16-azimuth `2.3 km` orthogonal-Radon Stage-2 manifolds, and `min_sep=3.00` CELF.
   - **Outcome:** **Passed ALL 5/5 frozen `E2` holdout clauses (`HOLDOUT-DTI = 0.049590` vs `H31-S = 0.046622`, `+0.002968`, 95% CI `[+0.001592, +0.004441]`, `9/10` seeds; `+0.003882` vs `H29-S`, `10/10` seeds; `+0.008441` vs `D0`, `10/10` seeds)** and passed 12-peer uniqueness (`max 58.67% <= 70%`), **but** `0°+45°` stitching nudged `3-px` overlap vs unscored `H31-1` (`cf8e1bbef244`) from `66.96%` to **`71.21% > 70.00%`**. Routed fail-closed to `docs/downloads/research/` (`verdict: "negative"`, `ok_to_submit: false`).
2. **Experiment 2 (`H33-2` / `AGMC-MDM-CELF345`, `91ba971e2f33`, seeds `610..619`, `evidence/h33_2_s12_run_card_2026-10-26.json`):**
   - **Mechanism & Outcome:** Dropped the `12` raw `base_X` `lidar_*` columns and expanded `min_sep` to `3.45`. Passed stitched `E1`/`E3` uniqueness (`66.89% <= 70%` vs `cf8e1bbef244`; `55.03%` vs peers), **proving that raw 1 m LiDAR scarp bands are indispensable** (`H33_2-A` fell `-0.00656`, `H33_2-S = 0.040878 < H31-S = 0.044685`). Routed to `docs/downloads/research/` (`ok_to_submit: false`).
3. **Experiment 3 (`H33-3` / `AGMC-WL-CELF315`, `99c013f6e930`, seeds `620..629`, `evidence/h33_3_s12_run_card_2026-10-26.json`):**
   - **Mechanism & Outcome:** Restored all `32` `base_X` bands (`69` cols, `max_features=0.62`) with `N22.5°E + N67.5°E` Basin-and-Range OOF stitch and `min_sep_px = 3.15` (`r_min = \sqrt{10} = 3.1623\text{ px}`, `nbr_le_3px = 0.0`). **Passed stitched uniqueness (`62.50% <= 70%` vs `cf8e1bbef244`; `54.82%` vs peers) AND beat every benchmark (`U0`, `B0`, `D0`, `H29-S`, `H31-S`) on pooled buffered `HOLDOUT-DTI` (`0.044310 > H31-S = 0.044042`; `+0.005605` vs `D0`, `10/10` seeds; `+0.007648` vs `B0`, `10/10` seeds; `SW +0.00563` & `NW +0.00053` vs `H31-S`)**, but missed strict paired consistency clauses `(b)/(c)` (`5/10` seeds vs `H31-S` because `max_features=0.62` diluted `NE_LidarGapHeavy`). Routed fail-closed to `docs/downloads/research/` (`ok_to_submit: false`).

---

## 4. Approved Primary Unique Submission Details (`H31-1` `cf8e1bbef244`)

| Field | Verified Value |
|------|----------------|
| **Machine Verdict (`gems27.readiness.publication_decision`)** | ✅ **`ok_to_publish_as_submission = true` (`OK TO DOWNLOAD AND SUBMIT`)** |
| **Primary All-Finite `.tif`** | `docs/downloads/gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif` (`825,820` B) |
| **Single-TIFF `.zip`** | `docs/downloads/gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.zip` (`184,837` B) |
| **SHA-256 (`.tif`)** | `2c002b02792419864bd3b29a218e543cb41e3f07b3b57c29ef35c6e39e184bfe` |
| **Unique Submission Name** | `27GEMSDOE-H31-DRCG-WL-20261026-cf8e1bbef244` |
| **Copyable Short Note (`118 / 140` chars)** | `27GEMSDOE H31-1 | dualRegime MSub+MFull+WLseis+obliq+CELF2.8 B2 37654px | id cf8e1bbef244 | unscored validated-promote` |
| **`[0, 1]` Format & Grid Gate** | `float32`, `EPSG:32611`, `3730×3292`, `(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)`, exact `{0.0, 1.0}`, `0` NaN/Inf anywhere (`nodata=None`), `37,654` `B2` dots |
| **Step-by-Step Upload Subpage** | `docs/how-to-submit.html` & `docs/executive-summary.html` |
| **Run Card & Readiness Audit** | `evidence/h31_s10_run_card_2026-10-26.json` · `docs/data/submission_readiness_audit.json` |

---

## 5. Five Genuinely Untried Geological Hypotheses Ranked for Next Session (`registry/next_hypotheses.json`, Seeds `>= 630`)

| Rank | ID | Hypothesis | Specific Layers | Physical Signature / Transform | Why Missing from USGS/INGENIOUS | Non-Fault Mimic | Differs from Repo | Expected `ΔHOLDOUT-DTI` | Cost & Official Data Gate |
|---:|---|---|---|---|---|---|---|---|---|
| **#1** | **`H34-1`** | **High-Feature-Retention (`max_features=0.72`) `H33` Detector + `N22.5°E/N67.5°E` Stitch + `min_sep=3.15` CELF** | All `32` `base_X` + `15` `sub15` + `19` `H33` + `3` `H33-2` + `11` 16-az Radon | Retains `H33-1`'s `max_features=0.72` split breadth (`NE = 0.06584`) while decoupling overlap via `22.5°+67.5°` strike-aligned stitch & `min_sep=3.15` (`r_min=3.162 px`, `nbr_le_3px=0.0`) | Preserves blind half-graben clay-cap + bajada canyon-mouth discovery without LiDAR-gap dilution | Interior playas & Lahontan shorelines | Isolates the exact parameter difference between `H33-1` (`0.04959`, `71.2%` ov) and `H33-3` (`62.5%` ov) | `+0.002` to `+0.004` vs `H31-S` | Low (~45 min CPU); 100% locally cached |
| **#2** | **`H34-2`** | **3-D Euler-Deconvolution Structural-Index (`SI=0.0` Contact vs `SI=1.0` Dike) Solution Clustering** | `rtp`, `tmi_hg`, `tmi_vg`, `TMI_up150`, `iso_grav_anom`, `iso_grav_anom_hg`, `iso_grav_anom_vg`, `depth_to_base_surf` | Least-squares 3-D Euler homogeneity solver (Reid et al. 1990) in `9×9` windows; tight horizontal clusters (`sigma_xy <= 150 m`, `200 <= z0 <= 2,500 m`) for `SI = 0` fault contacts | Directly locates sub-alluvial 3-D fault-plane apexes under 200–1,500 m of basin fill | Shallow Miocene basaltic feeder dikes (`SI = 1` without basement throw) | `H29-2`/`H30-1` shifted scalar edges heuristically (negative); 3-D Euler cluster density is untried | `+0.001` to `+0.005` | Medium (~20 min CPU); 100% locally hash-pinned |
| **#3** | **`H34-3`** | **Quadrature Gabor Step-Phase Symmetry & Walker Lane Drainage-Deflection Shear Tensor** | `lidar_ex_mean`, `lidar_cross_max`, `lidar_coh100`, `det_elev`, `det_gradient`, `geod_shearrate` | Odd-symmetric vs even-symmetric Gabor phase congruence (Kovesi 1999) + transverse wash deflection angles across strike-slip corridors | Strike-slip faults in Walker Lane have minimal vertical scarp throw but systematically deflect ephemeral channels 20–150 m laterally | Longitudinal eolian sand-dune crests (even-symmetric ridges) | First quadrature phase-symmetry & lateral channel-deflection transform in repo | `+0.001` to `+0.004` | Medium (~25 min CPU); 100% locally hash-pinned |
| **#4** | **`H27-16`** | **Official DOE GDR #1391 Paleo-Geothermal Sinter/Tufa + 2 m Temperature Probes + Quaternary Volcanics** | GDR #1391 `paleo_geothermal_regional.zip`, `2m_temperature_probe_INGENIOUS_regional_data.zip`, `great_basin_q_volcanics.zip` | Anisotropic siliceous sinter / carbonate tufa alignments (Siler et al. 2022) coupled with `> +2.5 °C` 2 m probe thermal anomalies (Kraal et al. 2022) | Sinter/travertine cementation masks Holocene coseismic scarps while directly marking upflow fault conduits | Lake Lahontan lacustrine tufa mounds & lateral outflow plumes | Uses 3 official GDR #1391 regional vector/probe packages absent from `gdr_wellspring_in_footprint.csv` | `+0.001` to `+0.008` | Medium–High; free US DOE GDR #1391 (`https://gdr.openei.org/submissions/1391`, CC-BY-4.0; blocked by sandbox egress) |
| **#5** | **`H34-4`** | **Slip-Rate & Recency Cost-Sensitive Transfer from Visible NBMG INGENIOUS Qfaults Attributes** | `qfaults_v2_in_footprint.json` (`SLIPRATE`, `AGE` strictly on `sp.known`), `ieq_n100a15`, `deq_n100a15`, `geod_dilaterate`, `geod_shearrate` | Cost-sensitive tree weighting prioritizing Holocene / high-slip-rate (`> 0.2 mm/yr`) visible training traces | Unmapped active geothermal conduits share strain/microseismic signatures of young active faults rather than degraded early-Quaternary scarps | Off-fault 1954 Fairview Peak / Dixie Valley aftershock swarms | All prior detectors weight all `labels.tif` pixels uniformly (`1.0`) | `+0.001` to `+0.004` | Medium (~25 min CPU); 100% locally hash-pinned |

---

## 6. Limitations, Official Sources & Verification Commands

- **Limitations & Access Needed:** (1) DrivenData (`drivendata.org`) is never accessed automatically (Terms of Use); human upload of `cf8e1bbef244` is required to obtain a live organizer score and record it in `registry/live_scores.json`. (2) Sandbox egress permits only GitHub/PyPI/npm, so `gdr.openei.org` (`H27-16`) and Dropbox (`scripts/download_competition_data.sh`) require an unrestricted machine or authorized workflow artifact staging. (3) All `HOLDOUT-DTI` figures are catalogue-internal buffered spatial holdouts, not organizer test-label scores.
- **Official Verified Sources:** [DrivenData #306 Overview](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) · [Competition Home](https://www.drivendata.org/competitions/306/competition-doe-gems/) · [Data Page (login-walled)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) · [Reference Solution](https://github.com/drivendataorg/gems-prize-reference-solution) · [Official Rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) · [DOE GDR #1391 INGENIOUS Dataset](https://gdr.openei.org/submissions/1391) · [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) · [EPSG:32611](https://epsg.io/32611).

```bash
GEMS_DATA_DIR=./data_cache .venv/bin/python scripts/restore_data.py
.venv/bin/python scripts/fetch_parallel_registry.py
.venv/bin/python scripts/prepare_data.py
.venv/bin/python scripts/audit_submission_readiness.py
.venv/bin/python scripts/verify_downloads.py
.venv/bin/python scripts/build_site.py && .venv/bin/python -m pytest -q && .venv/bin/ruff check src/gems27/asymmetric_graben_conduit.py scripts/run_h33*.py scripts/build_h33*.py
```
