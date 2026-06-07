# SmartCal — Implementation Plan DGUV V3 ortsfest (MA507)

## Graph Provenance Pattern

Jeder Node und jede Edge bekommt Metadata:
```cypher
CREATE (:Node {
  id: '...',
  ...
  _quelle: 'Kalkulationshilfen NBG v2 / Sheet Ortsfest DGUV / Zeile 2',
  _stand: '2026-05-29',
  _validiert_durch: 'S. Pausch',
  _typ: 'regel'  // regel | statistik | llm_augmentiert | fachexperte
})
```

`_typ` Werte:
- `regel` = aus LPV / Kalkulationshilfen (deterministisch, offiziell)
- `statistik` = aus Prüfberichten extrahiert (belastbar, aber sample-abhängig)
- `llm_augmentiert` = Branchenwissen via LLM (Schätzung, markiert)
- `fachexperte` = von Pausch/Veit explizit vorgegeben (z.B. Reifegrad-Werte)
- `ausschreibung` = aus Gersthofen/Audi Ausschreibung (realer Preis)
- `versand` = aus Versand-Daten (reale Faktura)

---

## A. FLOW & INTERAKTION

### A1 — Kundenperspektive-Fragen per Branche

**Was:** System fragt Hotel→"Wie viele Zimmer?", Krankenhaus→"Wie viele Betten?", nicht "Wie viele UV?"

**Datenquelle:** Veit Mail 30.05 Punkt 2 (explizite Liste per Branche)

**Graph:**
```cypher
CREATE (:Branchenfrage {
  id: 'BF_HOTEL',
  gebaeudetyp: 'Hotel',
  frage: 'Wie viele Zimmer hat das Hotel?',
  zusatzfragen: ['Restaurant vorhanden?', 'Spa/Wellness vorhanden?', 'Konferenzbereiche vorhanden?'],
  _quelle: 'S. Veit Mail 30.05 Punkt 2',
  _typ: 'fachexperte'
})

CREATE (:Branchenfrage {
  id: 'BF_KRANKENHAUS',
  gebaeudetyp: 'Krankenhaus',
  frage: 'Wie viele Betten?',
  zusatzfragen: ['OP-Bereich vorhanden?', 'Intensivstation?'],
  _quelle: 'S. Veit Mail 30.05 Punkt 2',
  _typ: 'fachexperte'
})

// Analog: BF_INDUSTRIE, BF_TIEFGARAGE, BF_MOEBELHAUS, BF_VERWALTUNG, BF_SCHULE, BF_SUPERMARKT
```

**Chat Coordinator:** Wenn Gebäudetyp erkannt → query Graph nach Branchenfrage → stelle diese statt technische Fragen.

---

### A2 — Umrechnung Kundenmerkmal → m²

**Was:** Zimmer×30=m², Betten×50=m², etc.

**Datenquelle:** Branchenwissen (LLM-validiert), zu validieren mit S. Pausch auf Testrunde

**Graph:**
```cypher
CREATE (:Umrechnungsregel {
  id: 'UR_HOTEL_ZIMMER',
  gebaeudetyp: 'Hotel',
  kundenmerkmal: 'Zimmeranzahl',
  faktor_m2: 30,
  varianz: '25-45 je nach Hotelklasse',
  _quelle: 'Branchenwissen / LLM',
  _typ: 'llm_augmentiert',
  _validiert_durch: null  // → Pausch soll validieren
})
```

**Implementierung:** Wenn User "120 Zimmer" sagt → Graph query UR_HOTEL_ZIMMER → 120×30 = 3.600m² → weiter mit Fläche×Kat.

---

### A3 — Nutzungs-Mix

**Was:** "30% Büro, 50% Logistik, 20% Produktion" → gewichteter Kat-Preis

**Datenquelle:** Kalkulationshilfen NBG Sheet "Ortsfest DGUV" (Pos 1-16) + Veit Mail Punkt 4

**Graph:**
```cypher
// Bereits vorhanden als Installationskategorie-Nodes
// NEU: Nutzung→Kategorie Mapping mit Gewichtung

CREATE (:NutzungsMapping {
  id: 'NM_BUERO',
  nutzung: 'Büro',
  kategorie: 2,
  _quelle: 'Kalkulationshilfen NBG / Hilfstabellen / Zeile "Büro- oder Wohnräume"',
  _typ: 'regel'
})

CREATE (:NutzungsMapping {
  id: 'NM_LOGISTIK',
  nutzung: 'Logistik/Lager',
  kategorie: 1,  // Veit: "grundsätzlich Kat 1, abhängig von Ausstattung ggf. Kat 2"
  _quelle: 'S. Veit Mail 30.05 Punkt 4',
  _typ: 'fachexperte'
})

CREATE (:NutzungsMapping {
  id: 'NM_PRODUKTION',
  nutzung: 'Produktion',
  kategorie: 4,  // Veit: "je nach technischer Ausstattung Kat 4 oder höher"
  _quelle: 'S. Veit Mail 30.05 Punkt 4',
  _typ: 'fachexperte'
})

CREATE (:NutzungsMapping {
  id: 'NM_TECHNIKRAUM',
  nutzung: 'Technikräume/NSHV/Trafo',
  kategorie: 6,  // Veit: Kat 6 (NEU! nicht in Kalkulationshilfen)
  _quelle: 'S. Veit Mail 30.05 Punkt 4',
  _typ: 'fachexperte'
})
```

**Implementierung:** User gibt Mix% → per Anteil gewichteter Kat-Preis:
`Gesamt = Σ(Anteil_i × Fläche × €/m²_Kat_i)`

---

### A4 — Chat Prompt Fix

**Was:** Nicht nach UV/Messstellen fragen, sondern Branchenfrage stellen

**Datenquelle:** Kein Graph — Prompt-Änderung in `products/dguv_v3/chat.py`

**Änderung:**
```
ALT: "Minimum für Kalkulation: nutzung + anzahl_ableitungen"
NEU: "Minimum für Kalkulation: nutzung + gesamtflaeche_m2 (oder Kundenmerkmal das in Fläche umgerechnet wird)"
```

---

## B. PRICING-LOGIK

### B1+B2 — Fläche × €/m² per Kategorie (kalibriert)

**Was:** Core Pricing Formula

**Datenquelle:** Kalkulationshilfen NBG Sheet "Ortsfest DGUV" + "Hilfstabellen"

**Graph:**
```cypher
// EXISTIERT bereits — €/m² Werte KORRIGIEREN:
MATCH (k:Installationskategorie {id: 'KAT_1'}) SET k.preis_pro_10m2 = 1.00, k._quelle = 'Kalkulationshilfen NBG / Hilfstabellen / 2026'
MATCH (k:Installationskategorie {id: 'KAT_2'}) SET k.preis_pro_10m2 = 3.10, k._quelle = 'Kalkulationshilfen NBG / Hilfstabellen / 2026'
MATCH (k:Installationskategorie {id: 'KAT_3'}) SET k.preis_pro_10m2 = 5.00, k._quelle = 'Kalkulationshilfen NBG / Hilfstabellen / 2026'
MATCH (k:Installationskategorie {id: 'KAT_4'}) SET k.preis_pro_10m2 = 5.40, k._quelle = 'Kalkulationshilfen NBG / Hilfstabellen / 2026'
```

**ACHTUNG:** Code hat aktuell KAT_1=1€, KAT_2=2€, KAT_3=1.5€, KAT_4=3€. Muss auf NBG-Werte kalibriert werden!

---

### B3 — Gebäudetyp → Kategorie Mapping

**Datenquelle:** Kalkulationshilfen NBG "Hilfstabellen" + Veit Mail Punkt 4

**Graph:**
```cypher
// Gebäudetyp-Nodes existieren — Edges zu Kategorie hinzufügen/korrigieren
MATCH (g:Gebaeudetyp {id: 'GT_SCHULE'}), (k:Installationskategorie {id: 'KAT_2'})
CREATE (g)-[:TYPISCHE_KATEGORIE {
  _quelle: 'Kalkulationshilfen NBG / Hilfstabellen / Zeile "Schulen"',
  _typ: 'regel'
}]->(k)

MATCH (g:Gebaeudetyp {id: 'GT_HOTEL'}), (k:Installationskategorie {id: 'KAT_2'})
CREATE (g)-[:TYPISCHE_KATEGORIE {
  _quelle: 'Kalkulationshilfen NBG / Hilfstabellen / Zeile "Gasträume"',
  _typ: 'regel'
}]->(k)

MATCH (g:Gebaeudetyp {id: 'GT_SUPERMARKT'}), (k:Installationskategorie {id: 'KAT_3'})
CREATE (g)-[:TYPISCHE_KATEGORIE {
  _quelle: 'Kalkulationshilfen NBG / Hilfstabellen / Zeile "Verkaufsräume"',
  _typ: 'regel'
}]->(k)
```

---

### B4 — Reifegrad-Modell

**Datenquelle:** S. Veit Mail 30.05 Punkt 7 (explizite Werte)

**Graph:**
```cypher
CREATE (:Reifegrad {id: 'RG_1', name: 'Ungeordneter Anlagenbetrieb', faktor: 1.25,
  beschreibung: 'Keine/rudimentäre Anlagendaten, erhöhter Abstimmungsaufwand',
  _quelle: 'S. Veit Mail 30.05 Punkt 7', _typ: 'fachexperte'})

CREATE (:Reifegrad {id: 'RG_2', name: 'Reaktiver Anlagenbetrieb', faktor: 1.25,
  beschreibung: 'Unterlagen teilweise vorhanden, Nachholbedarf',
  _quelle: 'S. Veit Mail 30.05 Punkt 7', _typ: 'fachexperte'})

CREATE (:Reifegrad {id: 'RG_3', name: 'Strukturierter Regelbetrieb', faktor: 1.0,
  beschreibung: 'Standardfall, 100% Basis',
  _quelle: 'S. Veit Mail 30.05 Punkt 7', _typ: 'fachexperte'})

CREATE (:Reifegrad {id: 'RG_4', name: 'Hochprofessioneller Betrieb', faktor: 0.80,
  beschreibung: 'Vollständige Doku, fristgerechte Prüfungen, -15-20%',
  _quelle: 'S. Veit Mail 30.05 Punkt 7', _typ: 'fachexperte'})
```

---

### B5 — Dokumentationsumfang

**Datenquelle:** S. Pausch Mail 29.05 + S. Veit Mail 30.05 Punkt 6

**Graph:**
```cypher
CREATE (:Dokumentationszuschlag {id: 'DOK_VOLL', name: 'Vollerfassung DGUV', faktor: 1.30,
  beschreibung: 'NUR bei DGUV, nicht VdS/Baurecht',
  messdaten_preis: 15.0,  // €/Punkt bei 100% Erfassung
  pruefung_preis: 8.50,   // €/Punkt bei nur-Prüfung
  _quelle: 'S. Pausch Mail 29.05 + S. Veit Mail 30.05 Punkt 6',
  _typ: 'fachexperte'})
```

---

### B6+B7+B8 — Referenzpreis-Logik

**Datenquelle:** S. Veit Mail 30.05 Punkt 9 (explizite Steigerungstabelle)

**Graph:**
```cypher
CREATE (:Preissteigerung {id: 'PS_2020', jahr: 2020, steigerung_vs_2026: 0.282, _quelle: 'S. Veit Mail 30.05 Punkt 9', _typ: 'fachexperte'})
CREATE (:Preissteigerung {id: 'PS_2021', jahr: 2021, steigerung_vs_2026: 0.244, _quelle: 'S. Veit Mail 30.05 Punkt 9', _typ: 'fachexperte'})
CREATE (:Preissteigerung {id: 'PS_2022', jahr: 2022, steigerung_vs_2026: 0.208, _quelle: 'S. Veit Mail 30.05 Punkt 9', _typ: 'fachexperte'})
CREATE (:Preissteigerung {id: 'PS_2023', jahr: 2023, steigerung_vs_2026: 0.148, _quelle: 'S. Veit Mail 30.05 Punkt 9', _typ: 'fachexperte'})
CREATE (:Preissteigerung {id: 'PS_2024', jahr: 2024, steigerung_vs_2026: 0.083, _quelle: 'S. Veit Mail 30.05 Punkt 9', _typ: 'fachexperte'})
CREATE (:Preissteigerung {id: 'PS_2025', jahr: 2025, steigerung_vs_2026: 0.055, _quelle: 'S. Veit Mail 30.05 Punkt 9', _typ: 'fachexperte'})

CREATE (:Warnregel {id: 'WARN_REFERENZ', schwelle_prozent: 20,
  text: 'Neukalkulation weicht >20% vom fortgeschriebenen Referenzpreis ab — fachliche Plausibilisierung empfohlen',
  _quelle: 'S. Veit Mail 30.05 Punkt 9', _typ: 'fachexperte'})
```

**Implementierung:**
1. User input: "Letzte Prüfung 2023 für 4.200€"
2. Query PS_2023 → Steigerung 14,8%
3. Referenzpreis = 4.200 × 1.148 = 4.822€
4. Neukalkulation = X€
5. Abweichung = (X - 4.822) / 4.822 × 100
6. Wenn >20% → WARN_REFERENZ anzeigen

---

## C. DATENQUELLEN & KONSOLIDIERUNG

### C1 — Kalkulationshilfen NBG laden

**Datei:** `input-files/02_Kalkulationstools/NBG_Kalkulationshilfen_Angebote_v2.xlsx`
**Sheets:** "Ortsfest DGUV", "Ortsfest VdS_DIN", "DGUV Ortsveränd", "Hilfstabellen"

**Graph:** Alle Installationskategorien + Preise + Nutzung→Kat Mappings
**Provenance:** Jeder Node bekommt `_quelle: 'Kalkulationshilfen NBG / Sheet X / Zeile Y'`

---

### C2 — Similar-Case Lookup

**Datei:** `input-files/03_Ausschreibungen/Gersthofen_DGUV_V3_2025.xlsm` (bereits geladen als Golden Set)

**Graph:**
```cypher
CREATE (:Referenzobjekt {
  id: 'REF_GERSTHOFEN_01',
  name: 'Rathaus Gersthofen',
  gebaeudetyp: 'Verwaltungsgebäude',
  ort: 'Gersthofen',
  plz: '86368',
  anzahl_uv: 24,
  gesamtpreis: 7996.00,
  _quelle: 'Ausschreibung Gersthofen 2025 / Position 01',
  _typ: 'ausschreibung'
})

CREATE (:Referenzobjekt {
  id: 'REF_GERSTHOFEN_03',
  name: 'Pestalozzischule',
  gebaeudetyp: 'Schule',
  ort: 'Gersthofen',
  plz: '86368',
  gesamtpreis: 3992.80,
  _quelle: 'Ausschreibung Gersthofen 2025 / Position 03',
  _typ: 'ausschreibung'
})
// ... für alle 40 Gebäude
```

**Query bei Kalkulation:**
```cypher
MATCH (r:Referenzobjekt)
WHERE r.gebaeudetyp = $gebaeudetyp
RETURN r.name, r.gesamtpreis, r.ort
ORDER BY ABS(r.gesamtpreis - $kalkulierter_preis) LIMIT 3
```

---

## E. OUTPUT

### E1 — Confidence-Anzeige

**Logik:**
- Basis: 100%
- Kein Reifegrad angegeben: -10%
- Keine Referenzobjekte gefunden: -15%
- Fläche geschätzt (aus Zimmer/Betten): -10%
- Mix-Nutzung ohne Prozentangabe: -15%
- Referenzpreis vorhanden und <20% Abweichung: +10%

**Graph:** Confidence-Regeln als Nodes mit Penalty/Bonus-Werten

---

## GRAPH-ÜBERSICHT: Neue Nodes für DGUV V3

| Node-Typ | Anzahl | Quelle | _typ |
|---|---|---|---|
| Installationskategorie | 5 (KORRIGIERT) | Kalkulationshilfen NBG | regel |
| NutzungsMapping | ~15 | Kalkulationshilfen + Veit Mail | regel + fachexperte |
| Branchenfrage | ~8 | Veit Mail Punkt 2 | fachexperte |
| Umrechnungsregel | ~8 | Branchenwissen | llm_augmentiert |
| Reifegrad | 4 | Veit Mail Punkt 7 | fachexperte |
| Dokumentationszuschlag | 2 | Pausch + Veit Mail | fachexperte |
| Preissteigerung | 6 | Veit Mail Punkt 9 | fachexperte |
| Warnregel | 2 | Veit Mail Punkt 9 | fachexperte |
| Referenzobjekt (Gersthofen) | 40 | Ausschreibung Gersthofen | ausschreibung |
| Referenzobjekt (Audi) | ~35 | Ausschreibung Audi | ausschreibung |
| Gebaeudetyp | 8 (EXISTIERT) | — | — |
| Verteilung | 3 (EXISTIERT) | — | — |
| Standort | 23 (EXISTIERT) | — | — |

**Total: ~145 existierend + ~120 neu = ~265 Nodes**

---

## DEMO-FLOW (Ziel)

```
User: "Verwaltungsgebäude, 5.000m², davon 60% Büro, 30% Lager, 10% Technik.
       Reifegrad 3. Keine Vollerfassung. Letzte Prüfung 2023 für 4.200€. PLZ 86368."

System (Graph-basiert):

1. NUTZUNGSMAPPING query:
   Büro→Kat2 (0,31€/m²) [_quelle: Kalkulationshilfen NBG]
   Lager→Kat1 (0,10€/m²) [_quelle: Kalkulationshilfen NBG]
   Technik→Kat4 (0,54€/m²) [_quelle: S. Veit Mail / Kat 6 noch nicht in LPV]

2. PRÜFKOSTEN berechnen:
   3.000m² × 0,31 = 930€ (Büro)
   1.500m² × 0,10 = 150€ (Lager)
   500m² × 0,54 = 270€ (Technik)
   = 1.350€ Prüfkosten

3. GRUNDKOSTEN hinzufügen:
   250€ Grundpreis + 242€ Ordnungsprüfung + 49€ Prüfmittel + 380€ Bericht
   = 921€ [_quelle: LPV B04]

4. REISEKOSTEN:
   PLZ 86368 → NL Augsburg → 15km → 1,10€/km × 30km (hin+zurück) = 33€
   + Reisezeit 0,5h × 180€ = 90€
   = 123€ [_quelle: PLZ-CRM-Mapping + LPV]

5. REIFEGRAD:
   Rg3 = ×1.0 [_quelle: S. Veit Mail Punkt 7]

6. DOKUMENTATION:
   Keine Vollerfassung = ×1.0

7. GESAMTPREIS:
   (1.350 + 921 + 123) × 1.0 × 1.0 = 2.394€

8. REFERENZPREIS:
   4.200€ (2023) × 1.148 = 4.822€ [_quelle: S. Veit Steigerungstabelle]
   Abweichung: -50% → ⚠ WARNUNG

9. SIMILAR-CASE:
   Rathaus Gersthofen (Verwaltung, 24 UV) = 7.996€ [_quelle: Ausschreibung Gersthofen]
   → Größere Anlage, höherer Preis plausibel

10. CONFIDENCE: 75%
    - Reifegrad angegeben ✓
    - Referenzpreis vorhanden ✓ aber >20% Abweichung ⚠
    - Mix-Nutzung mit % ✓
    - Fläche direkt angegeben ✓

OUTPUT:
  Geschätzter Preis: 2.394€
  Referenzpreis (2023→2026): 4.822€
  ⚠ Abweichung: -50% — Prüfumfang geändert? Bitte plausibilisieren.
  Ähnlich: Rathaus Gersthofen 7.996€ (größere Anlage)
  Confidence: 75%
  [Aufschlüsselung: Prüf 1.350€ + Grund 921€ + Reise 123€]
```
