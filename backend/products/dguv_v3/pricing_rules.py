"""DGUV V3 ortsfeste elektrische Anlage pricing rules — LPV B04 Kap. 2.

Formula: Grundpreis (250€) + Fläche × Preis_per_10m² (wg Installationskategorie).

LPV B04 Kap. 2:
- Grundpreis: 250€ per Anlage
- Fläche-Faktor (per 10 m² kategorii instalacji):
  - Kat 1 (Büro):       1,00 €
  - Kat 2 (Produktion): 2,00 €
  - Kat 3 (Lager):      1,50 €
  - Kat 4 (Verkehrsfläche): 3,00 €
  - Kat 5 (Sonder):     5,00 €

TODO M3.4: walidacja przeciwko Gersthofen (1,393 pozycji Verteiler-Ebene).
"""

from products.dguv_v3.merkmale import DGUVMerkmale, GebaeudeNutzungDGUV, Installationskategorie
from common.pricing_primitives import (
    ZUSCHLAG_NICHT_VEREINSMITGLIED,
    ZUSCHLAG_EILZUSCHLAG,
    ZUSCHLAG_ERSTPRUEFUNG,
)


DGUV_GRUNDPREIS_ANLAGE = 250.00

# LPV B04 Kap. 2: €/10 m² per Installationskategorie
PREIS_PER_10M2 = {
    Installationskategorie.KAT_1: 1.00,
    Installationskategorie.KAT_2: 2.00,
    Installationskategorie.KAT_3: 1.50,
    Installationskategorie.KAT_4: 3.00,
    Installationskategorie.KAT_5: 5.00,
}

# Zuschläge za NEA / SV-NSHV
ZUSCHLAG_NEA = 320.00
ZUSCHLAG_SV_NSHV = 180.00

# Verteilungen — Grundkosten per Einheit
PREIS_VERTEILUNG_UV = 25.00   # Unterverteilung
PREIS_VERTEILUNG_HV = 85.00   # Hauptverteilung
PREIS_VERTEILUNG_NSHV = 145.00  # NSHV


def dguv_pruefkosten(m: DGUVMerkmale) -> float:
    """LPV B04 Kap. 2: 250€ Grundpreis + Fläche × €/10m² + Verteilungen + Zuschläge."""
    cost = DGUV_GRUNDPREIS_ANLAGE

    # Fläche-based
    rate = PREIS_PER_10M2[m.primary_installationskategorie]
    cost += (m.gesamtflaeche_m2 / 10.0) * rate

    # Verteilungen
    cost += m.anzahl_verteilungen_uv * PREIS_VERTEILUNG_UV
    cost += m.anzahl_verteilungen_hv * PREIS_VERTEILUNG_HV
    cost += m.anzahl_verteilungen_nshv * PREIS_VERTEILUNG_NSHV

    # Zuschläge za security-critical
    if m.nea_vorhanden:
        cost += ZUSCHLAG_NEA
    if m.sv_nshv_vorhanden:
        cost += ZUSCHLAG_SV_NSHV

    return cost


def dguv_estimate_pruef_tage(m: DGUVMerkmale) -> float:
    """Heurystyka: 1 dzień per ~500 m² w kat. 1. TODO walidacja na MA507 sample."""
    flaeche = m.gesamtflaeche_m2
    if flaeche <= 500:
        return 0.5
    if flaeche <= 2000:
        return 1.0
    if flaeche <= 5000:
        return 2.0
    return max(2.0, flaeche / 2500)


def dguv_choose_bericht_typ(m: DGUVMerkmale) -> str:
    total_verteilungen = (
        m.anzahl_verteilungen_uv + m.anzahl_verteilungen_hv + m.anzahl_verteilungen_nshv
    )
    if m.gesamtflaeche_m2 <= 500 and total_verteilungen <= 3:
        return "klein"
    if m.gesamtflaeche_m2 <= 5000 and total_verteilungen <= 15:
        return "standard"
    return "komplex"


def dguv_zuschlaege(m: DGUVMerkmale) -> list[tuple[str, float]]:
    z = []
    if not m.vereinsmitglied:
        z.append(("Nicht-Vereinsmitglied", ZUSCHLAG_NICHT_VEREINSMITGLIED))
    if m.eilzuschlag:
        z.append(("Eilzuschlag / Sondertermin", ZUSCHLAG_EILZUSCHLAG))
    if m.erstpruefung:
        z.append(("Erstprüfung", ZUSCHLAG_ERSTPRUEFUNG))
    return z


TYPICAL_FLAECHE = {
    GebaeudeNutzungDGUV.BUEROGEBAEUDE: (100, 5000),
    GebaeudeNutzungDGUV.SERVICE_CENTER: (200, 3000),
    GebaeudeNutzungDGUV.SENIORENTREFF: (50, 1000),
    GebaeudeNutzungDGUV.HOTEL: (500, 15000),
    GebaeudeNutzungDGUV.KRANKENHAUS: (2000, 100000),
    GebaeudeNutzungDGUV.INDUSTRIE: (500, 50000),
    GebaeudeNutzungDGUV.SCHULE: (500, 10000),
    GebaeudeNutzungDGUV.VERKAUFSSTAETTE: (200, 20000),
    GebaeudeNutzungDGUV.SONSTIGE: (50, 50000),
}

TYPICAL_KAT = {
    GebaeudeNutzungDGUV.BUEROGEBAEUDE: Installationskategorie.KAT_1,
    GebaeudeNutzungDGUV.SERVICE_CENTER: Installationskategorie.KAT_1,
    GebaeudeNutzungDGUV.SENIORENTREFF: Installationskategorie.KAT_1,
    GebaeudeNutzungDGUV.HOTEL: Installationskategorie.KAT_1,
    GebaeudeNutzungDGUV.INDUSTRIE: Installationskategorie.KAT_2,
    GebaeudeNutzungDGUV.SCHULE: Installationskategorie.KAT_1,
    GebaeudeNutzungDGUV.VERKAUFSSTAETTE: Installationskategorie.KAT_1,
}


def dguv_validate_ranges(m: DGUVMerkmale) -> tuple[float, str]:
    reasons = []
    confidence = 1.0

    lo, hi = TYPICAL_FLAECHE.get(m.nutzung, (50, 50000))
    if m.gesamtflaeche_m2 < lo:
        confidence *= 0.85
        reasons.append(
            f"Gesamtfläche ({m.gesamtflaeche_m2:.0f} m²) unter typisch "
            f"für {m.nutzung.value} ({lo}-{hi} m²)"
        )
    elif m.gesamtflaeche_m2 > hi * 1.5:
        confidence *= 0.75
        reasons.append(
            f"Gesamtfläche ({m.gesamtflaeche_m2:.0f} m²) deutlich über typisch "
            f"für {m.nutzung.value} ({lo}-{hi} m²)"
        )

    typical_kat = TYPICAL_KAT.get(m.nutzung)
    if typical_kat and m.primary_installationskategorie != typical_kat:
        confidence *= 0.9
        reasons.append(
            f"Installationskategorie {m.primary_installationskategorie.value} "
            f"untypisch für {m.nutzung.value} (typisch Kat {typical_kat.value})"
        )

    total_vert = m.anzahl_verteilungen_uv + m.anzahl_verteilungen_hv + m.anzahl_verteilungen_nshv
    if total_vert == 0:
        confidence *= 0.8
        reasons.append("Keine Verteilungen angegeben — Prüfumfang unklar")

    reason = " · ".join(reasons) if reasons else "Alle Merkmale in typischen Bereichen"
    return confidence, reason
