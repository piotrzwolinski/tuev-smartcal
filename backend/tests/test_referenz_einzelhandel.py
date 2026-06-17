"""A3 — Einzelhandel-Referenz (REWE-Staffel).

S. Pausch 17.06.2026: REWE-Liste = Referenz für ALLE Einzelhandelsprojekte.
≤2.000 m² = 562 €, 2.001–5.000 m² = 848 €, >5.000 m² → NBG-Fallback.
"""

from products.dguv_v3.merkmale import (
    DGUVMerkmale,
    GebaeudeNutzungDGUV,
    Installationskategorie,
)
from products.dguv_v3.referenzpreise import (
    lookup_referenzpreis,
    _einzelhandel_staffel,
)
from products.dguv_v3.pricing_rules import dispatch_pruefkosten


class TestEinzelhandelStaffel:
    def test_band1_unter_2000(self):
        assert _einzelhandel_staffel(800)["pruefkosten"] == 562.0
        assert _einzelhandel_staffel(2000)["pruefkosten"] == 562.0

    def test_band2_2001_bis_5000(self):
        assert _einzelhandel_staffel(2001)["pruefkosten"] == 848.0
        assert _einzelhandel_staffel(2500)["pruefkosten"] == 848.0
        assert _einzelhandel_staffel(5000)["pruefkosten"] == 848.0

    def test_ueber_5000_kein_listenwert(self):
        assert _einzelhandel_staffel(6000) is None


class TestLookupRouting:
    def test_verkaufsstaette_enum_routet_staffel(self):
        ref = lookup_referenzpreis(GebaeudeNutzungDGUV.VERKAUFSSTAETTE, 2500)
        assert ref is not None
        assert ref["pruefkosten"] == 848.0
        assert ref["referenz_typ"] == "einzelhandel_staffel"

    def test_chat_supermarkt_routet_staffel(self):
        ref = lookup_referenzpreis(
            GebaeudeNutzungDGUV.SONSTIGE, 1500, nutzung_str="Supermarkt"
        )
        assert ref is not None
        assert ref["pruefkosten"] == 562.0

    def test_buero_unveraendert_keine_staffel(self):
        # Regression: Büro darf NICHT in die Einzelhandels-Staffel rutschen
        ref = lookup_referenzpreis(GebaeudeNutzungDGUV.BUEROGEBAEUDE, 2500)
        assert ref is None or ref["referenz_typ"] != "einzelhandel_staffel"


class TestDispatchEndToEnd:
    def test_rewe_2500m2_nahe_848(self):
        # T02/T11-Profil (Pausch: 2001–5000 m² → 848 €), ±Reifegrad
        m = DGUVMerkmale(
            nutzung=GebaeudeNutzungDGUV.VERKAUFSSTAETTE,
            gesamtflaeche_m2=2500,
            primary_installationskategorie=Installationskategorie.KAT_3,
        )
        cost = dispatch_pruefkosten(m)
        # Referenz 848 € × Reifegrad (Standard RG_3 = 1.0)
        assert abs(cost - 848.0) < 50, f"erwartet ~848 €, war {cost}"


class TestRvFlatAllIn:
    """RV-Flat: REWE-Liste ist all-in (Pausch 17.06) — Grund/Reise/Bericht
    werden NICHT zusätzlich gestapelt; Engine-Total ≈ Listenwert."""

    def test_total_etwa_848_all_in(self):
        from unittest.mock import patch
        from engine.pricing_engine import PricingEngine
        from engine.gewerk import get_gewerk
        import products.dguv_v3  # noqa: F401

        def _mock(lat, lon):
            return {"id": "MUC", "name": "München", "plz": "80686",
                    "adresse": "Westendstraße 199", "distance_km": 30.0,
                    "duration_min": 25.0, "routing": "test_mock"}

        m = DGUVMerkmale(
            nutzung=GebaeudeNutzungDGUV.VERKAUFSSTAETTE,
            gesamtflaeche_m2=2500,
            adresse_lat=48.30, adresse_lon=11.62,
        )
        with patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock):
            angebot = PricingEngine().calculate(get_gewerk("dguv_v3"), m)
        assert abs(angebot.total - 848.0) / 848.0 < 0.15, (
            f"RV-Flat all-in: {angebot.total:.0f}€ vs 848€")
        # Grund/Reise/Bericht müssen unterdrückt sein
        assert angebot.breakdown.grund == 0.0
        assert angebot.breakdown.reise == 0.0
        assert angebot.breakdown.bericht == 0.0
