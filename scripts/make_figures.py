#!/usr/bin/env python3
"""Figures for the site (docs/assets/*.png) from the evidence JSON files and the candidate registry."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems27 import grid, links, paths  # noqa: E402

A = paths.DOCS / "assets"
INK, BLUE, RED, GREY, GREEN = "#1b2733", "#1f6feb", "#d1242f", "#8c959f", "#1a7f37"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": INK, "axes.labelcolor": INK, "xtick.color": INK,
                     "ytick.color": INK, "axes.spines.top": False, "axes.spines.right": False})


def plain(ax, ticks):
    """Explicit plain-number ticks on a log x axis (no overlapping minor labels)."""
    from matplotlib.ticker import FixedLocator, FormatStrFormatter, NullLocator
    ax.xaxis.set_major_locator(FixedLocator(ticks))
    ax.xaxis.set_major_formatter(FormatStrFormatter("%g"))
    ax.xaxis.set_minor_locator(NullLocator())


def fig_connectivity():
    g = json.loads((paths.EVIDENCE / "graph_report.json").read_text())
    fd = g["figure_data"]
    lens = np.array(fd["lengths_km"])
    fig, ax = plt.subplots(1, 3, figsize=(12.5, 3.6))
    srt = np.sort(lens)
    ccdf = 1.0 - np.arange(len(srt)) / len(srt)
    ax[0].loglog(srt, ccdf, ".", ms=3, color=BLUE)
    b = g["berkowitz_style_estimate"]
    x = np.geomspace(2, 45, 50)
    ccdf_at = lambda v: float(np.mean(lens >= v))  # noqa: E731
    ax[0].loglog(x, ccdf_at(2) * (x / 2) ** (1 - b["a"]), "-", color=RED, lw=1.5, label=f"a = {b['a']:.2f} (lmin 2 km)")
    ax[0].set_xlabel("mapped system length l (km)"); ax[0].set_ylabel("P(L ≥ l)")
    plain(ax[0], [0.1, 0.3, 1, 3, 10, 30])
    ax[0].set_title("Length distribution of mapped systems", fontsize=9)
    ax[0].legend(frameon=False)
    r = np.array(fd["c2_r_m"]) / 1e3
    c2 = np.array(fd["c2"])
    ax[1].loglog(r, c2, "o", color=BLUE, ms=4)
    ax[1].loglog(r, c2[0] * (r / r[0]) ** b["D"], "-", color=RED, label=f"D = {b['D']:.2f}")
    ax[1].set_xlabel("distance r (km)"); ax[1].set_ylabel("C2(r)")
    plain(ax[1], [5, 10, 20, 40])
    ax[1].set_title("Correlation integral of system centres", fontsize=9)
    ax[1].legend(frameon=False)
    sl = g["single_linkage"]
    rk = [s["radius_km"] for s in sl]
    share = [100 * s["largest_share"] for s in sl]
    nsys = [s["systems"] for s in sl]
    ax[2].semilogx(rk, share, "o-", color=BLUE, ms=4)
    ax[2].axvspan(1.0, 4.0, color=RED, alpha=0.12, lw=0)
    ax[2].set_xlabel("closure radius (km)"); ax[2].set_ylabel("largest system, % of fault length", color=BLUE)
    plain(ax[2], [0.15, 0.3, 0.6, 1, 2, 4, 8])
    a2 = ax[2].twinx()
    a2.semilogx(rk, nsys, "s--", color=GREY, ms=3)
    a2.set_ylabel("number of systems", color=GREY)
    a2.spines["right"].set_visible(True)
    a2.xaxis.set_minor_locator(__import__("matplotlib.ticker", fromlist=["NullLocator"]).NullLocator())
    ax[2].set_title("Single-linkage connectivity (shaded: 1–4 km link range)", fontsize=9)
    fig.tight_layout(); fig.savefig(A / "fig_connectivity.png", dpi=130); plt.close(fig)


def fig_validation():
    c = json.loads((paths.EVIDENCE / "topology_confirmation_v2.json").read_text())
    e = c["efficiency_pooled"]
    items = [("rotated-cone\ncontrols", c["control_pooled"], GREY), ("random same-size\nsubsets (mean)", c["random_same_size"]["mean"], GREY),
             ("all forward\nlinks (T-v1)", e["all"], BLUE), ("z ≥ 2", e["z>=2"], BLUE), ("z ≥ 3", e["z>=3"], BLUE),
             ("z ≥ 3, mutual\npairs de-duplicated\n(shipped)", e["z>=3 dedup"], GREEN), ("z ≥ 4", e["z>=4"], BLUE)]
    fig, ax = plt.subplots(figsize=(8.2, 3.9))
    ax.bar(range(len(items)), [i[1] for i in items], color=[i[2] for i in items])
    for i, it in enumerate(items):
        ax.text(i, it[1] + 0.006, f"{it[1]:.3f}", ha="center", fontsize=8)
    ax.axhline(c["inclusion_threshold"]["dti_0.25"], color=RED, ls="--", lw=1,
               label=f"break-even efficiency at DTI 0.25 ({c['inclusion_threshold']['dti_0.25']:.3f})")
    ax.axhline(c["inclusion_threshold"]["dti_0.30"], color=RED, ls=":", lw=1,
               label=f"break-even efficiency at DTI 0.30 ({c['inclusion_threshold']['dti_0.30']:.3f})")
    ax.legend(loc="upper left", frameon=False, fontsize=8)
    ax.set_xticks(range(len(items))); ax.set_xticklabels([i[0] for i in items], fontsize=7.5)
    ax.set_ylabel("efficiency  ΔTP_w / ΔFP_w  (hidden catalogue pieces)")
    ax.set_title("Confirmatory holdout, seeds 110–119 (40 cells): efficiency of added dots (empty base)", fontsize=9)
    fig.tight_layout(); fig.savefig(A / "fig_validation.png", dpi=130); plt.close(fig)


def load_mask(p):
    with rasterio.open(p) as s:
        return np.nan_to_num(s.read(1)) > 0


def fig_map_and_examples():
    foot = grid.load_footprint(paths.TEMPLATE)
    labels = grid.load_labels(paths.LABELS)
    base = load_mask(paths.DOTTED_0_2477)
    reg = json.loads((paths.REGISTRY / "topology_candidates.json").read_text())["links"]
    H, W = labels.shape
    fig, ax = plt.subplots(figsize=(8.2, 9.2))
    fy, fx = np.nonzero(foot[::8, ::8])
    ax.scatter(fx * 8, fy * 8, s=0.2, c="#eef1f4", marker="s", linewidths=0)
    ly, lx = np.nonzero(labels)
    ax.scatter(lx, ly, s=0.35, c=INK, linewidths=0, label="catalogue (INGENIOUS/USGS), 60,988 px")
    for r in reg:
        ax.plot([r["e_col"], r["q_col"]], [r["e_row"], r["q_row"]], "-", color=RED, lw=1.1, alpha=0.9)
    ax.plot([], [], "-", color=RED, label=f"{len(reg)} candidate gap links (z ≥ 3)")
    ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([]); ax.legend(loc="lower left", frameon=True, fontsize=8)
    ax.set_title("GeoDAWN footprint, 329 × 373 km (100 m pixels): catalogue and topology candidates", fontsize=9)
    fig.tight_layout(); fig.savefig(A / "fig_map_overview.png", dpi=125); plt.close(fig)

    # examples: strongly supported, long, little base coverage, spread over the footprint
    cand = [r for r in reg if r["z"] >= 4 and r["gap_km"] >= 2.0 and r["base_overlap"] <= 0.2]
    cand.sort(key=lambda r: (-r["z"], -r["gap_km"]))
    chosen = []
    for r in cand:
        mid = np.array([(r["e_row"] + r["q_row"]) / 2, (r["e_col"] + r["q_col"]) / 2])
        if all(np.hypot(*(mid - m)) > 400 for m in chosen):
            chosen.append(mid)
            if len(chosen) == 6:
                break
    sel = []
    for m in chosen:
        sel.append(min(cand, key=lambda r: np.hypot((r["e_row"] + r["q_row"]) / 2 - m[0], (r["e_col"] + r["q_col"]) / 2 - m[1])))
    fig, axs = plt.subplots(2, 3, figsize=(11.5, 7.8))
    for a, r in zip(axs.ravel(), sel):
        cr, cc = int((r["e_row"] + r["q_row"]) / 2), int((r["e_col"] + r["q_col"]) / 2)
        h = 60
        r0, r1, c0, c1 = max(cr - h, 0), min(cr + h, H), max(cc - h, 0), min(cc + h, W)
        img = np.ones((r1 - r0, c1 - c0, 3))
        img[ndi.binary_dilation(labels[r0:r1, c0:c1], iterations=0) & labels[r0:r1, c0:c1]] = (0.11, 0.15, 0.2)
        b = base[r0:r1, c0:c1]
        by, bx = np.nonzero(b)
        a.imshow(img, extent=(c0, c1, r1, r0), interpolation="nearest")
        a.scatter(bx + c0 + 0.5, by + r0 + 0.5, s=9, c=BLUE, marker="s", linewidths=0, label="0.2477 emission")
        one = links.rasterize_links(__import__("pandas").DataFrame([{"e_row": r["e_row"], "e_col": r["e_col"], "q_row": r["q_row"],
                                                                      "q_col": r["q_col"]}]), labels.shape, 3)[r0:r1, c0:c1]
        dy, dx = np.nonzero(one)
        a.scatter(dx + c0 + 0.5, dy + r0 + 0.5, s=16, c=RED, marker="o", linewidths=0, label="link dots")
        a.plot([r["e_col"], r["q_col"]], [r["e_row"], r["q_row"]], "--", color=RED, lw=0.7)
        a.set_title(f"{r['link_id']}  z={r['z']}  gap {r['gap_km']:.1f} km  compat {100 * r['strike_compat']:.0f}%  base-overlap {100 * r['base_overlap']:.0f}%", fontsize=7.5)
        a.set_xticks([]); a.set_yticks([])
    axs.ravel()[0].legend(fontsize=7, loc="lower left")
    fig.suptitle("Examples: gaps closed by the shipped candidate set (dark = mapped catalogue, 12 × 12 km windows)", fontsize=9)
    fig.tight_layout(); fig.savefig(A / "fig_examples.png", dpi=120); plt.close(fig)
    (paths.EVIDENCE / "example_links.json").write_text(json.dumps([r["link_id"] for r in sel]))


def main() -> int:
    A.mkdir(parents=True, exist_ok=True)
    fig_connectivity(); print("connectivity ok")
    fig_validation(); print("validation ok")
    fig_map_and_examples(); print("map+examples ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
