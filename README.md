# GEMSDOE27: fault-discovery research and submission audit

**DO NOT SUBMIT — no file is currently approved or authorized for a weekly slot.** The user reports that H31-1 content ID `cf8e1bbef244` was already submitted and received **0.2250 OWNER-REPORTED**. There is no organizer receipt in this repository. Do not upload, rename or re-thin that raster as a new submission. A valid GeoTIFF and a local holdout pass are not slot authorization.

- [Executive summary of GEMSDOE24/25/27/28/30/31/32/33/36](EXECUTIVE_SUMMARY.md)
- [GitHub Pages status](https://buffedlizard55-lab.github.io/GEMSDOE27/) · [Submission instructions](docs/how-to-submit.html) · [Research and run card](docs/research.html) · [Source feed](docs/sources.html)
- [2026-10-27 hypothesis ranking and preregistration](knowledge/30_lane_2026-10-27_preregistration.md)
- [Owner-reported submitted-raster ledger](registry/submitted_rasters.json) · [Submission readiness audit](docs/data/submission_readiness_audit.json)
- Earlier parallel audits: [Session 12](knowledge/30_session12_repo_review_2026-10-27.md) · [Session 13](knowledge/30_session13_repo_review_2026-10-27.md); later evidence here supersedes their then-current status.

## What is established and what is not

Historical values are **OWNER-REPORTED**, not ORGANIZER-CONFIRMED; the association between some values and files conflicts across sibling evidence. The historical GEMSDOE32 value of 0.2778 is not a forecast. Its measured dot set is the GEMSDOE25 d=2.8 dots minus a 2-pixel catalogue collar. Spacing and collar exclusion are plausible ways to reduce redundant or low-yield DTI mass, but the hidden truth and a receipt are unavailable: geometry does not prove the reported score's cause. We do not know whether any untested method will exceed it.

The current research lane evaluates a **detrended-relief proxy**, not actual drainage, downstream directions, fan apices or confirmed faults. Its preregistered canaries and whole-FID hide-and-recover screen are research evidence, not a live score. FID assignment is approximate and quadrant-stratified rather than a wholly independent geographic block; repeated catalogue hides are not independent geological samples. Promotion additionally requires a matched whole-FID comparison against the current H31 architecture, complete duplicate checks and a separate weekly-slot selector.

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
pytest -q
```

`build_site.py` regenerates the public HTML and `EXECUTIVE_SUMMARY.md` from recorded evidence without network access. `verify_downloads.py` checks historical raster format and consistency; it does **not** grant permission to submit. The shared raster writer supports an all-finite, zero-outside variant to avoid NaN-related `[0, 1]` rejections; passing local checks does not guarantee acceptance by the organizer.

To examine the recorded 2026-10-27 experiment, read `evidence/relief_profile_run_card_20261027.json`. Seeds are consumed: do not rerun or tune this experiment after seeing its results and present it as a fresh test. Follow `AGENTS.md` for preregistration, evidence, data and portal rules. The earlier reports in `knowledge/` and `evidence/` are preserved for historical audit; where they disagree with the current status, they do not override this README or the fail-closed gate.
