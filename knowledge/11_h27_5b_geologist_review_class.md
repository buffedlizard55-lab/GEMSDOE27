# H27-5b: geologist-review priority class for short inter-FID links

**Purpose.** Separate a reviewable subset of the existing 345 T-v2 topology links for manual geological inspection. This is a prioritization aid, not a new emission, a new holdout-improvement claim, or permission to spend a weekly submission slot.

## Exact filter and count

The population is the existing 345 shipped T-v2 candidates (`z >= 3`, deduplicated; each has a 1–4 km gap); this review filter creates no new links. For each such link, the class is assigned when all three conditions hold:

```text
fid_src != fid_tgt
AND same_name == true
AND kinematic_compat == true
```

`same_name` means equal NBMG `NAME` attributes except the generic `Unnamed fault` value. `kinematic_compat` is the existing H27-5 screen: differing non-empty slip senses are rejected; registered opposite dip-direction pairs are also rejected when slip senses differ and at least one is right-/left-lateral. Blank or `Unspecified` values are normalized to unknown and may pass the permissive check. It is a record-level consistency screen, not a stress inversion or verified slip history. See `src/gems27/vector_graph.py` and `src/gems27/topology_classes.py` for the executable rule.

The exclusive classification of all 345 links is:

| Exclusive review class | Count |
|---|---:|
| Same-FID multipart continuity | 230 |
| **H27-5b: inter-FID, same-name, kinematically compatible** | **81** |
| Inter-FID, other-name, kinematically compatible | 22 |
| Inter-FID, kinematic conflict or unknown under the screen | 12 |

The focused 81 consist of 73 end-to-end links, 4 abutting links, and 4 tip-to-tip oblique links. Their gaps are sorted shortest-first in the review CSV, with link ID as deterministic tie-break. All 81 are marked as graph bridges in the selected 345-link graph; “bridge” here means no other selected candidate joins those graph sides under the code's graph construction. It does **not** demonstrate that the geographic gap is a real fault, that the network is tectonically connected, or that a hidden target label lies there.

## Why this subset is prioritized—and what the evidence does not say

The NBMG INGENIOUS whole-`FID` holdout (Addendum B, seeds 120–129) measured H27-5b pooled efficiency at **0.178296**, versus **0.020384** for the rotated control (**8.75×**). This is catalogue-internal evidence on held-out FID records from the same compilation. It supports spending geologist review effort on this subset relative to the broader set; it does not establish transfer to the organizer-created test labels, candidate-by-candidate fault truth, a leaderboard/live-score gain, or superiority of graph-importance ranking. The exact record is `evidence/vector_topology_validation.json`.

Distinct FIDs are records in the same NBMG compilation, not independent surveys. Same-name features may be named segments of one fault zone. The vector association is nearest-polyline attribution and can be affected by map scale, segmentation, raster-to-vector alignment and ambiguous/multipart geometries. “Kinematically compatible” permits missing attributes and is not a claim that the faults share a local stress field. Each row should therefore be checked against the original map and source-layer attributes before any geological conclusion is drawn.

The prior graph-ΔP ranking was **refuted** as a predictive holdout-ranking signal in Addendum D (seeds 140–149); graph importance is included only as descriptive context in each dossier. The registered overlapping en-echelon step-over test was also **refuted** as an efficiency/holdout-improvement signal (Addendum D-4). An individual T-v2 row's “tip-to-tip oblique” cue is not evidence of an overlapping step-over, a favorable relay, or a productive geothermal setting. Do not conflate the map-review class with either refuted hypothesis.

## Geometry-only review cues

The `setting_hint` field is deliberately cautious and conditional:

- **End-to-end:** along-strike endpoint gap; assess continuation, relay, or cartographic segmentation.
- **Abutting:** abutment/termination geometry; verify intersections and cross-cutting relations.
- **Tip-to-tip oblique:** oblique, step-over-like map geometry; verify actual overlap, slip sense, and relay direction.

These are prompts for map inspection, not automated structural interpretations. Faulds & Hinz (2015) describes setting frequencies among characterized geothermal systems; those frequencies are not evidence that any particular candidate occupies such a setting.

## Review artifacts

- Focused CSV: [`docs/data/topology_priority_h27_5b.csv`](../docs/data/topology_priority_h27_5b.csv) — 81 rows, sorted by gap; includes endpoint coordinates, FID/NAME/NUM, feature type and map scale, slip-sense/dip-direction attributes, compatibility flag, gap geometry, cautious setting hint, graph context, a per-link written argument, and official source-layer/context URLs.
- Focused map data: [`docs/data/topology_priority_h27_5b.geojson`](../docs/data/topology_priority_h27_5b.geojson) — WGS84 line geometries from the candidate endpoints, for loading in a GIS. Coordinates represent candidate gaps, not verified fault traces.
- Static footprint preview: [`docs/assets/fig_map_h27_5b_priority.png`](../docs/assets/fig_map_h27_5b_priority.png) — H27-5b links in red, other T-v2 links in gray, and catalogue pixels in dark ink; not a substitute for reviewing each link against original map/source geometry.
- Full context: [`docs/data/topology_links.csv`](../docs/data/topology_links.csv) and [`docs/data/topology_links.geojson`](../docs/data/topology_links.geojson) — all 345 candidates with exclusive class and review fields.
- Machine-readable definition, class counts, evidence and limitations: [`docs/data/topology_review_classes.json`](../docs/data/topology_review_classes.json) and [`evidence/structural_relay_classes.json`](../evidence/structural_relay_classes.json).
- The [Topology page](../docs/topology.html) presents the filter, direct downloads and full candidate table; the review-class column is searchable.

## Official-source trail

- [NBMG Qfaults INGENIOUS feature layer](https://web2.nbmg.unr.edu/arcgis/rest/services/Qfaults/Qfaults_INGENIOUS/MapServer/0) — source for vector geometry and `FID`, `NAME`, `NUM`, `SLIPSENSE`, `DIPDIRECT`, `FTYPE_` and `MAPSCALE`; registry records the REST layer as verified/queryable and the local 1,179-feature in-footprint extract as restored at `data_cache/qfaults_v2_in_footprint.json` (SHA-256 `4d6efc7b…`). See `registry/sources.json` for retrieval status and details.
- [Faulds & Hinz (2015), OSTI-hosted paper](https://www.osti.gov/servlets/purl/1724082) — read for broad setting context only; not a candidate-specific source.
- [Berkowitz et al. (2000), AGU/Wiley publisher abstract](https://agupubs.onlinelibrary.wiley.com/doi/10.1029/1999GL011241) — supports an ensemble-scale connectivity framework; it does not assign truth to any particular gap.
- The [USGS Interactive Fault Map](https://doi.org/10.5066/F7S75FJM) provides a separate human-review reference for Quaternary faults. Its coverage and mapping scale do not constitute independent validation of these links.

No DrivenData page was accessed, no submission TIFF was created from this class, no score was observed, and no weekly-slot artifact was modified.
