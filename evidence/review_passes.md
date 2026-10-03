# Three review passes (27GEMSDOE — Sessions 1 & 2)

## Pass 1 - implement and verify
* **Session 1:**
  * Inputs restored by hash (`scripts/restore_data.py`): labels, template, H19-5, the 0.2477 file, d2.8 file, lidar/radiometric rasters, training raster (`4371c82e...`).
  * Re-implemented the official DTI; tested against a literal brute-force transcription of the definition (random grids, soft predictions, masks) and, on a real cell, against the sibling's independent implementation (difference `0.00e+00`).
  * Regenerated the 0.2477 emission (60,069 px) and the sibling d2.8 emission (44,090 px) bit-for-bit.
  * Built the fault graph, links, evidence score, candidate set; pre-registered and ran the gates (seeds 100-109, then 110-119); built submissions.
* **Session 2 (executing previous session's next steps first):**
  * Restored `qfaults_v2_in_footprint.json` (`1,179` NBMG INGENIOUS Quaternary fault polylines, SHA-256 `4d6efc7bb3659ea2545353fcec574ef085b0acdb189c7590e4420a7c6c57b41c`), `gdr_volcanic_vents_in_footprint.csv` (`340` vents), `gdr_wellspring_in_footprint.csv` (`4,897` wells/springs), and `dem_links.json` (716 USGS 1 m DEM links; 706 successful derivatives, 10 failures; the prior 1,701 claim was corrected in the H28 continuation) via `data/manifest.json` and `scripts/restore_data.py`.
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
| 3–5 untried hypotheses, layers/signature/why-missing/differs, ranked, top validated pre-slot | `registry/hypotheses.json` + regenerated `knowledge/02`: added **H27-8** (built, verified, unspent), **H27-10** (new geological hypothesis: the 100–300 m offset scarp halo — the sign-flip of H27-4, motivated by Hermant's 150–400 m offsets and the tomography's habitat peak), and **H27-6/7/9** tested and rejected with measurements, zero slots spent | H27-10 is **not yet validated**; its cheap OOF test now uses fresh seeds 150–159 because H28-1 consumed 140–149. The Hermant offset figure remains `secondary quote only` — the host was unreachable from the sandbox |
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

---

# Session 4 (2026-10-02) — SGMC-gap live inversion, Addendum D/E, graph value, external-layer bridge

## Pass 1 — implement and verify
* `scripts/invert_sgmc_probe.py` (new): authenticates the h18-4 probe by SHA-256 against
  `registry/live_scores.json`, re-verifies its construction claim from the raster bytes, reproduces
  Session 3's published anchors with the same instrument, inverts under three |G| candidates and under
  exact MP bounds, and models the habitat's best possible thinning budget with the live-validated
  retention rule. Output `evidence/sgmc_gap_inversion.json`.
* `src/gems27/graph_value.py` + `tests/test_graph_value.py` (4 tests): per-link bridge status, merged
  length, largest-share change, Berkowitz dP (reproduces the published P = 5.784491473419016 exactly)
  and the continuous d(sum l^2) tie-break. Wired into `scripts/build_candidates.py`, so all 345
  dossiers, `docs/data/topology_links.csv`/`.geojson`, `evidence/link_graph_value.json` and the site
  table carry it.
* `src/gems27/newinfo.py` + `tests/test_newinfo.py` (8 tests): 24 oriented line-integral bands, 16
  unused-official-layer bands, and the overlapping en-echelon step-over rule with its perpendicular
  control. `scripts/build_augmented_features.py` writes the 40-band matrix (827 MB memmap,
  sha256 `98abf032a0df…`), `scripts/run_addendum_d_gates.py` runs the registered gates,
  `scripts/diagnose_arm_habitats.py` decomposes where an arm's credit comes from.
* `oof_detector.fit_predict_oof_probabilities` gained an optional band matrix and chunked prediction
  (3 GB box); `fit_predict_full_probabilities` added for emission time. Base arm reproduces Session 3
  (mean DTI 0.08894 vs 0.0861; T-v2 +0.01221 vs +0.0115), so the refactor did not move the instrument.
* Slot 5 built by `scripts/build_submission27.py`; `scripts/verify_downloads.py` extended from 79 to
  **125 checks over 5 slots, 0 failures**, including six Addendum-E single-variable invariants.
* `.github/workflows/fetch-gdr-external-layers.yml` + `scripts/fetch_external_layers.py`: hash-pinned
  download/verify/inventory/clip of three official GDR 1391 layers plus HEAD-checks of the larger
  sources. Failure path exercised locally (host unreachable from the sandbox -> `ok:false` recorded,
  no crash); success path runs on the runner.
* `scripts/restore_data.py` hardened (stale `.part` removal, retries, GitHub-reported byte-count
  verification, deletion of a corrupt assembly and its parts).

## Pass 2 — bugs, wrong assumptions, edge cases (each one caught and fixed this session)
1. **Wrong inversion closure.** The first draft solved `TP` from `MP = rho * c * G` while leaving `TP`
   free — an inconsistent double use of the uniform-truth assumption. It gave anchor concentrations
   6.01/6.12 instead of the published 5.67/5.66. Fixed to the repository's self-consistent closure
   (`TP = s(0.2N + 0.8|G|)/(1 - 0.2s + 0.2 s rho)`), after which the anchors reproduce to 5
   significant figures (credit 5,286.0 and 6,188.8; rel. diff 3.2e-5).
2. **Prose written before the numbers.** That same draft carried a pre-written verdict claiming the
   probe was "BELOW the blind lattice floor of 1.00 under every closure". The corrected measurement is
   **1.62x blind (bracket 0.76-1.65)** — the claim was false. Verdict text is now generated from the
   computed values, not written by hand.
3. **Boolean-index bug** in the construction check (`d = pos[in_fp]` then used as a mask) — IndexError
   on first run.
4. **Redundant links looked valuable.** `merged_lengths` added every link's gap length to the merged
   system, so one of two parallel closures reported d(sum l^2) = 6.72 km^2 instead of 0. Rewritten as
   ascending-gap union-find where only a merge of two *different* systems contributes; pinned by a test.
5. **A wrong test, not wrong code:** merging two 4 km strands gives dn = 1 - 1 - 1 = -1, so dP < 0. The
   test asserted dP > 0; rewritten to assert the quantum semantics in both directions.
6. **Unbounded statistic on a signed band:** the pre-registered anisotropy `(max-mean)/max` reached
   6.6e7 on `det_local_relief` (signed, 64.7 % negative, 3,061 NaN). Bounded form used for signed
   layers only, disclosed in `knowledge/03` Addendum D **before** the gate ran.
7. **Band lookup by the wrong key** (`KeyError: 1`) in the first augmented-features build; now reads
   band names from the raster's own descriptions.
8. **Silent patch miss:** `_d3_verdict` computed the two exploratory pools but never returned them.
   Caught by a KeyError on read; recomputed from the per-cell rows the registered run had already
   stored, and the evidence file says so explicitly rather than looking like a fresh run.
9. **Step-over search was both slow and incomplete** (centroid radius would miss long parallel strands;
   pixel-pair matrices were O(|A|x|B|)). Rewritten with per-component projections, a capped-extent
   KD-tree candidate search and a `cKDTree` closest-pair query; the cap is documented in the docstring
   as a conservative omission (pairs of systems each > 20 km offset along strike by > 10 km).
10. **An unquoted heredoc ate the README's backticks.** `bash <<PY` command-substituted every
    `` `path` `` span, deleting file names from the text. Caught by re-reading the file, reverted with
    `git checkout README.md`, re-applied from a written-out patch script. Recorded as a standing rule:
    never patch prose through an unquoted heredoc.
11. **Arithmetic quoted from memory was wrong.** "98.1 % of credit within 200 m" and band shares
    36.2/50.7/11.2/0.4 recomputed from the evidence are **99.6 %** and **36.8/51.5/11.4/0.37**. All six
    affected files corrected and the site regenerated. The site computes the figure itself and showed
    99.6 % — which is how the error was caught. Lesson: compute prose numbers from the artifact.
12. **A claim with no committed reproduction.** The LiDAR-response corollary (136.4 vs 99.7) existed
    only in an ephemeral scratch script. `scripts/sgmc_lidar_response.py` now produces
    `evidence/sgmc_lidar_response.json` and confirms the numbers exactly (136.41 / 99.66 / 86.15 on
    `lidar:valid` pixels), with the pooled-AUC artefact that motivated the `valid` restriction recorded.
13. **Slot 5 would have shipped unverified:** `verify_downloads.py` iterated a hard-coded 4-slot tuple.
    Extended, plus invariants specific to a single-variable probe (near field byte-identical, no pixel
    changed within 300 m of the catalogue, added dots off-catalogue/in-footprint/>= 1.5 px from kept
    dots, manifest fractions consistent).

**Assumptions audited, not assumed:** |G| (three instruments within 4.3 %; verdict identical under all
three candidates); the uniform-truth rho (bracketed exactly by MP in [0, N], so no verdict rests on it);
the retention rule for the probe's budget sweep (validated live at -0.1 % and +4.0 % on two independent
pairs, and labelled MODEL, never a score); the catalogue-internal proxy (now *measured* to be blind to
the far field, which is why two gate-passing arms were not promoted); the 20 % far-field swap fraction
(fixed before building, downside declared in the registration).

## Pass 3 — recheck against the original request
* **One-click submission on the first screen:** Slot 1 unchanged and still the recommendation, with
  `.zip` (exactly one GeoTIFF) and an all-finite fallback; the portal's `Predicted values must be in
  range [0, 1]` rejection is defended by exact 0.0/1.0 values, nodata=NaN like the sample, the
  all-finite variant and 125 automated checks. Slot 5 appears next to it, unmistakably labelled
  `MEASUREMENT PROBE — NOT RECOMMENDED`, with its registered reading and declared downside.
* **Fault-network topology rather than pixels:** nodes/edges/systems graph, 345 short low-scoring gaps
  treated as a distinct high-priority class, each with a written argument naming the two independently
  mapped faults (NBMG FID, zone name, slip sense, dip direction), the system they would form, and now
  its network consequence (bridge, dP, d(sum l^2), merged length, largest-share change) — independently
  checkable in `docs/data/topology_links.csv`/`.geojson` and `docs/topology.html`. Headline: closing all
  345 moves P from 5.784 to 6.124 across Pc = 5.6-6.0.
* **3-5 untried hypotheses before implementing:** five registered (H27-11 to H27-14, H27-16) plus
  H27-17 and an updated H27-2, each with layers, physical signature, why it catches a fault missing
  from USGS/INGENIOUS, how it differs from the repo, expected gain and cost; re-ranked 1-16. External
  data is named specifically (three GDR 1391 files with byte counts and SHA-256) and its obtainability
  is hash-pinned from an independent runner record, not asserted.
* **Validate before spending a slot:** Addendum D ran on fresh seeds 140-149 after pre-registration was
  committed. Two arms passed both criteria and were **not** promoted, with the reason measured rather
  than argued; no slot was spent by the agent. Slot 5 is offered to the owner as a bounded experiment
  with its interpretation rule fixed in advance.
* **Verify from official sources with links; flag irregularities:** `registry/sources.json` now 21 rows
  with honest statuses (the three new GDR rows say explicitly "hash-pinned, NOT downloaded here");
  `registry/irregularities.json` now 34 items, 8 added this session including one against my own
  scratch analysis and one against this repo's restore script.
* **Site:** rebuilt (submit / executive summary / topology / research / sources), with the Session-4
  findings card, the Addendum-D row in the validation table, the fifth slot in both decision tables and
  the graph-value columns. The source feed was **not** refreshed this session: the sandbox cannot reach
  the official hosts it checks, and a refresh would only record failures — the feed still carries its
  Session-3 timestamps, and that limitation is written in `knowledge/06`.
* **Limitations and needed access:** `knowledge/06` gains six measured limitations, the access list
  (owner upload + score report; sibling-read token for CI; 1 m 3DEP tiles; GPU; Siler/DeAngelo surfaces)
  and a five-item prioritised list for Session 5.
* **Negative results are deliverables:** four refutations recorded with numbers (SGMC-gap emission,
  connectivity ranking, step-overs, oriented lineament/radiometric/thermal features) and a fifth
  methodological one (the proxy's blindness), each with a "do not re-propose" entry.
## H28-1 continuation review (2026-10-02)

This addendum records the H28 experiment and its integration with upstream Session 3. Earlier Session-3 tables remain historical; current weekly-slot count is four, while H28-1 remains a separate research candidate.

### Pass 1 — implement and verify
- Re-read the complete README, including the verbatim owner task and Core Values. Kept the submission page's four current weekly artifacts unchanged and integrated the new Slot 4 from upstream `origin/main`.
- Added the H28-1 full-map candidate links and note to the research site, and rendered the five distinct ranked H28 geological hypotheses (layers, signature, missing-fault rationale, repo distinction, confounders, status and prior gain/cost). Expected ΔDTI ranges are explicitly priors, not predictions or results.
- Kept `1113fba5f6cb` in `h28_1_candidate_manifest.json`, never in the four-slot manifest. Candidate is marked unscored/research only. The holdout evidence is exposed on the research page with negative NE-fold and seed-149 exceptions.
- Rebuilt Pages output: `index.html`, `executive-summary.html`, `topology.html`, `research.html`, `sources.html`, and root `index.html`.

### Pass 2 — inspect assumptions, provenance, integration and format
- Confirmed the frozen catalogue-internal result: baseline mean DTI `0.10453779787967096`, augmented `0.10748663667407192`, paired gain `+0.002948838794400959`; three of four folds and nine of ten seeds improve. NE_LidarGapHeavy and seed 149 regress. This is not a live score; adjacent covariate values may be correlated across the 600 m fold buffer.
- Confirmed full-map research candidate `1113fba5f6cb` has 59,075 binary emissions and zero overlap with known catalogue cells. It remains outside all four weekly slots. The four weekly manifest and slot assets from current `origin/main` (including Slot 4 `23ad46a4d7ba`) are preserved.
- `scripts/verify_downloads.py`: **0 failures** across the four weekly slots and separate H28 research candidate. It checks CRS, template shape/transform, one-band float32, exact in-footprint `[0,1]` range, nodata/NaN behavior, fallback, archive, note length and hashes.
- `scripts/prepare_data.py` reproduced metadata schema 2 and the 32-feature matrix SHA-256 `83ed2704ee2de03cf8b1c8f2966fcf71813501df97c1c35400e6c0415393f6dc`; no feature values changed. Official USGS catalog metadata verifies the public 3DEP collection, not the owner-mirrored local derivative. DrivenData source-page authentication and the organizer-created test labels remain unavailable.
- Resolved the integration conflicts by combining H28 provenance with upstream Session-3 live-score inversion, tests, evidence, and four weekly candidates. No conflict markers remain. Reserved H27-10 seeds 150–159 and a distinct later detector range (e.g. 160–169) to avoid reusing H28's 140–149.
- Checks after integration: **53 pytest passed**, Ruff passed, Python compilation passed, `git diff --check` passed, download audit 0 failures. GitHub Actions still needs to run on the pushed merge-resolution commit; on a clean checkout the two raster-dependent checks are skipped because sibling-repository inputs cannot be restored by CI.

### Pass 3 — acceptance criteria and remaining limitations
| requirement | current evidence | status / limitation |
|---|---|---|
| Obvious valid download, exact name/comment, portal range error addressed | Four-slot first-screen site and per-slot manifest; every weekly and separate H28 TIFF audited as single-band float32 on the template grid, exact 0/1 inside and valid NaN/fallback outside | local validator passes; only a manual portal response can identify the historical closed-source range error |
| Re-read and preserve north star; explain 0.2477 / investigate 0.3195 | Full owner prompt/Core Values remain verbatim in README; authenticated-raster inversion is in `knowledge/07_live_score_inversion.md` | 0.2477 is owner-reported and reproduced on authenticated sibling raster; 0.3195 remains owner/secondary-reported, not agent-verified; no 27GEMSDOE live score |
| Distinct ranked hypotheses, validated before weekly slot | H28 registry renders five distinct ideas; H28-1 passed its frozen catalogue-internal gate; H28-2/3/4 are untried, H28-5 conditional on data access | no slot used; H28-1 is unscored and is not a fifth weekly candidate; holdout is not organizer truth |
| INGENIOUS/USGS graph and fault context | Existing named 345-link T-v2 graph, NBMG `FID`/kinematics, vector holdouts and Slot 4 preserved | graph-centrality ranking and overlapping relay tests remain next work |
| Auditable knowledge base, sources, three passes, PR/merge | H28 protocol/evidence/candidate records, source/irregularity registers, this review file; PR #5 has an updated, complete description | live-score ingestion and official raw-data retrieval remain blocked; PR #5 is open and mergeable at the pre-merge review, with CI passing on head `064f742624f4c2422e07c5da42512638f299d61f`; merge attempt follows this audit |


## Pass 2 addendum — merging a parallel session that landed on `main` mid-flight (Session 4)
While this branch was open, PR #5 (`arena/01a0fec2-gemsdoe27`, the H28-1 edge-coherence work) merged to `main`, so this branch had to be merged with it rather than fast-forwarded. 15 files conflicted; every resolution kept **both** sessions' work:
* `src/gems27/oof_detector.py`: both sessions independently added an optional extra-band matrix, under different names (`extra_features` on main, `extra` here). The merged function accepts **either alias**, keeps main's shape validation and keeps this session's chunked gather/predict (the box has 3 GB of RAM; main's dense `np.concatenate` over 5.1 M rows would not fit with a 40-band memmap). Both callers work unchanged.
* `scripts/verify_downloads.py`: main verifies a separate `h28_1_research` candidate injected from `h28_1_candidate_manifest.json`; this session added `quinary_probe`. The merged slot tuple covers both, so the audit runs **147 checks over 6 files with 0 failures** (79 before either session).
* `scripts/build_site.py`: three additive conflicts (evidence loaders, derived-number blocks, the executive-summary slot table) unioned; the duplicated slot-4 row that the union produced was removed, and both the Slot-5 probe row and the H28-1 research box render.
* `registry/sources.json` (18 + 4 = 22 rows), `registry/irregularities.json` (28 + 8 = 36 items) and `registry/hypotheses.json` (16, ids unique) were merged by id with main's refreshed statuses as the base; `README.md` and this file were unioned.
* Generated files (`docs/*.html`, `index.html`, `docs/data/sources.csv`, `knowledge/02`, `knowledge/05`) were taken from main and then **regenerated** from the merged registries, so the site and the derived knowledge docs have one source of truth.
* **Numbering collision resolved:** main already had `knowledge/08_preregistration_H28-1.md` and `knowledge/09_...`; this session's findings document was renamed to `knowledge/10_session4_farfield_measurement_and_proxy_limit.md` and every reference updated.
* **Disclosed coincidence, not a conflict:** both sessions pre-registered gates on **seeds 140–149**. `holdout.make_split` is deterministic in the seed, so the two gates ran on the *same* 40 hidden-truth cells with different candidates. Their results are therefore correlated, not independent replicates; neither session knew of the other when it froze its seeds. Any future claim that "two gates agree" must account for this.
* Not re-run and not claimed: main's `scripts/prepare_data.py` now requires a LiDAR metadata sidecar (`paths.LIDAR_META`) that this sandbox's `data_cache/` does not contain, so the prepared matrix was **not** rebuilt here. Every Session-4 number rests on the matrix already on disk, `data_cache/prepared/features.npy` sha256 `83ed2704…`, and `data_cache/prepared/features_aug.json` pins that base sha so a future rebuild cannot silently change the comparison.
* After the merge: **65 tests pass** (59 from this session's run + 6 from main), site rebuilt, `verify_downloads.py` 147/0.

---

# Session 5 (2026-10-03) — H27-10 negative result and H27-5b geologist-review exports

## Pass 1 — implement and verify

* Re-read `README.md`, `AGENTS.md`, and `knowledge/06_limitations_and_access.md` at session start. Continued the Session 5 priorities without accessing DrivenData.
* **H27-10 integrity record:** preserved the original failed spacing diagnostic in `evidence/h27_10_annulus_holdout_initial.json`; the corrected runner rechecked the same already-used seeds 150–159. All data checks pass on the corrected output, while the cell results, +0.00084615 mean paired ΔDTI, 4/4 folds, 7/10 seeds, annulus efficiency 0.03357 vs 0.05212 break-even, and frozen FAIL outcome are unchanged. This is an integrity recheck, not fresh confirmation. Updated Addendum F, the irregularity record, the tested-hypothesis entry and the Session 5 screen.
* **H27-5b class:** implemented four exclusive reviewer classes in `src/gems27/topology_classes.py`; assigned the exact inter-FID + same non-generic NBMG NAME + `kinematic_compat=true` class to the existing z≥3 deduplicated T-v2 candidate set (345 short 1–4 km links). Generated 81 focused rows (73 end-to-end, 4 abutting, 4 tip-to-tip oblique), all-link review fields, per-row source URLs/arguments, `docs/data/topology_priority_h27_5b.csv`, focused WGS84 GeoJSON, full class-count JSON and registry/evidence summaries.
* Generated the focused map preview `docs/assets/fig_map_h27_5b_priority.png` with proposed H27-5b gaps in red, other T-v2 gaps in gray, and mapped catalogue pixels in dark ink. Added a searchable review-class column, counts, source links and explicit caveats to `docs/topology.html`; the map and focused downloads are exposed on the page.
* Updated `knowledge/02`, `knowledge/04`, `knowledge/06`, `knowledge/07`, `knowledge/11`, `registry/next_hypotheses.json`, `registry/hypotheses.json`, `registry/sources.json`, and `registry/irregularities.json`. Four genuinely untried hypotheses remain; H27-10 is recorded as tested/rejected and is absent from the untried list.
* Rechecked official source pages through the page-fetch service: NBMG Qfaults feature-layer metadata, OSTI-hosted Faulds & Hinz, and the Berkowitz AGU/Wiley publisher abstract. Current retrieval statuses are in `registry/sources.json`. The raw GDR #1391 packages were not downloaded or re-hashed in this update.

## Pass 2 — review for bugs, assumptions, and edge cases

* **Class-rule review:** the population restriction is explicit (the existing 345 T-v2 links, all 1–4 km; no link generation). The exclusive classes sum to 345: 230 same-FID, 81 H27-5b, 22 other-name compatible inter-FID, and 12 conflict/unknown inter-FID. The focused CSV and GeoJSON independently contain 81 rows/features; rows satisfy different FIDs, same NAME and compatibility; gaps sort ascending with link ID tie-break; kinds total 73/4/4. The output records that unknown kinematic fields can pass, FIDs are records in one NBMG compilation, and graph bridges are graph properties, not fault truth.
* **Interpretation guard:** graph-ΔP was not used to choose the class; the prior graph-value ranking and overlapping en-echelon step-over test remain refuted as holdout-improvement signals. Geometry cues are not structural diagnoses, and Faulds & Hinz frequencies are context rather than candidate-specific evidence. The Tier-2 whole-FID enrichment (0.178296 vs 0.020384, 8.75×; seeds 120–129) is labeled catalogue-internal review prioritization only—not hidden-label truth, transfer, or live-score gain.
* **H27-10 audit:** corrected the stale fold count in records from 3/4 to the evidence-backed 4/4. Preserved the first-run false-negative diagnostic and disclosed the same-seed integrity recheck; no algorithm, threshold, gate or result was tuned.
* **Generated-page/test order:** one focused test initially read a stale HTML artifact after a source edit; rebuilding the JSON-derived site resolved it. Calling the `pytest` console entrypoint failed to import the namespace `scripts` package in this sandbox; the repository-prescribed `python -m pytest` invocation ran the full suite successfully. These were invocation/order issues, not product-code failures.
* **Verification:** focused topology/site tests: 17 passed. Full suite: **82 passed**. `ruff check src scripts tests`, Python compilation of the changed generators/module, and `git diff --check` passed. `scripts/verify_downloads.py`: **0 failures** across the existing weekly files and separate H28-1 research file; no submission file or manifest was changed.

## Pass 3 — recheck against the original request

| request / constraint | result | remaining limitation |
|---|---|---|
| Keep 3–5 current untried hypotheses; do not call H27-10 untried or spend a slot on it | Four hypotheses remain in `knowledge/07_untried_hypotheses.md` and `registry/next_hypotheses.json`; H27-10 is a tested failed result. No weekly slot was used. | Future candidate needs its own preregistration and fresh unused seeds. |
| Distinct geologist-reviewable short inter-FID class, exact filter/count, map and table | 81/345 exact-filter links; focused CSV, GeoJSON, static footprint preview, GIS-ready source links, searchable site column and exclusive counts are present. | Geologist review has not yet been performed; the inputs are catalogue records, not field-verified faults. |
| Keep graph importance separate from truth/live-score claims; preserve refuted signals | Explicit cautions are in the site, knowledge and machine-readable summaries. Both graph-ΔP ranking and overlapping en-echelon step-overs remain refuted as holdout-improvement signals. | No organizer-created hidden labels or live-score evidence is available. |
| Official sources, honest retrieval status, knowledge/evidence/irregularity trail | Official NBMG/OSTI/Wiley pages rechecked; source statuses, H27-10 initial/corrected evidence and irregularity record updated. | GDR #1391 raw packages were not fetched/re-hashed; no new external package is claimed obtained. |
| Preserve one-click submission TIFF, ≤200-character note, executive-summary steps and format checks | Existing files/site/notes remain unchanged; audit reports zero failures. | Portal acceptance still requires human submission; no upload was attempted. |
| Maximize P(Win), Own the Outcome; no DrivenData access | H27-10 rejected on its frozen gate; H27-5b is review-only and no candidate score is inferred. No DrivenData site access, upload or score occurred. | Catalogue-internal evidence cannot guarantee transfer to organizer labels. |
