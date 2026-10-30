# Session 20 verification record — 2026-10-30

## Decision

**No experiment was run, no candidate TIFF was generated, and no file is OK to download and submit.** The prompt's protocol says the lane is "the single method paragraph below", but no method paragraph is present (irregularity `IR-2026-10-29-lane-paragraph-missing`, still open as `IR-2026-10-30-lane-paragraph-still-missing`). Choosing a method ourselves would break the protocol.

This record adds three verified facts that the earlier Session 20 notes lacked: the inputs can be restored, the byte-level verifier passes, and the official leaderboard can be read. It also corrects two earlier statements.

## Verified in this session (commands run from the repository root)

| Check | Command | Result |
|---|---|---|
| Input restore (owner mirror, SHA-256 pinned) | `python scripts/restore_data.py` | All 16 files reported `OK` against `data/manifest.json`. Source archives came from `codeload.github.com`. |
| Download/raster verifier | `python scripts/verify_downloads.py` | `0 failure(s)`. |
| Test suite | `python -m pytest -q` | 229 passed, 0 skipped (after restore). |
| Lint | `ruff check src scripts tests` | All checks passed. |
| Readiness gate | `python scripts/audit_submission_readiness.py` | No slot authorizations (`slot_authorized: []`). |

Limits: restored files are owner-mirror copies. They are not organizer-authenticated and do not come from DrivenData.

## Corrections to earlier notes

1. **Verifier status.** `knowledge/42` and the README paragraph said `verify_downloads.py` was blocked by missing `data_cache/` files. After `restore_data.py`, it passes with 0 failures. The earlier statement applied to a checkout without the restored inputs.
2. **Branch history.** The session branch was not an ancestor of `origin/main`. The trees differed only by the Session 20 README and knowledge additions. The branch was reconciled by merging `origin/main` with `--allow-unrelated-histories`, keeping main's tree (`IR-2026-10-30-unrelated-history-reconciled`).

## Official leaderboard snapshot (read 2026-10-30)

Source: [DrivenData GEMS leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) (column "Best public DW-Tversky").

- #1 `xiaofanhu` **0.4544**; #2 `cfld__` 0.3925; #3 `Batik Shirt Brothers` 0.3915.
- #50 `kpomazi` **0.3195**. This is the rank-50 cutoff on the page. It is not the top score.
- **0.4413** does not appear on the page (the first 50 rows were read; the page has further pages).
- No row carries a GEMSDOE team name or handle in the 50 rows read.

So the prompt's claim that "0.3195 is the highest score" is contradicted by the official page, and the 0.4413 figure is unverified. Registered as `IR-2026-10-30-leaderboard-official-snapshot`.

## GEMSDOE32 0.2778

The 0.2778 value remains **OWNER-REPORTED**. The mechanism analysis from earlier sessions is in [Session 19](41_session19_repo_review_2026-10-29.md) and [Session 20](42_session20_repo_review_2026-10-30.md). In short: the GEMSDOE32 dot mask is a strict subset of GEMSDOE25's d=2.8 mask, with 6,436 dots removed at catalogue distances ≤ 2 px. That pattern is consistent with a precision-weighted DTI gain from pruning low-credit dots, but nothing here shows causation. No organizer receipt for 0.2778 exists in the repository.

## What would be needed to beat 0.2778 (and the official #1 at 0.4544)

1. The single-method lane paragraph from the user (blocker).
2. An organizer receipt for any target score (the public page does not show GEMSDOE entries in the rows read).
3. A candidate that beats the current matched holdout control with a paired CI excluding zero, and passes both duplicate stops (3-px overlap ≤ 70%, |Spearman| ≤ 0.90) before and after placement.

No holdout DTI in this repository has been shown to predict leaderboard score, so no leaderboard estimate is given.

## Run card (review only)

```json
{
  "hypothesis": "No new hypothesis tested; review and verification session.",
  "mechanism": "Not applicable.",
  "named_non_fault_process_that_could_mimic_it": "Not applicable.",
  "holdout_dti": "NOT RUN this session",
  "correlation_overlap_vs_registry": "Not measured this session",
  "raster_sha256": null,
  "validator_output": "scripts/verify_downloads.py: 0 failures on restored owner-mirror inputs; no new raster generated",
  "submission_name": null,
  "submission_note": "None; no candidate TIFF generated.",
  "verdict": "negative"
}
```

Sources: [DrivenData competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/), [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), [reference solution](https://github.com/drivendataorg/gems-prize-reference-solution), [submission format PDF (NLR 96647)](https://docs.nlr.gov/docs/fy26osti/96647.pdf), [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [DOE GDR #1391](https://gdr.openei.org/submissions/1391), [EPSG:32611](https://epsg.io/32611), [Tversky index](https://en.wikipedia.org/wiki/Tversky_index).
