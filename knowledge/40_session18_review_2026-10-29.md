# Session 18 review (2026-10-29): what the 0.2778 result is, what was tested, what is still open

**Decision: NOT OK TO SUBMIT. No file in the repository is approved for a weekly slot.** This session ran one preregistered experiment (H29-XG). It was negative, and no TIFF was written. The unique research file from 2026-10-27 (H33-1) is still NOT OK.

Labels: every performance number below is **HOLDOUT-DTI** (evaluator `gems27.metric.dti_binary` v1, α = 0.2, β = 0.8, R = 3 px triangular, whole-FID buffered holdout). Historical scores are **OWNER-REPORTED** (see `registry/live_scores.json`). The leaderboard figures 0.4413 and 0.3195 are **USER-REPORTED** and unverified. No value here is **ORGANIZER-CONFIRMED**.

## 1. Why the GEMSDOE32 file scored 0.2778 (owner-reported), and whether it can be beaten

**What the bytes show** (`evidence/peer_relations_20261028.json`, recomputed this session from the pinned rasters):

- GEMSDOE32 (`gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif`) is a strict subset of GEMSDOE25's d = 2.8 dot field (`gems25-dotted-h19-5-d2-8-…-nan.tif`, 44,090 dots).
- 6,436 dots (14.6%) are removed. All of them are within 2 px of a catalogue cell (3,891 within 1 px). The 37,654 dots kept are at least 2.236 px from the catalogue.
- The chain GEMSDOE25 → GEMSDOE31 → GEMSDOE32 is nested. Each step only deletes dots. The owner-reported scores move with the collar width: 0.2600 → 0.2708 → 0.2778.

**Mechanism (analytic, not measured on the removed dots).** The DTI denominator is TP + 0.2·FP + 0.8·FN. Removing a dot raises DTI only if its marginal credit-per-false-positive is below the break-even value 0.2·DTI/(1 − 0.2·DTI). At DTI ≈ 0.25 that is ≈ 0.0526 (`metric.inclusion_threshold`). A dot near a catalogue trace may earn little credit if hidden truth is rarely that close to the catalogue, so a collar can lower the FP term more than it lowers TP. This is a hypothesis about the removed dots, not a measurement. It is consistent with `evidence/operating_point_model.json` (break-even efficiency 0.0521 at DTI 0.2477). **Not verified in this session:** the marginal efficiency of the removed dots was not measured, because the hidden truth is not available.

**Caveats that stay on the record:**

- The score steps are owner-reported. They are a dose-response pattern in numbers, not a causal finding. The file-to-score association is also disputed in sibling evidence.
- GEMSDOE25 and GEMSDOE30 are byte-identical in dot values, as are GEMSDOE28 H27-4 and GEMSDOE31 (`identical_in_footprint_pairs`). Those pairs cannot be counted as independent submissions.

**Can a unique file beat 0.2778?** Not shown.

- Pruning GEMSDOE32 further is a subset of that raster. Its directed 3-px overlap is 100% by construction, so it fails the 70% duplicate rule.
- A collar applied to a family that is not registered (a new emission, not a subset) could be unique. Nothing in this repository tests that yet. It is the most direct next test (section 4).
- No new local candidate has beaten its matched control on the holdout (section 2).

## 2. Experiment run this session: H29-XG joint gravity–magnetic cross-gradient

Preregistration `knowledge/39_preregistration_H29-XG_2026-10-29.md` (written before any scoring). Run card `evidence/h29xg_run_card_2026-10-29.json`. Evidence `evidence/h29xg_e1_canary_and_surface_800_809.json`, `evidence/h29xg_e2_holdout_800_809.json`. Seeds 800–809 (unused range).

| Stage | Result | Gate | Outcome |
|---|---|---|---|
| E1 leakage canary (50 inputs, direction-invariant AUC) | max 0.588 (`lidar_upface_max`); new columns max 0.540 (`xg_amp_s4`) | ≤ 0.90 | pass |
| E1 pre-placement surface | max \|Spearman\| 0.110 vs 12 pinned peers | ≤ 0.90 | pass |
| E2 paired holdout, candidate C vs control D | pooled C 0.043372 vs D 0.043878; mean seed Δ −0.000469; 95% CI [−0.001546, +0.000614]; 126,011 withheld-positive occurrences | Δ ≥ 0.001, CI > 0, ≥ 7/10 seeds, ≥ 3/4 folds, C > D | **fail** (5/10 seeds, 2/4 folds, CI spans 0) |
| E3 uniqueness, pinned 12-raster checker | max overlap 0.465; registry checker pass | ≤ 0.70 | pass |
| E3 uniqueness, local research family (22 files) | max overlap 0.845 vs `gems27-h28-1-edge-coherence-plus-t-v2-h27-4-…-allfinite.tif` | ≤ 0.70 | **fail** |

Outcome: **negative**. Because efficacy failed, no raster was written. The local-overlap failure is a second, independent stop. The output is a dot set that is 84.5% within 3 px of a family already on file. The cross-gradient surface is different (|ρ| 0.110), but the emitter's dots land in nearly the same places. **Lesson:** changing the features does not make the dots unique. Uniqueness has to come from the emission geometry (for example, the collar or a different placement rule), not from a new surface.

Cross-gradient literature: Gallardo & Meju 2003 (https://doi.org/10.1029/2003GL017370) and 2004 (https://doi.org/10.1029/2003JB002716). Both citations were verified by a search result citing the DOI. Neither full text was read in this session.

## 3. Three-pass review

**Pass 1 (implement and verify).** Restored 17 hash-pinned inputs (`scripts/restore_data.py`), prepared the 32-band stack and registry (`prepare_data.py`, `fetch_parallel_registry.py`), ran the readiness audit and `build_site.py`, and ran `verify_downloads.py` (0 failures). Wrote `src/gems27/crossgrad_features.py` (3 columns) and its tests, and `scripts/run_h29xg_crossgrad.py`, which reuses the shared holdout, fit, emitter, scorer, writer and uniqueness helpers by import.

**Pass 2 (defects and edge cases).**
- The H28-6 runner wrote a research TIFF whenever uniqueness passed, even when efficacy failed. The new runner writes only if both pass. The older runners are not yet aligned: `IR-2026-10-29-research-tif-write-policy-inconsistent`.
- `build_site.py` showed only the single newest dated irregularity batch. Adding a new batch hid the previous session's records and broke a regression test. The page now shows the two newest batches. The full registry is linked either way.
- The executive-summary "New result" paragraph was static text saying no experiment had run. It is replaced with the 2026-10-29 result. Its numbers come from the run cards.
- `docs/data/submission_readiness_audit.json` was stale (missing the session-17 card). Regenerated. All 25 cards still have `slot_authorized = false` (`slot_authorized` list is empty).
- A fail-closed test now checks the H29-XG run card: no raster unless efficacy and uniqueness both pass, and never a slot authorisation.

**Pass 3 (re-check against the request).**
- Executive summary with file, estimate, unique and OK columns: present at the top of `EXECUTIVE_SUMMARY.md`, generated from the run cards.
- Three to five hypotheses ranked with layers, signature, non-fault mimic and cost: `knowledge/38_hypothesis_screen_2026-10-29.md`.
- Unique TIFF with an obvious OK / NOT OK label: the H33-1 file is labelled NOT OK. The H29-XG and H28-6 runs wrote no file.
- Holdout labels, CI and withheld counts: given above.
- Leakage canary on every input: done (50 inputs).
- Link every official source for manual review: section 5.

## 4. Next steps (ranked by expected value per hour)

1. **Human action: the leaderboard figure.** Read the leaderboard page and record the high value with a date and a screenshot or link. The two values in the prompt (0.4413 and 0.3195) cannot both be right. Without this, no estimate can be checked against a real target.
2. **Unregistered-parent collar test.** Build a new emission (a new parent, not a subset of any registered raster), apply the 2-px catalogue collar, and score it on the holdout against a matched control. Checks: uniqueness against the parent and the registry, and whether the collar is still a gain on its own parent. This tests the one lever the owner-reported evidence points to.
3. **Matched current-best comparison.** Rerun H31 or H29-S on the same splits as any candidate. The readiness gate requires it before any slot.
4. **Align older runners.** Apply the stricter TIFF write rule to `run_h28_6_gravity_persistence.py` and `run_h33_lane.py`.
5. **Human data gate: GDR #1391 packages.** Download the sinter/tufa, 2 m probe and volcanic packages from `https://gdr.openei.org/submissions/1391` (DOI 10.15121/1881483, CC-BY-4.0). Pin their SHA-256 and rerun H27-16. These are the only new data sources identified. The sandbox cannot reach them (HTTP 000, `IR-2026-10-29-gdr-and-usgs-unreachable-from-sandbox`).
6. **Add the sibling xg1 raster to the pinned set**, so the cross-gradient uniqueness check covers GEMSDOE25's `xg1-crossgrad` file.

## 5. Sources for manual review

- DrivenData competition (human only; not accessed by this agent): https://www.drivendata.org/competitions/306/competition-doe-gems/
- Official reference solution, read from GitHub this session (first chunk of README; commit `aebe92f`): https://github.com/drivendataorg/gems-prize-reference-solution
- DOE GDR #1391, metadata read in an earlier session, packages not accessed: https://gdr.openei.org/submissions/1391
- Cross-gradient method: Gallardo & Meju (2003) https://doi.org/10.1029/2003GL017370 (listing verified; full text not read); Gallardo & Meju (2004) https://doi.org/10.1029/2003JB002716 (listing verified; full text not read).
- Registry rows added this session: `registry/sources.json` (34 entries), `registry/irregularities.json` (101 entries).

## 6. Limits

- The holdout is catalogue-internal. Its H29-S baseline is about 0.042, while the owner-reported live scores are 0.22–0.28. The proxy is roughly five to six times lower, so a holdout gain is not a leaderboard gain.
- The holdouts repeat the same catalogue. They are not independent geological samples.
- Lane: no lane paragraph was supplied. H29-XG was self-selected and is labelled as such.
- The 0.4413 and 0.3195 figures cannot be verified from this sandbox, and no DrivenData access is allowed.

## 7. Merge note (parallel work on main)

While this session was open, `main` gained PRs #54 and #55. Their files were merged into this branch, not rewritten. `knowledge/37_review_2026-10-29.md` and `knowledge/38_review_2026-10-29.md` come from that work, so the number 38 is used twice. Those filenames differ, and no file was renamed, because the H29-XG run card and preregistration cite the paths written here. The registry union kept every irregularity ID from both sides (98 from `main` plus 7 from this session, 105 in total). `main`'s H28-6 correction (untried → tested, seeds 700–709 reserved) agrees with section 1 and `knowledge/38`.

Site build with the workflow's exact dependency set (`pip install numpy rasterio`, then `python scripts/build_site.py`) succeeds in a clean venv (checked 2026-10-29). Failures that `main`'s review reports on remote runs could not be read, because the Actions logs were blocked, so their cause is not established here.
