# SmartCal@EG — Development Timeline 3 Produkte
## Stand: 12.04.2026

---

## Deltas zum Original-Plan (PROJECT_PLAN_12W.md)

### Zeitverschiebung (+2 Wochen)
| | Original | Jetzt |
|---|---|---|
| Projektstart | KW14 (31.03) | **KW16 (14.04)** — 2 Wochen später |
| Phase 1 Ende (M1) | KW16 | **KW18** |
| Phase 2 Ende (M2) | KW20 | **KW22** |
| Phase 3 Ende (M3) | KW23 | **KW25** |
| Phase 4 Ende (M4) | KW25 | **KW27** |
| Buffer | KW26 (1 Woche) | **entfällt** |
| Demo KW27 | 06.07.2026 | **unverändert** — Phase 4 + Demo in KW27 |

### Produktänderungen
| | Original | Jetzt | Impact |
|---|---|---|---|
| Produkt 1 | Blitzschutz | **Blitzschutz** | kein Change |
| Produkt 2 | BMA (Brandmeldeanlagen) | **RLT (Lüftungsanlagen)** | ähnliche Komplexität, anderer Fachbereich |
| Produkt 3 | DGUV V3 ortsveränderlich | **Elektrische Anlagen ortsfest** | **deutlich komplexer** — m²×Kat statt Stückpreis |

### Daten-Status (vs Original-Annahme)
| | Original-Annahme | Realität |
|---|---|---|
| LPV / Preisliste | "KW14 benötigt" | **✅ erhalten 10-12.04** (129 S. komplett) |
| Beispielangebote | "KW14 benötigt" | **✅ erhalten** (Gersthofen, Augsburg, Audi, Volkswohlbund, WISAG, Apleona) |
| Kalkulationsexcel | "KW14 benötigt" | **✅ erhalten** (8+ Tools) |
| Prüfberichte Blitzschutz | nicht eingeplant | **✅ 99 Berichte erhalten** (Bonus!) |
| Prüfberichte RLT | nicht eingeplant | **⏳ Pausch ab 14.04** |
| Prüfberichte Elektr. Anlagen | nicht eingeplant | **⏳ Pausch ab 14.04** |
| Prüfpflichtendatenbank | nicht eingeplant | **⏳ Felix Teichler via Pfeifer** |
| Sachverständiger-Slot | "KW14-15" | **⏳ noch nicht terminiert** |
| Realpreise Blitzschutz | nicht eingeplant | **✅ ~200-300 Augsburg-Objekte** (Bonus!) |

### Hosting
| | Original | Jetzt |
|---|---|---|
| Entscheidung | "KW22" | **✅ entschieden 10.04**: POC auf MING Cloud, Azure TÜV SÜD Tenant nach Decision Gate |
| StyleGuide | "KW17 benötigt" | **nicht nötig für POC** (Lars Bremer: "Funktionsvalidierung first") |

### Komplexitätsverschiebung
| | Original | Jetzt | Aufwand-Delta |
|---|---|---|---|
| Blitzschutz | 2,25 d | **3 d** | +0.75 d (6 Features aus 99 Berichten dazu) |
| Produkt 2 (BMA→RLT) | 2,5 d | **2 d** | -0.5 d (RLT einfachere Preisstruktur als BMA) |
| Produkt 3 (DGUV ortv→EA ortf) | 2,25 d | **4 d** | **+1.75 d** (Zonen-Splitting, Installationskategorien, Sicherheitsbeleuchtung) |
| Shared | 4,5 d | **4,5 d** | unverändert |
| **Total Phase 1** | **11,5 d** | **13,5 d** | **+2 Tage** |

---

## Neuer Timeline: Phase 1 Entwicklung (KW15–KW18)

### KW15: 14–17 April — "Blitzschutz + Graph Foundation"

**Daten-Voraussetzung:** ✅ alles vorhanden

```
Mo 14.04:
  □ S1: Graph Setup FalkorDB — Schema, Named Graph "smartcal"          [2h]
  □ B1: Blitzschutz Preisdaten in Graph (33€/MS, Berichtstypen)        [2h]
  □ B2: 20+ Standorte mit Geocoding in Graph                           [3h]
  □ B4: PDF-Extraktion 99 Berichte starten (Claude API batch, Hintergrund) [2h]

Di 15.04:
  □ B3: Gebäudetypen + Schutzklassen in Graph                          [1h]
  □ B5: Aggregation 99 JSONs (Trennstellen-Tabelle, Mängel, Ergebnis)  [2h]
  □ B6: Graph-Import TYPISCHE_TRENNSTELLEN + MangelKategorien           [1h]
  □ B7: Kalkulationslogik Blitzschutz (Formel komplett)                 [3h]

Mi 16.04:
  □ B8: Schätzung Trennstellen (UI Button "Schätzen" + Graph-Query)    [2h]
  □ B9: Input-Validator (Perzentile-Check, Warning)                     [1h]
  □ B10: UI-Boxen (Upsell, Mängelstatistik, Konfidenz-Range)           [2h]
  □ B11: Hinweis-System (>10 MS, Erstprüfung, Hochhaus)                [1h]

Do 17.04:
  □ B12: Validierung vs Augsburg-Realpreise (6 Testfälle)              [2h]
  □ S2: Grundkosten-Modul (256€ + 49€ + Tagegeld)                     [1h]
  □ S4: Berichterstellungs-Modul (119/380/550€)                        [1h]
  □ R1+R2: RLT Preisdaten in Graph (Sonderbauten + Garagen)            [2h]
  □ E1: Elektrische Anlagen Preisdaten in Graph (Kat 1/2/3)            [1h]

Fr 18.04:
  □ Demo-Prep + interne Review
  □ DEMO 14:00: Blitzschutz kalkuliert mit realen Preisen
```

**Meilenstein KW15:** Blitzschutz End-to-End funktionsfähig inkl. 6 Features aus 99 Berichten. RLT + EA Preisdaten im Graph geladen.

**Blocker:** keiner — alle Daten vorhanden.

**Pausch-Aufgabe für diese Woche:** Prüfberichte RLT + EA vorbereiten und senden.

---

### KW16: 21–25 April — "RLT komplett + EA Basis"

**Daten-Voraussetzung:** ⏳ Prüfberichte RLT + EA von Pausch (erwartet KW15/16)

```
Mo 21.04:
  □ S3: Reisekosten-Modul (nächster Standort, km-Berechnung, Reisezeit) [4h]
  □ R3: RLT Gebäudetyp-Routing (Sonderbau vs Garage vs OP vs fensterlos) [2h]

Di 22.04:
  □ R4: RLT Schätzformel (BGF + Nutzung → Luftstromvolumen m³/h)       [3h]
      WENN Prüfberichte RLT da: aus Berichten ableiten
      WENN NICHT: Faustregeln aus Normen (DIN EN 13779 / VDI 6022)
  □ R5: RLT Rückfragen-Logik ("Wie viel m³/h?", "Brandschutzklappen?") [2h]

Mi 23.04:
  □ E2: EA Gebäudetyp → Installationskategorie Mapping                 [3h]
      (Büro=Kat2, Industrie=Kat3, Wohn-Allgemein=Kat1, mixed buildings)
  □ E3 start: EA Zonen-Splitting-Logik                                  [4h]
      (Gebäude = Summe der Zonen × Kategorie × Fläche)

Do 24.04:
  □ E3 finish: Zonen-Splitting fertig + Schieberegler grob/fein         [4h]
      GROB: eine Kat für ganzes Gebäude → schnelle Schätzung
      FEIN: User gibt Zonen-Aufteilung ein → exakte Kalkulation
  □ E4: Sicherheitsbeleuchtung (5 Grundpreise + 3 Zuschläge + Garagen) [2h]

Fr 25.04:
  □ E5: Flächenfaktoren (<100m² / >500m² Korrekturfaktor)              [1h]
  □ E6: EA Schätzformel (BGF + Nutzung → typische Kat-Verteilung)      [3h]
      WENN Prüfberichte EA da: aus Berichten + Gersthofen/Augsburg
      WENN NICHT: Gersthofen + Augsburg + Audi als 3 Referenzpunkte
  □ DEMO 14:00: Alle 3 Produkte kalkulieren mit realen Preisen
```

**Meilenstein KW16:** RLT End-to-End. EA kalkuliert (Grundlogik + Zonen-Splitting grob/fein).

**Risiko:** Falls Prüfberichte RLT/EA nicht bis Mi kommen → Schätzformeln aus Normen/Faustregeln statt aus Daten. Funktioniert, aber weniger beeindruckend.

---

### KW17: 28 Apr – 2 Mai — "Chat-Engine + Integration"

**Daten-Voraussetzung:** ✅ Preisdaten komplett, Schätzformeln vorhanden (ggf. vorläufig)

```
Mo 28.04:
  □ E7: EA Rückfragen-Logik                                             [3h]
      ("Haben Sie Angaben zu Installationskategorien?"
       "Gibt es Serverräume/EDV-Zentralen?"
       "Sicherheitsbeleuchtung vorhanden?")
  □ S6: Kalkulationsausgabe (Aufschlüsselung, Gesamt, Hinweise)         [3h]

Di 29.04 – Do 01.05:
  □ S5: Chat + Rückfragen-Engine (ReAct Agent, 3 Produkte integriert)  [12h]
      - Agent erkennt Produkt aus natürlichsprachiger Anfrage
      - Stellt produktspezifische Rückfragen
      - Ruft richtige Kalkulationslogik auf
      - Formatiert Ergebnis mit Hinweisen + Upsell + Mängelstatistik
      - Cross-Selling: "Blitzschutz + EA = gleiche Begehung"

Fr 02.05:
  □ Integration-Tests: 10+ Szenarien über alle 3 Produkte              [3h]
  □ DEMO 14:00: Natürlichsprachige Anfrage → komplette Kalkulation
```

**Meilenstein KW17:** Chat-basierte Kalkulation aller 3 Produkte funktioniert. Rückfragen, Hinweise, Upsell.

**→ MEILENSTEIN M1: Korrekte Kalkulation der 3 Produkte mit realen Preisen ✓**

---

### KW18: 5–9 Mai — "Schieberegler + Cross-Selling"

```
Mo-Di:
  □ Schieberegler grob/mittel/fein für alle 3 Produkte                 [6h]
  □ Cross-Selling-Logik (gleiche Begehung, Bündelrabatt Reisekosten)   [3h]

Mi-Do:
  □ Zuschläge-System (Erstprüfung +100%, Einzelprüfung +20%, Eil +25%) [3h]
  □ Angebotshistorie / Session-Management (persistent)                  [4h]

Fr:
  □ DEMO 14:00: Schieberegler live, Cross-Selling, Zuschläge
```

**→ Übergang zu Phase 2 (UX & Features) ab KW19**

---

## Zusammenfassung: neuer vs alter Zeitplan

```
         KW14  KW15  KW16  KW17  KW18  KW19  KW20  KW21  KW22  KW23  KW24  KW25  KW26  KW27
ORIGINAL ├──Phase 1──┤├────Phase 2────┤├──Phase 3──┤├Phase 4┤ Buf  DEMO
NEU                   ├──Phase 1──┤├────Phase 2────┤├──Phase 3──┤├Phase 4┤    DEMO
                                                                              ↑
                                                                         kein Buffer
```

| Phase | Original | Neu | Delta |
|---|---|---|---|
| Phase 1: Foundation | KW14–16 (3 Wo) | **KW16–18** (3 Wo) | +2 Wochen Verschiebung |
| Phase 2: UX & Features | KW17–20 (4 Wo) | **KW19–22** (4 Wo) | +2 Wochen Verschiebung |
| Phase 3: Qualität | KW21–23 (3 Wo) | **KW23–25** (3 Wo) | +2 Wochen Verschiebung |
| Phase 4: Launch | KW24–25 (2 Wo) | **KW26–27** (2 Wo) | +2 Wochen Verschiebung |
| Buffer | KW26 (1 Wo) | **entfällt** | aufgebraucht |
| Demo | KW27 | **KW27** | **unverändert** |

---

## Risiken im neuen Plan

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|---|---|---|---|
| **Kein Buffer mehr** | 100% | Jede weitere Verzögerung trifft KW27 direkt | Scope-Reduktion als Ventil: EA-Schieberegler nur grob/fein (kein mittel), RLT nur Sonderbauten+Garagen (kein OP/Hygiene) |
| **Prüfberichte RLT/EA kommen spät** | 40% | Schätzformeln nur aus Normen, nicht aus Daten | Kalkulator funktioniert trotzdem (LPV-Preise reichen), Schätzformeln nachliefern |
| **EA Zonen-Splitting zu komplex** | 30% | KW16 reicht nicht für volle Implementierung | Fallback: nur grob-Modus (eine Kat pro Gebäude), fein-Modus in Phase 2 |
| **Prüfpflichtendatenbank kommt nicht** | 50% | Pflichtprüfungen manuell gepflegt (10-15 Mappings) | Ausreichend für MVP, vollständige DB in Phase 2 |
| **SV-Validierung nicht terminiert** | 60% | Schätzformeln unvalidiert auf Demo | Konfidenz-Label "vorläufig, SV-Validierung ausstehend" |

## Scope-Ventile (falls wir Zeit brauchen)

Was wir CUTTEN können ohne die Demo zu gefährden:

| Feature | Originalplan | Kann weg? | Warum |
|---|---|---|---|
| EA Schieberegler "mittel" | 3 Stufen | ✅ nur grob + fein | mittel = nice-to-have |
| RLT Subtypen 2.3–2.9 | OP, Reinraum, Hygiene, Energie | ✅ nur 2.1 Sonderbauten + 2.2 Garagen | Rest = "nach Vereinbarung" = kein Kalkulator nötig |
| PDF-Export | KW20 | ✅ verschieben auf KW21+ | Demo zeigt Live-Kalkulation, kein PDF nötig |
| Angebotshistorie | KW18 | ✅ verschieben | Nice-to-have für Demo |
| Responsive Layout | KW17 | ✅ Desktop only für POC | Bremer: "Funktionsvalidierung" |

---

## Wöchentliche Demos (Phase 1)

| KW | Demo-Titel | Zeige | Veit-Insight |
|---|---|---|---|
| **15** | "Blitzschutz kalkuliert" | Live: 41 Messstellen → 2.238€ + Schätzung + Upsell | "99 Berichte ausgewertet: 78% Mängel, Bewuchs #1, Realpreis-Match X%" |
| **16** | "3 Produkte kalkulieren" | RLT: "Gaststätte 8.000 m³/h" → Preis. EA: "Büro 5.000m²" → Zonen-Kalkulation | "Vergleich Gersthofen (Verteiler-Ebene) vs Augsburg (nur m²) — SmartCal handelt beides" |
| **17** | "Chat versteht Deutsch" | Natürlichsprachig: "Bürogebäude Augsburg, Blitzschutz + Elektrische Anlage" → Cross-Sell | "Prüfintervall-Analyse: 62% häufiger geprüft als DIN-Minimum" |
| **18** | "Grob oder fein — du entscheidest" | Schieberegler: Museum 2000m² → Richtpreis 5s vs exakte Kalkulation 2min | "Betreiber-Muster: 20% der Anfragen kommen über Facility Manager" |
