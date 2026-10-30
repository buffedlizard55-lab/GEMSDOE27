# Session 20 repository review — 2026-10-30

Handoff for the next session. It supersedes `41_session19_repo_review_2026-10-29.md` as the latest review. The charter in `README.md` and the hard rules in `AGENTS.md` still apply.

## 1. Bottom line

- **No file is OK to submit.** This is unchanged. The one new-to-the-repo finding is that the only generated unique TIFF (H33-1) is format-valid and unique against the 12 pinned rasters, but it **lost** on the holdout (HOLDOUT-DTI 0.0252 against control 0.0414).
- **No new TIFF was generated and no experiment was run.** The 2026-10-30 prompt again says "Your lane is the single method paragraph below", but no paragraph follows. Under the protocol the agent may not choose a lane. See `IR-2026-10-30-lane-paragraph-still-missing`.
- **Highest owner-reported value in the 2026-10-30 list: 0.2778 (GEMSDOE32).** The prompt also states 0.4413 and 0.3195 as "current leaderboard high". These conflict with each other and were not read from the leaderboard. Treat both as unverified.
- **What this session added:** an auditable ledger of all 160 rows in the prompt's list (`registry/owner_reported_scores_20261030.csv`), 5 tests that guard it (`tests/test_owner_ledger.py`), 9 new irregularity records (`registry/irregularities.json`), and the pointers in `README.md` and `AGENTS.md`.
- **No upload, no slot, no DrivenData access.** Every leaderboard figure here is OWNER-REPORTED. None is an ORGANIZER-CONFIRMED receipt, and none is a leaderboard projection.

## 2. Verification run this session

Environment: Python 3.11.2 venv, `requirements.txt` installed (rasterio 1.4.4, numpy 2.4.6, scipy 1.17.1). All checks were run in the sandbox against the repo at commit `bdbc3c9`, plus this session's additions.

| Check | Command | Result |
|---|---|---|
| Hash-pinned inputs | `python scripts/restore_data.py` | 17/17 files restored; every SHA-256 matched `data/manifest.json` |
| Peer rasters | `python scripts/fetch_parallel_registry.py` | 12/12 pinned peer rasters fetched from codeload archives (ledger in the run log) |
| Download verifier | `python scripts/verify_downloads.py` | 288 PASS lines, **0 failures** |
| Peer byte audit | `python scripts/verify_peer_relations.py` | reproduced: 12 peers, 2 identical in-footprint pairs, 11 strict-subset relations. Only `created_utc` changed; the cosmetic diff was reverted (`IR-2026-10-30-peer-audit-timestamp-churn`) |
| Unit tests | `python -m pytest -q` | **234 passed** (229 existing + 5 new ledger tests), 0 skipped |
| Lint | `ruff check src scripts tests` | passed |
| Site build | `python scripts/build_site.py` | rebuilt 6 pages, root index, executive summary; only the irregularity list changed |
| Readiness gate | `python scripts/audit_submission_readiness.py` | `evidence_passed` = [], `slot_authorized` = [] |
| DrivenData access | workflows and scripts | no workflow or script contacts drivendata.org; the guards in `refresh_source_feed.py` and `fetch_vector_faults.py` remain |

## 3. Independent re-read of the one generated TIFF (H33-1)

File: `docs/downloads/research/gems27-h33-bss-complement-20261027-9ba8480691ed-allfinite.tif`. I opened it with rasterio. I did not use the repo's helper for these checks.

| Property | Value | Matches the run card? |
|---|---|---|
| SHA-256 | `1373358188a96b20414834b3e0159065d87470fe695153262ced7b46bc1eb492` | yes (matches `EXECUTIVE_SUMMARY.md`) |
| Bands / dtype | 1 band, float32 | yes |
| Shape | 3730 × 3292 (same as the template `data_cache/sample_submission.tif`) | yes |
| CRS | EPSG:32611 (same as the template) | yes |
| Transform | identical to the template | yes |
| NaN count | 0 | yes (all-finite variant) |
| Value range | min 0.0, max 1.0; values {0, 1} | yes |
| In-footprint cells (template is finite) | 5,167,373; non-finite in footprint: 0 | yes |
| Non-zero outside footprint | 0 | yes |
| Dots (value = 1) | 37,654 | yes |

**Format validity is confirmed. This is not a score.**

Uniqueness recomputed independently (directed 3-px overlap: share of the H33 dots within 3 px of a peer dot; binary Spearman over the footprint):

| Peer raster | Peer dots | H33 dots within 3 px | Binary Spearman |
|---|---|---|---|
| g24_d15 | 60,069 | 0.00% | −0.0093 |
| g25_d28 | 44,090 | 0.00% | −0.0079 |
| g27_tv2_d15 | 61,328 | 0.00% | −0.0094 |
| g28_h27_4_r1 | 40,199 | 0.00% | −0.0076 |
| g28_h32_1 | 42,294 | 0.00% | −0.0078 |
| g28_h36_1 | 37,660 | 0.00% | −0.0073 |
| g28_h38_1 | 37,860 | 0.00% | −0.0074 |
| g30_d28 | 44,090 | 0.00% | −0.0079 |
| g31_h27_4 | 40,199 | 0.00% | −0.0076 |
| g32_h33_2_b2 | 37,654 | 0.00% | −0.0073 |
| g33_h33d | 41,865 | 0.00% | −0.0077 |
| g36_anderson | 38,854 | 0.00% | −0.0075 |

The 0.00% overlap is **by construction**. H33-1 is the complement of the peer dots, so it is disjoint from them. That is a uniqueness result only within the 12 pinned rasters. It is not evidence that the dots are better placed.

**Holdout record (HOLDOUT-DTI; copied from `evidence/h33_e2_holdout_520_529.json` and checked against it):** candidate pooled 0.0252106, control B pooled 0.0414458, paired CI95 [−0.0175756, −0.0144487], 134,150 withheld-positive occurrences, 0 of 10 seeds positive, 0 of 4 folds positive, `gate_efficacy_pass: false`. This is the recorded run. It was not re-run this session.

## 4. The metric: what is verified and what is not

- The formula in `src/gems27/metric.py` is DTI = TPw / (TPw + 0.2·FPw + 0.8·FNw), with a kernel k(d) = max(1 − d/300 m, 0) at 3 px. Known catalogue pixels are masked from both credit and cost.
- **Verified this session:** the α = 0.2 false-positive and β = 0.8 false-negative weights appear in DrivenData's reference solution notebook, cell 16 (`alpha = 0.2  # weight for false positives in Tversky loss`, `beta = 0.8  # weight for false negatives`). Source: https://github.com/drivendataorg/gems-prize-reference-solution (archive commit `aebe92f7c8a990f0e3443451b7a825d9afd6336b`, read from codeload).
- **Not verified:** the 300 m distance kernel and the masking rule. The notebook does not contain them. The repo cites the competition's problem page for them. AGENTS.md forbids this agent from accessing drivendata.org, so that page was not re-read. A human should check the "Performance metric" section against `metric.py`.
- **Calibration warning:** the holdout's absolute level (about 0.04 for the controls) is roughly 6–7 times below the owner-reported leaderboard values (about 0.27). The holdout ranks candidates against a control. Its calibration to the organizer score is unknown.

## 5. Why 0.2778 is the top owner-reported value, and whether it can be beaten

**What the data show (owner-reported scores; byte-level dot audit in `evidence/peer_relations_20261028.json`):**

1. One family, three owner-reported points. GEMSDOE25/GEMSDOE30 is the d = 2.8 field with 44,090 dots (0.2600). Removing its dots within 1 px of the catalogue gives 40,199 dots (0.2708, the GEMSDOE28 H27-4 and GEMSDOE31 files). Removing dots within 2 px gives 37,654 dots (0.2778, GEMSDOE32). Every removed dot is within 2 px of a catalogue cell, and the nearest kept dot is 2.236 px away.
2. Identical dot sets carry identical scores. Two pairs are byte-identical in-footprint: GEMSDOE25 = GEMSDOE30 (both 0.2600), and GEMSDOE28 H27-4 = GEMSDOE31 (both 0.2708). This is consistent with the score depending only on the binary dot set. It is two pairs, so it is consistent evidence, not proof.

**Mechanism (hypothesis, consistent with the metric):** the formula penalises false positives at 0.2 but does not mask dots that sit 1–2 px from a catalogue cell, unless the dot is on a known pixel. A dot that is near a known fault, with no unknown truth inside 3 px, adds false-positive mass and earns no credit. Removing such dots raises DTI. This fits the monotone pattern in point 1.

**Non-fault mimic (must be tested before it is believed):** fewer dots means higher precision in general, so the same gain can come from simply thinning the field, with no geology involved. The next test has to separate "dots near the catalogue are wasted" from "fewer dots are better".

**Can 0.2778 be beaten while staying unique?** Not with a pruned variant of this family:

- Any further pruning of GEMSDOE32 gives a subset. Its directed 3-px overlap with GEMSDOE32 is 100%, which fails the 70% duplicate stop. A 3-px collar version fails for the same reason.
- To beat 0.2778 uniquely, a candidate must place dots away from the GEMSDOE32 set. The only such candidate tested so far, H33-1, scored worse on the holdout (0.0252 against 0.0414).

Conclusion: the owner-reported 0.2778 has a plausible mechanism and a clean dose-response, but no unique candidate has demonstrated a holdout gain over the current best. Nothing in the repo supports a claim that a file will beat 0.2778.

## 6. Current download decision

| File | Estimate | Unique? | OK to submit? |
|---|---|---|---|
| H33-1 all-finite GeoTIFF (research only) | HOLDOUT-DTI 0.025211 against control 0.041446 (negative) | Yes, within the 12 pinned rasters (0% overlap by construction) | **NOT OK TO SUBMIT** |
| Historical site files (GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36) | OWNER-REPORTED values from the prompt; not organizer receipts | Already in the pinned set, so not new | **NOT OK — do not resubmit** |
| Any new candidate | none | none | **NOT OK — no lane, no holdout gain** |

The authoritative table remains `EXECUTIVE_SUMMARY.md`, generated from the run cards.

## 7. Owner-reported top values from the 2026-10-30 prompt

The full list is in `registry/owner_reported_scores_20261030.csv`. Top 12 by value (138 scored rows, 22 blank):

| Score | Site | File label (as listed) |
|---|---|---|
| 0.2778 | GEMSDOE32 | h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros |
| 0.2750 | GEMSDOE36 | anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros |
| 0.2710 | GEMSDOE28 | h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan |
| 0.2708 | GEMSDOE31 | h27-4-solo-d28-20261004-8acb75e1-nan |
| 0.2708 | GEMSDOE28 | h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan |
| 0.2707 | GEMSDOE28 | h38-1-hf-euler-r30-r1-20261003-56a9f473edc7-nan |
| 0.2649 | GEMSDOE28 | h32-1-prethin-tip-euler-d2-8-20261003-31e35eee884e-nan |
| 0.2632 | GEMSDOE33 | h33d-analog-tip-stepover-r30-20261004-cb490425926e |
| 0.2600 | GEMSDOE25 | dotted-h19-5-d2-8-20261002-e56ea318af89-nan |
| 0.2600 | GEMSDOE30 | d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca |
| 0.2600 | GEMSDOE29 | efd28-repro-20261003-1cc7dc534d51-nan |
| 0.2560 | GEMSDOE29 | wormrank-d28-20261003-59dcaf6dd11d-zeros |

The prompt's 0.4413 and 0.3195 values do not appear in the list. Neither was matched to a file.

## 8. Irregularities

Nine new records were added to `registry/irregularities.json` (IDs `IR-2026-10-30-*`):

- `lane-paragraph-still-missing` (high) and `leaderboard-high-conflict-restated` (high): both block progress.
- `uniqueness-scope-12-rasters` (high): the prompt asks for uniqueness against every listed site, but only 12 rasters are pinned. The 113 owner repos behind the listed Pages sites all answered HEAD requests (200) on codeload, so fetching and hashing them is feasible. Content-Length is not returned, so total download size is unknown.
- `blank-scores-in-prompt` (medium): 22 rows have no score (10 bare ":" lines and 12 files without a score).
- `hash-suffix-reused-across-sites` (medium): for example `7f00890a` on two sites, both 0.1563. The repo has no byte check for that pair.
- `owner-ledger-not-in-live-scores` (medium): `live_scores.json` is missing most 2026-10-25 to 2026-10-30 values. The ledger holds them now.
- `readme-not-verbatim-prompt` (low): the README keeps a condensed brief rather than the full prompt. Reason in the record.
- `sandbox-cannot-open-pages-or-drivendata` (info): the Pages hosts are not on the sandbox allow-list, so the owner download links were not fetched.
- `peer-audit-timestamp-churn` (low).

## 9. What is needed to make progress

1. **An explicit single-method lane paragraph** from the user. Without it, no experiment may run under the protocol. Once it is supplied, preregister it with fresh seeds (not 520–529, which H33-1 consumed), run the feature-alone leakage canary, and compare against the matched current-best holdout.
2. **A leaderboard row copied by a human** (rank, score, date). This resolves 0.4413 against 0.3195.
3. **Full uniqueness scope (optional, feasible).** Fetch the 113 owner repos at pinned commits, locate each listed TIFF by filename, hash it, and run the duplicate gate against it. Record any file that cannot be found as a gap.
4. **A preregistered test of the collar mechanism** (section 5) that separates "near-catalogue dots are wasted" from "any thinning helps", using fresh seeds.
5. **Human check of the metric's distance kernel and masking rule** against the official problem page, since this agent may not open that page.

## 10. Sources (manual review)

| Source | Link | Opened in this session? |
|---|---|---|
| Competition page (human only) | https://www.drivendata.org/competitions/306/competition-doe-gems/ | No (AGENTS.md forbids automated access) |
| Leaderboard (human only) | https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/ | No |
| Reference solution (DrivenData, GitHub) | https://github.com/drivendataorg/gems-prize-reference-solution | Yes (README and notebook, archive commit `aebe92f`) |
| Submission-format PDF | https://docs.nlr.gov/docs/fy26osti/96647.pdf | No |
| CRS definition | https://epsg.io/32611 | No (the CRS was read from the TIFF: EPSG:32611) |
| USGS GeoDAWN release | https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and | No |
| INGENIOUS project | https://gbcge.org/current-projects/ingenious/ | No |
| Tversky index | https://en.wikipedia.org/wiki/Tversky_index | No |
| Repo evidence (this session) | `evidence/h33_e2_holdout_520_529.json`, `evidence/peer_relations_20261028.json`, `registry/owner_reported_scores_20261030.csv`, `registry/irregularities.json` | Yes |
