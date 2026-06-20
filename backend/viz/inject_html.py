"""Fügt pro Testfall eine Tab 'Berechnung Schritt-für-Schritt' in testrunde1_analyse.html ein.
Idempotent: bereits getabbte Fälle werden übersprungen. Tab-CSS/JS einmalig in <head>.

PANES[case_id] = HTML-Fragment (nutzt vorhandene CSS-Klassen der Datei).
"""
from pathlib import Path

HTML = Path("/Users/piotrzwolinski/Downloads/testrunde1_analyse.html")

TAB_CSS = """
  /* --- Berechnungs-Tabs (injiziert) --- */
  .tabs { display:flex; gap:6px; margin:-2px 0 16px; border-bottom:1px solid #eee; }
  .tab-btn { background:none; border:none; font:inherit; font-size:13px; font-weight:600; color:#888; padding:8px 14px; cursor:pointer; border-bottom:2px solid transparent; margin-bottom:-1px; }
  .tab-btn.active { color:#3b5998; border-bottom-color:#3b5998; }
  .tab-pane { display:none; }
  .tab-pane.active { display:block; }
  .calc-step td:first-child { color:#333; }
  .calc-step .amt { text-align:right; font-variant-numeric:tabular-nums; font-weight:600; white-space:nowrap; }
  .calc-step .src2 { color:#999; font-size:12px; }
  .calc-step .sum td { border-top:2px solid #ddd; font-weight:700; }
  .band td { font-size:12.5px; }
  .keyq { background:#fef2f2; border-left:3px solid #ef4444; padding:12px 16px; border-radius:0 8px 8px 0; margin-top:12px; font-size:14px; }
"""

TAB_JS = """
<script>
function caltab(btn, pane){
  const body = btn.closest('.case-body');
  body.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  body.querySelectorAll('.tab-pane').forEach(p=>p.classList.remove('active'));
  body.querySelector('.tab-pane[data-pane="'+pane+'"]').classList.add('active');
}
</script>
"""

TABBAR = ('<div class="tabs">'
          '<button class="tab-btn active" onclick="caltab(this,\'fb\')">Feedback &amp; Maßnahmen</button>'
          '<button class="tab-btn" onclick="caltab(this,\'calc\')">Berechnung Schritt-für-Schritt</button>'
          '</div>\n<div class="tab-pane active" data-pane="fb">')


PANES = {}

PANES["T01"] = """
<div class="section">
  <div class="section-label">So rechnet die Engine — Schritt für Schritt</div>
  <p style="font-size:13px;color:#555;margin-bottom:8px">Geparster Input: VdS · Industrie · 20.000 m² · 45 UV · PLZ 85276 → NL München (55 km). <b>Kategorie aktuell: Kat 3 (Produktion).</b></p>
  <table class="calc-step">
    <tr><th>Schritt</th><th class="amt">Wert</th><th>Herkunft</th></tr>
    <tr><td>Grundpreis Anlage (VdS 2871)</td><td class="amt">250 €</td><td class="src2">LPV B04 Kap. 2</td></tr>
    <tr><td>Flächenkosten — 20.000 m² × <b>5,0 €/10m²</b> (Kat 3) · VdS-Degression</td><td class="amt">6.600 €</td><td class="src2">Kalkulationshilfen NBG</td></tr>
    <tr><td>Verteilungen — 45 UV × 25 €</td><td class="amt">1.125 €</td><td class="src2">Schätzung intern</td></tr>
    <tr class="sum"><td>= Prüfkosten</td><td class="amt">7.975 €</td><td></td></tr>
    <tr><td>Grundkosten — Pauschale 256 + Prüfmittel 392 (49€×8 Tage) + Tagegeld 200</td><td class="amt">848 €</td><td class="src2">LPV §4 · 8 Prüftage = 20k÷2500 (Heuristik)</td></tr>
    <tr><td>Reisekosten — Pfaffenhofen 55 km, <b>3 Anfahrten</b> (8 Tage → mehrtägig)</td><td class="amt">1.286 €</td><td class="src2">CRM PLZ→NL · LPV §4.3</td></tr>
    <tr><td>Bericht (komplex)</td><td class="amt">550 €</td><td class="src2">LPV: Klein 119 / Std 380 / Komplex 550</td></tr>
    <tr class="sum"><td>= Gesamt</td><td class="amt">10.659 €</td><td class="src2">Real 6.850 € → <span class="delta-pos">+56 %</span></td></tr>
  </table>
</div>

<div class="section">
  <div class="section-label">Flächenkosten — Bandweise Degression (das ist der größte Block)</div>
  <table class="band">
    <tr><th>Band m²</th><th>m²</th><th>× 0,5 €/m² (Kat 3)</th><th>× VdS-Faktor</th><th class="amt">=</th></tr>
    <tr><td>0–2.000</td><td>2.000</td><td></td><td>1,00</td><td class="amt">1.000 €</td></tr>
    <tr><td>2.000–4.000</td><td>2.000</td><td></td><td>0,90</td><td class="amt">900 €</td></tr>
    <tr><td>4.000–6.000</td><td>2.000</td><td></td><td>0,80</td><td class="amt">800 €</td></tr>
    <tr><td>6.000–10.000</td><td>4.000</td><td></td><td>0,70</td><td class="amt">1.400 €</td></tr>
    <tr><td>10.000–20.000</td><td>10.000</td><td></td><td>0,50</td><td class="amt">2.500 €</td></tr>
    <tr class="sum"><td colspan="4">Summe Flächenkosten (Kat 3)</td><td class="amt">6.600 €</td></tr>
  </table>
  <p style="font-size:12.5px;color:#888;margin-top:6px">VdS degressiert weniger als DGUV (steilere Kurve) — gleiche Basisrate, weniger Größenrabatt, weil VdS gründlicher ist.</p>
</div>

<div class="keyq">
  <b>Kategorie ist die größte Stellschraube — und Pauschs Entscheidung:</b><br>
  Kat 3 (Produktion, 5,0 €) → 10.659 € (<span class="delta-pos">+56 %</span>, FAIL) · Kat 2 (Büro/Standard, 3,1 €) → ~8.078 € (<b>+18 %</b>, fast PASS).<br>
  Der reale Angebot ist wie <b>Kat 2</b> bepreist. Aber: Kategorie nicht an den Wunschpreis anpassen — Pausch sagt die fachlich richtige Kategorie (reale Installationsdichte). Ist Produktion = Kat 3, dann heißt +56 %, dass die <b>VdS-Kurve für Großindustrie zu steil</b> ist → rekalibrieren, nicht umlabeln.
</div>

<div class="section" style="margin-top:14px">
  <div class="section-label">Mapping auf das Dokument — Angebot 6.850 € (Q3 ZIP, EQ1550815)</div>
  <p style="font-size:14px">Unsere <b>Leistung ohne Reise</b> = 848 + 7.975 + 550 = 9.373 € bei Kat 3 — bei Kat 2: 848 + 5.467 + 550 = <b>6.865 €</b>, also fast exakt die realen 6.850 €. Heißt: mit Kat 2 trifft die <b>reine Prüfleistung punktgenau</b>, und die Gesamt-Überschätzung kommt von den <b>Reisekosten</b> (3 statt evtl. 1 Anfahrt). Die Kalkulation der Prüfung selbst ist nicht das Problem.</p>
</div>

<div class="section">
  <div class="section-label">Zwei Inputs, die ins Leere fallen</div>
  <ul style="font-size:14px;margin-left:18px">
    <li><b>8.000 kVA Trafo wird ignoriert</b> — im Input genannt, im Trace keine einzige Position dafür. Für eine VdS-Prüfung einer 8.000-kVA-Station ist das erhebliche Arbeit (kVA-Zuschlag fehlt, offener Bug).</li>
    <li><b>25 €/UV ist „Schätzung intern"</b> — Dehner/Augsburg legen 116–283 €/UV nahe. Entweder deutlich zu niedrig, oder per-UV gehört gar nicht additiv zur Flächen-Methode.</li>
  </ul>
</div>
"""


PANES["T02"] = """
<div class="section">
  <div class="section-label">So rechnet die Engine — Schritt für Schritt</div>
  <p style="font-size:13px;color:#555;margin-bottom:8px">Geparster Input: DGUV ortsfest · Verkaufsstätte · 800 m² · PLZ 85386 → NL München (25 km). Kategorie auto: Kat 2 (3,1 €).</p>
  <table class="calc-step">
    <tr><th>Schritt</th><th class="amt">Wert</th><th>Herkunft</th></tr>
    <tr><td>Grundpreis Anlage (DGUV V3)</td><td class="amt">250 €</td><td class="src2">LPV B04 Kap. 2</td></tr>
    <tr><td>Flächenkosten — 800 m² × 3,1 €/10m² · Degression (Band 0–2.000 = 0,80)</td><td class="amt">198 €</td><td class="src2">Kalkulationshilfen NBG</td></tr>
    <tr class="sum"><td>= Prüfkosten</td><td class="amt">448 €</td><td></td></tr>
    <tr><td>Grundkosten — Pauschale 256 + Prüfmittel 49 + Tagegeld 25 (1 Prüftag)</td><td class="amt">330 €</td><td class="src2">LPV §4</td></tr>
    <tr><td>Reisekosten — 25 km, 1 Anfahrt (1 Tag ≤ 9h)</td><td class="amt">220 €</td><td class="src2">CRM PLZ→NL · LPV §4.3</td></tr>
    <tr><td>Bericht (Standard)</td><td class="amt">380 €</td><td class="src2">LPV</td></tr>
    <tr class="sum"><td>= Gesamt</td><td class="amt">1.378 €</td><td class="src2">Real 657 € → <span class="delta-pos">+110 %</span></td></tr>
  </table>
</div>

<div class="keyq">
  <b>Das ist KEIN Rechenfehler — es ist ein Rahmenvertrag (RV).</b><br>
  Die 657 € sind ein <b>Filialnetz-Flatpreis</b>: REWE zahlt pro Filiale pauschal ~657 €, egal wie groß. Unsere 1.378 € sind der korrekte <b>Listenpreis (LPV)</b>. Die +110 % sind der RV-Rabatt, nicht ein Fehler.<br>
  <b>Beweis:</b> T02 (800 m²) und T11 (REWE München, 1.600 m²) ergeben <b>beide exakt 657,26 €</b> — doppelte Fläche, gleicher Preis ⇒ Flatpreis, nicht größenbasiert. Das System flaggt das korrekt (Konfidenz 81 %, RV-Banner).
</div>

<div class="section" style="margin-top:14px">
  <div class="section-label">Zweiter Effekt: kleines Objekt = Overhead dominiert</div>
  <p style="font-size:14px">Selbst der Listenpreis ist bei kleinen Objekten fixkosten-lastig: <b>Bericht 380 + Grundkosten 330 + Reise 220 = 930 €</b> Overhead gegenüber nur <b>448 € echter Prüfung</b>. Die Kalkulation ist nicht falsch, aber bei 800 m² erdrücken die Fixkosten die eigentliche Leistung.</p>
</div>

<div class="section">
  <div class="section-label">Mapping auf das Dokument — Q3 ZIP (Pausch XLSX, ZIP-2)</div>
  <p style="font-size:14px">Referenz 657,26 € stammt aus der Übersichtstabelle, nicht aus einem Einzel-Angebot. <b>Für RV-Kunden kommt der Preis aus dem Vertrag, nicht aus dem Rechner.</b> Den Rechner mit dem RV-Preis zu vergleichen ist Äpfel-mit-Birnen — die richtige Aufgabe des Rechners ist der Listenpreis, der Rabatt ist eine kaufmännische Ebene darüber.</p>
</div>
"""


def inject(html: str, panes: dict) -> str:
    # 1. CSS einmalig
    if ".tab-btn" not in html:
        html = html.replace("</style>", TAB_CSS + "</style>", 1)
    # 2. JS einmalig (vor </body>)
    if "function caltab" not in html:
        html = html.replace("</body>", TAB_JS + "</body>", 1)
    # 3. pro Fall: case-block finden, body wrappen, calc-pane einfügen
    parts = html.split('<div class="case">')
    head = parts[0]
    out = [head]
    for chunk in parts[1:]:
        cid = None
        import re
        m = re.search(r'<span class="case-id">(T\d+)</span>', chunk)
        if m:
            cid = m.group(1)
        if cid in panes and 'data-pane="calc"' not in chunk:
            # body öffnen → Tabbar + fb-pane
            chunk = chunk.replace('<div class="case-body">\n', '<div class="case-body">\n    ' + TABBAR + '\n', 1)
            # body schließen: die letzten zwei </div> = case-body close + case close
            i_case = chunk.rfind('</div>')
            i_body = chunk.rfind('</div>', 0, i_case)
            calc = '</div>\n<div class="tab-pane" data-pane="calc">\n' + panes[cid] + '\n</div>\n'
            chunk = chunk[:i_body] + calc + chunk[i_body:]
        out.append(chunk)
    return '<div class="case">'.join(out)


if __name__ == "__main__":
    html = HTML.read_text(encoding="utf-8")
    html = inject(html, PANES)
    HTML.write_text(html, encoding="utf-8")
    print(f"Injiziert: {list(PANES.keys())} → {HTML}")
