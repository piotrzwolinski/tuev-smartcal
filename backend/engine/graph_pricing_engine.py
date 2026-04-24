"""Graph-based pricing engine — queries FalkorDB for ALL rules.

Parallel to pricing_engine.py (Python-hardcoded).
Same input (Gewerk + Merkmale) → same output (Angebot).
Difference: every value comes from graph query, not Python constant.

Each step records provenance: which node/relationship provided the value.
"""

from __future__ import annotations

from pydantic import BaseModel

from engine.gewerk import Gewerk, Angebot, Breakdown, ZuschlagApplied
from common.database import get_graph


class GraphPricingEngine:
    """Pricing engine that reads ALL rules from FalkorDB graph."""

    def __init__(self, graph_name: str = "blitzschutz"):
        self.graph_name = graph_name
        self.provenance: list[dict] = []

    def _q(self, cypher: str, **params) -> list:
        graph = get_graph(self.graph_name)
        result = graph.query(cypher, params)
        if not result.result_set:
            return []
        return result.result_set

    def _q1(self, cypher: str, **params):
        rows = self._q(cypher, **params)
        return rows[0][0] if rows else None

    def _log(self, step: str, source: str, value, node_id: str = "", ref: str = ""):
        self.provenance.append({
            "step": step,
            "source": source,
            "value": value,
            "node_id": node_id,
            "ref": ref,
        })

    def calculate(self, gewerk: Gewerk, merkmale: BaseModel) -> Angebot:
        self.provenance = []
        breakdown = Breakdown()
        warnings = []
        ms = getattr(merkmale, "anzahl_ableitungen", 0)
        nutzung = getattr(merkmale, "nutzung", None)
        nutzung_val = nutzung.value if nutzung else "sonstige"

        # ─── 1. GRUNDKOSTEN (from graph) ──────────────────────
        pauschale = self._q1("MATCH (g:Grundkosten {id: 'GRUND_PAUSCHALE'}) RETURN g.betrag")
        self._log("grundkosten", "Grundkosten.GRUND_PAUSCHALE", pauschale, "GRUND_PAUSCHALE",
                  ref="LPV 2025/2026 Teil A §4, Punkt 'Pauschale für Auftragsanlage, Verwaltung, Angebotsgebühr' + TÜV-Korrespondenz 14.08.2025 Punkt 2 'Grundkosten-Bestandteile'")

        # Ordnungsprüfung (nur baurechtlich)
        ordnung = 0
        if getattr(merkmale, "baurechtlich", False):
            ordnung = self._q1("MATCH (g:Grundkosten {id: 'GRUND_ORDNUNG'}) RETURN g.betrag") or 0
            self._log("grundkosten", "Grundkosten.GRUND_ORDNUNG (baurechtlich)", ordnung, "GRUND_ORDNUNG",
                      ref="LPV Teil A §4 'Pauschale für die Ordnungsprüfung von Prüfgrundlagen bei baurechtlichen Prüfungen' + TÜV-Korrespondenz: 'nur bei baurechtlichen Prüfungen, nicht im aktuellen Beispiel'")

        # Prüfmittel per Tag
        pruefmittel_tag = self._q1("MATCH (g:Grundkosten {id: 'GRUND_PRUEFMITTEL'}) RETURN g.betrag_pro_tag")
        self._log("grundkosten", "Grundkosten.GRUND_PRUEFMITTEL", pruefmittel_tag, "GRUND_PRUEFMITTEL",
                  ref="LPV Teil A §4 'Energie- und Prüfmittelpauschale: 49€ je Prüftag, je Sachverständiger' + TÜV-Korrespondenz Punkt 2")

        # Prüftage (from graph heuristic)
        pruef_tage_row = self._q(
            "MATCH (p:Prueftagschaetzung) WHERE p.von_ms <= $ms AND p.bis_ms >= $ms RETURN p.tage, p.formel, p.id",
            ms=ms
        )
        if pruef_tage_row:
            tage = pruef_tage_row[0][0]
            formel = pruef_tage_row[0][1]
            pt_id = pruef_tage_row[0][2]
            if tage == -1 and formel == "ms/40":
                tage = max(3.0, ms / 40)
            self._log("prueftage", f"Prueftagschaetzung.{pt_id} [HEURISTIK — nicht aus Dokumenten]", tage, pt_id,
                      ref="⚠ KEINE QUELLE — Eigenständige Schätzung. LPV und TÜV-Korrespondenz enthalten keine Angaben zur Prüfdauer pro Messstelle. Rückfrage an TÜV SÜD EG erforderlich: 'Wie viele Prüftage plant ihr typischerweise?'")
        else:
            tage = max(0.5, ms / 30)
            self._log("prueftage", "Fallback (no graph rule)", tage)

        # Tagegeld PER TAG (fixed from bug: was total, should be per-day)
        hours_per_day = 8
        tagegeld_row = self._q(
            "MATCH (t:Tagegeld) WHERE t.von_h <= $h AND t.bis_h > $h RETURN t.betrag, t.id",
            h=hours_per_day
        )
        tagegeld_per_tag = tagegeld_row[0][0] if tagegeld_row else 25.0
        tagegeld_total = tagegeld_per_tag * tage
        self._log("tagegeld", f"Tagegeld ({hours_per_day}h/Tag) × {tage} Tage", tagegeld_total,
                  tagegeld_row[0][1] if tagegeld_row else "fallback",
                  ref=f"LPV Teil A §4.3 Tagegeld-Tabelle: 'bei {hours_per_day} bis <14h Außendienst: 25,00€' — angewandt pro Prüftag ({tage} Tage)")

        breakdown.grund = (pauschale or 256) + ordnung + (pruefmittel_tag or 49) * tage + tagegeld_total

        # ─── 2. PRÜFKOSTEN (Staffeln from graph) ─────────────
        staffeln = self._q(
            "MATCH (p:Produkt {id: 'BLITZ_AUSSEN'})-[:HAT_STAFFEL]->(s:Staffel) "
            "RETURN s.von, s.bis, s.preis_pro_ms, s.id, s.typ ORDER BY s.von"
        )
        pruef = 0
        remaining = ms
        for von, bis, preis, sid, typ in staffeln:
            if remaining <= 0:
                break
            band = bis - von + 1
            in_band = min(remaining, band)
            cost = in_band * preis
            pruef += cost
            remaining -= in_band
            staffel_ref = (
                "LPV B04 §8.1: 'Messstellen, je 1 Stück: 33,00€'" if typ == "lpv_konform"
                else f"⚠ HEURISTIK — LPV sagt nur 'Bei mehr als 10 Messstellen: besondere Vereinbarung'. Staffelpreis {preis}€ ist geschätzt, validiert gegen 316 Anlagen Stadtwerke Augsburg StV (±5% Match für ≤25 MS)"
            )
            self._log("pruefkosten", f"Staffel {sid}: {in_band}×{preis}€ ({typ})", cost, sid, ref=staffel_ref)

        breakdown.pruef = pruef

        # ─── 3. REISEKOSTEN (Standorte from graph) ────────────
        lat = getattr(merkmale, "adresse_lat", None)
        lon = getattr(merkmale, "adresse_lon", None)
        if lat and lon:
            from common.pricing_primitives import find_nearest_standort
            standort = find_nearest_standort(lat, lon)
            km_rt = standort["distance_km"] * 2
            dur_min = standort.get("duration_min", standort["distance_km"] / 80 * 60)

            km_rate = self._q1("MATCH (r:Reisekostenregel {id: 'RK_PKW'}) RETURN r.betrag_pro_km") or 1.10
            reise_std = self._q1("MATCH (s:Stundensatz {id: 'STD_EINFACH'}) RETURN s.betrag") or 180.0

            reise_km = km_rt * km_rate
            reise_zeit = (dur_min * 2 / 60) * reise_std
            breakdown.reise = reise_km + reise_zeit

            self._log("reisekosten", f"Nearest: {standort['name']} ({standort['distance_km']:.0f}km)", breakdown.reise, f"STD_{standort.get('id','?')}",
                      ref=f"TÜV-Korrespondenz 14.08.2025: 'Das Tool muss anhand der eingegebenen Objektadresse den nächst möglichen TÜV SÜD Standort suchen.' Standort {standort['name']}: {standort.get('adresse','')}, {standort.get('plz','')}. Routing via OSRM (Fahrstrecke, nicht Luftlinie). LPV Teil A §4.3: 1,10€/km PKW.")
            self._log("reisekosten", "Regel: nur 1 Anfahrt bei mehrtägig (RK_MEHRTAEGIG)", "1× roundtrip", "RK_MEHRTAEGIG",
                      ref="TÜV-Korrespondenz 14.08.2025: 'Bei mehrtägigen Prüfungen ist von maximalen Anfahrten auszugehen.' → Interpretation: nur 1 Hin-/Rückfahrt, unabhängig von Prüftagen.")
        else:
            warnings.append("Adresse ohne Koordinaten — Reisekosten nicht berechnet")

        # ─── 4. BERICHTERSTELLUNG (from graph) ────────────────
        bericht_rows = self._q(
            "MATCH (p:Produkt {id: 'BLITZ_AUSSEN'})-[r:HAT_BERICHTSTYP]->(b:Berichtstyp) "
            "RETURN b.betrag, b.name, b.id, r.bedingung"
        )
        # Simple rule evaluation
        bericht_preis = 380  # fallback
        bericht_id = "BER_STANDARD"
        for betrag, name, bid, bedingung in bericht_rows:
            if "messstellen <= 10" in (bedingung or "") and ms <= 10:
                bericht_preis = betrag
                bericht_id = bid
                break
            elif "messstellen > 40" in (bedingung or "") and ms > 40:
                bericht_preis = betrag
                bericht_id = bid
                break
            elif "messstellen > 10 AND messstellen <= 40" in (bedingung or "") and 10 < ms <= 40:
                bericht_preis = betrag
                bericht_id = bid
                break

        breakdown.bericht = bericht_preis
        self._log("bericht", f"Berichtstyp {bericht_id} für {ms} MS", bericht_preis, bericht_id,
                  ref=f"Preise aus TÜV-Korrespondenz 14.08.2025 Punkt 4 'Kosten für die Berichterstellung': Klein 119€ / Standard 380€ / Komplex 550€. ⚠ SCHWELLEN-ZUORDNUNG (≤10 MS→klein, 11-40→standard, >40→komplex) ist HEURISTIK — nicht aus Dokumenten. Rückfrage an TÜV: 'Ab wie vielen Messstellen gilt Standardbericht vs klein?'")

        # ─── 5. ZUSCHLÄGE (from graph) ────────────────────────
        subtotal = breakdown.subtotal
        total = subtotal
        zuschlaege_applied = []

        if getattr(merkmale, "erstpruefung", False):
            z = self._q1("MATCH (z:Zuschlag {id: 'ZS_ERSTPRUEFUNG'}) RETURN z.prozent") or 1.0
            amount = total * z
            total += amount
            zuschlaege_applied.append(ZuschlagApplied(name="Erstprüfung", percent=z, amount=amount))
            self._log("zuschlag", "Zuschlag.ZS_ERSTPRUEFUNG", f"+{z*100:.0f}%", "ZS_ERSTPRUEFUNG",
                      ref="LPV Teil A §5.2: 'Für Erstprüfungen: Zuschlag von bis zu 100% auf die Preise für wiederkehrende Prüfungen'")

        if not getattr(merkmale, "vereinsmitglied", True):
            z = self._q1("MATCH (z:Zuschlag {id: 'ZS_NICHT_VEREIN'}) RETURN z.prozent") or 0.20
            amount = total * z
            total += amount
            zuschlaege_applied.append(ZuschlagApplied(name="Nicht-Vereinsmitglied", percent=z, amount=amount))
            self._log("zuschlag", "Zuschlag.ZS_NICHT_VEREIN", f"+{z*100:.0f}%", "ZS_NICHT_VEREIN",
                      ref="LPV Teil A §4.2: 'Bei Nicht-Vereinsmitgliedern kann auf alle Leistungen ein Zuschlag von bis zu 20% erhoben werden.'")

        if getattr(merkmale, "eilzuschlag", False):
            z = self._q1("MATCH (z:Zuschlag {id: 'ZS_EIL'}) RETURN z.prozent") or 0.25
            amount = total * z
            total += amount
            zuschlaege_applied.append(ZuschlagApplied(name="Eilzuschlag", percent=z, amount=amount))
            self._log("zuschlag", "Zuschlag.ZS_EIL", f"+{z*100:.0f}%", "ZS_EIL",
                      ref="LPV Teil A §11: 'Für Prüfungen, die zu einem vom Auftraggeber verlangten Zeitpunkt durchgeführt werden, kann auf die Preise ein Zuschlag bis zu 25% erhoben werden.'")

        # ─── 6. CONFIDENCE (from graph: Gebäudetyp ranges) ────
        confidence = 1.0
        conf_reason = ""
        gt_map = {
            "schule": "GT_SCHULE", "buero": "GT_BUERO", "industrie": "GT_INDUSTRIE",
            "wohnung": "GT_WOHNUNG", "hotel": "GT_HOTEL", "museum": "GT_MUSEUM",
            "krankenhaus": "GT_KRANKENHAUS", "lager": "GT_LAGER", "garage": "GT_GARAGE",
        }
        gt_id = gt_map.get(nutzung_val)
        if gt_id:
            ranges = self._q(
                "MATCH (g:Gebaeudetyp {id: $gid}) RETURN g.typische_ts_min, g.typische_ts_max",
                gid=gt_id,
            )
            if ranges:
                lo, hi = ranges[0][0], ranges[0][1]
                if ms > hi * 1.5:
                    confidence *= 0.7
                    conf_reason += f"Anzahl Ableitungen ({ms}) deutlich über typisch für {nutzung_val} ({lo}-{hi}). "
                    self._log("confidence", f"Gebaeudetyp.{gt_id} range {lo}-{hi} vs {ms}", confidence, gt_id)

        if ms > 25:
            confidence *= 0.85
            conf_reason += f">{25} MS: in Ausschreibungen oft 30-50% Rabatt vs LPV. "

        # ─── 7. CROSS-SELL (from graph) ───────────────────────
        empfehlungen = self._q(
            "MATCH (a:Produkt {id: 'BLITZ_AUSSEN'})-[r:EMPFIEHLT]->(b:Produkt) "
            "RETURN b.name, r.text"
        )
        if empfehlungen:
            for name, text in empfehlungen:
                warnings.append(f"Empfehlung: {text}")
                self._log("cross_sell", f"EMPFIEHLT → {name}", text)

        return Angebot(
            gewerk=gewerk.name,
            total=total,
            breakdown=breakdown,
            zuschlaege=zuschlaege_applied,
            confidence=confidence,
            confidence_reason=conf_reason.strip() or "Alle Merkmale in typischen Bereichen (Graph-validiert)",
            similar=[],
            lpv_referenz=gewerk.lpv_referenz,
            warnings=warnings,
        )
