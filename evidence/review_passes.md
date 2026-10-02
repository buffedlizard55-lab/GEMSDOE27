# Three review passes (27GEMSDOE)

## Pass 1 - implement and verify
* Inputs restored by hash (`scripts/restore_data.py`): labels, template, H19-5, the 0.2477 file, d2.8 file, lidar/radiometric rasters, training raster (4371c82e...).
* Re-implemented the official DTI; tested against a literal brute-force transcription of the definition (random grids, soft predictions, masks) and, on a real cell, against the sibling's independent implementation (difference 0.00e+00).
* Regenerated the 0.2477 emission (60,069 px) and the sibling d2.8 emission (44,090 px) bit-for-bit.
* Built the fault graph, links, evidence score, candidate set; pre-registered and ran the gates (seeds 100-109, then 110-119); built both submissions; verified them with an independent script; 32 tests; ruff clean.

## Pass 2 - bugs, assumptions, edge cases
| # | finding | action |
|---|---|---|
| 1 | **Implementation bug (mine):** the first confirmatory launch applied the minimum gap before choosing the nearest target, deviating from the registered rule (caught by a unit test) | fixed; run stopped, disclosed (`topology_validation_runA_partial_log.txt`), rerun as registered |
| 2 | **Defect in the graph edge builder:** 1-px stubs recorded as self-loops inflated the cyclomatic number (504) | fixed; reported figures replaced (250 raw / 110 / 6 enclosed >= 20 px); no effect on links, validation or files (content ids unchanged: 5512495c6bd1, 3ebd51534bb1) |
| 3 | Mutual links appear twice (A->B, B->A): duplicate dot trains | de-duplicated variant added to the confirmatory run (efficiency 0.280 vs 0.226) and shipped; duplicates were marginal anyway (~0.069 vs break-even 0.053) |
| 4 | 8 of 345 links pass within ~100 m of a third system | kept (validated rule), flagged per link |
| 5 | Efficiency of "all links" (0.121) is below random same-size subsets (0.149): overlap saturates credit | null for z>=3 is the same-size random subset (p95 0.156), not the full set |
| 6 | Paired base is leaky; holdout DTI (~0.098) is not the live regime | paired comparisons only; payoff table recomputed at the 0.2477 operating point with break-even logic |
| 7 | Enrichment may be catalogue segmentation, not geology (larger merged systems were *less* enriched) | stated as the main transfer risk; class described as fragment completion, not giant-system bridging |
| 8 | Berkowitz et al. results are ensemble statistics; per-gap claim not in the paper | claims table; per-gap statements rest on our graph analysis and holdout |
| 9 | The `tc` training band is rank-identical to radiometric total count | registered as an irregularity; not used as a magnetic edge transform |
| 10 | The verbatim task prompt is no longer available; git cannot notarise the pre-registration order | placeholders and plain statements (README, knowledge/03, registry) |
| 11 | Portal "[0,1]" cause unknown | exact 0/1, nodata=NaN like the sample, all-finite fallback, zip; independent verifier |
| 12 | Edge cases: footprint border (dots outside footprint would be silently dropped by NaN masking) | emission asserted inside the footprint and off catalogue before writing; verifier re-checks |

## Pass 3 - recheck against the original request
| request item | where satisfied | residual gap |
|---|---|---|
| 1. why 0.2477 won; achievability; new system | `knowledge/01`, `docs/research.html`; new graph/link/verification code and site | 0.3195 not reachable with verified/modelled increments - stated |
| 2. topology class: graph, gaps, kinematics/step-over/termination, dossier per candidate, Berkowitz only as verified | `knowledge/04`, `docs/topology.html`, `registry/topology_candidates.json`, CSV/GeoJSON | kinematics are data-driven (strike domain); independent stress model is H27-5; per-link "low-scoring" = non-redundant with the 0.2477 emission |
| 3. 3-5 untried hypotheses ranked; top validated pre-slot; external data named and checked | `registry/hypotheses.json`, `knowledge/02`; gates passed | external sources verified by listing only (not downloaded) - stated |
| 4. knowledge base + auditable table with links, overlooked sources, contrarian | `docs/sources.html`, `docs/data/sources.csv`, `knowledge/05` | several sources "not read" are labelled as such |
| 5. one-click valid TIF on the first screen; [0,1]; unique name; note; exec-summary steps | `docs/index.html`, `docs/executive-summary.html`, `docs/downloads/` | portal acceptance cannot be tested by the agent |
| 6. clean Pages site, official links, up-to-date feed | `docs/`, `source-feed.yml`, `build-site.yml` | feed runs on a GitHub runner; the first run is part of the PR checks |
| 7. README with the prompt verbatim + Core Values | Core Values verbatim; prompt restated | **verbatim prompt unavailable - owner placeholder** |
| 8. limitations and access | `knowledge/06`, executive summary | - |
| 9. three passes, PR, merge, remaining work | this file; PR/merge recorded in the final report only if they occur | - |
