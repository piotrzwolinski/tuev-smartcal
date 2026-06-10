"""DGUV V3 regression tests — deterministic, no DB/LLM/network.

Covers:
  - Grundpreis + Fläche × Installationskategorie pricing
  - Verteilungen (UV/HV/NSHV) pricing
  - NEA / SV-NSHV Zuschläge
  - Prüftage estimation
  - Berichtstyp selection
  - Merkmale Pydantic validation
  - PricingEngine end-to-end

Test data sources:
  - LPV B04 Kap. 2 constants
  - Sample report MA507-WP: Seniorentreff Regensburg, TT-System, 2017
"""

import pytest
from unittest.mock import patch

from products.dguv_v3.merkmale import (
    DGUVMerkmale,
    GebaeudeNutzungDGUV,
    Netzform,
    Installationskategorie,
)
from products.dguv_v3.pricing_rules import (
    dguv_pruefkosten,
    dguv_estimate_pruef_tage,
    dguv_choose_bericht_typ,
    dguv_zuschlaege,
    dguv_validate_ranges,
    flaechenkosten_degressiv,
    DGUV_GRUNDPREIS_ANLAGE,
    PREIS_PER_10M2,
    DEGRESSION_DGUV,
    ZUSCHLAG_NEA,
    ZUSCHLAG_SV_NSHV,
    PREIS_VERTEILUNG_UV,
    PREIS_VERTEILUNG_HV,
    PREIS_VERTEILUNG_NSHV,
)
from common.pricing_primitives import (
    BERICHT_KLEIN,
    BERICHT_STANDARD,
    BERICHT_KOMPLEX,
)
from engine.pricing_engine import PricingEngine

import products.dguv_v3  # noqa: F401
from engine.gewerk import get_gewerk


def _make(flaeche: float, **kw) -> DGUVMerkmale:
    defaults = dict(
        nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE,
        gesamtflaeche_m2=flaeche,
    )
    defaults.update(kw)
    return DGUVMerkmale(**defaults)


def _mock_find_nearest(lat, lon):
    return {
        "id": "RGB", "name": "Regensburg", "plz": "93051",
        "adresse": "Friedenstraße 6",
        "distance_km": 10.0, "duration_min": 12.0,
        "routing": "test_mock",
    }


# ──────────────────────────────────────────────────────────────
# 1. Prüfkosten — Grundpreis + Fläche
# ──────────────────────────────────────────────────────────────

class TestDGUVPruefkosten:
    def test_basic_kat1_1000m2(self):
        # Degression v2: 1000m² in band 0-2000 → factor 0.80
        # 250 + (1000/10) × 1.00 × 0.80 = 250 + 80 = 330
        m = _make(1000, primary_installationskategorie=Installationskategorie.KAT_1)
        expected = DGUV_GRUNDPREIS_ANLAGE + flaechenkosten_degressiv(1000, PREIS_PER_10M2[Installationskategorie.KAT_1], DEGRESSION_DGUV)
        assert dguv_pruefkosten(m) == expected

    def test_kat2_higher_rate(self):
        # Degression v2: 1000m² in band 0-2000 → factor 0.80
        # 250 + (1000/10) × 3.10 × 0.80 = 250 + 248 = 498
        m = _make(1000, primary_installationskategorie=Installationskategorie.KAT_2)
        expected = DGUV_GRUNDPREIS_ANLAGE + flaechenkosten_degressiv(1000, PREIS_PER_10M2[Installationskategorie.KAT_2], DEGRESSION_DGUV)
        assert dguv_pruefkosten(m) == expected

    def test_all_kategorien_rates(self):
        for kat in Installationskategorie:
            m = _make(500, primary_installationskategorie=kat)
            expected = DGUV_GRUNDPREIS_ANLAGE + flaechenkosten_degressiv(500, PREIS_PER_10M2[kat], DEGRESSION_DGUV)
            assert dguv_pruefkosten(m) == expected

    def test_kat6_most_expensive(self):
        costs = {}
        for kat in Installationskategorie:
            costs[kat] = dguv_pruefkosten(_make(1000, primary_installationskategorie=kat))
        assert costs[Installationskategorie.KAT_6] == max(costs.values())

    def test_degression_reduces_large(self):
        # Degression: effective rate falls with area. 2000→4000 uses factor 0.80,
        # but 4000→5000 uses factor 0.60, so the marginal cost is lower.
        c2k = dguv_pruefkosten(_make(2000, primary_installationskategorie=Installationskategorie.KAT_1))
        c4k = dguv_pruefkosten(_make(4000, primary_installationskategorie=Installationskategorie.KAT_1))
        c6k = dguv_pruefkosten(_make(6000, primary_installationskategorie=Installationskategorie.KAT_1))
        marginal_2_4 = (c4k - c2k) / 2000
        marginal_4_6 = (c6k - c4k) / 2000
        assert marginal_4_6 < marginal_2_4


# ──────────────────────────────────────────────────────────────
# 2. Verteilungen pricing
# ──────────────────────────────────────────────────────────────

class TestVerteilungen:
    def test_uv_only(self):
        m = _make(500, anzahl_verteilungen_uv=5)
        cost_with = dguv_pruefkosten(m)
        cost_without = dguv_pruefkosten(_make(500))
        assert cost_with - cost_without == 5 * PREIS_VERTEILUNG_UV

    def test_hv_only(self):
        m = _make(500, anzahl_verteilungen_hv=3)
        cost_with = dguv_pruefkosten(m)
        cost_without = dguv_pruefkosten(_make(500))
        assert cost_with - cost_without == 3 * PREIS_VERTEILUNG_HV

    def test_nshv_only(self):
        m = _make(500, anzahl_verteilungen_nshv=2)
        cost_with = dguv_pruefkosten(m)
        cost_without = dguv_pruefkosten(_make(500))
        assert cost_with - cost_without == 2 * PREIS_VERTEILUNG_NSHV

    def test_all_verteilungen(self):
        m = _make(500, anzahl_verteilungen_uv=10, anzahl_verteilungen_hv=3, anzahl_verteilungen_nshv=1)
        base = dguv_pruefkosten(_make(500))
        expected = base + 10 * PREIS_VERTEILUNG_UV + 3 * PREIS_VERTEILUNG_HV + 1 * PREIS_VERTEILUNG_NSHV
        assert dguv_pruefkosten(m) == expected

    def test_verteilung_prices_ordering(self):
        assert PREIS_VERTEILUNG_UV < PREIS_VERTEILUNG_HV < PREIS_VERTEILUNG_NSHV


# ──────────────────────────────────────────────────────────────
# 3. NEA / SV-NSHV Zuschläge
# ──────────────────────────────────────────────────────────────

class TestDGUVZuschlaege:
    def test_nea_zuschlag(self):
        m = _make(500, nea_vorhanden=True)
        cost_with = dguv_pruefkosten(m)
        cost_without = dguv_pruefkosten(_make(500))
        assert cost_with - cost_without == ZUSCHLAG_NEA

    def test_sv_nshv_zuschlag(self):
        m = _make(500, sv_nshv_vorhanden=True)
        cost_with = dguv_pruefkosten(m)
        cost_without = dguv_pruefkosten(_make(500))
        assert cost_with - cost_without == ZUSCHLAG_SV_NSHV

    def test_both_zuschlaege(self):
        m = _make(500, nea_vorhanden=True, sv_nshv_vorhanden=True)
        cost_with = dguv_pruefkosten(m)
        cost_without = dguv_pruefkosten(_make(500))
        assert cost_with - cost_without == ZUSCHLAG_NEA + ZUSCHLAG_SV_NSHV

    def test_no_zuschlaege_default(self):
        m = _make(500)
        assert m.nea_vorhanden is False
        assert m.sv_nshv_vorhanden is False


# ──────────────────────────────────────────────────────────────
# 4. Prüftage
# ──────────────────────────────────────────────────────────────

class TestDGUVPruefTage:
    def test_small(self):
        assert dguv_estimate_pruef_tage(_make(300)) == 0.5

    def test_medium(self):
        assert dguv_estimate_pruef_tage(_make(1500)) == 1.0

    def test_large(self):
        assert dguv_estimate_pruef_tage(_make(4000)) == 2.0

    def test_very_large(self):
        assert dguv_estimate_pruef_tage(_make(10000)) == 4.0

    def test_boundary_500(self):
        assert dguv_estimate_pruef_tage(_make(500)) == 0.5

    def test_boundary_2000(self):
        assert dguv_estimate_pruef_tage(_make(2000)) == 1.0

    def test_boundary_5000(self):
        assert dguv_estimate_pruef_tage(_make(5000)) == 2.0

    def test_formula_above_5000(self):
        # max(2.0, 7500/2500) = 3.0
        assert dguv_estimate_pruef_tage(_make(7500)) == 3.0


# ──────────────────────────────────────────────────────────────
# 5. Berichtstyp
# ──────────────────────────────────────────────────────────────

class TestDGUVBerichtstyp:
    def test_klein(self):
        m = _make(300, anzahl_verteilungen_uv=2)
        assert dguv_choose_bericht_typ(m) == "klein"

    def test_standard(self):
        m = _make(3000, anzahl_verteilungen_uv=10)
        assert dguv_choose_bericht_typ(m) == "standard"

    def test_komplex_large_flaeche(self):
        m = _make(6000, anzahl_verteilungen_uv=5)
        assert dguv_choose_bericht_typ(m) == "komplex"

    def test_komplex_many_verteilungen(self):
        m = _make(3000, anzahl_verteilungen_uv=16)
        assert dguv_choose_bericht_typ(m) == "komplex"

    def test_boundary_klein_flaeche(self):
        m = _make(500, anzahl_verteilungen_uv=3)
        assert dguv_choose_bericht_typ(m) == "klein"

    def test_boundary_standard_flaeche(self):
        m = _make(5000, anzahl_verteilungen_uv=15)
        assert dguv_choose_bericht_typ(m) == "standard"


# ──────────────────────────────────────────────────────────────
# 6. Merkmale — Pydantic validation
# ──────────────────────────────────────────────────────────────

class TestDGUVMerkmale:
    def test_minimal_valid(self):
        m = _make(1000)
        assert m.gesamtflaeche_m2 == 1000
        assert m.nutzung == GebaeudeNutzungDGUV.BUEROGEBAEUDE

    def test_all_nutzung_types(self):
        for n in GebaeudeNutzungDGUV:
            m = _make(100, nutzung=n)
            assert m.nutzung == n

    def test_all_netzformen(self):
        for nf in Netzform:
            m = _make(100, netzform=nf)
            assert m.netzform == nf

    def test_all_installationskategorien(self):
        for kat in Installationskategorie:
            m = _make(100, primary_installationskategorie=kat)
            assert m.primary_installationskategorie == kat

    def test_invalid_nutzung_rejected(self):
        with pytest.raises(Exception):
            _make(100, nutzung="flughafen")

    def test_flaeche_min_1(self):
        m = _make(1)
        assert m.gesamtflaeche_m2 == 1

    def test_flaeche_zero_rejected(self):
        with pytest.raises(Exception):
            _make(0)

    def test_negative_flaeche_rejected(self):
        with pytest.raises(Exception):
            _make(-100)

    def test_defaults(self):
        m = _make(100)
        assert m.vereinsmitglied is True
        assert m.eilzuschlag is False
        assert m.erstpruefung is False
        assert m.baurechtlich is False
        assert m.nea_vorhanden is False
        assert m.sv_nshv_vorhanden is False
        assert m.primary_installationskategorie == Installationskategorie.KAT_2

    def test_verteilungen_default_zero(self):
        m = _make(100)
        assert m.anzahl_verteilungen_uv == 0
        assert m.anzahl_verteilungen_hv == 0
        assert m.anzahl_verteilungen_nshv == 0


# ──────────────────────────────────────────────────────────────
# 7. PricingEngine — end-to-end
# ──────────────────────────────────────────────────────────────

class TestDGUVPricingEngine:
    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_simple_buero_1000m2(self, mock_standort):
        gewerk = get_gewerk("dguv_v3")
        engine = PricingEngine()
        m = _make(1000, adresse_lat=49.01, adresse_lon=12.08)

        angebot = engine.calculate(gewerk, m)

        assert angebot.total > 0
        assert angebot.breakdown.pruef == dguv_pruefkosten(m)
        assert angebot.gewerk == gewerk.name
        assert angebot.lpv_referenz == "B04 Kap. 2"

    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_with_verteilungen(self, mock_standort):
        gewerk = get_gewerk("dguv_v3")
        engine = PricingEngine()
        m = _make(
            2000,
            anzahl_verteilungen_uv=8,
            anzahl_verteilungen_hv=2,
            anzahl_verteilungen_nshv=1,
            adresse_lat=49.01,
            adresse_lon=12.08,
        )

        angebot = engine.calculate(gewerk, m)
        assert angebot.breakdown.pruef == dguv_pruefkosten(m)

    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_with_nea_zuschlag(self, mock_standort):
        gewerk = get_gewerk("dguv_v3")
        engine = PricingEngine()
        m = _make(500, nea_vorhanden=True, adresse_lat=49.01, adresse_lon=12.08)

        angebot = engine.calculate(gewerk, m)
        assert angebot.breakdown.pruef == dguv_pruefkosten(m)

    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_no_gewerk_zuschlaege(self, mock_standort):
        gewerk = get_gewerk("dguv_v3")
        engine = PricingEngine()
        m = _make(500, adresse_lat=49.01, adresse_lon=12.08)

        angebot = engine.calculate(gewerk, m)
        assert len(angebot.zuschlaege) == 0

    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_confidence_with_verteilungen(self, mock_standort):
        gewerk = get_gewerk("dguv_v3")
        engine = PricingEngine()
        m = _make(500, anzahl_verteilungen_uv=2, adresse_lat=49.01, adresse_lon=12.08)

        angebot = engine.calculate(gewerk, m)
        assert angebot.confidence == 1.0

    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_confidence_no_verteilungen_penalized(self, mock_standort):
        gewerk = get_gewerk("dguv_v3")
        engine = PricingEngine()
        m = _make(500, adresse_lat=49.01, adresse_lon=12.08)

        angebot = engine.calculate(gewerk, m)
        assert angebot.confidence < 1.0

    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_dict_structure(self, mock_standort):
        gewerk = get_gewerk("dguv_v3")
        engine = PricingEngine()
        m = _make(2000, adresse_lat=49.01, adresse_lon=12.08)

        d = engine.calculate(gewerk, m).to_dict()
        assert "total" in d
        assert set(d["breakdown"].keys()) == {"grund", "pruef", "reise", "bericht", "subtotal"}


# ──────────────────────────────────────────────────────────────
# 8. Golden reference — pinned scenarios
# ──────────────────────────────────────────────────────────────

class TestDGUVGoldenReference:
    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_sample_seniorentreff_regensburg(self, mock_standort):
        """From sample MA507-WP: Seniorentreff Regensburg, TT-System, 2017."""
        gewerk = get_gewerk("dguv_v3")
        engine = PricingEngine()
        m = DGUVMerkmale(
            nutzung=GebaeudeNutzungDGUV.SENIORENTREFF,
            gesamtflaeche_m2=200,
            errichtungszeitraum="2017",
            baujahr=2017,
            netzform=Netzform.TT,
            netzbetreiber="Rewag",
            ueberspannungsschutz_vorhanden=False,
            primary_installationskategorie=Installationskategorie.KAT_1,
            anzahl_verteilungen_uv=1,
            adresse_ort="Regensburg",
            adresse_plz="93051",
            adresse_lat=49.01,
            adresse_lon=12.08,
        )

        angebot = engine.calculate(gewerk, m)

        # Degression v2: 200m² band 0-2000 factor 0.80
        # 250 + (200/10)×1.00×0.80 + 1×25 = 250 + 16 + 25 = 291
        assert angebot.breakdown.pruef == 291.00
        assert angebot.breakdown.bericht == BERICHT_KLEIN  # 200m², 1 UV
        assert angebot.total > 0

    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_industrie_5000m2_kat2(self, mock_standort):
        """Industrial building, 5000m², Kat 2, with NEA."""
        gewerk = get_gewerk("dguv_v3")
        engine = PricingEngine()
        m = DGUVMerkmale(
            nutzung=GebaeudeNutzungDGUV.INDUSTRIE,
            gesamtflaeche_m2=5000,
            primary_installationskategorie=Installationskategorie.KAT_2,
            anzahl_verteilungen_uv=15,
            anzahl_verteilungen_hv=3,
            anzahl_verteilungen_nshv=1,
            nea_vorhanden=True,
            adresse_lat=49.01,
            adresse_lon=12.08,
        )

        angebot = engine.calculate(gewerk, m)

        # Degression v2: 5000m² KAT_2=3.10€/10m²
        # Band 0-2000: 200×3.10×0.80=496, 2000-4000: 200×3.10×0.80=496, 4000-5000: 100×3.10×0.60=186
        # 250 + 1178 + 15×25 + 3×85 + 1×145 + 320(NEA) = 2523
        assert angebot.breakdown.pruef == 2523.00
        # 5000m² + 19 total verteilungen (>15) → komplex
        assert angebot.breakdown.bericht == BERICHT_KOMPLEX

    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_krankenhaus_large(self, mock_standort):
        """Krankenhaus, 20.000m², Kat 5, full security."""
        gewerk = get_gewerk("dguv_v3")
        engine = PricingEngine()
        m = DGUVMerkmale(
            nutzung=GebaeudeNutzungDGUV.KRANKENHAUS,
            gesamtflaeche_m2=20000,
            primary_installationskategorie=Installationskategorie.KAT_5,
            anzahl_verteilungen_uv=30,
            anzahl_verteilungen_hv=5,
            anzahl_verteilungen_nshv=2,
            nea_vorhanden=True,
            sv_nshv_vorhanden=True,
            adresse_lat=49.01,
            adresse_lon=12.08,
        )

        angebot = engine.calculate(gewerk, m)

        # Degression v2: 20000m² KAT_5=5.40€/10m²
        # 0-2k: 200×5.40×0.80=864, 2-4k: 200×5.40×0.80=864, 4-6k: 200×5.40×0.60=648,
        # 6-10k: 400×5.40×0.50=1080, 10-20k: 1000×5.40×0.40=2160 → Σ=5616
        # 250 + 5616 + 30×25 + 5×85 + 2×145 + 320 + 180 = 7831
        assert angebot.breakdown.pruef == 7831.00
        assert angebot.breakdown.bericht == BERICHT_KOMPLEX


# ──────────────────────────────────────────────────────────────
# 9. LPV constants integrity
# ──────────────────────────────────────────────────────────────

class TestDGUVZuschlaege:
    def test_no_zuschlaege_default(self):
        assert dguv_zuschlaege(_make(500)) == []

    def test_nicht_vereinsmitglied(self):
        z = dguv_zuschlaege(_make(500, vereinsmitglied=False))
        assert len(z) == 1
        assert z[0][1] == 0.20

    def test_eilzuschlag(self):
        z = dguv_zuschlaege(_make(500, eilzuschlag=True))
        assert len(z) == 1
        assert z[0][1] == 0.25

    def test_erstpruefung(self):
        z = dguv_zuschlaege(_make(500, erstpruefung=True))
        assert len(z) == 1
        assert z[0][1] == 1.00

    def test_all_stacked(self):
        z = dguv_zuschlaege(_make(500, vereinsmitglied=False, eilzuschlag=True, erstpruefung=True))
        assert len(z) == 3


class TestDGUVValidateRanges:
    def test_typical_buero(self):
        conf, _ = dguv_validate_ranges(_make(1000, anzahl_verteilungen_uv=5))
        assert conf == 1.0

    def test_buero_too_large(self):
        conf, _ = dguv_validate_ranges(_make(10000, anzahl_verteilungen_uv=5))
        assert conf < 1.0

    def test_buero_too_small(self):
        conf, _ = dguv_validate_ranges(_make(50, anzahl_verteilungen_uv=1))
        assert conf < 1.0

    def test_wrong_kat_for_nutzung(self):
        conf, _ = dguv_validate_ranges(_make(
            1000,
            nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE,
            primary_installationskategorie=Installationskategorie.KAT_5,
            anzahl_verteilungen_uv=3,
        ))
        assert conf < 1.0

    def test_no_verteilungen_penalized(self):
        conf, _ = dguv_validate_ranges(_make(500))
        assert conf < 1.0

    def test_industrie_large_ok(self):
        conf, _ = dguv_validate_ranges(_make(
            20000,
            nutzung=GebaeudeNutzungDGUV.INDUSTRIE,
            primary_installationskategorie=Installationskategorie.KAT_3,
            anzahl_verteilungen_uv=10,
        ))
        assert conf == 1.0


class TestDGUVConstants:
    def test_grundpreis(self):
        assert DGUV_GRUNDPREIS_ANLAGE == 250.00

    def test_kat_rates_ordering(self):
        rates = [PREIS_PER_10M2[kat] for kat in sorted(Installationskategorie, key=lambda k: k.value)]
        # Kat 1: 1.00, Kat 2: 3.10, Kat 3: 5.00, Kat 4: 5.40, Kat 5: 5.40, Kat 6: 6.00
        assert rates == [1.00, 3.10, 5.00, 5.40, 5.40, 6.00]

    def test_zuschlag_nea(self):
        assert ZUSCHLAG_NEA == 320.00

    def test_zuschlag_sv_nshv(self):
        assert ZUSCHLAG_SV_NSHV == 180.00

    def test_verteilung_preise(self):
        assert PREIS_VERTEILUNG_UV == 25.00
        assert PREIS_VERTEILUNG_HV == 85.00
        assert PREIS_VERTEILUNG_NSHV == 145.00
