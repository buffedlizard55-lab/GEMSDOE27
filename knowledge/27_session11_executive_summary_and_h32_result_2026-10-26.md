# 27 — Session 11 Executive Summary: 9 Focus Sites, Why 0.2778 Won, What To Download, and the H32 Negative Result

**Date:** 2026-10-26 · **Lane:** L-S11 (H32) · **Evidence:** `evidence/session11_reaudit.json` (all byte values below recomputed this session), `evidence/h32_e2_holdout_500_509.json`, `evidence/h32_run_card_2026-10-26.json`, `registry/parallel_submission_registry.json`, `registry/live_scores.json`
**Labelling rule:** live numbers are **OWNER-REPORTED** (no organizer receipt exists in this repo; this agent never accesses drivendata.org). Holdout numbers are **HOLDOUT-DTI** (evaluator stated each time). Estimates are **PROJECTION** with method shown. A projection is never a score.

---

## 0. The one obvious download (machine-validated, zero human inspection)

| Question | Answer |
|---|---|
| **Which file do I download and submit?** | ✅ **`docs/downloads/gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif`** (or the single-TIFF `.zip` beside it) |
| Submission name | `27GEMSDOE-H31-DRCG-WL-20261026-cf8e1bbef244` |
| Copyable note (118/140 chars) | `27GEMSDOE H31-1 \| dualRegime MSub+MFull+WLseis+obliq+CELF2.8 B2 37654px \| id cf8e1bbef244 \| unscored validated-promote` |
| SHA-256 (recomputed Session 11) | `2c002b02792419864bd3b29a218e543cb41e3f07b3b57c29ef35c6e39e184bfe` |
| Why is it OK? | All-finite {0.0, 1.0}, EPSG:32611, 3730×3292, 37,654 dots, 0 on catalogue, min catalogue distance 2.24 px (B2) — validator hard-PASS (this format cannot trigger *"Predicted values must be in range [0, 1]"*); frozen holdout gate 5/5 PASS (Session 10, seeds 400–409); unique (below) |
| **Estimated live score (PROJECTION, not a score)** | **~0.235 anchor-transfer** (planning range across methods **0.19–0.30**; §4). Two parallel Session-11 lanes independently computed 0.2348. Honest reading: likely **below** 0.2778. Unscored until submitted |
| **Unique vs all 9 focus sites?** | **YES** — max directed 3-px dot overlap vs the 12 pinned peer rasters = **57.7 %** (50.2 % vs GEMSDOE32's 0.2778 file), ≤ 70 % threshold; max surface Spearman 0.165 ≤ 0.90 (both recomputed Session 11 from fetched peer bytes) |
| Has it been submitted before? | No record of submission/score in `registry/live_scores.json` (status: unscored validated-promote) |
| New file generated THIS session | `docs/downloads/research/gems27-h32-poisson-demag-b2-20261026-1ac69a77008d-allfinite.tif` — **⛔ DO NOT SUBMIT** (failed its frozen holdout gate, §5). It is unique vs peers (46.4 %) and format-valid, but efficacy-negative |
| Second approved-but-superseded file | H30-1 `…801dff07541d…` also passes the machine audit, but it was evaluated on previously-consumed seeds 240–244 and is ranked second by the site's selector note — submit **H31-1 first**; H30-1 only as a separate later slot if desired |

---

## 1. Executive summary of the 9 focus sites (best submission each; bytes re-measured Session 11)

All live scores **OWNER-REPORTED**. `c` = mean 300 m triangular-kernel coverage over the active footprint (recomputed). Overlap = directed fraction of that file's dots within 3 px of GEMSDOE32's dots (recomputed).

| Rank | Site | Best file (registry id) | Live score | Dots N | c | ≤200 m catalogue-collar dots | 3-px overlap vs G32 | Verdict |
|---:|---|---|---:|---:|---:|---:|---:|---|
| 1 | GEMSDOE32 | `g32_h33_2_b2` | **0.2778** ⚠¹ | 37,654 | 0.0592 | 0 | 100 % | Already submitted — DO NOT copy/re-submit |
| 2 | GEMSDOE36 | `g36_anderson` | **0.2750** | 38,854 | 0.0610 | 0 | 97.4 % | = G32 + exactly 1,200 dots (verified) — already submitted |
| 3= | GEMSDOE28 | `g28_h36_1` / `g28_h27_4_r1` | **0.2710 / 0.2708** | 37,660 / 40,199 | 0.0605 / 0.0626 | 2,353 / 2,545 | 95.5 / 95.4 % | `g28_h27_4_r1` = G25 minus ≤1 px collar, exact (verified) |
| 3= | GEMSDOE31 | `g31_h27_4` | **0.2708** | 40,199 | 0.0626 | 2,545 | 95.4 % | In-footprint **identical** to GEMSDOE28's file (verified) |
| 5 | GEMSDOE33 | `g33_h33d` | **0.2632** | 41,865 | 0.0649 | 3,894 | 92.6 % | H19-5-family variant — already submitted |
| 6= | GEMSDOE25 | `g25_d28` | **0.2600** ⚠² | 44,090 | 0.0668 | 6,436 | 88.2 % | Unpruned d = 2.8 parent of G28/G31/G32 (verified) |
| 6= | GEMSDOE30 | `g30_d28` | **0.2600** ⚠² | 44,090 | 0.0668 | 6,436 | 88.2 % | In-footprint **identical** to GEMSDOE25's file (verified) |
| 8 | GEMSDOE24 | `g24_d15` | **0.2477** | 60,069 | 0.0751 | 8,769 | 88.5 % | Over-dense d = 1.5 — already submitted |
| 9 | GEMSDOE27 (this repo) | Slot 1 `g27_tv2_d15`; H29-S `511898747886` | **0.2449 / 0.2190** | 61,328 / 37,654 | 0.0770 / 0.0527 | 8,875 / 0 | 86.7 / 56.1 % | Both already submitted. H29-S is the only top file **outside** the H19-5 clone cluster |

⚠¹ **Irregularity (flagged, not smoothed over):** `registry/parallel_submission_registry.json` records G32's 0.2778 as *"OWNER-REPORTED in task; peer audit calls file UNSCORED"*. No organizer receipt exists here for any score. Treat 0.2778 as the owner's reported fleet best, not an organizer-confirmed value.
⚠² G25/G30 score-to-file attribution is flagged unresolved in peer sources — and Session 11 verified the two files are pixel-identical in-footprint, so they cannot have different scores; both are listed 0.2600.

**Bottom line across the 9 sites:** every historical 0.2449–0.2778 file except GEMSDOE27's H29-S is one H19-5 pixel family (86.7–100 % 3-px overlap with G32) and every one has already been submitted. None is a legitimate "new" submission. The only machine-approved, unscored, unique file in the focus fleet is this repo's **H31-1** (§0).

## 2. Why did GEMSDOE32 score 0.2778? (verified line by line from bytes)

Session 11 re-derived the entire ladder from fetched peer rasters + the hash-pinned catalogue (`labels.tif` sha256 `7ba308cc…`):

1. **`G32 ≡ G25(d=2.8) ∧ (EDT(catalogue) > 2 px)` — exact, symmetric difference 0.** Likewise `G28/G31 ≡ G25 ∧ (EDT > 1 px)` exact, and `G36 = G32 ∪ {1,200 dots}` exact (0 dots of G32 missing from G36).
2. So the 0.2600 → 0.2708 → 0.2778 progression is **pure catalogue-collar deletion**: removing 3,891 dots at ≤100 m then 2,545 more at 100–200 m from *already-catalogued* faults. Those dots are detector halo echo around masked known faults: they can earn almost no TP_w (truth pixels there are masked/known) but pay full FP_w. At DTI ≈ 0.278 a dot subset only helps if ΔTP_w/ΔFP_w > 0.2·DTI/(1−0.2·DTI) ≈ 0.0588 (`metric.inclusion_threshold`); the collar dots' measured live yield is ≈ 0, so deleting them is free score.
3. The base they prune (H19-5, 0.1922 solid) already encodes the two earlier wins: multi-line corroboration (a ridge must be confirmed by a second physical domain, killing volcanic-rim/pluton-contact mimics) and d = 2.8 px Poisson dotting (0.1922 → 0.2477 at d = 1.5 → 0.2600 at d = 2.8), which keeps ≈ 89 % of a solid line's kernel credit at ~⅓ the FP cost.
4. Adding dots back hurts symmetrically: G36's +1,200 PINN dots yielded ≈ 0.015 < 0.0588 marginal efficiency, diluting 0.2778 → 0.2750.

**PhD judgement:** 0.2778 is not a discovery breakthrough; it is the *emission-geometry optimum of one detector family* (H19-5 ridges × d = 2.8 × B2). Its remaining headroom by rearrangement is ~zero — every rung of that ladder has been measured live. Beating it requires **new ranking information** (different physics/features), which is exactly what H29-S/H31-1 attempt (hydrothermal + piedmont + seismic-fabric, 5.79× blind concentration at only 56 % overlap with G32) and what H32 attempted and failed (§5).

## 3. Can we generate something scoring higher than 0.2778?

Honest answer: **not established, and the best-anchored estimate says no.** H31-1's projections (§4) span 0.19–0.30 across methods; only the 6.5×-concentration sensitivity end (GEMSDOE32-level concentration, not demonstrated live by this detector family) exceeds 0.2778, while the anchor-transfer estimate both Session-11 lanes computed independently is 0.2348. Catalogue-internal HOLDOUT-DTI cannot settle this — H29-S already proved holdout rank ≠ live rank calibration (holdout-best surface, live 0.2190). The only measurement is one DrivenData slot. Claims of beating the owner's stated external highs (0.3195 in one prompt snapshot; 0.4413 in another — **irregularity: the two prompt values conflict and neither has a receipt here**) are not supported by any evidence in this repo.

## 4. How the estimated scores were computed (PROJECTION — verify me)

Two independent, fully stated methods (`scripts/reaudit_session11.py`):

- **Concentration model:** DTI = TP/(0.8|G| + 0.2N + 0.2(1−ρ)TP), TP = concentration × c × |G|, with **assumptions** |G| = 12,226 (repo-inferred hidden-truth size, unconfirmed), ρ = 1.38 (repo-fitted). c and N are exact from bytes. Sanity: at H29-S's measured 5.8× concentration the model gives 0.2193 vs its OWNER-REPORTED live 0.2190; at G32's 6.5× it gives 0.2778 by construction of the fit — so the sensitivity band, not any point value, is the honest output.
- **Holdout-ratio anchor (single anchor, weak):** H29-S live 0.2190 / its HOLDOUT-DTI 0.044116 inside the H31 experiment = 4.96×; × H31-1 HOLDOUT-DTI 0.047302 → **0.235**.

| File to download | Status | Estimated live score (PROJECTION) | Unique vs 9 focus sites? |
|---|---|---:|---|
| ✅ `gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif` | **OK TO DOWNLOAD & SUBMIT** (unscored) | 0.228 (5.0×) – **0.266 (5.8×)** – 0.299 (6.5×); ratio method 0.235 | **YES** — max 57.7 % 3-px vs peers, 50.2 % vs G32 |
| `gems27-h30-1-updip-hydrothermal-b2-35k-20261025-801dff07541d-allfinite.tif` | Machine-approved, second priority (consumed-seed caveat) | 0.213 (5.0×) – 0.248 (5.8×) – 0.279 (6.5×) | YES — max 43.2 % vs peers |
| ⛔ `research/gems27-h32-poisson-demag-b2-20261026-1ac69a77008d-allfinite.tif` | **DO NOT SUBMIT** (this session's negative) | Not estimated for submission (gate failed; concentration sensitivity would be 0.22–0.29 but holdout says its ranking is *worse*, so quoting it would mislead) | YES vs peers (46.4 %); NO vs strict repo screen (85.5 % vs an Arm-D repo raster) |
| Any 0.2449–0.2778 focus-site file | Already submitted | Their OWNER-REPORTED scores are known; re-submission adds nothing | NO — 86.7–100 % clones of each other |

## 5. This session's new experiment: H32 Poisson demagnetization — NEGATIVE (deliverable)

Preregistered in `knowledge/26` before any run. E1 canary clean (max direction-invariant AUC **0.546** ≤ 0.90). E2, fresh seeds 500–509, 40 cells, **118,039** withheld positives, evaluator `gems27.metric.dti_binary v1 + buffered quadrant holdout (6 px)`, identical blind B2 Poisson-2.8 emission (HOLDOUT-DTI):

| Arm | Pooled HOLDOUT-DTI | NW | NE_LidarGapHeavy | SW | SE |
|---|---:|---:|---:|---:|---:|
| B (base-32) | 0.03647 | 0.03351 | 0.04888 | 0.02707 | 0.03880 |
| D (+ subsurface-15) | **0.03922** | 0.03767 | 0.05038 | 0.02693 | 0.04507 |
| P (D + H32 Poisson-8) | 0.03573 | 0.03170 | 0.04698 | 0.02493 | 0.04153 |

P−D = **−0.00349**, 95 % CI **[−0.00477, −0.00223]**, 1/10 seeds, 0/4 folds → **0/5 frozen clauses pass. Verdict: negative; no tuning; seeds consumed.** (Useful by-product: D−B = +0.00275, CI [+0.00162, +0.00397], 10/10 seeds — the subsurface transforms replicate again on fresh seeds.)
Interpretation (labelled as interpretation): catalogue faults are predominantly magnetically-expressed basement structures, so "gravity edge without magnetic edge" features mostly fire on the named mimics (carbonate–granite contacts, reversely-magnetised tuffs) and dilute the GBM. The instrument cannot distinguish "signal exists only for truly blind faults" from "no signal" — which is precisely why the frozen gate, not optimism, decides: **no slot.**

## 6. Untried hypotheses remaining (ranked; full table in `knowledge/26` §1)

1. **H31-3** MT clay-cap × asymmetric graben-margin cross-strike pairing (hash-pinned bands; fresh seeds ≥ 510).
2. **H29-5** Canyon-mouth knickpoint/fan-apex collinearity (existing DEM/LiDAR bands).
3. **H27-16** Official GDR #1391 paleo-sinter + 2 m probe + Quaternary-volcanics layers — free official source `https://gdr.openei.org/submissions/1391` (DOI 10.15121/1881483), **not obtainable from this sandbox** (host outside allowlist); needs an authorized fetch + SHA-256 pins before it is viable.

## 7. How to submit (no human inspection step)

1. Download the H31-1 `.tif` (or `.zip`) from `docs/downloads/` (site first-screen buttons).
2. DrivenData → *New submission* → choose the file → paste the note from §0 → submit. (Competition: https://www.drivendata.org/competitions/306/competition-doe-gems/ · rules PDF: https://docs.nlr.gov/docs/fy26osti/96647.pdf · reference solution: https://github.com/drivendataorg/gems-prize-reference-solution)
3. Record the returned score as a **new** row in `registry/live_scores.json` with the file SHA-256; never edit a score onto different bytes.

## 8. Run card (H32, protocol §5)

```json
{
  "hypothesis": "H32: Poisson-theorem demagnetization-residual features expose hydrothermally demagnetised blind fault conduits (gravity edge persists, RTP magnetic edge erased) missed by coincident-edge detectors and by the surface-rupture catalogue.",
  "mechanism": "8 label-free features (local sigma=15px gravity-on-RTP regression residual + gradients, grav-minus-mag edge contrasts, gravity-only coherence, pseudogravity-mismatch gradient) added to base-32 + subsurface-15 HistGB OOF detector; blind B2 (>200 m) ridge-NMS + priority Poisson-disk 2.8 px emission, 37,654 dots.",
  "named_non_fault_mimic": "Non-magnetic Paleozoic carbonate faulted against granite; reversely magnetised Tertiary ash-flow tuffs; RTP flight-line levelling seams.",
  "holdout_dti": "HOLDOUT-DTI pooled P=0.03573 vs D=0.03922 vs B=0.03647 (gems27.metric v1, buffered quadrant holdout, seeds 500-509, 40 cells, 118,039 withheld positives); P-D=-0.00349, 95% CI [-0.00477,-0.00223], 1/10 seeds, 0/4 folds; canary max AUC 0.546",
  "correlation_overlap_vs_registry": "Directed 3-px overlap max 0.4644 vs 12 pinned peers (0.4114 vs GEMSDOE32); strict repo screen max 0.8553 (vs Arm-D repo raster) FAILS 0.70; surface Spearman max |rho|=0.718 <= 0.90",
  "raster_sha256": "8ff3b255b9399871f5bb034da289cfb5c7c0cddda97cf77d3371c3b79fee60ed",
  "validator": "allfinite hard-PASS: single-band float32, EPSG:32611, 3730x3292, exact {0,1}, 0 NaN/Inf, nodata=None; 0 dots on catalogue; min catalogue distance >2 px",
  "submission_name_and_note": "RESEARCH ONLY - no submission name authorized. Note on file (113 chars): 27GEMSDOE H32 PoissonDemag B2 37654px HOLDOUT-DTI P-D -0.0035 | id 1ac69a77008d | RESEARCH NEGATIVE DO NOT SUBMIT",
  "verdict": "negative"
}
```

**Selector note (protocol §6):** this session does not spend a weekly slot. The pre-existing machine-approved H31-1 file (§0) is presented for the owner's separate selector decision; H32 must not be submitted.

---

## Post-merge addendum (parallel Session-11 lanes, PRs #31/#32 merged to main first)

Two parallel sessions from the same prompt merged before this lane: PR #31 (`knowledge/26_session11_review_and_score_estimate_2026-10-26.md`, audited estimate **~0.235 PROJECTION, planning range 0.19–0.26**) and PR #32 (`EXECUTIVE_SUMMARY.md`). Conclusions converge with this lane on every material point: H31-1 `cf8e1bbef244` is the one approved unique download; its anchor-transfer projection is **0.2348** (computed independently by both lanes: 0.2190 × 0.047302/0.044116); honest reading is likely below 0.2778. Knowledge-file number 26 now covers two different files from the parallel lanes (this lane's H32 preregistration vs PR #31's review) — cite by full filename. Neither parallel lane generated a new TIFF, so this lane's H32 uniqueness screen is unaffected; H32 was additionally cross-checked here against H31-1 (directed 3-px overlap 52.9 % H32→H31, 50.1 % H31→H32 — not duplicates; `evidence/session11_reaudit.json`).
