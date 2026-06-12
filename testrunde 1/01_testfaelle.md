# Testrunde 1 — Alle Testfälle

## Ergebnisübersicht

**Pass-Rate: 2 von 16 (12.5%)**

| Status | Anzahl | Kriterium |
|--------|--------|-----------|
| PASS | 2 | Delta ≤ ±15% |
| MARGINAL | 2 | Delta ±15–35% |
| FAIL | 10 | Delta > ±35% oder "utopisch" |
| INKONKLUSIV | 1 | Referenzpreis offensichtlich fehlerhaft |
| NICHT GETESTET | 1 | — |

---

## Testfälle im Detail

### T01 — Hipp Nahrungsmittel, VdS (Pausch)
- **Produkt**: MA505 VdS2871
- **Objekt**: Hipp-Werk, Georg-Hipp-Str. 7, 85276 Pfaffenhofen
- **Merkmale**: 8.000 kVA, 45 UV, 20.000 m²
- **SmartCal**: 11.877 €
- **Real**: 6.850 €
- **Delta**: +73% → **FAIL**
- **Quelle**: Pausch XLSX Anlage 1, PDF EQ1550815
- **Anmerkung Pausch**: "Ggf. Prüfdienstleistung abweichend? VdS kommt fast hin"

### T02 — REWE Markt Eching, DGUV (Pausch)
- **Produkt**: MA507 DGUV
- **Objekt**: REWE-Markt, Gewerbepark 1, 83088 Kiefersfelden (Auftraggeber 85386 Eching)
- **Merkmale**: Kühltheke, 800 m² Verkaufsfläche (Annahme)
- **SmartCal**: 2.125,28 €
- **Real**: 657,26 €
- **Delta**: +223% → **FAIL**
- **Quelle**: Pausch XLSX Anlage 2, PDF EQ2828424, Weiß PPTX Slide 16-19
- **Anmerkung Pausch**: "Abrechnung ggf. zu gering"

### T03 — badenovaNETZE 1 Schaltschrank, DGUV (Pausch)
- **Produkt**: MA501 el. Anlage
- **Objekt**: KO Huwe Anl 192, Zwischen den Wegen, 77933 Lahr-Hugsweier
- **Merkmale**: 1 Schaltschrank (KKS-Fremdstrom Speisegerät)
- **SmartCal**: 1.051,06 €
- **Real**: 391 €
- **Delta**: +169% → **FAIL**
- **Quelle**: Pausch XLSX Anlage 3, PDF EQ3316380
- **Anmerkung Pausch**: "Abfrage führt zu zu hohen Preisen?"
- **Zusätzliche Anmerkungen**:
  - "PLZ passt nicht zu angezeigtem Ort, NL passt wiederum"
  - "Anfrage nach Mitarbeiter sinnfrei, da exakt 1 Schaltschrank beschrieben"

### T04 — TÜV Auto Service Calw, MA560 (Pausch) ✓
- **Produkt**: MA560 el. Betriebsmittel
- **Objekt**: TÜV SÜD Auto Service GmbH, Rudolf-Diesel-Str. 3, 75365 Calw
- **Merkmale**: 114 Betriebsmittel, Auto Service, ~300 m² (Annahme)
- **SmartCal**: 1.198,33 €
- **Real**: 1.216,95 €
- **Delta**: -1,5% → **PASS**
- **Quelle**: Pausch XLSX Anlage 4, PDF EQ2597657

### T05 — Landwirt 23 BM, MA560 (Pausch)
- **Produkt**: MA560 el. Betriebsmittel
- **Objekt**: Rank Silke, Boehmerwaldstr., 93453 Neukirchen b. hl. Blut
- **Merkmale**: 23 Betriebsmittel, Landwirtschaftl. Betrieb, 1 Gebäude, 150 m²
- **SmartCal**: 1.400 €
- **Real**: 174,80 €
- **Delta**: +701% → **FAIL***
- **Quelle**: Pausch XLSX Anlage 5, PDF EQ3578607
- **Anmerkung Pausch**: "Abrechnung fehlerhaft"
- *Referenzpreis möglicherweise nicht marktgerecht (174€ für 23 BM mit 2 Mängeln)*

### T06 — Maritim Hotel Königswinter, MA510 (Pausch)
- **Produkt**: MA510 el. Anlage Baurecht
- **Objekt**: Maritim Hotel, Rheinallee 3, 53639 Königswinter
- **Merkmale**: 5 Konferenzräume, Gastrobereich, 40 UV, ~100 Zimmer, Beherbergungsstätte
- **SmartCal**: 4.063,50 €
- **Real**: 220 €
- **Delta**: +1.747% → **INKONKLUSIV***
- **Quelle**: Pausch XLSX Anlage 6, PDF EQ2909976 (10 Seiten, 46 Mängel!)
- **Anmerkung Pausch**: "Abrechnung fehlerhaft"
- *220€ ist für ein 10-seitiges Baurecht-Gutachten mit 46 Mängeln sicher falsch*

### T07 — König & Bauer Metallbetrieb, VdS (Pausch)
- **Produkt**: MA505 VdS2871
- **Objekt**: König & Bauer Industrial, Friedrich-List-Str. 47, 01445 Radebeul
- **Merkmale**: Metallverarbeitung, 48 UV, 4 Gebäude, 80/20 Produktion/Verw., 900 m²
- **SmartCal**: —
- **Real**: —
- **Quelle**: Pausch XLSX Anlage 7, PDF EQ3218668 (32 Seiten)
- **Status**: **NICHT GETESTET**

### T08 — Apleona Gilching, VdS+DGUV (Weiß)
- **Produkt**: VdS + DGUV kombiniert
- **Objekt**: Bau- und Kreativwerkstatt, Zeppelinstr. 16-18b, 82205 Gilching
- **Merkmale**: 26.000 m², 37 UV, Büro/Verwaltung + Produktion + Labor
- **SmartCal**: ~10.370 € → angepasst auf ~23.982 €
- **Real**: 7.932 € (Angebot Benjamin Bachmeir: 30h × 236€ + 3 Anfahrten)
- **Delta**: +31% (erste Berechnung) → **MARGINAL**
- **Quelle**: Weiß PPTX Slides 2-6, VdS-Fragebogen
- **Anmerkung**: Preis ging nach Nachfragen auf ~24k hoch — Overshoot nach oben

### T09 — Adolf-Weber-Gymnasium, Multi (Weiß)
- **Produkt**: BMA (583-PI) + SiBel (511-PI) + DGUV (510-PI)
- **Objekt**: Adolf-Weber-Gymnasium, Kapschstr. 4, 80636 München
- **Merkmale**: Erweiterungsbau Schule, BMA + Sicherheitsbeleuchtung + DGUV V3
- **SmartCal**: ~2.834 € (nur DGUV?) oder ~13.000 € (unklar)
- **Real**: 4.800 € (8h BMA + 4h SiBel + 8h ELT, je 239€)
- **Delta**: +171% (wenn 13k) oder -41% (wenn 2.8k) → **FAIL**
- **Quelle**: Weiß PPTX Slides 7-9, Outlook-Mail Angebot 20667221
- **Kernproblem**: System kann kein Multi-Produkt-Bundling

### T10 — Max Planck Rechenzentrum 545 BM, MA560 (Weiß/Steinwidder)
- **Produkt**: MA560 el. Betriebsmittel
- **Objekt**: Max Planck Computing and Data Facility, Gießenbachstr. 2, 85748 Garching
- **Merkmale**: 545 ortsveränderliche Betriebsmittel, Rechenzentrum
- **SmartCal**: ~2.084 €
- **Real**: 5.341 € (545 × 9,80 €/Stück)
- **Delta**: -63% → **FAIL**
- **Quelle**: Weiß PPTX Slides 11-15, Original-Rechnung
- **Kernproblem**: System nutzt m²-Logik statt per-Gerät-Rate

### T11 — REWE München, DGUV (Weiß)
- **Produkt**: MA507 DGUV
- **Objekt**: REWE-Markt, Würmtalstr. 117, 81375 München
- **Merkmale**: ~1.600 m² (Annahme)
- **SmartCal**: ~1.738 €
- **Real**: 657,26 € (SAP: 1 ST × 657,26€)
- **Delta**: +164% → **FAIL**
- **Quelle**: Weiß PPTX Slides 16-19, SAP-Screenshot

### T12 — Helios Kliniken, VdS+DGUV (Weiß)
- **Produkt**: VdS + DGUV kombiniert
- **Objekt**: Klinikgebäude Pasing
- **Merkmale**: Großes Klinikgebäude, DGUV + VdS kombiniert
- **SmartCal**: ~10.840 €
- **Real**: ~13.110 € (54h × 239€ + Reise)
- **Delta**: -17% → **MARGINAL** (knapp)
- **Quelle**: Weiß PPTX Slides 20-23, Vergütungsseite + SAP KA 0004300652

### T13 — Motel One München, MA501 (Docx)
- **Produkt**: MA501-WP el. Anlage
- **Objekt**: Motel One München, Deutsches Museum
- **Merkmale**: EQ 2452914
- **SmartCal**: 5.161,31 €
- **Real**: 621 € (RV 2023), 858 € (2013)
- **Delta**: +731% → **FAIL**
- **Quelle**: Pausch Docx, Test 1
- **Kommentar Pausch**: "Utopischer Preis."

### T14 — roMEd Klinik Prien, DGUV (Docx) ✓
- **Produkt**: MA501-WP el. Anlage
- **Objekt**: roMEd Klinik, 83209 Prien am Chiemsee
- **Merkmale**: EQ 2050531
- **SmartCal**: ~4.323 €
- **Real**: 3.470 €
- **Delta**: ~0% → **PASS**
- **Quelle**: Pausch Docx, Test 2
- **Kommentar Pausch**: "Sieht gut aus"

### T15 — DGUV Würzburg (Docx)
- **Produkt**: MA507 DGUV
- **Objekt**: EQ 3186952, Raum Würzburg
- **Merkmale**: Standort 80 km / 54 min von Würzburg
- **SmartCal**: 3.282,37 €
- **Real**: 4.195,25 €
- **Delta**: -22% → **MARGINAL**
- **Quelle**: Pausch Docx, Test 3
- **Kommentar Pausch**: "Liegt 1000 drunter. Man muss sehr viele Daten wissen. Aus dem Internet bekommt man die nicht."

### T16 — Polizei Dachau, Blitzschutz (Docx)
- **Produkt**: MA574 Blitzschutz
- **Objekt**: Bereitschaftspolizei, 85221 Dachau
- **Merkmale**: Messstellen bis 4: 4, über 4: 8, EQ 1795048
- **SmartCal**: 1.536,66 €
- **Real**: 205 €
- **Delta**: +649% → **FAIL**
- **Quelle**: Pausch Docx, Test 4
- **Kommentar Pausch**: "Utopisch"

---

## Zusammenfassung nach Produkt

| Produkt | Tests | Pass | Marginal | Fail |
|---------|-------|------|----------|------|
| MA507 DGUV | 3 | 0 | 1 | 2 |
| MA560 BM | 3 | 1 | 0 | 2 |
| MA501 el. Anlage | 3 | 1 | 0 | 2 |
| MA505 VdS | 2 | 0 | 0 | 1+1 n.t. |
| VdS+DGUV kombi | 2 | 0 | 2 | 0 |
| MA510 Baurecht | 1 | 0 | 0 | 0+1 ink. |
| MA574 Blitzschutz | 1 | 0 | 0 | 1 |
| Multi-Produkt | 1 | 0 | 0 | 1 |

## Zusammenfassung nach Größe

| Objektgröße | Tests | Tendenz |
|-------------|-------|---------|
| Klein (1 Schaltschrank, <30 BM, klein Blitz) | 4 | Stark überhöht (+169% bis +701%) |
| Standard (100-1.000 BM, 500-3.000 m²) | 5 | Gemischt (1 Pass, 2 Marginal, 2 Fail) |
| Groß (>5.000 m², >40 UV) | 5 | Teils über-, teils unterpreist |
| Multi-Produkt | 1 | Nicht unterstützt |
