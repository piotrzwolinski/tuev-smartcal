# Plan: Engine-Konsolidierung (Drift beseitigen)

**Stand:** 14.06.2026 · Branch `v2-pricing` · nach Call mit Pausch umsetzen (nicht davor — Deploy-Pricing-Änderung).

---

## 1. Problem (quantifiziert)

Zwei Pricing-Engines liefern **verschiedene Preise für denselben Input** — Divergenz auf **8 von 15** Fällen:

| Engine | Verwendet von | MA560 | Kleinauftrag | Referenz-primär | Trace/Provenance |
|---|---|---|---|---|---|
| **PricingEngine** | Test-Suite (`test_testrunde1_all.py`) → „9/12 managed" | ✓ | ✓ | ✓ | ✗ (`provenance=[]`) |
| **GraphPricingEngine** | **Deployte App** (`/calculate?mode=graph`, Default) | ✗ | ✗ | ✗ | ✓ |

Worst case **T10 Max Planck** (545 Betriebsmittel): Test +12 % PASS · Prod **−79 % FAIL** (Δ 4.851 €) — die 545 Geräte werden in Prod komplett ignoriert. Weitere: T03 (+226 % vs +26 %), T15 (−45 % vs +12 %), T08, T09, T12.

**Folge:** Die validierten „9/12"-Zahlen gelten für PricingEngine; die App auf Fly zeigt die schlechtere GraphPricingEngine-Spalte.

## 2. Ursache

`GraphPricingEngine` ist eine **parallele Voll-Reimplementierung** von `calculate()` (eigene `_pruef_dguv`, `_calc_grundkosten`, `_calc_reisekosten`), nur um nebenbei `_log(...)`-Provenance zu emittieren. Dabei wurde die Prüfkosten-Logik unvollständig nachgebaut (keine MA560/Kleinauftrag/Referenz).

`PricingEngine` dagegen ist ein **dünner Orchestrator**:
- `breakdown.grund` ← `common/pricing_primitives.grundkosten_pauschal`
- `breakdown.pruef` ← `gewerk.pruefkosten()` → `pricing_rules.dispatch_pruefkosten` (**vollständige Logik**)
- `breakdown.reise/bericht` ← `common/pricing_primitives`
- `pricing_rules` liest Werte aus dem Graph (`get_reader()`/`_g_*`, 53×) → **graph-tunable**

→ PricingEngine hat **korrekte Zahlen + Tunability**, ihm fehlt **nur der Trace**. GraphPricingEngine hat **nur den Trace** und ist sonst die schwächere Kopie.

## 3. Zielarchitektur — EINE Engine

> Dünner Orchestrator über **eine** graph-tunable Logik-Schicht (`pricing_rules` + `pricing_primitives`), die **ihren Trace selbst emittiert** (Synapse §3: „der Trace kann nicht lügen", weil er aus genau der Berechnung entsteht, die wirklich lief).

Konkret: `PricingEngine` wird zur kanonischen Engine; die Logik-Funktionen bekommen einen **Trace-Sink**; `GraphPricingEngine` wird stillgelegt. Kein Nachbauen, kein Porten — die korrekte Logik existiert schon, sie muss nur Spuren hinterlassen.

## 4. Phasen (mit Gates)

### Phase 0 — Sicherheitsnetz: Parity-Test  *(~1h, Risiko: keins)*
- `tests/test_engine_parity.py`: für alle 16 Fälle `PricingEngine.total ≈ GraphPricingEngine.total` (Toleranz 1 €).
- **Jetzt ROT auf 8 Fällen** — das ist die Spezifikation dessen, was wir reparieren. Bleibt am Ende GRÜN.
- Zusätzlich Parity je Prüfart (ortsfest / VdS / ortsveränderlich / kombi / Kleinauftrag).

### Phase 1 — Trace-Sink Design  *(~1h, Risiko: keins — nur Design)*
- Kleiner Kollektor: `TraceStep{step, source, value, node_id, ref}`; Funktionen akzeptieren optionalen `trace: list | None`.
- Identisches Schema wie heutige `GraphPricingEngine.provenance` → Frontend (`AgentTrace.tsx`) bleibt unverändert.

### Phase 2 — Logik-Schicht instrumentieren  *(~1 Tag, Risiko: mittel)*
Trace-Emission additiv einbauen (Zahlen ändern sich NICHT, nur eine Liste wird gefüllt):
- `pricing_rules.py`: `dispatch_pruefkosten` + `dguv_pruefkosten`, `vds_pruefkosten`, `bm_pruefkosten`, `kleinauftrag_pruefkosten`, `dguv_plus_vds_pruefkosten` — je Schritt (Grundpreis, Fläche×Kat, Verteilungen, BM×Satz, Kleinauftrag-Pauschale, Kombi-Faktor) ein `trace.append(...)` mit `node_id`/`ref`.
- `common/pricing_primitives.py`: `grundkosten_pauschal`, `reisekosten`, `berichtskosten` analog.
- **Gate:** Parity-Test bleibt rot (erwartet), aber `test_dguv_v3`, `test_vds`, `test_ma560`, `test_kleinauftrag` bleiben GRÜN (Zahlen unverändert).

### Phase 3 — PricingEngine sammelt Trace  *(~0,5 Tag, Risiko: niedrig)*
- `PricingEngine.calculate` reicht einen `trace`-Kollektor durch und legt ihn auf `angebot`/`self.provenance`.
- Jetzt: **PricingEngine = korrekte Zahlen + Trace + graph-tunable** = alles.
- **Gate:** Provenance nicht leer; Schema == altes GraphPricingEngine-Schema.

### Phase 4 — GraphPricingEngine stilllegen + Router umstellen  *(~0,5 Tag, Risiko: mittel)*
- `routers/product_router.py`: `/calculate` nutzt **immer** PricingEngine (mit Trace). `mode`-Query entfällt oder beide Modi zeigen auf dieselbe Engine.
- `engine/graph_pricing_engine.py` → deprecated (erst Alias auf PricingEngine, später löschen).
- **Gate:** Parity-Test GRÜN (eine Engine = trivially parity); voller Suite + 16-Case-Lauf; manueller Smoke auf Fly (Trace sichtbar, Zahlen == Validierung).

### Phase 5 — Deploy & Default  *(~0,5 Tag)*
- Deploy; `graph_load` nach Deploy (Graph-Werte); Smoke (`T10` live = ~5.991 €, nicht 1.140 €).

**Aufwand gesamt: ~3 Tage** (+ Wertkonflikte unten, abhängig von Pausch).

## 5. Wertkonflikte, die die Konsolidierung erzwingt (gut!)

Sobald eine Engine, müssen widersprüchliche Werte aufgelöst werden — das zwingt Klärung statt zwei Antworten:
- **Kat 7-Rate:** Graph 5,42 €/10m² vs Konstante 8,00. → Pausch fragen, einen Wert setzen.
- **Kombi-Basis:** `pricing_rules` nimmt DGUV-Kurve × 1,20, `GraphPricingEngine` VdS-Kurve × 1,20. → DGUV-Kurve ist die dokumentierte (Docstring + 6-Großkunden-Basis) → DGUV-Kurve gewinnt.
- **MA560-Satz 9,50 €/BM:** aus 2 Referenzen (T04, T10) — bei der Gelegenheit mit weiteren Pausch-Abrechnungen kalibrieren.
- **T01 Hipp Kat 2 vs Kat 3:** Domänenentscheidung Pausch (nicht Teil der Konsolidierung, aber gleicher Klärungs-Slot).

## 6. Rollout / Rollback
- Jede Phase einzeln committen (eine Änderung pro Schritt — CLAUDE.md §3).
- Rollback = Router-Default zurück auf `mode=graph` (GraphPricingEngine bleibt bis Phase 4 lauffähig).
- Vor Deploy: Parity GRÜN + voller Suite + 16-Case-Zahlen in der PR.

## 7. Bekannte Bugs, die dabei mit-erledigt werden
- `_calc_dguv_addons` `NameError cost` (graph_pricing_engine.py ~Z.443) — verschwindet mit der Stilllegung.
- Doppelte Kombi-Pfade (Enum-`×1.20` + `vds_pruefung`-Addon) — kollabieren auf einen.
- Trace-Klarheit „degressiv" ohne Kurvenname (DGUV vs VdS) — beim Instrumentieren explizit machen.

## 8. Sofort für morgen (nicht Teil der Konsolidierung)
Minimal & risikolos: Router-Default `mode=python` ODER nur deckungsgleiche Fälle live demonstrieren (T02, T06, T07, T11, T13, T14). Konsolidierung bewusst NACH dem Call.
