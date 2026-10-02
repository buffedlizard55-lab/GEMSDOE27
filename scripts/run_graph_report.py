#!/usr/bin/env python3
"""Graph + connectivity report for the catalogue (writes evidence/graph_report.json and docs/assets figures)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import grid, paths  # noqa: E402
from gems27 import topology_theory as tt
from gems27.graph import build_graph, graph_summary  # noqa: E402


def main() -> int:
    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    fg = build_graph(labels)
    summ = graph_summary(fg)
    lens_m = fg.comp_length_px[1:] * 100.0
    from scipy import ndimage as ndi
    cm = np.array(ndi.center_of_mass(fg.skeleton, fg.comp, np.arange(1, fg.n_components + 1)))
    cxy = np.c_[cm[:, 1] * 100.0, cm[:, 0] * 100.0]   # metres, grid frame
    area_m2 = float(foot.sum()) * 1e4
    L_eq = float(np.sqrt(area_m2))
    out = {"graph": summ, "domain": {"area_km2": area_m2 / 1e6, "equivalent_square_side_km": L_eq / 1e3}}
    # exponent a vs lmin (sensitivity), D vs range (sensitivity)
    fits = {f"{lm:g}km": tt.fit_power_law_exponent(lens_m, lm * 1000.0) for lm in (1.0, 1.5, 2.0, 3.0, 4.0)}
    out["power_law_a"] = fits
    dfits = {}
    for lo, hi in ((3e3, 40e3), (5e3, 50e3), (5e3, 30e3), (8e3, 60e3)):
        d = tt.correlation_dimension(cxy, lo, hi)
        dfits[f"{lo / 1e3:g}-{hi / 1e3:g}km"] = {k: d[k] for k in ("D", "r2")}
    out["correlation_dimension_D"] = dfits
    # headline estimate: lmin = 2 km, D from 5-50 km
    lmin = 2000.0
    a_fit = fits["2km"]
    D = tt.correlation_dimension(cxy, 5e3, 50e3)
    n_ge = int((lens_m >= lmin).sum())
    res = {"lmin_m": lmin, "a": a_fit["a"], "a_se": a_fit["se"], "D": D["D"], "D_r2": D["r2"],
           "n_ge_lmin": n_ge, "D_plus_1": D["D"] + 1.0, "regime": None}
    res["regime"] = ("a < D+1: connectivity depends on the scale of measurement (large faults control it)"
                     if a_fit["a"] < D["D"] + 1 else
                     ("a ~ D+1: on the cusp, sensitive to lmin" if abs(a_fit["a"] - D["D"] - 1) < 2 * a_fit["se"]
                      else "a > D+1: scale-independent regime, controlled by density and lmin"))
    beta = tt.beta_from_counts(n_ge, a_fit["a"], lmin, L_eq, D["D"])
    res["beta"] = beta
    res["P_at_domain_equivalent_side"] = tt.percolation_parameter(L_eq, a_fit["a"], D["D"], beta, lmin)
    res["Pc_range"] = [tt.PC_LOW, tt.PC_HIGH]
    res["Lc_km"] = {f"Pc={pc}": tt.critical_length(a_fit["a"], D["D"], beta, lmin, pc) / 1e3
                    for pc in (tt.PC_LOW, tt.PC_HIGH)}
    out["berkowitz_style_estimate"] = res
    out["figure_data"] = {"lengths_km": np.sort(lens_m / 1e3)[::-1].round(3).tolist(),
                          "c2_r_m": D["r"], "c2": D["c2"]}
    # empirical single-linkage connectivity of the actual catalogue
    py, px = np.nonzero(fg.skeleton)
    lens_km = fg.comp_length_px * 0.1
    out["single_linkage"] = tt.single_linkage_curve(np.c_[py, px], fg.comp[py, px], lens_km,
                                                    [1.5, 2.0, 3.0, 5.0, 8.0, 12.0, 20.0, 30.0, 40.0, 50.0, 60.0, 80.0])
    out["paper_check"] = {"a": 2.1, "D": 1.65, "beta": 0.0085,
                          "Lc_km_lmin_to_0": tt.critical_length(2.1, 1.65, 0.0085, 1e-9) / 1e3,
                          "Lc_km_lmin_1km": tt.critical_length(2.1, 1.65, 0.0085, 1000.0) / 1e3,
                          "paper_text_km": 21}
    Path(paths.EVIDENCE / "graph_report.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: out[k] for k in ("graph", "power_law_a", "correlation_dimension_D", "berkowitz_style_estimate")},
                     indent=1, default=float)[:3500])
    print([(s["radius_km"], s["systems"], round(s["largest_km"]), round(s["largest_share"], 3)) for s in out["single_linkage"]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
