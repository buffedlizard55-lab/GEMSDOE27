# Lane L-DCONFIRM (2026-10-25, second session): hypotheses, preregistration, and the 0.2778 answer

**Labelling.** Leaderboard numbers are **OWNER-REPORTED** (task prompt / owner sites; no
DrivenData receipt exists in this repo). Raster quantities recomputed this session are
**MEASURED (2026-10-25B)**. Detector numbers from this session's runs will be **HOLDOUT-DTI**
(evaluator `gems27.metric` v1, α=0.2 β=0.8, 300 m triangular kernel). No number here is
ORGANIZER-CONFIRMED. The prompt again contains no delimited "single method paragraph", so this
session declares its lane in §2 (same irregularity class as IR-2026-10-25-01; new entry added).

## 1. Why 0.2778 (GEMSDOE32 `h33-h33-2-b2`) is the family best — re-verified pixel-exactly

MEASURED (2026-10-25B; registry peers fetched at the pinned commits in
`registry/parallel_submission_registry.json`, catalogue = `labels.tif` sha256 `7ba308cc…`):

| file (site) | OWNER-REPORTED | dots | ≤1 px | (1,2] px | med. d(cat) |
|---|---:|---:|---:|---:|---:|
| g24 dotted H19-5 d1.5 (24) | 0.2477 | 60,069 | 5,355 | 3,414 | 14.9 |
| GEMSDOE27 T-v2 on d1.5 (27) | 0.2449 | 61,328 | 5,413 | 3,462 | 14.1 |
| dotted H19-5 d2.8 (25 = 30) | 0.2600 | 44,090 | 3,891 | 2,545 | 15.0 |
| h33d analog tip-stepover (33) | 0.2632 | 41,865 | 1,377 | 2,517 | 16.6 |
| H27-4 r1-solo d2.8 (28 = 31) | 0.2708 | 40,199 | 0 | 2,545 | 17.7 |
| Anderson PINN (36) | 0.2750 | 38,854 | 0 | 0 | 19.2 |
| **h33-2-b2 (32)** | **0.2778** | **37,654** | **0** | **0** | **19.6** |

Pixel-exact chain (both equalities return `True` this session):
`d2.8 & (d_cat>1) == r1-solo` (removes 3,891) and `r1-solo & (d_cat>2) == h33-2-b2`
(removes a further 2,545). The winning step is a *deletion*, not new geology. Every one of the
12 registry rasters has 87–100 % of its dots within 3 px (Euclidean) of the 0.2778 dots: the
whole top family is one dot field (H19-5) re-thinned/pruned. GEMSDOE27's own T-v2 addition is
the family's one live A/B regression (0.2449 < its 0.2477 parent, OWNER-REPORTED).

**Mechanism (MODEL, from the official metric).** DTI = TP/(0.2·TP+0.2·FP+0.8·|G|). Deleting a
dot set raises DTI iff its credit efficiency dTP/dFP < 0.2·DTI/(1−0.2·DTI) ≈ 0.057 at DTI
0.2708. Dots 100–200 m from a catalogued trace are the detector's echo of that known fault
(dip offset + 100 m quantisation); catalogue pixels are masked from scoring, so an echo dot
earns credit only if a *different* hidden fault lies inside its 300 m kernel — rare. This repo
measured the r≤1 band's OOF efficiency at 0.0034, 15× below break-even. Each family step
(0.1922 solid → 0.2477 dotted → 0.2600 d2.8 → 0.2708 r1 → 0.2778 B2) deletes near-zero-credit
FP mass; GEMSDOE36's independent PINN converging on B2 + ~38 k dots is cross-method evidence
the emission optimum (≈38 k dots, ≥200 m off-catalogue, ≥280 m spacing) is real.

**Can we beat 0.2778?** Three facts bound the answer. (i) Emission surgery on H19-5 is nearly
exhausted (family credit concentration plateaued at 5.3–5.7× blind) *and* is forbidden here by
the uniqueness rule (any H19-5 edit is >70 % within 3 px of a registry raster). (ii) The one
replicated source of *new* detector information in this repo is subsurface physics **on top
of** the full stack: Lane L-2026-10-25 arm D (full-32 + 15 subsurface transforms) beat the
full-32 control by HOLDOUT-DTI +0.0045 [+0.0003, +0.0090], 15/20 cells (seeds 200–204), while
subsurface-*only* failed (−0.0262). H28-1's related potential-edge increment independently
passed its gate (+0.0029, seeds 140–149). (iii) The prompt's leader is stated as both 0.3195
and 0.4413 (unresolved, IR-2026-10-25-02): at |G|≈12.6 k (sibling lattice calibration,
unconfirmed) 0.3195 needs weighted recall ≈0.48 at a 38 k-dot budget (family ≈0.43–0.50 —
within reach of a better detector), whereas 0.4413 needs ≈0.68 (+40–55 % relative — a
different detector class, e.g. supervised 1 m-DEM learning, not emission edits). Judgement:
P(beat 0.2778 | confirmed hybrid increment at B2/38 k) ≈ 0.35–0.5; P(reach 0.4413 this way)
< 0.05. This session therefore runs the confirmatory hybrid lane D was deferred as, augmented
by three untried transform families (§3), under a selection/confirmation seed split (§4).
Any file that does not clear every gate is generated but badged **⛔ DO NOT SUBMIT**.

## 2. LANE L-DCONFIRM (the single method paragraph for this session)

> **Hybrid augmented detector at the live emission optimum.** A quadrant-OOF / full-fit
> HistGradientBoosting detector (template instrument, unchanged hyperparameters) on the
> 32-band cached stack plus label-free transforms: the 15 subsurface transforms of Lane
> L-2026-10-25 (`gems27.subsurface_features`, frozen) and 8 new transforms
> (`gems27.dip_rad_features`: 3 dip-offset doublet, 3 radiometric alteration-front edges,
> 2 scarp-polarity pairs; §3). Emission: 1-px ridge NMS of the detector surface,
> priority-ordered Poisson-disk placement at ≥2.8 px, B2 exclusion (no dot within 200 m of a
> visible catalogue fault), fixed 38,000-dot budget, binary {0,1}, written all-finite
> (zeros outside, nodata=None) by the shared writer. Arms: **B** = full-32 (control),
> **D** = full-32+15 (fallback candidate), **E** = full-32+15+8 (primary candidate).
> Exactly one candidate (E preferred, else D) is selected on seeds 210–214 and confirmed
> against B on untouched seeds 215–224; only a confirmed, uniqueness- and validator-passing
> arm may be badged OK TO SUBMIT. Nothing outside this paragraph is in-lane.

## 3. Five candidate hypotheses, ranked (expected HOLDOUT-DTI Δ is a prior, not a score)

| # | Hypothesis | Layers | Signature targeted | Why a catalogue-missing fault | Differs from this repo | Prior ΔDTI / cost |
|---|---|---|---|---|---|---|
| 1 ★LANE | Hybrid sufficiency, confirmatory: subsurface transforms + dip-doublet + radiometric fronts + polarity pairs **augment** (not replace) the full stack | 32 prepared bands; RTP/gravity/strain/cond/depth/seismicity (15 frozen transforms); `geodawn_rad_u8` K + `geodawn_extensions_u8` ThK/UK (u8, hash-pinned); lidar step/lappos/lapneg/upface/downface | (a) potential edge with a scarp ridge in its 2–6 px annulus (and vice-versa; basement-step variant) = one dipping fault seen in two physics at dip offset; (b) gradient-magnitude fronts of radiometric ratio grids = alteration boundaries; (c) lappos↔lapneg / upface↔downface adjacency at 1–3 px = signed scarp polarity | Catalogue scope = young surface rupture; a blind/dipping fault's subsurface edge continues under alluvium past where its scarp dies, fluids alter rock along it, and its subdued scarp keeps signed polarity after amplitude fades | D was a *control*, never a preregistered primary or shipped; doublet annulus pairing, ratio-*front* edges (values were tried, +0.0007 PR-AUC, refuted) and polarity pairing exist nowhere in repo/sibling docs | vs B: +0.003…+0.008 (D measured +0.0045 on seeds 200–204; new 8 add −0.002…+0.004) / low |
| 2 | Pure dip-offset emission: dots **on** the potential-field edge where the paired scarp has died under alluvium | RTP/gravity/depth edges × lidar scarp annulus *absence* along-strike | Edge continuation beyond scarp termination | Directly targets buried strike-extensions the surface catalogue cannot list | Emission-side rule, not a detector feature; but catalogue-internal holdout truth sits on surface traces, so the proxy is structurally biased against it (knowledge/10) — not falsifiable here without a live slot | unknown (proxy-blind) / med — deferred |
| 3 | Radiometric-front standalone detector (fronts replace lidar) | rad/ext u8 grids only | Ratio-front ridges | Alteration along permeable buried structures | Front geometry untried; standalone regime-exclusion already failed for subsurface-only (arm A), so prior is poor | −0.02…+0.002 / low — not run standalone |
| 4 | Quaternary vent-alignment corridors | GDR vents in footprint (**21 points**, MEASURED local CSV) + volcanic polygons | ≥3-vent collinear alignments (Hough/RANSAC) | Dikes exploit fault permeability | Point-distance tried (+0.0005, refuted); alignment geometry untried — but 21 points give negligible statistical power | 0…+0.002 / med — deferred (power) |
| 5 | Hydrothermal chemistry-gradient corridors (H28-5) | GDR well/spring CSV (27,092 rows, owner-mirror hash-pinned; **official GDR bytes not re-hashed from source** — sandbox cannot reach gdr.openei.org) | Spatially coherent temp/geothermometer *gradient* ridges after QA/dedup | Upflow along untraced permeable faults | Isotropic distance features refuted; gradient corridors untried. Sampling-density bias is a severe mimic. Named free official source: GDR #1391 (https://gdr.openei.org/submissions/1391) — **not obtainable from this sandbox's allowlist**, so not viable as confirmatory this session | 0…+0.003, high uncertainty / high — blocked on provenance |

Ranking rule: prior Δ × P(holdout can falsify) ÷ cost. Non-fault mimics for the lane:
basin-margin lithologic contacts (mag edge + topographic break co-occur naturally),
radiometric provenance/levelling seams, terrace risers and channel banks (polarity pairs),
clay-cap conductivity. The holdout + canary exist to price exactly these.

## 4. Frozen gates (written before E1–E3 code runs; ≤3 experiments)

* **Holdout (template, unchanged):** quadrant folds; whole 8-connected catalogue segments
  hidden at 20 % per quadrant; catalogue-derived quantities (B2 distance) from *visible*
  faults only; visible faults masked pixel-exactly; 6-px buffered scoring ring excluded;
  pooled DTI = ΣTPw/(ΣTPw+0.2ΣFPw+0.8ΣFNw). Per-fold budgets = 38,000 × footprint share.
* **E1 canary:** each of the 8 new transforms alone vs seed-210 hidden segments; any AUC
  > 0.90 stops the line as leakage.
* **E2a selection (seeds 210–214, 20 cells):** arms B/D/E. Candidate = E if pooled(E)>pooled(B)
  and pooled(E) ≥ pooled(D)−0.001; else D if pooled(D)>pooled(B); else none → **negative, stop**.
* **E2b confirmation (seeds 215–224, 40 cells, untouched until E2a closes):** candidate vs B.
  **PROMOTE** iff pooled Δ>0 AND mean paired Δ ≥ +0.002 AND ≥3/4 fold-mean Δ>0 AND ≥6/10
  seed-mean Δ>0. 95 % CI by deterministic cell bootstrap (2,000 draws, seed 0).
* **Uniqueness (both required, checked on OOF surface before placement AND final dots):**
  Spearman(OOF prob, σ=3 density of each registry raster) < 0.90; directed fraction of final
  dots within 3 px Euclidean of any single registry raster < 0.70. Registry = 12 pinned peer
  rasters (GEMSDOE24/25/27/28/30/31/32/33/36) + this repo's shipped candidates. Failure =
  duplicate lane: log, badge ⛔, stop.
* **Validator:** shared `verify_geotiff` hard-PASS on the all-finite primary (no NaN inside
  footprint, values in [0,1] over all 12,279,160 cells, EPSG:32611 / 3730×3292 / transform
  match, single-band float32); additionally 0 dots on catalogue, 0 dots with d(cat)≤2.
* **`ok_to_submit` = confirmation PASS ∧ uniqueness PASS ∧ validator PASS** — computed by the
  build script into the run card; the website badge reads that JSON. No human inspection step.
  A generated-but-failing file goes to `docs/downloads/research/` badged ⛔ DO NOT SUBMIT.
* Seeds used historically: 120–169, 200–204. 210–224 are fresh. No post-hoc tuning, no re-runs
  on the same seeds after seeing results.
