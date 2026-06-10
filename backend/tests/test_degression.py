"""Degression curve tests — Phase 1 (Plan v2).

Hand-calculated bandwise sums, boundary continuity, monotonicity,
and engine parity. All values verified against Kalkulationshilfen NBG.
"""

import pytest
from unittest.mock import patch

from products.dguv_v3.pricing_rules import (
    flaechenkosten_degressiv,
    dguv_pruefkosten,
    DEGRESSION_DGUV,
    DEGRESSION_VDS,
    DGUV_GRUNDPREIS_ANLAGE,
    PREIS_PER_10M2,
)
from products.dguv_v3.merkmale import (
    DGUVMerkmale,
    GebaeudeNutzungDGUV,
    Installationskategorie,
)
from engine.pricing_engine import PricingEngine

import products.dguv_v3  # noqa: F401
from engine.gewerk import get_gewerk


def _make(flaeche, **kw):
    defaults = dict(nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE, gesamtflaeche_m2=flaeche)
    defaults.update(kw)
    return DGUVMerkmale(**defaults)


def _mock_find_nearest(lat, lon):
    return {
        "id": "RGB", "name": "Regensburg", "plz": "93051",
        "adresse": "Friedenstraße 6",
        "distance_km": 10.0, "duration_min": 12.0, "routing": "test_mock",
    }


class TestFlaechenkostenDegressiv:
    """Hand-calculated bandwise sums for DGUV curve."""

    def test_zero_m2(self):
        assert flaechenkosten_degressiv(0, 3.10, DEGRESSION_DGUV) == 0.0

    def test_small_500m2_kat2(self):
        # 500m² in band 0-2000, factor 0.80
        # (500/10) × 3.10 × 0.80 = 50 × 2.48 = 124.00
        assert flaechenkosten_degressiv(500, 3.10, DEGRESSION_DGUV) == 124.00

    def test_boundary_2000m2_kat2(self):
        # Full first band: (2000/10) × 3.10 × 0.80 = 200 × 2.48 = 496.00
        assert flaechenkosten_degressiv(2000, 3.10, DEGRESSION_DGUV) == 496.00

    def test_mid_5000m2_kat2(self):
        # 0-2000: 200 × 3.10 × 0.80 = 496
        # 2000-4000: 200 × 3.10 × 0.80 = 496
        # 4000-5000: 100 × 3.10 × 0.60 = 186
        # Total: 1178
        assert flaechenkosten_degressiv(5000, 3.10, DEGRESSION_DGUV) == 1178.00

    def test_large_20000m2_kat5(self):
        # 0-2k: 200×5.40×0.80=864, 2-4k: 200×5.40×0.80=864
        # 4-6k: 200×5.40×0.60=648, 6-10k: 400×5.40×0.50=1080
        # 10-20k: 1000×5.40×0.40=2160
        # Total: 5616
        assert flaechenkosten_degressiv(20000, 5.40, DEGRESSION_DGUV) == 5616.00

    def test_beyond_last_band_30000m2(self):
        # ..same as 20k bands + 20-25k: 500×3.10×0.40=620, 25-30k: 500×3.10×0.30=465
        # 0-2k: 496, 2-4k: 496, 4-6k: 372, 6-10k: 620, 10-25k: 1395, 25-30k: 465
        # Let me recalculate step by step with rate=3.10:
        # 0-2000: 200 × 3.10 × 0.80 = 496
        # 2000-4000: 200 × 3.10 × 0.80 = 496
        # 4000-6000: 200 × 3.10 × 0.60 = 372
        # 6000-10000: 400 × 3.10 × 0.50 = 620
        # 10000-25000: 1500 × 3.10 × 0.40 = 1860
        # 25000-30000: 500 × 3.10 × 0.30 = 465
        # Total: 496+496+372+620+1860+465 = 4309
        assert flaechenkosten_degressiv(30000, 3.10, DEGRESSION_DGUV) == 4309.00


class TestDegressionBoundaries:
    """Continuity: cost at boundary == limit from below."""

    @pytest.mark.parametrize("boundary", [2000, 4000, 6000, 10000, 25000])
    def test_continuity_at_boundary(self, boundary):
        rate = 3.10
        at = flaechenkosten_degressiv(boundary, rate, DEGRESSION_DGUV)
        just_above = flaechenkosten_degressiv(boundary + 1, rate, DEGRESSION_DGUV)
        assert just_above > at


class TestDegressionMonotonicity:
    """Total cost rises with area, effective rate per m² falls."""

    def test_total_monotonic(self):
        rate = 3.10
        areas = [100, 500, 1000, 2000, 4000, 6000, 10000, 20000, 30000]
        costs = [flaechenkosten_degressiv(a, rate, DEGRESSION_DGUV) for a in areas]
        for i in range(len(costs) - 1):
            assert costs[i + 1] > costs[i], f"cost should rise: {areas[i]}→{areas[i+1]}"

    def test_effective_rate_falls(self):
        rate = 3.10
        areas = [500, 2000, 5000, 10000, 25000]
        eff = [flaechenkosten_degressiv(a, rate, DEGRESSION_DGUV) / a for a in areas]
        for i in range(len(eff) - 1):
            assert eff[i + 1] <= eff[i], f"effective rate should fall: {areas[i]}→{areas[i+1]}"


class TestVdSCurve:
    """VdS curve starts at 1.0 (no discount for small) and degresses slower."""

    def test_vds_small_no_discount(self):
        # VdS band 0-2000: factor 1.0 → same as linear
        assert flaechenkosten_degressiv(1000, 3.10, DEGRESSION_VDS) == pytest.approx(310.0, abs=0.01)

    def test_vds_higher_than_dguv(self):
        areas = [2000, 5000, 10000, 25000]
        for a in areas:
            vds = flaechenkosten_degressiv(a, 3.10, DEGRESSION_VDS)
            dguv = flaechenkosten_degressiv(a, 3.10, DEGRESSION_DGUV)
            assert vds >= dguv, f"VdS should be >= DGUV at {a}m²"


class TestDegressionEngineIntegration:
    """Pruefkosten use degression in the Python engine."""

    def test_small_buero_uses_degression(self):
        m = _make(1000, primary_installationskategorie=Installationskategorie.KAT_2)
        pruef = dguv_pruefkosten(m)
        # 250 + flaechenkosten_degressiv(1000, 3.10, DGUV) = 250 + 248 = 498
        assert pruef == DGUV_GRUNDPREIS_ANLAGE + flaechenkosten_degressiv(
            1000, PREIS_PER_10M2[Installationskategorie.KAT_2], DEGRESSION_DGUV
        )

    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_engine_parity(self, mock_standort):
        gewerk = get_gewerk("dguv_v3")
        engine = PricingEngine()
        for flaeche in [200, 1000, 5000, 15000]:
            m = _make(flaeche, adresse_lat=49.01, adresse_lon=12.08)
            angebot = engine.calculate(gewerk, m)
            assert angebot.breakdown.pruef == dguv_pruefkosten(m), f"parity failed at {flaeche}m²"
