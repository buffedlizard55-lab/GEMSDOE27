"""Vector attribution of the 100 m fault graph using the NBMG INGENIOUS Qfaults polylines.

Maps every catalogue pixel (`labels.tif`) and every skeleton component to its nearest vector polyline
in `qfaults_v2_in_footprint.json` (1,179 NBMG INGENIOUS Qfaults polylines inside the GeoDAWN bounding box,
matching `labels.tif` to 98.42% within 100 m and 99.97% within 200 m). Provides:
  * pixel-level group maps (`pix_fid`, `pix_name`) for trace-level (`FID`) and zone-level (`NAME`) holdouts;
  * component-level vector attributes (`FID`, `NAME`, `NUM`, `SLIPSENSE`, `DIPDIRECT`, `FTYPE_`, `MAPSCALE`);
  * link-level kinematic compatibility (`kinematic_compat`) for H27-5.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import CRS, Transformer
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree
from skimage.draw import line as sk_line

from . import grid, paths
from .graph import FaultGraph

NBMG_ALBERS_WKT = (
    'PROJCS["NAD_1983_Contiguous_USA_Albers_117",'
    'GEOGCS["GCS_North_American_1983",DATUM["D_North_American_1983",'
    'SPHEROID["GRS_1980",6378137.0,298.257222101]],PRIMEM["Greenwich",0.0],'
    'UNIT["Degree",0.0174532925199433]],PROJECTION["Albers"],'
    'PARAMETER["False_Easting",0.0],PARAMETER["False_Northing",0.0],'
    'PARAMETER["Central_Meridian",-117.0],PARAMETER["Standard_Parallel_1",29.5],'
    'PARAMETER["Standard_Parallel_2",45.5],PARAMETER["Latitude_Of_Origin",23.0],'
    'UNIT["Meter",1.0]]'
)

OPPOSITE_DIP = {
    ("E", "W"), ("W", "E"),
    ("N", "S"), ("S", "N"),
    ("NE", "SW"), ("SW", "NE"),
    ("NW", "SE"), ("SE", "NW"),
}


@dataclass
class VectorAttribution:
    features: list[dict]          # attributes dict per feature index 0..N-1
    pix_fid_idx: np.ndarray       # int32 (H, W), 1-based feature index on label pixels (0 elsewhere)
    pix_name_id: np.ndarray       # int32 (H, W), 1-based unique NAME index on label pixels (0 elsewhere)
    alignment_stats: dict         # correspondence summary between labels.tif and vector polylines


def is_kinematically_compatible(sa: str, sb: str, da: str, db: str) -> bool:
    """Pre-registered H27-5 kinematic compatibility check on (SLIPSENSE, DIPDIRECT) pairs."""
    sa = (sa or "").strip()
    sb = (sb or "").strip()
    if sa and sb and sa != sb:
        return False
    da = (da or "").strip()
    db = (db or "").strip()
    if da in ("", "Unspecified"):
        da = ""
    if db in ("", "Unspecified"):
        db = ""
    if (da, db) in OPPOSITE_DIP and (sa in ("RL", "LL") or sb in ("RL", "LL")) and sa != sb:
        return False
    return True


def is_kinematic_compat(attr_a: dict, attr_b: dict) -> bool:
    """Pre-registered H27-5 kinematic compatibility check between two fault attribute dicts."""
    return is_kinematically_compatible(
        attr_a.get("SLIPSENSE", ""),
        attr_b.get("SLIPSENSE", ""),
        attr_a.get("DIPDIRECT", ""),
        attr_b.get("DIPDIRECT", ""),
    )


def load_vector_attribution(
    labels: np.ndarray,
    foot: np.ndarray,
    vec_path: Path = paths.QFAULT_VECTORS,
) -> VectorAttribution:
    data = json.loads(Path(vec_path).read_text())
    tf = Transformer.from_crs(CRS.from_wkt(NBMG_ALBERS_WKT), CRS.from_epsg(grid.CRS_EPSG), always_xy=True)
    pts_rc: list[tuple[int, int]] = []
    pts_fid: list[int] = []
    feat_attrs: list[dict] = []
    vec_mask = np.zeros(labels.shape, bool)

    for idx, feat in enumerate(data["features"]):
        feat_attrs.append(feat["attributes"])
        for path in feat["geometry"]["paths"]:
            pts = np.asarray(path, float)
            ux, uy = tf.transform(pts[:, 0], pts[:, 1])
            cols = np.floor((ux - grid.TRANSFORM[2]) / grid.PIXEL_M).astype(int)
            rows = np.floor((grid.TRANSFORM[5] - uy) / grid.PIXEL_M).astype(int)
            for i in range(len(rows) - 1):
                rr, cc = sk_line(int(rows[i]), int(cols[i]), int(rows[i + 1]), int(cols[i + 1]))
                ok = (rr >= 0) & (rr < grid.SHAPE[0]) & (cc >= 0) & (cc < grid.SHAPE[1])
                rr_ok, cc_ok = rr[ok], cc[ok]
                vec_mask[rr_ok, cc_ok] = True
                for r, c in zip(rr_ok.tolist(), cc_ok.tolist()):
                    pts_rc.append((r, c))
                    pts_fid.append(idx)

    tree = cKDTree(pts_rc)
    pts_fid_arr = np.asarray(pts_fid, dtype=np.int32)
    names = [(a.get("NAME") or "").strip() or f"unnamed_{i}" for i, a in enumerate(feat_attrs)]
    uniq_names = {n: k for k, n in enumerate(sorted(set(names)))}
    name_lut = np.array([uniq_names[n] for n in names], dtype=np.int32)

    ly, lx = np.nonzero(labels)
    dist, nn = tree.query(np.c_[ly, lx])
    pix_fid = np.zeros(labels.shape, dtype=np.int32)
    pix_name = np.zeros(labels.shape, dtype=np.int32)
    pix_fid[ly, lx] = pts_fid_arr[nn] + 1
    pix_name[ly, lx] = name_lut[pts_fid_arr[nn]] + 1

    vec_in_foot = vec_mask & foot
    d_to_vec = distance_transform_edt(~vec_in_foot)
    d_to_lab = distance_transform_edt(~labels)
    stats = {
        "n_vector_features": len(feat_attrs),
        "n_unique_names_in_json": len(set((a.get("NAME") or "").strip() for a in feat_attrs)),
        "n_unique_names_matched_to_labels": int(len(np.unique(pix_name[labels]))),
        "n_unique_fids_matched_to_labels": int(len(np.unique(pix_fid[labels]))),
        "labels_px": int(labels.sum()),
        "vector_rasterized_in_footprint_px": int(vec_in_foot.sum()),
        "share_labels_within_1px_100m": float((d_to_vec[labels] <= 1.5).mean()),
        "share_labels_within_2px_200m": float((d_to_vec[labels] <= 2.5).mean()),
        "share_labels_within_3px_300m": float((d_to_vec[labels] <= 3.5).mean()),
        "share_vector_within_2px_of_labels": float((d_to_lab[vec_in_foot] <= 2.5).mean()),
        "median_label_to_vector_px": float(np.median(dist)),
    }
    return VectorAttribution(feat_attrs, pix_fid, pix_name, stats)


def annotate_links(df: pd.DataFrame, va: VectorAttribution) -> pd.DataFrame:
    """Attach source/target NBMG vector attributes and kinematic compatibility to a link DataFrame."""
    out = df.copy()
    if out.empty:
        for col in (
            "fid_src", "fid_tgt", "name_src", "name_tgt", "num_src", "num_tgt",
            "slipsense_src", "slipsense_tgt", "dipdirect_src", "dipdirect_tgt",
            "ftype_src", "ftype_tgt", "mapscale_src", "mapscale_tgt",
            "same_fid", "same_name", "kinematic_compat",
        ):
            out[col] = []
        return out

    rows = []
    for r in out.itertuples(index=False):
        idx_a = int(va.pix_fid_idx[int(r.e_row), int(r.e_col)]) - 1
        idx_b = int(va.pix_fid_idx[int(r.q_row), int(r.q_col)]) - 1
        a = va.features[max(idx_a, 0)]
        b = va.features[max(idx_b, 0)]
        fid_a, fid_b = int(a["FID"]), int(b["FID"])
        name_a = (a.get("NAME") or "").strip() or "Unnamed fault"
        name_b = (b.get("NAME") or "").strip() or "Unnamed fault"
        num_a = (a.get("NUM") or "").strip()
        num_b = (b.get("NUM") or "").strip()
        sa = (a.get("SLIPSENSE") or "").strip() or "Unspecified"
        sb = (b.get("SLIPSENSE") or "").strip() or "Unspecified"
        da = (a.get("DIPDIRECT") or "").strip() or "Unspecified"
        db = (b.get("DIPDIRECT") or "").strip() or "Unspecified"
        fa = (a.get("FTYPE_") or "").strip()
        fb = (b.get("FTYPE_") or "").strip()
        ma = (a.get("MAPSCALE") or "").strip()
        mb = (b.get("MAPSCALE") or "").strip()
        rows.append({
            "fid_src": fid_a,
            "fid_tgt": fid_b,
            "name_src": name_a,
            "name_tgt": name_b,
            "num_src": num_a,
            "num_tgt": num_b,
            "slipsense_src": sa,
            "slipsense_tgt": sb,
            "dipdirect_src": da,
            "dipdirect_tgt": db,
            "ftype_src": fa,
            "ftype_tgt": fb,
            "mapscale_src": ma,
            "mapscale_tgt": mb,
            "same_fid": bool(fid_a == fid_b),
            "same_name": bool(name_a == name_b and name_a != "Unnamed fault"),
            "kinematic_compat": bool(is_kinematic_compat(a, b)),
        })
    extra = pd.DataFrame(rows, index=out.index)
    for col in extra.columns:
        out[col] = extra[col]
    return out


def make_group_split(
    labels: np.ndarray,
    fold: np.ndarray,
    group_map: np.ndarray,
    fold_id: int,
    seed: int,
    frac: float = 0.20,
) -> tuple[np.ndarray, np.ndarray]:
    """Hide `frac` of distinct positive group ids inside quadrant `fold_id`."""
    fm = fold == fold_id
    gids = np.unique(group_map[labels & fm])
    gids = gids[gids > 0]
    if len(gids) == 0:
        return np.zeros_like(labels, bool), labels.copy()
    rng = np.random.default_rng(4242 + fold_id + 1000 * seed)
    keep = rng.choice(gids, size=max(1, int(round(frac * len(gids)))), replace=False)
    hidden = np.isin(group_map, keep) & labels & fm
    known = labels & ~hidden
    return hidden, known


def component_vector_summary(fg: FaultGraph, va: VectorAttribution, sel_links: pd.DataFrame) -> dict:
    """Summary of how the 3,199 raster components and 345 T-v2 links map to NBMG vector records."""
    ann = annotate_links(sel_links, va)
    return {
        "alignment": va.alignment_stats,
        "shipped_links_total": int(len(ann)),
        "shipped_same_fid": int(ann["same_fid"].sum()),
        "shipped_inter_fid": int((~ann["same_fid"]).sum()),
        "shipped_same_name": int(ann["same_name"].sum()),
        "shipped_inter_name": int((~ann["same_name"]).sum()),
        "shipped_kinematic_compat": int(ann["kinematic_compat"].sum()),
        "shipped_inter_fid_and_same_name": int((~ann["same_fid"] & ann["same_name"]).sum()),
        "shipped_inter_fid_and_kinematic_compat": int((~ann["same_fid"] & ann["kinematic_compat"]).sum()),
    }
