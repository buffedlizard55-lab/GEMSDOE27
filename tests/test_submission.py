import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine

from gems27 import grid, submission


@pytest.fixture()
def tiny_template(tmp_path, monkeypatch):
    # small synthetic template with the same semantics (NaN outside, nodata NaN, LZW)
    H, W = 40, 50
    foot = np.zeros((H, W), bool)
    foot[5:35, 8:45] = True
    arr = np.where(foot, 0.0, np.nan).astype("float32")
    path = tmp_path / "tpl.tif"
    prof = dict(driver="GTiff", dtype="float32", count=1, height=H, width=W, crs="EPSG:32611",
                transform=Affine(100, 0, 243350, 0, -100, 4508550), nodata=np.nan, compress="lzw")
    with rasterio.open(path, "w", **prof) as d:
        d.write(arr, 1)
    monkeypatch.setattr(grid, "FOOTPRINT_PX", int(foot.sum()))
    monkeypatch.setattr(grid, "SHAPE", (H, W))
    monkeypatch.setattr(grid, "BOUNDS", (243350.0, 4508550.0 - H * 100, 243350.0 + W * 100, 4508550.0))
    return path, foot


def test_write_and_verify_nan_and_zero_variants(tiny_template, tmp_path):
    tpl, foot = tiny_template
    pred = np.zeros(foot.shape, "float32")
    pred[10, 10:20] = 1.0
    pred[20, 20] = 0.5
    p_nan = submission.write_geotiff(pred, tpl, tmp_path / "a-nan.tif", outside="nan")
    p_zero = submission.write_geotiff(pred, tpl, tmp_path / "a-allfinite.tif", outside="zero")
    r1 = submission.verify_geotiff(p_nan, tpl)
    r2 = submission.verify_geotiff(p_zero, tpl)
    assert r1["hard_checks_passed"], r1["hard_failures"]
    assert r2["hard_checks_passed"], r2["hard_failures"]
    assert r1["variant"] == "nan" and r2["variant"] == "allfinite"
    with rasterio.open(p_nan) as s:
        a = s.read(1)
        assert s.nodata is not None and np.isnan(s.nodata)
        assert np.isnan(a[~foot]).all() and np.isfinite(a[foot]).all()
    with rasterio.open(p_zero) as s:
        a = s.read(1)
        assert s.nodata is None and np.isfinite(a).all() and a.min() >= 0 and a.max() <= 1


@pytest.mark.parametrize("bad", [1.0000001, -0.0000001, np.nan, np.inf])
def test_writer_refuses_out_of_range_or_nonfinite(tiny_template, tmp_path, bad):
    tpl, foot = tiny_template
    pred = np.zeros(foot.shape, "float32")
    pred[10, 10] = bad
    with pytest.raises(ValueError):
        submission.write_geotiff(pred, tpl, tmp_path / "bad.tif")


def test_zip_contains_exactly_one_identical_tif(tiny_template, tmp_path):
    tpl, foot = tiny_template
    p = submission.write_geotiff(np.zeros(foot.shape, "float32"), tpl, tmp_path / "z-nan.tif")
    z = submission.zip_single(p)
    import zipfile
    with zipfile.ZipFile(z) as zf:
        assert zf.namelist() == [p.name]
        assert zf.read(p.name) == p.read_bytes()


def test_note_length_and_filename():
    note = submission.make_note("T-v1", "x" * 400, "abcdef123456")
    assert len(note) <= 200 and note.endswith("not yet live-scored")
    fn = submission.make_filename("gems27", "Topo gap/closure d1.5", "20261002", "abcdef123456", "nan")
    assert fn == "gems27-topo-gap-closure-d1-5-20261002-abcdef123456-nan.tif"


def test_content_id_ignores_catalogue_pixels():
    foot = np.ones((5, 5), bool)
    cat = np.zeros((5, 5), bool)
    cat[2, 2] = True
    a = np.zeros((5, 5), "float32")
    b = a.copy()
    b[2, 2] = 1.0
    assert submission.scored_content_id(a, foot, cat) == submission.scored_content_id(b, foot, cat)
