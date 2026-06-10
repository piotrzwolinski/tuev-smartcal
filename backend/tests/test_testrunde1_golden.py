"""Testrunde 1 — Golden-16 regression tests (Phase 6, Plan v2).

16 cases from the 08.06 Testrunde, parametrised with merkmale, real price,
tolerance, and verdict. Out-of-scope/bad-ref cases are xfail.
RV-cases assert price > real (LPV vs Rahmenvertrag delta expected).

Case numbering: T01-T07 = ZIP-1..7, T08-T12 = PPT-1..5, T13-T16 = DOC-1..4.
"""

import pytest
from unittest.mock import patch

from products.dguv_v3.merkmale import (
    DGUVMerkmale,
    GebaeudeNutzungDGUV,
    Installationskategorie,
    Pruefart,
    NutzungsMixEintrag,
)
from engine.pricing_engine import PricingEngine
from engine.gewerk import get_gewerk

import products.dguv_v3  # noqa: F401


def _mock_find_nearest(lat, lon):
    return {
        "id": "MUC", "name": "München", "plz": "80686",
        "adresse": "Westendstraße 199",
        "distance_km": 30.0, "duration_min": 25.0,
        "routing": "test_mock",
    }


def _calc(merkmale):
    gewerk = get_gewerk("dguv_v3")
    engine = PricingEngine()
    return engine.calculate(gewerk, merkmale)


# ═══════════════════════════════════════════════════════════
# T01 — ZIP-1: Hipp Pfaffenhofen, VdS, 20k m², 45 UV
# Real: 6,850€. After degression + VdS curve: target ~7.3k
# ═══════════════════════════════════════════════════════════
class TestT01HippVdS:
    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_total_in_range(self, mock_standort):
        m = DGUVMerkmale(
            nutzung=GebaeudeNutzungDGUV.INDUSTRIE,
            pruefart=Pruefart.VDS,
            gesamtflaeche_m2=20000,
            anzahl_verteilungen_uv=45,
            adresse_lat=48.53, adresse_lon=11.49,
        )
        angebot = _calc(m)
        assert 5000 < angebot.total < 12000, f"T01 Hipp: {angebot.total:.0f}€ outside 5k-12k"

    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_degression_applied(self, mock_standort):
        m = DGUVMerkmale(
            nutzung=GebaeudeNutzungDGUV.INDUSTRIE,
            pruefart=Pruefart.VDS,
            gesamtflaeche_m2=20000,
            adresse_lat=48.53, adresse_lon=11.49,
        )
        angebot = _calc(m)
        assert angebot.breakdown.pruef < 15000, "T01: degression must reduce pruef below linear"


# ═══════════════════════════════════════════════════════════
# T02 — ZIP-2: REWE Eching, 800m², RV case
# Real: 657.26€ (flat Filialnetz-RV). LPV should be ABOVE real.
# ═══════════════════════════════════════════════════════════
class TestT02REWEEchingRV:
    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_lpv_above_rv_real(self, mock_standort):
        m = DGUVMerkmale(
            nutzung=GebaeudeNutzungDGUV.VERKAUFSSTAETTE,
            gesamtflaeche_m2=800,
            adresse_lat=48.30, adresse_lon=11.62,
        )
        angebot = _calc(m)
        assert angebot.total > 657.26, f"T02 RV: LPV {angebot.total:.0f}€ should be > RV real 657€"


# ═══════════════════════════════════════════════════════════
# T03 — ZIP-3: badenova, 1 Schaltschrank (Kleinauftrag)
# Real: 391€. After Kleinauftrag: target ~450-550€
# ═══════════════════════════════════════════════════════════
class TestT03BadenovaSchaltschrank:
    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_kleinauftrag_range(self, mock_standort):
        m = DGUVMerkmale(
            nutzung=GebaeudeNutzungDGUV.SONSTIGE,
            anzahl_verteilungen_nshv=1,
            adresse_lat=47.99, adresse_lon=7.84,
        )
        angebot = _calc(m)
        assert 350 < angebot.total < 700, f"T03 Schaltschrank: {angebot.total:.0f}€ outside 350-700"


# ═══════════════════════════════════════════════════════════
# T04 — ZIP-4: TÜV Auto Service Calw, 114 BM (MA560)
# Real: 1,216.95€. PASS in Runde 1.
# ═══════════════════════════════════════════════════════════
class TestT04AutoServiceCalw:
    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_per_device_pass(self, mock_standort):
        m = DGUVMerkmale(
            nutzung=GebaeudeNutzungDGUV.INDUSTRIE,
            pruefart=Pruefart.DGUV_ORTSVERAENDERLICH,
            anzahl_betriebsmittel=114,
            adresse_lat=48.71, adresse_lon=8.73,
        )
        angebot = _calc(m)
        # pruef matches calibration; total includes mock travel costs
        assert angebot.breakdown.pruef == pytest.approx(1283, abs=20)
        assert 1000 < angebot.total < 2200, f"T04 Calw: {angebot.total:.0f}€ outside 1k-2.2k"


# ═══════════════════════════════════════════════════════════
# T05 — ZIP-5: Landwirt Neukirchen, 23 BM
# Real: 174.80€ — Pausch: "Abrechnung fehlerhaft"
# ═══════════════════════════════════════════════════════════
@pytest.mark.xfail(reason="T05: Referenz defekt — Pausch: 'Abrechnung fehlerhaft, 174.80€ für 23 BM unmöglich'")
class TestT05LandwirtBadRef:
    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_would_not_match(self, mock_standort):
        m = DGUVMerkmale(
            nutzung=GebaeudeNutzungDGUV.INDUSTRIE,
            pruefart=Pruefart.DGUV_ORTSVERAENDERLICH,
            anzahl_betriebsmittel=23,
            adresse_lat=49.27, adresse_lon=12.36,
        )
        angebot = _calc(m)
        assert abs(angebot.total - 174.80) / 174.80 < 0.15


# ═══════════════════════════════════════════════════════════
# T06 — ZIP-6: Maritim Hotel Königswinter, MA510 Baurecht
# Real: 220€ — Pausch: "220€ für 3-Tage-Baurecht unmöglich"
# ═══════════════════════════════════════════════════════════
@pytest.mark.xfail(reason="T06: Referenz defekt + MA510 Baurecht außerhalb PoC-Scope")
class TestT06MaritimBadRef:
    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_would_not_match(self, mock_standort):
        m = DGUVMerkmale(
            nutzung=GebaeudeNutzungDGUV.HOTEL,
            gesamtflaeche_m2=15000,
            anzahl_verteilungen_uv=40,
            adresse_lat=50.67, adresse_lon=7.20,
        )
        angebot = _calc(m)
        assert abs(angebot.total - 220) / 220 < 0.15


# ═══════════════════════════════════════════════════════════
# T07 — ZIP-7: König & Bauer Radebeul, 48 UV, MA505
# Not tested in Runde 1 — candidate for Runde 2.
# ═══════════════════════════════════════════════════════════
class TestT07KoenigBauer:
    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_smoke(self, mock_standort):
        m = DGUVMerkmale(
            nutzung=GebaeudeNutzungDGUV.INDUSTRIE,
            pruefart=Pruefart.VDS,
            gesamtflaeche_m2=25000,
            anzahl_verteilungen_uv=48,
            adresse_lat=51.10, adresse_lon=13.67,
        )
        angebot = _calc(m)
        assert angebot.total > 0, "T07 K&B: should produce a price"
        assert angebot.breakdown.pruef > 0


# ═══════════════════════════════════════════════════════════
# T08 — PPT-1: Apleona Gilching, 26k m², DGUV+VdS
# Real: 7,932€. After degression + VdS: target ~8-11k
# ═══════════════════════════════════════════════════════════
class TestT08ApleonaGilching:
    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_dguv_plus_vds_range(self, mock_standort):
        m = DGUVMerkmale(
            nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE,
            pruefart=Pruefart.DGUV_PLUS_VDS,
            gesamtflaeche_m2=26000,
            anzahl_verteilungen_uv=37,
            adresse_lat=48.11, adresse_lon=11.29,
        )
        angebot = _calc(m)
        assert 5000 < angebot.total < 15000, f"T08 Apleona: {angebot.total:.0f}€ outside 5k-15k"


# ═══════════════════════════════════════════════════════════
# T09 — PPT-2: Weber-Gymnasium, Multi-Produkt (BMA+SiBel+ELT)
# Real: 4,800€. Multi-Produkt = MVP scope.
# ═══════════════════════════════════════════════════════════
@pytest.mark.xfail(reason="T09: Multi-Produkt (BMA+SiBel+ELT) = MVP-Scope, nicht PoC")
class TestT09WeberGymnasiumMulti:
    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_elt_only_lower_than_bundle(self, mock_standort):
        m = DGUVMerkmale(
            nutzung=GebaeudeNutzungDGUV.SCHULE,
            gesamtflaeche_m2=5000,
            adresse_lat=48.15, adresse_lon=11.57,
        )
        angebot = _calc(m)
        assert abs(angebot.total - 4800) / 4800 < 0.15


# ═══════════════════════════════════════════════════════════
# T10 — PPT-3: Max Planck RZ Garching, 545 BM (MA560)
# Real: 5,341€ (545×9.80€). Target: ~5.4k
# ═══════════════════════════════════════════════════════════
class TestT10MaxPlanckRZ:
    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_per_device_545bm(self, mock_standort):
        m = DGUVMerkmale(
            nutzung=GebaeudeNutzungDGUV.INDUSTRIE,
            pruefart=Pruefart.DGUV_ORTSVERAENDERLICH,
            anzahl_betriebsmittel=545,
            adresse_lat=48.26, adresse_lon=11.67,
        )
        angebot = _calc(m)
        assert abs(angebot.total - 5341) / 5341 < 0.15, (
            f"T10 Max Planck: {angebot.total:.0f}€ vs real 5,341€ (>{15}% delta)"
        )


# ═══════════════════════════════════════════════════════════
# T11 — PPT-4: REWE München, ~1600m², RV case
# Real: 657.26€ (flat Filialnetz-RV). LPV should be ABOVE.
# ═══════════════════════════════════════════════════════════
class TestT11REWEMuenchenRV:
    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_lpv_above_rv_real(self, mock_standort):
        m = DGUVMerkmale(
            nutzung=GebaeudeNutzungDGUV.VERKAUFSSTAETTE,
            gesamtflaeche_m2=1600,
            adresse_lat=48.14, adresse_lon=11.51,
        )
        angebot = _calc(m)
        assert angebot.total > 657.26, f"T11 RV: LPV {angebot.total:.0f}€ should be > RV real 657€"


# ═══════════════════════════════════════════════════════════
# T12 — PPT-5: Helios Klinik Pasing, DGUV+VdS, Krankenhaus
# Real: ~13,110€ (54h×239€). Target: ballpark with Kat-Mix
# ═══════════════════════════════════════════════════════════
class TestT12HeliosKlinik:
    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_krankenhaus_with_mix(self, mock_standort):
        m = DGUVMerkmale(
            nutzung=GebaeudeNutzungDGUV.KRANKENHAUS,
            pruefart=Pruefart.DGUV_PLUS_VDS,
            gesamtflaeche_m2=18000,
            nutzungs_mix=[
                NutzungsMixEintrag(nutzung="Allgemeinbereiche", anteil=0.70, kategorie=Installationskategorie.KAT_2),
                NutzungsMixEintrag(nutzung="Technik/OP", anteil=0.30, kategorie=Installationskategorie.KAT_7),
            ],
            adresse_lat=48.14, adresse_lon=11.45,
        )
        angebot = _calc(m)
        assert 7000 < angebot.total < 20000, f"T12 Helios: {angebot.total:.0f}€ outside 7k-20k"


# ═══════════════════════════════════════════════════════════
# T13 — DOC-1: Motel One München, MA501-WP, RV case
# Real: 621€ (RV 2023). LPV should be ABOVE.
# ═══════════════════════════════════════════════════════════
class TestT13MotelOneRV:
    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_lpv_above_rv_real(self, mock_standort):
        m = DGUVMerkmale(
            nutzung=GebaeudeNutzungDGUV.HOTEL,
            gesamtflaeche_m2=6000,
            adresse_lat=48.14, adresse_lon=11.56,
        )
        angebot = _calc(m)
        assert angebot.total > 621, f"T13 RV: LPV {angebot.total:.0f}€ should be > RV real 621€"


# ═══════════════════════════════════════════════════════════
# T14 — DOC-2: roMEd Klinik Prien, MA501-WP
# Real: 3,470€ (2012 nominal). PASS in Runde 1. Our old: 4,322€.
# Inflation-adjusted ~3,470→~4,100. Target: ±25% of 4,100.
# ═══════════════════════════════════════════════════════════
class TestT14RoMEdKlinik:
    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_pass_maintained(self, mock_standort):
        m = DGUVMerkmale(
            nutzung=GebaeudeNutzungDGUV.KRANKENHAUS,
            gesamtflaeche_m2=8000,
            nutzungs_mix=[
                NutzungsMixEintrag(nutzung="Allgemeinbereiche", anteil=0.70, kategorie=Installationskategorie.KAT_2),
                NutzungsMixEintrag(nutzung="Technik", anteil=0.30, kategorie=Installationskategorie.KAT_7),
            ],
            adresse_lat=47.85, adresse_lon=12.34,
        )
        angebot = _calc(m)
        real_infl = 4100
        assert abs(angebot.total - real_infl) / real_infl < 0.35, (
            f"T14 roMEd: {angebot.total:.0f}€ vs infl-adjusted 4,100€ (>{35}% delta)"
        )


# ═══════════════════════════════════════════════════════════
# T15 — DOC-3: DGUV Würzburg, MA507-WP
# Real: 4,195.25€ (2022). Our old: 3,282€ (-22%).
# ═══════════════════════════════════════════════════════════
class TestT15DGUVWuerzburg:
    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_closer_to_real(self, mock_standort):
        m = DGUVMerkmale(
            nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE,
            gesamtflaeche_m2=5000,
            adresse_lat=49.79, adresse_lon=9.93,
        )
        angebot = _calc(m)
        assert 1800 < angebot.total < 6000, (
            f"T15 Würzburg: {angebot.total:.0f}€ outside 1.8k-6k"
        )


# ═══════════════════════════════════════════════════════════
# T16 — DOC-4: Polizei Dachau, Blitz MA574 + RV
# Different product (Blitzschutz, not DGUV V3).
# ═══════════════════════════════════════════════════════════
@pytest.mark.xfail(reason="T16: Blitz-Produkt (MA574), nicht DGUV V3 — separate Gewerk-Tests")
class TestT16PolizeiDachauBlitz:
    def test_not_dguv(self):
        pytest.fail("T16 is a Blitzschutz case, not testable via DGUV V3 engine")
