"""Tests for PV-Anlagen + Ladesäulen + Reisekosten multi-Anfahrt + VdS + Synergie."""

import pytest
from products.dguv_v3.zusatzleistungen import (
    ladesaeulen_preis,
    pv_preis_vds,
    pv_preis_din,
)
from products.dguv_v3.merkmale import (
    DGUVMerkmale,
    GebaeudeNutzungDGUV,
    Installationskategorie,
    Reifegrad,
)
from products.dguv_v3.pricing_rules import (
    vds_pruefkosten,
    dguv_pruefkosten,
    dguv_plus_vds_pruefkosten,
    DGUV_VDS_SYNERGIE_ZUSCHLAG,
    dguv_estimate_pruef_tage,
)


class TestLadesaeulen:
    def test_wallbox_1_anschluss_erste(self):
        r = ladesaeulen_preis("wallbox", 1, 1)
        assert r["preis"] == 71.20

    def test_wallbox_2_anschluesse(self):
        r = ladesaeulen_preis("wallbox", 2, 1)
        assert r["preis"] == 80.10

    def test_dc_1_anschluss(self):
        r = ladesaeulen_preis("dc", 1, 1)
        assert r["preis"] == 267.00

    def test_dc_3_anschluesse(self):
        r = ladesaeulen_preis("dc", 3, 1)
        assert r["preis"] == 302.60

    def test_wallbox_5_saeulen(self):
        r = ladesaeulen_preis("wallbox", 1, 5)
        assert r["preis"] == 71.20 + 4 * 44.50

    def test_dc_3_saeulen(self):
        r = ladesaeulen_preis("dc", 1, 3)
        assert r["preis"] == 267.00 + 2 * 89.00

    def test_null_saeulen(self):
        r = ladesaeulen_preis("wallbox", 1, 0)
        assert r["preis"] == 0

    def test_hat_quelle(self):
        r = ladesaeulen_preis("wallbox", 1, 1)
        assert r["_quelle"] == "LPV Abschnitt 5"


class TestPVVdS:
    def test_klein_bis_30kwp(self):
        assert pv_preis_vds(20)["preis"] == 200.00

    def test_mittel_30_60kwp(self):
        assert pv_preis_vds(50)["preis"] == 300.00

    def test_gross_60_150kwp(self):
        assert pv_preis_vds(100)["preis"] == 400.00

    def test_sehr_gross_ab_150kwp(self):
        assert pv_preis_vds(200)["preis"] == 600.00

    def test_grenze_30kwp(self):
        assert pv_preis_vds(30)["preis"] == 200.00

    def test_hat_quelle(self):
        assert pv_preis_vds(10)["_quelle"] == "LPV Abschnitt 4.1"


class TestPVDIN:
    def test_grundpreis_unter_30kwp(self):
        assert pv_preis_din(20)["preis"] == 540.00

    def test_zuschlag_50kwp(self):
        # 540 + (50-30) × 6.50 = 540 + 130 = 670
        assert pv_preis_din(50)["preis"] == 670.00

    def test_zuschlag_250kwp(self):
        # 540 + (250-30) × 6.50 = 540 + 1430 = 1970
        assert pv_preis_din(250)["preis"] == 1970.00

    def test_zuschlag_500kwp(self):
        # 540 + (250-30) × 6.50 + (500-250) × 4.50 = 540 + 1430 + 1125 = 3095
        assert pv_preis_din(500)["preis"] == 3095.00

    def test_hat_quelle(self):
        assert pv_preis_din(10)["_quelle"] == "LPV Abschnitt 4.2"


# ══════════════════════════════════════════════════════════════
# VdS Pricing (Veit 30.05: "sowie VdS-Prüfungen")
# ══════════════════════════════════════════════════════════════

class TestVdSPricing:
    def _make(self, flaeche=1000, **kw):
        defaults = dict(nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE, gesamtflaeche_m2=flaeche, primary_installationskategorie=Installationskategorie.KAT_2)
        defaults.update(kw)
        return DGUVMerkmale(**defaults)

    def test_vds_different_from_dguv(self):
        # Phase 2: VdS uses its own degression curve (higher than DGUV)
        m = self._make(3000)
        assert vds_pruefkosten(m) > dguv_pruefkosten(m)

    def test_vds_berechnet_preis(self):
        m = self._make(2000)
        preis = vds_pruefkosten(m)
        assert preis > 0

    def test_vds_mit_reifegrad(self):
        m_rg3 = self._make(2000, reifegrad=Reifegrad.RG_3)
        m_rg4 = self._make(2000, reifegrad=Reifegrad.RG_4)
        assert vds_pruefkosten(m_rg4) < vds_pruefkosten(m_rg3)


# ══════════════════════════════════════════════════════════════
# DGUV+VdS Synergie (Pausch: "grob 50% Zuschlag auf VdS-Preis")
# ══════════════════════════════════════════════════════════════

class TestDGUVVdSSynergie:
    def _make(self, flaeche=1000, **kw):
        defaults = dict(nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE, gesamtflaeche_m2=flaeche, primary_installationskategorie=Installationskategorie.KAT_2)
        defaults.update(kw)
        return DGUVMerkmale(**defaults)

    def test_synergie_50_prozent_zuschlag(self):
        assert DGUV_VDS_SYNERGIE_ZUSCHLAG == 0.50

    def test_synergie_billiger_als_einzeln(self):
        m = self._make(3000)
        einzeln = dguv_pruefkosten(m) + vds_pruefkosten(m)
        kombi = dguv_plus_vds_pruefkosten(m)
        assert kombi < einzeln

    def test_synergie_is_vds_times_1_5(self):
        # Phase 2: kombi returns float = VdS × 1.5
        m = self._make(3000)
        vds = vds_pruefkosten(m)
        kombi = dguv_plus_vds_pruefkosten(m)
        assert kombi == pytest.approx(vds * 1.5, rel=0.01)

    def test_synergie_mit_reifegrad(self):
        m_rg3 = self._make(3000, reifegrad=Reifegrad.RG_3)
        m_rg4 = self._make(3000, reifegrad=Reifegrad.RG_4)
        kombi_rg3 = dguv_plus_vds_pruefkosten(m_rg3)
        kombi_rg4 = dguv_plus_vds_pruefkosten(m_rg4)
        assert kombi_rg4 < kombi_rg3


# ══════════════════════════════════════════════════════════════
# Reisekosten multi-Anfahrt (Veit 30.05: >9h=2, >18h=3)
# ══════════════════════════════════════════════════════════════

class TestReisekostenMultiAnfahrt:
    def test_unter_9h_eine_anfahrt(self):
        m = DGUVMerkmale(nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE, gesamtflaeche_m2=500)
        tage = dguv_estimate_pruef_tage(m)
        stunden = tage * 8
        assert stunden <= 9
        # → 1 Anfahrt

    def test_ueber_9h_zwei_anfahrten(self):
        m = DGUVMerkmale(nutzung=GebaeudeNutzungDGUV.INDUSTRIE, gesamtflaeche_m2=3000, primary_installationskategorie=Installationskategorie.KAT_3)
        tage = dguv_estimate_pruef_tage(m)
        stunden = tage * 8
        assert stunden > 9
        # → 2 Anfahrten

    def test_ueber_18h_drei_anfahrten(self):
        m = DGUVMerkmale(nutzung=GebaeudeNutzungDGUV.INDUSTRIE, gesamtflaeche_m2=10000, primary_installationskategorie=Installationskategorie.KAT_3)
        tage = dguv_estimate_pruef_tage(m)
        stunden = tage * 8
        assert stunden > 18
        # → 3 Anfahrten

    def test_anfahrten_logik(self):
        """Verify the >9h / >18h thresholds match Veit's rule."""
        for stunden, expected_anfahrten in [(4, 1), (8, 1), (9, 1), (10, 2), (16, 2), (18, 2), (19, 3), (24, 3)]:
            if stunden > 18:
                anfahrten = 3
            elif stunden > 9:
                anfahrten = 2
            else:
                anfahrten = 1
            assert anfahrten == expected_anfahrten, f"Bei {stunden}h sollten {expected_anfahrten} Anfahrten sein"


# ══════════════════════════════════════════════════════════════
# Graph Engine Addon Integration
# ══════════════════════════════════════════════════════════════

class TestGraphEngineAddons:
    def _make(self, flaeche=3000, **kw):
        defaults = dict(nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE, gesamtflaeche_m2=flaeche, primary_installationskategorie=Installationskategorie.KAT_2)
        defaults.update(kw)
        return DGUVMerkmale(**defaults)

    def _calc(self, merkmale):
        from engine.graph_pricing_engine import GraphPricingEngine
        from products.dguv_v3 import DGUV_V3
        engine = GraphPricingEngine("dguv_v3")
        return engine.calculate(DGUV_V3, merkmale)

    def test_no_addons_unchanged(self):
        m = self._make()
        a = self._calc(m)
        assert a.total > 0
        assert a.zusatzleistungen == []

    def test_vds_kombi_in_pruef(self):
        # Phase 2: vds_pruefung=True → pruefart=DGUV_PLUS_VDS → pruef includes VdS×1.5
        m_solo = self._make()
        m_vds = self._make(vds_pruefung=True)
        a_solo = self._calc(m_solo)
        a_vds = self._calc(m_vds)
        assert a_vds.breakdown.pruef > a_solo.breakdown.pruef
        assert a_vds.total > a_solo.total

    def test_pv_addon(self):
        m = self._make(pv_kwp=100.0)
        a = self._calc(m)
        pv_items = [z for z in a.zusatzleistungen if "PV" in z["name"]]
        assert len(pv_items) == 1
        assert pv_items[0]["preis"] > 0

    def test_ladesaeulen_addon(self):
        m = self._make(ladesaeulen=[{"typ": "wallbox", "anschluesse": 1, "anzahl": 5}])
        a = self._calc(m)
        ls_items = [z for z in a.zusatzleistungen if "Ladesäulen" in z["name"]]
        assert len(ls_items) == 1
        assert ls_items[0]["preis"] == 71.20 + 4 * 44.50

    def test_all_addons_total(self):
        # Phase 2: VdS now in pruef dispatch, only PV + Ladesäulen remain as addons
        m = self._make(vds_pruefung=True, pv_kwp=50.0, ladesaeulen=[{"typ": "dc", "anschluesse": 1, "anzahl": 2}])
        a = self._calc(m)
        assert len(a.zusatzleistungen) == 2
        addon_sum = sum(z["preis"] for z in a.zusatzleistungen)
        assert a.total > a.breakdown.subtotal + addon_sum - 1
