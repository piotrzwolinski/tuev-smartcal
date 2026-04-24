# SmartCal: RLT + DGUV V3 completion + Blitzschutz calibration

## Context

3 produkty obiecane Veitowi: Blitzschutz (SHIPPED), RLT (stub), DGUV V3 (stub).
Batch 2 danych (20-22.04): 28.674 Versand-Berichte z Finanzdaten + Inspektionspflichten + CRM PLZ.
Deadline: KW17 = RLT, KW18 = DGUV V3, KW27 = Abteilungsleitertagung live demo.

Architektura jest product-agnostic (Gewerk base class). Każdy produkt = 7 plików.
Blitzschutz to reference implementation — RLT i DGUV V3 replikują ten sam pattern.

## Stan per produkt

| Plik | Blitzschutz | RLT | DGUV V3 |
|---|---|---|---|
| `__init__.py` | done | done (brak zuschlaege/validate) | done (brak zuschlaege/validate) |
| `merkmale.py` | done | done (30 pól, 2 warianty) | done (18 pól, 5 Kat) |
| `pricing_rules.py` | done | done (HYG+GARAGE) | done (250€+m²×Kat) |
| `golden_set.py` | done (316 Anlagen) | **STUB** → Versand 13.894 | **STUB** → Gersthofen+VdS+Audi |
| `chat.py` | done (245 lines) | **BRAK** | **BRAK** |
| `graph_schema.py` | done (73 nodes) | **BRAK** | **BRAK** |
| `extraction_prompt.txt` | done | **STUB** | **STUB** |

## Plan implementacji

### KW17 (pon-pt): RLT kompletny

**Dzień 1-2: Core files**

1. `backend/products/rlt/chat.py` (~220 lines) — NEW
   - Template: `blitzschutz/chat.py`
   - COORDINATOR_SYSTEM: detect variant (hygiene VDI 6022 vs garage GaStellV)
   - Minimum: variant + anzahl_pruefbereiche (HYG) lub stellplaetze/flaeche (GARAGE)
   - Rückfragen: Ventilatoren? BSK? Garagentyp? Filterklasse?
   - Cross-sell: Blitzschutz + gleiche Begehung

2. `backend/products/rlt/graph_schema.py` (~200 lines) — NEW
   - Template: `blitzschutz/graph_schema.py`
   - ~50 nodes: 3 Produkt (HYG/GARAGE/STANDARD), 6 Grundpreis, 2 Zuschlag_Stk (Ventilator 170€, BSK 40€), 2 HYG-Kalk + shared (Grundkosten, Stundensätze, Reisekosten, Standorte)

3. `backend/products/rlt/extraction_prompt.txt` (~80 lines) — EXPAND stub
   - Variant detection logic + all RLTMerkmale fields

**Dzień 3: Zuschläge + Validate + Normalize**

4. `backend/products/rlt/pricing_rules.py` — ADD 2 functions
   - `rlt_zuschlaege()`: vereinsmitglied, eilzuschlag, erstpruefung
   - `rlt_validate_ranges()`: check bereiche/stellplaetze/ventilatoren/BSK in typical ranges

5. `backend/products/rlt/__init__.py` — MODIFY
   - Add zuschlaege() + validate_ranges() overrides
   - Fix extraction_prompt() to read from file

6. `backend/common/normalize.py` — ADD ~50 lines
   - `normalize_rlt_extracted()` + RLT_VARIANT_MAP, GARAGENTYP_MAP

**Dzień 4: Golden set + Blitzschutz calibration**

7. `backend/products/rlt/golden_set.py` (~120 lines) — REPLACE stub
   - Source: `441_419_Versand.xlsx` (13.894 rows)
   - `_classify_variant(eq_art)`: "Lüftung allgemein"→HYGIENE, "Lüft.Garage"→GARAGE
   - Filter: Faktura > 0 AND Faktura > Kosten (Stefan-Filter)
   - Target: ~200-500 golden set entries

8. `backend/scripts/calibrate_staffel.py` (~150 lines) — NEW
   - Load `57234_Versand.xlsx` → group by MS-range → median Faktura/MS per bucket
   - Compare vs current Staffeln (30/28/26/24€) → derive optimal rates
   - Update `blitzschutz/pricing_rules.py` STAFFEL + `graph_schema.py` Staffel nodes

**Dzień 5: Frontend + E2E validation**

9. `frontend/lib/products.ts` (~60 lines) — NEW
   - ProductConfig interface: id, name, subtitle, apiPrefix, suggestions, angebotLabels
   - 3 configs: blitzschutz, rlt, dguv_v3

10. `frontend/app/page.tsx` — MODIFY
    - `activeProduct` state, sidebar clickable, dynamic apiPrefix/suggestions/title
    - Product switch clears session

11. `frontend/components/AngebotPanel.tsx` — RENAME from BlitzschutzAngebotPanel
    - Accept ProductConfig prop, dynamic labels

12. E2E: start backend, test `/api/rlt/chat` + `/api/rlt/validate`

---

### KW18 (pon-pt): DGUV V3 kompletny

**Dzień 1-2: Core files** (identyczny pattern jak RLT)

13. `backend/products/dguv_v3/chat.py` (~230 lines) — NEW
    - Minimum: nutzung + gesamtflaeche_m2
    - Rückfragen: Installationskategorie? NEA? Verteilungen UV/HV/NSHV?
    - Cross-sell: Blitzschutz + RLT

14. `backend/products/dguv_v3/graph_schema.py` (~220 lines) — NEW
    - ~45 nodes: 1 Produkt, 5 Installationskategorie (1-5€/10m²), 3 Verteilung (UV/HV/NSHV), 2 Zuschlag (NEA/SV-NSHV) + shared

15. `backend/products/dguv_v3/extraction_prompt.txt` (~80 lines) — EXPAND stub

**Dzień 3: Zuschläge + Validate + Normalize**

16. `backend/products/dguv_v3/pricing_rules.py` — ADD 2 functions
    - `dguv_zuschlaege()` + `dguv_validate_ranges()` (m² vs nutzung ranges)

17. `backend/products/dguv_v3/__init__.py` — MODIFY (add overrides)

18. `backend/common/normalize.py` — ADD ~40 lines
    - `normalize_dguv_extracted()` + DGUV_NUTZUNG_MAP, NETZFORM_MAP

**Dzień 4: Golden set + Shared data**

19. `backend/products/dguv_v3/golden_set.py` (~150 lines) — REPLACE stub
    - 3 sources: Gersthofen (aggregate 1.393 Verteiler → ~30 Anlagen), VdS+UVV StV (375 Anlagen, filter UVV), Audi Ausschreibung
    - Target: ~50-100 entries

20. `backend/common/inspektionspflichten.py` (~80 lines) — NEW
    - Load Inspektionspflichten.xlsx → lookup by gewerk + gebäudetyp → Zyklus, Qualifikation
    - Used by chat coordinators for regulatory context

21. `backend/common/plz_niederlassung.py` (~60 lines) — NEW
    - Load CRM PLZ NL → `plz_to_niederlassung(plz)` → {nl, region, bereich}
    - Supplements geocode-based Standort lookup

**Dzień 5: Versand analysis + E2E**

22. `backend/scripts/versand_analysis.py` (~200 lines) — NEW
    - Blitzschutz: Erlös-h-Satz distribution, Staffel validation
    - RLT: Faktura per EQ Art, 208€/h vs reality (HYG), Grundpreis tiers vs reality (GARAGE)
    - Output: summary dict for next TÜV call

23. E2E: test `/api/dguv-v3/chat` + `/api/dguv-v3/validate` + cross-product

---

## Decyzje architektoniczne

- **GraphPricingEngine**: RLT i DGUV V3 używają `mode="python"` (default). Graph mode zostaje Blitzschutz-only. Generalizacja graph engine → KW19+ stretch goal.
- **Golden set RLT**: EQ Art z Versand IS taksonomia — nie potrzebujemy legendy sufixów od Stefana.
- **Golden set DGUV V3**: bez Versand budujemy z Gersthofen+VdS+Audi. Jak Stefan dosypie MA507 Versand → dodajemy.

## Stefan email (parallel track, nie blokuje)

| Pytanie | Kiedy odpowiedź | Akcja | Effort |
|---|---|---|---|
| Material-Taxonomia | nieistotne | EQ Art wystarczy | — |
| MA507 Versand | jeśli KW18 | dodatkowy golden set + kalibracja | 4h |
| PLZ→NL link | jeśli KW18 | plz_niederlassung.py integracja w chat | 2h |

## Weryfikacja

1. `curl POST /api/rlt/chat` — SSE stream z Rückfragen + kalkulacją
2. `curl GET /api/rlt/validate?sample=50` — match_rate@±15% ≥ 70%
3. `curl POST /api/dguv-v3/chat` — j.w.
4. `curl GET /api/dguv-v3/validate?sample=50` — match_rate@±15% ≥ 70%
5. Frontend: przełączanie produktów w sidebar, kalkulacja per produkt
6. Blitzschutz re-validation po Staffel calibration: match_rate@±10% improvement vs baseline

## Pliki do zmiany (pełna lista, 23 pozycje)

**NEW (13):**
- `backend/products/rlt/chat.py`
- `backend/products/rlt/graph_schema.py`
- `backend/products/dguv_v3/chat.py`
- `backend/products/dguv_v3/graph_schema.py`
- `backend/common/inspektionspflichten.py`
- `backend/common/plz_niederlassung.py`
- `backend/scripts/calibrate_staffel.py`
- `backend/scripts/versand_analysis.py`
- `frontend/lib/products.ts`
- `frontend/components/AngebotPanel.tsx`

**MODIFY (8):**
- `backend/products/rlt/__init__.py` (add overrides)
- `backend/products/rlt/pricing_rules.py` (add zuschlaege + validate)
- `backend/products/rlt/golden_set.py` (replace stub)
- `backend/products/rlt/extraction_prompt.txt` (expand)
- `backend/products/dguv_v3/__init__.py` (add overrides)
- `backend/products/dguv_v3/pricing_rules.py` (add zuschlaege + validate)
- `backend/products/dguv_v3/golden_set.py` (replace stub)
- `backend/products/dguv_v3/extraction_prompt.txt` (expand)
- `backend/common/normalize.py` (add RLT + DGUV normalizers)
- `frontend/app/page.tsx` (multi-product switching)

**CALIBRATE (2):**
- `backend/products/blitzschutz/pricing_rules.py` (Staffel rates)
- `backend/products/blitzschutz/graph_schema.py` (Staffel node prices)
