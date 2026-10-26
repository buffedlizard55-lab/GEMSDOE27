# H31-3 Result — MT Graben-Margin Asymmetry (2026-10-26)

**Lane:** `L-S12-H31-3-MTGRABEN`  
**Preregistration:** `knowledge/28_preregistration_H31-3_mt_graben_2026-10-26.md` (committed as `83ceee5` before any H31-3 computation)  
**Verdict:** **NEGATIVE — DO NOT SUBMIT**  
**Organizer status:** no organizer score exists. Every numerical outcome below is **HOLDOUT-DTI**, not a live score.

## Scientific question

H31-3 tested a specific, label-free geothermal mechanism: a conductive smectite/clay-cap or brine anomaly should occur **basinward** of a steep basement-depth gradient at a buried normal-fault margin. It uses only `cond_surf`, `depth_to_base_surf`, `iso_grav_anom`, and `geod_dilaterate`; it does not use fault vectors, catalogue geometry as a predictor, or external fault labels. The declared non-fault mimic was conductive evaporite/playa fill at a lithologic basement contact.

The frozen method appended eight bounded, within-footprint-rank features (three signed 300/600/900 m normal samples, cross-strike conductivity asymmetry, depth persistence, and gravity/extension corroborations) to the shared H31 dual-regime out-of-fold architecture. The unchanged blind B2 axial-CELF emission used 37,654 dots and excluded all catalogue pixels within 2 px.

## E1 — leakage and pre-placement uniqueness: PASS

Fresh frozen seeds **510–519** were unused by prior H31/H32 experiments.

| Check | Result | Frozen criterion | Verdict |
|---|---:|---:|---|
| Max individual-feature direction-invariant AUC | **0.53194** | `<= 0.90` | Pass — no leakage canary |
| Max pre-placement surface Spearman vs 12 pinned peers | **0.11011** | `<= 0.90` | Pass |
| Features | 8 deterministic finite rank transforms | only four preregistered bands | Pass |

Receipt: `evidence/h31_3_e1_canary_and_surface_510_519.json`.

## E2 — matched HOLDOUT-DTI efficacy: FAIL

**Evaluator:** `gems27.metric.dti_binary v1 (alpha=0.2, beta=0.8, R=3px triangular) + buffered quadrant holdout (buffer_px=6)`  
**Withheld positives:** 121,745 across 40 buffered hide-and-recover cells; seeds 510–519; folds NW, NE_LidarGapHeavy, SW, SE.  
**Caveat:** this is a catalogue-internal proxy and cannot measure far-field organizer performance.

| Arm | Pooled HOLDOUT-DTI |
|---|---:|
| H31-S exact control | 0.044966 |
| H31-3-S MT-graben candidate | **0.045332** |
| Candidate − H31-S pooled difference | +0.000366 |
| Mean paired seed difference, 95% CI | +0.000392, **[-0.001182, +0.001823]** |
| Positive seeds / folds | 6/10; 2/4 |

The pooled value is directionally positive, but the preregistered five-clause gate explicitly required a stable effect. Only 1/5 clause passed: pooled candidate > control. The mean effect was below `+0.001`, the CI includes zero, and neither the 7/10-seed nor 3/4-fold stability condition was met. The negative is therefore conclusive for the frozen method/seed block: **no tuning or rerun is allowed on these seeds.**

Receipt: `evidence/h31_3_e2_holdout_510_519.json`.

## E3 — byte-bound research artifact and duplicate screen

E3 was performed once, after E2, strictly to bind the negative result to a reproducible raster rather than promote it:

- all-finite candidate: `docs/downloads/research/gems27-h31-3-mt-graben-celf28-20261026-0f397db36baf-allfinite.tif`
- SHA-256: `da29080bf6acfdc91a835b06464e7d64c056703067967129505af886a59a9d68`
- all-finite validation: exact `{0,1}`, float32 single band, EPSG:32611, 3730×3292, 0 NaN/Inf, zeros outside footprint, 37,654 dots.
- maximum final-dot overlap vs the 12 pinned peer rasters: **56.74%**; 12-peer gate pass.
- maximum final raster Spearman vs the 12 peers: **0.04669**; pre-placement surface maximum **0.12063**.
- **extended local check:** 86.87% within 3 px of H31-1. This independently blocks promotion under the repository's stricter all-local-raster screen, even though the required 12-peer screen passes.

The file, its ZIP, NaN companion, checks, and note are intentionally under `docs/downloads/research/`; `docs/downloads/h31_3_candidate_manifest.json` sets `ok_to_submit: false`. It is not linked as a download candidate. The authoritative end-of-experiment card is `evidence/h31_3_run_card_2026-10-26.json`.

## Decision

H31-3 was a non-leaky and 12-peer-unique geological test, but it did not demonstrate a statistically stable incremental H31-S holdout benefit and is materially co-located with H31-1. It consumes **one negative experiment**, not a DrivenData weekly slot. H31-1 remains the only machine-authorized download, pending the separate owner/selector decision to use a weekly slot. H31-3 must not be uploaded, re-emitted, or tuned on seeds 510–519.

```json
{
  "hypothesis_id": "H31-3",
  "mechanism": "basinward conductive clay-cap anomaly across steep basement-depth gradient",
  "named_non_fault_mimic": "conductive evaporite/playa fill at a lithologic contact",
  "holdout_label": "HOLDOUT-DTI",
  "evaluator": "gems27.metric.dti_binary v1 + buffered quadrant holdout (6 px)",
  "withheld_positives": 121745,
  "seeds": [510, 511, 512, 513, 514, 515, 516, 517, 518, 519],
  "pooled_candidate_minus_h31s": 0.0003663575,
  "paired_mean_ci95": [-0.0011822506, 0.0018226982],
  "registry_max_dot_overlap_3px": 0.56737664,
  "extended_local_max_dot_overlap_3px": 0.86872577,
  "raster_sha256": "da29080bf6acfdc91a835b06464e7d64c056703067967129505af886a59a9d68",
  "validator_allfinite_pass": true,
  "note": "H31-3 negative: effect unstable and locally overlaps H31-1; never submit.",
  "verdict": "negative",
  "ok_to_submit": false
}
```
