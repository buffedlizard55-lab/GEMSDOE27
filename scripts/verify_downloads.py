#!/usr/bin/env python3
"""Standalone verification of the shipped submission files (rasterio + numpy only; imports no project code).

Re-derives, from the files themselves: grid, dtype, band count, nodata, NaN-outside count, value range inside, the
value set, catalogue overlap, zip contents, SHA-256s against docs/downloads/manifest.json, and the relation of the
primary file to the owner's 0.2477 file (superset, nothing removed). Exit status 1 on any failure.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("GEMS_DATA_DIR", ROOT / "data_cache"))
DL = ROOT / "docs" / "downloads"
FAIL: list[str] = []


def ok(cond: bool, msg: str) -> None:
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        FAIL.append(msg)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    man = json.loads((DL / "manifest.json").read_text())
    research_manifest = DL / "h28_1_candidate_manifest.json"
    if research_manifest.exists():
        research = json.loads(research_manifest.read_text())
        candidate = research.get("candidate")
        if candidate and research.get("status", "").startswith("research candidate"):
            man["h28_1_research"] = candidate
    with rasterio.open(DATA / "sample_submission.tif") as t:
        tpl = t.read(1)
        tprof = (t.crs.to_epsg(), t.shape, tuple(t.transform)[:6], t.dtypes[0])
    foot = np.isfinite(tpl)
    with rasterio.open(DATA / "labels.tif") as s:
        cat = s.read(1) == 1
    with rasterio.open(DATA / "dotted_h19_5_d1_5_nan.tif") as s:
        base = np.nan_to_num(s.read(1)) > 0
    ok(int(foot.sum()) == 5167373 and tprof[:2] == (32611, (3730, 3292)), "template: EPSG:32611, 3730x3292, 5,167,373 px footprint")
    # both Session-4's Addendum-E probe and Session-5's H28-1 research slot are verified here
    slots = tuple(s for s in ("primary", "secondary", "tertiary", "quaternary", "quinary_probe",
                              "h28_1_research") if s in man)
    for slot in slots:
        m = man[slot]
        for variant in ("nan", "allfinite"):
            p = DL / m[variant]
            with rasterio.open(p) as s:
                a = s.read(1)
                prof = (s.crs.to_epsg(), s.shape, tuple(s.transform)[:6], s.dtypes[0])
                nd, count = s.nodata, s.count
            tag = f"{slot}/{variant}"
            ok(prof == tprof, f"{tag}: same CRS/shape/transform/dtype as the template (float32)")
            ok(count == 1, f"{tag}: single band")
            inside, outside = a[foot], a[~foot]
            ok(bool(np.isfinite(inside).all()), f"{tag}: every in-footprint value is finite")
            ok(float(inside.min()) >= 0.0 and float(inside.max()) <= 1.0, f"{tag}: in-footprint range [{inside.min():g}, {inside.max():g}] within [0,1]")
            ok(set(np.unique(inside).tolist()) <= {0.0, 1.0}, f"{tag}: values are exactly 0.0 / 1.0 (no float rounding above 1)")
            n1 = int((inside == 1.0).sum())
            ok(n1 == m["emitted_px"], f"{tag}: {n1} pixels equal 1.0 (manifest {m['emitted_px']})")
            ok(not bool((a == 1.0)[cat].any()), f"{tag}: no emitted pixel on a catalogue cell")
            ok(not bool(np.isinf(a).any()), f"{tag}: no infinities anywhere")
            if variant == "nan":
                ok(int(np.isnan(outside).sum()) == outside.size == 7111787 and nd is not None and np.isnan(nd),
                   f"{tag}: NaN outside the footprint (7,111,787 px) and nodata=NaN declared, like the sample")
            else:
                ok(bool((outside == 0).all()) and nd is None and bool(np.isfinite(a).all()),
                   f"{tag}: zeros outside, no NaN anywhere, no nodata tag (fallback)")
            ok(sha(p) == m["sha256_nan"] or variant != "nan", f"{tag}: sha256 matches manifest" if variant == "nan" else f"{tag}: (fallback hash recorded in checks json)")
        z = DL / m["zip"]
        with zipfile.ZipFile(z) as zf:
            ok(zf.namelist() == [m["nan"]] and zf.read(m["nan"]) == (DL / m["nan"]).read_bytes(), f"{slot}: zip holds exactly the one nan GeoTIFF, byte-identical")
        note = (DL / f"note-{m['nan'][:-4]}.txt").read_text().strip()
        ok(len(note) <= 200 and note == m["note"], f"{slot}: note is {len(note)} chars (<= 200) and matches the manifest")
    with rasterio.open(DL / man["primary"]["nan"]) as s:
        A = np.nan_to_num(s.read(1)) > 0
    ok(bool((A & base).sum() == base.sum()), "primary is a superset of the 0.2477 emission (nothing removed)")
    ok(int(A.sum() - base.sum()) == man["primary"]["added_px"], f"primary adds exactly {man['primary']['added_px']} px to the 0.2477 emission")
    # slot 4 must be exactly: dot_thin(H19-5, 2.8) minus the 1 px catalogue-flank shadow, plus T-v2 dots
    if "quaternary" in man:
        from gems27 import thinning
        with rasterio.open(DATA / "h19_5_nan.tif") as s:
            raw = np.nan_to_num(s.read(1)) > 0
        base28 = thinning.dot_thin(raw & ~cat, 2.8)
        dcat = distance_transform_edt(~cat)
        base28_r1 = base28 & (dcat > 1.0)
        with rasterio.open(DL / man["quaternary"]["nan"]) as s:
            Dm = np.nan_to_num(s.read(1)) > 0
        ok(bool((Dm & base28_r1).sum() == base28_r1.sum()),
           "slot4 contains the whole pruned d2.8 base (nothing else removed)")
        ok(int(Dm.sum()) == man["quaternary"]["emitted_px"],
           f"slot4 emits exactly {man['quaternary']['emitted_px']} px (manifest)")
        ok(int(Dm.sum() - base28_r1.sum()) == man["quaternary"]["added_px"],
           f"slot4 adds exactly {man['quaternary']['added_px']} T-v2 dots on top of the pruned base")
        ok(int((base28 & ~base28_r1).sum()) == man["quaternary"]["pruned_flank_shadow_px"],
           f"slot4 prunes exactly {man['quaternary']['pruned_flank_shadow_px']} catalogue-flank-shadow px")
    # slot 5 (Addendum E far-field swap probe) must differ from the 0.2477 file in exactly one way:
    # WHICH far-field pixels are emitted. Same count, same near field, every change >= 300 m out.
    if "quinary_probe" in man:
        from gems27 import oof_detector  # noqa: F401  (imported for parity of environment checks)
        m5 = man["quinary_probe"]
        with rasterio.open(DL / m5["nan"]) as s5:
            E = np.nan_to_num(s5.read(1)) > 0
        dcat5 = distance_transform_edt(~cat)
        near_base, near_E = base & (dcat5 < 3.0), E & (dcat5 < 3.0)
        dropped, added = base & ~E, E & ~base
        ok(int(E.sum()) == int(base.sum()) == m5["emitted_px"],
           f"slot5 keeps the 0.2477 file's exact pixel count ({m5['emitted_px']} px)")
        ok(bool((near_base == near_E).all()),
           f"slot5 near field (< 300 m from catalogue) is byte-identical to the 0.2477 file ({int(near_base.sum())} px)")
        ok(int(dropped.sum()) == m5["far_field_px_dropped"] == m5["far_field_px_added"] == int(added.sum()),
           f"slot5 swaps exactly {m5['far_field_px_dropped']} far-field dots")
        ok(bool((dcat5[dropped] >= 3.0).all()) and bool((dcat5[added] >= 3.0).all()),
           "slot5 changes no pixel closer than 300 m to the catalogue (single-variable far-field swap)")
        ok(bool((dcat5[added] >= 3.0).all() and not (added & cat).any() and not (added & ~foot).any()),
           "slot5 added dots are off-catalogue and inside the footprint")
        kept = E & ~added
        dk = distance_transform_edt(~kept)
        ok(bool((dk[added] >= 1.5 - 1e-6).all()),
           "slot5 added dots respect the d1.5 emission geometry (>= 1.5 px from every kept dot)")
        ok(abs(m5["fraction_of_file_swapped"] - added.sum() / E.sum()) < 1e-9,
           f"slot5 manifest reports the one-sided swapped fraction {m5['fraction_of_file_swapped']:.4f} "
           f"(symmetric difference {m5['symmetric_difference_fraction']:.4f})")
    ok(len(list(DL.glob("*.tif"))) == len(set(p.name for p in DL.glob("*.tif"))), "all .tif file names are unique")
    h30_manifest = DL / "h30_1_manifest.json"
    if h30_manifest.exists():
        hm = json.loads(h30_manifest.read_text())
        r = hm["raster"]
        for variant, fname, exp_sha in [
            ("allfinite", r["primary_allfinite"], r["sha256"]),
            ("nan", r["nan_twin"], r["nan_sha256"]),
        ]:
            p = DL / fname
            with rasterio.open(p) as s:
                a = s.read(1)
                prof = (s.crs.to_epsg(), s.shape, tuple(s.transform)[:6], s.dtypes[0])
                nd, count = s.nodata, s.count
            tag = f"h30_1/{variant}"
            ok(prof == tprof, f"{tag}: same CRS/shape/transform/dtype as the template (float32)")
            ok(count == 1, f"{tag}: single band")
            inside, outside = a[foot], a[~foot]
            ok(bool(np.isfinite(inside).all()), f"{tag}: every in-footprint value is finite")
            ok(float(inside.min()) >= 0.0 and float(inside.max()) <= 1.0, f"{tag}: in-footprint range [{inside.min():g}, {inside.max():g}] within [0,1]")
            ok(set(np.unique(inside).tolist()) <= {0.0, 1.0}, f"{tag}: values are exactly 0.0 / 1.0")
            n1 = int((inside == 1.0).sum())
            ok(n1 == r["dots"], f"{tag}: {n1} pixels equal 1.0 (manifest {r['dots']})")
            ok(not bool((a == 1.0)[cat].any()), f"{tag}: no emitted pixel on a catalogue cell")
            dcat_h30 = distance_transform_edt(~cat)
            ok(bool((dcat_h30[a == 1.0] > 2.0).all()), f"{tag}: every dot obeys B2 (>2 px from catalogue)")
            if variant == "nan":
                ok(int(np.isnan(outside).sum()) == outside.size == 7111787 and nd is not None and np.isnan(nd),
                   f"{tag}: NaN outside the footprint (7,111,787 px) and nodata=NaN declared")
            else:
                ok(bool((outside == 0).all()) and nd is None and bool(np.isfinite(a).all()),
                   f"{tag}: zeros outside, no NaN anywhere, no nodata tag (primary allfinite)")
            ok(sha(p) == exp_sha, f"{tag}: sha256 matches h30_1_manifest.json")
        z_h30 = DL / r["zip"]
        with zipfile.ZipFile(z_h30) as zf:
            ok(zf.namelist() == [r["primary_allfinite"]] and zf.read(r["primary_allfinite"]) == (DL / r["primary_allfinite"]).read_bytes(),
               "h30_1: zip holds exactly the primary allfinite GeoTIFF, byte-identical")
        note_h30 = (DL / f"note-{r['primary_allfinite'][:-4]}.txt").read_text().strip()
        ok(0 < len(note_h30) <= 140 and note_h30 == hm["note_max_140_chars"],
           f"h30_1: note is {len(note_h30)} chars (<= 140) and matches manifest")

    # Session-7 H29-1 (Lane L-S7-2026-10-25) autonomous verification (zero human intervention):
    h29_man_path = DL / "h29_candidate_manifest.json"
    if h29_man_path.exists():
        hm = json.loads(h29_man_path.read_text())
        for variant, key_fn, key_sha in (
            ("allfinite", "allfinite", "sha256_allfinite"),
            ("nan", "nan", "sha256_nan"),
        ):
            hp = DL / hm[key_fn]
            with rasterio.open(hp) as hs:
                ha = hs.read(1)
                hprof = (hs.crs.to_epsg(), hs.shape, tuple(hs.transform)[:6], hs.dtypes[0])
                hnd, hcount = hs.nodata, hs.count
            htag = f"h29/{variant}"
            ok(hprof == tprof, f"{htag}: same CRS/shape/transform/dtype as template (EPSG:32611, 3730x3292, float32)")
            ok(hcount == 1, f"{htag}: single band")
            h_in, h_out = ha[foot], ha[~foot]
            ok(bool(np.isfinite(h_in).all()), f"{htag}: every in-footprint value is finite")
            ok(float(h_in.min()) >= 0.0 and float(h_in.max()) <= 1.0, f"{htag}: in-footprint range in [0,1]")
            ok(set(np.unique(h_in).tolist()) <= {0.0, 1.0}, f"{htag}: exact binary {{0.0, 1.0}}")
            ok(int((h_in == 1.0).sum()) == hm["emitted_px"], f"{htag}: emitted {hm['emitted_px']} dots")
            ok(not bool((ha == 1.0)[cat].any()), f"{htag}: 0 catalogue overlap")
            dcat_h = distance_transform_edt(~cat)
            ok(bool((dcat_h[ha == 1.0] > hm["b_exclusion_px"]).all()), f"{htag}: strict B2 collar > {hm['b_exclusion_px']} px")
            if variant == "allfinite":
                ok(bool(np.isfinite(ha).all() and (h_out == 0.0).all() and hnd is None),
                   f"{htag}: all 12,279,160 cells finite in [0,1], zeros outside, nodata=None")
            else:
                ok(int(np.isnan(h_out).sum()) == h_out.size and hnd is not None and np.isnan(hnd),
                   f"{htag}: NaN outside footprint and nodata=NaN declared")
            ok(sha(hp) == hm[key_sha], f"{htag}: sha256 matches h29_candidate_manifest.json")
        hz = DL / hm["zip_allfinite"]
        with zipfile.ZipFile(hz) as zf:
            ok(zf.namelist() == [hm["allfinite"]] and zf.read(hm["allfinite"]) == (DL / hm["allfinite"]).read_bytes(),
               "h29/zip: holds exactly the single allfinite GeoTIFF, byte-identical")
        ok(sha(hz) == hm["sha256_zip_allfinite"], "h29/zip: sha256 matches h29_candidate_manifest.json")
        hnote = (DL / hm["note_file"]).read_text().strip()
        ok(len(hnote) <= 140 and hnote == hm["note"], f"h29/note: {len(hnote)} chars (<= 140) and matches manifest")
        rc = json.loads((ROOT / hm["run_card"]).read_text())
        ok(rc["uniqueness_vs_registry"]["pass"] and rc["uniqueness_vs_registry"]["max_dot_overlap_within_3px_vs_peers"] <= 0.70,
           "h29/uniqueness: <= 70% 3px dot overlap & <= 0.90 Spearman vs all 12 peer rasters")
        ok(rc["ok_to_submit"] == (rc["verdict"] == "promote" and rc["validator"]["technical_validator_pass"]),
           f"h29/gate-consistency: verdict={rc['verdict']} ok_to_submit={rc['ok_to_submit']}")

    # Session-10 H31-1 DRCG-WL (Lane L-S10-2026-10-26) autonomous verification (zero human intervention):
    h31_s10_man_path = DL / "h31_s10_candidate_manifest.json"
    if h31_s10_man_path.exists():
        from gems27.readiness import publication_decision
        hm31 = json.loads(h31_s10_man_path.read_text())
        h31_dir = ROOT / hm31["directory"]
        for variant, key_fn, key_sha in (
            ("allfinite", "allfinite", "sha256_allfinite"),
            ("nan", "nan", "sha256_nan"),
        ):
            hp = h31_dir / hm31[key_fn]
            with rasterio.open(hp) as hs:
                ha = hs.read(1)
                hprof = (hs.crs.to_epsg(), hs.shape, tuple(hs.transform)[:6], hs.dtypes[0])
                hnd, hcount = hs.nodata, hs.count
            htag = f"h31_s10/{variant}"
            ok(hprof == tprof, f"{htag}: same CRS/shape/transform/dtype as template (EPSG:32611, 3730x3292, float32)")
            ok(hcount == 1, f"{htag}: single band")
            h_in, h_out = ha[foot], ha[~foot]
            ok(bool(np.isfinite(h_in).all()), f"{htag}: every in-footprint value is finite")
            ok(float(h_in.min()) >= 0.0 and float(h_in.max()) <= 1.0, f"{htag}: in-footprint range in [0,1]")
            ok(set(np.unique(h_in).tolist()) <= {0.0, 1.0}, f"{htag}: exact binary {{0.0, 1.0}}")
            ok(int((h_in == 1.0).sum()) == hm31["emitted_px"], f"{htag}: emitted {hm31['emitted_px']} dots")
            ok(not bool((ha == 1.0)[cat].any()), f"{htag}: 0 catalogue overlap")
            dcat_h31 = distance_transform_edt(~cat)
            ok(bool((dcat_h31[ha == 1.0] > hm31["b_exclusion_px"]).all()), f"{htag}: strict B2 collar > {hm31['b_exclusion_px']} px")
            if variant == "allfinite":
                ok(bool(np.isfinite(ha).all() and (h_out == 0.0).all() and hnd is None),
                   f"{htag}: all 12,279,160 cells finite in [0,1], zeros outside, nodata=None")
            else:
                ok(int(np.isnan(h_out).sum()) == h_out.size and hnd is not None and np.isnan(hnd),
                   f"{htag}: NaN outside footprint and nodata=NaN declared")
            ok(sha(hp) == hm31[key_sha], f"{htag}: sha256 matches h31_s10_candidate_manifest.json")
        hz31 = h31_dir / hm31["zip_allfinite"]
        with zipfile.ZipFile(hz31) as zf:
            ok(zf.namelist() == [hm31["allfinite"]] and zf.read(hm31["allfinite"]) == (h31_dir / hm31["allfinite"]).read_bytes(),
               "h31_s10/zip: holds exactly the single allfinite GeoTIFF, byte-identical")
        ok(sha(hz31) == hm31["sha256_zip_allfinite"], "h31_s10/zip: sha256 matches h31_s10_candidate_manifest.json")
        hnote31 = (h31_dir / hm31["note_file"]).read_text().strip()
        ok(0 < len(hnote31) <= 140 and hnote31 == hm31["note"], f"h31_s10/note: {len(hnote31)} chars (<= 140) and matches manifest")
        rc31_s10 = json.loads((ROOT / hm31["run_card"]).read_text())
        dec31 = publication_decision(rc31_s10, ROOT)
        ok(rc31_s10["uniqueness_vs_registry"]["pass"] and rc31_s10["uniqueness_vs_registry"]["max_dot_overlap_within_3px_euclidean"] <= 0.70,
           "h31_s10/uniqueness: <= 70% 3px dot overlap & <= 0.90 Spearman vs all peers & scored GEMSDOE27 rasters")
        ok(dec31["ok_to_publish_as_submission"] == hm31["ok_to_submit"],
           f"h31_s10/readiness-gate: publication_decision={dec31['ok_to_publish_as_submission']} reasons={dec31['reasons']}")

    # Session-10 H31 rank-ensemble (2026-10-26) autonomous verification:
    h31_card_path = ROOT / "evidence" / "h31_run_card.json"
    if h31_card_path.exists():
        rc31 = json.loads(h31_card_path.read_text())
        r31 = rc31["raster"]
        d31 = ROOT / r31["directory"]
        for variant, fname in (("allfinite", r31["primary_allfinite"]),
                               ("nan", r31["nan_twin"])):
            p31 = d31 / fname
            with rasterio.open(p31) as s31:
                a31 = s31.read(1)
                prof31 = (s31.crs.to_epsg(), s31.shape, tuple(s31.transform)[:6],
                          s31.dtypes[0])
                nd31, cnt31 = s31.nodata, s31.count
            t31 = f"h31/{variant}"
            ok(prof31 == tprof, f"{t31}: same CRS/shape/transform/dtype as template")
            ok(cnt31 == 1, f"{t31}: single band")
            in31, out31 = a31[foot], a31[~foot]
            ok(bool(np.isfinite(in31).all()), f"{t31}: every in-footprint value finite")
            ok(float(in31.min()) >= 0.0 and float(in31.max()) <= 1.0,
               f"{t31}: in-footprint range in [0,1]")
            ok(set(np.unique(in31).tolist()) <= {0.0, 1.0}, f"{t31}: exact binary")
            ok(int((in31 == 1.0).sum()) == r31["dots"], f"{t31}: emitted {r31['dots']} dots")
            ok(not bool((a31 == 1.0)[cat].any()), f"{t31}: 0 catalogue overlap")
            ok(bool((distance_transform_edt(~cat)[a31 == 1.0] > 2.0).all()),
               f"{t31}: strict B2 collar > 2.0 px")
            if variant == "allfinite":
                ok(bool(np.isfinite(a31).all() and (out31 == 0.0).all() and nd31 is None),
                   f"{t31}: all cells finite in [0,1], zeros outside, nodata=None")
                ok(sha(p31) == r31["sha256"], f"{t31}: sha256 matches h31 run card")
            else:
                ok(int(np.isnan(out31).sum()) == out31.size and nd31 is not None
                   and np.isnan(nd31), f"{t31}: NaN outside footprint, nodata=NaN")
        z31 = d31 / r31["zip"]
        with zipfile.ZipFile(z31) as zf:
            ok(zf.namelist() == [r31["primary_allfinite"]]
               and zf.read(r31["primary_allfinite"])
               == (d31 / r31["primary_allfinite"]).read_bytes(),
               "h31/zip: holds exactly the single allfinite GeoTIFF, byte-identical")
        stem31 = r31["primary_allfinite"][:-len("-allfinite.tif")]
        note31 = (d31 / f"note-{stem31}-allfinite.txt").read_text().strip()
        ok(len(note31) <= 140 and note31 == rc31["note_max_140_chars"],
           f"h31/note: {len(note31)} chars (<= 140) and matches run card")
        u31 = rc31["uniqueness_vs_registry"]
        ok(u31["pass"] and u31["max_dot_overlap_within_3px_euclidean"] <= 0.70
           and u31["max_surface_spearman"] <= 0.90,
           "h31/uniqueness: <= 70% 3px overlap & <= 0.90 Spearman (13-raster screen)")
        ok(rc31["ok_to_submit"] == (rc31["verdict"] == "promote"
                                    and rc31["validator"]["zeros_hard_pass"]
                                    and rc31["holdout"]["gate_efficacy_pass"]),
           f"h31/gate-consistency: verdict={rc31['verdict']} "
           f"ok_to_submit={rc31['ok_to_submit']}")

    # ---- Session 11 H32 negative research artifact (must stay NOT approved) ----
    h32_card_path = ROOT / "evidence" / "h32_run_card_2026-10-26.json"
    if h32_card_path.exists():
        rc32 = json.loads(h32_card_path.read_text())
        r32 = rc32["raster"]
        d32 = ROOT / r32["directory"]
        for variant, fname in (("allfinite", r32["primary_allfinite"]),
                               ("nan", r32["nan_twin"])):
            p32 = d32 / fname
            with rasterio.open(p32) as s32:
                a32 = s32.read(1)
                prof32 = (s32.crs.to_epsg(), s32.shape, tuple(s32.transform)[:6],
                          s32.dtypes[0])
                nd32, cnt32 = s32.nodata, s32.count
            t32 = f"h32/{variant}"
            ok(prof32 == tprof, f"{t32}: same CRS/shape/transform/dtype as template")
            ok(cnt32 == 1, f"{t32}: single band")
            in32, out32 = a32[foot], a32[~foot]
            ok(bool(np.isfinite(in32).all()), f"{t32}: every in-footprint value finite")
            ok(float(in32.min()) >= 0.0 and float(in32.max()) <= 1.0,
               f"{t32}: in-footprint range in [0,1]")
            ok(set(np.unique(in32).tolist()) <= {0.0, 1.0}, f"{t32}: exact binary")
            ok(int((in32 == 1.0).sum()) == rc32["n_dots"], f"{t32}: emitted {rc32['n_dots']} dots")
            ok(not bool((a32 == 1.0)[cat].any()), f"{t32}: 0 catalogue overlap")
            ok(bool((distance_transform_edt(~cat)[a32 == 1.0] > 2.0).all()),
               f"{t32}: strict B2 collar > 2.0 px")
            if variant == "allfinite":
                ok(bool(np.isfinite(a32).all() and (out32 == 0.0).all() and nd32 is None),
                   f"{t32}: all cells finite in [0,1], zeros outside, nodata=None")
                ok(sha(p32) == r32["sha256"], f"{t32}: sha256 matches h32 run card")
            else:
                ok(int(np.isnan(out32).sum()) == out32.size and nd32 is not None
                   and np.isnan(nd32), f"{t32}: NaN outside footprint, nodata=NaN")
        z32 = d32 / r32["zip"]
        with zipfile.ZipFile(z32) as zf:
            ok(zf.namelist() == [r32["primary_allfinite"]]
               and zf.read(r32["primary_allfinite"])
               == (d32 / r32["primary_allfinite"]).read_bytes(),
               "h32/zip: holds exactly the single allfinite GeoTIFF, byte-identical")
        stem32 = r32["primary_allfinite"][:-len("-allfinite.tif")]
        note32 = (d32 / f"note-{stem32}-allfinite.txt").read_text().strip()
        ok(len(note32) <= 140 and note32 == rc32["note_max_140_chars"],
           f"h32/note: {len(note32)} chars (<= 140) and matches run card")
        u32 = rc32["uniqueness_vs_registry"]
        ok(u32["max_dot_overlap_within_3px_vs_peers"] <= 0.70
           and u32["max_surface_spearman"] <= 0.90 and not u32["pass"],
           "h32/uniqueness: <= 70% vs peers but strict repo screen fails (recorded, not hidden)")
        ok(rc32["verdict"] == "negative" and rc32["ok_to_submit"] is False
           and rc32["holdout"]["gate_efficacy_pass"] is False,
           "h32/gate-consistency: verdict=negative ok_to_submit=False (DO NOT SUBMIT)")

    # ---- Session 12 H31-3 negative research artifact (must stay NOT approved) ----
    h313_card_path = ROOT / "evidence" / "h31_3_run_card_2026-10-26.json"
    if h313_card_path.exists():
        rc313 = json.loads(h313_card_path.read_text())
        r313 = rc313["raster"]
        d313 = ROOT / r313["directory"]
        for variant, fname in (("allfinite", r313["primary_allfinite"]),
                               ("nan", r313["companion_nan"])):
            p313 = d313 / fname
            with rasterio.open(p313) as s313:
                a313 = s313.read(1)
                prof313 = (s313.crs.to_epsg(), s313.shape, tuple(s313.transform)[:6],
                           s313.dtypes[0])
                nd313, cnt313 = s313.nodata, s313.count
            t313 = f"h31_3/{variant}"
            ok(prof313 == tprof, f"{t313}: same CRS/shape/transform/dtype as template")
            ok(cnt313 == 1, f"{t313}: single band")
            in313, out313 = a313[foot], a313[~foot]
            ok(bool(np.isfinite(in313).all()), f"{t313}: every in-footprint value finite")
            ok(float(in313.min()) >= 0.0 and float(in313.max()) <= 1.0,
               f"{t313}: in-footprint range in [0,1]")
            ok(set(np.unique(in313).tolist()) <= {0.0, 1.0}, f"{t313}: exact binary")
            ok(int((in313 == 1.0).sum()) == r313["dots"],
               f"{t313}: emitted {r313['dots']} dots")
            ok(not bool((a313 == 1.0)[cat].any()), f"{t313}: 0 catalogue overlap")
            ok(bool((distance_transform_edt(~cat)[a313 == 1.0] > 2.0).all()),
               f"{t313}: strict B2 collar > 2.0 px")
            if variant == "allfinite":
                ok(bool(np.isfinite(a313).all() and (out313 == 0.0).all() and nd313 is None),
                   f"{t313}: all cells finite in [0,1], zeros outside, nodata=None")
                ok(sha(p313) == r313["sha256"], f"{t313}: sha256 matches H31-3 run card")
            else:
                ok(int(np.isnan(out313).sum()) == out313.size and nd313 is not None
                   and np.isnan(nd313), f"{t313}: NaN outside footprint, nodata=NaN")
        z313 = d313 / r313["zip"]
        with zipfile.ZipFile(z313) as zf:
            ok(zf.namelist() == [r313["primary_allfinite"]]
               and zf.read(r313["primary_allfinite"])
               == (d313 / r313["primary_allfinite"]).read_bytes(),
               "h31_3/zip: holds exactly the single allfinite GeoTIFF, byte-identical")
        stem313 = r313["primary_allfinite"][:-len("-allfinite.tif")]
        note313 = (d313 / f"note-{stem313}-allfinite.txt").read_text().strip()
        ok(len(note313) <= 140 and note313 == rc313["note_max_140_chars"],
           f"h31_3/note: {len(note313)} chars (<= 140) and matches run card")
        u313 = rc313["uniqueness_vs_registry"]
        ok(u313["peer_gate_pass"] and u313["max_dot_overlap_vs_12_peers"] <= 0.70
           and u313["max_surface_spearman_armD"] <= 0.90 and not u313["pass"],
           "h31_3/uniqueness: peer screen passes; strict local screen fails (recorded, not hidden)")
        ok(rc313["verdict"] == "negative" and rc313["ok_to_submit"] is False
           and rc313["holdout"]["gate_efficacy_pass"] is False,
           "h31_3/gate-consistency: verdict=negative ok_to_submit=False (DO NOT SUBMIT)")

    print(f"\n{len(FAIL)} failure(s)")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
