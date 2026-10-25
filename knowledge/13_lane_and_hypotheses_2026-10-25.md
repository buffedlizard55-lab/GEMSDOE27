# Lane declaration + 5 candidate hypotheses, ranked (2026-10-25) — written BEFORE implementation

**Irregularity IR-2026-10-25-01 (flagged, `registry/irregularities.json`):** the PARALLEL-RUN
PROTOCOL says "Your lane is the single method paragraph below", but the prompt as received
contains no delimited single method paragraph. Rather than guess silently, this session
DECLARES its lane explicitly (§1), stays inside it, and enforces the protocol's numeric
uniqueness tests (surface Spearman < 0.90 and < 70 % of final dots within 3 px Euclidean of
any single registry raster, checked on the surface before placement AND on final dots).
Registry = the five fetched top files (0.2600 d2.8, 0.2632 h33d, 0.2708 r1-solo, 0.2750 PINN,
0.2778 B2) + this repo's six shipped candidates. All scores OWNER-REPORTED (no receipts seen).

## 1. LANE L-2026-10-25 (the single method paragraph for this session)

> **Buried-fault subsurface detector.** A spatially-blocked out-of-fold gradient-boosted
> detector fed ONLY subsurface-physics features — multiscale potential-field edges
> (RTP magnetic + isostatic gravity: gradient magnitude, tilt/analytic-signal ridges,
> cross-field orientation coherence), geodetic strain invariants and their gradient
> corridors, conductivity and depth-to-basement step edges, and directional
> seismicity-fabric persistence — with every lidar-scarp/topography band and every
> catalogue-distance feature excluded by construction. Emission is priority-ordered
> (descending probability) Poisson-disk placement at ≥2.8 px spacing on the detector's
> 1-px ridges, B2 catalogue exclusion (no dot within 200 m of a visible fault), fixed
> 38,000-dot budget. Validation is hide-and-recover of whole catalogue segments with a
> 600 m buffer, visible faults masked pixel-exactly, pooled DTI (α=0.2, β=0.8, 300 m
> triangular kernel, evaluator `gems27.metric` v1). Nothing outside this paragraph is
> in-lane for this session; a hybrid arm appears in the holdout ONLY as a labelled
> control to price the lidar exclusion, never as the shipped file.

## 2. Five untried hypotheses (none implemented in this repo; checked vs `knowledge/02`,
`knowledge/07`, `registry/hypotheses.json`, `registry/next_hypotheses.json`)

| # | Hypothesis | Layers | Physical signature targeted | Why it catches a catalogue-missing fault | Differs from repo because | Expected ΔDTI (prior, live) | Cost |
|---|---|---|---|---|---|---|---|
| H-A ★LANE | Subsurface-only sufficiency: potential-field + strain + conductivity + seismicity detector, lidar excluded | `rtp, tmi_hg/vg, iso_grav_anom(+hg/vg/slope), geod_*, cond_surf, depth_to_base_surf, deq/ieq_n100a15` (prepared stack, hash-pinned) | Tilt-angle zero-crossing ridges + cross-field edge coherence at σ=2,5,10 px; strain-corridor × conductivity-gradient product; basement-step edges; seismicity structure-tensor coherence | Q-fault catalogue scope requires young surface rupture; buried/older faults juxtapose magnetic/density units and localise strain/fluids without a scarp | Repo detectors always include lidar bands; H28-1 added edges ON TOP of lidar. Exclusion-as-hypothesis + priority thinning + B2-direct emission is untested | −0.01…+0.03 (wide; holdout expected to UNDERESTIMATE, see §3) | Low–med (features exist; transforms new) |
| H-B | Dip-offset doublet: score pixels where a potential-field edge runs parallel to, and 200–600 m from, a lidar scarp ridge (hanging-wall offset of a dipping blind fault) | RTP/gravity edges × lidar `step_max/lappos_max` ridges + offset-direction consistency | Paired parallel lineaments at fixed offset = surface trace + subsurface edge of ONE dipping fault | Catalogue maps the surface trace where seen; the offset edge continues where the scarp dies under alluvium | No cross-layer offset-pairing anywhere in repo/siblings' documented methods | 0…+0.015 | Med |
| H-C | Radiometric alteration fronts: K/Th ratio + total-count *edges* (not values) as hydrothermal-upflow markers | GeoDAWN radiometric u8 stack (`geodawn_rad_u8.tif`, restored) | Ratio-gradient ridges; K-enrichment fronts along permeable fault zones | Fault-hosted fluid flow alters bedrock along structures too old/buried for the Q catalogue; GEMSDOE46's scarp×radiometric fusion scored 0.1589 with values — edges untested | Repo tested radiometric ratios as detector VALUES (+0.0007 PR-AUC, refuted); edge/front geometry untested | 0…+0.008 | Low |
| H-D | Monte Cristo Range 2020 M6.5 rupture as labelled "new-fault" training exemplar (transfer) | Published MCRE surface-rupture mapping (Koehler et al. 2021, SRL 92(2A):823–829; USGS Pubs Warehouse 70217872) + prepared stack | Train detector to recover a fault that WAS missing pre-2020, measure which bands see it, transfer weights | The one ground-truth case in-region of a seismogenic fault absent from pre-event mapping | No event-based exemplar training in repo. **Data gate:** rupture vectors must be fetched from an official source and hash-pinned first; NOT obtainable from this sandbox's allowlist → deferred, named source: USGS Publications Warehouse / NBMG MCRE data page | Unknown (methodological) | High (blocked) |
| H-E | Quaternary volcanic vent-alignment corridors | GDR 1391 vents (21 pts in footprint, local) + GEMSDOE30's `derived_gdr_volcanics_100m_u8.tif` (fetchable via gh, must hash-verify vs GEMSDOE30 records) | Vent-to-vent alignment density (Hough/RANSAC lines through ≥3 vents) × volcanic-unit boundary edges | Dikes exploit fault permeability; alignments mark structures with no surface rupture | Repo holds vent POINTS only, never used as alignments; H27-12 refuted point-distance features, not alignment geometry | 0…+0.006 | Med |

Ranking rule: expected live ΔDTI × P(holdout can falsify) ÷ cost. **Order: H-A > H-B > H-C > H-E > H-D**
(H-D highest scientific value but data-blocked this session — not viable until fetched+hashed).

## 3. Pre-registered gate for H-A (frozen before any run)

* Holdout: quadrant folds (existing `make_quadrant_folds`), whole 8-connected catalogue
  segments hidden at 20 % per quadrant, seeds **200–204** (unused: repo history used
  130–159), 600 m buffer ring around each test quadrant excluded from training; hidden
  segments' buffer excluded from scoring; B2 mask and any catalogue-derived quantity from
  VISIBLE faults only; visible faults masked pixel-exactly (`known=` in metric).
* Arms, matched per-fold dot budget (38,000 × fold footprint share):
  **A** = lane (subsurface-only), **B** = full-32 incumbent detector (control),
  **D** = full-32 + lane transforms (labelled control, never shipped).
* Canary first: each new transform alone, pooled AUC vs hidden segments; AUC > 0.90 stops
  the line as leakage until explained.
* Known bias, declared: catalogue-internal truth favours lidar (truth segments HAVE scarps).
  H-A is therefore gated on **pooled ΔDTI(A−B) > −0.01 AND A beats a same-budget random-
  ridge control by > 0.05 AND uniqueness passes** for a "promote as exploratory" verdict;
  ΔDTI(A−B) > 0 is required for a clean "promote". Any live claim is forbidden; the run
  card reports HOLDOUT-DTI + 95 % CI + n withheld positives only.
* Budget: ≤3 experiments total (E1 canary, E2 holdout, E3 final build), then stop.
