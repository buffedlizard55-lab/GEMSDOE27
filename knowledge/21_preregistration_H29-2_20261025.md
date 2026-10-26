# Preregistration — H29-2 DIPDIRECT-conditioned edge projection (frozen before code)

**State:** preregistered, not run. Frozen after the candidate screen in `knowledge/20_candidate_screen_20261025.md` and before implementing the feature. Lane: **H29-2 only**. This is not the H28-6 radiometric lane in open PR #18.

## Hypothesis, mechanism, and named mimic

**Hypothesis.** Among the current D-detector's line candidates, a `rtp` or `depth_to_base_surf` gradient edge sampled 100–300 m down-dip from a target pixel will better identify the corresponding surface-fault location when the local *visible* NBMG `DIPDIRECT` field points down-dip. The candidate transforms project edge evidence **up-dip** by one, two, or three 100 m pixels. No numerical dip angle or unverified `depth/tan(dip)` value is assumed; the restored Qfaults attributes contain direction categories, not a measured dip magnitude.

**Layers / signature.** The hash-pinned 32-band GeoDAWN cache (`rtp`, `depth_to_base_surf`), the 15 existing label-free subsurface transforms, and the official-source-attributed NBMG Qfaults line attributes `DIPDIRECT`. The three predeclared added features are (1) up-dip-projected RTP edge, (2) up-dip-projected basement-depth edge, and (3) their minimum/concordance. For each target pixel, sample the edge field at the target plus `d × local_down_dip_unit`, for fixed `d∈{1,2,3}` pixels; take the maximum over these offsets. A local direction is usable only when a specified direction-bearing visible vector is within 50 pixels (5 km). Else all three added features are zero. Directions are rasterized from visible vector features only and are not filled from hidden FIDs.

**Why a catalogue-missing fault could be found.** A potential-field or basement edge can be laterally displaced from the surface expression of a dipping structure; projecting the deep edge toward the surface on the up-dip side is a physical correction rather than another emission-thinning rule. The test only asks whether this directional relation transfers from visible segments to withheld FIDs; it does not assume every unmapped fault has the same geometry.

**Named non-fault mimic.** Basin-margin lithologic contacts or cover-induced edge termination combined with inaccurate/ambiguous mapped dip direction. Other risks: sparse/biased direction attributes, mixed-generation faults, and remanent magnetic boundaries.

## Exact holdout and evaluation

- **Shared template tools:** `gems27.holdout` whole-FID split and 600 m buffer; `gems27.oof_detector` cached feature stack / fixed HGB instrument; `gems27.metric` binary DTI; `gems27.submission.write_geotiff` and `verify_geotiff`. There is no `evaluate_holdout.py` or `submission_writer.py` in this checkout; no private copy will be introduced.
- **Whole-segment unit:** vector feature index in the restored NBMG Qfaults inventory, mapped to the labels through `VectorAttribution.pix_fid_idx`. Select 20% of distinct positive FIDs per footprint quadrant, stratified by group centroid, using seeds **300–309**. If a selected FID spans quadrants, hide its entire mapped label support across the full grid. Seed 300–309 are reserved for this frozen H29-2 screen only.
- **Buffer:** exclude the 6-pixel (600 m) ring around the hidden segment pixels from both model training and scoring (hidden truth cells remain scoreable). Any visible FID with source line pixels within that ring is excluded from the dip-direction feature source for that split. Visible label cells are passed as `known` and masked pixel-exactly in the evaluator.
- **Catalogue-derived features:** the only new catalogue-derived feature is the DIPDIRECT direction field. For each split, the implementation must demonstrate that no selected hidden FID is among the source features and no source pixel is inside the 600 m hidden ring. All 32 GeoDAWN bands and the 15 subsurface transforms are label-free.
- **Paired arms:** D = 32-band prepared feature cache + the frozen 15 subsurface transforms; D+dip = the same inputs plus the three fixed H29-2 transforms. Same positive labels, training mask, negative sample (`neg_ratio=10`), HGB parameters (100 iterations, 31 leaves, learning rate 0.08, L2=5), emission geometry and 38,000-dot budget in each arm. Detector random state is `2026 + seed`.
- **Emission/scoring:** ridge NMS sigma=1.0; candidate mask is the buffered scoring region, outside the visible catalogue at pixel-exact B2 (distance >2 px), and within the footprint; priority Poisson disk minimum distance 2.8 px; exactly 38,000 dots per arm/seed or integrity fails. Score with `gems27.metric.dti_binary`, α=0.2, β=0.8 and the 3-pixel / 300 m triangular kernel. Sum TPw/FPw/FNw over seed replicates before computing pooled DTI; bootstrap whole seeds (10,000 resamples, RNG seed 11) for 95% CIs. Also report per-seed paired deltas and withheld-positive occurrences. These are **HOLDOUT-DTI**, not organizer scores. The sole full-fit predictor in E3 uses seed 3026.
- **Feature canary:** each of the three added features alone, direction-invariant AUC `max(AUC,1−AUC)` against the hidden-segment positives, with negatives sampled only from the valid scoring region outside all catalogue labels. Compute for all 10 seeds; any AUC >0.90 is a leakage failure and stops the experiment. Report exact AUCs and sample counts.

## Frozen gates and 3-experiment / 2-hour budget

1. **E1 — canary and holdout integrity:** verify the 10 whole-FID splits, no hidden IDs in feature sources, zero source pixels within the hidden buffer, nonempty truth, and each feature's canary. Any AUC >0.90, missing/zero FID mapping, or split-integrity failure stops with a negative result.
2. **E2 — paired holdout:** gate passes only if pooled candidate HOLDOUT-DTI exceeds paired D control, mean paired ΔDTI >0, seed-bootstrap 95% CI lower bound >0, at least 8/10 seeds improve, and E1 is clean. No parameter search, retuning, alternate feature set, or seed shopping.
3. **E3 — one full-fit uniqueness/format pass:** use all catalogue FIDs to build the full-map DIPDIRECT feature and full-fit surface, then compare the continuous surface against every pinned parallel-registry raster and every in-repo candidate TIFF **before placement**. Stop and register a duplicate if any Spearman rank correlation >0.90. Only if that surface gate passes, make the 38,000-dot output and re-check directed ≤3 px overlap against every raster; stop/register a duplicate if any >70%. If nonduplicate, write one research-only all-finite GeoTIFF and single-TIFF ZIP, validate CRS/shape/transform against the cached sample template, finite [0,1] values in-footprint, byte hashes, and note length ≤140 characters. This is **not** a weekly slot and does not authorize an upload.

At most these three experiments and two hours. No upload, no selection into a weekly slot, and no claim of an organizer score. If E2 fails but E3 is reached without a duplicate, any TIFF is a **NEGATIVE RESEARCH ARTIFACT — NOT APPROVED TO SUBMIT**. If a duplicate threshold is crossed, stop rather than creating a new file. `verdict=promote` means only “eligible for the separate selector to review”; `ok_to_submit` remains false absent selector approval.

## Frozen file identifiers and note

- Submission-style name: `GEMSDOE27-H29-2-DIPDIRECT-EDGE-UPDIP-38K`.
- Note target (≤140 chars): `H29-2 DIPDIRECT up-dip edge projection; HOLDOUT-DTI gate; unscored research artifact; not approved to submit.`
- Research artifacts only: `docs/downloads/research/`; do not edit any weekly slot manifest.

## Inputs and source status

- Grid/template, label mask, training feature cube, and NBMG Qfaults JSON must match `data/manifest.json` SHA-256 pins before use. Prepared feature cache must match its hash in `data_cache/prepared/features.json`.
- NBMG source record and manual review link: `registry/sources.json` / https://web2.nbmg.unr.edu/arcgis/rest/services/Qfaults/Qfaults_INGENIOUS/MapServer/0 . The local Qfaults mirror can be independently SHA-checked here; a fresh official endpoint fetch is not claimed because the host is outside the session's outbound allowlist.
- Competition rules and submission-format links remain linked from `registry/sources.json`; no automated access to DrivenData is permitted by repository policy.
