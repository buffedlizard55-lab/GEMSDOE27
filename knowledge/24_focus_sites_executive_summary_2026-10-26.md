# 24 — Executive summary: the 9 focus sites (2026-10-26)

**Question asked:** for GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36 — what is each site's best
submission, which single file is best to submit for a high score, and can we generate a
*unique* (non-duplicate) file that beats 0.2778?

**Evidence classes.** Every score below is **OWNER-REPORTED** (2026-10-26 owner prompt; no
ORGANIZER-CONFIRMED receipt is stored in any reviewed repo; this agent never accesses
drivendata.org). Dot counts, nesting and overlaps are **MEASURED** from bytes this session
(pinned peer rasters re-fetched and hash-verified; `registry/parallel_submission_registry.json`).
Machine-readable version: `registry/focus_sites_2026-10-26.json`.

## Bottom line (obvious answer first)

1. **The proven best file in the fleet is GEMSDOE32's `h33-h33-2-b2` — 0.2778 (OWNER-REPORTED).**
   It is **already submitted and scored → ⛔ DO NOT RESUBMIT.** The scorer is deterministic;
   resubmitting identical bytes can only reproduce 0.2778 while burning one of the weekly slots.
2. **Every focus site's best file is already scored, and all nine are the same H19-5 dot
   family** (two pairs are pixel-identical dot fields; one is a superset of the champion).
   **None of them should be submitted again.** There is no "best old file to submit" — that
   slot can only be filled by a *new, unscored, unique* file.
3. **New unscored candidates that exist today:** (a) GEMSDOE32's parallel-session
   `R6-1 STEP` file (`23fbbb51`, unscored) — peer-claimed PROMOTE on an SGMC-truth instrument,
   while their own catalogue-hidden instrument ranks it below the champion; the selector must
   resolve that instrument disagreement before spending a slot. (b) **This session's H31 file** —
   its submit badge is computed fail-closed from its run card by
   `gems27.readiness.publication_decision` (`evidence/h31_run_card.json`,
   `docs/data/submission_readiness_audit.json`): **download-and-submit is OK only if that
   machine gate says `promote`; otherwise the site shows ⛔ DO NOT SUBMIT.** No human
   inspection is part of the gate.
4. **Can a new file beat 0.2778?** Only with better *ranking* at the proven B2 / ≈37.7 k-dot
   optimum. The family's deletion ladder is exhausted (ceiling ≈0.29 MODEL and a protocol
   duplicate besides). H29-S — this repo's best holdout surface ever — scored **0.2190 live**
   (OWNER-REPORTED, new in this prompt), proving holdout gains alone don't transfer. H31 is
   the cheapest remaining falsifiable ranking idea; its gate result, not enthusiasm, decides.

## Per-site verdicts

| Site | Best submission (OWNER-REPORTED score) | Dots (MEASURED) | What it mechanically is | Verdict today |
|---|---|---:|---|---|
| [GEMSDOE24](https://buffedlizard55-lab.github.io/GEMSDOE24/) | `h25-1-dotted-h19-5-d1-5` **0.2477** | 60,069 | H19-5 ridge surface dot-thinned at 1.5 px. Also listed: `gems24-gvc1-…` 0.0859 | ⛔ DO NOT SUBMIT — scored; superseded by its own sparser children (d2.8/B1/B2) |
| [GEMSDOE25](https://buffedlizard55-lab.github.io/GEMSDOE25/) | `dotted-h19-5-d2-8` **0.2600** | 44,090 | Same surface thinned at 2.8 px — parent of the champion. Also: `gems25-h66-mgd-flank…` 0.0742 | ⛔ DO NOT SUBMIT — scored; its B2 child (0.2778) strictly dominates it |
| [GEMSDOE27](https://buffedlizard55-lab.github.io/GEMSDOE27/) (this repo) | `topo-gap-closure-t-v2-on-d1-5` **0.2449**; 2nd `gems27-h29-hydrothermal-…-511898747886` **0.2190** (new score in 2026-10-26 prompt) | 61,328 / 37,654 | T-v2 graph gap-closure dots added to D1.5 (live A/B: scored *below* D1.5 — added mass earned ~0). H29-S = hydrothermal/piedmont CELF detector, repo holdout-best but live 0.2190 | ⛔ DO NOT RESUBMIT either — both scored. This session's H31 is the only unscored file here; follow its machine badge |
| [GEMSDOE28](https://buffedlizard55-lab.github.io/GEMSDOE28/) | `h36-1-rung30-blind-r1` **0.2710** (cluster: solo 0.2708, h38-1 0.2707, h32-1 0.2649) | 37,660 | D2.8 re-packs + 1-px catalogue-flank prune. Also: `gems28-s18-mxtp…` 0.0217 | ⛔ DO NOT SUBMIT — scored cluster, all one family, all below the B2 child |
| [GEMSDOE30](https://buffedlizard55-lab.github.io/GEMSDOE30/) | `d28-poisson300m-offcat-44090` **0.2600** | 44,090 | **Dot field pixel-identical to GEMSDOE25's d2.8** (MEASURED symdiff = 0) — same score is a scorer-determinism check, not a second result. Also: `gems30-MSDB1…` 0.1462 | ⛔ DO NOT SUBMIT — scored duplicate of GEMSDOE25's file |
| [GEMSDOE31](https://buffedlizard55-lab.github.io/GEMSDOE31/docs/) | `h27-4-solo-d28` **0.2708** | 40,199 | **Dot field pixel-identical to GEMSDOE28's solo** (MEASURED symdiff = 0) | ⛔ DO NOT SUBMIT — scored duplicate lineage |
| [GEMSDOE32](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` **0.2778 — fleet best** | 37,654 | 0.2708 base **minus exactly its 2,545 dots within (100, 200] m of the catalogue** (MEASURED pixel-exact). New unscored parallel file: `r6-stepprofile-…-23fbbb51` (det_elev step detector; peer-claimed PROMOTE, SGMC instrument; sha256 `c7f094c1…` verified) | Champion: ⛔ DO NOT RESUBMIT (already scored). R6: **selector decision** — unscored and unique (≤21 % overlap MEASURED) but promoted on a different instrument that this repo has not validated |
| [GEMSDOE33](https://buffedlizard55-lab.github.io/GEMSDOE33/) | `h33d-analog-tip-stepover-r30` **0.2632** | 41,865 | Analogue tip/step-over protection + Euler additions on the same family | ⛔ DO NOT SUBMIT — scored, below champion |
| [GEMSDOE36](https://buffedlizard55-lab.github.io/GEMSDOE36/docs/) | `anderson-geothermal-pinn-38854` **0.2750** | 38,854 | **Contains all 37,654 champion dots + exactly 1,200 more** (MEASURED superset) — the extras cost −0.0028. Not an independent physics result despite the name | ⛔ DO NOT SUBMIT — scored champion-superset |

## Why 0.2778 won (one paragraph; full proof in knowledge/12 + 18)

DTI = TP/(0.2·TP + 0.2·FP + 0.8·|G|). The organizers mask the published catalogue from
scoring, so a dot hugging a *known* fault pays full FP cost but can only earn if a distinct
hidden fault lies within its 300 m kernel — rare, because such dots exist mainly as the
detector's echo of the known fault itself (dip offset + 100 m quantisation). Deleting a dot
set pays iff its credit efficiency < 0.2·DTI/(1−0.2·DTI) ≈ 0.056 at DTI 0.2778; the
(100, 200] m annulus measures ≈0.003–0.016. The whole ladder 0.1922 → 0.2477 → 0.2600 →
0.2708 → 0.2778 is successive deletion/spacing of one H19-5 field toward the B2 (zero dots
within 200 m of catalogue) / 37,654-dot optimum — independently converged on by GEMSDOE36's
file. That is also why no further edit of the same dots can reach the prompt's stated
leaderboard highs (0.3195 / 0.4413 — both OWNER-REPORTED, mutually inconsistent, flagged):
at fixed ranking, the remaining deletion headroom is ≈+0.005–0.015 (MODEL).

## How to submit (only a file whose machine badge is green)

1. Open the site's first screen / executive-summary page. The badge is rendered from the
   run-card JSON — green **OK TO DOWNLOAD AND SUBMIT** only when format + holdout-efficacy +
   uniqueness gates all PASS; red **⛔ DO NOT SUBMIT** otherwise. Do not rely on filenames.
2. Download the `-allfinite.tif` (or its single-GeoTIFF `.zip`). All-finite means every one
   of the 12,279,160 cells is finite and in [0, 1] (nodata=None) — this is the permanent fix
   for the portal error *"Predicted values must be in range [0, 1]"* (caused by float32-min
   nodata / NaN leaking inside the footprint).
3. On DrivenData → *New submission*: choose the `.tif`, paste the ≤140-char **Note** shown
   beside the download (it encodes hypothesis, holdout result and content id), submit, and
   record the returned score in `registry/live_scores.json` as a new row — never edit an
   old row's score onto new bytes.

Official sources for manual review: competition
https://www.drivendata.org/competitions/306/competition-doe-gems/ · problem description
https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ · leaderboard
https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/ · rules
https://docs.nlr.gov/docs/fy26osti/96647.pdf · reference solution
https://github.com/drivendataorg/gems-prize-reference-solution · USGS GeoDAWN
https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and ·
INGENIOUS https://gbcge.org/current-projects/ingenious/ · GDR #1391
https://gdr.openei.org/submissions/1391 · EPSG:32611 https://epsg.io/32611 ·
Tversky index https://en.wikipedia.org/wiki/Tversky_index
