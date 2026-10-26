# Session 11 Preregistration — Lane `L-S11-2026-10-26` / Hypothesis `H31-2` (DEMAG stacker)

**Frozen before any seed in 410–419 is run. Date (UTC): 2026-10-26.**
**Branch:** `arena/6ab960ad-gemsdoe27`
**Labelling (Parallel-Run Protocol §3):** every number produced under this document is
`HOLDOUT-DTI` (evaluator version + withheld-positive count + 95% CI) or `MODEL` (a labelled
projection from a stated formula) or `OWNER-REPORTED` (copied from the owner's score lists).
Nothing here is `ORGANIZER-CONFIRMED`; no DrivenData receipt exists in this repo and the agent
never accesses `drivendata.org` (`AGENTS.md` Hard Rule #1).

---

## 0. Inherited state (verified in this checkout before writing this document)

- Data restored hash-exact: `scripts/restore_data.py` 17/17 `OK`; prepared 32-band stack
  SHA-256 `83ed2704ee2de03cf8b1c8f2966fcf71813501df97c1c35400e6c0415393f6dc`;
  12 parallel-registry peers `OK` (`g32_h33_2_b2 c55bafc47005…` etc.).
- `pytest -q`: **137 passed**. `scripts/verify_downloads.py`: **0 failures**.
- Current promoted, unscored file: `gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif`
  (H31-1, Session 10, seeds 400–409, pooled buffered `HOLDOUT-DTI 0.047302`). It remains the
  download recommendation unless this lane's frozen gate (below) passes **and** beats it.
- Fleet best across the 9 focus sites is GEMSDOE32 `h33-h33-2-b2` at **0.2778 OWNER-REPORTED**
  (already submitted; pixel-exactly the 0.2708 file minus its 2,545 dots in the (100 m, 200 m]
  catalogue annulus — `knowledge/12`, `registry/focus_sites_2026-10-26.json`). Re-submitting any
  scored file is forbidden; every 0.2449–0.2778 focus file is 86.7–100% within 3 px of it.
- Inherited next steps (`knowledge/25_h31_results_2026-10-26.md` §4, `registry/next_hypotheses.json`):
  H31-2 (seeds 410–419) → H31-3 (420–429) → H27-16 (external-data gate) → H29-5 (≥440).
  This session executes step 1 only. Seeds 410–419 are unused anywhere in `evidence/`.

## 1. Candidate hypothesis screen (generated before implementing; ranked)

Novelty scope: this checkout (`registry/hypotheses.json`, `registry/next_hypotheses.json`,
`evidence/`) + the 12 pinned focus-site peers. Expected Δ are **planning priors (MODEL)**,
not scores.

| Rank | Hypothesis | Layers | Physical signature | Why a catalogue-*missing* fault | Differs from repo | Named non-fault mimic | Prior paired Δ HOLDOUT-DTI | Cost / data gate |
|---|---|---|---|---|---|---|---|---|
| **1 ★LANE** | **H31-2 Poisson-relation demagnetization residual stacker** | `rtp`, `iso_grav_anom`, `iso_grav_anom_vg`, `iso_grav_anom_hg`, `tmi_vg`, `tmi`, GeoDAWN ext `TMI_up150` | Local Gaussian-window (σ=8, 20 px) linear regression of gravity vertical gradient on RTP (the local form of the Poisson pseudogravity relation); positive standardised residual = gravity step present but magnetic expression destroyed; gated by gravity-edge strength and shallow magnetic quietness | Hydrothermal fluids alter titanomagnetite to non-magnetic pyrite/hematite/clay along blind upflow conduits (`knowledge/15`), erasing the magnetic edge while the basement density step persists — exactly the blind class a surface-rupture catalogue misses (~39% of Great Basin systems blind, Faulds & Hinz 2015, OSTI 1724082, read) | Every existing potential-field transform (`sub_crossfield_coherence`, H28-1 edges, H31 Blakely crests) rewards *co-located* magnetic+gravity edges via `min(·)`/products, which actively suppresses magnetite-destroyed conduits. No local Poisson-regression residual exists anywhere in `src/gems27/` | Non-magnetic Paleozoic carbonate on granite; reversely magnetised Tertiary ash-flow tuffs; deep basement under thick basin fill (magnetic field decays with depth with no alteration) | [+0.001, +0.005] vs H31-S | Low–medium; all bands hash-pinned locally (prepared stack + `geodawn_extensions_u8.tif a35a9c6d…`). **Data gate PASS** |
| 2 | H31-3 MT clay-cap × asymmetric basement-relief graben-margin coupling | `cond_surf`, `depth_to_base_surf`, `iso_grav_anom`, `geod_dilaterate`, `det_elev` | Cross-strike pairing: steep footwall `depth_to_base_surf` gradient with conductive hanging-wall anomaly 300–900 m basinward | Buried range-front conduits with smectite/brine caps offset from the resistive footwall step; no surface scarp needed | H28-3 tested *co-located* strain×conductivity (−0.0026, refuted); no asymmetric cross-strike pairing exists | Conductive playa evaporite pans | [+0.001, +0.004] | Medium; local. Reserved seeds 420–429 |
| 3 (blocked) | H27-16 three official GDR #1391 packages (paleo-geothermal sinter/tufa, 2 m probes, Quaternary volcanics) | GDR #1391 zips `faffcf69…`, `1301f70d…`, `c4a2d2df…` | Sinter/tufa alignments + shallow thermal residuals + vent alignments | Fossil sinter cements and masks traces while marking upflow directly | New raw geometries never ingested | Lacustrine tufa; groundwater outflow plumes | [+0.001, +0.008] | **Not viable this session:** source https://gdr.openei.org/submissions/1391 (DOI 10.15121/1881483, CC-BY-4.0) is outside the sandbox allowlist and bytes are not hash-pinned locally. Named, checked, blocked — not proposed as viable until obtained and SHA-256-verified |
| 4 | H29-5 canyon-mouth knickpoint / fan-apex collinearity | `det_elev`, `det_local_relief`, `det_gradient`, lidar relief/cross | 0.5–2 km collinear alignments of transverse canyon outlets along range fronts | Aggrading bajadas bury inter-canyon scarps while drainage geometry keeps fault control | All DEM features are local height/curvature; none measures multi-canyon collinearity | Resistant hogback strata | [0, +0.002] | Medium; local. Reserved seeds ≥440 |
| 5 | Detector-class change: spatial segmentation (U-Net/FaultSEG-style) | 32-band stack + lidar | Learned 2-D linear continuity at 1–5 km scale | Captures lineament continuity per-pixel HGB cannot | No convolutional model in repo; official reference solution is a U-Net (https://github.com/drivendataorg/gems-prize-reference-solution) | Any linear geomorphic/survey artefact | unknown | High (CPU-only here, 2 cores / 3.8 GB; no GPU). Deferred, not this lane |

## 2. Frozen lane (one paragraph)

Build 8 label-free demagnetization features (`src/gems27/demagnetization.py`, §3) from the
hash-pinned prepared stack + `TMI_up150`. Reuse the frozen H31-1 quadrant-OOF instrument
(`gems27.geothermal_conduit_nis.fit_predict_dual_regime_oof`, seed 400, buffer 6 px) to obtain
honest OOF surfaces `(p_sub, p_s1, p_s2)`. Train two quadrant-OOF gradient-boosting stackers
(identical hyperparameters, 6 px guard, all positives + ≤340k sampled negatives per fold):
**STK0** on `[p_s2, p_s1, p_sub]` (recalibration control) and **DEMAG** on
`[p_s2, p_s1, p_sub] + demag8` (candidate). Emit every arm with the identical frozen emitter
`emit_h31_celf` (axial-crest sharpen, weighted CELF, γ=1.35, min-sep 2.8 px, B2 `d_cat>2 px`,
37,654 full-map budget). If the candidate surface's Spearman correlation with any registry
raster exceeds 0.90, or >70% of its final dots fall within 3 px of one registry raster
(12 pinned peers + both scored GEMSDOE27 files + the promoted H31-1 file), it is logged a
duplicate and the lane stops. Nothing else changes; no post-hoc tuning.

## 3. Frozen feature definitions (all label-free; no labels/catalogue/`tc` read)

Grids are taken from `data_cache/prepared/features.npy` by band name, scattered onto the full
grid, footprint-mean-filled outside finite footprint values (same convention as
`gems27.solarsubsurface_features._fill`). `G_σ` = `scipy.ndimage.gaussian_filter(mode="nearest")`;
local moments use Gaussian-weighted means, e.g. `E_w[R]=G_σ(R)`,
`Cov_w(R,Y)=G_σ(RY)−G_σ(R)G_σ(Y)`, `Var_w(R)=Cov_w(R,R)`.

With `R=rtp`, `Y=iso_grav_anom_vg`, window `σ∈{8,20}` px:
`α_σ = Cov_w(R,Y)/(Var_w(R)+ε)`, `β_σ = E_w[Y]−α_σ·E_w[R]`, residual `e_σ = Y−(α_σR+β_σ)`,
standardised `z_σ = e_σ/sqrt(Var_w(Y)+ε)`, `ε=1e-12` (relative floor `1e-6·median Var` guard
against division blow-ups in flat windows, clipped to ±10).

`zpos(A)` = `max(0,(A−median_foot(A))/(IQR_foot(A)/1.349))` (as `geothermal_conduit_nis._zpos`);
`gm2(F)=|∇G_2(F)|`; gravity-edge strength `gE = zpos(gm2(iso_grav_anom))`;
magnetic-edge strength `mE = zpos(gm2(rtp))`.

| # | Name | Definition |
|---|---|---|
| 0 | `demag_resid_abs_s8` | `|z_8|` |
| 1 | `demag_resid_pos_s8` | `max(z_8,0)` (gravity VG unexplained by magnetics = magnetite-destroyed) |
| 2 | `demag_resid_gated_s8` | `max(z_8,0)·(0.25+gE)` |
| 3 | `demag_edge_deficit` | `max(gE−mE,0)` (gravity edge without magnetic edge) |
| 4 | `demag_edge_deficit_x_gE` | `max(gE−mE,0)·gE` |
| 5 | `demag_shallow_quiet_x_gE` | `gE/(1+zpos(|G_2(tmi_vg)|))` (gravity edge + shallow magnetic quietness) |
| 6 | `demag_resid_pos_s20` | `max(z_20,0)` (2 km regional window) |
| 7 | `demag_up150_deficit_x_gE` | `max(rank01(TMI_up150)−rank01(tmi),0)·(0.25+gE)`, ranks within footprint (shallow field weaker than its 150 m upward continuation predicts, at a gravity edge) |

Disclosed instrument caveat (same class as H28-1's): Gaussian windows up to σ=20 px share
label-free covariates across the 6 px scoring buffer. No label enters any transform.

## 4. Frozen experiments (budget: 3; stop rules binding)

- **E1 — leakage canary + pre-placement surface screen.** On the union of withheld positives
  for seeds **410–419** (`holdout.make_split`, 4 quadrants): direction-invariant univariate
  ROC-AUC of each demag feature; stop if any >0.90. After surfaces are fit, pre-placement
  Spearman of DEMAG vs 12 peers + scored GEMSDOE27 (`5512495c6bd1`, `511898747886`) + promoted
  H31-1 (`cf8e1bbef244`) on a fixed 400k footprint sample; stop if max |ρ| >0.90.
- **E2 — paired blind holdout, seeds 410–419 × 4 quadrants = 40 cells.** Buffered scoring
  (`buffered_scoring_mask`, 6 px) primary via `gems27.metric.dti_binary`
  (α=0.2, β=0.8, R=3 px triangular kernel); unbuffered diagnostic secondary. Visible faults
  masked pixel-exactly (`known=sp.known`); emission blind (sees only `fold_domain`, `sp.known`).
  Arms: **U0** uniform null, **H31S** (`emit_h31_celf(p_s2)`, primary comparator = current
  holdout best), **STK0** (recalibration control), **DEMAG** (candidate).
  **Gate — ALL required:** (a) pooled buffered DEMAG > H31S and > STK0;
  (b) mean seed-level paired Δ(DEMAG−H31S) ≥ +0.0010; (c) 10,000-draw seed-bootstrap 95% CI
  lower bound >0 vs H31S **and** vs STK0; (d) ≥3/4 folds vs H31S; (e) ≥8/10 seeds vs H31S;
  (f) E1 passed. Seeds 410–419 are consumed by this gate whatever the outcome.
- **E3 — one unique TIFF.** Full-footprint DEMAG quadrant-OOF stacked surface (disclosed: single
  quadrant partition, unlike H31-1's dual-partition stitch) → `emit_h31_celf`, B2, 37,654 dots.
  All-finite primary (`nodata=None`, every cell ∈{0,1} — the `[0,1]` portal fix) + NaN twin +
  single-GeoTIFF ZIP via shared `gems27.submission`; content-hashed name; note ≤140 chars.
  Uniqueness: 3-px dot overlap (Euclidean, candidate→reference) + Spearman vs 12 peers + both
  scored GEMSDOE27 + promoted H31-1, gated at 0.70 / 0.90.
  `ok_to_submit = E2 gate PASS ∧ uniqueness PASS ∧ validator hard PASS`, computed by
  `gems27.readiness.publication_decision` — no human inspection. If E2 fails the file is a
  **NEGATIVE research artifact (⛔ DO NOT SUBMIT)** in `docs/downloads/research/` and H31-1
  remains the recommendation. Even on PASS, promotion to a weekly slot is the owner's separate
  selector step. No live score is claimed for any file built here.

## 5. Preregistered MODEL live-estimate (for the executive-summary table; not a score)

For an unscored file `F` emitted at the same N=37,654 / B2 operating point as H29-S
(live **0.2190 OWNER-REPORTED**), the estimate is anchored *within detector family*:

- `MODEL-no-transfer`: `0.2190` (catalogue-internal holdout gain transfers not at all).
- `MODEL-proportional`: `0.2190 × (HOLDOUT-DTI_buf(F-arm) / HOLDOUT-DTI_buf(H29S-arm))` with both
  arms measured on the **same seeds/instrument** (for H31-1: seeds 400–409, 0.047302/0.044116).
- `MODEL-unbuffered`: same ratio on unbuffered pooled HOLDOUT-DTI.
- Reported as central = MODEL-proportional, interval = [MODEL-no-transfer, max of the two ratios].
- Beat-0.2778 arithmetic (same N): DTI inversion at |G|=12,226 (`evidence/live_inversion.json`)
  requires weighted-recall `TPw/|G| ≥ 0.385` vs H29-S's implied `0.305` (+26%); any candidate
  whose same-instrument holdout ratio is <1.26× H29-S is **MODEL-unlikely** to beat 0.2778 live.
  This is a planning statement, never a leaderboard claim. Cross-family anchoring (e.g. to the
  H19-5 family) is forbidden: H29-S was holdout-best yet scored 0.2190 live vs the family's
  0.2778, proving holdout↔live calibration does not transfer across detector classes.

## 6. What would change our mind

A PASS means demagnetization residuals add ranking information beyond the repo's best surface
on catalogue-internal hide-and-recover — necessary, not sufficient, for live gain. A FAIL
retires H31-2 in this form (recorded in `registry/hypotheses.json` /
`registry/next_hypotheses.json`) and leaves H31-3 (seeds 420–429) as the next lane. Either way
the run card, evidence JSONs, and (on FAIL) the negative TIFF are deliverables.
