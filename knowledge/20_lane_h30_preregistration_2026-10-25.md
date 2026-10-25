# Lane L-H30 preregistration — frozen 2026-10-25 BEFORE any H30 gate run

**Labelling (parallel-run protocol §3).** Leaderboard numbers are **OWNER-REPORTED**
(prompt / owner sites; no ORGANIZER-CONFIRMED receipt exists in this repo). Detector
numbers from this session will be **HOLDOUT-DTI** (evaluator `gems27.metric` v1,
alpha 0.2, beta 0.8, 300 m triangular kernel) with withheld-positive counts and 95 % CIs.
Raster facts recomputed this session are **MEASURED (2026-10-25, this session)**.
A projection is never written as a score.

## 0. Previous next steps done first (Pass 1, measured this session)

Session 8 (`knowledge/18`) and the readiness audit (`knowledge/19_readiness…`) required:
restore the hash-pinned `data_cache/`, re-run prepare + download verification, then choose
one untried lane with fresh seeds. Done before this preregistration, no gate run yet:

- `scripts/restore_data.py`: all 16 pinned files + assembled `training_features.tif` OK
  (SHA-256 verified; e.g. template `2176d08e…`, labels `7ba308cc…`, training `4371c82e…`).
- `scripts/prepare_data.py`: rebuilt the 32-band label-free stack,
  `data_cache/prepared/features.npy` sha256 `83ed2704ee2de03cf8b1c8f2966fcf71813501df9…`,
  identical to the value recorded in `evidence/data_preparation.json` history.
- `scripts/fetch_parallel_registry.py`: 12 pinned peer rasters OK (incl. `g32_h33_2_b2`
  sha256 `c55bafc47005…`).
- `pytest -q`: **107 passed**. `scripts/verify_downloads.py`: **0 failure(s)**.

## 1. Why h33-h33-2-b2 (0.2778, GEMSDOE32) is the family best — re-verified line by line

MEASURED this session from the pinned peer bytes (catalogue `labels.tif` sha256 `7ba308cc…`):

| file (site) | OWNER-REPORTED | dots | ≤1 px of cat. | (1,2] px | median d(cat) px | dots within 3 px of 0.2778 dots |
|---|---:|---:|---:|---:|---:|---:|
| g24 dotted H19-5 d1.5 (24) | 0.2477 | 60,069 | 5,355 | 3,414 | 14.87 | 88.5 % |
| g27 T-v2 on d1.5 (27) | 0.2449 | 61,328 | 5,413 | 3,462 | 14.14 | 86.7 % |
| dotted H19-5 d2.8 (25 = 30, byte-identical dot sets) | 0.2600 | 44,090 | 3,891 | 2,545 | 15.00 | 88.2 % |
| g28 h32-1 tip/Euler (28) | 0.2649 | 42,294 | 1,542 | 3,095 | 16.12 | 91.6 % |
| H27-4 r1-solo d2.8 (28 = 31, byte-identical) | 0.2708 | 40,199 | 0 | 2,545 | 17.69 | 95.4 % |
| g28 h36-1 rung-3.0 r1 (28) | 0.2710 | 37,660 | 0 | 2,353 | 17.72 | 95.5 % |
| g28 h38-1 hf-Euler r1 (28) | 0.2707 | 37,860 | 0 | 2,353 | 17.69 | 95.0 % |
| g33 h33d analog tip-stepover (33) | 0.2632 | 41,865 | 1,377 | 2,517 | 16.64 | 92.6 % |
| Anderson PINN (36) | 0.2750 | 38,854 | 0 | 0 | 19.24 | 97.4 % |
| **h33-2-b2 (32)** | **0.2778** | **37,654** | **0** | **0** | **19.65** | 100 % |

Pixel-exact (both `True` this session): `d2.8 & (d_cat>1) == r1-solo` (deletes 3,891 dots)
and `r1-solo & (d_cat>2) == h33-2-b2` (deletes a further 2,545). PhD-level mechanism
(MODEL, from the official metric in `src/gems27/metric.py`):
DTI = TPw/(0.2·TPw+0.2·FPw+0.8·|G|), so deleting a dot set raises DTI iff its credit
efficiency dTP/dFP < 0.2·DTI/(1−0.2·DTI) ≈ 0.057 at DTI 0.2708. Dots 100–200 m from a
catalogued trace are the detector's echo of that known fault (dip offset + 100 m
quantisation); catalogue pixels are masked from scoring, so an echo dot earns credit only
if a *different* hidden fault lies inside its 300 m kernel. This repo measured the r≤1
band's OOF efficiency at 0.0034 (≈15× below break-even, HOLDOUT-DTI, `evidence/oof_…`).
Each family step 0.1922 → 0.2477 → 0.2600 → 0.2708 → 0.2778 is therefore pure
false-positive-mass deletion on one frozen detector (H19-5), and GEMSDOE36's unrelated
PINN converging on B2 + ~38 k dots is cross-method evidence that the emission optimum
(≈38 k dots, ≥200 m off catalogue, ≥280 m spacing) is real and detector-independent.

**Can 0.2778 be beaten?** Judgement (MODEL/prior): not by more emission surgery on H19-5
(family credit concentration plateaued at 5.3–5.7× blind, `evidence/live_inversion.json`;
any H19-5 edit is also a protocol duplicate, 87–100 % within 3 px). Only better *ranking*
from new detector information at the same B2/38 k emission can beat it. This repo's only
replicated ranking increment is Arm D (32-band + 15 subsurface transforms:
HOLDOUT-DTI +0.00857 [+0.00513, +0.01249] seeds 210–214 and +0.00760
[+0.00489, +0.01038] seeds 215–224 vs the 32-band control). Arm D is therefore the
**control to beat** in this lane, not the candidate: re-emitting D would copy the
H29-1/L-DCONFIRM family (87.5 % cross-session dot overlap). The prompt's leaderboard
highs 0.4413 vs 0.3195 conflict and remain unverified (IR-2026-10-25-02; the agent does
not access drivendata.org).

## 2. LANE L-H30 (the single method paragraph for this session)

> **Dip-advected / gap-flanked hybrid detector at the live emission optimum.**
> The shared quadrant-OOF / full-fit HistGradientBoosting instrument
> (`gems27.oof_detector`, unchanged) on the cached 32-band stack + the frozen 15
> subsurface transforms (`gems27.subsurface_features`), augmented by exactly one of two
> new label-free transform families: **H30-1 dip advection** (potential-field and
> basement-step edge strength sampled *down-dip* — along the depth-to-basement gradient
> by a depth-scaled offset `clip(depth·cot(dip)/100 m, 0, 8 px)`, dip ∈ {50°, 70°} — so
> deep-edge evidence is relocated to the surface-trace position a per-pixel detector
> cannot otherwise learn) or **H30-2 gap flanking** (min of RTP/gravity edge strength
> sampled ±6/±12 px along four strikes, max over strikes: along-strike continuation
> evidence where the local edge dies under cover); emission is ridge NMS → B2 exclusion
> (no dot within 2 px of a *visible* catalogue fault) → priority Poisson-disk ≥2.8 px at
> 38,000 dots, binary — with **H30-3 soft rank-taper** (76,000-dot support, values
> `1−k/N` by descending-detector-probability rank, rescaled to effective mass 38,000)
> admitted as the emission variant of the D control surface. Exactly one candidate is
> selected on seeds 240–244 and confirmed against the Arm-D control on untouched seeds
> 245–254; only a confirmed, canary-clean, protocol-unique, validator-passing candidate
> may be badged OK TO SUBMIT. Nothing outside this paragraph is in-lane.

## 3. Five candidate hypotheses, ranked (priors are MODEL, never scores)

| # | Hypothesis | Layers | Physical signature | Why it should catch a catalogue-missing fault | How it differs from this repo | Named non-fault mimic | Prior ΔHOLDOUT-DTI vs D / cost |
|---|---|---|---|---|---|---|---|
| 1 ★ | **H30-1 dip-advection correction** | `rtp`, `iso_grav_anom`, `depth_to_base_surf` (label-free; depth 5–95th pct 6–1,881 m measured this session) | Edge strength relocated up-dip by `depth·cot(dip)`: a dipping fault's basement/potential-field edge sits hundreds of metres down-dip from its surface trace | Buried/pre-Quaternary dipping faults with no young scarp: their only expression is the offset deep edge; a per-pixel model scores the pixel *over the deep edge*, not over the trace, losing the 300 m kernel credit | H29-2 was proposed but never implemented; the L-DCONFIRM dip *doublets* only paired an edge with an undirected scarp annulus (and hurt, arm E). Directed depth-scaled advection along the depth gradient exists nowhere here | Dipping lithologic contacts; basin-margin basement steps without faulting | 0…+0.006 / low-med |
| 2 ★ | **H30-2 along-strike gap flanking** | RTP + isostatic gravity edges (σ=2) | `max_strike min(E(x−d·u), E(x+d·u))`, d = 6/12 px: collinear edge segments bounding a low-amplitude interval | Where alluvium thickens along strike the potential-field edge of one continuous buried fault fades out and resumes; the catalogue (surface-rupture scope) and a local detector both stop at the fade | Addendum-D directional bands averaged *lidar* layers along strike (refuted, PR-AUC +0.0010); min-of-flanks at fixed lags on *potential-field edges*, targeting interruption rather than continuity, is untried (cf. `knowledge/19_readiness…` priority 1) | Lithologic contacts interrupted by cover; chance collinearity of unrelated segments | 0…+0.004 / low-med |
| 3 ★ | **H30-3 soft rank-taper emission** | Arm-D OOF/full-fit probability surface only | 2× support at graduated p∈(0,1] under the exact soft DTI (`metric.dti_exact`), effective mass fixed at the binary optimum | Second-tier candidates for uncatalogued structures can be hedged at fractional FP cost instead of the binary all-or-nothing cut | Every scored family file is binary; H29-3 was proposed, never tested. Emission-side only, evaluated on the D surface | None (representation change); risk is credit dilution — the 300 m kernel may already be the optimal hedge | −0.004…+0.005 / low |
| 4 | H28-5 hydrothermal chemistry-gradient corridors | GDR #1391 well/spring CSV (owner-mirror pinned `122718e6…`) | QA'd temperature/geothermometer contrasts along short gradients | Upflow along permeable untraced faults | Distance-only features refuted (+0.0005); gradient corridors untried | Sampling density; groundwater transport | 0…+0.003 / med — **deferred: official GDR raw bytes not obtainable/re-hashed in this sandbox (allowlist excludes gdr.openei.org)** |
| 5 | H27-16 official GDR layers (sinter/2 m probes/volcanics) | GDR #1391 packages | Independent thermal/volcanic surface evidence | Blind permeable structures without scarps | Layers absent from checkout | Non-fault heat sources; volcanic contacts | 0…+0.006 / high — **deferred: same data gate as #4** |

★ = arms frozen for this session's single selection experiment. Ranking rule: prior Δ ×
falsifiability on the buffered holdout ÷ cost. Hypotheses 4–5 are named with their free
official source (https://gdr.openei.org/submissions/1391) and are **not** viable for a
confirmatory run until those bytes are hash-verified from the source.

## 4. Frozen transforms (implemented in `src/gems27/dip_gap_features.py` after this file)

All transforms are deterministic functions of the pinned rasters only — no labels, no
catalogue distance — percentile-ranked within the footprint to [0,1] float32 in
row-major footprint order (shared `_fill`/`_grad_mag`/`_rank01` from
`gems27.subsurface_features`).

- Edge ranks: `E_rtp = rank01(|∇(rtp, σ=2)|)`, `E_grav = rank01(|∇(iso_grav_anom, σ=2)|)`,
  `E_depth = rank01(|∇(depth_to_base_surf, σ=3)|)` as full grids (0 outside footprint).
- Dip field: `u = ∇(depth, σ=5)/|∇(depth, σ=5)|` (toward deeper basement = down-dip for a
  normal fault whose hanging wall subsides); `r_dip = clip(max(depth,0)·cot(dip)/100, 0, 8)` px.
  H30-1 features (sampled by bilinear `map_coordinates` at `x + r_dip·u`, then ranked):
  `dipadv_rtp_dip50`, `dipadv_rtp_dip70`, `dipadv_grav_dip50`, `dipadv_grav_dip70`,
  `dipadv_depth_dip50` (5 features, cot50°=0.83909963, cot70°=0.36397023).
- H30-2 features: strikes u ∈ {(0,1),(1,0),(1,1)/√2,(1,−1)/√2} (dy,dx);
  `gap(E,d) = max_u min(E(x+d·u), E(x−d·u))`, ranked:
  `gapflank_rtp_lag6`, `gapflank_rtp_lag12`, `gapflank_grav_lag6`, `gapflank_grav_lag12`
  (4 features).
- H30-3 soft emission: support = priority Poisson-disk (≥2.8 px) with budget 2× the
  binary fold budget; order support pixels by descending detector probability (stable);
  raw value `p_k = 1 − k/N` (k = 0-based rank, N = support size); scale all values by
  `B/Σp` (B = binary fold budget), clip to [0,1]; record effective mass Σp per cell.

## 5. Frozen gates — E1/E2/E3 = the 3-experiment budget. No other experiments.

Holdout (template, unchanged): quadrant folds (`holdout.make_quadrant_folds`); whole
8-connected catalogue segments hidden at 20 % per quadrant; every catalogue-derived
quantity (B2 distance) from **visible** faults only; visible faults masked pixel-exactly;
6-px buffered scoring ring excluded (`holdout.buffered_scoring_mask`); pooled DTI =
ΣTPw/(ΣTPw+0.2ΣFPw+0.8ΣFNw) over cells. Emission identical across binary arms
(ridge NMS → B2 → priority Poisson-disk 2.8 px; per-fold budgets = 38,000 × footprint
share). Arms: **D** = 32+15 (control to beat), **DIP** = D+5 H30-1, **GAP** = D+4 H30-2,
**SOFT** = D surface with H30-3 emission (scored with `metric.dti_exact`).

- **E1 leakage canary:** each of the 9 new features alone, ROC AUC vs seed-240 hidden
  segments (all 4 folds, positives + 200k sampled negatives, rng 7 as in prior lanes).
  Any direction-invariant AUC > 0.90 ⇒ leakage: stop, verdict negative.
- **E2a selection (seeds 240–244, 20 cells):** candidate = the arm in {DIP, GAP, SOFT}
  with the highest pooled HOLDOUT-DTI, **provided it strictly exceeds pooled D**; else
  **negative, stop** (D itself is not a shippable candidate — see §1). Surface
  uniqueness pre-check here: Spearman(OOF probability, each registry raster value and
  its σ=3 density) on a deterministic 300k footprint sample must be ≤ 0.90.
- **E2b confirmation (seeds 245–254, 40 cells, untouched until E2a closes):** candidate
  vs D. **Efficacy PASS iff** pooled(candidate) > pooled(D) **and** mean paired Δ ≥
  +0.0015 **and** deterministic cell-bootstrap 95 % CI (2,000 draws, rng 11) lower bound
  > 0 **and** ≥24/40 cells positive **and** ≥3/4 fold-mean Δ > 0. This is the
  single-candidate confirmation required before any weekly slot may be considered; it
  must beat the current holdout best (Arm D), per the tasking.
- **E3 build + uniqueness + validator (exactly one candidate file is built:**
  the E2a-selected candidate, *whatever E2b says — a negative deliverable still ships
  its bytes badged ⛔*; **clarified before any E2a result was seen:** if no contender
  beats D in E2a, the built file is the highest-pooled contender of {DIP, GAP, SOFT}
  as a **negative research artifact** with verdict negative, so the session still
  delivers exactly one new unique TIFF + run card):
  full-fit surface (all labels), B2, 38,000-dot (or 38,000-mass soft) emission;
  primary file all-finite (zeros outside, nodata=None) via the shared writer.
  **Promotion uniqueness registry (protocol-literal, decided here before results):**
  the 12 pinned peer rasters in `registry/parallel_submission_registry.json`
  (GEMSDOE24/25/27-scored/28/30/31/32/33/36 — the parallel lanes' submissions).
  Candidate fails uniqueness iff final-raster Spearman vs any registry raster > 0.90
  **or** directed fraction of candidate dots (value > 0.5, the shared
  `scripts/check_parallel_uniqueness.py` definition; support > 0 also reported for soft)
  within 3 px Euclidean of any single registry raster's dots > 0.70. Overlaps vs this
  repo's own **unscored** research artifacts (H28-1/H29-1/H29-1b/L-DCONFIRM/H28-3/lane/
  scatter) are **measured and printed in the run card but are not the promotion gate**:
  those files were never submitted, the dense 59,075-px H28-1 file makes ≤70 %
  geometrically near-impossible for any accurate 38k emission (H29-1b deconfliction
  proof, `knowledge/16` addendum + §3), and the session protocol defines "registry
  raster" by the parallel registry. This supersedes, explicitly and prospectively (not
  silently and not post-hoc), the extended self-screen frozen by the H29-1/L-DCONFIRM
  lanes; it is logged as an irregularity update for selector review (IR-2026-10-25-06).
  **Validator:** shared `verify_geotiff` hard-PASS on the all-finite primary (no NaN
  inside footprint, all 12,279,160 cells in [0,1], EPSG:32611 / 3730×3292 / transform
  match, single-band float32); plus 0 dots on catalogue and 0 dots with d(cat) ≤ 2.
- `ok_to_submit` = E2b efficacy PASS ∧ canary clean ∧ uniqueness PASS ∧ validator PASS —
  computed by the build script into the run-card JSON and re-checked fail-closed by
  `gems27.readiness` / `scripts/audit_submission_readiness.py`; the website badge reads
  only that audit. No human-inspection gate anywhere. Promotion to a real weekly slot
  remains the owner's separate selector step within the actual cap (protocol §6); the
  agent never uploads. Note ≤ 140 characters. Any gate failure ⇒ verdict **negative**,
  file in `docs/downloads/research/` badged ⛔ DO NOT SUBMIT, no post-hoc tuning, no
  seed shopping, no re-runs on used seeds (historically consumed: 100–169, 200–231
  ranges as recorded per-hypothesis; 240–254 are fresh).

Official sources for manual review: competition
https://www.drivendata.org/competitions/306/competition-doe-gems/ · problem
https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ · reference
solution https://github.com/drivendataorg/gems-prize-reference-solution · rules
https://docs.nlr.gov/docs/fy26osti/96647.pdf · USGS GeoDAWN
https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and ·
INGENIOUS https://gbcge.org/current-projects/ingenious/ · GDR 1391
https://gdr.openei.org/submissions/1391 · EPSG:32611 https://epsg.io/32611 ·
Tversky index https://en.wikipedia.org/wiki/Tversky_index
