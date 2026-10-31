# Geothermal-vent research (official sources) — stored 2026-10-31

Purpose: satisfy the standing request to "store deep geothermal-vent research from official
sources", and to source the H35-5 volcanic-vent-transfer hypothesis screen. **Sourcing
discipline (AGENTS.md):** this sandbox can only fetch `github.com`; every line below is
labelled by provenance. Nothing here is a score, a projection, or an organizer claim.

Provenance labels used:
- **[FETCHED 2026-10-31]** — bytes actually retrieved in this session.
- **[REPO-CACHED]** — quoted from files already in this repository that transcribe official
  sources; the official URL is given for manual verification; not re-fetched here.
- **[NOT FETCHED — allowlist]** — official source named and linked, unreachable from this
  sandbox; content not verified here.

## 1. Official competition reference solution

- **[FETCHED 2026-10-31]** https://github.com/drivendataorg/gems-prize-reference-solution —
  "Reference solution for the GEMS Prize Challenge", author Prof. John Lipor
  (Portland State; https://web.cecs.pdx.edu/~lipor/). Single commit `aebe92f`
  (2026-06-16). The benchmark is the notebook `unet-mc-cv-reference-solution.ipynb`
  (U-Net with Monte-Carlo cross-validation), "implemented in Python and uses standard
  libraries to provide a baseline for comparison with other solutions". README instructs:
  "Download the data from the GEMS Prize Challenge website and place it in the `data/`
  directory." Environments: `environment.yml` (GPU) / `environment-cpu.yml` (CPU).
  Takeaway for this repo: the organizer's own baseline is a **pixel-model (U-Net)**, not a
  dot emitter — consistent with the knowledge/07 finding that only new detector information
  moves the score. This URL is already cited on the site's Sources page.

## 2. GeoDAWN / INGENIOUS / 3DEP — the official layer stack behind the cached features

- **[NOT FETCHED — allowlist]** USGS GeoDAWN airborne magnetic and radiometric surveys,
  northwestern Great Basin, Nevada:
  https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
- **[NOT FETCHED — allowlist]** DOE INGENIOUS Geothermal Data Repository submission #1391
  (well/spring temperature and chemistry packages): https://gdr.openei.org/submissions/1391
- **[NOT FETCHED — allowlist]** USGS 3D Elevation Program (3DEP) LiDAR:
  https://www.usgs.gov/3d-elevation-program
- **[REPO-CACHED]** `registry/next_hypotheses.json` rows 1–3 and `knowledge/41`'s task-prompt
  transcription state, from those official datasets: wells and springs temperature data
  (27,092 stations), hot springs (89 stations above 30 °C), thermal-gradient wells
  (332 records) and mineral occurrence data (439 sites), plus a Quaternary fault and fold
  database and volcanic vent locations. The in-repo cached stack is `data_cache/` (hash-pinned
  in `data/manifest.json`; owner-mirrored bytes, "not independently organizer-authenticated").

## 3. Volcanic vents and geothermal systems — the geological research record

- **[REPO-CACHED]** `knowledge/41` records the prompt's citation of **Mack et al.** for
  mid-Pleistocene (17 Ma is the prompt's transcription) caldera-forming eruptions whose
  post-caldera lavas record vent locations, with "vents younger than 763 ka" as the
  Quaternary expression, and **Williams (1996)**, "Quaternary volcanic and tectonic
  segmentation of the western Great Basin", *Monogenetic volcanoes and their vents*,
  for vent distribution and alignment. These are the scientific basis for treating vent
  alignments as **structural transfer corridors** (conjugate/transfer segments between
  fault systems).
- **[NOT FETCHED — allowlist]** The Mack et al. and Williams (1996) publications themselves
  were not re-fetched here (publisher sites are outside the sandbox allowlist). Do not quote
  page-level claims beyond the repo-cached transcription without a human re-check.

## 4. H35-5 volcanic-vent transfer corridors — the derived hypothesis (research only)

Screened and ranked #5 before implementation in `knowledge/45` (full six-dimension screen:
layers, physical signature, why it could catch a catalogue-missing fault, named non-fault
mimic, novelty vs this repo, cost):

- **Layers and physical signature:** the 21 Quaternary vents recorded in the cached stack;
  vent-alignment corridors and conjugate transfers: linear vent chains mark buried
  displacements/tip damage of blind fault segments ("vent-feeding structures can be blind but
  aligned").
- **Why it could catch a catalogue-missing fault:** magma exploited fault-parallel
  permeability; a young vent lineament can record the structure where no scarp survives.
- **Named non-fault mimic:** random cinder-cone clustering, regional stress-aligned dike
  swarms without fault displacement.
- **Novelty vs this repo:** vents were only auxiliary distance bands in earlier feature
  sets; no vent-alignment emitter has been tested here. The SGMC-only emission analogue is a
  tested negative (0.0512 OWNER-REPORTED), so a vent-only emitter must beat that bar or be
  used as a conjunction.
- **Cost:** low (point geometry + directional continuity; no new rasters required).
- **Status: untried.** Ranked below H35-2 (hydrothermal-discharge lineaments) because the
  vent count (21) is small and prior geometry-only emitters have plateaued at ≈0.255
  (knowledge/07 retention wall). It is not a validated lever and must not be presented as one.

## 5. What is still needed before any vent-based lane can run

1. Human re-check of the Mack et al. / Williams (1996) citations against publisher pages
   (the prompt's "17 Ma" and "763 ka" figures conflict with the regional Quaternary vent
   literature as usually stated; treat both as OWNER-REPORTED transcriptions until checked —
   recorded as `IR-2026-10-31-vent-citation-ages-unverified`).
2. GDR #1391 package bytes are still blocked for direct fetch (H27-16 remains blocked);
   the wells/springs residual for H35-2 must come from the cached `wells`/`springs` layers
   (already in the 32-band stack's provenance set) rather than new downloads.
3. Any resulting file must clear the same gates as `knowledge/46`: canary AUC ≤ 0.90
   direction-invariant, ≥70% uniqueness vs the 12 pinned rasters **and** vs local
   `docs/downloads/**` rasters, positive paired holdout delta vs the arm-D family, seven
   hard validator checks, ≤140-char note, and the fail-closed publication gate.
