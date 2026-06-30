"""Impact-Analyse: Berichterstellung-Regel S. Pausch (Mail 17.06 10:34) vs. aktuell.

Stefan-Regel: DGUV/VdS/Blitz → IMMER kleiner Bericht 119€.
  550€ (komplex) nur bei Baurecht / Elektrothermographie / Kunde-Sonderanforderung.
  RV-Flat / Kleinauftrag / ortsveränderlich → bleibt inklusive (Pauschale).

Läuft die Engine 2× (aktuelle Regel vs. monkeypatched Stefan-Regel) — KEINE Quelländerung.
Nur Analyse. Lauf: ./venv/bin/python scripts/impact_berichterstellung.py
"""
from unittest.mock import patch

import products.dguv_v3  # noqa: F401
from products.dguv_v3.merkmale import (
    DGUVMerkmale, GebaeudeNutzungDGUV, Installationskategorie, Pruefart, NutzungsMixEintrag,
)
from products.dguv_v3.pricing_rules import is_kleinauftrag, is_einzelhandel_rv_flat
from engine.pricing_engine import PricingEngine
from engine.gewerk import get_gewerk


def _mock_find_nearest(lat, lon):
    return {"id": "MUC", "name": "München", "plz": "80686", "adresse": "Westendstraße 199",
            "distance_km": 30.0, "duration_min": 25.0, "routing": "test_mock"}


def stefan_choose_bericht_typ(m):
    """Stefan-Regel."""
    if getattr(m, "pruefart", None) == Pruefart.DGUV_ORTSVERAENDERLICH:
        return "inklusive"
    if is_kleinauftrag(m):
        return "inklusive"
    if is_einzelhandel_rv_flat(m):
        return "inklusive"
    if getattr(m, "grundlage_baurecht", False) or getattr(m, "elektrothermographie", False):
        return "komplex"   # 550
    return "klein"         # 119 flat


def calc(m):
    return PricingEngine().calculate(get_gewerk("dguv_v3"), m)


# 16 Golden-Fälle (Merkmale 1:1 aus tests/test_testrunde1_golden.py) + reale Referenz
M = DGUVMerkmale
CASES = [
    ("T01 Hipp VdS",        M(nutzung=GebaeudeNutzungDGUV.INDUSTRIE, pruefart=Pruefart.VDS, gesamtflaeche_m2=20000, anzahl_verteilungen_uv=45, adresse_lat=48.53, adresse_lon=11.49), 6850, ""),
    ("T02 REWE Eching RV",  M(nutzung=GebaeudeNutzungDGUV.VERKAUFSSTAETTE, gesamtflaeche_m2=2500, adresse_lat=48.30, adresse_lon=11.62), 848, "RV-flat"),
    ("T03 Badenova klein",  M(nutzung=GebaeudeNutzungDGUV.SONSTIGE, anzahl_verteilungen_nshv=1, adresse_lat=47.99, adresse_lon=7.84), 391, "Kleinauftrag"),
    ("T04 AutoService 560", M(nutzung=GebaeudeNutzungDGUV.INDUSTRIE, pruefart=Pruefart.DGUV_ORTSVERAENDERLICH, anzahl_betriebsmittel=114, adresse_lat=48.71, adresse_lon=8.73), 1217, "MA560"),
    ("T07 König&Bauer VdS", M(nutzung=GebaeudeNutzungDGUV.INDUSTRIE, pruefart=Pruefart.VDS, gesamtflaeche_m2=25000, anzahl_verteilungen_uv=48, adresse_lat=51.10, adresse_lon=13.67), None, "smoke"),
    ("T08 Apleona D+VdS",   M(nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE, pruefart=Pruefart.DGUV_PLUS_VDS, gesamtflaeche_m2=26000, anzahl_verteilungen_uv=37, adresse_lat=48.11, adresse_lon=11.29), 7932, ""),
    ("T10 MaxPlanck 560",   M(nutzung=GebaeudeNutzungDGUV.INDUSTRIE, pruefart=Pruefart.DGUV_ORTSVERAENDERLICH, anzahl_betriebsmittel=545, adresse_lat=48.26, adresse_lon=11.67), 5341, "MA560"),
    ("T11 REWE Muc RV",     M(nutzung=GebaeudeNutzungDGUV.VERKAUFSSTAETTE, gesamtflaeche_m2=2500, adresse_lat=48.14, adresse_lon=11.51), 848, "RV-flat"),
    ("T12 Helios D+VdS",    M(nutzung=GebaeudeNutzungDGUV.KRANKENHAUS, pruefart=Pruefart.DGUV_PLUS_VDS, gesamtflaeche_m2=18000, nutzungs_mix=[NutzungsMixEintrag(nutzung="Allg", anteil=0.70, kategorie=Installationskategorie.KAT_2), NutzungsMixEintrag(nutzung="OP", anteil=0.30, kategorie=Installationskategorie.KAT_7)], adresse_lat=48.14, adresse_lon=11.45), 13110, ""),
    ("T13 MotelOne RV",     M(nutzung=GebaeudeNutzungDGUV.HOTEL, gesamtflaeche_m2=6000, adresse_lat=48.14, adresse_lon=11.56), 621, "RV (LPV>real)"),
    ("T14 roMEd Klinik",    M(nutzung=GebaeudeNutzungDGUV.KRANKENHAUS, gesamtflaeche_m2=8000, nutzungs_mix=[NutzungsMixEintrag(nutzung="Allg", anteil=0.70, kategorie=Installationskategorie.KAT_2), NutzungsMixEintrag(nutzung="Tech", anteil=0.30, kategorie=Installationskategorie.KAT_7)], adresse_lat=47.85, adresse_lon=12.34), 4100, "infl-adj"),
    ("T15 DGUV Würzburg",   M(nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE, gesamtflaeche_m2=5000, adresse_lat=49.79, adresse_lon=9.93), 4195, ""),
]


def run():
    rows = []
    with patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest):
        for name, m, real, note in CASES:
            a_old = calc(m)
            b_old = a_old.breakdown.bericht
            t_old = a_old.total
            with patch("products.dguv_v3.dguv_choose_bericht_typ", side_effect=stefan_choose_bericht_typ):
                a_new = calc(m)
            b_new = a_new.breakdown.bericht
            t_new = a_new.total
            rows.append((name, real, note, b_old, b_new, t_old, t_new))

    print(f"\n{'Fall':22}{'real':>7}{'Ber_alt':>9}{'Ber_neu':>9}{'Tot_alt':>9}{'Tot_neu':>9}{'ΔTot':>8}  {'dev_alt':>8}{'dev_neu':>8}")
    print("─" * 100)
    for name, real, note, b_old, b_new, t_old, t_new in rows:
        d = t_new - t_old
        if real:
            da = f"{(t_old-real)/real*100:+.0f}%"
            dn = f"{(t_new-real)/real*100:+.0f}%"
        else:
            da = dn = "  —"
        flag = "" if abs(d) < 0.5 else ("▲" if d > 0 else "▼")
        print(f"{name:22}{(str(real) if real else '—'):>7}{b_old:>9.0f}{b_new:>9.0f}{t_old:>9.0f}{t_new:>9.0f}{d:>+8.0f}{flag} {da:>8}{dn:>8}  {note}")
    print("─" * 100)
    chg = [r for r in rows if abs((r[6]-r[5])) >= 0.5]
    print(f"\nFälle mit Total-Änderung: {len(chg)}/{len(rows)}")
    for name, real, note, b_old, b_new, t_old, t_new in chg:
        print(f"  {name:22} Bericht {b_old:.0f}→{b_new:.0f}€  →  Total {t_old:.0f}→{t_new:.0f}€  ({t_new-t_old:+.0f}€)")


if __name__ == "__main__":
    run()
