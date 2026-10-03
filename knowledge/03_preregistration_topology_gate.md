# Pre-registration: topology gap-closure gate (frozen before the confirmatory run)

Written 2026-10-02 (UTC), before running `scripts/run_topology_validation.py` on seeds 100-109.

## What was exploratory (disclosed)
A quick prototype (seeds 0-2, not shipped; summarised in `evidence/exploratory_seeds_0_2.md`) produced the
design choices below. It showed forward-cone links were ~2x enriched over rotated-cone controls **only for gaps
of 1-4 km**; links of 0.3-1 km showed no enrichment (ratio 0.6-1.0). The 1 km lower bound is therefore a
*fitted* choice; the confirmatory seeds below were not looked at.

## Candidate rule T-v1 (frozen)
* Graph: skeletonise the **known** catalogue (all labels not hidden in the fold), 8-connectivity.
* Tips: free skeleton ends with a >= 4-layer, 800 m chain (tangent defined).
* Link: nearest skeleton pixel of a *different* system inside a forward cone of +-30 deg around the tip
  tangent, gap 10-40 px (1.0-4.0 km). One link per tip.
* Emission: dots every 3 px along the straight link, skipping the pixel next to each tip.
* Redundancy rule: dots within < 3 px of the base emission are dropped before scoring the addition.
* Controls: identical procedure with the cone rotated by +90 and -90 deg (same endpoints, same gap range).

## Validation protocol (frozen)
* Quadrant folds as in the sibling harness (NW, NE_LidarGapHeavy, SW, SE); in each, 20 % of 8-connected
  catalogue components are hidden truth; all other catalogue pixels are known (masked).
* Replicates: seeds 100-109 (10 hidden-set draws x 4 folds = 40 cells).
* Efficiency of a pixel set S added to base B: eff = dTP_w / dFP_w (official kernel, 3 px).
* Inclusion threshold for a set to raise DTI: m(DTI) = 0.2 DTI / (1 - 0.2 DTI) (derived in `metric.py`).
  Conservative reference DTI = 0.30 -> m = 0.0638.

## Gate (all must hold; otherwise T-v1 is NOT promoted and no slot is spent on it)
1. Pooled forward efficiency >= 2.0 x pooled control efficiency (mean of the two controls).
2. Pooled forward efficiency >= 0.10 (>= 1.5 x m(0.30)).
3. Forward efficiency > control efficiency in >= 3 of 4 folds (pooled over seeds).
4. Paired DTI against the dotted-H19-5 base (which is *leaky*: H19-5 was trained on all labels, so its coverage
   of hidden pieces is inflated and the paired gain is conservative): mean gain over the 4 folds > +0.001
   and no fold loses more than 0.01.

## Standing caveats (these are limits of the test, not of the gate)
* The hidden pieces are catalogue-internal. Shared segmentation or belt structure that makes catalogue pieces
  predictable from their neighbours inflates recall relative to genuinely new expert-mapped faults.
  The test measures *detectability of along-strike continuation in the catalogue's own geometry*, not the base
  rate of new expert faults in gaps. Only a live score can measure the latter.
* Seeds change the hidden set, not the catalogue; replicates are correlated. No significance claim is made.

---

# Addendum A - outcome of the registered run and pre-registration of T-v2 (written before seeds 110-119)

## Run history (disclosed)
* **Run A (discarded):** the first launch applied the minimum gap *before* choosing the nearest target, so a tip with a
  neighbour 4 px away produced a "10 px link" running along that neighbour. This deviated from the text above ("nearest
  skeleton pixel ... gap 10-40 px"). Caught by a unit test (`tests/test_graph_links.py`), fixed, stopped after seeds 100-104;
  its partial log is kept in `evidence/topology_validation_runA_partial_log.txt`.
* **Run B (as registered, seeds 100-109, 40 cells):** pooled forward efficiency 0.1183 vs controls 0.0573 (2.07x; the 2.0x bar
  is cleared narrowly); forward > control in 4/4 folds (5.14x, 2.53x, 1.44x, 1.70x); paired DTI gain vs the leaky dotted-H19-5
  base +0.0184 (per-seed +0.0159..+0.0225), no cell negative. **Gate T-v1: PASSED** (`evidence/topology_validation.json`).

## Post-hoc finding (seeds 100-109 only; exploratory)
Dot-level hit ratio rises monotonically with a 5-point evidence score z = [mutual] + [end-to-end] + [angle <= 15 deg] +
[local strike compatibility >= 0.4] + [merged length <= 8 km]: z=0 0.029, z=1 0.037, z=2 0.066, z=3 0.102, z=4 0.144, z=5 0.257
(all links 0.072). Larger merged systems were *less* enriched than small fragments (consistent with catalogue segmentation).

## Candidate rule T-v2 (frozen before seeds 110-119)
T-v1 links filtered to z >= 3 (primary); z >= 2 and z >= 4 reported as neighbours. Same dots, spacing and redundancy rule.

## Confirmatory gate for T-v2 (all must hold on seeds 110-119; otherwise the z >= 3 filter is not used)
1. Pooled set efficiency (empty base) of z >= 3 is >= 0.15 **and** >= 1.25 x the efficiency of all forward links.
2. It exceeds the 95th percentile of 20 random same-size subsets of the forward links (pooled): the filter carries information.
3. In >= 3 of 4 folds its efficiency exceeds that fold's all-links efficiency.
4. Paired DTI gain vs the leaky dotted-H19-5 base is > +0.001 on average and no cell loses more than 0.01.

Same standing caveats as above: catalogue-internal truth, correlated replicates, no significance claim.


## Provenance limit of this pre-registration (stated plainly)
Both registration texts (the original and Addendum A) were written *before* the corresponding runs in the working session, but the repository's first commit was made after the runs, so
**git history cannot independently prove that ordering**; there is no external timestamp. The ordering is attested only by the session record and by the structure of the evidence (distinct,
non-overlapping seed ranges: exploratory 0-2, confirmatory 100-109, filter selection from 100-109 only, confirmation 110-119). Treat the gates as disciplined, not notarised.

---

# Addendum B - Vector-attributed fault graph, three-tier holdout, and H27-5 kinematic attribute gate (written before seeds 120-129)

## Motivation (Next Step #4 from `knowledge/06_limitations_and_access.md`)
In the previous session, only per-trace centroids (`gdr_qfaults_traces.csv`) were used, so the fault graph was purely raster-based and could not distinguish:
1. **Multipart polyline fragmentation (`same_fid`):** a single NBMG INGENIOUS vector record (`FID`) broken into multiple 8-connected components at 100 m;
2. **Intra-zone trace continuation (`inter_fid & same_name`):** two distinct NBMG vector records (`FID_src != FID_tgt`) belonging to the same named fault zone (`NAME`/`NUM`);
3. **Inter-zone linkage (`inter_name`):** two independently named fault zones (`NAME_src != NAME_tgt`).

Restoring `qfaults_v2_in_footprint.json` from `buffedlizard55-lab/GEMSDOE24@ee5d7c65` (1,179 NBMG INGENIOUS Qfaults vector polylines in the footprint, matching `labels.tif` to 98.42% within 100 m and 99.97% within 200 m) maps every catalogue pixel and all 3,199 skeleton components to official vector attributes (`FID`, `NAME`, `NUM`, `SLIPSENSE`, `DIPDIRECT`, `FTYPE_`, `MAPSCALE`, `REC2023`, `SLIPRT2023`).

## Pre-registered protocol (frozen before running `scripts/run_vector_topology_validation.py` on seeds 120-129)
* **Three holdout tiers** on the 4 spatial quadrants (`NW`, `NE_LidarGapHeavy`, `SW`, `SE`), fresh seeds `120-129` (40 cells per tier):
  1. **Tier 1 (`component`):** hide 20% of 8-connected raster components (replicates the T-v2 protocol on seeds 120-129 as a baseline).
  2. **Tier 2 (`FID_trace`):** hide 20% of whole NBMG multipart vector records (`FID`) per quadrant (eliminates intra-`FID` multipart fragmentation from hidden truth).
  3. **Tier 3 (`NAME_zone`):** hide 20% of whole named fault zones (`NAME`) per quadrant (eliminates intra-zone continuation from hidden truth).
* **H27-5 kinematic attribute rule (frozen):**
  * Each T-v2 link (`z >= 3`, de-duplicated mutual pairs) inherits endpoint vector attributes `(FID, NAME, NUM, SLIPSENSE, DIPDIRECT, FTYPE_, MAPSCALE)` from its source and target skeleton components.
  * Define `kinematic_compat = True` iff:
    1. `SLIPSENSE` is non-conflicting (either endpoint has unspecified slip sense, or `SLIPSENSE_src == SLIPSENSE_tgt`), AND
    2. `DIPDIRECT` is non-conflicting on non-matching slip sense (synthetic or antithetic relay geometry is allowed within the same slip sense; opposite dip directions across conflicting slip senses are rejected).
  * Subsets evaluated on Tier 2 (`FID_trace`): all forward links, `T-v2 (z>=3 dedup)`, `T-v2 inter-FID (FID_src != FID_tgt)`, `T-v2 inter-FID + kinematic_compat (H27-5a)`, and `T-v2 inter-FID + same_name + kinematic_compat (H27-5b)`.

## Confirmatory gate for Tier 2 (`FID_trace`) and H27-5 (seeds 120-129)
1. **Whole-trace survival gate (T-v2 on `FID_trace`):** pooled efficiency of `T-v2 (z>=3 dedup)` on `FID_trace` exceeds the break-even threshold $m(0.30) = 0.0638$ AND is $\ge 2.0\times$ the rotated-cone control efficiency on `FID_trace`.
2. **H27-5 kinematic typing gate:** on `FID_trace`, `inter-FID + kinematic_compat` achieves higher pooled efficiency than untyped `T-v2 (z>=3 dedup)` AND `inter-FID + same_name + kinematic_compat` achieves pooled efficiency $\ge 0.10$.

---

# Addendum C - Honest label-blind spatial-CV surface ($B_{\text{oof}}$) and gates for H27-1, H27-3, H27-4 (written before seeds 130-139)

## Motivation (Next Step #3 from `knowledge/06_limitations_and_access.md`)
In the previous session, H27-3 (emission-graph coherence filter) and H27-4 (tip-shadow pruning within 300 m of known catalogue pixels) were left untested because the dotted H19-5 base was trained on all labels (leaky on the holdout). Using the 32-band label-free prepared feature matrix (`data_cache/prepared/features.npy`, excluding the mislabelled `tc` band), we construct a strictly out-of-fold (OOF) spatial-CV detector across the 4 quadrants.

## Pre-registered protocol (frozen before running `scripts/run_oof_hypothesis_gates.py` on seeds 130-139)
* **Out-of-fold detector ($B_{\text{oof}}$):**
  * For each quadrant $f \in \{0, 1, 2, 3\}$, train `HistGradientBoostingClassifier(max_iter=100, max_leaf_nodes=31, learning_rate=0.08, l2_regularization=5.0, random_state=2026+f)` on pixels strictly outside quadrant $f$ with a 600 m (6 px) buffer from quadrant $f$ (so no 300 m kernel or spatial feature crosses the boundary), using all positive catalogue pixels and a 10:1 random negative subsample.
  * Predict probability $P_{\text{oof}}$ on quadrant $f$, smooth with $\sigma = 1.0\text{ px}$ Gaussian, extract 1-px ridges via directional non-maximum suppression (`ridge_nms`), mask out the fold/seed's known catalogue pixels (`~known`), select the top ridge pixels matching the 0.2477 pre-thinning density (or top positive ridges), and apply `dot_thin(d=1.5)` to match the 0.2477 emission geometry (~1.16% footprint dot density).
* **Evaluated hypotheses on fresh seeds `130-139` (40 cells):**
  1. **H27-1 / T-v2 on $B_{\text{oof}}$:** add non-redundant `T-v2 (z>=3 dedup)` dots to $B_{\text{oof}}$. Gate passes iff mean paired $\Delta\text{DTI} > +0.001$ and $\ge 3/4$ folds improve.
  2. **H27-4 (Tip-shadow pruning) on $B_{\text{oof}}$:** drop $B_{\text{oof}}$ dots within distance $r \in \{1, 2, 3\}\text{ px}$ ($100, 200, 300\text{ m}$) of known catalogue pixels. Gate passes iff the dropped dots have pooled efficiency $< m(\text{DTI}_{\text{oof}})$ AND mean paired $\Delta\text{DTI} > +0.0005$ in $\ge 3/4$ folds.
  3. **H27-3 (Emission-graph coherence filter) on $B_{\text{oof}}$:** drop isolated 1-dot fragments of $B_{\text{oof}}$ that have no other emitted dot within 600 m (6 px, i.e., single-dot connected components under radius-6 dilation). Gate passes iff the dropped isolated dots have pooled efficiency $< m(\text{DTI}_{\text{oof}})$ AND mean paired $\Delta\text{DTI} > +0.0005$ in $\ge 3/4$ folds.

## Provenance note for Addenda B and C
Unlike the initial session's registration, Addenda B and C are committed to git **before** running `scripts/run_vector_topology_validation.py` (seeds 120-129) and `scripts/run_oof_hypothesis_gates.py` (seeds 130-139), so the commit graph attests the pre-registration order.



---

# Addendum D - Session 4: new-information detector arms, graph-connectivity link ranking, and overlapping step-overs (written and committed BEFORE seeds 140-149 were run)

## Motivation (Next Steps #2, #3 and #4 from `knowledge/06_limitations_and_access.md`)
Session 3 proved arithmetically (`knowledge/07_live_score_inversion.md` section 8) that 0.3195 is out of reach by rearranging pixels: it needs either retention ~= 1.0 at ~44k px or **concentration above 5.7x blind**, and the whole H19-5/h19-4/h16-1 family plateaus at 5.3-5.7x. Both surviving routes are detector problems that need *new information*. Session 4 therefore registers only arms that add information or add structure the repo does not have, and it registers the two live-inverted refutations first so that no future session re-proposes them.

## D-0 (already measured, no labels involved): the SGMC-gap live probe is registered and inverted
`registry/live_scores.json` gained a 21st hash-authenticated (raster, score) pair: 16GEMSDOE **H18-4** `aef8f42c` (sha256 `736f62c2da58...`), owner-reported **0.0360**, constructed as "USGS State Geologic Map Compilation (NV+CA) faults >300 m from every catalogue fault, thinned to 1-px lines; no model, no training". It is the only scored emission in the group's history whose pixels are all >= 300 m from the catalogue, so its score is a direct live measurement of the far-field/lithological habitat. `scripts/invert_sgmc_probe.py` (a) re-verifies the construction claim from the raster bytes, (b) checks that the same instrument reproduces Session 3's published anchors within 2 %, and (c) inverts the probe. **No gate is attached to D-0**: it is a measurement, and it is recorded as a refutation of "independent bedrock catalogue as an emission" (see `evidence/sgmc_gap_inversion.json`). Any arm that emits on SGMC/geologic-map-gap structure is now barred without new evidence.

## D-1 H27-13: multi-scale directional lineament context (the FaultSEG direction, CPU-feasible)
* **Claim:** a pixelwise tabular detector cannot integrate evidence along a 1-5 km linear feature, which is exactly what separates a fault scarp from nonlinear geomorphology (paleo-shorelines, canyon rims, stream boundaries) in Hermant, Kiersnowski & Bellanger (2025). Adding *oriented line-integral* features should raise detector quality at no cost in emission geometry.
* **Frozen feature construction** (`src/gems27/newinfo.py: directional_lineament_bands`): for each label-free input layer in {`lidar_lappos_max`, `lidar_step_max`, `lidar_ex_max`, `det_local_relief`} and each along-strike half-length L in {5, 10, 20} px (0.5, 1, 2 km), compute a Gaussian-weighted oriented line mean at 4 orientations {0, 45, 90, 135} deg with across-strike sigma = 1 px, then keep (i) the maximum over orientation and (ii) the anisotropy ratio (max - mean)/max. 4 layers x 3 scales x 2 statistics = **24 bands**, all label-free, all computed with a 6-px-safe margin so nothing crosses a fold boundary.
* **Arm:** `B_oof+dir` = the Addendum-C detector retrained on the 32-band matrix **plus** these 24 bands (identical HGB hyper-parameters, identical 600 m buffer, identical 10:1 negative subsample, identical `ridge_nms`, identical budget fraction and `dot_thin(1.5)`).
* **Gate D1 (both must hold, else the arm is dropped):**
  1. out-of-fold PR-AUC (`average_precision` against catalogue pixels, computed strictly on out-of-fold predictions) improves by **>= +0.005 absolute** over the 32-band base;
  2. on fresh seeds **140-149** (40 cells) the arm's mean paired DTI gain over `base_oof` is **> 0** in **>= 3 of 4 folds** and **> +0.001** on average, at the matched budget.

## D-2 H27-12: the three restored official layers that no detector in the programme has ever used
`derived_sgmc_faults_100m_u8.tif`, `geodawn_rad_u8.tif` (K, Th, U, TC), `geodawn_extensions_u8.tif` (Th/K, U/K, U/Th, TMI_up150), `gdr_wellspring_in_footprint.csv` (27,092 rows; 1,873 `Hot`, 2,245 `Warm`, with quartz/chalcedony/cat's-eye geothermometer temperatures) and `gdr_volcanic_vents_in_footprint.csv` (21 vents) are used only by the refuted habitat tomography (`src/gems27/tomography.py`) and by the Session-1 single-channel AUC screen. **As features they have never been in any detector here.** (They are *not* claimed as new to the whole group: the sibling's H19-5 blend already contains a "backward thermal/geochemical conduit inversion" expert and `hydro_uk_anom`/`hydro_rad_edge`/`hydro_clay_conduit` channels appear in its leaderboard-attribution table, so this arm is registered as *new to this repo* and its value must be measured, not assumed.)
* **Frozen bands:** `+rad` = 8 bands (K, Th, U, TC, ThK, UK, UTh, TMI_up150 as float32, 0 = nodata); `+sgmc` = 3 bands (distance to SGMC clipped at 20 px, on-SGMC indicator, SGMC-within-1-km indicator); `+thermal` = 5 bands (distance to any well/spring, to `Hot`+`Hot ` rows only, to rows with a quartz geothermometer >= 150 C, to vents, and log10(1+d) of the hot-spring field); `+all` = the union (16 bands).
* **Gate D2:** identical to Gate D1, applied to each ablation separately. All results are reported, including failures. An ablation that fails PR-AUC but wins paired DTI (or the reverse) is reported as **inconclusive** and is not shipped.

## D-3 H27-14: rank the 345 shipped T-v2 links by graph-connectivity value, not by local z-score
* **Claim (Berkowitz, Bour, Davy & Odling 2000):** near the connectivity threshold a link that merges two *large* clusters moves the network's connectivity parameter P further than one that merges two small ones, so links are not equal. `knowledge/04` section 3 puts this catalogue at P ~= 5.8 against Pc = 5.6-6.0, i.e. at the threshold.
* **Frozen per-link values** (`src/gems27/graph_value.py`), computed on the catalogue graph plus the 345 shipped links:
  * `bridge` = 1 iff the link is a graph bridge of the merged candidate graph (removing it re-splits the component);
  * `merge_len_km` = len(A) + len(B) + gap;
  * `delta_largest_share` = change in (largest-system length / total fault length) when the link is added;
  * `delta_P` = change in the Berkowitz connectivity parameter P = beta L^D using the closed form already verified against the paper in `src/gems27/topology_theory.py` and `tests/test_topology_theory.py`.
* **Gate D3 (measurable, and pre-registered in the direction that Session 2's post-hoc finding predicts will FAIL):** on the component holdout, seeds **140-149**, compare pooled efficiency of (a) the shipped `z>=3 dedup` 345 links, (b) the top 173 by |`delta_P`| within those 345, (c) the bottom 173, and (d) 20 random same-size subsets of (a). The arm passes only if (b) >= 1.15 x (a) **and** (b) exceeds the 95th percentile of (d). If it fails, the ranking is still written into every candidate dossier as *documentation* (which is what the task prompt asks for) but the emission is **not** changed.
* **Documentation deliverable, unconditional on the gate:** each of the 345 dossiers in `registry/topology_candidates.json`, `docs/data/topology_links.csv`/`.geojson` and `docs/topology.html` gains `bridge`, `merge_len_km`, `delta_largest_share`, `delta_P`, `connectivity_rank` and a one-paragraph graph argument naming the two independently-mapped faults (NBMG `FID`, `NAME`), the system length they would form, and the kinematic compatibility already recorded.

## D-4 H27-2 (the never-generated variant): overlapping en-echelon step-over links
* **Claim:** relay/step-over settings host ~32 % of characterised Great Basin geothermal systems (Faulds & Hinz 2015), and the geometry that identifies a relay is *along-strike overlap* of two parallel strands separated laterally by 0.3-3 km - not tip-to-tip alignment. The repo's forward-cone rule cannot generate overlapping offsets at all (`knowledge/02` H27-2: "Overlapping offsets were never generated"), and only 15 of the 345 shipped links are oblique.
* **Frozen rule** (`src/gems27/newinfo.py: steppover_links`): for every pair of distinct components whose principal-axis strikes agree within 20 deg, whose perpendicular lateral offset is in [3, 30] px (0.3-3 km) and whose projections onto the mean strike **overlap by >= 2 px (200 m)**, emit a straight breaching segment between the two closest overlapping points; keep it if its length is in [3, 30] px and its dots are not already within 3 px of the base emission.
* **Gate D4:** on the component holdout, seeds **140-149**, pooled efficiency of the step-over set must exceed the rotated/offset control by **>= 2.0x** and exceed the break-even $m(0.30) = 0.0638$; and adding its non-redundant dots to `base_oof` must give a mean paired DTI gain **> +0.001** in **>= 3 of 4 folds**. Otherwise the class is recorded as refuted and not shipped.

## Standing caveats (unchanged, and they bind every gate above)
1. Hidden truth in these gates is **catalogue-internal** (held-out pieces of the INGENIOUS/USGS compilation). It cannot measure whether an arm finds *new* expert-mapped faults; a pass is a reason to consider an arm, never a claim about the leaderboard.
2. Replicates within a seed range are correlated; no p-values or significance claims are made.
3. Scores are owner-reported, never DrivenData receipts. Nothing here uploads anything.
4. Any file built from a passing arm is labelled **UNSCORED**, carries a unique content-hashed name and a note <= 200 characters, and is verified by `scripts/verify_downloads.py` before it is offered for download.
5. `drivendata.org` is never accessed by script or agent (Terms of Use); the leaderboard context in `registry/live_scores.json` is a secondary quote of an owner-directed read.

## Addendum D band-construction deviation, disclosed BEFORE the gate was run
`det_local_relief` in `data_cache/prepared/features.npy` is **signed** (min -207.686, max +299.416, mean -0.026, 64.7 % negative, 3,061 NaN = 0.06 %) and the pre-registered anisotropy statistic `(max - mean)/max` is unbounded for signed inputs: measured values reached 6.6e7 (`dir_det_local_relief_aniso_L5`), which would swamp a gradient-boosted tree's binning. For that one layer the anisotropy is therefore the bounded, scale-free `(max - mean)/(max - min)` in [0, 1]. The three LiDAR input layers (`lappos_max`, `step_max`, `ex_max`, all non-negative after nodata -> 0) keep the pre-registered `(max - mean)/max`, measured in [0, 0.8]. Band names, count (24), scales (5/10/20 px), orientations (4) and across-strike sigma (0.8 px) are unchanged. No threshold or gate was chosen using holdout results; this is a numerical-definition fix, disclosed rather than silently applied.

---

# Addendum E - Session 4: the far-field swap probe (Slot 5), registered BEFORE it was built and before any score exists for it

## Why a probe rather than another gate
`scripts/diagnose_arm_habitats.py` decomposed the Addendum-D result on the same 40 cells and found the proxy's resolution limit: **100 % of the hidden truth (120,983 px) lies at distance 0 from the published catalogue**, because hidden truth *is* catalogue pixels. Consequently **99.6 % of every arm's credit is earned within 200 m of the published catalogue spine** (base arm: 36.8 % on the spine itself, 51.5 % at 100 m, 11.4 % at 200 m, 0.37 % at 300 m-1 km, **0.0 % beyond 1 km**) while the live-scored 0.2477 emission puts **81.4 % of its dots >= 300 m from the catalogue** (median 1.5 km) and earns 5.67x blind. The catalogue-internal holdout therefore cannot see the habitat that carries the real credit: it is not biased against far-field arms, it is **blind** to them. No further gate on this proxy can decide whether a better detector helps.

The one live measurement that does speak to the far field is the h18-4 SGMC-gap probe (0.0360 -> 1.62x blind). So the decisive question for the rest of the programme is a *live* one, and it can be asked with a single bounded slot.

## Frozen construction of Slot 5 (`slot5-farfield-swap-augmented-detector`)
1. Fit the augmented detector (32 prepared bands + the 40 Addendum-D bands = 72 label-free features, including the SGMC distance/indicator bands) on **all** published labels - there is no held-out truth at submission time, so out-of-fold fitting would only weaken it. Identical `HistGradientBoostingClassifier(max_iter=100, max_leaf_nodes=31, learning_rate=0.08, l2_regularization=5.0)`, identical 10:1 negative subsample, `random_state=2026`.
2. Take the owner-reported 0.2477 file (`dotted_h19_5_d1_5_nan.tif`, sha256 `68d0e2e4...`, 60,069 px) and split it into near-field (`d_cat < 3 px`, 18.6 %) and far-field (`d_cat >= 3 px`, 81.4 %).
3. **Remove** the K = 20 % of far-field dots with the LOWEST augmented-detector probability and **add** the K highest-probability far-field ridge dots of that detector that are not already in the file, are >= 3 px from the catalogue, are inside the footprint and are >= 1.5 px from every kept dot (so the d1.5 emission geometry is preserved).
4. Nothing else changes: the near-field dots, the total pixel count (60,069), the nodata convention, the CRS and the grid are identical to the 0.2477 file. A live comparison against 0.2477 therefore differs in exactly **one** variable: *which* far-field pixels are emitted.

## Registered interpretation rule (fixed before any upload; the agent never uploads)
* live(Slot 5) >= 0.2477 + 0.003  ->  the augmented detector carries **real far-field information**; adopt it and rebuild the whole emission from it.
* |live(Slot 5) - 0.2477| < 0.003  ->  **no measurable far-field information**; the Addendum-D PR-AUC/DTI gains are catalogue-proximity artefacts and must not be promoted.
* live(Slot 5) <= 0.2477 - 0.003  ->  **refuted**: re-ranking the proven emission's far field with this detector destroys credit.
The 0.003 band is set from the smallest live difference this programme has ever resolved (0.2477 vs 0.1922 = 0.0555; the h18-4 probe 0.0360) and from the forward model's own sensitivity: replacing 9,778 of 60,069 dots at 5.67x blind concentration with blind dots moves the modelled score by about -0.006, so 0.003 is inside the range the experiment can actually resolve.

## Declared downside (owned, not hidden)
If the augmented detector has no far-field information, this probe **randomises 16.3 % of the best file's dots** and should lose roughly 0.003-0.008 of live score. That is the price of the only measurement that can settle whether detector work can pay at all. Slot 5 is therefore labelled `MEASUREMENT PROBE - NOT THE RECOMMENDED SUBMISSION` everywhere it appears, and **Slot 1 remains the one-click recommendation**. The group has 3 slots per week and about 9 weeks to the 2026-12-03 deadline; spending one on this is judged worth more than a fifth unscored rearrangement of the same pixels, which Session 3 proved cannot exceed ~0.2550 by geometry alone.

---

# Addendum F - Session 5: H27-10 model-ranked 100-300 m offset-scarp annulus (frozen before implementation and seeds 150-159)

## Motivation and corrected source scope
The 100-300 m ring is a falsifiable engineering choice, not a distribution established by the literature. The official Hermant, Kiersnowski & Bellanger (2025) Stanford workshop PDF (full text retrieved through the page-fetch service on 2026-10-02) says in Figure 2 that a *local* distance between USGS Quaternary traces and TLS fault labels can be up to 400 m. It does not establish a general 150-400 m offset distribution, a 150 m lower bound, or the 100-300 m ring used here. The older registry wording overstated that source and is corrected in `registry/sources.json` and `registry/irregularities.json`.

The prior habitat-tomography estimate is excluded: it failed leave-one-submission-out validation (signal ratio 0.96) and MUST NOT be used to locate a candidate. H27-4's measured 100 m removed-band efficiency of 0.0034 versus the owner-reported 0.2477 live break-even m=0.0521 motivates testing the adjacent band, but does not establish that the adjacent band is productive. No SLIPSENSE/DIPDIRECT side-selection is made: without a local stress model and a frozen mechanical rule, assigning an expected branch side would be speculative.

## Frozen candidate and comparison
* **Target annulus:** pixel-centre Euclidean distance from the *known catalogue pixels in the current holdout fold*, `1.0 < d_known <= 3.0` pixels on the 100 m grid (100-300 m). The hidden component pixels are not used to form this mask.
* **Frozen ranker:** strictly four-quadrant OOF probabilities from the current-best H28-1 detector (32 prepared features plus the six hash-validated H28-1 magnetic/gravity edge features; detector seed 2026), followed by the same `ridge_nms(sigma=1.0)`. No parameter is fitted on seeds 150-159.
* **Baseline, per cell:** `H28_edge_best_Tv2_prune_r1` — H28-1 OOF dotted base (`PRE_THIN_FRAC`, `thin_d=1.5`), H27-4 prune `d_known > 1.0`, plus the existing deterministic T-v2 z>=3 deduplicated link dots at the registered `metric.RADIUS_PX` spacing. This is the current strongest in-repository paired OOF variant; it is not a leaderboard score.
* **Equal-count substitution, per cell:** Let K be the count of H28-1 base dots that H27-4 r1 removes at `d_known <= 1.0`. Remove the K lowest-probability H28-1 base dots in the baseline with `d_known > 3.0`; replace them with the K highest-probability eligible H28-1 OOF ridge pixels in the 100-300 m annulus. Candidates must be in the active fold, not already emitted, and at least 1.5 px from every retained or newly selected dot (Euclidean). T-v2 links are unchanged. If either the source or candidate pool cannot supply exactly K pixels, the cell is invalid and the data gate fails; do not lower K or alter the annulus after seeing results.
* **No submission is constructed.** The test writes only a machine-readable evidence JSON. It does not modify the four weekly candidates or the separate H28-1 full-map research TIFF.

## Frozen holdout protocol
* Fresh split seeds **150-159 only**, 10 random 20% component-hidden draws in each of the four existing quadrants (`NW`, `NE_LidarGapHeavy`, `SW`, `SE`), 40 paired cells. Seeds 140-149 belong to H28-1 and are not reused.
* Score the equal-count annulus substitution against the frozen baseline with the existing DTI kernel. Report paired mean, per-fold and per-seed gains, gross addition/removal efficiencies, emitted-dot counts, and all data checks. Holdout truth remains catalogue pixels; the 600 m quadrant buffer blocks model-training leakage but not shared geomorphic/covariate structure.

## Confirmatory gate (all conditions required; otherwise reject this annulus variant and spend no weekly slot)
1. Mean paired DTI gain versus `H28_edge_best_Tv2_prune_r1` is **>= +0.001** across all 40 cells.
2. At least **3 of 4** quadrant-fold means improve and at least **8 of 10** seed means improve.
3. Pooled gross efficiency of the added annulus pixels is **>= m(0.2477)=0.0521** and exceeds the pooled efficiency of the removed >300 m pixels.
4. Exactly the preregistered seed list `150-159` and 40 cells are present.
5. All source/target swaps are exactly K; baseline and candidate dot counts match cell by cell; no prediction overlaps known labels; all scores and features are finite and in range; all annulus additions satisfy `1<d<=3` and the >=1.5 px spacing rule; prepared-feature and H28-1 edge-cache hashes/metadata match.

Even a pass is only a catalogue-internal candidate-class result, not evidence of transfer to the organizer-created labels or a score increase. A pass may justify a geologist-reviewed, content-hashed research candidate, but it does **not** authorize a weekly slot; the prior live habitat evidence still makes a real live comparison necessary. No thresholds, annulus bounds, or ranking rules may be changed after unblinding these seeds.

## Post-run implementation-audit disclosure (not a protocol change)
The first execution on seeds 150-159 produced mean paired ΔDTI +0.00084615, improved 3/4 folds and 7/10 seeds, and pooled annulus efficiency 0.03357 (<0.05219); these results already fail multiple frozen criteria. Review found the diagnostic spacing check measured each selected pixel's distance to the selected set *including itself*, so it necessarily returned zero and falsely marked the spacing data check as failed. The ranking/selection algorithm, masks, scores, threshold and holdout outcome were not changed. The first-run JSON is preserved as `evidence/h27_10_annulus_holdout_initial.json`; a same-seed deterministic integrity rerun after correcting only that diagnostic is not a second confirmation and will not be used to tune or reconsider the failed gate.
