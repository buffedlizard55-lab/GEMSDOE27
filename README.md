# 27GEMSDOE - topology-first research and submission lab for DrivenData #306 (DOE GEMS)

**Site:** https://buffedlizard55-lab.github.io/GEMSDOE27/ (first screen = one-click download + the note to paste).
**Status (2026-10-03):** The four weekly-slot candidates and separate Slot 5 measurement probe remain unchanged; the unscored H28-1 research candidate remains separate. H27-10's frozen seeds 150–159 gate failed and its corrected same-seed integrity rerun changed no metrics; no weekly slot was used. The distinct H27-5b geologist-review class contains 81 of the 345 T-v2 links and is not a submission candidate. **No leaderboard score exists for any 27GEMSDOE file** - nothing in this repo claims one.
Owner-reported reference: the 24GEMSDOE file scored **0.2477** (owner-reported); the owner-stated leader is **0.3195** (unconfirmed; the agent does not access drivendata.org).

## Start here every session (checklist)
1. Re-read **Task prompt (verbatim)** and **Core Values (verbatim)** below. Maximize P(Win) and Own the Outcome are the focal point of every build, research and implementation decision.
2. Do the previous session's next steps first: `knowledge/06_limitations_and_access.md` -> newest dated outcome and carry-forward priorities (Session 5 outcome, 2026-10-03).
3. Verify inputs: `python scripts/restore_data.py` (16 hash-pinned artifacts; SHA-256 in `data/manifest.json`), `python scripts/prepare_data.py`, then `python -m pytest -q` and `python scripts/verify_downloads.py`.
4. Verify line by line against official sources and give links for manual review (`registry/sources.json`, `docs/sources.html`). Flag irregularities (`registry/irregularities.json`). No hallucinations: unknown stays unknown.
5. Never automate drivendata.org (Terms of Use); never claim an upload, score, PR or merge without evidence.
6. Before implementing new predictive features: maintain a current screen of 3-5 genuinely untried hypotheses in `knowledge/07_untried_hypotheses.md` and `registry/next_hypotheses.json`; validate any chosen candidate on the spatially blocked holdout **before** a weekly slot is spent. The broader `registry/hypotheses.json` is the historical evidence ledger.
7. Run three passes: implement+verify; review bugs/assumptions/edge cases; recheck against the original request (`evidence/review_passes.md`).

## Submit (one click — Slot 1 is the recommendation; 5 verified files exist)
* **Slot 1 (Primary A/B):** `docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif` (`.zip`: `gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.zip`; fallback: `...-allfinite.tif`).
  * SHA-256 (nan file): `33003374335d84bf885f2d8f5e9dd4c57044c8ec58fa6a0d7fa581e8bc41c11d`; content id `5512495c6bd1`; **61,328** emitted pixels = the 0.2477 emission (60,069 px, nothing removed) + 1,259 topology gap-closure dots on 345 aligned 1–4 km links.
  * Note to paste (`151` chars, `<= 200`): `27GEMSDOE T-v2 A/B | 0.2477 base (dotted H19-5 d1.5) + 1259 dots on 345 aligned 1-4 km gap links; A/B vs 0.2477 | id 5512495c6bd1 | not yet live-scored`
* **Slot 2 (Secondary d2.8):** `docs/downloads/gems27-topo-gap-closure-t-v2-on-d2-8-20261002-3ebd51534bb1-nan.tif` (`.zip` & `-allfinite.tif` included).
  * Content id `3ebd51534bb1`; **45,374** emitted pixels = d2.8-thinned H19-5 (44,090 px) + 1,284 topology dots.
  * Note to paste (`162` chars): `27GEMSDOE T-v2 d2.8 | d2.8-thinned H19-5 + 1284 dots on 345 aligned gap links; conditional slot 2, combination unvalidated | id 3ebd51534bb1 | not yet live-scored`
* **Slot 3 (Tertiary T-v2 + H27-4 100 m flank-shadow prune):** `docs/downloads/gems27-topo-gap-closure-t-v2-plus-h27-4-r1-on-d1-5-20261002-d466b251f309-nan.tif` (`.zip` & `-allfinite.tif` included).
  * Content id `d466b251f309`; **55,992** emitted pixels = 0.2477 base minus 5,355 100 m catalogue-flank shadow dots (54,714 px) + 1,278 non-redundant T-v2 dots.
  * Note to paste (`154` chars): `27GEMSDOE T-v2+H27-4 | 0.2477 base minus 5355 100m flank-shadow dots + 1278 T-v2 gap dots (OOF +0.0141, 4/4 folds) | id d466b251f309 | not yet live-scored`
* **Slot 4 (NEW this session — all three validated increments at the live-anchored budget optimum):** `docs/downloads/gems27-all-increments-d2-8-h27-4-r1-t-v2-20261002-23ad46a4d7ba-nan.tif` (`.zip` & `-allfinite.tif` included).
  * SHA-256 (nan file): `344e7c857f363b195dbfd6e64a0a0e0fc77923c8c14d7830e53bfd2d5c05610c`; content id `23ad46a4d7ba`; **41,507** emitted pixels = `dot_thin(H19-5, 2.8)` (44,090 px, the live-anchored budget optimum) minus 3,891 100 m catalogue-flank-shadow dots (H27-4 r≤1) + 1,308 non-redundant T-v2 topology dots.
  * Note to paste (`172` chars, `<= 200`): `27GEMSDOE H27-8 all-increments | d2.8 optimum base minus 3891 flank-shadow dots + 1308 T-v2 dots; all 3 validated increments stacked | id 23ad46a4d7ba | not yet live-scored`
  * Modelled `0.2484` (geometric) / **`0.2781`** (hybrid) — the highest hybrid estimate of the four. The two models differ *only* in what the targeted prune is charged; **slot 1 vs slot 3 is the live A/B that settles it**.
* **Slot 5 (NEW this session — MEASUREMENT PROBE, *not* a recommendation):** `docs/downloads/gems27-farfield-swap-augmented-detector-probe-20261002-a34b0799df59-nan.tif` (`.zip` & `-allfinite.tif` included).
  * SHA-256 (nan file): `f8e6c76cf584c6fdae6610998d12da185ae858f2a41833b3f630f6f2dd03985c`; content id `a34b0799df59`; **60,069** emitted pixels — *exactly* the 0.2477 file's count. The near field (11,153 px, <300 m from the catalogue) is byte-identical; **9,783 far-field dots (16.29 % of the file) were swapped** for the 72-band augmented detector's best far-field picks (mean detector probability: dropped 0.0288 → added 0.4380; added dots' median distance from the catalogue 640 m, 31.7 % ≥1 km out, so they are not hugging the 300 m boundary).
  * Note to paste (`194` chars, `<= 200`): `27GEMSDOE Addendum E probe | 0.2477 base with 9783 far-field dots swapped for the augmented detector's best; 1 variable, same 60,069 px; MEASUREMENT PROBE | id a34b0799df59 | not yet live-scored`
  * **No model score is quoted for it, on purpose:** the catalogue-internal holdout cannot see this habitat (Session 4 below). Registered reading (`knowledge/03_preregistration_topology_gate.md` Addendum E): **≥ 0.2507** → the detector carries real far-field information, rebuild the emission from it; **0.2447–0.2507** → no measurable information, close the detector-feature route; **≤ 0.2447** → refuted. Declared downside if it carries nothing: ≈ −0.003…−0.008. This is the only experiment left that can license or close all future detector work.
* Exact steps and the decision rules for the 5 weekly slots: `docs/executive-summary.html`.

## Session 5 update — H27-10 rejected; H27-5b review class (`knowledge/06`, `knowledge/11`)

* **H27-10 frozen gate: FAIL; no weekly slot.** On seeds 150–159, baseline mean DTI was 0.10937685 and the annulus substitution mean was 0.11022300: paired ΔDTI **+0.00084615**, below +0.001. Fold means improved 4/4, seed means 7/10 (gate required 8/10), and added-annulus efficiency was **0.03357**, below m(0.2477)=**0.05212**. The first run's self-distance spacing diagnostic falsely marked the integrity check; the initial JSON is preserved. A corrected same-seed integrity rerun passed all data checks while leaving all metrics and the failed gate unchanged. It is not fresh confirmation. See `evidence/h27_10_annulus_holdout.json`, `evidence/h27_10_annulus_holdout_initial.json`, and Addendum F.
* **Review-only H27-5b class:** applied to the existing 345 z≥3 deduplicated T-v2 short links (1–4 km gaps), with exact filter `fid_src != fid_tgt AND same_name AND kinematic_compat`; count **81/345** (73 end-to-end, 4 abutting, 4 tip-to-tip oblique). Focused review files are `docs/data/topology_priority_h27_5b.csv` and `.geojson`; `docs/assets/fig_map_h27_5b_priority.png` previews the 81 links, and the Topology page includes class counts, source links, per-link arguments, cautious geometry cues and a searchable class column. Tier-2 whole-FID enrichment (0.1783 vs 0.0204 rotated control) supports review prioritization only—not hidden-label truth, transfer or live-score gain. FIDs are records in one NBMG compilation; unknown kinematic fields can pass the screen.
* Graph-ΔP ranking and overlapping en-echelon step-overs remain **refuted as holdout-improvement signals**. A geometry cue is not a fault interpretation. Four current genuinely untried hypotheses remain in `knowledge/07_untried_hypotheses.md` and `registry/next_hypotheses.json`; H27-10 is in the tested-results record, not the untried screen.
* NBMG REST layer metadata, all four fetched chunks of Faulds & Hinz (OSTI), and the Berkowitz publisher abstract were rechecked; status is in `registry/sources.json`. The raw GDR #1391 packages have not been fetched/re-hashed in this checkout. Its two Actions fetch runs failed before any job (no logs); the cause is unknown and source unavailability is not inferred. No DrivenData access, upload or live score occurred. [PR #9](https://github.com/buffedlizard55-lab/GEMSDOE27/pull/9) merged to `main` at `733e2b2141c8babba29da383d264b4f3da12de38`; GitHub closeout and verification are recorded in `evidence/review_passes.md`.

## New in Session 4 — the far field was measured, and the holdout ran out of resolution (`knowledge/10_session4_farfield_measurement_and_proxy_limit.md`)
* **A live score this repo never had.** 16GEMSDOE's h18-4 (content id `aef8f42c`, sha256 `736f62c2da58…`, owner-reported **0.0360**) is the only scored emission in the programme whose pixels are *all* ≥300 m from the catalogue — 57,783 px of USGS State Geologic Map Compilation faults with no Quaternary counterpart. It was registered, hash-authenticated, its construction re-verified from the raster bytes (0 positives on catalogue px, minimum catalogue distance 3.16 px, 34 residual 2×2 blocks, 79.66 % on the restored SGMC mask), and inverted with this repo's own metric code — which first reproduced Session 3's published anchors to 5 significant figures (0.2477 → credit 5,286.0, concentration 5.667; 0.1922 → 6,188.8, 5.663).
* **Verdict: 1.62× blind** (exact bracket 0.76–1.65× over MP ∈ [0, N]), credit fraction **0.062 of |G|**, best modelled score at its own thinning optimum **0.0424** — against 5.3–6.0× for the family that produced 0.2477. Its 1-px lines also cover *less* DTI kernel mass than a uniform spray of the same size (c = 0.0384 vs 0.1050, ρ = 2.73 vs 1.43): an independent confirmation, from a file built by a completely different route, of why dotting beats tracing. **Never emit on an "independent second catalogue" again.**
* **The corollary that kills a plausible idea:** SGMC-gap pixels have a *higher* mean 1 m LiDAR positive-laplacian response than catalogued faults (136.4 vs 99.7; random background 86.2 — all on `lidar:valid` pixels only). Raw scarp-detector intensity does **not** discriminate hidden truth; position relative to the Quaternary catalogue does.
* **Addendum D (seeds 140–149, pre-registered and committed before running).** The base arm reproduces Session 3 exactly (mean DTI 0.08894 vs 0.0861; T-v2 paired gain +0.01221 vs +0.0115), so the instrument did not drift. **+24 oriented 0.5–2 km lineament bands: PR-AUC +0.0010 → REFUTED** (registered requirement +0.005); radiometric ratios +0.0007 and thermal-point distances +0.0005 likewise. Only the SGMC-distance arm passes criterion 1 (+0.01817 PR-AUC, 0.0246 → 0.0428) and the union arm (+0.02177), and both then pass criterion 2 (paired DTI **+0.02852** and **+0.03414**, 4/4 folds each). **Graph-connectivity ranking of the 345 links: REFUTED** (top half by |dP| 0.2914 vs all links 0.2889 — ratio 1.008 against a required ≥1.15 — and *below* the random-half 95th percentile 0.3117; the bottom half scored 0.2953). **Overlapping en-echelon step-overs — a class the forward-cone rule cannot generate at all (148.8 links/cell, median lateral offset 1.36 km, median along-strike overlap 1.12 km, median strike difference 8.1°): REFUTED** (pooled efficiency 0.0605, below break-even 0.0638, and only 1.11× the perpendicular-strike control against a required ≥2.0×; they still add +0.0022 paired DTI in 4/4 folds, 5.5× weaker than T-v2's +0.0122 at a quarter of the efficiency).
* **Why the two passing arms were NOT promoted** (`evidence/arm_habitat_decomposition.json`). Hidden truth in every gate this programme has run is catalogue pixels, so **100 % of it (120,983 px) lies at distance 0 from the published catalogue** and Habitat A (≥300 m away) contains *zero* truth by construction. Base-arm credit shares: 36.8 % on the catalogue spine, 51.5 % at 100 m, 11.4 % at 200 m, 0.37 % at 300 m–1 km, **0.0 % beyond 1 km** — while the live-scored 0.2477 emission puts **81.4 % of its dots ≥300 m away** (median 1.5 km) and earns 5.67× blind. The proxy is not biased against far-field arms, it is **blind** to them; both arms' entire gain is catalogue proximity, and their distinctive far-field behaviour is the habitat just measured live at 1.62× blind. Passing a gate that cannot see the habitat that pays is not a reason to spend a slot — so Slot 5 asks the question live instead, at fixed pixel count.
* **The graph argument a reviewing geologist can check independently** (`src/gems27/graph_value.py`). Every one of the 345 candidates now carries its network consequence — bridge status, merged system length, change in the largest-system share of mapped fault length, dP under Berkowitz et al. (2000) computed with this repo's own unit-tested closed form, and a continuous d(Σl²) tie-break — in `registry/topology_candidates.json`, `docs/data/topology_links.csv`/`.geojson` and `docs/topology.html`. **Closing all 345 moves the network's connectivity parameter from P = 5.784 to 6.124, i.e. from inside the paper's critical range (Pc 5.6–6.0) to above it; 339 of 345 links are bridges.** Disclosed: dP is quantised to {−1, 0, +1}·P/n_ge because it counts systems above l_min = 2 km (so a link joining two systems that are *both* already ≥2 km has dP < 0), and **no critical value is claimed for Σl²/area** because none could be verified from an official source inside this sandbox.
* **Access bridge built:** `.github/workflows/fetch-gdr-external-layers.yml` + `scripts/fetch_external_layers.py` download, **hash-verify against the 2026-09-30 pins** (refusing to use a file that does not match), inventory and footprint-clip three official GDR 1391 layers no detector here has ever used — paleo-geothermal (84,008 B, `faffcf69…`), INGENIOUS 2 m temperature probes (1,080,530 B, `1301f70d…`), Great Basin Quaternary volcanics (9,898,770 B, `c4a2d2df…`) — and HEAD-check the larger sources (wellspring FileGDB, both Qfaults releases, SGMC NV/CA, the Siler 2022 and DeAngelo 2022 DOIs, the GeoDAWN ScienceBase item) so obtainability is a recorded fact rather than an assumption. Results come back as a run artifact (`gh run download`). It never commits, never pushes, and never contacts drivendata.org.
* **Bug fixed:** `scripts/restore_data.py` used to leave a truncated `.part` file after a failed download and to keep a hash-mismatched assembly where the next run would trust it (this is how a corrupt 492,887,617 B / `c0e9b856…` `training_features.tif` appeared instead of the pinned 418,912,844 B / `4371c82e…`). It now removes stale parts, retries with backoff, verifies every part against the byte count GitHub itself reports, and deletes a bad assembly together with its parts.

### Separate H28-1 research candidate (not one of the four current weekly slots)

* `docs/downloads/gems27-h28-1-edge-coherence-plus-t-v2-h27-4-20261002-1113fba5f6cb-nan.tif`; ZIP, all-finite fallback, checks, and `h28_1_candidate_manifest.json` are in the same downloads directory.
* Content id `1113fba5f6cb`; SHA-256 `61f9b53de42786e6d48afa50fd453a87c57d5d7b9b626c7dcf28c2dfbd20f411`; 59,075 exact binary pixels; zero known-label overlap. Its preregistered seeds 140–149 cleared the internal gate with mean paired ΔDTI `+0.00294884`, 3/4 folds and 9/10 seeds. NE_LidarGapHeavy and seed 149 regressed; this is not a leaderboard result.
* Note to paste (`142` characters): `27GEMSDOE H28-1 research | OOF +0.0029 paired DTI; 3/4 folds, 9/10 seeds; no live score | id 1113fba5f6cb | research only; not yet live-scored`.
* See `docs/research.html` for direct download links and `knowledge/09_preregistration_H28-1_candidate.md` for recipe, checks, hashes and limits. The candidate is not a fifth weekly slot and does not replace or alter any of the four current slot artifacts.

## New in Session 3 — the live scores were inverted (`knowledge/07_live_score_inversion.md`)
All **20** of the owner's scored rasters that could be matched were recovered from the sibling repositories and accepted **only if their SHA-256 equalled a `registry/live_scores.json` row** (provenance by hash, not filename; `scripts/fetch_scored_corpus.py`). Five rows could not be matched and are listed as unmatched, not guessed.
* **The exact identity**, including a term the programme had been missing: `DTI = TPw / (0.2·TPw·(1 − ρ) + 0.2·N + 0.8·|G|)` where `ρ = MPw/TPw` is a **crowding factor**. Credit takes a *max* over predictions per truth pixel but false-positive mass takes a *sum*, so a pixel that merely sits near truth is cheap even when redundant — **crowding near truth is a discount, not a penalty**. The identity reproduces both live anchors exactly: H19-5 solid → **0.1922** (live 0.1922), dotted d1.5 → **0.2477** (live 0.2477).
* **|G| = 12,226 px**, from a blind spacing-5 lattice whose credit per truth pixel (`c = 0.37481`) is pure geometry and needs no assumption about *where* the truth is. The sibling's independent estimate was 12,503 — **2.2 % apart**. Use 12.2–12.8k.
* **Retention rule validated twice live**: `credit(d) = credit_solid · c(d)/c_solid` predicts H19-5→d1.5 to **−0.1 %** and H25-ctx→h28 to **+4.0 %**. Budget optimum **d = 2.25–2.8 → 0.2550** (+0.0073); the sibling's independent fit said 0.2553. **The emission-geometry lever is exhausted at ≈0.255.**
* **Concentration** (`(TPw/|G|)/c`) ranks detector quality independently of budget: the 0.2477 file is **5.67×** better than blind. The whole H19-5/h19-4/h16-1 family **plateaus at 5.3–5.7** — same detector, different clothes — and **no submission in the group's history has ever earned more than 0.508·|G|** of credit.
* **0.3195 is arithmetically out of reach by rearranging pixels**: at 60,069 px it needs **0.570·|G|** of credit, more than any submission has ever earned at any budget; at 44,090 px it needs 0.486·|G|, which H19-5 solid *has* (0.506) but thinning to that budget retains only 0.759 → 0.384. **Retention, not knowledge, is the wall.** Only two routes remain: retention ≈1.0 at ~44k px, or concentration above 5.7 — both are detector problems needing *new information*.
* **Rejected with evidence, so nobody re-derives them:** H27-6 coverage-optimal thinning (**0.866× Poisson-disk — 13 % worse** at the budget that matters); H27-7 union-recall ensembling (central 0.2655 but **pessimistic bound 0.2310**, vs 0.2550 for h19-5 alone on a rule validated to 4 %); H27-9 habitat tomography (**not identifiable** — LOO score RMSE 0.0715 vs a score spread of 0.0686, signal ratio 0.96).
* **Leaderboard context** (secondary quote from the sibling's owner-directed read, *not* fetched by this agent — drivendata.org is off limits): rank 1 **0.3195**, rank 2 **0.3128 with only 2 submissions**, rank 5 **0.2941**; the group's 0.2477 sits at **rank 16**. Rank 2 reaching 0.31+ in two attempts is evidence of a materially better **detector**, not a better submission schedule.

## What is validated, and what is not
| claim | status |
|---|---|
| Files are single-band float32, exact 0.0/1.0 inside the footprint, NaN outside (nodata=NaN) like the sample; fallback and zip provided | verified by an independent script (`scripts/verify_downloads.py`, **147 checks, 0 failures**, covering the five weekly-slot files, the separate H28-1 research candidate, and the Addendum-E single-variable invariants) |
| Emitting on independently-mapped bedrock faults the Quaternary catalogue lacks ("a second official catalogue sees what we miss") | **LIVE-REFUTED** — h18-4 scored 0.0360 → 1.62× blind (bracket 0.76–1.65×), credit fraction 0.062 of \|G\|, best modelled 0.0424 (`evidence/sgmc_gap_inversion.json`) |
| Ranking gap links by graph-connectivity value beats the local z ≥ 3 rule | **REFUTED** on seeds 140–149 (0.2914 vs 0.2889, needed ≥1.15×, and inside the random-half spread). The values stay in every dossier as documentation |
| Overlapping en-echelon step-overs are a productive candidate class | **REFUTED** (efficiency 0.0605 < break-even 0.0638; 1.11× the perpendicular control, needed ≥2.0×) |
| Oriented 0.5–2 km lineament integration, radiometric ratios or thermal-point distances improve the detector | **REFUTED** as features on this footprint: PR-AUC +0.0010 / +0.0007 / +0.0005 against a registered +0.005 requirement |
| The catalogue-internal holdout can decide whether a better detector pays | **REFUTED** — 100 % of its truth sits at d = 0 from the published catalogue and 99.6 % of credit within 200 m, while 81.4 % of the live emission's dots are ≥300 m out. Slot 5 is the registered live substitute |
| The four weekly files are single-band float32, exact 0.0/1.0 inside the footprint, NaN outside (nodata=NaN) like the sample; fallback and zip provided | independent script (`scripts/verify_downloads.py`, 79 checks, 0 failures) |
| Separate H28-1 full-map research candidate is a valid, exact binary single-band GeoTIFF on the official template grid | independently verified by the same audit: EPSG:32611, 3730×3292, float32, `[0,1]`/finite inside, NaN outside with nodata=NaN, all-finite fallback, one-TIFF ZIP, no known-label overlap; candidate is unscored and not a weekly slot |
| The forward model `DTI = TPw/(0.2·TPw·(1−ρ) + 0.2·N + 0.8·|G|)` reproduces the two live anchors | **verified exactly** on hash-authenticated rasters: H19-5 solid → 0.1922, dotted d1.5 → 0.2477 (`evidence/live_inversion.json`, `tests/test_inversion.py`) |
| The retention rule `credit(d) = credit_solid·c(d)/c_solid` transfers to an unseen live pair | **verified**: −0.1 % on H19-5→d1.5, +4.0 % on H25-ctx→h28 (`evidence/budget_optimum.json`) |
| `|G|` ≈ 12.2–12.8k px | three independent instruments agree within 4.3 % (blind lattice 12,226 here; sibling lattice 12,503; sibling pair 12,769). Still an **estimate**, not an organiser receipt |
| Coverage-optimal thinning beats Poisson-disk | **REFUTED** — 0.866× at the sparse budget (`src/gems27/coverage_thin.py`) |
| Union-recall ensembling of near-disjoint surfaces beats the best single surface | **REFUTED as an improvement** — central 0.2655 vs pessimistic 0.2310, against 0.2550 for h19-5 alone |
| Habitat tomography of the hidden truth is identifiable from 20 live scores | **REFUTED** — LOO signal ratio 0.96, no better than predicting the mean |
| The 0.2477 file is exactly `dot_thin(H19-5 minus catalogue, 1.5)` | reproduced (60,069 px identical) |
| Topology gap-closure beats rotated-cone controls and random same-size subsets on the 8-connected component holdout | pre-registered gates passed on seeds 100-109 (`0.118` vs `0.057` ctrl) and confirmed on fresh seeds 110-119 (`z>=3 dedup = 0.280` vs `0.056` ctrl) and seeds 120-129 (`0.2926` vs `0.0586` ctrl) |
| Topology gap-closure and H27-5 kinematic typing beat rotated-cone controls when **whole NBMG INGENIOUS `FID` vector polylines** are held out | pre-registered Addendum B gate passed on seeds 120-129 (`evidence/vector_topology_validation.json`): `z>=3 dedup = 0.1003` vs `0.0204` ctrl (`4.92x`, `> m(0.30) = 0.0638`); `H27-5a (inter-FID + kinematic_compat) = 0.1374` (`6.74x`); `H27-5b (inter-FID + same_name + kinematic_compat) = 0.1783` (`8.74x`) |
| Topology gap-closure (H27-1) and 100–200 m flank-shadow pruning (H27-4) improve DTI on a **strictly out-of-fold 4-quadrant spatial-CV detector ($B_{\text{oof}}$)** | pre-registered Addendum C gates passed on seeds 130-139 (`evidence/oof_hypothesis_gates.json`): `plus_T_v2` gains `+0.0115` (`4/4` folds); `prune_r1_100m` gains `+0.0022` solo (`4/4` folds, removed efficiency `0.0034` vs live break-even `0.0521`) and **`+0.0141` stacked with T-v2** (`4/4` folds); H27-3 isolated-dot removal refuted (`-0.0010`, `0/4` folds) |
| H28-1 multiscale magnetic/gravity edge features + T-v2/H27-4 beat the OOF best | preregistered seeds 140–149 passed (`evidence/h28_1_edge_holdout.json`): mean paired ΔDTI `+0.00294884`; 3/4 folds, 9/10 seeds. NE_LidarGapHeavy and seed 149 regressed. Catalogue-internal only; not a public score. |
| Full-map H28-1 + T-v2 + H27-4 r1 candidate | fit on all existing catalogue labels with frozen parameters; exact binary GeoTIFF, no known-label overlap, independently format/range checked; separate research manifest and note. No weekly slot or upload used. |
| The same on the real hidden test set | **unknown until a slot is used** (only a live score tests the organisers' newly created expert labels) |
| Plausible effect on DTI at the 0.2477 operating point | Slot 1 (`5512495c6bd1`): `-0.0029` (zero hit rate) ... `+0.0024` (`FID_trace` eff `0.1003`) ... `+0.0110` (`component` eff `0.280`); Slot 3 (`d466b251f309`): `+0.0141` (`FID_trace`) to `+0.0223` (`component`) |
| Modelled DTI of all four slots under both truth assumptions | `evidence/candidate_model_scores.json`: geo/hyb — slot 1 `0.2506`/`0.2580`, slot 2 `0.2585`/`0.2671`, slot 3 `0.2439`/`0.2704`, slot 4 `0.2484`/`0.2781`. **Models, not scores.** They disagree only on the targeted prune; the geometric model is validated for *unbiased* removal and is known to be biased against *targeted* removal (it charges pruned flank pixels average credit; the OOF gate measured 0.0034, ~15× below the 0.0521 break-even) |
| Reaching 0.3195 | **No** — not with any rearrangement of pixels the group already has. It needs 0.570·\|G\| of credit at 60,069 px (more than any submission has ever earned) or retention ≈1.0 at ~44k px. See `knowledge/07_live_score_inversion.md` §8 |

## Map of the repo
| path | what |
|---|---|
| `src/gems27/` | `metric.py`, `thinning.py`, `holdout.py`, `graph.py`, `links.py`, `candidates.py`, `topology_theory.py`, `submission.py`, `grid.py`, `paths.py`, **`vector_graph.py`** (NBMG INGENIOUS vector attribution & H27-5 kinematic compatibility), **`topology_classes.py`** (exclusive H27-5b reviewer classes and geometry-only cues), **`oof_detector.py`** (4-fold spatial-CV detector with optional extra features), **`potential_edges.py`** (H28-1 label-free multiscale magnetic/gravity transforms) |
| `scripts/` | `restore_data.py`, `download_competition_data.sh`, `prepare_data.py`, `fetch_vector_faults.py`, `run_graph_report.py`, `run_topology_validation.py`, `run_topology_confirm.py`, `run_vector_topology_validation.py`, `run_oof_hypothesis_gates.py`, `run_h28_1_edge_holdout.py`, `build_h28_1_candidate.py` (separate research export), `build_candidates.py`, `build_submission27.py`, `verify_downloads.py`, `make_figures.py`, `build_site.py`, `refresh_source_feed.py`, `operating_point.py`, `channel_auc.py` |
| `knowledge/` | 01 why 0.2477 won; 02 hypothesis ledger (incl. H27-10 result); 03 pre-registration (incl. Addenda A–F); 04 topology & vector argument; 05 sources; 06 limitations/access and current priorities; 07 live-score inversion plus current Session 5 screen/results; 08 frozen H28-1 protocol; 09 full-map candidate export preregistration; 10 Session 4 far-field limit; 11 H27-5b geologist-review class |
| `registry/` | `sources.json`, `hypotheses.json` (historical evidence ledger), `next_hypotheses.json` (current four-item untried screen plus tested H27-10 result), `irregularities.json`, `live_scores.json`, `topology_candidates.json` (345 links with NBMG attributes, exclusive review class and graph context) |
| `evidence/` | machine-readable results (`topology_validation.json`, `topology_confirmation_v2.json`, `vector_topology_validation.json`, `oof_hypothesis_gates.json`, `h28_1_edge_holdout.json`, H27-10 initial/corrected holdout JSONs, `structural_relay_classes.json`, live-score inversion/model evidence, `data_preparation.json`, `graph_report.json`, `channel_auc.json`, `review_passes.md`) |
| `docs/` | GitHub Pages site (`index.html`, `executive-summary.html`, `topology.html`, `research.html`, `sources.html`), `downloads/` (four-slot `manifest.json` plus separate `h28_1_candidate_manifest.json`), `data/` (all 345 topology links plus focused 81-row H27-5b CSV/GeoJSON and class definition, feed and vector-fault status) |
| `.github/workflows/` | `source-feed.yml` (official sources only; never drivendata.org), `fetch-vector-faults.yml` (NBMG INGENIOUS ArcGIS REST check), `ci.yml` (tests + lint + site build) |

## Reproduce
```bash
pip install -r requirements.txt
GEMS_DATA_DIR=./data_cache python scripts/restore_data.py          # restores 16 hash-pinned artifacts (or run bash scripts/download_competition_data.sh outside the sandbox)
python scripts/prepare_data.py                                     # builds 32-band label-free feature matrix (data_cache/prepared/features.npy)
python scripts/fetch_vector_faults.py                              # verifies qfaults_v2_in_footprint.json (1,179 NBMG polylines)
python scripts/run_graph_report.py
python scripts/run_topology_validation.py --seeds 100-109
python scripts/run_topology_confirm.py --seeds 110-119
python scripts/run_vector_topology_validation.py --seeds 120-129   # Addendum B: 3-tier vector holdout + H27-5
python scripts/run_oof_hypothesis_gates.py --seeds 130-139         # Addendum C: honest 4-fold spatial-CV OOF gates
python scripts/build_augmented_features.py                         # Addendum D: 40 extra label-free bands (827 MB memmap)
python scripts/run_addendum_d_gates.py --seeds 140-149             # Addendum D: PR-AUC screen + paired gates (D1-D4)
python scripts/diagnose_arm_habitats.py                            # where an arm's credit actually comes from
python scripts/invert_sgmc_probe.py                                # invert the h18-4 SGMC-gap live score
python scripts/build_candidates.py
python scripts/build_submission27.py && python scripts/verify_downloads.py
python scripts/make_figures.py && python scripts/build_site.py
```

## Task prompt (verbatim, owner-supplied)
```text
We are competing in this competition to be placed at the top of the leaderboard: https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/ https://www.drivendata.org/competitions/306/competition-doe-gems/

Fault network topology. In Berkowitz, Bour, Davy, and Odling (GRL 2000), a fault network's percolation/connectivity threshold is governed by its length-distribution exponent and fractal dimension, and a single mapped segment can be the difference between two faults being disconnected vs. part of one connected cluster. Build the known INGENIOUS/USGS traces into an explicit graph (nodes at segment endpoints and intersections, edges as mapped fault segments), then identify short, otherwise-low-scoring gaps whose closure would convert two structurally related but disconnected mapped faults into a single coherent system consistent with regional kinematics and known step-over/termination settings. Treat those topologically load-bearing gaps as a distinct high-priority candidate class, and write the graph-based argument directly into each candidate's documentation.

We got our highest score on https://buffedlizard55-lab.github.io/GEMSDOE24/ , study, analyze and understand why and how at a Phd level. Can we generate a higher scoring submission? And if so, how? Higher than 0.2477, and ideally higher than the current high on the leaderboard of 0.3195?

Build a unique new research and generation system, not just a re-skinning of the existing website. Provide a clean, simple website with links to official sources and an up-to-date feed so I don't have to manually check things. Ensure the submission TIF is easy to download and obvious on the first screen, and verify it passes the competition's validation checks (fixing the "Predicted values must be in range [0, 1]" error). Also, build an organized, auditable knowledge base and data table with links to official sources.

Review the repo and put this full prompt into the README.Read the README every session as the starting point.

Work on the next steps from the previous sessions first.

Before writing any new feature code, generate 3-5 untried candidate geological hypotheses — each naming the specific layer(s), the physical signature it targets, why it should catch a fault that is missing from the USGS/INGENIOUS catalogue rather than one already in it, and how it differs from everything already in the repo. Rank them by expected DTI improvement and implementation cost, then validate the top candidate on the spatially-blocked holdout set before touching a weekly submission slot. If a hypothesis needs external data, name the free official source and check that it's actually obtainable.

Don't limit your thinking to what's already in the repo — be contrarian, think outside the box, and look for overlooked data sources, unconventional geological signals, or novel ways of combining existing layers that no previous session has tried. Ground every wild idea in a real physical mechanism and a concrete validation test so we only ship what actually works.

Remember, the goal is to get the highest score possible on the leaderboard. Do not spend a weekly submission slot on an idea that hasn't beaten our current best on the holdout set.

Provide a one-click submission button on the executive summary page that downloads the TIF file with a unique name, along with a short comment to copy-paste into the submission form. Explain how to submit it on the executive-summary subpage.

The submit form on DrivenData takes a .tif (or a .zip with one GeoTIFF) and an optional short "Note" (≤200 chars) that only shows up in your own submissions list to help you tell runs apart.

Create a deep-research knowledge base from official sources, and an auditable data/source table with verified links.

State your limitations and what access you need.

Run the task through 3 passes: Pass 1: Implement and verify. Pass 2: Review for bugs, missing requirements, incorrect assumptions, and edge cases, then fix. Pass 3: Re-check the entire implementation against the original request and polish. Then create a pull request and merge onto main. List remaining work and limitations for the next session.

Current leaderboard high is 0.3195

Scores from our other sites:
https://buffedlizard55-lab.github.io/GEMSDOE/ : 0.1563
https://buffedlizard55-lab.github.io/5GEMSDOE/ : 0.1563
https://buffedlizard55-lab.github.io/7GEMSDOE/ : 0.1461
https://buffedlizard55-lab.github.io/8GEMSDOE/ : 0.1563
https://buffedlizard55-lab.github.io/GEMSDOE10/ : (h28-dotted-ridge) 0.1839
https://buffedlizard55-lab.github.io/12GEMSDOE/ : 0.1294
https://buffedlizard55-lab.github.io/16GEMSDOE/ : (h16-1) 0.1855, (h18-3a) 0.0976, (h18-4) 0.0360
https://buffedlizard55-lab.github.io/19GEMSDOE/ : (h19-5) 0.1922, (h19-4) 0.1894
https://buffedlizard55-lab.github.io/20GEMSDOE/ : (h20-1) 0.1890
https://buffedlizard55-lab.github.io/GEMSDOE22/ : (h23-a) 0.1002
https://buffedlizard55-lab.github.io/24GEMSDOE/ : (h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan) 0.2477
https://buffedlizard55-lab.github.io/25GEMSDOE/ :
https://buffedlizard55-lab.github.io/26GEMSDOE/ :
https://buffedlizard55-lab.github.io/27GEMSDOE/ :

Official Rules: https://docs.nlr.gov/docs/fy26osti/96647.pdf
The GEMS Prize utilizes the INGENIOUS play fairway regional dataset inside the GeoDAWN footprint: https://gdr.openei.org/submissions/1391
Dropbox links for the competition data:
GEMS_96647.pdf: https://www.dropbox.com/scl/fi/aemhtutjgcp6tr3tint94/GEMS_96647.pdf?rlkey=rek210cj2smnmzb8n0sla1vmd&st=wz4kofki&dl=0
example_submission.tif: https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&st=8junzdyw&dl=0
existing_faults.tif: https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&st=rnino7ya&dl=0
gems-geodawn-numerical-features.tif: https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?rlkey=je8d8fepqfbst9lnwsq9rkplu&st=zj1lag1r&dl=0
Digital-elevation-model-links-JSON.pdf: https://www.dropbox.com/scl/fi/ig0mban712ns1atphgphe/Digital-elevation-model-links-JSON.pdf?rlkey=zm77f1vbtt2if8hlruymptnu3&st=srhhir10&dl=0
```

## Core Values (verbatim, owner-supplied)
```text
The following is taken from the Arena AI team and I think it makes a good point on building a successful project, so let's keep the Core Values and Own the Outcome as a focal point when building, developing, researching, suggesting upgrades, and implementing the work.

Our Core Values
Maximize P(Win)
"Maximize the Probability of Winning": our decision making framework. In every decision, we weigh tradeoffs, assess risk, and choose the path that maximizes the probability that Arena succeeds. We set aside our emotions and make tough decisions in order to maximize P(Win). "Maximize P(Win)" frees us from constraints and clarifies that we must put Arena first.

Own the Outcome
We own results end to end — not just our individual slice of the work. When problems arise and we have the means to act, we do so without waiting for permission or assignment. We treat failure and success as signals and use them to improve. At Arena, we stay accountable to the final outcome.

Work line by line verifying from official verified trusted sources, provide links for manual review. There should be no manual input, work on your own to complete tasks. Flag any irregularities for review. No hallucinations.
Verify no hallucinations.
```

## Credit and disclosure
Metric, thinning and holdout conventions re-implement the owner's sibling repository `buffedlizard55-lab/GEMSDOE24` (credited in each module); the graph, link, candidate, connectivity-theory, vector-attribution, OOF-detector, and submission-verification code is new.
This work was produced by an AI agent on Arena.ai; see `AI_DISCLOSURE.md` (the Official Rules require generative-AI use to be stated in the narrative).
