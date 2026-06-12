# SmartCal Action Plan — Post-Testrunde 08.06.2026

**Cel**: AL-Tagung 30.06–02.07 — 4-5 zwalidowanych przykładów + 30min live testing
**Deadline**: ~20.06 (tydzień przed Tagung, żeby Pausch mógł zwalidować)
**Constraint**: Piotr + Matthias, 2-3 spotkania robocze z Pausch + testereami

---

## Testrunde — Wyniki

| # | Tester | Typ | Produkt | SmartCal | Real | Delta | Verdict |
|---|--------|-----|---------|----------|------|-------|---------|
| T01 | Pausch | Nahrungsmittel 20.000m² | MA505 VdS | 11.877€ | 6.850€ | +73% | FAIL |
| T02 | Pausch+Weiß | REWE 800m² | MA507 | 2.125€ | 657€ | +223% | FAIL |
| T03 | Pausch | 1 Schaltschrank | MA501 | 1.051€ | 391€ | +169% | FAIL |
| T04 | Pausch | Auto Service 114 BM | MA560 | 1.198€ | 1.217€ | **-1.5%** | **PASS** |
| T05 | Pausch | Landwirt 23 BM | MA560 | 1.400€ | 175€ | +701% | FAIL* |
| T06 | Pausch | Maritim Hotel | MA510 | 4.064€ | 220€ | +1747% | INKONKL.* |
| T07 | Pausch | Metallbetrieb 48UV | MA505 | — | — | — | NICHT GETESTET |
| T08 | Weiß | Apleona 26.000m² | VdS+DGUV | ~10.370€ | 7.932€ | +31% | MARGINAL |
| T09 | Weiß | Schule BMA+SiBel+ELT | Multi | ~13.000€ | 4.800€ | +171% | FAIL |
| T10 | Weiß | Max Planck 545 BM | MA560 | 1.947€ | 5.341€ | **-63%** | FAIL |
| T11 | Weiß | REWE München | MA507 | 1.736€ | ~657€ | +164% | FAIL |
| T12 | Weiß | Helios Kliniken | VdS+DGUV | 4.771€ | 13.110€ | **-64%** | FAIL |
| T13 | Docx | Motel One MA501 | MA501 | "utopisch" | 621€ RV | — | FAIL |
| T14 | Docx | roMEd Klinik | MA501 | ~3.470€ | 3.470€ | **~0%** | **PASS** |
| T15 | Docx | DGUV Würzburg | MA507 | ~3.195€ | 4.195€ | -24% | MARGINAL |
| T16 | Docx | Polizei Blitzschutz | MA574 | "utopisch" | 205€ | — | FAIL |

**Pass rate: 2/14 = 14%**
*T05: Referenzpreis möglicherweise fehlerhaft (Pausch: "Abrechnung fehlerhaft")*
*T06: 220€ ist sicher falsch für Maritim Hotel Baurecht*

---

## Probleme — Priorisiert nach Impact

### P1. Flächenfaktor-Degression fehlt [KRITISCH]
**Impact**: Alle Gebäude >2.000m² betroffen (T01, T08, T09, T12)
**Root Cause**: Lineares Pricing `(m² / 10) × rate` ohne Degression
**Daten vorhanden**: NBG Kalkulationshilfen — separate DGUV vs VdS Tabellen:
- DGUV: {0m²: 0.8, 2000: 0.8, 4000: 0.6, 6000: 0.5, 10000: 0.4, 25000: 0.3}
- VdS: {0m²: 1.0, 2000: 0.9, 4000: 0.8, 6000: 0.7, 10000: 0.5, 25000: 0.35}
**Fix**: Interpolierte Degression in `dguv_pruefkosten()` + `_pruef_dguv()` (graph engine)
**Aufwand**: ~2h
**Dateien**: `pricing_rules.py:281-308`, `graph_pricing_engine.py:293-405`

### P2. VdS Stub-Bug — gibt DGUV-Preis zurück [KRITISCH]
**Impact**: ALLE VdS-Kalkulationen falsch (T01, T08, T12)
**Root Cause**: `vds_pruefkosten()` (line 388) = `return dguv_pruefkosten(m)` — ignoriert VdS-Flächenfaktor + Stundensatz 208€
**Zusätzlich**: `VDS_ID_PAUSCHALE = 208.00` deklariert (line 24) aber NIRGENDS verwendet
**Fix**: Eigene VdS-Logik mit VdS-Degression + 208€ Stundensatz
**Aufwand**: ~2h
**Dateien**: `pricing_rules.py:388-390`, `graph_pricing_engine.py:411-461`

### P3. VdS-Only zeigt DGUV+VdS doppelt [KRITISCH]
**Impact**: T08 (Weiß), T12 — User fragt VdS-only, bekommt DGUV-Basis + VdS obendrauf
**Root Cause**: `dguv_plus_vds_pruefkosten()` berechnet immer DGUV erst, addiert VdS als Zuschlag
**Erwartung**: Bei VdS-only → NUR VdS-Kosten anzeigen, KEIN DGUV-Basis
**Fix**: Routing-Logik: wenn `vds_pruefung=True` und KEIN DGUV gewünscht → nur `vds_pruefkosten()`
**Aufwand**: ~3h (Chat Coordinator + Pricing Logic + UI Labels)
**Dateien**: `pricing_rules.py:393-405`, `chat.py` (DGUV coordinator prompt), `graph_pricing_engine.py`

### P4. Chat fixiert sich auf m² [HOCH]
**Impact**: ALLE Tester haben das bemerkt (Pausch, Weiß, Pfilf, Steinwidder)
**Root Cause**: Coordinator system prompt behandelt m² als quasi-Pflichtfeld
**Fälle**:
- 48 UV auf 4 Gebäude → fragt nach m² (Pausch)
- 545 BM ortsveränderlich → fragt nach m² (Steinwidder)
- 1 Schaltschrank → fragt nach Mitarbeitern (Pausch)
- Motel One BM-Anzahl gegeben → fragt nach Zimmern (Pfilf)
- UV-Ortsfest + Maschinen → Schleife zu m² (Weiß)
**Fix**: Coordinator prompt überarbeiten:
- m² ist EIN Merkmal, nicht DAS Merkmal
- Wenn UV-Anzahl gegeben → calculate SOFORT (Prüfkosten = f(UV × Kat))
- Wenn BM-Anzahl gegeben (MA560) → calculate SOFORT (kein m² nötig)
- Wenn Schaltschrank-Einzelprüfung → Mindestpreis-Logik, kein m²
**Aufwand**: ~3h
**Dateien**: `products/dguv_v3/chat.py` (COORDINATOR_SYSTEM prompt)

### P5. MA560 per-Device Pricing fehlt [HOCH]
**Impact**: T04 zufällig ok (+1.5%), T05 (+701%), T10 (-63%)
**Root Cause**: System verwendet m²-basierte Logik statt Per-Gerät-Rate
**Reales Pricing**: 9.80€/BM (Max Planck Angebot) oder Blend 9.50€/BM + 200€ Overhead
**Daten**: NBG (4.60€/Gerät flat) vs MUC/LPV (515€ + 12.80€/weiteres)
**Fix**: Per-BM Pricing-Funktion mit Staffelung
**Aufwand**: ~4h (neues Pricing-Modul + Chat-Integration)
**Dateien**: Neues Modul oder Erweiterung in `pricing_rules.py`

### P6. Referenzpreis wird ignoriert [MITTEL]
**Impact**: T02 (Steinwidder: 545€ gegeben, System blieb bei 1.900€)
**Root Cause**: Referenzpreis-Mechanismus existiert (`_apply_dguv_modifiers`), aber Gewicht zu niedrig
**Fix**: Referenzpreis stärker gewichten, insbesondere bei kürzlichen Referenzen (<3 Jahre)
**Aufwand**: ~2h
**Dateien**: `graph_pricing_engine.py:467-510`

### P7. Installationskategorien 7+8 fehlen [MITTEL]
**Impact**: Krankenhäuser (T12, T14), Ex-Bereiche (MA501)
**Root Cause**: Code hat nur Kat 1-6, SBR-Tool hat 8 Kategorien
**Daten**: Kat 7 = 5.42€/10m² (AG2 Krankenhaus), Kat 8 = 7.68€/10m² (Ex-Bereich)
**Fix**: `PREIS_PER_10M2` dict erweitern + Graph-Nodes
**Aufwand**: ~1h
**Dateien**: `pricing_rules.py:29-36`

### P8. Kleine Aufträge → überhöhte Preise [MITTEL]
**Impact**: T03 (1 Schaltschrank +169%), T05 (23 BM +701%), T16 (klein Blitz "utopisch")
**Root Cause**: Grundkosten + Reise dominieren bei Mini-Aufträgen
**Fix**: Minimum-Pricing-Pfad: wenn Scope < X → Stundensatz × geschätzte Dauer statt Fläche×Rate
**Aufwand**: ~3h
**Dateien**: `pricing_rules.py`, `graph_pricing_engine.py`

### P9. PLZ/Ort-Mapping Fehler [NIEDRIG]
**Impact**: T03 (77933 → Bad Kissingen falsch), Reisekosten 0€ bei nur PLZ
**Root Cause**: Geocoding-Fallback unzuverlässig
**Fix**: PLZ-Centroid-Fallback verbessern, NL-Zuordnung über CRM-PLZ-Mapping priorisieren
**Aufwand**: ~1h
**Dateien**: `common/geocode.py`

### P10. UI-Cleanup [NIEDRIG]
**Impact**: Verwirrung bei Testern, aber kein Pricing-Fehler
**Fixes**:
- "Messstellen und Staffelung" Label aus Blitzschutz entfernen (~30min)
- RLT Hygieneinspektion Empfehlung bei ELT entfernen (~30min)
- "DGUV V3" Label bei VdS-Only nicht anzeigen (~1h)
- Inflationsabweichung Vorzeichen korrigieren (~30min)
**Aufwand**: ~2.5h total

---

## Nicht im PoC-Scope (für MVP notieren)

### F1. Multi-Produkt-Bundling
T09 zeigt: BMA + SiBel + ELT = 4.800€ gesamt. System kann nur 1 Produkt. → MVP
**Why**: Erfordert komplett neue Architektur (Multi-Graph-Query, Synergie-Reisekosten)

### F2. Rahmenvertrag-Rabatte
T01, T02, T13 — Großkunden zahlen 30-60% unter LPV. → MVP
**Why**: Erfordert Kunden-DB mit RV-Konditionen, Rabattmatrix

### F3. PDF/Datei-Upload
Weiß: "Kann ich auch Dateien reinladen?" → MVP/Phase 2
**Why**: Erfordert Document-Processing-Pipeline (OCR/LLM-Extraction)

### F4. Stundenbasis-Pricing für komplexe Fälle
Helios (T12): 54h × 239€ = 13.110€. Wenn Aufwand nicht über Fläche bestimmbar → Stundenschätzung.
**Why**: Erfordert Aufwands-Schätzmodell basierend auf Anlagenkomplexität

---

## Implementierungsplan — Priorisierte Reihenfolge

### Phase A: Pricing-Korrekturen (1-2 Tage)
**Ziel**: Korrekte Preise für Standard-DGUV und VdS

| # | Task | Aufwand | Dateien |
|---|------|---------|---------|
| A1 | Flächenfaktor-Degression implementieren (DGUV + VdS getrennt) | 2h | pricing_rules.py, graph_pricing_engine.py |
| A2 | VdS-Stub fixen — eigene Logik mit VdS-Degression + 208€ | 2h | pricing_rules.py, graph_pricing_engine.py |
| A3 | VdS-Only Routing (kein DGUV-Basis bei reiner VdS-Anfrage) | 2h | pricing_rules.py, graph_pricing_engine.py |
| A4 | Installationskategorien 7+8 hinzufügen | 1h | pricing_rules.py, graph nodes |
| A5 | Referenzpreis-Gewichtung erhöhen | 1h | graph_pricing_engine.py |

**Validierung nach Phase A**: T01, T02, T08, T12, T15 neu berechnen → müssen besser werden

### Phase B: Chat-Coordinator-Überarbeitung (1 Tag)
**Ziel**: Natürlicheres Gespräch, weniger irrelevante Fragen

| # | Task | Aufwand | Dateien |
|---|------|---------|---------|
| B1 | m²-Fixierung auflösen — UV/BM/Schaltschrank als gleichwertige Inputs | 3h | dguv_v3/chat.py |
| B2 | Irrelevante Fragen eliminieren (PV bei Supermarkt, Mitarbeiter bei Schaltschrank) | 1h | dguv_v3/chat.py |
| B3 | MA560-Routing: BM-Anzahl → sofort calculate, kein m² | 1h | dguv_v3/chat.py |
| B4 | Kleine-Aufträge-Erkennung: "1 Schaltschrank" → Mindestpreis-Pfad | 2h | dguv_v3/chat.py, pricing_rules.py |

**Validierung nach Phase B**: T03, T04, T05, T10 Szenarien manuell durchspielen

### Phase C: MA560 Per-Device Pricing (0.5 Tag)
**Ziel**: Ortsveränderliche korrekt bepreisen

| # | Task | Aufwand | Dateien |
|---|------|---------|---------|
| C1 | Per-BM Pricing-Funktion: Staffelung nach Geräteanzahl | 2h | pricing_rules.py |
| C2 | Blend-Modell: ~9.50€/BM + 200€ Overhead (oder NBG/MUC) | 1h | pricing_rules.py |
| C3 | Graph-Integration für MA560 | 1h | graph_pricing_engine.py |

**Validierung**: T04 (114 BM → ~1.200€), T10 (545 BM → ~5.300€)

### Phase D: UI + Kleinigkeiten (0.5 Tag)
**Ziel**: Saubere Darstellung für AL-Tagung

| # | Task | Aufwand | Dateien |
|---|------|---------|---------|
| D1 | Blitzschutz-Labels aus DGUV entfernen | 30min | Frontend |
| D2 | RLT-Empfehlung bei ELT entfernen | 30min | chat.py |
| D3 | PLZ-Mapping verbessern (77933 Bug) | 1h | geocode.py |
| D4 | Labels: "DGUV" bei VdS-Only nicht anzeigen | 1h | Frontend + Backend |
| D5 | Inflationsabweichung Vorzeichen fixen | 30min | graph_pricing_engine.py |

### Phase E: Validierung + 5 Demo-Cases (1 Tag)
**Ziel**: 4-5 zwalidowane przykłady für AL-Tagung

| # | Task | Aufwand |
|---|------|---------|
| E1 | 16 Test Cases erneut durchlaufen → Pass-Rate dokumentieren | 2h |
| E2 | 5 Best-Case-Szenarien für Demo auswählen | 1h |
| E3 | Demo-Script für AL-Tagung vorbereiten | 2h |
| E4 | Absprache mit Pausch — Validierung der 5 Cases | 1h (Call) |

---

## Demo-Kandidaten für AL-Tagung (5 Szenarien)

1. **Standard-Büro DGUV** — 3.000-5.000m², Kat 2, München → Preis ±15%
2. **Industrie VdS** — 8.000m², Kat 3, Augsburg → VdS-Only korrekt
3. **Multi-Site DGUV** — 3 Standorte mit je m² → per-Werk Aufschlüsselung (Weiß: "hat gut funktioniert")
4. **Hotel + PV + Ladesäulen** — Zusatzleistungen demonstrieren
5. **Referenzpreis-Korrektur** — alten Preis eingeben → System adjustiert → zeigt Transparenz

**Bewusst NICHT zeigen**: MA560 ortsveränderlich (noch zu instabil), sehr große/sehr kleine Objekte

---

## Timeline

```
KW24 (09.-13.06): Phase A (Pricing) + Phase B (Chat)
KW25 (16.-20.06): Phase C (MA560) + Phase D (UI) + Phase E (Validierung)
KW26 (23.-27.06): Buffer + Demo-Prep + Pausch-Call
KW27 (30.06-02.07): AL-Tagung
```

---

## Offene Fragen an Pausch (nächster Call)

1. T05 (23 BM, 175€) und T06 (Maritim 220€) — "Abrechnung fehlerhaft"? Korrekte Referenzpreise?
2. VdS-Only Pricing: soll das System VdS ohne DGUV berechnen können? Oder immer kombiniert?
3. Baurecht (MA510): eigener Pricing-Pfad oder über DGUV mit Zuschlag?
4. Kleine Aufträge (1 Schaltschrank): Stundenbasis oder Mindestpreis?
5. Welche 5 Demo-Cases für AL-Tagung? Pausch wählt aus seinen realen Anlagen?
6. Benni Bachmeier / Martin Römerkamp einbinden? (Burgey + Steinwidder: "Wir bräuchten die EFI")
7. T07 (König & Bauer Metallbetrieb): hat er das noch getestet? Ergebnis?
