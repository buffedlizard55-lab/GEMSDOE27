> **Current correction (2026-10-26):** Read the [readiness audit](knowledge/28_submission_readiness_audit_2026-10-26.md) and the subsequent [H31-3 result](knowledge/29_h31_3_mt_graben_result_2026-10-26.md).
> H31-1 is evidence-qualified and downloadable, but **not authorized for a weekly slot without a separate selector/current-registry/cap check**.
> H31-3 was subsequently preregistered and tested; it is a negative research artifact, never an eligible download.
> Historical “OK TO SUBMIT” wording below is superseded by this selector requirement.

# Executive Summary: GEMSDOE Competition — Highest-Scoring Submissions Analysis & Unique Submission Strategy

**Repository:** `buffedlizard55-lab/GEMSDOE27`  
**Date:** 2026-10-26  
**Session:** 12 (H31-1 approved; H32 and H31-3 negative research lanes completed)<br>
**Status:** ✅ **H31-1 ONLY: EVIDENCE PASS / DOWNLOAD VALIDATED — HUMAN SELECTOR REQUIRED BEFORE ANY WEEKLY SUBMISSION**<br>
**Latest research result:** ❌ **H31-3 MT-graben: DO NOT SUBMIT** — its frozen H31-S comparison failed 4/5 efficacy clauses; no live organizer score is claimed.

---

## 1. Executive Decision Table: What to Submit Right Now

| Focus Site | Historical Best Submission (Hash-Verified) | Live Score (OWNER-REPORTED) | Dots (N) | Blind Coverage (c) | Concentration | 3-px Overlap vs GEMSDOE32 | 3-px Overlap vs **H31-1** | Actionable Guidance |
|------------|-------------------------------------------|----------------------------|----------|-------------------|---------------|---------------------------|--------------------------|---------------------|
| **GEMSDOE32** | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` (sha256: `c55bafc4…`) | **0.2778** | 37,654 | 0.0592 | 6.50× | 100.0% | **50.2%** | **HISTORICAL BENCHMARK (#1 of 9)** — ALREADY SUBMITTED; DO NOT COPY OR RE-SUBMIT. |
| **GEMSDOE36** | `anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif` (sha256: `e1589102…`) | **0.2750** | 38,854 | 0.0610 | 6.34× | 97.4% | **50.5%** | ALREADY SUBMITTED (G32 + 1,200 PINN dots) — DO NOT RE-SUBMIT. |
| **GEMSDOE31** | `h27-4-solo-d28-20261004-8acb75e1-nan.tif` (sha256: `07b6db44…`) | **0.2710** | 40,199 | 0.0626 | 6.18× | 95.4% | **53.0%** | ALREADY SUBMITTED (B1-only sibling of G28/G31) — DO NOT RE-SUBMIT. |
| **GEMSDOE28** | `h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan.tif` (sha256: `ab023001…`) | **0.2708** | 40,199 | 0.0626 | 6.18× | 95.4% | **53.0%** | ALREADY SUBMITTED (in-footprint identical to G31; S18 collapsed to 0.0217) — DO NOT RE-SUBMIT. |
| **GEMSDOE33** | `h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif` (sha256: `87f857d5…`) | **0.2632** | 41,865 | 0.0649 | 5.91× | 92.6% | **54.3%** | ALREADY SUBMITTED (H19-5 variant) — DO NOT RE-SUBMIT. |
| **GEMSDOE25** | `dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif` (sha256: `91eae1ca…`) | **0.2600** | 44,090 | 0.0668 | 5.80× | 88.2% | **55.9%** | ALREADY SUBMITTED (unpruned d=2.8) — DO NOT RE-SUBMIT. |
| **GEMSDOE30** | `d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca-zeros.tif` (sha256: `8cf893ea…`) | **0.2600** | 44,090 | 0.0668 | 5.80× | 88.2% | **55.9%** | ALREADY SUBMITTED (byte-identical in-footprint to GEMSDOE25) — DO NOT RE-SUBMIT. |
| **GEMSDOE24** | `h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif` (sha256: `68d0e2e4…`) | **0.2477** | 60,069 | 0.0751 | 5.77× | 88.5% | **57.4%** | ALREADY SUBMITTED (over-dense d=1.5) — DO NOT RE-SUBMIT. |
| **GEMSDOE27** | Slot 1: `topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif` (0.2449) | **0.2449** | 61,328 | 0.0764 | 5.67× | 86.7% | **57.7%** | **THIS REPO** — Both Slot 1 and H29-S (0.2190) ALREADY SUBMITTED. Only **Session-10 H31-1** is evidence-qualified; selector/cap review remains required. |
| **GEMSDOE27** | **H29-S**: `gems27-h29-hydrothermal-piedmont-celf-20261025-511898747886-allfinite.tif` | **0.2190** | 37,654 | 0.0527 | 5.79× | 56.1% | **62.8%** | **#1 of 2026-10-25 non-H19-5 cohort** — ALREADY SUBMITTED; do not re-upload. |
| **GEMSDOE27** | **H31-1 (Session 10)**: `gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif` (sha256: `2c002b02…`) | **UNSCORED** | 37,654 | **0.0636** | **5.94× (est.)** | **50.2%** | **N/A (THIS FILE)** | ✅ **EVIDENCE PASS / DOWNLOAD VALIDATED** — all automated gates passed, but a human selector must recheck cap/current registry before any weekly submission. |
| **GEMSDOE27** | **H31-3 (Session 12)**: `gems27-h31-3-mt-graben-celf28-20261026-0f397db36baf-allfinite.tif` (research only; sha256: `da29080b…`) | **UNSCORED** | 37,654 | n/a | n/a | **49.2%** | **86.9%** | ❌ **DO NOT SUBMIT** — H31-3−H31-S pooled HOLDOUT-DTI +0.000366, CI [−0.001182,+0.001823], 6/10 seeds and 2/4 folds; 4/5 frozen efficacy clauses failed. |

---

## 2. PhD-Level Forensic Analysis: Why GEMSDOE32 Scored 0.2778

### 2.1 Exact Pixel Identity (MEASURED)
**GEMSDOE32's `h33-h33-2-b2` (37,654 dots) is pixel-exactly:**
```
(GEMSDOE25 d=2.8 > 0) & (EDT(~existing_faults) > 2.0)
```
Starting from GEMSDOE25's dotted H19-5 at d=2.8 (44,090 dots, 0.2600):
- Remove 3,891 dots with d(catalogue) ≤ 1 px → 40,199 dots → **0.2708** (GEMSDOE28/31)
- Remove further 2,545 dots with 1 < d(catalogue) ≤ 2 px → 37,654 dots → **0.2778** (GEMSDOE32)

**No new geology, no new detector** — the winning step is a *deletion* of 6.3% of dots.

### 2.2 Why the Deletion Raises DTI (MODEL from official metric)
Under DTI = TP / (0.2·TP + 0.2·FP + 0.8·|G|) with α=0.2, β=0.8, R=300m triangular kernel:

1. **Masking Asymmetry:** Catalogue pixels are masked from scoring; hidden truth is *not* the catalogue. Dots hugging known traces only earn credit if a distinct hidden fault pixel lies within 300m — geometrically unlikely when the dot exists because the detector fired on the known fault's own scarp/edge.

2. **Detector Echo:** The H19-5 family's strongest responses are on mapped structures. The 100–200m annulus is where the echo of a *known* fault lives. GEMSDOE27 measured r≤1 version OOF (+0.0022 solo, +0.0141 stacked, HOLDOUT-DTI); GEMSDOE32 extended to 2px and live-mirrored +0.00487.

3. **Budget Interaction:** Dotting already moved the family to the flat optimum (44,090 px at d=2.8, MODEL 0.2550 vs 0.2477 live at 60,069 px). Removing lowest-credit 6–15% of mass slides along the same curve: 0.2600 → 0.2708 (r1) → 0.2778 (B2).

### 2.3 The Uncomfortable Corollary (MEASURED)
**All five top files (0.2600, 0.2632, 0.2708, 0.2750, 0.2778) are the SAME dot field re-thinned:**
- 91–100% of each file's dots lie within 3px of the 0.2778 file's dots
- Family credit concentration plateaued at 5.3–5.7× blind
- Beating 0.2778 by editing its dots is **FORBIDDEN** by uniqueness rule (>70% dots within 3px = duplicate lane)

### 2.4 Can We Beat 0.2778? (Judgement)
| Path | P(beat 0.2778) | Expected Margin | Verdict |
|------|----------------|-----------------|---------|
| Another H19-5 emission edit | 0.5–0.65 | +0.003–0.010 | **FORBIDDEN** (uniqueness rule) |
| Genuinely new detector at B2/38k | 0.25–0.40 | Up to 0.30+ | **ONLY VIABLE PATH** |

The leaderboard gap (0.3195–0.4413) implies the leader's credit density is ~25–60% above this family's — requires a better detector (most plausibly supervised learning on 1m DEM + full GeoDAWN stack).

---

## 3. GEMSDOE27 H29-S (0.2190) Forensic Diagnosis vs. 0.2778

| Deficit | Measurement | H31-1 Fix |
|---------|-------------|-----------|
| **min_sep=2.0 2D crowding** | 8.51% dots have ≥3 neighbors in 300m (12.5× worse than G32's 0.68%); c = 0.0527 vs 0.0592 | **min_sep_px = 2.8** axial-crest CELF → c = 0.0636 (+20.7%) |
| **Near-catalogue halo bleed** | 24.1% vs 15.0% at 2<d_cat≤5px; 9,075 dots dumped in flanks | Quantile-calibrated M_Sub + 800m halo subtraction |
| **LiDAR-gap starvation** | 18.3% dot share in 24.63% area (single-tree under-emission) | **Dual-regime M_Sub (LiDAR-free) ⊕ M_Full** cross-fitting |
| **Walker Lane SE deficit** | H29-A trails D0 by -0.0057 in SE quadrant | Added `ieq/deq` seismic fabric × `geod_shearrate` → SE = 0.0589 |

---

## 4. Current Approved Unique Submission: H31-1 (Session 10)

### 4.1 Machine-Validated Gates (ZERO HUMAN INTERVENTION)
| Gate | Status | Evidence |
|------|--------|----------|
| **Format & [0,1] Range** | ✅ PASS | Single-band float32, EPSG:32611, 3730×3292, exact {0.0,1.0} across 12,279,160 cells, 0 NaN, 0 Inf, nodata=None |
| **Leakage Canary (E1)** | ✅ PASS | Max direction-invariant ROC-AUC = 0.5895 ≤ 0.90 (max_H31 = 0.5606) |
| **27-Raster Uniqueness (E1+E3)** | ✅ PASS | Max 3-px dot overlap = 62.8% ≤ 70% (50.2% vs G32); Max Spearman = 0.1645 ≤ 0.90 |
| **Blind 40-Cell Holdout (E2)** | ✅ 5/5 CLAUSES PASS | Seeds 400–409, 120,778 withheld positives, gems27.metric v1 + holdout-blind-buffered-v2 |

### 4.2 Holdout Results (HOLDOUT-DTI, Catalogue-Internal, NOT Live Organizer Score)
| Comparator | Pooled DTI | Δ vs H31-S | 95% CI | Seeds | Folds |
|------------|------------|------------|--------|-------|-------|
| **H31-S (Candidate)** | **0.047302** | — | [0.0445, 0.0496] | 10/10 | 4/4 |
| H31-A (Detector Poisson Ablation) | 0.045202 | -0.0021 | — | — | — |
| H29-S (Live 0.2190) | 0.044116 | **+0.003185** | [+0.0015, +0.0051] | 9/10 | 3/4 |
| D0 (Full-32 Control) | 0.040298 | **+0.007004** | [+0.0046, +0.0090] | 10/10 | 4/4 |
| B0 (Base) | 0.037725 | **+0.009577** | [+0.0080, +0.0112] | 10/10 | 4/4 |
| H28_1_B2 | 0.039091 | +0.008211 | — | — | — |
| U0 (Null) | 0.014825 | +0.032477 | — | — | — |

**Per-fold breakdown (H31-S vs D0):** NW +0.0001, NE_LidarGapHeavy +0.0168, SW +0.0040, SE +0.0067

### 4.3 Download & Submission Details
| Item | Value |
|------|-------|
| **Primary .tif** | `docs/downloads/gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif` (806 KB) |
| **Single-TIFF .zip** | `docs/downloads/gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.zip` (180 KB) |
| **SHA-256** | `2c002b02792419864bd3b29a218e543cb41e3f07b3b57c29ef35c6e39e184bfe` |
| **Unique Submission Name** | `27GEMSDOE-H31-DRCG-WL-20261026-cf8e1bbef244` |
| **Content ID** | `cf8e1bbef244` |
| **Copyable Note (118/140 chars)** | `27GEMSDOE H31-1 | dualRegime MSub+MFull+WLseis+obliq+CELF2.8 B2 37654px | id cf8e1bbef244 | unscored validated-promote` |
| **Validator JSON** | `docs/downloads/checks-gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.json` |
| **Run Card** | `evidence/h31_s10_run_card_2026-10-26.json` |

---

## 5. Session 12 Negative Result: H31-3 MT Graben-Margin Coupling

**Verdict: DO NOT SUBMIT.** H31-3 added eight preregistered label-free cross-strike transforms from `cond_surf`, `depth_to_base_surf`, `iso_grav_anom`, and `geod_dilaterate` to the H31 dual-regime model. It tested the prediction that a conductive clay-cap/brine anomaly lies 300–900 m basinward of a steep basement-margin gradient; the named non-fault mimic was conductive evaporite/playa fill at a lithologic contact.

- **E1 pass:** maximum single-feature direction-invariant AUC = **0.53194** (no leakage); maximum pre-placement Spearman vs the 12 pinned peers = **0.11011**.
- **E2 fail (HOLDOUT-DTI, not an organizer score):** fresh seeds 510–519, 40 buffered spatial cells, 121,745 withheld positives. H31-3-S = **0.045332** vs exact H31-S = **0.044966**; paired mean delta **+0.000392**, 95% CI **[−0.001182, +0.001823]**, 6/10 positive seeds and 2/4 positive folds. Only 1/5 frozen efficacy clauses passed.
- **E3 research binding:** all-finite `{0,1}` GeoTIFF validation passed. It passes the 12-peer uniqueness screen (max 56.74% 3-px overlap; max final rank correlation 0.04669), but has **86.87%** 3-px overlap with the existing H31-1 in the stricter all-local-raster check. Its manifest sets `ok_to_submit: false` and it is deliberately stored only under `docs/downloads/research/`.

Receipts: `knowledge/29_h31_3_mt_graben_result_2026-10-26.md`, `evidence/h31_3_e1_canary_and_surface_510_519.json`, `evidence/h31_3_e2_holdout_510_519.json`, and `evidence/h31_3_run_card_2026-10-26.json`. The seed block is closed: do not tune or rerun H31-3 on 510–519.

---

## 6. Research Ledger: Tested and Remaining Geological Hypotheses

The following table preserves the originally ranked candidates while marking those now conclusively tested. Any future candidate must be newly preregistered, use fresh seeds, pass E1/E2/E3, and improve holdout before it can be considered for a weekly slot.

| Rank | ID | Hypothesis | Specific Layers | Physical Signature / Transform | Why Missing from USGS/INGENIOUS | Non-Fault Mimic | Differs from Repo | Expected ΔHOLDOUT-DTI | Cost | Data Availability |
|------|-----|------------|-----------------|-------------------------------|----------------------------------|-----------------|-------------------|----------------------|------|-------------------|
| **#1** | **H31-2 / H32** | **Poisson-Theorem Gravity–Pseudogravity Hydrothermal Demagnetization Residual (ΔM→0, Δρ≠0)** | `rtp`, `iso_grav_anom_vg`, `iso_grav_anom_hg`, `tmi_vg`, `TMI_up150`, `K`, `Th` | Local sliding-window regression residual `iso_grav_anom_vg - (α_loc·rtp + β_loc)` gated by high `iso_grav_anom_hg` and low `tmi_vg` (≤0) | Hydrothermal upflow alters crustal magnetite → non-magnetic hematite/pyrite/illite, erasing magnetic edge while preserving basement density fault step | Non-magnetic Paleozoic carbonate-on-granite pluton contacts | Existing `H28-1` and `subsurface_features.py` multiply `min(grad_rtp, grad_grav)`, which **zeros out** magnetite-destroyed geothermal fault conduits! | +0.001 to +0.005 | Low–Medium (~10 min CPU) | **TESTED AS H32 — NEGATIVE** on seeds 500–509; frozen efficacy gate failed. Do not retry the tested formulation. |
| **#2** | **H31-3** | **Magnetotelluric Brittle–Ductile Conduit & Basement-Relief Asymmetric Graben Margin Coupling** | `cond_surf`, `depth_to_base_surf`, `iso_grav_anom`, `geod_dilaterate`, `det_elev` | Cross-strike pairing: steep `∇depth_to_base_surf` basin-bounding fault walls + adjacent hanging-wall `cond_surf` conductive clay-cap/brine plumes within 300–900m down-dropped toward basin minimum | Buried range-front/intrabasin geothermal faults exhibit low-resistivity smectite caps offset basinward of resistive footwall basement step (Gasperikova et al. 2022) | Conductive evaporative playa salt pans | `H28-3` tested co-located `dilaterate × cond_surf` globally (-0.0026), **never** cross-strike asymmetric pairing against `∇depth_to_base_surf` | +0.001 to +0.004 | Medium (~15 min CPU) | **TESTED — NEGATIVE** on fresh seeds 510–519: 4/5 frozen efficacy clauses failed and local H31-1 overlap is 86.87%. Do not tune/rerun. |
| **#3** | **H31-4** | **Supervised Seismogenic Transfer Learning: USGS Quaternary Fault Slip-Rate Labels → Great Basin Microseismicity** | `ieq_n100a15`, `deq_n100a15`, `geod_shearrate`, `geod_dilaterate`, USGS Q-faults slip-rate (vector) | Fine-tune `HistGradientBoosting` on USGS Q-fault slip-rate classes (categorical: <0.2, 0.2–1, >1 mm/yr) using 15 subsurface transforms as features; transfer to Great Basin microseismicity clusters | USGS Q-faults scope ≈ evidence of coseismic surface deformation in ~1.6 Ma; **faults without young scarps** (buried beneath alluvium/older bedrock) are preferentially missing — they express in seismicity, not lidar-scarp bands | Tectonic tremor / slow slip unrelated to Quaternary faulting | First **supervised transfer** from labelled USGS slip-rates to unlabelled Great Basin microseismicity; `H31-1` uses `ieq/deq` only as unsupervised coherence | +0.002 to +0.006 | Medium–High (~30 min CPU + GPU fine-tune) | **100% locally hash-pinned** USGS Q-faults vector (fetched via `scripts/fetch_vector_faults.py`) — VIABLE NOW |
| **#4** | **H31-5** | **Hydrothermal Alteration Mineralogy from ASTER TIR Emissivity (Quartz/Sericite/Chlorite Indices)** | ASTER L2 Surface Emissivity (Bands 10–14), `geodawn_rad_u8`, `geodawn_extensions_u8` | Quartz Index = (B13-B12)/(B13+B12); Sericite = (B11-B12)/(B11+B12); Chlorite = (B10-B12)/(B10+B12); aligned linear anomalies along fault traces | Fossil/active hydrothermal fault upflow zones marked by siliceous sinter, argillic (sericite), propylitic (chlorite) alteration halos — **invisible to USGS Q-faults** which require surface rupture evidence | Lacustrine Lake Lahontan carbonate muds, playa evaporites, unaltered volcanic glass | **No optical/thermal mineralogy transform exists in repo** — `H29` uses only magnetic/gravity/strain/lidar; ASTER TIR is orthogonal to potential fields | +0.002 to +0.007 | High (requires ASTER ingest) | **Free official NASA LP DAAC** (ASTER GED/GDS, `https://lpdaac.usgs.gov/products/ast_07xt/`); **blocked in sandbox egress** — requires external download |
| **#5** | **H27-16** | **DOE GDR #1391: Paleo-Geothermal Sinter/Tufa Aprons + 2m Temperature Probes + Quaternary Volcanics** | GDR #1391: `paleo_geothermal_regional.zip`, `2m_temperature_probe_INGENIOUS_regional_data.zip`, `great_basin_q_volcanics.zip` | Anisotropic linear alignments of siliceous sinter/carbonate tufa terraces (Siler et al. 2022) coupled with >+2.5°C 2m probe thermal anomalies (Kraal et al. 2022) | Fossil sinter/travertine cementation masks Holocene scarps while directly marking fossil/active hydrothermal fault upflow zones | Lacustrine Lake Lahontan tufa mounds & lateral outflow plumes | Uses **3 official regional vector/probe packages** absent from `gdr_wellspring_in_footprint.csv` | +0.002 to +0.008 | Medium–High (external ingest) | **Free official US DOE CC-BY-4.0** (`https://gdr.openei.org/submissions/1391`, DOI 10.15121/1881483); **SHA-256-pinned in `scripts/fetch_external_layers.py`** — **blocked in sandbox** until raw zips supplied |

---

## 7. Recommended Next Steps (Priority Order)

### Current Decision
1. ✅ **H31-1 remains the only evidence-qualified candidate** — its download and manual portal instructions are at `docs/how-to-submit.html`. A human weekly-slot selector/cap/current-registry decision remains separate and must not be automated.
2. ❌ **H32 (formerly H31-2) and H31-3 are closed negative lanes.** Neither may be tuned, re-emitted, uploaded, or used to spend a weekly slot.

### Next Research Gate
3. Preregister one genuinely new, label-free candidate with a new seed block only after reviewing the completed negative cards; it must pass E1 leakage/peer checks and improve E2 HOLDOUT-DTI before E3 promotion.
4. Candidate directions still requiring a new preregistration: supervised but leakage-guarded microseismic transfer (H31-4), or an external-data hypothesis only after bytes are authorized, restored, and SHA-256 verified.

### External Data Gates (Requires Owner Action)
5. **H31-5 (ASTER TIR):** Download ASTER L2 emissivity tiles covering footprint from NASA LP DAAC (free, CC-BY-4.0), record checksums, and only then assess a label-free transform.
6. **H27-16 (GDR #1391):** Obtain the raw official packages via an authorized route and hash-verify them before feature creation; sandbox egress currently cannot retrieve `gdr.openei.org`.

---

## 8. [0,1] Portal Error: Root Cause & Permanent Fix

**Root Cause 1 (NaN outside footprint):** `sample_submission.tif` has 7,111,787 NaN pixels outside the 5,167,373-pixel study footprint. Strict validator `((arr >= 0.0) & (arr <= 1.0)).all()` returns `False` if any NaN exists anywhere in the 3730×3292 array. Official reference notebook Cell 19 initializes `y_out = np.zeros(...)` with `nodata=None`.

**Root Cause 2 (Float32 sentinel bleed):** Raw `training_features.tif` stores `-3.4028235e+38` sentinels on 3,061 cells *inside* the valid footprint; unclipped pipelines propagate out-of-range values.

**Automated Guarantee on H31-1:** Primary all-finite zeros-outside GeoTIFF (`nodata=None`, 0 NaN/Inf across all 12,279,160 pixels, value set strictly {0.0, 1.0}) — verified by independent re-read (`scripts/verify_downloads.py`, 162/162 checks PASS).

---

## 9. Limitations & Access Needed

| Limitation | Impact | Owner Action Required |
|------------|--------|----------------------|
| No DrivenData auth | Cannot auto-download training data, cannot auto-submit | Run `bash scripts/download_competition_data.sh` on unrestricted machine into `data/` |
| No live organizer score for any 27GEMSDOE file | Validation is catalogue-internal (HOLDOUT-DTI); paired base is leaky | Submit H31-1, record exact portal score + timestamp in `registry/live_scores.json` |
| Sandbox egress allowlist blocks GDR #1391 & ASTER | H31-4, H27-16 cannot be validated in-container | Download raw zips externally; place in `data_cache/` with SHA-256 verification |
| CI cannot restore `data_cache/` | Raster-dependent tests skipped in CI (2 skipped) | Provide GitHub token with read access to sibling repos for CI data restore |
| Leaderboard high discrepancy (0.4413 vs 0.3195) | Unverified; no ORGANIZER-CONFIRMED receipt | Paste submission-page receipt to upgrade any figure |

---

## 10. Compliance Checklist

- [x] **Automation:** Never requests `drivendata.org` (Terms of Use prohibit bots)
- [x] **AI Disclosure:** Stated in `AI_DISCLOSURE.md` (Official Rules requirement)
- [x] **Deadline:** Using earlier binding time (5:00 p.m. ET per Rules A.1)
- [x] **Finalist Deliverables:** This repository is the code + documentation deliverable
- [x] **Unique Submission:** H31-1 passes 27-raster uniqueness (max 62.8% ≤ 70%)
- [x] **Format Validation:** All-finite [0,1] GeoTIFF, CRS/shape/transform match sample
- [x] **Negative Results Delivered:** H28-3, H30, H29-2, H31-RankEnsemble, H32, and H31-3 all documented as negative

---

## 11. Sources & Verification Links (Official, Verified)

| Resource | URL | Status |
|----------|-----|--------|
| DrivenData Competition #306 | https://www.drivendata.org/competitions/306/competition-doe-gems/ | Official |
| Competition Overview | https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ | Official |
| About Page / Resources | https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/ | Official |
| Data Download (login-walled) | https://www.drivendata.org/competitions/306/competition-doe-gems/data/ | Official |
| Reference Solution | https://github.com/drivendataorg/gems-prize-reference-solution | Official |
| Official Rules PDF | https://docs.nlr.gov/docs/fy26osti/96647.pdf | Official |
| GEMS Data (GDR #1391) | https://gdr.openei.org/submissions/1391 | Official |
| USGS GeoDAWN Surveys | https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and | Official |
| INGENIOUS Project | https://gbcge.org/current-projects/ingenious/ | Official |
| EPSG:32611 | https://epsg.io/32611 | Official |
| Tversky Index | https://en.wikipedia.org/wiki/Tversky_index | Reference |

**All scores labelled `OWNER-REPORTED` unless accompanied by a submission-page receipt. No `ORGANIZER-CONFIRMED` scores exist in this repository.**

---

## 12. Verification Commands (Run Before Any Submission)

```bash
# 1. Restore hash-pinned data (17 artifacts)
GEMS_DATA_DIR=./data_cache python scripts/restore_data.py

# 2. Fetch & SHA-256-authenticate 12 peer rasters
python scripts/fetch_parallel_registry.py

# 3. Build 32-band label-free feature matrix
python scripts/prepare_data.py

# 4. Run H31-1 holdout validation (E1 canary + E2 40-cell blind)
python scripts/run_h31_holdout.py  # (or run_h29_holdout.py adapted for H31)

# 5. Verify downloads (162 automated checks)
python scripts/verify_downloads.py

# 6. Check submission readiness audit
cat docs/data/submission_readiness_audit.json

# 7. Run tests
python -m pytest -q
```

---

## 13. Conclusion

**The best evidence-qualified unique file is `gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif` (H31-1).** It has passed 100% of automated machine validation gates without human intervention, but is **not authorized for a weekly slot until a human selector rechecks cap and current registry**:
- 5/5 frozen holdout clauses on fresh seeds 400–409 (new #1 blind pooled HOLDOUT-DTI 0.0473)
- 27-raster uniqueness (max 3-px overlap 62.8% ≤ 70%; 50.2% vs GEMSDOE32 0.2778)
- Strict [0,1] all-finite GeoTIFF validation (fixes "Predicted values must be in range [0, 1]")

**Do not re-submit any historical file from GEMSDOE24–36** — all have already been submitted, and 8 of 9 belong to the exhausted H19-5 ridge clone cluster (86.7%–100% 3-px overlap with GEMSDOE32).

**H32/H31-2 and H31-3 were both tested against spatially blocked holdout and are negative.** Their tiny or adverse effects do not support a weekly slot, and their results do not imply a live-score projection. To exceed the OWNER-REPORTED 0.2778 benchmark, a future approach must introduce genuinely new information, be preregistered, use fresh seeds, improve the spatial HOLDOUT-DTI gate, and pass the complete uniqueness/validator screen before a separate selector decision.

**Next research session:** choose only one new direction after preregistration—leakage-guarded H31-4 microseismic transfer if its independent target construction can be demonstrated, or an external-data geological hypothesis only after authorized checksum-verified acquisition. No automation may upload it to DrivenData.