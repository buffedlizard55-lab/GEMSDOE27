# Instructions for agents working in this repository

Read `README.md` first (Task prompt, Core Values, session-start checklist) at the start of **every** session. Maximize P(Win) and Own the Outcome decide trade-offs;
neither is a licence to claim what is not evidenced.

## Hard rules
1. **Never access drivendata.org by script or agent** (Terms of Use prohibit robots/automatic means "for any purpose, including monitoring or copying"). `scripts/refresh_source_feed.py` has a hard guard; keep it. Leaderboard/forum/submission pages are links for a human.
2. **Never upload a submission, and never state or invent a leaderboard score, PR, merge or deployment without evidence.** Scores are owner-reported (`registry/live_scores.json`); unknown stays unknown.
3. **Pre-register before running** any gate (`knowledge/03_preregistration_topology_gate.md` is the template), use fresh seeds for confirmation, and disclose deviations/bugs (see Addendum A).
4. **Paired comparisons and controls only** on the holdout: the dotted-H19-5 base is leaky (trained on all labels); catalogue-internal truth overstates real-world enrichment.
5. A renamed or re-thinned reference is not new work. New files must be labelled *unscored*, carry a unique content-hashed name and a note of at most 200 characters.
6. Every external claim needs a row in `registry/sources.json` with an honest status (`read`, `listing verified`, `secondary quote only`, `not read`, `UNVERIFIED`).
7. Flag irregularities in `registry/irregularities.json`; do not smooth them over.

## Commands
```
python scripts/restore_data.py [--verify]      # hash-pinned inputs into GEMS_DATA_DIR (default ./data_cache, git-ignored)
python -m pytest -q && ruff check src scripts tests
python scripts/verify_downloads.py             # standalone verification of docs/downloads
python scripts/build_site.py                   # rebuilds docs/*.html from JSON only (no rasters needed)
```

## Definition of done for a candidate file
Exact 0.0/1.0 (or sanitised probabilities) inside the footprint, NaN outside with nodata=NaN, an all-finite fallback, a zip with exactly one GeoTIFF, a checks JSON,
`verify_downloads.py` passing, no pixel on a catalogue cell, a documented hypothesis and its holdout gate result, and an entry in the correct manifest (`docs/downloads/manifest.json` for a weekly slot; `docs/downloads/h28_1_candidate_manifest.json` for the separate H28-1 research file).

## Next steps inherited from this session
`knowledge/06_limitations_and_access.md` -> "Prioritised next steps for Session 4". Do those first.

## Session-3 additions to the hard rules
* **Every scored raster used in an argument must be hash-authenticated.** `scripts/fetch_scored_corpus.py` accepts a sibling file only if its SHA-256 equals a `registry/live_scores.json` row; unmatched rows stay listed as unmatched. Never match by filename.
* **Report both truth assumptions for any modelled score.** `geometric` (uniform-truth retention for every pixel change) is validated only for *unbiased* removal such as thinning; `hybrid` (geometric for thinning, measured OOF efficiencies for targeted steps) is the right charge for *targeted* pruning. Quoting one without the other hides the only term the two disagree about.
* **A model is not a score.** `evidence/candidate_model_scores.json` and `evidence/budget_optimum.json` are calibrated models that reproduce live anchors; they are never to be quoted as leaderboard results.
* **Negative results are deliverables.** H27-6, H27-7 and H27-9 are recorded in `registry/hypotheses.json` with the measurement that killed them, so no session repeats the work.
* **H28-1 consumed the preregistered OOF seeds 140–149.** Its +0.00295 mean paired DTI result is catalogue-internal and mixed (3/4 folds, 9/10 seeds); do not reuse those seeds as a fresh confirmation. The next H27-10 annulus test is reserved for fresh seeds 150–159; a subsequent CNN/FaultSEG detector test needs a separate fresh set (e.g. 160–169), preregistered before either run.
* **Keep the H28-1 full-map file separate from all weekly slots.** It is a fixed full-fit research candidate, not a live score or a replacement for the four existing slots; no upload is automated.
