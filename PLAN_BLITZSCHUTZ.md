# SmartCal@EG — Implementation Plan (Phase 1: 3 produkty)

**Data**: 2026-04-16
**Demo deadline**: KW27 = 06.07.2026 (Abteilungsleitertagung TÜV SÜD EG)
**Pierwszy checkpoint**: KW17 = pn 20.04.2026 (Projektregeltermin, 11 osób)

**Scope Phase 1** (Veit-confirmed na callu 10.04.2026):
1. **Blitzschutz äußerer** — MA570 umfassend (primary, 5,403 raportów + 325 Anlagen StV walidacja)
2. **RLT-Anlage** — MA419 (Hygiene VDI 6022 + Garagenlüftung WPBA)
3. **DGUV V3 ortsfeste elektrische Anlage** — MA507 (Veit-benchmark: "wenn das funktioniert, glaubt uns jeder")

**Strategia**: jeden product-agnostic engine, 3 produkty zashippowane do KW27, framework gotowy żeby dodać kolejne 8 produktów (MA438/441/501/510/555/560/572/574) w Phase 2 po 1-2 dni każdy.

---

## 1. Architektura — product-agnostic engine

### 1.1 Klucz: Vorlage Kalkulation potwierdza ujednolicony schemat
**Discovery z dataset**: master Vorlage TÜV ma 13 Gewerk-sheets o **identycznej strukturze 46-52 × 10 kolumn** (GT RLT, GT Hygiene, GT MRA/RDA/NRA, GT SPR, GT FL, GT CO Warn, ET BMA, ET ALA, ET NEA SSV, ET SiBel, ET VDS, ET allg. el. Anl., ET DGUV V3, ET Blitz, DD Behälter, FT-Liste).

→ TÜV już sami stworzyli abstrakcję: **Gewerk** = jednostka kalkulacji z ustandaryzowanymi inputami i pricing rules.
→ Replikujemy tę abstrakcję w kodzie: `Gewerk` jako pierwszorzędny obiekt, parametryzowany per produkt.

### 1.2 Struktura backend (refaktor + rozszerzenie)

```
backend/
├── common/                      ← shared infrastructure
│   ├── llm.py                  (Claude wrapper)
│   ├── database.py             (FalkorDB client, multi-graph)
│   ├── pdf_extractor.py        (generic PDF→JSON via Haiku/Sonnet)
│   ├── chat_core.py            (session, coordinator)
│   └── pricing_primitives.py   (LPV Teil A: Reise, Tagegeld, Bericht, Stundensätze)
│
├── engine/                      ← product-agnostic Kalkulator
│   ├── gewerk.py               (Gewerk base class)
│   ├── merkmale.py             (Pydantic schemas, generic + per-Gewerk)
│   ├── pricing_engine.py       (rules executor: input → breakdown → total)
│   ├── extractor.py            (PDF → Merkmale, dispatch per Gewerk)
│   ├── validator.py            (porównanie nasz_output vs golden set)
│   └── graph_schema.py         (universal: Objekt/Anlage/Pruefbericht/Mangel)
│
├── products/                    ← konkretne produkty (Phase 1: 3)
│   ├── blitzschutz/
│   │   ├── __init__.py         (Gewerk config: MA570 binding)
│   │   ├── merkmale.py         (BlitzschutzMerkmale: 17 pól)
│   │   ├── pricing_rules.py    (LPV B04 §8.1: 33€/MS + Staffeln)
│   │   ├── extraction_prompt.txt
│   │   └── golden_set.py       (loader Blitzschutz_StV.xlsx → 325 Anlagen)
│   ├── rlt/
│   │   ├── __init__.py         (Gewerk config: MA419-HYG + MA419-WPBA)
│   │   ├── merkmale.py         (RLTMerkmale: ~15 pól dla HYG, ~12 dla Garage)
│   │   ├── pricing_rules.py    (LPV B05 Kap. 2: 600/780€ Grundpreis + Ventilatoren + BSK)
│   │   ├── extraction_prompt.txt
│   │   └── golden_set.py       (subset z VdS+UVV_StV.xlsx + Vorlage GT-RLT/GT-Hygiene)
│   └── dguv_v3/
│       ├── __init__.py         (Gewerk config: MA507 ortsfest)
│       ├── merkmale.py         (DGUVMerkmale: ~12 pól)
│       ├── pricing_rules.py    (LPV B04 Kap. 2: 250€/Anlage + 1-5€/10m² Installationskategorie)
│       ├── extraction_prompt.txt
│       └── golden_set.py       (Gersthofen Verteiler-Ebene + 059E Audi Ausschreibung GAEB)
│
├── routers/                     ← API per produkt
│   ├── blitzschutz_router.py   (/api/blitzschutz/*)
│   ├── rlt_router.py           (/api/rlt/*)
│   ├── dguv_v3_router.py       (/api/dguv-v3/*)
│   └── smartcal_router.py      (/api/smartcal/* — istniejące demo, refaktor)
│
└── main.py                      (register all routers)
```

### 1.3 Gewerk base class (kontrakt produktu)

```python
class Gewerk(ABC):
    name: str                          # "Blitzschutz äußerer"
    ma_codes: list[str]                # ["MA570"]
    lpv_referenz: str                  # "B04 §8.1"
    merkmale_schema: type[BaseModel]   # BlitzschutzMerkmale
    pricing_rules: PricingRules        # callable(merkmale) → breakdown
    extraction_prompt: str             # LLM prompt dla PDF → Merkmale
    golden_set_loader: Callable        # → list[(merkmale, real_price)]

    def calculate(self, merkmale: BaseModel) -> Angebot: ...
    def extract_from_pdf(self, pdf_path: str) -> BaseModel: ...
    def validate(self, sample_size: int = None) -> ValidationReport: ...
```

→ Dodanie 4. produktu w Phase 2 = stworzenie nowego folderu `products/<name>/` z 4 plikami. Routery i frontend rejestrują się automatycznie z manifestu.

### 1.4 Frontend (Next.js)

```
app/
├── smartcal/                    (istniejące demo)
└── [product]/                   ← dynamic route per Gewerk
    ├── page.tsx                 (home + stats)
    ├── anfrage/page.tsx         (formularz Merkmale, generated z schema)
    ├── angebot/[id]/page.tsx    (wynik + PDF export)
    ├── chat/page.tsx            (conversational UI, shared)
    └── admin/page.tsx           (upload Prüfberichte)
```

`[product]` = `blitzschutz` | `rlt` | `dguv-v3`. Komponenty (`<KalkulatorForm>`, `<AngebotCard>`, `<ConfidenceBadge>`, `<SimilarAnlagen>`) shared, schema-driven.

### 1.5 FalkorDB — graphs

| Graph name | Zawartość | Czemu osobny |
|---|---|---|
| `smartcal` | Istniejące demo | Backwards compat, no migration |
| `blitzschutz` | 5,403 raporty MA570 + 325 StV + LPV §8 | Izolacja schematu, łatwy reset |
| `rlt` | MA419 raporty (~10k między HYG i WPBA) | Inne entity (Filterklasse, Volumenstrom, Stellplätze) |
| `dguv_v3` | MA507 raporty (10,096) + Gersthofen | Per-Stromkreis tabele, inne Merkmale |

Universal nodes (`Objekt`, `Standort`, `Sachverstaendiger`, `TUEV_Niederlassung`) duplikowane per graf — koszt mały (1k nodes), zysk: pełna niezależność per produkt.

---

## 2. Scope Phase 1 — co dokładnie shippujemy

### 2.1 Blitzschutz (MA570 umfassend)
- **Norma**: DIN EN 62305-1/-3 + Beiblatt 3 (2012)
- **Grundlage**: Auftrag des Betreibers (non-Baurecht, non-Ex)
- **Walidacja**: 325 Anlagen w `Blitzschutz_StV.xlsx` z realnymi cenami TÜV
- **Merkmale (17)**: Nutzung, Bauart, Dach, Werkstoff Gebäudeleitung, Schutzklasse I-IV, Abmessungen, Gebäudeumfang, Anzahl Ableitungen, Material Ableitung, Typ Erdungsanlage (A/B), Material Erdungsanlage, Blitzschutzpotentialausgleich, Überspannungsschutz, Art Ableitung + tabela Messwerte per Messstelle
- **Pricing core**: 33€/Messstelle (LPV B04 §8.1) + Reise + Grund + Bericht (119/380/550€)
- **Edge case Phase 2**: Schön Klinik 178 Ableitungen (multi-Teilgebäude) — w Phase 1 musi nie crashować, walidacja Phase 2

### 2.2 RLT-Anlage (MA419 — 2 sub-warianty)
- **Sub-wariant A — Hygiene VDI 6022 (MA419-HYG)**: 862 raportów
  - Merkmale (15): Baujahr, Hersteller, Nennvolumenstrom m³/h, Filterklasse AUL/ZUL (ISO ePM), WRG (Kreuzstrom/Rotation), Luftbehandlung, Ventilator, Außenluftansaugung, KBE/25cm² Pilze/Bakterien
  - Pricing: LPV B05 Kap. 2.7 (Stundensatz 208€)
- **Sub-wariant B — Garagenlüftung (MA419-WPBA)**: 8,150 raportów
  - Merkmale (12): Fläche m², spez. Volumenstrom m³/(h·m²), Stellplätze, Garagentyp, Brandschutzklappen Anzahl, Zeitschaltuhr, Ist/Soll Volumenstrom
  - Pricing: LPV B05 Kap. 2.2 (450/690/1250€ per Stellplatz-Bereich)
- **Walidacja**: Vorlage Kalkulation `GT RLT` + `GT Hygiene` sheets jako reference, MUC Preistool `VDI 6022` sheet (80×11) jako secondary
- **Decyzja Phase 1**: 1 produkt UI (RLT) z auto-detection sub-wariantu z Anfrage. Engine internally rozdziela na 2 pricing-paths.

### 2.3 DGUV V3 ortsfest (MA507)
- **Norma**: DIN VDE 0105-100/A1 + DGUV V3/V4 + BetrSichV
- **Grundlage**: Kundenauftrag (cyclic protective check)
- **Merkmale (12)**: Nutzung Gebäude (Seniorentreff/Service/Bürogebäude), Errichtungszeitraum, Netzform (TT/TN-C-S), Netzbetreiber, Einspeisung (MS-Hausanschluss/Trafo), Leistung kVA, Räume besonderer Nutzung (NEA, SV-NSHV), Überspannungsschutz, **Messwerte per Stromkreis** (Fehlerschleife/RISO/RCD)
- **Pricing core**: LPV B04 Kap. 2 (250€ Grundpreis + 1-5€/10m² per Installationskategorie), 5 Flächenfaktoren 100-500m²
- **Walidacja**: Gersthofen-Excel (1,393 pozycji LV na Verteiler-Ebene) + 059E-2025 Audi Ausschreibung (GAEB-Konverter format)
- **Veit-benchmark**: ten produkt jest najtrudniejszy. Jeśli zadziała → "glaubt uns jeder"

### 2.4 Co NIE robimy w Phase 1
- MA572 Blitzschutz Baurecht Sonderbau (Bauaufsichtsbehörde-flow)
- MA574 Blitzschutz wiederkehrend non-Baurecht
- MA555 Blitzschutz Ex (ZÜS, GefStoffV §7(7))
- MA438 NRA Rauchabzug (Treppenraum)
- MA441 BSK (Brandschutzklappen, granularność per BSK)
- MA501 Elektr. Ex (VDE 0165, rafinerie)
- MA510 Starkstrom Sonderbau (najbogatszy, 40-60 Mängel/raport — Phase 2 najwyższy ROI)
- MA560 Ortsveränderliche Geräte (per-device check)
- Innerer Blitzschutz / Überspannungsschutz (MA570 inner część)
- Automatyczny ingest klient-strony PDFów
- Integracja SAP/NetInform TÜV
- Pełny TÜV StyleGuide (decyzja Veit 10.04: POC = MING Cloud, no styleguide)

### 2.5 Definicja sukcesu Phase 1 (KW27)

| Metryka | Target | Pomiar |
|---|---|---|
| Blitzschutz match_rate@±10% | ≥ 80% | 325 Anlagen StV |
| RLT match_rate@±15% | ≥ 70% | Vorlage GT RLT + MUC VDI 6022 |
| DGUV V3 match_rate@±15% | ≥ 70% | Gersthofen + Audi Ausschreibung |
| Live Anfrage → Angebot | &lt; 60 sek | Demo timer |
| Stress test edge cases | bez crash | Schön Klinik 178, Gersthofen 1,393 LV |
| User-test (7 testerów Regeltermin) | ≥ 5/7 może sami zrobić Anfrage | UAT KW22 |

---

## 3. Data pipeline

### 3.1 Inwentaryzacja źródeł (Phase 1)

| # | Źródło | Lokalizacja | Produkt | Rola | Priorytet |
|---|---|---|---|---|---|
| 1 | 5,403 PDF MA570-WP | `~/Desktop/TUEV/570_572_574/MA570-WP-*.pdf` | Blitz | Training extraction | P0 |
| 2 | 325 Anlagen Blitzschutz_StV | `~/Desktop/TUEV/Anlagenliste-LV-Preisblätter_WP Blitzschutz_StV (1).xlsx` | Blitz | **Golden validation** | P0 |
| 3 | 862 PDF MA419-HYG | `~/Desktop/TUEV/441_419/MA419-HYG-*.pdf` | RLT | Training Hygiene | P0 |
| 4 | 8,150 PDF MA419-WPBA | `~/Desktop/TUEV/441_419/MA419-WPBA-*.pdf` | RLT | Training Garage | P0 |
| 5 | 10,096 PDF MA507-WP | `~/Desktop/TUEV/507/MA507-WP-*.pdf` | DGUV V3 | Training extraction | P0 |
| 6 | LPV 2026 B04+B05 | `~/Desktop/TUEV/LP_00_2026_Gesamt (1).pdf` s.71-93 | wszystkie | Pricing rules | P0 |
| 7 | Vorlage Kalkulation 13 Gewerk-sheets | `~/Desktop/TUEV/2024-04-09 Vorlage Kalkulation (1).xlsm` | wszystkie | Reference business logic | P1 |
| 8 | NBG Kalkulationshilfen v2 | `~/Desktop/TUEV/Kalkulationstools (1)/NBG/...xlsx` | wszystkie | Extended Merkmale (per-norma split) | P1 |
| 9 | MUC Preistool 2026 | `~/Desktop/TUEV/Preistool_EG1_MUC 2026_251121 (1).xlsx` | RLT | VDI 6022 sheet 80×11 | P1 |
| 10 | Gersthofen 88k cells | `~/Desktop/TUEV/Pruefung Elektrische Anlagen_Stadt Gersthofen...xlsm` | DGUV V3 | Edge case granulation | P1 |
| 11 | 059E Audi Ausschreibung | `~/Desktop/TUEV/059E-2025_Ausschreibungsunterlagen...xlsm` | DGUV V3 | GAEB format | P2 |
| 12 | VdS+UVV Anlagenliste | `~/Desktop/TUEV/Anlagenliste-LV-Preisblätter_WP VdS+UVV_StV (1).xlsx` | (Phase 2 Sprinkler+DGUV ortsveränd) | secondary | P2 |

**Łącznie batch extraction Phase 1**: 5,403 + 862 + 8,150 + 10,096 = **24,511 PDFów** do graf-ingest.

### 3.2 Pipeline ekstrakcji (universal, parametryzowany per Gewerk)

```
PDF (24,511)
   ↓
[Dispatch by MA-code → Gewerk]
   ↓
[Claude Haiku + extraction_prompt.txt per Gewerk]
   ↓
[Pydantic merkmale_schema validation per Gewerk]
   ↓
   ├── valid → FalkorDB upsert (graph per produkt)
   └── invalid → retry queue (Sonnet, larger context)
       ↓
       ├── valid → upsert
       └── failed → manual review queue (~5%)
```

**Estymata czasu**:
- Haiku: ~30s/PDF × 24,511 / 10 parallel workers = **~20h**
- Sonnet retry (5%): ~60s × 1,225 / 5 parallel = **~4h**
- Manual review: ~1% = ~250 raportów (1-2 dni pracy)

→ Plan: batch overnight w KW18 (4-5 nocy), gotowy graph w KW19.

### 3.3 Universal graph schema (per produkt, izolowany graf)

```cypher
// Universal entities (we wszystkich grafach)
(:Objekt {id, adresse_plz, adresse_strasse, name, branche})
(:Anlage {id, gewerk: "blitzschutz"|"rlt"|"dguv_v3",
          baujahr, hersteller, typ, ...gewerk_specific_props})
(:Pruefbericht {id, datum, typ: "WP"|"PI"|"PM"|"BG"|"WPBA"|"EPBA",
                auftrags_nr, equipment_nr, naechste_pruefung,
                ma_code, source_pdf})
(:Sachverstaendiger {id, name, niederlassung_id})
(:TUEV_Niederlassung {id, name, adresse, lat, lon})
(:Mangel {id, kategorie, einstufung: 1|2|3|H, beschreibung})
(:Standort {id, name, plz, lat, lon})  // address resolution

// Per-Gewerk extensions (przykłady)
// Blitzschutz:
(:Messstelle {id, nummer, wert_ohm, position_text})
(:Schutzklasse {id, name, beschreibung})
(:Erdungsanlage {id, typ: "A"|"B", material})

// RLT:
(:Filterklasse {id, name: "ISO ePM 2,5 65%"})
(:Probe {id, medium, kbe_pilze, kbe_bakterien, entnahmeort})
(:Brandschutzklappe {id, zulassung, hersteller, zugaenglichkeit})

// DGUV V3:
(:Stromkreis {id, bezeichnung, kabel_typ, sicherung_a,
              fehlerschleife_ohm, riso_mohm, rcd_ms})
(:Verteilung {id, typ: "NSHV"|"HV"|"UV", standort_text})
(:Installationskategorie {id, kat: 1-5, flaechenfaktor})

// Universal relations
(Objekt)-[:HAT_ANLAGE]->(Anlage)
(Anlage)-[:LIEGT_IN]->(Standort)
(Pruefbericht)-[:PRUEFT]->(Anlage)
(Pruefbericht)-[:ERSTELLT_VON]->(Sachverstaendiger)
(Sachverstaendiger)-[:ARBEITET_AT]->(TUEV_Niederlassung)
(Pruefbericht)-[:ZEIGT_MANGEL]->(Mangel)
(Anlage)-[:HAT_MESSSTELLE]->(Messstelle)        // Blitz
(Anlage)-[:HAT_FILTERKLASSE]->(Filterklasse)    // RLT
(Anlage)-[:HAT_STROMKREIS]->(Stromkreis)        // DGUV V3
```

**Stats docelowe per graf** (po pełnym ingestcie):

| Graph | Objekt | Anlage | Detail entity | Mangel |
|---|---|---|---|---|
| blitzschutz | ~3,500 | ~5,400 | ~95,000 Messstelle | ~22,000 |
| rlt | ~6,000 | ~9,000 | ~25,000 Filter+Probe+BSK | ~30,000 |
| dguv_v3 | ~6,500 | ~10,000 | ~150,000 Stromkreis | ~35,000 |

### 3.4 Pricing engine (uniwersalny executor)

```python
class PricingEngine:
    def calculate(self, gewerk: Gewerk, merkmale: BaseModel) -> Angebot:
        rules = gewerk.pricing_rules

        # 1. Grundkosten (LPV Teil A — wspólne dla wszystkich Gewerk)
        grund = self._grundkosten(merkmale, rules.estimate_pruef_tage(merkmale))

        # 2. Prüfkosten (LPV Teil B — per Gewerk)
        pruef = rules.pruefkosten(merkmale)

        # 3. Reisekosten (LPV Teil A — wspólne, depend od Standort)
        reise = self._reisekosten(merkmale.adresse, gewerk.preferred_standorte)

        # 4. Berichterstellung (LPV Teil A — z heurystyką per Gewerk)
        bericht = rules.berichtskosten(merkmale)

        # 5. Zuschläge (LPV Teil A)
        total = grund + pruef + reise + bericht
        for zuschlag in rules.zuschlaege(merkmale):
            total *= (1 + zuschlag.percent)

        # 6. Confidence + similar lookup (graph)
        confidence = self._validate_against_graph(gewerk, merkmale)
        similar = self._find_similar_anlagen(gewerk, merkmale, limit=3)

        return Angebot(
            gewerk=gewerk.name,
            total=total,
            breakdown={"grund": grund, "pruef": pruef, "reise": reise, "bericht": bericht},
            zuschlaege=[...],
            confidence=confidence,
            similar=similar,
            lpv_referenz=gewerk.lpv_referenz,
        )
```

**Common primitives** (pricing_primitives.py):
- `tagegeld(hours)` → 6/25/30€
- `kilometergeld(km, vehicle)` → 1,10/1,20€/km
- `stundensatz(level)` → 180/208/239/265/320€
- `vereinsmitglied_zuschlag()` → +20% (Audi-logic)
- `eilzuschlag()` → +25%
- `nearest_tuev_standort(adresse)` → wybór z 20+ Niederlassungen

---

## 4. API endpoints (per produkt + shared)

### 4.1 Per-produkt routery

```
POST /api/blitzschutz/calculate
POST /api/blitzschutz/anfrage/parse
GET  /api/blitzschutz/anlage/{id}
GET  /api/blitzschutz/stats
GET  /api/blitzschutz/validate?sample=50

POST /api/rlt/calculate
POST /api/rlt/anfrage/parse
GET  /api/rlt/anlage/{id}
GET  /api/rlt/stats
GET  /api/rlt/validate

POST /api/dguv-v3/calculate
POST /api/dguv-v3/anfrage/parse
GET  /api/dguv-v3/anlage/{id}
GET  /api/dguv-v3/stats
GET  /api/dguv-v3/validate
```

### 4.2 Shared endpoints

```
POST /api/chat                  (multi-product coordinator: detect Gewerk z Anfrage)
POST /api/admin/ingest-pdf      (upload + auto-dispatch po MA-code)
GET  /api/health
GET  /api/products              (manifest 3 produktów + ich stats)
GET  /api/standorte             (TÜV Niederlassungen z lat/lon)
```

### 4.3 Smart chat — multi-product coordinator

```python
# Coordinator routing
"szkoła 35m × 12m, 35 Ableitungen, Würzburg" → blitzschutz
"Bürogebäude RLT Hygiene, 5000 m³/h, Filterklasse F7" → rlt
"Gewerbehalle 4800 m², DGUV V3 Wiederholung" → dguv_v3
"Ich habe 99 Berichte, was kann ich machen?" → meta-coordinator (cross-product)
```

LLM-based dispatcher (Haiku, &lt;500ms) → przekierowanie do właściwego pipeline. Multi-product Anfrage (np. "Schule + RLT-Inspektion") → split na 2 calls + connected response.

---

## 5. Frontend

### 5.1 Strony

```
/                           — landing, 3 produkty + stats
/[product]                  — home produktu (stats per Gewerk)
/[product]/anfrage          — formularz Merkmale (auto-generated z schema)
/[product]/angebot/[id]     — wynik + breakdown + PDF export
/[product]/chat             — conversational UI (shared component)
/[product]/admin            — upload Prüfberichte
/admin                      — cross-product (graph stats, validate runs)
```

### 5.2 Komponenty (schema-driven, shared między 3 produkty)

| Komponent | Funkcja | Źródło config |
|---|---|---|
| `<KalkulatorForm gewerk={"blitzschutz"} />` | Auto-generated form z Pydantic schema | `merkmale.py` |
| `<AngebotCard breakdown={...} />` | Offer card w stylu TÜV | shared |
| `<ConfidenceBadge level={...} />` | Veit-angle Risk Score | shared |
| `<SimilarAnlagen results={...} />` | "3 podobne raporty z naszej bazy" | graph query |
| `<ChatPanel gewerk={...} />` | SSE streaming z coordinator | shared |
| `<PriceBreakdown gewerk={...} items={...} />` | LPV-style breakdown (Grund/Pruef/Reise/Bericht) | per-Gewerk template |
| `<MesswertTable />` | Blitzschutz: Messstellen [Ω] | Blitz only |
| `<FilterklasseSelect />` | RLT: ISO ePM filter classes | RLT only |
| `<StromkreisTable />` | DGUV V3: per Stromkreis Messwerte | DGUV V3 only |

### 5.3 Design system
- Kolory: TÜV-blue `#0046ad`, accent `#003080` (z timeline.html)
- Font: DM Sans body + JetBrains Mono numbers
- Light theme (jak dashboard.html w Desktop/TUEV)
- **No full TÜV StyleGuide** w POC (Veit 10.04: fokus na funkcjonalność)
- Polish na komponenty per Gewerk dopiero w KW20-22

---

## 6. Validation strategy

### 6.1 Golden sets per produkt

| Produkt | Golden set | Liczba | Match target |
|---|---|---|---|
| Blitzschutz | `Blitzschutz_StV.xlsx` | 325 Anlagen z realnymi cenami | ±10% na ≥80% |
| RLT | Vorlage `GT RLT` + `GT Hygiene` sheets + MUC `VDI 6022` (80×11) | ~150 derived examples | ±15% na ≥70% |
| DGUV V3 | Gersthofen (1,393 LV pozycji) + Audi 059E (74×48 GAEB) | ~50 reference cases | ±15% na ≥70% |

### 6.2 Process walidacji
- Każdy Gewerk implementuje `golden_set_loader()` → list[(merkmale, real_price, source)]
- `engine.validator.run(gewerk, sample=N)` → ValidationReport
- Cron nightly: `cd /backend && python -m engine.validator --all` → JSON report w `/validation_history/<date>.json`
- `/admin/validate` UI shows historical match rates per produkt

### 6.3 Edge cases (must not crash)
- Schön Klinik 178 Ableitungen multi-Teilgebäude (Blitzschutz Phase 2, ale stress test już Phase 1)
- Gersthofen 1,393 pozycji LV (DGUV V3 max-detail)
- Wohnhochhaus 17 pięter z 59 Mängel (MA510 — Phase 2, ale graph schema musi obsłużyć)
- 0-Mangel raport (Business Campus MA507-3)

### 6.4 Outlier analysis
- Top 10 outlierów per produkt → manualny review co tydzień
- Pattern detection: czy outliers grupują się per Standort, per Gebäudetyp, per zakres rozmiaru?
- Findings → tickets do Pauscha ("czy Apleona-StV ma hidden Rabatte których LPV nie pokazuje?")

---

## 7. Milestones (KW16 → KW27)

### KW16 (16-20.04) — Foundation + demo dziś za 4 dni
- **M0** · 16-19.04: Backend refaktor (common/ + engine/ + products/), 3 puste Gewerk-stubs
- **M1** · pn 20.04 8:00-10:00 **Projektregeltermin demo** — pokazać:
  - Dashboard danych (`Desktop/TUEV/dashboard.html`)
  - Plan implementacji (ten dokument)
  - Sekcja Blitzschutz na dashboardzie z inwentaryzacją
  - Pytania do testerów (Kai Eiden, Markus Burgey, Holger Weiss)
  - **NIE obiecywać działającego kodu** (mamy tylko 4 dni roboczych)

### KW17 (21-25.04) — Engine core
- M2.1: Common layer + engine base classes działają
- M2.2: Blitzschutz Gewerk: pricing_rules.py + golden_set.py loader
- M2.3: First `/api/blitzschutz/calculate` na hardcoded test merkmale
- M2.4: Pierwsza walidacja przeciwko 50 Anlagen z 325 StV (sample) → baseline match_rate

### KW18 (28.04-02.05) — Extraction batch + 2 nowe produkty
- M3.1: PDF extraction pipeline (Haiku + Sonnet retry) działa na 50 PDFów MA570
- M3.2: Batch overnight: pełny ingest 5,403 MA570 → blitzschutz graph
- M3.3: RLT Gewerk: pricing_rules + extraction prompt + golden_set
- M3.4: DGUV V3 Gewerk: pricing_rules + extraction prompt + golden_set

### KW19 (05-09.05) — Pełny graph + multi-product coordinator
- M4.1: Batch ingest RLT (8,150+862 = 9,012 PDFów) → rlt graph
- M4.2: Batch ingest DGUV V3 (10,096 PDFów) → dguv_v3 graph
- M4.3: Chat coordinator (multi-product dispatch)
- M4.4: Frontend `/blitzschutz` + `/rlt` + `/dguv-v3` MVP routes

### KW20-21 (12-23.05) — UX + Anfrage parsing
- M5.1: Anfrage natural-language parser per produkt
- M5.2: PDF export oferty w stylu TÜV (per produkt)
- M5.3: Similar Anlagen graph queries
- M5.4: Confidence scoring + Veit-angle Risk Score

### KW22 (26-30.05) — UAT z testerami Regeltermin
- M6.1: Internal UAT (Piotr + Slava)
- M6.2: Live UAT z 3-4 testerami z Projektregeltermin (Kai Eiden, Markus Burgey, Sarah Pfilf)
- M6.3: Iteration na feedback

### KW23-24 (02-13.06) — Validation + Polish
- M7.1: Walidacja na pełnym 325 Blitzschutz_StV golden set
- M7.2: RLT validation na Vorlage GT-sheets references
- M7.3: DGUV V3 validation na Gersthofen + Audi 059E
- M7.4: Outlier analysis + iteracja pricing rules

### KW25-26 (16-26.06) — Staging + rehearsal
- M8.1: Deployment MING Cloud (POC)
- M8.2: Performance tuning (p95 &lt; 2s)
- M8.3: Abnahme z Pauschem
- M8.4: 2× dry run z Veitem

### KW27 · **06.07.2026** — **Abteilungsleitertagung LIVE DEMO**
- Veit prezentuje 3 produkty (Blitzschutz + RLT + DGUV V3)
- Live Anfrage → Angebot w &lt; 60s per produkt
- Match rate report na 325 StV + RLT + DGUV golden sets
- Success → Phase 2 green-light (6-stellig budget Matthias, +8 produktów MA438/441/501/510/555/560/572/574)

---

## 8. Risk register

| # | Ryzyko | Prawd. | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Ekstrakcja Merkmale &lt;70% trafność | Średnie | Wysoki | Haiku→Sonnet retry, manual ground truth 100 raportów per produkt, validation feedback loop |
| R2 | RLT match_rate &lt;70% (słabszy golden set) | Średnie | Średni | Wczesny pivot: jeśli &lt;60% w KW19, rozszerzyć golden set z manual TÜV-input |
| R3 | DGUV V3 graph complexity (per-Stromkreis) | Średnie | Wysoki | Stress test na Gersthofen (1,393 pozycji) wcześnie w KW19 |
| R4 | Veit AI-sceptyk blokuje UAT | Średnie | Wysoki | Pausch sponsor, Kai Eiden champion proxy. Demo 20.04 osłabia sceptyzm |
| R5 | MING Cloud outage przed demo | Niskie | Wysoki | Local backup deploy, Azure tenant ready (Fischermann) |
| R6 | MING dług 108.5k blokuje hosting | Średnie | Wysoki | Oddzielny rozdziel rozmów z Matthiasem (memory: ming-payment-crisis) |
| R7 | 20.04 demo nie-gotowy | Wysokie | Średni | NIE pokazujemy kodu — pokazujemy plan + dashboard + pytania (mamy 4 dni!) |
| R8 | Scope creep — Piotr dodaje 4. produkt w trakcie | **Wysokie** | Wysoki | Sztywna lista §2.4, coach-mode (memory: user_psychology_coaching), Veit-3 = scope sealed |
| R9 | Multi-product coordinator źle dispatchuje | Średnie | Średni | Test set z 50 Anfragen per produkt, fallback do menu wyboru w UI |
| R10 | Performance: 24,511 raportów ingest crashuje FalkorDB | Niskie | Wysoki | Batch po 500, monitor memory, persistent storage z snapshots |
| R11 | TÜV nie da realnego Anfrage na demo | Niskie | Średni | Mamy własne historyczne Anfragi z PDFów — replay |
| R12 | Confidence scoring źle calibruje (false flags) | Średnie | Niski | Iteracja po UAT, threshold tunable per Gewerk |

---

## 9. Pytania do alignment (przed startem kodu)

1. **Refaktor `/api/*` → `/api/smartcal/*`**: OK na drobny breaking change w istniejącym demo?
2. **Multi-graph FalkorDB**: 4 osobne grafy (smartcal + 3 produkty) OK, czy szukamy tańszej hostingu (jeden graf z multi-label)?
3. **Frontend dynamic `[product]` route**: szybsze niż 3× duplikacja, ale wymaga schema-driven forms — OK?
4. **Batch extraction overnight**: 4-5 nocy w KW18, czy wolimy ukrytą cron-job ekstrakcję ciągłą?
5. **PDF export template**: minimal nasz design (zgodne z Veit 10.04) czy próbujemy minimalnie odwzorować TÜV-StyleGuide?
6. **Cross-product chat coordinator**: budujemy razem z 3 produktami w KW19 czy odkładamy do KW20+?
7. **UAT (KW22)**: zapraszamy testerów na Teams call (live demo + feedback) czy dajemy im access do staging na 1-2 dni?
8. **Performance budget**: p95 &lt; 2s OK, czy potrzebujemy mocniejszych SLO (np. p99 &lt; 3s)?

---

## 10. Plan na najbliższe 4 dni (do demo 20.04)

| Dzień | Działanie | Output |
|---|---|---|
| **Cz 16.04** (dziś) | Plan zatwierdzony, alignment na pytania §9 | PLAN_BLITZSCHUTZ.md committed |
| **Pt 17.04** | Backend refaktor: common/ + engine/ + products/{blitzschutz,rlt,dguv_v3}/ stubs | Tests pass, 3 puste produkty registered |
| **Pt 17.04** | Pre-call z Pauschem 15min: zwęzić scope demo, ile czasu mamy w 8-10h slot, kto z 11 testerów na czym focus | Notatki + agenda demo |
| **Sb-Nd 18-19.04** | Sekcja "Blitzschutz" na dashboardzie z bullet-pointed planem (tym z punktów §2.1, §3.3, §4.1, §6.1) | Polished demo material |
| **Pn 20.04 8:00-10:00** | **Projektregeltermin demo** — plan + dashboard + pytania | Validation: które 5 pytań testerzy pomogą rozstrzygnąć |

---

## 11. Referencje

- **Dataset dashboard**: `~/Desktop/TUEV/dashboard.html`
- **Pricing details (pre-dataset)**: `/projects/tuev/BLITZSCHUTZ_PLAN.md` (577 lines, dużo nadal aktualne)
- **PRD demo**: `/projects/tuev/PRD.md`
- **12W Timeline (poprzednia wersja)**: `/projects/tuev/PROJECT_PLAN_12W.md`
- **Memory keys**:
  - `smartcal-eg-delivery-april2026.md` — stan projektu + dane wejściowe
  - `tuev-projektregeltermin-20april2026.md` — pn 20.04 demo
  - `tuev-sued-deepdive.md` — stakeholderzy (Veit, Pausch, Pfeifer)
  - `matthias-minglabs-relationship.md` — MING/IP dynamics
  - `feedback_pitch_augment_not_replace.md` — pitch framing (uzbrajamy, nie zastępujemy)
  - `pricing-model-tic.md` — value-based pricing
  - `user_psychology_coaching.md` — coach-mode dla Piotra
