# Peer-submission audit and H28-3 decision record (2026-10-25 UTC)

## Scope and evidence standard

This audit reviewed the named owner repositories **GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, and 36** through their GitHub source trees at the pinned commits in `registry/parallel_submission_registry.json`. A peer-repository page, an owner prompt, or a local audit is **not an organizer receipt**. Accordingly, every numerical score below is labelled **OWNER-REPORTED** unless an actual DrivenData receipt is stored (none was found in the reviewed paths). The 0.3195 leaderboard target is likewise **OWNER-REPORTED** in this repository because this agent does not access DrivenData.

The review has two purposes:

1. prevent accidental reuse of a peer raster or its one-mechanism derivative; and
2. decide which *currently untried, data-ready* geological mechanism earns one pre-registered holdout experiment.

The official scientific context remains the GEMS rules and problem description, the GeoDAWN airborne geophysics record, and GDR #1391 / INGENIOUS. Manual-review links are in `registry/sources.json` and the source table on `docs/sources.html`. The training raster restored for this run is an owner mirror, hash-pinned in `data/manifest.json`; it is not represented as an organizer-authenticated download.

## What the claimed 0.2778 GEMSDOE32 artifact actually is

The requested file is `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif`. Its own audit calls it **H33-2-B2**: a 37,654-dot raster obtained by deleting every dot at Euclidean distance <=2 100-m pixels from the published catalogue from a 40,199-dot, one-pixel-flank-pruned D2.8 base. It contains no new detector, fault interpretation, or external geological observation. Its repo's audit records local format checks, a proxy “live-mirror” gain, and a projected 0.2747—not an organizer score. The owner prompt supplied the separate 0.2778 score assertion. These statements conflict in evidence class, so this project records **0.2778 as OWNER-REPORTED ONLY**, never organizer-confirmed.

### Why the mechanism could appear to work

The metric charges false-positive mass at alpha=0.2 and grants distance-weighted credit only within the 300-m triangular kernel. If a prediction is very close to a *published* catalogue trace but the organizer masks that trace from scoring, such a dot can carry cost while earning little score credit. The claimed D2.8 -> 0.2708 controlled contrast is a useful, but owner-reported, observation: the 40,199-dot file is reported to equal the 44,090-dot D2.8 set after removal of 3,891 dots within one pixel of the catalogue. H33-2-B2 extrapolates that same removal mechanism from 100 m to 200 m.

This is a metric-operating-point explanation, not evidence that the deleted pixels are geologically false faults. It can fail when the unpublished organizer labels lie near the catalogue, when catalogue / organizer registration differs, or when the private-label spatial distribution differs from the SGMC-based proxy. GEMSDOE32 itself documents that its local mirror produces implausible scores when used outside small, mechanism-matched perturbations. Thus no claim is made that H33-2-B2 will beat 0.2778, 0.3195, or any score at all.

## High-score claims reviewed and duplication implications

| Site / source artifact | Claim in owner materials | Physical/mechanical content found in peer source | Audit consequence |
|---|---:|---|---|
| GEMSDOE24 H25-1 D1.5 | **OWNER-REPORTED 0.2477** | Dotted / Poisson-thinned H19-5 ridge surface | Do not reproduce or re-thin as “new.” |
| GEMSDOE25 / GEMSDOE30 D2.8 | **OWNER-REPORTED 0.2600**; peer pages also flag score-to-file attribution unresolved | Wider-spaced dotted H19-5 surface | A shared baseline, not a novel candidate. |
| GEMSDOE27 T-v2 | **OWNER-REPORTED 0.2449** | Topology gap closure added to D1.5 | Negative live A/B relative to its claimed D1.5 parent; not reused as a positive strategy. |
| GEMSDOE28 / GEMSDOE31 H27-4 | **OWNER-REPORTED 0.2708** | Delete D2.8 dots within one 100-m cell of the catalogue | A catalogue-flank prune lane; no new candidate may be a broadened/relabelled prune. |
| GEMSDOE28 H36/H38 | **OWNER-REPORTED 0.2710 / 0.2707** in the owner prompt | Re-packing / small corroborated additions | Must be included in final raster similarity checks. |
| GEMSDOE32 H33-2-B2 | **OWNER-REPORTED 0.2778** in the owner prompt; peer audit says unscored | 200-m catalogue-flank pruning of the H27-4 base | Explicitly excluded from this lane; it is the central duplicate risk. |
| GEMSDOE33 H33-D | **OWNER-REPORTED 0.2632** | Analogue / tip-stepover protection plus Euler additions | Include in final similarity registry; it is not adopted. |
| GEMSDOE36 Anderson-PINN | **OWNER-REPORTED 0.2750** | Anderson-orientation filter plus geothermal / basement additions | Include in final similarity registry; peer source offers only proxy validation. |

## Candidate slate required before implementation

The current 3–5 candidate screen is `knowledge/07_untried_hypotheses.md` and `registry/next_hypotheses.json`. The five operational entries for this session are ranked below. Ranges are planning priors for the **catalogue-internal holdout**, not leaderboard-score forecasts.

| Rank / status | Candidate | Specific layers and physical signature | Why it could find a missing catalogue fault | Difference from reviewed work | Expected holdout delta / cost / data readiness |
|---|---|---|---|---|---|
| 1 — data-blocked | H27-16, paleothermal / 2-m probe / volcanics | GDR #1391 paleo-geothermal alteration, 2-m temperatures, Quaternary volcanic polygons | Independently measured heat, alteration, and young volcanism can expose fluid pathways where mapping lacks a trace. | New raw geometries, not a catalogue flank operation. | +0.000–0.006; medium-high; **blocked** until official bytes and SHA-256s are obtained. |
| 2 — **selected** | H28-3, dilatational-strain × conductivity corridor | Existing `geod_2ndinv`, `geod_shearrate`, `geod_dilaterate`, `cond_surf`, `depth_to_base_surf`; 300-m label-free co-location / gradient corridor transform | A blind or alluvium-covered strand can concentrate strain and fluid-altered conductivity without a young scarp. | No pixel deletion or re-spacing of a peer raster; uses an explicit spatial conjunction absent from this checkout’s scalar-channel detector. | +0.000–0.003; low-medium; hash-pinned owner-mirror raster is present. |
| 3 — ready | H28-4, seismicity-fabric lineaments | `deq_n100a15`, `ieq_n100a15`, `geod_shearrate`; directional multi-scale persistence | An aligned earthquake fabric may mark blind active structure. | Directional seismicity transform, distinct from prior broad LiDAR/geophysical line integration. | +0.000–0.002; low-medium; existing raster. |
| 4 — provenance-limited | H28-5, hydrothermal chemistry gradients | GDR well/spring temperature and geothermometers after QA/deduplication | A fluid-chemistry contrast may identify upflow along an untraced structure. | Not the previously refuted isotropic distance-to-spring feature. | +0.000–0.003; medium; raw official GDR binary is not locally re-hashed. |
| 5 — required negative control | uniform replacement at the same emission count | Same output geometry and count, but random eligible locations drawn deterministically | Has no geological mechanism; quantifies whether a proposed signal beats geometry alone. | A formal negative control, not a geological candidate. | Expected <=0; low; generated only inside the frozen H28-3 holdout protocol. |

**Selection rationale:** H27-16 has the largest prior but is correctly blocked by provenance. H28-3 is therefore the highest-ranked ready idea. It is not a reimplementation of H33-2-B2, H27-4, topology closure, D2.8 thinning, Anderson orientation, GDR thermal-conduit addition, or a peer submission raster.

## H28-3 pre-run leakage canary

Before the holdout run, each source layer was tested alone against the owner-mirror catalogue solely as a leakage screen. Direction-invariant ROC AUCs were: `geod_2ndinv` 0.5702, `geod_shearrate` 0.5690, `geod_dilaterate` 0.5255, `cond_surf` 0.5167, and `depth_to_base_surf` 0.5119. All are below the protocol’s 0.90 leakage canary. These are not efficacy results and do not validate the candidate; the values and command are reproduced by `scripts/run_h28_3_strain_holdout.py --canary-only` after implementation.

## Frozen next step

`knowledge/13_preregistration_H28-3.md` fixes the feature transform, baseline, component-hidden spatial holdout, seeds 160–169, controls, success rule, and no-slot rule. The run will create no TIFF. A unique download-ready GeoTIFF is generated only if that frozen gate passes and the final raster separately clears the registry rank-correlation / spatial-overlap duplicate checks.
