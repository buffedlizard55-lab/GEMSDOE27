# Session 19 review — 2026-10-29 (repo audit, no new experiment)

## Scope and decision

- **Request:** "Review the repo", plus a standing request to produce a unique GeoTIFF that scores above the stated leaderboard figures, and to open and merge a pull request.
- **Decision:** no new TIFF, no experiment, no slot authorization. The prompt still does not contain the single-method lane paragraph its parallel-run protocol refers to (`IR-2026-10-29-lane-paragraph-missing`). Without that lane, any new raster would be an unregistered method. The charter budget (3 experiments / 2 h) also requires a registered lane.
- **Outcome:** **no file is OK to submit.** The only generated unique TIFF, H33-1 (`gems27-h33-bss-complement-20261027-9ba8480691ed-allfinite.tif`), failed its holdout efficacy gate (HOLDOUT-DTI 0.025211 vs control 0.041446). Its uniqueness result does not authorize submission.

## Checks run this session (reproducible)

| Check | Command | Result |
|---|---|---|
| Branch state | `git status`, `git rev-parse` | Clean; `HEAD` = `main` = `494ec17625bf8fe9e19510ec3f39912451c4f7f7` |
| Lint | `ruff check src scripts tests` | All checks passed |
| Tests | `python -m pytest -q` | Before restore: 225 passed, 3 skipped. After restore: **228 passed** (the 3 skips needed restored inputs) |
| Input restore | `python scripts/restore_data.py` | 17 inputs printed OK, 0 non-OK; hash-pinned owner-mirror copies (not DrivenData) |
| Download verifier | `python scripts/verify_downloads.py` | 288 PASS lines, **0 FAIL / 0 failures** |
| Independent raster re-read | rasterio, inline script (see below) | 22 `-allfinite` GeoTIFFs: all single-band float32, 0 NaN, values in [0, 1], grid = template |

Template grid, read from `data_cache/sample_submission.tif`: EPSG:32611, shape 3730 × 3292, transform (100, 0, 243350; 0, −100, 4508550), float32.

Independent re-read covered every file matching `docs/downloads/**/*allfinite.tif`. Sample SHA-256 prefixes: H33-1 `1373358188a9`, H31-1 `2c002b027924`, H29-XG not written (no file).

## Findings and irregularities for review

1. **Leaderboard figures conflict.** The prompt cites 0.4413 and 0.3195 as current highs. Repo evidence (`evidence/focus_sites_executive_summary_20261026.json`) records both values and their sources. Neither has an organizer receipt here. This agent does not access DrivenData (charter item 5). Action: a human should read the live leaderboard and record the value as ORGANIZER-CONFIRMED or leave it unknown.
2. **Portal error cause unconfirmed.** The "Predicted values must be in range [0, 1]" error is documented in the registry as an unconfirmed cause. The `-allfinite` variants pass the local range check. The `-nan` variants contain NaN outside the footprint. The file the user uploaded is not identified, so it is unknown which variant caused the error. Action: confirm which file was uploaded before any future upload.
3. **Owner-reported 0.2778 (GEMSDOE32) is not reproducible here.** The GEMSDOE32 file is not in this repository. The repo's own analysis says it is the d=2.8 family minus a 2 px catalogue collar, with the same lineage as GEMSDOE25 (`README.md`, `EXECUTIVE_SUMMARY.md`). Copying it fails the uniqueness rule.
4. **Byte-identical peer pairs.** GEMSDOE25 = GEMSDOE30 (in-footprint dots) and GEMSDOE28 H27-4 = GEMSDOE31. These were byte-measured in earlier sessions (`verify_peer_relations.py`). Both pairs remain documented; neither file should be resubmitted.
5. **Restore touches external hosts.** `restore_data.py` downloads hash-pinned copies from the owner's GitHub mirror. The pins were checked (all 17 OK), but the bytes are **not organizer-authenticated**.
6. **Parallel-run prompt is missing its lane paragraph.** The 'single method paragraph' in the protocol is absent from this prompt, as the README already records. No lane was assigned.

## Verification limits

- No DrivenData page, leaderboard, or submission form was accessed (charter item 5).
- Official sources named in the prompt (competition pages, the reference solution repo, the NLR PDF, the USGS GeoDAWN page, GBCGE INGENIOUS, EPSG:32611, the Tversky index) were not re-fetched in this session. Any claim that depends on them should be treated as unverified here.
- Holdout DTI values are local measurements (HOLDOUT-DTI), not leaderboard scores.

## Next steps

1. Human: read the live leaderboard and record the highest value as ORGANIZER-CONFIRMED or as unknown.
2. Human: assign a single-method lane (a full paragraph) for the next session. Without it, no new TIFF should be generated.
3. Human: confirm which file caused the portal error.
4. Agent (next session, once a lane exists): pre-register, run one holdout experiment against the H33-1 / current-best control on the shared holdout, apply the 3 px / 0.90 duplicate stops before and after placement, and write a run card.

No candidate is OK to submit. Organizer receipts and current leaderboard values remain unknown.
