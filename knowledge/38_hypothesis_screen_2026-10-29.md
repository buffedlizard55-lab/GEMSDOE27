# Hypothesis screen, 2026-10-29 (three to five candidates, ranked)

Scope: the registry (`registry/next_hypotheses.json`, `registry/hypotheses.json`), the knowledge ledger (`knowledge/`), and the sibling-site raster inventory (`evidence/focus_inventory_20261027.json`). This is a screen of ideas in this repository's ledger, not a global novelty claim. "Untried" means no run in this repository. Expected gains are qualitative: no candidate has a numerical prior.

Ranking basis: (a) whether the test can run with cached, hash-pinned local inputs; (b) whether the formulation is not a duplicate of a tested family; (c) implementation cost.

| Rank | ID | Layers | Physical signature | Why it could catch a catalogue-missing fault | Named non-fault mimic | Differs from what is in the repo | Status and evidence | Cost |
|---|---|---|---|---|---|---|---|---|
| 1 | **H29-XG** joint gravity–magnetic cross-gradient | `iso_grav_anom`, `rtp` (cached) | Coincident gravity and magnetic edges that are not parallel: \|∇g × ∇m\| | A basement step that juxtaposes two domains can show both contrasts, even if no surface trace exists | Lithologic contacts with both contrasts; terrain-correlated residuals | The stack has gradient magnitudes (`iso_grav_anom_hg`, `tmi_hg`) and the H28-6 scale persistence, but no joint-direction term | **Run in this session** (preregistered, `knowledge/39`). Literature: Gallardo & Meju 2003 (doi:10.1029/2003GL017370), 2004 (doi:10.1029/2003JB002716). A sibling GEMSDOE25 `xg1-crossgrad` raster exists with no recorded score; not in the 12 pinned rasters | Low (cached inputs, about 30 min) |
| 2 | H28-7 directional radiometric alteration continuity | GeoDAWN K, Th, U (`geodawn_rad_u8.tif`) | Orientation-coherent K/Th fronts along a line | Fluid flow along a fault alters bedrock beyond the trace | Soil and lithology contrast | **Duplicate of a tested family.** The radiometric alteration-front edges were tested in D-confirm as part of `dip_rad_features` (`knowledge/16`: "the 8 new dip/rad/polarity transforms hurt as detector augmentation (E < B < D)"). The K–Th front (`h29_k_th_alter_grad`) was computed and canary-tested in `evidence/h29_e1_canary_and_surface.json` | Low, but would repeat a tested result. **Not run** |
| 3 | H27-16 GDR #1391 sinter/tufa and 2 m probes | GDR packages (paleo-geothermal, 2 m probes, Quaternary volcanics) | Sinter alignments with positive probe residuals | Fossil sinter marks upflow conduits | Lacustrine tufa on Lake Lahontan shorelines | **Blocked.** `gdr.openei.org` returns HTTP 000 from this sandbox (checked 2026-10-29 with `curl`). Metadata only, via the fetch tool (`knowledge/37`). Not runnable | Unknown until bytes are obtained |
| 4 | H29-5 routed drainage and fan-apex collinearity | USGS 3DEP DEM (raw) | Collinear canyon-mouth knickpoints and fan apices | Fans bury scarps but leave aligned outlets | Resistant hogbacks crossed by streams | **Blocked.** The raw DEM is not in the sandbox. `usgs.gov` is unreachable (`knowledge/37`); the proxy `H29-5-PROXY` is a different operator and was negative | Unknown |
| 5 | H28-6 scale-persistent gravity edges | `iso_grav_anom` | Persistence of horizontal-gradient edges at 1, 2 and 4 px | Buried density boundaries | Basin-fill density pinch-outs | **Tested, negative** (2026-10-28, `knowledge/37`): C 0.041238 vs D 0.041574 (HOLDOUT-DTI), and the dots broke the 70% local-overlap stop. No TIFF written | Done |

## Decision

1. **Run H29-XG** (rank 1). It is the only candidate that is both runnable on cached inputs and not a duplicate of a tested family.
2. **Do not run H28-7** (rank 2). Its signal is a repeat of a result on file.
3. **Record the blocked items** (ranks 3–4) as blocked, not as failed. The blocked sources are the data needed for any future test. They are listed as limits in the README.

## Note on the alternative sources (overlooked but blocked)

- DOE GDR #1391 (`https://gdr.openei.org/submissions/1391`, DOI 10.15121/1881483, CC-BY-4.0) is the official source for the sinter/tufa, probe and volcanic packages. It is unreachable from the sandbox, so this session cannot verify those packages. The owner-side URLs are in `scripts/fetch_external_layers.py`.
- USGS 3DEP (`https://www.usgs.gov/3d-elevation-program`) is listed but not reachable from the sandbox.
