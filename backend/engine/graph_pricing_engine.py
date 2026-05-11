"""Graph-based pricing engine — queries FalkorDB for ALL rules.

Supports multiple products via per-graph Prüfkosten logic:
  - blitzschutz: Staffeln × Messstellen
  - rlt: HYG (Stundensatz × Bereiche + Labor) / GARAGE (Grundpreis + Stück)
  - dguv_v3: Grundpreis + Fläche × Kat + Verteilungen + Sonderzuschläge
"""

from __future__ import annotations

from pydantic import BaseModel

from engine.gewerk import Gewerk, Angebot, Breakdown, ZuschlagApplied
from common.database import get_graph


class GraphPricingEngine:

    def __init__(self, graph_name: str = "blitzschutz"):
        self.graph_name = graph_name
        self.provenance: list[dict] = []

    def _q(self, cypher: str, **params) -> list:
        graph = get_graph(self.graph_name)
        result = graph.query(cypher, params)
        return result.result_set if result.result_set else []

    def _q1(self, cypher: str, **params):
        rows = self._q(cypher, **params)
        return rows[0][0] if rows else None

    def _log(self, step: str, source: str, value, node_id: str = "", ref: str = ""):
        self.provenance.append({"step": step, "source": source, "value": value, "node_id": node_id, "ref": ref})

    # ═══════════════════════════════════════════════════════════
    # Main entry point
    # ═══════════════════════════════════════════════════════════

    def calculate(self, gewerk: Gewerk, merkmale: BaseModel) -> Angebot:
        self.provenance = []
        breakdown = Breakdown()
        warnings = []

        # ─── 1. GRUNDKOSTEN (shared) ──────────────────────────
        breakdown.grund = self._calc_grundkosten(merkmale)

        # ─── 2. PRÜFKOSTEN (per product) ─────────────────────
        if self.graph_name == "blitzschutz":
            breakdown.pruef = self._pruef_blitzschutz(merkmale)
        elif self.graph_name == "rlt":
            breakdown.pruef = self._pruef_rlt(merkmale)
        elif self.graph_name == "dguv_v3":
            breakdown.pruef = self._pruef_dguv(merkmale)
        else:
            breakdown.pruef = gewerk.pruefkosten(merkmale)
            self._log("pruefkosten", "Python fallback", breakdown.pruef)

        # ─── 3. REISEKOSTEN (shared) ─────────────────────────
        breakdown.reise = self._calc_reisekosten(merkmale, warnings)

        # ─── 4. BERICHTERSTELLUNG (per product) ──────────────
        breakdown.bericht = self._calc_bericht(gewerk, merkmale)

        # ─── 5. ZUSCHLÄGE (shared) ───────────────────────────
        total, zuschlaege = self._calc_zuschlaege(merkmale, breakdown.subtotal)

        # ─── 6. CONFIDENCE (per product) ─────────────────────
        confidence, conf_reason = self._calc_confidence(gewerk, merkmale)

        # ─── 7. CROSS-SELL (from graph) ──────────────────────
        self._add_cross_sell(warnings)

        return Angebot(
            gewerk=gewerk.name, total=total, breakdown=breakdown,
            zuschlaege=zuschlaege, confidence=confidence, confidence_reason=conf_reason,
            similar=[], lpv_referenz=gewerk.lpv_referenz, warnings=warnings,
        )

    # ═══════════════════════════════════════════════════════════
    # SHARED: Grundkosten
    # ═══════════════════════════════════════════════════════════

    def _calc_grundkosten(self, merkmale: BaseModel) -> float:
        pauschale = self._q1("MATCH (g:Grundkosten {id: 'GRUND_PAUSCHALE'}) RETURN g.betrag") or 256
        self._log("grundkosten", "Grundkosten.GRUND_PAUSCHALE", f"{pauschale}€", "GRUND_PAUSCHALE",
                  ref="LPV Teil A §4: Pauschale Auftragsanlage 256€")

        ordnung = 0
        if getattr(merkmale, "baurechtlich", False):
            ordnung = self._q1("MATCH (g:Grundkosten {id: 'GRUND_ORDNUNG'}) RETURN g.betrag") or 242
            self._log("grundkosten", "Grundkosten.GRUND_ORDNUNG (baurechtlich)", f"{ordnung}€", "GRUND_ORDNUNG",
                      ref="LPV Teil A §4: Ordnungsprüfung 242€ (nur baurechtlich)")

        pruefmittel_tag = self._q1("MATCH (g:Grundkosten {id: 'GRUND_PRUEFMITTEL'}) RETURN g.betrag_pro_tag") or 49
        pruef_tage = self._get_pruef_tage(merkmale)

        self._log("grundkosten", f"Prüfmittel {pruefmittel_tag}€ × {pruef_tage} Tage", f"{pruefmittel_tag * pruef_tage}€", "GRUND_PRUEFMITTEL",
                  ref="LPV Teil A §4: 49€ je Prüftag")

        hours = pruef_tage * 8
        tg_row = self._q("MATCH (t:Tagegeld) WHERE t.von_h <= $h AND t.bis_h > $h RETURN t.betrag, t.id", h=hours)
        tagegeld = tg_row[0][0] if tg_row else (0 if hours < 6 else 25)
        self._log("tagegeld", f"Tagegeld ({hours}h Außendienst)", f"{tagegeld}€",
                  tg_row[0][1] if tg_row else "none",
                  ref="LPV Teil A §4.3: 0€ (<6h), 6€ (6-8h), 25€ (8-14h), 30€ (14-24h)")

        return pauschale + ordnung + pruefmittel_tag * pruef_tage + tagegeld

    def _get_pruef_tage(self, merkmale: BaseModel) -> float:
        if self.graph_name == "blitzschutz":
            ms = getattr(merkmale, "anzahl_ableitungen", 0)
            row = self._q("MATCH (p:Prueftagschaetzung) WHERE p.von_ms <= $ms AND p.bis_ms >= $ms RETURN p.tage, p.formel, p.id", ms=ms)
            if row:
                tage, formel = row[0][0], row[0][1]
                if tage == -1 and formel == "ms/40":
                    tage = max(3.0, ms / 40)
                self._log("prueftage", f"Prueftagschaetzung für {ms} MS", f"{tage} Tage", row[0][2], ref="Heuristik")
                return tage
            return max(0.5, ms / 30)

        elif self.graph_name == "rlt":
            variant = getattr(merkmale, "variant", None)
            if variant and variant.value == "hygiene":
                bereiche = getattr(merkmale, "anzahl_pruefbereiche_hyg", None) or 1
                tage = max(0.5, bereiche * 0.4)
                self._log("prueftage", f"{bereiche} Bereiche × 0,4 Tage", f"{tage} Tage", "PT_HYG", ref="Heuristik")
                return tage
            else:
                sp = getattr(merkmale, "stellplaetze", None) or 0
                row = self._q("MATCH (p:Prueftagschaetzung) WHERE p.typ = 'garage' AND p.von_stellplaetze <= $sp AND p.bis_stellplaetze >= $sp RETURN p.tage, p.id", sp=sp)
                tage = row[0][0] if row else 0.5
                self._log("prueftage", f"Garage {sp} SP", f"{tage} Tage", row[0][1] if row else "fallback", ref="Heuristik")
                return tage

        elif self.graph_name == "dguv_v3":
            flaeche = getattr(merkmale, "gesamtflaeche_m2", 0)
            row = self._q("MATCH (p:Prueftagschaetzung) WHERE p.von_m2 <= $f AND p.bis_m2 >= $f RETURN p.tage, p.formel, p.id", f=flaeche)
            if row:
                tage, formel = row[0][0], row[0][1]
                if tage == -1 and formel == "flaeche/2500":
                    tage = max(2.0, flaeche / 2500)
                self._log("prueftage", f"{flaeche} m²", f"{tage} Tage", row[0][2], ref="Heuristik")
                return tage
            return max(0.5, flaeche / 2500)

        return 1.0

    # ═══════════════════════════════════════════════════════════
    # PRÜFKOSTEN: Blitzschutz (Staffeln × Messstellen)
    # ═══════════════════════════════════════════════════════════

    def _pruef_blitzschutz(self, merkmale: BaseModel) -> float:
        ms = getattr(merkmale, "anzahl_ableitungen", 0)
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
            ref = "LPV B04 §8.1: 33€/Messstelle" if typ == "lpv_konform" else f"Heuristik: {preis}€/MS (validiert StV Augsburg)"
            self._log("pruefkosten", f"Staffel {sid}: {in_band}×{preis}€", f"{cost}€", sid, ref=ref)
        return pruef

    # ═══════════════════════════════════════════════════════════
    # PRÜFKOSTEN: RLT (HYG: Stunden / GARAGE: Grundpreis+Stück)
    # ═══════════════════════════════════════════════════════════

    def _pruef_rlt(self, merkmale: BaseModel) -> float:
        variant = getattr(merkmale, "variant", None)
        if variant and variant.value == "hygiene":
            return self._pruef_rlt_hyg(merkmale)
        return self._pruef_rlt_garage(merkmale)

    def _pruef_rlt_hyg(self, merkmale: BaseModel) -> float:
        bereiche = getattr(merkmale, "anzahl_pruefbereiche_hyg", None) or 1
        std_row = self._q("MATCH (p:Produkt {id: 'RLT_HYG'}) RETURN p.stundensatz, p.stunden_pro_bereich, p.labor_pauschale")
        if std_row:
            stundensatz, stunden_pro_b, labor = std_row[0]
            cost = bereiche * (stunden_pro_b * stundensatz + labor)
            self._log("pruefkosten", f"HYG: {bereiche} Bereiche × ({stunden_pro_b}h × {stundensatz}€ + {labor}€ Labor)", f"{cost}€", "RLT_HYG",
                      ref="LPV B05 Kap. 2.7: Stundensatz 208€ (schwierig), 2,5h/Bereich + Laborpauschale 180€")
            return cost
        return bereiche * (2.5 * 208 + 180)

    def _pruef_rlt_garage(self, merkmale: BaseModel) -> float:
        sp = getattr(merkmale, "stellplaetze", None)
        vol = getattr(merkmale, "nennvolumenstrom_m3h", None)

        if sp is not None:
            rows = self._q(
                "MATCH (p:Produkt {id: 'RLT_GARAGE'})-[:HAT_GRUNDPREIS]->(g:Grundpreis) "
                "WHERE g.von_stellplaetze <= $sp AND g.bis_stellplaetze >= $sp "
                "RETURN g.betrag, g.name, g.id", sp=sp)
            if rows:
                grund = rows[0][0]
                self._log("pruefkosten", f"Grundpreis Garage: {sp} SP → {rows[0][1]}", f"{grund}€", rows[0][2],
                          ref="LPV B05 Kap. 2.2: Grundpreis per Stellplatz-Bereich")
            else:
                grund = 450 if sp <= 30 else (690 if sp <= 100 else 1250)
                self._log("pruefkosten", f"Grundpreis Garage fallback: {sp} SP", f"{grund}€")
        elif vol is not None:
            rows = self._q(
                "MATCH (p:Produkt {id: 'RLT_STANDARD'})-[:HAT_GRUNDPREIS]->(g:Grundpreis) "
                "WHERE g.von_volumenstrom <= $vol AND g.bis_volumenstrom >= $vol "
                "RETURN g.betrag, g.id", vol=vol)
            if rows:
                grund = rows[0][0]
                self._log("pruefkosten", f"Grundpreis RLT: {vol} m³/h", f"{grund}€", rows[0][1],
                          ref="LPV B05 Kap. 2.1: Grundpreis per Volumenstrom")
            else:
                grund = 600
                self._log("pruefkosten", "Grundpreis RLT fallback", f"{grund}€")
        else:
            grund = 600
            self._log("pruefkosten", "Grundpreis RLT default (keine SP/Vol)", f"{grund}€")

        vent = getattr(merkmale, "anzahl_ventilatoren", None) or 0
        bsk = getattr(merkmale, "anzahl_brandschutzklappen", None) or 0
        if vent > 0:
            vent_row = self._q("MATCH (z:ZuschlagStueck {id: 'ZS_VENTILATOR'}) RETURN z.betrag_pro_stueck")
            vent_preis = vent_row[0][0] if vent_row else 170
            grund += vent * vent_preis
            self._log("pruefkosten", f"Ventilatoren: {vent} × {vent_preis}€", f"{vent * vent_preis}€", "ZS_VENTILATOR",
                      ref="LPV B05 Kap. 2: 170€/Ventilator")
        if bsk > 0:
            bsk_row = self._q("MATCH (z:ZuschlagStueck {id: 'ZS_BSK'}) RETURN z.betrag_pro_stueck")
            bsk_preis = bsk_row[0][0] if bsk_row else 40
            grund += bsk * bsk_preis
            self._log("pruefkosten", f"BSK: {bsk} × {bsk_preis}€", f"{bsk * bsk_preis}€", "ZS_BSK",
                      ref="LPV B05 Kap. 2: 40€/BSK")
        return grund

    # ═══════════════════════════════════════════════════════════
    # PRÜFKOSTEN: DGUV V3 (Grundpreis + Fläche×Kat + Vert + SZ)
    # ═══════════════════════════════════════════════════════════

    def _pruef_dguv(self, merkmale: BaseModel) -> float:
        produkt = self._q("MATCH (p:Produkt {id: 'DGUV_V3_ORTSFEST'}) RETURN p.grundpreis")
        grundpreis = produkt[0][0] if produkt else 250
        self._log("pruefkosten", "Grundpreis Anlage", f"{grundpreis}€", "DGUV_V3_ORTSFEST",
                  ref="LPV B04 Kap. 2: Grundpreis 250€ pro Anlage")

        flaeche = getattr(merkmale, "gesamtflaeche_m2", 0)
        kat = getattr(merkmale, "primary_installationskategorie", None)
        kat_val = kat.value if kat else 1
        kat_id = f"KAT_{kat_val}"

        kat_row = self._q("MATCH (k:Installationskategorie {id: $kid}) RETURN k.preis_per_10m2, k.name", kid=kat_id)
        rate = kat_row[0][0] if kat_row else 1.0
        kat_name = kat_row[0][1] if kat_row else f"Kat {kat_val}"
        flaeche_cost = (flaeche / 10.0) * rate
        self._log("pruefkosten", f"Fläche {flaeche}m² × {rate}€/10m² ({kat_name})", f"{flaeche_cost}€", kat_id,
                  ref=f"LPV B04 Kap. 2: {rate}€ pro 10m² für {kat_name}")

        cost = grundpreis + flaeche_cost

        for field, label, node_prefix in [
            ("anzahl_verteilungen_uv", "UV", "VERT_UV"),
            ("anzahl_verteilungen_hv", "HV", "VERT_HV"),
            ("anzahl_verteilungen_nshv", "NSHV", "VERT_NSHV"),
        ]:
            count = getattr(merkmale, field, 0)
            if count > 0:
                vrow = self._q(f"MATCH (v:Verteilung {{id: '{node_prefix}'}}) RETURN v.preis_pro_einheit")
                preis = vrow[0][0] if vrow else 25
                vert_cost = count * preis
                cost += vert_cost
                self._log("pruefkosten", f"{label}: {count} × {preis}€", f"{vert_cost}€", node_prefix,
                          ref=f"LPV B04 Kap. 2: {preis}€ pro {label}")

        for field, node_id, label in [
            ("nea_vorhanden", "SZ_NEA", "Netzersatzanlage"),
            ("sv_nshv_vorhanden", "SZ_SV_NSHV", "Sicherheitsstromversorgung"),
        ]:
            if getattr(merkmale, field, False):
                sz_row = self._q(f"MATCH (s:Sonderzuschlag {{id: '{node_id}'}}) RETURN s.betrag")
                betrag = sz_row[0][0] if sz_row else 0
                cost += betrag
                self._log("pruefkosten", f"{label}: +{betrag}€", f"{betrag}€", node_id,
                          ref=f"LPV B04 Kap. 2: {label} {betrag}€")

        return cost

    # ═══════════════════════════════════════════════════════════
    # SHARED: Reisekosten
    # ═══════════════════════════════════════════════════════════

    def _calc_reisekosten(self, merkmale: BaseModel, warnings: list) -> float:
        lat = getattr(merkmale, "adresse_lat", None)
        lon = getattr(merkmale, "adresse_lon", None)
        if not lat or not lon:
            warnings.append("Adresse ohne Koordinaten — Reisekosten nicht berechnet")
            return 0

        from common.pricing_primitives import find_nearest_standort
        plz = getattr(merkmale, "adresse_plz", None)
        standort = find_nearest_standort(lat, lon, plz=plz)
        km_rt = standort["distance_km"] * 2
        dur_min = standort.get("duration_min", standort["distance_km"] / 80 * 60)

        km_rate = self._q1("MATCH (r:Reisekostenregel {id: 'RK_PKW'}) RETURN r.betrag_pro_km") or 1.10
        reise_std = self._q1("MATCH (s:Stundensatz {id: 'STD_EINFACH'}) RETURN s.betrag") or 180.0

        reise = km_rt * km_rate + (dur_min * 2 / 60) * reise_std

        zuordnung = standort.get("zuordnung", "nearest")
        label = "Zuständiger TÜV-Standort" if zuordnung == "crm" else "Nächster TÜV-Standort"
        self._log("reisekosten", f"{label}: {standort['name']} ({standort['distance_km']:.0f}km)", f"{reise:.2f}€",
                  f"STD_{standort.get('id','?')}", ref=f"LPV Teil A §4.3: {km_rate}€/km PKW, Reisezeit × {reise_std}€/h")
        self._log("reisekosten", "Regel: nur 1 Anfahrt bei mehrtägig (RK_MEHRTAEGIG)", "1× roundtrip", "RK_MEHRTAEGIG")

        zuordnung_warnung = standort.get("zuordnung_warnung")
        if zuordnung_warnung:
            warnings.append(f"⚠ {zuordnung_warnung}")
        if standort["distance_km"] > 0:
            warnings.append(f"{label}: {standort['name']} ({standort.get('adresse','')}, {standort['plz']}) — "
                          f"{standort['distance_km']:.0f} km / {dur_min:.0f} min [{standort.get('routing','')}]")
        return reise

    # ═══════════════════════════════════════════════════════════
    # SHARED: Berichterstellung (per product logic)
    # ═══════════════════════════════════════════════════════════

    def _calc_bericht(self, gewerk: Gewerk, merkmale: BaseModel) -> float:
        typ = gewerk.choose_bericht_typ(merkmale)
        typ_map = {"klein": ("BER_KLEIN", 119), "standard": ("BER_STANDARD", 380), "komplex": ("BER_KOMPLEX", 550)}
        bid, fallback = typ_map.get(typ, ("BER_STANDARD", 380))
        betrag = self._q1(f"MATCH (b:Berichtstyp {{id: '{bid}'}}) RETURN b.betrag") or fallback
        self._log("bericht", f"Berichtstyp {bid} ({typ})", f"{betrag}€", bid,
                  ref=f"LPV: Klein 119€ / Standard 380€ / Komplex 550€")
        return betrag

    # ═══════════════════════════════════════════════════════════
    # SHARED: Zuschläge
    # ═══════════════════════════════════════════════════════════

    def _calc_zuschlaege(self, merkmale: BaseModel, subtotal: float) -> tuple[float, list[ZuschlagApplied]]:
        total = subtotal
        applied = []

        checks = [
            (not getattr(merkmale, "vereinsmitglied", True), "ZS_NICHT_VEREIN", "Nicht-Vereinsmitglied", 0.20,
             "LPV Teil A: bis +20% für Nicht-Vereinsmitglieder"),
            (getattr(merkmale, "eilzuschlag", False), "ZS_EIL", "Eilzuschlag", 0.25,
             "LPV Teil A §11: bis +25% Sondertermin"),
            (getattr(merkmale, "erstpruefung", False), "ZS_ERSTPRUEFUNG", "Erstprüfung", 1.00,
             "LPV Teil A §5.2: bis +100% Erstprüfung"),
        ]

        for condition, zid, name, fallback_pct, ref in checks:
            if condition:
                pct = self._q1(f"MATCH (z:Zuschlag {{id: '{zid}'}}) RETURN z.prozent") or fallback_pct
                amount = total * pct
                total += amount
                applied.append(ZuschlagApplied(name=name, percent=pct, amount=amount))
                self._log("zuschlag", f"{name}: +{pct*100:.0f}%", f"{amount:.2f}€", zid, ref=ref)

        return total, applied

    # ═══════════════════════════════════════════════════════════
    # SHARED: Confidence (delegates to Gewerk.validate_ranges)
    # ═══════════════════════════════════════════════════════════

    def _calc_confidence(self, gewerk: Gewerk, merkmale: BaseModel) -> tuple[float, str]:
        confidence, reason = gewerk.validate_ranges(merkmale)
        self._log("confidence", f"Confidence Score: {confidence*100:.0f}%", reason or "Alle Merkmale in typischen Bereichen")
        return confidence, reason or "Alle Merkmale in typischen Bereichen (Graph-validiert)"

    # ═══════════════════════════════════════════════════════════
    # SHARED: Cross-sell
    # ═══════════════════════════════════════════════════════════

    def _add_cross_sell(self, warnings: list):
        rows = self._q("MATCH (c:CrossSell) RETURN c.empfehlung, c.produkt")
        for empfehlung, produkt in (rows or []):
            warnings.append(f"Empfehlung: {empfehlung}")
            self._log("cross_sell", f"→ {produkt}", empfehlung)
