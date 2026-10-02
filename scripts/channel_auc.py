#!/usr/bin/env python3
"""Univariate fault-vs-background AUC of every raster channel (calibration for a transparent 'support' score).

Catalogue pixels vs a random sample of other footprint pixels. Output: evidence/channel_auc.json.
This is an exploratory descriptor of the *catalogue*, not a detector; roads, terraces, shorelines etc. also
create scarps (see caveats in the lidar descriptor).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.stats import rankdata

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import grid, paths  # noqa: E402


def channels():
    for path, tag, u8 in ((paths.TRAINING, "train", False), (paths.LIDAR, "lidar", True),
                          (paths.EXTENSIONS, "ext", True), (paths.RAD, "rad", True)):
        with rasterio.open(path) as s:
            names = list(s.descriptions)
            for i in range(1, s.count + 1):
                nm = (names[i - 1] or f"b{i}").split(" - ")[0]
                yield tag, nm, i, path, u8


def auc(pos: np.ndarray, neg: np.ndarray) -> float:
    allv = np.concatenate([pos, neg])
    r = rankdata(allv)
    n1, n0 = len(pos), len(neg)
    return float((r[:n1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def main() -> int:
    foot = grid.load_footprint(paths.TEMPLATE)
    lab = grid.load_labels(paths.LABELS)
    rng = np.random.default_rng(7)
    idx_pos = np.flatnonzero(lab.ravel() & foot.ravel())
    idx_neg_all = np.flatnonzero(foot.ravel() & ~lab.ravel())
    idx_neg = rng.choice(idx_neg_all, size=200_000, replace=False)
    out = []
    for tag, nm, i, path, u8 in channels():
        with rasterio.open(path) as s:
            a = s.read(i).astype(np.float32).ravel()
            nd = s.nodata
        if u8:
            a[a == 0] = np.nan
        elif nd is not None:
            a[a == np.float32(nd)] = np.nan
        a[~np.isfinite(a)] = np.nan
        p, n = a[idx_pos], a[idx_neg]
        p, n = p[np.isfinite(p)], n[np.isfinite(n)]
        if len(p) < 1000 or len(n) < 1000:
            continue
        A = auc(p, n)
        out.append({"layer": f"{tag}:{nm}", "auc": A, "strength": abs(A - 0.5), "sign": 1 if A >= 0.5 else -1,
                    "n_pos": int(len(p)), "mean_neg": float(np.mean(n)), "std_neg": float(np.std(n)),
                    "mean_pos": float(np.mean(p))})
        print(f"{tag}:{nm:22s} AUC={A:.3f}", flush=True)
    out.sort(key=lambda r: -r["strength"])
    Path(paths.EVIDENCE / "channel_auc.json").write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
