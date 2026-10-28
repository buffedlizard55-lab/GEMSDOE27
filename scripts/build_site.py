#!/usr/bin/env python3
"""Build the public status pages and executive summary from versioned evidence.

No network calls, downloads or model fitting. Readiness is fail-closed and never
selects or authorizes a competition slot. Historic score claims are unverified.
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
sys.path.insert(0, str(ROOT / "src"))
from gems27.readiness import publication_decision  # noqa: E402

REPO = "https://github.com/buffedlizard55-lab/GEMSDOE27"
PRE = f"{REPO}/blob/main/knowledge/30_lane_2026-10-27_preregistration.md"
H31_ID = "cf8e1bbef244"


def read(relative: str, default=None):
    path = ROOT / relative
    return json.loads(path.read_text()) if path.exists() else default


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def repo_link(relative: str) -> str:
    return f"{REPO}/blob/main/{relative}"


def verified_research_path(card: dict, gate: dict) -> tuple[str, str] | None:
    """Link only evidence-bound, byte-validated files located under docs/.

    Research downloadability is independent of scientific/slot authorization.
    A missing or modified TIFF must not be advertised as a valid download.
    """
    raster = card.get("raster") or {}
    if not isinstance(raster, dict):
        return None
    name, directory = raster.get("primary_allfinite"), raster.get("directory", "docs/downloads/research")
    if not isinstance(name, str) or not isinstance(directory, str) or not name:
        return None
    path = (ROOT / directory / name).resolve()
    if (not path.is_relative_to(DOCS.resolve()) or not path.is_file()
            or gate.get("actual_sha256") != raster.get("sha256")
            or not (gate.get("independent_byte_validation") or {}).get("pass")):
        return None
    return path.relative_to(DOCS).as_posix(), gate["actual_sha256"]


def card_summary(card: dict | None) -> tuple[str, str]:
    """Return a short HTML summary and matching Markdown for the H29-5 lane."""
    if not card:
        return (
            '<p><b>H29-5-PROXY:</b> no completed run card is present. The proposed proxy is not approved.</p>',
            "H29-5-PROXY: no completed run card is present; the proposed proxy is not approved.",
        )
    status = esc(card.get("verdict", "incomplete"))
    hold = card.get("holdout") or {}
    stats = hold.get("statistics") or {}
    if stats:
        ci = stats["candidate_ci95"]
        delta = stats["paired_delta_ci95"]
        control_ci = stats["control_ci95"]
        detail = (f"Candidate HOLDOUT-DTI {stats['candidate_pooled']:.5f}, 95% CI "
                  f"[{ci[0]:.5f}, {ci[1]:.5f}]; 32-band control HOLDOUT-DTI {stats['control_pooled']:.5f}, "
                  f"95% CI [{control_ci[0]:.5f}, {control_ci[1]:.5f}]; pooled change "
                  f"{stats['pooled_delta']:+.5f}, paired 95% CI [{delta[0]:+.5f}, {delta[1]:+.5f}]. "
                  f"The screening gate failed because the paired interval includes zero; "
                  f"{hold['n_withheld_positives_total']:,} withheld-positive occurrences; "
                  f"evaluator {hold['evaluator']}. Bootstrap intervals resample five repeated hides, "
                  "not independent faults; they do not estimate a leaderboard score.")
        canary = card.get("canary") or {}
        if canary.get("max_auc") is not None:
            detail += (f" Leakage canaries covered {canary.get('features_tested', 'unknown')} features; "
                       f"maximum direction-invariant AUC {canary['max_auc']:.4f} (threshold 0.90).")
    else:
        detail = "Efficacy evaluation is incomplete; no holdout estimate is available."
    gate = publication_decision(card, ROOT)
    verified = verified_research_path(card, gate)
    if verified:
        relative, actual_hash = verified
        download = (f'<p><a class="btn alt" href="{esc(relative)}" download>Download research GeoTIFF — '
                    'NOT APPROVED FOR SUBMISSION</a></p>')
        file_note = (f"Research-only file: `{relative}`; SHA-256 `{actual_hash}`. "
                     f"Submission name: `{card.get('submission_name', 'not supplied')}`. "
                     f"Short note: `{card.get('note_max_140_chars', 'not supplied')}`.")
        extra = f'<p class="small">{esc(file_note)}</p>'
    else:
        download = "<p>No new GeoTIFF is available: the run stopped before publication.</p>"
        file_note = ("No new GeoTIFF was written and no raster SHA-256 or validator result exists. "
                     f"Research label: `{card.get('submission_name', 'not supplied')}`. "
                     f"Research note: `{card.get('note_max_140_chars', 'not supplied')}`.")
        extra = f'<p class="small">{esc(file_note)}</p>'
    unique = card.get("uniqueness_vs_registry") or {}
    if unique.get("duplicate") and unique.get("max_dot_overlap_within_3px_euclidean") is not None:
        detail += (f" Final-dot uniqueness failed: {unique['max_dot_overlap_within_3px_euclidean']:.2%} "
                   f"within 3 pixels of {unique['duplicate']} (limit 70%); stopped after "
                   f"{unique['references_checked_before_stop']} of {unique['reference_count']} references; "
                   f"maximum absolute dot Spearman among those checked: {unique['max_dot_abs_spearman']:.4f}. "
                   f"Maximum absolute pre-placement surface Spearman among those screened: "
                   f"{unique['max_surface_abs_spearman']:.4f}. The pre-placement screen covered "
                   "the stated available reference set, not all submissions.")
    gate_text = ("Evidence gate passes, but no slot has been selected." if gate["ok_to_publish_as_submission"]
                 else "The fail-closed evidence gate does not approve submission.")
    return (
        f'<div class="card"><h3>H29-5-PROXY detrended-relief — {status}</h3>'
        f'<p>{esc(detail)}</p><p><b>{esc(gate_text)}</b> '
        f'<a href="{repo_link("evidence/relief_profile_run_card_20261027.json")}">Machine run card</a> · '
        f'<a href="{repo_link("evidence/relief_profile_registry_20261027.json")}">Uniqueness details</a>.</p>'
        f'{download}{extra}</div>',
        f"**H29-5-PROXY — {card.get('verdict', 'incomplete')}.** {detail} {gate_text} {file_note}",
    )


def h33_summary() -> tuple[str, str]:
    """Verdict for the unique TIFF generated by the H33-1 lane. Never a slot authorization."""
    card = read("evidence/h33_run_card_2026-10-27.json")
    if not card:
        text = "H33-1: no run card is present. Do not upload an older file in its place."
        return f'<div class="card"><h3>Generated TIFF</h3><p>{esc(text)}</p></div>', text
    hold = card.get("holdout") or {}
    paired = hold.get("paired_candidate_minus_B") or {}
    ci = paired.get("ci95") or []
    unique = card.get("uniqueness_vs_registry") or {}
    raster = card.get("raster") or {}
    dti = hold.get("pooled_candidate")
    control = hold.get("pooled_control_B")
    detail = (
        f"Generated file `{raster.get('primary_allfinite', 'missing')}` is unique versus the 12 pinned "
        f"focus-site rasters (max 3 px overlap {unique.get('max_dot_overlap_within_3px_euclidean', 'n/a')}; "
        f"pre-placement surface Spearman {unique.get('max_surface_spearman', 'n/a')}). "
        f"HOLDOUT-DTI {dti:.6f} versus base-32 control {control:.6f}; paired 95% CI "
        f"[{ci[0]:+.6f}, {ci[1]:+.6f}]; {hold.get('n_withheld_positives_total', 'n/a')} withheld-positive "
        f"occurrences; seeds 520–529; evaluator {hold.get('evaluator', 'n/a')}. "
        "That number is HOLDOUT-DTI, not an organizer score and not a live estimate. "
        "The frozen gate failed on every seed and every fold. "
        "The comparison is against base-32, not a matched current-best H31 control, and the card does not "
        "meet the current publication-gate fields. Either fact is enough to stop."
    )
    gate = publication_decision(card, ROOT)
    gate_text = ("Evidence gate passes, but no slot has been selected."
                 if gate["ok_to_publish_as_submission"]
                 else "The fail-closed evidence gate does not approve submission. NOT OK TO SUBMIT.")
    verified = verified_research_path(card, gate)
    if verified:
        relative, actual_hash = verified
        download = (f'<p><a class="btn alt" href="{esc(relative)}" download>Download research GeoTIFF — '
                    'NOT APPROVED FOR SUBMISSION</a></p>')
        file_note = (f"Research-only file: `{relative}`; SHA-256 `{actual_hash}`. "
                     f"Name: `{card.get('submission_name', 'not supplied')}`. "
                     f"Note: `{card.get('note_max_140_chars', 'not supplied')}`.")
    else:
        download = "<p>No generated GeoTIFF is available.</p>"
        file_note = "No generated GeoTIFF was found."
    html_block = (
        '<div class="card" style="border-left:5px solid #cf222e" id="h33-verdict">'
        '<h2 style="margin-top:0">NOT OK TO SUBMIT the generated TIFF</h2>'
        f'<p>{esc(detail)}</p><p><b>{esc(gate_text)}</b> '
        f'<a href="{repo_link("evidence/h33_run_card_2026-10-27.json")}">H33-1 run card</a> · '
        f'<a href="{repo_link("knowledge/31_h33_result_2026-10-27.md")}">Result note</a>.</p>'
        f'{download}<p class="small">{esc(file_note)}</p></div>'
    )
    return html_block, f"**H33-1 generated TIFF — NOT OK TO SUBMIT.** {detail} {gate_text} {file_note}"


def peer_relation_sentences(rel: dict, peers: dict) -> tuple[str, str]:
    """Plain-language sentences built only from evidence/peer_relations_20261028.json.

    Returns (GEMSDOE32 collar paragraph, identical-file paragraph). Every number is read from the
    byte-level audit (scripts/verify_peer_relations.py); owner-reported scores come from the peer
    registry and are labelled as such. If the audit is missing, the text says so.
    """
    subs = {(x["parent"], x["child"]): x for x in rel.get("strict_subset_relations", [])}
    s32_25 = subs.get(("g25_d28", "g32_h33_2_b2"))
    s31_25 = subs.get(("g25_d28", "g31_h27_4"))
    s32_31 = subs.get(("g31_h27_4", "g32_h33_2_b2"))
    if not (s32_25 and s31_25 and s32_31):
        return ("Byte-level peer relations are unavailable: run scripts/verify_peer_relations.py.", "")

    def score(pid: str) -> str:
        v = peers[pid].get("claimed_score")
        return f"{v:.4f}" if isinstance(v, (int, float)) else "unknown"

    removed = s32_25["removed_dots"]
    within2 = s32_25["removed_dots_catalogue_distance_px"]["<= 2px"]
    kept_min = s32_25["min_catalogue_distance_of_kept_dots_px"]
    collar = (
        "Measured on the pinned peer bytes (evidence/peer_relations_20261028.json): the owner-reported "
        f"GEMSDOE32 file ({s32_25['child_dots']:,} dots) is a strict subset of the GEMSDOE25 d=2.8 field "
        f"({s32_25['parent_dots']:,} dots). {'All' if within2 == removed else f'{within2:,} of'} {removed:,} removed dots lie within 2 px of a "
        f"catalogue cell, and the nearest kept dot is {kept_min} px away. GEMSDOE31 is the same field with "
        f"{s31_25['removed_dots']:,} dots within 1 px removed; GEMSDOE32 is GEMSDOE31 minus "
        f"{s32_31['removed_dots']:,} dots at 2 px. Owner-reported scores therefore step "
        f"{score('g25_d28')} → {score('g31_h27_4')} → {score('g32_h33_2_b2')} as the removed collar widens "
        "from none to 1 px to 2 px. That is one family with one raster per step and owner-reported values: a "
        "dose-response pattern, not proof of cause. Any further pruning of this family yields a subset, whose "
        "directed 3-px overlap with the GEMSDOE32 raster is 100% by construction, so it fails the 70% duplicate rule."
    )
    names = {x["id"]: x["repo"].rsplit("/", 1)[-1] for x in peers.values()}
    pairs = rel.get("identical_in_footprint_pairs", [])
    per = rel.get("per_peer", {})
    ident = " ".join(
        f"{names[a]} and {names[b]} have identical in-footprint dot values ({per[a]['dots_in_footprint']:,} dots; "
        f"SHA-256 {per[a]['file_sha256'][:12]}… vs {per[b]['file_sha256'][:12]}…)."
        for a, b in pairs
    )
    identity = ("Byte-level check: " + ident + " Different files with identical values are one submission under "
                "two names, not independent results.") if pairs else ""
    return collar, identity


def make_pages() -> tuple[dict[str, tuple[str, str]], str]:
    registry = read("registry/focus_sites_2026-10-26.json")
    peers = {x["id"]: x for x in read("registry/parallel_submission_registry.json")["entries"]}
    inventory = read("evidence/focus_inventory_20261027.json", {})
    lane = read("evidence/relief_profile_run_card_20261027.json")
    lane_html, lane_md = card_summary(lane)
    h33_html, h33_md = h33_summary()
    peer_rel_text, peer_identity_text = peer_relation_sentences(
        read("evidence/peer_relations_20261028.json", {}), peers)
    h31_hold = read("evidence/h31_s10_run_card_2026-10-26.json")["holdout"]
    h31_ci = h31_hold["pooled_dti_H31S_ci95"]
    h31_history = (f"The historical H31-1 HOLDOUT-DTI was {h31_hold['pooled_dti_H31S_candidate']:.6f}, "
                   f"95% CI [{h31_ci[0]:.6f}, {h31_ci[1]:.6f}], "
                   f"{h31_hold['n_withheld_positives_total']:,} withheld-positive occurrences, "
                   f"evaluator {h31_hold['evaluator']}. It used component/quadrant splits, not the H29-5-PROXY "
                   "whole-FID protocol; these values cannot be compared directly. The required matched H31 "
                   "comparison was not run.")
    rows, md_rows = [], []
    for site in registry["sites"]:
        peer = peers[site["peer_id"]]
        url = f'https://github.com/{peer["repo"]}/blob/{peer["commit"]}/{peer["path"]}'
        file_name = Path(peer["path"]).name
        score = f'{site["score"]:.4f}'
        rows.append(f'<tr><th>{esc(site["site"])}</th><td><a href="{esc(url)}">{esc(file_name)}</a>'
                    f'<br><span class="small">SHA-256 {esc(site["sha256"])}</span></td>'
                    f'<td>{score}</td><td>{esc(site["mechanism"])}</td>'
                    '<td>Historical registry entry; not new</td></tr>')
        md_rows.append(f'| {site["site"]} | [{file_name}]({url}) | {score} | '
                       f'{site["mechanism"]} | Already in registry; not new |')
    table = ('<div class="tw"><table><thead><tr><th>Site</th><th>Pinned historical raster / SHA-256</th>'
             '<th>Owner-reported value</th><th>Provenance / geometry</th><th>Uniqueness / action</th>'
             '</tr></thead><tbody>' + "".join(rows) + '</tbody></table></div>')
    table_md = ("| Site | Pinned historical raster | Owner-reported value | Geometry / provenance | Action |\n"
                "|---|---|---:|---|---|\n" + "\n".join(md_rows))
    sites = inventory.get("sites", [])
    checked = sum(len(s.get("files", [])) for s in sites)
    binary = sum(bool(x.get("binary_grid_valid")) for s in sites for x in s.get("files", []))
    invalid = checked - binary
    inventory_text = (f"The current nine-site inventory found {checked} TIFF paths: {binary} have verified Git blobs "
                      f"and finite binary values on the template grid; {invalid} cannot be treated as comparable "
                      "binary rasters (including a format test). Coverage is not globally complete, and an inventory "
                      "is not a list of all submitted files.") if checked else "The current nine-site inventory is not available."
    provenance = ("The score-to-file links below come from the 2026-10-26 pinned peer registry and owner/sibling "
                  "reports, not receipts. They are not organizer-confirmed. Older executive evidence assigns different "
                  "files or swaps the GEMSDOE28/GEMSDOE31 values; GEMSDOE25 and GEMSDOE36 file associations are also "
                  "uncertain. Treat every pairing and claimed maximum as provisional. The files are historical, not "
                  "new candidates, regardless of their reported values.")
    provenance = provenance + (" " + peer_identity_text if peer_identity_text else "")
    other_reports = ("Other user-reported values, not organizer-confirmed: GEMSDOE28 S21 0.0206; "
                     "GEMSDOE33 S33 0.0963; GEMSDOE36 KPL36 0.1647. File and score associations remain unverified.")
    rationale = ("The measured GEMSDOE32 positive-dot set is the GEMSDOE25 d=2.8 set after removing pixels within "
                 "two pixels of the known catalogue. Wider spacing and a catalogue collar plausibly reduce redundant "
                 "or low-yield prediction mass under a distance-weighted metric, but the hidden truth and organizer "
                 "score-to-file receipt are unavailable. The reported 0.2778 cannot be causally explained or "
                 "independently verified from geometry alone. A genuinely new method might do better, but there is "
                 "no validated evidence here that it will beat that value." + " " + peer_rel_text)
    hypothesis_table = """
<div class="tw"><table><thead><tr><th>Rank / hypothesis</th><th>Signature and missing-fault mechanism</th><th>Non-fault mimic / cost</th></tr></thead><tbody>
<tr><th>1 · detrended-relief profile (selected)</th><td>Cached detrended elevation → higher/lower-side slope contrast × transverse concavity × fixed tangential support; may find eroded or covered range-front breaks.</td><td>Incision, lithologic contacts and roads mimic it; medium cost. It is not mapped drainage or a validated fan apex.</td></tr>
<tr><th>2 · multiscale geophysical boundary</th><td>Cached K/Th/U ratios and magnetic gradients → consistent cross-scale boundary signs; alteration along a covered fracture could leave a boundary.</td><td>Soil/weathering and lithologic contacts mimic it; medium cost; not tested in this lane.</td></tr>
<tr><th>3 · paleothermal markers</th><td>Official GDR 1391 sinter/tufa and temperature observations → spatial/orientation support for concealed conduits.</td><td>Shoreline tufa and lateral flow mimic it; high cost; source packages unavailable here.</td></tr>
<tr><th>4 · conditioned 3DEP drainage</th><td>Raw 3DEP DEM → conditioned stream outlets and along-front alignment; deposition might hide a scarp.</td><td>Erosion, roads and stratigraphy mimic it; high cost; raw tiles/routing not available here.</td></tr>
</tbody></table></div>"""
    important = ('<div class="card" style="border-left:5px solid #cf222e"><h2 style="margin-top:0">'
                 'DO NOT SUBMIT — no candidate is approved</h2><p><b>NOT AUTHORIZED FOR A WEEKLY SLOT.</b> '
                 f'H31-1 <code>{H31_ID}</code> was reported already submitted at <b>0.2250 OWNER-REPORTED</b>; '
                 'there is no organizer receipt in this repository. Do not upload or rename it. '
                 'A valid TIFF, a local holdout pass, or a downloadable research file is not slot authorization.</p></div>')
    history_notice = (f'<p>{esc(provenance)}</p><p>{esc(inventory_text)} '
                      f'<a href="{repo_link("evidence/focus_inventory_20261027.json")}">Inventory and excluded files</a>.</p>')
    g32 = f'<h2>What might explain the reported GEMSDOE32 result?</h2><p>{esc(rationale)}</p>'
    action = ('<h2>Next decision</h2><p>Complete a matched, buffered whole-FID comparison against the current H31 '
              'architecture, strengthen geographic blocking and resolve incomplete registry coverage. Only then may '
              'a separate selector consider a weekly slot. Actual organizer outcome, weekly capacity and '
              'score-to-file receipts are not known here. No portal upload was made.</p>')
    # A static link/claimed hash can outlive a replaced or deleted research file.
    # Bind the decision table to the same independent byte re-read as the verdict.
    h33_card = read("evidence/h33_run_card_2026-10-27.json", {})
    verified = verified_research_path(h33_card, publication_decision(h33_card, ROOT))
    if verified:
        candidate_file, candidate_hash = verified
        candidate_download = (f'<a href="{esc(candidate_file)}" download>H33-1 all-finite GeoTIFF '
                              '— RESEARCH ONLY, DO NOT SUBMIT</a>')
        md_download = (f'[`H33-1 all-finite GeoTIFF — RESEARCH ONLY, DO NOT SUBMIT`]'
                       f'(docs/{candidate_file})')
        sha_html = f'<br><span class="small">SHA-256 {esc(candidate_hash)}</span>'
        sha_md = f' (SHA-256 `{candidate_hash}`)'
    else:
        candidate_download = 'No verified research TIFF available (missing or byte validation failed)'
        md_download = candidate_download
        sha_html = sha_md = ''
    decision_table = f'''<h2>Download and submission decision</h2>
<p>This is the decision table for files produced by this repository. An empty “estimated organizer score” is intentional: no local HOLDOUT-DTI can be converted honestly into an organizer score.</p>
<div class="tw"><table><thead><tr><th>File to download</th><th>Local evidence / estimated organizer score</th><th>Unique?</th><th>May be submitted?</th></tr></thead><tbody>
<tr><td>{candidate_download}{sha_html}</td><td><b>HOLDOUT-DTI 0.025211</b> vs control 0.041446; paired 95% CI [−0.017576, −0.014449]; evaluator gems27.metric.dti_binary v1 + whole-FID buffered holdout, 134,150 withheld-positive occurrences. <b>No justified organizer-score estimate.</b></td><td>Yes versus the 12 pinned focus-site rasters only (max 3 px overlap 0.000; scope-limited).</td><td><b>No — frozen holdout gate failed.</b></td></tr>
<tr><td>No currently approved file</td><td>No estimate</td><td>Not applicable</td><td><b>No — selector authorization is absent.</b></td></tr>
</tbody></table></div>'''
    decision_table_md = f'''## Download and submission decision

| File to download | Local evidence / estimated organizer score | Unique? | May be submitted? |
|---|---|---|---|
| {md_download}{sha_md} | HOLDOUT-DTI 0.025211 vs control 0.041446; paired 95% CI [−0.017576, −0.014449]; evaluator gems27.metric.dti_binary v1 + whole-FID buffered holdout, 134,150 withheld-positive occurrences. **No justified organizer-score estimate.** | Yes vs the 12 pinned focus-site rasters only (max 3 px overlap 0.000; scope-limited). | **No — frozen holdout gate failed.** |
| No currently approved file | No estimate | Not applicable | **No — selector authorization is absent.** |

'''
    home = f"""
<h1>GEMSDOE27 research and submission status</h1>
<p class="lead">A transparent audit of nine sites, one pre-registered geological proxy, and the gates between research and a competition submission.</p>
{important}
{h33_html}
{decision_table}
{lane_html}
<h2>Executive snapshot</h2>
<p>The highest owner-reported historical value in the selected nine-site registry is GEMSDOE32's 0.2778, not an independently verified score. No new projected live score is supplied.</p>
<p><a class="btn alt" href="executive-summary.html">Read the nine-site executive summary</a> <a class="btn alt" href="research.html">See the hypothesis and run card</a></p>
{g32}{action}
"""
    executive = f"""
<h1>Executive summary · nine focus sites</h1>
<p class="lead">Historical file provenance, reported values, uniqueness and what can safely be submitted.</p>
{important}{h33_html}{decision_table}{lane_html}
<h2>Best reported historical submission per site</h2>
{history_notice}{table}<p class="small">{esc(other_reports)}</p>
{g32}
<h2>Scope and confidence</h2><p>GEMSDOE25/GEMSDOE30 and GEMSDOE28/GEMSDOE31 have documented dot-identical pairs; renaming or thinning a prior file is not a new method. Historic claims of higher leaderboard values conflict and are unverified. Local validation reports HOLDOUT-DTI, not organizer performance.</p>
{action}
"""
    how = f"""
<h1>Submission instructions</h1>
<p class="lead">Use only after a separate selector authorizes an eligible candidate.</p>{important}
{h33_html}
<ol class="steps"><li>Read the current run card, the shared readiness audit and the selector decision. No weekly slot is authorized by an evidence pass alone.</li>
<li>Confirm the candidate is not already submitted, its full-scope pre-placement surface and post-placement dots meet the duplicate thresholds, and a matched current-best holdout comparison passes. If any evidence is missing, stop.</li>
<li>For an authorized candidate only, download the exact named <code>allfinite.tif</code> or its one-TIFF ZIP. Check the published SHA-256. The file must be float32, single-band, template-aligned and finite within [0,1] throughout, with zeros outside the footprint. A NaN-outside TIFF can trigger “Predicted values must be in range [0, 1]”. Passing our validator does not guarantee organizer acceptance.</li>
<li>Use the documented name and short note. Open the <a href="https://www.drivendata.org/competitions/306/">competition portal</a> yourself, check remaining slots and upload only if authorized. Record the organizer receipt and resulting score separately.</li></ol>
<p>There is currently no approved new TIFF. Do not re-upload H31-1 or any old file; do not treat a research link as an invitation to submit.</p>
{lane_html}
"""
    research = f"""
<h1>Research: hypotheses and evidence</h1>{important}
{h33_html}
<p>The following qualitative ranking was committed before feature computation; it is not a predicted score. Detailed transforms, inputs, distinctions, cost and stop conditions are in the <a href="{PRE}">pre-registration</a>.</p>
{hypothesis_table}
{lane_html}
<p>{esc(h31_history)}</p>
<p>The selected input is <code>det_elev</code>, a detrended owner-mirrored band: its gradient is not guaranteed to be downhill and the proxy is not drainage or an actual fan-apex inference. The model uses the shared cached 32-band stack, four added features, visible catalogue labels, a 600 m hidden-group training buffer, and an emitter blind to withheld truth. The DTI evaluator masks exact known pixels and scores the full 300 m kernel. Nearest-Qfault FID attribution is approximate; grouping is quadrant-stratified rather than an independent geographic block, and repeated catalogue hides do not establish performance on hidden competition faults.</p>
<h2>Earlier negative research</h2><p><b>H27-10 annulus: rejected</b> (<a href="{repo_link('evidence/h27_10_annulus_holdout_initial.json')}">initial</a> and <a href="{repo_link('evidence/h27_10_annulus_holdout.json')}">corrected</a> evidence). <b>H28-3 strain × conductivity: failed</b> (<a href="{repo_link('evidence/h28_3_strain_holdout.json')}">run evidence</a>). Neither is approved for submission or a weekly slot.</p>
<p><a href="{repo_link('evidence/h31_3_run_card_2026-10-26.json')}">H31-3 negative run</a> · <a href="{repo_link('evidence/h32_run_card_2026-10-26.json')}">H32 negative run</a> · <a href="{repo_link('knowledge/21_preregistration_H29-2_20261025.md')}">Earlier whole-FID preregistration</a>. Historic interpretations in archived files are not organizer confirmation and may conflict with this status page.</p>
"""
    topology = f"""
<h1>Fault topology and caveats</h1>{important}
<p>The catalogue-derived diagnostic assets are retained for audit, not as evidence of new faults. Connections and nearby vectors may reflect segmentation, mapping density, lithology or artifacts.</p>
<ul><li><a href="data/topology_links.geojson">Topology links (GeoJSON)</a></li><li><a href="data/topology_links.csv">Topology links (CSV)</a></li><li><a href="data/vector_faults_status.json">Vector-fault attribution status</a></li></ul>
<h2>Archived H27-5b priority class: 81 of 345 links</h2>
<p>This is a review-oriented classification of the existing 345 T-v2 links (1–4 km), not new ground truth or a required human inspection. Its exclusive classes are 230 same-FID, 81 H27-5b, 22 other-name compatible and 12 conflict/unknown. The class uses distinct attributed FIDs, shared non-unnamed names and a permissive kinematic screen; records in one compilation are not independent surveys.</p>
<table><thead><tr><th>Review class</th><th>Count</th></tr></thead><tbody><tr><td>same-FID multipart continuity</td><td>230</td></tr><tr><td>H27-5b inter-FID same-name compatible</td><td>81</td></tr><tr><td>other-name compatible</td><td>22</td></tr><tr><td>conflict or unknown</td><td>12</td></tr></tbody></table>
<p><a href="data/topology_priority_h27_5b.csv">Priority CSV</a> · <a href="data/topology_priority_h27_5b.geojson">Priority GeoJSON</a> · <a href="assets/fig_map_h27_5b_priority.png">Archived map</a> · <a href="data/topology_review_classes.json">Class rules and limitations</a>.</p>
<p>The prior graph-ΔP ranking and overlapping en-echelon step-over hypothesis were refuted as holdout-improvement signals; they are not a score or proof of transfer. Whole-FID experiments approximate source FIDs by nearest-vector attribution. Consult the <a href="https://web2.nbmg.unr.edu/arcgis/rest/services/Qfaults/Qfaults_INGENIOUS/MapServer/0">NBMG Qfaults service</a> for the original mapping layer and limitations.</p>
"""
    feed = read("docs/data/feed.json", {})
    irregularities = read("registry/irregularities.json", {}).get("items", [])
    latest_issues = [x for x in irregularities if x.get("id", "").startswith("IR-2026-10-27")]
    issue_rows = "".join(f'<li><b>{esc(x.get("id"))}:</b> {esc(x.get("issue"))} '
                         f'<i>{esc(x.get("action"))}</i></li>' for x in latest_issues)
    feed_rows = "".join(f'<li><a href="{esc(x.get("url", ""))}">{esc(x.get("title", x.get("id", "source")))}</a>'
                        f' — checked {esc(x.get("checked_utc", "not checked"))}; '
                        f'{"reachable at last check" if x.get("ok") is True else "not verified at last check"}</li>'
                        for x in feed.get("entries", []) if x.get("url"))
    sources = f"""
<h1>Sources and current-source feed</h1>{important}
<p>These are dated snapshots, not a live leaderboard. The latest recorded feed was generated {esc(feed.get('generated_utc', 'unknown'))}. A source listed below may have changed or be inaccessible since its last check. The feed does not request DrivenData; no organizer score or submission status is verified automatically.</p>
<ul>{feed_rows}</ul><p><a href="data/feed.json">Machine-readable feed</a> · <a href="data/feed_history.json">Feed history</a> · <a href="{repo_link('registry/sources.json')}">Source registry</a>.</p>
<h2>Primary references and data provenance</h2><ul>
<li><a href="https://github.com/drivendataorg/gems-prize-reference-solution">Official competition reference solution</a> — read from GitHub in this session; not evidence of this repository's scores.</li>
<li><a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN release</a>, <a href="https://gdr.openei.org/submissions/1391">DOE INGENIOUS GDR listing</a> and <a href="https://www.usgs.gov/3d-elevation-program">USGS 3DEP</a> — official source links, not newly downloaded here.</li>
<li><a href="{repo_link('data/manifest.json')}">Hash-pinned owner-mirror data manifest</a> — restored bytes are not independently organizer-authenticated.</li></ul>
<h2>Recorded irregularities</h2><p>These dated records describe the state when each audit was made; older status statements may since have changed.</p><ul>{issue_rows}</ul><p><a href="{repo_link('registry/irregularities.json')}">Full irregularity registry</a>.</p>
{history_notice}
"""
    pages = {"index.html": ("Status", home), "executive-summary.html": ("Executive summary", executive),
             "how-to-submit.html": ("Submission instructions", how), "research.html": ("Research", research),
             "topology.html": ("Topology", topology), "sources.html": ("Sources", sources)}
    markdown = f"""# Executive summary — GEMSDOE27 and nine focus sites

**DO NOT SUBMIT. NOT AUTHORIZED FOR A WEEKLY SLOT.** H31-1 `{H31_ID}` is already submitted according to the user, who reports 0.2250. There is no organizer receipt; do not resubmit it. No portal upload was made.

## New result and estimate

{decision_table_md}{h33_md}

{lane_md}

{h31_history}

The local HOLDOUT-DTI is not an organizer score or a prediction of the eventual leaderboard result. There is no justified estimated organizer score and no newly approved candidate.

## Best reported historical submission per site

{provenance}

{table_md}

{other_reports}

SHA-256 hashes and pinned sources are in [the focus-site registry]({repo_link('registry/focus_sites_2026-10-26.json')}). {inventory_text} See the [inventory]({repo_link('evidence/focus_inventory_20261027.json')}).

## GEMSDOE32: why it may look strong

{rationale}

## Research and next decision

The pre-registered [hypothesis ranking and protocol]({PRE}) distinguish the detrended-relief proxy from actual drainage or fan-apex inference. A matched current-best whole-FID comparison, stronger geographic blocking and complete uniqueness scope are still required before a separate weekly-slot selector. Read the [submission instructions]({REPO}/blob/main/docs/how-to-submit.html). Official organizer scores, current slot capacity and score-to-file receipts remain unknown.
"""
    return pages, markdown


def render(title: str, body: str, current: str, prefix: str = "") -> str:
    links = [("index.html", "Status"), ("executive-summary.html", "Executive summary"),
             ("research.html", "Research"), ("how-to-submit.html", "How to submit"),
             ("topology.html", "Topology"), ("sources.html", "Sources")]
    nav = " ".join(f'<a class="{"on" if filename == current else ""}" href="{prefix}{filename}">{label}</a>'
                   for filename, label in links)
    if prefix:
        body = re.sub(r'(?<=href=")(?!https?://|#|mailto:)([^" ]+)', lambda m: prefix + m.group(1), body)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} · GEMSDOE27</title>
<link rel="stylesheet" href="{prefix}assets/style.css"></head><body>
<header class="top"><div class="in"><a class="brand" href="{prefix}index.html">GEMSDOE27</a><nav>{nav}</nav></div></header>
<main>{body}</main><footer>Reproducible research · owner-reported values are unverified · no automatic portal access</footer></body></html>\n'''


def main() -> None:
    pages, markdown = make_pages()
    for name, (title, body) in pages.items():
        (DOCS / name).write_text(render(title, body, name))
    title, body = pages["index.html"]
    (ROOT / "index.html").write_text(render(title, body, "index.html", "docs/"))
    (ROOT / "EXECUTIVE_SUMMARY.md").write_text(markdown)
    print(f"Built {len(pages)} pages, root index, and executive summary from recorded evidence.")


if __name__ == "__main__":
    main()
