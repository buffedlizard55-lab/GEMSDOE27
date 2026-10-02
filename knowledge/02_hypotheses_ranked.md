# Untried hypotheses, ranked (generated from `registry/hypotheses.json`; do not edit by hand)

Ranking rule: expected DTI gain x probability the test can validate it / cost. Before any weekly slot is spent, the top hypothesis must beat the holdout baseline (see `03_preregistration_topology_gate.md`).

## H27-1 (rank 1): Topology gap-closure: along-strike links between disconnected mapped fault systems

* **Layers:** Catalogue raster (labels.tif) -> skeleton graph + NBMG INGENIOUS Qfaults vector polylines (qfaults_v2_in_footprint.json, 1,179 features); local strike domain from the same graph.
* **Physical signature:** Free tips (degree-1 nodes) whose strike points at a tip of a different system 1-4 km away; straight link; evidence score z = [mutual] + [end-to-end] + [tip within 15 deg] + [local strike agreement >= 0.4] + [merged length <= 8 km]; ship z >= 3 (345 links, 1,259 non-redundant dots vs 0.2477). Network sits near its connectivity threshold (Berkowitz-style P ~ 5.8 vs Pc 5.6-6.0).
* **Why it catches a fault missing from USGS/INGENIOUS:** Mapped faults are compiled in pieces; unmapped continuations across short gaps are where an expert panel adds 'new' faults, and surface-contrast detectors cannot see them because the gap itself is low-contrast. Vector attribution against 1,179 NBMG polylines shows 230/345 links bridge intra-FID sub-parts of the same multipart polyline, 115/345 bridge distinct FID polylines, 312/345 lie within the same named fault zone (NAME/NUM), and 333/345 have compatible SLIPSENSE/DIPDIRECT.
* **How it differs from the repo:** First use of the catalogue's graph and vector polyline topology. The sibling's h16-continuation (owner-reported 0.0461) is the nearest prior idea; T-v2 differs by requiring a target system, a 1-4 km gap bound, tip-to-tip alignment, and a strike-agreement score, and by being gated on rotated-cone controls across three holdout tiers plus an out-of-fold spatial-CV base.
* **Status:** VALIDATED across 4 independent protocols: (1) component holdout seeds 100-109 (0.281 vs 0.059 ctrl) and fresh seeds 110-119 (0.280 vs 0.056 ctrl, +0.0117 paired DTI, 4/4 folds); (2) NBMG FID vector-trace holdout seeds 120-129 (0.1003 vs 0.0204 ctrl, 4.92x enrichment, > m(0.30)=0.0638); (3) honest 4-fold spatial-CV out-of-fold detector B_oof on seeds 130-139 (+0.0115 paired DTI, 4/4 folds, marginal efficiency 0.2251).
* **Expected gain:** At the 0.2477 operating point: worst case -0.0029 (zero hit rate), break-even at efficiency 0.0522, +0.0024 at the FID vector-trace holdout efficiency 0.1003, and +0.0110 at the component holdout efficiency 0.280-0.293. Shipped as Primary Slot 1 (5512495c6bd1) and Secondary Slot 2 (3ebd51534bb1).
* **Cost:** Done (this repo). Shipped in Slot 1 & Slot 2.

## H27-4 (rank 2): Tip-shadow pruning: drop emission within 100-300 m of masked catalogue pixels

* **Layers:** Catalogue distance transform (d_cat) + dotted emission surface.
* **Physical signature:** A surface trained on catalogued scarps peaks on them; once 1-px catalogue cells are masked, emission survives as 1-3 px 'shadows' beside known faults (further reinforced by 100-400 m USGS-vs-LiDAR scarp offsets documented by Hermant et al. 2025, Fig. 2 & Fig. 9B). In the 0.2477 file (60,069 px), 5,355 dots (8.91%) sit at exactly d_cat = 100 m (1 px) and 8,769 (14.60%) within 200 m.
* **Why it catches a fault missing from USGS/INGENIOUS:** Because ground truth G consists of newly created fault labels rather than the unmasked 100-200 m flank of already-catalogued faults, these 1-2 px flank-shadow dots are almost pure false-positive mass; removing them cuts FP without touching recall on new faults.
* **How it differs from the repo:** Subset transform driven by catalogue distance geometry and gated on an honest out-of-fold spatial-CV detector; the repo's thinning is geometry-blind.
* **Status:** VALIDATED on the honest 4-fold spatial-CV out-of-fold detector B_oof (seeds 130-139, evidence/oof_hypothesis_gates.json): dropping dots at d_cat <= 100 m (1 px) removes dots with efficiency 0.0034 (15x below the 0.0521 live break-even), raising DTI in 4/4 folds (+0.0022 solo; +0.0141 when stacked with T-v2 in 4/4 folds). Dropping d_cat <= 200 m (2 px) removes dots with efficiency 0.0080 (+0.0025 solo, 4/4 folds; +0.0147 stacked with T-v2). Dropping d_cat < 300 m (3 px) removes dots with efficiency 0.0140 (+0.0014 solo, 3/4 folds).
* **Expected gain:** At the 0.2477 operating point: pruning the 5,355 d_cat=100 m flank-shadow dots alone gives +0.0118 modelled DTI (to ~0.2598); stacking with T-v2 (Slot 3 candidate d466b251f309, 55,992 px) gives +0.0141 modelled DTI under FID_trace efficiency (to ~0.2621) and +0.0223 under component efficiency (to ~0.2702).
* **Cost:** Done (this repo). Shipped as Tertiary Slot 3 (d466b251f309).

## H27-5 (rank 3): Kinematically typed linking with official NBMG/USGS vector fault attributes (SLIPSENSE, DIPDIRECT, NAME)

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

## H27-3 (rank 4): Emission-graph coherence filter: keep multi-dot chains, drop isolated 1-dot fragments

* **Layers:** The dotted emission itself as a point-proximity graph (no new data).
* **Physical signature:** Drop isolated emitted dots that have no other emitted dot within 600 m (6 px), on the hypothesis that isolated specks are false-positive noise whereas multi-dot chains are true fault scarps.
* **Why it catches a fault missing from USGS/INGENIOUS:** Tests whether isolated dots in a d=1.5 thinned ridge emission have efficiency below the break-even threshold m(D).
* **How it differs from the repo:** Graph filter on the emission itself rather than on the catalogue.
* **Status:** REFUTED on the honest 4-fold spatial-CV out-of-fold detector B_oof (Addendum C, seeds 130-139, evidence/oof_hypothesis_gates.json): isolated dots removed by the 600 m filter had hit efficiency 0.0329 (> m_oof = 0.0175), so dropping them reduced DTI in 4/4 folds (mean -0.0010, min -0.0013, max -0.0006). Because catalogued fault segments have a median length of 1.27 km, a single d=1.5 thinned scarp fragment often consists of 1-2 dots; dropping isolated dots discards real short faults. Rejected — no submission slot spent.
* **Expected gain:** -0.0010 on OOF holdout (negative in 4/4 folds). Do not ship.
* **Cost:** Tested and rejected on holdout (0 slots spent).

## H27-2 (rank 5): Step-over / relay-typed linking (oblique tip-to-tip, overlapping en-echelon tips)

* **Layers:** Same graph; lateral offset and overlap of parallel tips.
* **Physical signature:** Tips of parallel strands offset 0.3-3 km, linked by an oblique breaching segment; Faulds & Hinz (2015) report step-overs as the most common structural setting (~32%) of characterised geothermal systems.
* **Why it catches a fault missing from USGS/INGENIOUS:** Relay zones are where overlapping strands multiply; an expert panel mapping a geothermal target would add strands there.
* **How it differs from the repo:** Adds lateral-offset geometry the forward-cone rule cannot generate (overlapping tips).
* **Status:** Partly tested, not supported: in seeds 100-109 oblique tip-to-tip and abutting links had dot-level hit ratios 0.048 and 0.040 against 0.125 for end-to-end links, and only 15 + 16 of the 345 shipped links are of those kinds. Overlapping offsets were never generated.
* **Expected gain:** Not demonstrated.
* **Cost:** Low.
