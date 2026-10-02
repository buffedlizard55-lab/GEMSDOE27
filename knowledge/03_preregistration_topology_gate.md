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


