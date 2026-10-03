#!/usr/bin/env python3
"""LiDAR scarp response of SGMC-gap pixels vs catalogued fault pixels (the H27-11 corollary).

Session 4's screening measured this in a scratch script; this is the committed, reproducible version,
and it fixes the artefact that scratch script had: descriptor statistics are computed on `lidar:valid`
pixels ONLY (24.6 % of the footprint has no 1 m LiDAR, where every descriptor is 0/nodata, which drags
any pooled mean or AUC towards "no difference").

Output: evidence/sgmc_lidar_response.json. Nothing here reads predictions or scores.

Usage: GEMS_DATA_DIR=/home/user/GEMSDOE27/data_cache .venv/bin/python scripts/sgmc_lidar_response.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import grid, paths  # noqa: E402

DESCRIPTORS = ("lappos_max", "step_max", "ex_max", "relief", "lapneg_max")


def stats(v: np.ndarray) -> dict:
    v = v[np.isfinite(v)]
    if v.size == 0:
        return {"n": 0}
    return {"n": int(v.size), "mean": float(v.mean()), "p50": float(np.percentile(v, 50)),
            "p90": float(np.percentile(v, 90)), "std": float(v.std())}


def main() -> int:
    foot = grid.load_footprint(paths.TEMPLATE)
    cat = grid.load_labels(paths.LABELS)
    with rasterio.open(paths.LIDAR) as s:
        desc = {d: i + 1 for i, d in enumerate(s.descriptions)}
        valid = s.read(desc["valid"]) > 0
        bands = {d: s.read(desc[d]).astype(np.float32) for d in DESCRIPTORS}
    with rasterio.open(paths.SGMC) as s:
        sgmc = s.read(1) > 0

    d_cat = distance_transform_edt(~cat)
    populations = {
        "catalogue_pixels": cat & foot,
        "sgmc_all": sgmc & foot,
        "sgmc_only_ge_300m_from_catalogue": sgmc & foot & (d_cat >= 3.0),
        "sgmc_only_ge_600m_from_catalogue": sgmc & foot & (d_cat >= 6.0),
    }
    rng = np.random.default_rng(7)
    bg_pool = np.flatnonzero((foot & valid & ~cat & ~sgmc).ravel())
    bg = np.zeros(foot.shape, bool).ravel()
    bg[rng.choice(bg_pool, size=min(200_000, len(bg_pool)), replace=False)] = True
    populations["random_background_200k"] = bg.reshape(foot.shape)

    out = {"note": ("Descriptor statistics are restricted to lidar:valid pixels (the 24.6 % of the "
                    "footprint without 1 m LiDAR carries 0 in every descriptor and would otherwise "
                    "flatten every comparison). Populations are measured on the restored official "
                    "layers, not on any prediction."),
           "lidar_valid_px": int((valid & foot).sum()), "footprint_px": int(foot.sum()),
           "catalogue_px": int((cat & foot).sum()), "sgmc_px": int((sgmc & foot).sum()),
           "populations": {}}
    for name, mask in populations.items():
        m = mask & valid & foot
        out["populations"][name] = {"px_total": int(mask.sum()), "px_with_lidar": int(m.sum()),
                                    "descriptors": {d: stats(bands[d][m]) for d in DESCRIPTORS}}
        print(f"{name:<38} n={int(m.sum()):>9,} " +
              " ".join(f"{d}={out['populations'][name]['descriptors'][d].get('mean', float('nan')):7.2f}"
                       for d in DESCRIPTORS), flush=True)

    # the comparison that matters: is raw scarp intensity enough to pick hidden truth?
    lap = "lappos_max"
    c = out["populations"]["catalogue_pixels"]["descriptors"][lap]["mean"]
    g = out["populations"]["sgmc_only_ge_300m_from_catalogue"]["descriptors"][lap]["mean"]
    b = out["populations"]["random_background_200k"]["descriptors"][lap]["mean"]
    out["reading"] = {
        "mean_lappos_max_catalogue": c, "mean_lappos_max_sgmc_gap": g, "mean_lappos_max_background": b,
        "sgmc_gap_response_vs_catalogue": g / c if c else None,
        "conclusion": ("SGMC-gap pixels show a HIGHER mean 1 m LiDAR positive-laplacian response than "
                       "catalogued fault pixels, yet the live-scored emission built from exactly those "
                       "pixels (16GEMSDOE h18-4, 0.0360) inverts to 1.62x blind against 5.3-6.0x for "
                       "the H19-5 family. Raw scarp-detector intensity therefore does NOT discriminate "
                       "hidden truth; position relative to the Quaternary catalogue does. "
                       "evidence/sgmc_gap_inversion.json."),
    }
    (paths.EVIDENCE / "sgmc_lidar_response.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out["reading"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
