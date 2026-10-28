# Session 16 — three-pass repository and delivery review

## Decision

**NOT OK TO SUBMIT. No geological experiment, new TIFF, slot selection or upload was performed.** The repeated user prompt omits the promised single-method paragraph. The recorded H29-5-PROXY and H33-1 experiments are negative; do not rerun consumed seeds as new evidence. The ranked four-hypothesis screen remains in [the preregistration](30_lane_2026-10-27_preregistration.md). This session does not claim those hypotheses are newly untried.

The existing executive summary, research download and how-to-submit page were rebuilt from their recorded evidence with no content change. An estimated leaderboard score remains **unknown**, not an extrapolation from a local holdout. No source-page receipt or current weekly cap is available. Historical scores remain OWNER-REPORTED. The conflicting leaderboard values in the prompt are unresolved.

## Pass 1 — implementation and prerequisites

Read README.md, AGENTS.md, current executive summary, preregistration and safety policy. The fresh checkout had no scientific Python dependencies or data cache. Created an ignored `.venv`, installed requirements, restored hash-pinned inputs through `scripts/restore_data.py`, and fetched the pinned parallel registry. Mirrors are owner-hosted, not organizer-authenticated. The first peer audit failed because the peer cache was missing; fetching it and rerunning resolved that prerequisite, not a scientific gate.

Fixed a shared readiness defect in `src/gems27/readiness.py`: embedded-NUL paths and symlink loops from run-card JSON could raise during path resolution and abort the entire audit. Such cards now fail closed with the existing missing/outside-repository reason and no hash. The evaluator and submission writer were not forked or modified.

## Pass 2 — defects and edge cases

Added regressions for embedded NULs, parent traversal and symlink loops. Before data restoration: 197 tests passed, three data-dependent tests skipped. After restoration: **200 tests passed, none skipped**. Ruff passed. The download verifier reported **0 failures**. The readiness audit still approves no candidate or slot. These are software/format checks, not HOLDOUT-DTI or organizer scores.

Reran `verify_peer_relations.py`: twelve pinned rasters, two identical-value pairs and eleven strict-subset relations. The only change to its evidence JSON is its execution timestamp; measured relations reproduced exactly. GEMSDOE32's field is the d=2.8 field minus its two-pixel catalogue collar. Geometry alone does not establish why the organizer would award a particular score or show that more collar removal helps. Further subsets fail directed overlap uniqueness.

## Pass 3 — requirement check and limits

`build_site.py` regenerated six pages, root index and executive summary without content changes. Existing research files are clearly rejected rather than advertised as leaderboard-ready. The automated range-safe all-finite writer remains the route for any later eligible file; a successful local validator is not organizer acceptance.

Source links for review: [official organizer reference repository](https://github.com/drivendataorg/gems-prize-reference-solution), [competition description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [official GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [GDR 1391](https://gdr.openei.org/submissions/1391). GitHub API verified the reference repository README location during this session. The other hosts were not freshly read or verified here. No claim of new literature research or line-by-line official verification is made. The network allowlist and repository prohibition on automated DrivenData access remain in force.

### Next work

1. Supply an explicit parallel-method assignment before any new scientific run. Do not invent a lane or cosmetically modify an existing raster.
2. Preregister unused seeds and run feature-alone canaries plus matched current-best whole-segment buffered evaluation, with stronger independent geographic validation.
3. Restore complete current registry scope and check surfaces and final dots; twelve pinned references alone cannot prove global novelty.
4. Only a positive matched holdout and complete provenance/uniqueness/byte gates can reach a separate weekly-slot selector. A new TIFF solely to satisfy a download request would not solve the measured efficacy deficit.

The existing full negative run card is [H33-1](../evidence/h33_run_card_2026-10-27.json). It is historical evidence, not a newly run experiment. No new geological run card is fabricated for this software audit.
