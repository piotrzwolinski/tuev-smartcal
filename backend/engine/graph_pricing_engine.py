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

        # ─── 5. REIFEGRAD + VOLLERFASSUNG (DGUV only) ────────
        referenzpreis = None
        zusatzleistungen = []
        if self.graph_name == "dguv_v3":
            breakdown.pruef, referenzpreis = self._apply_dguv_modifiers(merkmale, breakdown.pruef, warnings)
            zusatzleistungen = self._calc_dguv_addons(merkmale, breakdown)

        # ─── 6. ZUSCHLÄGE (shared) ───────────────────────────
        addon_total = sum(z["preis"] for z in zusatzleistungen)
        total, zuschlaege = self._calc_zuschlaege(merkmale, breakdown.subtotal + addon_total)

        # ─── 7. CONFIDENCE (per product) ─────────────────────
        confidence, conf_reason = self._calc_confidence(gewerk, merkmale)

        # ─── 7b. KALIBRIERUNG confidence adjustment (DGUV Büro only) ─
        nutzung_for_kal = getattr(merkmale, "nutzung", None)
        nutzung_val_kal = nutzung_for_kal.value if nutzung_for_kal else ""
        if self.graph_name == "dguv_v3" and nutzung_val_kal in ("buerogebaeude", "service_center"):
            try:
                from products.dguv_v3.kalibrierung import get_kalibrierung_for_trace
                nutzung = nutzung_for_kal
                gt_name = nutzung.value.replace("_", " ").title() if nutzung else None
                vds = getattr(merkmale, "vds_pruefung", False)
                kal = get_kalibrierung_for_trace(
                    3.10, gebaeudetyp=gt_name, pruefgrundlage="VdS" if vds else "DGUV"
                )
                if kal.kalibriert_rate != kal.basis_rate:
                    gap = kal.range_max / max(kal.range_min, 0.01)
                    if gap > 2.0:
                        confidence *= 0.85
                        n_src = len(kal.quellen) - 1
                        conf_reason += f" · Kalibrierungsdaten ({n_src} Quellen) zeigen Preisspanne ×{gap:.1f}"
                        warnings.append(
                            f"Kalibrierung: Kalkulationshilfen {kal.basis_rate}€/10m² vs. "
                            f"Marktdaten {kal.kalibriert_rate:.1f}€/10m² "
                            f"(Range {kal.range_min}–{kal.range_max}€/10m²)"
                        )
            except Exception:
                pass

        # ─── 8. CROSS-SELL (from graph) ──────────────────────
        self._add_cross_sell(warnings)

        angebot = Angebot(
            gewerk=gewerk.name, total=total, breakdown=breakdown,
            zuschlaege=zuschlaege, confidence=confidence, confidence_reason=conf_reason,
            similar=[], lpv_referenz=gewerk.lpv_referenz, warnings=warnings,
            zusatzleistungen=zusatzleistungen,
        )
        if referenzpreis:
            angebot.referenzpreis = referenzpreis
        return angebot

    # ═══════════════════════════════════════════════════════════
    # SHARED: Grundkosten
    # ═══════════════════════════════════════════════════════════

    def _calc_grundkosten(self, merkmale: BaseModel) -> float:
        pauschale = self._q1("MATCH (g:Grundkosten {id: 'GRUND_PAUSCHALE'}) RETURN g.betrag") or 256
        self._log("grundkosten", "Grundkosten.GRUND_PAUSCHALE", f"{pauschale}", "GRUND_PAUSCHALE",
                  ref="LPV Teil A §4: Pauschale Auftragsanlage 256€")

        ordnung = 0
        if getattr(merkmale, "baurechtlich", False):
            ordnung = self._q1("MATCH (g:Grundkosten {id: 'GRUND_ORDNUNG'}) RETURN g.betrag") or 242
            self._log("grundkosten", "Grundkosten.GRUND_ORDNUNG (baurechtlich)", f"{ordnung}", "GRUND_ORDNUNG",
                      ref="LPV Teil A §4: Ordnungsprüfung 242€ (nur baurechtlich)")

        pruefmittel_tag = self._q1("MATCH (g:Grundkosten {id: 'GRUND_PRUEFMITTEL'}) RETURN g.betrag_pro_tag") or 49
        pruef_tage = self._get_pruef_tage(merkmale)

        self._log("grundkosten", f"Prüfmittel {pruefmittel_tag}€ × {pruef_tage} Tage", f"{pruefmittel_tag * pruef_tage}", "GRUND_PRUEFMITTEL",
                  ref="LPV Teil A §4: 49€ je Prüftag")

        hours_per_day = 8
        days = max(1, int(pruef_tage))
        tg_row = self._q("MATCH (t:Tagegeld) WHERE t.von_h <= $h AND t.bis_h > $h RETURN t.betrag, t.id", h=hours_per_day)
        tg_per_day = tg_row[0][0] if tg_row else (0 if hours_per_day < 6 else 25)
        tagegeld = tg_per_day * days
        self._log("tagegeld", f"Tagegeld ({hours_per_day}h/Tag × {days} Tage)", f"{tagegeld}",
                  tg_row[0][1] if tg_row else "none",
                  ref="LPV Teil A §4.3: 0€ (<6h), 6€ (6-8h), 25€ (8-14h), 30€ (14-24h)")

        return pauschale + ordnung + pruefmittel_tag * pruef_tage + tagegeld

    def _get_pruef_tage(self, merkmale: BaseModel) -> float:
        if self.graph_name == "blitzschutz":
            ms = self._resolve_blitz_ms(merkmale)
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
            flaeche = getattr(merkmale, "gesamtflaeche_m2", 0) or 0  # None-Guard (flaeche Optional)
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

    def _resolve_blitz_ms(self, merkmale: BaseModel) -> int:
        ms = getattr(merkmale, "anzahl_ableitungen", None)
        if ms is not None:
            return ms
        from products.blitzschutz.pricing_rules import estimate_ableitungen
        estimated, _ = estimate_ableitungen(merkmale)
        return estimated

    def _pruef_blitzschutz(self, merkmale: BaseModel) -> float:
        ms = self._resolve_blitz_ms(merkmale)
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
            self._log("pruefkosten", f"Staffel {sid}: {in_band}×{preis}€", f"{cost}", sid, ref=ref)
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
            self._log("pruefkosten", f"HYG: {bereiche} Bereiche × ({stunden_pro_b}h × {stundensatz}€ + {labor}€ Labor)", f"{cost}", "RLT_HYG",
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
                self._log("pruefkosten", f"Grundpreis Garage: {sp} SP → {rows[0][1]}", f"{grund}", rows[0][2],
                          ref="LPV B05 Kap. 2.2: Grundpreis per Stellplatz-Bereich")
            else:
                grund = 450 if sp <= 30 else (690 if sp <= 100 else 1250)
                self._log("pruefkosten", f"Grundpreis Garage fallback: {sp} SP", f"{grund}")
        elif vol is not None:
            rows = self._q(
                "MATCH (p:Produkt {id: 'RLT_STANDARD'})-[:HAT_GRUNDPREIS]->(g:Grundpreis) "
                "WHERE g.von_volumenstrom <= $vol AND g.bis_volumenstrom >= $vol "
                "RETURN g.betrag, g.id", vol=vol)
            if rows:
                grund = rows[0][0]
                self._log("pruefkosten", f"Grundpreis RLT: {vol} m³/h", f"{grund}", rows[0][1],
                          ref="LPV B05 Kap. 2.1: Grundpreis per Volumenstrom")
            else:
                grund = 600
                self._log("pruefkosten", "Grundpreis RLT fallback", f"{grund}")
        else:
            grund = 600
            self._log("pruefkosten", "Grundpreis RLT default (keine SP/Vol)", f"{grund}")

        vent = getattr(merkmale, "anzahl_ventilatoren", None) or 0
        bsk = getattr(merkmale, "anzahl_brandschutzklappen", None) or 0
        if vent > 0:
            vent_row = self._q("MATCH (z:ZuschlagStueck {id: 'ZS_VENTILATOR'}) RETURN z.betrag_pro_stueck")
            vent_preis = vent_row[0][0] if vent_row else 170
            grund += vent * vent_preis
            self._log("pruefkosten", f"Ventilatoren: {vent} × {vent_preis}€", f"{vent * vent_preis}", "ZS_VENTILATOR",
                      ref="LPV B05 Kap. 2: 170€/Ventilator")
        if bsk > 0:
            bsk_row = self._q("MATCH (z:ZuschlagStueck {id: 'ZS_BSK'}) RETURN z.betrag_pro_stueck")
            bsk_preis = bsk_row[0][0] if bsk_row else 40
            grund += bsk * bsk_preis
            self._log("pruefkosten", f"BSK: {bsk} × {bsk_preis}€", f"{bsk * bsk_preis}", "ZS_BSK",
                      ref="LPV B05 Kap. 2: 40€/BSK")
        return grund

    # ═══════════════════════════════════════════════════════════
    # PRÜFKOSTEN: DGUV V3 (Grundpreis + Fläche×Kat + Vert + SZ)
    # ═══════════════════════════════════════════════════════════

    def _pruef_dguv(self, merkmale: BaseModel) -> float:
        from products.dguv_v3.merkmale import Pruefart
        pa = getattr(merkmale, "pruefart", Pruefart.DGUV_ORTSFEST)

        produkt = self._q("MATCH (p:Produkt {id: 'DGUV_V3_ORTSFEST'}) RETURN p.grundpreis")
        grundpreis = produkt[0][0] if produkt else 250
        pruefart_label = "VdS 2871" if pa == Pruefart.VDS else "DGUV+VdS Kombi" if pa == Pruefart.DGUV_PLUS_VDS else "DGUV V3"
        self._log("pruefkosten", f"Grundpreis Anlage ({pruefart_label})", f"{grundpreis}", "DGUV_V3_ORTSFEST",
                  ref="LPV B04 Kap. 2: Grundpreis 250€ pro Anlage")

        flaeche = getattr(merkmale, "gesamtflaeche_m2", 0) or 0  # None-Guard (flaeche Optional)
        mix = getattr(merkmale, "nutzungs_mix", None)

        from products.dguv_v3.pricing_rules import flaechenkosten_degressiv
        kurve_name = "vds" if pa in (Pruefart.VDS, Pruefart.DGUV_PLUS_VDS) else "dguv"
        deg_rows = self._q("MATCH (f:Flaechenstaffel {kurve: $k}) RETURN f.ab_m2, f.faktor ORDER BY f.ab_m2", k=kurve_name)
        deg_kurve = [(float(r[0]), float(r[1])) for r in deg_rows] if deg_rows else [(0, 0.80), (2000, 0.80), (4000, 0.60), (6000, 0.50), (10000, 0.40), (25000, 0.30)]

        if mix and len(mix) > 0:
            flaeche_cost = 0.0
            for eintrag in mix:
                e_kat = getattr(eintrag, "kategorie", None)
                if e_kat is None:
                    from products.dguv_v3.pricing_rules import resolve_mix_kategorie
                    e_kat = resolve_mix_kategorie(eintrag.nutzung)
                e_kat_val = e_kat.value if hasattr(e_kat, "value") else int(e_kat)
                e_kat_id = f"KAT_{e_kat_val}"
                e_row = self._q("MATCH (k:Installationskategorie {id: $kid}) RETURN k.preis_per_10m2, k.name", kid=e_kat_id)
                e_rate = e_row[0][0] if e_row else 1.0
                e_name = e_row[0][1] if e_row else f"Kat {e_kat_val}"
                zone_m2 = flaeche * eintrag.anteil
                zone_cost = flaechenkosten_degressiv(zone_m2, e_rate, deg_kurve)
                flaeche_cost += zone_cost
                self._log("pruefkosten",
                          f"Mix {eintrag.nutzung}: {zone_m2:.0f}m² × {e_rate}€/10m² degressiv ({e_name})",
                          f"{zone_cost:.2f}", e_kat_id,
                          ref=f"Kalkulationshilfen NBG: {e_rate}€/10m² für {e_name}, Flächenstaffel")
        else:
            kat = getattr(merkmale, "primary_installationskategorie", None)
            kat_val = kat.value if kat else 1
            kat_id = f"KAT_{kat_val}"

            kat_row = self._q("MATCH (k:Installationskategorie {id: $kid}) RETURN k.preis_per_10m2, k.name", kid=kat_id)
            rate = kat_row[0][0] if kat_row else 1.0
            kat_name = kat_row[0][1] if kat_row else f"Kat {kat_val}"
            flaeche_cost = flaechenkosten_degressiv(flaeche, rate, deg_kurve)
            self._log("pruefkosten", f"Fläche {flaeche}m² × {rate}€/10m² degressiv ({kat_name})", f"{flaeche_cost}", kat_id,
                      ref=f"Kalkulationshilfen NBG: {rate}€/10m² für {kat_name}, Flächenstaffel")

        # Kalibrierung: compare with real-world data sources (only for Büro — DEKA data is Büro-specific)
        nutzung = getattr(merkmale, "nutzung", None)
        nutzung_val = nutzung.value if nutzung else ""
        if nutzung_val in ("buerogebaeude", "service_center"):
            gt_name = nutzung_val.replace("_", " ").title()
            vds = getattr(merkmale, "vds_pruefung", False)
            pg = "VdS" if vds else "DGUV"
            try:
                from products.dguv_v3.kalibrierung import get_kalibrierung_for_trace
                kal = get_kalibrierung_for_trace(rate, gebaeudetyp=gt_name, pruefgrundlage=pg)
                if kal.kalibriert_rate != kal.basis_rate:
                    kal_cost = (flaeche / 10.0) * kal.kalibriert_rate
                    n_sources = len(kal.quellen) - 1
                    self._log("kalibrierung",
                              f"Kalibrierung ({n_sources} Quellen): {kal.kalibriert_rate}€/10m² → {kal_cost:.0f}€ "
                              f"[Range {kal.range_min}–{kal.range_max}€/10m²]",
                              f"{kal_cost:.2f}",
                              ref=", ".join(q["name"] for q in kal.quellen if q["typ"] != "regel"))
            except Exception:
                pass

        cost = grundpreis + flaeche_cost

        from products.dguv_v3.pricing_rules import _g_komplexitaet, KOMPLEXITAET_SCHWELLE_M2
        k_faktor = _g_komplexitaet(nutzung, flaeche)
        if k_faktor != 1.0:
            cost *= k_faktor
            self._log("pruefkosten",
                      f"Komplexitätsfaktor: ×{k_faktor} (>{KOMPLEXITAET_SCHWELLE_M2}m² + {nutzung_val})",
                      f"{cost:.2f}",
                      ref="Kriterien_Preisfindung_EG.docx (S. Pausch): >10.000m² komplex → 60% Anlagenmerkmale")

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
                self._log("pruefkosten", f"{label}: {count} × {preis}€", f"{vert_cost}", node_prefix,
                          ref=f"Schätzung intern: {preis}€ pro {label} — Rückfrage TÜV")

        for field, node_id, label in [
            ("nea_vorhanden", "SZ_NEA", "Netzersatzanlage"),
            ("sv_nshv_vorhanden", "SZ_SV_NSHV", "Sicherheitsstromversorgung"),
        ]:
            if getattr(merkmale, field, False):
                sz_row = self._q(f"MATCH (s:Sonderzuschlag {{id: '{node_id}'}}) RETURN s.betrag")
                betrag = sz_row[0][0] if sz_row else 0
                cost += betrag
                self._log("pruefkosten", f"{label}: +{betrag}€", f"{betrag}", node_id,
                          ref=f"Schätzung intern: {label} {betrag}€ — Rückfrage TÜV")

        # Branchenvergleich: avg Prüftage from 10k Berichte
        branche_map = {
            "buerogebaeude": "Öffentliche Verwaltung", "service_center": "Öffentliche Verwaltung",
            "hotel": "Gastgewerbe", "krankenhaus": "Gesundheitswesen",
            "schule": "Bildungseinrichtung", "industrie": "Automobilzulieferer",
            "verkaufsstaette": "Lebensmittelhandel", "moebelhaus": "Lebensmittelhandel",
            "gartenmarkt": "Lebensmittelhandel", "tiefgarage": "Öffentliche Verwaltung",
            "versammlungsstaette": "Öffentliche Verwaltung", "seniorentreff": "Gesundheitswesen",
            "sonstige": "Religionsgemeinschaft",
        }
        branche_key = branche_map.get(nutzung_val, "")
        if branche_key:
            bp = self._q(
                "MATCH (b:BranchenProfil) WHERE b.branche = $br RETURN b.n_berichte, b.avg_prueftage, b.median_prueftage",
                br=branche_key
            )
            if bp:
                n_ber, avg_t, med_t = bp[0]
                est_tage = max(1, round(cost / 1200))
                self._log("branchenvergleich",
                          f"Branchenvergleich: {n_ber} {branche_key}-Berichte im Archiv, Ø {avg_t:.1f} Prüftage (Median {med_t:.1f})",
                          f"Schätzung {est_tage} Tage",
                          ref=f"Batch Extraction 10.096 MA507 Prüfberichte")

        if pa == Pruefart.DGUV_PLUS_VDS:
            from products.dguv_v3.pricing_rules import DGUV_VDS_KOMBI_FAKTOR
            cost = round(cost * DGUV_VDS_KOMBI_FAKTOR, 2)
            self._log("pruefkosten", f"DGUV+VdS Kombi: ×{DGUV_VDS_KOMBI_FAKTOR}", f"{cost}", ref="6 Großkunden: Kombi = DGUV × 1.20")

        return cost

    # ═══════════════════════════════════════════════════════════
    # DGUV V3: Zusatzleistungen (VdS, PV, Ladesäulen)
    # ═══════════════════════════════════════════════════════════

    def _calc_dguv_addons(self, merkmale: BaseModel, breakdown) -> list[dict]:
        addons = []

        from products.dguv_v3.merkmale import Pruefart
        pa = getattr(merkmale, "pruefart", Pruefart.DGUV_ORTSFEST)
        if pa in (Pruefart.VDS, Pruefart.DGUV_PLUS_VDS):
            pass  # VdS already handled in _pruef_dguv dispatch
        elif getattr(merkmale, "vds_pruefung", False):
            from products.dguv_v3.pricing_rules import DGUV_VDS_KOMBI_FAKTOR
            kombi_addon = round(cost * (DGUV_VDS_KOMBI_FAKTOR - 1.0), 2) if hasattr(breakdown, 'pruef') else 0
            self._log("zusatzleistung",
                      f"VdS 2871 Kombi: +{kombi_addon:.0f}€",
                      f"{kombi_addon:.2f}", "VDS_KOMBI",
                      ref="6 Großkunden: Kombi = DGUV × 1.20")
            addons.append({
                "name": "VdS 2871 Prüfung (Kombi-Preis)",
                "positionen": [
                    {"name": "VdS bei Kombi-Begehung (×1.20 auf DGUV)", "betrag": kombi_addon},
                ],
                "preis": kombi_addon,
                "quelle": "6 Großkunden: Kombi = DGUV × 1.20",
            })

        pv_kwp = getattr(merkmale, "pv_kwp", None)
        if pv_kwp and pv_kwp > 0:
            from products.dguv_v3.zusatzleistungen import pv_preis_vds, pv_preis_din
            pv_norm = getattr(merkmale, "pv_norm", "din")
            pv = pv_preis_vds(pv_kwp) if pv_norm == "vds" else pv_preis_din(pv_kwp)
            addons.append({
                "name": f"PV-Anlage ({pv_kwp:.0f} kWp, {pv_norm.upper()})",
                "positionen": pv["positionen"],
                "preis": round(pv["preis"], 2),
                "quelle": pv["_quelle"],
            })
            self._log("zusatzleistung", f"PV {pv_norm.upper()} {pv_kwp} kWp", f"{pv['preis']:.2f}€",
                      "PV_ADDON", ref=pv["_quelle"])

        for ls in (getattr(merkmale, "ladesaeulen", None) or []):
            if isinstance(ls, dict) and ls.get("anzahl", 0) > 0:
                from products.dguv_v3.zusatzleistungen import ladesaeulen_preis
                r = ladesaeulen_preis(ls.get("typ", "wallbox"), ls.get("anschluesse", 1), ls["anzahl"])
                addons.append({
                    "name": f"Ladesäulen ({ls['anzahl']}× {ls.get('typ', 'wallbox').upper()})",
                    "positionen": r["positionen"],
                    "preis": round(r["preis"], 2),
                    "quelle": r["_quelle"],
                })
                self._log("zusatzleistung", f"Ladesäulen {ls['anzahl']}× {ls.get('typ', 'wallbox')}",
                          f"{r['preis']:.2f}€", "LS_ADDON", ref=r["_quelle"])

        return addons

    # ═══════════════════════════════════════════════════════════
    # DGUV V3: Reifegrad + Vollerfassung + Referenzpreis
    # ═══════════════════════════════════════════════════════════

    def _apply_dguv_modifiers(self, merkmale: BaseModel, pruef: float, warnings: list) -> tuple[float, dict | None]:
        rg = getattr(merkmale, "reifegrad", None)
        if rg is not None:
            rg_val = rg.value if hasattr(rg, "value") else rg
            rg_id = f"RG_{rg_val}"
            faktor = self._q1("MATCH (r:Reifegrad {id: $rid}) RETURN r.faktor", rid=rg_id)
            if faktor is None:
                from products.dguv_v3.pricing_rules import REIFEGRAD_FAKTOR
                from products.dguv_v3.merkmale import Reifegrad
                faktor = REIFEGRAD_FAKTOR.get(rg if isinstance(rg, Reifegrad) else Reifegrad(rg_val), 1.0)
            if faktor != 1.0:
                old = pruef
                pruef = pruef * faktor
                self._log("reifegrad", f"Reifegrad {rg_val}: ×{faktor:.2f}", f"{pruef:.2f} (war {old:.2f})", rg_id,
                          ref=f"Veit P7: RG{rg_val} Faktor {faktor}")

        voll = getattr(merkmale, "vollerfassung", False)
        if voll:
            faktor_v = self._q1("MATCH (d:Dokumentationszuschlag {id: 'DOK_VOLL'}) RETURN d.faktor") or 1.30
            old = pruef
            pruef = pruef * faktor_v
            self._log("vollerfassung", f"Vollerfassung Messdaten: ×{faktor_v:.2f}", f"{pruef:.2f} (war {old:.2f})", "DOK_VOLL",
                      ref="Veit P6: +30% bei 100% Messdatenerfassung")

        referenzpreis = None
        ref_jahr = getattr(merkmale, "referenzpreis_jahr", None)
        ref_betrag = getattr(merkmale, "referenzpreis_betrag", None)
        if ref_jahr and ref_betrag:
            steigerung = self._q1("MATCH (p:Preissteigerung {jahr: $j}) RETURN p.steigerung_vs_2026", j=ref_jahr)
            if steigerung is None:
                from products.dguv_v3.pricing_rules import PREISSTEIGERUNG
                steigerung = PREISSTEIGERUNG.get(ref_jahr, 0)
            fortgeschrieben = ref_betrag * (1 + steigerung)
            referenzpreis = {
                "original_jahr": ref_jahr,
                "original_betrag": ref_betrag,
                "steigerung_pct": steigerung * 100,
                "fortgeschrieben_2026": round(fortgeschrieben, 2),
            }
            self._log("referenzpreis", f"Referenz {ref_jahr}: {ref_betrag}€ → 2026: {fortgeschrieben:.0f}€ (+{steigerung*100:.1f}%)",
                      f"{fortgeschrieben:.2f}", f"PS_{ref_jahr}",
                      ref=f"Veit P9: Preissteigerung {ref_jahr}→2026 = +{steigerung*100:.1f}%")

        return pruef, referenzpreis

    # ═══════════════════════════════════════════════════════════
    # SHARED: Reisekosten
    # ═══════════════════════════════════════════════════════════

    def _calc_reisekosten(self, merkmale: BaseModel, warnings: list) -> float:
        lat = getattr(merkmale, "adresse_lat", None)
        lon = getattr(merkmale, "adresse_lon", None)
        if not lat or not lon:
            plz = getattr(merkmale, "adresse_plz", None)
            if plz:
                from common.geocode import geocode
                coords = geocode(ort=None, plz=plz)
                if coords:
                    lat, lon = coords
            if not lat or not lon:
                warnings.append("Adresse ohne Koordinaten — Reisekosten nicht berechnet")
                return 0

        from common.pricing_primitives import find_nearest_standort
        plz = getattr(merkmale, "adresse_plz", None)
        standort = find_nearest_standort(lat, lon, plz=plz)

        zuordnung = standort.get("zuordnung", "nearest")
        if zuordnung == "crm":
            self._log("reisekosten", f"PLZ {plz} → CRM-Zuordnung NL {standort.get('crm_nl', '?')} → {standort['name']}",
                      f"CRM PLZ→NL Mapping", f"STD_{standort.get('id','?')}",
                      ref="CRM-Daten: 8.309 PLZ→Niederlassung (TÜV SÜD intern)")
        else:
            self._log("reisekosten", f"PLZ {plz} nicht in CRM → nächster Standort: {standort['name']} (Luftlinie)",
                      f"Nearest Fallback", f"STD_{standort.get('id','?')}",
                      ref="Fallback: Haversine-Distanz zu 20 TÜV-Standorten")

        km_ow = standort["distance_km"]
        km_rt = km_ow * 2
        dur_min_ow = standort.get("duration_min", km_ow / 80 * 60)
        dur_min_rt = dur_min_ow * 2
        routing = standort.get("routing", "Haversine")
        self._log("reisekosten", f"Entfernung: {km_ow:.0f}km one-way × 2 = {km_rt:.0f}km roundtrip ({routing})",
                  f"{km_rt:.0f}km RT", f"STD_{standort.get('id','?')}",
                  ref=f"Routing: {standort['name']} → {getattr(merkmale, 'adresse_ort', 'Objekt')} ({routing})")

        km_rate = self._q1("MATCH (r:Reisekostenregel {id: 'RK_PKW'}) RETURN r.betrag_pro_km") or 1.10
        reise_std = self._q1("MATCH (s:Stundensatz {id: 'STD_EINFACH'}) RETURN s.betrag") or 180.0

        fahrtkosten = km_rt * km_rate
        reisezeit_h = dur_min_rt / 60
        reisezeit_kosten = reisezeit_h * reise_std
        reise_single = fahrtkosten + reisezeit_kosten
        self._log("reisekosten",
                  f"Einzelanfahrt: {km_rt:.0f}km × {km_rate}€/km = {fahrtkosten:.0f}€ + {reisezeit_h:.1f}h × {reise_std:.0f}€/h = {reisezeit_kosten:.0f}€",
                  f"{reise_single:.0f}€", "RK_PKW",
                  ref=f"LPV Teil A §4.3: PKW {km_rate}€/km + Reisezeit {reise_std}€/h")

        pruef_tage = self._get_pruef_tage(merkmale)
        pruef_stunden = pruef_tage * 8
        if pruef_stunden > 18:
            anzahl_anfahrten = 3
        elif pruef_stunden > 9:
            anzahl_anfahrten = 2
        else:
            anzahl_anfahrten = 1
        reise = reise_single * anzahl_anfahrten

        self._log("reisekosten",
                  f"{anzahl_anfahrten} Anfahrt{'en' if anzahl_anfahrten > 1 else ''} × {reise_single:.0f}€ = {reise:.0f}€ ({pruef_stunden:.0f}h Prüfzeit → Regel: ≤9h=1, >9h=2, >18h=3)",
                  f"{reise:.0f}€", "RK_MEHRTAEGIG",
                  ref="S. Veit: Mehrtägig >9h=2 Anfahrten, >18h=3 Anfahrten")

        zuordnung_warnung = standort.get("zuordnung_warnung")
        if zuordnung_warnung:
            warnings.append(f"⚠ {zuordnung_warnung}")
        label = "Zuständiger TÜV-Standort" if zuordnung == "crm" else "Nächster TÜV-Standort"
        if standort["distance_km"] > 0:
            warnings.append(f"{label}: {standort['name']} ({standort.get('adresse','')}, {standort['plz']}) — "
                          f"{standort['distance_km']:.0f} km / {dur_min_ow:.0f} min [{standort.get('routing','')}]")
        return reise

    # ═══════════════════════════════════════════════════════════
    # SHARED: Berichterstellung (per product logic)
    # ═══════════════════════════════════════════════════════════

    def _calc_bericht(self, gewerk: Gewerk, merkmale: BaseModel) -> float:
        typ = gewerk.choose_bericht_typ(merkmale)
        typ_map = {"klein": ("BER_KLEIN", 119), "standard": ("BER_STANDARD", 380), "komplex": ("BER_KOMPLEX", 550)}
        bid, fallback = typ_map.get(typ, ("BER_STANDARD", 380))
        betrag = self._q1(f"MATCH (b:Berichtstyp {{id: '{bid}'}}) RETURN b.betrag") or fallback
        self._log("bericht", f"Berichtstyp {bid} ({typ})", f"{betrag}", bid,
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
                self._log("zuschlag", f"{name}: +{pct*100:.0f}%", f"{amount:.2f}", zid, ref=ref)

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
