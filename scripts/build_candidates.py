#!/usr/bin/env python3
"""Build the topology candidate set from the full catalogue and write dossiers + GIS files."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import candidates, grid, paths, vector_graph  # noqa: E402


def load_mask(p):
    with rasterio.open(p) as s:
        return np.nan_to_num(s.read(1)) > 0


def argument(r, gb) -> str:
    kind = {"end-to-end": "tip-to-tip along strike", "tip-to-tip oblique": "oblique tip-to-tip (step-over-like)",
            "abutting": "tip abutting a through-going trace"}[r.kind]
    tgt = "" if not np.isfinite(r.ang_tgt) else f" and {r.ang_tgt:.0f} deg"
    mut = "mutual nearest tips" if r.mutual else "one-sided"
    ns = r.name_src or "unnamed trace"
    nt = r.name_tgt or "unnamed trace"
    if r.same_fid:
        vec_desc = (
            f"NBMG INGENIOUS vector attribution: intra-FID raster/discretisation gap within multipart polyline "
            f"FID={r.fid_src} ('{ns}', NUM={r.num_src or 'n/a'}, {r.ftype_src or 'untyped'}, "
            f"SLIPSENSE={r.slipsense_src or 'unspec'}, DIPDIRECT={r.dipdirect_src or 'unspec'})."
        )
    elif r.same_name:
        vec_desc = (
            f"NBMG INGENIOUS vector attribution: inter-FID structural linkage within fault zone '{ns}' "
            f"(NUM={r.num_src or 'n/a'}), bridging FID={r.fid_src} ({r.ftype_src or 'untyped'}, "
            f"SLIPSENSE={r.slipsense_src or 'unspec'}, DIPDIRECT={r.dipdirect_src or 'unspec'}) to "
            f"FID={r.fid_tgt} ({r.ftype_tgt or 'untyped'}, SLIPSENSE={r.slipsense_tgt or 'unspec'}, "
            f"DIPDIRECT={r.dipdirect_tgt or 'unspec'}); kinematic_compat={bool(r.kinematic_compat)}."
        )
    else:
        vec_desc = (
            f"NBMG INGENIOUS vector attribution: inter-zone linkage bridging FID={r.fid_src} ('{ns}', "
            f"{r.ftype_src or 'untyped'}, SLIPSENSE={r.slipsense_src or 'unspec'}, DIPDIRECT={r.dipdirect_src or 'unspec'}) "
            f"to FID={r.fid_tgt} ('{nt}', {r.ftype_tgt or 'untyped'}, SLIPSENSE={r.slipsense_tgt or 'unspec'}, "
            f"DIPDIRECT={r.dipdirect_tgt or 'unspec'}); kinematic_compat={bool(r.kinematic_compat)}."
        )
    return (f"Closing this {r.gap_km:.1f} km gap would join two currently disconnected mapped systems "
            f"({r.size_src_km:.1f} km and {r.size_tgt_km:.1f} km) into one {r.merged_km:.1f} km system. "
            f"{vec_desc} Geometry: {kind}; "
            f"{mut}; the tip points {r.ang_src:.0f} deg off the link{tgt}. The link strikes N{r.strike:.0f} E and "
            f"{100 * r.strike_compat:.0f}% of the distance-weighted catalogued fault length within ~40 km lies within 20 deg of that "
            f"strike (data-driven kinematic domain; no external stress model). Structural-setting label (geometry only; "
            f"mapping to settings is ours): linkage/termination/step-over settings host ~25%/32% of characterised Great Basin "
            f"geothermal systems (Faulds & Hinz 2015). Connectivity context: the catalogue network is near its critical "
            f"connectivity (Berkowitz-style P={gb['P']:.2f} vs Pc 5.6-6.0 at the domain scale), where individual closures matter "
            f"most, but Berkowitz et al. (2000) give ensemble statistics, not a verdict on this particular gap. "
            f"Base coverage: {100 * r.base_overlap:.0f}% of its dots already lie within 300 m of the 0.2477 emission. "
            + ("NOTE: the straight link passes within ~100 m of a THIRD mapped system (crossing/T-junction), so it is not a pure "
               "two-system gap; kept because it belongs to the validated rule. " if r.third_system_contact else "")
            + "Status: validated on both 8-connected component holdout (0.293 vs 0.059 ctrl) and NBMG FID vector-trace holdout (0.100 vs 0.020 ctrl).")


def main() -> int:
    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    base = load_mask(paths.DOTTED_0_2477)
    raw = load_mask(paths.H19_5)
    res = candidates.build_set(labels, foot, base, raw)
    va = vector_graph.load_vector_attribution(labels, foot)
    L = vector_graph.annotate_links(res["links"], va)
    vec_summary = vector_graph.component_vector_summary(res["fg"], va, L)
    gr = json.loads((paths.EVIDENCE / "graph_report.json").read_text())["berkowitz_style_estimate"]
    gb = {"P": gr["P_at_domain_equivalent_side"]}
    L["argument"] = [argument(r, gb) for r in L.itertuples(index=False)]
    keep = ["link_id", "z", "kind", "gap_km", "ang_src", "ang_tgt", "mutual", "strike", "strike_compat",
            "size_src_km", "size_tgt_km", "merged_km", "dots", "base_overlap", "dots_near_h19_5_raw_px3", "third_system_contact",
            "fid_src", "fid_tgt", "same_fid", "name_src", "name_tgt", "same_name", "num_src", "num_tgt",
            "ftype_src", "ftype_tgt", "slipsense_src", "slipsense_tgt", "dipdirect_src", "dipdirect_tgt",
            "mapscale_src", "mapscale_tgt", "kinematic_compat",
            "lon_a", "lat_a", "lon_b", "lat_b", "e_row", "e_col", "q_row", "q_col", "argument"]
    df = L[keep].copy()
    for c in ("gap_km", "ang_src", "ang_tgt", "strike", "strike_compat", "size_src_km", "size_tgt_km", "merged_km",
              "lon_a", "lat_a", "lon_b", "lat_b"):
        df[c] = df[c].astype(float).round(5 if c.startswith(("lon", "lat")) else 3)
    docs_data = paths.DOCS / "data"
    docs_data.mkdir(parents=True, exist_ok=True)
    df.drop(columns=["argument"]).to_csv(docs_data / "topology_links.csv", index=False)
    feats = []
    for r in df.itertuples(index=False):
        feats.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[r.lon_a, r.lat_a], [r.lon_b, r.lat_b]]},
                      "properties": {"id": r.link_id, "z": int(r.z), "kind": r.kind, "gap_km": r.gap_km, "mutual": bool(r.mutual),
                                     "strike": r.strike, "strike_compat": r.strike_compat, "merged_km": r.merged_km,
                                     "base_overlap": r.base_overlap, "fid_src": int(r.fid_src), "fid_tgt": int(r.fid_tgt),
                                     "same_fid": bool(r.same_fid), "name_src": r.name_src, "name_tgt": r.name_tgt,
                                     "same_name": bool(r.same_name), "slipsense_src": r.slipsense_src,
                                     "slipsense_tgt": r.slipsense_tgt, "dipdirect_src": r.dipdirect_src,
                                     "dipdirect_tgt": r.dipdirect_tgt, "kinematic_compat": bool(r.kinematic_compat),
                                     "argument": r.argument}})
    (docs_data / "topology_links.geojson").write_text(json.dumps({"type": "FeatureCollection", "crs_note": "WGS84 lon/lat",
                                                                   "features": feats}))
    clo = {k: v for k, v in res["closure"].items() if k != "cluster_km_after_each_link"}
    summary = {"rule": candidates.RULE, "spacing": candidates.SPACING, "z_min": candidates.Z_MIN, "dedupe_mutual": True,
               "links_all_forward": res["links_all_forward"], "z_counts": res["z_counts"], "selected_links": int(len(df)),
               "selected_dots": int(res["dots"].sum()), "nonredundant_dots_vs_0_2477": int(res["dots_nonredundant"].sum()),
               "closure": clo, "graph": res["graph"], "vector_attribution": vec_summary,
               "kind_counts": df.kind.value_counts().to_dict(),
               "mutual_links": int(df.mutual.sum()), "third_system_contact_links": int(df.third_system_contact.sum()),
               "median_gap_km": float(df.gap_km.median()), "mean_base_overlap": float(df.base_overlap.mean())}
    (paths.EVIDENCE / "candidate_summary.json").write_text(json.dumps(summary, indent=1, default=float))
    (paths.REGISTRY / "topology_candidates.json").write_text(json.dumps({"summary": summary, "links": json.loads(df.to_json(orient="records"))},
                                                                         indent=1))
    np.save(paths.DATA / "topology_dots_nonredundant.npy", res["dots_nonredundant"])
    print(json.dumps(summary, indent=1, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
