"""Universal pricing executor.

For each Gewerk executes identical flow:
    Grundkosten (shared) + Prüfkosten (per-Gewerk) + Reisekosten (shared) + Bericht (shared)
    → Zuschläge (shared + per-Gewerk)
    → Confidence scoring (per-Gewerk validation)
    → Similar Anlagen (graph lookup)
"""

from __future__ import annotations

from pydantic import BaseModel

from engine.gewerk import Gewerk, Angebot, Breakdown, ZuschlagApplied
from common.trace import Trace, emit
from common.pricing_primitives import (
    grundkosten_pauschal,
    PRUEFMITTEL_PRO_TAG_SV,
    tagegeld,
    kilometergeld,
    stundensatz,
    berichtskosten,
    BerichtTyp,
    find_nearest_standort,
    TUEV_NIEDERLASSUNGEN,
)


class PricingEngine:
    """Wykonuje kalkulacje dla dowolnego Gewerku."""

    def __init__(self, default_reisezeit_stundensatz: str = "einfach"):
        self.default_reisezeit_stundensatz = default_reisezeit_stundensatz

    # ─────────────────────────────────────────────────────────
    def calculate(self, gewerk: Gewerk, merkmale: BaseModel) -> Angebot:
        """Main entry point — sammelt den Trace (Synapse §3) und hängt ihn ans Angebot."""
        with Trace() as t:
            angebot = self._calculate(gewerk, merkmale)
            angebot.provenance = t.steps
            return angebot

    def _calculate(self, gewerk: Gewerk, merkmale: BaseModel) -> Angebot:
        """Berechnung — emittiert Trace-Schritte an den aktiven Kontext (von calculate gesetzt)."""

        # Walidacja schema
        if not isinstance(merkmale, gewerk.merkmale_schema):
            raise TypeError(
                f"Expected {gewerk.merkmale_schema.__name__}, got {type(merkmale).__name__}"
            )

        breakdown = Breakdown()
        warnings = []

        # 1. Grundkosten (Pauschale + Prüfmittel × Prüftage + Tagegeld)
        pruef_tage = gewerk.estimate_pruef_tage(merkmale)
        emit("prueftage", "Geschätzte Prüftage", f"{pruef_tage} Tage", "PRUEFTAGE", "Heuristik")
        g_override = getattr(gewerk, "grundkosten_override", lambda m: None)(merkmale)
        if g_override is not None:
            breakdown.grund = g_override
            emit("grundkosten", "Grundkosten (Gewerk-Override)", round(g_override, 2), "GRUND_OVERRIDE", "Gewerk-spezifisch")
        else:
            include_ordnung = getattr(merkmale, "baurechtlich", False)
            pauschale = grundkosten_pauschal(include_ordnungspruefung=include_ordnung)
            pruefmittel = PRUEFMITTEL_PRO_TAG_SV * pruef_tage
            tg = tagegeld(pruef_tage * 8)  # 8h per Prüftag jako upraszczenie
            breakdown.grund = pauschale + pruefmittel + tg
            emit("grundkosten", "Grundpauschale Auftrag" + (" + Ordnungsprüfung" if include_ordnung else ""),
                 round(pauschale, 2), "GRUND_PAUSCHALE", "LPV Teil A §4")
            emit("grundkosten", f"Prüfmittel {PRUEFMITTEL_PRO_TAG_SV}€ × {pruef_tage} Tage",
                 round(pruefmittel, 2), "GRUND_PRUEFMITTEL", "LPV Teil A §4: je Prüftag")
            emit("grundkosten", f"Tagegeld (8h/Tag × {pruef_tage} Tage)", round(tg, 2), "TAGEGELD", "LPV Teil A §4.3")

        # 2. Prüfkosten (per-Gewerk logic — emittiert eigene Schritte via pricing_rules)
        breakdown.pruef = gewerk.pruefkosten(merkmale)

        # 3. Reisekosten (if Anlage address available)
        # Veit 30.05: >9h = 2 Anfahrten, >18h = 3 Anfahrten
        reise_inkl = getattr(gewerk, "reise_inklusive", lambda m: False)(merkmale)
        adresse_lat = getattr(merkmale, "adresse_lat", None)
        adresse_lon = getattr(merkmale, "adresse_lon", None)
        if reise_inkl:
            # MA560 ortsveränderlich: Grundpauschale + €/Gerät ist all-inclusive (kalibriert
            # gegen reale Auftragspreise T04/T10 OHNE separate Reise → sonst Doppelzählung).
            emit("reisekosten", "Reisekosten in Pauschale enthalten (all-inclusive)", 0.0,
                 "RK_INKLUSIVE", "MA560: Grundpauschale + €/Gerät all-inclusive")
        elif adresse_lat is not None and adresse_lon is not None:
            adresse_plz = getattr(merkmale, "adresse_plz", None)
            standort = find_nearest_standort(adresse_lat, adresse_lon, plz=adresse_plz)
            km_one_way = standort["distance_km"]
            km_roundtrip = km_one_way * 2
            duration_min = standort.get("duration_min", km_one_way / 80 * 60)
            reisezeit_h = (duration_min * 2) / 60  # roundtrip single trip
            routing = standort.get("routing", "unknown")
            pruef_stunden = pruef_tage * 8
            if pruef_stunden > 18:
                anzahl_anfahrten = 3
            elif pruef_stunden > 9:
                anzahl_anfahrten = 2
            else:
                anzahl_anfahrten = 1
            reisezeit_charged = reisezeit_h
            if pruef_tage < 1.0:
                reisezeit_charged = reisezeit_h * pruef_tage
            km_kosten = kilometergeld(km_roundtrip * anzahl_anfahrten, vehicle="pkw")
            zeit_kosten = reisezeit_charged * anzahl_anfahrten * stundensatz(self.default_reisezeit_stundensatz)
            breakdown.reise = km_kosten + zeit_kosten
            emit("reisekosten", f"Standort {standort['name']} — {km_one_way:.0f} km einfach, {anzahl_anfahrten} Anfahrt(en)",
                 f"{km_roundtrip * anzahl_anfahrten:.0f} km gesamt", standort.get("crm_nl", "STANDORT"),
                 "CRM PLZ→NL · " + routing)
            emit("reisekosten", f"Kilometergeld {km_roundtrip * anzahl_anfahrten:.0f} km × 1,1€/km",
                 round(km_kosten, 2), "RK_PKW", "LPV Teil A §4.3")
            emit("reisekosten", f"Reisezeit {reisezeit_charged:.1f}h × {anzahl_anfahrten} Anfahrt(en)",
                 round(zeit_kosten, 2), "RK_ZEIT", "LPV Teil A §4.3: Stundensatz")
            zuordnung = standort.get("zuordnung", "nearest")
            if km_one_way > 0:
                label = "Zuständiger TÜV-Standort" if zuordnung == "crm" else "Nächster TÜV-Standort"
                anfahrt_info = f" · {anzahl_anfahrten} Anfahrt(en)" if anzahl_anfahrten > 1 else ""
                warnings.append(
                    f"{label}: {standort['name']} "
                    f"({standort.get('adresse', '')}, {standort['plz']}) — "
                    f"{km_one_way:.0f} km / {duration_min:.0f} min einfach "
                    f"[{routing}]{anfahrt_info}"
                )
            zuordnung_warnung = standort.get("zuordnung_warnung")
            if zuordnung_warnung:
                warnings.append(f"⚠ {zuordnung_warnung}")
        else:
            warnings.append("Adresse ohne Koordinaten — Reisekosten nicht berechnet")

        # 4. Berichterstellung
        bericht_typ_str = gewerk.choose_bericht_typ(merkmale)
        if bericht_typ_str == "inklusive":
            breakdown.bericht = 0
            emit("bericht", "Bericht inklusive (Kleinauftrag / ortsveränderlich)", 0.0, "BER_INKLUSIVE", "LPV")
        else:
            bericht_typ = BerichtTyp(bericht_typ_str)
            breakdown.bericht = berichtskosten(bericht_typ)
            emit("bericht", f"Berichtstyp {bericht_typ_str}", round(breakdown.bericht, 2),
                 f"BER_{bericht_typ_str.upper()}",
                 "LPV: kleiner Bericht 119€ · komplex 550€ (Baurecht / Elektrothermographie / Sonderanforderung)")

        # 4b. Zusatzleistungen (PV / Ladesäulen — per-Gewerk Addon-Hook)
        zusatzleistungen = gewerk.zusatzleistungen(merkmale)
        addon_total = sum(z["preis"] for z in zusatzleistungen)

        # 5. Zuschläge (per-Gewerk + shared) — auf subtotal inkl. Addons
        subtotal = breakdown.subtotal + addon_total
        zuschlaege_applied: list[ZuschlagApplied] = []
        total = subtotal
        for (name, percent) in gewerk.zuschlaege(merkmale):
            amount = total * percent
            total += amount
            zuschlaege_applied.append(ZuschlagApplied(
                name=name, percent=percent, amount=amount
            ))

        # 6. Confidence scoring (per-Gewerk validation)
        confidence, reason = gewerk.validate_ranges(merkmale)

        return Angebot(
            gewerk=gewerk.name,
            total=total,
            zusatzleistungen=zusatzleistungen,
            breakdown=breakdown,
            zuschlaege=zuschlaege_applied,
            confidence=confidence,
            confidence_reason=reason,
            similar=[],  # TODO: graph lookup (Phase 1 M2.2)
            lpv_referenz=gewerk.lpv_referenz,
            warnings=warnings,
        )
