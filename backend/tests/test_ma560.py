"""MA560 ortsveränderliche Betriebsmittel tests — Phase 3 (Plan v2).

Covers: bm_pruefkosten math, Merkmale without flaeche, ortsv path
(Grundkosten=0, Bericht inklusive), calibration T04/T10, engine integration.
"""

import pytest
from unittest.mock import patch

from products.dguv_v3.merkmale import (
    DGUVMerkmale,
    GebaeudeNutzungDGUV,
    Pruefart,
)
from products.dguv_v3.pricing_rules import (
    bm_pruefkosten,
    dispatch_pruefkosten,
    dguv_estimate_pruef_tage,
    dguv_choose_bericht_typ,
    BM_GRUNDPAUSCHALE,
    BM_SATZ_PRO_BM,
)
from engine.pricing_engine import PricingEngine

import products.dguv_v3  # noqa: F401
from engine.gewerk import get_gewerk


def _make_ortsv(n_bm, **kw):
    defaults = dict(
        nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE,
        pruefart=Pruefart.DGUV_ORTSVERAENDERLICH,
        anzahl_betriebsmittel=n_bm,
    )
    defaults.update(kw)
    return DGUVMerkmale(**defaults)


def _mock_find_nearest(lat, lon):
    return {
        "id": "RGB", "name": "Regensburg", "plz": "93051",
        "adresse": "Friedenstraße 6",
        "distance_km": 10.0, "duration_min": 12.0, "routing": "test_mock",
    }


class TestBMPruefkosten:
    def test_basic_100_bm(self):
        m = _make_ortsv(100)
        # 200 + 100 × 9.50 = 1150
        assert bm_pruefkosten(m) == 1150.00

    def test_basic_1_bm(self):
        m = _make_ortsv(1)
        assert bm_pruefkosten(m) == BM_GRUNDPAUSCHALE + BM_SATZ_PRO_BM

    def test_calibration_t04_114bm(self):
        # T04 ZIP-4: 114 BM → real 1.217€, expected ~1.283€
        m = _make_ortsv(114)
        cost = bm_pruefkosten(m)
        assert cost == 200 + 114 * 9.50  # 1283.00
        assert abs(cost - 1217) / 1217 < 0.10  # within 10% of real

    def test_calibration_t10_545bm(self):
        # T10 PPT-3 Max Planck: 545 BM → real 5.341€, expected ~5377.50
        m = _make_ortsv(545)
        cost = bm_pruefkosten(m)
        assert cost == 200 + 545 * 9.50  # 5377.50
        assert abs(cost - 5341) / 5341 < 0.10  # within 10% of real

    def test_linear_scaling(self):
        c1 = bm_pruefkosten(_make_ortsv(100))
        c2 = bm_pruefkosten(_make_ortsv(200))
        assert c2 - c1 == 100 * BM_SATZ_PRO_BM


class TestOrtsvMerkmale:
    def test_ortsv_valid_without_flaeche(self):
        m = _make_ortsv(100)
        assert m.pruefart == Pruefart.DGUV_ORTSVERAENDERLICH
        assert m.gesamtflaeche_m2 is None

    def test_ortsv_requires_bm(self):
        with pytest.raises(Exception, match="anzahl_betriebsmittel"):
            DGUVMerkmale(
                nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE,
                pruefart=Pruefart.DGUV_ORTSVERAENDERLICH,
            )

    def test_small_bm_kindergarten(self):
        # 20 BM Kindergarten should work, not be rejected
        m = _make_ortsv(20, nutzung=GebaeudeNutzungDGUV.SCHULE)
        assert bm_pruefkosten(m) > 0


class TestOrtsvPath:
    def test_dispatch_routes_to_bm(self):
        m = _make_ortsv(100)
        assert dispatch_pruefkosten(m) == bm_pruefkosten(m)

    def test_pruef_tage_from_bm(self):
        m = _make_ortsv(545)
        tage = dguv_estimate_pruef_tage(m)
        assert tage == pytest.approx(545 / 200, abs=0.1)

    def test_pruef_tage_minimum(self):
        m = _make_ortsv(10)
        assert dguv_estimate_pruef_tage(m) == 0.5

    def test_bericht_inklusive(self):
        m = _make_ortsv(100)
        assert dguv_choose_bericht_typ(m) == "inklusive"


class TestOrtsvEngineIntegration:
    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_grundkosten_zero(self, mock_standort):
        gewerk = get_gewerk("dguv_v3")
        engine = PricingEngine()
        m = _make_ortsv(100, adresse_lat=49.01, adresse_lon=12.08)
        angebot = engine.calculate(gewerk, m)
        assert angebot.breakdown.grund == 0

    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_bericht_zero(self, mock_standort):
        gewerk = get_gewerk("dguv_v3")
        engine = PricingEngine()
        m = _make_ortsv(100, adresse_lat=49.01, adresse_lon=12.08)
        angebot = engine.calculate(gewerk, m)
        assert angebot.breakdown.bericht == 0

    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_total_is_pruef_plus_reise(self, mock_standort):
        gewerk = get_gewerk("dguv_v3")
        engine = PricingEngine()
        m = _make_ortsv(100, adresse_lat=49.01, adresse_lon=12.08)
        angebot = engine.calculate(gewerk, m)
        assert angebot.total == pytest.approx(
            angebot.breakdown.pruef + angebot.breakdown.reise, abs=1
        )

    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_pruef_matches_bm_formula(self, mock_standort):
        gewerk = get_gewerk("dguv_v3")
        engine = PricingEngine()
        m = _make_ortsv(200, adresse_lat=49.01, adresse_lon=12.08)
        angebot = engine.calculate(gewerk, m)
        assert angebot.breakdown.pruef == bm_pruefkosten(m)
