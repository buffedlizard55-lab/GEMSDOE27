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
4. **Reaching `0.3195` requires higher base recall or lower base false positives beyond `H19-5`:** Stacking T-v2 (`+1,259` gap-closure dots) and H27-4 (`-5,355` 100 m flank-shadow dots) on the `0.2477` base models to **`~0.262–0.270`**. Closing the remaining gap to `0.3195` requires a materially stronger scarp/lineament detector or multi-scale 2D CNN/U-Net segmentation (as in Hermant et al. 2025 `FaultSEG`) rather than pixelwise tabular boosting alone. The pinned LiDAR sidecar reports 716 tile links, 706 successful derived tiles and 10 failures; this is an owner-mirror inventory, not a newly verified USGS download list.

## Data audit corrections (2026-10-02)

- **LiDAR feature labels were wrong, values were not shown to be wrong.** The pinned sibling sidecar (`data/external/lidar_scarp_features.json`, SHA-256 `9ef0df6e87598a8b0cd52fe821661e5fdb3a00568c5d9b1c5d61fd6b242dcd41`) and raster descriptions identify bands 1–10 as `ex_max`, `ex_mean`, `step_max`, `lapneg_max`, `lappos_max`, `downface_max`, `upface_max`, `cross_max`, `relief`, and `coh100`. `scripts/prepare_data.py` now labels these positional channels accurately and asserts all 12 descriptions. The rebuilt 32-column matrix has the same SHA-256 as the earlier matrix (`83ed2704…`), confirming no numerical channel change; the earlier feature-name interpretations are withdrawn. H28-1 is not run until the updated metadata check passes.
- **DEM inventory count corrected.** Some previous prose claimed 1,701 tiles. The hash-pinned `dem_links.json` and pinned sidecar instead report 716 links/tiles total, of which 706 succeeded and 10 failed. The exact 1,701 figure was not supported by the restored inventory and has been removed from active prose. This count describes the owner mirror, not an independent official USGS download audit.

---

## Access needed from the human owner

1. **DrivenData submission & live score recording:** Upload **Slot 1 (`5512495c6bd1`)** on DrivenData, record the returned public score in `registry/live_scores.json`, and follow the pre-committed Slot 2 / Slot 3 decision tree (`3ebd51534bb1` or `d466b251f309`).
2. **Portal error message (if any):** If any upload is rejected, paste the exact portal error string and filename into `registry/irregularities.json`.
3. **1 m DEM/GPU runner (for >0.30 scarp segmentation):** The local owner-mirror inventory contains 716 links (706 successful derived tiles; 10 failed), not the previously reported 1,701. Reprocessing raw 1 m DEMs or training a 2D U-Net / `FaultSEG` model on multi-azimuth hillshades still requires an external runner with sufficient storage, full internet and a GPU; direct raw-tile retrieval was not verified in this sandbox.

---

## Current prioritised next steps

1. **Ingest the live Slot 1 A/B score (`score(5512495c6bd1) - 0.2477`):**
   - Compute the empirical live efficiency of the 1,259 T-v2 dots from the exact score difference.
   - Select **Slot 2** (`3ebd51534bb1` d2.8 + T-v2 vs. **Slot 3** `d466b251f309` d1.5 + H27-4 100 m flank-shadow prune + T-v2).
2. **Upgrade the OOF detector from tabular `HistGradientBoostingClassifier` (`0.0861` holdout DTI) to a multi-scale spatial U-Net / `FaultSEG` ridge detector:**
   - Hermant et al. (2025) demonstrated that 2D convolutional segmentation (`FaultSEG`, PR-AUC `0.595`) on LiDAR DEM + slope + NIR substantially outperforms pixelwise or small-receptive-field models because it captures 1–5 km linear continuity and rejects nonlinear geomorphology (paleo-shorelines, canyon rims, stream boundaries).
3. **Integrate Siler (2022) slip & dilation tendency (`doi:10.5066/P9YL58W6`) and DeAngelo et al. (2022) heat flow (`doi:10.5066/P9BZPVUC`) via GitHub Actions:**
   - Extend `.github/workflows/fetch-vector-faults.yml` to fetch the Siler (2022) shapefile attributes (`Shapefile_INGENIOUS area.zip`, 27.35 MB) and test whether weighting H27-5b links by slip/dilation tendency further improves `FID_trace` holdout efficiency above `0.1783`.
