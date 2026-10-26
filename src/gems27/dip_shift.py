"""Visible-fault DIPDIRECT vectors for directional potential-field edge projection (H29-2).

This module uses only NBMG Qfaults vector features explicitly supplied by the caller as visible.
It does not read the label raster, hidden group IDs, catalogue distance, or submission registry.
Caller-side fold discipline is mandatory: filter vector feature indices from the visible-label mask,
exclude line pixels within the hidden-segment buffer, then build this field separately per split.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from pyproj import CRS, Transformer
from scipy.ndimage import distance_transform_edt, gaussian_filter
from skimage.draw import line as sk_line

from . import grid
from .subsurface_features import _rank01
from .vector_graph import NBMG_ALBERS_WKT

DIP_DIRECTIONS: dict[str, tuple[float, float]] = {
    # Unit directions in row/column coordinates; rows increase south, columns increase east.
    "N": (-1.0, 0.0),
    "NE": (-2**-0.5, 2**-0.5),
    "E": (0.0, 1.0),
    "SE": (2**-0.5, 2**-0.5),
    "S": (1.0, 0.0),
    "SW": (2**-0.5, -2**-0.5),
    "W": (0.0, -1.0),
    "NW": (-2**-0.5, -2**-0.5),
}
FEATURE_NAMES = (
    "dip_updip_rtp_100_300m",
    "dip_updip_depth_100_300m",
    "dip_updip_crossfield_100_300m",
)
OFFSETS_PX = (1, 2, 3)


@dataclass(frozen=True)
class DipDirectionField:
    down_dip_y: np.ndarray
    down_dip_x: np.ndarray
    valid: np.ndarray
    source_mask: np.ndarray
    source_feature_indices: tuple[int, ...]
    metadata: dict


def rasterize_visible_dip_directions(
    vector_path: Path | str,
    visible_feature_indices: set[int] | tuple[int, ...] | list[int],
    footprint: np.ndarray,
    *,
    exclude_source_mask: np.ndarray | None = None,
    max_distance_px: float = 50.0,
) -> DipDirectionField:
    """Rasterize visible Qfaults DIPDIRECT values and nearest-fill no farther than 5 km.

    ``visible_feature_indices`` are zero-based indices in the pinned Qfaults ``features`` list.
    Direction attributes outside the eight explicit compass directions are treated as unknown,
    not guessed. Conflicting overlapping directions (mean-vector coherence < 0.75) are dropped.
    ``exclude_source_mask`` is normally the buffered training mask; no source vector pixel may be
    placed inside or outside that mask. The direction field itself is valid only within
    ``max_distance_px`` of a surviving specified-direction source pixel.
    """
    foot = np.asarray(footprint, bool)
    if foot.ndim != 2:
        raise ValueError("footprint must be a 2-D boolean grid")
    if not np.isfinite(max_distance_px) or max_distance_px < 0:
        raise ValueError("max_distance_px must be finite and non-negative")
    exclude = foot if exclude_source_mask is None else np.asarray(exclude_source_mask, bool) & foot
    if exclude.shape != foot.shape:
        raise ValueError("exclude_source_mask and footprint must have the same shape")

    payload = json.loads(Path(vector_path).read_text())
    features = payload.get("features")
    if not isinstance(features, list):
        raise ValueError("Qfaults vector JSON must contain a features list")
    selected = tuple(sorted(set(int(i) for i in visible_feature_indices)))
    if any(i < 0 or i >= len(features) for i in selected):
        raise ValueError("visible Qfaults feature index is outside the vector inventory")

    h, w = foot.shape
    y_sum = np.zeros((h, w), dtype=np.float32)
    x_sum = np.zeros((h, w), dtype=np.float32)
    votes = np.zeros((h, w), dtype=np.uint16)
    categories: dict[str, int] = {}
    transformer = Transformer.from_crs(
        CRS.from_wkt(NBMG_ALBERS_WKT), CRS.from_epsg(grid.CRS_EPSG), always_xy=True
    )

    for feature_index in selected:
        feature = features[feature_index]
        attributes = feature.get("attributes") or {}
        direction = str(attributes.get("DIPDIRECT", "")).strip().upper()
        unit = DIP_DIRECTIONS.get(direction)
        if unit is None:
            continue
        categories[direction] = categories.get(direction, 0) + 1
        geometry = feature.get("geometry") or {}
        for path in geometry.get("paths", []):
            points = np.asarray(path, dtype=np.float64)
            if points.ndim != 2 or points.shape[1] < 2 or points.shape[0] == 0:
                continue
            east, north = transformer.transform(points[:, 0], points[:, 1])
            cols = np.floor((np.asarray(east) - grid.TRANSFORM[2]) / grid.PIXEL_M).astype(np.int64)
            rows = np.floor((grid.TRANSFORM[5] - np.asarray(north)) / grid.PIXEL_M).astype(np.int64)
            if len(rows) == 1:
                rr, cc = rows, cols
                ok = (rr >= 0) & (rr < h) & (cc >= 0) & (cc < w)
                rr, cc = rr[ok], cc[ok]
            else:
                row_parts: list[np.ndarray] = []
                col_parts: list[np.ndarray] = []
                for j in range(len(rows) - 1):
                    rr, cc = sk_line(int(rows[j]), int(cols[j]), int(rows[j + 1]), int(cols[j + 1]))
                    ok = (rr >= 0) & (rr < h) & (cc >= 0) & (cc < w)
                    if ok.any():
                        row_parts.append(rr[ok])
                        col_parts.append(cc[ok])
                if not row_parts:
                    continue
                rr = np.concatenate(row_parts)
                cc = np.concatenate(col_parts)
            keep = foot[rr, cc] & exclude[rr, cc]
            rr, cc = rr[keep], cc[keep]
            y_sum[rr, cc] += np.float32(unit[0])
            x_sum[rr, cc] += np.float32(unit[1])
            votes[rr, cc] += 1

    magnitude = np.hypot(y_sum, x_sum)
    coherence = np.divide(magnitude, votes, out=np.zeros_like(magnitude), where=votes > 0)
    source = (votes > 0) & (coherence >= 0.75) & foot & exclude
    if source.any():
        y_source = np.divide(y_sum, magnitude, out=np.zeros_like(y_sum), where=source)
        x_source = np.divide(x_sum, magnitude, out=np.zeros_like(x_sum), where=source)
        distance, nearest = distance_transform_edt(
            ~source, return_distances=True, return_indices=True
        )
        down_y = y_source[tuple(nearest)].astype(np.float32, copy=False)
        down_x = x_source[tuple(nearest)].astype(np.float32, copy=False)
        valid = foot & (distance <= max_distance_px)
        down_y = np.where(valid, down_y, 0.0).astype(np.float32)
        down_x = np.where(valid, down_x, 0.0).astype(np.float32)
    else:
        distance = np.full(foot.shape, np.inf, dtype=np.float32)
        valid = np.zeros(foot.shape, dtype=bool)
        down_y = np.zeros(foot.shape, dtype=np.float32)
        down_x = np.zeros(foot.shape, dtype=np.float32)

    return DipDirectionField(
        down_dip_y=down_y,
        down_dip_x=down_x,
        valid=valid,
        source_mask=source,
        source_feature_indices=selected,
        metadata={
            "visible_feature_indices": list(selected),
            "specified_direction_feature_count": int(sum(categories.values())),
            "direction_category_counts": categories,
            "source_pixels": int(source.sum()),
            "direction_valid_pixels": int(valid.sum()),
            "max_distance_px": float(max_distance_px),
            "excluded_source_pixels": int((source & ~exclude).sum()),
        },
    )


def _rank_supported(values: np.ndarray, support: np.ndarray) -> np.ndarray:
    out = np.zeros(values.shape, dtype=np.float32)
    active = support & np.isfinite(values)
    selected = values[active].astype(np.float64)
    if selected.size == 0 or float(np.ptp(selected)) <= 0.0:
        return out
    out[active] = _rank01(selected)
    return out


def build_updip_edge_features(
    rtp_edge_rank: np.ndarray,
    depth_edge_rank: np.ndarray,
    field: DipDirectionField,
    footprint: np.ndarray,
    *,
    offsets_px: tuple[int, ...] = OFFSETS_PX,
) -> tuple[np.ndarray, dict]:
    """Project edge evidence up-dip; return (footprint-row matrix, support metadata).

    A target pixel samples the source edge at ``target + offset * down_dip_unit``; in this
    way the source edge is translated opposite its down-dip direction. Sampling is nearest
    pixel at the frozen offsets 1, 2 and 3 (100, 200 and 300 m on the 100 m grid). The three
    output columns are independently percentile-ranked on direction-supported footprint cells.
    """
    foot = np.asarray(footprint, bool)
    rtp = np.asarray(rtp_edge_rank, dtype=np.float32)
    depth = np.asarray(depth_edge_rank, dtype=np.float32)
    if foot.ndim != 2 or rtp.shape != foot.shape or depth.shape != foot.shape:
        raise ValueError("edge grids and footprint must have the same 2-D shape")
    if field.valid.shape != foot.shape or field.down_dip_y.shape != foot.shape or field.down_dip_x.shape != foot.shape:
        raise ValueError("dip-direction field and footprint must have the same shape")
    if not offsets_px or any(int(d) != d or d <= 0 for d in offsets_px):
        raise ValueError("offsets_px must contain positive integer pixel distances")
    if not np.isfinite(rtp[foot]).all() or not np.isfinite(depth[foot]).all():
        raise ValueError("edge surfaces must be finite inside the footprint")

    rows, cols = np.indices(foot.shape, dtype=np.float32)
    rtp_shift = np.zeros(foot.shape, dtype=np.float32)
    depth_shift = np.zeros(foot.shape, dtype=np.float32)
    for offset in offsets_px:
        source_rows = np.rint(rows + float(offset) * field.down_dip_y).astype(np.int32)
        source_cols = np.rint(cols + float(offset) * field.down_dip_x).astype(np.int32)
        inside = (
            (source_rows >= 0) & (source_rows < foot.shape[0])
            & (source_cols >= 0) & (source_cols < foot.shape[1])
        )
        rr = np.clip(source_rows, 0, foot.shape[0] - 1)
        cc = np.clip(source_cols, 0, foot.shape[1] - 1)
        valid = field.valid & foot & inside & foot[rr, cc]
        rtp_shift = np.maximum(rtp_shift, np.where(valid, rtp[rr, cc], 0.0))
        depth_shift = np.maximum(depth_shift, np.where(valid, depth[rr, cc], 0.0))

    support = field.valid & foot
    rtp_rank = _rank_supported(rtp_shift, support)
    depth_rank = _rank_supported(depth_shift, support)
    cross_rank = _rank_supported(np.minimum(rtp_shift, depth_shift), support)
    matrix = np.column_stack((rtp_rank[foot], depth_rank[foot], cross_rank[foot])).astype(np.float32)
    if not np.isfinite(matrix).all() or matrix.min(initial=0.0) < 0.0 or matrix.max(initial=0.0) > 1.0:
        raise ValueError("DIPDIRECT-projected features must be finite ranks in [0,1]")
    return matrix, {
        "feature_names": list(FEATURE_NAMES),
        "offsets_px": list(offsets_px),
        "support_px": int(support.sum()),
        "support_fraction_footprint": float(support.sum() / max(int(foot.sum()), 1)),
        "zero_feature_rows": int((matrix == 0.0).all(axis=1).sum()),
    }


def build_edge_ranks(
    prepared_features: np.ndarray,
    feature_names: list[str],
    footprint: np.ndarray,
    *,
    sigma_px: float = 2.0,
    pixel_size_m: float = 100.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Derive label-free RTP and basement-depth gradient-rank surfaces from the cached matrix."""
    foot = np.asarray(footprint, bool)
    X = prepared_features
    if X.ndim != 2 or X.shape[0] != int(foot.sum()):
        raise ValueError("prepared feature matrix must have one row per footprint pixel")
    required = ("rtp", "depth_to_base_surf")
    missing = [name for name in required if name not in feature_names]
    if missing:
        raise ValueError(f"cached stack is missing required bands: {missing}")

    def make_rank(name: str) -> np.ndarray:
        vals = np.asarray(X[:, feature_names.index(name)], dtype=np.float32)
        valid = np.isfinite(vals)
        if not valid.any():
            raise ValueError(f"cached band {name!r} has no finite footprint values")
        full = np.zeros(foot.shape, dtype=np.float32)
        full[foot] = vals
        finite_grid = np.zeros(foot.shape, dtype=bool)
        finite_grid[foot] = valid
        if not finite_grid.all():
            indices = distance_transform_edt(~finite_grid, return_distances=False, return_indices=True)
            filled = full[tuple(indices)]
        else:
            filled = full
        smooth = gaussian_filter(filled, sigma=sigma_px, mode="nearest")
        gy, gx = np.gradient(smooth, pixel_size_m, pixel_size_m)
        magnitude = np.hypot(gx, gy).astype(np.float32)
        result = np.zeros(foot.shape, dtype=np.float32)
        result[foot] = _rank01(magnitude[foot].astype(np.float64))
        return result

    return make_rank("rtp"), make_rank("depth_to_base_surf")
