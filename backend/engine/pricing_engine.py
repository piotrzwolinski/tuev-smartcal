"""Universal pricing executor.

Dla każdego Gewerku wykonuje identyczny flow:
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
        include_ordnung = getattr(merkmale, "baurechtlich", False)
        breakdown.grund = (
            grundkosten_pauschal(include_ordnungspruefung=include_ordnung)
            + PRUEFMITTEL_PRO_TAG_SV * pruef_tage
            + tagegeld(pruef_tage * 8)  # 8h per Prüftag jako upraszczenie
        )

        # 2. Prüfkosten (per-Gewerk logic)
        breakdown.pruef = gewerk.pruefkosten(merkmale)

        # 3. Reisekosten (jeśli mamy adres Anlage)
        # Veit-Spec: "Bei mehrtägigen Prüfungen ist von maximalen Anfahrten auszugehen"
        # → NUR 1 Hin-/Rückfahrt, egal wie viele Prüftage
        adresse_lat = getattr(merkmale, "adresse_lat", None)
        adresse_lon = getattr(merkmale, "adresse_lon", None)
        if adresse_lat is not None and adresse_lon is not None:
            standort = find_nearest_standort(adresse_lat, adresse_lon)
            km_one_way = standort["distance_km"]
            km_roundtrip = km_one_way * 2
            # Reisezeit: OSRM liefert echte Fahrzeit, sonst km/80 fallback
            duration_min = standort.get("duration_min", km_one_way / 80 * 60)
            reisezeit_h = (duration_min * 2) / 60  # roundtrip
            routing = standort.get("routing", "unknown")
            breakdown.reise = (
                kilometergeld(km_roundtrip, vehicle="pkw")
                + reisezeit_h * stundensatz(self.default_reisezeit_stundensatz)
            )
            if km_one_way > 0:
                warnings.append(
                    f"Nächster TÜV-Standort: {standort['name']} "
                    f"({standort.get('adresse', '')}, {standort['plz']}) — "
                    f"{km_one_way:.0f} km / {duration_min:.0f} min einfach "
                    f"[{routing}]"
                )
        else:
            warnings.append("Adresse ohne Koordinaten — Reisekosten nicht berechnet")

        # 4. Berichterstellung
        bericht_typ_str = gewerk.choose_bericht_typ(merkmale)
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
