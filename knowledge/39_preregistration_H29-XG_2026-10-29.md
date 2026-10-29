# Preregistration H29-XG: joint gravity–magnetic cross-gradient structural coupling (2026-10-29)

Frozen before any holdout or placement run. The runner records this file's SHA-256 in its run card.

## 0. Lane and scope

- The parallel-run prompt for this session again omits its single-method lane paragraph ("Your lane is the single method paragraph below" is followed directly by the REUSE section). No lane was supplied. Lane choice is therefore a documented self-selection from the registry screen in `knowledge/38_hypothesis_screen_2026-10-29.md`. Flag: `IR-2026-10-29-lane-paragraph-missing`.
- Budget: one experiment with three stages (E1 canary and surface, E2 paired holdout, E3 placement and uniqueness). Stop rule: 3 experiments or 2 hours; this is experiment 1 of the session.
- Seeds: **800–809**. Consumed seed ranges (grep of `scripts/*.py`): 1–9, 140–169, 200–224, 230–254, 260–269, 300–309, 400–409, 500–529, 620–624, 700–709. 800–809 is unused.

## 1. Hypothesis

A buried fault that juxtaposes two basement or density domains can produce **coincident** edges in the gravity (`iso_grav_anom`) and reduced-to-pole magnetic (`rtp`) fields, at the same location and with an oblique relative orientation. Lithologic contacts and terrain-residual artefacts can also produce edges, but they are less likely to make both fields change at the same place with a large cross-product of their gradients.

**Mechanism.** Cross-gradient t = ∇g × ∇m = g_x m_y − g_y m_x. Its magnitude is |∇g||∇m| |sin θ|, where θ is the angle between the two edge normals. Large t means both fields have strong gradients that are not parallel, which is the structural-coupling signature used in joint inversion (Gallardo & Meju 2003, GRL, doi:10.1029/2003GL017370; Gallardo & Meju 2004, JGR, doi:10.1029/2003JB002716).

**Named non-fault mimic.** Lithologic contacts with both density and susceptibility contrasts (granite–basin boundaries, ash-flow tuff contacts), and terrain-correlated residuals that appear in both fields.

**Why it could find a catalogue-missing fault.** Coincident edges mark a juxtaposition that does not need to be visible at the surface. The catalogue records only mapped traces, so a buried step with both contrasts could appear here without an existing trace.

## 2. Frozen feature construction (3 new columns)

Inputs: `iso_grav_anom` and `rtp` from the cached 32-band footprint matrix (`data_cache/prepared/features.npy`, names in `features.json`). No labels, catalogue distances, hidden masks or predictions are read.

1. Footprint-normalized convolution for each field, as in H28-6: `G_σ = gaussian(f·m, σ)/max(gaussian(m, σ), 1e-6)` with `f` = field where finite and inside the footprint, `m` = finite-and-footprint mask. Use σ ∈ {2, 4} px (200 m and 400 m at 100 m pixels).
2. Gradients `(g_y, g_x)`, `(m_y, m_x)` with `np.gradient`. Cross-gradient t = g_x m_y − g_y m_x.
3. Columns, each normalized by the footprint 99th percentile and clipped to [0, 1]:
   - `xg_amp_s2` = |t| at σ = 2 px
   - `xg_amp_s4` = |t| at σ = 4 px
   - `xg_sin_s2` = |t| / (|∇g||∇m|) at σ = 2 px (structural angle only, amplitude removed)
   The round-off floor from H28-6 is reused: a field whose gradients are below 1e-9 of its amplitude gives zero, and the sine column is zero where |∇g||∇m| < 1e-6 of its own footprint p99.
4. Outside the footprint every column is 0 and is not emitted.

## 3. Arms (same splits, buffer and scorer)

- **Control D:** cached 32 bands + 15 subsurface transforms (47 columns). This is the H28-6 control.
- **Candidate C:** D + the 3 cross-gradient columns (50 columns).

The shared holdout (`holdout.make_segment_split`, `buffered_training_mask`, buffer 6 px), the shared fit (`run_h33_lane.fit_predict`, HistGradientBoosting, 100 iterations, negatives capped at 10× positives), the shared emitter (`run_h33_lane.emit`, ridge NMS and Poisson 3.0 px) and the shared scorer (`metric.dti_binary`, α = 0.2, β = 0.8, R = 3 px triangular) are reused. No copy is forked.

## 4. Gates (frozen)

- **E1 leakage:** every one of the 50 inputs must have direction-invariant AUC ≤ 0.90 (hidden positives vs 250,000 negatives, same as H28-6).
- **E1 surface:** full-fit candidate surface |Spearman| ≤ 0.90 against the 12 pinned peer rasters.
- **E2 efficacy (all required):** mean per-seed paired Δ(C−D) ≥ 0.001; 95% paired bootstrap CI lower bound > 0; ≥ 7 of 10 seeds with Δ > 0; ≥ 3 of 4 quadrant folds with pooled Δ > 0; pooled C > pooled D.
- **E3 uniqueness:** the pinned 12-raster checker (`scripts/check_parallel_uniqueness.py`) passes, the local overlap against research and all-finite `docs/downloads` files is ≤ 0.70, and the post-placement surface |Spearman| ≤ 0.90.
- **Writing rule (stricter than H28-6):** a research TIFF is written only if E2 efficacy AND E3 uniqueness both pass. Otherwise no raster is written, and the run card records why.

## 5. Labels and decisions

- Every performance number is **HOLDOUT-DTI** (evaluator `gems27.metric.dti_binary` v1, whole-FID buffered holdout). No number is an organizer score or a leaderboard projection.
- Even if every gate passes, the file is **NOT OK TO SUBMIT**. Matched current-best comparison (H31 / H29-S on the same splits) is not run in this experiment, and the readiness gate requires it. No weekly slot is selected, and no upload is made.

## 6. Known limits (stated before the run)

- Holdout DTI on catalogue-internal hides is a weak proxy for the organizer's expert labels. The H29-S holdout (~0.042) and the live scores (0.22–0.28, owner-reported) differ by about 6×, so a holdout gain will not guarantee a live gain.
- The sibling GEMSDOE25 `xg1-crossgrad` raster (`docs/downloads/gems25-xg1-crossgrad-sapd2-4-k3p5-20261025-52e65fb521f9-nan.tif`, sha256 `15073e72…2e032`, listed in `evidence/focus_inventory_20261027.json`) is not among the 12 pinned rasters. Its live score is not recorded. The uniqueness check here does not cover it unless it is fetched. Flag: `IR-2026-10-29-xg1-sibling-not-in-pinned-set`.
- The radiometric stretch issue (uint8 bands) is not relevant to this hypothesis. The magnetic and gravity inputs are float32.
