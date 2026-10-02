"""Fault graph of the catalogue: nodes = endpoints and junctions, edges = mapped segments.

The catalogue raster is skeletonised to one-pixel lines. Free line ends become `end` nodes; each
connected cluster of branch pixels (>= 3 neighbours) becomes one `junction` node; every pixel chain
between nodes becomes one edge carrying its length. Connected components of the graph are the
mapped fault *systems* at 100 m resolution. Nothing here reads predictions or scores.

Note on provenance: the competition labels are a raster, so the graph inherits the rasterisation
(100 m cells, 8-connectivity). Vector geometry and attributes (names, slip sense, dip direction)
exist upstream (INGENIOUS / USGS Qfaults) but were not obtainable from this sandbox; see
knowledge/06_limitations_and_access.md.
"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
import numpy as np
import pandas as pd
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

ST8 = np.ones((3, 3), int)
K8 = np.ones((3, 3), int)
K8[1, 1] = 0
_OFFS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
TANGENT_STEPS = 8   # 800 m of chain used to define an end tangent
MIN_TANGENT_LAYERS = 4


@dataclass
class FaultGraph:
    skeleton: np.ndarray            # bool (H, W)
    comp: np.ndarray                # int32 (H, W), component id per skeleton pixel (0 = none)
    comp_length_px: np.ndarray      # float, index = component id (0 unused), skeleton length in px
    nodes: pd.DataFrame             # node_id, kind, row, col, comp, degree
    edges: pd.DataFrame             # edge_id, u, v, length_px, comp
    endpoints: pd.DataFrame         # row, col, comp, ty, tx (unit outward tangent), layers
    graph: nx.MultiGraph

    @property
    def n_components(self) -> int:
        return int(self.comp.max())


def skeleton_length_by_component(sk: np.ndarray, comp: np.ndarray, n: int) -> np.ndarray:
    """Chain length in pixel units (orthogonal step 1, diagonal sqrt 2), per component."""
    length = np.zeros(n + 1)
    r2 = np.sqrt(2.0)
    for dy, dx, w in ((0, 1, 1.0), (1, 0, 1.0), (1, 1, r2), (1, -1, r2)):
        a = sk[: sk.shape[0] - dy, max(0, -dx): sk.shape[1] - max(0, dx)]
        b = sk[dy:, max(0, dx): sk.shape[1] - max(0, -dx)]
        ca = comp[: sk.shape[0] - dy, max(0, -dx): sk.shape[1] - max(0, dx)]
        both = a & b
        length += np.bincount(ca[both], minlength=n + 1) * w
    # a single isolated pixel has no pairs; give it unit length so it is not zero
    sizes = np.bincount(comp[sk], minlength=n + 1)
    length = np.where((length == 0) & (sizes > 0), 1.0, length)
    return length


def _end_tangents(sk: np.ndarray, ey: np.ndarray, ex: np.ndarray, comp: np.ndarray) -> pd.DataFrame:
    H, W = sk.shape
    rows = []
    for y, x in zip(ey.tolist(), ex.tolist()):
        seen = {(y, x)}
        frontier = [(y, x)]
        layers = [[(y, x)]]
        for _ in range(TANGENT_STEPS):
            nxt = []
            for a, b in frontier:
                for da, db in _OFFS:
                    q = (a + da, b + db)
                    if 0 <= q[0] < H and 0 <= q[1] < W and sk[q] and q not in seen:
                        seen.add(q)
                        nxt.append(q)
            if not nxt:
                break
            layers.append(nxt)
            frontier = nxt
        n_layers = len(layers)
        if n_layers < MIN_TANGENT_LAYERS:
            rows.append((y, x, int(comp[y, x]), np.nan, np.nan, n_layers))
            continue
        far = np.asarray(layers[-1], float).mean(axis=0)
        v = np.array([y, x], float) - far
        n = float(np.hypot(*v))
        if n == 0:
            rows.append((y, x, int(comp[y, x]), np.nan, np.nan, n_layers))
        else:
            rows.append((y, x, int(comp[y, x]), v[0] / n, v[1] / n, n_layers))
    return pd.DataFrame(rows, columns=["row", "col", "comp", "ty", "tx", "layers"])


def build_graph(mask: np.ndarray, with_edges: bool = True) -> FaultGraph:
    """Skeleton, components and end tangents; `with_edges=False` skips the node/edge tables (fast)."""
    mask = np.asarray(mask, bool)
    sk = skeletonize(mask)
    comp, n_comp = ndi.label(sk, structure=ST8)
    comp = comp.astype(np.int32)
    nb = ndi.convolve(sk.astype(np.int16), K8, mode="constant")
    end_pix = sk & (nb == 1)
    if not with_edges:
        lens = skeleton_length_by_component(sk, comp, n_comp)
        tang = _end_tangents(sk, *np.nonzero(end_pix), comp)
        empty_n = pd.DataFrame(columns=["node_id", "kind", "row", "col", "comp", "degree"])
        empty_e = pd.DataFrame(columns=["edge_id", "u", "v", "length_px", "comp"])
        return FaultGraph(sk, comp, lens, empty_n, empty_e, tang, nx.MultiGraph())
    iso_pix = sk & (nb == 0)
    jun_pix = sk & (nb >= 3)
    jlab, n_j = ndi.label(jun_pix, structure=ST8)
    chain_pix = sk & ~jun_pix
    clab, n_c = ndi.label(chain_pix, structure=ST8)

    nodes: list[tuple] = []
    G = nx.MultiGraph()
    # junction nodes (centroid, summed neighbour count, component via the cluster's first pixel)
    jn_id: dict[int, int] = {}
    if n_j:
        jobjs = ndi.find_objects(jlab)
        for j in range(1, n_j + 1):
            sl = jobjs[j - 1]
            ys, xs = np.nonzero(jlab[sl] == j)
            ys = ys + sl[0].start
            xs = xs + sl[1].start
            nid = len(nodes)
            jn_id[j] = nid
            nodes.append((nid, "junction", int(round(ys.mean())), int(round(xs.mean())),
                          int(comp[ys[0], xs[0]]), int(nb[ys, xs].sum())))
    # endpoint / isolated-pixel nodes
    ey, ex = np.nonzero(end_pix | iso_pix)
    en_id: dict[tuple[int, int], int] = {}
    for y, x in zip(ey.tolist(), ex.tolist()):
        nid = len(nodes)
        en_id[(y, x)] = nid
        nodes.append((nid, "end", y, x, int(comp[y, x]), int(nb[y, x])))
    # edges: one per pixel chain
    edge_rows = []
    if n_c:
        objs = ndi.find_objects(clab)
        for c in range(1, n_c + 1):
            sl = objs[c - 1]
            sub = clab[sl] == c
            ys, xs = np.nonzero(sub)
            ys += sl[0].start
            xs += sl[1].start
            pts = set(zip(ys.tolist(), xs.tolist()))
            ends = []
            for (y, x) in pts:
                k = sum(((y + a, x + b) in pts) for a, b in _OFFS)
                if k <= 1:
                    ends.append((y, x))
            if not ends:        # closed ring without branch pixels
                ends = [next(iter(pts))]
            ends = ends[:2] if len(ends) > 2 else ends
            # Terminals: for every chain end, any adjacent junction cluster(s) and, if the end pixel is itself a
            # free tip, its tip node. A 1-px stub on a junction therefore gets BOTH (junction, tip) - recording only
            # the junction would turn it into a spurious self-loop and inflate the cyclomatic number.
            terminals: list[int] = []
            for (y, x) in ends:
                hits = []
                for a_, b_ in _OFFS:
                    yy_, xx_ = y + a_, x + b_
                    if 0 <= yy_ < mask.shape[0] and 0 <= xx_ < mask.shape[1] and jlab[yy_, xx_]:
                        hits.append(jn_id[int(jlab[yy_, xx_])])
                for h in dict.fromkeys(hits):
                    if h not in terminals or len(ends) == 1:
                        terminals.append(h)
                if (y, x) in en_id:
                    terminals.append(en_id[(y, x)])
            terminals = list(dict.fromkeys(terminals)) if len(ends) == 1 else terminals
            u = terminals[0] if terminals else -1
            v = terminals[1] if len(terminals) > 1 else (terminals[0] if terminals else -1)
            L = float(len(pts))
            ci = int(comp[ys[0], xs[0]])
            edge_rows.append((len(edge_rows), u, v, L, ci))
    nodes_df = pd.DataFrame(nodes, columns=["node_id", "kind", "row", "col", "comp", "degree"])
    edges_df = pd.DataFrame(edge_rows, columns=["edge_id", "u", "v", "length_px", "comp"])
    for r in nodes_df.itertuples(index=False):
        G.add_node(r.node_id, kind=r.kind, row=r.row, col=r.col, comp=r.comp)
    for r in edges_df.itertuples(index=False):
        if r.u >= 0:
            G.add_edge(r.u, r.v, key=r.edge_id, length_px=r.length_px)
    lens = skeleton_length_by_component(sk, comp, n_comp)
    tang = _end_tangents(sk, *np.nonzero(end_pix), comp)
    return FaultGraph(sk, comp, lens, nodes_df, edges_df, tang, G)


def graph_summary(fg: FaultGraph) -> dict:
    """Counts for documentation (all at 100 m / 8-connectivity).

    Loops: at 100 m, pixel-scale loops around thick junction clusters dominate any raw cycle count, so three views are
    reported: the raw graph cyclomatic number, the same after dropping self-loops of <= 3 px, and the number of enclosed
    background regions of >= 20 px (a robust Euler-type count of genuinely closed fault polygons).
    """
    n_end = int((fg.nodes.kind == "end").sum())
    n_jun = int((fg.nodes.kind == "junction").sum())
    n_edge = int(len(fg.edges))
    comps = fg.n_components
    lens_km = fg.comp_length_px[1:] * 0.1
    raw = int(fg.graph.number_of_edges() - fg.graph.number_of_nodes() + nx.number_connected_components(fg.graph))
    g2 = nx.MultiGraph()
    g2.add_nodes_from(fg.graph.nodes)
    for r in fg.edges.itertuples(index=False):
        if r.u >= 0 and not (r.u == r.v and r.length_px <= 3):
            g2.add_edge(r.u, r.v)
    cyc = int(g2.number_of_edges() - g2.number_of_nodes() + nx.number_connected_components(g2))
    bg, nb = ndi.label(~fg.skeleton, structure=ndi.generate_binary_structure(2, 1))
    border = set(np.unique(np.r_[bg[0], bg[-1], bg[:, 0], bg[:, -1]]).tolist())
    sizes = np.bincount(bg.ravel(), minlength=nb + 1)
    enclosed = [i for i in range(1, nb + 1) if i not in border]
    return {
        "skeleton_px": int(fg.skeleton.sum()),
        "components": comps,
        "end_nodes": n_end,
        "junction_nodes": n_jun,
        "edges": n_edge,
        "cyclomatic_number_raw": raw,
        "cyclomatic_number": cyc,
        "enclosed_regions_all": len(enclosed),
        "enclosed_regions_ge_20px": int(sum(sizes[i] >= 20 for i in enclosed)),
        "self_loop_edges_le_3px": int(((fg.edges.u == fg.edges.v) & (fg.edges.length_px <= 3)).sum()),
        "endpoints_with_tangent": int(fg.endpoints.ty.notna().sum()),
        "component_length_km": {
            "median": float(np.median(lens_km)), "p90": float(np.percentile(lens_km, 90)),
            "p99": float(np.percentile(lens_km, 99)), "max": float(lens_km.max()),
            "sum": float(lens_km.sum()),
        },
        "components_ge_10km": int((lens_km >= 10).sum()),
        "components_lt_2km": int((lens_km < 2).sum()),
    }
