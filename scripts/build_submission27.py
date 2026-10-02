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
    d28 = distance_transform_edt(~base28)
    add28 = res["dots"] & (d28 >= 3)
    B = base28 | add28
    extraB = {"base": "dotted H19-5 d2.8 (sibling-modelled optimum; never live-scored)", "added_px": int(add28.sum()),
              "base_px": int(base28.sum()), "links": n_links, "conditional_on": ma["content_id"]}
    mb = emit("topo-gap-closure-t-v2-on-d2-8", "T-v2 d2.8",
              f"d2.8-thinned H19-5 + {int(add28.sum())} dots on {n_links} aligned gap links; conditional slot 2, combination unvalidated",
              B, labels, foot, out_dir, extraB)
    manifest = {"generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "status": "UNSCORED candidates; no leaderboard score is claimed",
                "primary": ma, "secondary": mb,
                "reference_0_2477": {"owner_reported_score": 0.2477, "sha256": "68d0e2e4fcc594f9a23f56c44b885fee733d026d39be55e18ad2a07289525310",
                                     "url": "https://github.com/buffedlizard55-lab/GEMSDOE24/raw/07345ea0604953d7efb858d9cfbc21e20c7aca0b/docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif",
                                     "note": "owner-reported; not an organiser receipt"}}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(json.dumps({"primary": {k: ma[k] for k in ("nan", "content_id", "emitted_px", "added_px", "removed_px_vs_base", "note")},
                      "secondary": {k: mb[k] for k in ("nan", "content_id", "emitted_px", "added_px", "note")}}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
