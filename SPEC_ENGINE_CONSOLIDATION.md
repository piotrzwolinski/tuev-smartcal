# SPEC: Engine-Konsolidierung — vollständige Änderungs- & Teststrategie

**Branch:** `engine-consolidation` (off `v2-pricing`) · **Stand:** 15.06.2026
**Ersetzt** die Skizze in `PLAN_ENGINE_CONSOLIDATION.md` (dort Executive Summary, hier die Spezifikation).

---

## 0. Invariante (das Ziel in einem Satz)

> **Eine** Engine. Die Pricing-Logik lebt an **einem** Ort (`pricing_rules` + `pricing_primitives`), ist graph-tunable und **emittiert ihren eigenen Trace**. Kein zweiter Pfad, der driften kann. (Synapse §3: der Trace entsteht aus genau der Berechnung, die lief — er kann nicht lügen.)

**Akzeptanz:** `PricingEngine` liefert für alle 16 Fälle dieselben Zahlen wie heute (validierte „9/12") **und** einen Trace im selben Schema wie heute `GraphPricingEngine.provenance`. `GraphPricingEngine` wird stillgelegt. Frontend (`AgentTrace.tsx`) bleibt unverändert.

---

## 1. Ist-Architektur (Datei-Karte)

| Datei | Rolle heute |
|---|---|
| `engine/pricing_engine.py` `PricingEngine.calculate` | **Dünner Orchestrator (KORREKT).** grund/reise/bericht via `pricing_primitives`; `breakdown.pruef = gewerk.pruefkosten()`. Liefert **keinen** Trace (`provenance=[]`). |
| `engine/graph_pricing_engine.py` `GraphPricingEngine.calculate` | **Voll-Reimplementierung (TRACE, aber unvollständig).** Eigene `_pruef_dguv`, `_calc_grundkosten`, `_calc_reisekosten` + `_log(...)`. **Fehlt:** MA560, Kleinauftrag, Referenz-primär. |
| `products/dguv_v3/pricing_rules.py` | **Single source of pricing logic.** 8 Prüfkosten-Funktionen, 13 `_g_*`-Graph-Reader. Vollständig + graph-tunable. |
| `common/pricing_primitives.py` | Shared: `grundkosten_pauschal`, `tagegeld`, `berichtskosten`, `find_nearest_standort`. |
| `routers/product_router.py:55-70` | `/calculate?mode=graph|python` → Default `graph` (=GraphPricingEngine). |
| `frontend/app/page.tsx:32` | `pricingMode` default `"graph"`, nie umschaltbar (kein UI-Toggle). |

**Divergenz heute:** 8/15 Fälle (T01, T03, T04, T05, T08, T09, T10, T12, T15). Worst: T10 −4.851 €.

---

## 2. Soll-Architektur

```
PricingEngine.calculate(gewerk, merkmale)
  │  setzt Trace-Kontext (contextvar)
  ├─ grundkosten_pauschal(...)        ─┐
  ├─ gewerk.pruefkosten()             ─┤  jede Funktion appended Trace-Schritte
  │     → dispatch_pruefkosten(...)    │  an den aktiven Kontext (kein Signatur-Umbau)
  ├─ reisekosten-Orchestrierung       ─┤
  ├─ berichtskosten(...)              ─┘
  └─ Angebot(..., provenance=trace.steps)
```

- **Werte** kommen aus `pricing_rules`/`primitives` (graph-tunable via `_g_*`) → korrekt.
- **Trace** entsteht in denselben Funktionen → wahrhaftig.
- `GraphPricingEngine` → deprecated Alias auf `PricingEngine`, später gelöscht.

---

## 3. Trace-Kontrakt (Schema — MUSS bleiben)

Identisch zu heutiger `GraphPricingEngine.provenance` (sonst bricht das Frontend):

```python
TraceStep = {
  "step":   str,   # grundkosten|prueftage|tagegeld|pruefkosten|reisekosten|bericht|
                   # reifegrad|vollerfassung|kalibrierung|zuschlag|cross_sell
  "source": str,   # menschenlesbar, MIT gefeuertem Zweig (z.B. "Fläche 5000m² × 5.0€/10m² VdS-Kurve degressiv")
  "value":  str|float,
  "node_id":str,   # Graph-Knoten (KAT_3, DGUV_V3_ORTSFEST, VERT_UV, RK_PKW, BER_STANDARD, BM_PREIS, KLEINAUFTRAG ...)
  "ref":    str,   # Provenance (LPV B04 / Kalkulationshilfen NBG / 6 Großkunden / ...)
}
```

**Regel (Anti-Fabrikation, Synapse §3):** Ein Schritt entsteht nur, wenn der Wert wirklich berechnet/gelesen wurde. Leeres `ref` ist erlaubt nur für Meta-Schritte (confidence, cross_sell), nie für Geld-Schritte → Testfall 6.3.

---

## 4. Detaillierte Änderungen (Datei für Datei)

### 4.1 NEU `common/trace.py`
- `contextvars.ContextVar` `_TRACE` (default `None`).
- `class Trace`: `steps: list[dict]`; Kontextmanager `with Trace() as t:` setzt/reset den ContextVar.
- `emit(step, source, value, node_id="", ref="")`: appended an aktiven Trace, **No-op wenn keiner aktiv** (→ Funktionen bleiben außerhalb von `calculate` reine Float-Funktionen, bestehende Unit-Tests unverändert).

### 4.2 `products/dguv_v3/pricing_rules.py` — Instrumentierung
Additiv: nach jeder Wertermittlung ein `emit(...)`. **Zahlen ändern sich nicht.** Quell-/Ref-Strings aus `graph_pricing_engine.py` übernehmen (dort existieren sie bereits).

| Funktion (Zeile) | zu emittierende Schritte | node_id / ref |
|---|---|---|
| `dguv_pruefkosten` (372) | Grundpreis Anlage · Flächenkosten (Kurvenname **DGUV**) · Verteilungen UV/HV/NSHV · Sonderzuschlag NEA/SV · Reifegrad× · Komplexität× · Vollerfassung× | DGUV_V3_ORTSFEST, KAT_x, VERT_*, REIFEGRAD, KOMPLEX_FAKTOR |
| `vds_pruefkosten` (494) | analog, Kurvenname **VdS** explizit | VDS_2871, KAT_x |
| `bm_pruefkosten` (560) | BM-Grundpauschale · n × Satz | BM_PREIS · `_g_bm_params` |
| `kleinauftrag_pruefkosten` (592) | Kleinauftrag-Erkennung · min-Pauschale ODER Komponenten×Stunden | KLEINAUFTRAG · `_g_kleinauftrag_params` |
| `dguv_plus_vds_pruefkosten` (526) | Basis (Referenz ODER dguv_pruefkosten) · **Kombi-Faktor ×1.20** | VDS_KOMBI · „6 Großkunden" |
| `flaechenkosten_degressiv` (331) | optional je Band ein Schritt (sonst 1 Summenschritt) | FLAECHENSTAFFEL |
| `dispatch_pruefkosten` (635) | Routing-Entscheidung (welcher Pfad/Preisquelle) | — |
| `_g_*` (13 Helfer) | **fact-access auto-emit** (jeder Graph-Read = optional 1 Schritt) | jeweiliger Knoten |

**Kurven-Klarstellung (Bugfix):** Trace nennt explizit „DGUV-Kurve" vs „VdS-Kurve" statt nur „degressiv".

### 4.3 `common/pricing_primitives.py` — Instrumentierung
- `grundkosten_pauschal` → Schritte: Pauschale, Prüfmittel×Tage, (Ordnung), Tagegeld.
- `berichtskosten` → 1 Schritt (Berichtstyp).
- Reisekosten-Orchestrierung (heute teils in `PricingEngine.calculate` inline, teils `GraphPricingEngine._calc_reisekosten`): **in eine shared Funktion `reisekosten(merkmale, pruef_tage) -> (float, steps)` extrahieren** (Standort-Lookup, Distanz, Einzelanfahrt, Mehrtägig-Regel). Beide Trace-Strings aus `_calc_reisekosten` übernehmen.

### 4.4 `engine/pricing_engine.py`
- `calculate`: `with Trace() as t:` umschließen; nach Berechnung `angebot.provenance = t.steps`.
- `Angebot` (gewerk.py) bekommt Feld `provenance: list = []` (falls nicht vorhanden) + in `to_dict()`.

### 4.5 `routers/product_router.py`
- `/calculate`: beide `mode`-Zweige → `PricingEngine` (mit Trace). `mode`-Query bleibt nur für Rückwärtskompatibilität, zeigt aber auf dieselbe Engine. `result["provenance"] = angebot.provenance` in beiden Fällen.

### 4.6 `engine/graph_pricing_engine.py`
- Phase 4: `GraphPricingEngine = PricingEngine` (Alias) ODER Klasse, die intern an PricingEngine delegiert. Später ganz löschen (eigener Cleanup-Commit). Behebt nebenbei `_calc_dguv_addons` `NameError cost` (CLAUDE.md §5).

### 4.7 `frontend/app/page.tsx`
- `pricingMode` default bleibt egal (beide Modi = gleiche Engine). Optional: `mode`-Param ganz entfernen. Kein UI-Umbau nötig (Trace-Schema unverändert).

### 4.8 Wertkonflikte (graph_schema.py + Konstanten) — **erfordert Entscheidung**
| Konflikt | Optionen | Default-Vorschlag |
|---|---|---|
| Kat 7 Rate | Graph 5,42 vs Konst 8,00 €/10m² | **Pausch fragen**; bis dahin Graph (5,42) als Single-Value setzen, Konstante = Fallback identisch |
| Kombi-Basis | DGUV-Kurve (pricing_rules) vs VdS-Kurve (GraphPE) | **DGUV-Kurve** (dokumentiert: Docstring + 6-Großkunden) |
| MA560-Satz | 9,50 €/BM aus 2 Referenzen | beibehalten, später kalibrieren |

---

## 5. Testplan

### Phase 0 — Parity-Test (Sicherheitsnetz, zuerst) `tests/test_engine_parity.py`
- Für alle 16 Fälle: `assert abs(PricingEngine.total − GraphPricingEngine.total) ≤ 1.0`.
- **Erwartung jetzt: ROT auf 8 Fällen.** Das ist die Spezifikation. Am Ende GRÜN (= eine Engine).
- Zusatz: Parität je Prüfart (ortsfest / VdS / ortsveränderlich / kombi / Kleinauftrag) — mind. 1 Fall je Typ.

### Bestehende Tests — müssen GRÜN bleiben (Zahlen unverändert)
`test_dguv_v3` · `test_dguv_v3_v2` · `test_vds` · `test_ma560` · `test_kleinauftrag` · `test_degression` · `test_zusatzleistungen` · `test_kalibrierung` · `test_testrunde1_golden`.
→ Gate nach Phase 2 (Instrumentierung darf Zahlen nicht ändern).

### NEU — Trace-Tests `tests/test_trace.py`
1. **Nicht leer:** jeder der 5 Prüfart-Pfade liefert `len(provenance) > 0`.
2. **Summen-Konsistenz:** Summe der Geld-Schritte je Block == `breakdown.{grund,pruef,reise,bericht}` (±0,01).
3. **Keine Fabrikation:** jeder Geld-Schritt hat nicht-leeres `ref` UND `node_id` (Meta-Schritte ausgenommen). Fängt das §5a-Problem (`if e_row else 1.0` + erfundene Quelle).
4. **node_id auflösbar:** jeder `node_id` existiert im geladenen FalkorDB-Graph.
5. **Schema-Stabilität:** Keys == `{step,source,value,node_id,ref}` (Frontend-Kontrakt).
6. **Prüfart-Coverage:** MA560-Fall enthält BM-Schritt; Kleinauftrag-Fall enthält Kleinauftrag-Schritt; Kombi-Fall enthält Kombi-Faktor-Schritt — genau die heute in Prod fehlenden.

### 16-Fall-Validierung `scripts/test_testrunde1_all.py`
- Zahlen == heutige PricingEngine-Werte (Snapshot vor Umbau als Baseline-JSON sichern, danach diffen).
- Managed-Quote bleibt ≥ heutige (kein Regress).

### HTTP-Parität (End-to-End)
- Lokaler Server: `POST /api/dguv-v3/calculate?mode=graph` == `?mode=python` für alle 16 (nach Konsolidierung trivial gleich). Beweist: was das UI zeigt == Validierung.

### Frontend-Smoke
- `npm run build` grün; lokal: ein DGUV-Fall durch UI → Zahlen == Validierung, Trace-Panel gefüllt, keine Konsolen-Fehler.

### Gate-Matrix (pro Phase)
| nach Phase | muss grün sein |
|---|---|
| 0 | Parity-Test existiert (rot, dokumentiert) |
| 2 | bestehende Unit-Tests (Zahlen unverändert) |
| 3 | Trace-Tests (Trace gefüllt, konsistent) |
| 4 | Parity-Test GRÜN + 16-Fall + HTTP-Parität + Frontend-Smoke |

---

## 6. Migrationssequenz (ein Commit pro Schritt — CLAUDE.md §3)

1. `test: engine parity test (red on 8 cases) — spec for consolidation`
2. `feat: common/trace.py — contextvar trace sink (no-op when inactive)`
3. `feat: instrument pricing_rules with trace emit (numbers unchanged)`
4. `feat: instrument pricing_primitives + extract shared reisekosten`
5. `feat: PricingEngine collects + exposes provenance`
6. `test: trace tests (non-empty, consistent, no fabrication, prüfart coverage)`
7. `fix: resolve value conflicts (Kat7 / kombi base) — graph + const aligned`
8. `refactor: route /calculate to PricingEngine in both modes`
9. `refactor: deprecate GraphPricingEngine (alias) + remove _calc_dguv_addons NameError`
10. `chore: snapshot 16-case validation + parity green`

Jeder Commit: relevanter Test grün, Zahlen im Commit-Body.

---

## 7. Rollout / Deploy / Rollback

- **Entwicklung+Test:** lokal gegen lokale FalkorDB; nach Branch-Wechsel `load_dguv_graph()` (Graph ist shared+stateful, CLAUDE.md §3).
- **Deploy:** erst nach Gate Phase 4. `git push` → `fly deploy` → `graph_load` Endpoint → Smoke (`T10` live == ~5.991 €).
- **Rollback:** Branch nicht mergen / Router-Default zurück auf `graph` (GraphPricingEngine bleibt bis Commit 9 lauffähig).
- **Graph identisch?** Ja — selbe `graph_schema.py`-Definition; nur Commit 7 (Wertkonflikte) ändert wenige Knotenwerte. Nach jedem Branch-Wechsel/Schema-Edit Graph neu laden.

---

## 8. Offene Entscheidungen (blockieren NICHT den Start)
- **Pausch:** Kat 7 Rate (5,42 vs 8,00); Nahrungsmittel = Kat 2 oder 3 (T01, separat).
- **Intern:** Kombi-Basis = DGUV-Kurve (Vorschlag, dokumentiert).
- Diese betreffen nur Commit 7; Phasen 0–6 laufen unabhängig.

## 9. Risiken & Mitigation
| Risiko | Mitigation |
|---|---|
| Instrumentierung ändert versehentlich Zahlen | Gate Phase 2: bestehende Unit-Tests + 16-Fall-Snapshot-Diff |
| Trace weicht vom Frontend-Schema ab | Schema-Test (6.3.5) + Frontend-Smoke |
| Wertkonflikt-Auflösung verschiebt validierte Fälle | Commit 7 isoliert; 16-Fall-Lauf davor/danach diffen |
| Reisekosten-Extraktion bricht Edge-Case (nur PLZ, HESE-Fallback) | bestehende Reise-Tests + manuelle Fälle T01/T15 |
| FalkorDB stale nach Branch-Wechsel | Reload-Schritt im Test-Setup (Fixture lädt Graph) |

## 10. Definition of Done
- [ ] Parity-Test GRÜN (16/16, eine Engine)
- [ ] Alle bestehenden Unit-Tests grün, Zahlen unverändert
- [ ] Trace-Tests grün (gefüllt, konsistent, keine Fabrikation, Prüfart-Coverage)
- [ ] 16-Fall-Lauf == validierte Werte; managed ≥ heute
- [ ] HTTP `graph == python` für alle 16
- [ ] Frontend-Smoke: Zahlen korrekt + Trace gefüllt
- [ ] `T10` live == ~5.991 € (nicht 1.140 €)
- [ ] `GraphPricingEngine` stillgelegt; `_calc_dguv_addons`-Bug weg
- [ ] CLAUDE.md §5 Bug-Ledger aktualisiert
