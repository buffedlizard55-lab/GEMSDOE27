# Review passes (27GEMSDOE — Sessions 1 onward)

## Pass 1 - implement and verify
* **Session 1:**
  * Inputs restored by hash (`scripts/restore_data.py`): labels, template, H19-5, the 0.2477 file, d2.8 file, lidar/radiometric rasters, training raster (`4371c82e...`).
  * Re-implemented the official DTI; tested against a literal brute-force transcription of the definition (random grids, soft predictions, masks) and, on a real cell, against the sibling's independent implementation (difference `0.00e+00`).
  * Regenerated the 0.2477 emission (60,069 px) and the sibling d2.8 emission (44,090 px) bit-for-bit.
  * Built the fault graph, links, evidence score, candidate set; pre-registered and ran the gates (seeds 100-109, then 110-119); built submissions.
* **Session 2 (executing previous session's next steps first):**
  * Restored `qfaults_v2_in_footprint.json` (`1,179` NBMG INGENIOUS Quaternary fault polylines, SHA-256 `4d6efc7bb3659ea2545353fcec574ef085b0acdb189c7590e4420a7c6c57b41c`), `gdr_volcanic_vents_in_footprint.csv` (`340` vents), `gdr_wellspring_in_footprint.csv` (`4,897` wells/springs), and `dem_links.json` (716 links; 706 successful tiles, 10 failed, per the hash-pinned owner metadata) via `data/manifest.json` and `scripts/restore_data.py`.
  * Created `scripts/download_competition_data.sh` (mirroring the official Dropbox competition data links) and `scripts/prepare_data.py` (building the 32-band label-free feature matrix `data_cache/prepared/features.npy`, `[5167373, 32]`, SHA-256 `83ed2704...`, excluding the mislabelled `tc` band and asserting all 18 remaining band descriptions).
  * Pre-registered and committed (`1487895`) **Addendum B** (seeds 120-129, 3-tier vector holdout + H27-5 kinematic typing) and **Addendum C** (seeds 130-139, honest 4-fold spatial-CV out-of-fold detector $B_{\text{oof}}$ gating H27-1, H27-4, and H27-3) in `knowledge/03_preregistration_topology_gate.md` *before* running the confirmatory scripts.
  * Implemented `src/gems27/vector_graph.py`, `scripts/fetch_vector_faults.py`, `.github/workflows/fetch-vector-faults.yml`, and `scripts/run_vector_topology_validation.py`; confirmed Addendum B gates (`component` `0.2926`, `FID_trace` `0.1003` vs `0.0204` ctrl, `H27-5a` `0.1374`, `H27-5b` `0.1783`, `NAME_zone` `0.0014`).
  * Implemented `src/gems27/oof_detector.py` and `scripts/run_oof_hypothesis_gates.py`; confirmed Addendum C gates on $B_{\text{oof}}$ (`plus_T_v2` `+0.0115` in 4/4 folds; `prune_r1_100m` `+0.0022` solo and `+0.0141` stacked with T-v2 in 4/4 folds; `coherence_h27_3` refuted `-0.0010` in 0/4 folds).
  * Annotated all 345 T-v2 dossiers with official NBMG/USGS fault attributes (`FID`, `NAME`, `NUM`, `FTYPE_`, `SLIPSENSE`, `DIPDIRECT`, `MAPSCALE`, `kinematic_compat`) and built the **Tertiary Slot 3 candidate (`d466b251f309`, 55,992 px = 0.2477 minus 5,355 100 m flank-shadow dots + 1,278 T-v2 dots)** alongside the unchanged Primary (`5512495c6bd1`) and Secondary (`3ebd51534bb1`) candidates.

## Pass 2 - bugs, assumptions, edge cases
| # | finding | action |
|---|---|---|
| 1 | **Implementation bug (Session 1):** the first confirmatory launch applied the minimum gap before choosing the nearest target, deviating from the registered rule (caught by a unit test) | fixed; run stopped, disclosed (`topology_validation_runA_partial_log.txt`), rerun as registered |
| 2 | **Defect in the graph edge builder (Session 1):** 1-px stubs recorded as self-loops inflated the cyclomatic number (504) | fixed; reported figures replaced (250 raw / 110 / 6 enclosed >= 20 px); no effect on links, validation or files |
| 3 | Mutual links appear twice (A->B, B->A): duplicate dot trains | de-duplicated variant added to the confirmatory run (efficiency 0.280 vs 0.226) and shipped |
| 4 | 8 of 345 links pass within ~100 m of a third system | kept (validated rule), flagged per link |
| 5 | Efficiency of "all links" (0.121) is below random same-size subsets (0.149): overlap saturates credit | null for z>=3 is the same-size random subset (p95 0.156), not the full set |
| 6 | **Band-order assumption in `prepare_data.py` (Session 2):** `det_elev` in `training_features.tif` is at band 12 (not band 8), while `dem_slope` is at band 8 | added explicit `EXPECTED_DESCRIPTIONS` assertion for all 19 bands in `scripts/prepare_data.py` before writing `features.npy` |
| 7 | **Vector attribution performance bottleneck (Session 2):** looping `pix_fid == i` over 1,179 full `(3730, 3292)` grids took >22s per call | replaced with 1D lookup tables (`name_lut[pts_fid[nn]]`) at label coordinates `(ly, lx)`, cutting attribution time to 1.1s |
| 8 | **`fetch_vector_faults.py` dependency & manifest schema (Session 2):** `requests` was not installed in the sandbox and `data/manifest.json` stores file entries as a list with `"path"` | switched `scripts/fetch_vector_faults.py` to standard-library `urllib.request` and `Path(f["path"]).name` |
| 9 | **`irregularities.json` schema compatibility with `build_site.py` (Session 2):** `build_site.py` expects `"items"` with `"severity"`, `"issue"`, `"action"` | verified schema against `HEAD` and `build_site.py`, preserving all 18 items and adding `hermant-2025-lidar-catalogue-offset` |
| 10 | **Hermant et al. (2025) 150–400 m USGS-vs-LiDAR scarp offset (Session 2):** explains why 5,355 dots (8.91%) of the 0.2477 file sit at `d_cat = 100 m` with OOF efficiency `0.0034` | documented in `registry/irregularities.json` and `knowledge/04`, and mitigated in Tertiary Slot 3 (`d466b251f309`) |
| 11 | **H27-3 isolated-dot removal (Session 2):** tested on the honest OOF surface and found to *reduce* DTI (`-0.0010`, `0/4` folds) because 1.27 km median faults thin to 1–2 dots | rejected on holdout — zero submission slots spent |
| 12 | Edge cases: footprint border, NaN outside vs zero outside, single-member zip, note <= 200 chars | verified across all 3 slots (`primary`, `secondary`, `tertiary`) by `scripts/verify_downloads.py` (66 checks, 0 failures) and `pytest` (36 passed) |

## Pass 3 - recheck against the original request
| request item | where satisfied | residual gap |
|---|---|---|
| 1. why 0.2477 won; achievability; new system | `knowledge/01`, `docs/research.html`; new graph/link/vector/OOF/verification code and site | 0.3195 not reachable with verified/modelled increments on H19-5 alone (`~0.262-0.270`) - stated |
| 2. topology class: graph, gaps, kinematics/step-over/termination, dossier per candidate, Berkowitz only as verified | `knowledge/04`, `docs/topology.html`, `registry/topology_candidates.json`, CSV/GeoJSON (now with official NBMG/USGS fault names, `FID`, `SLIPSENSE`, `DIPDIRECT`, `kinematic_compat`) | Berkowitz ensemble scope explicitly distinguished from per-gap validation |
| 3. 3-5 untried hypotheses ranked; top validated pre-slot; external data named and checked | `registry/hypotheses.json`, `knowledge/02`, `evidence/vector_topology_validation.json`, `evidence/oof_hypothesis_gates.json` | H27-1, H27-4, and H27-5 validated; H27-3 refuted on OOF holdout |
| 4. knowledge base + auditable table with links, overlooked sources, contrarian | `docs/sources.html`, `docs/data/sources.csv`, `knowledge/05` | Official Rules (all 7 chunks), Hermant et al. 2025 (all 8 chunks), GDR #1391, ScienceBase items, and NBMG ArcGIS REST all read and verified |
| 5. one-click valid TIF on the first screen; [0,1]; unique name; note; exec-summary steps | `docs/index.html`, `docs/executive-summary.html`, `docs/downloads/` (3 weekly slot candidates, 66 standalone checks) | portal acceptance awaits human upload |
| 6. clean Pages site, official links, up-to-date feed | `docs/`, `source-feed.yml`, `fetch-vector-faults.yml`, `ci.yml` | - |
| 7. README with the prompt verbatim + Core Values | `README.md` (both verbatim Task prompt and verbatim Core Values included) | resolved in Session 2 |
| 8. limitations and access | `knowledge/06`, executive summary | - |
| 9. three passes, PR, merge, remaining work | this file; prior PR and merge executed on `arena/01a0fe2a-gemsdoe27` -> `main` | - |

## Current continuation (2026-10-02) — H28-1 work

### Pass 1 — implement and verify (pre-holdout)
- Re-read the full owner prompt in `README.md`; read `AGENTS.md` and followed its no-DrivenData-automation and pre-registration rules.
- Retrieved and hash-pinned the sibling LiDAR sidecar. Verified its 12-band order against the embedded raster descriptions; verified the official USGS 3DEP catalog page directly. Restored and hash-checked all 17 manifest artifacts.
- Corrected the ten LiDAR feature labels in `scripts/prepare_data.py`, added all-12-band assertions and stale-cache invalidation. Regenerated the matrix: the numerical SHA-256 is identical to the pre-change committed matrix (`83ed2704…`); only the metadata names changed.
- Implemented label-free H28-1 multiscale magnetic/gravity edge features and a paired OOF holdout runner. The runner writes evidence/cache only, verifies source bands, prepared metadata, ranges and known-label overlap, and never writes a submission TIFF.
- Ran the synthetic transform tests, full tests (**42 passed**), `ruff check` (**pass**), JSON validation, the site build, input restore, cached preparation check and the independent existing-file GeoTIFF audit (**66 checks, 0 failures**). Full-size H28-1 feature matrix was finite, `[0,1]`, shape `[5167373, 6]`, with 5,164,312 jointly valid cells.

### Pass 2 — review and corrections before the holdout
- Found that the former preparation names did not match the same-position source raster bands. Corrected the labels and source registry, while confirming byte-identical prepared matrix content; the raw-raster `channel_auc.py` audit is unaffected because it reads embedded descriptions directly.
- Found old prose claiming 1,701 DEM tiles. Corrected it to the pinned owner-mirror inventory (716 links, 706 successful derivatives, 10 failures); explicitly state this is not an independent USGS download audit.
- Reviewed transform boundary/nodata behavior, classifier sampling and feature order, T-v2 graph reuse, the 100 m catalogue prune, DTI masks and no-known-catalogue-overlap guard. Disclosed that 1 km covariate filters can share adjacent field values across the existing 600 m fold buffer; no labels enter the transform, but spatial covariate correlation remains a limitation.
- After commits `c5d40b7` (hypotheses/protocol) and `5a6972e` (implementation), ran the frozen seeds 140–149. H28-1 + T-v2 + H27-4 r1 passed: `+0.00294884` mean paired ΔDTI, 3/4 folds, 9/10 seeds. The NE fold and seed 149 were negative; see `evidence/h28_1_edge_holdout.json` for all 40 paired cells and hashes.
- The holdout runner wrote no submission TIFF. The existing three submission files remain unchanged, no weekly slot was used, and no public score is claimed. A separate full-map export protocol is now preregistered in `knowledge/09_preregistration_H28-1_candidate.md`; its implementation and format checks remain pending.

### Pass 3 — full-request recheck

Pending the full-map candidate export/format checks and final repository/PR review. The final recheck must include the user-requested site/download workflow, scientific limits, score uncertainty, tests, and the PR/merge outcome.
