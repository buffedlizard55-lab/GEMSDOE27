# 45 — Preregistration H34-1: hot-station collinearity corridors (2026-10-31)

**Written before any H34-1 feature, surface, emission or holdout score was computed, and before seeds 900–909 were used.** The file's SHA-256 is recorded in `evidence/h34_1_run_card_2026-10-31.json` at run time. Any change after the run is a deviation and must be disclosed.

**Budget:** 1 experiment (E1 canary + pre-placement surface, E2 holdout, E3 raster + uniqueness). The session budget is 3 experiments or 2 hours; this session stops after this one unless a new preregistration is written.

**Lane (self-selected; see `IR-2026-10-31-lane-paragraph-missing`):** the prompt's single-method paragraph is absent again. This lane was chosen from the repository's own untried list (`knowledge/19`, `knowledge/38`) and from the data that is actually present. It is recorded as a self-assignment, not as a user-assigned lane.

## 0. Hypothesis screen (3–5 candidates, ranked by feasibility × novelty)

| Rank | ID | Layers | Physical signature | Why it would be a catalogue-missing fault | Named non-fault mimic | Already tested here? | Data gate in this sandbox | Decision |
|---|---|---|---|---|---|---|---|---|
| 1 | **H34-1 hot-station collinearity** (this file) | GDR #1391 INGENIOUS quartz geothermometer ≥120 °C (973 rows with `geothermquartz_c`, before QA) (`geothermquartz_c`; owner-mirror CSV `data_cache/gdr_wellspring_in_footprint.csv`) | ≥3 hot stations (≥120 °C quartz) on one straight 1.5–6 km line, within 300 m of the line | Hot fluid moves along a permeable structure; stations aligned along it can reveal a buried trace with no surface expression | Aligned water wells along roads, irrigation or pipelines; valley-axis regional aquifer discharge | **Not run.** Distance-to-any-spring features (H27-12) and chemistry *re-ranking* of a detector (H30) were tested. Line geometry of hot stations was not | PASS (CSV present, SHA-pinned to the owner mirror; the official GDR bytes are not re-hashed here) | **RUN** |
| 2 | H28-5 chemistry-gradient corridors | Same CSV: `temp_c`, `geothermquartz_c`, `geothermchalc_c` | Ridges of the gradient of a smoothed chemistry field | Sharp fluid-chemistry contrasts mark permeable boundaries | Sampling bias; depth-dependence of well temperature; aquifer transport | **Partly.** H30's `build_chemistry_field` (`src/gems27/hydrochemistry.py`) builds the same field, used only as a bounded re-ranker (negative) | PASS | Not run: close to a repeat of H30's field (the standalone emitter is the only new part) |
| 3 | H28-7 radiometric alteration lineaments | GeoDAWN K, Th, U (`geodawn_rad_u8.tif`, uint8) | Coherent 1–2 km alteration fronts | Fault-controlled fluid alteration extends beyond the trace | Lithology, soil, drainage, survey seams | **Yes.** `knowledge/38`: the same edges were tested as detector augmentation (`dip_rad_features`, `h29_k_th_alter_grad` canary) and `knowledge/38` calls the candidate a repeat | PASS | **Not run** (duplicate of a tested family) |
| 4 | H27-16 GDR #1391 sinter/tufa, 2 m probes, volcanics | GDR #1391 packages | Sinter alignments; probe residuals | Fossil sinter masks scarps while marking upflow | Lacustrine tufa | No | **BLOCKED.** `gdr.openei.org` returns HTTP 000 from this sandbox (checked 2026-10-31, see §6) | Not runnable |
| 5 | H29-5 canyon-mouth knickpoint / fan-apex collinearity | Routed drainage from 1 m 3DEP DEM | Collinear outlets and fan apices | Aggrading bajadas bury scarps but keep aligned outlets | Resistant hogbacks crossed by streams | Only the proxy (`H29-5-PROXY`, negative) | **BLOCKED.** No raw DEM; `prd-tnm.s3.amazonaws.com` returns HTTP 000 (§6) | Not runnable |
| — | Quaternary vent alignment | `gdr_volcanic_vents_in_footprint.csv` | Vent collinearity as dike/fissure proxy | Dikes and faults share orientation | Eruptive-field elongation | No | PASS but **21 vents in footprint** | Rejected on sample size: a whole-segment holdout would withhold ≈4 points per seed |

## 1. Hypothesis (H34-1)

A fault that the INGENIOUS/USGS catalogue omits can carry hot water from depth. Where at least three quartz-geothermometer stations with T ≥120 °C lie within 300 m of one straight line spanning 1.5–6 km, that line is a candidate buried trace. Mechanism: a permeable conduit concentrates upflow, so stations sample it along its strike.

## 2. Frozen method

- **Station table.** Rows of `gdr_wellspring_in_footprint.csv` with finite `geothermquartz_c` and 20 ≤ T ≤ 300 °C (QA: quartz geothermometer values below 20 °C are not physical for these waters; the CSV contains −34.4 °C). Duplicate stations in one grid cell are merged by median T. **The `dist_known_fault_px` column is never read** (it is catalogue-derived).
- **Hot stations.** T ≥ 120 °C (fixed; not tuned).
- **Candidate lines.** Every pair of hot stations at 15 ≤ d ≤ 60 px (1.5–6 km). Support = other hot stations whose perpendicular distance to the segment is ≤ 3 px and whose projection falls inside the segment. Accept the line if it has ≥1 supporting station (≥3 hot stations in total).
- **Line raster.** A line of weight w (= number of stations on it) fills the pixels within 1 px of its segment (`skimage.draw.line`). L(x) = max over lines of w·mask. Surface S = Gaussian(L, σ=1) divided by its maximum, zero outside accepted lines, restricted to the footprint.
- **Emission.** Identical to H33-1 (`run_h33_lane.emit`): ridge NMS of S, cells within 2 px of visible faults excluded, Poisson-disk spacing 2.8 px, budget 37,654.
- **Candidate arm** (H34-1): S-emission **with** the complement constraint: dots must lie more than 3 px from every positive pixel of the 12 pinned registry rasters. This makes the file unique within those rasters by construction (the same design as H33-1).
- **Matched control B_c:** base-32 emission with the same complement constraint. This isolates the detector, not the constraint.
- **Secondary control B_u:** base-32 emission without the constraint (the historical H33 control).
- **Holdout:** `holdout.make_segment_split` (whole-FID, 20 % of vector groups hidden, quadrant-stratified), buffer 6 px, visible faults masked pixel-exactly, evaluator `gems27.metric.dti_binary` (α=0.2, β=0.8, 300 m triangular kernel). Base-32 training uses the buffered training mask.
- **Seeds:** **900–909**. Not used before this file was written (grep of `evidence/` and `knowledge/`: no seed list contains 900–909).

## 3. Gates

- **Collinearity null (E1 diagnostic, pre-registered stop).** Permute the station coordinates uniformly inside the footprint (same count, same T) and recount accepted lines (5 permutations, fixed RNG 45). If the real count is ≤ 1.5 × the mean null count, stop: the hot-station geometry is not distinguishable from random placement.
- **E1 canary.** Direction-invariant ROC-AUC of S on the union of withheld positives vs a background sample. AUC > 0.90 is leakage. Stop.
- **E1 surface.** Absolute Spearman of S vs each of the 12 pinned rasters on a fixed 400,000-pixel sample. > 0.90 is a duplicate. Stop before placement.
- **E2 efficacy (vs matched control B_c).** Promote only if mean paired seed Δ ≥ +0.001, 95 % seed-bootstrap CI lower bound > 0, ≥7/10 seeds positive, ≥3/4 quadrant folds positive, and pooled candidate > pooled B_c.
- **E3 uniqueness (final dots).** Directed 3-px overlap ≤ 0.70 and |surface Spearman| ≤ 0.90 against each pinned registry raster, plus the same 0.70 check against every `*allfinite.tif` in `docs/downloads/` (local prior rasters). The H34-1 file also has to pass `check_parallel_uniqueness.py`.
- **E3 format.** Single-band float32 GeoTIFF with the template CRS/shape/transform, zeros outside the footprint (allfinite variant), values in {0,1} inside, plus a NaN-outside twin. Note ≤140 characters.
- **Verdict.** `promote` only if E1, E2 and E3 all pass. Otherwise `negative`. Even a negative TIFF is written as a research artifact, labelled **NOT OK TO SUBMIT**. Nothing here selects a weekly slot.

## 4. What the numbers will and will not mean

- HOLDOUT-DTI is catalogue-internal. It is not an organizer score and is never converted into one.
- The hidden positives are catalogue segments. Hidden segments are spatially close to visible ones, so a detector that avoids catalogue neighbourhoods (as this one does through the complement constraint) is penalised by construction. A holdout loss therefore does not prove the candidate is worse on the blind organizer truth. This is a known limit (`knowledge/30`, §Why 0.2778 is not a template).
- Line-collinearity is also expected to produce fewer dots than the 37,654 budget. The number of emitted dots is reported, not padded.

## 5. Named non-fault mimics (run-card copy)

Water-well alignments along roads, field boundaries, irrigation ditches and pipelines; valley-axis regional groundwater discharge; geothermometer scatter from silica loss and mixing; sampling bias (wells drilled where accessible); duplicate stations.

## 6. Source checks made for this preregistration (2026-10-31, this sandbox)

- `https://gdr.openei.org/submissions/1391`: HTTP 000 (not reachable). The H27-16 and H28-5 data gates depend on it.
- `https://prd-tnm.s3.amazonaws.com`: HTTP 000 (not reachable). The H29-5 data gate depends on the 1 m DEM.
- `https://www.drivendata.org`: HTTP 000. Not accessed by agent policy; checked only for reachability.
- `https://raw.githubusercontent.com/...`: HTTP 000 (so the reference notebook must come from `codeload.github.com`).
- Local CSV `data_cache/gdr_wellspring_in_footprint.csv`: 27,092 rows, 12,570 unique (row, col) stations, 973 rows with a finite `geothermquartz_c` (row count, before the 20–300 °C QA and the (row, col) merge). These numbers were read in this session from the restored file.

## 7. Addendum A (written 2026-10-31, before any E2 holdout score or any H34-1 raster)

**Why this addendum exists.** The uniform-random collinearity null in §3 is not a valid null for clustered stations. Exploratory counts (this session, before this addendum; reproducible with the functions in `src/gems27/hot_station_lines.py`) found:

- Real station layout: 564 stations after QA, 143 hot (≥120 °C), **149 accepted lines** (41 with ≥3 supporting stations, 25 with ≥4). The median nearest-neighbour spacing between stations is **11.7 px** (1.17 km).
- Uniform-random placement of the same stations (5 draws): 0–2 lines. This is not a fair comparison: the real stations are clustered, so random placement destroys the clusters.
- Cluster-preserving jitter null (each station displaced uniformly inside a disk; 10 draws per radius): R = 10 px → mean 152.8 lines (range 141–173); 41 real ≥3-station lines vs null mean 34.9; 25 real ≥4-station lines vs null mean 16.9. R = 20 px → mean 155.8 lines, but ≥3-station mean 16.1 and ≥4-station mean 4.0; R = 30 px → 135.4 lines, ≥3-station mean 7.4.

**Choice of null (fixed here, before E2).** R = 10 px is the cluster-preserving null: displacement is below the median nearest-neighbour spacing (11.7 px), so local clusters survive and only alignment is perturbed. R = 20 and 30 px displace stations beyond their neighbours and destroy the clusters themselves, so they test something else. I disclose that R = 20 px would show a larger excess (≥3-station ratio about 2.5); the choice of R = 10 px is a researcher degree of freedom, made after this exploratory look, and the result is reported with that caveat.

**Amended gates.**

1. The uniform-random null in §3 is retained as registered. It passed (real 149 vs mean 0.4), so **E2 and E3 are permitted to run under the registered protocol.** This passage is not evidence of collinearity; it only shows that the registered gate was not a sufficient null.
2. **New promotion gate A2 (required for `promote`, not for running E2/E3):** with 20 cluster-preserving jitter draws at R = 10 px (RNG seed 45), the ratio real / null-mean must exceed 1.5 for both the total line count (support ≥1) and the ≥3-station count (support ≥3). If either ratio is ≤ 1.5, the verdict cannot be `promote`, and the line geometry is reported as clustering-explained.
3. The verdict is `promote` only if E1 (registered), E2, E3 and A2 all pass. Otherwise `negative`. A negative TIFF is written only as a research artifact, labelled **NOT OK TO SUBMIT**, and is not authorized for a weekly slot.

**Expected outcome from the exploratory numbers.** A2 is expected to fail on the total count (ratio ≈ 0.98) and is borderline on the ≥3 count (ratio ≈ 1.17). This is disclosed here so the verdict is not read as a surprise.
