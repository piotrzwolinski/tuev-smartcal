"""
SmartCal Deterministic Pipeline — replaces the ReAct agent.

Fixed traversal order, no LLM calls for graph navigation.
Every run with the same input produces the same output.

Steps:
  1. Match Gebäudetyp → ERFORDERT_PRUEFUNG → mandatory services
  2. Add services implied by user params (Wallboxen → DL_WALLBOX, etc.)
  3. For each service: collect HAT_PREISPOSITION → Preisposition + HAT_STAFFEL
  4. Estimate missing Merkmale via SCHAETZT edges
  5. Compute prices (Staffel lookup + formulas)
  6. Discover GLEICHE_BEGEHUNG → bundle discounts
  7. Collect EMPFIEHLT → recommendations
  8. Check LOEST_AUS → danger zones / surcharges
  9. Assemble Kalkulation
"""

import math
import time
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Fact:
    claim: str
    source: str  # "GRAPH", "CALCULATED", "ESTIMATED"


@dataclass
class TraceStep:
    label: str
    detail: str = ""
    duration_ms: int = 0


# ---------------------------------------------------------------------------
# Safe math evaluation (same as before)
# ---------------------------------------------------------------------------

def safe_eval(expression: str, variables: dict) -> float:
    safe_ns = {
        "__builtins__": {},
        "abs": abs, "round": round, "min": min, "max": max,
        "ceil": math.ceil, "floor": math.floor,
        "CEIL": math.ceil, "FLOOR": math.floor,
        **variables,
    }
    return eval(expression, safe_ns)  # noqa: S307


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class KalkulationPipeline:
    """Deterministic graph-driven pricing pipeline."""

    def __init__(self, db):
        self.db = db

    async def run(self, user_input: str, params: dict, on_step=None) -> dict:
        t_total = time.monotonic()
        trace: list[TraceStep] = []
        facts: list[Fact] = []

        async def step(label: str, detail: str = "", t0: float = 0):
            ms = int((time.monotonic() - t0) * 1000) if t0 else 0
            s = TraceStep(label=label, detail=detail, duration_ms=ms)
            trace.append(s)
            if on_step:
                await on_step({
                    "step": len(trace),
                    "action": label,
                    "result_summary": detail,
                    "duration_ms": ms,
                })

        # ------------------------------------------------------------------
        # 1. Identify Gebäudetyp
        # ------------------------------------------------------------------
        t0 = time.monotonic()
        gt_name = params.get("gebaeudetyp", "")
        gt_rows = await self.db.query(
            "MATCH (g:Gebaeudetyp) WHERE g.name CONTAINS $name OR g.keywords CONTAINS $name "
            "RETURN g.id AS id, g.name AS name LIMIT 1",
            name=gt_name,
        )
        gt_id = gt_rows[0]["id"] if gt_rows else None
        gt_display = gt_rows[0]["name"] if gt_rows else gt_name
        await step("Gebäudetyp identifiziert", gt_display, t0)
        if gt_id:
            facts.append(Fact(f"Gebäudetyp: {gt_display}", "GRAPH"))

        # ------------------------------------------------------------------
        # 2. Mandatory services from ERFORDERT_PRUEFUNG
        # ------------------------------------------------------------------
        t0 = time.monotonic()
        service_ids = set()
        service_map = {}  # id → {name, kurz, ...}

        if gt_id:
            rows = await self.db.query(
                "MATCH (g:Gebaeudetyp {id: $gid})-[r:ERFORDERT_PRUEFUNG]->(d:Dienstleistung) "
                "RETURN d.id AS id, d.name AS name, d.kurz AS kurz, "
                "properties(r) AS rprops",
                gid=gt_id,
            )
            for r in rows:
                service_ids.add(r["id"])
                service_map[r["id"]] = {"name": r["name"], "kurz": r["kurz"]}
                facts.append(Fact(
                    f"{r['name']}: Pflichtprüfung ({r['rprops'].get('grund', '')})",
                    "GRAPH",
                ))

        # Add services implied by user params
        param_service_map = {
            "anzahl_aufzuege": ["DL_AUFZUG_HP"],
            "aufzuege": ["DL_AUFZUG_HP"],
            "wallboxen": ["DL_WALLBOX"],
            "anzahl_ladepunkte": ["DL_WALLBOX"],
            "anzahl_stromkreise": ["DL_DGUV_ORTF"],
        }
        for key, svc_ids in param_service_map.items():
            val = params.get(key)
            if val and (isinstance(val, (int, float)) and val > 0 or val):
                for sid in svc_ids:
                    if sid not in service_ids:
                        service_ids.add(sid)

        # Fetch names for any services we added
        if service_ids:
            missing = [sid for sid in service_ids if sid not in service_map]
            if missing:
                rows = await self.db.query(
                    "MATCH (d:Dienstleistung) WHERE d.id IN $ids "
                    "RETURN d.id AS id, d.name AS name, d.kurz AS kurz",
                    ids=list(missing),
                )
                for r in rows:
                    service_map[r["id"]] = {"name": r["name"], "kurz": r["kurz"]}

        svc_names = [service_map.get(s, {}).get("name", s) for s in service_ids]
        await step("Relevante Prüfungen ermittelt", ", ".join(svc_names[:5]) + (f" (+{len(svc_names)-5})" if len(svc_names) > 5 else ""), t0)

        # ------------------------------------------------------------------
        # 3. Collect Preispositionen + Staffeln for each service
        # ------------------------------------------------------------------
        t0 = time.monotonic()
        # {service_id: [{pp_props, staffeln: [...]}]}
        service_prices = {}

        if service_ids:
            pp_rows = await self.db.query(
                "MATCH (d:Dienstleistung)-[r:HAT_PREISPOSITION]->(p:Preisposition) "
                "WHERE d.id IN $ids "
                "OPTIONAL MATCH (p)-[:HAT_STAFFEL]->(s:Staffel) "
                "RETURN d.id AS dl_id, properties(p) AS pp, properties(r) AS rp, "
                "collect(properties(s)) AS staffeln",
                ids=list(service_ids),
            )
            for row in pp_rows:
                dl_id = row["dl_id"]
                if dl_id not in service_prices:
                    service_prices[dl_id] = []
                service_prices[dl_id].append({
                    **row["pp"],
                    "rel": row["rp"],
                    "staffeln": [s for s in row["staffeln"] if s],
                })

        n_pp = sum(len(v) for v in service_prices.values())
        await step("Preispositionen geladen", f"{n_pp} Positionen für {len(service_prices)} Prüfungen", t0)

        # ------------------------------------------------------------------
        # 4. Estimate missing Merkmale via SCHAETZT
        # ------------------------------------------------------------------
        t0 = time.monotonic()
        # Normalize user params
        merkmale = dict(params)
        # Common aliases
        if "aufzuege" in merkmale and "anzahl_aufzuege" not in merkmale:
            merkmale["anzahl_aufzuege"] = merkmale["aufzuege"]
        if "wallboxen" in merkmale and "anzahl_ladepunkte" not in merkmale:
            merkmale["anzahl_ladepunkte"] = merkmale["wallboxen"]
        if "bgf" in merkmale and "bgf_m2" not in merkmale:
            merkmale["bgf_m2"] = merkmale["bgf"]

        # Fetch all SCHAETZT edges
        schaetzt_rows = await self.db.query(
            "MATCH (m:Merkmal)-[r:SCHAETZT]->(t:Merkmal) "
            "RETURN m.key AS from_key, t.key AS to_key, t.label AS to_label, "
            "properties(r) AS rprops"
        )

        estimated = []
        # Run estimation in multiple passes (some estimates depend on others)
        for _ in range(3):
            for row in schaetzt_rows:
                to_key = row["to_key"]
                if to_key in merkmale and merkmale[to_key] is not None:
                    continue  # already known
                formel = row["rprops"].get("formel", "")
                if not formel:
                    continue
                try:
                    value = safe_eval(formel, merkmale)
                    sf = row["rprops"].get("sicherheitsfaktor", 1.0)
                    value = math.ceil(value * sf)
                    merkmale[to_key] = value
                    desc = row["rprops"].get("beschreibung", formel)
                    estimated.append(f"{row['to_label']}: ~{value} ({desc})")
                    facts.append(Fact(
                        f"{row['to_label']} ≈ {value} (geschätzt: {desc})",
                        "ESTIMATED",
                    ))
                except Exception:
                    pass  # missing variables, skip for now

        if estimated:
            await step("Fehlende Mengen geschätzt", "; ".join(estimated[:3]) + (f" (+{len(estimated)-3})" if len(estimated) > 3 else ""), t0)
        else:
            await step("Mengen geprüft", "Alle Angaben vorhanden", t0)

        # ------------------------------------------------------------------
        # 4b. Collect Rückfragen for estimated values + important unknowns
        # ------------------------------------------------------------------
        rueckfragen = []

        # For estimated values: ask user to confirm
        for row in schaetzt_rows:
            to_key = row["to_key"]
            to_label = row["to_label"] or to_key
            if to_key in merkmale and to_key not in params:
                # This was estimated, not provided by user
                # Only ask if the value is used by a Preisposition
                for pps in service_prices.values():
                    for pp in pps:
                        if pp.get("bezugs_merkmal") == to_key:
                            rueckfragen.append(
                                f"{to_label}: geschätzt ~{merkmale[to_key]} — stimmt das?"
                            )
                            break
                    else:
                        continue
                    break

        # Important optional params from ERFORDERT_MERKMAL
        if service_ids:
            merk_rows = await self.db.query(
                "MATCH (d:Dienstleistung)-[:ERFORDERT_MERKMAL]->(m:Merkmal) "
                "WHERE d.id IN $ids AND m.required_at IN ['grob', 'mittel'] "
                "RETURN DISTINCT m.key AS key, m.label AS label, m.required_at AS req",
                ids=list(service_ids),
            )
            for mr in merk_rows:
                key = mr["key"]
                if key not in params and key not in merkmale:
                    rueckfragen.append(f"{mr['label']}?")

        # Other important optional params (only if not already covered by ERFORDERT_MERKMAL)
        asked_keys = {mr["key"] for mr in merk_rows} if service_ids else set()
        optional_questions = {
            "entfernung_km": ("Entfernung zum Standort in km? (für Anfahrtskosten)", None),
        }
        for key, (question, req_service) in optional_questions.items():
            if key not in params and key not in asked_keys:
                if req_service is None or req_service in service_ids:
                    rueckfragen.append(question)

        # ------------------------------------------------------------------
        # 5. Compute prices
        # ------------------------------------------------------------------
        t0 = time.monotonic()
        positionen = []

        for dl_id in sorted(service_ids):
            dl_info = service_map.get(dl_id, {})
            dl_name = dl_info.get("name", dl_id)
            pps = service_prices.get(dl_id, [])

            if not pps:
                continue

            for pp in pps:
                pp_name = pp.get("name", "")
                einheit = pp.get("einheit", "")
                basispreis = pp.get("basispreis", 0)
                bezugs_merkmal = pp.get("bezugs_merkmal")
                bedingung = pp.get("bedingung")
                schwellwert = pp.get("schwellwert")
                schwellwert_logik = pp.get("schwellwert_logik")
                ist_anfahrt = pp.get("ist_anfahrt", False)
                ist_basis = pp.get("rel", {}).get("ist_basis", True)

                # Skip Anfahrt (handle separately if needed)
                if ist_anfahrt:
                    continue

                # Check bedingung
                if bedingung:
                    try:
                        if not safe_eval(bedingung.replace("AND", "and").replace("OR", "or").replace("=", "==").replace("true", "True").replace("false", "False"), merkmale):
                            continue
                    except Exception:
                        continue  # can't evaluate → skip conditional position

                # Determine quantity
                if einheit == "pauschal":
                    menge = 1
                elif bezugs_merkmal:
                    menge = merkmale.get(bezugs_merkmal)
                    if menge is None:
                        rueckfragen.append(f"Wie viele {einheit} für {dl_name}? (benötigt für: {pp_name})")
                        continue
                else:
                    menge = 1

                # Apply schwellwert_logik
                if schwellwert and schwellwert_logik == "nur_ueber":
                    menge = max(0, menge - schwellwert)
                    if menge == 0:
                        continue

                # Staffel lookup: find highest ab_menge ≤ actual menge
                staffeln = pp.get("staffeln", [])
                preis = basispreis
                if staffeln and menge:
                    applicable = [s for s in staffeln if s.get("ab_menge", 0) <= menge]
                    if applicable:
                        best = max(applicable, key=lambda s: s["ab_menge"])
                        preis = best["preis"]

                betrag = round(preis * menge, 2)

                positionen.append({
                    "dienstleistung": dl_name,
                    "beschreibung": pp_name,
                    "menge": menge,
                    "einheitspreis": preis,
                    "einheit": einheit,
                    "betrag": betrag,
                    "berechnung": f"{menge} × {preis} €/{einheit}" if menge != 1 else f"{preis} € pauschal",
                })

                facts.append(Fact(
                    f"{dl_name} → {pp_name}: {menge} × {preis} € = {betrag} €",
                    "CALCULATED",
                ))

        subtotal = sum(p["betrag"] for p in positionen)
        await step("Preise berechnet", f"{len(positionen)} Positionen, Zwischensumme {subtotal:,.2f} €", t0)

        # ------------------------------------------------------------------
        # 6. GLEICHE_BEGEHUNG → bundle discounts
        # ------------------------------------------------------------------
        t0 = time.monotonic()
        rabatte = []

        if len(service_ids) > 1:
            gb_rows = await self.db.query(
                "MATCH (a:Dienstleistung)-[r:GLEICHE_BEGEHUNG]->(b:Dienstleistung) "
                "WHERE a.id IN $ids AND b.id IN $ids "
                "RETURN a.id AS a_id, a.name AS a_name, b.id AS b_id, b.name AS b_name, "
                "properties(r) AS rprops",
                ids=list(service_ids),
            )

            seen_pairs = set()
            for row in gb_rows:
                pair = tuple(sorted([row["a_id"], row["b_id"]]))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)

                rabatt_pct = row["rprops"].get("rabatt_prozent", 0)
                grund = row["rprops"].get("grund", "")

                # Calculate discount on the smaller service
                a_total = sum(p["betrag"] for p in positionen if p["dienstleistung"] == row["a_name"])
                b_total = sum(p["betrag"] for p in positionen if p["dienstleistung"] == row["b_name"])
                smaller = min(a_total, b_total)
                betrag = round(smaller * rabatt_pct / 100, 2)

                if betrag > 0:
                    rabatte.append({
                        "name": f"Bündelrabatt {row['a_name']} + {row['b_name']}",
                        "grund": grund,
                        "betrag": betrag,
                    })
                    facts.append(Fact(
                        f"Bündelrabatt {rabatt_pct}%: {row['a_name']} + {row['b_name']} = -{betrag} €",
                        "GRAPH",
                    ))

        if rabatte:
            await step("Bündelrabatte ermittelt", f"{len(rabatte)} Rabatte", t0)

        # ------------------------------------------------------------------
        # 7. EMPFIEHLT → recommendations
        # ------------------------------------------------------------------
        t0 = time.monotonic()
        empfehlungen = []

        if service_ids:
            emp_rows = await self.db.query(
                "MATCH (a:Dienstleistung)-[r:EMPFIEHLT]->(b:Dienstleistung) "
                "WHERE a.id IN $ids AND NOT b.id IN $ids "
                "RETURN DISTINCT b.id AS id, b.name AS name, "
                "collect(properties(r))[0] AS rprops",
                ids=list(service_ids),
            )

            for row in emp_rows:
                grund = row["rprops"].get("grund", "") if row["rprops"] else ""
                # Estimate price for recommended service
                est_price = await self._estimate_service_price(row["id"], merkmale)
                empfehlungen.append({
                    "dienstleistung": row["name"],
                    "grund": grund,
                    "geschaetzter_preis": est_price,
                })

        if empfehlungen:
            await step("Empfehlungen ermittelt", ", ".join(e["dienstleistung"] for e in empfehlungen), t0)

        # ------------------------------------------------------------------
        # 8. Assemble Kalkulation
        # ------------------------------------------------------------------
        zuschlaege = []  # Could add Erstprüfung, Altanlage etc. based on params

        gesamtbetrag = round(
            sum(p["betrag"] for p in positionen)
            + sum(z["betrag"] for z in zuschlaege)
            - sum(r["betrag"] for r in rabatte),
            2,
        )

        total_ms = int((time.monotonic() - t_total) * 1000)
        await step("Kalkulation erstellt", f"Gesamtbetrag: {gesamtbetrag:,.2f} €", 0)

        kalkulation = {
            "positionen": positionen,
            "zuschlaege": zuschlaege,
            "rabatte": rabatte,
            "gesamtbetrag": gesamtbetrag,
            "rueckfragen": rueckfragen,
            "empfehlungen": empfehlungen,
            "facts": [{"claim": f.claim, "source": f.source} for f in facts],
        }

        return {
            "kalkulation": kalkulation,
            "trace": [
                {
                    "step": i + 1,
                    "action": s.label,
                    "result_summary": s.detail,
                    "duration_ms": s.duration_ms,
                }
                for i, s in enumerate(trace)
            ],
            "steps": len(trace),
            "total_ms": total_ms,
        }

    async def _estimate_service_price(self, dl_id: str, merkmale: dict) -> float | None:
        """Quick estimate for a recommended service."""
        rows = await self.db.query(
            "MATCH (d:Dienstleistung {id: $id})-[:HAT_PREISPOSITION]->(p:Preisposition) "
            "WHERE p.ist_anfahrt IS NULL OR p.ist_anfahrt = false "
            "RETURN properties(p) AS pp",
            id=dl_id,
        )
        total = 0
        for row in rows:
            pp = row["pp"]
            basispreis = pp.get("basispreis", 0)
            bezugs_merkmal = pp.get("bezugs_merkmal")
            einheit = pp.get("einheit", "")

            if einheit == "pauschal":
                total += basispreis
            elif bezugs_merkmal and bezugs_merkmal in merkmale:
                total += basispreis * merkmale[bezugs_merkmal]
            else:
                total += basispreis  # at least 1 unit
        return round(total, 2) if total > 0 else None
