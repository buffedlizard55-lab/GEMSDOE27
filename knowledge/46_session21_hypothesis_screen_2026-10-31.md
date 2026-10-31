# Session 21 hypothesis screen + H34-1 preregistration (2026-10-31)

Scope: this repository's ledger (`registry/next_hypotheses.json`, `registry/hypotheses.json`,
`evidence/`, `knowledge/`) and the restored 32-band cached stack. This is a screen of ideas in
THIS repository, not a global novelty claim. "Untried" = no run in this repository. Expected
gains are qualitative: no candidate has a validated numerical prior, and a holdout DTI is a
diagnostic, not a leaderboard projection.

Ranking basis: (a) can the test run on the restored, hash-pinned cached bands; (b) is the
formulation not a duplicate of an already-tested family; (c) implementation cost. The lane
paragraph the parallel-run protocol names is again absent from the prompt (see
`registry/irregularities.json`, `IR-2026-10-31-lane-paragraph-still-missing`), so this session
runs the registry's highest-ranked *runnable, non-duplicate* candidate and records the deviation,
exactly as Sessions 12/17 did.

## Candidates (3-5), ranked

| Rank | ID | Layers | Physical signature | Why it could catch a catalogue-missing fault | Named non-fault mimic | Differs from what is in the repo | Cost |
|---|---|---|---|---|---|---|---|
| 1 | **H34-1** magnetic-gravity gradient **alignment** | `rtp`, `iso_grav_anom` | `min(|∇M|,|∇G|)·|cosθ|`: both fields show a strong edge and the two edges are parallel | A fault juxtaposes density and susceptibility contrasts, so both horizontal-gradient vectors point across it (θ≈0); a buried/unmapped segment still shows the coincident contrast | Parallel lithologic contacts; basin-margin stratigraphic contacts; survey lineation seams; remanence stripes | H29-XG tested the CROSS-PRODUCT `|∇g×∇m|` (large when PERPENDICULAR) and was negative; this is the orthogonal DOT-PRODUCT complement, never run | Low (cached bands, ~10 min) |
| 2 | H34-2 LiDAR **exposure-gated** scarp | `lidar_step_max`, `lidar_lappos_max`, `lidar_coh100` | Scarp strength weighted by 1-coherence (bare/stable terrain) | Vegetation masks LiDAR scarps; gating exposes real scarps in bare areas and suppresses vegetation false positives | Terrace risers on bare slopes; channel banks; cultural edges | `coh100` appears only inside `hydrothermal_piedmont` band 5 and `tomography`; never as a standalone gate | Low (cached bands) |
| 3 | H34-3 Radon/U–Th anomaly **triple conjunction** | `geodawn_rad_u8` (U, Th, U/Th), `rtp`, `iso_grav_anom` | Co-located U/Th anomaly, magnetic low and gravity high | Hydrothermal fluids redistribute U/Th along permeable fault conduits while oxidising magnetite | Playa/evaporite U anomalies; soil radiogenic enrichment | Addendum D tested radiometric VALUES and front gradients in wider arms (negative); a spatially co-located U–Th–magnetic–gravity triple conjunction was not a standalone arm | Medium (cached bands) |
| 4 | H34-4 Basement-step **along-strike continuity** | `depth_to_base_surf`, `geod_dilaterate`, `iso_grav_anom_hg` | A basement-depth step that persists along strike over 1-2 km with shear localised on it | A concealed range-front fault steps the basement without a young scarp; continuity separates it from a localised lithologic step | Dip-controlled stratigraphic step; basin-margin unconformity | H30-1 tested dip-advection sampling; H31-3 tested cross-strike graben pairing; neither tested along-strike step persistence as a ridge | Medium (cached bands) |
| 5 | H34-5 MT conductive cap **∧** magnetic low **∧** gravity step | `cond_surf`, `tmi`, `iso_grav_anom` | A conductive alteration cap sitting on a magnetic low and a density step | Clay-cap alteration over a buried upflow conduit correlates magnetic and gravity edges | Evaporative playa salt; clay-rich lithology | H31-3 tested conductive-cap pairing against depth-to-basement (negative); this adds the magnetic-low conjunction | Medium-high (cached bands) |

Ranks describe experiment priority conditional on the lane/data gates, not predicted scores.

## H34-1 preregistration (frozen before the run)

- **Hypothesis:** the magnetic-gravity gradient ALIGNMENT surface carries information about
  coincident density/susceptibility contrasts (faults) that the single-physics gravity
  horizontal-gradient control does not.
- **Mechanism:** `score = min(|∇M|,|∇G|)·|cosθ|` over smoothed (σ=2 px) RTP and isostatic
  gravity; percentile-ranked within the footprint.
- **Named non-fault process that could mimic it:** parallel lithologic contacts juxtaposing
  contrasting density and susceptibility; basin-margin stratigraphic contacts; airborne-survey
  lineation seams; remanent-magnetisation stripes.
- **Emission:** `ridge_nms(σ=1)` on the ranked surface; strict B2 collar (d_cat > 2.0 px);
  priority Poisson-disk at 2.8 px; budget 37,654 px (the live-anchored d=2.8 operating point).
- **Control:** identical machinery on `iso_grav_anom_hg` (single-physics gravity edge).
- **Leakage canary (E1):** H34-1 alone on withheld positives; stop if direction-invariant AUC
  > 0.90.
- **Holdout (E2):** whole-component buffered hide-and-recover (buffer 6 px), visible-only
  catalogue features, pixel-exact visible masking, pooled + paired HOLDOUT-DTI
  (`gems27.metric.dti_binary` v1, α=0.2, β=0.8, 300 m triangular).
- **Seeds:** 900-909 (fresh; 120-809 consumed).
- **Promotion rule:** paired mean ΔDTI > 0 with the 95% CI excluding zero, on ≥8/10 seeds, AND
  the lane uniqueness gate passing against the 12 pinned registry rasters. Otherwise negative.
- **Limitations to record:** the holdout truth is catalogue-internal (proxy), so the result is
  a diagnostic and NOT an organizer score; the control is a single-physics edge, not the full
  current-best H29-S/H31 architecture, so a win here is not automatically a slot authorization.

## Addendum — H34-1 result superseded by the whole-FID matched-control test

This branch preregistered and ran H34-1 on a **component/quadrant split with a gravity-only control** and
observed a positive catalogue-internal proxy (pooled HOLDOUT-DTI 0.017740 vs 0.014084; paired 95% CI
[+0.001939, +0.005431]; 9/10 seeds positive; 121,621 withheld positives).

A parallel Session 21 branch ran the **same hypothesis under the required whole-FID buffered hide-and-recover
protocol with a matched control Bc** and measured pooled HOLDOUT-DTI **0.000526 vs 0.025996** — i.e. **NEGATIVE**
(`evidence/h34_1_e2_holdout_900_909.json`, `evidence/h34_1_run_card_2026-10-31.json`).

The component/quadrant proxy result above is therefore **SUPERSEDED** and must not be read as support for H34-1.
The generated TIFF (`docs/downloads/h34/gems27-h34-1-align-b2-20261031-8e61fd96ce99-allfinite.tif`) is a research
artifact, NOT OK TO SUBMIT. Recorded as `IR-2026-10-31-h34-1-proxy-superseded`.
