# PhD-level analysis: Why GEMSDOE32 h33-h33-2-b2 scored 0.2778, and whether we can beat it

**Status:** OWNER-REPORTED score (no DrivenData receipt; the agent does not access drivendata.org per Terms of Use). All raster measurements are MEASURED this session from hash-authenticated sibling files. DTI model quantities are MODEL, not scores.

## 1. What the 0.2778 file actually is (MEASURED, pixel-exact)

`gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` (sha256 `c55bafc4…`) was reconstructed pixel-exactly from the GEMSDOE28/GEMSDOE31 file `h27-4-r1-solo-d2-8` (content id `8acb75e1`, owner-reported 0.2708):

| Step | Operation | Dots | Owner-reported score |
|------|-----------|------|---------------------|
| 0 | `dot_thin(H19-5 minus catalogue, 2.8)` | 44,090 | 0.2600 |
| 1 | Remove dots with d(catalogue) ≤ 1 px | 40,199 | 0.2708 |
| 2 | Remove dots with d(catalogue) ≤ 2 px | 37,654 | **0.2778** |

The identity `b2708 & (d_cat > 2) == w2778` is **True, pixel-exact** (this session). No new geology, no new detector: the entire gain from 0.2708 → 0.2778 is a **deletion** of 2,545 dots (6.3% of the file), all within 100–200 m of a mapped catalogue trace.

## 2. Why deletion raises DTI (MODEL, from `src/gems27/metric.py`)

The official metric:

    DTI = TPw / (0.2·TPw + 0.2·FPw + 0.8·|G|)

At the 0.2477 operating point, false positives carry ≈49% of the denominator. A pixel deletion raises DTI iff its credit efficiency dTP/dFP < 0.2·DTI/(1−0.2·DTI) ≈ **0.052–0.059** at DTI 0.25–0.28. Dots 100–200 m from a known fault have near-zero credit efficiency for three compounding reasons:

1. **Masking asymmetry.** Catalogue pixels are masked out of scoring; hidden truth is by construction *not* the catalogue. A dot hugging a known trace can earn credit only if a distinct hidden fault pixel lies within its 300 m kernel — geometrically unlikely when the dot exists because the detector fired on the known fault's own scarp, rasterised 1–2 px off the mapped trace (dip offset + 100 m quantisation).

2. **Detector echo.** The H19-5 family corroborates lines across topography/geophysics; its strongest responses are on mapped structures. The 100–200 m annulus is where the echo of a *known* fault lives. GEMSDOE27 measured the r≤1 version OOF (+0.0022 solo, +0.0141 stacked); GEMSDOE32 extended the radius to 2 px and live-mirrored +0.00487 in 4/4 folds.

3. **Budget interaction.** Dotting already moved the family to the flat optimum (44,090 px at d=2.8). Removing the lowest-credit 6–15% of mass slides along the same curve: 0.2600 → 0.2708 (r≤1) → 0.2778 (B2).

## 3. The convergence evidence (MEASURED)

All five top files (0.2600, 0.2632, 0.2708, 0.2750, 0.2778) are the **same dot field re-thinned**: 91–100% of each file's dots lie within 3 px (Chebyshev) of the 0.2778 file's dots. GEMSDOE36's independent PINN (owner-reported 0.2750, re-read here: 38,854 dots, also **0 within 2 px**) converges on the same B2 + ~38k optimum from unrelated physics. This is the strongest cross-method evidence that the optimum is real and emission-side.

## 4. Can we beat 0.2778? (PhD judgement)

| Path | Probability | Expected margin | Verdict |
|------|-------------|-----------------|---------|
| Another H19-5 emission edit (thinning/pruning) | 0.5–0.65 | +0.003–0.010 | **FORBIDDEN** by the uniqueness rule (>70% overlap with registry raster) |
| Genuinely new detector at B2/38k | 0.25–0.40 per attempt | +0.01–0.03+ | Only path to 0.30+, requires new information |
| Rearranging existing pixels | ≈0 | 0 | **Arithmetically impossible** — the emission-geometry lever is exhausted at ≈0.255 |

**Why rearrangement can't reach 0.3195:** At 60,069 px, 0.3195 needs 0.570·|G| of credit — more than any submission in the group's history has ever earned (best ever: 0.508·|G|). At 44,090 px it needs 0.486·|G|, which H19-5 solid earns (0.506) but thinning to that budget retains only 0.759 → 0.384. **Retention, not knowledge, is the wall.**

**The contrarian bet:** Faults missing from a surface-rupture-scoped catalogue (USGS Q-fault scope ≈ evidence of coseismic surface deformation in ~1.6 Ma) are preferentially the ones **without young scarps** — buried beneath alluvium or older bedrock structures. Those express in potential fields, strain, conductivity, and seismicity fabric, not in the lidar-scarp bands that drive H19-5. A subsurface-only detector is the only design whose dot placement is physically expected to decorrelate from H19-5 (dipping-fault edges are laterally offset from surface traces), satisfying uniqueness by mechanism rather than by jitter.

**Session result:** Lane L-2026-10-25 (subsurface-only buried-fault detector, B2/38k) ran a frozen holdout gate: pooled HOLDOUT-DTI 0.0752 vs full-32 control 0.1001 (Δ −0.0262, 95% CI [−0.0368, −0.0163], 60,423 withheld positives). **FAILED.** H28-4 seismicity-fabric lineaments (this session, 2 seeds): mean gain −0.00067, 0/2 seeds improved. **FAILED.** The catalogue-internal proxy cannot see far-field credit by design.

## 5. Bottom line

Beating 0.2778 requires **new detector information**, not more emission surgery. The group's best files have plateaued at 5.3–5.7× blind concentration; reaching 0.3195 needs concentration above 5.7 or retention ≈1.0 at ~44k px — both detector problems. No rearrangement of existing pixels can close the gap. A supervised scarp detector on the 1 m DEM with geologist-labelled scarps, or new external data (GDR 1391 paleo-geothermal layers, 2 m temperature probes, Quaternary volcanics polygons), remains the most plausible route — but none is currently available in this checkout or validated on holdout.
