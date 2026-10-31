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
from urllib.parse import quote

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
        download = "<p>No byte-verified GeoTIFF is available from this card.</p>"
        file_note = ("No byte-verified research GeoTIFF is available from this card; it may be missing, modified, or incomplete. "
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


def candidate_peer_screen_summary(card: dict, report: dict) -> dict | None:
    """Return a byte-bound final-dot screen only when its candidate hash matches the run card."""
    card_hash = (card.get("raster") or {}).get("sha256")
    audit_candidate = report.get("candidate") or {}
    rows = report.get("candidate_vs_peers")
    if (not card_hash or audit_candidate.get("sha256") != card_hash or not isinstance(rows, dict)
            or not rows):
        return None
    max_overlap_id, max_overlap = max(
        rows.items(), key=lambda item: item[1].get("dot_overlap_within_3px", -1)
    )
    max_rho_id, max_rho_row = max(rows.items(), key=lambda item: abs(item[1].get("spearman", 0)))
    duplicates = [
        peer_id for peer_id, row in rows.items()
        if abs(row.get("spearman", 0)) > 0.90 or row.get("dot_overlap_within_3px", 0) > 0.70
    ]
    return {
        "n_peers": len(rows),
        "max_overlap": max_overlap.get("dot_overlap_within_3px"),
        "max_overlap_peer": max_overlap_id,
        "max_abs_binary_spearman": abs(max_rho_row.get("spearman", 0)),
        "max_spearman_peer": max_rho_id,
        "duplicates": duplicates,
    }


def h33_summary() -> tuple[str, str]:
    """Verdict for the unique TIFF generated by the H33-1 lane. Never a slot authorization."""
    card = read("evidence/h33_run_card_2026-10-27.json")
    if not card:
        text = "H33-1: no run card is present. Do not upload an older file in its place."
        return f'<div class="card"><h3>Generated TIFF</h3><p>{esc(text)}</p></div>', text
    hold = card.get("holdout") or {}
    paired = hold.get("paired_candidate_minus_B") or hold.get("paired_candidate_minus_Bc") or {}
    ci = paired.get("ci95") or []
    unique = card.get("uniqueness_vs_registry") or {}
    raster = card.get("raster") or {}
    final_screen = candidate_peer_screen_summary(
        card, read("evidence/peer_final_dot_uniqueness_20261028.json", {})
    )
    if final_screen:
        peer_names = {row["id"]: f'{row["repo"].rsplit("/", 1)[-1]} [{row["id"]}]'
                      for row in read("registry/parallel_submission_registry.json", {}).get("entries", [])}
        final_unique_text = (
            f"Post-placement re-audit on {final_screen['n_peers']} pinned rasters: max directed 3-px overlap "
            f"{final_screen['max_overlap']:.1%} vs {peer_names.get(final_screen['max_overlap_peer'], final_screen['max_overlap_peer'])}; "
            f"max |final binary Spearman| {final_screen['max_abs_binary_spearman']:.6f} vs "
            f"{peer_names.get(final_screen['max_spearman_peer'], final_screen['max_spearman_peer'])}; "
            f"no duplicate stop triggered. The stored pre-placement surface Spearman "
            f"{unique.get('max_surface_spearman', 'unknown')} is from the prior run, not recomputed in this audit."
        )
    else:
        final_unique_text = (
            "No hash-matched post-placement peer re-audit is available; the prior run-card uniqueness "
            f"result (max overlap {unique.get('max_dot_overlap_within_3px_euclidean', 'unknown')}) is historical only."
        )
    dti = hold.get("pooled_candidate")
    control = hold.get("pooled_control_B")
    detail = (
        f"Generated file `{raster.get('primary_allfinite', 'missing')}`. {final_unique_text} "
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


NINE_SITE_UNIQUENESS = {
    "GEMSDOE25": "Identical in-footprint dot values to GEMSDOE30 (byte-measured).",
    "GEMSDOE30": "Identical in-footprint dot values to GEMSDOE25 (byte-measured).",
    "GEMSDOE28": "Its H27-4 file is identical in dot values to GEMSDOE31 (byte-measured).",
    "GEMSDOE31": "Identical in dot values to GEMSDOE28 H27-4 (byte-measured).",
    "GEMSDOE32": "The d=2.8 family minus a 2 px catalogue collar; same lineage as GEMSDOE25.",
}


def _new_tiff_row(label: str, path: str) -> dict | None:
    """One decision row for a generated research TIFF, from its run card only."""
    card = read(path)
    if not card:
        return None
    gate = publication_decision(card, ROOT)
    verified = verified_research_path(card, gate)
    hold = card.get("holdout") or {}
    uniq = card.get("uniqueness_vs_registry") or {}
    paired = hold.get("paired_candidate_minus_B") or hold.get("paired_candidate_minus_Bc") or {}
    ci = paired.get("ci95") or hold.get("ci95") or []
    pooled = hold.get("pooled_candidate")
    control = hold.get("pooled_control_D", hold.get("pooled_control_B", hold.get("pooled_matched_control_Bc")))
    if isinstance(pooled, (int, float)) and isinstance(control, (int, float)) and len(ci) == 2:
        estimate = (f"HOLDOUT-DTI {pooled:.6f} vs control {control:.6f}; paired 95% CI "
                    f"[{ci[0]:+.6f}, {ci[1]:+.6f}]; {hold.get('n_withheld_positives_total', 'n/a'):,} "
                    "withheld-positive occurrences. Organizer score: none (no leaderboard estimate is computable).")
    else:
        estimate = "No holdout estimate recorded."
    local = uniq.get("local_prior_rasters") or {}
    local_max = local.get("max_dot_overlap_within_3px")
    worst = (local.get("worst") or [{}])[0].get("file", "a local prior raster")
    pinned_max = uniq.get("max_dot_overlap_within_3px_euclidean")
    if uniq.get("pass") is True:
        unique = (f"YES vs the 12 pinned rasters (max 3 px overlap {pinned_max:.3f}; surface abs-rho "
                  f"{uniq.get('max_surface_spearman', 0):.3f}) and {local.get('n_local_rasters', 0)} local prior "
                  f"rasters (max overlap {local_max:.3f}; limit 0.70). Scope is limited to these files.")
    elif uniq:
        if isinstance(local_max, float) and local_max > 0.70:
            unique = (f"NO - {local_max:.1%} of dots lie within 3 px of {worst} (limit 70%). "
                      f"Pinned-set max {pinned_max:.1%}. No TIFF was written.")
        else:
            unique = "NO - failed a uniqueness gate; no TIFF was written."
    else:
        unique = "Not evaluated."
    if verified:
        relative, actual_hash = verified
        file_cell = (f'<a href="{esc(relative)}" download>{esc(Path(relative).name)}</a>'
                     f'<br><span class="small">SHA-256 {esc(actual_hash)}</span>')
        file_md = f"[`{Path(relative).name}`]({relative}) SHA-256 `{actual_hash}`"
    else:
        file_cell = "None - no valid TIFF was written for download."
        file_md = "None - no valid TIFF was written for download."
    if gate["ok_to_publish_as_submission"]:
        ok = "Gates pass; still requires the separate weekly-slot selector."
    else:
        reasons = card.get("download_decision_reasons") or []
        if not reasons and hold.get("gate_efficacy_pass") is False:
            reasons = ["the frozen holdout efficacy gate failed"]
        reasons = reasons or gate["reasons"] or ["the evidence gate did not pass"]
        ok = f"NOT OK TO SUBMIT - {reasons[0]}"
    return {"label": label, "file_cell": file_cell, "file_md": file_md, "estimate": estimate,
            "unique": unique, "ok": ok}


def decision_board() -> tuple[str, str]:
    """Top-of-site table: the file to download, its estimate, uniqueness, and submit status."""
    rows = [r for r in (
        _new_tiff_row("GEMSDOE27 H29-XG joint gravity-magnetic cross-gradient (new, 2026-10-29)", "evidence/h29xg_run_card_2026-10-29.json"),
        _new_tiff_row("GEMSDOE27 H28-6 gravity persistence (new, 2026-10-28)", "evidence/h28_6_run_card_2026-10-28.json"),
        _new_tiff_row("GEMSDOE27 H33-1 buried-step complement (new, 2026-10-27)", "evidence/h33_run_card_2026-10-27.json"),
        _new_tiff_row("GEMSDOE27 H34-1 hot-station collinearity (new, 2026-10-31)", "evidence/h34_1_run_card_2026-10-31.json"),
    ) if r]
    registry = read("registry/focus_sites_2026-10-26.json", {"sites": []})
    peers = {x["id"]: x for x in read("registry/parallel_submission_registry.json")["entries"]}
    for site in registry["sites"]:
        peer = peers[site["peer_id"]]
        url = f'https://github.com/{peer["repo"]}/blob/{peer["commit"]}/{peer["path"]}'
        name = Path(peer["path"]).name
        uniq = NINE_SITE_UNIQUENESS.get(site["site"], "Already in the 12 pinned rasters; not new.")
        rows.append({
            "label": f'{site["site"]} historical best',
            "file_cell": f'<a href="{esc(url)}">{esc(name)}</a>',
            "file_md": f"[`{name}`]({url})",
            "estimate": f'OWNER-REPORTED {site["score"]:.4f} (not organizer-confirmed).',
            "unique": f"NO. {uniq}",
            "ok": "NO - historical file; do not resubmit.",
        })
    body = "".join(
        f'<tr><th>{esc(r["label"])}</th><td>{r["file_cell"]}</td><td>{esc(r["estimate"])}</td>'
        f'<td>{esc(r["unique"])}</td><td><b>{esc(r["ok"])}</b></td></tr>' for r in rows)
    html_block = (
        '<div class="card" id="download-decision" style="border-left:5px solid #cf222e">'
        '<h2 style="margin-top:0">Which file to download, and can it be submitted?</h2>'
        '<p><b>Short answer: no file is OK to submit right now.</b> Two generated TIFFs are unique against the pinned and local rasters but failed their holdout gates: H33-1 (research only, NOT OK) and H34-1 (hot-station collinearity, 2026-10-31, NOT OK; its holdout is far below its matched control and its cluster-null check fails). H28-6 and H29-XG wrote no TIFF. Historical '
        'files are already in the registry and are not new. Estimates are local HOLDOUT-DTI or owner-reported values, '
        'never leaderboard projections.</p>'
        '<div class="tw"><table><thead><tr><th>Site / file</th><th>File to download</th><th>Estimated score</th>'
        '<th>Unique?</th><th>OK to submit?</th></tr></thead><tbody>' + body + '</tbody></table></div></div>')
    md_rows = "\n".join(
        f'| {r["label"]} | {r["file_md"]} | {r["estimate"]} | {r["unique"]} | **{r["ok"]}** |' for r in rows)
    md = ("## Which file to download, and can it be submitted?\n\n"
          "**Short answer: no file is OK to submit right now.** Two generated TIFFs (H33-1 and H34-1) are unique against the pinned "
          "and local rasters but failed their holdout gates (H34-1 also fails its cluster-null check). H28-6 and H29-XG wrote no TIFF. Historical files are already in the registry. Estimates are local "
          "HOLDOUT-DTI or owner-reported values, never leaderboard projections.\n\n"
          "| Site / file | File to download | Estimated score | Unique? | OK to submit? |\n"
          "|---|---|---|---|---|\n" + md_rows + "\n")
    return html_block, md


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


def peer_uniqueness_summary(peer_id: str, screen: dict, peers: dict, relations: dict) -> str:
    """Summarize final-dot uniqueness for one historical raster within the pinned scope."""
    result = (screen.get("per_candidate") or {}).get(peer_id)
    if not isinstance(result, dict):
        return "UNKNOWN — no pairwise final-dot check; do not treat as unique."
    comparisons = result.get("comparisons")
    expected = max(0, len(peers) - 1)
    if not isinstance(comparisons, list) or len(comparisons) != expected or expected == 0:
        n = len(comparisons) if isinstance(comparisons, list) else 0
        return f"UNKNOWN — {n}/{expected} pinned comparisons; do not treat as unique."

    overlap = result.get("max_directed_overlap_within_3px")
    overlap_peer = result.get("worst_overlap_peer")
    abs_rho = result.get("max_abs_binary_spearman")
    corr_peer = result.get("worst_correlation_peer")
    def peer_name(pid: str) -> str:
        repo = peers.get(pid, {}).get("repo", pid).rsplit("/", 1)[-1]
        return f"{repo} [{pid}]"
    exact = [
        peer_name(b if a == peer_id else a)
        for a, b in relations.get("identical_in_footprint_pairs", [])
        if peer_id in (a, b)
    ]
    if result.get("pass_within_pinned_peer_set") is True:
        max_overlap = f"{overlap:.1%}" if isinstance(overlap, (int, float)) else "unknown"
        return (f"PASS within {expected} pinned final-dot rasters only (max directed 3-px overlap "
                f"{max_overlap}); this historical file is not a new submission and the registry is not global.")

    duplicates = result.get("duplicate_peers") or []
    overlap_text = f"{overlap:.1%} vs {peer_name(overlap_peer)}" if isinstance(overlap, (int, float)) else "unknown"
    rho_text = f"{abs_rho:.4f} vs {peer_name(corr_peer)}" if isinstance(abs_rho, (int, float)) else "unknown"
    exact_text = f" Exact in-footprint dot match: {', '.join(exact)}." if exact else ""
    return (f"NO — duplicate stop triggered vs {len(duplicates)}/{expected} pinned rasters; "
            f"max directed 3-px overlap {overlap_text}; max |binary Spearman| {rho_text}."
            f"{exact_text} Final-dot-only, pinned scope; not a global inventory.")


def make_pages() -> tuple[dict[str, tuple[str, str]], str]:
    registry = read("registry/focus_sites_2026-10-26.json")
    peers = {x["id"]: x for x in read("registry/parallel_submission_registry.json")["entries"]}
    inventory = read("evidence/focus_inventory_20261027.json", {})
    lane = read("evidence/relief_profile_run_card_20261027.json")
    lane_html, lane_md = card_summary(lane)
    h33_html, h33_md = h33_summary()
    decision_html, decision_md = decision_board()
    peer_relations = read("evidence/peer_relations_20261028.json", {})
    peer_rel_text, peer_identity_text = peer_relation_sentences(peer_relations, peers)
    peer_final_audit = read("evidence/peer_final_dot_uniqueness_20261028.json", {})
    peer_final_screen = peer_final_audit.get("pairwise_final_dot_screen", {})
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
        raw_path = quote(peer["path"], safe="/")
        url = f'https://github.com/{peer["repo"]}/blob/{peer["commit"]}/{raw_path}?raw=1'
        file_name = Path(peer["path"]).name
        score_status = peer.get("score_label", "OWNER-REPORTED")
        reported_value = f'{site["score"]:.4f} — OWNER-REPORTED'
        if "unresolved" in score_status.lower() or "unscored" in score_status.lower():
            score_note = score_status.removeprefix("OWNER-REPORTED").lstrip(" ;")
            reported_value += f" ({score_note})"
        estimate = "Unknown; no justified conversion to organizer score"
        uniqueness = peer_uniqueness_summary(site["peer_id"], peer_final_screen, peers, peer_relations)
        action_text = "Historical file; not new and not authorized for reuse"
        rows.append(
            f'<tr><th>{esc(site["site"])}</th><td><a href="{esc(url)}">Download {esc(file_name)}</a>'
            f'<br><span class="small">SHA-256 {esc(site["sha256"])}</span></td>'
            f'<td>{esc(reported_value)}</td><td>{esc(estimate)}</td>'
            f'<td>{esc(uniqueness)}</td><td>{esc(action_text)}</td></tr>'
        )
        md_rows.append(
            f'| {site["site"]} | [Download {file_name}]({url}) | {reported_value} | {estimate} | '
            f'{uniqueness} | {action_text} |'
        )
    table = (
        '<div class="tw"><table><thead><tr><th>Site</th><th>Pinned historical raster / SHA-256</th>'
        '<th>Owner-reported value (not a receipt)</th><th>Estimated organizer score</th>'
        '<th>Unique among pinned peers?</th><th>Submission decision</th>'
        '</tr></thead><tbody>' + "".join(rows) + '</tbody></table></div>'
    )
    table_md = (
        "| Site | Pinned historical raster | Owner-reported value (not a receipt) | "
        "Estimated organizer score | Unique among pinned peers? | Submission decision |\n"
        "|---|---|---|---|---|---|\n" + "\n".join(md_rows)
    )
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
                  "new candidates, regardless of their reported values. The 3-px screen compares final binary dot "
                  "rasters with the 12 pinned peer entries; the peers' pre-placement continuous surfaces are not "
                  "available, and this snapshot is not a complete global submission registry.")
    provenance = provenance + (" " + peer_identity_text if peer_identity_text else "")
    other_reports = ("Other OWNER-REPORTED values (not organizer-confirmed): GEMSDOE28 S21 0.0206; "
                     "GEMSDOE33 S33 0.0963; GEMSDOE36 KPL36 0.1647. File and score associations remain unverified.")
    highest_site = max(registry["sites"], key=lambda item: item["score"])
    highest_peer = peers[highest_site["peer_id"]]
    highest_status = highest_peer.get("score_label", "OWNER-REPORTED")
    highest_uniqueness = peer_uniqueness_summary(
        highest_site["peer_id"], peer_final_screen, peers, peer_relations
    )
    highest_report = (
        f"Highest listed historical claim: {highest_site['site']} {highest_site['score']:.4f} "
        f"OWNER-REPORTED (not ORGANIZER-CONFIRMED); registry file-status note: {highest_status}. "
        f"Its final-dot uniqueness check: {highest_uniqueness} It is not an eligible new submission."
    )
    rationale = ("The measured GEMSDOE32 positive-dot set is the GEMSDOE25 d=2.8 set after removing pixels within "
                 "two pixels of the known catalogue. Wider spacing and a catalogue collar plausibly reduce redundant "
                 "or low-yield prediction mass under a distance-weighted metric, but the hidden truth and organizer "
                 "score-to-file receipt are unavailable. The OWNER-REPORTED 0.2778 cannot be causally explained or "
                 "independently verified from geometry alone. A genuinely new method might do better, but there is "
                 "no validated evidence here that it will beat that value." + " " + peer_rel_text)
    hypothesis_registry = read("registry/next_hypotheses.json", {})
    hypothesis_rows = []
    for hypothesis in hypothesis_registry.get("hypotheses", []):
        layer_text = ", ".join(hypothesis.get("layers", []))
        def sentence(value: str) -> str:
            return str(value).strip().rstrip(".") + "."

        data_gate_text = (
            f"{sentence(hypothesis.get('cost', 'Cost unknown'))} "
            f"Data gate: {sentence(hypothesis.get('data_gate', 'not recorded'))}"
        )
        # Keep the official GDR listing directly clickable when that external-data idea is shown.
        data_gate_html = esc(data_gate_text).replace(
            "https://gdr.openei.org/submissions/1391",
            '<a href="https://gdr.openei.org/submissions/1391">DOE GDR 1391</a>',
        )
        official_sources = {
            "H27-16": '<a href="https://gdr.openei.org/submissions/1391">DOE GDR 1391 listing</a>',
            "H29-5": '<a href="https://www.usgs.gov/3d-elevation-program">USGS 3DEP</a>',
            "H28-6": '<a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN</a>',
            "H28-7": '<a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN</a>',
        }
        if hypothesis.get("id") in official_sources:
            data_gate_html += (
                f"<br><b>Official source link for manual review (not freshly verified here):</b> "
                f"{official_sources[hypothesis['id']]}"
            )
        expected_benefit = hypothesis.get(
            "expected_benefit", "Uncertain; no numerical improvement is established."
        )
        novelty_and_mimics = (
            f"{hypothesis.get('differs_from_repo', 'Difference from existing work not recorded')} "
            f"Non-fault mimics: {hypothesis.get('confounders', 'not recorded')}"
        )
        hypothesis_rows.append(
            "<tr>"
            f"<th>{hypothesis.get('rank', '?')} · {esc(hypothesis.get('id', ''))}: "
            f"{esc(hypothesis.get('title', 'Untitled'))}<br><span class=\"small\">"
            f"{esc(hypothesis.get('status', 'status unknown'))}</span></th>"
            f"<td><b>Layers:</b> {esc(layer_text)}<br><b>Signature:</b> "
            f"{esc(hypothesis.get('signature', 'not recorded'))}<br><b>Why potentially missing:</b> "
            f"{esc(hypothesis.get('why_missing_faults', 'not recorded'))}</td>"
            f"<td>{esc(novelty_and_mimics)}</td>"
            f"<td>{esc(expected_benefit)}<br><b>Implementation cost / data gate:</b> {data_gate_html}</td>"
            "</tr>"
        )
    hypothesis_table = (
        '<div class="tw"><table><thead><tr><th>Qualitative rank / untried formulation</th>'
        '<th>Layers, physical signature and missing-fault rationale</th>'
        '<th>Difference from repo / named non-fault mimics</th>'
        '<th>Expected HOLDOUT-DTI improvement / cost</th>'
        '</tr></thead><tbody>' + "".join(hypothesis_rows) + '</tbody></table></div>'
    )
    hypothesis_caveat = (
        "The ranking is the registry's qualitative expert-planning prior, not a measured or numeric "
        "DTI forecast. All expected gains are unknown. H29-5 refers here to the untested actual "
        "conditioned-drainage/fan-apex formulation, not the negative H29-5-PROXY. H27-16 requires "
        "official GDR packages absent from this checkout; the GDR host is outside this sandbox's "
        "network allowlist, so current availability and hashes were not verified. H29-5 actual routing "
        "needs unmodified DEM and verified outlet observations not present in the restored cache. "
        "Neither data-gated idea is viable in this session. H28-7 uses cached feature families, "
        "but the assigned method paragraph is missing; no experiment may be launched by guessing a lane."
    )
    important = ('<div class="card" style="border-left:5px solid #cf222e"><h2 style="margin-top:0">'
                 'DO NOT SUBMIT — no candidate is approved</h2><p><b>NOT AUTHORIZED FOR A WEEKLY SLOT.</b> '
                 f'H31-1 <code>{H31_ID}</code> was reported already submitted at <b>0.2250 OWNER-REPORTED</b>; '
                 'there is no organizer receipt in this repository. Do not upload or rename it. '
                 'A valid TIFF, a local holdout pass, or a downloadable research file is not slot authorization.</p></div>')
    history_notice = (f'<p>{esc(provenance)}</p><p>{esc(inventory_text)} '
                      f'<a href="{repo_link("evidence/focus_inventory_20261027.json")}">Inventory and excluded files</a>.</p>')
    g32 = f'<h2>What might explain the reported GEMSDOE32 result?</h2><p>{esc(rationale)}</p>'
    action = ('<h2>Next decision</h2><p>No new geological experiment was run: the current prompt says a single-method '
              'paragraph assigns the lane, but no such paragraph is present. Do not invent a lane. The <a '
              'href="research.html">three-formulation untried-hypothesis screen</a> is a qualitative planning aid; '
              'external-data blockers and missing assignment prevent testing. Next, obtain an explicit lane, '
              'preregister unused seeds, use the shared cached stack/evaluator/writer, run feature-alone leakage '
              'canaries, and compare a candidate against a same-split current-best control. Strengthen geographic '
              'blocking and resolve incomplete registry coverage. Only then may a separate selector consider a '
              'weekly slot. Actual organizer outcome, weekly capacity and score-to-file receipts are unknown. '
              'No portal upload was made.</p>')
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
    holdout = h33_card.get("holdout", {})
    paired = holdout.get("paired_candidate_minus_B", {})
    hold_ci = paired.get("ci95", [])
    candidate_dti = holdout.get("pooled_candidate")
    control_dti = holdout.get("pooled_control_B")
    if candidate_dti is not None and control_dti is not None and len(hold_ci) == 2:
        local_evidence = (
            f"HOLDOUT-DTI {candidate_dti:.6f} vs control HOLDOUT-DTI {control_dti:.6f}; "
            f"paired candidate-minus-control 95% CI [{hold_ci[0]:+.6f}, {hold_ci[1]:+.6f}]; "
            f"evaluator {holdout.get('evaluator', 'unknown')}; "
            f"{holdout.get('n_withheld_positives_total', 'unknown')} withheld-positive occurrences. "
            "No justified organizer-score estimate. HOLDOUT-DTI is not a leaderboard score."
        )
    else:
        local_evidence = "HOLDOUT-DTI not available; estimated organizer score unknown."
    h33_peer_screen = candidate_peer_screen_summary(h33_card, peer_final_audit)
    h33_old_unique = h33_card.get("uniqueness_vs_registry", {})
    if h33_peer_screen:
        h33_unique_text = (
            f"Yes within {h33_peer_screen['n_peers']} pinned final-dot rasters only: max directed 3-px overlap "
            f"{h33_peer_screen['max_overlap']:.1%}; max |final binary Spearman| "
            f"{h33_peer_screen['max_abs_binary_spearman']:.6f}. Saved pre-placement surface Spearman "
            f"{h33_old_unique.get('max_surface_spearman', 'unknown')} is from the prior run; no global guarantee."
        ) if not h33_peer_screen["duplicates"] else (
            f"No — duplicates vs {', '.join(h33_peer_screen['duplicates'])}."
        )
    else:
        h33_unique_text = "Unknown — no hash-matched post-placement peer screen; do not treat as unique."
    decision_table = f'''<h2>Download and submission decision</h2>
<p>This is the decision table for files produced by this repository. The organizer-score estimate is explicitly unknown: no local HOLDOUT-DTI can be converted honestly into a leaderboard score.</p>
<div class="tw"><table><thead><tr><th>File to download</th><th>HOLDOUT-DTI / organizer-score estimate</th><th>Unique?</th><th>May be submitted?</th></tr></thead><tbody>
<tr><td>{candidate_download}{sha_html}</td><td>{esc(local_evidence)}</td><td>{esc(h33_unique_text)}</td><td><b>No — frozen holdout gate failed. NOT OK TO SUBMIT.</b></td></tr>
<tr><td>No currently approved file</td><td>Unknown</td><td>Not applicable</td><td><b>No — selector authorization is absent.</b></td></tr>
</tbody></table></div>'''
    decision_table_md = f'''## Download and submission decision

| File to download | HOLDOUT-DTI / estimated organizer score | Unique? | May be submitted? |
|---|---|---|---|
| {md_download}{sha_md} | {local_evidence} | {h33_unique_text} | **No — frozen holdout gate failed. NOT OK TO SUBMIT.** |
| No currently approved file | HOLDOUT-DTI not available; estimate unknown | Not applicable | **No — selector authorization is absent.** |

'''
    home = f"""
<h1>GEMSDOE27 research and submission status</h1>
<p class="lead">A transparent audit of nine sites, one pre-registered geological proxy, and the gates between research and a competition submission.</p>
{decision_html}
{important}
{h33_html}
{decision_table}
{lane_html}
<h2>Executive snapshot</h2>
<p>{esc(highest_report)} The prompt cites conflicting USER-REPORTED leaderboard maxima of 0.3195 and 0.4413; no DrivenData page was accessed and neither is ORGANIZER-CONFIRMED here.</p>
<p><a class="btn alt" href="executive-summary.html">Read the nine-site executive summary</a> <a class="btn alt" href="research.html">See the untried hypothesis screen and run card</a></p>
{g32}{action}
"""
    executive = f"""
<h1>Executive summary · nine focus sites</h1>
<p class="lead">Historical file provenance, reported values, uniqueness and what can safely be submitted.</p>
{decision_html}{important}{h33_html}{decision_table}{lane_html}
<h2>Highest listed historical claim</h2>
<p>{esc(highest_report)} The task prompt cites 0.3195 and 0.4413 as current leaderboard maxima; these conflict and were not verified because the organizer site was not accessed.</p>
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
<p>The following three formulations remain untried in this repository's updated screen; the rank is qualitative, not a numerical DTI prediction. See the <a href="{repo_link('registry/next_hypotheses.json')}">machine-readable hypothesis ledger</a> and <a href="{PRE}">prior preregistration</a>. No new lane has been assigned in the current prompt.</p>
{hypothesis_table}
<p class="warnbox">{esc(hypothesis_caveat)}</p>
<h2>Previously tested negative H29-5-PROXY</h2>
{lane_html}
<p>{esc(h31_history)}</p>
<p>The tested H29-5-PROXY used <code>det_elev</code>, a detrended owner-mirrored band: its gradient is not guaranteed to be downhill and the proxy is not drainage or an actual fan-apex inference. It used the shared cached 32-band stack, four added features, visible catalogue labels, a 600 m hidden-group training buffer, and an emitter blind to withheld truth. The DTI evaluator masked exact known pixels and scored the full 300 m kernel. Nearest-Qfault FID attribution was approximate; grouping was quadrant-stratified rather than an independent geographic block, and repeated catalogue hides do not establish performance on hidden competition faults.</p>
<h2>Earlier negative research</h2><p><b>H28-6 gravity persistence: tested negative, not an untried hypothesis.</b> Its local final-dot overlap also exceeded the duplicate stop; no TIFF was written. <a href="{repo_link('evidence/h28_6_run_card_2026-10-28.json')}">H28-6 run card</a>. <b>H27-10 annulus: rejected</b> (<a href="{repo_link('evidence/h27_10_annulus_holdout_initial.json')}">initial</a> and <a href="{repo_link('evidence/h27_10_annulus_holdout.json')}">corrected</a> evidence). <b>H28-3 strain × conductivity: failed</b> (<a href="{repo_link('evidence/h28_3_strain_holdout.json')}">run evidence</a>). Neither is approved for submission or a weekly slot.</p>
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
    issue_dates = [re.match(r"IR-(\d{4}-\d{2}-\d{2})", x.get("id", ""))
                   for x in irregularities]
    # Show the two most recent dated batches so a new session never hides the previous session's records.
    recent_dates = set(sorted({match.group(1) for match in issue_dates if match}, reverse=True)[:2])
    latest_issues = [x for x in irregularities
                     if any(x.get("id", "").startswith(f"IR-{d}") for d in recent_dates)]
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

{decision_md}
**DO NOT SUBMIT. NOT AUTHORIZED FOR A WEEKLY SLOT.** H31-1 `{H31_ID}` is already submitted according to the user, who reports 0.2250. There is no organizer receipt; do not resubmit it. No portal upload was made.

## New result and estimate

On 2026-10-31 one preregistered experiment ran (H34-1, hot-station collinearity, seeds 900–909, `knowledge/45`). It is **negative**. Its cluster-preserving null check (Addendum A) shows the line count is not distinguishable from station clustering (ratio 0.97 total, 1.18 for three or more supporting stations; both need >1.5). Its holdout pooled HOLDOUT-DTI was 0.000526 against 0.025996 for the matched control, with 0 of 10 seeds positive. Part of that gap is sparseness: the candidate emitted 448 dots against a 37,654-dot budget. The file is downloadable for research only and is **NOT OK TO SUBMIT**. Full record: `knowledge/46_session21_review_2026-10-31.md`.

On 2026-10-29 one preregistered experiment ran (H29-XG, joint gravity–magnetic cross-gradient, seeds 800–809, `knowledge/39`). It is **negative**: its holdout efficacy gate failed against the matched control, and its dots broke the 70% local-overlap stop, so **no TIFF was written**. The earlier research files (H28-6 and H33-1) are also negative. Every file in the table is NOT OK TO SUBMIT. The decision table below is generated from the run cards. Its numbers are HOLDOUT-DTI, not organizer scores.

{decision_table_md}{h33_md}

{lane_md}

{h31_history}

The local HOLDOUT-DTI is not an organizer score or a prediction of the eventual leaderboard result. There is no justified estimated organizer score and no newly approved candidate.

## Best reported historical submission per site

{highest_report}

The task prompt cites conflicting USER-REPORTED current leaderboard maxima of 0.3195 and 0.4413. No automated DrivenData access is permitted, no receipt is stored here, and neither is ORGANIZER-CONFIRMED in this repository.

{provenance}

{table_md}

{other_reports}

SHA-256 hashes and pinned sources are in [the focus-site registry]({repo_link('registry/focus_sites_2026-10-26.json')}). {inventory_text} See the [inventory]({repo_link('evidence/focus_inventory_20261027.json')}).

## GEMSDOE32: why it may look strong

{rationale}

## Research and next decision

A qualitative three-hypothesis screen (no numerical expected gains) and official-source access gates are on the [Research page]({REPO}/blob/main/docs/research.html) and in [`registry/next_hypotheses.json`]({repo_link('registry/next_hypotheses.json')}). The single-method lane paragraph referenced by the prompt is absent, so no experiment or new TIFF was generated in this review. No currently available file passes both efficacy and authorization gates. Obtain an explicit lane; preregister fresh seeds; run feature-alone leakage checks and same-split current-best holdout; then check pre-placement and final-dot uniqueness against a current complete registry. Only a separate selector may consider a weekly slot. Official organizer scores, current slot capacity and score-to-file receipts remain unknown. Read the [submission instructions]({REPO}/blob/main/docs/how-to-submit.html).
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
