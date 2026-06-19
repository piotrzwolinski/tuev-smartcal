"""V3 — Inflation 2024/2025 gegen reale MA505-Preisdrift verankert.

Burgey 18.06: Standard-VdS-Listenpreis 641,23€ (2024) → 657,26€ (2025/26) = +2,5%,
danach ~flat. Ersetzt Veits Schätzung (8,3%/5,5%). Ältere Jahre (Veit) unverändert.
"""
from products.dguv_v3.pricing_rules import PREISSTEIGERUNG, _g_steigerung


class TestInflationMA505Anker:
    def test_2024_drift_entspricht_641_auf_657(self):
        # 641,23 × (1 + steigerung_2024) ≈ 657,26 (reale +2,5%)
        fortgeschrieben = 641.23 * (1 + PREISSTEIGERUNG[2024])
        assert abs(fortgeschrieben - 657.26) < 12.0, fortgeschrieben

    def test_2025_nahezu_flat(self):
        assert PREISSTEIGERUNG[2025] <= 0.02

    def test_juengste_drift_gesenkt_vs_veit(self):
        # War 0.083 / 0.055 (Veit) — jetzt niedriger (MA505)
        assert PREISSTEIGERUNG[2024] < 0.083
        assert PREISSTEIGERUNG[2025] < 0.055

    def test_veit_altjahre_unveraendert(self):
        # Nur 2024/2025 angefasst — ältere Jahre (Veit-Schätzung) bleiben
        assert PREISSTEIGERUNG[2012] == 0.480  # T14 roMEd-Referenzjahr
        assert PREISSTEIGERUNG[2020] == 0.282
        assert PREISSTEIGERUNG[2023] == 0.148

    def test_monoton_fallend_richtung_2026(self):
        jahre = sorted(PREISSTEIGERUNG)
        werte = [PREISSTEIGERUNG[j] for j in jahre]
        assert werte == sorted(werte, reverse=True)
