"""V1 — VdS-Curve-Regressionsguard gegen reale MA505-Verteilung.

Bakt die reale VdS-Preis-Hüllkurve (MA505-Export 18.06, n=5.995) als
Guardrail ein: representative VdS-Anlagen müssen in plausiblen Quantil-Bändern
landen. Fängt grobe Fehlkalibrierung der VdS-Kurve (z.B. 10× zu hoch/niedrig).
Quelle: sources/data/2026-06-18_ma505_kaufm_analyse.md.
"""
from products.dguv_v3.merkmale import (
    DGUVMerkmale, GebaeudeNutzungDGUV, Installationskategorie, Pruefart,
)
from products.dguv_v3.pricing_rules import vds_pruefkosten

# Reale Quantile (umsatz_auftrag > 0)
REAL_MIN, REAL_P10, REAL_P25, REAL_MEDIAN = 46, 385, 657, 1190
REAL_P75, REAL_P90, REAL_P99, REAL_MAX = 2045, 3882, 10734, 136308


def _vds(nutzung, m2, kat):
    m = DGUVMerkmale(nutzung=nutzung, pruefart=Pruefart.VDS, gesamtflaeche_m2=m2,
                     primary_installationskategorie=Installationskategorie(kat))
    return vds_pruefkosten(m)


class TestVdSImEnvelope:
    def test_kleine_anlage_in_unterer_haelfte(self):
        # Büro 500 m² = kleine Anlage → zwischen Realminimum und Median
        x = _vds(GebaeudeNutzungDGUV.BUEROGEBAEUDE, 500, 2)
        assert REAL_MIN <= x <= REAL_MEDIAN, f"{x}€ außerhalb [min, median]"

    def test_grosse_industrie_oberes_band(self):
        # Industrie 20.000 m² Kat3 → echte Schwerindustrie, p75..p99
        x = _vds(GebaeudeNutzungDGUV.INDUSTRIE, 20000, 3)
        assert REAL_P75 <= x <= REAL_P99, f"{x}€ außerhalb [p75, p99]"

    def test_kein_profil_ausserhalb_realer_spanne(self):
        # Kein realistisches Einzel-Anlagen-Profil darf das reale Maximum sprengen
        for m2 in (200, 500, 1000, 2500, 5000, 8000, 15000, 25000):
            for kat in (2, 3):
                x = _vds(GebaeudeNutzungDGUV.INDUSTRIE, m2, kat)
                assert REAL_MIN <= x <= REAL_MAX, f"{m2}m² Kat{kat}: {x}€ außerhalb realer Spanne"

    def test_curve_monoton_in_flaeche(self):
        prev = -1
        for m2 in (500, 2000, 5000, 10000, 20000):
            x = _vds(GebaeudeNutzungDGUV.INDUSTRIE, m2, 3)
            assert x > prev, f"VdS nicht monoton bei {m2}m² ({x} <= {prev})"
            prev = x

    def test_hipp_anker_p90_p99(self):
        # Bekannter realer Anker: T01 Hipp (Industrie 20.000 m²) = 6.850 €
        x = _vds(GebaeudeNutzungDGUV.INDUSTRIE, 20000, 3)
        assert REAL_P90 <= x <= REAL_P99
