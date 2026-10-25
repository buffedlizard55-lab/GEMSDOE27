# H29-1 preregistration — D-refill lane (frozen 2026-10-25, BEFORE fresh-seed run)

**Session lane (single method paragraph, PARALLEL-RUN PROTOCOL §1).** Full 32-band cached
feature stack **plus** the 15 label-free subsurface transforms
(`src/gems27/subsurface_features.py`: potential-field gradient/tilt/analytic-signal edges,
cross-field coherence, conductivity / basement-depth / strain gradients, seismicity fabric),
HistGradientBoosting ranking (shared `gems27.oof_detector`, unchanged hyperparameters),
ridge NMS, priority Poisson-disk ≥ 2.8 px, **B2** exclusion (no dot within 2 px = 200 m of a
*visible* catalogue fault), **38,000-dot** budget, binary {0,1}, all-finite primary file.
This is Arm **D** of `evidence/lane_holdout_2026-10-25.json` shipped as an independent
full-map emission. It was a control there (never shipped); H28-1's file is different
(59,075 px, r≤1 prune + T-v2 dots stacked on an H19-5-derived base, not a D-surface emission).

## Why this could beat 0.2778 (OWNER-REPORTED; `knowledge/12`)

0.2778 is pixel-exactly H19-5 re-thinned minus dots ≤2 px from the catalogue: pure FP-mass
deletion on a frozen detector. At the same B2/~38 k emission, score differences can only come
from *which* pixels the 38 k dots occupy, i.e. detector ranking. Arm D added
**+0.0045 HOLDOUT-DTI (95 % CI [+0.0003, +0.0090], 15/20 cells, seeds 200–204)** over the
full-32 control — the only significant positive increment measured in this repo that has never
been emitted at the live optimum. Subsurface edges target faults the surface-rupture-scoped
catalogue misses (buried under alluvium / pre-Quaternary), complementing lidar scarps.
**Named non-fault mimics:** lithologic contacts, survey seams, remanent magnetisation,
clay-cap conductivity highs, basin-margin steps.

## Frozen confirmatory test (fresh seeds; 200–204 are consumed and must not be reused)

- **Seeds 210–214** × 4 quadrants = 20 cells; buffered hide-and-recover
  (`holdout.buffered_scoring_mask`, 6 px ring); visible faults masked pixel-exactly;
  every catalogue-derived quantity (B2 distance) from visible faults only.
- Arms: **D** (lane) vs **B** (full-32, no transforms), identical emission
  (ridge NMS → B2 → priority Poisson-disk 2.8 px, matched per-fold budgets summing to 38,000).
  OOF probabilities are fold-safe (600 m train buffer); detector seed fixed as in shared code.
- **E1 canary:** each of the 15 transforms alone, AUC vs hidden truth on seed-210 splits.
  Any AUC > 0.90 ⇒ leakage, stop.
- **Promote gate (all required):** pooled HOLDOUT-DTI(D) > pooled HOLDOUT-DTI(B) **and**
  paired mean Δ > 0 **and** ≥ 12/20 cells positive **and** canary clean **and**
  uniqueness PASS (surface Spearman ≤ 0.90 and final-dot ≤3 px overlap ≤ 70 % vs *every*
  raster in `registry/parallel_submission_registry.json` + this repo's shipped candidates)
  **and** validator hard-PASS (all-finite, [0,1], EPSG:32611 3730×3292, no NaN in footprint).
- Any failure ⇒ verdict **negative**, file badged ⛔ DO NOT SUBMIT, no post-hoc tuning,
  no seed shopping. A holdout pass does **not** guarantee a live score (catalogue-internal
  proxy; `knowledge/10`); the run card never writes a projection as a score.
- Budget: E1+E2+E3(build) = 3 experiments. Promotion to a weekly slot remains the owner's
  separate selector step (protocol §6); this session only certifies gate status.

## Ranked untried hypotheses screened this session (top = H29-1, tested above)

| Rank | ID | Layers / signature | Why a catalogue-missing fault | Differs from repo | Prior ΔDTI (MODEL) / cost |
|---:|---|---|---|---|---|
| 1 | **H29-1 D-refill** | 32-band stack + 15 subsurface transforms; HGB rank; B2/38 k Poisson | Buried/older faults edge in magnetics/gravity/depth without young scarps | First independent D-surface emission at live optimum | +0.003…+0.012 live (MODEL) / low |
| 2 | H29-2 dip-shift correction | Potential-field edges + `depth_to_base_surf` + Qfaults DIPDIRECT/dip stats; shift deep edges up-dip by depth/tan(dip) before dotting | Dipping fault's surface trace is laterally offset from its basement edge; uncorrected dots sit 100s of m off-trace | No geometric dip correction anywhere in family | 0…+0.008 / medium (vector data already pinned) |
| 3 | H29-3 soft-probability emission | Same D surface emitted as calibrated p∈[0,1] optimised under exact soft DTI instead of binary dots | Uncertain far-field candidates can be hedged at fractional FP cost | Every scored family file is binary | −0.005…+0.010 / low (needs its own holdout vs binary) |
| 4 | H28-4 seismicity fabric | `deq/ieq_n100a15` directional persistence × shear gradient | Blind active strands lineate seismicity without scarps | Channels used only as scalars so far | 0…+0.002 / low-medium |
| 5 | H27-16/H28-5 GDR hydrothermal | GDR #1391 sinter/travertine, 2 m probes, volcanics polygons | Fluid-flow evidence on unmapped permeable faults | Layers absent from checkout | 0…+0.006 / high — **blocked: official bytes not yet obtained/hash-verified in this sandbox** |

Free official sources (manual review): DrivenData #306
https://www.drivendata.org/competitions/306/competition-doe-gems/ · reference solution
https://github.com/drivendataorg/gems-prize-reference-solution · USGS GeoDAWN
https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and ·
INGENIOUS/GDR https://gdr.openei.org/submissions/1391 · https://gbcge.org/current-projects/ingenious/ ·
CRS https://epsg.io/32611 · metric basis https://en.wikipedia.org/wiki/Tversky_index ·
rules PDF https://docs.nlr.gov/docs/fy26osti/96647.pdf
