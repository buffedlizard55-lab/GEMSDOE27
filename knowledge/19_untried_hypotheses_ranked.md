# 3–5 untried geological hypotheses, ranked (PhD-level)

**Screening basis:** expert priors on potential paired catalogue-holdout ΔDTI × testability / engineering cost. Planning priors are not leaderboard predictions. Baseline: current in-repo OOF best (H28-1 edges + T-v2 + H27-4 r1 prune), seeds 140–149, mean paired ΔDTI +0.00294884, 3/4 folds, 9/10 seeds. Catalogue-internal component-hidden four-quadrant holdout; cannot see far-field (>300 m) credit by design.

---

## H27-16 — Three official GDR 1391 layers absent from the detector (Rank 1)

**Layers:** GDR #1391 paleo-geothermal regional features (sinter/tufa/travertine, altered-bedrock vectors; 84,008 B, sha256 `faffcf69…`); INGENIOUS 2 m temperature-probe records (1,080,530 B, sha256 `1301f70d…`); Great Basin Quaternary volcanics polygons (9,898,770 B, sha256 `c4a2d2df…`).

**Physical signature:** Surface and shallow-subsurface thermal/chemical/volcanic evidence for fault-focused fluid flow — sinter deposits, alteration halos, 2 m sediment temperature anomalies, and young volcanic unit boundaries/vent alignments.

**Why it catches catalogue-missing faults:** A permeable fault can localise hydrothermal alteration, thermal anomalies, or young volcanic alignments even where no Quaternary surface trace is catalogued (USGS scope ≈ coseismic surface deformation in ~1.6 Ma). These are blind or alluvium-covered structures invisible to lidar-scarp detectors.

**Confounders:** Sampling density, groundwater transport, non-fault heat sources, volcanic contacts unrelated to the target fault. Prior thermal-point-distance features were measured near zero (Addendum D).

**Differs from repo:** The checkout holds 21 vent points and 27,092 well/spring rows, but not these regional paleo-geothermal features, 2 m probes, or volcanics polygons. The existing thermal-distance feature arm was measured near zero; this tests new records and polygon geometry.

**Expected holdout ΔDTI:** [0.0, +0.006]

**Cost:** Medium-high — requires authorized data retrieval and SHA-256 checksum verification, then fold-safe vector reading/rasterization and separate feature arms per layer group.

**Data gate:** Official GDR #1391 listing and hash pins exist; the sibling 16GEMSDOE runner record reports `ok:true` for the three packages on 2026-09-30. Raw packages are **absent from this checkout**. Reviewed workflow runs 37099986237, 37100053264, 37100608786, 37100751573, 37100935082, 37101134684 all concluded failure with zero jobs and no logs. Cause unknown; do not infer source unavailability. Obtain bytes through an authorized runner or official source and verify SHA-256 before any feature use.

**Sources:** https://gdr.openei.org/submissions/1391 ; https://gdr.openei.org/files/1391/paleo_geothermal_regional.zip ; https://gdr.openei.org/files/1391/2m_temperature_probe_INGENIOUS_regional_data.zip ; https://gdr.openei.org/files/1391/great_basin_q_volcanics.zip

**Status:** UNTRIED; official source packages not yet present in this checkout.

---

## H28-4 — Anisotropic seismicity-fabric lineaments (Rank 2)

**Layers:** `deq_n100a15` (earthquake density catalog A), `ieq_n100a15` (earthquake density catalog B), `geod_shearrate` (geodetic shear rate) — cols 8, 14, 5 of the prepared 32-band matrix.

**Physical signature:** Directional persistence of earthquake-density ridges aligned with local shear-rate gradient orientation, computed via directional morphological line-strength at 0/45/90/135° and shear-direction agreement within 30°.

**Why it catches catalogue-missing faults:** A linear earthquake fabric may expose a blind active strand without a clear young surface scarp. Currently-active slip localised along a fault that lacks Quaternary surface expression is absent from the catalogue but present in seismicity.

**Confounders:** Aseismic faults, catalogue-completeness gradients, earthquake swarms unrelated to a single fault, over-smoothed density products.

**Differs from repo:** No previous candidate uses directional seismicity fabric. The refuted oriented line-integral arm (H27-13) used topography/geophysics bands, not seismicity, and targeted kilometre-scale linear continuity rather than shear-aligned earthquake persistence.

**Expected holdout ΔDTI:** [0.0, +0.002]

**Cost:** Low-medium — current feature raster only; no new external data.

**Data gate:** Existing hash-pinned raster bands; no new external data. Feature module: `src/gems27/seismicity_fabric.py`.

**Status:** **TESTED THIS SESSION (2 seeds 230–231): NEGATIVE.** Mean paired gain −0.00067 vs baseline; 0/2 seeds improved; 2/4 folds improved. Gate FAIL. Not promoted to a weekly slot. Full evidence: `evidence/h28_4_quick.json` (2-seed probe); full 10-seed run would use seeds 230–239.

---

## H28-5 — Quality-filtered hydrothermal chemistry gradients (Rank 3)

**Layers:** GDR/INGENIOUS wellspring CSV: `temp_c`, `geothermquartz_c`, `geothermchalc_c`, `geothermcat_c`, `thermalclass`, station name, coordinates (27,092 rows, hash-pinned `122718e65bdf…`). Optional H27-16 2 m temperature probes after provenance verification.

**Physical signature:** Quality-controlled, de-duplicated geothermometer/temperature contrasts along short spatial gradients and locally fault-aligned corridors — not isotropic distance-to-point surfaces.

**Why it catches catalogue-missing faults:** A chemically distinct upflow zone can reveal permeable fault pathways where the surface trace is absent. The target is spatial contrast and alignment, not proximity to a spring by itself.

**Confounders:** Duplicate sampling, geothermometer validity, groundwater flow away from the fault, sparse biased stations, non-fault heat sources.

**Differs from repo:** H27-12 tested simple well/spring distance features and found nearly zero benefit (PR-AUC +0.0005, fail). This candidate uses screened measurement values and local contrasts — a distinct transform that remains untried and must not be represented as already supported.

**Expected holdout ΔDTI:** [0.0, +0.003]

**Cost:** Medium — point QA/deduplication and fold-safe spatial encoding.

**Data gate:** In-footprint wellspring CSV present as owner-repository mirror; official GDR package listing verified; raw GDR binary not independently fetched/re-hashed this session.

**Sources:** https://gdr.openei.org/files/1391/wellspringdata.gdb.zip

**Status:** UNTRIED; separate from the refuted distance-only feature arm.

---

## H28-6 (new) — Blind fault gravity-gradient tensor invariants (Rank 4)

**Layers:** `iso_grav_anom` (band 13), `iso_grav_anom_slope` (band 4), `iso_grav_anom_vg` (band 9), `iso_grav_anom_hg` (band 16) from the prepared 32-band matrix (GeoDAWN gravity).

**Physical signature:** Gravity-gradient tensor invariants (vertical gravity gradient, horizontal gradient magnitude, analytic signal amplitude) highlight density contrasts at fault zones. Blind faults offsetting basement density produce edge responses without surface expression.

**Why it catches catalogue-missing faults:** Bouguer/anomaly gravity responds to density contrasts across faults regardless of surface rupture. A blind fault cutting bedrock beneath alluvium still produces a gravity gradient signature. The catalogue only lists Quaternary surface-rupture faults.

**Confounders:** Basin-fill density variations, non-fault lithologic contacts, regional gravity trends.

**Differs from repo:** H28-1 used multiscale edge *coherence* between magnetic and gravity (6 features). H28-6 uses gravity-gradient *tensor invariants* alone as a standalone detector surface, without magnetic cross-check. Not previously tested as an independent feature arm.

**Expected holdout ΔDTI:** [0.0, +0.002]

**Cost:** Low — derived from existing gravity bands in the prepared matrix; no new data.

**Status:** UNTRIED.

---

## H28-7 (new) — Thermal IR emissivity anomaly lineaments from radiometric bands (Rank 5)

**Layers:** `geodawn_rad_u8.tif` (K, Th, U, TC bands) and `geodawn_extensions_u8.tif` (Th/K, U/K, U/Th, TMI_up150) — already restored.

**Physical signature:** Hydrothermal alteration (argillic, advanced argillic, silicic) changes surface mineralogy and thermal emissivity. Radiometric ratios (e.g., Th/K, U/K) and upward-continued magnetic (TMI_up150) highlight alteration zones associated with permeable fault pathways.

**Why it catches catalogue-missing faults:** Alteration halos can extend beyond mapped fault traces and mark blind structures. A fault acting as a fluid conduit produces chemical alteration detectable in radiometric ratios even without a Quaternary surface scarp.

**Confounders:** Lithologic variations unrelated to faulting, soil moisture effects on radiometric response, drainage patterns.

**Differs from repo:** Addendum D tested radiometric ratios (+8 bands) and found PR-AUC +0.00074 (fail, below +0.005 threshold) as *features added to the 32-band detector*. H28-7 tests radiometric ratios as a *standalone lineament detector* with directional lineament extraction — a different use, not previously evaluated.

**Expected holdout ΔDTI:** [0.0, +0.002]

**Cost:** Low — existing radiometric grids; no new data.

**Status:** UNTRIED.

---

## Ranking summary

| Rank | ID | Expected ΔDTI | Cost | Data available? | Testable this session? |
|------|----|--------------|------|-----------------|----------------------|
| 1 | H27-16 GDR 1391 layers | [0.0, +0.006] | Medium-high | No (packages absent) | No — needs external data |
| 2 | H28-4 Seismicity fabric | [0.0, +0.002] | Low-medium | Yes | **Yes — NEGATIVE (2 seeds)** |
| 3 | H28-5 Hydrothermal chemistry | [0.0, +0.003] | Medium | Yes (CSV present) | Yes |
| 4 | H28-6 Gravity-gradient invariants | [0.0, +0.002] | Low | Yes (bands present) | Yes |
| 5 | H28-7 Radiometric lineaments | [0.0, +0.002] | Low | Yes (grids present) | Yes |

**Recommendation:** H27-16 has the highest expected gain but requires external data not yet obtained. Among testable candidates with existing data, H28-5 (hydrothermal chemistry gradients) ranks highest by expected gain and uses data already in the checkout. H28-4 was tested this session and is negative. No candidate has yet beaten the current holdout best (+0.00294884, H28-1).
