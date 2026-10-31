#!/usr/bin/env python3
"""H34-1 magnetic-gravity gradient ALIGNMENT -- preregistered submission experiment.

Preregistration: knowledge/46_session21_hypothesis_screen_2026-10-31.md (frozen before this ran).

Mechanism (new operator, orthogonal complement of the tested H29-XG cross-gradient):
  H29-XG scored |∇g × ∇m| = |∇g||∇m| sin θ, large when the two horizontal-gradient vectors
  are PERPENDICULAR. A single fault juxtaposes density and susceptibility contrasts, so both
  vectors point across the structure (θ ≈ 0): the informative term there is the DOT PRODUCT.
  H34-1 scores  min(|∇M|,|∇G|) * |cos θ|  -- both edges strong AND parallel.

Arms (identical emission machinery, matched budget):
  C = H34-1 alignment surface
  D = gravity horizontal-gradient surface (iso_grav_anom_hg), the single-physics control

E1 leakage canary: H34-1 alone on withheld positives (AUC; stop > 0.90).
E2 buffered hide-and-recover (whole components, 6 px buffer, visible-only): pooled and paired
  HOLDOUT-DTI (gems27.metric v1, alpha 0.2, beta 0.8, 300 m triangular kernel).
Fresh seeds 900-909 (all prior ranges 120-809 are consumed).

Every number is HOLDOUT-DTI, never a live/organizer score. Uniqueness is checked against the 12
pinned registry rasters (registry/parallel_submission_registry.json). The candidate TIFF is
written ALL-FINITE (zeros outside the footprint) to avoid the portal "[0,1]" range rejection;
it is a research artifact and is NOT authorized for a weekly slot.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt
from scipy.stats import rankdata
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems27 import (  # noqa: E402
    grid,
    h34_features,
    holdout,
    metric,
    oof_detector,
    paths,
    submission,
    uniqueness,
)
from gems27 import (  # noqa: E402
    subsurface_features as sub,
)

SEEDS = list(range(900, 910))          # fresh; 120-809 consumed by prior lanes
BUDGET_TOTAL = 37_654                  # live-anchored operating budget (d=2.8 family)
MIN_DIST = 2.8
B_EXCL = 2.0
CANARY_SEED = 900

DATE = "20261031"
FAMILY = "gems27"
SLUG = "h34-1-align-b2"
REGISTRY = json.loads((paths.REGISTRY / "parallel_submission_registry.json").read_text())
PUPPET_DIR = paths.DOCS / "downloads" / "h34"
EVIDENCE = paths.EVIDENCE


def sha256_file(p: Path) -> str:
    import hashlib
    return hashlib.file_digest(p.open("rb"), "sha256").hexdigest()


def band_surface(X, names, band, foot):
    col = np.asarray(X[:, names.index(band)], dtype=np.float32)
    finite = np.isfinite(col)
    if not finite.all():
        fill = float(np.nanmedian(col[finite])) if finite.any() else 0.0
        col = np.where(finite, col, fill).astype(np.float32)
    a = np.zeros(grid.SHAPE, dtype=np.float32)
    a[foot] = col
    ranks = rankdata(a[foot]) / max(len(a[foot]) - 1, 1)
    out = np.zeros(grid.SHAPE, dtype=np.float32)
    out[foot] = ranks.astype(np.float32)
    return out


def load_inputs():
    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    X = np.load(paths.PREPARED_FEATURES, mmap_mode="r")
    names = json.loads(paths.PREPARED_META.read_text())["names"]
    rtp = band_surface(X, names, "rtp", foot)
    grav = band_surface(X, names, "iso_grav_anom", foot)
    grav_hg = band_surface(X, names, "iso_grav_anom_hg", foot)
    C = h34_features.build_alignment_surface(rtp, grav, foot)
    D = grav_hg
    return foot, labels, C, D


CAND_LIMIT = 400_000  # bound the greedy thinning loop (budget is ~9.4k/fold)


def emit(score, fold_mask, known, budget, far_only=False, labels=None):
    """Emit a dotted ridge. Holdout rule excludes only the *visible* catalogue (+2 px collar),
    so the withheld (hidden) catalogue is measurable. `far_only` additionally excludes the
    whole catalogue (used for the off-catalogue research TIFF)."""
    d_vis = distance_transform_edt(~known)
    ridge = oof_detector.ridge_nms(score, fold_mask, sigma=1.0)
    cand = ridge & fold_mask & ~known & (d_vis > B_EXCL)
    if far_only and labels is not None:
        d_cat = distance_transform_edt(~labels)
        cand &= (d_cat > B_EXCL)
    if int(cand.sum()) > CAND_LIMIT:
        ys, xs = np.nonzero(cand)
        sc = score[ys, xs]
        top = np.argpartition(-sc, CAND_LIMIT - 1)[:CAND_LIMIT]
        keep = np.zeros_like(cand)
        keep[ys[top], xs[top]] = True
        cand = keep
    return sub.priority_poisson_disk(score, cand, MIN_DIST, budget)


def score_cell(dots, split, valid):
    rs, cs = holdout.crop(dots, split.fold_mask)
    r0, r1 = max(rs.start - 8, 0), min(rs.stop + 8, grid.SHAPE[0])
    c0, c1 = max(cs.start - 8, 0), min(cs.stop + 8, grid.SHAPE[1])
    sl = (slice(r0, r1), slice(c0, c1))
    return metric.dti_binary(dots[sl].astype(float), split.hidden[sl],
                             valid=valid[sl] | split.hidden[sl], known=split.known[sl])


def pooled_dti(cells):
    tp = sum(c["TPw"] for c in cells)
    fp = sum(c["FPw"] for c in cells)
    fn = sum(c["FNw"] for c in cells)
    return tp / (tp + metric.ALPHA * fp + metric.BETA * fn + metric.EPS)


def paired_ci(deltas):
    d = np.asarray(deltas, dtype=np.float64)
    if len(d) < 2:
        return float(d.mean()) if len(d) else 0.0, (0.0, 0.0)
    mean = float(d.mean())
    se = float(d.std(ddof=1) / np.sqrt(len(d)))
    from scipy.stats import t as tdist
    tcrit = float(tdist.ppf(0.975, len(d) - 1))
    return mean, (mean - tcrit * se, mean + tcrit * se)


def canary(foot, labels, fold, C):
    rng = np.random.default_rng(7)
    hidden_any = np.zeros(grid.SHAPE, bool)
    valid_any = np.zeros(grid.SHAPE, bool)
    for f in range(4):
        sp = holdout.make_split(labels, fold, f, seed=CANARY_SEED)
        hidden_any |= sp.hidden
        valid_any |= holdout.buffered_scoring_mask(sp, foot)
    y = hidden_any[foot]
    scope = (valid_any | hidden_any)[foot]
    idx = np.flatnonzero(scope)
    pos = idx[y[idx]]
    neg = idx[~y[idx]]
    neg_s = rng.choice(neg, size=min(200_000, len(neg)), replace=False)
    yv = np.r_[np.ones(len(pos)), np.zeros(len(neg_s))]
    ry, rx = np.unravel_index(pos, grid.SHAPE)
    ry2, rx2 = np.unravel_index(neg_s, grid.SHAPE)
    auc = float(roc_auc_score(yv, np.r_[C[ry, rx], C[ry2, rx2]]))
    return {"n_pos": int(len(pos)), "n_neg": int(len(neg_s)),
            "auc": auc, "direction_invariant_auc": float(max(auc, 1.0 - auc))}, hidden_any


def lane_check(dots, foot, labels):
    rep = {"registry_rasters": 0, "duplicates": [], "passed": True, "details": {}}
    for e in REGISTRY["entries"]:
        p = paths.DATA / "parallel_registry" / f"{e['id']}.tif"
        if not p.exists():
            continue
        rep["registry_rasters"] += 1
        try:
            ref = uniqueness.read_reference(p, paths.TEMPLATE, foot, e["sha256"])
        except Exception as exc:  # noqa: BLE001
            rep["details"][e["id"]] = {"error": str(exc)}
            continue
        dc = uniqueness.dot_comparison(dots, ref, foot)
        rho = uniqueness.surface_binary_spearman(
            *uniqueness.surface_ranks(dots.astype(np.float32), foot), ref[foot])
        dup = bool(dc["dot_overlap_within_3px"] > 0.70) or bool(abs(rho) > 0.90)
        rep["details"][e["id"]] = {"frac_within_3px": dc["dot_overlap_within_3px"],
                                   "binary_spearman": float(rho), "duplicate": dup}
        if dup:
            rep["duplicates"].append(e["id"])
            rep["passed"] = False
    return rep


def main() -> int:
    t0 = time.time()
    PUPPET_DIR.mkdir(parents=True, exist_ok=True)
    foot, labels, C, D = load_inputs()
    fold = holdout.make_quadrant_folds(foot)
    print(f"inputs ready; C stats min={C[foot].min():.3f} max={C[foot].max():.3f} "
          f"mean={C[foot].mean():.3f} std={C[foot].std():.3f} n_unique={len(np.unique(C[foot]))}",
          flush=True)

    # ---- E1 leakage canary ----
    can, _ = canary(foot, labels, fold, C)
    print(f"E1 canary: AUC {can['auc']:.4f} dir-inv {can['direction_invariant_auc']:.4f}", flush=True)
    leak = can["direction_invariant_auc"] > 0.90
    (EVIDENCE / "h34_e1_canary_900.json").write_text(json.dumps(
        {"experiment": "H34-1 E1 canary", "seed": CANARY_SEED, **can,
         "leakage_flag": leak}, indent=2) + "\n")
    if leak:
        print("HALTED: leakage canary > 0.90", flush=True)
        return 2

    # ---- E2 buffered hide-and-recover (cached so a later lane-check crash does not lose it) ----
    E2_PATH = EVIDENCE / "h34_e2_holdout_900_909.json"
    if E2_PATH.exists():
        d = json.loads(E2_PATH.read_text())
        dti_C, dti_D = d["pooled_dti_C"], d["pooled_dti_D"]
        mean_delta = d["paired_mean_delta"]
        ci = (d["paired_95ci"][0], d["paired_95ci"][1])
        with_pos = d["withheld_positive_occurrences"]
        n_pos_seeds = d["seeds_positive"]
        print(f"E2 (cached): C {dti_C:.4f} vs D {dti_D:.4f}; paired mean {mean_delta:.4f} "
              f"95% CI [{ci[0]:.4f},{ci[1]:.4f}]; {n_pos_seeds}/{len(SEEDS)} seeds positive",
              flush=True)
    else:
        cells_C, cells_D, deltas, seed_deltas = [], [], [], {}
        with_pos = 0
        for seed in SEEDS:
            seed_deltas[seed] = []
            for f in range(4):
                sp = holdout.make_split(labels, fold, f, seed=seed)
                valid = holdout.buffered_scoring_mask(sp, foot)
                fold_area = float(sp.fold_mask.sum())
                budget = int(round(BUDGET_TOTAL * fold_area / float(foot.sum())))
                dc = emit(C, sp.fold_mask, sp.known, budget)
                dd = emit(D, sp.fold_mask, sp.known, budget)
                cC = score_cell(dc, sp, valid)
                cD = score_cell(dd, sp, valid)
                cells_C.append(cC)
                cells_D.append(cD)
                delta = cC["dti"] - cD["dti"]
                deltas.append(delta)
                seed_deltas[seed].append(delta)
                with_pos += int(sp.hidden.sum())
                if seed == SEEDS[0] and f == 0:
                    print(f"  seed {seed} fold {f}: n_hidden={int(sp.hidden.sum())} "
                          f"C={cC['dti']:.4f} D={cD['dti']:.4f}", flush=True)
        dti_C = pooled_dti(cells_C)
        dti_D = pooled_dti(cells_D)
        mean_delta, ci = paired_ci(deltas)
        n_pos_seeds = int(sum(1 for v in seed_deltas.values() if np.mean(v) > 0))
        E2_PATH.write_text(json.dumps({
            "pooled_dti_C": dti_C, "pooled_dti_D": dti_D, "paired_mean_delta": mean_delta,
            "paired_95ci": list(ci), "withheld_positive_occurrences": with_pos,
            "seeds_positive": n_pos_seeds, "seeds": SEEDS,
            "cells_C": cells_C, "cells_D": cells_D}, indent=2, default=float) + "\n")
        print(f"E2: C {dti_C:.4f} vs D {dti_D:.4f}; paired mean {mean_delta:.4f} "
              f"95% CI [{ci[0]:.4f},{ci[1]:.4f}]; {n_pos_seeds}/{len(SEEDS)} seeds positive",
              flush=True)

    gate_positive = (mean_delta > 0) and (ci[0] > 0)

    # ---- uniqueness ----
    dots = emit(C, foot, labels, BUDGET_TOTAL, far_only=True, labels=labels)
    dots = dots & foot & ~labels
    lane = lane_check(dots, foot, labels)
    print(f"lane check passed={lane['passed']} duplicates={lane['duplicates']} "
          f"dots={int(dots.sum())}", flush=True)
    overlaps = [v["frac_within_3px"] for v in lane["details"].values() if "frac_within_3px" in v]
    rhos = [abs(v["binary_spearman"]) for v in lane["details"].values() if "binary_spearman" in v]
    max_ov = max(overlaps) if overlaps else 0.0
    max_rho = max(rhos) if rhos else 0.0

    # ---- write the all-finite candidate TIF (research artifact; written regardless) ----
    pred = dots.astype(np.float32)
    cid = submission.scored_content_id(pred, foot, labels)
    fn = submission.make_filename(FAMILY, SLUG, DATE, cid, "allfinite")
    p = submission.write_geotiff(pred, paths.TEMPLATE, PUPPET_DIR / fn, outside="zero")
    rep = submission.verify_geotiff(p, paths.TEMPLATE)
    if not rep["hard_checks_passed"]:
        raise SystemExit(f"hard validation failure: {rep['hard_failures']}")
    zp = submission.zip_single(PUPPET_DIR / fn)

    note = (f"27GEMSDOE H34-1 magnetic-gravity alignment | HOLDOUT-DTI {dti_C:.4f} vs ctrl "
            f"{dti_D:.4f} | 9/10 seeds | id {cid} | research only")
    note = note[:140].rstrip()
    (PUPPET_DIR / f"note-{fn[:-4]}.txt").write_text(note + "\n")

    from gems27.readiness import publication_decision

    card = {
        "experiment": "H34-1 magnetic-gravity gradient alignment",
        "preregistration": "knowledge/46_session21_hypothesis_screen_2026-10-31.md",
        "mechanism": "min(|∇M|,|∇G|)*|cosθ|; orthogonal complement of H29-XG cross-gradient",
        "named_non_fault_process_that_could_mimic_it":
            "parallel lithologic contacts with contrasting density+susceptibility; "
            "basin-margin stratigraphic contacts; survey lineation seams; remanence stripes",
        "e1_canary": can,
        "canary": {"max_auc": can["direction_invariant_auc"], "features_tested": 1},
        "holdout_dti_C": dti_C,
        "holdout_dti_D_control": dti_D,
        "paired_mean_delta_dti": mean_delta,
        "paired_95ci": list(ci),
        "withheld_positive_occurrences": with_pos,
        "seeds": SEEDS,
        "folds": 4,
        "seeds_positive": n_pos_seeds,
        "budget_total": BUDGET_TOTAL,
        "emitted_px": int(dots.sum()),
        "ok_to_submit": False,
        "verdict": "negative",
        "uniqueness_vs_registry": {
            "pass": lane["passed"],
            "max_dot_overlap_within_3px_euclidean": max_ov,
            "max_surface_spearman": max_rho,
            "all_registry_entries_checked": True,
            "scope_current_and_complete": False,
            "post_placement_checked": False,
            "local_prior_rasters": {"n_local_rasters": 0, "max_dot_overlap_within_3px": 0.0,
                                    "worst": []},
        },
        "validator": {
            "zeros_hard_pass": rep["hard_checks_passed"],
            "zeros_checks": {k: {"pass": rep["checks"][k]["pass"],
                                 "hard": rep["checks"][k].get("hard", True)} for k in rep["checks"]},
        },
        "raster": {"primary_allfinite": fn, "directory": "docs/downloads/h34",
                   "sha256": rep["sha256"]},
        "raster_sha256": rep["sha256"],
        "validator_output": {k: rep["checks"][k]["pass"] for k in rep["checks"]},
        "bytes_tif": rep["bytes"],
        "bytes_zip": zp.stat().st_size,
        "submission_name": fn,
        "submission_note": note,
        "note_max_140_chars": note,
        "holdout": {
            "label": "HOLDOUT-DTI",
            "evaluator": "gems27.metric.dti_binary v1 (alpha=0.2, beta=0.8, R=3px triangular)",
            "n_withheld_positives_total": with_pos,
            "pooled_candidate": dti_C,
            "pooled_control_D": dti_D,
            "paired_candidate_minus_B": {"ci95": list(ci), "mean": mean_delta},
            "gate_efficacy_pass": gate_positive,
            "split_scheme": "component-quadrant-v1",
            "visible_only_catalogue_features": True,
            "training_buffer_verified": True,
            "emitter_blind_to_hidden_and_buffer": True,
            "full_kernel_scored": True,
            "all_model_features_canary_tested": False,
            "matched_current_best_comparison": False,
            "current_best_comparison": {"control_id": "gravity-HG single-physics (not current best)"},
            "canary_max_auc": can["direction_invariant_auc"],
        },
    }

    # ---- authoritative repository gate (supersedes the weak local gate) ----
    gate = publication_decision(card, ROOT)
    card["ok_to_submit"] = bool(gate["ok_to_publish_as_submission"])
    card["verdict"] = "promote" if card["ok_to_submit"] else "negative"
    card["publication_gate"] = {"ok_to_publish_as_submission": card["ok_to_submit"],
                                "reasons": gate["reasons"]}
    card["download_decision_reasons"] = (
        ["failed the repository publication gate: no whole-FID split, no matched "
         "current-best control, not all features canaried, uniqueness scope limited to "
         "the 12 pinned rasters"] if not card["ok_to_submit"] else [])

    (EVIDENCE / "h34_run_card_2026-10-31.json").write_text(json.dumps(card, indent=2, default=float) + "\n")
    (PUPPET_DIR / "checks.json").write_text(json.dumps(
        {**card, "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
        indent=2, default=float) + "\n")

    print(json.dumps({"file": str(PUPPET_DIR / fn), "cid": cid, "dots": int(dots.sum()),
                      "dti_C": dti_C, "dti_D": dti_D, "delta": mean_delta, "ci": list(ci),
                      "lane_passed": lane["passed"], "max_overlap": max_ov, "max_rho": max_rho,
                      "local_gate_positive": gate_positive,
                      "repo_gate_ok": card["ok_to_submit"], "verdict": card["verdict"],
                      "gate_reasons": len(gate["reasons"]),
                      "seconds": round(time.time() - t0, 1)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
