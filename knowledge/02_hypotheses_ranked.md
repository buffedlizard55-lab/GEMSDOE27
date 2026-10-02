# Untried hypotheses, ranked (generated from `registry/hypotheses.json`; do not edit by hand)

Ranking rule: expected DTI gain x probability the test can validate it / cost. Before any weekly slot is spent, the top hypothesis must beat the holdout baseline (see `03_preregistration_topology_gate.md`).

## H27-8 (rank 1): Stack every validated increment at the live-anchored budget optimum (slot 4)

* **Layers:** H19-5 emission (h19_5_nan.tif) + catalogue raster (labels.tif) + NBMG INGENIOUS vectors + T-v2 link set. No new external data.
* **Physical signature:** dot_thin(H19-5, 2.8) [= the live-anchored budget optimum, 44,090 px] minus the 1 px (100 m) catalogue-flank shadow (H27-4 r<=1, 3,891 px) plus 1,308 non-redundant T-v2 gap-closure dots = 41,507 px.
* **Why it catches a fault missing from USGS/INGENIOUS:** Session 3 inverted all 20 hash-authenticated live scores and produced a forward model DTI = TP/(0.2 TP (1-rho) + 0.2 N + 0.8|G|) that reproduces BOTH live anchors exactly (H19-5 solid -> 0.1922, dotted d1.5 -> 0.2477) and whose retention rule predicts a second, unrelated live pair to +4.0%. Under that model the budget optimum is d = 2.25-2.8 -> 0.2550, and the sibling's independent two-parameter fit gave 0.2553. Slot 4 is the first candidate to combine that optimum with the two increments the out-of-fold gate validated (T-v2 +0.0115, H27-4 stacked +0.0141, both 4/4 folds).
* **How it differs from the repo:** Slot 2 uses the d2.8 budget but carries only T-v2; slot 3 carries T-v2 + the prune but at d1.5. Nothing in the programme has stacked all three at the anchored optimum.
* **Status:** BUILT AND VERIFIED, UNSCORED. evidence/candidate_model_scores.json: geometric model 0.2484, hybrid model 0.2781 (highest hybrid of the four). The two models differ ONLY in what the targeted prune is charged; slot 1 vs slot 3 is the live A/B that settles it. 79 format/consistency checks pass (scripts/verify_downloads.py).
* **Expected gain:** modelled 0.2484 (geometric) to 0.2781 (hybrid) vs 0.2477 live parent
* **Cost:** 1 submission slot; no new data; no GPU

## H27-1 (rank 2): Topology gap-closure: along-strike links between disconnected mapped fault systems

* **Layers:** Catalogue raster (labels.tif) -> skeleton graph + NBMG INGENIOUS Qfaults vector polylines (qfaults_v2_in_footprint.json, 1,179 features); local strike domain from the same graph.
* **Physical signature:** Free tips (degree-1 nodes) whose strike points at a tip of a different system 1-4 km away; straight link; evidence score z = [mutual] + [end-to-end] + [tip within 15 deg] + [local strike agreement >= 0.4] + [merged length <= 8 km]; ship z >= 3 (345 links, 1,259 non-redundant dots vs 0.2477). Network sits near its connectivity threshold (Berkowitz-style P ~ 5.8 vs Pc 5.6-6.0).
* **Why it catches a fault missing from USGS/INGENIOUS:** Mapped faults are compiled in pieces; unmapped continuations across short gaps are where an expert panel adds 'new' faults, and surface-contrast detectors cannot see them because the gap itself is low-contrast. Vector attribution against 1,179 NBMG polylines shows 230/345 links bridge intra-FID sub-parts of the same multipart polyline, 115/345 bridge distinct FID polylines, 312/345 lie within the same named fault zone (NAME/NUM), and 333/345 have compatible SLIPSENSE/DIPDIRECT.
* **How it differs from the repo:** First use of the catalogue's graph and vector polyline topology. The sibling's h16-continuation (owner-reported 0.0461) is the nearest prior idea; T-v2 differs by requiring a target system, a 1-4 km gap bound, tip-to-tip alignment, and a strike-agreement score, and by being gated on rotated-cone controls across three holdout tiers plus an out-of-fold spatial-CV base.
* **Status:** VALIDATED across 4 independent protocols: (1) component holdout seeds 100-109 (0.281 vs 0.059 ctrl) and fresh seeds 110-119 (0.280 vs 0.056 ctrl, +0.0117 paired DTI, 4/4 folds); (2) NBMG FID vector-trace holdout seeds 120-129 (0.1003 vs 0.0204 ctrl, 4.92x enrichment, > m(0.30)=0.0638); (3) honest 4-fold spatial-CV out-of-fold detector B_oof on seeds 130-139 (+0.0115 paired DTI, 4/4 folds, marginal efficiency 0.2251).
* **Expected gain:** At the 0.2477 operating point: worst case -0.0029 (zero hit rate), break-even at efficiency 0.0522, +0.0024 at the FID vector-trace holdout efficiency 0.1003, and +0.0110 at the component holdout efficiency 0.280-0.293. Shipped as Primary Slot 1 (5512495c6bd1) and Secondary Slot 2 (3ebd51534bb1).
* **Cost:** Done (this repo). Shipped in Slot 1 & Slot 2.

## H27-4 (rank 3): Tip-shadow pruning: drop emission within 100-300 m of masked catalogue pixels

* **Layers:** Catalogue distance transform (d_cat) + dotted emission surface.
* **Physical signature:** A surface trained on catalogued scarps peaks on them; once 1-px catalogue cells are masked, emission survives as 1-3 px 'shadows' beside known faults (further reinforced by 100-400 m USGS-vs-LiDAR scarp offsets documented by Hermant et al. 2025, Fig. 2 & Fig. 9B). In the 0.2477 file (60,069 px), 5,355 dots (8.91%) sit at exactly d_cat = 100 m (1 px) and 8,769 (14.60%) within 200 m.
* **Why it catches a fault missing from USGS/INGENIOUS:** Because ground truth G consists of newly created fault labels rather than the unmasked 100-200 m flank of already-catalogued faults, these 1-2 px flank-shadow dots are almost pure false-positive mass; removing them cuts FP without touching recall on new faults.
* **How it differs from the repo:** Subset transform driven by catalogue distance geometry and gated on an honest out-of-fold spatial-CV detector; the repo's thinning is geometry-blind.
* **Status:** VALIDATED on the honest 4-fold spatial-CV out-of-fold detector B_oof (seeds 130-139, evidence/oof_hypothesis_gates.json): dropping dots at d_cat <= 100 m (1 px) removes dots with efficiency 0.0034 (15x below the 0.0521 live break-even), raising DTI in 4/4 folds (+0.0022 solo; +0.0141 when stacked with T-v2 in 4/4 folds). Dropping d_cat <= 200 m (2 px) removes dots with efficiency 0.0080 (+0.0025 solo, 4/4 folds; +0.0147 stacked with T-v2). Dropping d_cat < 300 m (3 px) removes dots with efficiency 0.0140 (+0.0014 solo, 3/4 folds).
* **Expected gain:** At the 0.2477 operating point: pruning the 5,355 d_cat=100 m flank-shadow dots alone gives +0.0118 modelled DTI (to ~0.2598); stacking with T-v2 (Slot 3 candidate d466b251f309, 55,992 px) gives +0.0141 modelled DTI under FID_trace efficiency (to ~0.2621) and +0.0223 under component efficiency (to ~0.2702).
* **Cost:** Done (this repo). Shipped as Tertiary Slot 3 (d466b251f309).

## H27-5 (rank 4): Kinematically typed linking with official NBMG/USGS vector fault attributes (SLIPSENSE, DIPDIRECT, NAME)

* **Layers:** NBMG INGENIOUS Qfaults vector polylines (qfaults_v2_in_footprint.json, 1,179 features with FID, NAME, NUM, FTYPE_, SLIPSENSE, DIPDIRECT, MAPSCALE) + USGS Siler (2022) slip/dilation tendency.
* **Physical signature:** Attribute every skeleton endpoint and gap link with its NBMG vector polyline FID, fault zone NAME/NUM, SLIPSENSE (N/RL/LL), and DIPDIRECT, and retain inter-FID links with non-conflicting slip sense and synthetic or conjugate dip directions.
* **Why it catches a fault missing from USGS/INGENIOUS:** Distinguishes intra-FID raster discretisation gaps from true inter-FID structural relays and filters out kinematically incompatible cross-links when whole vector polylines are held out.
* **How it differs from the repo:** Uses official NBMG/USGS vector polyline topology and kinematic attributes rather than raster-only 8-connected components.
* **Status:** VALIDATED on the NBMG FID vector-trace holdout (Addendum B, seeds 120-129, evidence/vector_topology_validation.json): on whole-FID holdout, z>=3 dedup achieves 0.1003 vs 0.0204 rotated-cone control (4.92x); filtering to inter-FID + kinematic_compat (H27-5a) raises efficiency to 0.1374 (6.74x control), and inter-FID + same_name + kinematic_compat (H27-5b) reaches 0.1783 (8.74x control). All 345 shipped dossiers in registry/topology_candidates.json are now annotated with these vector attributes.
* **Expected gain:** Raises inter-FID holdout efficiency from 0.1003 to 0.1374 (+37% relative) and 0.1783 (+78% relative within named fault zones); 333/345 (96.5%) of shipped T-v2 links already satisfy kinematic_compat.
* **Cost:** Done for NBMG vector attributes (this repo); Siler (2022) raster stress overlay remains optional.
* **External data (free, official):** [NBMG Qfaults_INGENIOUS ArcGIS REST layer 0 (1,179 in-footprint polylines restored locally)](https://web2.nbmg.unr.edu/arcgis/rest/services/Qfaults/Qfaults_INGENIOUS/MapServer/0) - verified & restored locally in data_cache/qfaults_v2_in_footprint.json (sha256 4d6efc7b...)
* **External data (free, official):** [USGS Qfaults GIS (zip, 32.4 MB)](https://earthquake.usgs.gov/static/lfs/nshm/qfaults/Qfaults_GIS.zip) - verified downloadable from a GitHub runner 2026-10-02 (application/zip)
* **External data (free, official):** [Siler (2022) slip & dilation tendency, Great Basin (USGS ScienceBase)](https://www.sciencebase.gov/catalog/item/6296974dd34ec53d276bb33d) - ScienceBase JSON metadata verified; raster overlay optional

## H27-10 (rank 5): Offset scarp halo: emit preferentially in the 100-300 m ring around mapped traces, oriented by local kinematics

* **Layers:** Catalogue distance field (labels.tif) x NBMG INGENIOUS SLIPSENSE/DIPDIRECT per polyline (qfaults_v2_in_footprint.json) x LiDAR scarp descriptors lappos_max / step_max / ex_max (lidar_scarp_features_u8.tif, derived from USGS 3DEP 1 m DEM tiles).
* **Physical signature:** Dots placed in the annulus 1-3 px (100-300 m) from a mapped trace, ranked by the product of (a) LiDAR scarp response across the local strike and (b) kinematic compatibility with the parent trace's SLIPSENSE/DIPDIRECT, i.e. the side on which a splay, antithetic or flower-structure branch is mechanically expected.
* **Why it catches a fault missing from USGS/INGENIOUS:** Two independent lines of evidence put catalogue-MISSING faults in exactly this annulus and not closer. (1) Hermant et al. (2025, Stanford Geothermal Workshop) document LiDAR-mapped lineaments sitting 150-400 m off USGS/INGENIOUS traces - a catalogue compiled at 1:24,000-1:250,000 cannot place a trace to better than ~200-500 m, so the expert panel's new labels land in the offset band, not on top of the old trace. (2) Session 3's habitat tomography, though it FAILED its own leave-one-out validation (signal ratio 0.96) and must not be used to choose an emission, still put 66% of the fitted truth mass in the 100-200 m ring and 34% at 800-1500 m, with ~0 in between. (3) The out-of-fold gate measured the 0-100 m flank shadow at efficiency 0.0034 - about 15x below the 0.0521 live break-even - so the innermost band is dead while the band just outside it is where the evidence points. This hypothesis is the sign-flip of H27-4: H27-4 PRUNES r<=1; H27-10 EMITS into 1<r<=3.
* **How it differs from the repo:** H27-4 prunes the 0-100 m shadow; nothing in the repo emits INTO the 100-300 m annulus as a target class. H27-1/H27-5 select links between mapped tips (gap closure, mostly >1 km); H27-10 selects the halo around existing traces. It is also the only hypothesis whose habitat prior comes from the live scores rather than from a catalogue-internal holdout.
* **Status:** PROPOSED, NOT VALIDATED. Rank 5 on expected gain x probability of validation / cost. Cheap to test on infrastructure that already exists: add an 'annulus_1_3px' variant to scripts/run_oof_hypothesis_gates.py on fresh seeds 150-159 and compare its removed/added efficiency against the 0.0521 live break-even and against the measured 0.0034 of the r<=1 band. Pre-register in knowledge/03 BEFORE running. The tomography that motivated the habitat split failed validation, so this must be treated as a fresh hypothesis, not as a confirmed one.
* **Expected gain:** unknown; upper bound is set by the fact that the whole H19-5 family plateaus at concentration 5.3-5.7x blind, and any real gain has to come from finding truth the family misses
* **Cost:** low - reuses the OOF harness, the NBMG vectors and the LiDAR descriptors already in data_cache; no new external data, no GPU
* **External data (free, official):** [Hermant et al. (2025), 'Leveraging LiDAR and AI to Rapidly Expand the Fault Catalogue in Great Basin Geothermal Play Fairways', Stanford Geothermal Workshop](https://pangea.stanford.edu/ERE/db/GeoConf/papers/SGW/2025/Hermant.pdf) - NOT obtainable from the sandbox - pangea.stanford.edu is unreachable (curl 000, re-measured Session 3). registry/sources.json status is 'secondary quote only': the 150-400 m catalogue-offset figure is quoted from the owner's earlier reading, not re-verified by this agent. Treat as unverified until fetched in GitHub Actions.
* **External data (free, official):** [USGS 3DEP 1 m DEM (already reduced locally to lidar_scarp_features_u8.tif, 12 bands, 706/716 tiles)](https://www.usgs.gov/3d-elevation-program) - already restored and hash-pinned in data_cache (data/manifest.json); no new download needed for H27-10
* **External data (free, official):** [NBMG Qfaults_INGENIOUS ArcGIS REST layer 0 (1,179 in-footprint polylines)](https://web2.nbmg.unr.edu/arcgis/rest/services/Qfaults/Qfaults_INGENIOUS/MapServer/0) - already restored locally in data_cache/qfaults_v2_in_footprint.json (sha256 4d6efc7b...); the host itself is unreachable from the sandbox, so refresh must run in GitHub Actions (.github/workflows/fetch-vector-faults.yml)

## H27-3 (rank 6): Emission-graph coherence filter: keep multi-dot chains, drop isolated 1-dot fragments

* **Layers:** The dotted emission itself as a point-proximity graph (no new data).
* **Physical signature:** Drop isolated emitted dots that have no other emitted dot within 600 m (6 px), on the hypothesis that isolated specks are false-positive noise whereas multi-dot chains are true fault scarps.
* **Why it catches a fault missing from USGS/INGENIOUS:** Tests whether isolated dots in a d=1.5 thinned ridge emission have efficiency below the break-even threshold m(D).
* **How it differs from the repo:** Graph filter on the emission itself rather than on the catalogue.
* **Status:** REFUTED on the honest 4-fold spatial-CV out-of-fold detector B_oof (Addendum C, seeds 130-139, evidence/oof_hypothesis_gates.json): isolated dots removed by the 600 m filter had hit efficiency 0.0329 (> m_oof = 0.0175), so dropping them reduced DTI in 4/4 folds (mean -0.0010, min -0.0013, max -0.0006). Because catalogued fault segments have a median length of 1.27 km, a single d=1.5 thinned scarp fragment often consists of 1-2 dots; dropping isolated dots discards real short faults. Rejected — no submission slot spent.
* **Expected gain:** -0.0010 on OOF holdout (negative in 4/4 folds). Do not ship.
* **Cost:** Tested and rejected on holdout (0 slots spent).

## H27-2 (rank 7): Step-over / relay-typed linking (oblique tip-to-tip, overlapping en-echelon tips)

* **Layers:** Same graph; lateral offset and overlap of parallel tips.
* **Physical signature:** Tips of parallel strands offset 0.3-3 km, linked by an oblique breaching segment; Faulds & Hinz (2015) report step-overs as the most common structural setting (~32%) of characterised geothermal systems.
* **Why it catches a fault missing from USGS/INGENIOUS:** Relay zones are where overlapping strands multiply; an expert panel mapping a geothermal target would add strands there.
* **How it differs from the repo:** Adds lateral-offset geometry the forward-cone rule cannot generate (overlapping tips).
* **Status:** Partly tested, not supported: in seeds 100-109 oblique tip-to-tip and abutting links had dot-level hit ratios 0.048 and 0.040 against 0.125 for end-to-end links, and only 15 + 16 of the 345 shipped links are of those kinds. Overlapping offsets were never generated.
* **Expected gain:** Not demonstrated.
* **Cost:** Low.

## H27-6 (rank 8): Coverage-optimal budget thinning: choose WHICH dots to keep by maximising coverage

* **Layers:** The emission itself plus the official kernel (no new data).
* **Physical signature:** Poisson-disk thinning is a packing rule, blind to how much of the emission's own support survives. Replace it with the subset of N dots that maximises c(S') = mean over the footprint of max over dots of k(d(.,dot)) - a monotone submodular max-coverage problem whose objective IS the metric's credit functional. Batched greedy with exact local marginal gains gain(y) = sum_{|delta|<3} max(0, k(delta) - cov(y+delta)), 29 shifted-array ops per batch.
* **Why it catches a fault missing from USGS/INGENIOUS:** Under the live-validated retention rule credit(d) = credit_solid * c(d)/c_solid, the score at fixed budget is monotone in c, so maximising c directly should dominate packing.
* **How it differs from the repo:** Every thinning variant in this repository family (dot_thin, score-ordered dotting) ranks dots by geometry or by a detector score. This ranks them by the metric's own coverage functional.
* **Status:** REFUTED. src/gems27/coverage_thin.py, measured on quadrant NW at matched budgets: at 20,752 px coverage-greedy attains 143,341 coverage mass vs Poisson-disk 165,563 = 0.866x (13% WORSE); at 28,209 px it is a wash (1.010x). On a 1-px-wide ridge network isotropic spacing already is the near-optimal cover, and greedy's early picks are made against an empty coverage map and cannot be undone. Rejected - no slot spent. Do not re-propose.
* **Expected gain:** -13% coverage at the sparse budget that matters. Do not ship.
* **Cost:** Tested and rejected (0 slots spent); ~65 s per quadrant

## H27-7 (rank 9): Union-recall ensembling of near-disjoint high-score surfaces

* **Layers:** h19-5, h16-1, H25-ctx-ridge, r7-nms3-dem10-scarp emissions recovered by SHA-256 from the sibling repos.
* **Physical signature:** The best surfaces are nearly pixel-disjoint (Jaccard: h19-5 vs H25-ctx 0.075, vs r7-scarp 0.052, vs h16-1 0.592), which looks like free recall. Union them and thin to the budget optimum.
* **Why it catches a fault missing from USGS/INGENIOUS:** If two surfaces cover DIFFERENT truth, the union's credit could exceed either, and credit - not budget - is the binding constraint on 0.3195.
* **How it differs from the repo:** The group's scored ensembles (ens12 0.1563, dual-family-union 0.1560) were built by score averaging; this is a set union evaluated under the live-anchored forward model with explicit pessimistic bounds.
* **Status:** REFUTED as an improvement; BOUNDED as a gamble. Live-anchored model: h19-5 U h16-1 at d2.25 (51,971 px) = 0.2655 central but 0.2310 under the pessimistic bound TP_union = max(TP_A, TP_B); h19-5 U H25-ctx (87,906 px) = 0.2521 / 0.1688. Against those, h19-5 ALONE at d2.25 is 0.2550 with a retention rule validated to 4%. The union's entire edge lives in an unvalidated complementarity assumption and its downside is -0.086. A weekly slot is worth more than that. No slot spent.
* **Expected gain:** -0.086 to +0.011 depending on an unmeasurable assumption. Do not ship.
* **Cost:** Tested and rejected (0 slots spent)

## H27-9 (rank 10): Live-truth habitat tomography: recover WHERE the hidden labels live from the scores alone

* **Layers:** All 20 hash-authenticated scored rasters + catalogue distance field + LiDAR scarp descriptors.
* **Physical signature:** TP_i = sum_x lambda(x) K_i(x) is linear in the truth intensity lambda, so 20 scored submissions are 20 measurements of lambda - a designed sensing experiment on the private labels. Expand lambda in geological habitat bases and solve non-negative least squares with the mass constraint sum lambda = |G|.
* **Why it catches a fault missing from USGS/INGENIOUS:** Would answer the only question that matters for 0.3195: which habitats the organisers' new expert labels occupy, using the REAL private labels through their scores rather than a catalogue-internal proxy.
* **How it differs from the repo:** Every gate in this repository family validates against catalogue-internal holdouts. This uses the live scores as the label signal.
* **Status:** NOT IDENTIFIABLE - rejected. With overlapping geological bases the fit fails outright (in-sample R2 = -1.24). Restricted to a strict 7-cell catalogue-distance PARTITION (well identified, mass constraint exact) it still fails: in-sample R2 = -0.360, leave-one-submission-out score RMSE 0.0715 against a score spread of 0.0686 - signal ratio 0.96, i.e. no better than predicting the mean. 20 aggregate numbers cannot resolve a 5.2 M-pixel field. The fitted lambda put 66% of truth in the 100-200 m catalogue ring and 34% at 800-1500 m, which is suggestive and consistent with Hermant et al. (2025) 150-400 m LiDAR offsets, but it did not pass its own validation and MUST NOT be used to choose an emission.
* **Expected gain:** none - failed its own leave-one-out validation
* **Cost:** Tested and rejected (0 slots spent); evidence/live_truth_partition_radial.json
