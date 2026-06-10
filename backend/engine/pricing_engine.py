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
        """Main entry point — returns complete Angebot."""

        # Walidacja schema
        if not isinstance(merkmale, gewerk.merkmale_schema):
            raise TypeError(
                f"Expected {gewerk.merkmale_schema.__name__}, got {type(merkmale).__name__}"
            )

        breakdown = Breakdown()
        warnings = []

        # 1. Grundkosten (Pauschale + Prüfmittel × Prüftage + Tagegeld)
        pruef_tage = gewerk.estimate_pruef_tage(merkmale)
        g_override = getattr(gewerk, "grundkosten_override", lambda m: None)(merkmale)
        if g_override is not None:
            breakdown.grund = g_override
        else:
            include_ordnung = getattr(merkmale, "baurechtlich", False)
            breakdown.grund = (
                grundkosten_pauschal(include_ordnungspruefung=include_ordnung)
                + PRUEFMITTEL_PRO_TAG_SV * pruef_tage
                + tagegeld(pruef_tage * 8)  # 8h per Prüftag jako upraszczenie
            )

        # 2. Prüfkosten (per-Gewerk logic)
        breakdown.pruef = gewerk.pruefkosten(merkmale)

        # 3. Reisekosten (if Anlage address available)
        # Veit 30.05: >9h = 2 Anfahrten, >18h = 3 Anfahrten
        adresse_lat = getattr(merkmale, "adresse_lat", None)
        adresse_lon = getattr(merkmale, "adresse_lon", None)
        if adresse_lat is not None and adresse_lon is not None:
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
            breakdown.reise = (
                kilometergeld(km_roundtrip * anzahl_anfahrten, vehicle="pkw")
                + reisezeit_h * anzahl_anfahrten * stundensatz(self.default_reisezeit_stundensatz)
            )
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
        else:
            bericht_typ = BerichtTyp(bericht_typ_str)
            breakdown.bericht = berichtskosten(bericht_typ)

        # 5. Zuschläge (per-Gewerk + shared)
        subtotal = breakdown.subtotal
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
            breakdown=breakdown,
            zuschlaege=zuschlaege_applied,
            confidence=confidence,
            confidence_reason=reason,
            similar=[],  # TODO: graph lookup (Phase 1 M2.2)
            lpv_referenz=gewerk.lpv_referenz,
            warnings=warnings,
        )
