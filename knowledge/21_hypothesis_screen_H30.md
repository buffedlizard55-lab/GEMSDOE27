# 3–5 untried candidate hypotheses, ranked (Session 9, 2026-10-25) — written BEFORE implementation

Screening basis: expected holdout ΔDTI × P(unique, certifiable) ÷ cost, against the twice-confirmed
Arm-D increment (+0.0076/+0.0086 pooled HOLDOUT-DTI on disjoint seeds) as the reference. Priors are
**MODEL**, not scores. Every candidate names layers, signature, why-it-catches-a-*missing*-fault,
and how it differs from what this repo already implements.

| Rank | ID | Layers | Physical signature | Why a catalogue-missing fault | Differs from repo | Prior ΔDTI | Cost |
|---:|---|---|---|---|---|---|---|
| 1 | **H30 ★LANE** | INGENIOUS/GDR wellspring CSV (hash-pinned `122718e6…`): `temp_c`/`geothermquartz_c` station values (never the catalogue-derived `dist_known_fault_px` column) × Arm-D 32+15 detector | Local thermal-anomaly field (station temp vs 15 px local median), rank-normalised, bounded ±40 % multiplicative re-ranking of the detector surface before ridge NMS + Poisson placement | Buried/basement faults with active upflow host warm, chemically evolved wells without young scarps; the catalogue's scope is surface rupture | H27-12 used distance-to-spring *features* (≈0, refuted); no use of measured values; re-ranker cannot dilute the HGB (E2a's measured failure mode); deconflicted placement is new | +0.002…+0.008 vs B | Low-med |
| 2 | H28-6 gravity-gradient tensor invariants (standalone) | `iso_grav_anom` + `_slope/_vg/_hg` (prepared bands 13/4/9/16) | Vertical gradient, horizontal-gradient magnitude, analytic-signal amplitude as a standalone lineament surface | Blind faults offsetting basement density produce gravity edges under alluvium with no surface trace | H28-1 used magnetic-gravity *cross-field coherence*; a gravity-only invariant surface has never been emitted | 0…+0.002 vs B; standalone live likely 0.05–0.15 | Low |
| 3 | H29-3 soft-probability emission | Arm-D surface emitted as calibrated p∈[0,1] instead of binary dots | Credit hedging at fractional FP cost | — (representation change, not new geology) | Every scored family file is binary | **Deprioritised by theory**: under TP=max-aggregation and linear FP, the per-pixel marginal value is linear in p, so the optimum is bang-bang (binary at the calibrated threshold); soft values only hedge a *miscalibrated* ranking | −0.005…+0.010 but E<0 expected | Low |
| 4 | H29-2 dip-shifted basement-edge placement | Potential-field edges × `depth_to_base_surf` × Qfaults `DIPDIRECT` | Shift deep edges up-dip by depth/tan(dip) before dotting | A dipping fault's surface trace is laterally offset from its basement edge | No geometric dip correction anywhere in the family | Internally ≤0 by construction: withheld catalogue segments sit at mapped traces, so displacing dots off ridge crests can only lose internal credit; dconfirm E2a also measured dip *features* as harmful (E<B) | Medium |
| 5 | H27-16/H28-5 official GDR 1391 packages | paleo-geothermal vectors, 2 m temperature probes, Quaternary volcanics polygons (pins exist; bytes absent) | Sinter/travertine/alteration halos; 2 m sediment temperature; volcanic unit boundaries | Fluid/thermal evidence on unmapped permeable structures | Layers absent from checkout | 0…+0.006 | **Blocked**: gdr.openei.org unreachable from this sandbox; recorded workflow runs failed with zero jobs and no logs (IR logged). Named free official sources: the three GDR #1391 zips (URLs in `knowledge/19`) |

**Order: H30 > H28-6 > H29-3 > H29-2 > H27-16.** H30 is taken this session (preregistration
`knowledge/20`). H28-6 is the fallback lane if H30's canary trips. H29-3's demotion is a theoretical
result recorded so no future session re-derives it; it could be revived as a cheap holdout arm if a
calibration error is ever demonstrated. H27-16 remains blocked on bytes, not on ideas.

**Free official sources for manual review:** DrivenData #306
https://www.drivendata.org/competitions/306/competition-doe-gems/ · problem page
https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ · reference solution
https://github.com/drivendataorg/gems-prize-reference-solution · USGS GeoDAWN
https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and ·
INGENIOUS https://gbcge.org/current-projects/ingenious/ · GDR https://gdr.openei.org/submissions/1391 ·
EPSG:32611 https://epsg.io/32611 · Tversky index https://en.wikipedia.org/wiki/Tversky_index ·
rules https://docs.nlr.gov/docs/fy26osti/96647.pdf
