# SmartCal@EG — Blitzschutz: Kompletny Plan

## 1. Źródła danych

### 1.1 LPV 2025/2026 (Teil B04, §8)
- **Äußerer Blitzschutz**: 33,00 €/Messstelle (oder Ableitung ohne Messstelle)
- **> 10 Messstellen**: besondere Vereinbarung möglich
- **Innerer Blitzschutz**: nach Angebot, Stundensatz 208 €/h
- **Stundensatz einfach**: 180 €/h (Reise, Aufwand)

### 1.2 LPV Teil A — Shared Kosten
- **Grundkosten**:
  - Pauschale Auftragsverwaltung, Prüfmittel, Nebenkosten: 256,00 €
  - Ordnungsprüfung Dokumente (nur baurechtlich): 242,00 €
  - Energie- und Prüfmittelpauschale: 49,00 €/Prüftag/SV
  - Tagegeld: 6 € (6–8h) / 25 € (8–14h) / 30 € (14–24h)
- **Berichterstellung**:
  - Kleine Anlagen: 119,00 €
  - Standard (≤ 10 Seiten): 380,00 €
  - Komplex: 550,00 €
  - Individuell: n.V.
- **Reisekosten**:
  - PKW: 1,10 €/km
  - LKW-Gerätewagen: 1,20 €/km
  - Reisezeit: Stundensatz 180 €/h
  - Bei koordinierter Reisedisposition: verringert
- **Stundensätze** (fallback bei Sonderfällen):
  - Einfach: 180 € | Schwierig: 208 € | Komplex: 239 € | Besonders: 265 €
- **Zuschläge**:
  - Einzelprüfung (ohne Rahmenvertrag): bis +20 % auf WP-Preise
  - Erstprüfung (vor Inbetriebnahme): bis +100 %
  - Sondertermine / Eilzuschlag: bis +25 % (oder bis +100 % bei bevorzugt)
  - Nicht-Vereinsmitglieder: bis +20 %
  - Erfolgloser Termin: anteiliger Preis + Reisekosten

### 1.3 Veit-Mail: 4 Kostenblöcke erklärt
- Reisekosten vom nächsten TÜV SÜD Standort (1,10 €/km + Reisezeit × Stundensatz)
- 20+ Standorte mit Adressen (Augsburg bis Würzburg)
- Grundkosten: 256 € + 49 €/Tag + Tagegeld
- Berichterstellung: 119/380/550 €

### 1.4 99 Prüfberichte Blitzschutz (Q1 2025, TÜV SÜD IS Nürnberg EG1-3)
- 91× MA570-WP (Wiederkehrende Prüfung)
- 7× MA570-PI (Prüfung nach Instandsetzung)
- 1× MA570-PM (Prüfung nach Montage)
- Felder pro Bericht: Standort, Betreiber, Nutzung, Bauart, Schutzklasse, Anzahl Ableitungen, Material, Messergebnisse (Ohm), Mängel (Einstufung 1-3), Prüfintervall

### 1.5 Augsburg-Realpreise (~200-300 Objekte, von Veit)
- Excel mit Realpreisen der letzten Prüfdurchführung
- Felder: Blitzschutzklasse, Anzahl Ableitungen, Gebäudetyp, Preis
- Alle ab Standort Augsburg, städtischer Umkreis
- Nutzung: Cross-Check LPV-Kalkulation vs. tatsächliche Marktpreise

### 1.6 Kalkulationstools (Excel, von Pausch/Veit)
- `Anlagenliste-LV-Preisblätter_WP Blitzschutz_StV.xlsx`
- `Preistool_EG1_MUC 2026_251121.xlsx`
- `Kalkulation_Arbeitskopie_2026.xlsm`
- Weitere: Arbeitsdateien, Kalkulationshilfen

---

## 2. Graph-Schema Blitzschutz

### 2.1 Knoten

```cypher
// Produkt
CREATE (:Produkt {
  id: "BLITZ_AUSSEN",
  name: "Prüfung Blitzschutzanlagen — Äußerer Blitzschutz",
  lpv_referenz: "B04 §8.1",
  einheit: "Messstelle",
  preis_pro_einheit: 33.00,
  schwelle_vereinbarung: 10,
  stundensatz_einfach: 180.00,
  maengel_quote: 0.78,
  haeufigster_mangel: "Bewuchs/Vegetation"
})

CREATE (:Produkt {
  id: "BLITZ_INNEN",
  name: "Innerer Blitzschutz, Überspannungsschutz",
  lpv_referenz: "B04 §8.2",
  verrechnung: "nach_angebot",
  stundensatz: 208.00
})

// Berichtstypen
CREATE (:Berichtstyp {id: "BERICHT_KLEIN", name: "Kleine Anlagen", preis: 119.00})
CREATE (:Berichtstyp {id: "BERICHT_STANDARD", name: "Standard ≤10 Seiten", preis: 380.00})
CREATE (:Berichtstyp {id: "BERICHT_KOMPLEX", name: "Komplex", preis: 550.00})

// Gebäudetypen (aus 99 Berichten extrahiert)
CREATE (:Gebaeudetyp {id: "GT_MUSEUM", name: "Museum / Burg / Schloss"})
CREATE (:Gebaeudetyp {id: "GT_HOTEL", name: "Hotel / Gaststätte"})
CREATE (:Gebaeudetyp {id: "GT_BUERO", name: "Bürogebäude"})
CREATE (:Gebaeudetyp {id: "GT_INDUSTRIE", name: "Industriegebäude"})
CREATE (:Gebaeudetyp {id: "GT_WOHNUNG", name: "Wohngebäude"})
CREATE (:Gebaeudetyp {id: "GT_KRANKENHAUS", name: "Krankenhaus / Klinik"})
CREATE (:Gebaeudetyp {id: "GT_SCHULE", name: "Schule / Versammlungsstätte"})
CREATE (:Gebaeudetyp {id: "GT_LAGER", name: "Lager / Halle"})

// Schutzklassen
CREATE (:Schutzklasse {id: "SK_I", name: "Schutzklasse I", beschreibung: "Höchste Schutzklasse (Explosionsgefahr, Munition)"})
CREATE (:Schutzklasse {id: "SK_II", name: "Schutzklasse II", beschreibung: "Krankenhaus, Museum, Versammlungsstätten"})
CREATE (:Schutzklasse {id: "SK_III", name: "Schutzklasse III", beschreibung: "Standard (Büro, Industrie, Wohnung)"})
CREATE (:Schutzklasse {id: "SK_IV", name: "Schutzklasse IV", beschreibung: "Niedrigste (einfache Wohngebäude, Lager)"})

// Standorte (20+)
CREATE (:Standort {id: "STD_NBG", name: "Nürnberg", adresse: "Edisonstr. 15, 90431 Nürnberg", lat: 49.4521, lon: 11.0767})
CREATE (:Standort {id: "STD_AUG", name: "Augsburg", adresse: "Oskar-von-Miller-Str. 17, 86199 Augsburg", lat: 48.3668, lon: 10.8865})
CREATE (:Standort {id: "STD_MUC", name: "München", adresse: "Westendstraße 199, 80686 München", lat: 48.1351, lon: 11.5075})
// ... weitere 17+ Standorte aus Veit-Mail

// Mängelkategorien (aus 99 Berichten klassifiziert)
CREATE (:MangelKategorie {id: "MK_BEWUCHS", name: "Bewuchs / Vegetation", haeufigkeit: 0.34})
CREATE (:MangelKategorie {id: "MK_WIDERSTAND", name: "Übergangswiderstand zu hoch", haeufigkeit: 0.28})
CREATE (:MangelKategorie {id: "MK_KORROSION", name: "Korrosion", haeufigkeit: 0.18})
CREATE (:MangelKategorie {id: "MK_ZUGAENGLICH", name: "Nicht zugänglich", haeufigkeit: 0.12})
CREATE (:MangelKategorie {id: "MK_MECHANISCH", name: "Mechanische Beschädigung", haeufigkeit: 0.05})
CREATE (:MangelKategorie {id: "MK_DOKU", name: "Dokumentationslücken", haeufigkeit: 0.03})
```

### 2.2 Kanten

```cypher
// Upsell: äußerer → innerer Blitzschutz
MATCH (a:Produkt {id:"BLITZ_AUSSEN"}), (b:Produkt {id:"BLITZ_INNEN"})
CREATE (a)-[:UPSELL {
  text: "Für vollständige Beurteilung: innerer Blitzschutz + Überspannungsschutz empfohlen",
  quelle: "99/99 Prüfberichte enthalten diesen Hinweis",
  prioritaet: "hoch"
}]->(b)

// Berichtstyp-Zuordnung
MATCH (p:Produkt {id:"BLITZ_AUSSEN"}), (b1:Berichtstyp {id:"BERICHT_KLEIN"})
CREATE (p)-[:HAT_BERICHTSTYP {bedingung: "messstellen <= 10"}]->(b1)

MATCH (p:Produkt {id:"BLITZ_AUSSEN"}), (b2:Berichtstyp {id:"BERICHT_STANDARD"})
CREATE (p)-[:HAT_BERICHTSTYP {bedingung: "messstellen > 10 AND messstellen <= 40"}]->(b2)

MATCH (p:Produkt {id:"BLITZ_AUSSEN"}), (b3:Berichtstyp {id:"BERICHT_KOMPLEX"})
CREATE (p)-[:HAT_BERICHTSTYP {bedingung: "messstellen > 40 OR sonderfaelle"}]->(b3)

// Schätzung Trennstellen per Gebäudetyp (aus 99 Berichten)
MATCH (g:Gebaeudetyp {id:"GT_MUSEUM"}), (p:Produkt {id:"BLITZ_AUSSEN"})
CREATE (g)-[:TYPISCHE_TRENNSTELLEN {
  median: 38, min: 18, max: 65, p25: 28, p75: 48,
  schutzklasse: "III", n_berichte: 12, konfidenz: "mittel",
  quelle: "99 Prüfberichte EG Nürnberg Q1/2025"
}]->(p)

MATCH (g:Gebaeudetyp {id:"GT_BUERO"}), (p:Produkt {id:"BLITZ_AUSSEN"})
CREATE (g)-[:TYPISCHE_TRENNSTELLEN {
  median: 14, min: 6, max: 28, p25: 10, p75: 20,
  schutzklasse: "III", n_berichte: 15, konfidenz: "mittel",
  quelle: "99 Prüfberichte EG Nürnberg Q1/2025"
}]->(p)

// ... analogicznie für alle 8 Gebäudetypen

// Typische Schutzklasse per Gebäudetyp
MATCH (g:Gebaeudetyp {id:"GT_KRANKENHAUS"}), (s:Schutzklasse {id:"SK_II"})
CREATE (g)-[:TYPISCHE_SCHUTZKLASSE]->(s)

MATCH (g:Gebaeudetyp {id:"GT_BUERO"}), (s:Schutzklasse {id:"SK_III"})
CREATE (g)-[:TYPISCHE_SCHUTZKLASSE]->(s)

// ... analogicznie

// Erwartungsbereich für Input-Validierung (Perzentile aus 99 Berichten)
MATCH (p:Produkt {id:"BLITZ_AUSSEN"})
SET p.erwartung_sk3_p5 = 6,
    p.erwartung_sk3_p25 = 12,
    p.erwartung_sk3_p75 = 35,
    p.erwartung_sk3_p95 = 55

// Konfidenz-Range aus Augsburg-Realpreisen
MATCH (p:Produkt {id:"BLITZ_AUSSEN"})
SET p.realpreis_faktor_min = 0.85,
    p.realpreis_faktor_max = 1.15,
    p.realpreis_quelle = "~200 Realpreise Augsburg 2025"
```

### 2.3 Zusammenfassung Graph

| Element | Anzahl |
|---------|--------|
| Produkt-Knoten | 2 (äußerer + innerer) |
| Berichtstyp-Knoten | 3 |
| Gebäudetyp-Knoten | 8 |
| Schutzklasse-Knoten | 4 |
| Standort-Knoten | 20+ |
| MangelKategorie-Knoten | 6 |
| UPSELL-Kanten | 1 |
| TYPISCHE_TRENNSTELLEN-Kanten | 8 (je Gebäudetyp) |
| TYPISCHE_SCHUTZKLASSE-Kanten | 8 |
| HAT_BERICHTSTYP-Kanten | 3 |
| **Total** | **~50 Knoten, ~25 Kanten** |

---

## 3. Kalkulationslogik

### 3.1 Formel

```
Gesamtpreis = Prüfkosten + Grundkosten + Berichterstellung + Reisekosten

Prüfkosten:
  = anzahl_messstellen × 33,00 €

Grundkosten:
  = 256,00 €                              (Pauschale)
  + 49,00 € × anzahl_prueftage            (Prüfmittel)
  + tagegeld(stunden_aussendienst)         (6/25/30 €)

Berichterstellung:
  = WENN messstellen ≤ 10:    119,00 €
    WENN messstellen ≤ 40:    380,00 €
    SONST:                    550,00 €

Reisekosten:
  = entfernung_km × 1,10 €                (Fahrtkosten)
  + reisezeit_h × 180,00 €                (Reisezeit)
```

### 3.2 Schätzungen (wenn Daten fehlen)

```
WENN anzahl_messstellen UNBEKANNT:
  → Frage: Gebäudetyp + Schutzklasse
  → Lookup: TYPISCHE_TRENNSTELLEN Kante
  → Zeige Range: "Erfahrungswert: min–max, Median X"
  → Berechne mit Median, zeige ±Range

WENN schutzklasse UNBEKANNT:
  → Frage: Gebäudetyp
  → Lookup: TYPISCHE_SCHUTZKLASSE Kante
  → Vorschlag: "Für Bürogebäude typischerweise Schutzklasse III"

WENN standort UNBEKANNT:
  → Frage: PLZ oder Ort des Objekts
  → Berechne nächsten TÜV SÜD Standort
  → Zeige Entfernung + Reisekosten
```

### 3.3 Schieberegler grob/mittel/fein

```
GROB (2 Fragen):
  Input: Gebäudetyp + ungefähre Größe
  → Schätzung Trennstellen aus Graph (Median)
  → Pauschale Reisekosten (Durchschnitt 80 km)
  → Konfidenz: ±30%
  → Output: "Richtpreis: 1.800–3.000 €"

MITTEL (4 Fragen):
  Input: Gebäudetyp + Schutzklasse + ungefähre Trennstellen + PLZ
  → Kalkulation mit geschätzten Trennstellen
  → Reisekosten ab nächstem Standort
  → Konfidenz: ±15%
  → Output: "Kalkulierter Preis: 2.100–2.800 €"

FEIN (alle Daten):
  Input: exakte Trennstellen + Schutzklasse + Adresse + Besonderheiten
  → Exakte Kalkulation
  → Exakte Reisekosten
  → Konfidenz: ±5%
  → Output: "Preis: 2.438 € netto"
  → + Realpreis-Range: "Erfahrungswert: 2.100–2.800 €"
```

---

## 4. Features aus 99 Berichten

### 4.1 Schätzung Trennstellen (wenn Kunde nicht weiß)
- **Trigger**: Feld "Anzahl Trennstellen" leer, User klickt "Schätzen"
- **Input**: Gebäudetyp (Dropdown) + Schutzklasse (Dropdown)
- **Logik**: Graph-Query TYPISCHE_TRENNSTELLEN → Median + Range
- **Output**: "Erfahrungswert: Museum/Burg, SK III → 18–65 Trennstellen, Median 38"
- **Kalkulation**: Preis mit Median, Spanne min/max anzeigen

### 4.2 Input-Validator
- **Trigger**: User gibt Anzahl Trennstellen ein
- **Logik**: Vergleich mit p5/p95 aus 99 Berichten per Schutzklasse
- **Output gelb**: "Die Anzahl (200) ist ungewöhnlich hoch für SK III (typisch: 6–55). Bitte prüfen."
- **Output rot**: "Die Anzahl (0) ist ungültig."

### 4.3 Upsell innerer Blitzschutz
- **Trigger**: Jede Kalkulation BLITZ_AUSSEN
- **Logik**: Graph-Query UPSELL-Kante
- **Output**: Blaue Box: "Empfehlung: In 99 von 99 analysierten Prüfberichten wurde zusätzlich die Prüfung des inneren Blitzschutzes und Überspannungsschutzes empfohlen."
- **CTA**: "Inneren Blitzschutz hinzufügen" (→ Hinweis: nach Angebot, 208 €/h)

### 4.4 Mängelstatistik
- **Trigger**: Jede Kalkulation BLITZ_AUSSEN
- **Logik**: Properties auf Produkt-Knoten
- **Output**: Graue Info-Box: "Erfahrungswert: Bei 78 % der Blitzschutzprüfungen werden Mängel festgestellt. Häufigste Ursache: Bewuchs bei historischen Gebäuden (34 %). In der Regel sind Mängel geringfügig (Einstufung 1)."

### 4.5 Konfidenz-Range (LPV vs Realpreise)
- **Trigger**: Nach Kalkulation
- **Logik**: Kalkulierter Preis × realpreis_faktor_min/max
- **Output**: Unter dem Gesamtpreis: "Erfahrungswert aus vergleichbaren Prüfungen: X € – Y €"

### 4.6 Hinweis-System (Edge Cases)
- **> 10 Messstellen**: "Ab 10 Messstellen kann eine besondere Vereinbarung getroffen werden."
- **Hochhaus erkannt**: "Bei Hochhäusern (> 5 Stockwerke) kann erhöhter Aufwand anfallen."
- **Erstprüfung**: "Zuschlag bis +100 % auf die Preise für wiederkehrende Prüfungen."
- **Einzelprüfung**: "Zuschlag bis +20 % (ohne Rahmenvertrag)."
- **Schutzklasse I oder II**: "Kürzeres Prüfintervall (1–2 Jahre statt 4)."

---

## 5. Datenextraktion 99 Berichte

### 5.1 Extraction Pipeline

```
99 PDFs
  │
  ▼ Claude API (batch, ~$5-10, ~20 min)
  │ Prompt: "Extrahiere folgende Felder aus diesem Prüfbericht..."
  │ + JSON-Schema aus §5.2
  │
99 JSONs
  │
  ▼ Python Aggregation (pandas, 1-2h)
  │
  ├── tabelle_trennstellen.csv    (Gebäudetyp × SK → Median/Min/Max/P25/P75)
  ├── tabelle_maengel.csv         (Kategorie → Häufigkeit, typ. Einstufung)
  ├── tabelle_ergebnis.csv        (mit_maengeln / ohne_maengeln pro Gebäudetyp)
  ├── tabelle_intervall.csv       (SK × Gebäudetyp → Intervall Monate)
  └── gebaedetyp_katalog.json     (unique Nutzungstypen, normalisiert)
  │
  ▼ Graph-Import (Cypher, 30 min)
  │
  └── TYPISCHE_TRENNSTELLEN Kanten + MangelKategorien + Properties
```

### 5.2 Extraction JSON Schema

```json
{
  "equipment_nr": "string",
  "pruefart": "WP|PI|PM",
  "datum": "YYYY-MM-DD",
  "naechste_pruefung": "YYYY-MM",
  "intervall_monate": "number",

  "standort_plz": "string",
  "standort_ort": "string",
  "betreiber": "string",
  "auftraggeber": "string",

  "nutzung": ["string"],
  "schutzklasse": "I|II|III|IV",
  "anzahl_ableitungen": "number",
  "material": ["string"],

  "messstellen_total": "number",
  "messstellen_gemessen": "number",
  "messstellen_ueber_10_ohm": "number",
  "messstellen_999_ohm": "number",
  "messstellen_nicht_messbar": "number",

  "anzahl_maengel": "number",
  "max_einstufung": "1|2|3",
  "ergebnis": "ohne_maengel|mit_maengeln|mit_erheblichen_maengeln",
  "maengel": [
    {
      "beschreibung_kurz": "string",
      "einstufung": "1|2|3",
      "kategorie": "BEWUCHS|WIDERSTAND|KORROSION|ZUGAENGLICH|MECHANISCH|DOKU"
    }
  ],

  "upsell_nur_aeusserer": "boolean",
  "upsell_fehlende_unterlagen": "boolean"
}
```

### 5.3 Aggregation Queries

```python
# Tabelle A: Trennstellen per Gebäudetyp
df.groupby('nutzung_normalisiert').agg(
    n=('anzahl_ableitungen', 'count'),
    median=('anzahl_ableitungen', 'median'),
    min=('anzahl_ableitungen', 'min'),
    max=('anzahl_ableitungen', 'max'),
    p25=('anzahl_ableitungen', lambda x: x.quantile(0.25)),
    p75=('anzahl_ableitungen', lambda x: x.quantile(0.75))
)

# Tabelle B: Mängelverteilung
alle_maengel = df.explode('maengel')
alle_maengel['kategorie'].value_counts(normalize=True)

# Tabelle C: Ergebnis per Gebäudetyp
df.groupby('nutzung_normalisiert')['ergebnis'].value_counts(normalize=True)

# Erwartungsbereich per Schutzklasse (für Input-Validator)
df.groupby('schutzklasse')['anzahl_ableitungen'].quantile([0.05, 0.25, 0.75, 0.95])
```

---

## 6. Validierung

### 6.1 Cross-Check LPV vs Realpreise

```
Für jedes Objekt in Augsburg-Tabelle:
  kalkulierter_preis = anzahl_ableitungen × 33 + 256 + 49 + tagegeld + bericht
  realpreis = aus Excel
  abweichung = (kalkulierter_preis - realpreis) / realpreis × 100

Erwartung: mittlere Abweichung < 15 %
Falls > 15 %: Systematische Differenz → Rahmenvertrag-Rabatt? Regionale Sonderregel?
```

### 6.2 Testfälle

| # | Szenario | Input | Erwartetes Ergebnis |
|---|----------|-------|---------------------|
| 1 | Burg Lauenstein (aus Prüfbericht) | 41 Messstellen, SK III, PLZ 96337 | Prüf: 1.353 €, Grund: ~330 €, Bericht: 380 €, Reise: ~274 € → ~2.337 € |
| 2 | Kleines Wohnhaus | 6 Messstellen, SK IV, PLZ 90431 | Prüf: 198 €, Grund: ~330 €, Bericht: 119 €, Reise: ~20 € → ~667 € |
| 3 | Großes Industrieobjekt | 80 Messstellen, SK III, PLZ 86199 | Prüf: 2.640 €, Grund: ~355 €, Bericht: 550 €, Reise: ~50 € → ~3.595 € + Hinweis >10 MS |
| 4 | Schätzung (kein MS bekannt) | "Museum", SK III, PLZ 96049 | Schätzung: Median 38 MS → ~2.238 €, Range: 1.200–3.100 € |
| 5 | Input-Validator | 500 Messstellen, SK III | Warning: "ungewöhnlich hoch (typisch: 6–55)" |
| 6 | Erstprüfung | 20 Messstellen, SK III, Erstprüfung | Prüf: 660 € + Hinweis "+100 % Zuschlag möglich" |

---

## 7. UI-Elemente Blitzschutz

### 7.1 Input Panel

```
┌─ Blitzschutz äußerer ──────────────────────────┐
│                                                 │
│  Anzahl Trennstellen: [____] [Schätzen ▸]       │
│                                                 │
│  Schutzklasse:        [III ▾]                   │
│                                                 │
│  Standort / PLZ:      [_________]               │
│                                                 │
│  ☐ Erstprüfung (vor Inbetriebnahme)             │
│  ☐ Einzelprüfung (ohne Rahmenvertrag)           │
│  ☐ Hochhaus (> 22m / > 5 Etagen)               │
│                                                 │
│  [Berechnen]                                    │
└─────────────────────────────────────────────────┘
```

### 7.2 Schätzungs-Dialog (wenn "Schätzen" geklickt)

```
┌─ Trennstellen schätzen ────────────────────────┐
│                                                 │
│  Gebäudetyp: [Museum / Burg ▾]                  │
│                                                 │
│  Erfahrungswert (99 Prüfberichte):              │
│  ┌──────────────────────────────────────┐       │
│  │  ╟──────[████████]──────╢            │       │
│  │  18    28    38    48    65           │       │
│  │        p25  Median  p75              │       │
│  └──────────────────────────────────────┘       │
│                                                 │
│  Median: 38 Trennstellen                        │
│  Konfidenz: mittel (n=12 Berichte)              │
│                                                 │
│  [Übernehmen: 38]  [Range verwenden: 18–65]     │
└─────────────────────────────────────────────────┘
```

### 7.3 Result Panel

```
┌─ Kalkulation Blitzschutz äußerer ──────────────┐
│                                                 │
│  Prüfkosten     38 × 33,00 €       1.254,00 €  │
│  Grundkosten    Pauschale             256,00 €  │
│                 Prüfmittel (1 Tag)     49,00 €  │
│                 Tagegeld (8–14h)       25,00 €  │
│  Bericht        Standard (≤10 S.)    380,00 €   │
│  Reisekosten    85 km × 1,10 €        93,50 €  │
│                 1h × 180,00 €        180,00 €   │
│  ───────────────────────────────────────────     │
│  Gesamtpreis netto                 2.237,50 €   │
│                                                 │
│  ┌─ Erfahrungswert ──────────────────────────┐  │
│  │ Vergleichbare Prüfungen: 1.900–2.600 €    │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  ┌─ Empfehlung ─────────────────── blau ─────┐  │
│  │ In 99/99 Prüfberichten wurde zusätzlich   │  │
│  │ die Prüfung des inneren Blitzschutzes     │  │
│  │ und Überspannungsschutzes empfohlen.       │  │
│  │ [Hinzufügen →]                            │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  ┌─ Erfahrungswert ──────────────── grau ────┐  │
│  │ 78 % der Blitzschutzprüfungen ergeben     │  │
│  │ Mängel. Häufigste Ursache: Bewuchs (34 %).│  │
│  │ In der Regel geringfügig (Einstufung 1).  │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  ┌─ Hinweis ────────────────────── gelb ─────┐  │
│  │ Ab 10 Messstellen kann eine besondere     │  │
│  │ Vereinbarung getroffen werden.            │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

---

## 8. Task Breakdown

| # | Task | Aufwand | Abhängigkeit |
|---|------|---------|--------------|
| B1 | Preisdaten Blitzschutz in Graph laden (Cypher) | 2h | — |
| B2 | Standorte in Graph laden (20+ Adressen + Geocoding) | 3h | — |
| B3 | Gebäudetypen + Schutzklassen in Graph laden | 1h | — |
| B4 | PDF-Extraktion 99 Berichte (Claude API batch) | 2h | — |
| B5 | Aggregation: Trennstellen-Tabelle, Mängel, Ergebnis, Intervall | 2h | B4 |
| B6 | Graph-Import: TYPISCHE_TRENNSTELLEN + MangelKategorien + Erwartungsbereich | 1h | B5 |
| B7 | Kalkulationslogik implementieren (Formel aus §3.1) | 3h | B1, B2 |
| B8 | Schätzung Trennstellen (UI + Graph-Query) | 2h | B6 |
| B9 | Input-Validator (Perzentile-Check) | 1h | B6 |
| B10 | Upsell-Hinweis + Mängelstatistik + Konfidenz-Range (UI-Boxen) | 2h | B6 |
| B11 | Hinweis-System (Edge Cases: >10 MS, Erstprüfung, Hochhaus) | 1h | B7 |
| B12 | Validierung vs Augsburg-Realpreise (6 Testfälle) | 2h | B7 |
| **Total** | | **~22h = 3 Tage** | |

### Sequenzierung

```
Tag 1 (Mo):
  B1 + B2 + B3 parallel     (Preise + Standorte + Gebäudetypen in Graph)
  B4 (PDF-Extraktion batch — läuft in background)
  B7 start (Kalkulationslogik)

Tag 2 (Di):
  B5 (Aggregation, nachdem B4 fertig)
  B6 (Graph-Import Schätzungen)
  B7 finish (Kalkulationslogik)
  B8 (Schätzung Trennstellen)

Tag 3 (Mi):
  B9 (Input-Validator)
  B10 (UI-Boxen: Upsell + Mängel + Konfidenz)
  B11 (Hinweis-System)
  B12 (Validierung + Testfälle)
  → Demo-ready
```

---

## 9. Demo-Story KW15 Freitag

**Szenario 1 — Exakte Daten (Fein):**
"Blitzschutzprüfung, 41 Messstellen, Schutzklasse III, Burg Lauenstein, PLZ 96337."
→ Exakter Preis mit Aufschlüsselung. Hinweis >10 MS. Upsell innerer Blitzschutz.

**Szenario 2 — Schätzung (Grob):**
"Museum, keine Ahnung wie viele Trennstellen."
→ Button Schätzen → Range 18–65, Median 38 → Richtpreis 1.800–3.100 €.

**Szenario 3 — Input-Fehler:**
"200 Messstellen, Schutzklasse III."
→ Gelbes Warning: untypisch hoch.

**Veit-Insight:**
"Wir haben Ihre 99 Berichte ausgewertet. 78 % mit Mängeln, Bewuchs dominiert. Und: Cross-Check mit Ihren Augsburg-Realpreisen zeigt Abweichung von nur X %."
