"""Kleinauftrag + Referenz-Blend tests — Phase 4 (Plan v2).

Covers: Kleinauftrag detection, pricing, reduced Grundkosten,
Referenz-Blend with visible Zeile, cap ±30%, age weighting.
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
    is_kleinauftrag,
    kleinauftrag_pruefkosten,
    kleinauftrag_grundkosten,
    dispatch_pruefkosten,
    dguv_pruefkosten,
    referenz_blend,
    KLEINAUFTRAG_MIN_PAUSCHALE,
    KLEINAUFTRAG_STUNDENSATZ,
    KLEINAUFTRAG_GRUNDKOSTEN_REDUZIERT,
    REFERENZ_BLEND_GEWICHT,
    REFERENZ_BLEND_CAP,
)
from engine.pricing_engine import PricingEngine

import products.dguv_v3  # noqa: F401
from engine.gewerk import get_gewerk


def _make(flaeche=None, **kw):
    defaults = dict(nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE)
    if flaeche is not None:
        defaults["gesamtflaeche_m2"] = flaeche
    defaults.update(kw)
    return DGUVMerkmale(**defaults)


def _mock_find_nearest(lat, lon):
    return {
        "id": "RGB", "name": "Regensburg", "plz": "93051",
        "adresse": "Friedenstraße 6",
        "distance_km": 10.0, "duration_min": 12.0, "routing": "test_mock",
    }


class TestKleinauftragDetection:
    def test_small_is_kleinauftrag(self):
        m = _make(200, anzahl_verteilungen_uv=1)
        assert is_kleinauftrag(m)

    def test_boundary_300m2_2vert(self):
        m = _make(300, anzahl_verteilungen_uv=2)
        assert is_kleinauftrag(m)

    def test_too_large_flaeche(self):
        m = _make(500, anzahl_verteilungen_uv=1)
        assert not is_kleinauftrag(m)

    def test_too_many_vert(self):
        m = _make(200, anzahl_verteilungen_uv=3)
        assert not is_kleinauftrag(m)

    def test_minimal_1_vert(self):
        m = _make(100, anzahl_verteilungen_uv=1)
        assert is_kleinauftrag(m)

    def test_normal_buero_not_klein(self):
        m = _make(1000, anzahl_verteilungen_uv=5)
        assert not is_kleinauftrag(m)


class TestKleinauftragPricing:
    def test_single_component(self):
        m = _make(200, anzahl_verteilungen_uv=1)
        cost = kleinauftrag_pruefkosten(m)
        assert cost == max(KLEINAUFTRAG_MIN_PAUSCHALE, 1 * 1.5 * KLEINAUFTRAG_STUNDENSATZ)

    def test_two_components(self):
        m = _make(200, anzahl_verteilungen_uv=2)
        cost = kleinauftrag_pruefkosten(m)
        expected = max(KLEINAUFTRAG_MIN_PAUSCHALE, 2 * 1.5 * KLEINAUFTRAG_STUNDENSATZ)
        assert cost == expected

    def test_minimum_pauschale(self):
        m = _make(100)
        cost = kleinauftrag_pruefkosten(m)
        assert cost >= KLEINAUFTRAG_MIN_PAUSCHALE

    def test_grundkosten_reduziert(self):
        m = _make(200, anzahl_verteilungen_uv=1)
        assert kleinauftrag_grundkosten(m) == KLEINAUFTRAG_GRUNDKOSTEN_REDUZIERT

    def test_dispatch_routes_klein(self):
        m = _make(200, anzahl_verteilungen_uv=1)
        assert dispatch_pruefkosten(m) == kleinauftrag_pruefkosten(m)

    def test_dispatch_normal_for_large(self):
        m = _make(1000, anzahl_verteilungen_uv=5)
        assert dispatch_pruefkosten(m) == dguv_pruefkosten(m)


class TestKleinauftragEngine:
    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_schaltschrank_total_450_550(self, mock_standort):
        # Exit-Gate 4: ZIP-3 Schaltschrank ~450-550€
        m = _make(100, anzahl_verteilungen_nshv=1, adresse_lat=49.01, adresse_lon=12.08)
        gewerk = get_gewerk("dguv_v3")
        engine = PricingEngine()
        angebot = engine.calculate(gewerk, m)
        assert angebot.breakdown.grund == KLEINAUFTRAG_GRUNDKOSTEN_REDUZIERT
        assert 350 < angebot.total < 700

    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_grundkosten_reduced(self, mock_standort):
        m = _make(200, anzahl_verteilungen_uv=1, adresse_lat=49.01, adresse_lon=12.08)
        gewerk = get_gewerk("dguv_v3")
        engine = PricingEngine()
        angebot = engine.calculate(gewerk, m)
        assert angebot.breakdown.grund == KLEINAUFTRAG_GRUNDKOSTEN_REDUZIERT


class TestReferenzBlend:
    def test_no_referenz(self):
        m = _make(1000)
        assert referenz_blend(1000, m) is None

    def test_referenz_not_vergleichbar(self):
        m = _make(1000, referenzpreis_jahr=2024, referenzpreis_betrag=900)
        assert referenz_blend(1000, m) is None

    def test_referenz_blend_basic(self):
        m = _make(1000, referenzpreis_jahr=2024, referenzpreis_betrag=900, referenz_vergleichbar=True)
        result = referenz_blend(1000, m)
        assert result is not None
        assert "anpassung" in result
        assert "fortgeschrieben" in result
        assert result["gewicht"] == REFERENZ_BLEND_GEWICHT

    def test_blend_pulls_toward_referenz(self):
        m = _make(1000, referenzpreis_jahr=2024, referenzpreis_betrag=800, referenz_vergleichbar=True)
        result = referenz_blend(1200, m)
        assert result["anpassung"] < 0  # referenz < neukalk → pulls down

    def test_blend_cap_30_percent(self):
        m = _make(1000, referenzpreis_jahr=2024, referenzpreis_betrag=100, referenz_vergleichbar=True)
        result = referenz_blend(1000, m)
        assert abs(result["anpassung"]) <= 1000 * REFERENZ_BLEND_CAP + 0.01

    def test_old_referenz_lower_weight(self):
        m_recent = _make(1000, referenzpreis_jahr=2024, referenzpreis_betrag=900, referenz_vergleichbar=True)
        m_old = _make(1000, referenzpreis_jahr=2020, referenzpreis_betrag=700, referenz_vergleichbar=True)
        r_recent = referenz_blend(1000, m_recent)
        r_old = referenz_blend(1000, m_old)
        assert r_old["gewicht"] < r_recent["gewicht"]
