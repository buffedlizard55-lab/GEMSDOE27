#!/usr/bin/env python3
"""Render the GitHub Pages site (docs/*.html) and the derived knowledge docs from JSON only.

Inputs: docs/downloads/manifest.json, evidence/*.json, registry/*.json, docs/data/*. No rasters are needed, so this runs in CI.
Nothing here fetches drivendata.org or invents a score: scores come from registry/live_scores.json (owner-reported).
"""

from __future__ import annotations

import csv
import html
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS, EV, REG, KN = ROOT / "docs", ROOT / "evidence", ROOT / "registry", ROOT / "knowledge"
REPO_URL = "https://github.com/buffedlizard55-lab/GEMSDOE27"
DD_COMP = "https://www.drivendata.org/competitions/306/competition-doe-gems/"
DD_LB = DD_COMP + "leaderboard/"
NAV = [("index.html", "Submit"), ("executive-summary.html", "Executive summary"), ("topology.html", "Topology candidates"),
       ("research.html", "Research"), ("sources.html", "Sources & feed")]


def J(p: Path):
    return json.loads(p.read_text())


def e(x) -> str:
    return html.escape(str(x), quote=True)


def layout(fname: str, title: str, body: str, stamp: str) -> str:
    nav = "".join(f'<a href="{h}"{" class=on" if h == fname else ""}>{e(t)}</a>' for h, t in NAV)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} · 27GEMSDOE</title><meta name="description" content="27GEMSDOE: topology-first research and submission lab for DrivenData #306 (DOE GEMS). Unscored candidate; no score claimed.">
<link rel="stylesheet" href="assets/style.css"></head><body>
<header class="top"><div class="in"><a class="brand" href="index.html">27GEMSDOE · DOE GEMS</a><nav>{nav}</nav></div></header>
<main>{body}</main>
<footer>Built {e(stamp)} from <a href="{REPO_URL}">the repository</a>. Unscored candidates: no leaderboard score is claimed anywhere on this site.
Scores shown are owner-reported. This site never contacts drivendata.org.</footer>
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
    Q = man.get("quaternary")
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
    size_mb = P["bytes_nan"] / 1e6
    pages: dict[str, tuple[str, str]] = {}

    # ---------------------------------------------------------------- index
    pages["index.html"] = ("Submit", f"""
<h1>Submit this file.</h1>
<p class="lead">27GEMSDOE · DrivenData #306 DOE GEMS. The owner's 0.2477 file plus one controlled change: <b>{P['added_px']:,}</b> topology gap-closure dots on <b>{P['links']}</b> links.
<span class="badge warn">UNSCORED – no score is claimed</span></p>
<div class="card hero">
 <div class="row"><a class="btn" href="downloads/{e(P['nan'])}" download>⬇ Download submission (.tif)</a>
 <a class="btn alt" href="downloads/{e(P['zip'])}" download>.zip (same file)</a>
 <a class="btn alt" href="downloads/{e(P['allfinite'])}" download>fallback: all-finite .tif</a></div>
 <p class="small mono">{e(P['nan'])} · {size_mb:.2f} MB · sha256 {e(P['sha256_nan'])}</p>
 <h3>Note to paste into the form (optional field)</h3>
 <textarea id="note" class="note" readonly>{e(P['note'])}</textarea>
 <div class="row"><button class="btn copy" data-copy="#note">Copy note</button><span id="notecount" class="small">{len(P['note'])} / 200 characters</span></div>
 <div class="row"><span class="badge ok">format verified: float32 · single band · exact 0/1 · NaN outside</span><span class="badge ok">gates passed on blocked holdout (class level)</span><span class="badge warn">real hidden set: untested</span></div>
</div>
<p>Steps: download → open <a href="{DD_COMP}">the competition</a> (sign in) → Submit → upload the .tif (or the .zip) → paste the note → submit.
Exact steps, the "[0, 1]" troubleshooting and the 4-slot plan are in the <a href="executive-summary.html"><b>executive summary</b></a>.</p>
<div class="grid">
 <div class="stat"><b>{P['emitted_px']:,}</b><span>emitted pixels = 60,069 (the 0.2477 emission, nothing removed) + {P['added_px']:,}</span></div>
 <div class="stat"><b>{cs['selected_links']}</b><span>aligned gap links (median {cs['median_gap_km']:.1f} km), each with NBMG/USGS vector fault attribution &amp; written argument</span></div>
 <div class="stat"><b>{eff['z>=3 dedup']:.2f} / {veff_fid['z>=3 dedup']:.2f}</b><span>holdout efficiency on 8-conn components / whole NBMG FID vector polylines vs break-even 0.052</span></div>
 <div class="stat"><b>{oof['variants']['plus_T_v2']['mean_dti_gain']:+.4f} / {oof['variants']['plus_T_v2_and_prune_r1']['mean_dti_gain']:+.4f}</b><span>paired DTI gain on honest 4-fold spatial-CV OOF detector (T-v2 solo / T-v2 + H27-4 in Slot 3)</span></div>
</div>
{invcard}
<div class="card">
 <h3 style="margin-top:0">All 4 weekly slot candidates (pre-built &amp; verified)</h3>
 <table>
  <tr><th>Slot</th><th>Candidate (.tif / .zip / fallback)</th><th>Pixels</th><th>Model<br>geo / hyb</th><th>What it tests</th></tr>
  <tr><td><b>1 (Primary A/B)</b></td><td><a href="downloads/{e(P['nan'])}" download class="mono">{e(P['nan'])}</a> &middot; <a href="downloads/{e(P['zip'])}" download>.zip</a> &middot; <a href="downloads/{e(P['allfinite'])}" download>allfinite</a></td><td class="num">{P['emitted_px']:,}</td><td class="num">{mscore('slot1_primary_A_B','model_score_geometric')} / {mscore('slot1_primary_A_B','model_score_hybrid')}</td><td>0.2477 base + {P['added_px']:,} T-v2 dots, <b>nothing removed</b>. Changes exactly one thing, so slot 1 against the scored 0.2477 parent is a clean A/B. OOF &Delta;DTI {oof['variants']['plus_T_v2']['mean_dti_gain']:+.4f} (4/4 folds).</td></tr>
  <tr><td><b>2 (budget optimum)</b></td><td><a href="downloads/{e(S['nan'])}" download class="mono">{e(S['nan'])}</a> &middot; <a href="downloads/{e(S['zip'])}" download>.zip</a> &middot; <a href="downloads/{e(S['allfinite'])}" download>allfinite</a></td><td class="num">{S['emitted_px']:,}</td><td class="num">{mscore('slot2_secondary_d2_8','model_score_geometric')} / {mscore('slot2_secondary_d2_8','model_score_hybrid')}</td><td>d2.8-thinned H19-5 + {S['added_px']:,} T-v2 dots. d=2.25&ndash;2.8 is the <b>live-anchored budget optimum</b> ({geo_ceiling:.4f} for that base alone, vs 0.2477 live).</td></tr>
  <tr><td><b>3 (T-v2 + H27-4 prune)</b></td><td><a href="downloads/{e(T['nan'])}" download class="mono">{e(T['nan'])}</a> &middot; <a href="downloads/{e(T['zip'])}" download>.zip</a> &middot; <a href="downloads/{e(T['allfinite'])}" download>allfinite</a></td><td class="num">{T['emitted_px']:,}</td><td class="num">{mscore('slot3_tertiary_prune_d1_5','model_score_geometric')} / {mscore('slot3_tertiary_prune_d1_5','model_score_hybrid')}</td><td>0.2477 base &minus; {T['pruned_flank_shadow_px']:,} 100&nbsp;m catalogue-flank-shadow dots + {T['added_px']:,} T-v2 dots. OOF &Delta;DTI {oof['variants']['plus_T_v2_and_prune_r1']['mean_dti_gain']:+.4f} (4/4 folds). <b>Slot 1 vs slot 3 settles whether the prune pays.</b></td></tr>
  <tr><td><b>4 (NEW &mdash; all increments)</b></td><td><a href="downloads/{e(Q['nan'])}" download class="mono">{e(Q['nan'])}</a> &middot; <a href="downloads/{e(Q['zip'])}" download>.zip</a> &middot; <a href="downloads/{e(Q['allfinite'])}" download>allfinite</a></td><td class="num">{Q['emitted_px']:,}</td><td class="num">{mscore('slot4_quaternary_all_increments','model_score_geometric')} / {mscore('slot4_quaternary_all_increments','model_score_hybrid')}</td><td>d2.8 optimum base &minus; {Q['pruned_flank_shadow_px']:,} flank-shadow dots + {Q['added_px']:,} T-v2 dots. First candidate to stack <b>every</b> increment this programme validated, at the live-anchored budget; highest hybrid estimate of the four.</td></tr>
 </table>
</div>
<div class="warnbox"><b>Honest status.</b> We validated T-v2 across three holdout tiers (8-connected components: {eff['z>=3 dedup']:.3f}, whole NBMG FID vector polylines: {veff_fid['z>=3 dedup']:.3f} / H27-5b {veff_fid['z>=3 inter-FID + same_name + kinematic_compat (H27-5b)']:.3f}) and on a strictly out-of-fold 4-quadrant spatial-CV detector (ΔDTI {oof['variants']['plus_T_v2']['mean_dti_gain']:+.4f} solo, {oof['variants']['plus_T_v2_and_prune_r1']['mean_dti_gain']:+.4f} stacked with H27-4). Only a live score tests the organisers' newly created expert labels.
Reaching the owner-stated leader (0.3195) is not possible with verified/modelled increments on H19-5 alone (they reach ≈0.262–0.270) – see <a href="research.html">research</a>.
The agent never uploads anything; you press the button.</div>
<p class="small">Reference (owner-reported 0.2477): <a href="{e(man['reference_0_2477']['url'])}">24GEMSDOE file</a> (sha256 {e(man['reference_0_2477']['sha256'][:16])}…).</p>
""")

    # ---------------------------------------------------------------- executive summary
    rows_pay = "".join(f"<tr><td class='num'>{k}</td><td class='num'>{v:+.4f}</td></tr>" for k, v in pay.items())
    pages["executive-summary.html"] = ("Executive summary", f"""
<h1>Executive summary</h1>
<p class="lead">What to submit, exactly how, what it can and cannot do, and what to do next.</p>
<div class="card"><h2 style="margin-top:0">Decision in one table</h2>
<table><tr><th>Question</th><th>Answer</th></tr>
<tr><td>What to submit now</td><td><b>Slot 1:</b> <span class="mono">{e(P['nan'])}</span> (or its .zip)</td></tr>
<tr><td>Why this file</td><td>It is the owner-reported 0.2477 emission (dotted H19-5, d=1.5) plus {P['added_px']:,} dots on {P['links']} topology gap-closure links and nothing removed – a <b>controlled A/B test</b>:
score(A) − 0.2477 isolates the effect of the new class.</td></tr>
<tr><td>What it can do</td><td>Modelled effect at the 0.2477 operating point: {pay['0.0']:+.4f} (hit rate 0) · break-even at efficiency 0.052 · {pay['0.14']:+.4f} at half the holdout efficiency · {pay['0.28']:+.4f} at the holdout efficiency. The downside is small because only ~1.3k dots are added to a 60k base.</td></tr>
<tr><td>Evidence</td><td>Pre-registered gate passed on seeds 100–109 and confirmed on fresh seeds 110–119 (efficiency {eff['z>=3 dedup']:.3f}; controls {con['control_pooled']:.3f}; random same-size subsets {con['random_same_size']['mean']:.3f}, 95th pct {con['random_same_size']['p95']:.3f}).</td></tr>
<tr><td>Is 0.3195 reachable?</td><td>Not with verified/modelled increments (they reach ≈0.26–0.27). It needs ≈31% more weighted recall at equal false positives, or ≈46% fewer false-positive pixels at equal recall – i.e. new information. <a href="research.html">Why</a>.</td></tr>
<tr><td>What is unknown</td><td>The real hidden-set effect; the cause of the portal's "[0, 1]" rejection; the live scores of all 27GEMSDOE files.</td></tr></table></div>

<h2>Exact submission steps</h2>
<ol class="steps">
<li>Download the <b>.tif</b> from the <a href="index.html">front page</a> (do not open and re-save it in a GIS; that rewrites the file). Keep the file name.</li>
<li>Sign in at DrivenData and open <a href="{DD_COMP}">the competition page</a>.</li>
<li>Open the competition's submission form (the tab/button label depends on your logged-in view; the agent cannot see it and does not automate that site).</li>
<li>Upload the <b>.tif</b> – or the <b>.zip</b>, which holds exactly the same single GeoTIFF (the form takes a .tif or a .zip with one GeoTIFF).</li>
<li>Paste the note (<b>{len(P['note'])}</b> characters, copy button on the front page) into the optional Note field:<br><code>{e(P['note'])}</code></li>
<li>Submit and wait for scoring. Copy the public score.</li>
<li>Record it: add the number to the "27GEMSDOE" entry of <code>registry/live_scores.json</code> and push – the <i>build-site</i> workflow refreshes these pages. (Scores are owner-reported; the site never fetches them.)</li></ol>

<h2>If the form says "Predicted values must be in range [0, 1]"</h2>
<div class="card">
<p>The cause of that message in the earlier attempt is <b>not established</b> – the validator is not public. What is verified for these files (<code>scripts/verify_downloads.py</code>, independent of the project code):</p>
<ul class="tight"><li>single band, float32, EPSG:32611, 3730 × 3292, same transform as the sample;</li>
<li>every in-footprint pixel is exactly 0.0 or 1.0 (no float rounding above 1, no negatives, no NaN, no Inf inside the footprint);</li>
<li>NaN only outside the footprint (7,111,787 px) with <code>nodata=NaN</code> declared, exactly like the sample submission;</li>
<li>no emitted pixel on a catalogue cell; zip holds exactly one identical .tif; note ≤ 200 characters.</li></ul>
<p><b>Order to try:</b> (1) the .tif; (2) the <a href="downloads/{e(P['zip'])}">.zip</a>; (3) the <a href="downloads/{e(P['allfinite'])}">all-finite fallback</a> (zeros outside the footprint, no NaN anywhere – it satisfies even a validator that compares NaN directly; the owner's sibling forensics found both outside-footprint conventions have scored on the live board).
If all three are rejected, paste the exact message and the file name – that is the information needed to find the real rule.</p></div>

<h2>The four weekly slots (decision rules fixed in advance)</h2>
<table><tr><th>Slot</th><th>File</th><th>Run when</th><th>Reading the result (Δ = score − 0.2477, owner-reported)</th></tr>
<tr><td>1</td><td><b>A/B primary</b> (above)</td><td>now</td><td>Δ &gt; +0.0005: topology helps → slot 2 = file B. −0.0015 &lt; Δ ≤ +0.0005: no detectable effect → slot 2 = the owner's plain d2.8 file. Δ &lt; −0.0015: refuted on the real set → do not stack; slot 2 = plain d2.8. (A drop beyond −0.0026 would contradict the arithmetic – investigate scoring or masking.)</td></tr>
<tr><td>2</td><td>B = <span class="mono">{e(S['nan'])}</span> (d2.8 base + same links; <a href="downloads/{e(S['nan'])}" download>.tif</a> · <a href="downloads/{e(S['zip'])}" download>.zip</a>)<br><span class="small">Note ({len(S['note'])} chars): <code>{e(S['note'])}</code></span></td><td>after slot 1</td><td>d2.8 is a sibling <i>model</i> (+≈0.010 over d1.5), never scored; B stacks it with the topology dots.</td></tr>
<tr><td>3</td><td>C = <span class="mono">{e(T['nan'])}</span> (0.2477 base minus {T['pruned_flank_shadow_px']:,} 100 m flank-shadow dots + {T['added_px']:,} T-v2 dots; <a href="downloads/{e(T['nan'])}" download>.tif</a> · <a href="downloads/{e(T['zip'])}" download>.zip</a>)<br><span class="small">Note ({len(T['note'])} chars): <code>{e(T['note'])}</code></span></td><td>after slot 1/2</td><td>Validated on the honest 4-fold spatial-CV OOF detector (seeds 130–139): 100 m flank-shadow dots have hit efficiency 0.0034 (15× below break-even 0.0521); stacking H27-4 r≤1px + T-v2 gains <b>+0.0141 DTI in 4/4 folds</b> (modelled live DTI ≈ 0.262–0.270).</td></tr>
<tr><td>4</td><td><b>D = NEW</b> <span class="mono">{e(Q['nan'])}</span> (d2.8 optimum base minus {Q['pruned_flank_shadow_px']:,} flank-shadow dots + {Q['added_px']:,} T-v2 dots; <a href="downloads/{e(Q['nan'])}" download>.tif</a> · <a href="downloads/{e(Q['zip'])}" download>.zip</a>)<br><span class="small">Note ({len(Q['note'])} chars): <code>{e(Q['note'])}</code></span></td><td>after slot 1 or 3</td><td>First candidate stacking <b>all three</b> validated increments at the live-anchored budget. Model {mscore('slot4_quaternary_all_increments','model_score_geometric')} (geometric) / <b>{mscore('slot4_quaternary_all_increments','model_score_hybrid')}</b> (hybrid) &mdash; the highest hybrid estimate of the four. Run slot 1 or 3 first: they measure whether the prune pays, which is the only term the two models disagree about.</td></tr></table>
<p class="small">The geometric/hybrid pair is explained in <a href="research.html#inversion">the inversion</a>: they differ only in what the targeted H27-4 prune is charged, and slot&nbsp;1&nbsp;vs&nbsp;slot&nbsp;3 is the live A/B that settles it.</p>
<p class="small">Limit: 3 submissions per week; one submission is chosen for both rounds (problem page and Official Rules, read in part). Choose the final one deliberately.</p>

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
        rows.append(f"<tr class='link' data-id='{e(r['link_id'])}'><td>{e(r['link_id'])}</td><td class='num'>{r['z']}</td><td>{e(r['kind'])}</td>"
                    f"<td>{fname_cell}<br><span class='small mono'>{fid_tag} · {kin_tag}</span></td>"
                    f"<td class='num'>{r['gap_km']:.2f}</td><td>{'✓' if r['mutual'] else ''}</td><td class='num'>{r['strike']:.0f}°</td>"
                    f"<td class='num' data-v='{r['strike_compat']:.3f}'>{100 * r['strike_compat']:.0f}%</td><td class='num'>{r['merged_km']:.1f}</td>"
                    f"<td class='num' data-v='{r['base_overlap']:.3f}'>{100 * r['base_overlap']:.0f}%</td>"
                    f"<td class='mono'>{mlat:.4f}, {mlon:.4f}</td><td><a href='https://www.openstreetmap.org/#map=14/{mlat:.4f}/{mlon:.4f}'>map</a></td></tr>")
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
<tr><td>Addendum C (honest 4-fold spatial-CV OOF base)</td><td>130–139</td><td>On non-leaky B<sub>oof</sub> (mean DTI {oof['base_oof_mean_dti']:.4f}), T-v2 gains <b>{oof['variants']['plus_T_v2']['mean_dti_gain']:+.4f}</b> in 4/4 folds (marginal eff {oof['variants']['plus_T_v2']['marginal_or_removed_efficiency']:.4f}); H27-4 (100 m flank-shadow prune) gains <b>{oof['variants']['prune_r1_100m']['mean_dti_gain']:+.4f}</b> solo and <b>{oof['variants']['plus_T_v2_and_prune_r1']['mean_dti_gain']:+.4f}</b> stacked with T-v2 in 4/4 folds; H27-3 isolated-dot removal refuted ({oof['variants']['coherence_h27_3']['mean_dti_gain']:+.4f}, 0/4 folds). <b>PASSED (H27-1 &amp; H27-4)</b></td></tr></table>
<p class="small">Disclosed: my first confirmatory launch had an implementation bug (minimum gap applied before choosing the nearest target); a unit test caught it, it was stopped and rerun as registered – <code>evidence/topology_validation_runA_partial_log.txt</code>. Vector attribution uses the 1,179 NBMG INGENIOUS Qfaults polylines (<code>qfaults_v2_in_footprint.json</code>, matching 98.42% of <code>labels.tif</code> at 100 m and 99.97% at 200 m): 230/345 shipped links are intra-FID, 115/345 inter-FID, 312/345 same NAME, and 333/345 kinematically compatible.</p>

<h2>Examples and map</h2>
<figure><img class="fig" src="assets/fig_examples.png" alt="Six example gap closures"><figcaption>Dark: mapped catalogue. Blue: the 0.2477 emission. Red: link dots. These are strongly supported (z ≥ 4), long, and barely covered by the current emission.</figcaption></figure>
<figure><img class="fig" src="assets/fig_map_overview.png" alt="Footprint map with all 345 links"><figcaption>All {cs['selected_links']} shipped links over the catalogue.</figcaption></figure>

<h2>All {cs['selected_links']} candidates</h2>
<p class="small">Click a row for its written argument (including official NBMG/USGS fault zone name, FID, slip sense, and dip direction). Downloads: <a href="data/topology_links.csv">CSV</a> · <a href="data/topology_links.geojson">GeoJSON (WGS84)</a>. Review against the official <a href="https://doi.org/10.5066/F7S75FJM">USGS Interactive Fault Map</a> (Quaternary faults only) and the map link in each row. z = evidence score 0–5; compat = share of nearby catalogued fault length within 20° of the link strike; base overlap = share of the link's dots already within 300 m of the 0.2477 emission.</p>
<p><input id="filter" class="filter" placeholder="filter (id, fault name, FID, kind, z …)" aria-label="filter candidates"></p>
<div class="tw"><table id="links"><thead><tr><th data-k="0">ID</th><th class="num" data-k="1">z</th><th data-k="2">kind</th><th data-k="3">NBMG Fault Zone · FID · Slip/Dip</th><th class="num" data-k="4">gap km</th><th>mutual</th><th class="num" data-k="6">strike</th><th class="num" data-k="7">compat</th><th class="num" data-k="8">merged km</th><th class="num" data-k="9">base overlap</th><th>mid lat, lon</th><th></th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
""")

    # ---------------------------------------------------------------- research
    hrows = "".join(f"<tr><td><b>{e(h['id'])}</b><br><span class='small'>rank {h['rank']}</span></td><td><b>{e(h['title'])}</b><br><span class='small'>{e(h['layers'])}</span></td>"
                    f"<td>{e(h['signature'])}</td><td>{e(h['why'])}</td><td>{e(h['differs'])}</td><td>{e(h['status'])}</td><td>{e(h['gain'])}<br><span class='small'>cost: {e(h['cost'])}</span></td></tr>" for h in hyp)
    pages["research.html"] = ("Research", f"""
<h1>Research</h1>
<p class="lead">Why the 0.2477 file won, what a higher score needs, and the ranked hypotheses.</p>
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
<div class="tw"><table><tr><th>ID</th><th>Hypothesis · layers</th><th>Physical signature</th><th>Why it catches a fault missing from USGS/INGENIOUS</th><th>How it differs from the repo</th><th>Status</th><th>Gain · cost</th></tr>{hrows}</table></div>
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
        w = csv.writer(f)
        w.writerow(["id", "title", "publisher", "url", "category", "status", "accessed"])
        for s in src:
            w.writerow([s["id"], s["title"], s["publisher"], s["url"], s["category"], s["status"], s["accessed"]])
    print("site built:", ", ".join(pages), "at", stamp)


if __name__ == "__main__":
    build()
