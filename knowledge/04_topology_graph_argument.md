# Topology candidate class: the graph-based argument

Everything here is reproducible from `data/manifest.json` inputs: `scripts/run_graph_report.py` -> `evidence/graph_report.json`;
`scripts/run_topology_validation.py` and `scripts/run_topology_confirm.py` -> `evidence/topology_*.json`;
`scripts/build_candidates.py` -> `registry/topology_candidates.json`, `docs/data/topology_links.{csv,geojson}`.

## 1. The graph
Skeleton of the catalogue raster (60,988 px, 100 m, 8-connectivity). Nodes: free tips and junction clusters; edges: pixel chains (mapped segments).

| quantity | value |
|---|---|
| skeleton pixels | 59,209 |
| systems (graph components) | 3,199 |
| end nodes / junction nodes / edges | 6,949 / 679 / 4,681 |
| loops (see note) | raw cyclomatic number 250; 110 after dropping self-loops of <= 3 px; 370 enclosed background regions, of which only **6 exceed 20 px** and none 100 px |
| system length: median / p90 / p99 / max | 1.27 / 4.37 / 14.1 / 42.3 km |
| systems < 2 km / >= 10 km | 2,211 / 69 |
| tips with a defined strike (>= 800 m of chain) | 6,530 |

The catalogue is **fragmented**: most "faults" are short mapped pieces, and 32 % of tips have another system within 300 m. It is also **nearly acyclic** (tree-like): genuinely closed fault polygons are rare; most raw loops are pixel-scale artefacts around thick junction clusters (an earlier version of the edge builder over-counted them: 504, corrected in review pass 2).

## 2. What Berkowitz, Bour, Davy & Odling (GRL 27(14), 2061-2064, 2000) establish - checked line by line
Sources read 2026-10-02: the publisher abstract page and a full-text copy (see `registry/sources.json`).

| statement | verdict | basis |
|---|---|---|
| The paper analyses the San Andreas fault system and a joint network | **verified** | abstract |
| Connectivity depends on the scale of measurement for a < D+1 and is scale-independent for a > D+1 (a: length-distribution exponent, D: fractal dimension) | **verified** | abstract |
| For the San Andreas, a < D+1 and the connectivity threshold is reached only at a critical length scale | **verified** | abstract; text: a = 2.1, D = 1.65, beta = 0.0085; "connectivity is expected for L > 21 km" (lmin about 1 km); sensitivity 10 < Lc < 50 km |
| Numerical critical length | **reproduced approximately** | my own closed form from the paper's eq. (1) gives 21.6 km (lmin -> 0) and 26.7 km (lmin = 1 km) with the paper's inputs (`tests/test_topology_theory.py`); the paper's "21 km" is within ~25 % |
| One mapped segment decides whether two particular faults are joined | **not stated by the paper** | the paper says its results "are statistical, and provide connectivity estimates on averages, rather than on particular realizations". Near a threshold such a statement is plausible for a given realisation, which is why it is *tested* here rather than assumed |

## 3. Where the GeoDAWN catalogue sits (our analysis, not the paper's)
* Exponent a (density, MLE above lmin): 2.16 (1 km), 2.38 (1.5 km), 2.50 (2 km), 2.77 (3 km), 2.82 (4 km) - **not a clean power law** (the tail is steeper), so a is only roughly 2.2-2.8.
* Correlation dimension of system centres: D = 1.53-1.60 depending on the fit range (headline 1.57, 5-50 km, R^2 0.999).
* D+1 = 2.57, so a straddles D+1: the catalogue is **on the cusp** between "scale-dependent" and "controlled by the smallest segments" - the sandstone-joint regime of the paper, not the San Andreas regime (a = 2.1 << D+1 = 2.65).
* Headline parameters (lmin 2 km): beta = 0.54 (L in metres, equivalent square side 227 km), P(L = 227 km) = 5.78 against Pc = 5.6-6.0, i.e. **at the percolation threshold at the scale of the study area** (Lc = 197-269 km). Treat as order-of-magnitude: beta depends on L^D, a and D carry the uncertainties above, and the formulas are ensemble statements.
* Empirical single-linkage curve (merge every pair of systems closer than r): systems 3,199 -> 293 (2 km) -> 72 (4 km) -> 27 (6 km) -> 10 (8 km); largest system 0.6 % of fault length (150 m) -> 10.5 % (2 km) -> 27.9 % (4 km) -> 42.8 % (6 km) -> **83.7 % (8 km)**. The giant system emerges between 6 and 8 km.

Reading: the mapped network is close to critical, so closures matter more than in a well-connected network. **But** the closures that the holdout supports are not the giant-system bridges.

## 4. The candidate rule and its evidence
Rule T-v1 (frozen in `03_preregistration_topology_gate.md`): from each free tip, the nearest pixel of a different system inside a +-30 deg forward cone, kept if 1-4 km away; dots every 3 px.
Evidence score z in 0..5 (T-v2): mutual nearest tips, end-to-end alignment (target tip points back within 35 deg), tip within 15 deg of the link, local strike agreement >= 0.4, merged length <= 8 km; ship z >= 3.

| test | seeds | result |
|---|---|---|
| T-v1 gate (registered) | 100-109 (40 cells) | pooled efficiency 0.118 vs rotated-cone controls 0.057 (2.07x, narrow pass); forward > control in 4/4 folds (5.1x, 2.5x, 1.4x, 1.7x); paired DTI gain +0.0184 vs the leaky dotted-H19-5 base, no cell negative |
| T-v2 gate (registered before the run) | 110-119 (40 cells) | z>=3 efficiency 0.226 (all links 0.121; random same-size subsets mean 0.149, p95 0.156; controls 0.056); z>=3 beats all-links in 4/4 folds; paired gain +0.0115, worst cell +0.0036; **de-duplicated mutual pairs 0.280** (shipped) |
| break-even | - | 0.053 at DTI 0.25 (0.064 at 0.30) |

Efficiency falls as overlapping links accumulate, so the right null for the z>=3 set is a random subset of the same size, not the full set.

Post-hoc structure (seeds 100-109, exploratory): hit ratio rises with mutual tips (0.153 vs 0.051), end-to-end alignment (0.125 vs 0.040-0.048 for abutting/oblique), small tip angle (0.138 at <=10 deg vs 0.044 at 20-30 deg) and strike agreement (0.141 at >=0.5 vs 0.042 at <0.2).
**Larger merged systems were less enriched** (ratio 0.043 above 16 km vs 0.149 below 4 km). That is what fragment completion in a segmented catalogue looks like, and it is also the main reason to doubt that the holdout enrichment transfers to expert-mapped new faults.

## 5. The shipped set
1,965 forward links on the full catalogue; z >= 3 and de-duplicated mutual pairs -> **345 links, 1,840 dots, 1,259 not already within 300 m of the 0.2477 emission** (all 345 are listed with coordinates and a written argument in `docs/data/topology_links.csv` / `.geojson` and on `docs/topology.html`).
314 are end-to-end, 16 abutting, 15 oblique; 172 are mutual pairs; median gap 1.84 km; on average 32 % of a link's dots already lie near the base emission.
Closing all 345: systems 3,199 -> 2,857, largest 42.3 -> 57.5 km. The class **completes fragments; it does not form the giant system** - the percolation argument motivates the angle, the holdout validates only the fragment-completion part.

## 6. Regional-kinematics statement (what is and is not used)
* Used: a data-driven strike domain - the share of nearby catalogued fault length (distance-weighted, ~40 km) within 20 deg of the link strike — AND, in Session 2, official NBMG INGENIOUS Quaternary Fault vector attributes (`FID`, `NAME`, `NUM`, `FTYPE_`, `SLIPSENSE`, `DIPDIRECT`, `MAPSCALE` from `qfaults_v2_in_footprint.json`).
* Context only (literature, not an input): west- to northwest-directed extension of the Basin and Range and dextral Walker Lane shear (Faulds & Hinz 2015); step-overs/relay ramps host ~32 % and terminations ~25 % of characterised Great Basin geothermal systems; the largest strike-slip step broken by a rupture in Wesnousky's compilations was 4 km (as quoted by Biasi & Wesnousky 2016) - the same scale as the 1-4 km link range, which is context and not evidence.

## 7. Official NBMG INGENIOUS vector attribution & three-tier holdout (`evidence/vector_topology_validation.json`)
To resolve whether T-v2 merely repairs raster discretisation gaps or also bridges genuinely distinct vector fault traces, we cross-referenced `labels.tif` against the 1,179 NBMG INGENIOUS Quaternary fault polylines (`Qfaults [INGENIOUS 6-27-2023]`, `data_cache/qfaults_v2_in_footprint.json`, SHA-256 `4d6efc7bb3659ea2545353fcec574ef085b0acdb189c7590e4420a7c6c57b41c`):
* **Raster-to-vector alignment:** **98.42%** of `labels.tif` pixels lie within 100 m (1 px) of a vector polyline, and **99.97%** lie within 200 m (2 px).
* **Attribution of the 345 shipped T-v2 links:**
  * **230 / 345 (66.7%)** bridge sub-parts of the same multipart `FID` polyline (intra-`FID` compilation/discretisation gaps).
  * **115 / 345 (33.3%)** link distinct `FID` records (inter-`FID` review candidates; not all are verified geological relays or step-overs).
  * **312 / 345 (90.4%)** link segments within the same named fault zone (`NAME`/`NUM`); **33 / 345 (9.6%)** link differently named or unnamed records.
  * **333 / 345 (96.5%)** pass the permissive `kinematic_compat` screen. It rejects conflicting known slip senses and certain opposite dip-direction pairs; blank/`Unspecified` attributes can pass. It is not a stress inversion or verified slip history.
* **Confirmatory three-tier holdout (Addendum B, seeds 120-129, 40 cells per tier):**

| Holdout tier (20% hidden per quadrant) | `all` links | `z>=3 dedup` (shipped rule) | `H27-5a` (`inter-FID + kinematic_compat`) | `H27-5b` (`inter-FID + same_name + kinematic_compat`) | Rotated-cone `ctrl` | Enrichment (`z>=3 / ctrl`) |
|---|---:|---:|---:|---:|---:|---:|
| **Tier 1: `component`** (8-connected raster systems) | 0.1257 | **0.2926** | 0.1987 | 0.2366 | 0.0586 | **5.00x** |
| **Tier 2: `FID_trace`** (whole NBMG `FID` multipart polylines) | 0.0442 | **0.1003** | **0.1374** | **0.1783** | 0.0204 | **4.92x** (`H27-5b`: **8.74x**) |
| **Tier 3: `NAME_zone`** (entire 20-70 km named fault zones) | 0.0005 | **0.0014** | 0.0042 | 0.0031 | 0.0012 | 1.17x |

Both pre-registered Addendum B gates passed (`g1_fid_trace_z3_gt_m030_and_ge_2x_ctrl = true`, `g2_h27_5_kinematic_typing_improves_on_fid_trace = true`).

## 8. Honest out-of-fold (OOF) spatial-CV hypothesis gates (`evidence/oof_hypothesis_gates.json`)
To eliminate the `H19-5` training-label leakage on paired holdout tests, we trained a 4-fold spatial-CV `HistGradientBoostingClassifier` (with a 600 m buffer around each test quadrant) on the 32-band label-free feature matrix (`data_cache/prepared/features.npy`, excluding the mislabelled `tc` band) and extracted 1-px ridges via directional non-maximum suppression (`src/gems27/oof_detector.py`). On fresh seeds 130-139 (40 cells, mean base DTI `0.0861`, OOF break-even `0.0175`, live break-even `0.0521`):
* **H27-1 (`plus_T_v2`):** **`+0.0115`** mean paired DTI gain (`+0.0078` to `+0.0145` across all 10 seeds), improving **4/4 folds**, marginal efficiency **`0.2251`** (**PASSED**).
* **H27-4 (`prune_r1_100m`, dropping dots within 100 m of catalogue):** removed dots have efficiency **`0.0034`** (15x below live break-even `0.0521`), giving **`+0.0022`** mean DTI gain in **4/4 folds** solo, and **`+0.0141`** in **4/4 folds** when stacked with T-v2 (**PASSED**; shipped as Tertiary Slot 3 candidate `d466b251f309`).
* **H27-4 (`prune_r2_200m`, dropping dots within 200 m of catalogue):** removed dots have efficiency **`0.0080`**, giving **`+0.0025`** solo in **4/4 folds** and **`+0.0147`** stacked with T-v2 (**PASSED**).
* **H27-3 (`coherence_h27_3`, dropping isolated 1-dot fragments with no neighbour within 600 m):** removed dots have efficiency **`0.0329`** (`> m_oof = 0.0175`), reducing DTI by **`-0.0010`** in **0/4 folds** (**REFUTED** and rejected without spending a slot).

## 9. Session 5 H27-5b map-review export (not a new predictive class)
The exclusive geologist-review class is **81** of the 345 selected links, defined exactly as `fid_src != fid_tgt AND same_name AND kinematic_compat=true`; `same_name` excludes the generic `NAME == "Unnamed fault"` sentinel. The 345 records partition into 230 same-FID multipart-continuity, 81 H27-5b, 22 other-name kinematically-compatible inter-FID, and 12 conflict/unknown inter-FID links. The priority subset comprises 73 end-to-end, 4 abutting and 4 tip-to-tip oblique links; all 81 have `bridge=true` under the selected-candidate graph, which is a graph property and not fault confirmation.

The focused, shortest-gap-first table is `docs/data/topology_priority_h27_5b.csv`; the endpoint-line GeoJSON is `docs/data/topology_priority_h27_5b.geojson` (WGS84 candidate geometries, not mapped fault traces); all 345 links retain the exclusive review class in `docs/data/topology_links.csv`/`.geojson`. The docs page, machine-readable counts and source links are maintained in `docs/topology.html`, `docs/data/topology_review_classes.json`, `evidence/structural_relay_classes.json`, and `knowledge/11_h27_5b_geologist_review_class.md`.

Tier-2 whole-FID holdout efficiency for H27-5b is 0.178296 versus 0.020384 for the rotated control (8.75x), seeds 120-129. This catalogue-internal enrichment supports map-review prioritization only; it does not establish hidden-label truth, transfer, or a live-score gain. Different FIDs are records in the same NBMG compilation, not independent surveys, and the compatibility screen is permissive when attributes are missing. Geometry cues and Faulds & Hinz structural-setting frequencies are context only. The graph-ΔP ranking and overlapping en-echelon step-over were **refuted** as predictive holdout-improvement signals in Addendum D; the review class does not revive either signal.
