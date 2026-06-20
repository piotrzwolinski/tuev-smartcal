#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Baut den kombinierten Status-Report: Status-Overview (Mo→Fr) + die
Detail-Case-Blöcke aus dem Montags-Report, je mit „Seit Montag"-Update.
Plus Höflichkeits-Namensfix (S. Pausch statt Pausch)."""
import re

SRC = "/Users/piotrzwolinski/Downloads/testrunde1_analyse.html"
OUT = "/Users/piotrzwolinski/Downloads/testrunde1_status_komplett_2026-06-19.html"

html = open(SRC, encoding="utf-8").read()

# ── 1. Extra-CSS einfügen ─────────────────────────────────────────────
EXTRA_CSS = """
  h2 { font-size: 17px; margin: 34px 0 14px; padding-bottom: 6px; border-bottom: 2px solid #e3e6ea; }
  .hero { background: linear-gradient(135deg,#1e3a5f,#3b5998); color:#fff; border-radius:12px; padding:22px 26px; margin-bottom:24px; }
  .hero .big { font-size: 30px; font-weight: 800; }
  .hero .big span { opacity:.6; font-weight:600; font-size:21px; }
  .hero p { font-size:14px; opacity:.93; margin-top:6px; }
  .summary-box .delta { font-size: 11px; color:#9aa; }
  .card { background:#fff; border-radius:10px; box-shadow:0 1px 4px rgba(0,0,0,.07); padding:14px 18px; margin-bottom:12px; }
  .card h3 { font-size:14px; margin-bottom:5px; }
  .card .tag { font-size:11px; font-family:monospace; background:#eef1f6; color:#3b5998; padding:1px 7px; border-radius:5px; }
  .card p { font-size:13.5px; color:#444; margin-top:3px; }
  .grid2 { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
  .data-card { background:#fff; border-left:3px solid #6366f1; border-radius:0 8px 8px 0; padding:11px 15px; box-shadow:0 1px 3px rgba(0,0,0,.05); }
  .data-card h4 { font-size:13.5px; margin-bottom:3px; }
  .data-card p { font-size:12.5px; color:#555; }
  .open { background:#fffaf0; border-left:3px solid #f59e0b; padding:12px 16px; border-radius:0 8px 8px 0; }
  .open ul { margin-left:18px; font-size:13.5px; } .open li { margin-bottom:5px; }
  .note { font-size:12.5px; color:#777; }
  .legend { font-size:11.5px; color:#888; margin-top:8px; }
  .row-win td { background:#d9f5e2 !important; }
  .row-win td:first-child { box-shadow: inset 3px 0 0 #22c55e; }
  .upd { border-left:3px solid #28a745; background:#f3fbf5; border-radius:0 8px 8px 0; padding:10px 14px; margin:0 0 14px; }
  .upd.flat { border-left-color:#9ca3af; background:#f6f7f9; }
  .upd .lbl { font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.5px; margin-bottom:3px; }
  .upd.flat .lbl { color:#6b7280; } .upd .lbl { color:#1e8e4a; }
  .upd p { font-size:13.5px; color:#333; }
"""
html = html.replace("</style>", EXTRA_CSS + "\n</style>", 1)

# ── 2. Overview (ersetzt h1..summary-bar bis zum ersten Case) ──────────
OVERVIEW = """
<h1>SmartCal@EG — Wochen-Status &amp; Detail je Testfall</h1>
<p class="subtitle">Montag 15.06. → Freitag 19.06.2026 · für Status-Call mit S. Pausch · Zahlen aus der konsolidierten Engine (live auf Fly v25)</p>

<div class="hero">
  <div class="big">4 → 8 PASS <span>· alle 16 live im UI bestätigt</span></div>
  <p>Seit dem Montags-Call von <strong>4 auf 8 grüne Testfälle</strong> verdoppelt. Treiber: Antworten von S. Pausch (17.06.) + 2 neue Referenzlisten haben die Blocker gelöst → 4 Pricing-Änderungen umgesetzt, getestet, deployed. <strong>Alle 16 Fälle am 19.06. live im Chat-UI nachgetestet</strong> (nicht über Endpoint) — die 8 PASS halten. Zusätzlich 2 große reale Preis-Datensätze erhalten (MA505 + Kliniken Schmieder).</p>
</div>

<div class="summary-bar">
  <div class="summary-box"><div class="num" style="color:#28a745">8</div><div class="delta">▲ war 4 (Mo)</div><div class="label">PASS (≤20 %)</div></div>
  <div class="summary-box"><div class="num" style="color:#dc3545">2</div><div class="delta">T01 wartet · T03 Reise</div><div class="label">FAIL</div></div>
  <div class="summary-box"><div class="num" style="color:#0c5460">1</div><div class="delta">war 4</div><div class="label">RV-FLAG</div></div>
  <div class="summary-box"><div class="num" style="color:#888">4</div><div class="delta">Ref defekt / Multi</div><div class="label">xfail · 1 NO-REF</div></div>
  <div class="summary-box"><div class="num" style="color:#28a745">16/16</div><div class="delta">19.06 Chat</div><div class="label">live UI getestet</div></div>
  <div class="summary-box"><div class="num" style="color:#28a745">547</div><div class="delta">grün</div><div class="label">pytest</div></div>
</div>

<h2>1 · Diese Woche umgesetzt (jede Änderung getestet + deployed)</h2>
<div class="card"><h3>A3 — Einzelhandel-Referenz „REWE-Liste" 848 € <span class="tag">e57b6f7</span></h3><p>S. Pausch (17.06): REWE-Liste = Referenz für <em>alle</em> Einzelhandelsprojekte, 2.001–5.000 m² = 848 €. Als RV-Flat (all-in) umgesetzt → <strong>T02 + T11 von RV-FLAG auf +0 % PASS</strong>.</p></div>
<div class="card"><h3>A5 — Hotel-Referenzkurve „Motel One" (Zimmer-Staffel) <span class="tag">311ce83</span></h3><p>Hotels → Preis nach <strong>Zimmerzahl</strong> (Motel-One-Liste, M. Pfeifer) statt m²-Fallback. Schließt die Hotel-Routing-Lücke (T06, T13).</p></div>
<div class="card"><h3>A0 — VdS-Branchen-Kategorien <span class="tag">15707d1</span></h3><p>S. Pausch-Regeln: Kita separat; 0800 = Produktion, 0904 = Verkaufsstätten. Nahrungsmittel-Produktion an <em>einer</em> Konstante → Hipp-Entscheidung = 1-Zeilen-Flip.</p></div>
<div class="card"><h3>D-K7 — Kat-7-Rate korrigiert (5,42 → 8,00 €/10 m²) <span class="tag">626c0f7</span></h3><p>Bug: Kat-7 (OP/Intensiv) war <em>billiger</em> als Kat-6 — Monotonie gebrochen. NBG-skaliert 8,00 (S. Pausch 17.06: OP/Intensiv = Faktor 2). <strong>T12 Helios MARGINAL −35 % → +17 % PASS</strong>.</p></div>
<div class="card"><h3>V1 + V3 — Validierung &amp; Inflation gegen reale MA505-Daten <span class="tag">8c91627 · f785561</span></h3><p>V1: VdS-Modell gegen reale MA505-Verteilung geprüft (Korridor bestätigt). V3: Inflation 2024/25 von 8,3 %/5,5 % auf real <strong>2,5 %</strong> korrigiert (Anker 641,23 → 657,26 €).</p></div>

<h2>2 · Neue reale Daten erhalten (diese Woche)</h2>
<div class="grid2">
  <div class="data-card"><h4>Antworten S. Pausch 17.06.</h4><p>REWE 848 €, Kombi = Verkaufsthema (×1,20), Kita/0800/0904, Test 5/6 fehlerhaft bestätigt, Industrie = Preisliste reicht.</p></div>
  <div class="data-card"><h4>Helios-Angebot (T12, M. Pfeifer)</h4><p>Realwert 13.110 € = <strong>54 h × 239 €/h Aufwand</strong> — kein m²-Preis. Begründet das Aufwand-Modell.</p></div>
  <div class="data-card"><h4>Motel-One-Preisliste 2025</h4><p>Hotel = <strong>Zimmer-Staffel</strong>. Direkt in A5 umgesetzt.</p></div>
  <div class="data-card"><h4>MA505-Export (M. Burgey 18.06)</h4><p><strong>5.995 reale VdS-Ist-Umsätze</strong> (SAP). Median 1.190 €. RV-Flat bestätigt (657,26 € = T02/T11-Real, 80×). 507 + 560 folgen.</p></div>
  <div class="data-card"><h4>Kliniken Schmieder (M. Pfeifer 18.06)</h4><p>6 Standorte, <strong>6 reale VdS-Klinik-Preise</strong> (655–5.880 €/Campus). Verifiziert.</p></div>
  <div class="data-card"><h4>EQ-Join (läuft, S. Pausch)</h4><p>MA505 + Schmieder liefern Preise je EQ. S. Pausch löst auf, was hinter jeder EQ steckt → Kurve kalibrierbar.</p></div>
</div>

<h2>3 · Offen / nächste Schritte (zur AL-Tagung 30.06.)</h2>
<div class="open"><ul>
  <li><strong>Hipp Kat 2/3</strong> — Entscheidung S. Pausch heute (Fr 20.06.) → sofort 1-Zeilen-Flip (Kat 2 ≈ +18 %). Letzter unmanaged FAIL.</li>
  <li><strong>EQ-Auflösung</strong> (MA505 + Schmieder) — m²/Anlagen je EQ → Krankenhaus-/VdS-Kurve real kalibrieren.</li>
  <li><strong>Exporte 507 + 560</strong> (S. Pausch, Fr/Mo) — gleiche Validierung für DGUV-ortsfest + ortsveränderlich.</li>
  <li><strong>Aufwand-Modell</strong> (Stunden × Satz) für Krankenhaus/Industrie — Helios bestätigt Bedarf; nach Tagung.</li>
  <li><strong>Reisekosten/Geocoding für Kleinst-Aufträge</strong> (T03 badenova) — Live-UI geocodiert die Anfahrt höher (+51 % statt +26 %); Reisekosten-Bündelung / nächste NL prüfen.</li>
  <li><strong>Nutzungstyp-Extraktion robuster</strong> — Ergebnis ist typ-sensitiv (T08: „Bürogebäude" +1 % vs „Industrie" +38 %); Chat-Erkennung schärfen.</li>
  <li><strong>UI-Politur</strong> für 4–5 Demo-Fälle (Piotr) — REWE 848 € + Motel One live-UI bestätigt.</li>
</ul></div>

<h2>4 · Detail je Testfall — Montag + Update (alle live im UI getestet)</h2>
<p class="note" style="margin-bottom:18px;">Die KPI-Box „SmartCal (konsolidiert)" zeigt den <strong>Montags-Stand</strong>; der farbige Kasten darunter den <strong>Freitags-Stand, am 19.06. live im Chat-UI getestet</strong> (echter Klick-Weg, nicht über Endpoint) — plus was sich geändert hat.</p>
"""

# ── Übersichtstabelle 16 Testfälle (UI-getestet) ─────────────────────
# (id, Titel, Real, Mo-Verdict-Klasse, Mo-Text, Fr €·Δ, Fr-Klasse, Fr-Status, Änderung, win)
TBL = [
 ("T01","Hipp Nahrungsmittel (VdS)","6.850","badge-marginal","Kat-Frage","10.416 · +52 %","badge-fail","FAIL","wartet S. Pausch (Kat 2/3)",0),
 ("T02","REWE Eching (RV)","848","badge-rv","RV-FLAG","848 · +0 %","badge-pass","PASS","▲ A3 REWE-Liste 848 €",1),
 ("T03","badenova Schaltschrank","391","badge-marginal","+26 %","590 · +51 %","badge-fail","FAIL","UI-Reise höher (Geocoding)",0),
 ("T04","Auto Service Calw (MA560)","1.217","badge-marginal","+29 %","1.283 · +5 %","badge-pass","PASS","▲ in Toleranz",1),
 ("T05","Landwirt (MA560)","175","badge-xfail","xfail","419","badge-xfail","xfail","Ref defekt (S. Pausch)",0),
 ("T06","Maritim Hotel (MA510)","220","badge-xfail","xfail","5.439 · Zimmer","badge-xfail","xfail","A5 Zimmer; Ref defekt",0),
 ("T07","König &amp; Bauer (VdS)","—","badge-xfail","kein Real","2.861","badge-xfail","NO-REF","rechenbar, Ref fehlt",0),
 ("T08","Apleona Gilching (Kombi)","7.932","badge-pass","+1 %","8.038 · +1 %","badge-pass","PASS","stabil (als Büro)",0),
 ("T09","Weber-Gymnasium (Multi)","4.800","badge-xfail","xfail","3.730","badge-xfail","xfail","Multi = MVP",0),
 ("T10","Max Planck RZ (MA560)","5.341","badge-pass","+12 %","5.378 · +1 %","badge-pass","PASS","▲ verbessert",1),
 ("T11","REWE München (RV)","848","badge-rv","RV-FLAG","848 · +0 %","badge-pass","PASS","▲ A3 wie T02",1),
 ("T12","Helios Klinik (Kombi)","13.110","badge-marginal","−35 %","13.563 · +3 %","badge-pass","PASS","▲ D-K7 (Kat-7)",1),
 ("T13","Motel One München (RV)","621","badge-rv","RV-FLAG","4.313 · Zimmer","badge-xfail","xfail","A5 Zimmer; Ref defekt",0),
 ("T14","roMEd Klinik Prien","5.136*","badge-pass","PASS","4.494 · −12 %","badge-pass","PASS","stabil",0),
 ("T15","DGUV Würzburg","4.195","badge-pass","+12 %","4.707 · +12 %","badge-pass","PASS","stabil",0),
 ("T16","Polizei Dachau (Blitz)","205","badge-rv","RV-FLAG","1.295 · RV","badge-rv","RV-FLAG","RV-Listenpreis",0),
]
def _row(i,t,r,mc,mt,fr,fc,fs,ch,w):
    rc = ' class="row-win"' if w else ''
    return (f'  <tr{rc}><td><strong>{i}</strong></td><td>{t}</td><td>{r}</td>'
            f'<td><span class="badge {mc}">{mt}</span></td><td>{fr}</td>'
            f'<td><span class="badge {fc}">{fs}</span></td><td>{ch}</td></tr>')
_rows = "\n".join(_row(*x) for x in TBL)
TABLE_SECTION = (
 '<h2>1 · Übersicht 16 Testfälle — Montag → Freitag (live im UI getestet)</h2>\n'
 '<table>\n  <tr><th>#</th><th>Fall</th><th>Real €</th><th>Mo 15.06</th>'
 '<th>Fr 19.06 (€ · Δ)</th><th>Status</th><th>Änderung</th></tr>\n'
 + _rows + '\n</table>\n'
 '<p class="legend">Grün hinterlegt = seit Montag verbessert (▲). „Zimmer" = Hotel '
 '(bewusst xfail, Referenz defekt, aber Engine jetzt Zimmer-basiert). * inflationsbereinigt. '
 'Δ positiv = SmartCal über Real. Alle Werte am 19.06. live im Chat-UI getestet.</p>\n')

# Tabelle nach der Summary-Bar einfügen + Folge-Überschriften umnummerieren
OVERVIEW = OVERVIEW.replace('<h2>1 · Diese Woche', TABLE_SECTION + '<h2>2 · Diese Woche')
OVERVIEW = OVERVIEW.replace('<h2>2 · Neue reale Daten', '<h2>3 · Neue reale Daten')
OVERVIEW = OVERVIEW.replace('<h2>3 · Offen', '<h2>4 · Offen')
OVERVIEW = OVERVIEW.replace('<h2>4 · Detail je Testfall', '<h2>5 · Detail je Testfall')

case_start = html.find('<div class="case">')
body_open = html.find("<body>") + len("<body>")
html = html[:body_open] + "\n" + OVERVIEW + "\n" + html[case_start:]

# ── 3. Pro Case einen „Seit Montag"-Block einfügen ────────────────────
# fr-Wert = LIVE im UI (Chat) getestet am 19.06 — nicht über Endpoint.
UP = {
 "T01": (0,"badge-fail","FAIL","10.416 € · +52 %","<em>Live UI getestet.</em> Unverändert in der Sache — wartet auf die Kat-Entscheidung von S. Pausch (Kat 2/3, heute). A0 hat die 0800-Produktion auf <em>eine</em> Konstante gelegt → 1-Zeilen-Flip bei Entscheidung (Kat 2 ≈ +18 %)."),
 "T02": (1,"badge-pass","PASS","848 € · +0 %","<em>Live UI getestet ✓.</em> <strong>▲ A3</strong>: REWE-Liste 848 € als RV-Flat (Grund/Reise/Bericht im Listenpreis enthalten). Von RV-FLAG (Mo 1.378 €) auf PASS — exakt der von S. Pausch (17.06) bestätigte Listenwert."),
 "T03": (1,"badge-fail","FAIL","590 € · +51 %","<em>Live UI getestet.</em> Prüf 270 € korrekt (Kleinauftrag), aber <strong>Reisekosten höher geocodiert (220 € statt 122 €)</strong> → +51 % statt +26 %. Geocoding/Reisekosten-Bündelung für Kleinst-Aufträge ist offen (nächster Schritt)."),
 "T04": (1,"badge-pass","PASS","1.283 € · +5 %","<em>Live UI getestet ✓.</em> <strong>▲</strong> Jetzt in PASS-Toleranz (Mo war +29 % MARGINAL)."),
 "T05": (0,"badge-xfail","xfail","419 €","<em>Live UI getestet.</em> Unverändert — Referenz defekt, von S. Pausch bestätigt (Maschinenring-Preise folgen)."),
 "T06": (1,"badge-xfail","xfail","5.439 € · Zimmer","<em>Live UI getestet.</em> <strong>A5</strong>: jetzt Zimmer-basiert (Motel-One-Kurve, Prüf 2.566 € für 100 Zimmer) statt m². Bleibt xfail — Referenz 220 € defekt (S. Pausch: Markus liefert Realwert)."),
 "T07": (0,"badge-xfail","NO-REF","2.861 €","<em>Live UI getestet.</em> Unverändert — rechenbar, Referenz fehlt."),
 "T08": (1,"badge-pass","PASS","8.038 € · +1 %","<em>Live UI getestet ✓.</em> Als <strong>Bürogebäude</strong> (Apleona = FM/Verwaltung) → Augsburg-Referenz, +1 %. Hinweis: Wording Industriegebäude → Kat 3 → +38 % — das Ergebnis ist <strong>nutzungstyp-sensitiv</strong> (Extraktions-Qualität)."),
 "T09": (0,"badge-xfail","xfail","3.730 €","<em>Live UI getestet.</em> Unverändert — Multi-Produkt = MVP (nur ELT-Anteil; BMA/SiBe nicht im Scope)."),
 "T10": (1,"badge-pass","PASS","5.378 € · +1 %","<em>Live UI getestet ✓.</em> <strong>▲</strong> Verbessert (Mo +12 % → +1 %)."),
 "T11": (1,"badge-pass","PASS","848 € · +0 %","<em>Live UI getestet ✓.</em> <strong>▲ A3</strong> wie T02 — REWE-Liste 848 €."),
 "T12": (1,"badge-pass","PASS","13.563 € · +3 %","<em>Live UI getestet ✓.</em> <strong>▲ D-K7</strong>: Kat-7 von 5,42 auf 8,00 €/10 m² korrigiert (Monotonie-Bug; S. Pausch 17.06: OP/Intensiv = Faktor 2). Mit OP + Intensivstation im Chat trifft das UI <strong>+3 %</strong> (sogar näher am Realwert als der idealisierte Skript-Wert). Realwert 13.110 € = 54 h × 239 €/h Aufwand (Helios-Angebot, M. Pfeifer)."),
 "T13": (1,"badge-xfail","xfail","4.313 € · Zimmer","<em>Live UI getestet.</em> <strong>A5</strong>: Motel-One-Zimmer-Staffel (200 Zimmer → 3.160 € Prüf) statt NBG-m² (Mo 5.161 €). Reklassifiziert RV-FLAG → xfail: Referenz 621 € defekt, S. Pausch prüft (Liste deutlich höher)."),
 "T14": (0,"badge-pass","PASS","4.494 € · −12 %","<em>Live UI getestet ✓.</em> Stabil/PASS (inflationsbereinigt). UI-Kat-Extraktion etwas niedriger als Skript (−12 % vs −5 %), bleibt im PASS-Band."),
 "T15": (0,"badge-pass","PASS","4.707 € · +12 %","<em>Live UI getestet ✓.</em> Stabil."),
 "T16": (0,"badge-rv","RV-FLAG","1.295 € · RV","<em>Live UI getestet</em> (Blitzschutz-Produkt). Unverändert (RV-Listenpreis)."),
}

def block(cid):
    changed, cls, status, fr, note = UP[cid]
    flat = "" if changed else " flat"
    lbl = "🔄 Seit Montag — geändert" if changed else "🔄 Seit Montag — unverändert"
    return (f'<div class="upd{flat}"><div class="lbl">{lbl}</div>'
            f'<p><strong>Fr 19.06: {fr}</strong> &nbsp;·&nbsp; '
            f'<span class="badge {cls}">{status}</span> &nbsp;—&nbsp; {note}</p></div>')

# 4. KPI-Box je Case: frischester Wert (live im UI getestet 19.06).
# (value, kpi-small, badge-class für Farbe)
UIBOX = {
 "T01": ("10.416 €","Δ +52 % · Prüf 7.975 · Grund 678 · Reise 1.213 · Bericht 550","badge-fail"),
 "T02": ("848 €","Δ +0 % · RV-Flat all-in (Prüf 848, Grund/Reise/Bericht entfallen)","badge-pass"),
 "T03": ("590 €","Δ +51 % · Prüf 270 · Grund 100 · Reise 220 · Bericht 0","badge-fail"),
 "T04": ("1.283 €","Δ +5 % · MA560 all-in (Prüf 1.283)","badge-pass"),
 "T05": ("419 €","xfail · MA560 (Prüf 419) · Referenz defekt","badge-xfail"),
 "T06": ("5.439 €","xfail · Prüf 2.566 (Zimmer 100) · Reise 1.939 · Bericht 550 · Ref defekt","badge-xfail"),
 "T07": ("2.861 €","kein Real · Prüf 1.866 · Grund 330 · Reise 115 · Bericht 550","badge-xfail"),
 "T08": ("8.038 €","Δ +1 % · Prüf 6.134 · Grund 796 · Reise 558 · Bericht 550 (als Büro)","badge-pass"),
 "T09": ("3.730 €","xfail (nur ELT) · Prüf 2.833 · Grund 384 · Bericht 380","badge-xfail"),
 "T10": ("5.378 €","Δ +1 % · MA560 all-in (Prüf 5.378)","badge-pass"),
 "T11": ("848 €","Δ +0 % · RV-Flat all-in (Prüf 848)","badge-pass"),
 "T12": ("13.563 €","Δ +3 % · Prüf 11.953 · Grund 639 · Reise 422 · Bericht 550","badge-pass"),
 "T13": ("4.313 €","xfail · Prüf 3.160 (Zimmer 200) · Reise 199 · Bericht 550 · Ref defekt","badge-xfail"),
 "T14": ("4.494 €","Δ −12 % · Prüf 2.692 · Grund 443 · Reise 810 · Bericht 550","badge-pass"),
 "T15": ("4.707 €","Δ +12 % · Prüf 3.854 · Grund 384 · Reise 89 · Bericht 380","badge-pass"),
 "T16": ("1.295 €","RV-Listenpreis · Prüf 390 · Grund 330 · Reise 195 · Bericht 380 (Blitz)","badge-rv"),
}
BOXSTYLE = {
 "badge-pass": ("background:#eefdf3; border:1px solid #bbf3cf;", "#16a34a"),
 "badge-fail": ("background:#fff1f1; border:1px solid #f6c9c9;", "#dc3545"),
 "badge-xfail":("background:#f1f3f5; border:1px solid #e2e5e8;", "#5b6b80"),
 "badge-rv":   ("background:#e8f6fa; border:1px solid #c5e7ef;", "#0c5460"),
}

def ui_box(cid):
    val, small, bc = UIBOX[cid]
    bg, col = BOXSTYLE[bc]
    return (f'<div class="kpi" style="{bg}">'
            f'<div class="kpi-label">SmartCal · Fr 19.06 · live UI</div>'
            f'<div class="kpi-value" style="color:{col}">{val}</div>'
            f'<div class="kpi-small">{small}</div></div>')

def _close_div(s, start):
    """start = Index eines '<div'; gibt Index direkt nach dem passenden '</div>' zurück."""
    depth = 0; i = start
    while i < len(s):
        no = s.find('<div', i); nc = s.find('</div>', i)
        if nc == -1: return len(s)
        if no != -1 and no < nc:
            depth += 1; i = no + 4
        else:
            depth -= 1; i = nc + 6
            if depth == 0: return i
    return len(s)

GRID3 = 'grid-template-columns:1fr 1fr 1fr; gap:16px;'
GRID4 = 'grid-template-columns:1fr 1fr 1fr 1fr; gap:12px;'

# Insert: (a) „Seit Montag"-Block nach case-body, (b) 4. KPI-Box in das KPI-Grid
for cid in UP:
    anchor = f'<span class="case-id">{cid}</span>'
    i = html.find(anchor)
    if i == -1:
        print("WARN case fehlt:", cid); continue
    j = html.find('<div class="case-body">', i)
    k = j + len('<div class="case-body">')
    html = html[:k] + "\n" + block(cid) + html[k:]
    # 4. Box in das 3-Box-KPI-Grid dieses Cases einfügen
    si = html.find('SmartCal (konsolidiert)', k)
    if si == -1:
        print("WARN kein KPI-Grid:", cid); continue
    boxopen = html.rfind('<div class="kpi"', k, si)      # 3. Box (SmartCal konsolidiert)
    boxclose = _close_div(html, boxopen)                  # nach dessen </div>
    html = html[:boxclose] + "\n      " + ui_box(cid) + html[boxclose:]
    # Grid dieses Cases auf 4 Spalten verbreitern
    gi = html.rfind(GRID3, k, boxopen)
    if gi != -1:
        html = html[:gi] + GRID4 + html[gi+len(GRID3):]

# ── 4. Höflichkeits-Namensfix (Initiale + Nachname) ───────────────────
html = re.sub(r'(?<!S\. )\bPausch\b', 'S. Pausch', html)
html = re.sub(r'(?<![A-Z]\. )\bPfeiffer\b', 'M. Pfeiffer', html)
html = re.sub(r'(?<![A-Z]\. )\bPfeifer\b', 'M. Pfeifer', html)
html = re.sub(r'(?<!S\. )\bVeit\b', 'S. Veit', html)
html = re.sub(r'(?<!M\. )\bBurgey\b', 'M. Burgey', html)
# Titel-Tag aufräumen
html = html.replace("<title>Testrunde 1 — Analyse &amp; Maßnahmen</title>",
                    "<title>SmartCal — Status Mo→Fr + Detail je Testfall</title>")
html = re.sub(r'<title>.*?</title>', '<title>SmartCal — Status Mo 15.06 → Fr 19.06</title>', html, count=1)

# Alte „Gesamtübersicht — 16 Testfälle" (Montags-v4.1-Zahlen) am Ende entfernen —
# ersetzt durch die UI-getestete Übersicht oben (Abschnitt 1).
_gm = html.find('<div class="case" style="border-left: 4px solid #28a745;">')
if _gm != -1:
    _gend = _close_div(html, _gm)
    html = html[:_gm] + html[_gend:]
    print("Gesamtübersicht (alt) entfernt.")
else:
    print("WARN: alte Gesamtübersicht nicht gefunden.")

open(OUT, "w", encoding="utf-8").write(html)
n_pausch_bare = len(re.findall(r'(?<!S\. )\bPausch\b', html))
print("geschrieben:", OUT)
print("Cases mit Update:", sum(1 for c in UP if c in [m2 for m2 in UP]), "/ 16")
print("bare 'Pausch' (soll 0):", n_pausch_bare)
print("'S. Pausch' Vorkommen:", len(re.findall(r'S\. Pausch', html)))
