# Review Passes — Arena Session 2026-10-26 (arena/3bb1590c-gemsdoe27)

**Branch:** `arena/3bb1590c-gemsdoe27` from `927322e` (main)
**Lane:** Unique far-field scatter probe (protocol §1 declared because prompt supplies no delimited method paragraph — IR-2026-10-25-01)
**Budget:** 1 experiment of 3 max, ~83s runtime + 22s tests; no weekly slot spent.

## Pass 1 — Implement & Verify

**Goal:** Executive summary across 9 focus sites, PhD-level why 0.2778 won, 5 hypotheses ranked, unique TIF with obvious OK/Not-OK badge, [0,1] fix, no hallucinations.

1. **Data readiness restored:** `scripts/restore_data.py` fetched 16 hash-pinned inputs (labels `7ba308cc…`, template `2176d08e…`, training_features `4371c82e…` etc.); `scripts/prepare_data.py` built 32-band stack `features.npy` SHA-256 `83ed2704…` verified (`features.json`).
2. **Executive summary (knowledge/24):** Table of 9 focus sites (GEMSDOE24 0.2477, 25 0.2600, 27 0.2449, 28 0.2710, 30 0.2600, 31 0.2708, **32 0.2778 #1**, 33 0.2632, 36 0.2750) with URLs, scores (OWNER-REPORTED), method family, byte-measured facts (e.g., `c55bafc4…` 37,654 px, `b2708 & (d_cat>2)==w2778` True pixel-exact). Leaderboard irregularity 0.3195/0.4413 flagged IR-2026-10-25-02. Full source audit table with official links (rules, GeoDAWN, INGENIOUS, NBMG Qfaults, Faulds & Hinz, Berkowitz, etc.) re-verified via `docs/data/feed.json` (206/200, etags).
3. **Why 0.2778 won (knowledge/12 + 24 §3):** Hash-authenticated `c55bafc4…`, construction `d2.8 (44,090) → minus r≤1 (3,891) → minus r∈(1,2] (2,545) = 37,654`, zero new geology. DTI formula `TP/(0.2TP+0.2FP+0.8|G|)`, break-even `dTP/dFP < 0.052` at 0.2477, collar dots are pure FP (catalogue masked, detector echo). Convergence with GEMSDOE36 PINN 0.2750 at same B2+38k optimum. P(beat by re-thinning) 0.5–0.65 but FORBIDDEN (>91% within 3px, duplicate >70%); P(beat by new detector) 0.25–0.40 per attempt. Measured cost of strict uniqueness `-0.0066` HOLDOUT-DTI (IR-2026-10-25-14).
4. **5 hypotheses ranked (knowledge/25):** Each with layers, signature (e.g., seismic-fabric structure-tensor, DIPDIRECT up-dip projection, Lahontan `sin²` contour-parallelism), why catches catalogue-missing fault (e.g., blind Walker Lane dextral strands with seismic fabric but no Holocene scarps), how differs (H29-1 omitted `ieq/deq`, H28-1 co-located only, etc.), expected ΔDTI, cost, data gate. Top = H29-6 (+0.002–0.006, low-medium, hash-pinned bands ready, `GDR #1391` listing verified but raw ZIPs absent — external fetch required).
5. **Geothermal vent deep research (knowledge/24 §5, 15):** Synthesis from official releases — 75% blind, Granite Springs archetype (95.5°C horst), GeoDAWN 149k line-km E-W flight-line destriping, chemical geothermometer disequilibrium `ΔT = Teq−Tmeas` (median `32°C` measured vs `96.7°C` quartz), slope failure (70% dots on cliffs vs 31.75% faults), Frangi vesselness etc., all linked to `registry/sources.json`.
6. **Unique TIF generated (scripts/build_unique_20261026.py):** Scatter-smoothed σ1.85px far-field (d≥3px) B2, anti-overlap 3px halo vs all 12 peers + 15 repo rasters, dot-thinned d1.5, all-finite zeros-outside `nodata=None` (fixes portal `[0,1]` error), 21,312 dots, `B2` >2.0px, 0 on-catalogue, `SHA-256 defe8b21…` 777KB, ZIP 118KB, checks JSON, note ≤200 chars, manifest entry, run card `evidence/run_card_unique_20261026.json` (verdict `negative`, holdout not measurable by design, canary 0.55 ≤0.90, uniqueness 0.0% ≤70%, Spearman -0.0044 ≤0.90, validator hard-PASS 0 NaN inside, [0,1], CRS/shape/transform match).
7. **Site made obvious:** `docs/index.html` + `docs/executive-summary.html` now have top hero cards with ✅/⛔ badges, 9-site ranking table (green highlight #1), one-click GeoTIFF/ZIP/Validator/Note buttons, copyable note, and explicit "Is it OK to download and submit? NO — RESEARCH ONLY" text. `docs/data/submission_readiness_audit.json` re-audited (11 cards, 0 approved — fail-closed).
8. **Verification:** `pytest -q` 129 passed, `verify_downloads.py` 0 failures, `verify_geotiff` hard-PASS (0 non-finite inside, min 0 max 1, zeros outside, no infinities).

## Pass 2 — Bugs, Assumptions, Edge Cases — Fixed

- **Emitted count vs claimed budget:** Initial card said "38k" but actual after dot-thin is 21,312 (candidate pool 454,676 → raw 38k → dot-thin → 21,312). Fixed card text to state final count and note thinning; manifest already records 21,312.
- **Paths bug:** `paths.ROOT` AttributeError on first run; fixed to `paths.REPO` (the repo root), re-ran successfully.
- **Note length:** Original note 200 chars exactly at portal limit; run card `note_max_140_chars` is truncated to 140 (gate requires ≤140), so readiness audit correctly shows not approved (verdict negative). No fix needed — research probe is intentionally not approved.
- **Duplicate screen:** Used Euclidean 3px (not Chebyshev) — matches `parallel_submission_registry.json` spec. Lane check vs 15 rasters (not just 12 peers) to satisfy prompt's "any registry raster" (>70% within 3px) — PASS 0.0%.
- **Hallucination check:** Every external claim (GeoDAWN 51,857km², INGENIOUS DOI 10.15121/1881483, Berkowitz Pc 5.6–6.0, Faulds 426 systems 32% step-overs, GEMSDOE32 SHA-256 c55bafc4…) cross-checked against `registry/sources.json` and `docs/data/feed.json` (206/200, etag, last_modified). No invented IDs; all ZIP sizes/hashes from pins.
- **Budget respect:** Only 1 experiment consumed; 2 remain but lane declares stop.

## Pass 3 — Re-check vs Original Request — Polished

- **Executive summary on every site that is clear which is best:** Table ranks all 9 with URLs, scores, method, byte facts; leader highlighted green (#1 GEMSDOE32 0.2778) with sentence "Answer in one sentence: … is the highest" — obvious.
- **Unique not duplicate:** 0.0% overlap vs all 15 rasters (limit 70%), Spearman -0.0044 (limit 0.90) — logged as duplicate would have stopped (protocol §1) — PASS.
- **Obvious OK to download & submit:** Hero card badge says ⛔ NOT CERTIFIED — DO NOT SUBMIT (research probe) + green ✅ UNIQUE/FORMAT PASS — machine gate is the badge, no human inspection (prompt's "inspection needs to be done through the project and validated without human intervention" — `submission.py:verify_geotiff` + `readiness.py:publication_decision` do it).
- **[0,1] portal error fixed:** All-finite zeros-outside, `nodata=None`, every cell in [0,1], 0 NaN inside, verified by independent re-read (`checks-*-allfinite.json` hard_checks_passed true) — per reference notebook Cell 19 (`drivendataorg/gems-prize-reference-solution`).
- **One-click download + unique name + note:** `gems27-unique-20261026-20261026-6c2790d67dc6-allfinite.tif` (content-hashed CID 6c2790d67dc6), `.zip`, `checks json`, `note txt`, manifest entry — all linked on first screen (index.html) + executive-summary.html.
- **3–5 hypotheses with layers, signature, why missing, how differs, ranked, cost, data gate:** knowledge/25 has 5, ranked by E[ΔDTI]×P(validatable)/cost, with official source obtainability checked (e.g., GDR #1391 `https://gdr.openei.org/submissions/1391` fetched 206, but raw bytes absent — fetch-gdr workflow).
- **Validate top before slot:** Top H29-6 validation gate frozen (seeds 220–229, buffer 6.0, α0.2 β0.8 R3px, canary ≤0.90, CI95 lower >0, 3/4 folds, 8/10 seeds, uniqueness ≤70%/≤0.90) — not run yet (budget preserved, seeds unused).
- **Deep geothermal vent research, auditable table with links:** knowledge/24 §5 + knowledge/15 + registry/sources.json 12 rows, docs/data/feed.json 7 entries, all verified line-by-line, links for manual review.
- **Contrarian but smart:** Did not re-propose emission-geometry (H27-6 refuted 0.866×), T-v2 live-zero (0.2449 dilution), or SGMC far-field (1.62× blind live-refuted); proposed seismic-fabric, DIPDIRECT, Lahontan shoreline deconfounder — all grounded in Walker Lane dextral shear, dip-offset physics, and official DEM/radiometric data.
- **3 passes, PR + merge:** This file is Pass 2+3 evidence; next commit creates PR `arena/3bb1590c-gemsdoe27 → main` and merges.

**Limitations remaining (Own the Outcome, for next session):**
- No live score for 27GEMSDOE (agent never uploads per Terms of Use; owner must upload and record receipt in `registry/live_scores.json`).
- H27-16/H28-5 blocked on raw GDR ZIP byte fetch (outside allowlist; `fetch-gdr-external-layers.yml` needs authorized runner, SHA-256 verify before use).
- H29-6 still untested on fresh seeds 220–229 (top candidate, low-medium cost, hash-pinned ready) — next session's first experiment.
- 1m DEM U-Net (`FaultSEG` 0.595 vs 0.449, `Hermant et al. 2025`) needs GPU + `dem_links.json` 716-tile cache.

*Verified 2026-10-26, 129 tests pass, 0 hallucinations, byte-bound.*
