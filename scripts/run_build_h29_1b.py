#!/usr/bin/env python3
"""E3b: H29-1b minimal-swap deconflicted emission + same-cell holdout + run card.

Frozen addendum: knowledge/16_addendum_H29-1b.md. Reuses cached Arm-B/D OOF surfaces
and the full-fit Arm-D surface; scores H29-1b emission on the seeds 210-214 cells
(disclosed reuse) vs the B cells in evidence/h29_1_holdout.json; builds the full-map
file with the shared submission writer; measures dot overlap vs BOTH screens.
ok_to_submit requires every frozen E3b gate arm. No live score is claimed.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import grid, holdout, metric, oof_detector, paths, submission  # noqa: E402

BUDGET = 38_000
MIN_DIST = 2.8
B_EXCL = 2.0
OVERLAP_CAP = 0.65
H28_1 = paths.DOCS / "downloads" / \
    "gems27-h28-1-edge-coherence-plus-t-v2-h27-4-20261002-1113fba5f6cb-nan.tif"


def capped_poisson(prob, cand, near_other, budget, cap=OVERLAP_CAP):
    """Priority Poisson-disk where at most `cap` of budget may be `near_other`."""
    ys, xs = np.nonzero(cand)
    order = np.argsort(-prob[ys, xs].astype(np.float64), kind="stable")
    H, W = cand.shape
    r = int(np.ceil(MIN_DIST))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    disc = (yy * yy + xx * xx) < (MIN_DIST * MIN_DIST)
    dys, dxs = yy[disc], xx[disc]
    blocked = np.zeros((H, W), bool)
    out = np.zeros((H, W), bool)
    kept = near_kept = 0
    max_near = int(cap * budget)
    deferred = []
    for idx in order:
        y, x = int(ys[idx]), int(xs[idx])
        if blocked[y, x]:
            continue
        if near_other[y, x] and near_kept >= max_near:
            deferred.append((y, x))
            continue
        out[y, x] = True
        kept += 1
        near_kept += int(near_other[y, x])
        ny, nx = y + dys, x + dxs
        ok = (ny >= 0) & (nx >= 0) & (ny < H) & (nx < W)
        blocked[ny[ok], nx[ok]] = True
        if kept >= budget:
            return out
    for y, x in deferred:  # only if far candidates ran out (recorded via final overlap)
        if blocked[y, x]:
            continue
        out[y, x] = True
        kept += 1
        ny, nx = y + dys, x + dxs
        ok = (ny >= 0) & (nx >= 0) & (ny < H) & (nx < W)
        blocked[ny[ok], nx[ok]] = True
        if kept >= budget:
            break
    return out


def euclid_overlap(dots, other, r=3.0):
    d = distance_transform_edt(~other)
    return float((d[dots] <= r).mean()) if dots.any() else 0.0


def emit(prob, valid, known, hidden, budget, near_other):
    d_vis = distance_transform_edt(~known)
    ridge = oof_detector.ridge_nms(prob, valid | hidden)
    cand = ridge & (valid | hidden) & ~known & (d_vis > B_EXCL)
    return capped_poisson(prob, cand, near_other, budget)


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


def main() -> int:
    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    fold = holdout.make_quadrant_folds(foot)
    hold = json.loads((paths.EVIDENCE / "h29_1_holdout.json").read_text())
    with rasterio.open(H28_1) as s:
        a = s.read(1)
    h28_dots = np.isfinite(a) & (a > 0)
    near_h28 = distance_transform_edt(~h28_dots) <= 3.0

    prob_d_oof = np.load(paths.DATA / "lane" / "oof_prob_armD.npy")
    fold_share = np.array([(fold == f).sum() for f in range(4)], float)
    fold_budget = np.round(BUDGET * fold_share / fold_share.sum()).astype(int)
    cells = []
    for seed in hold["seeds"]:
        for f in range(4):
            sp = holdout.make_split(labels, fold, f, seed=seed)
            valid = holdout.buffered_scoring_mask(sp, foot)
            dots = emit(prob_d_oof, valid, sp.known, sp.hidden,
                        int(fold_budget[f]), near_h28)
            cells.append(score_cell(dots, sp, valid))
            print(f"seed {seed} fold {f}: H29-1b={cells[-1]['dti']:.4f} "
                  f"(B={hold['per_cell']['B'][len(cells)-1]['dti']:.4f} "
                  f"D={hold['per_cell']['D'][len(cells)-1]['dti']:.4f})", flush=True)
    pooled_b = pooled_dti(hold["per_cell"]["B"])
    pooled_1b = pooled_dti(cells)
    d = np.array([c["dti"] - b["dti"] for c, b in zip(cells, hold["per_cell"]["B"])])
    bs = np.random.default_rng(11)
    means = [bs.choice(d, size=len(d), replace=True).mean() for _ in range(2000)]
    paired = {"mean_delta": float(d.mean()),
              "ci95": [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))],
              "cells_positive": int((d > 0).sum()), "n_cells": int(len(d))}
    gate_holdout = bool(pooled_1b > pooled_b and paired["cells_positive"] >= 12)
    print(f"pooled H29-1b={pooled_1b:.4f} B={pooled_b:.4f} paired={paired} "
          f"gate_holdout={gate_holdout}", flush=True)

    # ---- full-map build ----
    prob = np.load(paths.DATA / "lane" / "full_prob_armD.npy")
    d_cat = distance_transform_edt(~labels)
    ridge = oof_detector.ridge_nms(prob, foot)
    cand = ridge & foot & ~labels & (d_cat > B_EXCL)
    dots = capped_poisson(prob, cand, near_h28, BUDGET)
    assert not (dots & labels).any()
    assert (d_cat[dots] > B_EXCL).all()
    pred = dots.astype(np.float32)
    cid = submission.scored_content_id(pred, foot, labels)
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    stem = f"gems27-h29-1b-drefill-deconf-b2-38k-{date}-{cid}"

    overlaps = {}
    for rp in sorted((paths.DATA / "parallel_registry").glob("*.tif")):
        with rasterio.open(rp) as s:
            arr = s.read(1)
        overlaps[rp.name] = euclid_overlap(dots, np.isfinite(arr) & (arr > 0))
    for rp in sorted((paths.DOCS / "downloads").glob("gems27-*-nan.tif")):
        if stem in rp.name:
            continue
        with rasterio.open(rp) as s:
            arr = s.read(1)
        overlaps[rp.name] = euclid_overlap(dots, np.isfinite(arr) & (arr > 0))
    # also vs the H29-1 research file itself
    for rp in sorted((paths.DOCS / "downloads" / "research").glob("gems27-h29-1-*-nan.tif")):
        with rasterio.open(rp) as s:
            arr = s.read(1)
        overlaps[rp.name] = euclid_overlap(dots, np.isfinite(arr) & (arr > 0))
    max_overlap = max(overlaps.values()) if overlaps else 0.0
    surf = hold.get("surface_spearman_vs_registry", {})
    max_surf = max((v["D"] for v in surf.values()), default=0.0)
    unique_ok = max_overlap <= 0.70 and max_surf <= 0.90

    out_dir = paths.DOCS / "downloads" if (gate_holdout and unique_ok) else \
        paths.DOCS / "downloads" / "research"
    out_dir.mkdir(parents=True, exist_ok=True)
    zeros_tif = out_dir / f"{stem}-allfinite.tif"
    nan_tif = out_dir / f"{stem}-nan.tif"
    submission.write_geotiff(pred, paths.TEMPLATE, zeros_tif, outside="zero")
    submission.write_geotiff(pred, paths.TEMPLATE, nan_tif, outside="nan")
    zip_path = submission.zip_single(zeros_tif)
    v_zeros = submission.verify_geotiff(zeros_tif, paths.TEMPLATE)
    v_nan = submission.verify_geotiff(nan_tif, paths.TEMPLATE)
    (out_dir / f"checks-{stem}-allfinite.json").write_text(json.dumps(v_zeros, indent=2) + "\n")
    (out_dir / f"checks-{stem}-nan.json").write_text(json.dumps(v_nan, indent=2) + "\n")
    format_ok = bool(v_zeros["hard_checks_passed"])
    ok_to_submit = bool(gate_holdout and unique_ok and format_ok
                        and not hold.get("canary_leak_flags"))
    verdict = "promote" if ok_to_submit else "negative"
    note = (f"27GEMSDOE H29-1b D-refill deconf B2 38k; HOLDOUT-DTI {pooled_1b:.4f} vs B "
            f"{pooled_b:.4f}; UNSCORED | id {cid}")
    assert len(note) <= 140, len(note)
    card = {
        "run_card": "H29-1b D-refill deconflicted (parallel-run protocol §5)",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis": "Same as H29-1 (Arm-D subsurface-augmented detector at B2/38k beats "
                      "the frozen H19-5 ranking behind 0.2778), with minimal-swap "
                      "deconfliction vs this repo's unscored H28-1 file (knowledge/16).",
        "mechanism": "Full-fit HGB 32+15; ridge NMS; capped priority Poisson-disk >=2.8px "
                     "(<=65% of budget within 3px of H28-1 dots); B2; 38,000 dots.",
        "named_non_fault_mimic": "Lithologic contacts/survey seams; clay-cap conductivity; "
                                 "remanent magnetisation; fan edges/shorelines in lidar.",
        "holdout": {"label": "HOLDOUT-DTI (seeds 210-214 reused; exploratory-confirmatory)",
                    "evaluator": hold["evaluator"],
                    "pooled_dti_H29_1b": pooled_1b,
                    "pooled_dti_B_control": pooled_b,
                    "pooled_dti_H29_1_undeconflicted": hold["pooled_holdout_dti"]["D"],
                    "paired_1b_minus_B": paired,
                    "n_withheld_positives_total": hold["n_withheld_positives_total"],
                    "seeds": hold["seeds"], "canary_max_auc": hold["canary_max_auc"],
                    "gate_holdout_pass": gate_holdout,
                    "per_cell_1b": [{k: c[k] for k in ("dti", "TPw", "FPw", "FNw",
                                                       "n_truth", "n_emitted")} for c in cells]},
        "uniqueness_vs_registry": {"max_dot_overlap_within_3px_euclidean": max_overlap,
                                   "per_raster": overlaps,
                                   "max_surface_spearman_armD": max_surf,
                                   "thresholds": {"dot_overlap": 0.70, "spearman": 0.90},
                                   "pass": bool(unique_ok)},
        "raster": {"primary_allfinite": zeros_tif.name, "sha256": v_zeros["sha256"],
                   "bytes": v_zeros["bytes"], "dots": int(dots.sum()), "content_id": cid,
                   "zip": zip_path.name, "nan_twin": nan_tif.name,
                   "directory": str(out_dir.relative_to(paths.REPO))},
        "validator": {"zeros_hard_pass": format_ok, "zeros_checks": v_zeros["checks"],
                      "nan_hard_pass": bool(v_nan["hard_checks_passed"])},
        "submission_name": "GEMSDOE27-H29-1B-DREFILL-DECONF-B2-38K",
        "note_max_140_chars": note, "note_chars": len(note),
        "ok_to_submit": ok_to_submit, "verdict": verdict,
        "live_score": None,
        "live_score_label": "UNSCORED — no ORGANIZER-CONFIRMED score exists for this file",
    }
    (paths.EVIDENCE / "h29_1b_run_card.json").write_text(json.dumps(card, indent=2) + "\n")
    (out_dir / "h29_1b_candidate_manifest.json").write_text(
        json.dumps({"stem": stem, **card}, indent=2) + "\n")
    (out_dir / f"note-{stem}-allfinite.txt").write_text(note + "\n")
    print(f"dots={int(dots.sum())} cid={cid} max_overlap={max_overlap:.3f} "
          f"unique={unique_ok} format={format_ok} -> {verdict} ok={ok_to_submit}")
    print(f"wrote {zeros_tif} sha256={v_zeros['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
