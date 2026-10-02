#!/usr/bin/env python3
"""Build the 27GEMSDOE submission files (unscored candidates) with strict validation.

Primary (slot 1, controlled A/B against the owner-reported 0.2477 file):
    dotted H19-5 (d = 1.5, regenerated and byte-identical in values to the 0.2477 file) UNION topology gap-closure dots.
Secondary (slot 2, conditional on slot 1):
    dotted H19-5 (d = 2.8, the sibling's modelled optimum, unscored) UNION the same topology dots.
Nothing here claims a leaderboard score; the agent never uploads anything.
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
from gems27 import candidates, grid, paths, submission, thinning  # noqa: E402

DATE = "20261002"
FAMILY = "gems27"


def load_mask(p):
    with rasterio.open(p) as s:
        return np.nan_to_num(s.read(1)) > 0


def emit(name_slug: str, hyp: str, summary: str, pred_bool: np.ndarray, labels, foot, out_dir: Path, extra: dict) -> dict:
    pred = pred_bool.astype(np.float32)
    assert not (pred_bool & labels).any(), "emission must not sit on catalogue pixels"
    assert not (pred_bool & ~foot).any(), "emission must not sit outside the footprint"
    cid = submission.scored_content_id(pred, foot, labels)
    files = {}
    for outside in ("nan", "allfinite"):
        fn = submission.make_filename(FAMILY, name_slug, DATE, cid, outside)
        p = submission.write_geotiff(pred, paths.TEMPLATE, out_dir / fn, outside="nan" if outside == "nan" else "zero")
        rep = submission.verify_geotiff(p, paths.TEMPLATE)
        if not rep["hard_checks_passed"]:
            raise SystemExit(f"hard validation failure for {fn}: {rep['hard_failures']}")
        files[outside] = {"file": fn, "report": rep}
    zpath = submission.zip_single(out_dir / files["nan"]["file"])
    note = submission.make_note(hyp, summary, cid)
    (out_dir / f"note-{files['nan']['file'][:-4]}.txt").write_text(note + "\n")
    checks = {"content_id": cid, "note": note, "note_chars": len(note), "variants": {k: v["report"] for k, v in files.items()},
              "zip": {"file": zpath.name, "bytes": zpath.stat().st_size, "sha256": submission.sha256_file(zpath)}, **extra}
    submission.dump_json(checks, out_dir / f"checks-{files['nan']['file'][:-4]}.json")
    return {"slug": name_slug, "hypothesis": hyp, "content_id": cid, "note": note, "nan": files["nan"]["file"],
            "allfinite": files["allfinite"]["file"], "zip": zpath.name,
            "sha256_nan": files["nan"]["report"]["sha256"], "bytes_nan": files["nan"]["report"]["bytes"],
            "emitted_px": int(pred_bool.sum()), **extra}


def main() -> int:
    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    out_dir = paths.DOCS / "downloads"
    out_dir.mkdir(parents=True, exist_ok=True)
    raw = load_mask(paths.H19_5)
    base15 = load_mask(paths.DOTTED_0_2477)
    # provenance: the 0.2477 file is exactly dot_thin(H19-5 off-catalogue, 1.5)
    regen = thinning.dot_thin(raw & ~labels, 1.5)
    prov = {"regenerated_equals_0_2477_file": bool((regen == base15).all()), "base15_px": int(base15.sum()),
            "h19_5_px": int(raw.sum())}
    assert prov["regenerated_equals_0_2477_file"], "dot_thin(1.5) no longer reproduces the 0.2477 file"
    res = candidates.build_set(labels, foot, base15, raw)
    add15 = res["dots_nonredundant"]
    A = base15 | add15
    n_links = int(len(res["links"]))
    extraA = {"base": "dotted H19-5 d1.5 (owner-reported live score 0.2477, 24GEMSDOE)", "added_px": int(add15.sum()),
              "removed_px_vs_base": int((base15 & ~A).sum()), "links": n_links, "provenance": prov}
    ma = emit("topo-gap-closure-t-v2-on-d1-5", "T-v2 A/B",
              f"0.2477 base (dotted H19-5 d1.5) + {int(add15.sum())} dots on {n_links} aligned 1-4 km gap links; A/B vs 0.2477",
              A, labels, foot, out_dir, extraA)
    # secondary: thinner base + the same links (non-redundant with respect to that base)
    base28 = thinning.dot_thin(raw & ~labels, 2.8)
    assert (base28 == load_mask(paths.DOTTED_D2_8)).all(), "dot_thin(2.8) no longer reproduces the sibling d2.8 emission"
    d28 = distance_transform_edt(~base28)
    add28 = res["dots"] & (d28 >= 3)
    B = base28 | add28
    extraB = {"base": "dotted H19-5 d2.8 (sibling-modelled optimum; never live-scored)", "added_px": int(add28.sum()),
              "base_px": int(base28.sum()), "regenerated_equals_sibling_d2_8": True, "links": n_links, "conditional_on": ma["content_id"]}
    mb = emit("topo-gap-closure-t-v2-on-d2-8", "T-v2 d2.8",
              f"d2.8-thinned H19-5 + {int(add28.sum())} dots on {n_links} aligned gap links; conditional slot 2, combination unvalidated",
              B, labels, foot, out_dir, extraB)
    # tertiary (slot 3): 0.2477 base with 100 m (1 px) catalogue-flank shadow pruned (H27-4 r<=1) + T-v2 gap-closure dots
    d_cat = distance_transform_edt(~labels)
    base15_r1 = base15 & (d_cat > 1.0)
    d_base15_r1 = distance_transform_edt(~base15_r1)
    add15_r1 = res["dots"] & (d_base15_r1 >= 3.0)
    C = base15_r1 | add15_r1
    extraC = {
        "base": "dotted H19-5 d1.5 with 100 m (1 px) catalogue-flank shadow removed (H27-4 r<=1)",
        "base_px_after_r1_prune": int(base15_r1.sum()),
        "pruned_flank_shadow_px": int((base15 & ~base15_r1).sum()),
        "added_px": int(add15_r1.sum()),
        "links": n_links,
        "conditional_on": ma["content_id"],
    }
    mc = emit(
        "topo-gap-closure-t-v2-plus-h27-4-r1-on-d1-5",
        "T-v2+H27-4",
        f"0.2477 base minus {int((base15 & ~base15_r1).sum())} 100m flank-shadow dots + {int(add15_r1.sum())} T-v2 gap dots (OOF +0.0141, 4/4 folds)",
        C,
        labels,
        foot,
        out_dir,
        extraC,
    )

    # ---- slot 4 (H27-8): every increment validated this programme, at the live-anchored budget ----
    # Session 3 added `scripts/optimize_budget.py`, a forward model that reproduces BOTH live anchors
    # exactly (H19-5 solid -> 0.1922, dotted d1.5 -> 0.2477) and whose retention assumption checks out
    # on two independent solid->dotted live pairs (-0.1 % and +4.0 %). Its optimum over the thinning
    # distance is d = 2.25-2.8 (N = 44,090, model score 0.2550 vs 0.2477). Slot 2 already sits at that
    # budget but carries only T-v2; slot 3 carries T-v2 + the H27-4 flank-shadow prune but at d1.5.
    # Nothing in the programme has stacked ALL THREE validated increments at the anchored optimum.
    base28_r1 = base28 & (d_cat > 1.0)
    d_base28_r1 = distance_transform_edt(~base28_r1)
    add28_r1 = res["dots"] & (d_base28_r1 >= 3.0)
    D = base28_r1 | add28_r1
    extraD = {
        "base": "dotted H19-5 d2.8 (live-anchored budget optimum, model 0.2550) minus the 100 m "
                "catalogue-flank shadow (H27-4 r<=1), plus T-v2 topology gap-closure dots (H27-1)",
        "base_px_before_prune": int(base28.sum()),
        "base_px_after_r1_prune": int(base28_r1.sum()),
        "pruned_flank_shadow_px": int((base28 & ~base28_r1).sum()),
        "added_px": int(add28_r1.sum()),
        "links": n_links,
        "increments_stacked": ["H27-1 T-v2 gap closure (OOF +0.0115, 4/4 folds)",
                               "H27-4 r<=1 flank-shadow prune (OOF +0.0022 solo, +0.0141 stacked, 4/4 folds)",
                               "live-anchored budget optimum d=2.25-2.8 (model 0.2550 vs 0.2477)"],
        "conditional_on": ma["content_id"],
    }
    md = emit(
        "all-increments-d2-8-h27-4-r1-t-v2",
        "H27-8 all-increments",
        f"d2.8 optimum base minus {int((base28 & ~base28_r1).sum())} flank-shadow dots + {int(add28_r1.sum())} T-v2 dots; all 3 validated increments stacked",
        D,
        labels,
        foot,
        out_dir,
        extraD,
    )
    manifest = {"generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "status": "UNSCORED candidates; no leaderboard score is claimed",
                "primary": ma, "secondary": mb, "tertiary": mc, "quaternary": md,
                "reference_0_2477": {"owner_reported_score": 0.2477, "sha256": "68d0e2e4fcc594f9a23f56c44b885fee733d026d39be55e18ad2a07289525310",
                                     "url": "https://github.com/buffedlizard55-lab/GEMSDOE24/raw/07345ea0604953d7efb858d9cfbc21e20c7aca0b/docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif",
                                     "note": "owner-reported; not an organiser receipt"}}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(json.dumps({"primary": {k: ma[k] for k in ("nan", "content_id", "emitted_px", "added_px", "removed_px_vs_base", "note")},
                      "secondary": {k: mb[k] for k in ("nan", "content_id", "emitted_px", "added_px", "note")},
                      "tertiary": {k: mc[k] for k in ("nan", "content_id", "emitted_px", "pruned_flank_shadow_px", "added_px", "note")},
                      "quaternary": {k: md[k] for k in ("nan", "content_id", "emitted_px", "pruned_flank_shadow_px", "added_px", "note")}}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
