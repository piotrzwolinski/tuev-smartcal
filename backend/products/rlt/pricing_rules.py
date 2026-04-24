"""RLT pricing rules — LPV B05 Kap. 2.

HYG (VDI 6022): Stundensatz 208€ × Laborprobenlat (Phase 1 heuristic).
GARAGE (WPBA): Grundpreis 600/780€ per Volumenstrom-range + Ventilatoren 170€/St. + BSK 40€/St.
    Dla Garagen: 450/690/1250€ per Stellplatz-Bereich (B05 Kap. 2.2).

TODO M3.3 (KW18): walidacja przeciwko Vorlage GT-RLT / GT-Hygiene sheets + MUC Preistool VDI 6022.
"""

from products.rlt.merkmale import RLTMerkmale, RLTVariant
from common.pricing_primitives import stundensatz


# ──────────────────────────────────────────────────────────────
# HYG constants (LPV B05 Kap. 2.7 — VDI 6022)
# ──────────────────────────────────────────────────────────────
HYG_STUNDENSATZ_LEVEL = "schwierig"  # 208 €/h
HYG_STUNDEN_PRO_BEREICH = 2.5        # heurystyka, TODO walidacja
HYG_LABOR_PAUSCHALE = 180.00         # Laborprobe-Verarbeitung


# ──────────────────────────────────────────────────────────────
# GARAGE constants (LPV B05 Kap. 2.2)
# ──────────────────────────────────────────────────────────────
GARAGE_GRUNDPREIS_KLEIN = 450.00     # ≤ 30 Stellplätze
GARAGE_GRUNDPREIS_MITTEL = 690.00    # 31-100 Stellplätze
GARAGE_GRUNDPREIS_GROSS = 1250.00    # > 100 Stellplätze

# Standard RLT (B05 Kap. 2.1) — dla nicht-Garage WPBA
RLT_GRUNDPREIS_BIS_10K = 600.00      # ≤ 10,000 m³/h
RLT_GRUNDPREIS_BIS_50K = 780.00      # ≤ 50,000 m³/h
RLT_GRUNDPREIS_GROSS = 1100.00       # > 50,000 m³/h

RLT_VENTILATOR_STK = 170.00          # €/Ventilator
RLT_BSK_STK = 40.00                  # €/Brandschutzklappe


def rlt_pruefkosten(m: RLTMerkmale) -> float:
    if m.variant == RLTVariant.HYGIENE:
        return _hyg_pruefkosten(m)
    return _garage_pruefkosten(m)


def _hyg_pruefkosten(m: RLTMerkmale) -> float:
    """Hygiene VDI 6022 — Stundensatz × bereiche."""
    bereiche = m.anzahl_pruefbereiche_hyg or 1
    stunden = bereiche * HYG_STUNDEN_PRO_BEREICH
    return stunden * stundensatz(HYG_STUNDENSATZ_LEVEL) + bereiche * HYG_LABOR_PAUSCHALE


def _garage_pruefkosten(m: RLTMerkmale) -> float:
    """Garagenlüftung + standardowe RLT WPBA."""
    # Garage-based pricing
    if m.stellplaetze is not None:
        if m.stellplaetze <= 30:
            grund = GARAGE_GRUNDPREIS_KLEIN
        elif m.stellplaetze <= 100:
            grund = GARAGE_GRUNDPREIS_MITTEL
        else:
            grund = GARAGE_GRUNDPREIS_GROSS
    # Volumenstrom-based pricing (non-Garage RLT)
    elif m.nennvolumenstrom_m3h is not None:
        v = m.nennvolumenstrom_m3h
        if v <= 10000:
            grund = RLT_GRUNDPREIS_BIS_10K
        elif v <= 50000:
            grund = RLT_GRUNDPREIS_BIS_50K
        else:
            grund = RLT_GRUNDPREIS_GROSS
    else:
        grund = RLT_GRUNDPREIS_BIS_10K  # fallback

    # Add-ons
    grund += (m.anzahl_ventilatoren or 0) * RLT_VENTILATOR_STK
    grund += (m.anzahl_brandschutzklappen or 0) * RLT_BSK_STK

    return grund


def rlt_estimate_pruef_tage(m: RLTMerkmale) -> float:
    if m.variant == RLTVariant.HYGIENE:
        bereiche = m.anzahl_pruefbereiche_hyg or 1
        return max(0.5, bereiche * 0.4)  # 0.4 dnia per bereich
    # Garage
    if m.stellplaetze is None:
        return 0.5
    if m.stellplaetze <= 30:
        return 0.5
    if m.stellplaetze <= 100:
        return 1.0
    return 2.0


def rlt_choose_bericht_typ(m: RLTMerkmale) -> str:
    if m.variant == RLTVariant.HYGIENE:
        bereiche = m.anzahl_pruefbereiche_hyg or 1
        if bereiche <= 2:
            return "klein"
        if bereiche <= 6:
            return "standard"
        return "komplex"
    # Garage
    sp = m.stellplaetze or 0
    if sp <= 30:
        return "klein"
    if sp <= 150:
        return "standard"
    return "komplex"
