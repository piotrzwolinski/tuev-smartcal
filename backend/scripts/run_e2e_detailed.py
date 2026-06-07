"""Detailed E2E runner — produces rich per-scenario reports.

Each scenario gets: full chat transcript, angebot breakdown, provenance,
judge scores with reasoning. Output as HTML for manual review.

Usage:
    cd backend
    ../venv/bin/python scripts/run_e2e_detailed.py S01 S02 S03 S04 S05
    ../venv/bin/python scripts/run_e2e_detailed.py --category gebaeudetyp
"""

import argparse
import asyncio
import html
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.e2e_scenarios import SCENARIOS, SCENARIO_MAP, E2EScenario
from scripts.e2e_judge import (
    user_llm_generate,
    judge_evaluate,
    JudgeVerdict,
    JUDGE_DIMENSIONS,
)


def _load_graph():
    try:
        from common.database import get_graph
        g = get_graph("dguv_v3")
        rows = g.query("MATCH (n) RETURN count(n) AS cnt").result_set
        if rows and rows[0][0] > 0:
            return
    except Exception:
        pass
    from products.dguv_v3.graph_schema import load_dguv_v3_graph
    load_dguv_v3_graph()


async def run_scenario_detailed(scenario: E2EScenario) -> dict:
    from products.dguv_v3.chat import (
        get_or_create_session,
        coordinator_respond,
        inject_kalkulation_result,
        coordinator_summarize,
    )
    from products.dguv_v3 import DGUV_V3 as gewerk
    from engine.graph_pricing_engine import GraphPricingEngine

    session = get_or_create_session()
    conversation = []
    all_angebote = []
    all_provenance = []
    last_system_msg = ""
    errors = []

    for turn_idx in range(scenario.max_turns):
        user_msg = await user_llm_generate(
            scenario, conversation, turn_idx,
            system_response=last_system_msg,
        )
        if user_msg is None:
            break

        result = await coordinator_respond(session, user_msg)
        turn_record = {
            "turn": turn_idx,
            "user": user_msg,
            "coordinator": result,
            "angebot": None,
            "summary": None,
            "provenance": None,
            "validation_error": None,
        }
        last_system_msg = result.get("message", "")

        if result.get("action") == "calculate":
            params = {k: v for k, v in result.get("params", {}).items() if v is not None}
            try:
                merkmale = gewerk.merkmale_schema(**params)
            except Exception as e:
                turn_record["validation_error"] = str(e)
                errors.append(f"Turn {turn_idx}: Validation error: {e}")
                conversation.append(turn_record)
                continue

            graph_engine = GraphPricingEngine("dguv_v3")
            angebot_obj = graph_engine.calculate(gewerk, merkmale)
            provenance = graph_engine.provenance

            angebot = angebot_obj.to_dict()
            angebot["provenance"] = provenance
            all_angebote.append(angebot)
            all_provenance.extend(provenance)

            inject_kalkulation_result(session, angebot)
            summary = await coordinator_summarize(session)
            turn_record["angebot"] = angebot
            turn_record["summary"] = summary
            turn_record["provenance"] = provenance
            last_system_msg = summary.get("message", "")

        conversation.append(turn_record)

    verdict = await judge_evaluate(scenario, conversation, all_angebote, all_provenance)

    return {
        "scenario": scenario,
        "conversation": conversation,
        "angebote": all_angebote,
        "provenance": all_provenance,
        "verdict": verdict,
        "errors": errors,
    }


def _esc(s):
    return html.escape(str(s)) if s else ""


def _score_color(score):
    if score >= 4:
        return "#22c55e"
    if score >= 3:
        return "#eab308"
    if score >= 2:
        return "#f97316"
    return "#ef4444"


def _score_bar(score):
    pct = score / 5 * 100
    color = _score_color(score)
    return f'<div style="display:flex;align-items:center;gap:8px"><div style="width:120px;height:16px;background:#e5e7eb;border-radius:4px;overflow:hidden"><div style="width:{pct}%;height:100%;background:{color};border-radius:4px"></div></div><span style="font-weight:600;color:{color}">{score}/5</span></div>'


def render_html(results: list[dict], elapsed: float) -> str:
    parts = []
    parts.append("""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>DGUV V3 E2E Test Report</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f8fafc; color: #1e293b; padding: 24px; line-height: 1.5; }
  h1 { font-size: 24px; margin-bottom: 8px; }
  .summary { background: #fff; padding: 16px 20px; border-radius: 8px; margin-bottom: 24px; border: 1px solid #e2e8f0; }
  .scenario { background: #fff; border-radius: 12px; margin-bottom: 32px; border: 1px solid #e2e8f0; overflow: hidden; }
  .scenario-header { padding: 16px 20px; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center; }
  .scenario-header h2 { font-size: 18px; }
  .badge { display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; }
  .badge-pass { background: #dcfce7; color: #166534; }
  .badge-fail { background: #fef2f2; color: #991b1b; }
  .badge-cat { background: #e0e7ff; color: #3730a3; margin-left: 8px; }
  .meta { padding: 12px 20px; background: #f8fafc; border-bottom: 1px solid #e2e8f0; font-size: 13px; color: #64748b; }
  .section { padding: 16px 20px; border-bottom: 1px solid #f1f5f9; }
  .section:last-child { border-bottom: none; }
  .section h3 { font-size: 14px; text-transform: uppercase; letter-spacing: 0.05em; color: #94a3b8; margin-bottom: 12px; }
  .chat-msg { margin-bottom: 12px; display: flex; gap: 12px; }
  .chat-bubble { max-width: 85%; padding: 10px 14px; border-radius: 12px; font-size: 14px; white-space: pre-wrap; word-break: break-word; }
  .chat-user { justify-content: flex-end; }
  .chat-user .chat-bubble { background: #3b82f6; color: white; border-bottom-right-radius: 4px; }
  .chat-system .chat-bubble { background: #f1f5f9; color: #1e293b; border-bottom-left-radius: 4px; }
  .chat-calc { background: #fef3c7 !important; color: #92400e !important; font-size: 12px; font-family: monospace; }
  .chat-label { font-size: 11px; color: #94a3b8; margin-bottom: 2px; }
  .angebot { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .angebot-block { background: #f8fafc; padding: 12px 16px; border-radius: 8px; border: 1px solid #e2e8f0; }
  .angebot-block h4 { font-size: 13px; color: #64748b; margin-bottom: 6px; }
  .angebot-line { display: flex; justify-content: space-between; font-size: 14px; padding: 2px 0; }
  .angebot-total { font-weight: 700; font-size: 18px; border-top: 2px solid #e2e8f0; padding-top: 8px; margin-top: 8px; }
  .prov-step { font-size: 12px; font-family: 'SF Mono', Menlo, monospace; padding: 4px 8px; margin-bottom: 4px; background: #f8fafc; border-radius: 4px; border-left: 3px solid #94a3b8; }
  .prov-step.grundkosten { border-left-color: #3b82f6; }
  .prov-step.pruefkosten { border-left-color: #22c55e; }
  .prov-step.reisekosten { border-left-color: #f97316; }
  .prov-step.bericht { border-left-color: #8b5cf6; }
  .prov-step.zuschlag { border-left-color: #ef4444; }
  .prov-step.confidence { border-left-color: #06b6d4; }
  .prov-step.kalibrierung { border-left-color: #ec4899; }
  .judge-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .judge-dim { background: #f8fafc; padding: 12px 16px; border-radius: 8px; border: 1px solid #e2e8f0; }
  .judge-dim h4 { font-size: 13px; color: #64748b; margin-bottom: 4px; }
  .judge-reason { font-size: 13px; color: #475569; margin-top: 6px; }
  .error { background: #fef2f2; color: #991b1b; padding: 8px 12px; border-radius: 6px; font-size: 13px; }
</style>
</head>
<body>
""")

    # Summary
    passed = sum(1 for r in results if r["verdict"].passed)
    failed = len(results) - passed
    avg_all = sum(r["verdict"].avg_score for r in results) / len(results) if results else 0
    parts.append(f"""
<h1>DGUV V3 E2E LLM-as-Judge Report</h1>
<div class="summary">
  <strong>{passed}</strong> passed, <strong>{failed}</strong> failed, <strong>{len(results)}</strong> total
  &nbsp;·&nbsp; Avg: <strong>{avg_all:.1f}/5</strong>
  &nbsp;·&nbsp; Time: <strong>{elapsed:.0f}s</strong> ({elapsed/len(results):.0f}s/scenario)
</div>
""")

    for r in results:
        sc = r["scenario"]
        v = r["verdict"]
        conv = r["conversation"]
        angebote = r["angebote"]
        prov = r["provenance"]

        status_class = "badge-pass" if v.passed else "badge-fail"
        status_text = f"PASS {v.avg_score:.1f}/5" if v.passed else f"FAIL {v.avg_score:.1f}/5"

        parts.append(f"""
<div class="scenario">
  <div class="scenario-header">
    <h2>{_esc(sc.id)}: {_esc(sc.name)}</h2>
    <div><span class="badge {status_class}">{status_text}</span><span class="badge badge-cat">{_esc(sc.category)}</span></div>
  </div>
  <div class="meta">
    <strong>Persona:</strong> {_esc(sc.persona)}<br>
    <strong>Gebäude:</strong> {_esc(sc.gebaeude)}<br>
    <strong>Tricky:</strong> {_esc(sc.tricky_aspect)}<br>
    <strong>Expected:</strong> {_esc(json.dumps(sc.expected, ensure_ascii=False))}
  </div>
""")

        # Chat transcript
        parts.append('  <div class="section"><h3>Chat-Verlauf</h3>')
        for turn in conv:
            user_msg = turn.get("user", "")
            parts.append(f'    <div class="chat-msg chat-user"><div><div class="chat-label">Kunde (LLM)</div><div class="chat-bubble">{_esc(user_msg)}</div></div></div>')

            coord = turn.get("coordinator", {})
            coord_msg = coord.get("message", "")
            if coord_msg:
                parts.append(f'    <div class="chat-msg chat-system"><div><div class="chat-label">System (Coordinator)</div><div class="chat-bubble">{_esc(coord_msg)}</div></div></div>')

            if coord.get("action") == "calculate":
                params = coord.get("params", {})
                params_short = {k: v for k, v in params.items() if v is not None and k not in ("adresse_lat", "adresse_lon")}
                parts.append(f'    <div class="chat-msg chat-system"><div><div class="chat-label">Extraction → Calculate</div><div class="chat-bubble chat-calc">{_esc(json.dumps(params_short, indent=2, ensure_ascii=False))}</div></div></div>')

            if turn.get("validation_error"):
                parts.append(f'    <div class="error">Validation Error: {_esc(turn["validation_error"])}</div>')

            summary = turn.get("summary", {})
            if summary and summary.get("message"):
                parts.append(f'    <div class="chat-msg chat-system"><div><div class="chat-label">System (Zusammenfassung)</div><div class="chat-bubble">{_esc(summary["message"])}</div></div></div>')

        parts.append('  </div>')

        # Angebot
        if angebote:
            last = angebote[-1]
            bd = last.get("breakdown", {})
            zs = last.get("zuschlaege", [])
            zl = last.get("zusatzleistungen", [])
            total = last.get("total", 0)
            conf = last.get("confidence", 0)
            conf_reason = last.get("confidence_reason", "")
            warnings = last.get("warnings", [])
            ref = last.get("referenzpreis")

            parts.append('  <div class="section"><h3>Angebot</h3><div class="angebot">')

            # Breakdown
            parts.append('    <div class="angebot-block"><h4>Preisaufstellung</h4>')
            parts.append(f'      <div class="angebot-line"><span>Grundkosten</span><span>{bd.get("grund", 0):,.2f} €</span></div>')
            parts.append(f'      <div class="angebot-line"><span>Prüfkosten</span><span>{bd.get("pruef", 0):,.2f} €</span></div>')
            parts.append(f'      <div class="angebot-line"><span>Reisekosten</span><span>{bd.get("reise", 0):,.2f} €</span></div>')
            parts.append(f'      <div class="angebot-line"><span>Bericht</span><span>{bd.get("bericht", 0):,.2f} €</span></div>')
            for z in zs:
                parts.append(f'      <div class="angebot-line"><span>{_esc(z.get("name", ""))}</span><span>+{z.get("amount", 0):,.2f} €</span></div>')
            parts.append(f'      <div class="angebot-line angebot-total"><span>GESAMT (netto)</span><span>{total:,.2f} €</span></div>')
            parts.append('    </div>')

            # Right column: Zusatz + Confidence
            parts.append('    <div class="angebot-block"><h4>Details</h4>')
            parts.append(f'      <div class="angebot-line"><span>Confidence</span><span>{conf*100:.0f}%</span></div>')
            if conf_reason:
                parts.append(f'      <div style="font-size:12px;color:#64748b;margin-top:4px">{_esc(conf_reason)}</div>')
            if zl:
                parts.append('      <h4 style="margin-top:12px">Zusatzleistungen</h4>')
                for z in zl:
                    parts.append(f'      <div class="angebot-line"><span>{_esc(z.get("name", ""))}</span><span>{z.get("preis", 0):,.2f} €</span></div>')
            if ref:
                parts.append(f'      <h4 style="margin-top:12px">Referenzpreis</h4>')
                for k, val in ref.items():
                    parts.append(f'      <div class="angebot-line"><span>{_esc(k)}</span><span>{_esc(str(val))}</span></div>')
            if warnings:
                parts.append('      <h4 style="margin-top:12px">Warnungen</h4>')
                for w in warnings:
                    parts.append(f'      <div style="font-size:12px;color:#b45309;margin-top:2px">⚠ {_esc(w)}</div>')
            parts.append('    </div>')
            parts.append('  </div></div>')

        # Provenance
        if prov:
            parts.append('  <div class="section"><h3>Graph-Provenance / Trace</h3>')
            for p in prov:
                step = p.get("step", "")
                source = p.get("source", "")
                value = p.get("value", "")
                node_id = p.get("node_id", "")
                ref_text = p.get("ref", "")
                css_class = step if step in ("grundkosten", "pruefkosten", "reisekosten", "bericht", "zuschlag", "confidence", "kalibrierung") else ""
                parts.append(f'    <div class="prov-step {css_class}"><strong>{_esc(step)}</strong> · {_esc(source)} = {_esc(str(value)[:80])}{f" [{_esc(node_id)}]" if node_id else ""}{f" (ref: {_esc(ref_text)})" if ref_text else ""}</div>')
            parts.append('  </div>')

        # Judge verdict
        parts.append('  <div class="section"><h3>Judge-Bewertung</h3><div class="judge-grid">')
        for dim in JUDGE_DIMENSIONS:
            score = v.scores.get(dim, 0)
            reason = v.reasoning.get(dim, "")
            parts.append(f'    <div class="judge-dim"><h4>{_esc(dim)}</h4>{_score_bar(score)}<div class="judge-reason">{_esc(reason[:300])}</div></div>')
        parts.append('  </div></div>')

        if v.error:
            parts.append(f'  <div class="section"><div class="error">Error: {_esc(v.error)}</div></div>')

        parts.append('</div>')

    parts.append('</body></html>')
    return "\n".join(parts)


async def _run_one(sc: E2EScenario, idx: int, total: int) -> dict:
    t_start = time.time()
    try:
        r = await run_scenario_detailed(sc)
    except Exception as e:
        r = {
            "scenario": sc,
            "conversation": [],
            "angebote": [],
            "provenance": [],
            "verdict": JudgeVerdict(scenario_id=sc.id, error=str(e)),
            "errors": [str(e)],
        }
    elapsed_sc = time.time() - t_start
    status = "PASS" if r["verdict"].passed else "FAIL"
    print(f"  [{idx+1}/{total}] {sc.id}: {sc.name} → {status} ({r['verdict'].avg_score:.1f}/5) [{elapsed_sc:.0f}s]")
    return r


def _classify_issues(v: JudgeVerdict, scenario: E2EScenario) -> dict:
    """Classify each low-scoring dimension into synapse_fix / tuev_input / known_limitation."""
    issues = {"synapse_fix": [], "tuev_input": [], "known_limitation": []}
    for dim in JUDGE_DIMENSIONS:
        score = v.scores.get(dim, 0)
        reason = v.reasoning.get(dim, "")
        if score >= 4:
            continue
        entry = f"**{dim}** ({score}/5): {reason[:200]}"
        if dim == "extraction" and score < 3:
            issues["synapse_fix"].append(entry)
        elif dim == "pricing" and score < 3:
            if "grundkosten" in reason.lower() or "prüfmittel" in reason.lower():
                issues["known_limitation"].append(entry + " [Grundkosten = Pauschale+Prüfmittel+Tagegeld, kein Bug]")
            else:
                issues["synapse_fix"].append(entry)
        elif dim == "kalibrierung":
            if "büro" not in scenario.gebaeude.lower() and "büro" not in scenario.name.lower():
                issues["known_limitation"].append(entry + " [Kalibrierungsdaten nur für Büro vorhanden]")
            else:
                issues["synapse_fix"].append(entry)
        elif dim == "completeness" and score < 3:
            issues["synapse_fix"].append(entry)
        elif dim == "conversation" and score < 3:
            issues["synapse_fix"].append(entry)
        elif dim == "trace" and score < 3:
            issues["synapse_fix"].append(entry)
        elif score < 3:
            issues["synapse_fix"].append(entry)
        elif score == 3:
            issues["known_limitation"].append(entry)
    return issues


def render_overview_html(results: list[dict], elapsed: float, outdir: str) -> str:
    """Overview page with scoring table, comments, and links to detail pages."""
    parts = ["""<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8">
<title>E2E Test Overview</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f8fafc; color: #1e293b; padding: 24px; line-height: 1.5; }
  h1 { font-size: 22px; margin-bottom: 4px; }
  .subtitle { color: #64748b; margin-bottom: 16px; font-size: 14px; }
  .summary-bar { display: flex; gap: 24px; background: #fff; padding: 14px 20px; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 20px; font-size: 14px; }
  .summary-bar strong { font-size: 18px; }
  table { width: 100%; border-collapse: collapse; background: #fff; border-radius: 8px; overflow: hidden; border: 1px solid #e2e8f0; margin-bottom: 24px; }
  th { background: #f1f5f9; text-align: left; padding: 8px 12px; font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; }
  td { padding: 8px 12px; border-top: 1px solid #f1f5f9; font-size: 13px; vertical-align: top; }
  tr:hover { background: #f8fafc; }
  .pass { color: #166534; font-weight: 600; }
  .fail { color: #991b1b; font-weight: 600; }
  .score-cell { text-align: center; font-weight: 600; }
  .sc4 { color: #166534; } .sc3 { color: #a16207; } .sc2 { color: #c2410c; } .sc1 { color: #991b1b; } .sc0 { color: #991b1b; }
  .issues { font-size: 12px; line-height: 1.4; }
  .issues strong { font-weight: 600; }
  .tag { display: inline-block; padding: 1px 6px; border-radius: 4px; font-size: 11px; font-weight: 600; margin-right: 4px; }
  .tag-fix { background: #fef2f2; color: #991b1b; }
  .tag-tuev { background: #fef3c7; color: #92400e; }
  .tag-ok { background: #f0fdf4; color: #166534; }
  .tag-limit { background: #e0e7ff; color: #3730a3; }
  a { color: #2563eb; text-decoration: none; }
  a:hover { text-decoration: underline; }
</style></head><body>
"""]
    passed = sum(1 for r in results if r["verdict"].passed)
    failed = len(results) - passed
    avg = sum(r["verdict"].avg_score for r in results) / len(results) if results else 0

    parts.append(f'<h1>DGUV V3 — E2E LLM-as-Judge Report</h1>')
    parts.append(f'<div class="subtitle">User-LLM: Sonnet · Judge-LLM: Sonnet (faktenbasiert) · {len(results)} Szenarien · {elapsed:.0f}s</div>')
    parts.append(f'<div class="summary-bar"><div><strong>{passed}</strong> passed</div><div><strong>{failed}</strong> failed</div><div>Avg: <strong>{avg:.1f}/5</strong></div></div>')

    dim_short = {"extraction": "Extr", "pricing": "Preis", "conversation": "Chat", "trace": "Trace", "kalibrierung": "Kalib", "completeness": "Compl"}

    parts.append('<table><thead><tr>')
    parts.append('<th>ID</th><th>Scenario</th><th>Status</th><th>Avg</th>')
    for dim in JUDGE_DIMENSIONS:
        parts.append(f'<th>{dim_short[dim]}</th>')
    parts.append('<th>Kommentar</th><th>Detail</th>')
    parts.append('</tr></thead><tbody>')

    for r in results:
        sc = r["scenario"]
        v = r["verdict"]
        issues = _classify_issues(v, sc)
        status_cls = "pass" if v.passed else "fail"
        status_txt = "PASS" if v.passed else "FAIL"
        detail_file = f"{sc.id}.html"

        parts.append(f'<tr>')
        parts.append(f'<td><strong>{sc.id}</strong></td>')
        parts.append(f'<td>{_esc(sc.name)}<br><span style="font-size:11px;color:#94a3b8">{_esc(sc.category)}</span></td>')
        parts.append(f'<td class="{status_cls}">{status_txt}</td>')

        avg_sc = v.avg_score
        avg_cls = f"sc{min(4, int(avg_sc))}"
        parts.append(f'<td class="score-cell {avg_cls}">{avg_sc:.1f}</td>')

        for dim in JUDGE_DIMENSIONS:
            s = v.scores.get(dim, 0)
            cls = f"sc{min(4, s)}"
            parts.append(f'<td class="score-cell {cls}">{s}</td>')

        comment_parts = []
        if v.error:
            comment_parts.append(f'<span class="tag tag-fix">ERROR</span> {_esc(v.error[:80])}')
        if issues["synapse_fix"]:
            comment_parts.append(f'<span class="tag tag-fix">Synapse Fix</span> {"; ".join(_esc(i[:100]) for i in issues["synapse_fix"])}')
        if issues["tuev_input"]:
            comment_parts.append(f'<span class="tag tag-tuev">TÜV Input</span> {"; ".join(_esc(i[:100]) for i in issues["tuev_input"])}')
        if issues["known_limitation"]:
            comment_parts.append(f'<span class="tag tag-limit">Limitation</span> {"; ".join(_esc(i[:100]) for i in issues["known_limitation"])}')
        if not comment_parts:
            comment_parts.append(f'<span class="tag tag-ok">OK</span>')
        parts.append(f'<td class="issues">{"<br>".join(comment_parts)}</td>')
        parts.append(f'<td><a href="{detail_file}">Details →</a></td>')
        parts.append('</tr>')

    parts.append('</tbody></table>')
    parts.append('</body></html>')
    return "\n".join(parts)


async def main(scenarios: list[E2EScenario], output_dir: str, parallel: int = 5):
    print("Loading DGUV V3 graph...")
    _load_graph()
    print(f"Running {len(scenarios)} scenarios in parallel (max {parallel})...\n")

    os.makedirs(output_dir, exist_ok=True)

    t0 = time.time()
    sem = asyncio.Semaphore(parallel)

    async def bounded(sc, idx, total):
        async with sem:
            return await _run_one(sc, idx, total)

    tasks = [bounded(sc, i, len(scenarios)) for i, sc in enumerate(scenarios)]
    results = await asyncio.gather(*tasks)

    elapsed = time.time() - t0

    for r in results:
        sc = r["scenario"]
        detail_html = render_html([r], elapsed)
        detail_path = os.path.join(output_dir, f"{sc.id}.html")
        with open(detail_path, "w", encoding="utf-8") as f:
            f.write(detail_html)

    overview_html = render_overview_html(list(results), elapsed, output_dir)
    overview_path = os.path.join(output_dir, "index.html")
    with open(overview_path, "w", encoding="utf-8") as f:
        f.write(overview_html)

    print(f"\nReport: {len(results)} detail files + index.html in {output_dir}/")
    print(f"Open: file://{os.path.abspath(overview_path)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("scenarios", nargs="*", help="Scenario IDs (e.g. S01 S02)")
    parser.add_argument("--category", "-c")
    parser.add_argument("--outdir", "-o", default="e2e_report")
    parser.add_argument("--parallel", "-p", type=int, default=5, help="Max concurrent scenarios")
    args = parser.parse_args()

    selected = SCENARIOS
    if args.scenarios:
        selected = [SCENARIO_MAP[sid] for sid in args.scenarios if sid in SCENARIO_MAP]
    elif args.category:
        selected = [s for s in SCENARIOS if s.category == args.category]

    if not selected:
        print("No matching scenarios.")
        sys.exit(1)

    asyncio.run(main(selected, args.outdir, parallel=args.parallel))
