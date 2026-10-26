# Pre-registration — H31-3 MT clay-cap × asymmetric basement-margin coupling

**Date frozen:** 2026-10-26  
**Lane:** `L-S12-H31-3-MTGRABEN` — this lane tests **only** the method specified below. The owner prompt did not supply a delimited single-method paragraph; this declaration is therefore the operative lane boundary (see the existing analogous irregularity `IR-2026-10-25-01`).  
**Budget:** at most three experiments and at most two hours: E1 canary/surface-duplicate screen, E2 holdout, E3 raster build/validator/duplicate screen.  
**Fresh seeds:** `510..519` (40 quadrant cells). These are disjoint from recorded used blocks `100..169`, `200..224`, `230..254`, `260..269`, `300..309`, `400..409`, and `500..509`. They become consumed whether the gate passes or fails.  
**Before-run status:** no H31-3 features have been computed and no H31-3 holdout cell has been run.

## 1. Candidate screen before implementation

Expected changes are **planning priors**, not HOLDOUT-DTI and not organizer scores. Novelty is screened against `src/`, `knowledge/`, `evidence/`, `registry/hypotheses.json`, `registry/next_hypotheses.json`, all in-repository candidate rasters, and the 12-raster parallel registry.

| Rank | Candidate; layers and physical signature | Why it may locate a catalogue-missing fault | Difference from implemented/tested work | Named non-fault process/mimic | Prior expected Δ HOLDOUT-DTI; cost/data gate |
|---:|---|---|---|---|---|
| **1 — selected** | **H31-3:** `cond_surf`, `depth_to_base_surf`, `iso_grav_anom`, `geod_dilaterate`. At each steep basement-depth gradient, sample smoothed conductivity on both normal sides at 300, 600, and 900 m; retain the **deeper-basin-side** excess, its cross-strike asymmetry, and its gravity/extension corroboration. | A buried range-front or intrabasin fault can juxtapose a basement step with a basinward conductive clay/brine alteration cap, while the surface rupture is absent/buried. The USGS Quaternary catalogue's stated scope is faults with geological evidence of coseismic surface deformation during the last 1.6 Ma, so this is a physically distinct, potentially omitted population. | H28-3's negative test used a **co-located**, global dilatation×conductivity corridor. H31-1 contains co-located depth-gradient/conductivity corroboration, but has no signed normal-direction sampling, no 300–900 m side-pairing, and no deeper-side contrast. | Conductive playa/evaporite basin fill adjacent to a lithologic basement contact, without a permeable fault conduit. | `+0.001..+0.004`; medium; **data gate PASS** — all four bands are in the restored, hash-pinned numerical stack. Official provenance: USGS GeoDAWN data release (`registry/sources.json#geodawn`, `#siler-companions`) and USGS Qfaults scope (`#usgs-qfaults`). |
| 2 | **H29-5:** `det_elev`, local relief/gradient, LiDAR relief/cross-max; 0.5–2 km canyon-mouth and fan-apex collinearity. | Fan aggradation may bury inter-canyon scarps but retain aligned range-front drainage anomalies. | No current transform scores multi-canyon outlet alignment. | Resistant stratiform hogbacks crossed by transverse channels. | `+0.001..+0.005`; medium; hash-pinned local data PASS. Not selected because the directional geomorphic operator is costlier. |
| 3 | **H27-16:** official GDR #1391 paleo-sinter/tufa, 2 m temperature probes, and Quaternary volcanic polygons. | Fossil/active hydrothermal signatures can mark conduits lacking a young mapped surface trace. | These three regional packages are absent from all local feature stacks. | Lake Lahontan tufa, groundwater outflow and volcanic contacts. | `+0.001..+0.008`; medium-high; **not viable here** until raw files are obtained from the free official source `https://gdr.openei.org/submissions/1391` and SHA-256 verified. That host is outside this sandbox's network allowlist; no bytes will be assumed present. |
| 4 | **H28-7:** radiometric-ratio directional alteration lineaments (`K`, `Th`, `U`, `Th/K`, `U/K`, `U/Th`, `TMI_up150`). | Alteration halos can extend beyond a surface-rupture catalogue trace. | Addendum D rejected these ratios as additive pixel features, not as a standalone directional lineament surface. | Lithologic/radiometric soil and drainage contrasts. | `0..+0.002`; low; local data PASS, lower priority after the previous additive failure. |

## 2. Frozen H31-3 method

### Inputs and exclusions

The transform reads **only** `cond_surf`, `depth_to_base_surf`, `iso_grav_anom`, and `geod_dilaterate` from the prepared, label-free numerical stack. It reads no labels, `existing_faults`, catalogue distances, holdout masks, LiDAR, or band 6 (`tc`). Invalid/outside-footprint input is nearest-filled only to stabilise filtering, then excluded from output ranking.

### Eight fixed feature columns

Let `D = depth_to_base_surf`, `C = log1p(max(cond_surf,0))`, `G = iso_grav_anom`, `E = max(geod_dilaterate,0)`. Let `u = ∇Gσ(D)/||∇Gσ(D)||` be the local normal toward *increasing* basement depth (the down-dropped/deeper-basin side), with a zero result where the normal is too small. Let `C+(r)` and `C−(r)` be bilinearly sampled smoothed conductivity at `x + r u` and `x − r u` for fixed `r ∈ {3,6,9}` pixels (300, 600, 900 m). All feature grids are percentile-ranked only over the footprint.

1. `mt_depth_grad_s3`: `||∇Gσ=3(D)||`.
2. `mt_depth_cond_deep_3`: `rank(depth-gradient × C+(3))`.
3. `mt_depth_cond_deep_6`: `rank(depth-gradient × C+(6))`.
4. `mt_depth_cond_deep_9`: `rank(depth-gradient × C+(9))`.
5. `mt_cond_crossstrike_asym_6`: `rank(depth-gradient × max(C+(6) − C−(6),0))`.
6. `mt_cond_deep_persistence`: `rank(depth-gradient × min(C+(3), C+(6), C+(9)))`.
7. `mt_grav_margin_cond`: `rank(||∇Gσ=3(G)|| × C+(6) × depth-gradient)`.
8. `mt_extension_margin_cond`: `rank(E × C+(6) × depth-gradient)`.

These fixed directions make a falsifiable prediction: conductivity on the *increasing-depth* side of an inferred basement margin is useful after conditioning on the margin; symmetric or opposite-side conductivity is not silently substituted. The model, rather than a hard threshold, decides how to combine the ranked columns.

### Detector and placement

- **Control `H31-S`:** the exact existing `H31-1` dual-regime, nested four-sector OOF detector plus axial-crest 300 m CELF (`min_sep_px=2.8`) emitted at 37,654 B2 dots.
- **Candidate `H31-3-S`:** exactly the same H31 architecture and frozen hyperparameters, with the eight H31-3 label-free columns appended to both `M_Sub` (all eight are non-LiDAR) and `M_Full`; they are also present in the stage-2 classifier's original-predictor block. No parameter, budget, spacing, feature pruning, or placement rule will be changed after E1/E2.
- **Blind E2 emission:** each fold observes only `fold_domain = footprint ∩ fold` and visible `known` faults. Candidate/controls must use `EDT(~known) > 2 px`, 37,654 dots split by fold area, `weighted_celf_cover`, `γ=1.35`, `min_sep_px=2.8`; hidden faults and scoring masks are never passed to an emitter.

## 3. Frozen gates

### E1: canary and surface lane screen

Using hidden positives derived from all `510..519` quadrant splits and a deterministic 250,000-negative sample:

1. Each of the eight new columns has direction-invariant ROC-AUC `<= 0.90`; above it is leakage and halts E2/E3.
2. Candidate pre-placement OOF surface vs every one of the 12 pinned peer dot rasters has absolute Spearman `<= 0.90`. A value above it is duplicate-lane drift and halts.

### E2: primary spatial holdout test

**Evaluator label:** `HOLDOUT-DTI` — `gems27.metric.dti_binary v1`, alpha `0.2`, beta `0.8`, 300 m (`3 px`) triangular kernel, whole-segment hide-and-recover quadrant splits, `buffer_px=6`. This is catalogue-internal and **not** an organizer score.

The candidate promotes from E2 only if **all** clauses pass against contemporaneous `H31-S` under identical fold/seed emissions:

1. pooled candidate HOLDOUT-DTI > pooled H31-S HOLDOUT-DTI;
2. mean paired seed delta `>= +0.0010`;
3. paired seed-bootstrap 95% CI lower bound `> 0`;
4. `>= 7/10` seed-level pooled deltas positive;
5. `>= 3/4` pooled fold deltas positive.

This is deliberately stricter than merely beating a historical scalar: it tests whether the new information exceeds the repo's current holdout-best H31 architecture on fresh, spatially separated cells. No weekly submission slot is spent when any clause fails.

### E3: byte-bound full-map artifact and run card

E3 is run once after E2, regardless of outcome; a failed result is retained under `docs/downloads/research/` as a negative deliverable. It uses two disjoint OOF surfaces (quadrants and 45° sectors) averaged 50:50, the frozen 37,654-dot B2/CELF emitter, and records:

- GeoTIFF validation: one float32 band; `EPSG:32611`; shape `3730×3292`; exact template transform; no NaN/Inf and all cells `[0,1]` in the all-finite primary; zero catalogue dots; one-member ZIP.
- Uniqueness: final directed 3-px overlap `<= 0.70` **and** surface Spearman `<= 0.90` vs the 12-raster registry; the same metrics against all local all-finite candidate files are recorded. If either registry threshold fails, log `duplicate` and do not promote.
- The JSON card must include hypothesis, mechanism, named mimic, HOLDOUT-DTI and CI, registry correlation/overlap, raster SHA-256, validator output, submission name/note `<=140` characters, and verdict (`promote` or `negative`). `ok_to_submit` may only be true when E1/E2/E3 all pass.

## 4. Sources and constraints

- USGS GeoDAWN official data release: `https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and` (tracked as `usgs-geodawn-2024-release` in `registry/sources.json`). It is provenance for the potential-field/MT grid bands; it does **not** prove this untested feature will work.
- Peacock & Bedrosian ModEM conductance / Glen et al. gravity & basement companion official releases are recorded in `registry/sources.json#siler-companions`. The current arrays are owner-mirrored, hash-pinned inputs; they are not re-downloaded from USGS in this run.
- USGS Qfaults scope: `https://www.usgs.gov/programs/earthquake-hazards/faults` (`registry/sources.json#usgs-qfaults`). This supports the catalogue-scope rationale, not candidate efficacy.
- Competition/reference contract: `https://github.com/drivendataorg/gems-prize-reference-solution`; no automated request will be made to DrivenData.

## 5. Stop rule

No outcome will be described as a leaderboard score or organizer confirmation. Seeds `510..519` cannot be reused to tweak the method. Stop after E3 or two hours, whichever is earlier. If E2 or the duplicate gate fails, the run card verdict is `negative`; the already-approved H31-1 file remains the separate selector candidate.
