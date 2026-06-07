# SmartCal@EG — PRD: Graph-as-Single-Source-of-Truth Refactoring

**Version:** 1.0
**Stand:** 31.05.2026
**Priorität:** Nach Testrunde 08.06 (kein funktionaler Impact, reines Architektur-Refactoring)
**Effort:** ~4h
**Risiko:** Mittel — 34 Tests betroffen, stille Nulls bei fehlenden Graph-Nodes

---

## 1. Ziel

Aktuell existieren Pricing-Regeln **doppelt**: als Python-Dicts in `pricing_rules.py` UND als Graph-Nodes in FalkorDB. Das führt zu:

- **Divergenz-Risiko**: Wert in Python ≠ Wert in Graph → widersprüchliche Ergebnisse je nach Engine-Pfad
- **Kein Self-Service**: Regeländerung (z.B. neue €/m²-Preise) erfordert Code-Deployment statt Graph-Update
- **Doppelte Provenance**: `_quelle` Metadata nur im Graph, Python-Dicts haben keine Traçabilität

**Ziel:** Pricing Engine liest ALLE Regeln aus dem Graph. Python-Dicts werden zu **Fallback** degradiert (nur wenn Graph nicht erreichbar). Single Source of Truth = Graph.

---

## 2. Ist-Zustand

### 2.1 Doppelt vorhanden (Python + Graph)

| # | Daten | Python (pricing_rules.py) | Graph Node | Zeilen betroffen |
|---|---|---|---|---|
| 1 | €/m² per Kat | `PREIS_PER_10M2` dict | `:Installationskategorie.preis_per_10m2` | 4 |
| 2 | Reifegrad-Faktoren | `REIFEGRAD_FAKTOR` dict | `:Reifegrad.faktor` | 2 |
| 3 | Vollerfassung-Faktor | `VOLLERFASSUNG_FAKTOR = 1.30` | `:Dokumentationszuschlag.faktor` | 1 |
| 4 | Preissteigerung | `PREISSTEIGERUNG` dict | `:Preissteigerung.steigerung_vs_2026` | 2 |
| 5 | Warn-Schwelle | `REFERENZPREIS_WARN_SCHWELLE = 0.20` | `:Warnregel.schwelle_prozent` | 1 |
| 6 | Nutzung→Kat Mapping | `TYPICAL_KAT` dict | `:Gebaeudetyp -[:TYPISCHE_KATEGORIE]→ :Installationskategorie` | 3 |
| 7 | Typische Flächen-Ranges | `TYPICAL_FLAECHE` dict | `:Gebaeudetyp.typische_flaeche_min/max` | 2 |
| 8 | Nutzungs-Mix→Kat | `NUTZUNG_ZU_KATEGORIE` dict | `:NutzungsMapping.kategorie` | 2 |
| 9 | Umrechnung (Zimmer→m²) | `UMRECHNUNG_M2` dict | `:Umrechnungsregel.faktor_m2` | 2 |

### 2.2 Nur im Prompt (chat.py)

| # | Daten | Prompt-Hardcoding | Graph Node |
|---|---|---|---|
| 10 | Branchenfragen | "Hotel→Wie viele Zimmer?" im Prompt-Text | `:Branchenfrage.frage` |
| 11 | Umrechnungsfaktoren | "Zimmer×30, Betten×50" im Prompt-Text | `:Umrechnungsregel.faktor_m2` |
| 12 | Kat-Zuordnung | "Krankenhaus→Kat 2" im Prompt-Text | `:Gebaeudetyp -[:TYPISCHE_KATEGORIE]→` |

---

## 3. Soll-Zustand

### 3.1 Pricing Engine: Graph-First mit Python-Fallback

```python
# VORHER:
cost *= REIFEGRAD_FAKTOR[m.reifegrad]  # Python dict

# NACHHER:
faktor = graph.query("MATCH (r:Reifegrad {id: $rg}) RETURN r.faktor", rg=f"RG_{m.reifegrad.value}")
if faktor is None:
    faktor = REIFEGRAD_FAKTOR_FALLBACK[m.reifegrad]  # Fallback
    log.warning(f"Graph Reifegrad {m.reifegrad} not found, using fallback")
cost *= faktor
```

### 3.2 Chat Coordinator: Dynamic Prompt aus Graph

```python
# VORHER:
COORDINATOR_SYSTEM = """...Hotel→Wie viele Zimmer?..."""  # statisch

# NACHHER:
branchenfragen = graph.query("MATCH (bf:Branchenfrage) RETURN bf.gebaeudetyp, bf.frage, bf.zusatzfragen")
umrechnungen = graph.query("MATCH (ur:Umrechnungsregel) RETURN ur.gebaeudetyp, ur.kundenmerkmal, ur.faktor_m2")
prompt = build_coordinator_prompt(branchenfragen, umrechnungen)  # dynamisch
```

### 3.3 Fallback-Pattern

```python
class GraphReader:
    """Reads values from Graph with Python-dict fallback."""
    
    def __init__(self, graph_name: str):
        self._graph = get_graph(graph_name)
        self._cache = {}  # per-request cache
    
    def get_value(self, query: str, params: dict, fallback, cache_key: str = None):
        """Query graph, return fallback if null/error."""
        if cache_key and cache_key in self._cache:
            return self._cache[cache_key]
        try:
            result = self._graph.query(query, params=params).result_set
            if result and result[0][0] is not None:
                value = result[0][0]
                if cache_key:
                    self._cache[cache_key] = value
                return value
        except Exception:
            pass
        return fallback
```

---

## 4. Implementierungsplan

### Phase 1: GraphReader Helper (30 min)

Erstelle `common/graph_reader.py` mit:
- `GraphReader` Klasse (query + fallback + cache)
- Logging bei Fallback-Nutzung (Warnung wenn Graph-Wert fehlt)
- Per-Request Cache (kein globaler Cache — Graph kann sich ändern)

**Tests:**
```
test_graph_reader_returns_value_from_graph
test_graph_reader_fallback_on_null
test_graph_reader_fallback_on_error
test_graph_reader_cache_per_request
```

### Phase 2: pricing_rules.py refactoren (2h)

Für jede der 9 Python-Dicts:

| # | Dict | Query | Fallback |
|---|---|---|---|
| 1 | `PREIS_PER_10M2[kat]` | `MATCH (k:Installationskategorie {id: $kid}) RETURN k.preis_per_10m2` | Aktueller dict-Wert |
| 2 | `REIFEGRAD_FAKTOR[rg]` | `MATCH (r:Reifegrad {id: $rid}) RETURN r.faktor` | `{RG_1: 1.25, ...}` |
| 3 | `VOLLERFASSUNG_FAKTOR` | `MATCH (d:Dokumentationszuschlag {id:'DOK_VOLL'}) RETURN d.faktor` | `1.30` |
| 4 | `PREISSTEIGERUNG[jahr]` | `MATCH (p:Preissteigerung {jahr: $j}) RETURN p.steigerung_vs_2026` | Aktueller dict-Wert |
| 5 | `REFERENZPREIS_WARN_SCHWELLE` | `MATCH (w:Warnregel {id:'WARN_REFERENZ'}) RETURN w.schwelle_prozent` | `0.20` |
| 6 | `TYPICAL_KAT[nutzung]` | `MATCH (g:Gebaeudetyp)-[:TYPISCHE_KATEGORIE]->(k) WHERE g.id = $gid RETURN k.id` | Aktueller dict-Wert |
| 7 | `TYPICAL_FLAECHE[nutzung]` | `MATCH (g:Gebaeudetyp {id: $gid}) RETURN g.typische_flaeche_min, g.typische_flaeche_max` | Aktueller tuple |
| 8 | `NUTZUNG_ZU_KATEGORIE[name]` | `MATCH (nm:NutzungsMapping) WHERE toLower(nm.nutzung) = $n RETURN nm.kategorie` | `KAT_2` |
| 9 | `UMRECHNUNG_M2[merkmal]` | `MATCH (ur:Umrechnungsregel {kundenmerkmal: $m}) RETURN ur.faktor_m2` | Aktueller dict-Wert |

**Pattern pro Dict:**
1. Dict bleibt als `_FALLBACK` renamed
2. Neue Funktion `get_X_from_graph(key) → value or fallback`
3. Alle Aufrufe umstellen
4. Test anpassen: testet Output (Preis), nicht Quelle (dict vs. graph)

**Tests (angepasst):**
```
# VORHER:
assert PREIS_PER_10M2[Installationskategorie.KAT_2] == 3.10

# NACHHER:
assert get_kat_preis(Installationskategorie.KAT_2) == 3.10  # egal ob aus Graph oder Fallback
```

### Phase 3: chat.py Dynamic Prompt (1h)

1. Beim Start/ersten Request: Branchenfragen + Umrechnungsregeln aus Graph laden
2. Prompt dynamisch zusammenbauen
3. Kat-Zuordnung aus Graph (bereits implementiert)

```python
def build_coordinator_prompt() -> str:
    graph = get_graph("dguv_v3")
    
    # Branchenfragen aus Graph
    bf_rows = graph.query("MATCH (bf:Branchenfrage) RETURN bf.gebaeudetyp, bf.frage, bf.zusatzfragen ORDER BY bf.gebaeudetyp")
    branchenfragen_text = "\n".join(f"- Bei {r[0]}: \"{r[1]}\"" for r in bf_rows.result_set)
    
    # Umrechnungen aus Graph
    ur_rows = graph.query("MATCH (ur:Umrechnungsregel) RETURN ur.kundenmerkmal, ur.faktor_m2")
    umrechnungen_text = ", ".join(f"{r[0]}×{r[1]:.0f}=m²" for r in ur_rows.result_set)
    
    return COORDINATOR_TEMPLATE.format(
        branchenfragen=branchenfragen_text,
        umrechnungen=umrechnungen_text,
    )
```

**Tests:**
```
test_dynamic_prompt_contains_branchenfragen
test_dynamic_prompt_contains_umrechnungen
test_dynamic_prompt_updates_when_graph_changes
```

### Phase 4: Tests anpassen (30 min)

34 Tests die Python dicts direkt referenzieren → auf Output-basierte Assertions umstellen:

```python
# VORHER: testet Implementierung
assert PREIS_PER_10M2[Installationskategorie.KAT_2] == 3.10

# NACHHER: testet Verhalten
m = DGUVMerkmale(nutzung=..., gesamtflaeche_m2=1000, primary_installationskategorie=Installationskategorie.KAT_2)
assert dguv_pruefkosten(m) == 250 + 100 * 3.10  # Output stimmt, egal woher der Wert kommt
```

---

## 5. Risikominimierung

### 5.1 Stille Nulls verhindern

```python
def get_value(self, query, params, fallback, cache_key=None):
    try:
        result = self._graph.query(query, params=params).result_set
        if result and result[0][0] is not None:
            value = result[0][0]
            # PLAUSIBILITÄTSCHECK: Wert muss im erwarteten Bereich liegen
            if isinstance(fallback, (int, float)) and isinstance(value, (int, float)):
                if value <= 0 or value > fallback * 10:
                    log.error(f"Graph value {value} outside plausible range (fallback: {fallback})")
                    return fallback
            return value
    except Exception as e:
        log.warning(f"Graph query failed: {e}, using fallback")
    return fallback
```

### 5.2 Graph Integrity Tests (vor jedem Deployment)

```
test_graph_has_all_installationskategorien
test_graph_has_all_reifegrade
test_graph_has_all_preissteigerungen
test_graph_has_all_nutzungsmappings
test_graph_has_all_branchenfragen
test_graph_has_all_umrechnungsregeln
test_graph_values_match_fallback  # ← KRITISCH: Prüft dass Graph = Fallback
```

### 5.3 Monitoring

```python
# In jeder Kalkulation loggen:
angebot.provenance = {
    "kat_preis_source": "graph" oder "fallback",
    "reifegrad_source": "graph" oder "fallback",
    ...
}
```

Wenn >5% Fallback-Nutzung → Alert.

---

## 6. Rollback-Plan

1. Python dicts bleiben als `_FALLBACK` erhalten → jederzeit rückbaubar
2. Feature Flag: `USE_GRAPH_PRICING = True/False` in `.env`
3. Wenn `False` → alle Reads gehen auf Python dicts, Graph wird ignoriert
4. Rollback = `USE_GRAPH_PRICING=False` in .env, kein Code-Change

---

## 7. Tests

### 7.1 Neue Tests (GraphReader)

```
test_graph_reader_returns_value_from_graph
test_graph_reader_fallback_on_null
test_graph_reader_fallback_on_error
test_graph_reader_fallback_on_implausible_value
test_graph_reader_cache_per_request
test_graph_reader_no_cache_between_requests
```

### 7.2 Graph Integrity Tests

```
test_graph_has_6_installationskategorien
test_graph_kat2_preis_equals_3_10
test_graph_has_4_reifegrade
test_graph_rg3_faktor_equals_1_0
test_graph_has_6_preissteigerungen
test_graph_has_warn_schwelle_20
test_graph_has_vollerfassung_1_30
test_graph_has_12_gebaeudetypen_mit_kategorie
test_graph_has_24_nutzungsmappings
test_graph_has_8_branchenfragen
test_graph_has_6_umrechnungsregeln
test_graph_values_match_python_fallbacks  # Komplett-Check
```

### 7.3 Angepasste bestehende Tests (34)

Umstellen von dict-Assertions auf Output-Assertions. Keine gelöscht, nur refactored.

### 7.4 E2E Tests (bestehende 140 bleiben)

Müssen ohne Änderung grün bleiben — testen Output, nicht Implementierung.

**Total neue Tests: 18 | Angepasste: 34 | Bestehende (unverändert): 106**

---

## 8. Definition of Done

- [ ] GraphReader implementiert mit Fallback + Plausibilitätscheck
- [ ] Alle 9 Python dicts auf Graph-First umgestellt
- [ ] Chat Prompt dynamisch aus Graph generiert
- [ ] Feature Flag `USE_GRAPH_PRICING` funktioniert
- [ ] 140 bestehende Tests grün
- [ ] 18 neue Tests grün
- [ ] Kein einziger Python-Fallback wird im Normalbetrieb genutzt (Graph hat alle Werte)
- [ ] Provenance in Angebot zeigt "graph" für alle Werte
