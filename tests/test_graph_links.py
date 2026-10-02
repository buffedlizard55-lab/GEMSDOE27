import numpy as np

from gems27 import links
from gems27.graph import build_graph, graph_summary
from gems27.thinning import dot_thin


def line_mask(shape, pts):
    from skimage.draw import line
    m = np.zeros(shape, bool)
    for (r0, c0), (r1, c1) in zip(pts[:-1], pts[1:]):
        rr, cc = line(r0, c0, r1, c1)
        m[rr, cc] = True
    return m


def test_graph_counts_simple_cross_and_isolated_segment():
    m = line_mask((80, 80), [(10, 40), (50, 40)])          # vertical
    m |= line_mask((80, 80), [(30, 20), (30, 60)])         # horizontal, crossing at (30, 40)
    m |= line_mask((80, 80), [(70, 10), (70, 25)])         # separate segment
    fg = build_graph(m)
    s = graph_summary(fg)
    assert s["components"] == 2
    assert s["end_nodes"] == 6 and s["junction_nodes"] == 1
    assert s["edges"] == 4 + 1          # 4 arms around the junction + the isolated segment


def test_collinear_gap_creates_one_forward_link_of_correct_length_and_none_when_rotated():
    m = line_mask((60, 120), [(30, 5), (30, 45)])           # left piece, tip at col 45
    m |= line_mask((60, 120), [(30, 65), (30, 110)])        # right piece, tip at col 65 (gap 20 px)
    fg = build_graph(m, with_edges=False)
    L = links.generate_links(fg, cone_deg=30, rmin=10, rmax=40)
    assert len(L) == 2                                      # one per facing tip
    assert set(np.round(L.length_px).astype(int)) == {20}
    assert L.mutual.all() and (L.kind == "end-to-end").all()
    assert np.all(L.strike.between(85, 95))                 # east-west strike
    Lc = links.generate_links(fg, cone_deg=30, rmin=10, rmax=40, rotate_deg=90)
    assert len(Lc) == 0                                     # control cone finds nothing across the gap


def test_links_ignore_same_system_and_too_short_or_too_long_gaps():
    m = line_mask((60, 200), [(30, 5), (30, 40)])
    m |= line_mask((60, 200), [(30, 44), (30, 80)])         # gap 4 px (< rmin)
    m |= line_mask((60, 200), [(30, 150), (30, 190)])       # gap 70 px from second piece (> rmax)
    fg = build_graph(m, with_edges=False)
    assert len(links.generate_links(fg, cone_deg=30, rmin=10, rmax=40)) == 0
    assert len(links.generate_links(fg, cone_deg=30, rmin=3, rmax=40)) == 2


def test_rasterised_dots_follow_spacing_and_skip_tips():
    m = line_mask((40, 100), [(20, 5), (20, 40)]) | line_mask((40, 100), [(20, 70), (20, 95)])
    fg = build_graph(m, with_edges=False)
    L = links.generate_links(fg, cone_deg=30, rmin=10, rmax=40)
    dots = links.rasterize_links(L.iloc[:1], m.shape, spacing=3)
    cols = np.sort(np.nonzero(dots)[1])
    assert len(cols) >= 8 and np.all(np.diff(cols) == 3)
    assert not dots[m].any()


def test_dot_thin_is_subset_deterministic_and_maximal():
    rng = np.random.default_rng(0)
    base = rng.random((60, 60)) < 0.15
    a = dot_thin(base, 2.8)
    b = dot_thin(base, 2.8)
    assert (a == b).all() and not (a & ~base).any()
    from scipy.ndimage import distance_transform_edt
    d = distance_transform_edt(~a)
    assert (d[base] < 2.8 + 1e-9).all()                    # every input pixel is within min_dist of a kept pixel
