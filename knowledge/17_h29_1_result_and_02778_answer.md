# Session 7 (2026-10-25): why 0.2778 won, whether it can be beaten, H29-1 result

**Labelling.** Leaderboard numbers are **OWNER-REPORTED** (prompt / owner sites); no
ORGANIZER-CONFIRMED receipt exists in this repo. Detector numbers are **HOLDOUT-DTI**
(evaluator `gems27.metric` v1, α 0.2 β 0.8, 300 m kernel). Raster facts are **MEASURED**.
Live-gain expectations are **MODEL** (priors), never scores.

## 1. Why h33-h33-2-b2 (0.2778, GEMSDOE32) is the family best — PhD-level answer

Reconstruction is pixel-exact (`knowledge/12`, re-verified this session: fetched
`g32_h33_2_b2.tif` sha256 `c55bafc47005…` via the pinned registry):

`H19-5 solid (0.1922) → dot_thin 1.5 (0.2477) → dot_thin 2.8 (0.2600) → delete dots ≤1 px
from catalogue (0.2708) → delete dots ≤2 px (0.2778)`. The last step deletes just
2,545 dots (6.3 %). Three mechanisms, in order of importance:

1. **DTI arithmetic.** DTI = TP/(0.2·TP + 0.2·FP + 0.8·|G|). Near DTI 0.25–0.28 a dot set
   pays for itself only if dTP/dFP > 0.052–0.059. Dots 100–200 m from a *known* fault are
   detector echo of that fault (scarp response rasterised 1–2 px off-trace + dip offset);
   hidden truth excludes the catalogue by construction, so their credit efficiency is
   ≈ 0 while each costs 0.2 FP mass. Deleting them is almost pure denominator reduction.
2. **Dotted geometry.** Under the 300 m triangular kernel a dot every ~2.8 px keeps ≈78 %
   of on-line credit for ~1/3 the mass of a solid line; credit/dot saturates at 3.0 while
   cost/dot stays 1. Thinning moved the family onto the flat FP optimum (~38–44 k px).
3. **Convergent optimum.** GEMSDOE36's unrelated physics file (0.2750, 38,854 dots, also
   0 within 2 px — re-read here) lands on the same B2 + ~38 k point. The optimum is
   emission-side and detector-independent; the top files differ only in *ranking*.

Corollary (MEASURED): all top files are one dot field re-thinned (91–100 % within 3 px of
each other); family credit concentration plateaus at 5.3–5.7× blind. **Further thinning
cannot reach 0.32+; only better ranking (new detector information) can.**

## 2. Focus-site league table (OWNER-REPORTED; from the prompt, cross-checked vs registry)

GEMSDOE32 0.2778 · GEMSDOE36 0.2750 · GEMSDOE28 0.2710/0.2708/0.2707/0.2649 ·
GEMSDOE31 0.2708 · GEMSDOE33 0.2632 · GEMSDOE25 0.2600 · GEMSDOE30 0.2600 ·
GEMSDOE24 0.2477 · GEMSDOE27 0.2449. Every entry ≥0.26 is an H19-5-descendant emission
variant (B1/B2 prune ± tip protection). Prompt's leaderboard highs 0.4413 and 0.3195
conflict (IR-2026-10-25-02, unresolved; agent does not access drivendata.org).

## 3. Can 0.2778 be beaten? Judgement + this session's measurement

- By more emission surgery on H19-5 dots: MODEL +0.003–0.010 plausible (B3/refill), but
  **forbidden as a "unique" lane** (>70 % ≤3 px overlap = duplicate) and capped ≈0.29.
- By new detector information at B2/38 k: the only route to 0.30+. This session tested the
  cheapest such increment — **H29-1 D-refill** (32-band stack + 15 subsurface transforms;
  preregistered `knowledge/15`, hypotheses ranked there incl. dip-shift H29-2, soft
  emission H29-3, H28-4, H27-16-blocked-on-bytes).
- **Result (HOLDOUT-DTI, fresh seeds 210–214, 20 cells, 59,362 withheld positives):**
  pooled D **0.1088** vs B **0.1002**; paired **+0.00857 [+0.00513, +0.01249]**, 18/20
  cells — *stronger* than the discovery estimate (+0.0045). Canary max AUC 0.557 (clean).
  Evidence: `evidence/h29_1_holdout.json`.
- **Uniqueness (MEASURED):** surface Spearman ≤ 0.446 (limit 0.90); ≤3 px dot overlap
  ≤ 46.2 % vs *every* pinned scored peer (40.9 % vs 0.2778; exact shared px 1,649/38,000,
  Jaccard 0.022) — **protocol-literal PASS**. But 85.4 % vs this repo's own unscored
  H28-1 research file (59,075 px; Jaccard 0.116) — **FAIL** under the extended screen
  frozen in `knowledge/15`. Deconflicted variant H29-1b (`knowledge/16`) proved
  geometrically infeasible: H28-1 dots + 3 px halos blanket the D-ridge candidate pool
  (final overlap 82.6 %). **Verdict: negative (not certified unique).** Bytes:
  `docs/downloads/research/gems27-h29-1-drefill-b2-38k-20261025-c24b6371179c-allfinite.tif`
  (sha256 `40dc48a9…`, 38,000 dots, validator hard-PASS: all-finite [0,1], EPSG:32611
  3730×3292). Run cards: `evidence/h29_1_run_card.json`, `evidence/h29_1b_run_card.json`.
- **Updated probability (MODEL/prior):** P(H29-1 bytes beat 0.2778 live) ≈ 0.4–0.55
  (holdout Δ is real but catalogue-internal; live transfer discount unknown, `knowledge/10`).
  Expected margin if it wins: +0.003–0.015. It does not reach 0.32–0.44; that needs a
  step-change detector (supervised 1 m-DEM segmentation on the full GeoDAWN stack).

## 4. What would maximise P(Win) next (selector owns slot decisions)

1. **Selector adjudication** of the extended-screen question (IR-2026-10-25-06): H29-1 is
   unique vs every *scored* file and format-valid; if the owner records that the H28-1
   screen arm is waived (H28-1 was never submitted), H29-1 becomes the rational next slot.
   Until recorded, the site badges it ⛔ NOT CERTIFIED UNIQUE.
2. H29-2 dip-shift correction (data already pinned) — new geometry, decorrelates by
   mechanism. 3. H29-3 soft-probability emission — never tried by the family.
4. GDR #1391 official bytes for H27-16/H28-5 (still unobtained in-sandbox).
5. The big lever remains a 1 m-DEM supervised segmenter (GPU; outside this sandbox).

## 5. Irregularities flagged this session

- **IR-2026-10-25-05:** deployed `docs/index.html` had been hand-edited (unique-scatter
  hero, "ready to submit") out of sync with `scripts/build_site.py` (STOP policy) and
  with README. Fixed: site regenerated from JSON only; hero removed.
- **IR-2026-10-25-06:** uniqueness-rule tension — any accurate 38 k emission dots the
  same ridges as the dense unscored H28-1 file, so ≤3 px overlap >70 % is near-unavoidable
  without destroying score; the pinned-peer screen (scored files) passes at ≤46.2 %.
  Selector must adjudicate which screen governs slot eligibility. Not waived here.
- Leaderboard-high conflict (0.4413 vs 0.3195) remains IR-2026-10-25-02.

Official sources for manual review: competition
https://www.drivendata.org/competitions/306/competition-doe-gems/ · problem
https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ · about
https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/ · leaderboard
https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/ ·
reference solution https://github.com/drivendataorg/gems-prize-reference-solution ·
rules https://docs.nlr.gov/docs/fy26osti/96647.pdf · GeoDAWN
https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and ·
INGENIOUS https://gbcge.org/current-projects/ingenious/ · GDR
https://gdr.openei.org/submissions/1391 · EPSG:32611 https://epsg.io/32611 ·
Tversky https://en.wikipedia.org/wiki/Tversky_index
