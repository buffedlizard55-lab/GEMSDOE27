# Three-pass submission safety review — 2026-10-27

## Outcome

**Negative / no promotion.** No new geological experiment, raster, leaderboard estimate or competition upload. Existing H33-1 remains a research-only downloadable unique TIFF; its historical HOLDOUT-DTI evidence is unchanged. See the executive summary for all nine focus sites and the four ranked hypotheses in `knowledge/30_lane_2026-10-27_preregistration.md`. Those hypotheses are historical proposals, not newly validated discoveries.

The prompt promises a single method paragraph but does not provide one. This review does not silently choose another parallel lane or rerun exhausted experiments. Missing raw data and an absent fresh geographic-block/current-best confirmation cannot be solved by renaming an existing file.

## Pass 1 — implementation and independent byte audit

Found that `publication_decision` checked recorded validator flags and SHA-256 but never opened the GeoTIFF itself. A malformed file with a matching recorded hash and fabricated flags could pass that portion of the gate. Added a shared independent block-wise raster read: fixed competition CRS, shape, transform and bounds; GTiff, one float32 band; every pixel finite and in [0,1]. Fail closed on unreadable bytes. Existing template-based footprint and outside-zero checks remain required; this additional byte scan does not replace them or independently authenticate organizer data.

Re-read the existing H33-1 all-finite TIFF. All new byte checks pass; this does **not** reverse its negative efficacy result or broaden its 12-peer uniqueness scope. `docs/data/submission_readiness_audit.json` records all decisions; no slot is authorized.

## Pass 2 — adversarial regression and reproducibility

Added regression tests for self-reported success hiding NaN, infinity, negative values, values above one, non-TIFF text and wrong CRS, even when the file hash matches. Tests use real small GeoTIFFs and a patched miniature grid, not fake successful TIFF bytes.

Full-suite collection exposed a pre-existing import-path issue when using the `pytest` console entry point (`scripts.prepare_data` was not importable). Added the repository root to pytest's configured path. Both source and scripts remain checked by Ruff.

## Pass 3 — requirements review and limits

179 tests passed, 3 skipped; Ruff passed. Site rebuilt from evidence; audited decisions contain no authorized slot. No holdout models trained, no new holdout seeds consumed. No claims of improved leaderboard performance.

The prompt's 0.3195 and 0.4413 are inconsistent owner reports, not organizer receipts. Historical score-to-file pairings remain provisional. H33 uniqueness was scoped to 12 peers and local rasters, not all 397 inventory paths; it must not be certified globally unique. The current-best matched control and independent geographic-block confirmation are still absent. No authentic current slot-cap receipt exists. DrivenData automated access remains prohibited by this repository's instructions. External official USGS/GDR/NLR hosts are outside this sandbox's network allowlist; no fresh literature verification is claimed. The official reference repository's identity and main branch were checked via GitHub API, not its scientific content re-reviewed: https://github.com/drivendataorg/gems-prize-reference-solution .

README now explicitly calls its operating brief condensed. The earlier irregularity claiming a verbatim prompt in README is inaccurate for the current file and is corrected in the registry.

## Next-session priorities

1. Assign one explicit distinct method lane before experiments; contextual segmentation remains a previously proposed detector-class change, not a new discovery here.
2. Restore hash-pinned cache with `scripts/restore_data.py` and prepare once; do not rebuild shared tooling privately. Obtain unavailable official source bytes through an authorized environment before treating external-data hypotheses as viable.
3. Pre-register fresh independent geographic blocks and a current-best architecture retrained on exactly the same visible faults/buffers; report pooled DTI and paired uncertainty. Exhaustive canaries first.
4. Refresh and complete registry comparisons, including both surfaces and final dots. A 12-reference pass is not a nine-site/global pass.
5. Only after all gates pass may a separate selector consider a real weekly slot; retain receipt and exact submitted SHA-256 afterward.
