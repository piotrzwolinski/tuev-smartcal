# SmartCal@EG — Arbeitsregeln für Claude Code

PoC: Preiskalkulation für TÜV SÜD Elektroprüfungen (DGUV V3 / VdS / ortsveränderlich /
Blitzschutz). FastAPI + FalkorDB + Claude Haiku, Next.js Frontend, Deploy auf Fly.io.
**Aktiver Stand: v4.1 — 9/12 managed (Branch `v2-pricing`).**

---

## 1. Wissen zuerst — der Graph ist die Karte

Es existiert ein Knowledge Graph über Code + Calls + Testfälle + Pricing-Regeln in
`graphify-out/`. **Vor breiter Code-Suche zuerst den Graphen fragen** — er kennt die
Verbindungen, die `grep` nicht sieht (Regel → abhängige Testfälle → Entscheidung aus Call).

```bash
graphify query "Was treibt Testfall T12 Helios?"     # BFS über Verbindungen
graphify path "Degression" "T08 Apleona"             # kürzester Pfad zwischen Konzepten
graphify explain "Komplexitätsfaktor 1.25"           # Knoten + Nachbarn erklären
graphify affected "flaechenkosten_degressiv"         # was bricht, wenn ich das ändere
```

Rohe Code-Dateien erst lesen, wenn der Graph die Antwort nicht hat oder beim Editieren.
Graph aktualisieren: Code → automatisch per post-commit Hook; Docs/Memory →
`/graphify --update` manuell.

## 2. PFLICHT vor jeder Änderung an einer Pricing-Regel

Genau das war die Ursache des Im-Kreis-Drehens: eine Regel für T15 anfassen und
unbemerkt T08/T12 zerschießen.

1. `graphify affected "<funktion>"` ODER `graphify explain "<regel>"` ausführen
2. Die abhängigen **Testfälle in der Antwort/dem Plan benennen**, bevor editiert wird
3. Erst dann ändern.

## 3. Egzekucja — bricht die Schleife (der Graph allein tut es nicht)

- **Eine Änderung pro Schritt.** Nicht drei Fixes bündeln — sonst ist hinterher
  unklar, welcher die Regression verursacht hat.
- **Kein „fertig" ohne grünen vollen Lauf.** Vor jeder „erledigt"-Aussage:
  ```bash
  cd backend && ./venv/bin/python -m pytest tests/ -q \
    --ignore=tests/test_e2e_llm_judge.py        # hängt (Live-LLM, kein Timeout)
  ./venv/bin/python scripts/test_testrunde1_all.py   # die 16 Testrunde-Fälle
  ```
  Ergebnis (Zahlen) in die Antwort einfügen. Nicht „sollte passen" — den Lauf zeigen.
- **Bug-Workflow:** zuerst ein Test der den Bug fängt, dann der Fix, dann ein Eintrag
  unter „Bekannte Bugs / Bug-Ledger" hier.
- **FalkorDB-Graph nach Schema-Änderung neu laden** (sonst Prüfkosten=0):
  `load_dguv_graph()` lokal / `graph_load` Endpoint nach Deploy.

## 4. Deploy

```bash
git push origin v2-pricing
cd backend && fly deploy --remote-only         # tuev-smartcal-api
curl -s -o /dev/null -w "%{http_code}" https://tuev-smartcal-api.fly.dev/api/health   # 401 = up (Auth aktiv)
fly logs --no-tail | grep "dguv_v3"            # prüfen dass Graph geladen (191 nodes)
```

## 5. Bekannte Bugs / offene Fragen (bei Extraction 12.06 gefunden)

- **`engine/graph_pricing_engine.py` `_calc_dguv_addons` (~Z.443):** referenziert
  undefinierte Variable `cost` → `NameError` wenn `vds_pruefung=True` mit
  `pruefart=DGUV_ORTSFEST`. **Latenter Bug — verifizieren & Test schreiben.**
- **Kat-7-Rate widersprüchlich:** Graph sagt 5,42 €/10m², Konstante im Code 8,00.
  Graph gewinnt zur Laufzeit. Mit Pausch klären welcher Wert stimmt.
- **Kat-Nummerierung:** `dguv_v3/extraction_prompt.txt` (1=Büro, 2=Produktion) ≠
  Code `merkmale.py` (1=Wohnung, 2=Büro). Prüfen ob Extraction-Daten falsch gelabelt.
- **`test_e2e_llm_judge.py` hängt** (~40 min, Live-LLM ohne Timeout) — daher oben ignored.
- **T01 Hipp Kat 2 (+17% PASS) vs Kat 3 (+53% FAIL):** Lebensmittelproduktion =
  welche Kategorie? Mit Pausch klären; bei Kat 3 VdS-Kurve für Großindustrie rekalibrieren.

## 6. Memory & Quellen

Persistentes Projektgedächtnis (Calls, Entscheidungen, Stakeholder):
`~/.claude/projects/-Users-piotrzwolinski-projects-tuev/memory/MEMORY.md`.
Bindender aktueller Plan: `testrunde 1/09_plan_v3_piątek.md`.
Rohe Transkripte/Mails gehören nach `sources/` (anlegen) — nicht nur im Chat-Verlauf.
