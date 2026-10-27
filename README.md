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

## What is established and what is not

Historical values are **OWNER-REPORTED**, not ORGANIZER-CONFIRMED; the association between some values and files conflicts across sibling evidence. The historical GEMSDOE32 value of 0.2778 is not a forecast. Its measured dot set is the GEMSDOE25 d=2.8 dots minus a 2-pixel catalogue collar. Spacing and collar exclusion are plausible ways to reduce redundant or low-yield DTI mass, but the hidden truth and a receipt are unavailable: geometry does not prove the reported score's cause. We do not know whether any untested method will exceed it.

The current **H29-5-PROXY** research lane evaluates a detrended-relief proxy, not actual drainage, downstream directions, fan apices or confirmed faults. It is distinct from the still-untested H29-5 routed-drainage hypothesis. Its preregistered canaries and whole-FID hide-and-recover screen are research evidence, not a live score. FID assignment is approximate and quadrant-stratified rather than a wholly independent geographic block; repeated catalogue hides are not independent geological samples. Promotion additionally requires a matched whole-FID comparison against the current H31 architecture, complete duplicate checks and a separate weekly-slot selector.

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
ruff check src scripts tests
python -m pytest -q
```

`build_site.py` regenerates the public HTML and `EXECUTIVE_SUMMARY.md` from recorded evidence without network access. `verify_downloads.py` checks historical raster format and consistency; it does **not** grant permission to submit. The shared raster writer supports an all-finite, zero-outside variant to avoid NaN-related `[0, 1]` rejections; passing local checks does not guarantee acceptance by the organizer.

To examine the recorded 2026-10-27 experiment, read `evidence/relief_profile_run_card_20261027.json`. Seeds are consumed: do not rerun or tune this experiment after seeing its results and present it as a fresh test. Follow `AGENTS.md` for preregistration, evidence, data and portal rules. The earlier reports in `knowledge/` and `evidence/` are preserved for historical audit; where they disagree with the current status, they do not override this README or the fail-closed gate.
