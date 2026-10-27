# Session 12 Pre-Registration (Experiment 3 of 3 — FINAL): Hypothesis `H33-3` — Full-Spectrum Asymmetric Graben + Walker Lane Strike-Slip Synthesis (`69` Cols, Restoring `32` Base Bands) with `N22.5°E` Basin-and-Range OOF Stitch & Zero-`3px`-Overlap `min_sep=3.15` Manifold CELF (`AGMC-WL-CELF315`)

- **Lane Declaration (Parallel-Run Protocol §§1, 6):**
  - **Session Experiment Index:** `3 of 3 (FINAL)` — last experiment permitted under the `[3]`-experiment session cap. After `H33-3` completes (`promote` or `negative`), experimentation stops unconditionally.
  - **Controlled Synthesis from Experiments 1 & 2 (both preserved unchanged in `evidence/` and `docs/downloads/research/`):**
    1. **Experiment 1 (`H33-1`, seeds `600..609`, `evidence/h33_s12_run_card_2026-10-26.json`):** Kept all `32` base columns (`20` non-LiDAR + `12` 1 m LiDAR) + `15` subsurface + `19` `H33` asymmetric-graben/canyon-mouth/`TMI_up150`/`ThK` columns (`66` cols) at `min_sep_px = 3.00` (`nbr_le_3px_mean = 0.247`). **Passed all 5/5 `E2` holdout gates** (`HOLDOUT-DTI = 0.049590` vs `H31-S = 0.046622`, `+0.002968`, 95% CI `[+0.001592, +0.004441]`, `9/10` seeds), losing slightly only in `SE` Walker Lane (`-0.00235`), and failed `E3` solely because `0°+45°` stitched `3-px` overlap vs `H31-1` (`cf8e1bbef244`) was `71.21% > 70.00%` (by `1.21%`).
    2. **Experiment 2 (`H33-2`, seeds `610..619`, `evidence/h33_2_s12_run_card_2026-10-26.json`):** Dropped the `12` raw `base_X` `lidar_*` columns from `M_Full` and jumped `min_sep_px` to `3.45` (`r_min = 3.606 px`). Passed `E1`/`E3` stitched uniqueness (`66.89% <= 70%`), **but** dropping the `12` `base_X` LiDAR columns crippled the detector (`H33_2-A = 0.04055` vs `H33-A = 0.04711`), failing `E2` (`0.04088` vs `H31-S = 0.04469`).
  - **Exact `H33-3` Design (`Lane L-S12C-2026-10-26`):**
    1. **Restores all `32` `base_X` columns** while combining the `19` `H33-1` half-graben/canyon-mouth/`TMI_up150`/`ThK`/deconfounded-LiDAR features AND the `3` `H33-2` LiDAR-free multi-elevation magnetic dip/verticality & Walker Lane seismic-fabric/uranium-redox features (`69` Stage-1 columns: `53` LiDAR-free in `M_Sub`; `69` full in `lidar_valid`-only `M_Full`, trained with `max_features = 0.62`), plus the `11` Stage-2 16-azimuth `2.3 km` orthogonal-Radon & vesselness columns (`clf_s2_sub` + `clf_s2_full`).
    2. **Zero-`3px`-Overlap `N18.4°E`-Preserving Lattice Spacing (`min_sep_px = 3.15`, `gamma = 1.48`):** Blocks the `33`-pixel disk $d^2 \le 9$ (`r <= 3.000 px`, driving `nbr_le_3px_mean` from `0.247` in `H33-1` to **`0.0000`**), while **preserving the exact `(±3, ±1)` ($r = \sqrt{10} = 3.1623\text{ px}$, `N18.4°E` Basin-and-Range fault strike) step** that `min_sep = 3.45` blocked!
    3. **Basin-and-Range Strike-Aligned Full-Map OOF Stitch (`22.5°` + `67.5°` 4-sector partitions for `E1`/`E3`; strict `0°` Cardinal Quadrant OOF for `E2`):** Aligns full-map cross-fitting seams with the `N22.5°E` regional Basin-and-Range structural grain (`45°` mutually offset so every pixel is out-of-fold with `600 m` guard and seam-free), while keeping `E2` strictly leak-free on the `0°` quadrant splits.
- **Fresh Unconsumed Confirmation Seeds:** `620, 621, 622, 623, 624, 625, 626, 627, 628, 629` (`40` fresh fold-seed cells; strictly disjoint from `0..2`, `100..169`, `210..269`, `300..309`, `400..419`, `500..509`, `600..609`, and `610..619`).

---

## Frozen Promotion & Uniqueness Gates (`E1`, `E2`, `E3`)

1. **`E1` (Univariate Leakage Canary + Exact `22.5°+67.5°` Stitched Uniqueness Gate — MUST PASS BEFORE `E2`):**
   - Direction-invariant univariate ROC-AUC `<= 0.90` across all `69` Stage-1 features on seeds `620..629` withheld positives.
   - Stitched (`0.5 * rot225 + 0.5 * rot675`) pre-placement surface `|Spearman| <= 0.90`, post-placement dot `|Spearman| <= 0.90`, AND directed `3-px` Euclidean dot overlap **`<= 0.70`** against all 12 focus-site peer rasters + `Slot 1` (`5512495c6bd1`) + `H29-S` (`511898747886`) + Session-10 `H31-1` (`cf8e1bbef244`).
2. **`E2` (Confirmatory Paired 40-Cell Buffered Hide-and-Recover Holdout on Fresh Seeds `620..629`):**
   Evaluated strictly out-of-fold (`prob_h333_s2_quad.npy`) at matched budget `BUDGET_TOTAL = 37,654` (`B2 > 200 m`) against `U0`, `B0`, `D0`, `H29-S`, and prior promoted holdout champion `H31-S` (`cf8e1bbef244` protocol), plus `H33_3-A` (`H33-3` detector + Poisson `d=2.8` ablation). `H33_3-S` promotes (`gate_e2_pass = True`) **if and only if ALL FIVE clauses hold**:
   - **(a) Beats all prior promoted/baseline benchmarks including `H31-S` on pooled buffered `HOLDOUT-DTI`:** `pooled(H33_3-S) > max(pooled(U0), pooled(B0), pooled(D0), pooled(H29-S), pooled(H31-S))`;
   - **(b) Material paired seed gain over baselines & positive paired gain over `H31-S`:** `mean_seed_paired(H33_3-S − D0) >= +0.0020`, `mean_seed_paired(H33_3-S − H29-S) >= +0.0010`, AND `mean_seed_paired(H33_3-S − H31-S) > 0.0`;
   - **(c) 95% paired seed bootstrap CIs & seed consistency:** lower 95% CI `> 0.0` and `>= 8/10` positive seeds vs `B0`, `D0`, and `H29-S`, AND `>= 6/10` positive seeds vs `H31-S`;
   - **(d) Spatial quadrant robustness:** `>= 3/4` positive quadrants vs `B0`, `D0`, and `H29-S`, AND western half-graben improvement (`NW` or `SW` pooled buffered `HOLDOUT-DTI` strictly exceeds `H31-S`);
   - **(e) `E1` passed (`gate_e1_pass = True`).**
3. **`E3` (Validated GeoTIFF + Run Card + Automated Readiness Audit):**
   - Emits `allfinite` (`.tif` + `.zip`) and `nan` companion; verifies `[0, 1]` range, `0` NaN in footprint, `EPSG:32611`, `3730×3292`, `37,654` dots, `<= 140`-char note, and `publication_decision == True` via `scripts/audit_submission_readiness.py`. Fail-closed to `docs/downloads/research/` (`verdict: "negative"`) if any clause fails.
