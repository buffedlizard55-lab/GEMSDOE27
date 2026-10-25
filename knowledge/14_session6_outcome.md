# Session 6 outcome and carry-forward (2026-10-25)

## Pass 1 — implementation and verification

1. Read the repository README and AGENTS rules first. Restored all 16 pinned file entries plus the assembled training feature artifact through the repository's GitHub mirror process and verified their hashes. Built the prepared 32-band feature matrix at `data_cache/prepared/features.npy` (shape 5,167,373 × 32; SHA-256 `83ed2704ee2de03cf8b1c8f2966fcf71813501df97c1c35400e6c0415393f6dc`). These are owner-mirrored inputs, not organizer-authenticated bytes.
2. Audited the requested GEMSDOE32 H33-2-B2 files from the sibling GitHub repository, without copying them into GEMSDOE27. The artifact is a deletion-only 200 m catalogue-flank prune of a 0.2708-labelled base, not a new vent detector. Its owner audit reports a calibrated projection of 0.274673, while the submission manifest receipt is null and its model/validation row has no live DTI. The requested 0.2778 attribution remains user-reported and unconfirmed. To correct the initial provenance uncertainty, five cited files were directly retrieved through the GitHub REST Contents API at immutable commit `d781d41e809366b2d5430fbca8bf0ebccd25202f`; Git blob IDs and raw-byte SHA-256 values are recorded in `evidence/gemsdoe32_h33_source_check.json`. This authenticates the owner-repository snapshot, not organizer results. Details: `knowledge/13_h33_score_review_2026-10-25.md`.
3. Screened three in-lane topology hypotheses and preregistered only H29-1 in `knowledge/12_preregistration_H29-1.md` before running the holdout. Implemented shared `holdout.make_split(..., feature_buffer_px=...)` support with distinct exact scoring and buffered feature masks, plus the reusable `src/gems27/relay_consensus.py` transform. Buffer defaults to zero to preserve prior runs; the new test froze a 3-pixel feature buffer.
4. Ran one frozen experiment on seeds 160–169, 40 fold/seed cells, using the cached feature stack and existing H28 edge-cache loader, OOF detector, T-v2 graph code and DTI evaluator. Results: H29-1 candidate pooled HOLDOUT-DTI 0.095266 versus same-run baseline 0.105108; paired Δ −0.009842; seed-cluster 95% CI [−0.010714, −0.008880]. The feature-only leakage-canary AUC was 0.500057. The hypothesis is rejected; see `evidence/h29_1_relay_consensus_holdout.json`.
5. Before raster placement, the H29-1 candidate surface had 229 dots; all 229 were within 3 pixels of the GEMSDOE27 H27-8 all-increments registry raster (SHA-256 `f881810d6713a4bd8d6f9fd15bca99cc928ea052473bbd6a82c738d54dd4067b`). This crosses the protocol's >70% duplicate threshold. Execution stopped: no final candidate raster, GeoTIFF, zip, weekly slot, rank-correlation result, or final-map comparison was produced. This is the required duplicate-stop outcome, not a missed submission.
6. The reviewed registry corpus came from codeload archives of the nine requested sibling GitHub repos. The pre-placement scan stopped at the first duplicate as required; it did not continue through every registry raster. No claim of complete similarity coverage is made.

## Pass 2 — review for bugs and assumptions

- Unit tests caught and corrected a test-fixture expectation: a reciprocal row can be independently supported by another, distinct component pair even though it cannot self-corroborate its mirror. The implementation correctly compares unordered component pairs, endpoints, midpoint distance and axial strike.
- The new holdout API keeps the visible-label scoring mask unchanged while withholding buffered neighboring visible labels from catalogue-feature construction. Tests verify this separation and that zero-buffer calls preserve legacy semantics.
- The random null is a matched eligible-link-count control, not a new experiment. The output's DTI is pooled from TPw/FPw/FNw; confidence intervals resample seed clusters, not individual pixels.
- No TIF was generated because the holdout gate failed and the lane-duplicate rule independently required stopping before placement. The registry/source mirrors are not organizer receipts. No DrivenData endpoint was contacted.

## Pass 3 — compare with the full request

- The project now records the H33-2-B2 evidence boundary, its likely mechanism, and the mismatch between the user-reported 0.2778 and the sibling's owner-audited 0.274673 projection/null receipt. It does not present the user score as confirmed.
- A new, unique, slot-ready TIF was **not** generated. Doing so after a measured negative holdout and a 100% proximity duplicate trigger would violate the explicit no-duplicate stop rule and the instruction not to promote unvalidated work. This negative result is the deliverable.
- The current 0.4413 leaderboard-high claim remains user-reported; this agent did not access DrivenData. The previous 0.3195 entry and October 4 sibling leaderboard snapshots remain historical, secondary data.
- The topological feature screen is not yet exhausted, but the next session must choose a genuinely distinct method rather than loosen H29-1 thresholds. Candidate H29-2 and H29-3 were not run and remain planning ideas only; do not imply their gains.

## Remaining work / limitations

1. **Score receipt:** only an authorized owner can supply the organizer receipt or exact submission-page record for H33-2-B2 and a current leaderboard snapshot. The agent must continue to avoid automated DrivenData access.
2. **No fresh upload:** no new TIFF is approved or produced. Weekly-slot selection remains a separate selector step and was not performed.
3. **Full registry scan:** the uniqueness check stopped at the first duplicate by protocol. If a different method is preregistered, rerun the pre-placement test against all available rasters in each requested site's current registry; verify version commits and record any unavailable sources.
4. **Official inputs:** cached data are pinned from owner sibling repositories, not authenticated through the gated competition download. No training-data credential or organizer receipt is available to this agent.
5. **Outside research:** H29-2 dimensionless gap-to-system scale and H29-3 4-/8-connectivity robustness are untested planning hypotheses, not recommendations. A fresh candidate must be preregistered, run on unused seeds, pass feature-alone AUC, paired DTI/CI and uniqueness gates, and remain separate from a weekly slot until the selector acts.

## Run card

```json
{
  "hypothesis": "H29-1 convergent-tip relay support",
  "mechanism": "Independent visible fault-tip links converging in a short, aligned corridor might identify an unmapped relay strand; the frozen test was negative.",
  "named_non_fault_mimic": "Drainage/canyon alignment or map-digitisation snapping",
  "holdout_dti_and_ci": "HOLDOUT-DTI, evaluator src/gems27/holdout.py+metric.py (metric SHA-256 4b0a600d7fa92e1338b3f8ffeed3df76031ab94725f8143df1fc194c40bfb101), 123,150 withheld-positive cell instances, seeds 160-169, pooled baseline 0.105108 (95% CI 0.102007-0.108071), candidate 0.095266 (95% CI 0.092017-0.098562), paired delta -0.009842 (95% CI -0.010714--0.008880)",
  "leakage_canary": "HOLDOUT-CANARY binary feature AUC 0.500057; not a DTI score",
  "correlation_overlap_vs_registry": "LANE-CHECK: 229/229 candidate dots (100%) within 3 px of GEMSDOE27 all-increments registry raster; duplicate stop (>70%). Spearman and final-raster checks not run after stop.",
  "raster_sha256": "NONE; no GeoTIFF generated",
  "validator_output": "NOT RUN; no raster exists; no submission validation is claimed",
  "submission_name": "NONE",
  "submission_note": "NOT GENERATED: holdout negative and pre-placement duplicate guard triggered; do not submit.",
  "verdict": "negative"
}
```
