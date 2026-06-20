"""Render-Modul NEBEN der Engine — liest viz/out/<id>.json (echter Trace) und
erzeugt eine eigenständige HTML-Visualisierung. KEINE Engine-Änderung.

Zeigt denselben echten Trace in 3 Stilen zum Vergleich/Diskussion:
  1. Entscheidungsbaum (Option A — flacher Trace hierarchisch gerendert)
  2. Wasserfall (wie sich der Preis aufbaut)
  3. Explizite Gates (Vorschau Option B — Bedingungen als Ja/Nein-Knoten)
"""

import html
import json
import re
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"

PHASE_LABEL = {
    "grundkosten": "Grundkosten", "prueftage": "Prüftage", "tagegeld": "Tagegeld",
    "pruefkosten": "Prüfkosten", "kalibrierung": "Referenz-Crosscheck",
    "branchenvergleich": "Branchen-Vergleich", "reisekosten": "Reisekosten",
    "bericht": "Bericht", "confidence": "Konfidenz", "cross_sell": "Cross-Sell",
}
PHASE_ORDER = ["grundkosten", "prueftage", "tagegeld", "pruefkosten", "kalibrierung",
               "branchenvergleich", "reisekosten", "bericht", "confidence", "cross_sell"]

# Regex zum Erkennen einer Bedingung im source-Text (der Trace bettet sie als Prosa ein)
COND_RE = re.compile(r"(>|≥|≤|<|=\d|Regel|Mehrtägig|degressiv|baurechtlich|Range|Staffel|→)", re.I)


def classify(step: dict) -> dict:
    """Leitet kind + Bedingung aus dem echten Trace-Step ab (read-only)."""
    src, ref, nid = step["source"], step.get("ref", ""), step.get("node_id", "")
    kind = "berechnung"
    if step["step"] in ("kalibrierung", "branchenvergleich"):
        kind = "crosscheck"          # diagnostisch, NICHT in den Preis geflossen
    elif not ref and not nid:
        kind = "luecke"              # keine Quelle — hier kann der Trace heute "lügen"
    elif ref and nid:
        kind = "faktum"              # Wert aus benannter Quelle + Graph-Knoten
    bedingung = bool(COND_RE.search(src))
    return {**step, "kind": kind, "bedingung": bedingung}


def esc(s) -> str:
    return html.escape(str(s))


def render_case(d: dict) -> str:
    steps = [classify(s) for s in d["provenance"]]
    bd = d["breakdown"]

    # ---------- VIEW 1: Entscheidungsbaum (gruppiert nach Phase) ----------
    phases = {}
    for s in steps:
        phases.setdefault(s["step"], []).append(s)

    tree_html = ""
    for ph in PHASE_ORDER:
        if ph not in phases:
            continue
        rows = phases[ph]
        phase_sum = ""
        if ph == "grundkosten": phase_sum = f"{bd['grund']:.0f}€"
        elif ph == "pruefkosten": phase_sum = f"{bd['pruef']:.0f}€"
        elif ph == "reisekosten": phase_sum = f"{bd['reise']:.0f}€"
        elif ph == "bericht": phase_sum = f"{bd['bericht']:.0f}€"
        leaves = ""
        for s in rows:
            badges = ""
            if s["bedingung"]:
                badges += '<span class="badge cond">if</span>'
            badges += f'<span class="badge k-{s["kind"]}">{s["kind"]}</span>'
            quelle = esc(s["ref"]) if s["ref"] else '<em class="missing">⚠ keine Quelle</em>'
            node = f'<span class="node">⬡ {esc(s["node_id"])}</span>' if s["node_id"] else ""
            leaves += f'''
              <div class="leaf k-{s["kind"]}">
                <div class="leaf-head">{badges}<span class="src">{esc(s["source"])}</span>
                  <span class="val">{esc(s["value"])}</span></div>
                <div class="leaf-prov">{node}<span class="ref">{quelle}</span></div>
              </div>'''
        tree_html += f'''
          <details open class="phase">
            <summary><span class="ph-name">{PHASE_LABEL.get(ph, ph)}</span>
              <span class="ph-sum">{phase_sum}</span></summary>
            {leaves}
          </details>'''

    # ---------- VIEW 2: Wasserfall ----------
    segs = [("Grundkosten", bd["grund"]), ("Prüfkosten", bd["pruef"]),
            ("Reisekosten", bd["reise"]), ("Bericht", bd["bericht"])]
    total = d["total"]
    wf = ""
    for name, val in segs:
        pct = (val / total * 100) if total else 0
        wf += f'''<div class="wf-row"><span class="wf-name">{name}</span>
          <div class="wf-bar"><div class="wf-fill" style="width:{pct:.1f}%"></div></div>
          <span class="wf-val">{val:.0f}€</span></div>'''

    # ---------- VIEW 3: Explizite Gates (Vorschau Option B) ----------
    gates = [s for s in steps if s["bedingung"]][:4]
    gate_html = ""
    for s in gates:
        gate_html += f'''<div class="gate">
          <div class="gate-q">{esc(s["source"])}</div>
          <div class="gate-arm yes">→ {esc(s["value"])}</div>
          <div class="gate-src">{esc(s["ref"]) if s["ref"] else "⚠ keine Quelle"}</div>
        </div>'''

    crosscheck = next((s for s in steps if s["kind"] == "crosscheck"
                       and "Kalibrierung" in s["source"]), None)
    cc_note = ""
    if crosscheck:
        cc_note = f'''<div class="cc-note">
          <b>Referenz-Crosscheck (diagnostisch, NICHT in Preis geflossen):</b><br>
          {esc(crosscheck["source"])} — Quelle: {esc(crosscheck["ref"])}<br>
          <span class="cc-warn">→ Engine nutzte {bd["pruef"]:.0f}€, Referenz sagt anders.
          Im Cockpit wäre das eine sichtbare Abweichung statt versteckt im Log.</span>
        </div>'''

    inputs = ", ".join(f"{k}={v}" for k, v in d["inputs"].items()
                       if k in ("nutzung", "pruefart", "gesamtflaeche_m2",
                                "primary_installationskategorie", "anzahl_verteilungen_uv",
                                "vds_pruefung", "adresse_ort"))

    return f'''
    <section class="case">
      <h2>{esc(d["titel"])}</h2>
      <div class="meta">Input: {esc(inputs)}<br>
        <b>Gesamt: {total:.0f}€</b> · Konfidenz {d["confidence"]*100:.0f}% · {len(steps)} Trace-Schritte</div>

      <div class="grid">
        <div class="col">
          <h3>① Entscheidungsbaum <span class="sub">(Option A — echter Trace, hierarchisch)</span></h3>
          {tree_html}
        </div>
        <div class="col">
          <h3>② Wasserfall <span class="sub">(Preisaufbau)</span></h3>
          {wf}
          <h3 style="margin-top:24px">③ Explizite Gates <span class="sub">(Vorschau Option B)</span></h3>
          <div class="gates">{gate_html}</div>
          {cc_note}
        </div>
      </div>
    </section>'''


def render_all() -> str:
    cases = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(OUT.glob("*.json"))]
    body = "\n".join(render_case(c) for c in cases)
    return f'''<!DOCTYPE html><html lang="de"><head><meta charset="utf-8">
<title>Kalkulation — Entscheidungsbaum (echte Traces)</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font: 14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif; margin:0; background:#0f1115; color:#e6e8ec; }}
  .wrap {{ max-width: 1180px; margin: 0 auto; padding: 28px; }}
  h1 {{ font-size: 22px; margin:0 0 4px; }}
  .lede {{ color:#9aa1ad; margin:0 0 24px; font-size:13px; }}
  .legend {{ display:flex; gap:14px; flex-wrap:wrap; margin:0 0 24px; font-size:12px; }}
  .legend span {{ padding:3px 9px; border-radius:20px; }}
  .case {{ background:#171a21; border:1px solid #262b35; border-radius:12px; padding:20px; margin-bottom:24px; }}
  .case h2 {{ font-size:17px; margin:0 0 4px; }}
  .meta {{ color:#9aa1ad; font-size:12.5px; margin-bottom:16px; }}
  .meta b {{ color:#fff; font-size:15px; }}
  .grid {{ display:grid; grid-template-columns: 1.25fr 1fr; gap:24px; }}
  h3 {{ font-size:13px; text-transform:uppercase; letter-spacing:.04em; color:#c3c8d2; margin:0 0 10px; }}
  h3 .sub {{ text-transform:none; letter-spacing:0; color:#6b7280; font-weight:400; }}
  details.phase {{ border-left:2px solid #2d3340; margin:0 0 6px; padding:0 0 0 12px; }}
  summary {{ cursor:pointer; display:flex; justify-content:space-between; padding:5px 0; font-weight:600; }}
  .ph-sum {{ color:#7dd3a8; font-variant-numeric: tabular-nums; }}
  .leaf {{ background:#1d212a; border-radius:8px; padding:8px 10px; margin:5px 0; border-left:3px solid #3a4150; }}
  .leaf.k-faktum {{ border-left-color:#4f8cff; }}
  .leaf.k-berechnung {{ border-left-color:#3ecf8e; }}
  .leaf.k-crosscheck {{ border-left-color:#a78bfa; }}
  .leaf.k-luecke {{ border-left-color:#ef5350; background:#26181a; }}
  .leaf-head {{ display:flex; align-items:baseline; gap:8px; }}
  .src {{ flex:1; }}
  .val {{ font-variant-numeric: tabular-nums; color:#fff; font-weight:600; white-space:nowrap; }}
  .leaf-prov {{ margin-top:4px; font-size:11.5px; color:#828a98; display:flex; gap:10px; }}
  .node {{ color:#7c93b8; font-family:ui-monospace,monospace; }}
  .ref {{ flex:1; }}
  .missing {{ color:#ff8a80; font-style:normal; }}
  .badge {{ font-size:10px; padding:1px 6px; border-radius:4px; font-weight:700; text-transform:uppercase; }}
  .badge.cond {{ background:#5a4a1a; color:#ffd479; }}
  .badge.k-faktum {{ background:#1a3358; color:#9cc2ff; }}
  .badge.k-berechnung {{ background:#16402c; color:#7dd3a8; }}
  .badge.k-crosscheck {{ background:#2e2456; color:#c4b5fd; }}
  .badge.k-luecke {{ background:#4a1a1a; color:#ff9a9a; }}
  .wf-row {{ display:flex; align-items:center; gap:10px; margin:6px 0; }}
  .wf-name {{ width:90px; font-size:12.5px; }}
  .wf-bar {{ flex:1; background:#1d212a; border-radius:5px; height:20px; overflow:hidden; }}
  .wf-fill {{ height:100%; background:linear-gradient(90deg,#4f8cff,#3ecf8e); }}
  .wf-val {{ width:54px; text-align:right; font-variant-numeric:tabular-nums; }}
  .gate {{ background:#1d212a; border:1px solid #2d3340; border-radius:8px; padding:9px 11px; margin:7px 0; }}
  .gate-q {{ font-weight:600; }}
  .gate-arm.yes {{ color:#7dd3a8; font-size:12.5px; margin-top:3px; }}
  .gate-src {{ color:#828a98; font-size:11px; margin-top:2px; }}
  .cc-note {{ background:#1c1830; border:1px solid #3a2f5c; border-radius:8px; padding:11px; margin-top:14px; font-size:12px; }}
  .cc-warn {{ color:#c4b5fd; }}
</style></head><body><div class="wrap">
  <h1>Kalkulation als Entscheidungsbaum — echte Traces aus der Engine</h1>
  <p class="lede">Quelle: <code>GraphPricingEngine.provenance</code> (derselbe Trace wie Produktion).
     Separates viz-Modul, Engine unverändert. 3 Darstellungen desselben echten Laufs zum Vergleich.</p>
  <div class="legend">
    <span class="badge k-faktum">Faktum (Quelle + Graph-Knoten)</span>
    <span class="badge k-berechnung">Berechnung</span>
    <span class="badge k-crosscheck">Crosscheck (nicht im Preis)</span>
    <span class="badge k-luecke">Lücke (keine Quelle)</span>
    <span class="badge cond">if = Bedingung im Schritt</span>
  </div>
  {body}
</div></body></html>'''


if __name__ == "__main__":
    out = OUT / "kalkulation_baum.html"
    out.write_text(render_all(), encoding="utf-8")
    print(f"HTML → {out}")
