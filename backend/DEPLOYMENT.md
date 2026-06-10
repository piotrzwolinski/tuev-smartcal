# Deployment-Checkliste SmartCal@EG (Fly.io, fra)

Apps: `tuev-smartcal-web` (Next.js) · `tuev-smartcal-api` (FastAPI) · `tuev-smartcal-db` (FalkorDB)

## Nach JEDEM Backend-Deploy (Pflicht)

1. `fly deploy` (in `backend/`)
2. **Graph-Reload prüfen** — Produkt-Graphen werden im `main.py`-lifespan geladen,
   aber NUR wenn FalkorDB beim Start erreichbar war:
   ```bash
   curl -s -X POST https://tuev-smartcal-api.fly.dev/api/graph/load-products -H "X-API-Key: $API_KEY"
   ```
   Erwartung: `blitzschutz` ~73 Nodes, `rlt` ~56, `dguv_v3` ≥64 (nach Plan v2 Phase 0.5: +12 Flaechenstaffel, +KAT_7/KAT_8, +BMPreis, +Kleinauftrag → ~80).
3. **Smoke-Check Prüfkosten ≠ 0** (Gotcha: Graph leer → Prüfkosten=0):
   ```bash
   curl -s -X POST https://tuev-smartcal-api.fly.dev/api/dguv-v3/calculate \
     -H "Content-Type: application/json" -H "X-API-Key: $API_KEY" \
     -d '{"nutzung": "buerogebaeude", "gesamtflaeche_m2": 1000}' | jq .breakdown.pruef
   ```
   Erwartung: > 250 (nicht 0, nicht exakt Grundpreis).
4. `/api/health` → Status ok.

## Neue Graph-Nodes (Plan v2)

Nach Änderungen an `products/*/graph_schema.py` reicht Schritt 2 (load-products
löscht + lädt den jeweiligen Produkt-Graph komplett neu). Neue tunable Nodes seit Phase 0.5:

| Node | Zweck | EFI-tunable Properties |
|------|-------|------------------------|
| `Flaechenstaffel` (FS_DGUV_*, FS_VDS_*) | Degressionskurven Fläche | `ab_m2`, `faktor` |
| `BMPreis` (BM_SATZ) | MA560 per-Device | `satz_pro_bm`, `grundpauschale`, `staffel_ab_bm`, `staffel_faktor` |
| `Kleinauftrag` (KLEINAUFTRAG) | Small-Job-Pfad | `max_verteilungen`, `max_flaeche_m2`, `stundensatz`, `stunden_pro_komponente`, `min_pauschale`, `grundkosten_reduziert` |
| `Installationskategorie` KAT_7/KAT_8 | Krankenhaus/Sonder | `preis_per_10m2` (5.42 / 7.68) |

EFI (Bachmeier/Römerkamp) kann diese Werte direkt im Graph ändern — ohne Deploy.
Nach manueller Graph-Änderung: KEIN load-products aufrufen (überschreibt Tuning!),
stattdessen Werte in `graph_schema.py` nachziehen und dann deployen.

## Lokal

```bash
# FalkorDB starten (falls nicht läuft)
docker run -d --name falkordb -p 6379:6379 falkordb/falkordb
# Graphen laden (alle Produkte): Server starten ODER
cd backend && python -c "from products.dguv_v3.graph_schema import load_dguv_graph; print(load_dguv_graph())"
# Legacy-Default-Graph (Agent-Pipeline /api/chat):
python load_graph.py
```

## Regressions-Gate vor jedem Deploy (Plan v2 Teststrategie)

```bash
cd backend && python -m pytest tests/ -q                     # alle Tests grün
python scripts/golden_baseline.py --compare                  # kein Case >2pp schlechter
```
