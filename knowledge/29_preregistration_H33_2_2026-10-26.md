# Session 12 Pre-Registration (Experiment 2 of 3): Hypothesis `H33-2` — Asymmetric Graben Dip-Coupling, Multi-Elevation Magnetic Dip/Verticality Separation, Deconfounded Morphotectonic `M_Full` & Zero-Overlap `min_sep=3.45` Manifold CELF (`AGMC-MDM-CELF345`)

- **Lane Declaration (Parallel-Run Protocol §§1, 6):**
  - **Session Experiment Index:** `2 of 3` (within the `[3]`-experiment / `[2]`-hour budget).
  - **Outcome of Experiment 1 (`H33-1`, `423b1d431032`, seeds `600..609`, preserved unchanged as `verdict: "negative"` in `evidence/h33_s12_run_card_2026-10-26.json`):**
    - `H33-1` **passed all 5/5 frozen `E2` holdout efficacy gates** on seeds `600..609` (`HOLDOUT-DTI = 0.049590` vs `H31-S = 0.046622`, paired `+0.002968`, 95% CI `[+0.001592, +0.004441]`, `9/10` seeds; `+0.003882` vs `H29-S`; `+0.008441` vs `D0`; `+0.009889` vs `B0`) and passed 12-peer uniqueness (`max = 58.67% <= 70%`) and live-scored `GEMSDOE27` uniqueness (`Slot 1 = 58.67%`, `H29-S = 56.61%`),
    - **However**, when `0°` and `45°` OOF surfaces were stitched in `E3`, directed `3-px` dot overlap against unscored Session-10 `H31-1` (`cf8e1bbef244`, listed in the 2026-10-26 prompt) rose from `66.96%` (`quad`) to **`71.21% > 70.00%`**, triggering our fail-closed readiness gate (`ok_to_submit: false`, routed to `docs/downloads/research/`). Per `AGENTS.md` Hard Rule #3, `H33-1`'s gate is never relaxed post-hoc.
  - **Hypothesis ID for Experiment 2:** `H33-2` (`AGMC-MDM-CELF345`, `Lane L-S12B-2026-10-26`)
  - **Root-Cause Diagnosis & Three Physics/Geometry Advances in `H33-2`:**
    1. **Deconfounded Morphotectonic `M_Full` (`57` Stage-1 columns: `20` non-LiDAR base + `15` subsurface + `17` LiDAR-free `H33-2` + `5` deconfounded 1 m LiDAR structural transforms, `max_features = 0.58`):** Dropping the `12` raw un-deconfounded `base_X` `lidar_*` columns from `M_Full` eliminates raw `u8` cliff/shoreline split cloning (`47/66 = 71.2%` column overlap with `H31-1`) while retaining slope-normalized, cross-contour (`sin^2`), wash-bridged, local-prominence 1 m LiDAR scarps.
    2. **Multi-Elevation Upward-Continued Magnetic Dip-Migration vs Vertical Strike-Slip Separation + Walker Lane Seismic-Fabric Coherence (`Rank 2` in `knowledge/28`, addressing `H33-1`'s `-0.00235` `SE` Walker Lane dip):**
       - `h332_mag_up150_downdip_shift`: $[\text{HGM}_{\text{TMI\_up150}}(\mathbf{x}+3\hat{\mathbf{u}}) - \text{HGM}_{\text{RTP}}(\mathbf{x}-3\hat{\mathbf{u}})]_+$ — dipping (`50°–65°`) normal faults migrate down-dip (`+\hat{\mathbf{u}}`) under `150 m` upward continuation (`geodawn_extensions_u8` band 4);
       - `h332_mag_vertical_strike_slip`: $\sqrt{z_+(\text{HGM}_{\text{RTP}})\cdot z_+(\text{HGM}_{\text{TMI\_up150}})} \cdot \exp(-|\text{HGM}_{\text{TMI\_up150}}(\mathbf{x}+3\hat{\mathbf{u}}) - \text{HGM}_{\text{TMI\_up150}}(\mathbf{x}-3\hat{\mathbf{u}})|)$ — sub-vertical (`80°–90°`) Walker Lane strike-slip faults (`SE`) persist strongly in `TMI_up150` with near-zero lateral phase shift;
       - `h332_wl_seis_redox_corridor`: structure-tensor linear anisotropy of `log1p(ieq_n100a15)` and `-deq_n100a15` coupled with dextral `geod_shearrate` and `geodawn_extensions_u8` `UTh` uranium-mobility edges.
    3. **Zero-Interior-Overlap `min_sep_px = 3.45` (`345 m`), `gamma = 1.30` 1-D Manifold CELF Allocation:**
       - Blocks all `37` integer offsets with $d < 3.45\text{ px}$ (`nbr_le_3px_mean == 0.0000`, vs `0.247` at `min_sep = 3.00` and `0.42` at `min_sep = 2.80`), raising blind `300 m` kernel coverage `c_blind` toward `~0.066–0.068` (`GEMSDOE32` live regime) while de-crowding the `200–500 m` near-catalogue ring.
  - **Upgraded `E1` Stitched Duplicate Stop Gate (before touching seeds `610..619`):**
    - `E1` fits **BOTH** `0°` Quadrant OOF and `45°` Rotated OOF first, constructs the **exact stitched `E3` surface and `37,654`-dot emission**, and verifies `max_3px_overlap <= 0.70` and `max_abs_spearman <= 0.90` against **all 12 focus-site peers + `Slot 1` (`5512495c6bd1`) + `H29-S` (`511898747886`) + Session-10 `H31-1` (`cf8e1bbef244`)** **BEFORE** running a single holdout seed in `E2`.
- **Fresh Unconsumed Confirmation Seeds:** `610, 611, 612, 613, 614, 615, 616, 617, 618, 619` (`40` fresh fold-seed cells; strictly disjoint from `0..2`, `100..169`, `210..269`, `300..309`, `400..419`, `500..509`, and `600..609`).

---

## Frozen Promotion & Uniqueness Gates (`E1`, `E2`, `E3`)

1. **`E1` (Univariate Leakage Canary + Full Stitched Pre- & Post-Placement Uniqueness Gate — MUST PASS BEFORE `E2`):**
   - Direction-invariant univariate ROC-AUC `<= 0.90` across all `57` Stage-1 features on seeds `610..619` withheld positives.
   - Stitched (`0.5 * quad + 0.5 * rot45`) pre-placement surface `|Spearman| <= 0.90`, post-placement dot `|Spearman| <= 0.90`, AND directed `3-px` Euclidean dot overlap **`<= 0.70`** against all 12 pinned focus-site peer rasters + `Slot 1` (`5512495c6bd1`) + `H29-S` (`511898747886`) + `H31-1` (`cf8e1bbef244`).
2. **`E2` (Confirmatory Paired 40-Cell Buffered Hide-and-Recover Holdout on Fresh Seeds `610..619`):**
   Evaluated at matched budget `BUDGET_TOTAL = 37,654` (`B2 > 200 m`) against `U0`, `B0`, `D0`, `H29-S`, and prior promoted holdout champion `H31-S` (`cf8e1bbef244` protocol), plus `H33_2-A` (`H33-2` detector + Poisson `d=2.8` ablation). `H33_2-S` promotes (`gate_e2_pass = True`) **if and only if ALL FIVE clauses hold**:
   - **(a) Beats all prior promoted/baseline benchmarks including `H31-S` on pooled buffered `HOLDOUT-DTI`:** `pooled(H33_2-S) > max(pooled(U0), pooled(B0), pooled(D0), pooled(H29-S), pooled(H31-S))`;
   - **(b) Material paired seed gain over baselines & positive paired gain over `H31-S`:** `mean_seed_paired(H33_2-S − D0) >= +0.0020`, `mean_seed_paired(H33_2-S − H29-S) >= +0.0010`, AND `mean_seed_paired(H33_2-S − H31-S) > 0.0`;
   - **(c) 95% paired seed bootstrap CIs & seed consistency:** lower 95% CI `> 0.0` and `>= 8/10` positive seeds vs `B0`, `D0`, and `H29-S`, AND `>= 6/10` positive seeds vs `H31-S`;
   - **(d) Spatial quadrant robustness:** `>= 3/4` positive quadrants vs `B0`, `D0`, and `H29-S`, AND western half-graben improvement (`NW` or `SW` pooled buffered `HOLDOUT-DTI` strictly exceeds `H31-S`);
   - **(e) `E1` passed (`gate_e1_pass = True`).**
3. **`E3` (Validated GeoTIFF + Run Card + Automated Readiness Audit):**
   - Emits `allfinite` (`.tif` + `.zip`) and `nan` companion from the exact `E1`-screened stitched OOF surface; verifies `[0, 1]` range, `0` NaN in footprint, `EPSG:32611`, `3730×3292`, `37,654` dots, `<= 140`-char note, and `publication_decision == True` via `scripts/audit_submission_readiness.py`. Fail-closed to `docs/downloads/research/` (`verdict: "negative"`) if any clause fails.
