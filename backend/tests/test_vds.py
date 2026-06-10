"""VdS 2871 pricing tests — Phase 2 (Plan v2).

Covers: VdS-only route, VdS≠DGUV for same Merkmale, Kombi = VdS×1.5,
dispatch routing, and engine parity.
"""

import pytest
from unittest.mock import patch

from products.dguv_v3.merkmale import (
    DGUVMerkmale,
    GebaeudeNutzungDGUV,
    Installationskategorie,
    Pruefart,
)
from products.dguv_v3.pricing_rules import (
    vds_pruefkosten,
    dguv_pruefkosten,
    dguv_plus_vds_pruefkosten,
    dispatch_pruefkosten,
    flaechenkosten_degressiv,
    DEGRESSION_VDS,
    DEGRESSION_DGUV,
    DGUV_GRUNDPREIS_ANLAGE,
    VDS_GRUNDPREIS_ANLAGE,
    DGUV_VDS_SYNERGIE_ZUSCHLAG,
    PREIS_PER_10M2,
)
from engine.pricing_engine import PricingEngine

import products.dguv_v3  # noqa: F401
from engine.gewerk import get_gewerk


def _make(flaeche, pruefart=Pruefart.DGUV_ORTSFEST, **kw):
    defaults = dict(
        nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE,
        gesamtflaeche_m2=flaeche,
        pruefart=pruefart,
    )
    defaults.update(kw)
    return DGUVMerkmale(**defaults)


def _mock_find_nearest(lat, lon):
    return {
        "id": "RGB", "name": "Regensburg", "plz": "93051",
        "adresse": "Friedenstraße 6",
        "distance_km": 10.0, "duration_min": 12.0, "routing": "test_mock",
    }


class TestVdSPruefkosten:
    def test_vds_not_equal_dguv(self):
        m = _make(5000)
        assert vds_pruefkosten(m) != dguv_pruefkosten(m)

    def test_vds_uses_vds_curve(self):
        m = _make(5000, primary_installationskategorie=Installationskategorie.KAT_2)
        rate = PREIS_PER_10M2[Installationskategorie.KAT_2]
        expected = VDS_GRUNDPREIS_ANLAGE + flaechenkosten_degressiv(5000, rate, DEGRESSION_VDS)
        assert vds_pruefkosten(m) == expected

    def test_vds_small_no_discount(self):
        # VdS curve starts at factor 1.0 → no discount for small buildings
        m = _make(1000, primary_installationskategorie=Installationskategorie.KAT_2)
        rate = PREIS_PER_10M2[Installationskategorie.KAT_2]
        # 250 + (1000/10) × 3.10 × 1.0 = 250 + 310 = 560
        assert vds_pruefkosten(m) == 560.00

    def test_vds_higher_than_dguv_for_large(self):
        for flaeche in [2000, 5000, 10000]:
            m = _make(flaeche)
            assert vds_pruefkosten(m) >= dguv_pruefkosten(m), f"VdS >= DGUV at {flaeche}m²"

    def test_vds_includes_verteilungen(self):
        m_without = _make(1000)
        m_with = _make(1000, anzahl_verteilungen_uv=5)
        diff = vds_pruefkosten(m_with) - vds_pruefkosten(m_without)
        assert diff == 5 * 25.00

    def test_vds_includes_nea(self):
        m_without = _make(1000)
        m_with = _make(1000, nea_vorhanden=True)
        diff = vds_pruefkosten(m_with) - vds_pruefkosten(m_without)
        assert diff == 320.00


class TestKombiPruefkosten:
    def test_kombi_is_vds_times_1_5(self):
        m = _make(5000)
        vds = vds_pruefkosten(m)
        kombi = dguv_plus_vds_pruefkosten(m)
        assert kombi == pytest.approx(vds * 1.5, abs=0.01)

    def test_kombi_returns_float(self):
        m = _make(1000)
        result = dguv_plus_vds_pruefkosten(m)
        assert isinstance(result, float)


class TestDispatchPruefkosten:
    def test_ortsfest_routes_to_dguv(self):
        m = _make(1000, pruefart=Pruefart.DGUV_ORTSFEST)
        assert dispatch_pruefkosten(m) == dguv_pruefkosten(m)

    def test_vds_routes_to_vds(self):
        m = _make(1000, pruefart=Pruefart.VDS)
        assert dispatch_pruefkosten(m) == vds_pruefkosten(m)

    def test_kombi_routes_to_kombi(self):
        m = _make(1000, pruefart=Pruefart.DGUV_PLUS_VDS)
        assert dispatch_pruefkosten(m) == dguv_plus_vds_pruefkosten(m)

    def test_vds_pruefung_bool_maps_to_kombi(self):
        m = _make(1000, vds_pruefung=True)
        assert m.pruefart == Pruefart.DGUV_PLUS_VDS
        assert dispatch_pruefkosten(m) == dguv_plus_vds_pruefkosten(m)

    def test_default_is_ortsfest(self):
        m = _make(1000)
        assert m.pruefart == Pruefart.DGUV_ORTSFEST


class TestVdSEngineParity:
    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_vds_through_engine(self, mock_standort):
        gewerk = get_gewerk("dguv_v3")
        engine = PricingEngine()
        m = _make(3000, pruefart=Pruefart.VDS, adresse_lat=49.01, adresse_lon=12.08)
        angebot = engine.calculate(gewerk, m)
        assert angebot.breakdown.pruef == vds_pruefkosten(m)

    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_kombi_through_engine(self, mock_standort):
        gewerk = get_gewerk("dguv_v3")
        engine = PricingEngine()
        m = _make(3000, pruefart=Pruefart.DGUV_PLUS_VDS, adresse_lat=49.01, adresse_lon=12.08)
        angebot = engine.calculate(gewerk, m)
        assert angebot.breakdown.pruef == dguv_plus_vds_pruefkosten(m)

    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_ortsfest_unchanged(self, mock_standort):
        gewerk = get_gewerk("dguv_v3")
        engine = PricingEngine()
        m = _make(3000, pruefart=Pruefart.DGUV_ORTSFEST, adresse_lat=49.01, adresse_lon=12.08)
        angebot = engine.calculate(gewerk, m)
        assert angebot.breakdown.pruef == dguv_pruefkosten(m)
