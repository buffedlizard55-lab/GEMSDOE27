# Preregistration H28-6 — scale-persistent gravity horizontal-gradient edges (2026-10-28)

**Written before any feature, holdout, emission or placement computation in this session.**
Runner: `scripts/run_h28_6_gravity_persistence.py` (to be written against the shared tools, not forked).
Result file: `knowledge/37_h28_6_result_2026-10-28.md` (to be written after the run, labelled HOLDOUT-DTI).

## 0. Lane and provenance disclosure (read first)

- The user prompt again says "Your lane is the single method paragraph below" and then gives no paragraph. This is the same omission recorded in `knowledge/35_session16_delivery_review_2026-10-28.md`. **Flagged for owner review.**
- To avoid inventing a lane, this run executes the **single untried hypothesis that the repository's own registry already ranks** (`registry/next_hypotheses.json`, rank 3, `H28-6`, status "UNTRIED exact formulation"; also listed as candidate 2 in `knowledge/33_session15_repo_review_2026-10-28.md`). No other hypothesis is run in this session.
- Seeds **700–709** were checked against every seed range recorded under `knowledge/`, `evidence/`, `registry/`, and `scripts/` at the time of writing; none is used. Seeds 520–529 (H33), 620–624 (H29-5-PROXY), 210–219 (H29-S), and 240–244 (H30-1) are **not** reused.

## 1. Candidate hypotheses considered (ranked; only #1 was run)

| Rank | Hypothesis | Layers | Signature targeted | Why it could catch a fault missing from the catalogue | Non-fault mimic | Novelty vs repo | Cost / data gate | Expected HOLDOUT-DTI gain |
|---|---|---|---|---|---|---|---|---|
| 1 (run) | **H28-6 scale-persistent gravity edges** | `iso_grav_anom` (cached band) | Horizontal-gradient magnitude of the gravity anomaly at 100, 200 and 400 m smoothing; their minimum across scales | A buried density step that persists across three scales can mark a basement boundary under alluvium, where scarps and magnetics are weak | Basin-fill density pinch-outs, lithologic contacts, regional-field trends, survey-line seams (which usually do not persist at 400 m) | The exact multi-scale persistence transform is not in the repo. The stack has single-scale `iso_grav_anom_hg`, `_vg`, `_slope`, so this is a partial overlap, not an unseen input | Low: cached band, no new data. Compute ~minutes | Unknown; no prior number. Gate-level requirement below |
| 2 | H28-7 directional radiometric alteration continuity | GeoDAWN K, Th, U and ratios | Orientation-coherent alteration fronts along a line | Fault-controlled fluid flow may leave an elongated alteration front beyond the mapped trace | Soil/lithology contrast, soil moisture, survey artefacts | Radiometric ratios were tested weakly in Addendum D (+0.0007 PR-AUC), so this is a new transform on a weak signal | Low, cached bands | Low; prior evidence weak |
| 3 | Actual routed-drainage fan-apex collinearity (H29-5 full form) | USGS 3DEP DEM, flow routing | Collinear canyon-mouth knickpoints and fan apices along a range front | Fans bury scarps while leaving aligned outlets | Resistant bedrock hogbacks | Not executed; the registry's proxy (H29-5-PROXY) is a different operator and is negative | **Blocked**: the raw DEM tiles are not in the sandbox allowlist (`dem_links.json` only lists URLs); not run | Unknown |
| 4 | DOE GDR #1391 paleo-sinter/tufa and 2 m temperature probes (H27-16) | GDR #1391 packages | Sinter/tufa alignments with probe residuals | Upflow conduits can be mapped by fossil deposits | Lacustrine tufa on Lake Lahontan shorelines; groundwater plumes | Novel data source for the repo (but the repo's H29-1 uses a different well/spring table) | **Blocked in bash**: `curl` to `gdr.openei.org` fails at TLS (checked 2026-10-28). Metadata is readable through the fetch tool (`https://gdr.openei.org/submissions/1391`, DOI 10.15121/1881483, CC-BY-4.0). Package bytes not obtained | Unknown |
| 5 | Magnetic-gradient tensor invariants with multi-scale persistence (magnetic analogue of #1) | `tmi`, `rtp`, `tmi_vg`, `tmi_hg` | Persistence of magnetic horizontal gradient across scales | Same as #1 but for susceptibility contrasts | Igneous intrusions, magnetised basement, cultural steel | Partly overlapping with `sub_tiltabs_rtp`, `sub_analytic_rtp` (already in subsurface transforms) | Low, cached bands | Likely small; redundant with existing transforms |

Ranking basis: expected gain is qualitative. Cost is the main tie-breaker; #1 is cheapest with a non-redundant formulation. **No numerical improvement is asserted for any candidate.**

## 2. Frozen feature construction (the candidate's 4 new columns)

Input: band `iso_grav_anom` from `data_cache/prepared/features.npy` at the footprint (5,167,373 px). Use row-major footprint order and place values on the full grid before filtering.

1. `m` = footprint AND finite(`iso_grav_anom`); `f` = `iso_grav_anom` where `m`, else 0.
2. For σ ∈ {1, 2, 4} px: `Gσ = gaussian(f·m, σ) / max(gaussian(m, σ), 1e-6)` (normalized convolution), set to 0 outside the footprint.
3. `Hσ = sqrt(d/dy(Gσ)² + d/dx(Gσ)²)` with `numpy.gradient`, footprint only.
4. `Ĥσ = clip(Hσ / p99(Hσ over footprint), 0, 1)`; a constant or empty field returns zeros.
5. The four columns are `Ĥ1`, `Ĥ2`, `Ĥ4`, and `P = min(Ĥ1, Ĥ2, Ĥ4)`.

Only the `P` column carries the persistence claim. The three single-scale columns are included because a persistence minimum alone can hide a candidate where one scale is weak.

**Deviation from the registry text:** the registry says "analytic-signal persistence". This formulation uses only the horizontal-gradient term. The vertical term is already in the stack (`iso_grav_anom_vg`). This is a deliberate reduction, not a claim of a true analytic signal.

## 3. Arms

- **C (candidate):** base 32 cached bands + 15 subsurface transforms (`subsurface_features.build_transforms`, cached by `run_h29_holdout.get_or_build_subsurface15`) + the 4 new columns.
- **D (matched control, the gate comparator):** base 32 + 15 subsurface transforms. This is the same family as the repository's internal D0 control, rebuilt on this session's splits.
- **B (context only, not gated):** base 32 alone, the H33 control.

C and D share the same seed, splits, buffer, HGB hyperparameters, negative subsampling, emission and scorer. C differs only by the four new columns.

## 4. Experiments (budget: 3 experiments or 2 hours, whichever first)

- **E1 — canaries and pre-placement surface.** For every one of the 51 model inputs (32 base + 15 subsurface + 4 new), compute direction-invariant ROC AUC of hidden positives (union of the 10 seeds' hidden pixels) versus up to 250,000 random non-catalogue footprint negatives outside all hidden sets. Stop if any `max(AUC, 1−AUC) > 0.90` (the feature is then a leakage suspect). Then fit a full-fit C surface on all visible labels and compare it with the 12 pinned registry rasters by Spearman on a 400,000-cell sample. Stop if any `|ρ| > 0.90`.
- **E2 — paired whole-FID holdout (10 seeds × 4 quadrant folds).** `holdout.make_segment_split(labels, footprint, group_map, seed, frac=0.20)` hides whole vector-segment groups; training excludes a 6 px buffer around hidden pixels (`buffered_training_mask`); the emitter sees only the probability surface, footprint and visible catalogue (`known`), via `emit()` (ridge NMS σ=1.0, B2 exclusion of 2 px around visible catalogue, Poisson 2.8 px, budget 37,654). Scoring: `metric.dti_binary` with the full 300 m triangular kernel (α=0.2, β=0.8, R=3 px), valid mask = `buffered_scoring_mask(buffer_px=6)`. Report pooled HOLDOUT-DTI per arm, paired C−D per seed, and bootstrap CI (10,000 resamples, RNG 20261028). Pass requires all of: mean paired Δ ≥ +0.001; bootstrap 95% CI lower bound > 0; positive seeds ≥ 7/10; positive quadrant folds ≥ 3/4; pooled C > pooled D.
- **E3 — placement and uniqueness (only if E1 passed).** Place dots from the full-fit C surface with the same emission and budget and the full catalogue as known. Checks before writing: directed 3 px dot overlap against all 12 pinned registry rasters ≤ 70%; final-dot Spearman ≤ 0.90; the same overlap against every local all-finite raster in `docs/downloads`. If any check fails, **no TIFF is written** and the run is recorded as a duplicate stop. If the checks pass, write a float32 all-finite [0,1] GeoTIFF with `gems27.submission.write_geotiff(outside="zero")`, a NaN twin, a one-member ZIP, and an independent reread via `submission.verify_geotiff`.

## 5. Gate and labelling rules

- All numbers are **HOLDOUT-DTI** (evaluator `gems27.metric.dti_binary` v1 + whole-FID buffered holdout, buffer 6 px). None is an organizer score, a leaderboard estimate, or a projection.
- **A holdout pass cannot make a file OK to submit by itself.** The readiness gate in `src/gems27/readiness.py` requires `matched_current_best_comparison` (the exact current-best architecture re-run on the same splits, which this run does not do: H29-S and H31 are not re-run). Therefore even an E2 pass yields **NOT OK TO SUBMIT** with the reason stated. The decision is written to the run card either way.
- Leakage stop: any feature with `max(AUC,1−AUC) > 0.90`.
- Duplicate stop: surface |ρ| > 0.90 or dot overlap > 70% against any registry or local raster.
- No DrivenData access, no upload, no weekly slot selection, no tuning after seeing results.

## 6. Deviations to disclose if they occur

- If the full-run budget does not allow the matched H31/H29-S comparison, record it as not run.
- If the registry scope is incomplete (12 pinned focus rasters and local all-finite files only), say so; it does not prove global novelty.
