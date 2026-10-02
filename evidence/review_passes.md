# Three review passes (27GEMSDOE — Sessions 1 & 2)

## Pass 1 - implement and verify
* **Session 1:**
  * Inputs restored by hash (`scripts/restore_data.py`): labels, template, H19-5, the 0.2477 file, d2.8 file, lidar/radiometric rasters, training raster (`4371c82e...`).
  * Re-implemented the official DTI; tested against a literal brute-force transcription of the definition (random grids, soft predictions, masks) and, on a real cell, against the sibling's independent implementation (difference `0.00e+00`).
  * Regenerated the 0.2477 emission (60,069 px) and the sibling d2.8 emission (44,090 px) bit-for-bit.
  * Built the fault graph, links, evidence score, candidate set; pre-registered and ran the gates (seeds 100-109, then 110-119); built submissions.
* **Session 2 (executing previous session's next steps first):**
  * Restored `qfaults_v2_in_footprint.json` (`1,179` NBMG INGENIOUS Quaternary fault polylines, SHA-256 `4d6efc7bb3659ea2545353fcec574ef085b0acdb189c7590e4420a7c6c57b41c`), `gdr_volcanic_vents_in_footprint.csv` (`340` vents), `gdr_wellspring_in_footprint.csv` (`4,897` wells/springs), and `dem_links.json` (`1,701` USGS 1 m DEM tiles) via `data/manifest.json` and `scripts/restore_data.py`.
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
| 9. three passes, PR, merge, remaining work | this file; PR and merge executed on `arena/01a0fe2a-gemsdoe27` -> `main` | - |

---

# Session 3 (2026-10-02) — live-score inversion, budget model, slot 4

Environment: venv `/home/user/.venv`; all 16 hash-pinned inputs restored by `scripts/restore_data.py`
(exit 0, every artifact `OK`, assembled `training_features.tif` = `4371c82e3b83`). `gh` authenticated
as `buffedlizard55-lab`. Sandbox network: `api.github.com`, `github.com`, `codeload.github.com`,
`pypi.org`, `files.pythonhosted.org` reachable; **every** official science host
(`data.usgs.gov`, `web2.nbmg.unr.edu`, `earthquake.usgs.gov`, `sciencebase.gov`, `gdr.openei.org`,
`pangea.stanford.edu`, `services.arcgis.com`, `ncei.noaa.gov`, `raw.githubusercontent.com`) returned
`000`. `drivendata.org` was never contacted (AGENTS.md hard rule).

## Pass 1 — implement and verify
| item | result |
|---|---|
| `scripts/fetch_scored_corpus.py` (new) | recovers scored sibling rasters through the GitHub API and accepts a file **only if its SHA-256 equals a `registry/live_scores.json` row**: **20/25 matched**, 5 listed as unmatched rather than guessed → `evidence/scored_corpus.json` |
| `scripts/invert_live_scores.py` (new) | exact identity `DTI = TPw/(0.2·TPw·(1−ρ) + 0.2·N + 0.8·|G|)`; **reproduces both live anchors exactly** (H19-5 solid → 0.1922, dotted d1.5 → 0.2477); **|G| = 12,226 px** from the blind lattice (`c = 0.37481`, `ρ = 0.99`) → `evidence/live_inversion.json` |
| `scripts/optimize_budget.py` (new) | retention rule validated on **two independent live pairs** (−0.1 %, +4.0 %); budget optimum **d = 2.25–2.8 → 0.2550** → `evidence/budget_optimum.json` |
| `src/gems27/coverage_thin.py` (new) | batched greedy max-coverage thinning, exact local marginal gains, deterministic |
| `scripts/tomography_partition.py` (new) | 7-cell catalogue-distance partition tomography + leave-one-submission-out validation → `evidence/live_truth_partition_radial.json` |
| `scripts/model_candidates.py` (new) | both truth assumptions for all four slots → `evidence/candidate_model_scores.json` |
| `src/gems27/layers.py` (new) | memory-capped band-verified loading of LiDAR / GeoDAWN / SGMC / NBMG-vector / GDR points |
| Slot 4 built (H27-8) | `gems27-all-increments-d2-8-h27-4-r1-t-v2-20261002-23ad46a4d7ba-nan.tif`, **41,507 px**, first candidate stacking all three validated increments at the anchored budget optimum |
| `scripts/verify_downloads.py` extended | now covers all four slots and asserts slot 4 is *exactly* `dot_thin(H19-5,2.8) − 1 px flank shadow + T-v2 dots`: **79 checks, 0 failures** |
| `pytest -q` | **47 passed** (36 inherited + 11 new in `tests/test_inversion.py`) |
| `ruff check src scripts tests` | clean |
| Site / figures | `make_figures.py` ok; `build_site.py` rebuilt all 5 pages from JSON only |

## Pass 2 — review for bugs, wrong assumptions, edge cases
| # | finding | resolution |
|---|---|---|
| 1 | **Real numeric bug:** `emission_of()` summed positives over the **whole grid**, so pixels outside the organisers' footprint were charged as scored. The GEMSDOE9 `PLACEHOLDER` raster (live 0.0107) has **196,132 positives outside** the footprint and only 145,610 inside — its scored count was overstated **2.3×** (341,742), corrupting its implied credit | fixed to count inside-footprint positives only and to report `n_positive_outside_footprint` separately; flagged as `gemsdoe9-placeholder-positives-outside-footprint` in `registry/irregularities.json`. \|G\| and all four slot models are unchanged (they emit 0 px outside) |
| 2 | **Wrong assumption found and corrected:** the closure `FPw = N − TPw` used in `knowledge/01` is exact only when each matched truth pixel sees ~1 dot. The metric takes a **max** over predictions for credit but a **sum** for matched mass, so `FPw = N − MPw` with `MPw ≥ TPw` | introduced the crowding factor `ρ = MPw/TPw = N·kernel_area/(nfp·c)`, which makes the identity exact; `ρ = 0.99` for the blind lattice (closure valid there, which is why it is a clean calibration instrument) and `ρ = 2.46` for solid H19-5 (where the naive closure overstates credit by 5 %) |
| 3 | **First tomography returned R² = −1.24** | diagnosed rather than tuned: overlapping bases cannot satisfy the mass constraint `Σ w_j|B_j| = |G|`. Added the missing uniform background field, then re-specified as a strict **partition** (well identified, constraint exact). It still failed (R² = −0.360, LOO signal ratio 0.96) and is recorded as **not identifiable** — H27-9 rejected, no slot spent |
| 4 | **H27-6 coverage-optimal thinning looked obviously right and is wrong** | measured at matched budgets on quadrant NW: greedy attains **0.866×** Poisson-disk coverage at 20,752 px (13 % worse) and 1.010× at 28,209 px. Recorded as REFUTED with the numbers so nobody re-derives it |
| 5 | **H27-7 union-recall looked like free recall and is a gamble** | Jaccard h19-5 vs H25-ctx = 0.075, vs r7-scarp = 0.052. Modelled: 0.2655 central / **0.2310 pessimistic** (both surfaces covering the *same* truth from different pixels) against **0.2550 for h19-5 alone on a rule validated to 4 %**. Rejected; downside −0.086 exceeds the edge |
| 6 | **The two candidate models disagree, and hiding that would be misleading** | geometric retention is validated only for *unbiased* removal; it is structurally biased against *targeted* pruning because it charges removed pixels with average credit, while the OOF gate measured the H27-4 flank pixels at 0.0034 (~15× below the 0.0521 break-even). Both numbers are now reported for every slot and the disagreement is named as the thing slot 1 vs slot 3 settles (`geometric-retention-biased-against-pruning` irregularity) |
| 7 | `build_site.py` crashed on a `None` score (`TypeError: unsupported format string`) and on a sources row missing `publisher`/`category` | added `_sc()` null-safe score rendering (shows an **UNSCORED** badge) and conformed the new `registry/sources.json` row to the existing 10-key schema |
| 8 | Literal `{dot}` from a registry string leaked into rendered HTML; index still said "3-slot plan" | de-braced the registry text, updated the wording to 4 slots; added a test asserting no unrendered braces and that slot 4 is on the first screen |
| 9 | `paths.ROOT` does not exist (module exports `REPO`); `KeyError: 'sha256'` in the unmatched-row report | both fixed; `scripts/fetch_scored_corpus.py` now reports unmatched rows with their hash |
| 10 | Memory: 3 GB sandbox, 3730×3292 grid, 20 rasters | all inversion work runs in footprint-index space; `src/gems27/layers.py` reads only the bands used and asserts each band's embedded description before use; `coverage_thin` restricts to a bounding window |
| 11 | 5 registry rows could not be hash-matched | listed explicitly (`five-scored-rasters-unmatched`); the inversion rests on 20 pairs and says so. No filename-only match was accepted anywhere |
| 12 | Leaderboard distribution is **secondary** evidence | copied verbatim from the sibling's owner-directed read with provenance, status `secondary quote only`, and an explicit caution that the five value coincidences identify nothing (`leaderboard-snapshot-sibling-only`) |

## Pass 3 — recheck against the original request
| request item | where satisfied this session | residual gap |
|---|---|---|
| Why 0.2477 scored 0.2477; can we exceed it and reach 0.3195 (PhD level) | `knowledge/07_live_score_inversion.md`, `docs/research.html#inversion`. Now **arithmetic**: 0.3195 at 60,069 px needs 0.570·\|G\| of credit, more than any submission in the group's history has earned (best 0.508); at 44,090 px it needs 0.486·\|G\|, which H19-5 solid *has* (0.506) but thinning retains only 0.759 → 0.384. **Retention, not knowledge, is the wall.** Exceeding 0.2477 is modelled at 0.2550–0.2781 | 0.3195 **not reachable** by rearranging existing pixels — stated plainly, with the two remaining routes (retention ≈1.0 at ~44k px, or concentration >5.7) both named as detector problems |
| Easy-download TIF on the first screen, exec summary, unique name, note ≤200 chars, `[0,1]` fix | `docs/index.html` hero + a 4-slot table; slot 4 note is **172 chars**; 79 checks confirm exact 0.0/1.0 in-footprint, NaN outside with `nodata=NaN`, single-file zip, all-finite fallback, 0 px on catalogue cells, 0 px outside the footprint | portal acceptance still awaits a human upload; the validator remains closed-source so the fix stays defensive |
| 3–5 untried hypotheses, layers/signature/why-missing/differs, ranked, top validated pre-slot | `registry/hypotheses.json` + regenerated `knowledge/02`: added **H27-8** (built, verified, unspent), **H27-10** (new geological hypothesis: the 100–300 m offset scarp halo — the sign-flip of H27-4, motivated by Hermant's 150–400 m offsets and the tomography's habitat peak), and **H27-6/7/9** tested and rejected with measurements, zero slots spent | H27-10 is **not yet validated**; its cheap OOF test (fresh seeds 140–149) is next-step 2. The Hermant offset figure is still `secondary quote only` — the host is unreachable from the sandbox |
| Topology / network-connectivity work (Berkowitz et al. 2000) | inherited: `knowledge/04`, `docs/topology.html`, 345 T-v2 links with NBMG `NAME`/`FID`/`SLIPSENSE`/`DIPDIRECT`/`kinematic_compat`, all carried into slots 1–4 | percolation-value ranking of the 345 links (Δ component merge, load-bearing bridges) still not implemented → next-step 3; overlapping en-echelon step-overs (H27-2) never generated → next-step 4 |
| Contrarian/outside-the-box, free official sources, auditable table | the contrarian result this session is that the obvious improvements **fail**: coverage-optimal thinning loses to Poisson-disk, unions are a gamble, and the truth's habitat is not identifiable from 20 scores. `registry/sources.json` now 17 rows with honest status | no new external source could be fetched (all science hosts blocked); Siler (2022) / DeAngelo (2022) remain Actions-only |
| Autonomous, no manual input; verify from official sources with links; flag irregularities; no hallucinations | 6 new irregularities (25 total) including one that changed a number; every score labelled owner-reported; every model labelled a model; three rejected ideas recorded with the measurement that killed them | **Blocked on the owner:** no 27GEMSDOE file has ever been uploaded, so `live_scores.json["27GEMSDOE"]` is still `null` and Session-3 priority 1 (ingest the slot 1 A/B score) could not be executed |
| Previous session's next steps first | priority 1 attempted and blocked (no score exists); substituted the no-upload-needed inversion, which delivered more than priority 1 would have. Priorities 2 (detector upgrade) and 5 (Siler/DeAngelo) **not done** | detector upgrade is now the top technical item and is next-step 2 for Session 4, with the arithmetic case for why it is the *only* remaining route |
| Three passes, PR, merge, remaining work | this file; `knowledge/06` "Prioritised next steps for Session 4"; PR from `arena/01a0fe89-gemsdoe27` → `main` | — |

### Pass 2 addendum — CI was red on `main` before this session
Reproduced in a clean clone of the base commit `ce80ead` **without** `data_cache/`: `1 failed, 35 passed`.
`tests/test_vector_and_oof.py::test_vector_attribution_and_evidence_files` opens `paths.TEMPLATE`, but
`.github/workflows/ci.yml` runs `pytest` on a bare checkout and cannot restore the inputs — they live in
*sibling* repositories that the workflow's `contents: read` token cannot read. Fixed with `tests/conftest.py`
(a `requires_rasters` marker plus a collection hook that skips with the missing file names in the reason),
applied to the pre-existing test and to the new raster-dependent one. Clean clone now gives **45 passed,
2 skipped**; locally after `restore_data.py`, **47 passed, 0 skipped**. Recorded as
`ci-red-on-main-raster-tests` (severity **high**) with the honest consequence: CI does not exercise those two
checks, so they must be re-run locally before any release. Giving CI a restore step needs a token with
sibling-repo read access — an owner access request, not something the agent can grant itself.
