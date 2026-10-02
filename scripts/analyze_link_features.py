#!/usr/bin/env python3
"""Post-hoc (exploratory) feature analysis of forward links from the confirmatory seeds.

y = mean kernel weight of a link's dots to hidden truth (1 = on truth, 0 = >= 300 m away).
Dot-level proxy ratio r = sum(n*y) / sum(n*(1-y)) is monotone in the set-level efficiency; it is used only to
choose a filter. The filter is then confirmed on fresh seeds with full marginal-gain accounting.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import paths  # noqa: E402


def table(df: pd.DataFrame, col: str, bins=None, labels=None) -> list[dict]:
    g = pd.cut(df[col], bins=bins, labels=labels, include_lowest=True) if bins is not None else df[col]
    out = []
    for k, d in df.groupby(g, observed=True):
        w = d.n_dots
        y = float((d.y * w).sum() / w.sum())
        out.append({"bin": str(k), "links": int(len(d)), "dots": int(w.sum()), "mean_y": y,
                    "ratio_y_over_1my": y / max(1 - y, 1e-9)})
    return out


def main() -> int:
    csv = Path(sys.argv[1] if len(sys.argv) > 1 else paths.EVIDENCE / "_scratch" / "topology_links_by_seed.csv")
    df = pd.read_csv(csv)
    df["size_min_km"] = np.minimum(df.size_src_km, df.size_tgt_km)
    w = df.n_dots
    base = float((df.y * w).sum() / w.sum())
    res = {"links": int(len(df)), "dots": int(w.sum()), "overall_mean_y": base,
           "overall_ratio": base / (1 - base)}
    res["gap_km"] = table(df, "gap_km", [1.0, 1.5, 2.0, 3.0, 4.01])
    res["mutual"] = table(df, "mutual")
    res["kind"] = table(df, "kind")
    res["ang_src_deg"] = table(df, "ang_src", [0, 10, 20, 30.01])
    res["size_min_km"] = table(df, "size_min_km", [0, 1, 2, 4, 1000])
    res["merged_km"] = table(df, "merged_km", [0, 4, 8, 16, 1000])
    res["strike_compat"] = table(df, "strike_compat", [-0.01, 0.2, 0.35, 0.5, 1.01])
    sp = {}
    for c in ("gap_km", "ang_src", "size_min_km", "merged_km", "strike_compat"):
        sp[c] = float(pd.Series(df[c]).corr(df.y, method="spearman"))
    res["spearman_with_y"] = sp
    out = paths.EVIDENCE / "topology_link_feature_analysis.json"
    out.write_text(json.dumps(res, indent=1))
    for k, v in res.items():
        if isinstance(v, list):
            print(k)
            for r in v:
                print(f"   {r['bin']:>16s} links={r['links']:5d} dots={r['dots']:6d} y={r['mean_y']:.3f} ratio={r['ratio_y_over_1my']:.3f}")
    print("overall", base, base / (1 - base))
    print("spearman", sp)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
