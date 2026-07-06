# UI-Test-Report — 16.06.2026 (nach Komplexitäts- + MA560-Fix)

**Stack:** FalkorDB (Docker, 6379) · Backend uvicorn :8000 (Graphen geladen: dguv_v3 **191 nodes**,
blitzschutz 73, rlt 56) · Frontend Next.js :3000 · Login `tuev`. Getestet über die **echte Chat-UI**
(LLM-Extraktion → Engine → Anzeige), nicht direkt über die Engine.

**Code-Stand:** Branch `v2-pricing` mit den 2 heutigen Commits (6cc0616 NetInform-Komplexität,
266c512 MA560-Reise). Reisekosten in der UI = **echtes OSRM-Routing** zum nächsten TÜV-Standort
(realistischer als der Mock im `test_testrunde1_all.py`-Skript → Reise-Werte weichen ab, Prüfkosten
sind identisch).

---

## 1 · UI-Ergebnisse (9 Fälle live durchgespielt)

| Fall | Typ / Prüfart | UI Gesamt | Grund | Prüf | Reise | Bericht | real € | Δ real | Verdikt |
|---|---|---|---|---|---|---|---|---|---|
| T01 Hipp | Industrie VdS, 20.000 m² | **10.415,87** | 678 | 7.975 | 1.213 | 550 | 6.850 | +52% | FAIL¹ |
| T02 REWE Eching | Verkaufsstätte, 800 m² | **1.502,60** | 330 | 570 | 223 | 380 | 657 | RV | RV-FLAG² |
| T03 badenova | Kleinauftrag, 1 Schaltschrank | **623,16** | 100 | 270 | 253 | 0 | 391 | +59% | über³ |
| **T04 Auto Service** | **MA560, 114 BM** | **1.283,00** | 0 | 1.283 | **0** | 0 | 1.217 | **+5%** | **PASS ✅geändert** |
| T08 Apleona | Büro DGUV+VdS, 26.000 m² | **8.037,86** | 796 | 6.134 | 558 | 550 | 7.932 | +1% | PASS |
| **T10 Max Planck** | **MA560, 545 BM** | **5.377,50** | 0 | 5.378 | **0** | 0 | 5.341 | **+1%** | **PASS ✅geändert** |
| **T12 Helios** | **Krankenhaus DGUV+VdS, 18.000 m²** | **12.778,68** | 639 | **11.391** | 199 | 550 | 13.110 | **−3%** | **PASS ✅geändert** |
| T14 roMEd | Krankenhaus, 8.000 m² | **4.382,58** | 443 | 2.580 | 810 | 550 | 5.136⁴ | −15% | PASS |
| T15 Würzburg | Büro DGUV, 5.000 m² | **4.706,85** | 384 | 3.854 | 89 | 380 | 4.195 | +12% | PASS |

¹ T01: Kat 2 vs Kat 3-Frage (CLAUDE.md §5) — offen für 20.06.
² T02/T11: Rahmenvertrag-Flatpreis, LPV korrekt darüber → RV-FLAG = managed.
³ T03: Prüf+Grund (370) ≈ real (391); Überschätzung = **nur Reise 253 €** (echter Standort Offenburg→Freiburg).
   In der UI sogar deutlicher über als im Skript (Mock-Reise 122 €) → Kleinauftrag-Reise = Fr-Thema #3.
⁴ T14: real 3.470 € (2012) inflationsbereinigt ~5.136 €.

**Nicht über UI gefahren (per Engine/Skript abgedeckt):** T05 Landwirt (xfail, Ref defekt),
T06 Maritim (xfail, MA510 OOS), T09 Weber-Gymnasium (xfail, Multi-MVP), T11 REWE München (RV,
analog T02), T13 Motel One (RV, Hotel <Schwelle), T16 Polizei Dachau (Blitzschutz-Produkt).

---

## 2 · Verifikation der heutigen Änderungen — UI bestätigt Engine

| Fall | Mechanismus | UI-Beleg |
|---|---|---|
| **T12** | Komplexitätsfaktor Krankenhaus 1,25 → **2,0** (NetInform), >10.000 m² | Prüf **11.390,59 €** (= Engine), Gesamt −3% → **PASS** |
| **T04** | MA560 Reise **inklusive** (all-inclusive) | Reise-Zeile **0,00 €**, Gesamt +5% → **PASS** |
| **T10** | MA560 Reise inklusive | Reise-Zeile **0,00 €**, Gesamt +1% → **PASS** |
| **T08** | Büro = Faktor **1,0** trotz 26.000 m² (>Schwelle) | Prüf 6.134 € **unverändert** → kein Über-Aufschlag, **kein Regress** |
| **T14** | Krankenhaus 8.000 m² **< Schwelle** → Faktor **nicht** angewandt | Prüf 2.580 € unverändert → **kein Regress** |

→ Beide Fixes wirken end-to-end durch die echte Chat-UI; die Schutz-Mechanik (Schwelle + Büro 1,0)
verhindert Kollateral-Überschätzung wie geplant.

---

## 3 · Änderungen ggü. vorheriger Version (deterministisch, Engine-Skript)

`MANAGED 8/12 → 10/12 (67% → 83%)` · PASS 4 → 6.

| Fall | vorher (Skript) | nachher (Skript) | Δ |
|---|---|---|---|
| T12 Helios | 8.558 € · −35% **MARGINAL** | 12.829 € · −2% **PASS** | Komplexität Krankenhaus 2,0 |
| T04 Auto Service | 1.565 € · +29% **MARGINAL** | 1.283 € · +5% **PASS** | MA560 Reise=0 (Regress behoben) |
| T10 Max Planck | 5.991 € · +12% PASS | 5.378 € · +1% PASS | MA560 Reise=0 (genauer) |
| alle übrigen | — | unverändert | kein Regress |

pytest: keine neuen Failures (513 passed). 7 Baseline-Failures bleiben (3× API-401 Auth/Server,
2× Graph-Env lokal, 2× Kat-Rate = bekannter Kat-7-Bug §5 → Fr).

---

## 4 · In der UI gefundene Fehler (To-Do #13)

### ✅ BUG-1 — BEHOBEN 16.06. (Commit 1810d56) — Blitzschutz-Labels im DGUV-Ergebnis
`app/page.tsx` rendert **alle** Produkte über `BlitzschutzAngebotPanel` (importiert nur dieses;
`KalkulationPanel.tsx` existiert, ist aber **nirgends eingebunden** = toter Code). Die Zeilen-
Beschreibungen sind hart als Blitzschutz codiert. Beim **DGUV-/Krankenhaus**-Ergebnis steht daher in
der Prüfkosten-Zeile wörtlich **„LPV B04 §8.1 · 33€/Messstelle + Staffeln"** — eine Blitzschutz-Formel.
Die **Beträge sind korrekt** (vom Backend), nur die Texte falsch.
**Behoben:** Zeilen-Labels jetzt produktabhängig via `angebot.gewerk` (`BlitzschutzAngebotPanel.tsx`).
DGUV zeigt nun „LPV B04 Kap. 2 · 250€ + Fläche×Kategorie (degressiv) + Verteilungen"; Blitzschutz
unverändert. In der UI verifiziert (Beträge unverändert). Screenshot: `ui-fix-dguv-labels.png`.
Offen bleibt: `KalkulationPanel.tsx` ist weiterhin toter Code — könnte später für eine echte
DGUV-spezifische Ansicht eingebunden werden (nicht demo-kritisch).

### 🟡 BUG-2 (kosmetisch) — favicon 404
`GET /favicon.ico → 404` in der Konsole. Harmlos, aber im Dev-Tools sichtbar.

### ✅ Kein Fehler — Reise-Abweichung UI vs. Skript
UI nutzt echtes OSRM-Routing zum nächsten Standort (z.B. T14 Reise 810 € vs. Skript-Mock 282 €).
Das ist realistischer, kein Bug. Prüfkosten stimmen exakt überein.

---

## 5 · Fazit & nächste Schritte
- **Beide heutigen Pricing-Fixes in der echten UI bestätigt** — T12/T04/T10 nun PASS, keine Regressionen.
- **BUG-1 sollte vor der AL-Tagung gefixt werden** (To-Do #13, Owner Piotr) — reine Frontend-Darstellung.
- Offen/Fr-20.06: T01 Kat-Frage, T03 Kleinauftrag-Reise, Kat-7-Rate (alle dokumentiert, nicht blind kalibriert).
- Screenshot T12 (Beleg): `ui-test-T12-helios.png`.
