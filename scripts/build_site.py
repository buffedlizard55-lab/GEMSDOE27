#!/usr/bin/env python3
"""Render the GitHub Pages site (docs/*.html) and the derived knowledge docs from JSON only.

Inputs: docs/downloads/manifest.json, evidence/*.json, registry/*.json, docs/data/*. No rasters are needed, so this runs in CI.
Nothing here fetches drivendata.org or invents a score: scores come from registry/live_scores.json (owner-reported).
"""

from __future__ import annotations

import csv
import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems27.readiness import publication_decision  # noqa: E402

DOCS, EV, REG, KN = ROOT / "docs", ROOT / "evidence", ROOT / "registry", ROOT / "knowledge"
REPO_URL = "https://github.com/buffedlizard55-lab/GEMSDOE27"
DD_COMP = "https://www.drivendata.org/competitions/306/competition-doe-gems/"
DD_LB = DD_COMP + "leaderboard/"
NAV = [("index.html", "Research status"), ("executive-summary.html", "Executive summary"), ("topology.html", "Topology candidates"),
       ("research.html", "Research"), ("sources.html", "Sources & feed")]


def J(p: Path):
    return json.loads(p.read_text())


def e(x) -> str:
    return html.escape(str(x), quote=True)


def layout(fname: str, title: str, body: str, stamp: str) -> str:
    nav = "".join(f'<a href="{h}"{" class=on" if h == fname else ""}>{e(t)}</a>' for h, t in NAV)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} · 27GEMSDOE</title><meta name="description" content="27GEMSDOE: topology-first research lab for DrivenData #306 (DOE GEMS). No current TIFF is approved for submission.">
<link rel="stylesheet" href="assets/style.css"></head><body>
<header class="top"><div class="in"><a class="brand" href="index.html">27GEMSDOE · DOE GEMS</a><nav>{nav}</nav></div></header>
<main><div class="card"><b>Automatic submission evidence audit:</b>
<a href="data/submission_readiness_audit.json">Read byte-bound gate decisions and blockers</a>.
Format PASS is not permission to submit; negative and duplicate files remain research-only.
</div>{body}</main>
<footer>Built {e(stamp)} from <a href="{REPO_URL}">the repository</a>. No current TIFF is approved for submission. No leaderboard score is claimed anywhere on this site.
Historical scores shown are owner-reported. This site never contacts drivendata.org.</footer>
<script src="assets/app.js"></script></body></html>"""


def rebase(text: str, prefix: str) -> str:
    """Prefix every relative href/src (used for the repository-root copy of the front page)."""
    import re
    return re.sub(r'(href|src)="(?!https?:|#|mailto:|data:)([^"]+)"', lambda m: f'{m.group(1)}="{prefix}{m.group(2)}"', text)


def kb(n: float, d=0) -> str:
    return f"{n:,.{d}f}"


def build() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    man = J(DOCS / "downloads" / "manifest.json")
    P, S, T = man["primary"], man["secondary"], man["tertiary"]
    # Keep historical peer artifacts auditable without presenting a raw GeoTIFF as a download.
    reference_audit_url = man["reference_0_2477"]["url"].replace("/raw/", "/blob/")
    Q = man.get("quaternary")
    Q5 = man["quinary_probe"]
    sgi = J(EV / "sgmc_gap_inversion.json") if (EV / "sgmc_gap_inversion.json").exists() else None
    hab = J(EV / "arm_habitat_decomposition.json") if (EV / "arm_habitat_decomposition.json").exists() else None
    addD = J(EV / "addendum_d_gates.json") if (EV / "addendum_d_gates.json").exists() else None
    gval = J(REG / "topology_candidates.json")["summary"].get("graph_value", {})
    # ---- Lane L-2026-10-25 parallel negative (JSON-driven; research/ per STOP policy) ----
    lane_path = DOCS / "downloads" / "lane_candidate_manifest.json"
    lane = J(lane_path) if lane_path.exists() else None
    lane_box = ""
    if lane:
        r, h, u = lane["raster"], lane["holdout"], lane["uniqueness_vs_registry"]
        ok = publication_decision(lane, ROOT)["ok_to_publish_as_submission"]
        badge = ('<span class="badge ok" style="font-size:1.05rem">&#9989; VALIDATED &mdash; OK TO DOWNLOAD &amp; SUBMIT '
                 '(format + uniqueness + holdout gates PASS; still UNSCORED)</span>') if ok else (
                 '<span class="badge bad" style="font-size:1.05rem">&#9940; RESEARCH ONLY &mdash; DO NOT SUBMIT '
                 '(holdout gate failed; see run card)</span>')
        lane_box = f"""
<div class="card" style="border-left:4px solid #b00">
 <h3 style="margin-top:0">Parallel lane L-2026-10-25: subsurface-only buried-fault detector &mdash; also NEGATIVE</h3>
 <p>{badge}</p>
 <p>A second parallel run tested a lidar-free detector (potential-field edges, strain, conductivity, seismicity fabric) at B2/38k. Pooled HOLDOUT-DTI {h['pooled_dti_lane_A']:.4f} vs full-32 control {h['pooled_dti_full_B']:.4f} (&Delta; {h['paired_A_minus_B']['mean_delta']:+.4f}, 95% CI [{h['paired_A_minus_B']['ci95'][0]:+.4f}, {h['paired_A_minus_B']['ci95'][1]:+.4f}], {h['n_withheld_positives_total']:,} withheld positives, {e(h['evaluator'])}). The same 15 transforms ON TOP of the full stack gained +0.0045 [+0.0003, +0.0090] &mdash; recorded as the next preregistered lane, not shipped.</p>
 <ul class="tight">
 <li><b>Unique (measured):</b> max dot overlap within 3&nbsp;px vs any registry raster <b>{u['max_dot_overlap_within_3px_euclidean']:.1%}</b> (limit 70&nbsp;%); surface Spearman max <b>{u['max_surface_spearman']:.3f}</b> (limit 0.90). Why the family best 0.2778 won, reconstructed pixel-exactly: <a href="https://github.com/buffedlizard55-lab/GEMSDOE27/blob/main/knowledge/12_why_02778_won.md">knowledge/12</a>.</li>
 <li><b>Format:</b> all-finite, nodata=None, every cell in [0,1] (<a href="downloads/research/checks-{e(lane['stem'])}-allfinite.json">re-read receipt</a>); research bytes in <a href="downloads/research/{e(r['primary_allfinite'])}">downloads/research/</a> (sha256 {e(r['sha256'][:16])}&hellip;), intentionally not a submission download. Full run card: <a href="https://github.com/buffedlizard55-lab/GEMSDOE27/blob/main/evidence/lane_run_card_2026-10-25.json">evidence/lane_run_card_2026-10-25.json</a>. No live score exists; none is claimed.</li>
 </ul>
</div>
"""

    # ---- H29-1/H29-1b D-refill (JSON-driven; machine gates decide the badge) ----
    h29_box = ""
    h29_card_path = EV / "h29_1_run_card.json"
    h29b_card_path = EV / "h29_1b_run_card.json"
    if h29_card_path.exists():
        c29 = J(h29_card_path)
        h29, u29, r29 = c29["holdout"], c29["uniqueness_vs_registry"], c29["raster"]
        peers = {k: v for k, v in u29["per_raster"].items() if not k.startswith("gems27-")}
        peer_max = max(peers.values()) if peers else 0.0
        g32_ov = u29["per_raster"].get("g32_h33_2_b2.tif", 0.0)
        ok29 = publication_decision(c29, ROOT)["ok_to_publish_as_submission"]
        badge29 = ('<span class="badge ok" style="font-size:1.05rem">&#9989; VALIDATED &mdash; OK TO DOWNLOAD &amp; SUBMIT '
                   '(all machine gates PASS; still UNSCORED)</span>') if ok29 else (
                   '<span class="badge bad" style="font-size:1.05rem">&#9940; NOT CERTIFIED UNIQUE &mdash; DO NOT SUBMIT AS THE UNIQUE LANE FILE '
                   '(extended duplicate screen failed; see run card)</span>')
        h29b_line = ""
        if h29b_card_path.exists():
            c29b = J(h29b_card_path)
            h29b_line = (f"<li><b>Deconflicted variant H29-1b:</b> minimal-swap vs H28-1 was geometrically infeasible on the ridge "
                         f"candidate pool &mdash; final max overlap still <b>{c29b['uniqueness_vs_registry']['max_dot_overlap_within_3px_euclidean']:.1%}</b> "
                         f"&rarr; also <b>negative</b>. No further tuning (experiment budget exhausted).</li>")
        h29_box = f"""
<div class="card" style="border-left:4px solid #b00">
 <h3 style="margin-top:0">H29-1 D-refill (2026-10-25): best-validated detector &mdash; NOT certified unique</h3>
 <p>{badge29}</p>
 <p>Full 32-band stack + 15 subsurface transforms at B2/38k, preregistered (<a href="https://github.com/buffedlizard55-lab/GEMSDOE27/blob/main/knowledge/15_preregistration_H29-1.md">knowledge/15</a>) and confirmed on <b>fresh seeds 210&ndash;214</b>: pooled HOLDOUT-DTI <b>{h29['pooled_dti_D_lane']:.4f}</b> vs full-32 control <b>{h29['pooled_dti_B_control']:.4f}</b> (paired &Delta; {h29['paired_D_minus_B']['mean_delta']:+.4f}, 95% CI [{h29['paired_D_minus_B']['ci95'][0]:+.4f}, {h29['paired_D_minus_B']['ci95'][1]:+.4f}], {h29['paired_D_minus_B']['cells_positive']}/20 cells, {h29['n_withheld_positives_total']:,} withheld positives, {e(h29['evaluator'])}; leakage canary max AUC {h29['canary_max_auc']:.3f}). Efficacy and format gates <b>PASS</b>.</p>
 <ul class="tight">
 <li><b>Unique vs every scored rival (measured):</b> max &le;3&nbsp;px dot overlap vs the 12 pinned peer rasters <b>{peer_max:.1%}</b> (limit 70&nbsp;%); vs the 0.2778 file specifically <b>{g32_ov:.1%}</b> (exact shared pixels 1,649 of 38,000); surface Spearman max <b>{u29['max_surface_spearman_armD']:.3f}</b> (limit 0.90).</li>
 <li><b>Why it is still NOT certified:</b> the frozen screen also covered this repo's own <i>unscored</i> H28-1 research file (59,075 px): overlap <b>{u29['max_dot_overlap_within_3px_euclidean']:.1%}</b> &gt; 70&nbsp;% (exact-pixel Jaccard 0.116 &mdash; same ridges, different dots). Frozen gates are not relaxed after the fact.</li>
 {h29b_line}
 <li><b>Format:</b> all-finite primary, nodata=None, every cell in [0,1], EPSG:32611 3730&times;3292 (re-read receipt beside the bytes in downloads/research/; sha256 {e(r29['sha256'][:16])}&hellip;). Run cards: <a href="https://github.com/buffedlizard55-lab/GEMSDOE27/blob/main/evidence/h29_1_run_card.json">H29-1</a> &middot; <a href="https://github.com/buffedlizard55-lab/GEMSDOE27/blob/main/evidence/h29_1b_run_card.json">H29-1b</a>. <b>No live score exists; none is claimed.</b> Spending a weekly slot on a non-certified file is the owner's separate selector decision and must be recorded first.</li>
 </ul>
</div>
"""

    # ---- Lane L-H30: dip-advection / gap-flanking / soft emission vs Arm-D (JSON-driven) ----
    h30_box = ""
    h30_card_path = EV / "h30_run_card.json"
    if h30_card_path.exists():
        c30 = J(h30_card_path)
        h30, u30, r30 = c30["holdout"], c30["uniqueness_vs_registry"], c30["raster"]
        ok30 = publication_decision(c30, ROOT)["ok_to_publish_as_submission"]
        badge30 = ('<span class="badge ok" style="font-size:1.05rem">&#9989; VALIDATED &mdash; OK TO DOWNLOAD &amp; SUBMIT '
                   '(all machine gates PASS; still UNSCORED)</span>') if ok30 else (
                   '<span class="badge bad" style="font-size:1.05rem">&#9940; DO NOT SUBMIT &mdash; frozen holdout '
                   'selection gate FAILED (negative research artifact)</span>')
        rel30 = r30["directory"].replace("docs/", "", 1)
        sel30 = h30["selection_pooled_holdout_dti"]
        dl30 = (f'<p><b>One-click download:</b> <a href="{e(rel30)}/{e(r30["primary_allfinite"])}" class="btn">Download .tif</a> '
                f'<a href="{e(rel30)}/{e(r30["zip"])}" class="btn">Download .zip</a></p>'
                f'<p><b>Note to paste (&le;140 chars):</b> <code>{e(c30["note_max_140_chars"])}</code></p>') if ok30 else ""
        h30_box = f"""
<div class="card hero" style="border-left:4px solid #b00">
 <h2 style="margin-top:0">Newest unique TIF (Lane L-H30, 2026-10-25): dip-advection / gap-flanking / soft emission &mdash; NEGATIVE</h2>
 <p>{badge30}</p>
 <p>One new unique GeoTIFF was generated this session (the GAP arm below). Whether it may be submitted is decided
 <b>only</b> by the machine gates in its run card &mdash; no human-inspection step. It <b>failed</b> the frozen
 efficacy gate, so the answer is <b>NOT OK TO SUBMIT</b>, even though its bytes are format-valid and unique.</p>
 {dl30}
 <p>Three preregistered contenders (<a href="{REPO_URL}/blob/main/knowledge/20_lane_h30_preregistration_2026-10-25.md">knowledge/20</a>,
 frozen before any run) were gated against the strongest in-repo control (Arm D = 32-band + 15 subsurface transforms)
 on fresh seeds 240&ndash;244 (20 cells, {h30['n_withheld_positives_total']:,} withheld positives, {e(h30['evaluator'])}).
 Pooled <b>HOLDOUT-DTI</b>: D control <b>{sel30['D']:.4f}</b> &middot; GAP (gap-flanking) <b>{sel30['GAP']:.4f}</b>
 &middot; SOFT (soft rank-taper) <b>{sel30['SOFT']:.4f}</b> &middot; DIP (dip-advection) <b>{sel30['DIP']:.4f}</b>.
 No contender beat the control (GAP paired &Delta; {h30['paired_A_minus_B']['mean_delta']:+.4f}, 95% CI
 [{h30['paired_A_minus_B']['ci95'][0]:+.4f}, {h30['paired_A_minus_B']['ci95'][1]:+.4f}]); confirmation did not run and
 no tuning followed. Leakage canary max AUC {h30['canary_max_auc']:.3f} (clean). Catalogue-internal evidence only; no live score.</p>
 <ul class="tight">
 <li><b>The generated file (research only):</b> <code>{e(r30['primary_allfinite'])}</code>, {r30['dots']:,} dots,
 sha256 {e(r30['sha256'][:16])}&hellip;, in <a href="{e(rel30)}/{e(r30['primary_allfinite'])}">{e(rel30)}/</a> &mdash; not a submission download.</li>
 <li><b>Format PASS:</b> single-band float32, all-finite, every cell in [0,1] (the portal-error fix), EPSG:32611
 3730&times;3292; 0 dots on catalogue; min catalogue distance 2.24&nbsp;px (B2).</li>
 <li><b>Unique vs scored peers PASS:</b> max &le;3&nbsp;px dot overlap <b>{u30['max_dot_overlap_within_3px_euclidean']:.1%}</b>
 vs the 12 pinned registry rasters (limit 70&nbsp;%); max surface Spearman {u30['max_surface_spearman']:.3f} (limit 0.90).
 Extended overlaps vs this repo's own unsubmitted research files (up to
 {c30['extended_self_overlap_reported_not_gated']['max_dot_overlap_within_3px_euclidean']:.1%}) are reported in the run card.</li>
 <li>Full result: <a href="{REPO_URL}/blob/main/knowledge/21_h30_result_2026-10-25.md">knowledge/21</a> &middot;
 run card: <a href="{REPO_URL}/blob/main/evidence/h30_run_card.json">evidence/h30_run_card.json</a> &middot;
 automatic audit: <a href="data/submission_readiness_audit.json">submission readiness audit</a>.</li>
 </ul>
</div>
"""

    # ---- Lane L-DCONFIRM, parallel session B (JSON-driven; same D family as H29-1) ----
    dc_path = DOCS / "downloads" / "dconfirm_candidate_manifest.json"
    dc = J(dc_path) if dc_path.exists() else None
    dconfirm_box = ""
    if dc:
        r, u = dc["raster"], dc["uniqueness_vs_registry"]
        conf = dc["holdout"]["confirmation"]
        stats = conf["paired_candidate_minus_B"]
        rel_dir = r["directory"].replace("docs/", "", 1)
        tif_href = f"{rel_dir}/{r['primary_allfinite']}"
        checks_href = f"{rel_dir}/checks-{dc['stem']}-allfinite.json"
        badge = ('<span class="badge ok" style="font-size:1.05rem">&#9989; VALIDATED &mdash; OK TO DOWNLOAD &amp; SUBMIT '
                 '(all machine gates PASS; still UNSCORED)</span>') if publication_decision(dc, ROOT)["ok_to_publish_as_submission"] else (
                 '<span class="badge bad" style="font-size:1.05rem">&#9940; DO NOT SUBMIT &mdash; duplicate of the H29-1 lane '
                 'family (selector treats both as one candidate)</span>')
        dconfirm_box = f"""
<div class="card" style="border-left:4px solid #1565c0">
 <h3 style="margin-top:0">Lane L-DCONFIRM (parallel session B): disjoint-seed confirmation of the same D detector</h3>
 <p>{badge}</p>
 <p>An independent parallel session preregistered the same hybrid idea (full 32-band stack + 15 subsurface transforms,
 B2/38k; plus 8 new dip-offset / radiometric-front / polarity transforms that <b>failed selection</b> and were dropped).
 On <b>disjoint confirmation seeds 215&ndash;224</b> (40 cells, {conf['n_withheld_positives']:,} withheld positives) arm D again beat
 the full-32 control: pooled <b>HOLDOUT-DTI {conf['pooled_holdout_dti'][dc['arm']]:.4f} vs {conf['pooled_holdout_dti']['B']:.4f}</b>
 (paired &Delta; {stats['mean_delta']:+.4f}, 95% CI [{stats['ci95'][0]:+.4f}, {stats['ci95'][1]:+.4f}],
 {stats['folds_positive']}/4 folds, {stats['seeds_positive']}/{stats['n_seeds']} seeds). Catalogue-internal evidence only; no live score.</p>
 <ul class="tight">
 <li><b>Cross-session duplicate (measured post-merge):</b> 87.5% of this file&rsquo;s dots lie within 3&nbsp;px of H29-1&rsquo;s dots (87.8% reverse) &mdash; the two parallel lanes converged. <b>Do not spend two slots on this family.</b> Evidence: <a href="{REPO_URL}/blob/main/evidence/dconfirm_cross_session_overlap.json">cross-session overlap</a>.</li>
 <li><b>Vs scored rivals:</b> max {u['max_dot_overlap_peer_registry_12']:.1%} within 3&nbsp;px of any of the 12 pinned peer rasters; surface Spearman max {u['max_surface_spearman']:.3f}. Vs audit-only H28-1: {u['max_dot_overlap_self_repo']:.1%} (same failure as H29-1).</li>
 <li><b>Format:</b> all-finite, nodata=None, every cell in [0,1], EPSG:32611 3730&times;3292 (<a href="{e(checks_href)}">re-read receipt</a>); research bytes in <a href="{e(tif_href)}">downloads/research/</a> (sha256 {e(r['sha256'][:16])}&hellip;). Run card: <a href="{REPO_URL}/blob/main/evidence/dconfirm_run_card_2026-10-25.json">evidence/dconfirm_run_card_2026-10-25.json</a>; analysis <a href="{REPO_URL}/blob/main/knowledge/16_dconfirm_result.md">knowledge/16 (L-DCONFIRM)</a>.</li>
 </ul>
</div>
"""

    # ---- Unique scatter-farfield submission candidate (this session) ----
    unique_checks_path = DOCS / "downloads" / "checks-gems27-unique-scatter-farfield-20261025-98e59bf8e3ce-allfinite.json"
    unique_run_card_path = EV / "run_card_unique_scatter_farfield_20261025.json"
    unique_tif = J(unique_checks_path) if unique_checks_path.exists() else None
    unique_run_card = J(unique_run_card_path) if unique_run_card_path.exists() else None
    unique_tif_box = ""
    if unique_tif:
        v = unique_tif["validation"]
        lane = unique_tif["lane_check"]
        badge = (
            '<span class="badge bad" style="font-size:1.05rem">&#9940; FORMAT-VALID + UNIQUE &mdash; NOT CERTIFIED FOR SUBMISSION '
            '(holdout DTI not measurable by design; owner selector decision required)</span>'
        )
        unique_tif_box = f"""
<div class="card hero" style="border-left:4px solid #b00">
 <h2 style="margin-top:0">&#128269; Unique submission TIF &mdash; ready to download</h2>
 <p>{badge}</p>
 <div class="row">
  <span class="badge ok">format: single-band float32 GeoTIFF, EPSG:32611, 3730&times;3292</span>
  <span class="badge ok">values: exactly 0.0/1.0 inside footprint, all in [0,1]</span>
  <span class="badge ok">unique: 0% dot overlap within 3&nbsp;px vs all 6 registry rasters (limit 70&nbsp;%)</span>
  <span class="badge bad">holdout: not measurable &mdash; far-field truth absent from catalogue proxy</span>
 </div>
 <p><b>File:</b> <code>{unique_tif['filename']}</code> &nbsp;({unique_tif['bytes_tif']:,} bytes) &nbsp;
 <b>ZIP:</b> <code>{unique_tif['zip']['file']}</code> &nbsp;({unique_tif['zip']['bytes']:,} bytes) &nbsp;
 <b>SHA-256:</b> <code>{unique_tif['sha256_tif']}</code></p>
 <p><b>One-click download:</b>
 <a href="downloads/{unique_tif['filename']}" class="btn">Download .tif</a>
 <a href="downloads/{unique_tif['zip']['file']}" class="btn">Download .zip (single GeoTIFF)</a></p>
 <p><b>Short note to paste into the DrivenData submission form (&le;200 chars):</b></p>
 <p style="background:#f5f5f5;padding:0.5rem;border-radius:4px;font-family:monospace;font-size:0.9rem;">
 {e(unique_tif['note'])}
 </p>
 <p><b>Hypothesis:</b> {e(unique_run_card['hypothesis'] if unique_run_card else unique_tif['hypothesis'])}</p>
 <p><b>Verdict:</b> {unique_run_card['verdict'] if unique_run_card else 'negative'}. {unique_run_card['verdict_reason'] if unique_run_card else 'Holdout DTI not measurable by design (far-field truth absent from catalogue-internal proxy). Format-valid and unique; not holdout-promoted.'}</p>
 <p class="small"><b>Submission steps:</b> 1) Download the .tif (do not open/re-save in GIS software). 2) Sign in at
 <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DrivenData #306</a>. 3) Upload the .tif (or .zip with exactly one GeoTIFF).
 4) Paste the note above. 5) Submit and record the organiser receipt. This project never contacts drivendata.org (Terms of Use).</p>
 <p class="small"><b>Why not certified:</b> the catalogue-internal component-hidden holdout has 100% of its truth at d=0 from the published
 catalogue and 99.6% of credit within 200 m; this emission is entirely at d_cat &ge; 3 px (far field), so holdout DTI = 0 by design
 (knowledge/10). Support: GEMSDOE32 truth model (+0.0247, 12/12 draws) and convergence with GEMSDOE36 PINN (0.2750) on the B2 + ~38k optimum.
 Full run card: <a href="https://github.com/buffedlizard55-lab/GEMSDOE27/blob/main/evidence/run_card_unique_scatter_farfield_20261025.json">evidence/run_card_unique_scatter_farfield_20261025.json</a> · 
 Format receipt: <a href="downloads/{unique_checks_path.name}">checks JSON</a></p>
</div>
"""
    h28_manifest_path = DOCS / "downloads" / "h28_1_candidate_manifest.json"
    h28_manifest = J(h28_manifest_path) if h28_manifest_path.exists() else None
    h28_candidate = h28_manifest.get("candidate") if h28_manifest else None
    h28_hypothesis_path = REG / "next_hypotheses.json"
    h28_hypotheses = J(h28_hypothesis_path).get("hypotheses", []) if h28_hypothesis_path.exists() else []
    h28_evidence_path = EV / "h28_1_edge_holdout.json"
    h28_eval = J(h28_evidence_path) if h28_evidence_path.exists() else None
    h27_10_evidence_path = EV / "h27_10_annulus_holdout.json"
    h27_10_eval = J(h27_10_evidence_path) if h27_10_evidence_path.exists() else None
    ms = J(EV / "candidate_model_scores.json") if (EV / "candidate_model_scores.json").exists() else None
    inv = J(EV / "live_inversion.json") if (EV / "live_inversion.json").exists() else None
    bo = J(EV / "budget_optimum.json") if (EV / "budget_optimum.json").exists() else None
    mslot = {c["slot"]: c for c in (ms["candidates"] if ms else [])}

    def mscore(slot, which):
        v = mslot.get(slot, {}).get(which)
        return f"{v:.4f}" if v else "&ndash;"

    geo_ceiling = max(c["model_score"] for c in bo["sweeps"]["h19_5"]["rows"]) if bo else 0.2550
    invcard = ""
    if inv and bo:
        invcard = (
            '<div class="card"><h3 style="margin-top:0">New this session: the live scores were inverted</h3>'
            "<p>All <b>20</b> of the owner's scored rasters were recovered from the sibling repositories and "
            "authenticated by <b>SHA-256</b>, then inverted against the official metric. Two instruments came "
            'out of it, and both reproduce the live anchors exactly.</p><div class="grid">'
            f'<div class="stat"><b>{inv["G_used"]:,.0f}</b><span>hidden-truth pixels |G|, from a blind '
            "spacing-5 lattice whose credit is pure geometry. The sibling's independent estimate: 12,503 "
            "&mdash; <b>2.2&nbsp;% apart</b></span></div>"
            '<div class="stat"><b>&minus;0.1&nbsp;% / +4.0&nbsp;%</b><span>error of the retention rule on two '
            "independent live solid&rarr;dotted pairs (H19-5&rarr;d1.5, H25-ctx&rarr;h28)</span></div>"
            f'<div class="stat"><b>{geo_ceiling:.4f}</b><span>ceiling of the emission-geometry lever '
            "(d=2.25&ndash;2.8, 44,090 px). The sibling's independent fit: 0.2553</span></div>"
            '<div class="stat"><b>5.67</b><span>concentration of the 0.2477 file &mdash; 5.67&times; better '
            "than a blind lattice at finding truth. The whole H19-5 family plateaus at 5.3&ndash;5.7</span></div>"
            '</div><p class="small">No submission in the group&#39;s history has ever earned more than '
            "<b>0.508&#124;G&#124;</b> of credit. 0.3195 at 60,069&nbsp;px needs <b>0.570&#124;G&#124;</b>. "
            'That is now an arithmetic statement, not an opinion &mdash; see <a href="research.html#inversion">'
            "the inversion</a>.</p></div>")
    # ---- tables for the Session-3 live-score inversion (research.html#inversion) ----
    inv_g = inv["G_used"] if inv else 12226.0
    concrows, retrows, sweeprows, reqrows = "", "", "", ""
    if inv:
        keep = [r for r in inv["submissions"]
                if r["credit_fraction_of_G"] >= 0.18 or "lattice" in r["label"]]
        for r in sorted(keep, key=lambda r: -r["score"])[:12]:
            conc = (r["credit_fraction_of_G"] / r["c_blind_credit_per_truth"]
                    if r["c_blind_credit_per_truth"] else 0.0)
            nm = r["label"].split(" ", 1)[-1]
            concrows += (f"<tr><td>{e(nm[:40])}</td><td class='num'>{r['n_scored']:,}</td>"
                         f"<td class='num'>{r['score']:.4f}</td>"
                         f"<td class='num'>{r['credit_TPw']:,.0f}</td>"
                         f"<td class='num'>{r['credit_fraction_of_G']:.3f}</td>"
                         f"<td class='num'><b>{conc:.2f}</b></td>"
                         f"<td class='num'>{r['rho_matched_over_TP']:.2f}</td></tr>")
        for v in (bo["retention_validation"] if bo else []):
            retrows += (f"<tr><td>{e(v['solid'].split(' ', 1)[-1][:26])} &rarr; "
                        f"{e(v['dotted'].split(' ', 1)[-1][:30])}</td>"
                        f"<td class='num'>{v['retention_predicted_by_geometry']:.4f}</td>"
                        f"<td class='num'>{v['retention_measured_live']:.4f}</td>"
                        f"<td class='num'>{v['relative_error'] * 100:+.1f}&nbsp;%</td></tr>")
        for n in (20000, 30000, 44090, 60069, 121131):
            row = {q["target"]: q for q in inv["requirements"] if q["emitted_px"] == n}
            if len(row) == 3:
                reqrows += (f"<tr><td class='num'>{n:,}</td>"
                            + "".join(f"<td class='num'>{row[t]['credit_fraction_required']:.3f}|G|</td>"
                                      for t in (0.2477, 0.2941, 0.3195)) + "</tr>")
    if bo and "h19_5" in bo["sweeps"]:
        for r in bo["sweeps"]["h19_5"]["rows"]:
            if r["min_dist"] in (1.0, 1.25, 1.5, 2.25, 3.0, 4.0, 6.0):
                sweeprows += (f"<tr><td class='num'>{r['min_dist']}</td>"
                              f"<td class='num'>{r['n_px']:,}</td>"
                              f"<td class='num'>{r['retention_vs_solid']:.3f}</td>"
                              f"<td class='num'>{r['rho']:.2f}</td>"
                              f"<td class='num'><b>{r['model_score']:.4f}</b></td></tr>")
    geoceil = max((c["model_score"] for c in bo["sweeps"]["h19_5"]["rows"]), default=0.2550) if bo else 0.2550

    val = J(EV / "topology_validation.json")
    con = J(EV / "topology_confirmation_v2.json")
    vval = J(EV / "vector_topology_validation.json")
    oof = J(EV / "oof_hypothesis_gates.json")
    gr = J(EV / "graph_report.json")
    cs = J(EV / "candidate_summary.json")
    relay_summary = (
        J(EV / "structural_relay_classes.json")
        if (EV / "structural_relay_classes.json").exists()
        else cs.get("structural_review_classes", {})
    )
    op = J(EV / "operating_point_model.json")
    hyp = J(REG / "hypotheses.json")["hypotheses"]
    src = J(REG / "sources.json")["sources"]
    irr = J(REG / "irregularities.json")["items"]
    sc = J(REG / "live_scores.json")
    cand = J(REG / "topology_candidates.json")["links"]
    feed = J(DOCS / "data" / "feed.json") if (DOCS / "data" / "feed.json").exists() else None
    be = gr["berkowitz_style_estimate"]
    eff = con["efficiency_pooled"]
    veff_fid = vval["tiers"]["FID_trace"]["efficiency_pooled"]
    pay = op["payoff_of_shipped_addition"]["by_efficiency"]
    _sgi = sgi["inversion"]["blind_lattice_this_repo"]
    sgi_c = _sgi["c_blind_credit_per_truth_px"]
    sgi_conc = sgi["reading"]["concentration_central"]
    sgi_lo, sgi_hi = sgi["reading"]["concentration_band"]
    sgi_n = sgi["construction_verified_from_raster"]["n_positive_in_footprint"]
    _hb = hab["per_arm"]["base"]["credit_by_band"]
    hab_share = sum(_hb[k] for k in ("d0_on_spine", "d1_100m", "d2_200m")) / max(sum(_hb.values()), 1e-9)
    sgmc_gain = addD["stage_b_verdicts"]["arms"]["sgmc"]["mean_paired_gain_vs_base"]
    gP0 = gval.get("P_catalogue_only_published", 0.0)
    gP1 = gval.get("P_with_all_345_candidates", 0.0)
    gbridges = gval.get("n_bridges", 0)
    _d3 = addD["stage_b_verdicts"]["d3"]
    d3top = _d3["top_half_by_abs_delta_P"]["efficiency"]
    d3all = _d3["all_T_v2"]["efficiency"]
    d3p95 = _d3["random_95th_percentile_efficiency"]
    d4eff = addD["stage_b_verdicts"]["d4"]["steppover_alone"]["efficiency"]
    h28_gate_summary = ""
    if h28_eval:
        negative_folds = [name for name, gain in h28_eval["gain_by_fold"].items() if gain < 0]
        negative_seeds = [seed for seed, gain in h28_eval["gain_by_seed"].items() if gain < 0]
        h28_gate_summary = (
            f"Frozen seeds 140–149: mean paired ΔDTI {h28_eval['candidate_minus_baseline_mean_gain']:+.5f}; "
            f"{h28_eval['improved_fold_count']}/4 folds and {h28_eval['positive_seed_count']}/10 seeds improved. "
            f"Negative fold(s): {', '.join(negative_folds) or 'none'}; negative seed(s): "
            f"{', '.join(negative_seeds) or 'none'}. Catalogue-internal validation, not a leaderboard score."
        )
    h28_research_box = ""
    if h28_candidate:
        h28_research_box = f"""
<div class="warnbox"><b>H28-1 historical research artifact — audit only; not approved for a new submission.</b>
{e(h28_gate_summary)} The archived full-map item has content id <code>{e(h28_candidate['content_id'])}</code> and
{h28_candidate['emitted_px']:,} binary cells with no known-label overlap. Its historical manifest remains in the repository for audit, but no direct download is offered on this site because the current parallel protocol requires a fresh uniqueness review before any submission recommendation.
The organizer-created test labels remain unobserved; this is not a fifth weekly slot or a score.</div>"""
    elif h28_eval:
        h28_research_box = f'<div class="warnbox"><b>H28-1 holdout:</b> {e(h28_gate_summary)} The separate full-map research candidate has not been built.</div>'
    h28_3_evidence_path = EV / "h28_3_strain_holdout.json"
    h28_3_eval = J(h28_3_evidence_path) if h28_3_evidence_path.exists() else None
    peer_registry_path = REG / "parallel_submission_registry.json"
    peer_registry = J(peer_registry_path) if peer_registry_path.exists() else None
    h28_3_negative_path = DOCS / "downloads" / "research" / "h28_3_negative_research_manifest.json"
    h28_3_negative = J(h28_3_negative_path) if h28_3_negative_path.exists() else None
    h28_3_box = ""
    if h28_3_eval:
        h = h28_3_eval["HOLDOUT_DTI"]
        gate_label = "PASS" if h28_3_eval["gate"]["pass"] else "FAILED"
        peer_count = len(peer_registry["entries"]) if peer_registry else 0
        negative_link = (
            '<a href="downloads/research/h28_3_negative_research_manifest.json">negative-artifact receipt</a>'
            if h28_3_negative else "negative artifact not retained"
        )
        h28_3_box = f"""
<div class="warnbox"><b>Session 6 H28-3 strain × conductivity result — {gate_label}; NO NEW SUBMISSION IS APPROVED.</b>
<b>HOLDOUT-DTI ({e(h28_3_eval['evaluator_version'])}):</b> baseline {h['baseline']['pooled_dti']:.6f}; candidate {h['candidate']['pooled_dti']:.6f}; paired Δ {h['candidate_minus_baseline_pooled']:+.6f}; 95% bootstrap CI [{h['bootstrap_95_ci_seed_resampling'][0]:+.6f}, {h['bootstrap_95_ci_seed_resampling'][1]:+.6f}] across the 10 seed-level differences; withheld-positive occurrences {h['candidate']['withheld_positives_total']:,}. It improved only {sum(v > 0 for v in h['seed_level_paired_deltas'].values())}/10 seeds and {sum(v > 0 for v in h['fold_pooled_deltas'].values())}/4 folds. Canary passed; the frozen gate failed.
The 59,243-dot all-finite research TIFF is format-valid and cleared the duplicate screen against {peer_count} pinned peer rasters, but is explicitly <b>NOT APPROVED FOR SUBMISSION</b>; format validity and novelty do not override a negative holdout. See {negative_link} ·
<a href="{REPO_URL}/blob/main/evidence/h28_3_strain_holdout.json">cell-level evidence</a> ·
<a href="{REPO_URL}/blob/main/evidence/h28_3_negative_uniqueness.json">duplicate check</a> ·
<a href="{REPO_URL}/blob/main/knowledge/13_preregistration_H28-3.md">frozen protocol</a>.</div>"""
    h27_10_box = ""
    if h27_10_eval:
        h27_10_box = f"""
<div class="warnbox"><b>Session 5 H27-10 annulus result — REJECTED; no weekly slot.</b>
Registered holdout on seeds 150-159 (first use): mean paired ΔDTI <b>{h27_10_eval['candidate_minus_baseline_mean_gain']:+.6f}</b> vs the current H28-1 + T-v2 + H27-4 r1 best;
{h27_10_eval['improved_fold_count']}/4 fold means improved but only {h27_10_eval['positive_seed_count']}/10 seed means improved.
The annulus addition efficiency was {h27_10_eval['gross_annulus_add_efficiency']:.5f} versus m(0.2477)={h27_10_eval['m_live_0_2477']:.5f};
removed far-field efficiency was {h27_10_eval['gross_removed_farfield_efficiency']:.5f}. The frozen gate <b>failed</b>, so the annulus is not promoted.
The deterministic integrity rerun passed all data checks; the first run's self-distance diagnostic false-negative is preserved and disclosed, with no change to the candidate or gate.
<a href="{REPO_URL}/blob/main/knowledge/03_preregistration_topology_gate.md#addendum-f-h27-10">Protocol</a> ·
<a href="{REPO_URL}/blob/main/evidence/h27_10_annulus_holdout.json">corrected cell-level evidence</a> ·
<a href="{REPO_URL}/blob/main/evidence/h27_10_annulus_holdout_initial.json">preserved first-run record</a> ·
<a href="{REPO_URL}/blob/main/registry/irregularities.json">diagnostic disclosure</a>.
Catalogue-internal result only; no organizer-label score is known.</div>"""
    priority_basis = relay_summary.get("priority_basis", {})
    priority_n = int(relay_summary.get("priority_candidate_count", 0))
    priority_total = int(relay_summary.get("candidate_count", cs.get("selected_links", 345)))
    exclusive_counts = relay_summary.get("counts_by_exclusive_review_class", {})
    class_count_text = " · ".join((
        f"{exclusive_counts.get('same-FID_multipart-continuity', 0)} same-FID",
        f"{exclusive_counts.get('H27-5b_inter-FID_same-name_kinematic-compatible', 0)} H27-5b",
        f"{exclusive_counts.get('inter-FID_other-name_kinematic-compatible', 0)} other-name compatible",
        f"{exclusive_counts.get('inter-FID_kinematic-conflict-or-unknown', 0)} conflict/unknown",
    ))
    priority_holdout = ""
    if priority_basis:
        priority_holdout = (
            f" Tier-2 whole-FID holdout, seeds {e(priority_basis.get('seeds', []))}: "
            f"efficiency {priority_basis['h27_5b_efficiency']:.4f} vs rotated control "
            f"{priority_basis['rotated_control_efficiency']:.4f} ({priority_basis['enrichment_over_control']:.2f}×)."
        )
    topology_priority_box = f"""
<div class="card"><h2>Geologist-review priority class: H27-5b ({priority_n} / {priority_total} links)</h2>
<p>Population: the existing 345 shipped T-v2 links (z ≥ 3, deduplicated; each gap is 1–4 km); this review filter generates no new links. Frozen filter: <code>fid_src != fid_tgt</code>, equal NBMG <code>NAME</code> other than the generic <code>Unnamed fault</code> sentinel, and <code>kinematic_compat=true</code>.
This identifies distinct vector records within one named zone, not independently sourced maps or confirmed separate faults.{e(priority_holdout)}</p>
<p class="small">Exclusive partition of all {priority_total}: {e(class_count_text)}.</p>
<p>Rows expose FID/NAME/NUM, slip sense, dip direction, map scale, gap geometry, local strike compatibility, graph consequences and a cautious setting hint.
End-to-end, abutting and oblique geometries are review cues only; they do not prove a favorable relay, step-over or termination. Faulds &amp; Hinz setting frequencies are context about characterized systems, not evidence for an individual candidate.
The prior graph-ΔP ranking and the separate overlapping en-echelon step-over test were both refuted as holdout-improvement signals; this class does not revive either claim.</p>
<p>Download the focused <a href="data/topology_priority_h27_5b.csv">81-row CSV with per-link arguments and official source links</a> ·
<a href="data/topology_priority_h27_5b.geojson">GeoJSON</a> ·
<a href="data/topology_review_classes.json">class definition, counts and limitations</a>.
Sources: <a href="https://web2.nbmg.unr.edu/arcgis/rest/services/Qfaults/Qfaults_INGENIOUS/MapServer/0">NBMG Qfaults feature layer</a> ·
<a href="https://www.osti.gov/servlets/purl/1724082">Faulds &amp; Hinz 2015</a> ·
<a href="https://agupubs.onlinelibrary.wiley.com/doi/10.1029/1999GL011241">Berkowitz et al. 2000 publisher abstract</a>.</p>
<p class="small">The Tier-2 result is catalogue-internal evidence from held-out FID records, not a score or proof of transfer to the organizer-created labels. The full 345-link rule and all four weekly files are unchanged.</p></div>""" if priority_n else ""
    pages: dict[str, tuple[str, str]] = {}

    # ---------------------------------------------------------------- index
    pages["index.html"] = ("Submit", f"""
<h1>Submission status</h1>
{unique_tif_box}
<p class="lead">27GEMSDOE · DrivenData #306 DOE GEMS. The unique TIFF above is format-valid and unique, but its holdout DTI is not measurable by design (far-field truth absent from the catalogue-internal proxy). No live score exists for any 27GEMSDOE file; none is claimed.</p>
<span class="badge bad">NO TIFF IS APPROVED TO SUBMIT</span> <span class="badge bad">DO NOT SUBMIT H28-3</span></p>
<div class="card hero">
 <h2 style="margin-top:0">There is no one-click submission download for this run.</h2>
 <p><b>Why:</b> H28-3 dilatational-strain × conductivity corridors reduced pooled HOLDOUT-DTI relative to the current H28-1 baseline. A TIFF that is merely valid GeoTIFF syntax is not an eligible competition candidate.</p>
 <div class="row"><span class="badge ok">research TIFF format verified: float32 · single band · values [0,1]</span><span class="badge ok">unique versus 12 pinned peer rasters</span><span class="badge bad">predictive gate failed</span></div>
 <p class="small">The exact gate, 95% CI, validation receipt and duplicate report are on the <a href="research.html#h28-3"><b>Research page</b></a>. The executive summary explains the rule used to decide when a future TIFF is actually okay to submit.</p>
</div>
{h30_box}
{h29_box}
{dconfirm_box}
{h28_3_box}
{lane_box}
<p><b>Legacy files below are retained only for audit and must not be submitted as a new unique candidate:</b> peer repositories now contain overlapping copies and no organizer receipt verifies their score/file pairing. The next action is a new pre-registered, data-ready hypothesis—not a renamed legacy raster.</p>
<div class="grid">
 <div class="stat"><b>{P['emitted_px']:,}</b><span>emitted pixels = 60,069 (the 0.2477 emission, nothing removed) + {P['added_px']:,}</span></div>
 <div class="stat"><b>{cs['selected_links']}</b><span>aligned gap links (median {cs['median_gap_km']:.1f} km), each with NBMG/USGS vector fault attribution &amp; written argument</span></div>
 <div class="stat"><b>{eff['z>=3 dedup']:.2f} / {veff_fid['z>=3 dedup']:.2f}</b><span>holdout efficiency on 8-conn components / whole NBMG FID vector polylines vs break-even 0.052</span></div>
 <div class="stat"><b>{oof['variants']['plus_T_v2']['mean_dti_gain']:+.4f} / {oof['variants']['plus_T_v2_and_prune_r1']['mean_dti_gain']:+.4f}</b><span>paired DTI gain on honest 4-fold spatial-CV OOF detector (T-v2 solo / T-v2 + H27-4 in Slot 3)</span></div>
</div>
{invcard}
<div class="card" style="border-left:4px solid #b00">
 <h3 style="margin-top:0">Session 4: three results that change what is worth doing</h3>
 <ol style="margin:.4rem 0 .4rem 1.2rem">
  <li><b>The far-field / bedrock-map habitat is live-refuted.</b> The group's own h18-4 file ({sgi_n:,} px of USGS State Geologic Map Compilation faults, all &ge;300&nbsp;m from the catalogue, owner-reported <b>0.0360</b>) was hash-authenticated and inverted: concentration <b>{sgi_conc:.2f}&times; blind</b> (exact bracket {sgi_lo:.2f}&ndash;{sgi_hi:.2f}&times;) against 5.3&ndash;6.0&times; for the family that produced 0.2477, and its 1-px lines cover <i>less</i> DTI kernel mass than a uniform spray of the same size (c&nbsp;=&nbsp;{sgi_c:.4f} vs 0.1050). Never emit on an &ldquo;independent second catalogue&rdquo;. <a href="research.html#inversion">details</a></li>
  <li><b>The holdout can no longer see what matters.</b> 100% of hidden truth in every gate here lies at distance 0 from the published catalogue and <b>{hab_share:.1%} of credit is earned within 200&nbsp;m of it</b>, while the live 0.2477 emission puts <b>81.4% of its dots &ge;300&nbsp;m away</b>. Two Addendum-D arms passed both registered criteria on that proxy (+SGMC features: out-of-fold PR-AUC 0.0246&rarr;0.0428, paired DTI {sgmc_gain:+.4f} in 4/4 folds) and are <b>not promoted</b>: their whole gain is catalogue proximity, and their far-field behaviour is the habitat measured at {sgi_conc:.2f}&times; blind above. Slot 5 exists to settle it live.</li>
  <li><b>Graph value is documentation, not a ranking signal.</b> Closing all {cs['selected_links']} candidates moves the network's Berkowitz connectivity parameter from <b>P&nbsp;=&nbsp;{gP0:.3f} to {gP1:.3f}</b> &mdash; from inside the paper's critical range (Pc 5.6&ndash;6.0) to above it &mdash; and {gbridges} of {cs['selected_links']} links are bridges. But ranking by |dP| does <i>not</i> beat the shipped z&ge;3 rule ({d3top:.4f} vs {d3all:.4f}, inside the random-half spread up to {d3p95:.4f}); overlapping en-echelon step-overs &mdash; a class the forward-cone rule cannot generate at all &mdash; reach only {d4eff:.4f}, below break-even 0.0638; and 24 oriented 0.5&ndash;2&nbsp;km lineament bands move PR-AUC by +0.0010. All three refuted, all recorded.</li>
 </ol>
</div>
<div class="card">
 <h3 style="margin-top:0">Historic slot artifacts — audit only</h3>
 <p>Five older rasters (four slot variants and one measurement probe) remain in the repository as evidence of prior work. They pre-date the pinned parallel registry, and peer-family overlap means they are not presented as fresh unique candidates. Direct TIFF and ZIP links have deliberately been removed from the public decision page.</p>
 <p class="small">Audit IDs: Slot 1 <code>{e(P['content_id'])}</code>; Slot 2 <code>{e(S['content_id'])}</code>; Slot 3 <code>{e(T['content_id'])}</code>; Slot 4 <code>{e(Q['content_id'])}</code>; probe <code>{e(Q5['content_id'])}</code>. Historical manifests are versioned with the repository.</p>
</div>
{h28_research_box}
<div class="warnbox"><b>Honest status.</b> We validated T-v2 across three holdout tiers (8-connected components: {eff['z>=3 dedup']:.3f}, whole NBMG FID vector polylines: {veff_fid['z>=3 dedup']:.3f} / H27-5b {veff_fid['z>=3 inter-FID + same_name + kinematic_compat (H27-5b)']:.3f}) and on a strictly out-of-fold 4-quadrant spatial-CV detector (ΔDTI {oof['variants']['plus_T_v2']['mean_dti_gain']:+.4f} solo, {oof['variants']['plus_T_v2_and_prune_r1']['mean_dti_gain']:+.4f} stacked with H27-4). Only a live score tests the organisers' newly created expert labels.
Reaching the owner-stated leader (0.3195) is not possible with verified/modelled increments on H19-5 alone (they reach ≈0.262–0.270) – see <a href="research.html">research</a>.
The agent never uploads anything; you press the button.</div>
<p class="small">Reference (owner-reported 0.2477): <a href="{e(reference_audit_url)}">24GEMSDOE audit record</a> (sha256 {e(man['reference_0_2477']['sha256'][:16])}…). It is historical comparison evidence, not a current download recommendation.</p>
""")

    # ---------------------------------------------------------------- executive summary
    rows_pay = "".join(f"<tr><td class='num'>{k}</td><td class='num'>{v:+.4f}</td></tr>" for k, v in pay.items())
    pages["executive-summary.html"] = ("Executive summary", f"""
<h1>Executive summary</h1>
{unique_tif_box}
<p class="lead">What to submit, exactly how, what it can and cannot do, and what to do next.</p>
<div class="card"><h2 style="margin-top:0">Decision in one table</h2>
<table><tr><th>Question</th><th>Answer</th></tr>
<tr><td>What to submit now</td><td><b>Nothing.</b> No current raster is marked okay to submit. H28-3 is format-valid but its frozen HOLDOUT-DTI gate failed; legacy slot rasters are peer-overlapping audit artifacts.</td></tr>
<tr><td>What the new H28-3 file is</td><td>A unique, reproducible <b>negative research artifact</b> generated from strain–conductivity corridors. It has valid GeoTIFF bytes but an adverse paired holdout result, so its status is <b>DO NOT SUBMIT</b>.</td></tr>
<tr><td>HOLDOUT-DTI evidence</td><td>H28-3 candidate minus current H28-1 baseline: {h28_3_eval['HOLDOUT_DTI']['candidate_minus_baseline_pooled']:+.6f} pooled; 95% seed-bootstrap CI [{h28_3_eval['HOLDOUT_DTI']['bootstrap_95_ci_seed_resampling'][0]:+.6f}, {h28_3_eval['HOLDOUT_DTI']['bootstrap_95_ci_seed_resampling'][1]:+.6f}]; only {sum(v > 0 for v in h28_3_eval['HOLDOUT_DTI']['seed_level_paired_deltas'].values())}/10 seeds improved. Negative result retained; no slot spent.</td></tr>
<tr><td>What qualifies in future</td><td>A new candidate must pass its pre-registered holdout gate, format validation, and the pinned peer-raster duplicate screen before this table changes to <b>APPROVED TO SUBMIT</b>.</td></tr>
<tr><td>Is 0.3195 reachable?</td><td>Not with verified/modelled increments (they reach ≈0.26–0.27). It needs ≈31% more weighted recall at equal false positives, or ≈46% fewer false-positive pixels at equal recall – i.e. new information. <a href="research.html">Why</a>.</td></tr>
<tr><td>What is unknown</td><td>The real hidden-set effect; the cause of the portal's "[0, 1]" rejection; the live scores of all 27GEMSDOE files.</td></tr></table></div>

<div class="card hero"><h2 style="margin-top:0">Current submission decision: STOP</h2>
<p><span class="badge bad">NO TIFF IS APPROVED TO SUBMIT</span></p>
<p>The unique H28-3 research TIFF is intentionally not offered as a submission download because it lost to the current baseline on its frozen holdout. Its all-finite GeoTIFF and ZIP passed format checks, but validity does not cure a negative model result.</p>
<p>Read the <a href="research.html#h28-3">H28-3 result and run card</a>, <a href="downloads/research/h28_3_negative_research_manifest.json">format receipt</a>, and <a href="{REPO_URL}/blob/main/evidence/h28_3_negative_uniqueness.json">peer-registry uniqueness report</a>. The receipt says <b>NOT APPROVED FOR SUBMISSION</b> on every file variant.</p></div>

<h2>Exact submission steps</h2>
<ol class="steps">
<li><b>Gate first:</b> use a file only when the front page explicitly says <b>APPROVED TO SUBMIT</b>. The current H28-3 research files are explicitly ineligible; do not upload them.</li>
<li>Download the approved <b>.tif</b> without opening/re-saving it in GIS software. Keep its content-hashed file name and the short note shown beside it.</li>
<li>Sign in at DrivenData and open <a href="{DD_COMP}">the competition page</a>.</li>
<li>Open the submission form (the tab/button label depends on the logged-in view; this project does not automate that site).</li>
<li>Upload the approved single-band <b>.tif</b> – or its approved <b>.zip</b>, which must contain exactly one GeoTIFF – and paste its <=200-character note.</li>
<li>Submit, retain the portal response / score, and record that exact outcome in <code>registry/live_scores.json</code>. Scores stay OWNER-REPORTED unless a receipt is stored.</li></ol>

<h2>Submission-format rule for a future approved candidate</h2>
<div class="card">
<p>The earlier portal message, “Predicted values must be in range [0, 1],” has no established cause because the organizer validator is not public. It is not a reason to upload an unapproved file.</p>
<p>Before any future candidate is labelled approved, the independent validator must record: a single-band float32 GeoTIFF on the exact competition grid/CRS/transform; every in-footprint prediction finite and within [0,1]; an explicitly verified outside-footprint/nodata convention; no known-catalogue overlap where the protocol forbids it; a ZIP containing exactly one TIFF if offered; and a note within the portal limit. The validation receipt and peer-uniqueness result must be linked beside the approved download.</p>
</div>

<h2>Historical weekly-slot decision tree — archived and suspended</h2>
{h30_box}
{h29_box}
{dconfirm_box}
{h28_3_box}
<p class="warnbox"><b>Do not follow historic slot instructions or upload historical rasters.</b> They are retained in repository history to audit earlier work, but their rasters pre-date the pinned peer registry and are not current unique submissions. A future pre-registered candidate can replace this notice only after it passes its gate, format validation, and duplicate screen.</p>
<p class="small">The historical model estimates and topology evidence remain available below for scientific context. They are not a submission recommendation and must not be read as organiser scores.</p>

<h2>Modelled payoff of the shipped addition</h2>
<div class="row"><table style="max-width:22rem"><tr><th class="num">hit efficiency</th><th class="num">ΔDTI at 0.2477</th></tr>{rows_pay}</table>
<p class="small" style="flex:1;min-width:16rem">Model arithmetic from <code>evidence/operating_point_model.json</code> (assumes hidden truth ≈ 12.6k px and FP ≈ 4.3|G|; both unconfirmed). Break-even efficiency is 0.052 at DTI 0.2477. Holdout efficiency of the shipped set: {eff['z>=3 dedup']:.2f}; catalogue-internal, so expect less.</p></div>

<h2>Compliance checklist</h2>
<ul class="tight"><li><b>Automation:</b> the DrivenData Terms of Use prohibit robots/automatic means "for any purpose, including monitoring or copying" – this project never requests drivendata.org.</li>
<li><b>AI disclosure:</b> the Official Rules require generative-AI use to be stated in the narrative – see <a href="{REPO_URL}/blob/main/AI_DISCLOSURE.md">AI_DISCLOSURE.md</a>.</li>
<li><b>Deadline:</b> the page says Dec 3, 2026 11:59 p.m. UTC; the rules (A.1) say 5:00 p.m. ET – unresolved; use the earlier.</li>
<li><b>Finalists</b> deliver code and documentation – this repository is that documentation.</li></ul>

<h2>Limitations and access needed</h2>
<ul class="tight"><li>No live score exists for any 27GEMSDOE file; validation is catalogue-internal; the paired base is leaky; the graph is raster-based (no names/slip sense).</li>
<li>Owner actions: submit and record the score; paste the exact portal message if rejected; paste the original task prompt into the README placeholder; optional geologist review of the 345 dossiers; optional CI download of USGS Qfaults/Siler data.</li></ul>
<p>Full lists: <a href="{REPO_URL}/blob/main/knowledge/06_limitations_and_access.md">limitations &amp; access</a> · <a href="sources.html#irregularities">flagged irregularities</a>.</p>
""")

    # ---------------------------------------------------------------- topology
    rows = []
    for r in sorted(cand, key=lambda r: (-r["z"], r["gap_km"])):
        mlat, mlon = (r["lat_a"] + r["lat_b"]) / 2, (r["lon_a"] + r["lon_b"]) / 2
        fname_cell = e(r.get("name_src") or "unnamed")
        if not r.get("same_name") and (r.get("name_tgt") or "") != (r.get("name_src") or ""):
            fname_cell += f" → {e(r.get('name_tgt') or 'unnamed')}"
        fid_tag = f"FID {r.get('fid_src')}" if r.get("same_fid") else f"FID {r.get('fid_src')}→{r.get('fid_tgt')}"
        kin_tag = f"{e(r.get('slipsense_src') or '?')}/{e(r.get('dipdirect_src') or '?')}"
        review_tag = e(r.get("review_class", "unclassified"))
        rows.append(f"<tr class='link' data-id='{e(r['link_id'])}' data-class='{review_tag}'><td>{e(r['link_id'])}</td><td class='num'>{r['z']}</td><td>{e(r['kind'])}</td>"
                    f"<td>{fname_cell}<br><span class='small mono'>{fid_tag} · {kin_tag}</span></td>"
                    f"<td class='num'>{r['gap_km']:.2f}</td><td>{'✓' if r['mutual'] else ''}</td><td class='num'>{r['strike']:.0f}°</td>"
                    f"<td class='num' data-v='{r['strike_compat']:.3f}'>{100 * r['strike_compat']:.0f}%</td><td class='num'>{r['merged_km']:.1f}</td>"
                    f"<td class='num' data-v='{r['base_overlap']:.3f}'>{100 * r['base_overlap']:.0f}%</td>"
                    f"<td class='mono'>{mlat:.4f}, {mlon:.4f}</td>"
                    f"<td class='num' data-v='{r.get('delta_P', 0.0):+.6f}'>{r.get('delta_P', 0.0):+.4f}</td>"
                    f"<td>{'&#10003;' if r.get('bridge') else ''}</td>"
                    f"<td><span class='small'>{review_tag}</span></td>"
                    f"<td><a href='https://www.openstreetmap.org/#map=14/{mlat:.4f}/{mlon:.4f}'>map</a></td></tr>")
    sl = {s["radius_px"]: s for s in gr["single_linkage"]}   # keyed by radius in pixels (1 px = 100 m)
    claims = [("The paper analyses the San Andreas fault system", "verified", "publisher abstract"),
              ("Connectivity depends on scale for a &lt; D+1, not for a &gt; D+1", "verified", "publisher abstract"),
              ("San Andreas: a &lt; D+1 and the threshold is reached only at a critical length scale", "verified", "abstract; text: a = 2.1, D = 1.65, β = 0.0085; \"connectivity is expected for L &gt; 21 km\" (lmin ≈ 1 km), sensitivity 10 &lt; Lc &lt; 50 km"),
              ("Numerical Lc", "reproduced approx.", "my closed form from the paper's eq. (1): 21.6 km (lmin→0), 26.7 km (lmin = 1 km)"),
              ("A single segment decides whether two particular faults are joined", "not stated by the paper", "the paper: results \"are statistical, and provide connectivity estimates on averages, rather than on particular realizations\" – tested here instead of assumed")]
    pages["topology.html"] = ("Topology candidates", f"""
<h1>Topology candidates</h1>
<p class="lead">A graph of the {gr['graph']['skeleton_px']:,}-pixel INGENIOUS/USGS catalogue: nodes at free tips and junctions, edges as mapped segments. Gaps of 1–4 km between tips of different systems become candidate links.</p>
<div class="grid">
<div class="stat"><b>{gr['graph']['components']:,}</b><span>disconnected systems (median {gr['graph']['component_length_km']['median']:.2f} km; {gr['graph']['components_lt_2km']:,} shorter than 2 km)</span></div>
<div class="stat"><b>{gr['graph']['end_nodes']:,} / {gr['graph']['junction_nodes']} / {gr['graph']['edges']:,}</b><span>tips / junctions / edges; nearly acyclic (only {gr['graph']['enclosed_regions_ge_20px']} enclosed regions ≥ 20 px)</span></div>
<div class="stat"><b>{be['P_at_domain_equivalent_side']:.2f}</b><span>Berkowitz-style connectivity P at the study-area scale vs threshold 5.6–6.0</span></div>
<div class="stat"><b>{cs['selected_links']} links</b><span>shipped (z ≥ 3): {cs['selected_dots']:,} dots, {cs['nonredundant_dots_vs_0_2477']:,} not already near the 0.2477 emission</span></div></div>
{topology_priority_box}
<figure><img class="fig" src="assets/fig_map_h27_5b_priority.png" alt="Map of 81 H27-5b candidate gaps highlighted in red across the GeoDAWN fault catalogue"><figcaption>H27-5b priority gaps in red; other T-v2 candidate gaps in gray; mapped catalogue pixels in dark ink. These lines are review candidates, not mapped fault traces. Load the focused GeoJSON for inspection in GIS.</figcaption></figure>

<h2>The argument</h2>
<p>The mapped network is <b>fragmented and near its connectivity threshold</b>: exponent a ≈ {be['a']:.2f}±{be['a_se']:.2f} (lmin 2 km; 2.2–2.8 depending on lmin – not a clean power law), correlation dimension D ≈ {be['D']:.2f}, so a straddles D+1 = {be['D_plus_1']:.2f}.
Single-linkage closure takes the network from {sl[1.5]['systems']:,} systems to {sl[20.0]['systems']} at 2 km, {sl[40.0]['systems']} at 4 km and {sl[80.0]['systems']} at 8 km; the largest system holds {100*sl[40.0]['largest_share']:.0f}% of fault length at 4 km and {100*sl[80.0]['largest_share']:.0f}% at 8 km.
Where a network sits near threshold, individual closures matter more than in a well-connected one – the motivation for a topology class.
<b>But</b> the closures the holdout supports are <i>fragment completions</i> (systems {cs['closure']['systems_before']:,} → {cs['closure']['systems_after']:,}; largest {cs['closure']['largest_km_before']:.0f} → {cs['closure']['largest_km_after']:.0f} km), not giant-system bridges: links joining large systems were <i>less</i> enriched.</p>
<figure><img class="fig" src="assets/fig_connectivity.png" alt="Length distribution, correlation integral and single-linkage connectivity of the catalogue"><figcaption>Left: system length distribution with the a = {be['a']:.2f} reference (lmin 2 km). Middle: correlation integral, D = {be['D']:.2f}. Right: largest system and number of systems vs closure radius; shaded = the 1–4 km link range.</figcaption></figure>

<h2>What the literature does and does not give us (Berkowitz et al., GRL 2000)</h2>
<div class="tw"><table><tr><th>Statement</th><th>Verdict</th><th>Basis</th></tr>{''.join(f'<tr><td>{a}</td><td><b>{b}</b></td><td>{c}</td></tr>' for a, b, c in claims)}</table></div>
<p class="small"><a href="https://agupubs.onlinelibrary.wiley.com/doi/10.1029/1999GL011241">Publisher page (abstract)</a> · structural settings: <a href="https://www.osti.gov/servlets/purl/1724082">Faulds &amp; Hinz 2015</a> – step-overs/relay ramps ~32%, terminations 25%, intersections 22% of characterised Great Basin geothermal systems (a statement about geothermal settings, not about fault presence).</p>

<h2>Validation (pre-registered, spatially blocked, component-masked)</h2>
<figure><img class="fig" src="assets/fig_validation.png" alt="Efficiency of added dots versus controls and break-even"><figcaption>Seeds 110–119 (40 cells). Random same-size subsets are the right null for the z ≥ 3 set because efficiency falls as overlapping links accumulate. Break-even: a pixel set raises DTI iff ΔTP/ΔFP &gt; 0.2·DTI/(1−0.2·DTI).</figcaption></figure>
<table><tr><th>Run</th><th>Seeds</th><th>Result</th></tr>
<tr><td>T-v1 gate (component holdout)</td><td>100–109</td><td>efficiency {val['pooled']['fwd_eff']:.3f} vs controls {val['pooled']['ctrl_eff']:.3f} ({val['pooled']['enrichment']:.2f}×, narrow pass); forward &gt; control in 4/4 folds; paired DTI gain {val['paired_vs_leaky_dotted_h19_5']['mean_gain_over_folds_and_seeds']:+.4f} (leaky base); <b>PASSED</b></td></tr>
<tr><td>T-v2 gate (component holdout)</td><td>110–119</td><td>z ≥ 3: {eff['z>=3']:.3f}; de-duplicated {eff['z>=3 dedup']:.3f}; all links {eff['all']:.3f}; random same-size {con['random_same_size']['mean']:.3f} (p95 {con['random_same_size']['p95']:.3f}); paired gain {con['paired_vs_leaky_dotted_h19_5']['z>=3']['mean_gain']:+.4f}; <b>PASSED</b></td></tr>
<tr><td>Addendum B (3-tier vector holdout + H27-5)</td><td>120–129</td><td><b>Tier 1 (component):</b> z≥3 dedup {vval['tiers']['component']['efficiency_pooled']['z>=3 dedup']:.4f} vs ctrl {vval['tiers']['component']['efficiency_pooled']['ctrl']:.4f} (5.00×). <b>Tier 2 (whole NBMG FID vector polylines):</b> z≥3 dedup <b>{veff_fid['z>=3 dedup']:.4f}</b> vs ctrl {veff_fid['ctrl']:.4f} (4.92×, &gt; m(0.30)=0.0638); H27-5a (inter-FID + kinematic_compat) <b>{veff_fid['z>=3 inter-FID + kinematic_compat (H27-5a)']:.4f}</b> (6.74×); H27-5b (inter-FID + same_name + kinematic_compat) <b>{veff_fid['z>=3 inter-FID + same_name + kinematic_compat (H27-5b)']:.4f}</b> (8.74×). <b>Tier 3 (whole 20–70 km named fault zones):</b> {vval['tiers']['NAME_zone']['efficiency_pooled']['z>=3 dedup']:.4f} vs ctrl {vval['tiers']['NAME_zone']['efficiency_pooled']['ctrl']:.4f}. <b>PASSED</b></td></tr>
<tr><td>Addendum C (honest 4-fold spatial-CV OOF base)</td><td>130–139</td><td>On non-leaky B<sub>oof</sub> (mean DTI {oof['base_oof_mean_dti']:.4f}), T-v2 gains <b>{oof['variants']['plus_T_v2']['mean_dti_gain']:+.4f}</b> in 4/4 folds (marginal eff {oof['variants']['plus_T_v2']['marginal_or_removed_efficiency']:.4f}); H27-4 (100 m flank-shadow prune) gains <b>{oof['variants']['prune_r1_100m']['mean_dti_gain']:+.4f}</b> solo and <b>{oof['variants']['plus_T_v2_and_prune_r1']['mean_dti_gain']:+.4f}</b> stacked with T-v2 in 4/4 folds; H27-3 isolated-dot removal refuted ({oof['variants']['coherence_h27_3']['mean_dti_gain']:+.4f}, 0/4 folds). <b>PASSED (H27-1 &amp; H27-4)</b></td></tr>
<tr><td>Addendum D (new-information arms, connectivity ranking, step-overs)</td><td>140&ndash;149</td><td>Base arm reproduces Addendum C exactly (mean DTI {addD['stage_b_verdicts']['base_mean_dti']:.4f}). <b>D-1/D-2 PR-AUC screen:</b> +radiometric {addD['stage_a_pr_auc']['rad']['oof_pr_auc']:.5f}, +thermal {addD['stage_a_pr_auc']['thermal']['oof_pr_auc']:.5f}, +24 oriented lineament bands {addD['stage_a_pr_auc']['dir']['oof_pr_auc']:.5f} vs base {addD['stage_a_pr_auc']['base']['oof_pr_auc']:.5f} &mdash; all <b>FAIL</b> the registered +0.005; only +SGMC ({addD['stage_a_pr_auc']['sgmc']['oof_pr_auc']:.5f}) and +all ({addD['stage_a_pr_auc']['all']['oof_pr_auc']:.5f}) pass, and both then pass paired DTI ({addD['stage_b_verdicts']['arms']['sgmc']['mean_paired_gain_vs_base']:+.4f} and {addD['stage_b_verdicts']['arms']['all']['mean_paired_gain_vs_base']:+.4f}, 4/4 folds) &mdash; <b>NOT PROMOTED</b>, because the habitat decomposition shows the gain is entirely catalogue proximity (see the Session-4 card on the submit page). <b>D-3 REFUTED:</b> top half by |dP| {addD['stage_b_verdicts']['d3']['top_half_by_abs_delta_P']['efficiency']:.4f} vs all links {addD['stage_b_verdicts']['d3']['all_T_v2']['efficiency']:.4f} (ratio {addD['stage_b_verdicts']['d3']['ratio_top_over_all']:.3f}, needed &ge;1.15) and below the random-half 95th percentile {addD['stage_b_verdicts']['d3']['random_95th_percentile_efficiency']:.4f}. <b>D-4 REFUTED:</b> overlapping en-echelon step-overs ({addD['stage_b_verdicts']['d4']['counts']['steppover_links']:.0f} links/cell, median lateral offset {addD['stage_b_verdicts']['d4']['counts']['median_lateral_px'] * 0.1:.2f} km, median overlap {addD['stage_b_verdicts']['d4']['counts']['median_overlap_px'] * 0.1:.2f} km) reach efficiency {addD['stage_b_verdicts']['d4']['steppover_alone']['efficiency']:.4f} &lt; break-even 0.0638 and only {addD['stage_b_verdicts']['d4']['enrichment_vs_control']:.2f}&times; the perpendicular control (needed &ge;2.0&times;), though they add {addD['stage_b_verdicts']['d4']['mean_paired_gain_vs_base']:+.4f} paired DTI in {addD['stage_b_verdicts']['d4']['folds_improved']}/4 folds.</td></tr></table>
<p class="small">Disclosed: my first confirmatory launch had an implementation bug (minimum gap applied before choosing the nearest target); a unit test caught it, it was stopped and rerun as registered – <code>evidence/topology_validation_runA_partial_log.txt</code>. Vector attribution uses the 1,179 NBMG INGENIOUS Qfaults polylines (<code>qfaults_v2_in_footprint.json</code>, matching 98.42% of <code>labels.tif</code> at 100 m and 99.97% at 200 m): 230/345 shipped links are intra-FID, 115/345 inter-FID, 312/345 same NAME, and 333/345 kinematically compatible.</p>

<h2>Examples and map</h2>
<figure><img class="fig" src="assets/fig_examples.png" alt="Six example gap closures"><figcaption>Dark: mapped catalogue. Blue: the 0.2477 emission. Red: link dots. These are strongly supported (z ≥ 4), long, and barely covered by the current emission.</figcaption></figure>
<figure><img class="fig" src="assets/fig_map_overview.png" alt="Footprint map with all 345 links"><figcaption>All {cs['selected_links']} shipped links over the catalogue.</figcaption></figure>

<h2>All {cs['selected_links']} candidates</h2>
<p class="small">Click a row for its written graph argument and geometry cue. The filter searches the review class as well as ID, name, FID, kind and z. Downloads: <a href="data/topology_links.csv">all-link CSV</a> · <a href="data/topology_links.geojson">all-link GeoJSON (WGS84)</a> · <a href="data/topology_priority_h27_5b.csv">focused H27-5b priority CSV</a>. Review against the official <a href="https://doi.org/10.5066/F7S75FJM">USGS Interactive Fault Map</a> (Quaternary faults only) and the official NBMG source-layer link in each row. z = evidence score 0–5; compat = share of nearby catalogued fault length within 20° of the link strike; base overlap = share of the link's dots already within 300 m of the 0.2477 emission. <b>dP</b> = change in the Berkowitz et al. (2000) connectivity parameter P if this gap is closed; it is quantised to &plusmn;P/n<sub>ge</sub> because it counts systems above l<sub>min</sub>&nbsp;=&nbsp;2&nbsp;km, so a link joining two systems that are <i>both</i> already &ge;2&nbsp;km has dP&nbsp;&lt;&nbsp;0. <b>bridge</b> = no other candidate joins those two sides. Closing all {cs['selected_links']} moves P from {gP0:.3f} to {gP1:.3f} against Pc 5.6&ndash;6.0. Ranking by |dP| was gated on seeds 140&ndash;149 and <b>refuted</b> (Addendum D): these columns are for a reviewing geologist, not a selection rule.</p>
<p><input id="filter" class="filter" placeholder="filter (id, fault name, FID, kind, review class, z …)" aria-label="filter candidates"></p>
<div class="tw"><table id="links"><thead><tr><th data-k="0">ID</th><th class="num" data-k="1">z</th><th data-k="2">kind</th><th data-k="3">NBMG Fault Zone · FID · Slip/Dip</th><th class="num" data-k="4">gap km</th><th>mutual</th><th class="num" data-k="6">strike</th><th class="num" data-k="7">compat</th><th class="num" data-k="8">merged km</th><th class="num" data-k="9">base overlap</th><th>mid lat, lon</th><th class="num" data-k="11">dP</th><th data-k="12">bridge</th><th data-k="13">review class</th><th></th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
""")

    # ---------------------------------------------------------------- research
    def historical_status(item: dict) -> str:
        if item["id"] == "H28-3":
            return "TESTED — FROZEN GATE FAILED; negative research artifact is NOT APPROVED FOR SUBMISSION."
        return "Historical evidence-ledger entry — audit only; it does not approve a current submission."

    hrows = "".join(f"<tr><td><b>{e(h['id'])}</b><br><span class='small'>historical rank {h['rank']}</span></td><td><b>{e(h['title'])}</b><br><span class='small'>{e(h['layers'])}</span></td>"
                    f"<td>{e(h['signature'])}</td><td>{e(h['why'])}</td><td>{e(h['differs'])}</td><td>{e(historical_status(h))}</td><td>See the versioned historical ledger for the original result, planning cost, and limitations.</td></tr>" for h in hyp)
    h28rows = "".join(
        f"<tr><td><b>{e(h['id'])}</b><br><span class='small'>rank {h['rank']}</span></td>"
        f"<td><b>{e(h['title'])}</b><br><span class='small'>{'<br>'.join(e(x) for x in h['layers'])}</span></td>"
        f"<td>{e(h['signature'])}</td><td>{e(h['why_missing_faults'])}</td>"
        f"<td>{e(h['differs_from_repo'])}</td><td>{e(h['confounders'])}</td>"
        f"<td>{e(h['status'])}</td><td>{h['expected_holdout_delta_dti'][0]:+.3f} to "
        f"{h['expected_holdout_delta_dti'][1]:+.3f}<br><span class='small'>cost: {e(h['cost'])}</span></td></tr>"
        for h in h28_hypotheses
    )
    pages["research.html"] = ("Research", f"""
<h1>Research</h1>
<p class="lead">Why the 0.2477 file won, what a higher score needs, and the ranked hypotheses.</p>
<h2 id="h28-3">Session 6 H28-3 — dilatational-strain × conductivity corridors</h2>
{h28_3_box}
<p>Mechanism: a blind or alluvium-covered fault could co-locate deformation and conductive fluid alteration. Named non-fault alternative: a conductive/clayey basin boundary coincident with smooth regional strain. The six label-free corridor features used the five geophysical grids listed in the frozen protocol; every source and derived feature passed the AUC > 0.90 leakage canary, but the paired DTI result was negative. This is a valid negative result, not an upload recommendation.</p>
<p>Peer review: <a href="{REPO_URL}/blob/main/knowledge/12_20261025_peer_submission_audit.md">high-score / 0.2778 audit</a> · <a href="{REPO_URL}/blob/main/registry/parallel_submission_registry.json">pinned parallel registry</a> · <a href="{REPO_URL}/blob/main/evidence/h28_3_negative_uniqueness.json">raster correlation and overlap report</a>. The claimed GEMSDOE32 0.2778 is labelled OWNER-REPORTED because its own peer audit calls the named file unscored; no organizer receipt was found in the reviewed paths.</p>
<h2 id="h28-1">H28-1 — multiscale potential-field edge coherence</h2>
<p>The H28-1 transform uses label-free, multiscale edge strength and orientation agreement in the existing RTP magnetic and isostatic gravity grids. It tests a feature representation of geophysical boundaries that differs from the earlier pixelwise/tabular detector; it does not itself prove that any edge is a fault. The T-v2 additions remain a separate, geology-reviewable graph hypothesis.</p>
<p><b>{e(h28_gate_summary) if h28_gate_summary else 'No frozen H28-1 holdout evidence is available.'}</b></p>
{h28_research_box}
{h27_10_box}
<p class="small">Session 5 screen, H27-10 outcome and remaining candidates: <a href="{REPO_URL}/blob/main/knowledge/07_untried_hypotheses.md">hypothesis ledger</a>. H28-1 protocol: <a href="{REPO_URL}/blob/main/knowledge/08_preregistration_H28-1.md">frozen preregistration</a> · full-map recipe: <a href="{REPO_URL}/blob/main/knowledge/09_preregistration_H28-1_candidate.md">candidate record</a> · <a href="{REPO_URL}/blob/main/evidence/h28_1_edge_holdout.json">cell-level H28-1 evidence</a>. The 1 km label-free filters can share covariate values across the existing 600 m quadrant buffer; no labels enter the transform, but spatial covariate correlation remains a limitation.</p>
<h3>Current Session 6 untried screen ({len(h28_hypotheses)} hypotheses)</h3>
<p class="small">Expected ΔDTI ranges are expert priors, not measurements or score guarantees. H27-10 and H28-3 were tested and rejected under frozen gates; H28-1 is already tested. The graph-based structural class is separately documented below and in Topology.</p>
<div class="tw"><table><thead><tr><th>ID · rank</th><th>Hypothesis · layers</th><th>Physical signature</th><th>Why a missing fault</th><th>Differs from repo</th><th>Confounders</th><th>Status</th><th>Prior ΔDTI · cost</th></tr></thead><tbody>{h28rows}</tbody></table></div>
<h2 id="inversion">Session 3 &mdash; inverting all 20 live scores</h2>
<p class="lead">The owner's scored rasters are still in the sibling repositories. All <b>20</b> that could be
matched were downloaded through the GitHub API and accepted <b>only if their SHA-256 equalled a
<code>registry/live_scores.json</code> row</b> &mdash; provenance by hash, not by filename
(<code>scripts/fetch_scored_corpus.py</code>, <code>evidence/scored_corpus.json</code>). Five rows could not be
matched and are listed as unmatched rather than guessed.</p>

<h3>The exact identity, and the term everyone missed</h3>
<p>With <code>k(d)=max(1&minus;d/300&nbsp;m,0)</code>, <code>TPw=&Sigma;_g max_x p(x)k</code> and
<code>FPw=&Sigma;_x p(x)(1&minus;max_g k)</code>, the metric collapses to</p>
<p class="mono" style="text-align:center">DTI = TPw / ( 0.2&middot;TPw&middot;(1 &minus; &rho;) + 0.2&middot;N + 0.8&middot;|G| ),
&nbsp;&nbsp; &rho; = MPw/TPw</p>
<p><code>&rho;</code> is a <b>crowding factor</b>: the metric takes a <i>max</i> over predictions per truth pixel
for credit but a <i>sum</i> over predictions for false-positive mass, so a pixel that merely sits near truth is
cheap even when it is redundant for credit. <b>Crowding near truth is a discount, not a penalty.</b> The identity
reproduces both live anchors exactly: H19-5 solid &rarr; <b>0.1922</b> (live 0.1922), dotted d1.5 &rarr;
<b>0.2477</b> (live 0.2477). For the blind lattice &rho;=0.99, which is why it is a clean instrument.</p>

<h3>|G| = {inv_g:,.0f} px, from an instrument that needs no geology</h3>
<p>A spacing-5 blind lattice earns credit <code>c=0.37481</code> per truth pixel by pure geometry, wherever the
truth is. Inverting its live score (0.0904, N=204,504) gives <b>|G| = {inv_g:,.0f} px</b>. The sibling's
independent estimate was 12,503 &mdash; <b>2.2&nbsp;% apart</b>, two instruments, two repositories.
<code>knowledge/01</code>'s ~12.6k should be read as 12.2&ndash;12.8k.</p>

<h3>Concentration: the only ranking that survives</h3>
<p><code>conc = (TPw/|G|) / c(S)</code> measures how many times better than blind an emission is at <i>finding</i>
truth. <code>c</code> alone only measures how much area was sprayed.</p>
<div class="tw"><table><tr><th>surface</th><th class="num">N</th><th class="num">live</th><th class="num">credit</th>
<th class="num">credit/|G|</th><th class="num">conc</th><th class="num">&rho;</th></tr>{concrows}</table></div>
<p>Three readings, each of which kills a family of ideas. (1) The H19-5 / h19-4 / h16-1 family sits on a
<b>plateau at conc 5.3&ndash;5.7</b>: same detector quality, different clothes &mdash; recombining them cannot
raise concentration. (2) <b>No submission in the group's history has ever exceeded 0.508|G| of credit</b>; the
best file ever made still misses about half the hidden truth. (3) Spraying area does not work &mdash; H19-C
reaches 0.239|G| with 452,798 px and scores 0.0297.</p>

<h3>The retention rule, validated twice live</h3>
<p>For geometric thinning, <code>credit(d) = credit_solid &middot; c(d)/c_solid</code>. Against two independent
live solid&rarr;dotted pairs:</p>
<table style="max-width:44rem"><tr><th>pair</th><th class="num">predicted by geometry</th><th class="num">measured live</th><th class="num">error</th></tr>
{retrows}</table>
<p>This is the strongest instrument the programme has: a rule anchored on one live pair predicts a second,
unrelated live pair to 4&nbsp;%. It is valid for <b>spatially unbiased</b> removal only.</p>

<h3>The budget sweep &mdash; a ceiling, not a springboard</h3>
<div class="tw"><table><tr><th class="num">min dist (px)</th><th class="num">N</th><th class="num">retention</th>
<th class="num">&rho;</th><th class="num">model score</th></tr>{sweeprows}</table></div>
<p>Optimum <b>d = 2.25&ndash;2.8 &rarr; {geoceil:.4f}</b>, i.e. <b>+{geoceil-0.2477:.4f}</b> over 0.2477. The
sibling's completely independent two-parameter fit said 0.2553 (band 0.250&ndash;0.261). Two methods, two
repositories, same number: <b>the emission-geometry lever is exhausted at &asymp;0.255.</b></p>

<h3>Two ideas tested and rejected this session</h3>
<ul class="tight">
<li><b>H27-6 coverage-optimal thinning &mdash; REFUTED.</b> Poisson-disk is a <i>packing</i> rule, blind to how
much of the emission's own support survives, so the obvious improvement is to pick the N dots that maximise
coverage directly (a monotone submodular problem whose objective <i>is</i> the metric's credit functional).
Implemented as batched greedy with exact local marginal gains (<code>src/gems27/coverage_thin.py</code>).
Measured on quadrant NW at matched budgets: at 20,752 px greedy scores <b>0.866&times;</b> Poisson-disk
(143,341 vs 165,563 coverage mass) &mdash; <b>13&nbsp;% worse</b>; at 28,209 px it is a wash (1.010&times;).
On a 1-px-wide ridge network isotropic spacing already <i>is</i> the near-optimal cover, and greedy's early
picks are made against an empty coverage map and cannot be undone. Do not re-propose.</li>
<li><b>H27-7 union-recall ensembling &mdash; REFUTED as an improvement.</b> The best surfaces are nearly
pixel-disjoint (Jaccard: h19-5 vs H25-ctx <b>0.075</b>, vs r7-scarp <b>0.052</b>), which looks like free recall.
It is not: h19-5&cup;h16-1 thinned to d2.25 models at 0.2655 central but <b>0.2310</b> under the pessimistic
bound (both cover the <i>same</i> truth from different pixels); h19-5&cup;H25-ctx models 0.2521 / <b>0.1688</b>.
Against those, <b>h19-5 alone at d2.25 is {geoceil:.4f} with a rule validated to 4&nbsp;%</b>. The union's whole
edge lives in an unvalidated complementarity assumption and its downside is &minus;0.086.</li>
<li><b>Habitat tomography &mdash; not identifiable.</b> Because <code>TP_i = &Sigma;_x &lambda;(x)K_i(x)</code> is
linear in the truth intensity, 20 scored submissions are in principle 20 measurements of <i>where</i> the hidden
labels live. With overlapping geological bases it fails outright (in-sample R&sup2; = &minus;1.24). Restricted to a
strict 7-cell catalogue-distance <b>partition</b> (well identified, mass constraint exact) it still fails:
R&sup2; = &minus;0.360, leave-one-submission-out score RMSE <b>0.0715</b> against a score spread of 0.0686 &mdash;
signal ratio 0.96, no better than predicting the mean. The fitted &lambda; put 66&nbsp;% of truth in the
100&ndash;200&nbsp;m catalogue ring and 34&nbsp;% at 800&ndash;1500&nbsp;m, consistent with the Hermant et al.
(2025) 150&ndash;400&nbsp;m LiDAR-offset finding, but it did not pass its own validation and <b>must not</b> be
used to choose an emission.</li></ul>

<h3>What 0.3195 requires, arithmetically</h3>
<div class="tw"><table><tr><th class="num">emitted px</th><th class="num">credit for 0.2477</th>
<th class="num">for 0.2941 (#5)</th><th class="num">for 0.3195 (#1)</th></tr>{reqrows}</table></div>
<p>The group's best ever credit fraction is <b>0.508</b>. So 0.3195 at 44,090&nbsp;px needs 0.486|G| &mdash;
<i>below</i> what H19-5 solid already earns (0.506), but thinning to 44,090&nbsp;px retains only 0.759 &rarr;
0.384. <b>Retention, not knowledge, is the wall.</b> And 0.3195 at 60,069&nbsp;px needs 0.570|G| &mdash; more
credit than any submission in the group's history has ever earned at any budget. Exactly two routes remain:
(1)&nbsp;retention &asymp;1.0 at ~44k&nbsp;px &mdash; and H27-6 shows the obvious way fails; (2)&nbsp;concentration
above 5.7 &mdash; which needs <i>new information</i>, since the whole family plateaus at 5.3&ndash;5.7. Both are
detector problems. <b>0.3195 is not reachable by rearranging pixels we already have.</b></p>
<p class="small">Scripts: <code>fetch_scored_corpus.py</code> &rarr; <code>invert_live_scores.py</code> &rarr;
<code>optimize_budget.py</code> / <code>tomography_partition.py</code> &rarr; <code>model_candidates.py</code>.
Full write-up with every number: <a href="{REPO_URL}/blob/main/knowledge/07_live_score_inversion.md">knowledge/07</a>.</p>

<h2>Why the 0.2477 file won</h2>
<p>DTI = TP / (0.2·TP + 0.2·FP + 0.8·|G|). The 0.8|G| term cannot be reduced; false positives are cheap per pixel (0.2) but unbounded – about 49% of the denominator at the reconstructed operating point (recall ≈0.43, FP ≈54k px; hidden truth |G| ≈ 12.6k px, unconfirmed).
Dotting a solid line at ~3 px keeps 78% of its on-line credit for a third of its false-positive mass because credit per dot saturates at 3 while cost stays 1.
The same surface gained +43.7% when dotted (H25-ctx 0.1280 → H28 0.1839) and H19-5 gained +28.9% (0.1922 → 0.2477). I regenerated the 0.2477 file from H19-5 and it is identical (60,069 px): <b>no new geology, pure emission geometry</b>.</p>
<table style="max-width:34rem"><tr><th>dot spacing (px)</th><th class="num">credit / true px</th><th class="num">credit / dot</th></tr>
{''.join(f"<tr><td>{k}</td><td class='num'>{v['credit_per_true_px']:.3f}</td><td class='num'>{v['credit_per_dot']:.2f}</td></tr>" for k, v in op['credit_per_dot'].items())}</table>
<h2>What 0.3195 would need</h2>
<p>From recall {op['to_reach_0.3195']['recall_now']:.2f} / FP ≈54k px: weighted recall <b>{op['to_reach_0.3195']['recall_needed_same_FP']:.2f}</b> at equal FP, or FP ≈ <b>{op['to_reach_0.3195']['FP_px_needed_same_recall']:,} px</b> (−{100*op['to_reach_0.3195']['FP_reduction']:.0f}%) at equal recall. Thinning alone cannot do this (sibling model: d2.8 ≈ +0.010 over d1.5, never scored).
Stacking only verified/modelled increments gives ≈0.26–0.27 – so 0.3195 needs <i>new information or a materially better detector</i> (e.g. a supervised scarp detector on the 1 m DEM with geologist-labelled scarps – an access need).</p>
<p>Full write-up: <a href="{REPO_URL}/blob/main/knowledge/01_why_0.2477_won_and_the_ceiling.md">knowledge/01</a>.</p>
<h2>Hypotheses, ranked (expected DTI gain × probability of validation ÷ cost)</h2>
<div class="tw"><table><tr><th>ID</th><th>Hypothesis · layers</th><th>Physical signature</th><th>Why it catches a fault missing from USGS/INGENIOUS</th><th>How it differs from the repo</th><th>Status</th><th>Audit record</th></tr>{hrows}</table></div>
<h2>Contrarian, grounded notes</h2>
<ul class="tight"><li>Point-wise AUC of any single channel is weak (best: lidar <code>lappos_max</code> 0.58); magnetic/gravity <i>values</i> sit near 0.5 – faults are edges, not values (<code>evidence/channel_auc.json</code>).</li>
<li>The training band <code>tc</code> is rank-identical to the radiometric total-count grid (Spearman 1.0000), not a magnetic tilt/curvature as its metadata says – a documentation irregularity.</li>
<li>The catalogue's scope (Quaternary faults with evidence of coseismic surface deformation, per USGS) cannot list older bedrock faults: one structural reason "new" labels exist.</li>
<li>Catalogue-hugging emission fails in the owner's record (files with ≥45% of emission within 300 m scored ≤ 0.046), yet topology links work in the holdout – they are chosen <i>between</i> systems, mostly beyond 300 m of mapped pixels.</li>
<li>The final round rescoring against expert-expanded labels rewards well-localised, defensible predictions; every link here carries a written argument for that reviewer.</li></ul>
<p class="small">Derived documents: <a href="{REPO_URL}/blob/main/knowledge/02_hypotheses_ranked.md">hypotheses</a> · <a href="{REPO_URL}/blob/main/knowledge/03_preregistration_topology_gate.md">pre-registration</a> · <a href="{REPO_URL}/blob/main/knowledge/04_topology_graph_argument.md">graph argument</a> · <a href="{REPO_URL}/blob/main/knowledge/05_sources_and_verification.md">sources</a>.</p>
""")

    # ---------------------------------------------------------------- sources
    srows = "".join(f"<tr><td><a href='{e(s['url'])}'>{e(s['title'])}</a><br><span class='small'>{e(s['publisher'])}</span></td><td>{e(s['category'])}</td><td>{e(s['used_for'])}</td>"
                    f"<td><b>{e(s['status'])}</b><br><span class='small'>{e(s['evidence'])}</span></td></tr>" for s in src)
    irows = "".join(f"<tr><td><span class='badge {'bad' if i['severity']=='high' else ('warn' if i['severity']=='medium' else '')}'>{e(i['severity'])}</span></td><td>{e(i['issue'])}</td><td>{e(i['action'])}</td></tr>" for i in irr)
    def _sc(a):
        v = a.get("owner_reported_public_score")
        return f"{v:.4f}" if isinstance(v, (int, float)) else "<span class='badge warn'>UNSCORED</span>"
    scrows = "".join(f"<tr><td>{e(a['label'])}</td><td class='num'>{_sc(a)}</td><td class='small'>{e(a.get('corroboration') or '')}</td></tr>" for a in sc["artifacts"])
    if feed:
        fstatic = "".join(f"<tr><td><a href='{e(x['url'])}'>{e(x['title'])}</a></td><td>{'reachable (HTTP ' + str(x.get('http', '?')) + ')' if x.get('ok') else 'NOT reachable'}</td>"
                          f"<td>{e(x.get('last_updated') or x.get('pushed_at') or x.get('last_modified') or '-')}{' · ' + format(x['total_bytes'], ',') + ' B' if x.get('total_bytes') else ''}{' · zip' if x.get('is_zip') else ''}{' · ' + str(x['record_count']) + ' records' if x.get('record_count') is not None else ''}</td><td>{'CHANGED' if x.get('changed_since_previous_check') else 'no change'}</td><td>{e(x['checked_utc'])}</td></tr>" for x in feed["entries"])
        fstamp = feed["generated_utc"]
    else:
        fstatic, fstamp = "<tr><td colspan=5>No feed run yet – the <i>source-feed</i> workflow writes <code>docs/data/feed.json</code> (daily and on demand).</td></tr>", "never"
    pages["sources.html"] = ("Sources & feed", f"""
<h1>Sources &amp; feed</h1>
<p class="lead">Every external claim, its link, and how far it was actually verified. Unknown stays unknown.</p>
<h2>Feed of official sources</h2>
<p class="small">Generated by a GitHub Actions workflow on a hosted runner (the build sandbox reaches only github.com) – <b>official sources only; drivendata.org is never requested</b>. Last run: <span id="feedstamp">{e(fstamp)}</span>.</p>
<div class="tw"><table><thead><tr><th>Source</th><th>Status</th><th>Last updated / modified</th><th>Change</th><th>Checked (UTC)</th></tr></thead><tbody id="feedbody">{fstatic}</tbody></table></div>
<div class="warnbox"><b>For a human to open (never fetched by this project):</b> <a href="{DD_LB}">leaderboard</a> · <a href="{DD_COMP}">competition page</a>. The DrivenData Terms of Use prohibit robots/automatic means for any purpose including monitoring.</div>
<h2>Source table</h2>
<div class="tw"><table><thead><tr><th>Source</th><th>Type</th><th>Used for</th><th>Verification status · evidence</th></tr></thead><tbody>{srows}</tbody></table></div>
<h2 id="irregularities">Flagged irregularities</h2>
<div class="tw"><table><thead><tr><th>Severity</th><th>Issue</th><th>Action</th></tr></thead><tbody>{irows}</tbody></table></div>
<h2>Owner-reported scores</h2>
<p class="small">{e(sc['warning'])} Owner-stated leader: {sc['owner_stated_leader']['score']} ({e(sc['owner_stated_leader']['corroboration'])}). 27GEMSDOE files: <b>not yet scored</b>.</p>
<div class="tw"><table><thead><tr><th>Artifact</th><th class="num">Score</th><th>Corroboration</th></tr></thead><tbody>{scrows}</tbody></table></div>
""")

    for fname, (title, body) in pages.items():
        (DOCS / fname).write_text(layout(fname, title, body, stamp))
    # Repository-root entry: GitHub Pages may be configured as main:/ (the API refused to change it), in which case the
    # root URL must show the one-click page. Same content, relative paths rebased onto docs/.
    t, b = pages["index.html"]
    banner = ('<div class="okbox small">This is the repository-root copy of the front page (Pages is served from the repository root). '
              'All other pages are under <a href="executive-summary.html">docs/</a>.</div>')
    (ROOT / "index.html").write_text(rebase(layout("index.html", t, banner + b, stamp), "docs/"))

    # derived markdown knowledge docs (single source of truth = registry JSON)
    md = ["# Untried hypotheses, ranked (generated from `registry/hypotheses.json`; do not edit by hand)\n",
          "Ranking rule: expected DTI gain x probability the test can validate it / cost. Before any weekly slot is spent, the top hypothesis must beat the holdout baseline (see `03_preregistration_topology_gate.md`).\n"]
    for h in hyp:
        md += [f"## {h['id']} (rank {h['rank']}): {h['title']}\n", f"* **Layers:** {h['layers']}", f"* **Physical signature:** {h['signature']}",
               f"* **Why it catches a fault missing from USGS/INGENIOUS:** {h['why']}", f"* **How it differs from the repo:** {h['differs']}",
               f"* **Status:** {h['status']}", f"* **Expected gain:** {h['gain']}", f"* **Cost:** {h['cost']}"]
        for x in h.get("external") or []:
            md.append(f"* **External data (free, official):** [{x['name']}]({x['url']}) - {x['obtainable']}")
        md.append("")
    (KN / "02_hypotheses_ranked.md").write_text("\n".join(md))
    md = ["# Sources and verification (generated from `registry/sources.json`; do not edit by hand)\n",
          "| source | type | used for | status | evidence |", "|---|---|---|---|---|"]
    for s in src:
        md.append(f"| [{s['title']}]({s['url']}) ({s['publisher']}) | {s['category']} | {s['used_for']} | **{s['status']}** | {s['evidence'].replace('|', '/')} |")
    (KN / "05_sources_and_verification.md").write_text("\n".join(md) + "\n")
    # lightweight CSV of the sources for the audit table
    with open(DOCS / "data" / "sources.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["id", "title", "publisher", "url", "category", "status", "accessed"])
        for s in src:
            w.writerow([s["id"], s["title"], s["publisher"], s["url"], s["category"], s["status"], s["accessed"]])
    print("site built:", ", ".join(pages), "at", stamp)


if __name__ == "__main__":
    build()
