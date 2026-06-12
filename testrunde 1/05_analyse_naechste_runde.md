# Testrunde 1 — Komplette Fall-Analyse + Plan für Testrunde 2

## Tabelle 1: DOCX — „Teste SmartCal.docx" (Pausch, 4 Cases)

| # | Objekt | MA | SmartCal → Real | Δ | Verdict | Root Cause |
|---|--------|-----|----------------|---|---------|------------|
| DOC-1 | Motel One München (EQ 2452914) | 501-WP | 5.161,31 € → 621 € (RV 2023) | +731% | FAIL „utopisch" | D5 Overhead-Stack (Grund 671 + Bericht 550) · F2 Real = RV-Preis (-46–85% unter LPV) · D11 Label „33€/Messstelle" in DGUV |
| DOC-2 | roMEd Klinik Prien (EQ 2050531) | 501-WP | 4.322,76 € → 3.470 € (2012!) | +25% nom., ~0% infl. | **PASS** „Sieht gut aus" | Sweet Spot des linearen Modells: Standardobjekt mittlerer Größe |
| DOC-3 | DGUV Würzburg (EQ 3186952) | 507-WP | 3.282,37 € → 4.195,25 € (2022) | -22% nom., -35% infl. | MARGINAL/FAIL | D12 Unterpricing komplexer Objekte · Reise = 998 € (30% des Preises!) · fehlende Merkmale → Defaults |
| DOC-4 | Bereitschaftspolizei Dachau, Blitz 12 MS | 574-WP | 1.536,66 € → 205 € | +650% | FAIL „utopisch" | D5: Grundkosten 572 € (inkl. **Ordnung 242 € — baurechtlich fälschlich aktiv!**) + Bericht 380 € > gesamte Real-Faktura · Real = RV/minimal |

## Tabelle 2: PPTX — Screenshots (Weiß, 5 Cases)

| # | Objekt | MA | SmartCal → Real | Δ | Verdict | Root Cause |
|---|--------|-----|----------------|---|---------|------------|
| PPT-1 | Apleona Gilching, 26.000 m², 37 UV | 505+507 | 10.370 € → nach Rückfragen 23.982 € → Real 7.932 € | +31% → +202% | FAIL | D1 keine Degression · D2 VdS-Stub · D3 DGUV+VdS doppelt · ⚠ **je mehr Daten, desto schlechter** — jede Antwort addierte linear |
| PPT-2 | Adolf-Weber-Gymnasium (BMA+SiBel+ELT) | 583+511+510 | 2.834 € → Real 4.800 € (Bundle 20h×239€) | -41% | FAIL | F1 Multi-Produkt nicht unterstützt — System rechnete nur ELT; BMA/SiBel nie im PoC-Scope |
| PPT-3 | Max Planck RZ Garching, 545 BM | 560-WP | 1.048 € → 2.084 € → Real 5.341 € (545×9,80€) | -61% | FAIL | D4 kein per-Device · S1 Chat fragte nach m² trotz BM-Anzahl |
| PPT-4 | REWE München Würmtalstr., ~1.600 m² | 507-WP | 1.738,54 € → Real 657,26 € (SAP) | +164% | FAIL | F2: REWE zahlt **flat ~657 €/Markt** (Filialnetz-RV, identische Summe wie ZIP-2!) |
| PPT-5 | Helios Klinik Pasing | 505+507 | 10.840 € → Real ~13.110 € (54h×239€) | -17% | MARGINAL | D7 Kat 2 statt 7 (Krankenhaus!) · D2 VdS-Stub · F4 Real aufwandsbasiert |

## Tabelle 3: ZIP — Pausch-Test (XLSX + 7 PDFs, 7 Cases)

| # | Objekt | MA | SmartCal → Real | Δ | Verdict | Root Cause |
|---|--------|-----|----------------|---|---------|------------|
| ZIP-1 | Hipp Pfaffenhofen, 20.000 m², 45 UV, 8.000 kVA | 505 VdS | 11.877 € → 6.850 € | +73% | FAIL | D1: Fläche linear = 10.000 € (mit Degression ~4.200 €) · D2 VdS-Stub · Pausch: „VdS kommt fast hin" |
| ZIP-2 | REWE Eching/Kiefersfelden, 800 m² | 507 | 2.125,28 € → 657,26 € | +223% | FAIL | F2 flat RV (gleiche Summe wie PPT-4!) · D5 · Pausch: „Abrechnung ggf. zu gering" |
| ZIP-3 | badenova, 1 Schaltschrank, 77933 | 501 | 1.051,06 € → 391 € | +169% | FAIL | D5 keine Stunden-Pfad (Real ≈ 2h×180€) · S1 Mitarbeiter-Frage („sinnfrei") · D8 PLZ→„Bad Kissingen" |
| ZIP-4 | TÜV Auto Service Calw, 114 BM | 560 | 1.198,33 € → 1.216,95 € | **-1,5%** | **PASS** „Passt!" | Zufall: m²-Ansatz traf; per-Device gäbe 114×9,8+200 ≈ 1.317 (+8%) — auch PASS, aber **aus richtigem Grund** |
| ZIP-5 | Landwirt Neukirchen, 23 BM | 560 | 1.400 € → 174,80 € | +701%* | INKONKL. | D13 „Abrechnung fehlerhaft" · unabhängig: per-Device gäbe ~425 € |
| ZIP-6 | Maritim Hotel Königswinter, 40 UV, 3 Prüftage | 510-WP | 4.063,50 € → 220 € | +1.747%* | INKONKL. | D13: 220 € für 3-Tage-Baurecht mit 46 Mängeln unmöglich (realer Aufwand ≈ 5,7k!) — **unser Wert evtl. näher an der Wahrheit als die Referenz** · MA510 außerhalb Scope |
| ZIP-7 | König & Bauer Radebeul, 48 UV, 4 Gebäude, 16.800 kVA | 505 | — | — | NICHT GETESTET | Kandidat #1 für Runde 2 (Befundschein 32 S. liegt vor) |

## Tabelle 4: Nur im Call berichtet (8 Meldungen)

| # | Meldung | Wer | Verdict | Root Cause |
|---|---------|-----|---------|------------|
| C-1 | Kindergarten Waiblingen, 20 BM → System **lehnte ab** („andere Fachleute") | Weiß | FAIL | S2/D4: Prompt = nur ortsfest; Ablehnung = Haiku-Improvisation, nichtdeterministisch |
| C-2 | Große DGUV: System 14-15k, Angebot 39k | Weiß | FAIL | D12: UV à 25 €, Kat max 6, kein Aufwands-Pfad |
| C-3 | Baurecht: 15.000 € „mehr als das Doppelte" | Pfilf | FAIL | MA510 außerhalb Scope + D1/D5 |
| C-4 | Motel One ortsveränderlich → fragte nach Zimmeranzahl | Pfilf | UX | S1: Zimmer×30→m² einziger bekannter Pfad |
| C-5 | Supermarkt: Referenz 545 € gegeben, System blieb bei 1.900 € (Real 650 €) | Steinwidder | FAIL | D6: Referenzpreis rein dekorativ — kein Einfluss auf Preis |
| C-6 | Trafostation → Schleife zu m² | Steinwidder | UX | S1: Kat 6 (Trafo) existiert im Enum, ohne m² nicht nutzbar |
| C-7 | 12 Werke multi-site, per-Werk-Preise | Weiß | **POSITIV** | „sauber aufgelistet… mit der Differenz habe ich leben können" |
| C-8 | Grundschule 93345: Reisekosten 0 € | Pausch | FIXED | D9: behoben (Commits 4661047→5a0ea2b) am Testmorgen |

## 5 Muster erklären 14 von 16 Fällen

1. **Preiskompression durch lineares Modell** (D1+D5+D12): kleine/einfache überteuert (+169 bis +731%), große/komplexe unterpreist (-17 bis -63%). Real: 175 €–39.000 €; wir: fast alles in 1.000–15.000 €.
2. **VdS existiert nicht** (D2+D3): Stub + kein Routing → gesamter Veit-MUST-Scope falsch (ZIP-1, PPT-1, PPT-5).
3. **Kein per-Device** (D4+S1+S2): MA560 hat weder Produkt noch Feld noch Formel → 3 Cases, davon der einzige PASS aus Zufall.
4. **Real ≠ LPV** (F2): Motel One, 2×REWE, Polizei — Referenzen sind RV/Filialnetz-Preise 30–85% unter LPV. **Kein Modell-Fix behebt das** — es ist ein Vergleichsproblem.
5. **Schmutzige Referenzen** (D13): 2 Cases (Landwirt 175 €, Maritim 220 €) unmessbar — 12% der Runde verbrannt.

**Prozess-Erkenntnis aus PPT-1**: Verfeinerung verschlechterte das Ergebnis (10,4k → 24k bei Real 7,9k). Jede User-Antwort addierte lineare Posten ohne Degression — Umkehrung des Produktversprechens „mehr Daten = besserer Preis". Gefährlichster Effekt fürs Tester-Vertrauen.

## Plan für Testrunde 2

### A. Code-Fixes → Case-Mapping

| Fix | Repariert | Erwartung nach Fix |
|-----|-----------|--------------------|
| 1. Degression DGUV+VdS | ZIP-1, PPT-1, PPT-5, C-2 | ZIP-1: ~7,3k vs 6,85k → PASS · PPT-1: ~8-11k (mixabhängig) → PASS/MARGINAL |
| 2. VdS eigene Logik (208 €, VdS-Kurve) | ZIP-1, PPT-1, PPT-5 | verstärkt Fix 1 |
| 3. VdS-Only Routing | PPT-1, Weiß-VdS (8.174 €) | Ende der Doppelzählung |
| 4. Kat 7+8 | PPT-5, DOC-3 | Helios: -17% → ~PASS |
| 5. MA560 per-Device (9,80 €/BM + Overhead) | PPT-3, ZIP-4, ZIP-5, C-1 | Max Planck: 5.541 vs 5.341 → +3,7% PASS · keine Ablehnungen mehr |
| 6. Small-Job-Pfad (Stunden × Satz) | ZIP-3, DOC-4, DOC-1 teilw. | Schaltschrank: ~450-550 vs 391 → PASS/MARGINAL |
| 7. Referenzpreis-Blend | C-5, ZIP-2 | Referenz zieht Preis real + Trace-Eintrag |
| Bonus: `baurechtlich`-Flag-Fix | DOC-4 | Ordnung 242 € nicht bei normalem Blitz-WP |

### B. Scope-Guards im Produkt

- MA510 Baurecht / Multi-Produkt → ehrliche Meldung „kommt im MVP — grobe Orientierung" statt falscher Präzision
- **RV-Frage im Chat**: „Besteht ein Rahmenvertrag?" → Warnung „Kalkulation = LPV-Niveau; RV-Konditionen typisch 30-60% darunter". Neutralisiert 4 „utopisch"-FAILs (DOC-1, ZIP-2, PPT-4, DOC-4) ohne Rabatt-Modellierung.

### C. Prozess Testrunde 2

1. **Referenzen VOR der Runde validiert** — Pausch bestätigt: volle Faktura oder Teilrechnung? RV oder LPV? (eliminiert D13)
2. **PASS-Kriterium vorab vereinbart** — Vorschlag ±15% vs inflationsbereinigte Referenz (Call mit Pausch, Action Item „Erfolgskriterien")
3. **Test-Template** = Pauschs XLSX als Standard für alle Tester (EQ, MA, Inputs, SmartCal, Real, Quelle, RV j/n, Kommentar)
4. **Scope-Karte für Tester**: im PoC (507, 505, 560, 570) vs außerhalb (510, Multi, BMA) — Out-of-Scope-FAILs zählen nicht zur Pass-Rate
5. **Interne Regression vor der Runde**: alle 16 Cases als Golden Tests nach jedem Fix
6. **Smoke-Test 48h vorher** (Runde 1: Reisekosten=0 erst um 8:00 am Testtag gefunden)
7. **EFI-Review der Kurven** (Bachmeier/Römerkamp) vor Präsentation der Degression + per-Device-Sätze
8. **ZIP-7 (König & Bauer) als Eröffnungs-Case** — voller Befundschein vorhanden, nie getestet, ideal für „VdS ist repariert"

### D. Pass-Rate-Projektion

| | Runde 1 | Nach Fixes A+B (Schätzung) |
|---|---------|---------------------------|
| PASS | 2/14 (14%) | 6-8/14 (43-57%) |
| Managed (Scope-Guard/RV-Flag statt FAIL) | 0 | +3-4 |
| Unmessbar (schlechte Referenzen) | 2 | 0 (nach Datenvalidierung) |
