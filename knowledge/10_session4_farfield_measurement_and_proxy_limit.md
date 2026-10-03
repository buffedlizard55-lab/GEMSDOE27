# Session 4 - the far field is measured, the proxy is exhausted, and a bounded live probe is registered

Generated 2026-10-02 (Session 4). Everything here is reproducible from the repository; every external
claim has a row in `registry/sources.json` and every score is owner-reported, never a receipt.

---

## 0. The seven decisions this session produced

| # | Decision | Evidence |
|---|----------|----------|
| 1 | **Do not emit on geologic-map (SGMC) structure that lacks a Quaternary-catalogue counterpart.** Live-refuted, not merely unvalidated. | `evidence/sgmc_gap_inversion.json` |
| 2 | **The catalogue-internal holdout can no longer discriminate improvements that matter.** It is *blind* to the far field, where the live credit is. | `evidence/arm_habitat_decomposition.json` |
| 3 | **Nothing was promoted.** Slots 1-4 are unchanged and re-verified byte-identical (content ids `5512495c6bd1`, `3ebd51534bb1`, `d466b251f309`, `23ad46a4d7ba`). Slot 1 stays the one-click recommendation. | `docs/downloads/manifest.json`, `scripts/verify_downloads.py` (0 failures) |
| 4 | **Slot 5 is a registered measurement probe, not a candidate**: the 0.2477 file with 16.3 % of its far-field dots swapped for the augmented detector's best picks. One variable, same pixel count. | `knowledge/03` Addendum E |
| 5 | **Graph-connectivity value is documentation, not a ranking signal.** Ranking the 345 shipped links by \|dP\| does not beat the z >= 3 rule (refuted). The structural headline survives: closing all 345 candidates moves the network from P = 5.784 to **P = 6.124**, i.e. from inside the paper's critical range (Pc = 5.6-6.0) to above it. | `evidence/link_graph_value.json`, `evidence/addendum_d_gates.json` |
| 6 | **Overlapping en-echelon step-overs are refuted** as a distinct candidate class, even though the forward-cone rule cannot generate them at all (148.8 links/cell, median lateral offset 1.36 km, median along-strike overlap 1.12 km). | `evidence/addendum_d_gates.json` (D-4) |
| 7 | **Multi-scale directional lineament context buys nothing here**: 24 oriented line-integral bands move out-of-fold PR-AUC by +0.001 (needed >= +0.005). Radiometric (+0.0007) and thermal (+0.0005) bands likewise. | `evidence/addendum_d_gates.json` (Stage A) |

---

## 1. D-0: the h18-4 SGMC-gap probe, inverted (`scripts/invert_sgmc_probe.py`)

Session 4 found the group's **21st hash-authenticated (raster, score) pair**, which three sessions of
this repository had not registered: 16GEMSDOE **H18-4**, content id `aef8f42c`,
sha256 `736f62c2da585677ef472cab0f9bc63bd15c50c340beb4a0f4627fafd3d1c853`, owner-reported **0.0360**.
It is the only scored emission in the programme's history whose pixels are *all* >= 300 m from the
catalogue, so its score is a direct live measurement of the far-field/lithological habitat.

**Construction re-verified from the raster bytes** (not from the sibling's description):

| check | value |
|---|---|
| in-footprint positive pixels | **57,783** (matches the sibling's claimed scored count exactly) |
| positives on catalogue pixels | **0** |
| minimum distance to a catalogue pixel | **3.162 px** (>= 3 px, i.e. >= 300 m as claimed) |
| residual 2x2 positive blocks | 34 (0.06 % - "thinned to 1-pixel lines" is true to within 34 blocks) |
| positives on the restored SGMC mask | 79.66 % |

**Instrument check.** The same code reproduces Session 3's published anchors to 5 significant figures:
0.2477 -> credit 5,286.0 / concentration 5.667 / rho 1.429 (published 5286 / 5.67 / 1.43) and
0.1922 -> 6,188.8 / 5.663 / 2.460 (published 6189 / 5.66 / 2.46).

**Inversion** (|G| = 12,225.9 px, the blind-lattice calibration this repo adopted):

| quantity | value |
|---|---|
| c(S), credit per truth pixel if truth were uniform | **0.0384** |
| ... versus a uniform spray of the same 57,783 px | 0.1050 (= c(S) x rho, i.e. N x kernel area / footprint) - so the probe's c(S) is **2.73x BELOW blind** |
| rho (matched mass / credit) | 2.731 |
| credit TPw (uniform closure) | **758.7** |
| exact bracket over MP in [0, N] | 354.7 - 773.7 |
| credit fraction of \|G\| | **0.062** |
| **concentration vs blind** | **1.62x** (exact bracket **0.76x - 1.65x**) |
| best modelled score at its own thinning optimum | 0.0424 at d = 2.25 px (20,090 px) - **5.8x below 0.2477** |

Two things follow, and they point in opposite directions, so both are recorded:

1. **Contiguous lines are geometrically wasteful.** A 1-px line network of 57,783 px covers less DTI
   kernel mass than a uniform spray of the same size (c = 0.0384 vs 0.1050) *and* crowds more
   (rho = 2.73 vs ~1.43 for the dotted 0.2477 file). This is an independent confirmation of why
   dotting beats tracing, from a file built by a completely different route.
2. **Lithological structure without Quaternary expression is nearly blind.** Independently mapped
   bedrock faults > 300 m from the Quaternary catalogue carry ~1.6x the truth density of a uniform
   spray, against 5.3-6.0x for the H19-5 family. The sibling's own exploratory holdout said the same
   thing from the other side: the *union* arm (H16-1 U SGMC-gap) improved dense DTI by +0.0286 while
   the pure gap arm lost -0.0300. SGMC helps only where the catalogue already is.

**The corollary that killed a plausible-sounding idea** (`scripts/sgmc_lidar_response.py` ->
`evidence/sgmc_lidar_response.json`, computed on `lidar:valid` pixels only; the 24.6 % of the footprint
without 1 m LiDAR carries 0 in every descriptor and flattens any pooled statistic):

| population | px with LiDAR | lappos_max | step_max | ex_max | relief |
|---|---|---|---|---|---|
| catalogue pixels | 48,465 | 99.66 | 79.23 | 93.36 | 57.92 |
| SGMC, all | 54,830 | 130.25 | 104.78 | 117.01 | 79.93 |
| **SGMC only, >= 300 m from catalogue** | 40,564 | **136.41** | 111.02 | 122.15 | 84.13 |
| SGMC only, >= 600 m from catalogue | 35,089 | 138.74 | 113.36 | 124.10 | 85.92 |
| random background (200k) | 200,000 | 86.15 | 68.99 | 83.76 | 51.89 |

SGMC-gap pixels show a **1.37x higher** mean 1 m LiDAR scarp response than catalogued fault pixels on
every descriptor - and the emission built from exactly those pixels scored 0.0360, i.e. **1.62x blind**.
Raw scarp-detector intensity therefore does **not** discriminate hidden truth; position relative to the
Quaternary catalogue does. Any future "the geologic map sees scarps the catalogue misses, so emit
there" argument is refuted by a live score, and the refutation is now reproducible from a committed
script rather than a scratch one.

**Far field is not empty.** 81.4 % of the 0.2477 emission's dots are >= 300 m from the catalogue
(median 1.49 km) and that file earns 5.67x blind. So distance from the catalogue is not the problem -
*which* detector chose the pixels is.

---

## 2. Addendum D gates (seeds 140-149, pre-registered and committed before running)

Base arm reproduces Session 3 exactly: mean DTI **0.08894** (was 0.0861), T-v2 marginal efficiency
**0.2503** / paired gain **+0.01221** (was 0.2251 / +0.0115). The instrument did not drift.

**Stage A - out-of-fold PR-AUC against catalogue pixels (criterion 1: >= +0.005 absolute)**

| arm | bands added | PR-AUC | gain | criterion 1 |
|---|---|---|---|---|
| base (32 prepared bands) | 0 | 0.02458 | - | reference |
| + radiometric/extension (`rad`) | 8 | 0.02532 | +0.00074 | FAIL |
| + SGMC (`sgmc`) | 3 | **0.04275** | **+0.01817** | **PASS** |
| + wellspring/vents (`thermal`) | 5 | 0.02510 | +0.00052 | FAIL |
| + directional lineaments (`dir`) | 24 | 0.02559 | +0.00101 | FAIL |
| + all (`all`) | 40 | **0.04635** | **+0.02177** | **PASS** |

**Stage B - paired DTI on 40 cells (criterion 2: mean gain > +0.001 and >= 3/4 folds)**

| arm | mean DTI | mean paired gain | folds improved | criterion 2 |
|---|---|---|---|---|
| `sgmc` | 0.11747 | **+0.02852** | 4/4 | **PASS** |
| `all` | 0.12309 | **+0.03414** | 4/4 | **PASS** |

Both passing arms are driven by the three SGMC bands; the other 37 bands add +0.0036 between them.

**D-3 REFUTED - graph-connectivity ranking carries no truth signal beyond z >= 3.** Pooled efficiency
(credit / false-positive weight, set added alone):

| subset of the 345 T-v2 links | efficiency | mean DTI | dots |
|---|---|---|---|
| top half by \|dP\| (registered) | 0.2914 | 0.0307 | 10,605 |
| bottom half by \|dP\| | 0.2953 | 0.0302 | 10,049 |
| all 345 | 0.2889 | 0.0586 | 20,721 |
| bridges only (339) | 0.2917 | 0.0580 | 20,256 |
| top half by *signed* dP (exploratory) | 0.3054 | 0.0318 | 10,373 |
| top half by second-moment increment (exploratory) | 0.2463 | 0.0292 | 11,609 |
| 5 random same-size halves | 0.2791 - 0.3117 | - | - |

The registered gate needed top-half >= 1.15x all-links **and** above the random 95th percentile
(0.3117). It achieved 1.008x and sat *inside* the random spread; the bottom half scored marginally
better than the top. Berkowitz-style connectivity value tells a geologist which closures matter to the
network (section 5) but does not predict where hidden catalogue truth is.

**D-4 REFUTED - overlapping en-echelon step-overs.** This is a class the forward-cone rule cannot
generate at all (Session 1: "overlapping offsets were never generated"), and it is now implemented
(`src/gems27/newinfo.steppover_links`): 148.8 links/cell, median lateral offset 13.6 px (1.36 km),
median along-strike overlap 11.2 px (1.12 km), median strike difference 8.1 deg, median gap 1.13 km.
Pooled efficiency **0.0605**, *below* the break-even m(0.30) = 0.0638, and only **1.11x** the
perpendicular-strike control (0.0545; needed >= 2.0x). Adding them to the base still gives +0.0022
paired DTI in 4/4 folds - real but 5.5x weaker than T-v2's +0.0122 at a quarter of the efficiency.
Not promoted. *Caveat recorded:* the control finds only 3.75 links/cell, so the enrichment ratio is
measured against a small sample; the absolute efficiency (below break-even) does not depend on it.

---

## 3. The proxy's resolution limit (`scripts/diagnose_arm_habitats.py`)

Hidden truth in every gate this programme has ever run is **catalogue pixels held out of the
detector's view**. Decomposing the same 40 cells by distance from the *full published* catalogue:

* truth: **120,983 px, 100 % at distance 0** from the published catalogue. Habitat A (>= 300 m) has
  **zero** truth, by construction.
* base arm credit by band: 36.8 % on the catalogue spine itself, 51.5 % at 100 m, 11.4 % at 200 m,
  0.37 % at 300 m-1 km, **0.0 % beyond 1 km**.
* `sgmc` arm: same shape, more dots near the spine (4,906 vs 3,799 on it; 71,070 vs 52,959 at 100 m;
  34,015 vs 25,711 at 200 m) at slightly *lower* per-band efficiency (0.2753 vs 0.2806 at 100 m).
  Its whole +0.0285 gain is catalogue proximity.

So the proxy rewards "predict which catalogue pixels were hidden", while the live metric pays for
"find faults nobody has mapped". The two are not opposites - the 0.2477 file proves a
catalogue-trained detector reaches 5.67x blind - but **the marginal increments this repository
measures live entirely in a band (<= 200 m from the published catalogue) that a real submission can
only partly occupy**: pixels *on* the spine are forbidden (`verify_downloads.py`), and pixels within
100-300 m of *known* catalogue were measured by H27-4 at efficiency **0.0034**, ~15x below break-even.
The apparent contradiction with the 0.281 efficiency of the 100 m band resolves cleanly: that band is
the union of "near known catalogue" (worthless) and "near hidden catalogue" (worth a lot in the proxy,
unidentifiable at prediction time).

**Consequence for the two passing arms.** They pass both registered criteria, and they are still not
promoted, for a reason that is now measured rather than argued: their gain lives in the habitat the
proxy over-rewards, and the one thing about them that could transfer - better far-field placement - is
exactly what the proxy cannot see and what the h18-4 live probe measured at 1.62x blind for
SGMC-selected positions. Promoting them would spend a slot on an unmeasured claim, which the standing
rules forbid.

---

## 4. Addendum E: the Slot-5 far-field swap probe (registered before it was built)

Because no gate on this proxy can decide the question, it is registered as a **bounded live
measurement** (full text and interpretation rule in `knowledge/03`, Addendum E):

* Fit the augmented detector (32 prepared + 40 Addendum-D bands = 72 label-free features) on **all**
  published labels - at submission time nothing is held out.
* Split the owner-reported 0.2477 file into near-field (< 300 m from catalogue, 18.6 %) and far-field
  (>= 300 m, 81.4 %).
* Remove the 20 % of far-field dots with the lowest augmented probability (9,783 px) and add that
  detector's 9,783 highest-probability far-field ridge dots (>= 3 px from catalogue, >= 1.5 px from
  every kept dot, inside the footprint, off-catalogue).
* Everything else is byte-identical: near field, total count (60,069 px), geometry, nodata, CRS, grid.
  A live comparison against 0.2477 differs in **one** variable: which far-field pixels are emitted.
* Registered rule: >= 0.2507 adopt the detector; 0.2447-0.2507 no measurable far-field information;
  <= 0.2447 refuted.
* Declared downside, owned: if the detector has no far-field information this randomises 16.3 % of the
  best file's dots and should cost ~0.003-0.008. Slot 5 is labelled `MEASUREMENT PROBE - NOT THE
  RECOMMENDED SUBMISSION` everywhere; **Slot 1 remains the one-click file**.

---

## 5. What the graph argument now says (`src/gems27/graph_value.py`)

Every one of the 345 shipped candidates carries its network consequence in
`registry/topology_candidates.json`, `docs/data/topology_links.csv`/`.geojson`, `docs/topology.html`
and `evidence/link_graph_value.json`:

* **P = 5.784 (catalogue alone) -> 6.124 (all 345 candidates closed)**, against Berkowitz et al.
  (2000) Pc = 5.6-6.0. The candidate set is precisely the set of closures that moves this network from
  *inside* the critical range to *above* it. P is computed with this repo's own closed form and
  reproduces the published value 5.784491473419016 to 15 digits; 4 unit tests cover the quantum, the
  bridge and redundant cases, and the rank ordering.
* **339 of 345 links are bridges** - only 6 are redundant with another candidate.
* Largest-system share of mapped fault length rises to 0.00774; the largest system goes 42.3 -> 57.5 km
  and the system count 3,199 -> 2,857 (Session 2).
* sum(l^2) over systems = 56,580 km^2 (1.095 per unit footprint area). **No critical value is claimed
  for it**: a threshold could not be verified from an official source inside this sandbox, so it is
  used only as a continuous relative measure and as the tie-break inside equal \|dP\|.
* **dP is quantised** to {-1, 0, +1} x P/n_ge because it counts systems above lmin = 2 km: 159 of 345
  links have dP != 0, and a link joining two systems that are *both* already >= 2 km has dP < 0
  (fewer long traces at the same total length). Disclosed before Stage B ran, together with the
  `det_local_relief` anisotropy definition fix (that layer is signed: min -207.7, max +299.4, 64.7 %
  negative, 3,061 NaN).

---

## 6. Irregularities found this session (all in `registry/irregularities.json`)

1. `h18-4-score-unregistered` - the group's most informative live measurement was invisible to this
   repository for three sessions.
2. `sgmc-px-count-discrepancy` - sibling exploratory reports 110,732 SGMC fault px in the footprint;
   our restored mask has 83,593; the probe's own positives overlap our mask on 79.66 %. Rasterisation
   or buffer difference; unresolved, and it does not affect the inversion (which reads the scored
   raster's bytes).
3. `restore-part-truncation-bug` - **fixed**: `scripts/restore_data.py` now removes stale `.part`
   files, retries, verifies every download against GitHub's own byte count, and deletes a corrupt
   assembled file (plus its parts) instead of leaving it where the next run would trust it.
4. `proxy-blind-to-far-field` - section 3; the standing caveat "catalogue-internal truth overstates
   real-world enrichment" now has numbers attached.
5. `det-local-relief-signed-with-nan` - a prepared-matrix band described as "local relief" is signed
   (64.7 % negative) and carries 3,061 NaN; the `lidar_*` columns carry 24.63 % NaN (not 0).
6. `d4-control-underpowered` - the perpendicular-strike control finds 3.75 links/cell vs 148.8.
7. `scratch-lidar-auc-artifact` - a Session-4 screening script computed LiDAR descriptor statistics
   over all footprint pixels, pushing an SGMC-vs-background AUC to 0.4831 although the means clearly
   favour SGMC (136.4 vs 86.2). The repository's published `evidence/channel_auc.json` is **not**
   affected: `scripts/channel_auc.py` maps 0 -> NaN for every uint8 layer and drops non-finite values
   on both sides (`lidar:lappos_max` n_pos = 48,441 of 60,988). Verified, not assumed.
8. `second-moment-threshold-unverified` - no official source reachable from this sandbox states a
   critical value for sum(l^2)/area; used only as a relative measure.

---

## 7. What would actually move the score, in order

Session 3 proved the arithmetic: 0.3195 needs 0.570 x |G| of credit at 60,069 px, i.e. retention
~= 1.0 at ~44k px **or** concentration above ~5.7x blind, and the whole H19-5/h19-4/h16-1 family
plateaus at 5.3-5.7x. Session 4 adds the reason why no amount of further gating here will find it:
the proxy cannot see the habitat that pays.

1. **Spend Slot 5** (the Addendum-E probe). It is the only experiment that can tell the programme
   whether detector work can pay at all. Cost: one of ~27 remaining weekly slots.
2. **Get the layers this sandbox cannot reach, after resolving the runner failure.**
   `.github/workflows/fetch-gdr-external-layers.yml` + `scripts/fetch_external_layers.py` are
   implemented to download, hash-verify against the 2026-09-30 pins, inventory and footprint-clip
   three official GDR 1391 files no detector here has used: paleo-geothermal (84,008 B,
   `faffcf69...`), INGENIOUS 2 m temperature probes (1,080,530 B, `1301f70d...`) and Great Basin
   Quaternary volcanics (9,898,770 B, `c4a2d2df...`). However, this checkout's Actions runs
   37099986237, 37100053264, 37100608786, and 37100751573 concluded failure with zero jobs and no logs, so there was no local
   fetch, checksum verification, clipping, or artifact. The older sibling-runner pin record is
   provenance only; it does not put bytes in this checkout. The workflow also contains HEAD-checks
   for larger sources. A repository maintainer must investigate why the runs created no jobs, or
   provide official bytes; the available run records do not establish the cause. Do not infer source
   unavailability from the empty runs.
3. **Ask the owner for one live measurement of a far-field-only variant of the *current* best
   detector** if Slot 5 is inconclusive: the far field is 81.4 % of the emission and no probe in the
   programme has ever isolated it.
4. **A supervised deep model on 1 m 3DEP tiles** (FaultSEG-style; Hermant et al. 2025 report PR-AUC
   0.595 vs siUNET 0.449) remains the only route with a published, order-of-magnitude better
   detector - and it needs a GPU and the 716-tile download, neither available here.

Everything else - emission geometry, thinning distance, coverage-optimal selection, ensembling,
habitat tomography, SGMC-gap emission, connectivity ranking, step-over links, directional lineament
features, radiometric and thermal features - has now been measured and is closed.
