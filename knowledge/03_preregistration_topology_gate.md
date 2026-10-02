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
