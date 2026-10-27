# Session 14: submission-readiness repair, not a new experiment

## Decision

**No file is approved for submission. No new geological experiment or TIFF was produced in this session.** The requested single-method paragraph is absent; this session did not choose a new lane in a parallel run. Existing H33-1 and H29-5-PROXY negative results remain negative. A downloadable unique artifact is not evidence of a high leaderboard result.

The nine-site, file-linked comparison remains in [EXECUTIVE_SUMMARY.md](../EXECUTIVE_SUMMARY.md). GEMSDOE32 has the largest **OWNER-REPORTED** historical value in that focus set (0.2778), not an organizer-confirmed score. Its dot geometry is documented in knowledge/12 and knowledge/31; deleting catalogue-adjacent predictions is a plausible explanation for improved efficiency, not proof of causal performance on undisclosed labels. The conflicting claimed leaders in the prompt cannot be reconciled from available receipts.

## Pass 1 — repo and evidence review

Read README, AGENTS, the current executive summary, H33-1 result, readiness policy/tests and CI. The existing hypothesis register already distinguishes four pending ideas:

| Priority | Hypothesis and layers | Signature, missing-fault rationale and mimic | Distinction and cost | Status |
|---|---|---|---|---|
| 1 | H27-16: GDR 1391 fossil deposits, 2 m probes, Quaternary volcanics | Aligned paleothermal deposits with local thermal excess could mark concealed conduits; lacustrine tufa and lateral outflow can mimic it | Adds packages absent from current well/spring stack; medium-high cost | Not viable here until official raw bytes and pins are verified |
| 2 | H29-5 actual drainage: raw elevation and routed streams | Collinear canyon mouths/fan apices could mark buried range-front faults; resistant bedrock and drainage inheritance mimic it | Actual routing, not the tested detrended-relief proxy; medium-high cost | Raw/conditioned elevation and verified apex observations missing |
| 3 | H28-6: gravity anomaly/vertical derivative/horizontal gradient/slope | Scale-persistent density edges could survive alluvial burial; basin-fill contacts mimic it | Standalone persistence ablation, related to existing potential-field work; low-medium cost | Preregistration and independent matched holdout still needed |
| 4 | H28-7: K/Th/U, their ratios and TMI_up150 | Directional, scale-persistent alteration-front continuity may trace fluid pathways; provenance/weathering can mimic it | Isolated operator rather than prior broad feature fusion; low-medium cost | Review overlap with same-day H33 radiometric screen before running |

This is a carry-forward ranking, **not four newly discovered methods**, and no numerical prospective DTI improvement is established. Expected benefit is unknown. Do not reuse consumed seeds or relabel a negative ablation as a new hypothesis. Registry descriptions, not this short table, govern exact transforms.

## Pass 2 — repaired validation defects

1. Non-object JSON run cards now explicitly fail closed instead of crashing on `.get`.
2. The audit isolates unreadable/invalid JSON cards, records a negative decision, and continues examining the other cards. It does not silently omit damaged evidence.
3. Positive DTI deltas and their improvement intervals must not exceed 1 (DTI lies in [0,1]); previously impossible values could satisfy the positive-interval gate.
4. CI's “site ... unchanged” step previously printed a diff and always succeeded. It now uses `git diff --exit-code` on generated docs, root index and executive summary.
5. Refreshed readiness evidence now includes the existing H33-1 run card, which was missing from the checked-in audit snapshot. Its result remains blocked.

These repairs do not make recorded assertions independent scientific proof, authorize slots, or replace a current complete uniqueness screen.

## Pass 3 — reproducibility and independent byte check

- Created ignored `.venv`, installed requirements. Initial system Python lacked pytest; that setup attempt was not a successful test.
- Baseline before data restore: 173 passed, 3 skipped.
- New regressions plus restored inputs: **185 passed**, no skips. Ruff: **all checks passed**.
- `restore_data.py`: pinned owner-mirror inputs restored, including the assembled feature raster. These are not independently authenticated organizer downloads.
- `verify_downloads.py`: **0 failures**.
- `build_site.py`: six pages, root mirror and summary regenerated without changes to generated prose.
- Independently re-read H33-1 with the shared `verify_geotiff`: **all hard checks pass**, no NaN inside, all values [0,1], single-band float32, CRS/shape/transform match. Full output: `evidence/session14_raster_recheck_20261027.json`.
- SHA-256 remains `1373358188a96b20414834b3e0159065d87470fe695153262ced7b46bc1eb492`. Existing file, not a new generation.

Saved H33-1 **HOLDOUT-DTI** is 0.0252105783; evaluator `gems27.metric.dti_binary v1`, alpha 0.2/beta 0.8, triangular radius 300 m, whole-FID buffered hides (6 px); 134,150 repeated withheld-positive occurrences. Paired improvement 95% CI [-0.0175755532, -0.0144486915] against base-32, not current-best H31. It was not rerun. Uniqueness was previously measured only against the stated pinned scope, not globally.

## Access and next steps

No official external source was freshly fetched in this session. Source-review links (not fresh verification): [organizer reference implementation](https://github.com/drivendataorg/gems-prize-reference-solution), [GDR 1391](https://gdr.openei.org/submissions/1391), [rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf). DrivenData automation remains prohibited by repository policy. The network allowlist does not permit GDR/USGS/NLR access; no receipt, current weekly-cap state, expert hidden labels or verified current leaderboard is available.

Next session: pin one explicit method lane, audit consumed seeds across all evidence, establish independent geographic-block splits and a matched current-best control, and obtain/verify official external packages before declaring them viable. Run all feature-alone canaries, then the shared holdout, then complete pre/post-placement registry comparisons. Only a passing candidate can reach the separate selector. Do not upload the existing negative research TIFF.

## Concurrent-main integration

PR #44 initially conflicted with concurrent PR #43's independent byte-validation repair. Merged `origin/main` into the fixed session branch, retained both sets of safety tests and both irregularity entries, regenerated the audit/site, and reran verification: **191 tests passed**, Ruff passed. No scientific result or raster changed during integration.
