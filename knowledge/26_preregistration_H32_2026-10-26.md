# 26 — Preregistration (Session 11, Lane L-S11): H32 Poisson-theorem demagnetization residual

**Date:** 2026-10-26 · **Written BEFORE any H32 feature was computed or any holdout cell ran.**
**Budget (Parallel-Run Protocol §6):** 3 experiments (E1 canary, E2 holdout, E3 build+uniqueness), ≤2 h compute.
**Seeds:** fresh, unconsumed **500–509** (consumed blocks on record: 100–159, 200–224, 240–254, 260–269, 300–309, 400–409). Seeds 500–509 are consumed by this session whatever the outcome; no re-run on them after seeing results.

## 1. Ranked untried hypotheses considered (screened against this repo + `registry/next_hypotheses.json`)

| Rank | ID | Layers | Physical signature | Why it catches catalogue-missing faults | Differs from repo because | E[ΔHOLDOUT-DTI] prior / cost | Data gate |
|---|---|---|---|---|---|---|---|
| **1 (selected)** | **H32 (= H31-2)** Poisson-theorem gravity↔pseudogravity demagnetization residual | `rtp`, `tmi`, `tmi_hg`, `tmi_vg`, `iso_grav_anom`, `iso_grav_anom_hg`, `iso_grav_anom_vg` (+ rad `K/Th` context only via base stack) | Local (Gaussian σ≈15 px) regression of gravity on RTP; residual + its gradient; gravity-edge-without-magnetic-edge contrast | Hydrothermal upflow oxidises magnetite→hematite/clay along blind conduits: magnetic edge is erased while the basement density step (gravity edge) persists. Surface-scarp catalogues (USGS Qfaults/INGENIOUS) require young surface rupture, so demagnetised blind conduits are systematically under-mapped | `subsurface_features.py` *multiplies* coincident mag+grav edges (`sub_crossfield_coherence = cos·min(gm_rtp, gm_grav)`), which actively suppresses exactly the demagnetised case. No Poisson-residual or grav-without-mag feature exists in `src/` | +0.001…+0.005 / low-medium | PASS — all bands in hash-pinned `training_features.tif` (sha256 `4371c82e…`), restored & verified this session |
| 2 | H31-3 MT clay-cap × asymmetric graben-margin pairing | `cond_surf`, `depth_to_base_surf`, `iso_grav_anom`, `geod_dilaterate` | Cross-strike offset pairing: steep basement-depth footwall gradient with conductive hanging-wall anomaly 300–900 m basinward | Buried range-front conduits have conductive smectite/brine caps offset from the resistive footwall step, no scarp | H28-3 tested *co-located* dilatation×conductivity globally (negative); never cross-strike asymmetric pairing | +0.001…+0.004 / medium | PASS (hash-pinned bands) |
| 3 | H29-5 Canyon-mouth knickpoint / fan-apex collinearity | `det_elev`, `det_local_relief`, `det_gradient`, lidar `relief`, `cross_max` | 0.5–2 km collinear alignments of transverse canyon outlets/fan apexes | Rapid bajada aggradation buries inter-canyon scarps in centuries; aligned knickpoints retain the trace | All DEM/LiDAR features are per-pixel scarp height/curvature; no multi-canyon collinearity operator exists | +0.001…+0.005 / medium | PASS |
| 4 | H27-16 Three official GDR #1391 layers (paleo-sinter/tufa, 2 m probes, Quaternary volcanics) | External GDR packages `faffcf69…`, `1301f70d…`, `c4a2d2df…` | Sinter/tufa lineaments + >+2.5 °C 2 m-probe residuals + vent alignments | Fossil sinter cements and masks scarps while marking Quaternary upflow | Never ingested (H29/H31 used only the well/spring CSV) | +0.001…+0.008 / medium-high | **BLOCKED in this sandbox**: official source is DOE GDR submission 1391, `https://gdr.openei.org/submissions/1391` (DOI 10.15121/1881483, CC-BY-4.0); `gdr.openei.org` is outside this environment's network allowlist and the raw ZIPs are absent from this checkout — NOT proposed as viable this session |
| 5 | H30-2 Standalone hydrothermal upflow detector ablation | well/spring CSV, `cond_surf`, `depth_to_base_surf` | Geothermometer-excess fields alone | ~39–50 % of Great Basin systems are blind (Faulds & Hinz) | Only ever tested fused inside H30-1; standalone ablation untried — but weakest novelty | +0.001…+0.004 / low | PASS |

Named non-fault mimic for H32: **non-magnetic Paleozoic carbonate faulted against granite, and reversely-magnetised Tertiary ash-flow tuff sheets** — both produce gravity edges without coincident magnetic edges with no through-going fault conduit. Also survey flight-line levelling seams in RTP.

## 2. H32 feature definition (label-free, fixed now)

Implemented in `src/gems27/poisson_demag.py`, percentile-ranked to [0,1] in-footprint, from smoothed (σ=2) bands:
1. `poi_resid_abs` — |local Poisson residual|: Gaussian-weighted (σ=15 px) local linear regression `iso_grav_anom ≈ a·rtp + b`; residual magnitude.
2. `poi_resid_signed_pos` — positive residual (gravity excess over magnetically-predicted gravity).
3. `poi_resid_grad_s2`, 4. `poi_resid_grad_s5` — gradient magnitude of the residual field.
5. `poi_demag_edge` — `clip(rank(iso_grav_anom_hg) − rank(tmi_hg), 0, 1)` (gravity edge, no magnetic edge).
6. `poi_demag_vg` — `clip(rank(iso_grav_anom_vg) − rank(tmi_vg), 0, 1)`.
7. `poi_gravonly_coh` — gravity structure-tensor coherence × (1 − rank(tmi_hg)).
8. `poi_pseudograv_mismatch_grad` — gradient magnitude (σ=3) of `(rank(iso_grav_anom) − rank(rtp))`.

## 3. Frozen experiment design

- **Arms (same OOF instrument, `oof_detector.fit_predict_oof_probabilities`, 4 quadrants, 600 m buffer):**
  B = base-32; D = base-32 + 15 subsurface transforms; **P = D + 8 H32 Poisson features**.
- **E1 canary:** direction-invariant univariate ROC-AUC of each of the 8 new features on seed-500 withheld positives; any AUC > 0.90 ⇒ leakage halt.
- **E2 holdout:** `holdout.make_split` (whole 8-connected components hidden per quadrant fold, 20 %), seeds 500–509, 40 cells, buffered scoring (`buffered_scoring_mask`, 6 px). Identical blind emission for every arm: `ridge_nms` → B2 exclusion (EDT to visible faults > 2 px) → `priority_poisson_disk` min-dist 2.8 px, total budget 37,654 dots split by fold footprint share. Metric: `gems27.metric.dti_binary` v1 (α=0.2, β=0.8, 300 m triangular). All numbers labelled **HOLDOUT-DTI**.
- **Promote gate (all must hold):** pooled P > pooled D and P > pooled B; mean per-seed pooled Δ(P−D) ≥ +0.0010; 95 % seed-bootstrap CI of Δ(P−D) excludes 0 (lower > 0); ≥7/10 seeds Δ(P−D) > 0; ≥3/4 folds pooled Δ(P−D) > 0.
- **E3 build (only the P arm, whatever the verdict — negative is a deliverable):** full-fit detector (`fit_predict_full_probabilities`, same features), same emission, 37,654 dots, B2 vs full catalogue. Uniqueness screen vs **every** `*allfinite.tif` in `docs/downloads/` + `docs/downloads/research/` and the two cache H19-5 dotted rasters: directed 3-px dot overlap ≤ 0.70 and Spearman (σ=3 dot density vs surface) ≤ 0.90. Format gates via `submission.verify_geotiff` (all-finite primary).
- **Verdict rule:** `promote` iff E1 clean **and** E2 gate passes **and** E3 uniqueness+format pass; otherwise `negative` / DO NOT SUBMIT. No post-hoc tuning on seeds 500–509.

## 4. Live-score language

No number from E1–E3 is a leaderboard score. Any live estimate in the executive summary will be labelled **PROJECTION** with its method and a sensitivity range; historical live numbers are **OWNER-REPORTED** (no organizer receipt exists in this repo; this agent never accesses drivendata.org — AGENTS.md rule 1).
