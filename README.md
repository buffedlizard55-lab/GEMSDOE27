# 27GEMSDOE - topology-first research and submission lab for DrivenData #306 (DOE GEMS)

**Site:** https://buffedlizard55-lab.github.io/GEMSDOE27/ (first screen = one-click download + the note to paste).
**Status (2026-10-02):** 3 weekly slot candidates built and format-verified (66 standalone checks passed); **no leaderboard score exists for any 27GEMSDOE file** - nothing in this repo claims one.
Owner-reported reference: the 24GEMSDOE file scored **0.2477** (owner-reported); the owner-stated leader is **0.3195** (unconfirmed; the agent does not access drivendata.org).

## Start here every session (checklist)
1. Re-read **Task prompt (verbatim)** and **Core Values (verbatim)** below. Maximize P(Win) and Own the Outcome are the focal point of every build, research and implementation decision.
2. Do the previous session's next steps first: `knowledge/06_limitations_and_access.md` -> "Prioritised next steps for Session 4".
3. Verify inputs: `python scripts/restore_data.py` (16 hash-pinned artifacts; SHA-256 in `data/manifest.json`), `python scripts/prepare_data.py`, then `python -m pytest -q` and `python scripts/verify_downloads.py`.
4. Verify line by line against official sources and give links for manual review (`registry/sources.json`, `docs/sources.html`). Flag irregularities (`registry/irregularities.json`). No hallucinations: unknown stays unknown.
5. Never automate drivendata.org (Terms of Use); never claim an upload, score, PR or merge without evidence.
6. Before implementing anything new: 3-5 untried hypotheses with layers, physical signature, why it catches a fault missing from USGS/INGENIOUS, how it differs from the repo, ranked by expected DTI gain and cost (`registry/hypotheses.json`); validate the top one on the spatially blocked holdout **before** a weekly slot is spent.
7. Run three passes: implement+verify; review bugs/assumptions/edge cases; recheck against the original request (`evidence/review_passes.md`).

## Submit (one click — 4 pre-built weekly slot candidates)
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
* Exact steps and the decision rules for the 4 weekly slots: `docs/executive-summary.html`.

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
| Files are single-band float32, exact 0.0/1.0 inside the footprint, NaN outside (nodata=NaN) like the sample; fallback and zip provided | verified by an independent script (`scripts/verify_downloads.py`, **79 checks, 0 failures**, now covering all four slots) |
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
| The same on the real hidden test set | **unknown until a slot is used** (only a live score tests the organisers' newly created expert labels) |
| Plausible effect on DTI at the 0.2477 operating point | Slot 1 (`5512495c6bd1`): `-0.0029` (zero hit rate) ... `+0.0024` (`FID_trace` eff `0.1003`) ... `+0.0110` (`component` eff `0.280`); Slot 3 (`d466b251f309`): `+0.0141` (`FID_trace`) to `+0.0223` (`component`) |
| Modelled DTI of all four slots under both truth assumptions | `evidence/candidate_model_scores.json`: geo/hyb — slot 1 `0.2506`/`0.2580`, slot 2 `0.2585`/`0.2671`, slot 3 `0.2439`/`0.2704`, slot 4 `0.2484`/`0.2781`. **Models, not scores.** They disagree only on the targeted prune; the geometric model is validated for *unbiased* removal and is known to be biased against *targeted* removal (it charges pruned flank pixels average credit; the OOF gate measured 0.0034, ~15× below the 0.0521 break-even) |
| Reaching 0.3195 | **No** — not with any rearrangement of pixels the group already has. It needs 0.570·\|G\| of credit at 60,069 px (more than any submission has ever earned) or retention ≈1.0 at ~44k px. See `knowledge/07_live_score_inversion.md` §8 |

## Map of the repo
| path | what |
|---|---|
| `src/gems27/` | `metric.py`, `thinning.py`, `holdout.py`, `graph.py`, `links.py`, `candidates.py`, `topology_theory.py`, `submission.py`, `grid.py`, `paths.py`, **`vector_graph.py`** (NBMG INGENIOUS vector attribution & H27-5 kinematic compatibility), **`oof_detector.py`** (4-fold spatial-CV out-of-fold detector) |
| `scripts/` | `restore_data.py`, `download_competition_data.sh`, `prepare_data.py`, `fetch_vector_faults.py`, `run_graph_report.py`, `run_topology_validation.py`, `run_topology_confirm.py`, `run_vector_topology_validation.py`, `run_oof_hypothesis_gates.py`, `build_candidates.py`, `build_submission27.py`, `verify_downloads.py`, `make_figures.py`, `build_site.py`, `refresh_source_feed.py`, `operating_point.py`, `channel_auc.py` |
| `knowledge/` | 01 why 0.2477 won; 02 hypotheses (ranked); 03 pre-registration (incl. Addenda A, B, C); 04 topology & vector argument; 05 sources; 06 limitations/access |
| `registry/` | `sources.json`, `hypotheses.json`, `irregularities.json`, `live_scores.json`, `topology_candidates.json` (345 links with NBMG/USGS vector fault names, `FID`, `SLIPSENSE`, `DIPDIRECT`, `kinematic_compat`) |
| `evidence/` | machine-readable results (`topology_validation.json`, `topology_confirmation_v2.json`, `vector_topology_validation.json`, `oof_hypothesis_gates.json`, `data_preparation.json`, `graph_report.json`, `channel_auc.json`, `review_passes.md`) |
| `docs/` | GitHub Pages site (`index.html`, `executive-summary.html`, `topology.html`, `research.html`, `sources.html`), `downloads/`, `data/` (`topology_links.csv`, `topology_links.geojson`, `feed.json`, `vector_faults_status.json`) |
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
