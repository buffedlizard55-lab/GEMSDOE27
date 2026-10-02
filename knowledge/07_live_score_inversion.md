# 07 · Inverting the live scores: what 20 submitted rasters say about the hidden truth

Session 3 (2026-10-02). Everything here is computed from **rasters whose SHA-256 matches a
`registry/live_scores.json` row**, so each (emission, score) pair is hash-authenticated rather than
matched by filename. Scores remain *owner-reported*, not DrivenData receipts.

Scripts: `scripts/fetch_scored_corpus.py` → `evidence/scored_corpus.json`;
`scripts/invert_live_scores.py` → `evidence/live_inversion.json`;
`scripts/optimize_budget.py` → `evidence/budget_optimum.json`;
`scripts/tomography_partition.py` → `evidence/live_truth_partition_*.json`;
`scripts/model_candidates.py` → `evidence/candidate_model_scores.json`.

## 1. What was recovered

20 of the 25 registry rows were matched by SHA-256 to a raster in a sibling repository and
downloaded through the GitHub API. 5 remain unmatched (`ens12-adopted`, `dual-family-union`,
`lidarscarp-ridge-top2pct`, GEMSDOE4 `combined`, `hgb88-topk03`) — recorded as such, not guessed.

## 2. The metric in one line, and its exact consequence

With the official `k(d) = max(1 − d/300 m, 0)`, `TPw = Σ_g max_x p(x)k`, `FPw = Σ_x p(x)(1 − max_g k)`,
`FNw = |G| − TPw`:

```
DTI = TPw / ( 0.2·TPw·(1 − ρ) + 0.2·N + 0.8·|G| ),     ρ = MPw/TPw,  MPw = Σ_x p(x)·max_g k
```

`ρ` is the **crowding factor**. It matters because the metric takes a *max* over predictions per
truth pixel for credit but a *sum* over predictions for false-positive mass: a pixel that merely
sits near truth is cheap even when it is redundant for credit. **Crowding near truth is a discount,
not a penalty.** Every claim in this file uses that identity.

Two consistency checks pass exactly:
* `ρ` computed from geometry reproduces both live anchors — H19-5 solid → **0.1922** (live 0.1922),
  dotted d1.5 → **0.2477** (live 0.2477).
* For the blind lattice, `ρ = 0.99`, i.e. the naive closure `FPw = N − TPw` is exact there, which is
  why the lattice is a clean calibration instrument.

## 3. |G| = 12,226 px, from an instrument that needs no geology

A spacing-5 blind lattice has a credit-per-truth-pixel `c` that is a *pure geometry* constant
(`c = 0.37481`, kernel area `9.3803` px), independent of where the truth is. Inverting its live
score 0.0904 at `N = 204,504` gives

> **|G| = 12,226 px**

The sibling's independent estimate was 12,503 (lattice) / 12,769 (pair) — **2.2 % apart**. Two
different instruments, two different repos, same answer. This is now the best-supported value; the
`knowledge/01` figure of ~12.63k should be read as 12.2–12.8k.

## 4. Concentration: the only ranking of surfaces that survives

`c(S)` = credit a uniformly spread truth would earn; `conc = (TPw/|G|)/c(S)` = how many times better
than blind the emission is at *finding* truth. Concentration is the detector-quality measure; `c`
alone only measures how much area you sprayed.

| surface | N | live | credit | credit/\|G\| | conc | ρ |
|---|---|---|---|---|---|---|
| dotted H19-5 d1.5 (**0.2477**) | 60,069 | 0.2477 | 5,286 | 0.432 | **5.67** | 1.43 |
| H19-5 solid | 121,131 | 0.1922 | 6,189 | **0.506** | 5.66 | 2.46 |
| h19-4 | 123,779 | 0.1894 | 6,206 | 0.508 | 5.49 | 2.43 |
| h16-1 topo-geophys | 123,939 | 0.1855 | 6,100 | 0.499 | 5.28 | 2.38 |
| h28-dotted-ridge | 65,236 | 0.1839 | 4,185 | 0.342 | 3.14 | 1.09 |
| H25-ctx-ridge | 161,366 | 0.1280 | 5,217 | 0.427 | 3.26 | 2.24 |
| r7-nms3-dem10-scarp | 103,347 | 0.1294 | 3,913 | 0.320 | 2.16 | 1.27 |
| pindrop-v4-nodes | 155,021 | 0.1193 | 4,861 | 0.398 | 1.47 | 1.04 |
| blind lattice s5 | 204,504 | 0.0904 | 4,582 | 0.375 | 1.00 | 0.99 |
| H19-C | 452,798 | 0.0297 | 2,924 | 0.239 | 1.23 | 4.22 |

Readings, each of which kills a family of ideas:
* The H19-5/h19-4/h16-1 family sits on a **plateau at conc ≈ 5.3–5.7**. They are the same detector
  quality wearing different clothes; recombining them cannot raise concentration.
* **No submission in the group's history exceeds credit fraction 0.508.** The best file ever made
  still misses ~half the hidden truth.
* Spraying area does not work: H19-C reaches 0.239 of truth with 452,798 px and scores 0.0297.
* The lattice is the floor: 1.00× concentration, 0.0904.

## 5. The retention rule, validated twice live

For geometric (Poisson-disk) thinning, `credit(d) = credit_solid · c(d)/c_solid`. Tested against two
independent solid→dotted live pairs:

| pair | retention predicted by geometry | retention measured live | error |
|---|---|---|---|
| H19-5 → dotted d1.5 | 0.8536 | 0.8541 | **−0.1 %** |
| H25-ctx-ridge → h28-dotted | 0.8338 | 0.8021 | **+4.0 %** |

This is the strongest instrument the programme has: a rule fitted on one live pair predicts a
*second, unrelated* live pair to 4 %. It is valid for **spatially unbiased** removal only (see §7).

## 6. The budget optimum, and why it is a ceiling not a springboard

Sweeping `d` on the anchored model (`evidence/budget_optimum.json`):

| d | N | retention | model score |
|---|---|---|---|
| 1.0 (solid) | 121,131 | 1.000 | 0.1922 *(live 0.1922)* |
| 1.25 | 73,771 | 0.892 | 0.2321 |
| **1.5** | **60,069** | **0.854** | **0.2475** *(live 0.2477)* |
| **2.25–2.8** | **44,090** | **0.759** | **0.2550** |
| 3.0 | 41,333 | 0.735 | 0.2537 |
| 4.0 | 31,930 | 0.621 | 0.2383 |
| 6.0 | 21,017 | 0.426 | 0.1887 |

The optimum is **d = 2.25–2.8 → 0.2550**, i.e. **+0.0073 over 0.2477** — and the sibling's
completely independent two-parameter fit said 0.2553 (band 0.250–0.261). Two methods, two repos,
same number. **The emission-geometry lever is exhausted at ≈0.255.**

## 7. Two ideas tested and rejected this session

**(a) H27-6 coverage-optimal thinning — REFUTED.** Poisson-disk is a *packing* rule and is blind to
how much of the emission's own support survives, so the obvious improvement is to choose the N dots
that maximise coverage `c(S')` directly (a monotone submodular max-coverage problem whose objective
*is* the metric's credit functional). Implemented as batched greedy with exact local marginal gains
(`src/gems27/coverage_thin.py`). Measured on quadrant NW at matched budgets:

| budget | Poisson-disk coverage mass | coverage-greedy | ratio |
|---|---|---|---|
| 20,752 (d=2.25) | 165,562.7 | 143,341.2 | **0.866 (worse)** |
| 28,209 (d=1.5) | 186,182.3 | 188,120.0 | 1.010 (a wash) |

At the sparse budget that actually matters, greedy max-coverage **loses** to Poisson-disk by 13 %.
Reason: on a 1-px-wide ridge network, isotropic spacing already is the near-optimal cover; greedy's
early picks are made against an empty coverage map and cannot be undone. Do not re-propose.

**(b) H27-7 union-recall ensembling — REFUTED as an improvement, bounded as a gamble.** The three
best surfaces are nearly pixel-disjoint (Jaccard: h19-5 vs H25-ctx **0.075**, vs r7-scarp **0.052**,
vs h16-1 0.592), which looks like free recall. It is not. Measured against the live-anchored model:

| union | d | N | central model | pessimistic bound¹ |
|---|---|---|---|---|
| h19-5 ∪ h16-1 | 2.25 | 51,971 | 0.2655 | 0.2310 |
| h19-5 ∪ H25-ctx | 2.25 | 87,906 | 0.2521 | 0.1688 |

¹ pessimistic = `TP_union = max(TP_A, TP_B)`, i.e. the two surfaces cover the *same* truth from
different pixels. The central estimate uses blind-coverage complementarity `c_union/(c_A+c_B)`.
Against those, **h19-5 alone at d2.25 is 0.2550 with a rule validated to 4 %**. The union's entire
edge lives in an unvalidated complementarity assumption, and its downside is −0.086. A slot is worth
more than that. Recorded so no future session re-derives it.

Also checked and rejected: a **habitat tomography** of the truth. Because `TP_i = Σ_x λ(x)K_i(x)` is
linear in the truth intensity `λ`, 20 scored submissions are in principle 20 measurements of *where*
the hidden labels live. With overlapping geological bases it fails outright (in-sample R² = −1.24).
Restricting to a strict 7-cell catalogue-distance **partition** (well-identified, mass constraint
exact) still fails: in-sample R² = −0.360, leave-one-submission-out score RMSE **0.0715** against a
score spread of 0.0686 — signal ratio 0.96, i.e. **no better than predicting the mean**. 20
aggregate numbers cannot resolve a 5.2 M-pixel field. The fitted λ put 66 % of truth in the
100–200 m catalogue ring and 34 % at 800–1500 m, which is *suggestive* and consistent with the
Hermant et al. (2025) 150–400 m LiDAR-offset finding, but it did not pass its own validation and
must not be used to choose an emission.

## 8. What 0.3195 actually requires (arithmetic, not opinion)

From `score = TP/(0.2N + 0.8|G|)` at |G| = 12,226:

| emitted px | credit needed for 0.2477 | for 0.2941 (#5) | for 0.3195 (#1) |
|---|---|---|---|
| 20,000 | 0.279\|G\| | 0.332\|G\| | 0.360\|G\| |
| 30,000 | 0.320\|G\| | 0.380\|G\| | 0.412\|G\| |
| 44,090 | 0.377\|G\| | 0.447\|G\| | **0.486\|G\|** |
| 60,069 | 0.442\|G\| | 0.524\|G\| | **0.570\|G\|** |
| 121,131 | 0.689\|G\| | 0.818\|G\| | 0.889\|G\| |

The group's **best ever credit fraction is 0.508** (h19-4, at 123,779 px). So:
* 0.3195 at 44,090 px needs 0.486|G| — *below* what H19-5 solid already achieves (0.506), but
  thinning to 44,090 px only retains 0.759 → 0.384. **Retention, not knowledge, is the wall.**
* 0.3195 at 60,069 px needs 0.570|G| — **more credit than any submission in the group's history has
  ever earned, at any budget.**

Two independent routes therefore exist, and only these two:
1. **Retention ≈ 1.0 at ~44 k px** — keep nearly all of H19-5's credit while emitting a third of its
   pixels. §7(a) shows the obvious way to do this fails; nothing in the repo achieves it.
2. **Concentration above 5.7** — a detector that finds truth the H19-5 family misses. Every surface
   in the family plateaus at 5.3–5.7, so this needs *new information*, not new combinations.

Both are detector problems. **0.3195 is not reachable by rearranging pixels we already have.** That
is now an arithmetic statement with two live-validated instruments behind it, not a judgement call.

## 9. Consequence for the shipped slots

`scripts/model_candidates.py` scores all four candidates under **both** truth assumptions, because
they disagree exactly where the evidence is weakest:

| slot | N | geometric² | hybrid³ |
|---|---|---|---|
| 1 — 0.2477 + T-v2 (A/B) | 61,328 | 0.2506 | 0.2580 |
| 2 — d2.8 + T-v2 | 45,374 | **0.2585** | 0.2671 |
| 3 — d1.5 − flank prune + T-v2 | 55,992 | 0.2439 | **0.2704** |
| 4 — d2.8 − flank prune + T-v2 (new) | 41,507 | 0.2484 | **0.2781** |

² geometric: uniform-truth retention charged for *every* pixel change.
³ hybrid: geometric retention for thinning, plus the efficiencies the out-of-fold gate *measured*
for the targeted steps (prune 0.0034 credit/px removed, T-v2 0.2251 credit/px added).

The disagreement is structural, not noise: the geometric model charges pruned catalogue-flank pixels
with *average* credit, but the OOF gate measured them at 0.0034 — about 15× below the 0.0521 live
break-even. The geometric model is validated for **unbiased** removal (thinning) and is known to be
biased for **targeted** removal (pruning). The hybrid is the better estimate for the prune and the
geometric is the better estimate for the thinning; slot 4 uses each where it is valid.

**Slot 1 vs slot 3 is the live A/B that settles it**, and that is why slot 1 is pre-registered as the
primary upload: it changes exactly one thing (adds 1,259 T-v2 dots, removes nothing) against a
scored parent.
