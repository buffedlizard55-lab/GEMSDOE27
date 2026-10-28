# New candidate hypotheses (2026-10-28) — ranked by expected DTI gain vs cost

**Scope:** GEMSDOE24/25/27/28/30/31/32/33/36. All layers use already-restored hash-pinned data in
`data_cache/`; no new external data fetch is required for the first confirmatory test of any candidate.
Expected ΔDTI ranges are subjective planning priors for catalogue-internal whole-FID holdouts, NOT
measurements or leaderboard predictions. Novelty is relative to this checkout only.

**Current validated baseline for comparison:** H28-1 + T-v2 + H27-4 r1 passed its frozen gate on seeds
140–149 (mean paired ΔDTI +0.00294884, 3/4 folds, 9/10 seeds). All subsequent experiments (H28-3,
H27-10, H29-5-PROXY, H30-1/2/3, H32, H33-1) FAILED their frozen gates. No weekly slot has been spent
by any of them.

---

## Rank 1 — H-GEO-1: Hydrothermal alteration-front coherence from radiometric ratios

**Layers:** `geodawn_extensions_u8.tif` bands Th/K, U/K, U/Th, TMI_up150 plus `geodawn_rad_u8.tif`
bands K, Th, U, TC (all hash-pinned, already restored).

**Physical signature:** Coherent NE–SW-trending alteration fronts where K/Th and U/Th ratios are
elevated over a multi-cell corridor, with cross-profile decay away from a central axis. Hydrothermal
alteration (argillic/phyllic) along blind or covered faults produces ratio anomalies that persist
laterally for hundreds of metres even where no surface scarp exists.

**Why it catches a fault missing from USGS/INGENIOUS:** A blind fault that juxtaposes altered wallrock
against unaltered host, or that hosts clay-altered fault gouge, creates a ratio front with no
Quaternary surface rupture. The catalogue maps surface traces; alteration fronts mark the subsurface
plumbing that the catalogue omits.

**How it differs from anything in this repo:** H27-12 tested radiometric bands as *per-pixel scalar
detector features* (+rad PR-AUC 0.02532, +0.00074 — failed the +0.005 gate). No candidate in this
repo builds *spatially coherent alteration fronts* with cross-profile decay and orientation
consistency, or combines ratio anomalies with strike-parallel persistence. This is a structural
front detector, not a per-pixel classifier.

**Named non-fault mimics:** Lithologic contacts (felsic vs mafic units), alluvial-fan apron
contacts, survey flight-line residuals in the radiometric data.

**Prior expected ΔDTI:** 0.000 to +0.005. **Cost:** Low (existing hash-pinned raster, ~1 day to
implement and holdout-test). **Data gate:** All bands already restored and hash-verified.

---

## Rank 2 — H-GEO-2: Seismicity-fabric lineament ridges

**Layers:** `deq_n100a15` (earthquake distance) and `ieq_n100a15` (earthquake intensity) from
`training_features.tif` (19-band stack).

**Physical signature:** Directionally persistent, anisotropic seismicity-density ridges at
2–5 km scale. Linear concentrations of hypocenters delineate blind fault strands that may have
little or no topographic expression. The fabric is extracted as a structure-tensor coherence map
along strike, not as raw per-pixel density.

**Why it catches a fault missing from USGS/INGENIOUS:** Many Great Basin geothermal faults are
aseismic or have sparse seismicity below catalogue magnitude thresholds. A linear seismicity fabric
reveals the through-going structure that surface mapping missed because it lacks a young scarp.

**How it differs from anything in this repo:** Raw earthquake-density channels exist in the training
matrix and were included in the univariate channel AUC audit, but no candidate extracts
directional fabric/lineament coherence from them. H28-4 (listed in knowledge/07) is untested and
differs only at the listing level; no implementation exists in src/.

**Named non-fault mimics:** Unrelated earthquake swarms, completeness gradients (station density),
induced seismicity near geothermal production, basin-edge concentration.

**Prior expected ΔDTI:** 0.000 to +0.002. **Cost:** Low–medium (existing feature raster, ~1–2 days).
**Data gate:** Already restored and hash-verified.

---

## Rank 3 — H-GEO-3: Quaternary volcanic vent alignments as buried-fault indicators

**Layers:** `gdr_volcanic_vents_in_footprint.csv` (21 INGENIOUS/GDR 1391 Quaternary volcanic vent
points, hash-pinned, already restored).

**Physical signature:** Volcanic vents align along buried fault conduits that provide magma ascent
pathways. Pairs and triplets of vents within 2–8 km, collinear within ±15 deg, define a buried
fault trend. Emission is placed along the alignment trend, offset from the vents themselves.

**Why it catches a fault missing from USGS/INGENIOUS:** Volcanic vents mark crustal weaknesses
that are often blind faults with no Quaternary surface rupture mapped in the compilation. The vent
locations are an independent observation type (volcanology, not fault mapping).

**How it differs from anything in this repo:** The 21 vent points are restored locally but no
candidate in this repo has used them. H27-12 mentions them only as context ("the 21 Great Basin
Quaternary vents"), never as an emission source. This is a wholly new observation class for this
checkout.

**Named non-fault mimics:** Monogenetic volcanic fields with distributed vents not controlled by
faults, erosion-resistant volcanic cones, random vent clustering.

**Prior expected ΔDTI:** 0.000 to +0.003. **Cost:** Very low (21 points, <1 day to implement).
**Data gate:** Already restored and hash-verified (sha256 f91bafbaccaaf2754e71d60434fc0f9eb2c7b880c6e714883f4974542ff6a0bf).

---

## Rank 4 — H-GEO-4: Quality-filtered hydrothermal chemistry corridors

**Layers:** `gdr_wellspring_in_footprint.csv` (27,092 INGENIOUS/GDR 1391 well/spring rows with
temp_c, quartz/chalcedony/cation geothermometers, quality/class fields, hash-pinned, already
restored).

**Physical signature:** Spatially coherent thermal-chemical anomalies in narrow, fault-aligned
corridors — not isotropic point buffers. Quality-filtered geothermometer exceedance (quartz
geothermometer >= 150 C, cation geothermometer elevated, quality class A/B) clustered along
NW–SE trends indicates fault-focused fluid upflow.

**Why it catches a fault missing from USGS/INGENIOUS:** Permeable faults focus thermal-water
discharge and geochemical anomalies even where the fault trace itself is absent from USGS/INGENIOUS.
Measured well temperatures carry information that LiDAR scarps cannot see.

**How it differs from anything in this repo:** H27-12 tested simple thermal-distance features
(+thermal PR-AUC 0.02510, +0.00052 — failed gate) and concluded they add nothing. H-GEO-4 uses
*quality-filtered chemistry gradients clustered into corridors*, a distinct transform that was listed
as H28-5 in knowledge/07 but never implemented. It was marked "not viable" only because the official
GDR binary could not be retrieved — the CSV is already restored locally.

**Named non-fault mimics:** Lateral down-gradient thermal outflow in alluvial aquifers,
non-fault heat sources, duplicate sampling, geothermometer validity limits, groundwater displacement.

**Prior expected ΔDTI:** 0.000 to +0.003, highly uncertain. **Cost:** Medium (QC, spatial de-dup,
fold-safe rasterization; ~2–3 days). **Data gate:** CSV already restored and hash-verified
(sha256 122718e65bdf55aab0ee12ad20d80062f0deb1de957225a61ad880dd5dc196ea).

---

## Rank 5 — H-GEO-5: Multi-scale curvature persistence on detrended elevation

**Layers:** `det_elev`, `det_elev_slope` from `training_features.tif`; `relief`, `step_max`,
`lappos_max` from `lidar_scarp_features_u8.tif`.

**Physical signature:** Curvature and relief features that persist across multiple spatial scales
(0.5, 1, 2 km) with consistent sign — a fault scarp is a line whose curvature signature survives
scale-space filtering, whereas isolated channel banks, roads, and shorelines do not.

**Why it catches a fault missing from USGS/INGENIOUS:** Subtle, short scarps below legacy mapping
thresholds retain a multi-scale curvature signature. Persistence rejects isolated false positives.

**How it differs from anything in this repo:** H27-13 tested 24 oriented line-integral bands
(+0.001 PR-AUC — failed gate). H-GEO-5 uses curvature *persistence* across scales rather than
orientation integration, and is applied to the detrended elevation surface itself rather than to a
prediction surface. Distinct from H27-13.

**Named non-fault mimics:** Channel banks, road cuts, shoreline features, glacial moraine crests.

**Prior expected ΔDTI:** 0.000 to +0.004. **Cost:** Low–medium (existing raster, ~1–2 days).
**Data gate:** Already restored and hash-verified.

---

## Selection for confirmatory test

**Selected: H-GEO-1 (hydrothermal alteration-front coherence).** Rationale: (1) uses only already
restored, hash-verified bands — no external fetch risk; (2) targets blind/covered faults with
alteration halos, a genuinely different fault population from the scarp-based H19-5 family and the
topology-based T-v2 family; (3) is structurally distinct from H27-12's per-pixel radiometric test
(coherent fronts vs scalar features); (4) low implementation cost; (5) directly addresses the
"scientific discovery of geothermal vents" goal by targeting hydrothermal alteration systems.

**Stop rule:** H-GEO-1 must beat the current holdout best under a preregistered paired whole-FID
comparison before any weekly-slot consideration. Catalogue-holdout success does not prove transfer to
organizer labels. No automated DrivenData access or upload.

---

## Sources (all official, free, publicly available)

- [USGS GeoDAWN ScienceBase record (Glen & Earney, 2024)](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7) — magnetic and radiometric survey deliverables including geophysical grids.
- [INGENIOUS GDR #1391](https://gdr.openei.org/submissions/1391) — regional compilation including wells/springs, volcanic vents, temperature data.
- [USGS 3DEP 1-m DEM record](https://data.usgs.gov/datacatalog/data/USGS:77ae0551-c61e-4979-aedd-d797abdcde0e) — public-domain bare-earth DEM; local LiDAR descriptors are an owner-repository derivative.
- [NBMG Qfaults_INGENIOUS ArcGIS REST layer 0](https://web2.nbmg.unr.edu/arcgis/rest/services/Qfaults/Qfaults_INGENIOUS/MapServer/0) — 1,179 in-footprint polylines, restored locally.
- [Siler (2022) slip & dilation tendency, Great Basin (USGS ScienceBase)](https://www.sciencebase.gov/catalog/item/6296974dd34ec53d276bb33d) — optional context layer.
- [Faulds & Hinz (2015) structural settings of Great Basin geothermal systems](https://pubs.usgs.gov/of/2015/1146/) — step-over/relay settings host ~32% of characterized systems.
- [Hermant, Kiersnowski & Bellanger (2025), Stanford Geothermal Workshop](https://pangea.stanford.edu/ERE/db/GeoConf/papers/SGW/2025/Hermant.pdf) — LiDAR vs USGS scarp separation up to 400 m.
- [Berkowitz, Bour, Davy & Odling (2000)](https://agupubs.onlinelibrary.wiley.com/doi/10.1029/1999GL011241) — fracture network connectivity.
- [DrivenData GEMS competition reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) — official submission format and metric definition.
- [Tversky index](https://en.wikipedia.org/wiki/Tversky_index) — metric basis (alpha 0.2, beta 0.8).
- [EPSG:32611](https://epsg.io/32611) — competition CRS (UTM Zone 11N, NAD83).