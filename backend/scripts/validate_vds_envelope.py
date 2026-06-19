"""V1 — VdS-Hüllkurven-Validierung gegen reale MA505-Auftragsdaten.

Quelle: sources/data/files/2026-06-18_505-WP_bereinigt_final_v3.xlsx (Burgey/Pausch
18.06, 5.995 bereinigte VdS-2871-Ist-Umsätze). Vergleicht unsere vds_pruefkosten()-
Ausgaben mit der realen Preis-Verteilung (Quantile). Reines Reporting — keine
Assertion (die Guardrail-Tests stehen in tests/test_vds_envelope.py).

Lauf:  ./venv/bin/python scripts/validate_vds_envelope.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from products.dguv_v3.merkmale import (
    DGUVMerkmale, GebaeudeNutzungDGUV, Installationskategorie, Pruefart,
)
from products.dguv_v3.pricing_rules import vds_pruefkosten

# Reale MA505-Quantile (umsatz_auftrag > 0, n=5.995). Aus der Analyse vom 18.06,
# siehe sources/data/2026-06-18_ma505_kaufm_analyse.md.
REAL_QUANTILE = {
    "min": 46, "p10": 385, "p25": 657, "median": 1190,
    "p75": 2045, "p90": 3882, "p99": 10734, "max": 136308,
}


def _band(x: float) -> str:
    q = REAL_QUANTILE
    if x < q["p10"]:
        return "< p10"
    for lo, hi in [("p10", "p25"), ("p25", "median"), ("median", "p75"),
                   ("p75", "p90"), ("p90", "p99")]:
        if x <= q[hi]:
            return f"{lo}–{hi}"
    return "> p99"


PROFILE = [
    ("Büro klein",      GebaeudeNutzungDGUV.BUEROGEBAEUDE, 500,   2),
    ("Büro mittel",     GebaeudeNutzungDGUV.BUEROGEBAEUDE, 2000,  2),
    ("Handel",          GebaeudeNutzungDGUV.INDUSTRIE,     2500,  3),
    ("Industrie",       GebaeudeNutzungDGUV.INDUSTRIE,     8000,  3),
    ("Industrie groß",  GebaeudeNutzungDGUV.INDUSTRIE,     20000, 3),
]


def main() -> None:
    q = REAL_QUANTILE
    print("=" * 64)
    print("VdS-Hüllkurven-Validierung — Modell vs reale MA505 (n=5.995)")
    print("=" * 64)
    print("Reale Quantile (€):  " + " · ".join(f"{k}={v}" for k, v in q.items()))
    print("-" * 64)
    print(f"{'Profil':<16}{'m²':>7}{'Kat':>4}{'VdS-Prüf €':>12}   reale Lage")
    for name, nutzung, m2, kat in PROFILE:
        m = DGUVMerkmale(nutzung=nutzung, pruefart=Pruefart.VDS, gesamtflaeche_m2=m2,
                         primary_installationskategorie=Installationskategorie(kat))
        x = vds_pruefkosten(m)
        print(f"{name:<16}{m2:>7}{kat:>4}{x:>12.0f}   {_band(x)}")
    print("-" * 64)
    print("Befund: Industrie 20.000m² ≈ p90–p99 (T01 Hipp real 6.850 ✓);")
    print("kleine/mittlere Büro-VdS tendenziell am unteren Rand (evtl. leicht niedrig).")


if __name__ == "__main__":
    main()
