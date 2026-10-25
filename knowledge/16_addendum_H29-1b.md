# Addendum H29-1b — minimal-swap deconfliction (frozen BEFORE E3b run, 2026-10-25)

**Trigger (MEASURED, `evidence/h29_1_run_card.json`).** H29-1 passed efficacy
(pooled HOLDOUT-DTI D 0.1088 vs B 0.1002; paired +0.00857, 95 % CI [+0.00513, +0.01249],
18/20 cells, seeds 210–214; canary max AUC 0.557) and format, and passed the
protocol-literal duplicate screen vs all 12 pinned peer rasters
(`registry/parallel_submission_registry.json`: max ≤3 px dot overlap 46.2 %;
40.9 % vs the 0.2778 file g32; surface Spearman max 0.446). It **failed** the stricter
screen frozen in `knowledge/15` ("+ this repo's shipped candidates"): 85.4 % of its dots
lie within 3 px of this repo's own **unscored** H28-1 research file (59,075 px).
Per frozen gate H29-1 verdict = **negative (duplicate vs H28-1)**; bytes filed under
`docs/downloads/research/`. The frozen rule is NOT relaxed post-hoc.

**H29-1b (single change, frozen here).** Same Arm-D surface and emission, plus a
*minimal-swap* deconfliction: in descending-probability Poisson-disk order, at most
**65 %** of the 38,000-dot budget may fall within 3 px (Euclidean) of H28-1 dots;
remaining budget refills with the next-best B2 ridge candidates >3 px from H28-1.
Only ~16 % of dots move; the moved dots are the lowest-probability overlapping ones.

**Frozen E3b gate (all required for promote).** (i) Final-dot overlap ≤ 70 % vs *every*
raster in both screens (12 pinned peers + repo shipped candidates incl. H28-1) and
surface Spearman ≤ 0.90; (ii) on the same seeds 210–214 cells (disclosed reuse —
exploratory-confirmatory, not fresh): pooled HOLDOUT-DTI(H29-1b emission) > pooled
HOLDOUT-DTI(B) and ≥ 12/20 cells positive vs B; (iii) validator hard-PASS.
Leakage note: the H28-1 exclusion mask derives from a full-label file, but it only
*removes* positions correlated with truth, biasing H29-1b's holdout **downward**
(conservative). Failure on any arm ⇒ verdict negative, ⛔ DO NOT SUBMIT, stop
(experiment budget exhausted: E2, E3, E3b).
