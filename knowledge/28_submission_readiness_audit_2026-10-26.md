# Executive audit — 2026-10-26

## Download decision first

**Existing H31 is format-valid and passes its saved research gates. It is NOT authorized for a weekly slot by this audit.**

[Download existing H31 TIFF](../docs/downloads/gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif) ·
[ZIP](../docs/downloads/gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.zip) ·
[Submission guide](../docs/how-to-submit.html) · [Nine-site executive page](../docs/executive-summary.html).

| File | Estimate (not a score) | Uniqueness scope | Upload decision |
|---|---|---|---|
| `gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif` | PROJECTION ~0.235 from one OWNER-REPORTED anchor; not a calibrated predictive interval | Pass vs pinned peers and saved local comparison; not proof against every current submission | Selector/current registry/weekly cap required; no slot selected |

No new TIFF was generated or renamed. The prompt's promised single-method lane paragraph is absent.
Running a guessed geological method would violate the parallel-run rule. Hypothesis selection, new training,
and new confirmation are therefore not completed in this audit; zero experiments consumed.

## Nine-site historical comparison

The following is the **existing repository evidence**, not independently retrieved organizer receipts.
These filenames are identifiers in that evidence, not newly verified hosted download links.
Scores cannot be relabelled ORGANIZER-CONFIRMED without receipts. The site table retains pinned peer-download
links for audit/education, not resubmission. No honest estimate of a new hidden-test score exists for each historical file.

| Site | Highest entry in saved comparison | Historical result | New-slot status |
|---|---|---|---|
| GEMSDOE32 | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` | 0.2778 OWNER-REPORTED | Historical; do not resubmit |
| GEMSDOE36 | `gemsdoe36-anderson-geothermal-pinn-38854-20261004T063428Z-c7e9bc92-zeros.tif` | 0.2750 OWNER-REPORTED | Historical; do not resubmit |
| GEMSDOE31 | `gemsdoe31-h32-2-b1-only-20261004-777da82e-allfinite.tif` | 0.2710 OWNER-REPORTED | Historical; do not resubmit |
| GEMSDOE28 | `gems28-h28-solo-r1-20261003-27c0796d-nan.tif` | 0.2708 OWNER-REPORTED | Historical; do not resubmit |
| GEMSDOE33 | `GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif` | 0.2632 OWNER-REPORTED | Historical; do not resubmit |
| GEMSDOE25 | `gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif` | 0.2600 OWNER-REPORTED | Historical; do not resubmit |
| GEMSDOE30 | `GEMSDOE30_dotted-h19-5-d2-8_20261003T061212Z_e56ea318-zeros.tif` | 0.2600 OWNER-REPORTED | Historical; do not resubmit |
| GEMSDOE24 | `gems24-dotted-h19-5-d1-5-20261001-989f59505db1.tif` | 0.2477 OWNER-REPORTED | Historical; do not resubmit |
| GEMSDOE27 | `gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-allfinite.tif (0.2449) & gems27-h29-hydrothermal-piedmont-celf-20261025-511898747886-allfinite.tif (0.2190)` | 0.2449 OWNER-REPORTED | Historical; do not resubmit |

The saved comparison differs from the latest prompt: GEMSDOE31 is listed at 0.2710 there while the prompt names
0.2708; the GEMSDOE28 comparison lists 0.2708 while the prompt also names 0.2710. These are provenance
conflicts, not verified site rankings. The 0.3195/0.4413 leaderboard claims also remain unresolved.
See [comparison evidence](../evidence/focus_sites_executive_summary_20261026.json),
[pinned registry](../registry/parallel_submission_registry.json), and
[score provenance](../registry/live_scores.json). Do not treat the table as a fresh live-site crawl.

## Why GEMSDOE32's reported 0.2778 is interesting

The independent byte re-audit reproduced the saved exact relationship: its prediction dots equal the
GEMSDOE25 d=2.8 family after deleting the catalogue collar at distance <=2 pixels.
This is a **set-identity measurement**, not proof of the cause of an organizer result.
Spacing can reduce redundant predictions under the 300 m triangular distance kernel; excluding
near-catalogue dots can reduce false-positive mass when known faults are masked. Those mechanisms are
plausible under the local evaluator, but hidden truth and organizer receipts are unavailable.
Do not infer that collar deletion creates a new geological detector, nor that copying it meets uniqueness.

H31's saved **HOLDOUT-DTI** is **0.047302**, 95% CI **[0.044527, 0.049619]**;
**120,778 withheld-positive occurrences** across 40 cells / seeds 400–409; evaluator
`gems27.metric v1 + holdout-blind-buffered-v2 (alpha=0.2, beta=0.8, R=3px triangular, buffer_px=6.0)`.
Counts are occurrences across repeated hides, not independent distinct faults. These results were **not retrained** here.
[Raw evaluation](../evidence/h31_s10_e2_holdout_400_409.json) and
[original run card](../evidence/h31_s10_run_card_2026-10-26.json) agree on the count;
README and knowledge/25 previously overstated it. The local metric does not establish that H31 beats
0.2778, 0.3195, or 0.4413 on hidden labels. A one-anchor transfer is not a reliable live-score estimator.

## Three review passes

1. **Implementation / evidence restoration:** read README and AGENTS; restored all pinned local inputs through
   the existing shared restorer, verified their hashes; restored 12 peer TIFFs from immutable GitHub commits.
   Kept large inputs in ignored `data_cache/`. Ran the standalone raster validator and independent byte re-audit.
2. **Bug / assumption review:** fixed the withheld-count transcription; changed the shared canary to
   `max(AUC,1-AUC) <= 0.90` for valid AUC in [0,1]. Added boundary, inverse-leakage, invalid-value and
   slot-separation tests. This fixes the shared template policy, not a private evaluator fork.
3. **Request / publication review:** replaced affirmative upload badges with **EVIDENCE PASS — SELECTOR REQUIRED**,
   exposed `slot_authorized: false` in readiness outputs, retained one-click downloads and short notes,
   and preserved historical quotes as historical quotes. No new geological result or novelty claim fabricated.

Fresh verification is recorded in `evidence/session11_reaudit.json` (same numeric results as before;
only slot-authorization fields changed), and `docs/data/submission_readiness_audit.json`.
The standalone `verify_downloads.py` returned **0 failures**. Final local suite: **148 passed** with restored data; Ruff: **all checks passed**.

## Limitations and next session, in order

1. A lane must be explicitly allocated before a new method is implemented. Do not consume new holdout seeds
   for an unassigned lane, nor re-use existing confirmation seeds for tuning.
2. Refresh the registry to include newly generated sibling submissions before considering a slot. Pinned
   historical comparisons are reproducible but not a real-time global uniqueness proof.
3. Obtain an authorized selector decision and current weekly-cap evidence. This audit never authorizes an upload.
4. Obtain organizer receipts to resolve historical rankings and evaluate calibration on independent outcomes.
5. Preregister the assigned detector-class change, not another cosmetic re-thinning of the H19-5 family.
   Include feature-alone canaries, whole-segment buffered hide/recover, pooled metric and confidence intervals.
6. Official sources outside the network allowlist cannot be fetched here. No new official literature or
   external data was verified this turn. Cached sibling mirrors have hash provenance, not fresh official provenance.

Official links for review (not newly accessed):
[competition description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/),
[reference implementation](https://github.com/drivendataorg/gems-prize-reference-solution),
[GDR 1391](https://gdr.openei.org/submissions/1391),
[rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf).
Repository rules prohibit automated DrivenData access. This competition predicts missing fault locations;
a predicted fault pixel is not an observed geothermal vent or a validated resource discovery.
