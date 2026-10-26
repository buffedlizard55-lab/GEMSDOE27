# Session 11 Review (2026-10-26) — 9 focus sites, score estimate, irregularities

Labelling: live numbers = OWNER-REPORTED (prompt/sibling registries; no DrivenData receipt in repo, no drivendata.org access). Holdout numbers = HOLDOUT-DTI (gems27.metric v1, α=0.2, β=0.8, 300 m triangular kernel). Projections are never scores.

## Verdict
**OK TO DOWNLOAD AND SUBMIT (unique, machine-validated, unscored):**
`docs/downloads/gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif`
SHA-256 `2c002b02792419864bd3b29a218e543cb41e3f07b3b57c29ef35c6e39e184bfe` (re-measured this session: single-band float32, EPSG:32611, 3730×3292, transform (100,0,243350,0,-100,4508550), values exactly {0,1}, 0 NaN, 37,654 dots).
Name `27GEMSDOE-H31-DRCG-WL-20261026-cf8e1bbef244`; note (118/140): `27GEMSDOE H31-1 | dualRegime MSub+MFull+WLseis+obliq+CELF2.8 B2 37654px | id cf8e1bbef244 | unscored validated-promote`

## 9 focus sites — best per site (all OWNER-REPORTED, all already submitted → DO NOT re-submit any)
| Site | Best file | Score | Unique new submission? |
|---|---|---|---|
| GEMSDOE32 | h33-h33-2-b2 e5eb6e7e-zeros | 0.2778 | No — benchmark; pixel-exact B2 re-thin of H19-5 family |
| GEMSDOE36 | anderson-geothermal-pinn 9b9ea4e6 | 0.2750 | No |
| GEMSDOE28 | h36-1-rung30 b531dae0 | 0.2710 | No |
| GEMSDOE31 | h27-4-solo-d28 8acb75e1 | 0.2708 | No |
| GEMSDOE33 | h33d-analog-tip cb490425 | 0.2632 | No |
| GEMSDOE25 | dotted-h19-5-d2-8 e56ea318 | 0.2600 | No |
| GEMSDOE30 | d28-poisson300m 91eae1ca | 0.2600 | No |
| GEMSDOE24 | h25-1-dotted d1.5 989f5950 | 0.2477 | No |
| GEMSDOE27 | topo-gap-closure 5512495c (Slot 1); H29-S 511898747886 = 0.2190 | 0.2449 | No |
Why 0.2778 won: zero new geology — `dot_thin(H19-5,2.8)` minus 6,436 dots within 200 m of catalogue (whose marginal efficiency 0.003–0.008 « break-even 0.0588). Deleting pure-FP collar dots raises DTI monotonically 0.2600→0.2708→0.2778. That lever is exhausted and its rasters are >91% mutual clones, so copying it violates the ≤70% 3-px uniqueness rule.

## Score estimate for the approved unique file (PROJECTION)
Anchor transfer: H29-S HOLDOUT-DTI 0.044116 → live 0.2190 (OWNER-REPORTED). H31-S 0.047302 (+7.22%, 40 cells, 120,778 withheld positives, seeds 400–409; paired −B0 +0.009577 [+0.0080,+0.0112], −H29-S +0.003185 [+0.0015,+0.0051]).
Projection = 0.2190 × 0.047302/0.044116 = **0.2348**; planning range 0.19–0.26 (transfer error, not a CI).
**Honest conclusion: expected live score is likely BELOW 0.2778.** No honest model in this repo projects >0.2778, let alone 0.3195/0.4413 (both OWNER-REPORTED, mutually inconsistent — flagged). Claiming otherwise would be fabrication. H31-1 is the best *validated unique* candidate; beating 0.2778 needs the next detector generation below.

## Untried hypotheses (ranked; from registry/next_hypotheses.json, screened vs repo)
1. **H31-2 Poisson demagnetization residual** — layers rtp/iso_grav_vg/hg/tmi_vg/K/Th; local gravity-vs-RTP regression residual gated by subdued tmi_vg. Catches magnetite-destroyed hydrothermal conduits with no scarp (invisible to catalogue mapping). Cost: low (cached stack). Mimic: lithologic contacts.
2. **H31-3 footwall/hanging-wall asymmetry** — depth_to_base_surf cross-strike gradient × cond_surf clay-cap. Catches buried range-front faults under alluvium. Cost: low.
3. **H29-5 canyon-mouth knickpoint collinearity** — DEM drainage knickpoints aligned along piedmont fronts. Cost: medium.
4. **H27-16 GDR #1391 external vectors** — sinter/tufa, 2 m temperature probes, Quaternary volcanics (official: https://gdr.openei.org/submissions/1391, DOI 10.15121/1881483). Direct geothermal surface evidence absent from all cached layers. Cost: needs internet-enabled fetch + hash pinning before use.
Gate for all: fresh seeds ≥410, canary AUC ≤0.90 per feature, must beat H31-S HOLDOUT-DTI before any weekly slot.

## Irregularities flagged
- IR-2026-10-26-05 (NEW): site prose + registry/sources.json claimed grid transform (323344.2347, 4565845.3247); every shipped raster + src/gems27/grid.py verify (243350.0, 4508550.0). Fixed in scripts/build_site.py + sources.json this session. Raster bytes were always correct — prose only.
- verify_downloads.py requires data_cache/sample_submission.tif (git-ignored, absent in fresh clone) → cannot run end-to-end here; H31 file itself re-validated directly with rasterio this session (above). 134 tests pass, 3 skipped.
- Leaderboard high stated as both 0.4413 and 0.3195 in prompt; neither verified (no drivendata.org access per AGENTS.md).

## Run card
```json
{"hypothesis":"H31-1 dual-regime corroborated geothermal conduit + Walker Lane synthesis, CELF min_sep=2.8","mechanism":"60-col LiDAR-free M_Sub quantile-calibrated over LiDAR gap + 79-col M_Full, Frangi/halo crest sharpening, B2 catalogue exclusion, 300m CELF cover","named_non_fault_mimic":"Lake Lahontan paleo-shoreline benches; volcanic/pluton contact rims","holdout_dti":"0.047302 [0.044527,0.049619] buffered, seeds 400-409, 120778 withheld positives; canary max AUC 0.5895","correlation_overlap_vs_registry":"max Spearman 0.1645; max 3px dot overlap 62.8% (50.2% vs GEMSDOE32 0.2778) — PASS ≤0.90/≤70%","raster_sha256":"2c002b02792419864bd3b29a218e543cb41e3f07b3b57c29ef35c6e39e184bfe","validator":"re-measured: float32 1-band EPSG:32611 3730x3292, {0,1}, 0 NaN, 37654 dots","submission_name":"27GEMSDOE-H31-DRCG-WL-20261026-cf8e1bbef244","note":"27GEMSDOE H31-1 | dualRegime MSub+MFull+WLseis+obliq+CELF2.8 B2 37654px | id cf8e1bbef244 | unscored validated-promote","live_projection":"~0.235 PROJECTION (anchor transfer), NOT a score; likely below 0.2778","verdict":"promote"}
```
