# SmartCal@EG — PRD: DGUV V3 ortsfest (MA507)

**Version:** 2.1
**Stand:** 30.05.2026
**Testrunde:** 08.06.2026
**Quellen:** S. Veit Mail 30.05, S. Pausch Mail 29.05, Call 29.05, Call 28.05

---

## 1. Ziel

Auf der Testrunde am 08.06.2026 zeigen wir den kompletten Kalkulationsflow für DGUV V3 ortsfeste elektrische Anlagen (MA507):

**User gibt einfache, kundenverständliche Angaben → System kalkuliert merkmalsbasiert → nachvollziehbarer Preisvorschlag mit Referenzpreis-Vergleich und Confidence-Anzeige.**

Kein technisches Detailwissen nötig (keine Verteilungen, keine Stromkreise, keine RCDs).

---

## 2. User Flow (Veit Punkt 8)

```
┌─────────────────────────────────────────────────────────┐
│ 1. Prüfart wählen                                       │
│    → DGUV V3 ortsfest (MA507)                           │
├─────────────────────────────────────────────────────────┤
│ 2. Gebäudetyp + Größe                                   │
│    → Branchenspezifische Frage (Hotel→Zimmer, etc.)     │
│    → Nutzungs-Mix wenn Mischnutzung                     │
├─────────────────────────────────────────────────────────┤
│ 3. Branchenspezifische Preislisten prüfen               │
│    → Gersthofen/Audi Match? → Vergleichspreis zeigen    │
├─────────────────────────────────────────────────────────┤
│ 4. Fläche × Installationskategorie kalkulieren          │
│    → Gewichteter Mix wenn Mischnutzung                  │
├─────────────────────────────────────────────────────────┤
│ 5. Dokumentationsumfang + Reifegrad                     │
│    → Vollerfassung? → +30%                              │
│    → Reifegrad 1-4 → ×0.80 bis ×1.25                   │
├─────────────────────────────────────────────────────────┤
│ 6. Referenzpreis-Vergleich                              │
│    → Alter TÜV-Preis × Steigerung vs. Neukalkulation   │
│    → Warnung wenn >20% Abweichung                       │
├─────────────────────────────────────────────────────────┤
│ 7. Output                                               │
│    → Preis mit Aufschlüsselung                          │
│    → Confidence %                                       │
│    → Ähnliche Objekte aus Ausschreibungen               │
│    → Referenzpreis-Vergleich                             │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Requirements

### 3.1 Flow & Interaktion

#### R-A1: Kundenperspektive-Fragen per Branche
**Quelle:** S. Veit Mail 30.05 Punkt 2
**Prio:** MUST

System fragt per Gebäudetyp die richtige kundenverständliche Frage:

| Gebäudetyp | Frage | Zusatzfragen |
|---|---|---|
| Hotel | Wie viele Zimmer? | Restaurant? Spa/Wellness? Konferenz? |
| Krankenhaus | Wie viele Betten? | OP-Bereich? Intensivstation? |
| Schule | Wie viele Klassenräume? | Turnhalle? Werkräume? |
| Tiefgarage | Wie viele Stellplätze? | — |
| Supermarkt | Wie groß ist die Verkaufsfläche? | Frischetheke? Bäckerei? |
| Industrie/Logistik | Anteil Verwaltung/Produktion/Logistik/Technik in % | — |
| Verwaltungsgebäude | Bürofläche in m²? | Kantine? Rechenzentrum? Tiefgarage? |
| Möbelhaus/Gartenmarkt | Verkaufs-/Lager-/Außenfläche? | — |

**NICHT fragen:** Verteilungen, Stromkreise, RCDs, technische Details.

**Graph:**
```cypher
(:Branchenfrage {id, gebaeudetyp, frage, zusatzfragen[],
  _quelle: 'S. Veit Mail 30.05', _typ: 'fachexperte'})
```

**E2E Tests:**
- `test_e2e_hotel_fragt_nach_zimmern` — Input "Hotel München" → System fragt "Wie viele Zimmer?" nicht "Wie viele UV?"
- `test_e2e_industrie_fragt_nach_mix` — Input "Industriegebäude" → System fragt nach % Verwaltung/Produktion/Logistik
- `test_e2e_schule_fragt_nach_klassenraeumen` — Input "Schule" → "Wie viele Klassenräume?"
- `test_e2e_tiefgarage_fragt_nach_stellplaetzen` — Input "Tiefgarage" → "Wie viele Stellplätze?"
- `test_e2e_verwaltung_fragt_nach_flaeche` — Input "Bürogebäude" → akzeptiert m² direkt

---

#### R-A2: Umrechnung Kundenmerkmal → m²
**Quelle:** S. Veit Mail 30.05 Punkt 2
**Prio:** MUST

| Kundenmerkmal | Umrechnung | Varianz | Quelle |
|---|---|---|---|
| Hotelzimmer | ×30 m² | 25-45 je nach Klasse | Branchenwissen (llm_augmentiert) |
| Krankenhausbetten | ×50 m² | 40-70 | Branchenwissen |
| Klassenräume | ×70 m² | 60-80 | Branchenwissen |
| Stellplätze | ×25 m² | 20-30 | Branchenwissen |
| Mitarbeiter (Büro) | ×15 m² | 10-20 | Branchenwissen |
| Sitzplätze (Versamml.) | ×3 m² | 2-5 | Branchenwissen |

**Graph:**
```cypher
(:Umrechnungsregel {id, gebaeudetyp, kundenmerkmal, faktor_m2, varianz,
  _quelle: 'Branchenwissen', _typ: 'llm_augmentiert', _validiert_durch: null})
```

**E2E Tests:**
- `test_e2e_hotel_120_zimmer_to_3600m2` — 120 Zimmer → 3.600 m² → Kat 2 → Preis
- `test_e2e_krankenhaus_200_betten_to_10000m2` — 200 Betten → 10.000 m² → Preis
- `test_e2e_user_gibt_m2_direkt` — "Schule, 3.000m²" → keine Umrechnung nötig

---

#### R-A3: Nutzungs-Mix
**Quelle:** S. Pausch Mail 29.05, S. Veit Mail 30.05 Punkt 4
**Prio:** MUST

User gibt: "30% Büro, 50% Logistik, 20% Produktion" → System berechnet gewichteten Preis.

| Nutzung | Installationskategorie | €/m² (2026) | Quelle |
|---|---|---|---|
| Wohngebäude, Freiflächen, Allgemeinbereiche | 1 | 0,10 | Kalkulationshilfen NBG |
| Büro, Schule, Restaurant, Lager, Krankenhaus AG0, Altenheim, Werkstätten | 2 | 0,31 | Kalkulationshilfen NBG |
| Supermarkt, Produktion (einfach), Museum, EDV, Großdruckerei, Versammlungsräume | 3 | 0,50 | Kalkulationshilfen NBG |
| Technikräume, Reinraum | 4 | 0,54 | Kalkulationshilfen NBG |
| Sonder (OP, Labor) | 5 | TBD | Code hat 5€/10m² |
| Technikräume, NSHV, Trafo, Batterieladestation | 6 | TBD | S. Veit Mail (NEU!) |

**Formel:** `Prüfkosten = Σ(Anteil_i × Gesamtfläche × €/m²_Kat_i)`

**ACHTUNG:** Veit definiert Kat 6 — nicht in Kalkulationshilfen. Preis klären mit Pausch.

**Graph:**
```cypher
(:NutzungsMapping {id, nutzung, kategorie,
  _quelle: 'Kalkulationshilfen NBG / Hilfstabellen', _typ: 'regel'})

// Spezialfall Veit Kat 6:
(:NutzungsMapping {id: 'NM_TECHNIK',
  nutzung: 'Technikräume/NSHV/Trafo',
  kategorie: 6,
  _quelle: 'S. Veit Mail 30.05 Punkt 4', _typ: 'fachexperte'})
```

**E2E Tests:**
- `test_e2e_mischnutzung_30_50_20` — 5.000m², 30% Büro + 50% Logistik + 20% Produktion → gewichteter Preis
- `test_e2e_reine_nutzung_schule` — 3.000m² Schule → 100% Kat 2
- `test_e2e_mischnutzung_mit_technik_kat6` — Anteil Technikräume → Kat 6 Preis

---

#### R-A4: Chat Prompt Fix
**Quelle:** Alle Calls + S. Veit Mail Intro
**Prio:** MUST

Änderung in `products/dguv_v3/chat.py`:

```
ALT: "Minimum für Kalkulation: nutzung + anzahl_ableitungen"
NEU: "Minimum für Kalkulation: nutzung + gesamtflaeche_m2
      (oder Kundenmerkmal das in Fläche umgerechnet wird).
      NICHT nach Verteilungen, Stromkreisen oder RCDs fragen.
      Stattdessen Branchenfrage aus Graph stellen."
```

**E2E Tests:**
- `test_e2e_system_fragt_nicht_nach_uv` — "Hotel München" → Antwort enthält NICHT "Unterverteilung" oder "Stromkreis"
- `test_e2e_system_kalkuliert_ohne_technische_details` — "Schule, 3.000m²" → sofort Preis, keine Rückfrage nach UV

---

#### R-A5: Alternative Größenermittlung
**Quelle:** S. Veit Mail 30.05 Punkt 2
**Prio:** NICE

Wenn User m² nicht kennt: Länge × Breite × Etagen = m²

**E2E Test:**
- `test_e2e_laenge_breite_etagen` — "40m lang, 20m breit, 3 Stockwerke" → 2.400m² → Preis

---

### 3.2 Pricing-Logik

#### R-B1+B2: Fläche × €/m² per Installationskategorie
**Quelle:** Kalkulationshilfen NBG, LPV B04 Kap. 2
**Prio:** MUST (KALIBRIERUNG)

**Datei:** `input-files/02_Kalkulationstools/NBG_Kalkulationshilfen_Angebote_v2.xlsx`
**Sheet:** "Ortsfest DGUV" + "Hilfstabellen"

Code hat aktuell FALSCHE Werte:
| Kat | Code aktuell | NBG korrekt |
|---|---|---|
| 1 | 1,00 €/10m² | 1,00 €/10m² ✓ |
| 2 | 2,00 €/10m² | **3,10 €/10m²** ✗ |
| 3 | 1,50 €/10m² | **5,00 €/10m²** ✗ |
| 4 | 3,00 €/10m² | **5,40 €/10m²** ✗ |
| 5 | 5,00 €/10m² | TBD |

**E2E Tests:**
- `test_e2e_kat2_preis_korrekt` — Büro 1.000m² → 1.000/10 × 3,10 = 310€ Prüfkosten
- `test_e2e_kat3_preis_korrekt` — Supermarkt 2.000m² → 2.000/10 × 5,00 = 1.000€
- `test_e2e_preise_steigen_mit_kategorie` — Kat1 < Kat2 < Kat3 < Kat4

---

#### R-B4: Reifegrad-Modell
**Quelle:** S. Veit Mail 30.05 Punkt 7
**Prio:** MUST

| Reifegrad | Name | Faktor | Beschreibung |
|---|---|---|---|
| 1 | Ungeordneter Anlagenbetrieb | ×1,25 | Keine Daten, erhöhter Aufwand |
| 2 | Reaktiver Anlagenbetrieb | ×1,25 | Teilweise Unterlagen, Nachholbedarf |
| 3 | Strukturierter Regelbetrieb | ×1,00 | Standardfall = 100% Basis |
| 4 | Hochprofessioneller Betrieb | ×0,80 | Alles vorhanden, -15-20% |

Default: Rg3 wenn nicht angegeben.

**Graph:**
```cypher
(:Reifegrad {id: 'RG_3', name: 'Strukturierter Regelbetrieb', faktor: 1.0,
  _quelle: 'S. Veit Mail 30.05 Punkt 7', _typ: 'fachexperte'})
```

**E2E Tests:**
- `test_e2e_reifegrad_1_teurer` — Rg1 Preis > Rg3 Preis (×1,25)
- `test_e2e_reifegrad_4_billiger` — Rg4 Preis < Rg3 Preis (×0,80)
- `test_e2e_reifegrad_default_3` — Kein Reifegrad → ×1,0

---

#### R-B5: Dokumentationsumfang
**Quelle:** S. Pausch Mail 29.05 + S. Veit Mail 30.05 Punkt 6
**Prio:** MUST

| Option | Faktor | Gilt für |
|---|---|---|
| Standard (nur bei Abweichung) | ×1,0 | Alle |
| Vollerfassung Messdaten | ×1,30 | NUR DGUV |
| 100% Inventarisierung | ×1,30 | NUR DGUV |

Messdatenerfassung Preise:
- Mit Vollerfassung: ~15€/Prüfpunkt
- Ohne (nur Prüfung): ~8,50-9€/Prüfpunkt

**Graph:**
```cypher
(:Dokumentationszuschlag {id: 'DOK_VOLL', name: 'Vollerfassung',
  faktor: 1.30, nur_dguv: true,
  _quelle: 'S. Pausch Mail 29.05', _typ: 'fachexperte'})
```

**E2E Tests:**
- `test_e2e_vollerfassung_30_prozent_zuschlag` — Vollerfassung → Preis ×1,30
- `test_e2e_standard_dokumentation_kein_zuschlag` — Standard → ×1,0
- `test_e2e_vollerfassung_nur_dguv_nicht_vds` — VdS + Vollerfassung → kein Zuschlag

---

#### R-B6+B7+B8: Referenzpreis-Logik
**Quelle:** S. Veit Mail 30.05 Punkt 9
**Prio:** MUST

**Abfrage bei Bestandskunden:**
1. Wurde die Anlage bereits durch TÜV SÜD geprüft?
2. In welchem Jahr?
3. Zu welchem Preis?
4. War der Prüfumfang vergleichbar?
5. Gab es seitdem Änderungen (Nutzung, Fläche, Ladesäulen, PV)?

**Preissteigerungstabelle:**

| Jahr | Steigerung ggü. 2026 |
|---|---|
| 2025 | +5,5% |
| 2024 | +8,3% |
| 2023 | +14,8% |
| 2022 | +20,8% |
| 2021 | +24,4% |
| 2020 | +28,2% |

**Formel:** `Referenzpreis_2026 = alter_Preis × (1 + Steigerung)`

**Warnregel:** Wenn |Neukalkulation - Referenzpreis| / Referenzpreis > 20% → Warnung anzeigen.

**Output:**
- Referenzpreis (fortgeschrieben): X€
- Neukalkulation: Y€
- Abweichung: Z% → ggf. ⚠ Warnung

**Graph:**
```cypher
(:Preissteigerung {id: 'PS_2023', jahr: 2023, steigerung: 0.148,
  _quelle: 'S. Veit Mail 30.05 Punkt 9', _typ: 'fachexperte'})

(:Warnregel {id: 'WARN_REF', schwelle_prozent: 20,
  text: 'Neukalkulation weicht >20% vom Referenzpreis ab',
  _quelle: 'S. Veit Mail 30.05 Punkt 9', _typ: 'fachexperte'})
```

**E2E Tests:**
- `test_e2e_referenzpreis_2023_fortschreibung` — 4.200€ (2023) × 1,148 = 4.822€
- `test_e2e_referenzpreis_2020_fortschreibung` — 3.000€ (2020) × 1,282 = 3.846€
- `test_e2e_referenzpreis_warnung_bei_abweichung` — Wenn Neukalk 2.400€ vs. Referenz 4.822€ → ⚠ "-50%"
- `test_e2e_referenzpreis_keine_warnung` — Wenn Neukalk 4.500€ vs. Referenz 4.822€ → OK (-7%)
- `test_e2e_kein_referenzpreis_kein_fehler` — Kein alter Preis → Referenzpreis-Block wird nicht angezeigt

---

### 3.3 Datenquellen & Konsolidierung

#### R-C1: Kalkulationshilfen NBG laden
**Datei:** `input-files/02_Kalkulationstools/NBG_Kalkulationshilfen_Angebote_v2.xlsx`
**Sheets:** "Ortsfest DGUV", "Ortsfest VdS_DIN", "Hilfstabellen"
**Prio:** MUST

Laden in Graph als:
- Installationskategorie-Nodes (5) mit korrekten €/m²
- NutzungsMapping-Nodes (~15) mit Nutzung→Kat Zuordnung
- Alle mit `_quelle: 'Kalkulationshilfen NBG / Sheet X / Zeile Y'`

**E2E Tests:**
- `test_e2e_kalkulationshilfen_geladen` — Graph enthält 5 Installationskategorien mit NBG-Preisen
- `test_e2e_nutzungsmapping_vollstaendig` — Alle 15+ Nutzungen gemappt

---

#### R-C2: Similar-Case Lookup
**Dateien:**
- `input-files/03_Ausschreibungen/Gersthofen_DGUV_V3_2025.xlsm` (40 Gebäude)
- `input-files/03_Ausschreibungen/Audi_059E_DGUV_V3_2025.xlsm` (~35 Gebäude)
**Prio:** MUST

Laden als Referenzobjekt-Nodes mit Gebäudetyp + Preis.

Bei Kalkulation: Query nach ähnlichen Objekten → "Ähnliche Schulen: Pestalozzischule 3.993€"

**Graph:**
```cypher
(:Referenzobjekt {id, name, gebaeudetyp, ort, plz, gesamtpreis, anzahl_uv,
  _quelle: 'Ausschreibung Gersthofen 2025 / Position 03', _typ: 'ausschreibung'})
```

**E2E Tests:**
- `test_e2e_similar_case_schule` — "Schule" → findet Pestalozzischule + Mozartschule
- `test_e2e_similar_case_verwaltung` — "Verwaltungsgebäude" → findet Rathaus Gersthofen
- `test_e2e_similar_case_kein_match` — "Schwimmbad" → keine ähnlichen Objekte, kein Fehler

---

### 3.4 Produkte

#### R-D1: DGUV V3 ortsfest (MA507)
**Prio:** MUST — Core des PoC

= Summe aller A+B+C Requirements.

---

#### R-D2: Blitzschutz (MA570)
**Prio:** MUST — 95% fertig
**Datei:** `input-files/06_Pruefberichte_Extrakte/Gebaeudedaten_MA570_alle_PDFs_v4.xlsx`

100 Anlagen mit Nutzung + Bauart + Umfang + Ableitungen + Angebotspreise + Rechnungspreise.
Gebäudeumfang → Ableitungen → 33€/Messstelle → Preis.

Fixes:
- Gebaeudedaten_MA570 Excel laden als Referenzobjekte
- Dachform als optionales Merkmal (Pausch 29.05)

**E2E Tests:**
- `test_e2e_blitz_buero_100m_umfang` — 100m Umfang → ~14 Messstellen → ~462€ Prüfkosten
- `test_e2e_blitz_schule_grosser_umfang` — 370m Umfang → ~31 Messstellen → ~1.023€
- `test_e2e_blitz_referenz_polizei_muenchen` — Vergleich mit Polizeipräsidium München 627€

---

### 3.5 Output & Darstellung

#### R-E1: Confidence-Anzeige
**Quelle:** S. Pausch 28.05
**Prio:** MUST

| Bedingung | Penalty/Bonus |
|---|---|
| Fläche direkt angegeben | +0% (Basis) |
| Fläche aus Kundenmerkmal geschätzt | -10% |
| Reifegrad angegeben | +0% |
| Reifegrad nicht angegeben | -10% |
| Referenzobjekte gefunden (≥2) | +5% |
| Keine Referenzobjekte | -15% |
| Mix-Nutzung mit % angegeben | +0% |
| Mix-Nutzung ohne % | -15% |
| Referenzpreis vorhanden und <20% Abweichung | +10% |
| Referenzpreis vorhanden und >20% Abweichung | -5% |

**E2E Tests:**
- `test_e2e_confidence_hoch_alle_angaben` — Fläche + Reifegrad + Referenz + Similar → 85%+
- `test_e2e_confidence_niedrig_nur_typ` — Nur "Hotel" ohne Zimmer/m² → 50-60%
- `test_e2e_confidence_mittel` — Zimmer geschätzt + kein Referenzpreis → 65-70%

---

#### R-E2: Nachvollziehbarer Preisvorschlag
**Quelle:** S. Veit Mail 30.05 Punkt 8
**Prio:** MUST

Output zeigt:

```
Geschätzter Preis: 2.394€

Aufschlüsselung:
  Prüfkosten:    1.350€  [Büro 930€ + Lager 150€ + Technik 270€]
  Grundkosten:     921€  [Grundpreis 250€ + Ordnungsprüfung 242€ + Prüfmittel 49€ + Bericht 380€]
  Reisekosten:     123€  [15km × 1,10€ × 2 + 0,5h × 180€]
  Reifegrad:       ×1,0  [Strukturierter Regelbetrieb]
  Dokumentation:   ×1,0  [Standard]

Referenzpreis (2023→2026): 4.822€
⚠ Abweichung: -50% — Prüfumfang geändert?

Ähnlich: Rathaus Gersthofen 7.996€ | Ballonmuseum 3.627€

Confidence: 75%
```

**E2E Tests:**
- `test_e2e_output_hat_aufschluesselung` — Prüf + Grund + Reise einzeln
- `test_e2e_output_hat_referenzpreis` — Wenn alter Preis angegeben → Vergleich
- `test_e2e_output_hat_similar_cases` — Wenn Matches → anzeigen
- `test_e2e_output_hat_confidence` — Immer Confidence %

---

#### R-E3: Referenzpreis vs. Neukalkulation
**Quelle:** S. Veit Mail 30.05 Punkt 9
**Prio:** MUST

Teil von Output (s. E2). Transparent: alter Preis, Steigerung, Neukalkulation, Abweichung, Warnung.

---

### 3.6 Infrastruktur

#### R-F1: Reisekosten / PLZ-Mapping
**Status:** ✓ EXISTIERT
**Datei:** `input-files/07_Sonstiges/CRM_PLZ_NL_Zuordnung.xlsx`

8.309 PLZ → 24 NL. OSRM Routing. Funktioniert.

---

## 4. Graph Provenance

### 4.1 Metadata per Node/Edge

```cypher
{
  _quelle: 'Kalkulationshilfen NBG / Hilfstabellen / 2026',
  _stand: '2026-05-29',
  _typ: 'regel',           // regel | statistik | llm_augmentiert | fachexperte | ausschreibung | versand
  _validiert_durch: 'K. Eiden (IS-EG-NBG)'
}
```

### 4.2 Provenance-Typen

| Typ | Bedeutung | Vertrauensstufe | Beispiel |
|---|---|---|---|
| `regel` | Aus LPV / Kalkulationshilfen | Höchste | €/m² per Kategorie |
| `ausschreibung` | Aus Gersthofen / Audi LV | Hoch | Pestalozzischule 3.993€ |
| `versand` | Reale Faktura aus SAP | Hoch | Versand-Preise |
| `fachexperte` | Von S. Veit / S. Pausch vorgegeben | Hoch | Reifegrad ×1,25 |
| `statistik` | Aus Prüfberichten extrahiert | Mittel | "Schule typisch 1-2 Prüftage" |
| `llm_augmentiert` | Branchenwissen via KI | Niedrigste | Zimmer ×30 = m² |

### 4.3 Neue Node-Typen

| Typ | Anzahl | Quelle |
|---|---|---|
| Branchenfrage | ~8 | S. Veit Mail |
| Umrechnungsregel | ~8 | LLM (zu validieren) |
| NutzungsMapping | ~15 | Kalkulationshilfen + Veit |
| Reifegrad | 4 | S. Veit Mail |
| Dokumentationszuschlag | 2 | Pausch + Veit |
| Preissteigerung | 6 | S. Veit Mail |
| Warnregel | 2 | S. Veit Mail |
| Referenzobjekt | ~75 | Gersthofen + Audi |
| **Σ Neue Nodes** | **~120** | |

---

## 5. Systemverhalten bei Unsicherheit und Konflikten

### 5.1 Precedence-Logik (Datenquellen-Rangfolge)

Wenn mehrere Quellen unterschiedliche Werte liefern, gilt:

```
regel (LPV/Kalkulationshilfen)
  > ausschreibung (Gersthofen/Audi)
    > fachexperte (Veit/Pausch)
      > versand (Faktura)
        > statistik (Prüfberichte)
          > llm_augmentiert (Branchenwissen)
```

Bei Konflikt: **beide Werte transparent anzeigen** mit Quelle.
Beispiel: Kalkulationshilfen sagt 2.400€, Gersthofen zeigt 3.993€ → zeige beides, nicht nur eins.

**E2E Tests:**
- `test_precedence_regel_vs_ausschreibung_zeigt_beide`
- `test_precedence_llm_nie_allein_bestimmend`

### 5.2 Guardrails für llm_augmentiert

LLM-basierte Umrechnungen (Zimmer→m²) haben Plausibilitätsgrenzen:

| Gebäudetyp | Min m² | Max m² | Quelle |
|---|---|---|---|
| Hotel | 500 | 50.000 | Plausibilität |
| Krankenhaus | 2.000 | 200.000 | Plausibilität |
| Schule | 500 | 30.000 | Plausibilität |
| Büro | 100 | 100.000 | Plausibilität |

Wenn Umrechnung außerhalb Range → **Warnung, nicht blind rechnen:**
*"Die geschätzte Fläche von 360.000 m² liegt außerhalb des erwarteten Bereichs für Hotels. Bitte Fläche direkt angeben."*

**E2E Tests:**
- `test_guardrail_hotel_12000_zimmer_warnung` — 12.000 Zimmer × 30 = 360.000m² → Warnung
- `test_guardrail_schule_2_klassenraeume_warnung` — 2 × 70 = 140m² → unter Min → Warnung
- `test_guardrail_innerhalb_range_keine_warnung` — 120 Zimmer = 3.600m² → OK

### 5.3 "Nicht kalkulierbar" Zustand

System muss erkennen wann es NICHT kalkulieren kann:

| Bedingung | Verhalten |
|---|---|
| Gebäudetyp unbekannt + keine Fläche + kein Referenzpreis | *"Für diese Anfrage kann keine belastbare Kalkulation erstellt werden. Bitte Gebäudetyp und Fläche angeben."* |
| Gebäudetyp = Exot (z.B. "JVA", "Atomkraftwerk") | *"Für diesen Gebäudetyp liegen uns keine Referenzdaten vor. Bitte Rücksprache mit Fachexperten."* |
| Confidence < 40% | Warnung: *"Geringe Datengrundlage — Ergebnis nur als grobe Indikation verwenden."* |

**NICHT raten.** Lieber ehrlich "nicht kalkulierbar" als falsche Sicherheit.

**E2E Tests:**
- `test_nicht_kalkulierbar_kein_input` — Leere Anfrage → Aufforderung
- `test_nicht_kalkulierbar_exot` — "Atomkraftwerk" → Fachexperte empfohlen
- `test_warnung_bei_niedriger_confidence` — Confidence < 40% → Warnung

### 5.4 Similar-Case Relevanz-Filter

Referenzobjekte nur zeigen wenn relevant:

| Regel | Warum |
|---|---|
| Gebäudetyp muss matchen | Rathaus ≠ Kindergarten |
| Preis in ±300% Range des kalkulierten Preises | Rathaus 7.996€ als "ähnlich" für Büro 500€ = irreführend |
| Maximal 3 Similar Cases | Nicht überfluten |
| Sortiert nach Preisähnlichkeit | Nächster Preis zuerst |

**E2E Tests:**
- `test_similar_case_nur_gleicher_gebaeudetyp` — Schule-Input → nur Schulen, keine Kindergärten
- `test_similar_case_max_3` — Nie mehr als 3 Ergebnisse
- `test_similar_case_preis_range` — Kalkuliert 2.000€ → zeigt nicht Rathaus 7.996€

### 5.5 Reifegrad-Scope

Reifegrad-Multiplikator gilt **NUR für DGUV V3 ortsfest (MA507)**.

| Produkt | Reifegrad anwendbar? | Begründung |
|---|---|---|
| DGUV V3 ortsfest (MA507) | ✓ Ja | Veit Mail Punkt 7 |
| Blitzschutz (MA570) | ✗ Nein | Pausch 29.05: "einfaches Material", EP/WP nimmt sich nix |

**E2E Tests:**
- `test_reifegrad_dguv_anwendbar` — DGUV + Rg4 → ×0.80
- `test_reifegrad_blitzschutz_ignoriert` — Blitzschutz + Rg4 → kein Abschlag

### 5.6 Numerische Stabilität

| Regel | Implementierung |
|---|---|
| Euro-Beträge | Auf 2 Dezimalstellen runden (kaufmännisch) |
| Mix-Summe ≠ 100% | Normalisieren: 30+50+30=110 → 27%+45%+27% |
| Identischer Input → identischer Output | Deterministisch, kein LLM-Zufall bei Kalkulation |
| Preissteigerung nur 2020-2025 | Jahr < 2020 oder > 2025 → *"Für dieses Jahr keine Steigerungsdaten vorhanden"* |

**E2E Tests:**
- `test_euro_rounding_2_dezimalen` — 930.333 → 930.33€
- `test_mix_normalisierung_110_prozent` — 30+50+30 → normalisiert auf 100%
- `test_identischer_input_identischer_output` — 2× gleiche Anfrage → exakt gleicher Preis
- `test_referenzpreis_jahr_2019_fehler` — Jahr 2019 → keine Steigerungsdaten
- `test_referenzpreis_jahr_2026_keine_steigerung` — Jahr 2026 → Faktor 0%

---

## 6. Datenquellen

| # | Datei | Pfad | Was wird geladen |
|---|---|---|---|
| 1 | Kalkulationshilfen NBG | `02_Kalkulationstools/NBG_*.xlsx` | €/m² per Kat, Nutzung→Kat Mapping |
| 2 | Gersthofen LV | `03_Ausschreibungen/Gersthofen_*.xlsm` | 40 Referenzobjekte mit Preisen |
| 3 | Audi LV | `03_Ausschreibungen/Audi_*.xlsm` | ~35 Referenzobjekte mit BGF |
| 4 | Gebaeudedaten MA570 | `06_Pruefberichte_Extrakte/Gebaeudedaten_MA570_v4.xlsx` | 100 Blitzschutz-Anlagen + Preise |
| 5 | PLZ-NL Mapping | `07_Sonstiges/CRM_PLZ_NL_Zuordnung.xlsx` | 8.309 PLZ → 24 NL |
| 6 | S. Veit Mail 30.05 | Memory | Reifegrad, Preissteigerung, Branchenfragen |
| 7 | S. Pausch Mail 29.05 | Memory | Dokumentation, Synergieeffekte |

---

## 7. Test-Suite

### 7.0 Graph Integrity Tests
```
test_graph_installationskategorien_5_nodes
test_graph_kat2_preis_3_10_nicht_2_00
test_graph_nutzungsmapping_schule_kat2
test_graph_nutzungsmapping_supermarkt_kat3
test_graph_nutzungsmapping_technik_kat6
test_graph_branchenfragen_8_nodes
test_graph_umrechnungsregeln_8_nodes
test_graph_reifegrade_4_nodes
test_graph_preissteigerung_6_nodes
test_graph_referenzobjekte_gersthofen_40
test_graph_referenzobjekte_audi_35
test_graph_provenance_jeder_node_hat_quelle
test_graph_provenance_jeder_node_hat_typ
test_graph_edges_gebaeudetyp_to_kategorie
test_graph_edges_produkt_to_kategorie
```

### 7.1 Flow-Tests (A)
```
test_e2e_hotel_fragt_nach_zimmern
test_e2e_industrie_fragt_nach_mix
test_e2e_schule_fragt_nach_klassenraeumen
test_e2e_tiefgarage_fragt_nach_stellplaetzen
test_e2e_verwaltung_fragt_nach_flaeche
test_e2e_system_fragt_nicht_nach_uv
test_e2e_system_kalkuliert_ohne_technische_details
test_e2e_hotel_120_zimmer_to_3600m2
test_e2e_krankenhaus_200_betten_to_10000m2
test_e2e_user_gibt_m2_direkt
test_e2e_mischnutzung_30_50_20
test_e2e_reine_nutzung_schule
test_e2e_mischnutzung_mit_technik_kat6
test_e2e_laenge_breite_etagen
```

### 7.2 Pricing-Tests (B)
```
test_e2e_kat2_preis_korrekt
test_e2e_kat3_preis_korrekt
test_e2e_preise_steigen_mit_kategorie
test_e2e_reifegrad_1_teurer
test_e2e_reifegrad_4_billiger
test_e2e_reifegrad_default_3
test_e2e_vollerfassung_30_prozent_zuschlag
test_e2e_standard_dokumentation_kein_zuschlag
test_e2e_referenzpreis_2023_fortschreibung
test_e2e_referenzpreis_2020_fortschreibung
test_e2e_referenzpreis_warnung_bei_abweichung
test_e2e_referenzpreis_keine_warnung
test_e2e_kein_referenzpreis_kein_fehler
```

### 7.3 Daten-Tests (C)
```
test_e2e_kalkulationshilfen_geladen
test_e2e_nutzungsmapping_vollstaendig
test_e2e_similar_case_schule
test_e2e_similar_case_verwaltung
test_e2e_similar_case_kein_match
```

### 7.4 Output-Tests (E)
```
test_e2e_output_hat_aufschluesselung
test_e2e_output_hat_referenzpreis
test_e2e_output_hat_similar_cases
test_e2e_output_hat_confidence
test_e2e_confidence_hoch_alle_angaben
test_e2e_confidence_niedrig_nur_typ
test_e2e_confidence_mittel
```

### 7.5 Blitzschutz-Tests (D2)
```
test_e2e_blitz_buero_100m_umfang
test_e2e_blitz_schule_grosser_umfang
test_e2e_blitz_referenz_polizei_muenchen
```

### 7.6 Demo-Szenarien (komplett)
```
test_e2e_demo_verwaltung_mischnutzung_mit_referenz
test_e2e_demo_hotel_kundenperspektive
test_e2e_demo_schule_simple_mit_similar_case
test_e2e_demo_blitzschutz_umfang
```

### 7.7 Precedence & Konflikt-Tests
```
test_precedence_regel_vs_ausschreibung_zeigt_beide
test_precedence_llm_nie_allein_bestimmend
```

### 7.8 Guardrail-Tests
```
test_guardrail_hotel_12000_zimmer_warnung
test_guardrail_schule_2_klassenraeume_warnung
test_guardrail_innerhalb_range_keine_warnung
```

### 7.9 "Nicht kalkulierbar" Tests
```
test_nicht_kalkulierbar_kein_input
test_nicht_kalkulierbar_exot
test_warnung_bei_niedriger_confidence
```

### 7.10 Similar-Case Relevanz-Tests
```
test_similar_case_nur_gleicher_gebaeudetyp
test_similar_case_max_3
test_similar_case_preis_range
```

### 7.11 Reifegrad-Scope Tests
```
test_reifegrad_dguv_anwendbar
test_reifegrad_blitzschutz_ignoriert
```

### 7.12 Numerische Stabilität Tests
```
test_euro_rounding_2_dezimalen
test_mix_normalisierung_110_prozent
test_identischer_input_identischer_output
test_referenzpreis_jahr_2019_fehler
test_referenzpreis_jahr_2026_keine_steigerung
```

### 7.13 Regression Tests
```
test_regression_blitzschutz_186_tests_pass
test_regression_reisekosten_plz_mapping
test_regression_grundkosten_berechnung
test_regression_zuschlaege_nicht_vereinsmitglied
test_regression_zuschlaege_eilzuschlag
```

**Total: 15 Graph + 41 E2E + 16 Guardrails/Edge + 5 Regression = 77 Tests**

---

## 8. Demo-Szenarien für 08.06.

### Szenario 1: Verwaltungsgebäude mit Mischnutzung + Referenzpreis
**Input:** "Verwaltungsgebäude, 5.000m², 60% Büro, 30% Lager, 10% Technik. Reifegrad 3. Keine Vollerfassung. Letzte Prüfung 2023 für 4.200€. PLZ 86368."
**Erwarteter Output:** ~2.394€, Referenz 4.822€, ⚠ -50% Warnung, Rathaus Gersthofen als Similar Case.

### Szenario 2: Hotel (Kundenperspektive)
**Input:** "Hotel, 120 Zimmer, Restaurant vorhanden, kein Spa. München."
**Erwarteter Output:** ~2.179€, Confidence 65% (Zimmer→m² Schätzung), System fragt NICHT nach Verteilungen.

### Szenario 3: Schule (Simple + Similar Case)
**Input:** "Schule, 3.000m², Heidelberg."
**Erwarteter Output:** ~2.001€, Similar Cases: Pestalozzischule 3.993€, Mozartschule 2.384€.

### Szenario 4: Blitzschutz
**Input:** "Bürogebäude, Würzburg, Gebäudeumfang ca. 100 Meter."
**Erwarteter Output:** ~1.433€ (Median 14 MS), Vergleich mit Polizeipräsidium München 627€.

---

## 9. Nicht im Scope (POST)

| Item | Warum nicht | Wann |
|---|---|---|
| MA560 ortsveränderlich | Eigenes Produkt | Nach Testrunde |
| MA505 VdS | PDFs erst jetzt uploadet | Nach Testrunde |
| MA510 Baurecht | Nur RPL/HH/NRW | Nach Testrunde |
| MA501 Freiwirtschaftlich | Kein Pricing Sheet | Nach Testrunde |
| Dehner/Poco/Motel One Preislisten | Nicht bei uns | MVP |
| Synergieeffekte DGUV+VdS | Braucht VdS-Logik | MVP |
| Ladesäulen/PV Detail | Stückpreise aus LPV | Nach Testrunde |
| TÜV Corporate Design | Niemand hat angefragt | MVP |
| Auth/Rollen/Session | MVP | MVP |
