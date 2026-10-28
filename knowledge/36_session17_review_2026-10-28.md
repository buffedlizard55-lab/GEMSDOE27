# Session 17 — three-pass review and run card (2026-10-28)

## Decision

**No new geological experiment or TIFF was produced. No submission is approved, and no weekly slot was used.** The prompt's required single-method lane paragraph is absent, so no method was inferred. The existing H33-1 TIFF is research-only and remains **NOT OK TO SUBMIT** because its frozen whole-FID HOLDOUT-DTI gate failed. The historical peer audit is descriptive and does not establish an organizer score.

### Relationship to the earlier Session 17 baseline review

The earlier Session 17 review on the base branch observed that ignored `data_cache/` inputs were absent in that checkout, so raster verification was blocked there. In this continued workspace, the pinned mirror cache was restored and hash-checked, the shared 32-feature matrix was prepared, and raster audits then ran successfully. This is a later environment state; it does not imply the earlier missing-cache observation was incorrect or that owner-mirror data are organizer-authenticated. The current review supersedes the baseline for the repository state recorded here.

## Pass 1 — implementation and evidence assembly

- Read the README's session-start brief and used the restored shared feature matrix rather than building a private feature stack. The prepared matrix has 5,167,373 rows, 32 features, a 3,730×3,292 EPSG:32611 grid, and SHA-256 `83ed2704ee2de03cfb8c1f2966fcf71813501df97c1c35400e6c0415393f6dc`.
- Added the pairwise final-dot screen for all 12 SHA-pinned historical peer rasters, using the repository's shared directed 3-px comparison and the stated strict stops (>0.90 absolute binary Spearman or >70% directed dot overlap). Historical raster values are compared only inside the shared footprint.
- Hardened `scripts/verify_peer_relations.py`: each cached file must match its registry SHA-256 before and after reading; peers and candidate must match template CRS, shape, transform and band count; every in-footprint peer/candidate value must be finite and exactly binary. NaN outside the footprint remains allowed for historical encodings.
- Regenerated the peer relation evidence and site. The executive table now has pinned download links, owner-reported values, unknown organizer-score estimates, pinned-scope uniqueness results and an explicit no-reuse decision for all nine selected sites. Same-repository peers are disambiguated by registry ID.
- Kept the four registered hypothesis rows data-driven. The page records their layers, targeted signatures, missing-fault rationale, novelty limits, mimics, qualitative priority, cost and data gates; it asserts no numeric expected DTI gain.

## Pass 2 — defect, edge-case and independent-byte review

- Added synthetic tests for NaNs outside the footprint, non-finite/soft values inside it, and shape mismatch. Also retained tests for directionality, exact in-footprint identity, strict subset accounting and the duplicate thresholds.
- Rechecked the H33-1 TIFF independently: one float32 band on the exact EPSG:32611 template grid; all-finite values in [0,1], exact binary footprint values, zero catalogue overlap, 37,654 emitted dots, no nodata tag, and SHA-256 matching the run card (`1373358188a96b20414834b3e0159065d87470fe695153262ced7b46bc1eb492`).
- The fail-closed readiness audit checked 22 cards. H33's byte checks pass; its publication decision and selector authorization are both false. `verify_downloads.py` reported 0 failures. Those are format/audit results only—not a holdout pass or organizer receipt.
- Fixed duplicated punctuation in hypothesis data gates and tested it. The generated site's internal links resolve, and its output is deterministic.

## Pass 3 — requirement re-check and scientific decision

### H33-1: prior HOLDOUT-DTI, not rerun

The prior H33-1 result is labeled **HOLDOUT-DTI**, evaluator `gems27.metric.dti_binary v1` with α=0.2, β=0.8 and a 3-px (300 m) triangular kernel, whole-FID buffered hide-and-recover with a 6-px training buffer, seeds 520–529, and 134,150 withheld-positive occurrences. Candidate pooled DTI was 0.0252105783 versus control 0.0414457522; paired candidate-minus-control was −0.0162351739 with a 95% CI of [−0.0175755532, −0.0144486915]. The gate failed. This is not a leaderboard score or a justified score estimate.

The earlier feature-alone canary tested six H33-1 additions; the maximum direction-invariant AUC was 0.567868, below the 0.90 stop. The saved pre-placement continuous-surface maximum was 0.1103810478 against `g27_tv2_d15`. This review did **not** recompute that surface statistic. The post-placement recheck, freshly rerun against 12 pinned final-dot rasters, found maximum directed 3-px overlap 0.0 and maximum absolute binary Spearman 0.009390; no duplicate stop. The pin set is not a complete global registry.

### Historical submissions and the reported GEMSDOE32 value

The table in `EXECUTIVE_SUMMARY.md` covers GEMSDOE24/25/27/28/30/31/32/33/36. It labels the claims OWNER-REPORTED, leaves organizer-score estimates unknown, links the pinned historical files for download, and reports uniqueness only within the 12-raster final-dot snapshot. All nine selected per-site historical bests trigger at least one duplicate stop against the other 11 pinned files. Several score-to-file associations remain disputed; the user-supplied 0.3195 and 0.4413 leaderboard maxima conflict and have not been confirmed from a receipt.

For the GEMSDOE32 explanation, the measured pinned dot set (37,654 dots) is a strict subset of the GEMSDOE25 d=2.8 set (44,090 dots): 6,436 removed dots are within 2 pixels of catalogue cells, and the nearest retained dot is 2.236 px away. The intermediate GEMSDOE31 set removes 3,891 dots within 1 px; GEMSDOE32 then removes 2,545 more at 2 px. The corresponding 0.2600 → 0.2708 → 0.2778 values are OWNER-REPORTED, not causal evidence. The task attributes 0.2778 to GEMSDOE32, while the peer audit labels that raster UNSCORED; no organizer receipt resolves the association. A collar reducing redundant or low-yield mass is plausible, but geometry cannot prove why a score was reported.

### Research gates and next steps

Four formulations remain ranked qualitatively in `registry/next_hypotheses.json`; no numeric gain is claimed. Official GDR #1391 packages and raw conditioned-drainage/fan-apex inputs were not present or freshly verified. The GDR host is outside this sandbox's allowlist, and existing detrended-elevation bands do not establish routed drainage. Treat those ideas as unavailable here, not viable recommendations. Cached gravity/radiometric feature families do not override the missing lane assignment. Future work needs an explicit method paragraph, confirmed free/official data availability and hashes before data-gated hypotheses are treated as viable, preregistration on unused seeds, feature-alone canaries, shared evaluator/writer, matched current-best whole-FID holdout, and current complete pre- and post-placement uniqueness screens. Only a separate selector can authorize a slot.

## Verification record

- `python -m pytest -q`: **213 passed**.
- Ruff: **passed** for the changed builder, peer-audit script and tests.
- `py_compile` and `git diff --check`: **passed**.
- `scripts/verify_downloads.py`: **0 failures**.
- `scripts/audit_submission_readiness.py`: **22 cards checked; 0 selector-authorized; H33 byte checks pass, publication false**.
- `scripts/verify_peer_relations.py`: **12 peers; 2 identical in-footprint pairs; 11 strict-subset relations**.
- `scripts/build_site.py`: generated six pages, root index and executive summary; deterministic output test passed.

Machine-readable audit/run card: [`evidence/session17_run_card_20261028.json`](../evidence/session17_run_card_20261028.json). Detailed pairwise raster evidence: [`evidence/peer_relations_20261028.json`](../evidence/peer_relations_20261028.json). The pre-existing H33 run card, canary and holdout records remain the source for its historic experiment; this session did not rerun the experiment.

## Limitations and immediate next actions

1. Obtain the missing single-method lane assignment before any experiment; do not infer it from the hypothesis ranking.
2. Verify official-source download availability and bytes (including provenance/license) from an authorized environment before proposing external layers as usable.
3. Treat peer coverage as finite: 12 pinned historical rasters are not all submissions, and their continuous pre-placement surfaces are unavailable.
4. Keep all historical score claims provisional until tied to an organizer receipt; do not project a leaderboard value from HOLDOUT-DTI.
5. Do not submit or spend a slot. The existing H33-1 result is negative, and no selector authorization exists.
