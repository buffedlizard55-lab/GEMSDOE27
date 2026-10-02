# 27GEMSDOE - topology-first research and submission lab for DrivenData #306 (DOE GEMS)

**Site:** https://buffedlizard55-lab.github.io/GEMSDOE27/ (first screen = one-click download + the note to paste).
**Status (2026-10-02):** candidates built and format-verified; **no leaderboard score exists for any 27GEMSDOE file** - nothing in this repo claims one.
Owner-reported reference: the 24GEMSDOE file scored **0.2477** (owner-reported); the owner-stated leader is **0.3195** (unconfirmed; the agent does not access drivendata.org).

## Start here every session (checklist)
1. Re-read **Task prompt** and **Core Values** below. Maximize P(Win) and Own the Outcome are the focal point of every build, research and implementation decision.
2. Do the previous session's next steps first: `knowledge/06_limitations_and_access.md` -> "Remaining work".
3. Verify inputs: `python scripts/restore_data.py` (hash-pinned; SHA-256 in `data/manifest.json`), then `python -m pytest -q` and `python scripts/verify_downloads.py`.
4. Verify line by line against official sources and give links for manual review (`registry/sources.json`, `docs/sources.html`). Flag irregularities (`registry/irregularities.json`). No hallucinations: unknown stays unknown.
5. Never automate drivendata.org (Terms of Use); never claim an upload, score, PR or merge without evidence.
6. Before implementing anything new: 3-5 untried hypotheses with layers, physical signature, why it catches a fault missing from USGS/INGENIOUS, how it differs from the repo, ranked by expected DTI gain and cost (`registry/hypotheses.json`); validate the top one on the spatially blocked holdout **before** a weekly slot is spent.
7. Run three passes: implement+verify; review bugs/assumptions/edge cases; recheck against the original request (`evidence/review_passes.md`).

## Submit (one click)
* Primary file: `docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif`  (zip with the same file: `docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.zip`; fallback with zeros outside the footprint: `docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-allfinite.tif`).
* SHA-256 (nan file): `33003374335d84bf885f2d8f5e9dd4c57044c8ec58fa6a0d7fa581e8bc41c11d`; content id `5512495c6bd1`; 61,328 emitted pixels = the 0.2477 emission (60,069 px) + 1,259 topology gap-closure dots (nothing removed).
* Note to paste (<= 200 characters): `27GEMSDOE T-v2 A/B | 0.2477 base (dotted H19-5 d1.5) + 1259 dots on 345 aligned 1-4 km gap links; A/B vs 0.2477 | id 5512495c6bd1 | not yet live-scored`
* Exact steps and the plan for the 3 weekly slots: `docs/executive-summary.html`.

## What is validated, and what is not
| claim | status |
|---|---|
| Files are single-band float32, exact 0.0/1.0 inside the footprint, NaN outside (nodata=NaN) like the sample; fallback and zip provided | verified by an independent script (`scripts/verify_downloads.py`) |
| The 0.2477 file is exactly `dot_thin(H19-5 minus catalogue, 1.5)` | reproduced (60,069 px identical) |
| Topology gap-closure beats rotated-cone controls and random same-size subsets on a spatially blocked, component-masked holdout | pre-registered gates passed on seeds 100-109 and confirmed on fresh seeds 110-119 (`knowledge/03_preregistration_topology_gate.md`) |
| The same on the real hidden test set | **unknown until a slot is used** (holdout truth is catalogue-internal) |
| Plausible effect on DTI at the 0.2477 operating point | -0.003 (zero hit rate) ... +0.011 (holdout efficiency); central +0.004 to +0.008 (judgment) |
| Reaching 0.3195 | not with the verified/modelled increments alone (`knowledge/01_why_0.2477_won_and_the_ceiling.md`) |

## Map of the repo
| path | what |
|---|---|
| `src/gems27/` | metric (official DTI, brute-force-tested), dot thinning, holdout, **graph**, **links**, **candidates**, Berkowitz-style connectivity theory, submission writer/verifier |
| `scripts/` | `restore_data`, `run_graph_report`, `run_topology_validation`, `run_topology_confirm`, `build_candidates`, `build_submission27`, `verify_downloads`, `make_figures`, `build_site`, `refresh_source_feed`, `operating_point`, `channel_auc` |
| `knowledge/` | 01 why 0.2477 won; 02 hypotheses (ranked); 03 pre-registration; 04 topology argument; 05 sources; 06 limitations/access |
| `registry/` | sources, hypotheses, irregularities, owner-reported scores, topology candidates |
| `evidence/` | machine-readable results (validation runs, graph report, channel AUC, review passes) |
| `docs/` | GitHub Pages site (`index.html`, `executive-summary.html`, `topology.html`, `research.html`, `sources.html`), `downloads/`, `data/` (links CSV/GeoJSON, source feed) |
| `.github/workflows/` | `source-feed.yml` (official sources only; never drivendata.org), `ci.yml` (tests + lint + site build) |

## Reproduce
```
pip install -r requirements.txt
GEMS_DATA_DIR=./data_cache python scripts/restore_data.py          # needs `gh` authenticated (reads github.com only)
python scripts/run_graph_report.py && python scripts/run_topology_validation.py --seeds 100-109
python scripts/run_topology_confirm.py --seeds 110-119 && python scripts/build_candidates.py
python scripts/build_submission27.py && python scripts/verify_downloads.py
python scripts/make_figures.py && python scripts/build_site.py
```

## Task prompt
> **Provenance note (read this).** The verbatim text of this session's task prompt is no longer available to the agent: the conversation was condensed before the README was written.
> The block below is a **faithful structured restatement, not the verbatim prompt**, followed by the owner's Core Values text, which *is* verbatim (copied from the owner's brief preserved in
> `buffedlizard55-lab/GEMSDOE24` README at commit 07345ea). **Owner action:** paste the original prompt into the marked placeholder.

<details><summary>Restatement of the 27GEMSDOE task (not verbatim)</summary>

Goal: place at the top of the DrivenData #306 DOE GEMS leaderboard (predict faults as a float32 GeoTIFF scored by a distance-weighted Tversky index). Group best 0.2477 (24GEMSDOE, dotted H19-5 d1.5); owner-stated leader 0.3195; other owner-reported scores in `registry/live_scores.json`; 25/26/27GEMSDOE blank.

1. Study why and how the 0.2477 file won and whether more than 0.2477 (ideally more than 0.3195) is achievable, with PhD-level reasoning; design a new, unique research and generation system, not a re-skin of the existing site.
2. **Topology candidate class:** graph of the known INGENIOUS/USGS traces (nodes at endpoints and intersections, edges as mapped segments); find short, low-scoring gaps whose closure joins two related but disconnected faults into one system consistent with regional kinematics and step-over/termination settings; treat as a distinct high-priority candidate class with the graph-based argument in each candidate's documentation; cite Berkowitz et al. (GRL 2000) only as far as it can be verified.
3. 3-5 untried geological hypotheses ranked by DTI gain and cost; validate the top one on the spatially blocked holdout before any slot is spent; for external data name a free official source and check it is obtainable.
4. Deep-research knowledge base from official sources and an auditable data table with links; include overlooked sources; be contrarian but grounded.
5. A one-click submission TIF, obvious on the first screen, passing DrivenData validation (fix "Predicted values must be in range [0, 1]"); unique filename; short Note; executive-summary subpage with exact submission steps.
6. A clean, simple GitHub Pages site with official links and an up-to-date source feed so the owner need not check things manually.
7. README containing the prompt verbatim plus the Core Values.
8. State limitations and the access needed.
9. Run three passes, then create a PR and merge it to main; list remaining work and limitations.

Standing instructions: work autonomously with no manual input; verify line by line against official/trusted sources with links; flag irregularities; no hallucinations; do previous sessions' next steps first; the submit form takes a .tif or a .zip with one GeoTIFF plus an optional Note; Berkowitz et al. statements are claims to verify, not facts.
</details>

<details><summary>OWNER PLACEHOLDER - paste the original 27GEMSDOE prompt here (verbatim)</summary>

<!-- paste the original prompt below this line -->

</details>

## Core Values (verbatim, owner-supplied)
```
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
Metric, thinning and holdout conventions re-implement the owner's sibling repository `buffedlizard55-lab/GEMSDOE24` (credited in each module); the graph, link, candidate, connectivity-theory and submission-verification code is new.
This work was produced by an AI agent on Arena.ai; see `AI_DISCLOSURE.md` (the Official Rules require generative-AI use to be stated in the narrative).
