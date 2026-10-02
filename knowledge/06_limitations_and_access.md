# Limitations, access needed, remaining work

## Limitations (what limits success)
1. **No live score exists for any 27GEMSDOE file.** The sandbox reaches only github.com/PyPI, and automated access to drivendata.org is prohibited by its Terms of Use (verified quote in `registry/sources.json`). The agent never uploads, never reads the leaderboard.
2. **Validation is catalogue-internal.** Hidden truth in the holdout is 20 % of catalogue components; segmentation of the catalogue can inflate link enrichment relative to genuinely new expert-mapped faults. The live score is the only test of the real hidden set.
3. **Paired base is leaky.** H19-5 was trained on all labels; its holdout DTI (~0.098) is not comparable with the live 0.2477. Only paired differences and controls are used.
4. **Raster graph, not vector.** The graph inherits 100 m rasterisation; names, slip sense and dip direction were not available (USGS Qfaults GIS is the free official source; see H27-5).
5. **No honest detector.** The base emission is the owner's H19-5 (hash-pinned); a label-blind surface for gating pruning/filter ideas (H27-3, H27-4) was not built in this session.
6. **Hidden-truth size (~12.6k px) is inferred** from one lattice submission and is unconfirmed; all operating-point arithmetic inherits that.
7. **Effect size is small.** Plausible gain of the shipped addition is -0.003 ... +0.011 DTI; with thinning d2.8 the modelled stack reaches ~0.26-0.27. **0.3195 is not reachable with the verified/modelled increments alone.**
8. The Berkowitz et al. quantities are ensemble statistics; a and D are only roughly determined for this (non-power-law) catalogue.
9. The cause of the portal's "[0,1]" rejection is unknown; the files are as safe as can be verified offline, with a fallback.

## Access needed (owner actions; nothing here can be done by the agent)
| need | why |
|---|---|
| Submit the file(s) and report the score (edit `registry/live_scores.json`) | only a live score tests the topology class on the real hidden set |
| If the portal rejects a file: paste the exact message and file name | to find the validator's real rule |
| Paste the original task prompt into README.md ("Task prompt" placeholder) | the agent no longer holds the verbatim text |
| Confirm the deadline (page: Dec 3 2026 11:59 p.m. UTC vs rules: 5 p.m. ET) | unresolved discrepancy |
| Disclose generative-AI use in the final narrative | Official Rules; see AI_DISCLOSURE.md |
| Optional: a geologist to review the 345 dossiers (`docs/topology.html`) | the final round re-scores against expert-expanded labels |
| Optional: approve a CI job that downloads the NBMG INGENIOUS Qfaults layer (22,956 polylines with dip/slip attributes; verified queryable from a runner) and USGS Qfaults GIS (32.4 MB; verified downloadable), and Siler (2022) | H27-5 and a trace-level holdout; obtainability is evidenced in `docs/data/feed.json`, the job itself is not written |
| Optional: DrivenData `1m_DEM_links.csv` (login) | supervised scarp detector (sibling hypothesis H25-3) |

## Remaining work (ordered by expected value per hour)
1. Owner submits slot 1 (primary, A/B against 0.2477); record the score.
2. Decide slot 2 by the rules in the executive summary (stack d2.8 only if slot 1 >= 0.2477).
3. Build an honest label-blind surface (spatial-CV detector) to gate H27-3/H27-4 on the holdout.
4. Write the CI job that pulls the NBMG INGENIOUS Qfaults vector layer (22,956 polylines; `DIPDIRECT`, `SLIPSENSE`, `FTYPE_`, `MAPSCALE`), build the attributed *vector* graph, validate on a trace-level holdout (hide whole mapped traces), and type the links (H27-5); add Siler stress.
5. Supervised scarp detector on 1 m DEM with geologist-labelled scarps.

## Previous sessions' next steps (from the sibling 24GEMSDOE record) - status
| inherited item | status here |
|---|---|
| Submit dotted H19-5 d1.5 | done by the owner (owner-reported 0.2477) |
| Modelled alternative d2.8 (44,090 px, never scored) | regenerated and asserted identical to the sibling file; shipped only combined with topology as slot-2 file B, and linked as the plain alternative |
| H25-2 strike-compatibility prior | implemented as the `strike_compat` term of the evidence score and validated inside T-v2 (catalogue-internal) |
| H25-3 scarp cross-profile template on 1 m 3DEP | not done (needs a CI pass over ~716 tiles, about 2 days) |
| H25-4 concealed basin-margin step | not done |
| H25-1b dotted multi-field union | not done (no label-blind way to rank fields) |
| H25-5 microseismic lineations | not done (location error 1-5 km >> 300 m kernel) |
| H25-6 map-scale correction corridor | not done (needs per-pixel map scale from the GDR vector data) |
