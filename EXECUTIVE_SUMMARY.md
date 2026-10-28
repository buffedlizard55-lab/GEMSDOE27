# Executive summary — GEMSDOE27 and nine focus sites

**DO NOT SUBMIT. NOT AUTHORIZED FOR A WEEKLY SLOT.** H31-1 `cf8e1bbef244` is already submitted according to the user, who reports 0.2250. There is no organizer receipt; do not resubmit it. No portal upload was made.

---

## ⚡ Quick answer: which file to download and submit

| File to download | Estimated organizer score | Unique vs other GEMSDOE sites? | OK to download and submit? |
|---|---|---|---|
| No currently approved file | No justified estimate | N/A | **No — no candidate passes all gates** |
| [`27GEMSDOE-h-geo-1-alteration-front-coherence-20261028-7b1944dc121a-allfinite.tif`](docs/downloads/research/27GEMSDOE-h-geo-1-alteration-front-coherence-20261028-7b1944dc121a-allfinite.tif) (SHA-256 `e608ba718d01be91376c0cd8a8efc838f766b62171cfe2078a810a8d7a5aea7b`) | No justified organizer-score estimate (HOLDOUT-DTI = 0.000000 vs control 0.000000; gate failed) | **Yes** — max 3-px dot overlap 0.0502 vs all pinned repo rasters; max surface | **No — frozen holdout gate failed. Research-only file.** |

**Bottom line:** There is no file in this repository that is approved for download and submission to the competition. Every generated research TIFF is explicitly marked **NOT OK TO SUBMIT** until a separate weekly-slot selector authorizes it after a matched current-best holdout win.

---

## New unique TIF generated this session (H-GEO-1)

**File:** `docs/downloads/research/27GEMSDOE-h-geo-1-alteration-front-coherence-20261028-7b1944dc121a-allfinite.tif`
**SHA-256:** `e608ba718d01be91376c0cd8a8efc838f766b62171cfe2078a810a8d7a5aea7b`
**ZIP:** `docs/downloads/research/27GEMSDOE-h-geo-1-alteration-front-coherence-20261028-7b1944dc121a-allfinite.zip`
**Submission name:** `27GEMSDOE-H-GEO-1-20261028-7b1944dc121a`
**Note (91 chars):** `27GEMSDOE H-GEO-1 alteration-front coherence B2 37654px id 7b1944dc121a | unscored research`

**Technical validation (all hard checks PASS):**
- Single-band float32 GeoTIFF, CRS EPSG:32611, shape (3730, 3292), transform matches template
- Values in [0, 1] inside footprint; zeros outside (all-finite variant)
- No NaN or infinities anywhere
- 24,025 dots emitted, min self-spacing 2.83 px, no dots on catalogue faults

**Uniqueness (PASS):**
- Max 3-px dot overlap vs all pinned repo rasters: 0.0502 (limit 0.70)
- Max surface rank Spearman vs all pinned registry rasters: 0.0168 pre-placement, 0.0075 post-placement (limit 0.90)
- Not a duplicate of any GEMSDOE site submission

**Holdout evaluation (FAIL):**
- HOLDOUT-DTI candidate: 0.000000, control B: 0.000000, paired Δ: 0.000000, 95% CI [0.000000, 0.000000]
- 457,660 withheld-positive occurrences, 40 cells (seeds 600–609, 4 folds)
- Gate efficacy: FAIL (0/10 seeds positive, 0/4 folds positive)
- **Verdict: negative** — not approved for a weekly submission slot

**Leakage canary (PASS):** max direction-invariant AUC deviation 0.046 (threshold 0.90) — no leakage.

**Scientific interpretation:** H-GEO-1 targets blind/covered faults with hydrothermal alteration halos that are MISSING from the USGS/INGENIOUS surface-trace catalogue. Because catalogue-internal holdout truth can only measure faults already in the catalogue, a zero holdout DTI is expected for this hypothesis type — it does not prove the approach is worthless for organizer labels, but it does mean the holdout gate cannot authorize submission.

---

## Download and submission decision

| File to download | Local evidence / estimated organizer score | Unique? | May be submitted? |
|---|---|---|---|
| `27GEMSDOE-h-geo-1-alteration-front-coherence-20261028-7b1944dc121a-allfinite.tif` (SHA-256 `e608ba718...`) | HOLDOUT-DTI 0.000000 vs control 0.000000; gate failed. **No justified organizer-score estimate.** | **Yes** vs all pinned repo rasters (max 3-px overlap 0.0502; max Spearman 0.0075) | **No — frozen holdout gate failed. Research-only.** |
| No currently approved file | No estimate | Not applicable | **No — selector authorization is absent.** |

**How to submit (when authorized):** A human must open the [DrivenData competition portal](https://www.drivendata.org/competitions/306/competition-doe-gems/), check remaining weekly slots, and upload the exact named `allfinite.tif` (or its one-TIFF ZIP) with the documented name and short note. The file must be float32, single-band, template-aligned, finite within [0,1] throughout, with zeros outside the footprint. Passing our validator does not guarantee organizer acceptance. A NaN-outside TIFF can trigger "Predicted values must be in range [0, 1]"; use the all-finite variant.

---

## Best reported historical submission per site

The score-to-file links below come from the 2026-10-26 pinned peer registry and owner/sibling reports, **not receipts**. They are not organizer-confirmed. Older executive evidence assigns different files or swaps the GEMSDOE28/GEMSDOE31 values; GEMSDOE25 and GEMSDOE36 file associations are also uncertain. Treat every pairing and claimed maximum as provisional. The files are historical, not new candidates, regardless of their reported values.

| Site | Pinned historical raster | Owner-reported value | Geometry / provenance | Action |
|---|---|---:|---|---|
| GEMSDOE24 | [gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE24/blob/05f6f85c695ff25546dcc2cbbfa34b3c2a8f4f4c/docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif) | 0.2477 | H19-5 dotted d1.5 | Already in registry; not new |
| GEMSDOE25 | [gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE25/blob/0f73c51dc954306468875c02cf98634e64ac0751/docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif) | 0.2600 | H19-5 dotted d2.8; champion parent | Already in registry; not new |
| GEMSDOE27 | [gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE27/blob/b8dd298e10884afffa05436673ac73aeaf850b8c/docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif) | 0.2449 | T-v2 gap closure on D1.5; live A/B below its parent | Already in registry; not new |
| GEMSDOE28 | [gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE28/blob/78e724f95337a6528b1248be5c113c6d6d502891/docs/downloads/gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif) | 0.2710 | D2.8 re-pack + 1px flank prune cluster (0.2649-0.2710) | Already in registry; not new |
| GEMSDOE30 | [gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif](https://github.com/buffedlizard55-lab/GEMSDOE30/blob/3d5bec2af5f29291617f97c9e2dfe443be6f55c3/docs/downloads/gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif) | 0.2600 | MEASURED dot-identical to GEMSDOE25 d2.8 (symdiff 0) | Already in registry; not new |
| GEMSDOE31 | [gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE31/blob/cf13282fcd86290f1539f0a86446c8ba7205a79b/docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif) | 0.2708 | MEASURED dot-identical to GEMSDOE28 solo (symdiff 0) | Already in registry; not new |
| GEMSDOE32 | [gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/012e17b2a115c3c0d5e7885bea625bf9657c99fc/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif) | 0.2778 | B2 (200m) catalogue-flank prune of 0.2708 base; fleet best | Already in registry; not new |
| GEMSDOE33 | [GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif](https://github.com/buffedlizard55-lab/GEMSDOE33/blob/f52533110fe62cd03e77f1228e9e5ecac412c463/docs/downloads/GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif) | 0.2632 | tip/step-over protection + Euler additions | Already in registry; not new |
| GEMSDOE36 | [gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif](https://github.com/buffedlizard55-lab/GEMSDOE36/blob/c9ad59ec6f969ed931d089a03044c1567a633e84/docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif) | 0.2750 | MEASURED exact superset: all 37654 champion dots + 1200 | Already in registry; not new |

**Highest owner-reported value:** GEMSDOE32 at 0.2778 — not independently verified, no organizer receipt.

Other user-reported values, not organizer-confirmed: GEMSDOE28 S21 0.0206; GEMSDOE33 S33 0.0963; GEMSDOE36 KPL36 0.1647. File and score associations remain unverified.

---

## GEMSDOE32: why the reported 0.2778 may look strong

The measured GEMSDOE32 positive-dot set is the GEMSDOE25 d=2.8 set after removing pixels within two pixels of the known catalogue. Wider spacing and a catalogue collar plausibly reduce redundant or low-yield prediction mass under a distance-weighted metric, but the hidden truth and organizer score-to-file receipt are unavailable. The reported 0.2778 cannot be causally explained or independently verified from geometry alone. A genuinely new method might do better, but there is no validated evidence here that it will beat that value.

**Why it cannot be copied:** Copying the GEMSDOE32 file fails the uniqueness rule (>70% of dots within 3 px of a registry raster). This repository's H-GEO-1 file is deliberately constructed outside the catalogue halo to be unique, but its holdout gate failed.

---

## New candidate hypotheses ranked (2026-10-28)

Five new hypotheses were generated (see `knowledge/34_new_hypotheses_2026-10-28.md`):

| Rank | Hypothesis | Layers | Physical signature | Expected ΔDTI | Cost |
|---|---|---|---|---|---|
| 1 (selected) | **H-GEO-1: alteration-front coherence** | GeoDAWN K/Th/U/TC + Th/K, U/K, U/Th ratios | Coherent NE-SW alteration fronts with cross-profile decay; blind faults with alteration halos | 0.000 to +0.005 | Low (existing data) |
| 2 | **H-GEO-2: seismicity-fabric lineaments** | deq_n100a15, ieq_n100a15 from training_features.tif | Directionally persistent seismicity-density ridges at 2-5 km scale; blind active strands | 0.000 to +0.002 | Low-medium |
| 3 | **H-GEO-3: Quaternary volcanic vent alignments** | gdr_volcanic_vents_in_footprint.csv (21 vents) | Vent alignments trace buried fault conduits | 0.000 to +0.003 | Very low |
| 4 | **H-GEO-4: quality-filtered chemistry corridors** | gdr_wellspring_in_footprint.csv (27,092 rows) | Thermal-chemical anomalies in narrow fault-aligned corridors | 0.000 to +0.003 | Medium |
| 5 | **H-GEO-5: multi-scale curvature persistence** | det_elev, lidar relief/curvature bands | Curvature persisting across 0.5-2 km scales; subtle scarps below mapping threshold | 0.000 to +0.004 | Low-medium |

H-GEO-1 was tested on holdout (seeds 600-609) and **failed** the efficacy gate (DTI 0.000 vs 0.000). The other four remain untested.

---

## Research and next decision

The pre-registered [hypothesis ranking and protocol](knowledge/35_preregistration_H-GEO-1_2026-10-28.md) distinguishes H-GEO-1 (alteration-front coherence) from the tested H33-1 and H29-5-PROXY lanes. A matched current-best whole-FID comparison, stronger geographic blocking, and complete registry coverage are still required before a separate weekly-slot selector.

Read the [submission instructions](docs/how-to-submit.html). Official organizer scores, current slot capacity and score-to-file receipts remain unknown. No portal upload was made.

**Limitations:**
- No DrivenData authentication: cannot auto-download training data or upload submissions (verified redirect to login)
- Historical scores are owner-reported, not ORGANIZER-CONFIRMED
- Local HOLDOUT-DTI is not an organizer score or leaderboard prediction
- No new candidate was promoted this session; negative results are deliverables