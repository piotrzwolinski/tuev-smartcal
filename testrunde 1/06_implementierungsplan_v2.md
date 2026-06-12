# Implementierungsplan v2 + Teststrategie (ersetzt 04_implementierungsplan.md)

**Ziel**: Testrunde 2 (~19./20.06 mit Pausch) → AL-Tagung 30.06
**Basis**: Snapshot-Commit `fdcf714`, Branch `v2-pricing`
**Test-Baseline**: 364 Tests in 10 Dateien (blitz 63, dguv 64+49, kalibrierung 67, rlt 63, zusatz 36, agent 10, graph 7, api 3, e2e 2)

---

## Architektur-Entscheidungen (vorab)

### AE-1: Pruefart-Enum statt neuer Produkte
Ein Elektro-Produkt (dguv_v3) mit Diskriminator — deckt Veit P1 („Prüfart identifizieren") ab:
```python
class Pruefart(str, Enum):
    DGUV_ORTSFEST = "dguv_ortsfest"           # MA507/501
    DGUV_ORTSVERAENDERLICH = "dguv_ortsv"     # MA560
    VDS = "vds"                                # MA505 only
    DGUV_PLUS_VDS = "dguv_plus_vds"           # Kombi (Pausch: VdS + 50%)
```
Löst Fix 3 (VdS-Only) UND Fix 5 (MA560) mit einem Konzept. Kein neues Gewerk, kein neuer Graph.

### AE-2: gesamtflaeche_m2 wird Optional
```python
gesamtflaeche_m2: Optional[float] = Field(None, ge=1, le=1_000_000)
anzahl_betriebsmittel: Optional[int] = Field(None, ge=1)
```
+ `model_validator`: Pflicht-Inputs je Pruefart:
- ortsfest/vds/kombi → flaeche ODER uv-anzahl (UV-only → Flächen-Schätzung UV×400m², Confidence ↓)
- ortsv → anzahl_betriebsmittel
**Rückwärtskompatibel**: alle bestehenden Konstruktionen mit flaeche bleiben gültig. `vds_pruefung: bool` bleibt als deprecated Alias (Validator mappt → DGUV_PLUS_VDS).

### AE-3: Shared Math-Helper gegen Engine-Drift
Es gibt ZWEI Engines (`pricing_rules.py` + `graph_pricing_engine._pruef_dguv`) mit duplizierter Formel. Neue Regel: Mathe lebt in `pricing_rules.py` als pure functions; Graph-Engine liest Raten/Kurven aus dem Graph und ruft dieselben Helper. Parity-Test (existiert in test_dguv_v3.py:299) wird auf alle Pruefarten erweitert.

### AE-4: Alle neuen Parameter graph-tunable
Degressionskurven, BM-Sätze, Kleinauftrag-Schwellen → Graph-Nodes mit Python-Fallback (bestehendes Muster `_g_*`). EFI (Bachmeier/Römerkamp) kann kalibrieren ohne Deploy.

---

## Phase 0: Fundament + Baseline (Tag 1 — Mi 11.06)

| # | Task | Dateien |
|---|------|---------|
| 0.1 | Branch `v2-pricing` von `fdcf714` | — |
| 0.2 | **Baseline-Snapshot**: `scripts/golden_baseline.py` — läuft alle Golden Sets (316 Blitz-Anlagen + DGUV-Set), schreibt `tests/baseline_v1.json` mit per-Case Delta. Committed VOR jeder Änderung | scripts/, tests/ |
| 0.3 | Schema: Pruefart-Enum, anzahl_betriebsmittel, flaeche Optional + Validator + vds_pruefung-Alias | merkmale.py |
| 0.4 | None-Guards: alle `getattr(m, "gesamtflaeche_m2", 0)` Stellen normalisieren (None → 0) | beide Engines |
| 0.5 | Graph-Nodes: Flaechenstaffel (DGUV+VdS Kurven), KAT_7 (5.42), KAT_8 (7.68), BMPreis, Kleinauftrag | graph_schema.cypher |
| 0.6 | `load_graph.py` lokal ausführen + Deployment-Checkliste ergänzen | — |

**Exit-Gate 0**: alle 364 Tests grün (Schema-Änderung ist rückwärtskompatibel). Baseline-JSON committed.

## Phase 1: Degression — Fix 1 (Tag 2 — Do 12.06)

Kurven (NBG Kalkulationshilfen, graph-tunable):
```python
DEGRESSION_DGUV = [(0, 0.80), (2000, 0.80), (4000, 0.60), (6000, 0.50), (10000, 0.40), (25000, 0.30)]
DEGRESSION_VDS  = [(0, 1.00), (2000, 0.90), (4000, 0.80), (6000, 0.70), (10000, 0.50), (25000, 0.35)]
```
⚠ DGUV-Faktor 0.8 schon ab 0 m² senkt auch kleine Objekte — **EFI-Review-Punkt** (evtl. erste Stufe 1.0).

| # | Task |
|---|------|
| 1.1 | `flaechenkosten_degressiv(flaeche, rate, kurve)` — bandweise Summe, pure function |
| 1.2 | Einbau in `dguv_pruefkosten()` + `_pruef_dguv()` (Helper-Aufruf, Trace pro Band für Quellennachweis-UI) |
| 1.3 | **Bewusste Test-Updates**: test_dguv_v3.py:77-88,131 (Exakt-Asserts der Linear-Formel) → neue Erwartungswerte, im Commit dokumentiert |
| 1.4 | Neu `test_degression.py`: Band-Mathe handgerechnet, Stetigkeit an Grenzen, Monotonie (Gesamt steigt, effektive Rate fällt), Engine-Parität |

**Exit-Gate 1**: ZIP-1 (Hipp) rechnet ~7.3k statt 11.9k · Golden-Delta vs baseline_v1.json: kein Case >2% schlechter ohne dokumentierten Grund.

## Phase 2: VdS eigene Logik + Routing — Fix 2+3 (Tag 3 — Fr 13.06)

| # | Task |
|---|------|
| 2.1 | `vds_pruefkosten()` echt: Grundpreis + flaechenkosten_degressiv(VDS-Kurve) + Verteilungen; Stundensatz-Referenz 208€ im Trace; kVA-Zuschlag = offene Frage Pausch |
| 2.2 | Dispatch in `_pruef_dguv` → per Pruefart: ortsfest→DGUV / vds→**NUR VdS, keine DGUV-Basis** / kombi→VdS×1.5 (Pausch-Regel) / ortsv→Phase 3 |
| 2.3 | `dguv_plus_vds_pruefkosten()` nutzt echte VdS-Funktion; `VDS_ID_PAUSCHALE` endlich verwendet oder entfernt |
| 2.4 | UI/Labels: VdS-Only zeigt „VdS 2871 Prüfkosten", kein DGUV-Block; Addon-Block nur bei Kombi |
| 2.5 | Neu `test_vds.py`: vds≠dguv für gleiche Merkmale · VdS-Only-Breakdown ohne DGUV-Basis · kombi==vds×1.5 · Trace-Referenzen |

**Exit-Gate 2**: ZIP-1 ±20% · Weiß-Szenario (VdS-only) erzeugt EINEN Block statt 8.174€-Doppelung.

## Phase 3: MA560 per-Device — Fix 5 (Tag 4 — Mo 16.06)

| # | Task |
|---|------|
| 3.1 | `bm_pruefkosten(n)` = Grundpauschale (200€) + n × Satz (9.50€), Staffel ab 500 — alles Graph-Params |
| 3.2 | Pfad ortsv: Grundkosten=0 (in Pauschale enthalten), Bericht inklusive, Reise standard; `estimate_pruef_tage` = n/200 |
| 3.3 | Kalibrierung gegen T04 (114→~1.283 vs 1.217), T10 (545→~5.378 vs 5.341); Sätze tunen |
| 3.4 | Neu `test_ma560.py`: Mathe · Merkmale gültig OHNE flaeche · T04/T10 ±10% · 20-BM-Kindergarten → rechnet (keine Ablehnung) |

**Exit-Gate 3**: T10 ±10% · T04 bleibt PASS (aus richtigem Grund).

## Phase 4: Kleinauftrag + baurechtlich + Referenz-Blend — Fix 6+7+Bonus (Tag 5 — Di 17.06)

| # | Task |
|---|------|
| 4.1 | Kleinauftrag-Erkennung: (UV+HV+NSHV ≤ 2 UND flaeche ≤ 300) ODER Einzelkomponente → Prüfkosten = max(MIN, Stunden×180€); Grundkosten reduziert (Param), Bericht=klein. Schwellen graph-tunable, EFI-Review |
| 4.2 | `baurechtlich`-Audit: DOC-4 zeigte Ordnung 242€ auf normalem Blitz-WP — Flag nur bei explizitem Baurecht/Sonderbau; Blitz-Chat-Prompt ergänzen |
| 4.3 | Referenz-Blend: wenn fortgeschrieben + `referenz_vergleichbar` (neue Frage, Veit P9) → **separate sichtbare Breakdown-Zeile** „Referenzpreis-Anpassung", Gewicht 0.4 (≤3 Jahre), Cap ±30%. Kein verstecktes Blending |
| 4.4 | Neu: `test_kleinauftrag.py`, `test_referenz_blend.py`; Assert DOC-4-Grundkosten 330€ statt 572€ |

**Exit-Gate 4**: ZIP-3 (Schaltschrank) ~450-550€ · C-5 (Referenz 545) zieht Ergebnis sichtbar Richtung Referenz.

## Phase 5: Chat-Coordinator — S1+S2+RV+Guards (Tag 6 — Mi 18.06)

| # | Task |
|---|------|
| 5.1 | COORDINATOR_SYSTEM neu: (1) Pruefart-Erkennung zuerst (Veit P1), (2) gleichwertige Inputs — m² ODER UV ODER BM ODER Einzelkomponente → sofort calculate, (3) „Krankenhaus ist Kat 2!"-Zeile raus → Auto-Mix 70% Kat2 / 30% Kat7 |
| 5.2 | UV-only-Pfad: UV ohne m² → Schätzung UV×400m² (Graph-Param, im Trace als Schätzung, Confidence ↓) |
| 5.3 | **RV-Frage**: „Besteht ein Rahmenvertrag?" → `rv_vorhanden` → Warnbanner „Kalkulation = LPV-Niveau, RV-Konditionen typisch 30-60% darunter" (keine Rabatt-Modellierung) |
| 5.4 | Scope-Guards: MA510 Baurecht / Multi-Produkt → ehrliche Meldung statt falscher Zahl · MA560 nie ablehnen |
| 5.5 | Cross-Sell-Filter: `_add_cross_sell` mit `WHERE c.source_produkt = $produkt` (D11) + RLT-Empfehlung bei ELT raus |
| 5.6 | `has_minimum` in chat.py: per-Pruefart-Minimum statt hartem m²-Gate |
| 5.7 | Neu `test_chat_routing.py` (LLM **gemockt**, deterministisch): „545 BM RZ"→ortsv ohne m²-Frage · „48 UV, 4 Gebäude"→calculate · „1 Schaltschrank"→Kleinauftrag, keine Mitarbeiter-Frage · „nur VdS"→pruefart=vds · „20 Geräte Kindergarten"→rechnet · RV-Frage gestellt |

**Exit-Gate 5**: alle 6 S1-Beschwerde-Szenarien aus Runde 1 laufen ohne m²-Nagging durch (Skript-Replay).

## Phase 6: Validierung + Golden-16 + Report (Tag 7 — Do 19.06)

| # | Task |
|---|------|
| 6.1 | Neu `tests/test_testrunde1_golden.py`: 16 Cases parametrisiert (merkmale, real, toleranz, verdict). Out-of-Scope/Bad-Ref als `xfail(reason=...)`: T06 (Referenz defekt), T09 (Multi=MVP), T05 (Referenz defekt). RV-Cases (DOC-1, ZIP-2, PPT-4, DOC-4): Assert = **Warnbanner vorhanden**, nicht Preis-Match |
| 6.2 | Volle Regression: 364 alt + ~80 neu grün; Golden-Delta-Report vs baseline_v1.json |
| 6.3 | E2E-Smoke: 5 Demo-Kandidaten als geskriptete Chat-Flows (Playwright, Screenshot je Case) |
| 6.4 | `testrunde 1/07_validierung_v2.md`: Vorher/Nachher-Tabelle aller 16 |
| 6.5 | Pausch-Call: Kurven-Review (EFI), T05/T06-Referenzen, Demo-Auswahl |

Fr 20.06 = Buffer + Nachbesserung aus Call.

---

## Teststrategie — der Anti-Regressions-Vertrag

1. **Baseline-first**: `baseline_v1.json` (Golden-Deltas Stand v1) wird VOR der ersten Änderung committed. Jeder spätere Lauf vergleicht dagegen: **kein Case >2% schlechter ohne dokumentierten Grund im Commit.**
2. **Zwei-Engine-Parität**: `breakdown.pruef == <python_rules>(m)` für alle 4 Pruefarten (Erweiterung des bestehenden Tests test_dguv_v3.py:299).
3. **Bewusste vs. zufällige Test-Änderung**: Exakt-Asserts der Linear-Formel (test_dguv_v3.py:77-88,131) werden auf neue Werte AKTUALISIERT (Hand-Rechnung im Test-Kommentar) — niemals auf „approx irgendwas" aufgeweicht.
4. **Golden Sets als Regressions-Netz**: 316 Blitz + DGUV-Set laufen nach jeder Phase (CI-Reihenfolge: unit → parity → golden-regression → testrunde-golden → e2e-smoke).
5. **Testrunde-16 = Abnahme-Suite**: die realen Fälle aus Runde 1 sind die Akzeptanzkriterien für Runde 2; xfail-Markierungen machen Out-of-Scope explizit statt unsichtbar.
6. **Chat deterministisch testen**: Routing-Tests mit gemocktem LLM-JSON; Live-LLM nur in separater Suite (Muster test_e2e_llm_judge existiert).
7. **Neue Fälle absichern**: jede neue Funktion bringt eigene Unit-Suite (degression/vds/ma560/kleinauftrag/blend/chat_routing ≈ 80 neue Tests).

## Risiken

| Risiko | Mitigation |
|--------|-----------|
| flaeche Optional → None-Crashes in Engines | Phase 0.4 None-Guards + Tests, die Merkmale OHNE flaeche konstruieren |
| Degression bricht Exakt-Tests | eingeplant: bewusste Updates mit Hand-Rechnung (Phase 1.3) |
| Engine-Drift (2 Implementierungen) | Shared Helper (AE-3) + Parity-Tests |
| NBG-Faktor 0.8 ab 0 m² senkt auch kleine Objekte | EFI-Review-Punkt; Kurve graph-tunable, ggf. erste Stufe 1.0 |
| UV→m²-Schätzung (×400) unvalidiert | Confidence-Penalty + Trace-Kennzeichnung + EFI |
| MA560-Sätze aus n=2 Referenzen | Kalibrierungs-Task 3.3 + Pausch um weitere MA560-Abrechnungen bitten |
| Haiku-Prompt-Umbau destabilisiert Chat | gemockte Routing-Tests + 6-Szenario-Replay-Skript (Exit-Gate 5) |
| Graph-Nodes fehlen auf Fly.io | Deployment-Checkliste: load_graph nach Deploy (Phase 0.6) |
| Referenz-Blend kaschiert Kalkulationsfehler | separate sichtbare Zeile + Cap ±30% + abschaltbar |

## Offene Fragen an Pausch/EFI (Call 19./20.06)

1. Degression erste Stufe: 0.8 (NBG wörtlich) oder 1.0 bis 2.000 m²?
2. VdS: kVA-Zuschlag nötig (Hipp 8.000, K&B 16.800 kVA)? Eigene Kat-Raten oder DGUV-Raten + VdS-Kurve?
3. MA560: 9.50€+200€ ok? Weitere echte Abrechnungen für Kalibrierung?
4. Kleinauftrag: Mindest-Pauschale? Stundenschätzung je Komponente?
5. T05 (174,80€) / T06 (220€): korrekte Referenzen?
6. Krankenhaus-Mix 70/30 Kat2/Kat7 plausibel?
7. UV-only: 400 m²/UV als Schätzfaktor ok?

## Aufwand & Termine

```
Mi 11.06  Phase 0  Fundament + Baseline          Gate: 364 grün
Do 12.06  Phase 1  Degression                    Gate: Hipp ~7.3k, Golden ok
Fr 13.06  Phase 2  VdS Logik + Routing           Gate: VdS-only 1 Block
Mo 16.06  Phase 3  MA560 per-Device              Gate: T10 ±10%
Di 17.06  Phase 4  Kleinauftrag + Blend + Flag   Gate: Schaltschrank ~500
Mi 18.06  Phase 5  Chat-Coordinator              Gate: 6 Szenarien sauber
Do 19.06  Phase 6  Validierung + Report          Gate: Pass-Rate-Report
Fr 20.06  Buffer + Pausch-Feedback einarbeiten
KW26      Demo-Prep AL-Tagung (30.06–02.07)
```
