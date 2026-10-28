# Session 15 — delivery audit (2026-10-28)

## Scope and decision

The parallel prompt supplies **no actual single-method lane paragraph** after its lane instruction. I did not assign myself another team's lane, spend a weekly slot, tune an old result, or call a model projection a score. The ranked four-hypothesis preregistration and completed H29-5-PROXY negative screen remain in `knowledge/30_lane_2026-10-27_preregistration.md` and `evidence/relief_profile_run_card_20261027.json`. Those are historical research records, not a new confirmation experiment. No untested method has demonstrated a matched current-best whole-FID holdout gain. In particular, the previously generated H33-1 TIFF is unique only against the specified pinned comparison scope and lost to its matched base-32 control; it is **NOT OK TO SUBMIT**.

## Pass 1 — implementation and direct verification

Reviewed the existing executive summary, H33 card, site generator, readiness gate and nine-site raster registry. Fixed a concrete delivery bug: the `EXECUTIVE_SUMMARY.md` download URL was `downloads/research/...`, which resolves at the repository root where that path does not exist. The Markdown link now resolves to `docs/downloads/research/...`. The generated HTML already used the correct docs-relative URL. The decision-table link is now derived from the recorded card and the independent raster-byte check, not a hardcoded filename/SHA-256 pair. If bytes change, the hash no longer matches, the file is missing, or the independent GeoTIFF check fails, no link is published. The research card display uses the same rule. This is a publication-safety fix, **not** an independent geology experiment or an organizer validation.

## Pass 2 — adversarial review

Added tests for the root-relative Markdown download, no-link behavior with missing/changed/failed-validator evidence and exclusion of paths outside `docs/`. Rebuilt the site twice (determinism test). Restored 17 inputs from hash-pinned owner sibling GitHub commits: `scripts/restore_data.py` printed matching hashes for all, including the template, labels and features. `scripts/verify_downloads.py` returned 0 failures; the restored arrays are owner mirrors, **not independently organizer-authenticated**. `scripts/audit_submission_readiness.py` regenerated the fail-closed audit; it did not authorize a weekly slot.

## Pass 3 — requirements and limits

Full suite with restored cache: `194 passed`; `ruff check src scripts tests`: passed; `git diff --check`: passed. No new portal observation or upload. GEMSDOE32's 0.2778 is owner-reported, not receipt-backed: the measured dot geometry is a two-pixel catalogue prune of the older d=2.8 raster. This is plausible DTI allocation, not proof of cause or a guarantee that a different model will outperform it. The user supplied incompatible 0.3195 and 0.4413 leaderboard claims; neither was checked against the portal. No reliable leaderboard-score estimate for any new file can be produced from this holdout. The historic nine-site table is a pinned peer snapshot, not a global uniqueness certificate. No automatic DrivenData access is permitted by the repository policy; the site's current weekly cap and any organizer acceptance require an authorized human to inspect the portal. This review did not perform new literature verification; older source claims retain their recorded source status in `registry/sources.json`.

## Next steps

1. Obtain the missing lane paragraph or an explicit new lane assignment; preregister 3–5 *untried* hypotheses, unused seed range, a geological mimic and matched H31 control before any new experiment. Do not reuse old seeds or retune a losing file.
2. Obtain an organizer-authenticated template and submission-page receipts through an authorized human process (no agent portal automation); reconcile owner-reported file-to-score mismatches.
3. Rebuild a *new* TIFF with the shared writer only if its feature-alone leakage canaries, whole-FID buffered holdout, matched-best paired gate, complete pre/post-placement registry uniqueness, byte validator and separate slot selector all pass. Otherwise publish the negative result without consuming a slot.
