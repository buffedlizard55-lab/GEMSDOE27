# Limitations, access needed, and work for the next session

## What was resolved in Session 2 (previously listed as Next Steps 1–7 in Session 1)

1. **Named, attributed vector fault graph (`src/gems27/vector_graph.py`, `scripts/fetch_vector_faults.py`, `.github/workflows/fetch-vector-faults.yml`):**
   - Restored the 1,179 NBMG INGENIOUS Quaternary fault polylines (`Qfaults [INGENIOUS 6-27-2023]`, `data_cache/qfaults_v2_in_footprint.json`, SHA-256 `4d6efc7bb3659ea2545353fcec574ef085b0acdb189c7590e4420a7c6c57b41c`), matching **98.42%** of `labels.tif` pixels within 100 m and **99.97%** within 200 m.
   - Annotated all **345 shipped T-v2 candidate dossiers** (`registry/topology_candidates.json`, `docs/data/topology_links.{csv,geojson}`) with official NBMG/USGS fault attributes (`FID`, `NAME`, `NUM`, `FTYPE_`, `SLIPSENSE`, `DIPDIRECT`, `MAPSCALE`, `same_fid`, `same_name`, `kinematic_compat`).
2. **Three-tier vector holdout & H27-5 kinematic typing (`scripts/run_vector_topology_validation.py`, `evidence/vector_topology_validation.json`, Addendum B seeds 120–129):**
   - **Tier 1 (`component`, 8-connected raster systems):** `z>=3 dedup` efficiency = **`0.2926`** vs **`0.0586`** rotated-cone control (**5.00x**).
   - **Tier 2 (`FID_trace`, whole NBMG `FID` multipart polylines):** `z>=3 dedup` efficiency = **`0.1003`** vs **`0.0204`** control (**4.92x**, clearing both $m(0.2477)=0.0522$ and $m(0.30)=0.0638$); **H27-5a (`inter-FID + kinematic_compat`)** rises to **`0.1374`** (**6.74x** control), and **H27-5b (`inter-FID + same_name + kinematic_compat`)** reaches **`0.1783`** (**8.74x** control).
   - **Tier 3 (`NAME_zone`, entire 20–70 km named fault zones):** efficiency = **`0.0014`** vs **`0.0012`** control, proving that 1–4 km links bridge unmapped segments *within* and *between traces of* fault zones rather than across 15–30 km inter-range basins.
3. **Honest out-of-fold (OOF) 4-quadrant spatial-CV detector (`src/gems27/oof_detector.py`, `scripts/run_oof_hypothesis_gates.py`, `evidence/oof_hypothesis_gates.json`, Addendum C seeds 130–139):**
   - Trained a 4-fold spatial-CV `HistGradientBoostingClassifier` (600 m buffer) on the 32-band label-free feature matrix (`data_cache/prepared/features.npy`, built by `scripts/prepare_data.py` with the mislabelled `tc` band excluded).
   - **H27-1 (`plus_T_v2`):** validated on the non-leaky OOF base (`+0.0115` mean paired DTI gain, **4/4 folds**, marginal efficiency `0.2251`).
   - **H27-4 (tip-shadow pruning):** validated on the non-leaky OOF base (`prune_r1_100m` removes dots with efficiency `0.0034` vs `0.0521` live break-even, `+0.0022` solo in **4/4 folds**, and **`+0.0141` in 4/4 folds** when stacked with T-v2). Shipped as **Tertiary Slot 3 candidate (`d466b251f309`)**.
   - **H27-3 (isolated-dot removal):** refuted on the non-leaky OOF base (`-0.0010` DTI, **0/4 folds**, removed efficiency `0.0329 > m_oof = 0.0175`) and rejected without spending a submission slot.
4. **Full literature & rules verification (`registry/sources.json`, `docs/data/feed.json`):**
   - Verified all 7 chunks of the Official Rules (`https://docs.nlr.gov/docs/fy26osti/96647.pdf`), all 8 chunks of Hermant, Kiersnowski & Bellanger (2025, `https://pangea.stanford.edu/ERE/db/GeoConf/papers/SGW/2025/Hermant.pdf`), GDR Submission #1391 (`https://gdr.openei.org/submissions/1391`), ScienceBase items (`657e1d85d34e23d3533209f7`, `628d4fabd34ef70cdba3c4a4`, `62979746d34ec53d276c113b`, `6297d2fad34ec53d276c5b28`), and the full verbatim task prompt in `README.md`.

---

## Remaining limitations

1. **No live score for 27GEMSDOE yet:** The agent never accesses or uploads to `drivendata.org` (per DrivenData Terms of Use). All three shipped 27GEMSDOE candidates (`5512495c6bd1`, `3ebd51534bb1`, `d466b251f309`) are **UNSCORED** until the human owner uploads them.
2. **Real hidden test set vs. catalogue holdout:** While T-v2 is now validated on both 8-connected components (`0.2926`) and whole NBMG `FID` vector polylines (`0.1003`, `0.1374` with H27-5a, `0.1783` with H27-5b), any holdout constructed from `labels.tif` tests held-out pieces of the existing compilation rather than the organisers' newly created expert labels. Only the live Slot 1 A/B score (`score(5512495c6bd1) - 0.2477`) measures the exact transfer rate to the private/public test labels.
3. **Cause of the historical `"Predicted values must be in range [0, 1]"` portal message:** Because the portal validator is closed-source, our fix is defensive (providing exact `{0.0, 1.0}` `float32` inside the footprint, `NaN` outside with `nodata=NaN`, a single-file `.zip`, and an `allfinite` zero-outside fallback, verified by 66 standalone checks in `scripts/verify_downloads.py`).
4. **Reaching `0.3195` requires higher base recall or lower base false positives beyond `H19-5`:** Stacking T-v2 (`+1,259` gap-closure dots) and H27-4 (`-5,355` 100 m flank-shadow dots) on the `0.2477` base models to **`~0.262–0.270`**. Closing the remaining gap to `0.3195` requires a materially stronger scarp/lineament detector trained on the full 1 m 3DEP LiDAR DEM tiles (`dem_links.json`, 1,701 USGS tiles) or multi-scale 2D CNN/U-Net segmentation (as in Hermant et al. 2025 `FaultSEG`) rather than pixelwise tabular boosting alone.

---

## Access needed from the human owner

1. **DrivenData submission & live score recording:** Upload **Slot 1 (`5512495c6bd1`)** on DrivenData, record the returned public score in `registry/live_scores.json`, and follow the pre-committed Slot 2 / Slot 3 decision tree (`3ebd51534bb1` or `d466b251f309`).
2. **Portal error message (if any):** If any upload is rejected, paste the exact portal error string and filename into `registry/irregularities.json`.
3. **1 m USGS DEM tile cache / GPU runner (for >0.30 scarp segmentation):** Downloading and processing the 1,701 1 m 3DEP LiDAR DEM tiles in `data_cache/dem_links.json` (or training a 2D U-Net / `FaultSEG` model on multi-azimuth hillshades) requires an external runner with full internet + GPU access.

---

## What Session 3 resolved
1. **"Ingest the live Slot 1 A/B score"** — could not be done: `registry/live_scores.json["27GEMSDOE"]` is still `null`, so no 27GEMSDOE file has been uploaded. Blocked on the owner, unchanged.
2. **Replaced that blocked step with something that needed no upload:** all 20 matchable scored rasters were recovered by SHA-256 and inverted against the official metric. This produced the exact forward identity (including the crowding term ρ), a second independent |G| estimate (12,226 px, 2.2 % from the sibling's), a retention rule validated on two live pairs (−0.1 %, +4.0 %), the budget optimum (d = 2.25–2.8 → 0.2550), and a concentration ranking that shows the whole H19-5 family plateauing at 5.3–5.7× blind. See `knowledge/07_live_score_inversion.md`.
3. **Built slot 4** — the first candidate stacking all three validated increments at the live-anchored budget optimum (`23ad46a4d7ba`, 41,507 px). 79 verification checks pass.
4. **Three ideas tested and rejected with evidence** (H27-6 coverage-optimal thinning, H27-7 union-recall ensembling, H27-9 habitat tomography) so no future session repeats them.
5. **Upgraded the OOF detector to a spatial/convolutional ridge detector — NOT done.** Still the top unfinished technical item; see next steps.

## Prioritised next steps for Session 4
1. **Ingest the live score for whichever slot the owner uploads** (`registry/live_scores.json["27GEMSDOE"]` is still `null`). Slot 1 vs slot 3 is the pre-registered A/B that settles whether the H27-4 prune pays live — that single comparison converts the geometric/hybrid model disagreement (0.2439 vs 0.2704) into a measurement. Record the exact portal response text either way.
2. **Detector upgrade — the only remaining route.** Session 3 proved arithmetically that 0.3195 needs concentration above 5.7× blind (the family plateaus at 5.3–5.7) or retention ≈1.0 at ~44k px (H27-6 shows the obvious approach fails). Both are detector problems. Upgrade `src/gems27/oof_detector.py` from the tabular HistGradientBoosting classifier (holdout DTI 0.0861) to a multi-scale spatial/convolutional ridge detector in the direction of Hermant et al. (2025) FaultSEG. Gate it on the 4-fold spatial-CV holdout with **fresh seeds (140–149)**, pre-registered before running.
3. **Rank the 345 T-v2 links by graph-connectivity value**, not just local z-score: Δ(component merge) and load-bearing-bridge centrality per Berkowitz, Bour, Davy & Odling (2000). A link that merges two large clusters is worth far more at the percolation threshold than one that merges two small ones. Cheap; uses only data already in `data_cache/`.
4. **H27-2 step-over/relay linking with *overlapping* en-echelon offsets** — never generated. The tested variant used non-overlapping offsets only.
5. **Siler (2022) slip/dilation tendency + DeAngelo (2022) heat flow** — still blocked locally (USGS/ScienceBase hosts unreachable from the sandbox). Advance by writing the GitHub Actions workflow only; test whether weighting H27-5b links by slip/dilation tendency beats `FID_trace` efficiency 0.1783.
6. **Do not re-propose** H27-3 (refuted), H27-6 (refuted, 13 % worse), H27-7 (bounded gamble, downside −0.086), H27-9 (not identifiable), Tier-3 `NAME_zone` gap closure (efficiency 0.0014), or any pure-emission-geometry tweak beyond d = 2.25–2.8 (ceiling ≈0.255).

## Prioritised next steps for Session 3 (superseded — kept for audit)

1. **Ingest the live Slot 1 A/B score (`score(5512495c6bd1) - 0.2477`):**
   - Compute the empirical live efficiency of the 1,259 T-v2 dots from the exact score difference.
   - Select **Slot 2** (`3ebd51534bb1` d2.8 + T-v2 vs. **Slot 3** `d466b251f309` d1.5 + H27-4 100 m flank-shadow prune + T-v2).
2. **Upgrade the OOF detector from tabular `HistGradientBoostingClassifier` (`0.0861` holdout DTI) to a multi-scale spatial U-Net / `FaultSEG` ridge detector:**
   - Hermant et al. (2025) demonstrated that 2D convolutional segmentation (`FaultSEG`, PR-AUC `0.595`) on LiDAR DEM + slope + NIR substantially outperforms pixelwise or small-receptive-field models because it captures 1–5 km linear continuity and rejects nonlinear geomorphology (paleo-shorelines, canyon rims, stream boundaries).
3. **Integrate Siler (2022) slip & dilation tendency (`doi:10.5066/P9YL58W6`) and DeAngelo et al. (2022) heat flow (`doi:10.5066/P9BZPVUC`) via GitHub Actions:**
   - Extend `.github/workflows/fetch-vector-faults.yml` to fetch the Siler (2022) shapefile attributes (`Shapefile_INGENIOUS area.zip`, 27.35 MB) and test whether weighting H27-5b links by slip/dilation tendency further improves `FID_trace` holdout efficiency above `0.1783`.

---

# Session 4 additions (2026-10-02)

## New limitations, measured rather than assumed
1. **The catalogue-internal holdout has reached its resolution limit.** Hidden truth in every gate this programme has run is catalogue pixels, so 100 % of it (120,983 px over the Addendum-D cells) lies at distance 0 from the published catalogue and Habitat A (>= 300 m away) contains *zero* truth by construction. Credit shares for the base arm: 36.8 % on the spine, 51.5 % at 100 m, 11.4 % at 200 m, 0.37 % at 300 m-1 km, 0.0 % beyond 1 km. The live-scored 0.2477 emission puts 81.4 % of its dots >= 300 m away. **No further gate on this proxy can decide whether a better detector pays**; `evidence/arm_habitat_decomposition.json`, `scripts/diagnose_arm_habitats.py`.
2. **Two arms passed both registered Addendum-D criteria and were still not promoted**, because their gain is entirely catalogue proximity and their far-field behaviour is the habitat the h18-4 live probe measured at 1.62x blind. This is the first time in the programme a *passed* gate was overridden by live evidence; the reasoning is written down so it can be audited (`knowledge/08` sections 3-4, `knowledge/03` Addendum E).
3. **dP is an ordinal, not a fine ranking.** Berkowitz-style P counts systems above l_min = 2 km, so a single merge changes it by exactly {-1, 0, +1} x P/n_ge; 159 of 345 links are non-zero and a link joining two systems that are both already >= 2 km *lowers* P. The continuous tie-break (change in sum l^2) was disclosed before the gate ran.
4. **No critical value for sum(l^2)/area is claimed anywhere.** It is the standard continuous connectivity measure for 2-D line networks, but a threshold could not be verified from an official source reachable from this sandbox (only github.com, api.github.com, codeload.github.com and pypi.org respond). Reported as 56,580 km^2 (1.095 per unit area) and used only as a relative measure.
5. **`data_cache/prepared/features.npy` band `det_local_relief` is signed** (min -207.686, max +299.416, 64.7 % negative, 3,061 NaN) and the `lidar_*` columns carry 24.63 % NaN (not 0). Code that assumes a non-negative descriptor silently misbehaves; the pre-registered anisotropy statistic reached 6.6e7 on that band before the disclosed fix.
6. **CI still cannot exercise the raster-dependent checks.** `data_cache/` is git-ignored by design and restoring it needs read access to the sibling repositories, which the workflow's `contents: read` GITHUB_TOKEN does not have. 59 tests pass locally with the cache restored; two raster checks are skipped in CI. Granting a token with sibling read access is an **owner action**.

## Access needed (unchanged items plus two new ones)
* Owner: upload one file and report the score back (the agent never uploads, never touches drivendata.org). **Slot 5 is the highest-information upload available** (`knowledge/03` Addendum E has the registered reading).
* Owner: re-check the submissions page so `registry/live_scores.json["27GEMSDOE"]` stops being null, and confirm which leaderboard rows belong to the owner's entity (one-entity / 3-per-week compliance).
* Runner (available now, needs a dispatch): `gh workflow run fetch-gdr-external-layers.yml` after this branch is merged, then `gh run download <id> --name gdr-external-layers`. That yields the paleo-geothermal, 2 m temperature-probe and Quaternary-volcanics layers, hash-verified and clipped.
* Outside the sandbox: USGS 1 m 3DEP tiles (the 716-tile reduction cannot be redone here), a GPU for a FaultSEG/U-Net style model, and the Siler (2022) / DeAngelo (2022) slip- and dilation-tendency surfaces.

## Prioritised next steps for Session 5
1. **Dispatch and read the workflow** (`fetch-gdr-external-layers.yml`). If the three GDR layers arrive hash-verified, add them as feature groups and re-run the Addendum-D PR-AUC screen on them - but read the result through `scripts/diagnose_arm_habitats.py`, not through paired DTI alone, because paired DTI on this proxy only measures catalogue proximity.
2. **Ask the owner to spend Slot 5** (or Slot 1 first if a slot is free: Slot 1 vs the scored 0.2477 parent is still the cleanest A/B of the topology increment). Record whatever comes back in `registry/live_scores.json` and re-run `scripts/invert_live_scores.py` - every new (raster, score) pair sharpens |G|, the retention rule and the concentration ceiling.
3. **If Slot 5 comes back >= 0.2507**, rebuild the whole emission from the 72-band detector at the live-anchored budget (d = 2.25-2.8) and re-verify; that is the only path this repository has found that could approach 0.3195. If it comes back inside +/-0.003, **close the detector-feature route** and stop spending slots on feature work; the remaining levers are external data (step 1) and a deep model (needs GPU + 1 m tiles).
4. **Keep hunting for unregistered scored rasters in the sibling repositories.** Session 4 found the programme's most informative live measurement sitting unregistered for three sessions (h18-4). 5 of 27 registry rows are still SHA-unmatched (`ens12-adopted`, `dual-family-union`, `lidarscarp-ridge-top2pct`, GEMSDOE4 `combined`, `hgb88-topk03`); `scripts/fetch_scored_corpus.py` lists them.
5. **Do not re-propose, with evidence on file:** SGMC/geologic-map-gap emission (1.62x blind, live); connectivity-value ranking of links (0.2914 vs 0.2889, inside the random spread); overlapping en-echelon step-overs (0.0605 < 0.0638 break-even); oriented km-scale lineament features (+0.0010 PR-AUC); radiometric ratios (+0.0007) and thermal-point distances (+0.0005) as features on this footprint; isolated-dot removal; coverage-optimal thinning; union-recall ensembling; habitat tomography; emission geometry beyond d = 2.25-2.8.
