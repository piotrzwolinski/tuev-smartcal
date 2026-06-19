#!/usr/bin/env python3
"""Testrunde-Validierung über das LIVE-UI (Chat) — kanonischer Testpfad.

Statt strukturierter Merkmale (test_testrunde1_all.py) geht jeder Fall als
natürlichsprachiger Chat-Prompt durch die ECHTE Pipeline: LLM-Extraktion (Haiku)
→ Geocoding → Engine. Das ist der Pfad, den Tester/Kunden sehen — und der z.B.
die Geocoding-Genauigkeit (T03 Lahr ~49 km) ehrlich abbildet, die der Skript-
Fixture (hardcoded coords) verfehlt.

Lauf:
  ./venv/bin/python scripts/test_ui_cases.py            # alle 16, live Fly
  ./venv/bin/python scripts/test_ui_cases.py T02 T11    # nur ausgewählte
  BASE_URL=http://localhost:3001 ./venv/bin/python scripts/test_ui_cases.py

Env: UI_USER (tuev) · UI_PASS · BASE_URL (default Fly) · HEADED=1 (sichtbar)
Output: Konsolen-Tabelle + scripts/ui_results.json (für Report-Generator).

Hinweis: LLM-Extraktion ist nicht-deterministisch — Nutzungstyp/Kategorie können
zwischen Läufen variieren (vgl. T08 „Industrie" vs „Büro"). Prompts daher
gebäudetyp-eindeutig halten. pytest-Unit-Guards (Engine-Interna, z.B. Kat-7-
Monotonie) bleiben separat — die lassen sich nicht über den Chat prüfen.
"""
import json
import os
import re
import sys

from playwright.sync_api import sync_playwright

BASE_URL = os.getenv("BASE_URL", "https://tuev-smartcal-web.fly.dev")
UI_USER = os.getenv("UI_USER", "tuev")
UI_PASS = os.getenv("UI_PASS", "TuevSmartcal2026##!")
HEADED = os.getenv("HEADED") == "1"

# (id, prompt, real_price|None, produkt, kind, note)
# kind: "" normal · "xfail" Referenz defekt/OOS · "noref" · "rv" RV-Listenpreis
CASES = [
 ("T01","VdS-Prüfung für ein Nahrungsmittelwerk in Pfaffenhofen, PLZ 85276, 20.000 m², 45 Unterverteilungen, 8.000 kVA", 6850, "dguv","", "MA505 VdS"),
 ("T02","DGUV V3 Prüfung für einen REWE-Markt in Eching, PLZ 85386, ca. 2500 m² Verkaufsfläche, Kühltheke", 848, "dguv","", "REWE-Liste 2001-5000m² (S. Pausch 17.06)"),
 ("T03","Material 501, 1 Schaltschrank in 77933", 391, "dguv","", "Kleinauftrag · Reise dominiert (Lahr ~49 km)"),
 ("T04","114 Betriebsmittel, Auto Service in Calw, PLZ 75365", 1217, "dguv","", "MA560"),
 ("T05","23 ortsveränderliche Betriebsmittel, Landwirtschaftlicher Betrieb, PLZ 93444", 175, "dguv","xfail", "Ref defekt (S. Pausch)"),
 ("T06","Elektrische Anlage nach Baurecht, Wiederkehrend, Maritim-Hotel, 5 Konferenzräume, Gastronomiebereich, 40 Unterverteilungen, 100 Zimmer, PLZ 32105", 220, "dguv","xfail", "Ref defekt + MA510 OOS"),
 ("T07","VdS 2871 Prüfung, Metallverarbeitung König & Bauer in Radebeul, PLZ 01445, 48 UV, 4 Gebäude, 80% Produktion 20% Verwaltung, 900m²", None, "dguv","noref", "kein Real"),
 ("T08","DGUV V3 + VdS Kombiprüfung, Bürogebäude Apleona Gilching PLZ 82205, 26000 m², 37 Unterverteilungen", 7932, "dguv","", "Kombi (Apleona = Büro/FM)"),
 ("T09","DGUV V3 Prüfung, Adolf-Weber-Gymnasium München, Schule, ca. 5000 m², PLZ 80636", 4800, "dguv","xfail", "Multi=MVP (nur ELT)"),
 ("T10","545 ortsveränderliche Betriebsmittel, Rechenzentrum Max Planck Garching, PLZ 85748", 5341, "dguv","", "MA560"),
 ("T11","DGUV V3 Prüfung, REWE-Markt München, ca. 2500 m², PLZ 81375", 848, "dguv","", "REWE-Liste (wie T02)"),
 ("T12","DGUV V3 + VdS Kombiprüfung, Helios Klinik Pasing, Krankenhaus mit OP und Intensivstation, 18.000 m², PLZ 81249", 13110, "dguv","", "Kombi · real = 54h×239€ Aufwand"),
 ("T13","DGUV V3 Prüfung, Motel One München Deutsches Museum, Hotel, ca. 200 Zimmer, PLZ 80331", 621, "dguv","xfail", "Ref defekt (S. Pausch prüft, Motel-One-Liste)"),
 ("T14","DGUV V3 Prüfung, Krankenhaus roMEd Klinik Prien am Chiemsee, ca. 8000 m², PLZ 83209", 5136, "dguv","", "inflationsbereinigt (2012→2026)"),
 ("T15","DGUV V3 Prüfung, Bürogebäude in Würzburg, ca. 5000 m², PLZ 97080", 4195, "dguv","", "Büro"),
 ("T16","Blitzschutzprüfung, Polizeiinspektion Dachau, PLZ 85221, 12 Ableitungen", 205, "blitz","rv", "RV, Blitz-Produkt"),
]

PROD_LABEL = {"dguv": "DGUV V3", "blitz": "Blitzschutz"}


def _verdict(real, total, kind):
    if kind == "noref" or real is None:
        return "NO-REF", None
    if kind == "xfail":
        d = (total - real) / real if (real and total) else None
        return "xfail", d
    d = (total - real) / real
    if kind == "rv":
        return "RV-FLAG", d
    a = abs(d)
    return ("PASS" if a <= 0.20 else "MARGINAL" if a <= 0.35 else "FAIL"), d


_EXTRACT = """() => {
  const t = [...document.querySelectorAll('table')].find(t => /Gesamt/.test(t.innerText));
  if (!t) return null;
  const num = s => { const m = (s||'').replace(/\\./g,'').replace(',', '.').match(/[\\d.]+/); return m ? parseFloat(m[0]) : null; };
  const out = {};
  for (const tr of t.querySelectorAll('tr')) {
    const c = [...tr.children].map(x => x.innerText.trim());
    if (c.length < 2) continue;
    const pos = c[0].toLowerCase(), val = num(c[c.length-1]);
    if (pos.startsWith('grund')) out.grund = val;
    else if (pos.startsWith('prüf') || pos.startsWith('pruef')) out.pruef = val;
    else if (pos.startsWith('reise')) out.reise = val;
    else if (pos.startsWith('bericht')) out.bericht = val;
    else if (pos.startsWith('gesamt')) out.total = val;
  }
  return out;
}"""


def run(selected):
    cases = [c for c in CASES if not selected or c[0] in selected]
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not HEADED)
        page = browser.new_page()
        page.set_default_timeout(60000)
        page.goto(BASE_URL)
        # Login
        page.fill('input[type="text"]', UI_USER)
        page.fill('input[type="password"]', UI_PASS)
        page.get_by_role("button", name=re.compile("Anmelden")).click()
        page.wait_for_selector("textarea", timeout=20000)

        cur_prod = None
        for cid, prompt, real, prod, kind, note in cases:
            if prod != cur_prod:
                page.get_by_role("button", name=re.compile(PROD_LABEL[prod])).first.click()
                page.wait_for_timeout(800)
                cur_prod = prod
            # Neue Anfrage (reset)
            nr = page.get_by_role("button", name=re.compile("Neue Anfrage"))
            if nr.count():
                nr.first.click(); page.wait_for_timeout(400)
            page.fill("textarea", prompt)
            page.locator("textarea").press("Enter")
            data, err = None, ""
            try:
                page.wait_for_function("() => [...document.querySelectorAll('table')].some(t => /Gesamtbetrag|Gesamt \\(netto\\)|Gesamtbetrag \\(netto\\)/.test(t.innerText))", timeout=55000)
                data = page.evaluate(_EXTRACT)
            except Exception as e:
                err = "kein Ergebnis (Follow-up-Frage?)"
            total = (data or {}).get("total")
            verdict, d = _verdict(real, total, kind) if total else ("ERR", None)
            if err:
                verdict = "ERR"
            row = {"id": cid, "real": real, "total": total, "delta": d,
                   "verdict": verdict, "kind": kind, "note": note,
                   "breakdown": data or {}, "error": err}
            results.append(row)
            ds = f"{d*100:+.0f}%" if d is not None else "—"
            ts = f"{total:,.0f}" if total else (err or "—")
            print(f"{cid:<4} real {str(real or '—'):>7}  UI {ts:>9}  {ds:>6}  {verdict:<9} {note}")
        browser.close()
    return results


def main():
    selected = [a.upper() for a in sys.argv[1:]]
    print(f"=== UI-Testrunde @ {BASE_URL} ({'gewählt: '+','.join(selected) if selected else 'alle 16'}) ===")
    print(f"{'ID':<4} {'Real':>12} {'UI €':>11} {'Δ':>6}  Verdict   Note")
    print("-" * 96)
    results = run(selected)
    # Summary
    cnt = {}
    for r in results:
        cnt[r["verdict"]] = cnt.get(r["verdict"], 0) + 1
    print("-" * 96)
    print("  ".join(f"{k}:{v}" for k, v in sorted(cnt.items())))
    pas = cnt.get("PASS", 0); rv = cnt.get("RV-FLAG", 0)
    testable = sum(cnt.get(k, 0) for k in ("PASS", "MARGINAL", "FAIL", "RV-FLAG"))
    if testable:
        print(f"MANAGED (PASS+RV): {pas+rv}/{testable} ({(pas+rv)/testable*100:.0f}%)")
    out = os.path.join(os.path.dirname(__file__), "ui_results.json")
    json.dump(results, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"→ {out}")


if __name__ == "__main__":
    main()
