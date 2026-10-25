# 16 — Session 7 Results (`Lane L-S7-2026-10-25` / `H29-1`), Run-Card Audit, Limitations, and Next Steps

**Date (UTC):** 2026-10-25  
**Preregistration Commit (Frozen Before Execution):** `30accf8` (`knowledge/15_geothermal_vent_discovery_and_h29_preregistration.md`)  
**Shipped Unique GeoTIFF (`E3`):** `docs/downloads/gems27-h29-hydrothermal-piedmont-celf-20261025-511898747886-allfinite.tif` (`825,276 B`, SHA-256 `8585c5e870f197f84fda5bac7f22047d646fb73d455eb8b1129486c79bb976cf`, `37,654` binary `{0.0, 1.0}` dots, `all-finite` zeros-outside `nodata=None`)  
**Machine Gate Verdict (`evidence/h29_run_card_2026-10-25.json`):**
- **Technical Format & Uniqueness Validator:** **`PASS (100%)`** — `EPSG:32611`, `3730×3292`, `float32`, `0` NaN across all `12,279,160` cells, exact `{0.0, 1.0}` in `[0, 1]`, `0` catalogue overlap, strict `B2` (`d_cat > 200 m`), `min_self_spacing = 2.0 px`, single-GeoTIFF `.zip` (`174,419 B`), `110`-char note (`<= 140`), and `< 70%` 3-px dot overlap across all 12 peer rasters (`0.5612` vs `GEMSDOE32`, max `0.6421` vs `GEMSDOE27` Slot 1; max Spearman `0.0472`).
- **Weekly Submission Slot Gate (`AGENTS.md` Hard Rule #3):** **`HOLD WEEKLY SLOT` (`verdict: "negative"`, `ok_to_submit: false`)** — `H29-S` achieved the **highest blind pooled `HOLDOUT-DTI` ever measured in this repository** (`0.042198` buffered / `0.103907` unbuffered) and crushed `B0` (`+0.005829`, `10/10` seeds, `4/4` folds) and the prior promoted champion `H28-1` (`+0.004620`, `10/10` seeds, `3/4` folds), while also beating Session 6's internal control `D0` on pooled `HOLDOUT-DTI` (`+0.001295` buffered / `+0.005399` unbuffered, `3/4` folds `NW, NE_LidarGapHeavy, SW`), **but** its buffered seed-bootstrap 95% CI vs `D0` (`[-0.000986, +0.003695]`, `6/10` seeds) spanned zero because `D0`'s earthquake-fabric coherence (`ieq_n100a15`, `deq_n100a15`) outperformed in `SE` (`-0.002526`). Per `AGENTS.md`, thresholds are never adjusted post-hoc and no weekly submission slot is spent on a partial gate pass.

---

## 1. Summary of the 3-Experiment Budget (`E1`, `E2`, `E3`)

### Experiment `E1` — Univariate Leakage Canary & Pre-Placement Surface Uniqueness (`evidence/h29_e1_canary_and_surface.json`)
- **Withheld segment pool (seeds `210–219`):** `37,000+` unique withheld positive fault pixels across 4 quadrants.
- **Canary result (`<= 0.90` threshold):** **PASS** — max direction-invariant single-feature ROC-AUC = **`0.5765`** (`h29_piedmont_concave_s3`), followed by `h29_piedmont_concave_s8` (`0.5716`), `h29_basin_horst_relief` (`0.5357`), `h29_rtp_destripe_hgm` (`0.5344`), `h29_cond_strain_piedmont` (`0.5331`), `h29_deconf_step` (`0.5322`), and `h29_mag_shallow_res` (`0.5291`, `raw = 0.4709` confirming negative shallow magnetic residual = hydrothermal magnetite destruction).
- **Pre-placement surface Spearman (`<= 0.90` threshold vs 12 peer rasters):** **PASS** — raw pixelwise `|rho| in [0.0855, 0.1116]`; 300 m kernel-density `|rho| in [0.4498, 0.4776]` (`max = 0.4776`).

### Experiment `E2` — Blind 40-Cell Spatial Holdout on Frozen Unused Seeds `210–219` (`evidence/h29_e2_holdout_210_219.json`)
All metrics below are **`HOLDOUT-DTI`** (`gems27.metric v1 + holdout-blind-buffered-v2`, $\alpha=0.2, \beta=0.8, R=300\text{ m}$ triangular kernel, `118,673` withheld positive occurrences across `40` cells, matched full-map `B2` budget `37,654` dots):

| Arm | Description | Buffered Pooled `HOLDOUT-DTI` | Unbuffered Pooled `HOLDOUT-DTI` | `NW` | `NE_LidarGap` | `SW` | `SE` |
|---|---|---:|---:|---:|---:|---:|---:|
| **`H29-S` (Candidate)** | `full-32 + 20 H29 + 10 S2 vesselness` + **Weighted 300 m CELF Cover** | **`0.042198`** | **`0.103907`** | **`0.040344`** | **`0.057200`** | `0.028470` | `0.046471` |
| `D0` (Internal Control) | `full-32 + 15 subsurface` + `priority_poisson_disk(d=2.8)` | `0.040902` | `0.098508` | `0.038171` | `0.054816` | `0.025265` | **`0.048997`** |
| `H29-A` (Detector Ablation) | `full-32 + 20 H29 + 10 S2 vesselness` + `priority_poisson_disk(d=2.8)` | `0.039698` | `0.098191` | `0.038802` | `0.050399` | **`0.029137`** | `0.043296` |
| `H28_1_B2` (Prior Champion) | `full-32 + 6 potential_edges` + `priority_poisson_disk(d=2.8)` | `0.037578` | `0.095259` | `0.026629` | `0.051847` | `0.024657` | `0.048131` |
| `B0` (Base Control) | `full-32` + `priority_poisson_disk(d=2.8)` | `0.036368` | `0.091025` | `0.031739` | `0.049975` | `0.025038` | `0.040999` |
| `U0` (Random Null) | Uniform eligible off-catalogue (`d_vis > 2.0 px`) | `0.015341` | `0.046113` | `0.012307` | `0.012645` | `0.017551` | `0.017389` |

**Key Paired Decompositions (`HOLDOUT-DTI`, 10,000-draw seed bootstrap):**
- **`H29-S` minus `B0`:** **`+0.005829`** (`95% CI [+0.004420, +0.007417]`, **`10/10` seeds**, **`4/4` folds**, `33/40` cells).
- **`H29-S` minus `H28_1_B2` (previous promoted OOF champion):** **`+0.004620`** (`95% CI [+0.003442, +0.005974]`, **`10/10` seeds**, **`3/4` folds**, `30/40` cells).
- **`H29-S` minus `H29-A` (isolated proof that `weighted_celf_cover` fixes `H27-6`):** **`+0.002500` buffered / `+0.005716` unbuffered** (`95% CI [+0.000736, +0.004311]`, **`8/10` seeds**, **`3/4` folds**, `29/40` cells) — especially dominant in **`NE_LidarGapHeavy` (`+0.006801`)** where geophysical/hydrothermal ridges are broader than 1 m LiDAR scarps!
- **`H29-S` minus `D0`:** **`+0.001295` buffered / `+0.005399` unbuffered** (`95% CI [-0.000986, +0.003695]`, `6/10` seeds, `3/4` folds: `NW +0.002172`, `NE_LidarGapHeavy +0.002384`, `SW +0.003205`, **`SE -0.002526`**).

### Experiment `E3` — Dual-Partition Stitched-OOF Submission Build & Audit (`evidence/h29_run_card_2026-10-25.json`)
- Emitted from `0.5 * Quadrant_OOF + 0.5 * Rotated45_Sector_OOF` (every pixel strictly `> 600 m` out-of-fold across two `45°`-offset spatial partitions, eliminating midline seams and full-fit `d_cat <= 5 px` memorization).
- Off-catalogue distance profile of the `37,654` emitted dots: `0` in `<= 200 m` collar; `14,402` (`38.2%`) in `200–1,000 m`; `10,972` (`29.1%`) in `1–3 km`; `12,280` (`32.6%`) in `> 3 km` (`median distance to catalogue = 1.62 km`).
- Passed all 162 checks in `scripts/verify_downloads.py` (`0 failure(s)`).

---

## 2. Limitations & Concrete Prioritized Next Steps

1. **Why `SE` lagged `D0` (`-0.0025`) while `NW, NE, SW` all won (`+0.0022` to `+0.0032`) -> Immediate Next Hypothesis `H29-6`:**
   - The `SE` quadrant covers the Hawthorne–Tonopah–Mina Deflection **Walker Lane seismic belt**, where active transtensional faults exhibit strong earthquake-lineament anisotropy (`ieq_n100a15`, `deq_n100a15`). `D0` included 2 structure-tensor seismic-fabric coherence features (`sub_seismic_fabric_ieq`, `sub_seismic_fabric_deq`) that were omitted from `H29-1`.
   - **Next preregistered experiment (`H29-6`, unused seeds `220–229`):** Append multi-scale earthquake structure-tensor anisotropy + dextral shear alignment (`ieq_n100a15`, `deq_n100a15`, `geod_shearrate`) to `H29-S` + `weighted_celf_cover` and test against both `D0` and `H29-S` on fresh seeds `220–229`.
2. **External Data Gate (`H27-16` / `H29-4` & `H29-3`):**
   - Three official GDR #1391 packages (`paleo_geothermal` sinter/tufa `faffcf69…`, `2m_temp` probes `1301f70d…`, `Quaternary_volcanics` `c4a2d2df…`) and raw USGS 3DEP absolute-elevation tiles (`1,335 m` Lake Lahontan shoreline belt) cannot be fetched directly inside this sandbox's outbound allowlist; maintainer resolution of the zero-job `fetch-gdr-external-layers.yml` Actions workflow unlocks `H27-16`.
3. **Catalogue-Internal Holdout Proxy Limit:**
   - All `HOLDOUT-DTI` values withhold segments of `labels.tif` (`existing_faults.tif`) and cannot directly observe the organizers' newly mapped fault inventory `G`; live public-leaderboard evaluation remains gated on passing the strict composite holdout gate so scarce `5/week` slots are never wasted.
