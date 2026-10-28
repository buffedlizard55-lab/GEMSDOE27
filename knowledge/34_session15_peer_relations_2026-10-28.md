# Session 15 review (2026-10-28): reproduction, byte-level peer audit, and the 0.2778 question

Scope: review the repository, reproduce it from pinned inputs, verify every claim this session could reach, answer why the owner-reported 0.2778 file scored highest, and decide whether any file may be submitted. Read with `README.md` and `AGENTS.md`.

## Decision

- **No file is OK to download and submit. No weekly slot is authorized.** No new GeoTIFF was generated. Nothing was uploaded. No DrivenData page was accessed.
- The most recent generated candidate, `gems27-h33-bss-complement-20261027-9ba8480691ed-allfinite.tif` (H33-1), remains **NOT OK TO SUBMIT** (HOLDOUT-DTI 0.025211, below its base-32 control of 0.041446).
- **Why no new candidate was produced.** (1) The parallel-run protocol assigns a lane "the single method paragraph below", but the prompt contains none. Any lane chosen here would be a guess, which the repository records as a collision risk (IR-2026-10-25-01; IR-2026-10-27-02, lane-paragraph entry). (2) A candidate needs a preregistered hypothesis, unused seeds, and a matched current-best control. (3) The most recent different-field candidate (H33-1) scored far below its control. Generating another unscored file would add a file, not evidence.

## Pass 1 — reproduction (all commands run in this session)

| Step | Command | Result |
|---|---|---|
| Environment | `python3 -m venv .venv && pip install -r requirements.txt` | Python 3.11.2; installed |
| Pinned inputs | `python scripts/restore_data.py` | 16/16 inputs OK; SHA-256 matches `data/manifest.json` (owner-mirror copies, not organizer-authenticated) |
| Feature stack | `python scripts/prepare_data.py` | exit 0 |
| Peer rasters | `python scripts/fetch_parallel_registry.py` | 12/12 pinned peers fetched from codeload at pinned commits; cache manifest written |
| Download gate | `python scripts/verify_downloads.py` | 0 failures |
| Readiness audit | `python scripts/audit_submission_readiness.py` | exit 0; slot_authorized = false |
| Site | `python scripts/build_site.py` | rebuilds; only the intended text changed (see Pass 2) |
| Lint | `ruff check src scripts tests` | all checks passed |
| Tests | `python -m pytest -q` | 195 passed, 0 skipped (after restore; before this session's new tests: 189 passed, 3 skipped without rasters) |

## Pass 2 — verified facts about the peer rasters (byte-level)

Source: `scripts/verify_peer_relations.py` → `evidence/peer_relations_20261028.json`. It reuses `gems27.grid`, `gems27.paths` and `gems27.uniqueness.dot_comparison`. The catalogue is `labels.tif == 1`. Scores are owner-reported labels copied from `registry/parallel_submission_registry.json`.

| Pinned file (registry id) | Owner-reported | Dots in footprint | Relation (measured) |
|---|---:|---:|---|
| GEMSDOE25 `g25_d28` | 0.2600 | 44,090 | Parent of the chain below |
| GEMSDOE30 `g30_d28` | 0.2600 | 44,090 | **In-footprint values identical to GEMSDOE25** (different outside-footprint encoding: zeros vs NaN) |
| GEMSDOE31 `g31_h27_4` | 0.2708 | 40,199 | GEMSDOE25 minus 3,891 dots, all within 1 px of a catalogue cell |
| GEMSDOE28 `g28_h27_4_r1` | 0.2708 | 40,199 | **In-footprint values identical to GEMSDOE31** (different SHA-256) |
| GEMSDOE32 `g32_h33_2_b2` | 0.2778 | 37,654 | GEMSDOE31 minus 2,545 dots, all at 2 px; equivalently GEMSDOE25 minus 6,436 dots, all within 2 px |
| GEMSDOE36 `g36_anderson` | 0.2750 | 38,854 | Contains all 37,654 GEMSDOE32 dots plus 1,200 more |
| Others: GEMSDOE24 `g24_d15`, GEMSDOE27 `g27_tv2_d15`, GEMSDOE28 `g28_h32_1`, `g28_h36_1`, `g28_h38_1`, GEMSDOE33 `g33_h33d` | 0.2477, 0.2449, 0.2649, 0.2710, 0.2707, 0.2632 | 60,069; 61,328; 42,294; 37,660; 37,860; 41,865 | Measured: none is a subset of GEMSDOE32 |

Other checks from the same run:
- All 12 peers share the template grid (EPSG:32611, 3730 × 3292).
- The candidate H33-1 has **0.0** directed 3-px overlap with each of the 12 peers. The Spearman in the JSON is the binary dot-field correlation (not the surface rank test); it lies between −0.00734 and −0.00939.

## The 0.2778 question

**What the bytes show.** GEMSDOE32 is the GEMSDOE25 d=2.8 dot field with every dot within 2 px of a catalogue cell removed. The nearest kept dot is 2.236 px from the catalogue, so the removal is a clean collar. The chain 25 → 31 → 32 is nested: each step only removes dots. The owner-reported scores step 0.2600 → 0.2708 → 0.2778 as the removed collar widens from none to 1 px to 2 px.

**Why it may have scored highest (hypotheses, not proofs).**
1. *Mechanism under the stated metric.* A pooled 300 m triangular-kernel DTI rewards dots that land on hidden fault truth. If the hidden truth is mostly unmapped faults (the stated goal), dots adjacent to mapped faults earn little credit. Removing them trades a little recall for precision where it was least likely to be new. This is consistent with the rising owner-reported scores.
2. *Non-fault mimic.* Dots next to mapped faults may sit on fault-parallel topographic or magnetic edges that are real geology but not hidden-truth faults. Removing them could reduce false positives from edge response rather than improve fault discovery. The two mechanisms predict the same score ordering, so the score alone cannot separate them.
3. *Count is not the driver.* GEMSDOE32 has the same dot count as H33-1 (37,654). H33-1 is the complement and scores 0.0252 HOLDOUT-DTI (repository holdout, not organizer), so location matters more than count. This is a HOLDOUT-DTI observation, not an organizer result.

**Can the repository produce a unique file above 0.2778?** Not demonstrated, and not inside this family:
- Any further pruning of the GEMSDOE32 field (a 3-px collar, for example) is a subset of that raster, so its directed 3-px overlap is 100% by construction. That fails the 70% duplicate rule.
- A unique file needs a different dot field. No such field in the repository has a matched holdout win over its control, and no organizer receipt exists for any score.
- The four pending hypotheses in `registry/next_hypotheses.json` remain untested in this session (see Next steps). None has a measured expected gain.

**Evidence labels.** Every score in this section is OWNER-REPORTED. The 0.2778 value has no organizer receipt. The collar sequence is one family, one raster per step, and is a dose-response pattern in owner-reported numbers, not a causal finding.

## Pass 3 — link check and source status

Command: HTTP HEAD (`curl -L`) of 62 unique URLs found in `EXECUTIVE_SUMMARY.md`, `README.md`, the generated pages, `registry/sources.json` and `registry/focus_sites_2026-10-26.json`.

- **26 github.com URLs returned HTTP 200.**
- **36 URLs returned no connection (code 000) from this sandbox.** They are DrivenData, docs.nlr.gov, gdr.openei.org, usgs.gov, sciencebase.gov, osti.gov, epsg.io, Wikipedia, doi.org, researchgate, and all `*.github.io` Pages hosts. These are **not verified** from here. Open them in a browser for manual review. This matches the sandbox allowlist (github.com, codeload.github.com, api.github.com, registry.npmjs.org, pypi.org, files.pythonhosted.org).

## Irregularities recorded this session

`registry/irregularities.json`: IR-2026-10-28-01 to -05.
- -01: GEMSDOE28 H27-4 and GEMSDOE31 H27-4 are one dot field under two names (both 0.2708).
- -02: GEMSDOE30 equals GEMSDOE25 in every in-footprint value (both 0.2600).
- -03: collar dose-response in owner-reported scores (not causal).
- -04: 36 official links not reachable from the sandbox.
- -05: the prompt asks for the full prompt in the README; README holds a condensed brief (owner decision).

Existing open items still apply: the leader score is 0.4413 in one place and 0.3195 in another (IR-2026-10-25-02, IR-2026-10-27-01); the lane paragraph is missing (IR-2026-10-25-01); score-to-file attribution for GEMSDOE28/31/36 and GEMSDOE25 is unresolved.

## Seeds already consumed (check every new preregistration against this list)

From evidence file names and run-card seed lists: 100–109, 110–119, 120–129, 130–139, 140–149, 150–159, 160–163 and 160–169, 210–219, 240–244 (245–254 reserved by the H30 lane), 260–269, 400–409, 500–509, 510–519, 520–529, and 620–624 (proxy lane, per its irregularity note). Before any new run, run `grep -rn "seeds" knowledge evidence` and confirm the range is unused.

## Limitations and what is needed from the owner

1. **The lane paragraph.** Provide the single method paragraph for the parallel protocol, or confirm the lane to use. Without it, no parallel lane is legitimately assigned.
2. **Organizer and portal access.** Only a human can read the leaderboard, check the weekly cap, or upload. The repository has no organizer receipt. Please paste the leaderboard rows you can see (score and file name) so 0.4413 and 0.3195 can be reconciled.
3. **Official sources.** GDR 1391, USGS, NLR, ScienceBase and DrivenData are unreachable from the sandbox. Verifying them needs a fetch from an allowed route, or a human-supplied copy with a recorded SHA-256.
4. **Confirm which GEMSDOE28/31 upload carried 0.2708**, since they are one dot field under two names.
5. **README scope.** Decide whether the full prompt belongs in README (IR-2026-10-28-05).

## Next steps (for the next session, in order)

1. Obtain the lane paragraph (limitation 1). If it is not provided, run only the registered hypotheses that have no new data dependency.
2. Only after a lane is assigned: preregister one hypothesis from `registry/next_hypotheses.json` with an unused seed range, the same holdout, leakage canaries at AUC 0.90, and a matched current-best control.
3. Do not spend a slot on any file that fails the duplicate rule or lacks a holdout win over its control.
4. Human action: check the leaderboard and submission page, and record exact receipts in `registry/live_scores.json`.

## Run card

```json
{
  "session": "15",
  "date_utc": "2026-10-28",
  "hypothesis": "No new hypothesis tested. Audit only: explain GEMSDOE32 (0.2778 owner-reported) from pinned bytes.",
  "mechanism": "GEMSDOE32 = GEMSDOE25 d=2.8 minus all dots within 2 px of catalogue; owner-reported steps 0.2600 -> 0.2708 -> 0.2778 with collar width.",
  "non_fault_mimic": "Dots beside mapped faults on fault-parallel topographic or magnetic edges; reduced false positives can mimic better fault discovery.",
  "holdout_dti": "not run this session; no new candidate",
  "correlation_overlap_vs_registry": {"candidate_H33_1_max_3px_overlap": 0.0, "candidate_H33_1_max_abs_binary_dot_spearman": 0.00939, "scope": "12 pinned peers"},
  "raster_sha256": {"H33_1_allfinite": "1373358188a96b20414834b3e0159065d87470fe695153262ced7b46bc1eb492"},
  "validator": "single band float32; EPSG:32611; 3730x3292; transform equal template; 0 NaN; values {0,1}; 37,654 dots",
  "submission_name": null,
  "note_140_chars_max": null,
  "verdict": "negative for submission: no file OK to submit; no slot authorized"
}
```
