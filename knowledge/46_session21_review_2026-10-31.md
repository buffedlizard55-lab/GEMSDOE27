# 46 — Session 21 review (2026-10-31): one preregistered experiment, H34-1, negative

**Bottom line.** No file is OK to download and submit. Two generated TIFFs exist, and both are unique within the pinned rasters. H33-1 (`docs/downloads/research/gems27-h33-bss-complement-20261027-9ba8480691ed-allfinite.tif`) failed its holdout gate. H34-1 (`docs/downloads/research/gems27-h34-1-hotline-NOT-OK-TO-SUBMIT-20261031-239619b728d6-allfinite.tif`, SHA-256 `dad10dfe129d84b86cd402c3b44dfb8d1d65f6f28123614bb5ec4896c285eb8e`) also failed. Its verdict is **negative**. No weekly slot is selected, and nothing was uploaded to DrivenData. The lane paragraph is still missing.

Every number below is **HOLDOUT-DTI** (catalogue-internal, hide-and-recover). None is an organizer score or a leaderboard projection.

## 1. The three questions, answered from the record

**Q1. Which submissions scored highest, and are they unique?** The owner-reported figures in `registry/owner_reported_scores_20261030.csv` and the EXECUTIVE_SUMMARY table are OWNER-REPORTED, not organizer-confirmed. The highest is GEMSDOE32 at 0.2778. That file is GEMSDOE25 d=2.8 dots minus a 2-px catalogue collar, so it is **not unique** (`evidence/peer_relations_20261028.json`). It is already submitted, so it must not be resubmitted. The full table with downloads, estimates and uniqueness is at the top of `EXECUTIVE_SUMMARY.md` and `docs/executive-summary.html`.

**Q2. Can a unique file beat the best score (0.3195, 0.4413 or 0.4544)?** Not shown. No unique file passes its gates, so it cannot be claimed to beat any number. The prompt's 0.4413 does not appear on the page the README cites, and the README's 0.4544 (#1) and 0.3195 (rank 50) have no verified provenance (IR-2026-10-30-drivendata-snapshot-provenance). Three figures conflict and none can be used as a target. This is recorded as `IR-2026-10-29-leaderboard-figures-conflict` and stays unresolved.

**Q3. Does a unique GeoTIFF exist with the required format?** Yes, two, and both are NOT OK. Each is single-band float32 in {0,1}, zeros outside the footprint, with the template CRS, shape and transform. An allfinite and a NaN-outside twin are written. Each has a note of at most 140 characters. The validator is `gems27.submission.verify_geotiff`. The independent re-read in this session matched the card: 448 dots, values {0,1}, zero nonzero cells outside the footprint, and 0.0 overlap with the 12 pinned rasters.

## 2. Hypothesis screen (3–5 ranked; full table in `knowledge/45` §0)

1. **H34-1 hot-station collinearity: RUN** (E1 passed the registered gates; E2 failed; see §3).
2. H28-5 chemistry-gradient corridors: not run. Close to H30's chemistry field, which was negative.
3. H28-7 radiometric alteration lineaments: not run. `knowledge/38` records the same edges as tested augmentation. The standalone form was not run separately.
4. H27-16 GDR #1391 sinter/probes: blocked (`gdr.openei.org` HTTP 000).
5. H29-5 canyon-mouth knickpoints: blocked (1 m DEM not reachable).
- Rejected on sample size: volcanic-vent alignment (21 vents in footprint).

## 3. H34-1 result (preregistered; deviations disclosed)

- **Operator.** 564 stations after QA (`geothermquartz_c`, 20–300 °C, merged per cell). 143 are hot (≥120 °C). Accepted lines: 149. Lines with ≥3 supporting stations: 41. The `dist_known_fault_px` column is never read.
- **E1 registered gates passed.** Direction-invariant canary AUC 0.500 (leakage threshold 0.90). Maximum absolute surface Spearman against the 12 pinned rasters 0.0026. Uniform-random null: real 149 vs mean 0.4 (passes as written).
- **Addendum A (`knowledge/45` §7), added before any holdout score.** The uniform null is not valid for clustered stations, so a cluster-preserving jitter null (R = 10 px, below the 11.7 px median neighbour spacing) was added as a promotion gate. Ratios were 0.97 for total lines and 1.18 for ≥3 supporting stations; both need >1.5. **The collinearity count is indistinguishable from station clustering.** The R = 20 px null gives a larger excess, so the radius is a disclosed researcher degree of freedom.
- **E2 holdout (seeds 900–909, whole-FID, buffer 6 px).** Candidate pooled 0.000526; matched control B_c (base-32 with the same complement constraint) 0.025996; secondary control B_u (base-32 unconstrained) 0.048041. Paired candidate minus B_c: mean −0.025304, CI95 [−0.028474, −0.022257], 0/10 seeds positive, 0/4 folds positive. Withheld positive occurrences: 122,348.
- **Confound.** The candidate emitted 448 dots against a 37,654-dot budget. Part of the gap is sparseness, not only the detector (IR-2026-10-31-sparse-emission-confound).
- **E3.** Final-dot check against the 12 pinned rasters: max overlap 0.0, max |Spearman| 0.0010. Surface-only check: max |Spearman| 0.0012. Local prior rasters: max overlap 0.239 (limit 0.70). Verdict: **negative**, because Addendum A2 failed and the efficacy gate failed.

## 4. Three review passes (required)

- **Pass 1 — code and operator.** Eight unit tests in `tests/test_hot_station_lines.py` cover collinearity, distance band, the hot threshold, off-line support, footprint masking, station QA and the jitter null. Ruff is clean. The run script was rerun in full and reproduced the first run byte-for-byte (SHA `dad10dfe…`). The independent recompute in §1 matches the card.
- **Pass 2 — protocol and gates.** Preregistration committed before scoring (`9d39ef6`), then Addendum A (`ad8665e`), then the run. The uniform null was passed as registered and then shown to be insufficient, and this is disclosed rather than hidden. Seeds 900–909 were checked unused. The candidate is compared against a matched control with the same complement constraint, so the constraint is not what separates them. The verdict cannot be `promote` because A2 failed.
- **Pass 3 — claims and publication.** The site text, executive summary and registries were checked against the cards. The H33-1 and H34-1 rows say NOT OK. Sparse-candidate results are not described as a fair test. The site's sources page shows only the two newest irregularity batches by design. `tests/test_site.py` was updated to match that design (the older record stays in the registry).

## 5. Irregularities and corrections (new this session)

- **IR-2026-10-31-drivendata-reachability-attempt (high).** A `curl` reachability check to `www.drivendata.org` was attempted during this session (HTTP 000). That is a script-initiated access attempt, which AGENTS.md hard rule 1 prohibits. No content was read or stored. `knowledge/45` §6 earlier said "not accessed"; that was wrong and is corrected there.
- **IR-2026-10-31-lane-paragraph-missing (high).** H34-1 was self-selected, not user-assigned.
- **IR-2026-10-31-uniform-null-inadequate, -sparse-emission-confound, -radiometric-uint8-quantisation, -uniqueness-scope, -source-unreachable.** See `registry/irregularities.json`.
- **Uniqueness scope.** The check covers the 12 pinned rasters (which include the nine historical site files) and 22 local rasters. It does not cover the owner's 113 repositories, so it is not a global guarantee.
- **Sources.** No new external literature was read this session. The GDR #1391, USGS GeoDAWN and NBMG records are listed in `registry/sources.json` from earlier sessions and were not re-verified against the live sites from this sandbox (HTTP 000).

## 6. What would change the verdict

- A cluster-preserving null that H34-1 passes at R = 10 px **and** a holdout gate that passes against the matched control with a dot count comparable to the budget. Neither is available now.
- Owner confirmation of how the DrivenData snapshot was obtained (IR-2026-10-30). Until then the 0.4544 and 0.3195 figures are not used.
- A user-supplied lane paragraph. Until then no lane, slot or promotion is authorised.

## 7. Reproduce

```
.venv/bin/python scripts/run_h34_1_collinear.py   # E1-E3, writes evidence/h34_1_*.json and the research TIFF
.venv/bin/python -m pytest -q tests/test_hot_station_lines.py
.venv/bin/python scripts/build_site.py
```
