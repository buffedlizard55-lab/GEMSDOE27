# GEMSDOE27: fault-discovery research and submission audit

## Project charter — read at the start of every session

This repository is an auditable research system for the DOE GEMS fault-discovery competition. The objective is to discover **previously unmapped faults** using defensible geology and free, official data—not to recreate, rename, or lightly re-thin a prior submission. A high leaderboard result is an objective, not evidence that an unvalidated raster will score well.

1. **Unique submission only.** A raster can be considered only when both its pre-placement surface and final dots clear the pinned duplicate stops: absolute surface rank correlation ≤0.90 and directed 3-pixel dot overlap ≤70% against every available registry raster. Passing this check proves uniqueness only within its recorded scope; it is not organizer acceptance or slot authorization.
2. **Holdout before a slot.** Pre-register the hypothesis and fresh seeds; derive catalogue-based features only from visible faults; hide whole fault segments with a buffer; pixel-mask visible faults; then report paired **HOLDOUT-DTI** (α=0.2, β=0.8, 300 m triangular kernel), withheld-positive count, and 95% CI. A leakage-canary AUC above 0.90 is a stop. A model projection is never called a score.
3. **Technical validation without a human gate.** Every emitted GeoTIFF needs an automated re-read showing: single-band float32, same CRS/shape/transform as the template, finite in-footprint values in [0,1], no unintended catalogue dots, content hash, and an all-finite zero-outside fallback. `scripts/verify_downloads.py` and the shared writer are the technical gates; use the all-finite variant if a strict portal range check rejects NaN-outside data.
4. **Evidence labels are mandatory.** Use `HOLDOUT-DTI` for local measurements and `ORGANIZER-CONFIRMED` only for a submission-page receipt. Historical scores in this repo are owner-reported unless explicitly marked otherwise. Never turn either into a projected leaderboard score.
5. **No automated DrivenData access or uploads.** The project may link a human to the portal, but it does not scrape the site or upload submissions. A separate selector must authorize any weekly slot after all evidence gates pass.
6. **Research constraints.** Work in one registered lane, stop after three experiments or two hours, preserve negative results, document a named non-fault mimic, and record data/provenance irregularities. Use official, free sources where available; this sandbox cannot authenticate to DrivenData or independently retrieve all third-party packages.

**Core values:** *Maximize P(Win)* and *Own the Outcome* mean closing evidence gaps, reporting limits, and refusing weak submissions—not overstating confidence.

**DO NOT SUBMIT — no file is currently approved or authorized for a weekly slot.** The user reports that H31-1 content ID `cf8e1bbef244` was already submitted and received **0.2250 OWNER-REPORTED**. There is no organizer receipt in this repository. Do not upload, rename or re-thin that raster as a new submission. A valid GeoTIFF and a local holdout pass are not slot authorization.

**Generated unique TIFF: NOT OK TO SUBMIT.** `docs/downloads/research/gems27-h33-bss-complement-20261027-9ba8480691ed-allfinite.tif` (sha256 `1373358188a96b20414834b3e0159065d87470fe695153262ced7b46bc1eb492`; name `27GEMSDOE-H33-BSS-20261027-9ba8480691ed`). HOLDOUT-DTI **0.025211** versus base-32 **0.041446** on seeds 520–529 (134,150 withheld-positive occurrences; paired 95% CI [−0.017576, −0.014449]; 0/10 seeds). That is not a leaderboard score. It is unique versus the 12 pinned focus-site rasters (3 px overlap 0.000 by the complement constraint) and format-valid. Uniqueness is not authorization. Note (92/140): `H33-1 buried-step complement B2 37654px HOLDOUT-DTI 0.0252 | id 9ba8480691ed | DO NOT SUBMIT`. Write-up: `knowledge/31_h33_result_2026-10-27.md`.

Why the owner-reported 0.2778 file is not copied: it is the d=2.8 family after a 2 px catalogue-collar deletion. Copying it fails the uniqueness rule, and these 100 m bands do not recover the faults that family misses. The prompt’s 0.4413 and 0.3195 figures were not read from the leaderboard and disagree with each other. They are not scores to beat with a projection.

Operating prompt for later sessions: read this section first, then `knowledge/30_preregistration_H33_2026-10-27.md` and `knowledge/31_h33_result_2026-10-27.md`. One lane, shared holdout and writer, label HOLDOUT-DTI versus ORGANIZER-CONFIRMED, leakage canary at AUC 0.90, stop after 3 experiments, do not select a weekly slot. Core values: Maximize P(Win), Own the Outcome. A unique losing TIFF is a result. Uploading it would spend a scarce slot on a measured loss.

- [Executive summary of GEMSDOE24/25/27/28/30/31/32/33/36](EXECUTIVE_SUMMARY.md)
- [GitHub Pages status](https://buffedlizard55-lab.github.io/GEMSDOE27/) · [Submission instructions](docs/how-to-submit.html) · [Research and run card](docs/research.html) · [Source feed](docs/sources.html)
- [2026-10-27 hypothesis ranking and preregistration](knowledge/30_lane_2026-10-27_preregistration.md)
- [Owner-reported submitted-raster ledger](registry/submitted_rasters.json) · [Submission readiness audit](docs/data/submission_readiness_audit.json)
- Earlier parallel audits: [Session 12](knowledge/30_session12_repo_review_2026-10-27.md) · [Session 13](knowledge/30_session13_repo_review_2026-10-27.md); later evidence here supersedes their then-current status.

## 2026-10-28 H28-6 lane — current decision (read first)

- **Download decision table:** the top of `EXECUTIVE_SUMMARY.md` and `docs/executive-summary.html` (generated by `scripts/build_site.py` from the run cards). It lists, for each site and each new TIFF, the file, its estimate (HOLDOUT-DTI or OWNER-REPORTED), uniqueness, and an OK/NOT OK verdict.
- **Result:** H28-6 scale-persistent gravity edges (preregistered, `knowledge/36`) is **negative**. Holdout C 0.041238 vs matched control D 0.041574 (HOLDOUT-DTI; paired 95% CI [−0.002550, +0.002143]; 121,143 withheld-positive occurrences; 4/10 seeds, 2/4 folds). Its dots break the 70% local-overlap stop (84.9% within 3 px of a local negative research raster), so **no TIFF was written**.
- **Unique TIFF on disk:** `docs/downloads/research/gems27-h33-bss-complement-20261027-9ba8480691ed-allfinite.tif` is unique against the pinned and local rasters, but holdout-negative. **NOT OK TO SUBMIT.**
- **No historical file is new.** Estimates are local HOLDOUT-DTI or owner-reported values, never leaderboard projections. No leaderboard score can be estimated from these holdouts.
- **Lane:** the prompt still omits its single-method lane paragraph. This session ran only the registry's own rank-3 hypothesis (H28-6), recorded in `knowledge/36` section 0.
- Full review: `knowledge/37_h28_6_result_and_review_2026-10-28.md`. No upload, no slot selection, no DrivenData access.

## Standing task brief — read at every session start

The request is to maximize the probability of a genuinely new, high-performing fault-prediction GeoTIFF, not merely produce a different filename. Focus on GEMSDOE24/25/27/28/30/31/32/33/36; keep their historical file-linked executive table and submission instructions prominent. Preserve Maximize P(Win) and Own the Outcome without overstating evidence.

Before implementation, rank 3–5 geological hypotheses with layers, physical signature, missing-fault rationale, non-fault mimics, novelty limits and cost. Respect the assigned single-method parallel lane, cached stack and shared evaluator/writer; do not invent an omitted lane. Stop at three experiments or two hours. Use whole-segment buffered visible-only hide-and-recover, pixel-exact known-fault masking, feature-alone leakage canaries, pooled triangular 300 m DTI and paired uncertainty. Require a matched current-best holdout win and complete pre/post-placement duplicate checks before any separate selector decision. No automatic portal upload or weekly-slot use.

Every generated candidate needs a content-hashed TIFF/name, a note of at most 140 characters, byte-bound validation of band count, [0,1], finiteness and exact grid, and an unmistakable **OK / NOT OK TO SUBMIT** decision. Format validity and uniqueness alone never imply scientific merit. Label holdout results with evaluator/count/CI; only a receipt establishes ORGANIZER-CONFIRMED status. Keep historical owner reports explicitly distinct, never turn a projection into a score, and leave unknown estimates unknown. Audit official-source provenance honestly; blocked sources are not verified sources. Run three passes (implementation, defects/edge cases, requirement re-check), tests and lint, then record limitations and next steps. Negative results are deliverables. **This is the durable session-start operating prompt: read it in full every time.** It is a structured consolidation rather than a verbatim transcript; the nine-site file/score ledger is in `EXECUTIVE_SUMMARY.md`, and source/hypothesis provenance is in the registries and `knowledge/` records.

Latest audit: [Session 17 three-pass continuation review and run card (2026-10-28)](knowledge/36_session17_review_2026-10-28.md), following [Session 16 safety review](knowledge/35_session16_safety_review_2026-10-28.md) and the earlier Session 17 baseline inventory. The baseline checkout had no ignored raster cache; this later workspace restored and hash-checked owner-mirror inputs, prepared the shared 32-feature matrix, and reran raster audits. Session 17: 213 tests passed; Ruff, `py_compile`, and `git diff --check` passed; `verify_downloads.py` reported 0 failures. Those owner mirrors are not organizer-authenticated. H33-1 remains a negative research result; **no candidate was promoted and no file is OK to submit.**

Session 15 also ran a byte-level peer audit and answers the 0.2778 question: [peer-relations audit](knowledge/34_session15_peer_relations_2026-10-28.md). It reproduces the restored inputs; it measures GEMSDOE32 as the GEMSDOE25 d=2.8 field minus its 2-px catalogue collar; and it records two peer pairs that are identical in value (GEMSDOE25 = GEMSDOE30; GEMSDOE28 H27-4 = GEMSDOE31). **No file is OK to submit, and no new candidate was promoted.** Earlier: [Session 14 review](knowledge/32_session14_review_2026-10-27.md) (malformed cards fail closed; the readiness audit includes H33-1). Its numbers are recorded in `evidence/peer_relations_20261028.json`.

**Latest safety review (2026-10-28):** the shared peer cache is now checked against fixed SHA-256 pins; changed cache bytes and stale PASS reports fail closed. The all-finite byte scan also rejects nodata tags and pixel masks. H33-1 remains a negative research artifact, not an approved submission. [Review and next steps](knowledge/35_session16_safety_review_2026-10-28.md) · [run card](evidence/safety_audit_20261028.json).

## What is established and what is not

Historical values are **OWNER-REPORTED**, not ORGANIZER-CONFIRMED; the association between some values and files conflicts across sibling evidence. The historical GEMSDOE32 value of 0.2778 is not a forecast. Its measured dot set is the GEMSDOE25 d=2.8 dots minus a 2-pixel catalogue collar. Spacing and collar exclusion are plausible ways to reduce redundant or low-yield DTI mass, but the hidden truth and a receipt are unavailable: geometry does not prove the reported score's cause. We do not know whether any untested method will exceed it.

The **last executed H29-5-PROXY** lane evaluated a detrended-relief proxy, not actual drainage, downstream directions, fan apices or confirmed faults. It is distinct from the still-untested H29-5 routed-drainage hypothesis. Its preregistered canaries and whole-FID hide-and-recover screen are research evidence, not a live score. FID assignment is approximate and quadrant-stratified rather than a wholly independent geographic block; repeated catalogue hides are not independent geological samples. The current prompt again omits its promised single-method paragraph, so no new lane is assigned. A future candidate still requires a matched whole-FID comparison against the current-best architecture, complete duplicate checks and a separate weekly-slot selector.

The 2026-10-27 nine-site inventory is broader than the 12 pinned peer rasters but is incomplete: it is a GitHub snapshot, not a global list of submissions, and not every TIFF can be compared on the competition grid. The code fails closed when the required scope or validation is missing. No automated access to or upload to DrivenData is permitted.

## Reproduce

Use Python 3.11 or newer. Restored data are hash-pinned owner-mirror copies, **not independently organizer-authenticated**; the preparation cache is ignored by Git.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python scripts/restore_data.py
python scripts/prepare_data.py
python scripts/fetch_parallel_registry.py
python scripts/audit_submission_readiness.py
python scripts/build_site.py
python scripts/verify_downloads.py
python scripts/verify_peer_relations.py      # byte-level peer dot-set audit -> evidence/peer_relations_20261028.json
ruff check src scripts tests
python -m pytest -q
```

`build_site.py` regenerates the public HTML and `EXECUTIVE_SUMMARY.md` from recorded evidence without network access. `verify_downloads.py` checks historical raster format and consistency; it does **not** grant permission to submit. The shared raster writer supports an all-finite, zero-outside variant to avoid NaN-related `[0, 1]` rejections; passing local checks does not guarantee acceptance by the organizer.

To examine the recorded 2026-10-27 experiment, read `evidence/relief_profile_run_card_20261027.json`. Seeds are consumed: do not rerun or tune this experiment after seeing its results and present it as a fresh test. Follow `AGENTS.md` for preregistration, evidence, data and portal rules. The earlier reports in `knowledge/` and `evidence/` are preserved for historical audit; where they disagree with the current status, they do not override this README or the fail-closed gate.

## Session-start operating brief — 2026-10-27 safety review

Read this README and `AGENTS.md` every session. This is a **condensed operating brief**, not a verbatim copy of the long user prompt.

- Maximize P(Win); Own the Outcome. Prefer reproducible negative evidence over an unsupported high-score claim.
- Audit GEMSDOE24/25/27/28/30/31/32/33/36; distinguish historical owner reports, HOLDOUT-DTI and organizer receipts. Never call a projection a score.
- Before implementing a new geological lane, rank 3–5 hypotheses with layers, signature, catalogue-omission rationale, confounder, novelty and cost. Require obtainable data, preregistration and an assigned lane.
- Use shared cached features, buffered whole-segment hide-and-recover, visible-only catalogue features, exact visible-fault masking and pooled triangular 300 m DTI (alpha .2, beta .8). Test every feature for direction-invariant AUC > .90 leakage.
- Stop at three experiments or two hours. Stop duplicate lanes at absolute Spearman > .90 or directed 3-pixel dot overlap > .70; check before placement and after placement against the complete registry.
- Produce unique content-hashed TIFFs only through the shared writer. Independently open bytes and check grid, one float32 band, finiteness and [0,1]. Publish a clearly marked download, name, <=140-character note and JSON run card. Format validity does not imply efficacy or authorization.
- Require a matched current-best holdout improvement with uncertainty before the separate weekly-slot selector. Never upload automatically or claim an unknown weekly cap.
- Preserve sources, access limitations and irregularities honestly. Do not claim line-by-line official verification when the source host is inaccessible.

Latest review: [three-pass safety audit](knowledge/32_submission_safety_review_2026-10-27.md). The readiness gate now rereads TIFF bytes rather than trusting validator booleans. **No new geological experiment or submission slot was used.**

## 2026-10-28 delivery audit

[Session 15 three-pass delivery audit](knowledge/33_session15_delivery_audit_2026-10-28.md) fixes the executive Markdown download link and fails closed if a research TIFF is missing or its bytes disagree with the run card. The previously generated H33-1 GeoTIFF is downloadable **for research only; NOT OK TO SUBMIT**. No new experiment or slot was used: the parallel prompt did not contain its promised single-method lane paragraph. With hash-pinned owner-mirror data restored, 194 tests and the standalone raster-download verifier pass; these are not organizer receipts or a leaderboard-score estimate. Next session: read this charter and the Session 15 audit before choosing any assigned lane.

## 2026-10-28 Session 16 continuation audit

[Three-pass review](knowledge/35_session16_delivery_review_2026-10-28.md): fixed malformed-path crashes in the shared readiness gate (NULs and symlink loops now reject the card), restored pinned caches, and reproduced peer relations. **200 tests passed; Ruff passed; download verifier: 0 failures.** No new geological experiment or TIFF was generated, no slot used, and no candidate promoted. The prompt still omits its single-method lane assignment. The existing unique TIFF remains **NOT OK TO SUBMIT**; leaderboard estimates and organizer receipts remain unknown. Read the linked review before continuing.

## 2026-10-28 Session 17 — pairwise peer audit and executive-table repair

[Three-pass review and run card](knowledge/36_session17_review_2026-10-28.md) adds a hash-pinned, ordered final-dot comparison for every pair among the 12 pinned historical rasters. All nine selected per-site historical “best” files trigger at least one duplicate stop in that finite scope; the executive table now reports owner-reported value, unknown organizer-score estimate, explicit uniqueness result and “do not reuse” action for each site. The byte-level GEMSDOE25/GEMSDOE30 and GEMSDOE28/GEMSDOE31 identical-dot pairs remain documented. The comparison is of final binary rasters only: continuous pre-placement peer surfaces are unavailable, and this is not a global inventory.

The website now presents the four registry-listed untried formulations with layers, physical signatures, catalogue-omission rationale, mimics, novelty limits, qualitative potential and cost/data gates. No numeric DTI estimate is available. The official GDR #1391 packages and raw conditioned 3DEP inputs are absent; current package availability was not verified. No new experiment or TIFF was generated because the prompt still does not supply its required single-method paragraph. No current file is **OK TO SUBMIT**, no slot was used, and organizer receipts/current leaderboard values remain unknown. Session 17 verification: **213 tests passed**, Ruff/`py_compile`/`git diff --check` passed, `verify_downloads.py` reported 0 failures, and the fail-closed readiness audit checked 22 cards with 0 slot authorizations.
