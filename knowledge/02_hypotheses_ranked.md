# Untried hypotheses, ranked (generated from `registry/hypotheses.json`; do not edit by hand)

Ranking rule: expected DTI gain x probability the test can validate it / cost. Before any weekly slot is spent, the top hypothesis must beat the holdout baseline (see `03_preregistration_topology_gate.md`).

## H27-1 (rank 1): Topology gap-closure: along-strike links between disconnected mapped fault systems

* **Layers:** Catalogue raster (labels.tif) -> skeleton graph; local strike domain from the same graph. No external layer.
* **Physical signature:** Free tips (degree-1 nodes) whose strike points at a tip of a different system 1-4 km away; straight link; evidence score z = [mutual] + [end-to-end] + [tip within 15 deg] + [local strike agreement >= 0.4] + [merged length <= 8 km]; ship z >= 3. Network sits near its connectivity threshold (Berkowitz-style P ~ 5.8 vs Pc 5.6-6.0).
* **Why it catches a fault missing from USGS/INGENIOUS:** Mapped faults are compiled in pieces; unmapped continuations across short gaps are where an expert panel adds 'new' faults, and surface-contrast detectors cannot see them because the gap itself is low-contrast. A catalogue that is near percolation is sensitive to exactly such closures.
* **How it differs from the repo:** First use of the catalogue's graph. The sibling's h16-continuation (owner-reported 0.0461) is the nearest prior idea; its construction was not re-examined here, but T-v2 differs by requiring a target system, a 1-4 km gap bound, tip-to-tip alignment and a strike-agreement score, and by being gated on controls.
* **Status:** Validated: pre-registered gates PASSED on seeds 100-109 and confirmed on fresh seeds 110-119 (catalogue-internal holdout).
* **Expected gain:** At the 0.2477 operating point: worst case about -0.003 (zero hit rate), break-even at efficiency 0.052, +0.011 at the holdout efficiency 0.28; central judgment +0.004 to +0.008 if half the holdout enrichment carries over.
* **Cost:** Done (this repo). One slot.

## H27-4 (rank 2): Tip-shadow pruning: drop emission within 300 m of masked catalogue pixels

* **Layers:** Catalogue distance transform + the dotted H19-5 emission.
* **Physical signature:** A surface trained on catalogued scarps peaks on them; once catalogue pixels are masked, emission survives as 1-3 px 'shadows' beside known faults (the sibling measured 22-23% of H19-5 emission within 300 m of the catalogue, ~3.2x enriched at exactly 100 m).
* **Why it catches a fault missing from USGS/INGENIOUS:** If hidden new faults rarely run within 300 m of known ones, these dots are almost pure false-positive mass; removing them cuts FP without touching recall elsewhere.
* **How it differs from the repo:** Subset transform driven by catalogue geometry; the repo's thinning is geometry-blind and its proximity analyses only correlated scores with distance.
* **Status:** Untested: a label-blind honest surface is not available (H19-5 is leaky), so it cannot be gated on the holdout; it is a one-slot diagnostic.
* **Expected gain:** Unknown, signed either way. Break-even logic: removing a set of n dots helps iff its hit efficiency is below 0.052.
* **Cost:** Minutes to build; one slot.

## H27-3 (rank 3): Emission-graph coherence filter: keep collinear chains, drop isolated short fragments

* **Layers:** The emission itself as a graph (no new data).
* **Physical signature:** H19-5 is 26,645 components of mean 4.5 px, whereas catalogued systems have median 12 px (1.27 km). Chains of fragments that are collinear within a few pixels behave like lineaments; isolated 1-4 px specks behave like noise.
* **Why it catches a fault missing from USGS/INGENIOUS:** Raises precision where lineament coherence is absent. Risk: true hidden faults can also be short.
* **How it differs from the repo:** Graph analysis of the emission rather than of the catalogue; the repo only thins by distance.
* **Status:** Untested (needs an honest label-blind surface).
* **Expected gain:** Unknown (0 to +0.02 judgment).
* **Cost:** Hours.

## H27-5 (rank 4): Kinematically typed linking with an official stress model and vector fault attributes

* **Layers:** USGS slip/dilation tendency (Siler 2022) and USGS Qfaults GIS (slip sense, dip direction).
* **Physical signature:** Retain a gap link only if both segments are critically stressed (high slip/dilation tendency) and dip senses are synthetic (relay) or antithetic (accommodation zone) rather than conflicting.
* **Why it catches a fault missing from USGS/INGENIOUS:** Replaces the data-driven strike domain by an independent stress field and adds dip/slip attributes the raster lacks.
* **How it differs from the repo:** No repo layer uses an independent stress model; all kinematics so far are data-driven.
* **Status:** Needs a CI download-and-derive job (not written yet). Both sources are free and official, and their obtainability is now EVIDENCED from a GitHub runner: the NBMG INGENIOUS Qfaults ArcGIS layer (22,956 polylines, 23 attributes incl. DIPDIRECT/SLIPSENSE/FTYPE_/MAPSCALE) is queryable, and USGS Qfaults_GIS.zip (32.4 MB, application/zip) is downloadable. The Siler (2022) stress release is listed (27.35 MB INGENIOUS-area zip) but its file download is not yet verified.
* **Expected gain:** Small to moderate, on the topology class only.
* **Cost:** 1-2 days (CI job + attributed vector graph + trace-level holdout).
* **External data (free, official):** [NBMG Qfaults_INGENIOUS ArcGIS REST layer 0 (22,956 polylines with dip/slip attributes)](https://web2.nbmg.unr.edu/arcgis/rest/services/Qfaults/Qfaults_INGENIOUS/MapServer/0) - verified queryable from a GitHub runner 2026-10-02
* **External data (free, official):** [USGS Qfaults GIS (zip, 32.4 MB)](https://earthquake.usgs.gov/static/lfs/nshm/qfaults/Qfaults_GIS.zip) - verified downloadable from a GitHub runner 2026-10-02 (application/zip)
* **External data (free, official):** [Siler (2022) slip & dilation tendency, Great Basin (USGS ScienceBase)](https://www.sciencebase.gov/catalog/item/6296974dd34ec53d276bb33d) - listing verified; file download not yet verified

## H27-2 (rank 5): Step-over / relay-typed linking (oblique tip-to-tip, overlapping en-echelon tips)

* **Layers:** Same graph; lateral offset and overlap of parallel tips.
* **Physical signature:** Tips of parallel strands offset 0.3-3 km, linked by an oblique breaching segment; Faulds & Hinz (2015) report step-overs as the most common structural setting (~32%) of characterised geothermal systems.
* **Why it catches a fault missing from USGS/INGENIOUS:** Relay zones are where overlapping strands multiply; an expert panel mapping a geothermal target would add strands there.
* **How it differs from the repo:** Adds lateral-offset geometry the forward-cone rule cannot generate (overlapping tips).
* **Status:** Partly tested, not supported: in seeds 100-109 oblique tip-to-tip and abutting links had dot-level hit ratios 0.048 and 0.040 against 0.125 for end-to-end links, and only 15 + 16 of the 345 shipped links are of those kinds. Overlapping offsets were never generated.
* **Expected gain:** Not demonstrated.
* **Cost:** Low.
