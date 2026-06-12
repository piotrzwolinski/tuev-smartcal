# Testrunde 1 — Implementierungsplan

**Ziel**: AL-Tagung 30.06–02.07 — 4-5 validierte Demo-Cases + 30min Live-Testing
**Deadline**: ~20.06 (Woche vorher, Pausch validiert)
**Budget**: ~5 Arbeitstage

---

## Priorisierung: Impact-Matrix

| Prio | Issue | Typ | Betroffene Tests | Geschätzter Impact auf Pass-Rate |
|------|-------|-----|-----------------|----------------------------------|
| P1 | Flächenfaktor-Degression | Daten (D1) | T01, T08, T09, T12 | +2-3 Tests (T08→PASS, T12→PASS) |
| P2 | VdS-Stub fixen | Daten (D2) | T01, T08, T12 | +1-2 Tests (verstärkt P1) |
| P3 | VdS-Only Routing | Daten (D3) | T08, T12 | +0-1 Tests (UX-Verbesserung) |
| P4 | MA560 per-Device | Daten (D4) | T04, T05, T10 | +1-2 Tests (T10→PASS) |
| P5 | Chat m²-Fixierung | Subjektiv (S1) | Alle | +0 Tests (UX, kein Pricing) |
| P6 | Kleine Aufträge | Daten (D5) | T03, T05, T13, T16 | +1-2 Tests (T03→MARGINAL) |
| P7 | Kat 7+8 | Daten (D7) | T12, T14 | +0-1 Tests |
| P8 | Referenzpreis-Gewicht | Daten (D6) | T02 | +0-1 Tests |
| P9 | UI-Cleanup | Daten (D10, D11) | — | +0 Tests (Professionalität) |
| P10 | PLZ-Mapping | Daten (D8) | T03 | +0 Tests |

**Erwartete Pass-Rate nach Fixes**: 6-8 von 14 bewertbaren Tests (~43-57%)

---

## Phase A: Pricing-Kern (2 Tage)
*Ziel: Korrekte Preise für Standard- und Groß-Objekte*

### A1. Flächenfaktor-Degression [P1] — 2h
**Was**: Interpolierte Degression statt linearem Pricing
**Dateien**: `pricing_rules.py:281-308`, `graph_pricing_engine.py:293-405`
**Daten**: NBG Kalkulationshilfen DGUV + VdS Tabellen (bereits vorhanden)
**Validierung**: T01 (20.000m²) neu berechnen — Ziel ≤8.500€ statt 11.877€

### A2. VdS eigene Pricing-Logik [P2] — 2h
**Was**: `vds_pruefkosten()` mit VdS-Degression + 208€ Stundensatz statt DGUV-Stub
**Dateien**: `pricing_rules.py:388-390`, `graph_pricing_engine.py:411-461`
**Validierung**: T01 VdS-Anteil separat prüfen — Pausch: "VdS kommt fast hin"

### A3. VdS-Only Routing [P3] — 3h
**Was**: Wenn User VdS-only will → NUR VdS-Kosten, KEIN DGUV-Basis anzeigen
**Dateien**: `pricing_rules.py:393-405`, `dguv_v3/chat.py`, `graph_pricing_engine.py`
**Validierung**: VdS-only-Anfrage → keine DGUV-Prüfkosten-Zeile in der Ausgabe

### A4. Installationskategorien 7+8 [P7] — 1h
**Was**: `PREIS_PER_10M2` dict um Kat 7 (5.42€) und Kat 8 (7.68€) erweitern + Graph-Nodes
**Dateien**: `pricing_rules.py:29-36`
**Validierung**: Krankenhaus-Case → Kat 7 statt Kat 3/4

### A5. Referenzpreis stärker gewichten [P8] — 1h
**Was**: Referenzpreis bei <3 Jahre alten Vergleichswerten höher gewichten
**Dateien**: `graph_pricing_engine.py:467-510`
**Validierung**: T02 mit Referenz 545€ → Ergebnis näher an 650€

**Phase-A-Gate**: T01, T02, T08, T12, T15 neu berechnen. Mindestens 3 davon besser.

---

## Phase B: Chat-Verhalten (1 Tag)
*Ziel: Natürlicheres Gespräch, weniger irrelevante Fragen*

### B1. m²-Fixierung auflösen [P5] — 3h
**Was**: Coordinator-Prompt überarbeiten:
- m² ist EIN mögliches Merkmal, nicht DAS Pflichtfeld
- Wenn UV-Anzahl gegeben → sofort kalkulierbar (Prüfkosten = f(UV × Kat))
- Wenn BM-Anzahl gegeben (MA560) → sofort kalkulierbar
- Wenn Schaltschrank-Einzelprüfung → Mindestpreis-Logik
**Dateien**: `products/dguv_v3/chat.py` (COORDINATOR_SYSTEM prompt)

### B2. Irrelevante Fragen eliminieren — 1h
**Was**: Keine PV-Frage bei Supermarkt, keine Mitarbeiter-Frage bei 1 Schaltschrank
**Dateien**: `products/dguv_v3/chat.py`

### B3. MA560-Routing fixen [S2] — 1h
**Was**: MA560 nie ablehnen ("wird von anderen Fachleuten durchgeführt" entfernen)
**Dateien**: `products/dguv_v3/chat.py`

### B4. Kleine-Aufträge-Erkennung [P6] — 2h
**Was**: Wenn Scope < Schwellwert → Stundensatz × geschätzte Dauer statt Fläche×Rate
**Dateien**: `products/dguv_v3/chat.py`, `pricing_rules.py`
**Validierung**: T03 (1 Schaltschrank) → Ergebnis ~400-500€ statt 1.051€

**Phase-B-Gate**: T03, T04, T05, T10 manuell durchspielen im Chat.

---

## Phase C: MA560 per-Device (0,5 Tag)
*Ziel: Ortsveränderliche nach Geräteanzahl bepreisen*

### C1. Per-BM Pricing-Funktion [P4] — 2h
**Was**: Staffelung nach Geräteanzahl statt m²-Logik
- Basis: ~9,50-9,80 €/BM (aus Max Planck Rechnung + NBG)
- Overhead: ~200€ Grundpauschale
- Staffelung: ab 100 BM leichte Degression
**Dateien**: `pricing_rules.py` (neue Funktion)

### C2. Graph-Integration MA560 — 1h
**Was**: MA560-Pfad im Pricing-Engine auf per-BM umstellen
**Dateien**: `graph_pricing_engine.py`

**Phase-C-Gate**: T04 (114 BM → ~1.200€ ✓), T10 (545 BM → ~5.300€ ✓)

---

## Phase D: UI + Cleanup (0,5 Tag)
*Ziel: Professionelle Darstellung für AL-Tagung*

### D1. Blitzschutz-Labels aus DGUV entfernen — 30min
### D2. RLT-Empfehlung bei ELT entfernen — 30min
### D3. PLZ-Mapping verbessern (77933 Bug) — 1h
### D4. "DGUV" Label bei VdS-Only nicht anzeigen — 1h
### D5. Inflationsabweichung Vorzeichen fixen — 30min

---

## Phase E: Validierung + Demo (1 Tag)
*Ziel: 4-5 validierte Demo-Cases für AL-Tagung*

### E1. Alle 16 Test Cases erneut durchlaufen — 2h
Erwartete neue Pass-Rate dokumentieren.

### E2. 5 Demo-Cases auswählen — 1h
Kandidaten (nach Fixes):
1. **Standard-Büro DGUV** ~3.000-5.000m², Kat 2 → Preis ±10%
2. **Industrie VdS-Only** ~8.000m², korrekte VdS-Preisfindung
3. **Multi-Site DGUV** 3 Standorte → per-Werk-Aufschlüsselung (Weiß: "hat gut funktioniert")
4. **MA560 Auto Service** 100+ BM → per-Gerät-Preis (T04 already PASS)
5. **Referenzpreis-Korrektur** alter Preis → System justiert transparent

**Bewusst NICHT zeigen**: Sehr kleine (<1.000€), sehr große (>20.000€), Multi-Produkt-Bundling.

### E3. Demo-Script vorbereiten — 2h
### E4. Absprache Pausch — 1h Call

---

## Timeline

```
KW24 (09.–13.06)
  Mo-Di: Phase A (Pricing-Kern)
  Mi-Do: Phase B (Chat-Verhalten)
  Fr:    Phase C (MA560 per-Device)

KW25 (16.–20.06)
  Mo:    Phase D (UI + Cleanup)
  Di-Mi: Phase E (Validierung + Demo)
  Do:    Pausch-Call — Demo-Cases validieren
  Fr:    Buffer / Nachbesserung

KW26 (23.–27.06)
  Buffer + finale Demo-Prep

KW27 (30.06–02.07)
  AL-Tagung
```

---

## Offene Fragen an Pausch (nächster Call)

1. **T05/T06 Referenzpreise**: 174€ für 23 BM bzw. 220€ für 10-Seiten-Gutachten — korrekt oder fehlerhaft?
2. **VdS-Only**: Soll System VdS ohne DGUV berechnen können? Oder immer kombiniert?
3. **Baurecht (MA510)**: Eigener Pricing-Pfad oder über DGUV mit Zuschlag?
4. **Kleine Aufträge**: Stundenbasis oder Mindestpreis?
5. **Demo-Cases**: Welche 5 aus seinen realen Anlagen?
6. **EFI einbinden**: Benni Bachmeier / Martin Römerkamp? (Burgey: "Wir bräuchten die EFI")
7. **T07 (Metallbetrieb)**: Noch getestet? Ergebnis?

---

## Nicht im PoC-Scope (→ MVP)

| Feature | Warum nicht jetzt | Evidenz |
|---------|-------------------|---------|
| Multi-Produkt-Bundling | Neue Architektur nötig | T09: BMA+SiBel+ELT = 4.800€ |
| Rahmenvertrag-Rabatte | Kunden-DB erforderlich | T01, T02, T13 |
| Datei-Upload | Pipeline erforderlich | Weiß: "Kann ich auch Dateien reinladen?" |
| Stundenbasis für Komplexfälle | Aufwands-Schätzmodell nötig | T12: 54h × 239€ |
