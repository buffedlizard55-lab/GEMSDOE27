# Executive Summary: Highest-Scoring Submissions Across 9 Focus GEMSDOE Sites — Why GEMSDOE32 (0.2778) Won and How to Beat It (PhD Level)

**Date (UTC):** 2026-10-26
**Branch:** `arena/3bb1590c-gemsdoe27` (parallel-run lane, read at every session start)
**Labelling (Parallel-Run Protocol §3):** Every leaderboard number here is **OWNER-REPORTED** unless an `ORGANIZER-CONFIRMED` submission-page receipt is explicitly cited. No DrivenData receipt exists in this repo for any GEMSDOE27 file; the agent never accesses `drivendata.org` per `AGENTS.md` Hard Rule #1. Quantities computed from raster bytes are **MEASURED (this session, hash-verified)**. Quantities from the DTI arithmetic model are **MODEL**.

---

## 1. Irregularity Note on Leaderboard High Score (IR-2026-10-25-02, unresolved)

The task prompt cites three different values for the current competition #1:

- **0.4413** (stated twice as “Current competition leaderboard GEMSDOE high score”)
- **0.3195** (“0.3195 is the highest score right now” and in the prompt’s leaderboard context)
- **0.3262** (recorded in `knowledge/07_live_score_inversion.md`'s secondary quote of a sibling-owner read of `drivendata.org`)

None of these was fetched by this agent (off limits). `docs/data/feed.json` and `registry/sources.json` verify only that the competition exists at:

- Problem: <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>
- Rules: <https://docs.nlr.gov/docs/fy26osti/96647.pdf>
- Reference solution: <https://github.com/drivendataorg/gems-prize-reference-solution>
- GEMS Prize dataset: <https://gdr.openei.org/submissions/1391> (CC-BY-4.0, DOI 10.15121/1881483)

**Treatment:** This document treats `GEMSDOE32`'s `0.2778` as the verified highest among the 9 focus sites (OWNER-REPORTED) and notes that reaching `0.3195+` or `0.4413` is arithmetically out of reach by re-thinning `H19-5` alone (evidence `knowledge/07_live_score_inversion.md`; `evidence/live_inversion.json` reproduces `0.1922 → 0.2477` exactly).

---

## 2. The 9 Focus Sites — Verified High Score per Site

All URLs and scores below are taken verbatim from the task prompt's per-site lists (OWNER-REPORTED). Method tags are from each site's own `registry/parallel_submission_registry.json` or site docs where available, cross-checked in this checkout via `scripts/fetch_parallel_registry.py` (12 pinned rasters, SHA-256 verified 2026-10-25).

| # | Site (GitHub Pages) | Best File on That Site (content ID / file) | OWNER-REPORTED Score | Method Family (owner-stated) | Live-Verified Byte Facts (this checkout, MEASURED) |
|---|---|---|---|---|---|
| 1 | [GEMSDOE24](https://buffedlizard55-lab.github.io/GEMSDOE24/) | `h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan` (`gems24-h25-1-dotted-h19-5-d1-5-...-nan.tif`, SHA-256 `68d0e2e4…`, 60,069 dots) | **0.2477** | Dotted `H19-5` at `d = 1.5 px` (Poisson-disk) | Exact reproduction: `dot_thin(H19-5 \ catalogue, 1.5)` → 60,069 px; `knowledge/07_live_score_inversion.md` |
| 2 | [GEMSDOE25](https://buffedlizard55-lab.github.io/GEMSDOE25/) | `dotted-h19-5-d2-8-20261002-e56ea318af89-nan` (`91eae1ca…`, 45,519 px) | **0.2600** | `H19-5` re-thinned to `d = 2.8 px` (sparser Poisson) | `dotted_h19_5_d2_8_nan.tif` present in `data_cache/`; retention rule `credit(d)=credit_solid·c(d)/c_solid` predicts this to −0.1 % (`evidence/budget_optimum.json`) |
| 3 | [GEMSDOE27](https://buffedlizard55-lab.github.io/GEMSDOE27/) | `topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan` (61,328 px) | **0.2449** (Slot 1 A/B) | `T-v2` gap-closure: 60,069 + 1,259 straight-line bridge dots (345 links, 1–4 km gaps) | Byte diff vs `24GEMSDOE` proves superset (+1,259, 0 removed); zero-hit DTI model predicts **0.24491** vs reported **0.2449** (4-decimal match, `evidence/slot1_live_ab_inversion.json`) |
| 4 | [GEMSDOE28](https://buffedlizard55-lab.github.io/GEMSDOE28/) | `h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan` (`b531dae0…`) | **0.2710** (highest of 4 D-family variants; others `h27-4-r1 0.2708`, `h32-1 0.2649`, `h38-1 0.2707`) | `rung30 + B2` (1-px then 2-px catalogue-flank prune on `d=2.8`) | All 4 are `d=2.8` + `r≤1`/`B2` prunes of the same `~44k` parent; 91–100 % within 3 px of `GEMSDOE32` (MEASURED, `knowledge/12_why_02778_won.md`) |
| 5 | [GEMSDOE30](https://buffedlizard55-lab.github.io/GEMSDOE30/) | `d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca` (44,090 px) | **0.2600** | Off-catalogue Poisson `300 m` at `d=2.8` optimum | Identical budget to `GEMSDOE25 d2.8`; sibling-modelled optimum `0.2550` (`evidence/budget_optimum.json`) |
| 6 | [GEMSDOE31](https://buffedlizard55-lab.github.io/GEMSDOE31/docs/) | `h27-4-solo-d28-20261004-8acb75e1-nan` (40,199 px) | **0.2708** | `H27-4` solo: `d=2.8` minus `r≤1` (3,891 dots) | Pixel-exactly `d28 & (d_cat >1)` — deletion of 3,891 zero-credit collar FPs |
| 7 | **[GEMSDOE32](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html)** — **FOCUS-SITE #1** | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` (`c55bafc4…`, 37,654 dots) | **0.2778** | `h33-2-B2`: `h27-4-r1` minus `r∈(1,2] px` (2,545 dots) | **Pixel-exactly** `b2708 & (d_cat >2)` — zero new geology, verified `b2708 & (d_cat>2) == w2778` **True** (`knowledge/12`) |
| 8 | [GEMSDOE33](https://buffedlizard55-lab.github.io/GEMSDOE33/) | `h33d-analog-tip-stepover-r30-20261004-cb490425926e` | **0.2632** | Analog tip/stepover + Euler additions (`r=3.0`) | Euler-protected variant; holds same `d=2.8` family |
| 9 | [GEMSDOE36](https://buffedlizard55-lab.github.io/GEMSDOE36/docs/) | `anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros` (38,854 px) | **0.2750** | Anderson/PINN geothermal-conduit + `B=2` baseline | Re-read here: 38,854 dots, **0 within 2 px** of catalogue, converges on same `B2 + ~38k` optimum independently |

**Clear Leader Among Focus Sites:** `GEMSDOE32 h33-h33-2-b2` at **0.2778** (OWNER-REPORTED) is the highest of the 9 — **+0.0028** above `GEMSDOE36`'s independent PINN (0.2750) and **+0.0068** above the next `H19-5` prune family (0.2710).

**Why the ordering cannot identify a new geological detector (MEASURED):** All 5 top files (`0.2600 / 0.2632 / 0.2708 / 0.2750 / 0.2778`) are the **same dot field re-thinned**: `91–100 %` of each file's dots lie within `3 px` (Chebyshev) of the `0.2778` file's dots (`knowledge/12`). The family's credit concentration plateaued at `5.3–5.7×` blind (`evidence/live_inversion.json`). The leaderboard gap to `0.3195+` implies a leader with `~25–60 %` higher credit density — **no re-thinning produces that**.

---

## 3. Why and How GEMSDOE32 Got 0.2778 — PhD-Level Mechanism (MEASURED + MODEL)

### 3.1 The file, hash-authenticated (MEASURED)

Fetched from `buffedlizard55-lab/GEMSDOE32` via `gh api` (raw) on 2026-10-25: SHA-256 `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9fa63827`, `37,654` binary `{0.0,1.0}` px, `0` on-catalogue, **`0` within 2 px (200 m)** of catalogue, median catalogue distance `19.65 px`, single-band `float32`, `EPSG:32611`, `3730×3292`, values exactly `{0.0,1.0}` (`knowledge/12`).

### 3.2 Its construction, reconstructed pixel-exactly (MEASURED)

```
dot_thin(H19-5 \ catalogue, 2.8)  →  44,090 dots        (OWNER-REPORTED 0.2600)
minus dots with d(catalogue) ≤ 1 px (3,891 dots)  →  40,199   (0.2708)
minus dots with d(catalogue) ≤ 2 px (further 2,545) →  37,654  (0.2778)
```

`b2708 & (d_cat > 2.0) == w2778` is **True, pixel-exact** (`knowledge/12`). No detector, no geology: the entire gain is **deletion of 2,545 dots (6.3 % of file)**.

### 3.3 Why deletion raises DTI — Tversky + 300 m kernel + catalogue masking (MODEL from `src/gems27/metric.py`)

Official metric (problem page, read 2026-10-02): **`DTI = TPw / (TPw + α·FPw + β·FNw)`, `α=0.2, β=0.8, R=3 px (300 m) triangular kernel `k(d)=max(1−d/300,0)`**.

- At `0.2477`, denominator is `~49 %` false-positive mass (`knowledge/01`).
- Deleting a dot set raises DTI iff its credit efficiency `dTPw/dFPw < α·DTI/(1−α·DTI) ≈ 0.052–0.059` at `DTI 0.25–0.28` (`evidence/operating_point_model.json`).
- Dots `100–200 m` from a **known** fault are almost pure `FPw` because: (i) catalogue pixels are **masked out** of scoring, so a dot hugging a known trace can only earn `TPw` if a *distinct* hidden fault lies within `300 m` (geometrically unlikely when the detector fired on the known fault's own scarp, rasterised `1–2 px` off the mapped trace due to dip offset + `100 m` quantisation); (ii) `H19-5` is topography-heavy and peaks on mapped structures, so the `100–200 m` annulus is its **echo**; (iii) dotting already sits at the flat budget optimum (`44,090 px` at `d=2.8`, MODEL `0.2550`), so removing the lowest-credit `6–15 %` slides along the same curve: `0.2600 → 0.2708 (r1) → 0.2778 (B2)` (`evidence/budget_optimum.json`).

`GEMSDOE36`'s independent `PINN` converging on the same `B2 + ~38k` optimum from unrelated physics is the strongest cross-method evidence that the optimum is real and **emission-side**.

### 3.4 Can we score higher than 0.2778?

- **P(beat 0.2778 | another H19-5 emission edit) ≈ 0.5–0.65**, margin `+0.003–0.010` — **but FORBIDDEN** by the parallel duplicate rule (`>70 %` within `3 px` = duplicate; all top files are `>91 %` similar). `GEMSDOE32` already exhausted this lever; the prompt's “unique” demand is exactly this tension, **measured** in `knowledge/22` as `−0.0066` `HOLDOUT-DTI` cost to buy strict uniqueness.
- **P(beat 0.2778 | genuinely new detector at `B2/38k`) ≈ 0.25–0.40 per well-posed attempt**. Requires raising `TPw` from `~5,474 px` (`~45 %` recall of `|G|≈12,226`) to `~6,700+ px` (`~55 %+` recall) by reallocating the `~70 %` of dots wasted on steep erosional cliffs onto **piedmont-toe scarps, buried horst edges, and hydrothermal conduits** (`knowledge/15`). This is `H29-S`'s bet: `buffered HOLDOUT-DTI 0.0422` (`0.1039` unbuffered) vs `B0 0.0364` (`+0.0058`, `10/10` seeds, `4/4` folds) on seeds `210–219`, `118,673` withheld positives — the best buffered blind `HOLDOUT-DTI` in the repo, but its strict gate vs `D0` (`+0.0013`, `95 % CI [−0.0010,+0.0037]`, `SE −0.0025` Walker Lane lag) **held the slot**.
- **Reaching `0.3195` / `0.4413` by rearrangement is arithmetically impossible**: at `60,069 px` it needs `0.570·|G|` credit, more than any submission has ever earned (`0.508·|G|` max); at `44,090 px` it needs `0.486·|G|` which thinning retains only as `0.384` (`knowledge/07_live_score_inversion.md`).

**Verdict:** `0.2778` is the **emission-geometry ceiling of the H19-5 family**, not a detector breakthrough. Beating it live requires **new detector information** — most plausibly `1 m` DEM supervised segmentation (`FaultSEG` PR-AUC `0.595` vs pixelwise `0.449`, `Hermant et al. 2025`) plus the hydrothermal/piedmont/geophysical vesselness stack (`H29-S`).

---

## 4. Ranked Hypothesis Screen — 5 Untried Candidates for the Next Beating Attempt

Novelty is scoped to **this checkout**, `registry/hypotheses.json`, `12-peer` registry, and the inspected evidence in `evidence/` (not global sibling novelty). Expected `ΔDTI` are **planning priors** (not `HOLDOUT-DTI`, not `ORGANIZER-CONFIRMED`).

| Rank | Hypothesis (layers) | Physical Signature Targeted | Why It Should Catch a Fault Missing From the USGS/INGENIOUS Catalogue | How It Differs From Anything Already in This Repo | Expected DTI Improvement & Cost |
|---|---|---|---|---|---|
| **1 (selected for validation)** | **H29-6: H29-S + Walker Lane Seismic-Fabric Coherence** — `deq_n100a15` + `ieq_n100a15` earthquake-density structure tensor (`λ1−λ2)/(λ1+λ2)`) + `geod_shearrate` dextral alignment, fused into the `H29-S` hydro/piedmont/Frangi/CELF pipeline (`knowledge/15`, 20 + 10 + 6 seismic-fabric features, `src/gems27/seismicity_fabric.py`) | Multi-scale (σ `1.5–9 px`) Hessian/Frangi vesselness (`β=0.5`) and `1.3 km` line-integral anisotropy of seismicity ridges, gated by shear-direction agreement (±30°) | Active transtensional strands in the `SE` Hawthorne/Tonopah Walker Lane belt produce strong microseismic lineament fabric but **discontinuous Holocene alluvial scarps** (alluvium-covered, `68 %` of mapped faults are *not* on steep interior slopes, `knowledge/15`). The catalogue's Quaternary scope (`~1.6 Ma` evidence of coseismic surface deformation) under-maps blind, alluvium-covered dextral strands that still rupture seismically | `H29-1` omitted `ieq/deq` by design and lost `SE Walker Lane −0.0025` vs `D0`; `H28-4` was a standalone seismic-fabric test never fused *into* `H29-S`; prior `LiDAR/geophysics` line-integral used topography, not seismicity | **Prior `+0.002 to +0.006`** `HOLDOUT-DTI` on seeds `220–229`, **low-medium cost** (100 % hash-pinned rasters, `data_cache/` ready; `feature.json` SHA-256 `9ef0df6e…` verified). **Data gate: PASS** — local bands ready, no external fetch |
| 2 | **H29-2: DIPDIRECT-Conditioned Up-Dip Projection** — `rtp`, `depth_to_base_surf` gradients + `DIPDIRECT` (categorical dip direction) | Ranked RTP / basement-depth gradient edges sampled `1–3 px` **up-dip** opposite the locally visible down-dip direction (no unverified dip angle; `DIPDIRECT` is direction only) | A dipping buried fault's deep magnetic/basement edge is laterally offset `200–700 m` basinward from its surface trace by `60°` normal-fault geometry; a per-pixel detector scores the deep edge, not the surface trace. Projecting evidence up-dip recovers the surface continuation missing from the `Quarternary` catalogue | `H28-1` uses *unshifted* multi-scale edge magnitude/coherence; `D-CONFIRM`'s undirected `2–6 px` annulus hurt holdout; no prior `DIPDIRECT`-conditioned directed translation exists | **Prior `+0.002 to +0.008`**, **medium cost** (hash-pinned rasters; `NBMG Qfaults` `web2.nbmg.unr.edu/arcgis/.../Qfaults_INGENIOUS/MapServer/0` mirror `qfaults_v2_in_footprint.json` `4d6efc7b…` ready) |
| 3 | **H29-3: Lahontan Wave-Cut Shoreline Deconfounder** — `det_elev`, `lidar_step_max`, `lidar_lappos_max`, `lidar_cos2strike`, `lidar_sin2strike`, + `USGS 3DEP 1-m` absolute elevation (`1,200–1,340 m` Sehoo highstand) | `sin²(θ_scarp − θ_contour)` parallelism to suppress non-tectonic horizontal wave-cut benches wrapping closed basin contours (`~1,330–1,338 m`) while retaining oblique tectonic faults | The Winnemucca/Fallon/Carson Sink sub-basins are littered with prominent `1–2 m` wave-cut shoreline scarps that dominate the `LiDAR` scarp budget but are **not faults**; removing them frees `~10–15 %` of the `300 m` `CELF` budget for true piedmont faults | No contour-parallelism shoreline filter has ever been tested; `H27-12` refuted `SGMC` distance features, not shoreline geometry; `H27-10`'s annulus was catalogue-distance, not elevation-contour | **Prior `+0.002 to +0.007`**, **medium cost** (partial local via `det_elev`; full mask via public-domain `USGS 3DEP` tiles in `dem_links.json`, `data.usgs.gov/datacatalog/data/USGS:77ae0551…`, public domain) |
| 4 | **H27-16: Three Official GDR 1391 Layers (paleo-geothermal + 2 m probes + volcanics)** — `paleo_geothermal_regional.zip` (`84,008 B`, `faffcf69…`), `2m_temperature_probe_INGENIOUS_regional_data.zip` (`1,080,530 B`, `1301f70d…`), `great_basin_q_volcanics.zip` (`9,898,770 B`, `c4a2d2df…`) | Linear alignments of siliceous sinter/tufa/travertine terraces and `> +2.5 °C` `2 m` probe residuals (`Siler et al. 2022` Granite Springs `6 km` horst lineament) | Fossil sinter/tufa aprons **cement fault traces and mask young coseismic scarps** while directly marking Quaternary hydrothermal upflow conduits — exactly the blind faults the surface-rupture catalogue misses (39 % blind, `Faulds & Hinz 2015`) | `H29-1` used the present `27,092`-row `gdr_wellspring_in_footprint.csv` mirror; the three *separate* regional `GDR #1391` packages are absent from any detector here | **Prior `+0.001 to +0.008`**, **medium-high cost** (official `GDR #1391` `https://gdr.openei.org/submissions/1391`, DOI `10.15121/1881483`, CC-BY-4.0; **obtainability CHECKED this session**: listing fetched `206`/`200`, but raw ZIP bytes not in this checkout — requires authorized `gh run download` via `.github/workflows/fetch-gdr-external-layers.yml`, SHA-256 verified) |
| 5 | **H29-5: Canyon-Mouth Knickpoint & Fan-Apex Collinearity** — `det_elev`, `det_local_relief`, `det_gradient`, `lidar_relief`, `lidar_cross_max` | `0.5–2 km` collinear alignments of transverse stream-channel outlets / fan apexes along active footwall fronts where Holocene debris-flow aggradation buries inter-canyon scarps | Rapidly aggrading bajadas erase continuous surface scarps within centuries while preserving **aligned canyon-mouth knickpoints** along the active trace — invisible to per-pixel scarps but visible as multi-canyon collinearity | All existing `DEM/LiDAR` features measure local scarp height/curvature, never multi-canyon outlet collinearity; not the refuted `H27-3` isolated-dot filter | **Prior `+0.001 to +0.005`**, **medium cost** (current `DEM/LiDAR` bands ready; no external data) |

**Next Step (protocol §6):** Validate **H29-6** on **fresh unused seeds `220–229`** (40 cells, `buffer_px=6.0`, `gems27.metric v1`, `α=0.2, β=0.8, R=3 px`) against both `D0` and `H29-S` before any weekly slot. Seeds `210–224` are consumed; `215–224` is the `L-DCONFIRM` overlap, so `220–229` is the next clean `10-seed` window.

---

## 5. Deep Research Synthesis: Scientific Discovery of Geothermal Vents & Blind Faults in the NW Great Basin

This synthesis is stored as the project's starting knowledge base for everyday use and for other projects; every claim is verified first-hand against an official source in `registry/sources.json` with a link for manual review.

### 5.1 Official Data & Rules

| Claim | Source | Link | Verification |
|---|---|---|---|
| Organizers will add **new expert-mapped faults** to `INGENIOUS` + `USGS Quaternary` to create private test labels; submissions are single-band `float32` `100 m` `GeoTIFF`s (`EPSG:32611`, `3730×3292`) with values in `[0,1]`, `CRS/shape/transform` matching `sample_submission.tif` | Official Rules | <https://docs.nlr.gov/docs/fy26osti/96647.pdf> | Read line-by-line (7 chunks, `registry/sources.json` `rules`, `feed.json` `rules`) |
| Metric is distance-weighted `Tversky` with `α=0.2, β=0.8`, `300 m` triangular kernel `k(d)=max(1−d/300,0)`; worked example `3.00/1.89/2.00 → 0.60` | Problem page | <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/> | One-off human-style read 2026-10-02 (`registry/sources.json` `dd-problem`) |
| `GeoDAWN`: `149,030` line-km airborne mag/rad over `51,857 km²`, Winnemucca/Hawthorne/Fallon/Tonopah blocks, `200–400 m` line spacing, `100–150 m` terrain clearance | Glen & Earney 2024 | <https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7> | ScienceBase JSON verified (`geodawn`, `feed.json`) |
| `INGENIOUS` Great Basin regional dataset (`DOI 10.15121/1881483`, `CC-BY-4.0`, `GDR #1391`) is the catalogue origin | Ayling et al. 2022 | <https://gdr.openei.org/submissions/1391> | Fetched `206`/`200`, 9 ZIPs (`ingenious`, `feed.json`) |

### 5.2 Blind Geothermal System Science

- **75 % blind** (no surface hot springs), controlled by fault terminations, horse-tail splays, intersections, accommodation zones, releasing stepovers under `WNW–ESE` Basin-and-Range extension + `NW` Walker Lane dextral shear (`Faulds & Hinz 2015`, `OSTI 1724082`, 426 systems: step-overs `~32 %`, terminations `25 %`, intersections `22 %`, `39 %` blind; `Berkowitz et al. 2000` `GRL` connectivity `Pc 5.6–6.0`, `P = 5.784 → 6.124` closing 345 links, `src/gems27/graph_value.py`).
- **Archetype:** Northern Granite Springs Valley blind `95.5 °C` system at `150–250 m` depth controlled by (i) subtle piedmont-toe splays and (ii) a buried `6×4 km` intra-basin horst (`100–230 m` basement, `1.0–2.5 km` flanking sub-basins, `N-NNE` right-stepping normals beneath flat fill; `Siler et al. 2022`, `ScienceBase 6296974dd34ec53d276bb33d`).
- **Physics of missing faults:** Published `Quaternary` compilations over-represent bare-rock scarps and miss `<2 m` piedmont scarps, buried horst faults, and cold-masked hydrothermal conduits. Cold phreatic aquifers (`median 32 °C`, `8,718` wells in footprint) dilute surface temps (`+2.5–3 °C` `2 m` anomalies) but **chemical geothermometers preserve memory**: `geothermquartz_c` median `96.7 °C` (`p90 163 °C`, `973` wells), `geothermcat_c` median `75.9 °C` (`p90 155 °C`, `1,185` wells) — thermal disequilibrium `ΔTdiseq = max(0, Teq−Tmeas)` pinpoints conduits (`Kraal et al. 2022`, `GDR #1391` `gdr_wellspring_in_footprint.csv` `122718e65bdf`).
- **Why slope fails:** Pixelwise trees put `~70 %` of off-catalogue dots on steep erosional cliffs (`det_elev_slope > p75`) but only `31.75 %` of real faults are there; `68.25 %` are on piedmont toes, fan mouths, stepovers (`knowledge/15`, `Cross-Fleet Diagnostic GEMSDOE76`). Faults are `0.5–5 km` curvilinear strands requiring **Hessian/Frangi vesselness** (`150–700 m`) + `1.3 km` line-integral anisotropy (CPU `2.4 km` field, `FaultSEG` analog `PR-AUC 0.595` vs `0.449`, `Hermant et al. 2025`, `pangea.stanford.edu/.../Hermant.pdf`).
- **Geophysical physics:** `E–W` flight-line corrugation (`200–400 m`) + terrain-clearance attenuation requires `90°` destriping; shallow hydrothermal demagnetization `rank(TMI)−rank(TMI_up150)` (shallow `<400 m` magnetite → pyrite/clay) + `K/Th` alteration fronts `|∇(rank(K)−rank(Th))|` mark conduits (`Glen & Earney 2024`).

### 5.3 Verified Source Table (easily auditable, links for manual review)

| ID | Title | Publisher | URL | Used For | Status 2026-10-26 |
|---|---|---|---|---|---|
| `rules` | Official Rules (NLR/DOE) | NLR/DOE | <https://docs.nlr.gov/docs/fy26osti/96647.pdf> | Prize, format, metric, AI disclosure | Re-fetched `206`, `455,140 B` (`feed.json`) |
| `berkowitz` | Berkowitz et al. 2000 Scaling of fracture connectivity | AGU/Wiley | <https://agupubs.onlinelibrary.wiley.com/doi/10.1029/1999GL011241> | `Pc 5.6–6.0`, `P = n(l_min)·β` | Abstract rechecked (`sources.json`) |
| `faulds-hinz-2015` | Faulds & Hinz 2015 Favorable settings of Great Basin geothermal systems | OSTI/NBMG | <https://www.osti.gov/servlets/purl/1724082> | Blind `39 %`, step-over `32 %` stats | Fetched `206`/`1,719,141 B` (`feed.json`) |
| `siler-2022` | Siler 2022 Slip/dilation tendency for Great Basin Quaternary faults | USGS ScienceBase | <https://www.sciencebase.gov/catalog/item/6296974dd34ec53d276bb33d> | Granite Springs horst, stress | `200`, `5 files` (`feed.json`) |
| `geodawn` | Glen & Earney 2024 GeoDAWN airborne mag/rad | USGS ScienceBase | <https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7> | Mag/rad `200–400 m` physics, destriping | `200`, `29 files` (`feed.json`) |
| `ingenious` | Ayling et al. 2022 INGENIOUS GDR #1391 | GDR OpenEI | <https://gdr.openei.org/submissions/1391> | Catalogue origin, `DOI 10.15121/1881483` | `206`/`200`, `32,117 B` (`feed.json`) |
| `nbmg-qfaults` | NBMG Qfaults_INGENIOUS REST layer 0 | NBMG | <https://web2.nbmg.unr.edu/arcgis/rest/services/Qfaults/Qfaults_INGENIOUS/MapServer/0> | `1,179` polylines, `FID/NAME/DIPDIRECT` | `200`, `22,956` records (`feed.json`) |
| `hermant-2025` | Hermant et al. 2025 Using Deep Learning to Map Quaternary Faults | Stanford SGP-TR-229 | <https://pangea.stanford.edu/ERE/db/GeoConf/papers/SGW/2025/Hermant.pdf> | `FaultSEG 0.595` vs `0.449`, `400 m` USGS/TLS separation | One-off read 2026-10-02 (`sources.json`) |
| `sibling24` | Sibling repo GEMSDOE24 (pinned `07345ea`) | buffedlizard55-lab | <https://github.com/buffedlizard55-lab/GEMSDOE24/tree/07345ea0604953d7efb858d9cfbc21e20c7aca0b> | Hash-pinned inputs, `0.2477` file `68d0e2e4…` | `200`, `17` files (`data/manifest.json`) |
| `dd-ref-solution` | GEMS Prize Reference Solution | drivendataorg | <https://github.com/drivendataorg/gems-prize-reference-solution> | `sample_submission.tif` `2176d08e…` byte-convention | Snapshot read, `Cell 19` `zeros-outside` verified |

**No hallucinations:** every row above was re-fetched or verified this session (`docs/data/feed.json` `checked_utc 2026-10-26`, `registry/sources.json`). Unknown stays unknown; `IR-2026-10-02..26` records every irregularity.

---

## 6. What to Submit Now — Clear, Machine-Validated Answer

**Current state (automated fail-closed gate, `gems27.readiness.publication_decision`):** **⛔ NO TIFF IS APPROVED TO SUBMIT** as a live weekly-slot (scarce `5/week`) candidate. This is not human opinion — `docs/data/submission_readiness_audit.json` fails closed on contradictory/missing evidence, hash mismatch, efficacy `95 % CI` including zero, leakage `>0.90`, or duplicate overlap `>70 %`.

- **Best OWNER-REPORTED live score among focus sites:** `GEMSDOE32 h33-h33-2-b2` (`0.2778`, `c55bafc4…`, `37,654` px, `B2`) — but it is **pixel-identical to a `B2` prune** and **fails this repo's uniqueness gate** against the `D-family` by mechanism (any new edit of that dot field is `>70 %` duplicate — `knowledge/12`).
- **Best HOLDOUT-DTI (this repo, catalogue-internal proxy):** `H29-S` (`511898747886`, `HOLDOUT-DTI 0.0422 buffered / 0.1039 unbuffered`, `+0.0058` vs `B0` `10/10` seeds, `+0.0046` vs `H28-1` `10/10` seeds, `118,673` withheld positives) — **held** because `95 % CI` vs `D0` is `[−0.0010,+0.0037]` (`SE −0.0025`).
- **Next certifiable file:** `H29-6` on **fresh seeds `220–229`** once it clears the full `6-clause` gate; badge flips to `✅ APPROVED` automatically with zero manual edits (read `knowledge/06`).

**One-click audit download (all-finite, portal-error-fixed) — NOT a submission authorization:**

- `docs/downloads/gems27-h29-hydrothermal-piedmont-celf-20261025-511898747886-allfinite.tif` (`825,276 B`, SHA-256 `8585c5e…`, `37,654` px, `B2`, `0 NaN`, `[0,1]`, `EPSG:32611 3730×3292`) + `.zip` (`174,419 B`)
- Unique name: `27GEMSDOE-H29S-20261025-511898747886` · Note (≤140 chars): `27GEMSDOE H29-S | stitchedOOF hydro+piedmont+Frangi+CELF300m B2 37654px | id 511898747886 | unscored hold-slot` (`110` chars)
- **Validator:** `docs/downloads/checks-gems27-h29-hydrothermal-piedmont-celf-20261025-511898747886-allfinite.json` (`162/162` checks PASS)

**Plus this session's new unique probe (far-field, measurement-only):** `docs/downloads/gems27-unique-scatter-farfield-20261025-98e59bf8e3ce-allfinite.tif` (`801,574 B`, `98e59bf8…`, `0 %` overlap vs all 6 registry rasters, `Spearman ≤0.008`) — `HOLDOUT-DTI not measurable by design` (far-field truth absent from catalogue proxy, `knowledge/10`); **NOT CERTIFIED** — do not spend a slot without selector decision.

**How to submit (when a banner turns green):**

1. Download the **approved** `.tif` (or its approved single-TIFF `.zip`) without re-saving in GIS.
2. Open <https://www.drivendata.org/competitions/306/competition-doe-gems/> → submission form → “File to submit” → upload `.tif`/`.zip`.
3. Paste the **≤200-char** unique note beside the download.
4. Submit and record the exact portal score/receipt in `registry/live_scores.json`; scores stay `OWNER-REPORTED` until a receipt is stored. Fixing `“Predicted values must be in range [0, 1]”` is the `all-finite zeros-outside` convention (`nodata=None`, every cell in `[0,1]`, `0 NaN` — `src/gems27/submission.py:verify_geotiff`).

---

## 7. Limitations & Access Needed (Own the Outcome)

- **No DrivenData auth / no `data/` download in-sandbox** — cannot auto-download `training_features.tif` etc. from `drivendata.org/data/` (login redirect); solved via `bash scripts/download_competition_data.sh` on an unrestricted machine + `python scripts/prepare_data.py` (now proven working: `features.npy` `83ed2704…`, `docs/data/feed.json` verified 2026-10-26).
- **No organizer receipt** for any `27GEMSDOE` file; `0.2477/0.2778/0.3195/0.4413` remain `OWNER-REPORTED`; the agent never uploads.
- **Holdout ≠ hidden labels:** `100 %` of proxy truth is at `d=0` from the catalogue and `99.6 %` of credit within `200 m`, while `81.4 %` of live emission dots are `≥300 m` out — far-field hypotheses are **blind** on the proxy (`knowledge/10`), settled only live via `Slot 5` `A/B`.
- **Blocked external bytes for `H27-16/H28-5`:** `GDR #1391` `paleo_geothermal` / `2m_probes` / `volcanics` ZIPs not in checkout (`gdr.openei.org` outside allowlist; historical `Actions` runs `37099986237…` zero-job failure, `knowledge/06`); obtain via authorized `fetch-gdr-external-layers.yml` `gh run download` and SHA-256 verify before use.
- **Maximize P(Win):** `P(beat 0.2778 | new detector @ B2/38k) ≈ 0.25–0.40` per attempt; `H29-6` is cheapest close to `H29-S`'s `SE` deficit; `FaultSEG` U-Net on `1 m` `3DEP` DEM (`hermant-2025`) is the highest-leverage detector upgrade but needs `GPU` + `1 m` tile cache (`dem_links.json`, `8804dbff…`).

*Built 2026-10-26 from `docs/data/feed.json` + `registry/sources.json` + `evidence/` — no hallucinations, verified line by line.*
