import json

import numpy as np
from pyproj import CRS, Transformer

from gems27 import dip_shift, grid
from gems27.vector_graph import NBMG_ALBERS_WKT


def _albers_path_for_grid_points(rows, cols):
    x = grid.TRANSFORM[2] + (np.asarray(cols, dtype=float) + 0.5) * grid.PIXEL_M
    y = grid.TRANSFORM[5] - (np.asarray(rows, dtype=float) + 0.5) * grid.PIXEL_M
    transform = Transformer.from_crs(
        CRS.from_epsg(grid.CRS_EPSG), CRS.from_wkt(NBMG_ALBERS_WKT), always_xy=True
    )
    east, north = transform.transform(x, y)
    return np.column_stack((east, north)).tolist()


def test_visible_dip_rasterization_and_updip_projection(tmp_path):
    vector_path = tmp_path / "qfaults.json"
    payload = {
        "features": [
            {
                "attributes": {"FID": 1, "DIPDIRECT": "E"},
                "geometry": {"paths": [_albers_path_for_grid_points([10, 10], [9, 11])]},
            },
            {
                "attributes": {"FID": 2, "DIPDIRECT": "Unspecified"},
                "geometry": {"paths": [_albers_path_for_grid_points([4, 4], [4, 8])]},
            },
        ]
    }
    vector_path.write_text(json.dumps(payload))
    foot = np.ones((20, 20), dtype=bool)

    field = dip_shift.rasterize_visible_dip_directions(
        vector_path, {0}, foot, exclude_source_mask=foot, max_distance_px=5
    )

    assert field.source_mask[10, 10]
    assert field.valid[10, 8]
    assert np.isclose(field.down_dip_y[10, 10], 0.0, atol=1e-5)
    assert np.isclose(field.down_dip_x[10, 10], 1.0, atol=1e-5)
    assert field.metadata["specified_direction_feature_count"] == 1
    assert field.metadata["excluded_source_pixels"] == 0

    rtp = np.zeros(foot.shape, dtype=np.float32)
    depth = np.zeros(foot.shape, dtype=np.float32)
    rtp[10, 10] = 1.0
    depth[10, 10] = 1.0
    features, meta = dip_shift.build_updip_edge_features(rtp, depth, field, foot)
    by_pixel = np.zeros((20, 20, len(dip_shift.FEATURE_NAMES)), dtype=np.float32)
    by_pixel[foot] = features
    assert features.shape == (int(foot.sum()), 3)
    assert np.isfinite(features).all()
    assert features.min() >= 0.0 and features.max() <= 1.0
    assert by_pixel[10, 8, 0] > 0.0
    assert meta["offsets_px"] == [1, 2, 3]


def test_visible_dip_sources_obey_exclusion_mask(tmp_path):
    vector_path = tmp_path / "qfaults.json"
    payload = {
        "features": [
            {
                "attributes": {"FID": 1, "DIPDIRECT": "N"},
                "geometry": {"paths": [_albers_path_for_grid_points([10, 10], [9, 11])]},
            }
        ]
    }
    vector_path.write_text(json.dumps(payload))
    foot = np.ones((20, 20), dtype=bool)
    allowed = foot.copy()
    allowed[10, 10] = False

    field = dip_shift.rasterize_visible_dip_directions(
        vector_path, {0}, foot, exclude_source_mask=allowed, max_distance_px=5
    )

    assert not field.source_mask[10, 10]
    assert not np.any(field.source_mask & ~allowed)
    assert field.metadata["excluded_source_pixels"] == 0


def test_unknown_dip_direction_produces_no_features(tmp_path):
    vector_path = tmp_path / "qfaults.json"
    vector_path.write_text(json.dumps({"features": [
        {
            "attributes": {"FID": 1, "DIPDIRECT": "Unspecified"},
            "geometry": {"paths": [_albers_path_for_grid_points([10, 10], [9, 11])]},
        }
    ]}))
    foot = np.ones((20, 20), dtype=bool)
    field = dip_shift.rasterize_visible_dip_directions(vector_path, {0}, foot)
    assert field.metadata["source_pixels"] == 0
    assert not field.valid.any()


def test_cached_band_edge_ranks_are_finite_and_bounded():
    rows, cols = np.mgrid[:24, :20]
    foot = np.ones((24, 20), dtype=bool)
    rtp = (cols.astype(np.float32) ** 2 + rows.astype(np.float32))
    depth = (rows.astype(np.float32) ** 2 - 0.25 * cols.astype(np.float32))
    features = np.column_stack((rtp[foot], depth[foot]))

    rtp_rank, depth_rank = dip_shift.build_edge_ranks(
        features, ["rtp", "depth_to_base_surf"], foot, sigma_px=1.0
    )

    for rank in (rtp_rank, depth_rank):
        assert rank.shape == foot.shape
        assert np.isfinite(rank).all()
        assert rank.min() >= 0.0 and rank.max() <= 1.0
        assert np.unique(rank).size > 1
