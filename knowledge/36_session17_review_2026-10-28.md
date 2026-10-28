# Session 17 — repository review and verification, 2026-10-28

## Executive decision

**No candidate is approved for a competition slot. No new TIFF was generated, no experiment or portal action was performed.** The requested scientific work cannot be honestly completed in this checkout: the hash-pinned raster cache is absent, and the prompt's parallel-run instruction does not identify a specific single-method lane. Do not treat the prior reported 0.2778, 0.3195, or 0.4413 as organizer-confirmed scores or use them as model estimates. The executive site table is a historical owner-reported snapshot, not a current leaderboard feed.

The highest-value next step is to restore and verify the repository's pinned research inputs, then identify the assigned lane and fresh holdout seeds before preregistration. Do not use a submission slot for this work.

## Pass 1 — inventory and task alignment

- Read `README.md` and `AGENTS.md` first. The repo already has the standing charter, submission safety gates, nine-site executive summary, submission instructions, scientific hypothesis records, pinned peer registry, and prior session reviews. The README explicitly says its standing task brief is a consolidated summary rather than a verbatim copy of the full user prompt.
- The currently recorded primary artifact, H33-1, is explicitly **NOT OK TO SUBMIT**. Its run card records HOLDOUT-DTI 0.025211 versus 0.041446 for its control, paired 95% CI [−0.017576, −0.014449], and 134,150 withheld-positive occurrences. It is a research negative, not a leaderboard score.
- The peer audit explains the GEMSDOE32 0.2778 geometry as a 2-pixel catalogue-collar deletion from the GEMSDOE25 d=2.8 dot field. That geometric relationship does not establish score causation. Pruning that same dot family further would fail the directed 3-pixel uniqueness stop by construction.
- Prior ranked hypothesis work is in `knowledge/07_untried_hypotheses.md`; it is not new work in this session. H28-1 is a prior catalogue-internal positive with a different protocol/context, not a current proof of improvement over the latest independent candidate. Do not silently treat it as a new pass.

## Pass 2 — adversarial verification and environment checks

Commands and outcomes in this checkout:

| Check | Result | Interpretation |
|---|---|---|
| `.venv/bin/python -m pytest -q` | **207 passed, 3 skipped** | All available unit tests passed; skipped tests need raster inputs. |
| `.venv/bin/ruff check src scripts tests` | **passed** | No lint findings. |
| `git diff --check` | **passed** | No whitespace errors. |
| `python scripts/verify_downloads.py` | **blocked** | Required files missing: `data_cache/sample_submission.tif`, `data_cache/labels.tif`, and `data_cache/dotted_h19_5_d1_5_nan.tif`. |
| `python scripts/restore_data.py --verify` | **failed as expected for absent cache** | All 17 manifest inputs reported BAD because the ignored cache is absent; verify-only mode does not download. No claim of corrupt pinned bytes is warranted. |

A local `.venv` was created from the pinned dependency ranges in `requirements.txt` to run the suite and lint. It is ignored by Git and is not a project deliverable.

No source files or raster bytes were changed in the verification. The prior Session 16 report says it restored a cache in its earlier environment; this checkout does not contain that ignored cache. That is an environment-state difference, not evidence that its earlier byte validation was false. It must be restored and revalidated before raster-dependent gates can run here.

## Pass 3 — requirements review, risks, and next actions

1. **Lane ambiguity:** the parallel protocol says to stay within “the single method paragraph below,” but the request does not provide an unambiguous one-method assignment. Selecting a method now would risk duplicating another parallel session. The already-ranked 3–5 candidates are documented in `knowledge/07_untried_hypotheses.md`; do not claim them as fresh hypotheses.
2. **Input availability:** `data/manifest.json` describes 16 files plus one assembled input; verify-only confirms no usable cache in this checkout. A true experiment requires `python scripts/restore_data.py` (network access to the pinned owner-repository mirrors), then hash verification, and `python scripts/prepare_data.py` if the prepared stack is absent. Mirror provenance is not organizer authentication.
3. **Holdout gate:** after inputs and lane are established, preregister fresh seeds and a matched current-best comparison. Run feature-alone leakage canaries (AUC > 0.90 is a stop), whole-FID buffered hide-and-recover with catalogue-derived features from visible faults only, exact visible-fault masking, pooled DTI (α=0.2, β=0.8, 300 m triangular kernel), and paired uncertainty. Stop at three experiments or two hours. Existing H28-1 evidence cannot substitute for this distinct gate.
4. **Uniqueness and publication:** use the shared pre-placement and post-placement registry checks. A technical validator pass or uniqueness pass is not submission approval. A separate selector must authorize any weekly slot; no upload is automated.
5. **Scores and official-source status:** keep historical reported values labeled owner-reported; estimate remains **unknown** absent calibrated evidence. Do not describe an estimate/projection as a score. Repository policy forbids agent access to DrivenData; submission receipts and current slot capacity remain owner-supplied. The executive summary should be read as a versioned historical comparison, not a live feed.
6. **PR/merge:** this review only records verification and limitations. A PR/merge should only be opened if there is a purposeful tracked change; do not fabricate changes or claim a remote PR/merge without GitHub evidence.

Official/manual-review references already documented in the repo include the [competition problem statement](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution), [USGS GeoDAWN record](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), and [GDR submission 1391](https://gdr.openei.org/submissions/1391). This session did not fetch or independently verify new external source content.

## Run card

```json
{
  "hypothesis": "No new hypothesis tested; prior H33-1 remains a negative research result.",
  "mechanism": "No candidate was built or evaluated in this session.",
  "named_non_fault_process_that_could_mimic_it": "Not applicable to this session; H33-1's registered mimics include roads, field boundaries, survey seams, and lithologic basin-fill pinch-outs.",
  "holdout_dti_and_ci": "No new HOLDOUT-DTI. Prior H33-1 HOLDOUT-DTI 0.025211 vs control 0.041446; paired 95% CI [-0.017576, -0.014449]; 134150 withheld-positive occurrences; gems27.metric.dti_binary v1, whole-FID buffered holdout. Historical result only, not a leaderboard score.",
  "correlation_overlap_vs_registry": "No new candidate to compare. Prior H33-1 check covered 12 pinned peers; not full registry certification.",
  "raster_sha256": null,
  "validator_output": "No new raster. Current verify_downloads.py blocked by absent ignored cache inputs; prior H33-1 independent byte validation is recorded in evidence/safety_audit_20261028.json.",
  "submission_name": null,
  "note": "No new submission generated; do not submit H33-1.",
  "verdict": "negative"
}
```
