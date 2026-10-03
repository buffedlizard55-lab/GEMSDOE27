#!/usr/bin/env python3
"""Build the topology candidate set from the full catalogue and write dossiers + GIS files."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import (  # noqa: E402
    candidates,
    graph_value,
    grid,
    paths,
    topology_classes,
    vector_graph,
)


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
    review_class = topology_classes.classify_review_class(r.same_fid, r.same_name, r.kinematic_compat)
    review_limit = (
        " Different FIDs are records in this same NBMG compilation, not independent source confirmation."
        if review_class == topology_classes.H27_5B_PRIORITY_CLASS
        else ""
    )
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
            + graph_sentence(r)
            + "Status: validated on both 8-connected component holdout (0.293 vs 0.059 ctrl) and NBMG FID vector-trace holdout (0.100 vs 0.020 ctrl). "
            + f"Reviewer geometry cue only: {topology_classes.geometry_setting_hint(r.kind)}; this is not proof of a step-over or termination. "
            + f"Exclusive review class: {review_class}.{review_limit}")


def graph_sentence(r) -> str:
    """The graph consequence of THIS link, computed by src/gems27/graph_value.py (Addendum D, D-3)."""
    bridge = ("It is a graph bridge: no other selected candidate joins these two sides, so this closure is what "
              "actually merges them." if bool(r.bridge) else
              "It is not a bridge: another selected candidate already joins these two sides, so its network value "
              "is redundant with that one.")
    return (f" Graph value (Berkowitz et al. 2000 connectivity parameter, computed on the catalogue graph plus all "
            f"345 selected candidates with a=2.500 and D=1.566 held at their fitted values): this closure changes "
            f"P by dP={r.delta_P:+.4f} (rank {int(r.connectivity_rank)} of 345 by |dP|) and the largest-system share "
            f"of total mapped fault length by {r.delta_largest_share:+.5f}; the merged system would be "
            f"{r.merge_len_km:.2f} km long. {bridge} ")


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
    gv = graph_value.link_connectivity_values(res["fg"], L)
    for c in ("bridge", "merge_len_km", "delta_largest_share", "delta_P", "delta_second_moment_km2",
              "connectivity_rank"):
        L[c] = gv[c].to_numpy()
    L["review_class"] = [
        topology_classes.classify_review_class(r.same_fid, r.same_name, r.kinematic_compat)
        for r in L.itertuples(index=False)
    ]
    L["setting_hint"] = [topology_classes.geometry_setting_hint(kind) for kind in L.kind]
    L["nbmg_source_layer_url"] = topology_classes.NBMG_LAYER_URL
    L["setting_context_url"] = topology_classes.FAULDS_HINZ_URL
    L["argument"] = [argument(r, gb) for r in L.itertuples(index=False)]
    keep = ["link_id", "z", "kind", "gap_km", "ang_src", "ang_tgt", "mutual", "strike", "strike_compat",
            "size_src_km", "size_tgt_km", "merged_km", "dots", "base_overlap", "dots_near_h19_5_raw_px3", "third_system_contact",
            "fid_src", "fid_tgt", "same_fid", "name_src", "name_tgt", "same_name", "num_src", "num_tgt",
            "ftype_src", "ftype_tgt", "slipsense_src", "slipsense_tgt", "dipdirect_src", "dipdirect_tgt",
            "mapscale_src", "mapscale_tgt", "kinematic_compat", "review_class", "setting_hint",
            "nbmg_source_layer_url", "setting_context_url",
            "bridge", "merge_len_km", "delta_largest_share", "delta_P", "delta_second_moment_km2",
            "connectivity_rank",
            "lon_a", "lat_a", "lon_b", "lat_b", "e_row", "e_col", "q_row", "q_col", "argument"]
    df = L[keep].copy()
    for c in ("gap_km", "ang_src", "ang_tgt", "strike", "strike_compat", "size_src_km", "size_tgt_km", "merged_km",
              "lon_a", "lat_a", "lon_b", "lat_b"):
        df[c] = df[c].astype(float).round(5 if c.startswith(("lon", "lat")) else 3)
    df["merge_len_km"] = df["merge_len_km"].astype(float).round(3)
    df["delta_largest_share"] = df["delta_largest_share"].astype(float).round(6)
    df["delta_P"] = df["delta_P"].astype(float).round(6)
    df["delta_second_moment_km2"] = df["delta_second_moment_km2"].astype(float).round(4)
    df["bridge"] = df["bridge"].astype(bool)
    df["connectivity_rank"] = df["connectivity_rank"].astype(int)
    docs_data = paths.DOCS / "data"
    docs_data.mkdir(parents=True, exist_ok=True)
    df.drop(columns=["argument"]).to_csv(docs_data / "topology_links.csv", index=False)
    priority_df = df[df.review_class == topology_classes.H27_5B_PRIORITY_CLASS].copy()
    priority_df = priority_df.sort_values(["gap_km", "link_id"], ascending=[True, True])
    priority_df.to_csv(docs_data / "topology_priority_h27_5b.csv", index=False)
    feats = []
    for r in df.itertuples(index=False):
        feats.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[r.lon_a, r.lat_a], [r.lon_b, r.lat_b]]},
                      "properties": {"id": r.link_id, "z": int(r.z), "kind": r.kind, "gap_km": r.gap_km, "mutual": bool(r.mutual),
                                     "strike": r.strike, "strike_compat": r.strike_compat, "merged_km": r.merged_km,
                                     "base_overlap": r.base_overlap, "fid_src": int(r.fid_src), "fid_tgt": int(r.fid_tgt),
                                     "name_src": r.name_src, "name_tgt": r.name_tgt, "num_src": r.num_src, "num_tgt": r.num_tgt,
                                     "ftype_src": r.ftype_src, "ftype_tgt": r.ftype_tgt,
                                     "mapscale_src": r.mapscale_src, "mapscale_tgt": r.mapscale_tgt,
                                     "same_fid": bool(r.same_fid), "same_name": bool(r.same_name),
                                     "slipsense_src": r.slipsense_src, "slipsense_tgt": r.slipsense_tgt,
                                     "dipdirect_src": r.dipdirect_src, "dipdirect_tgt": r.dipdirect_tgt,
                                     "kinematic_compat": bool(r.kinematic_compat), "review_class": r.review_class,
                                     "setting_hint": r.setting_hint, "third_system_contact": bool(r.third_system_contact),
                                     "bridge": bool(r.bridge), "delta_P": float(r.delta_P),
                                     "delta_largest_share": float(r.delta_largest_share),
                                     "delta_second_moment_km2": float(r.delta_second_moment_km2),
                                     "connectivity_rank": int(r.connectivity_rank), "nbmg_source_layer_url": r.nbmg_source_layer_url,
                                     "setting_context_url": r.setting_context_url, "argument": r.argument}})
    geojson = {"type": "FeatureCollection", "crs_note": "WGS84 lon/lat", "features": feats}
    (docs_data / "topology_links.geojson").write_text(json.dumps(geojson))
    priority_features = [
        feature for feature in feats
        if feature["properties"]["review_class"] == topology_classes.H27_5B_PRIORITY_CLASS
    ]
    (docs_data / "topology_priority_h27_5b.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "crs_note": "WGS84 lon/lat", "features": priority_features})
    )
    clo = {k: v for k, v in res["closure"].items() if k != "cluster_km_after_each_link"}
    vector_eval = json.loads((paths.EVIDENCE / "vector_topology_validation.json").read_text())
    tier2 = vector_eval["tiers"]["FID_trace"]["efficiency_pooled"]
    h27_5b_key = "z>=3 inter-FID + same_name + kinematic_compat (H27-5b)"
    priority_count = int((df.review_class == topology_classes.H27_5B_PRIORITY_CLASS).sum())
    class_counts = {name: int((df.review_class == name).sum()) for name in topology_classes.REVIEW_CLASS_NAMES}
    structural_classes = {
        "schema": 1,
        "candidate_count": int(len(df)),
        "priority_class": topology_classes.H27_5B_PRIORITY_CLASS,
        "priority_candidate_count": priority_count,
        "priority_population": "existing z>=3 deduplicated T-v2 candidate set; all 345 links have a 1-4 km gap; no new links generated",
        "priority_rule": "different NBMG FID AND same non-unnamed NAME AND kinematic_compat=true",
        "same_name_semantics": "vector_graph.annotate_links: name_src == name_tgt and name_src != 'Unnamed fault'",
        "kinematic_compatibility_semantics": (
            "vector_graph.is_kinematically_compatible: reject differing non-empty slip senses; also reject "
            "registered opposite dip-direction pairs when the senses differ and at least one is RL/LL. "
            "Blank/Unspecified values are normalized to unknown and may pass; this is a permissive screen."
        ),
        "counts_by_exclusive_review_class": class_counts,
        "priority_basis": {
            "validation": "Tier-2 whole NBMG FID_trace component holdout; not organizer-created test labels",
            "seeds": vector_eval["seeds"],
            "h27_5b_efficiency": float(tier2[h27_5b_key]),
            "rotated_control_efficiency": float(tier2["ctrl"]),
            "enrichment_over_control": float(tier2[h27_5b_key] / tier2["ctrl"]),
            "graph_delta_P_used_for_priority": False,
            "graph_value_ranking_status": "refuted as a predictive ranking signal in Addendum D (seeds 140-149)",
        },
        "geometry_setting_hints": {
            "end-to-end": topology_classes.geometry_setting_hint("end-to-end"),
            "abutting": topology_classes.geometry_setting_hint("abutting"),
            "tip-to-tip oblique": topology_classes.geometry_setting_hint("tip-to-tip oblique"),
        },
        "files": {
            "full_csv": "docs/data/topology_links.csv",
            "full_geojson": "docs/data/topology_links.geojson",
            "priority_csv": "docs/data/topology_priority_h27_5b.csv",
            "priority_geojson": "docs/data/topology_priority_h27_5b.geojson",
            "priority_map_preview": "docs/assets/fig_map_h27_5b_priority.png",
        },
        "official_sources": {
            "nbmg_qfaults_layer": topology_classes.NBMG_LAYER_URL,
            "faulds_hinz_2015_context": topology_classes.FAULDS_HINZ_URL,
            "berkowitz_2000_publisher": "https://agupubs.onlinelibrary.wiley.com/doi/10.1029/1999GL011241",
        },
        "limitations": [
            "Different FIDs are distinct records in one NBMG INGENIOUS compilation, not independent surveys; same-name records may be named segments of one fault zone.",
            "Nearest-polyline vector attribution and the compatibility rule are screening annotations, not verified slip histories or fault truth.",
            "H27-5b enrichment is catalogue-internal whole-FID holdout evidence; no hidden organizer labels or public score were observed.",
            "Geometry hints only nominate map-review context. Faulds and Hinz setting frequencies describe characterized geothermal systems, not any individual link.",
            "The separate overlapping en-echelon step-over test was refuted as a holdout-improvement signal; a tip-to-tip oblique cue does not reverse that result.",
        ],
    }
    (paths.EVIDENCE / "structural_relay_classes.json").write_text(json.dumps(structural_classes, indent=2) + "\n")
    (docs_data / "topology_review_classes.json").write_text(json.dumps(structural_classes, indent=2) + "\n")
    summary = {"rule": candidates.RULE, "spacing": candidates.SPACING, "z_min": candidates.Z_MIN, "dedupe_mutual": True,
               "links_all_forward": res["links_all_forward"], "z_counts": res["z_counts"], "selected_links": int(len(df)),
               "selected_dots": int(res["dots"].sum()), "nonredundant_dots_vs_0_2477": int(res["dots_nonredundant"].sum()),
               "closure": clo, "graph": res["graph"], "vector_attribution": vec_summary,
               "structural_review_classes": structural_classes,
               "kind_counts": df.kind.value_counts().to_dict(),
               "mutual_links": int(df.mutual.sum()), "third_system_contact_links": int(df.third_system_contact.sum()),
               "median_gap_km": float(df.gap_km.median()), "mean_base_overlap": float(df.base_overlap.mean()),
               "graph_value": {
                   "method": ("Berkowitz-Bour-Davy-Odling (2000) connectivity parameter P = beta L^D lmin^(1-a)/(a-1) "
                              "integrated over the domain, computed with this repo's own closed form "
                              "(src/gems27/topology_theory.py, unit-tested against the paper); a = 2.5000 and "
                              "D = 1.5662 held at the values fitted on the full catalogue "
                              "(evidence/graph_report.json), lmin = 2 km, L = 227.319 km "
                              "(domain-equivalent side). dP is exact for a single merge: dn = [lA+lB+gap >= lmin] "
                              "- [lA >= lmin] - [lB >= lmin] and P is linear in n."),
                   "P_with_all_345_candidates": float(gv.P_with_all_links.iloc[0]),
                   "P_catalogue_only_published": gr["P_at_domain_equivalent_side"],
                   "Pc_range": gr["Pc_range"],
                   "largest_share_of_mapped_length_with_all_candidates": float(gv.largest_share_with_all_links.iloc[0]),
                   "n_bridges": int(gv.bridge.sum()), "n_links": int(len(gv)),
                   "delta_P_min": float(gv.delta_P.min()), "delta_P_max": float(gv.delta_P.max()),
                   "delta_P_nonzero": int((gv.delta_P.abs() > 1e-12).sum()),
                   "delta_P_is_quantised": ("dP takes only the values {-1, 0, +1} x P/n_ge because it counts "
                                            "systems above lmin = 2 km; it is an ordinal. The continuous "
                                            "tie-break is delta_second_moment_km2 (change in sum l^2 over "
                                            "systems), and connectivity_rank = |dP| desc, |d(sum l^2)| desc, "
                                            "merged length desc. Disclosed in knowledge/03 Addendum D before "
                                            "the Stage-B gate ran."),
                   "network_second_moment_km2_with_all_candidates": float(gv.network_second_moment_km2.iloc[0]),
                   "second_moment_per_area_with_all_candidates": float(gv.second_moment_per_area.iloc[0]),
                   "second_moment_caveat": ("No critical value is quoted for sum(l^2)/area: a threshold for it "
                                            "could not be verified from an official source inside this sandbox "
                                            "(only github.com and pypi.org are reachable). It is reported as a "
                                            "continuous relative measure and as the tie-break inside equal |dP|, "
                                            "never as a pass/fail criterion."),
                   "delta_largest_share_max": float(gv.delta_largest_share.max()),
                   "top10_by_abs_delta_P": [
                       {"link_id": df.link_id.iloc[i], "delta_P": float(df.delta_P.iloc[i]),
                        "bridge": bool(df.bridge.iloc[i]), "merge_len_km": float(df.merge_len_km.iloc[i]),
                        "name_src": df.name_src.iloc[i], "kind": df.kind.iloc[i], "z": int(df.z.iloc[i])}
                       for i in gv.connectivity_rank.sort_values().index[:10]],
                   "gate": ("Addendum D, D-3: whether ranking by |dP| beats the shipped z>=3 rule is MEASURED on "
                            "seeds 140-149 in evidence/addendum_d_gates.json; these values are documentation "
                            "regardless of that gate's outcome.")}}
    (paths.EVIDENCE / "candidate_summary.json").write_text(json.dumps(summary, indent=1, default=float))
    (paths.REGISTRY / "topology_candidates.json").write_text(json.dumps({"summary": summary, "links": json.loads(df.to_json(orient="records"))},
                                                                         indent=1))
    (paths.EVIDENCE / "link_graph_value.json").write_text(json.dumps(
        {"summary": summary["graph_value"],
         "links": json.loads(df[["link_id", "bridge", "merge_len_km", "delta_largest_share", "delta_P",
                                 "delta_second_moment_km2", "connectivity_rank", "kind", "z", "gap_km",
                                 "name_src", "name_tgt", "fid_src", "fid_tgt"]].to_json(orient="records"))},
        indent=1))
    np.save(paths.DATA / "topology_dots_nonredundant.npy", res["dots_nonredundant"])
    print(json.dumps(summary, indent=1, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
