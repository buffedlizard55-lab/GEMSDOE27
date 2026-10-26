# 23 — Session 10 (2026-10-26): 5 ranked hypotheses + H31 preregistration (frozen before any run)

**Labelling.** Leaderboard numbers are **OWNER-REPORTED** (2026-10-26 owner prompt; no
ORGANIZER-CONFIRMED receipt exists in this repo; this agent never accesses drivendata.org).
Detector numbers will be **HOLDOUT-DTI** (`gems27.metric` v1, α=0.2, β=0.8, 300 m triangular
kernel). **MEASURED** = recomputed from bytes this session. Core values: Maximize P(Win),
Own the Outcome — neither licenses claiming what is not evidenced.

## 0. State inherited (verified this session, 2026-10-26)

- 129 tests pass; `verify_downloads.py` 0 failures; data restored hash-pinned
  (prepared stack sha256 `83ed2704…`, matches README); 12 peer rasters re-fetched.
- **No TIFF in this repo is certified OK to submit** (`docs/data/submission_readiness_audit.json`:
  `approved: []`). Every prior run card verdict is `negative`.
- Inherited next step was "H29-6 on seeds 220–229" (`knowledge/06`, `knowledge/16`).
  **Irregularity (flagged): seeds 215–224 were already consumed by L-DCONFIRM**
  (`evidence/dconfirm_holdout_2026-10-25.json`), so 220–224 are NOT fresh. This session
  therefore uses **seeds 260–269** (verified unused: no seed-26x usage anywhere in
  `knowledge/`, `registry/`, `evidence/`, `scripts/`).
- **New live datapoint from the 2026-10-26 prompt (OWNER-REPORTED):** this repo's H29-S file
  (`511898747886`) scored **0.2190** live. It was the repo's best-ever blind holdout surface
  yet scored below the 0.2778 family champion live — direct evidence that catalogue-internal
  holdout gains do not automatically transfer to the organizers' hidden labels (`knowledge/10`
  proxy limit). P(Win) reasoning below is tempered accordingly.
- **Parallel-lane collision check:** GEMSDOE32's site (fetched 2026-10-26) now promotes a new
  unscored file `gemsdoe32-r6-stepprofile-…-23fbbb51-zeros.tif` (sha256 `c7f094c1f4d0…`
  MEASURED from the repo tarball, 37,654 dots, ~19–21 % 3-px overlap vs every pinned peer —
  a genuinely decorrelated det_elev step-vs-ramp lane). Their PROMOTE rests on an **SGMC-truth
  instrument**; their own run card's catalogue-hidden instrument ranks it *below* the champion
  (0.00338 vs 0.00452). Cross-instrument disagreement is flagged for the selector; this repo
  neither promotes nor blocks it, but **screens H31 against it as a 13th peer**.

## 1. Why 0.2778 (GEMSDOE32 h33-h33-2-b2) is the family best — PhD-level answer (summary)

Full verified treatments: `knowledge/12_why_02778_won.md`, `knowledge/18_why_02778_won_phd_analysis.md`.
Re-verified from bytes this session (MEASURED): the entire top cluster is **one nested dot field**:
H19-5 dotted d=1.5 (60,069; 0.2477) → d=2.8 (44,090; 0.2600; GEMSDOE25 dots == GEMSDOE30 dots
pixel-exact) → B1 prune (40,199; 0.2708; GEMSDOE28 dots == GEMSDOE31 dots pixel-exact) →
B2 prune (37,654; **0.2778** = B1 minus exactly its 2,545 dots in the (100 m, 200 m] catalogue
annulus). GEMSDOE36's 0.2750 file is the champion **plus exactly 1,200 dots** (MEASURED superset).
Mechanism: the scorer masks the published catalogue, so dots within 200 m of known traces are
almost pure false-positive mass (measured credit efficiency ≈0.003–0.016/dot vs break-even
0.2·DTI ≈ 0.056 at DTI 0.2778); every family gain came from *deleting* such mass, not from new
geology. **Can we beat 0.2778?** Only by placing the same ~37.7 k B2 mass *better* (new ranking
information). More deletion/re-thinning of H19-5 is (a) at its measured ceiling (≈0.29 MODEL)
and (b) a protocol duplicate (>70 % 3-px overlap). The prompt states the leaderboard high as
both 0.4413 and 0.3195 (flagged, IR-2026-10-25-02 class); either target needs ranking
information this family does not contain.

## 2. Five candidate hypotheses, ranked (generated before implementing)

| Rank | Hypothesis | Layers | Physical signature | Why a catalogue-*missing* fault | Differs from repo | Named mimic | Prior paired ΔDTI (holdout) | Cost / data |
|---|---|---|---|---|---|---|---|---|
| **1 ★LANE** | **H31 complementary OOF-surface rank ensemble** | H29-S stage-2 OOF surface (32 + 20 H29 hydrothermal/piedmont + S2 Frangi vesselness) + D0 OOF surface (32 + 15 subsurface transforms incl. seismic-fabric coherence) | Per-pixel mean of within-footprint percentile ranks of two independently validated surfaces; identical CELF B2 emission | The two detectors encode different physics (surface hydrothermal/piedmont vs subsurface potential-field/strain/seismicity). Measured fold complementarity (`knowledge/16`): H29-S wins NW/NE/SW, D0 wins SE Walker Lane. Faults seen by either physics but missed by the other are exactly the blind/buried class absent from a surface-rupture-scoped catalogue | No cross-detector *surface* ensemble exists in the repo (prior "hybrids" appended features into one HGB — twice refuted by dilution: L-DCONFIRM arm E, H30 DIP/GAP). Rank-averaging validated surfaces cannot dilute a retrained model | Shared base-32 false lineaments (lithologic contacts, Lahontan shorelines, survey seams) are reinforced, not cancelled | [−0.001, +0.004] vs H29-S | Low; both surfaces rebuilt by existing frozen code; hash-pinned data present |
| 2 | H29-6 feature-append seismic fabric (inherited next step) | `ieq_n100a15`, `deq_n100a15`, `geod_shearrate` via `seismicity_fabric.py` (6 directional features) appended to H29 stage-1 | Directional morphological line-strength of earthquake density aligned ≤30° with shear gradient | Active blind transtensional strands (Mina deflection) with microseismic fabric but no Holocene scarp | Untried in this exact stacked form | Off-fault swarms; catalogue-completeness gradients | [−0.002, +0.003] | Low-medium; local. Ranked below H31: H28-4 2-seed probe was negative (evidence file missing, IR-2026-10-25-18), feature-append dilution twice measured, and D0 already carries the coherence version — H31 captures most of the SE signal at lower risk |
| 3 | H29-3 Lahontan shoreline deconfounder | `det_elev`, lidar step/strike bands (+ raw 3DEP elevation for the absolute 1,200–1,340 m belt) | sin²(scarp-strike − contour-strike) suppression of contour-parallel benches | Frees CELF budget from wave-cut false scarps in Carson Sink/Winnemucca, exposing genuine piedmont faults | No contour-parallelism filter anywhere in repo (GEMSDOE32's R6 *detects* steps and names shorelines as mimic; suppression is the inverse operation) | Low-angle detachment toes sub-parallel to contours | [0, +0.003] | Medium; `det_elev` is detrended — absolute-elevation belt needs USGS 3DEP tiles (`dem_links.json`; official source https://www.usgs.gov/3d-elevation-program), host not in sandbox allowlist → partial only |
| 4 | H29-5 canyon-mouth knickpoint collinearity | `det_elev`, `det_local_relief`, `det_gradient`, lidar relief/cross bands | Collinear 0.5–2 km alignments of transverse canyon outlets / fan apexes | Aggrading bajadas bury inter-canyon scarps within centuries while range-front fault control persists in drainage geometry | All existing DEM features are local (height/curvature); none measures multi-canyon collinearity | Resistant hogback strata crossed by streams | [0, +0.002] | Medium; local data ready |
| 5 (blocked) | H27-16 GDR #1391 paleo-geothermal + 2 m probes + Quaternary volcanics | Three official GDR #1391 packages absent locally | Sinter/tufa alignments + shallow thermal anomalies + vent alignments | Direct evidence of fault-focused fluid flow where no trace is mapped | New raw geometries, never in any local detector | Lacustrine tufa; groundwater outflow plumes | [0, +0.006] | **Not viable this session:** official source https://gdr.openei.org/submissions/1391 (DOI 10.15121/1881483, CC-BY-4.0) is outside the sandbox allowlist and bytes are not hash-pinned locally. Named, checked, blocked — per protocol it is not proposed as viable until obtained |

## 3. Frozen H31 protocol (single lane; budget 3 experiments; no post-hoc tuning)

**Lane (one paragraph).** Build the two existing quadrant-OOF surfaces exactly as the frozen
H29 instrument builds them (`scripts/run_h29_holdout.py` helpers: H29 two-stage OOF stage-2;
D0 = base-32 + 15 subsurface transforms OOF), convert each to within-footprint percentile
ranks (mean rank / N, ties averaged), average the ranks 50/50, and emit with the identical
H29-S weighted CELF cover (γ=1.5, min-sep 2.0 px, B2 `d_cat>2 px`, budget 37,654). Nothing
else changes. If the final raster's rank correlation with any registry raster exceeds 0.90 or
>70 % of its dots fall within 3 px of one registry raster (12 pinned peers **plus** GEMSDOE32
R6 `23fbbb51`), it is logged a duplicate and the lane stops.

- **E1 — leakage canary + pre-placement surface screen.** On the union of withheld positives
  for seeds 260–269: direction-invariant univariate ROC-AUC of the ENS surface (and, for the
  record, each component surface); stop if >0.90. Pre-placement Spearman of ENS vs each of
  12 peers + R6 (raw binary and σ=3 density, as H29 E1); stop if max >0.90.
- **E2 — paired blind holdout, seeds 260–269 × 4 quadrants = 40 cells**, buffered scoring
  (`buffered_scoring_mask`, buffer 6 px) primary, unbuffered diagnostic secondary; whole
  fault segments withheld with buffer; visible faults masked pixel-exactly; catalogue-based
  quantities derived only from visible faults (EDT on `sp.known`); identical blind CELF
  emission for all arms. Arms: **ENS** (candidate), **H29S** (primary comparator = current
  repo holdout best), **D0S** (D0 surface through CELF, descriptive ablation).
  **Gate (ALL required):** (a) pooled ENS > H29S and > D0S; (b) mean seed-level paired
  Δ(ENS−H29S) ≥ +0.0010; (c) 10,000-draw seed-bootstrap 95 % CI for Δ(ENS−H29S) excludes 0
  (lower > 0); (d) ≥3/4 folds vs H29S and vs D0S; (e) ≥8/10 seeds vs H29S; (f) E1 passed.
- **E3 — one unique TIFF.** Full-footprint ENS surface from the quadrant-OOF components
  (disclosed: H29-S's shipped file used a dual-partition stitch; H31 uses the single
  quadrant OOF pair that the holdout instrument measures — the file is therefore not a
  re-emission of the shipped H29-S dots). CELF B2 37,654 dots vs the full catalogue;
  all-finite primary (nodata=None, every cell ∈ {0,1} — the "[0, 1]" portal-error fix) +
  NaN twin + single-GeoTIFF ZIP via shared `gems27.submission`; content-hashed name;
  note ≤140 chars. Uniqueness: directed 3-px overlap + Spearman vs 12 peers + R6 gated at
  0.70/0.90; overlaps vs this repo's own rasters reported (operative screen per
  IR-2026-10-25-15). **`ok_to_submit` = E2 gate PASS ∧ uniqueness PASS ∧ validator hard PASS**,
  computed by `gems27.readiness.publication_decision` — no human inspection anywhere.
  If E2 fails, the file is still built (owner requirement: a unique TIFF every session) as a
  **NEGATIVE research artifact labelled ⛔ DO NOT SUBMIT**. Negative results are deliverables.
- **Budget/stop rules.** 3 experiments max. No weight tuning (50/50 frozen), no seed shopping,
  no threshold relaxation. Promotion to a weekly slot remains the owner's separate selector
  step even on PASS. No live score is claimed for any file built here.

## 4. What would change our mind

A PASS means the ensemble beats the repo's best single surface on *catalogue-internal*
hide-and-recover — necessary, not sufficient, for live gain (H29-S: holdout-best, live 0.2190).
The honest live prior even on PASS is "plausibly ≥ H29-S live, beating 0.2778 unproven".
A FAIL retires surface-ensembling of these two detectors and points at H29-3/H31-3 (deconfounding)
or new information (H27-16, blocked on data) as the remaining routes.
