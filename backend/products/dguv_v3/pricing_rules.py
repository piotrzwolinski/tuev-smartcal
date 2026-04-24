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

from products.dguv_v3.merkmale import DGUVMerkmale, Installationskategorie


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
