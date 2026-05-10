"""RLT regression tests — deterministic, no DB/LLM/network.

Covers both variants:
  HYG (VDI 6022): Stundensatz × Bereiche + Laborpauschale
  GARAGE (GaStellV): Grundpreis per Stellplatz-range + Ventilatoren + BSK

Test data sources:
  - LPV B05 Kap. 2 constants
  - Sample report MA419-HYG: RLT A1 Altbau, 9.000 m³/h, ISO ePM 2,5 65%
  - Sample report MA419-WPBA: Garage 600 m², 24 Stellplätze, 2 Ventilatoren
"""

import pytest
from unittest.mock import patch

from products.rlt.merkmale import (
    RLTMerkmale,
    RLTVariant,
    GaragentTyp,
    FilterklasseISO,
)
from products.rlt.pricing_rules import (
    rlt_pruefkosten,
    rlt_estimate_pruef_tage,
    rlt_choose_bericht_typ,
    rlt_zuschlaege,
    rlt_validate_ranges,
    HYG_STUNDEN_PRO_BEREICH,
    HYG_LABOR_PAUSCHALE,
    GARAGE_GRUNDPREIS_KLEIN,
    GARAGE_GRUNDPREIS_MITTEL,
    GARAGE_GRUNDPREIS_GROSS,
    RLT_GRUNDPREIS_BIS_10K,
    RLT_GRUNDPREIS_BIS_50K,
    RLT_GRUNDPREIS_GROSS,
    RLT_VENTILATOR_STK,
    RLT_BSK_STK,
)
from common.pricing_primitives import (
    BERICHT_KLEIN,
    BERICHT_STANDARD,
    BERICHT_KOMPLEX,
    stundensatz,
)
from engine.pricing_engine import PricingEngine

import products.rlt  # noqa: F401
from engine.gewerk import get_gewerk


def _hyg(**kw) -> RLTMerkmale:
    defaults = dict(variant=RLTVariant.HYGIENE)
    defaults.update(kw)
    return RLTMerkmale(**defaults)


def _gar(**kw) -> RLTMerkmale:
    defaults = dict(variant=RLTVariant.GARAGE)
    defaults.update(kw)
    return RLTMerkmale(**defaults)


def _mock_find_nearest(lat, lon):
    return {
        "id": "MUC", "name": "München", "plz": "80686",
        "adresse": "Westendstraße 199",
        "distance_km": 15.0, "duration_min": 18.0,
        "routing": "test_mock",
    }


# ──────────────────────────────────────────────────────────────
# 1. HYG Prüfkosten
# ──────────────────────────────────────────────────────────────

class TestHYGPruefkosten:
    def test_default_1_bereich(self):
        m = _hyg()
        cost = rlt_pruefkosten(m)
        expected = 1 * HYG_STUNDEN_PRO_BEREICH * stundensatz("schwierig") + 1 * HYG_LABOR_PAUSCHALE
        assert cost == expected

    def test_3_bereiche(self):
        m = _hyg(anzahl_pruefbereiche_hyg=3)
        cost = rlt_pruefkosten(m)
        expected = 3 * HYG_STUNDEN_PRO_BEREICH * stundensatz("schwierig") + 3 * HYG_LABOR_PAUSCHALE
        assert cost == expected

    def test_scaling_linear(self):
        cost_1 = rlt_pruefkosten(_hyg(anzahl_pruefbereiche_hyg=1))
        cost_5 = rlt_pruefkosten(_hyg(anzahl_pruefbereiche_hyg=5))
        assert cost_5 == cost_1 * 5

    def test_none_bereiche_defaults_to_1(self):
        m = _hyg(anzahl_pruefbereiche_hyg=None)
        cost = rlt_pruefkosten(m)
        expected = 1 * HYG_STUNDEN_PRO_BEREICH * stundensatz("schwierig") + 1 * HYG_LABOR_PAUSCHALE
        assert cost == expected


# ──────────────────────────────────────────────────────────────
# 2. GARAGE Prüfkosten — Stellplatz-based
# ──────────────────────────────────────────────────────────────

class TestGARAGEPruefkosten:
    def test_klein_30_stellplaetze(self):
        m = _gar(stellplaetze=30)
        assert rlt_pruefkosten(m) == GARAGE_GRUNDPREIS_KLEIN

    def test_mittel_31_stellplaetze(self):
        m = _gar(stellplaetze=31)
        assert rlt_pruefkosten(m) == GARAGE_GRUNDPREIS_MITTEL

    def test_mittel_100_stellplaetze(self):
        m = _gar(stellplaetze=100)
        assert rlt_pruefkosten(m) == GARAGE_GRUNDPREIS_MITTEL

    def test_gross_101_stellplaetze(self):
        m = _gar(stellplaetze=101)
        assert rlt_pruefkosten(m) == GARAGE_GRUNDPREIS_GROSS

    def test_with_ventilatoren(self):
        m = _gar(stellplaetze=24, anzahl_ventilatoren=2)
        expected = GARAGE_GRUNDPREIS_KLEIN + 2 * RLT_VENTILATOR_STK
        assert rlt_pruefkosten(m) == expected

    def test_with_bsk(self):
        m = _gar(stellplaetze=50, anzahl_brandschutzklappen=5)
        expected = GARAGE_GRUNDPREIS_MITTEL + 5 * RLT_BSK_STK
        assert rlt_pruefkosten(m) == expected

    def test_with_ventilatoren_and_bsk(self):
        m = _gar(stellplaetze=24, anzahl_ventilatoren=3, anzahl_brandschutzklappen=10)
        expected = GARAGE_GRUNDPREIS_KLEIN + 3 * RLT_VENTILATOR_STK + 10 * RLT_BSK_STK
        assert rlt_pruefkosten(m) == expected


# ──────────────────────────────────────────────────────────────
# 3. GARAGE Prüfkosten — Volumenstrom-based (non-Garage RLT)
# ──────────────────────────────────────────────────────────────

class TestRLTVolumenstromPricing:
    def test_bis_10k(self):
        m = _gar(nennvolumenstrom_m3h=9000)
        assert rlt_pruefkosten(m) == RLT_GRUNDPREIS_BIS_10K

    def test_bis_50k(self):
        m = _gar(nennvolumenstrom_m3h=25000)
        assert rlt_pruefkosten(m) == RLT_GRUNDPREIS_BIS_50K

    def test_gross(self):
        m = _gar(nennvolumenstrom_m3h=80000)
        assert rlt_pruefkosten(m) == RLT_GRUNDPREIS_GROSS

    def test_boundary_10k(self):
        assert rlt_pruefkosten(_gar(nennvolumenstrom_m3h=10000)) == RLT_GRUNDPREIS_BIS_10K

    def test_boundary_50k(self):
        assert rlt_pruefkosten(_gar(nennvolumenstrom_m3h=50000)) == RLT_GRUNDPREIS_BIS_50K

    def test_fallback_no_stellplaetze_no_volumenstrom(self):
        m = _gar()
        assert rlt_pruefkosten(m) == RLT_GRUNDPREIS_BIS_10K

    def test_stellplaetze_takes_priority_over_volumenstrom(self):
        m = _gar(stellplaetze=24, nennvolumenstrom_m3h=80000)
        assert rlt_pruefkosten(m) == GARAGE_GRUNDPREIS_KLEIN  # stellplaetze wins


# ──────────────────────────────────────────────────────────────
# 4. Prüftage
# ──────────────────────────────────────────────────────────────

class TestRLTPruefTage:
    def test_hyg_1_bereich(self):
        assert rlt_estimate_pruef_tage(_hyg(anzahl_pruefbereiche_hyg=1)) == 0.5

    def test_hyg_3_bereiche(self):
        assert abs(rlt_estimate_pruef_tage(_hyg(anzahl_pruefbereiche_hyg=3)) - 1.2) < 1e-9

    def test_hyg_none_defaults(self):
        assert rlt_estimate_pruef_tage(_hyg()) == 0.5

    def test_garage_klein(self):
        assert rlt_estimate_pruef_tage(_gar(stellplaetze=20)) == 0.5

    def test_garage_mittel(self):
        assert rlt_estimate_pruef_tage(_gar(stellplaetze=80)) == 1.0

    def test_garage_gross(self):
        assert rlt_estimate_pruef_tage(_gar(stellplaetze=200)) == 2.0

    def test_garage_no_stellplaetze(self):
        assert rlt_estimate_pruef_tage(_gar()) == 0.5


# ──────────────────────────────────────────────────────────────
# 5. Berichtstyp
# ──────────────────────────────────────────────────────────────

class TestRLTBerichtstyp:
    def test_hyg_klein(self):
        assert rlt_choose_bericht_typ(_hyg(anzahl_pruefbereiche_hyg=1)) == "klein"
        assert rlt_choose_bericht_typ(_hyg(anzahl_pruefbereiche_hyg=2)) == "klein"

    def test_hyg_standard(self):
        assert rlt_choose_bericht_typ(_hyg(anzahl_pruefbereiche_hyg=3)) == "standard"
        assert rlt_choose_bericht_typ(_hyg(anzahl_pruefbereiche_hyg=6)) == "standard"

    def test_hyg_komplex(self):
        assert rlt_choose_bericht_typ(_hyg(anzahl_pruefbereiche_hyg=7)) == "komplex"

    def test_garage_klein(self):
        assert rlt_choose_bericht_typ(_gar(stellplaetze=24)) == "klein"
        assert rlt_choose_bericht_typ(_gar(stellplaetze=30)) == "klein"

    def test_garage_standard(self):
        assert rlt_choose_bericht_typ(_gar(stellplaetze=31)) == "standard"
        assert rlt_choose_bericht_typ(_gar(stellplaetze=150)) == "standard"

    def test_garage_komplex(self):
        assert rlt_choose_bericht_typ(_gar(stellplaetze=151)) == "komplex"


# ──────────────────────────────────────────────────────────────
# 6. Merkmale — Pydantic validation
# ──────────────────────────────────────────────────────────────

class TestRLTMerkmale:
    def test_hyg_minimal(self):
        m = _hyg()
        assert m.variant == RLTVariant.HYGIENE
        assert m.baurechtlich is False

    def test_garage_minimal(self):
        m = _gar()
        assert m.variant == RLTVariant.GARAGE

    def test_all_defaults(self):
        m = _hyg()
        assert m.vereinsmitglied is True
        assert m.eilzuschlag is False
        assert m.erstpruefung is False

    def test_filterklasse_enum(self):
        for fk in FilterklasseISO:
            m = _hyg(filterklasse_aul=fk)
            assert m.filterklasse_aul == fk

    def test_garagentyp_enum(self):
        for gt in GaragentTyp:
            m = _gar(garagentyp=gt)
            assert m.garagentyp == gt

    def test_invalid_variant_rejected(self):
        with pytest.raises(Exception):
            RLTMerkmale(variant="dampf")

    def test_negative_stellplaetze_rejected(self):
        with pytest.raises(Exception):
            _gar(stellplaetze=-1)

    def test_negative_ventilatoren_rejected(self):
        with pytest.raises(Exception):
            _gar(anzahl_ventilatoren=-1)

    def test_adresse_optional(self):
        m = _hyg()
        assert m.adresse_ort is None
        assert m.adresse_lat is None


# ──────────────────────────────────────────────────────────────
# 7. PricingEngine — end-to-end (mocked Reisekosten)
# ──────────────────────────────────────────────────────────────

class TestRLTPricingEngine:
    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_hyg_e2e(self, mock_standort):
        gewerk = get_gewerk("rlt")
        engine = PricingEngine()
        m = _hyg(anzahl_pruefbereiche_hyg=2, adresse_lat=48.14, adresse_lon=11.58)

        angebot = engine.calculate(gewerk, m)

        assert angebot.total > 0
        assert angebot.breakdown.pruef == rlt_pruefkosten(m)
        assert angebot.breakdown.bericht == BERICHT_KLEIN  # 2 bereiche → klein
        assert angebot.gewerk == gewerk.name

    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_garage_e2e(self, mock_standort):
        gewerk = get_gewerk("rlt")
        engine = PricingEngine()
        m = _gar(stellplaetze=24, anzahl_ventilatoren=2, adresse_lat=48.14, adresse_lon=11.58)

        angebot = engine.calculate(gewerk, m)

        expected_pruef = GARAGE_GRUNDPREIS_KLEIN + 2 * RLT_VENTILATOR_STK
        assert angebot.breakdown.pruef == expected_pruef
        assert angebot.breakdown.bericht == BERICHT_KLEIN
        assert angebot.total > 0

    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_no_zuschlaege_by_default(self, mock_standort):
        gewerk = get_gewerk("rlt")
        engine = PricingEngine()
        m = _hyg(adresse_lat=48.14, adresse_lon=11.58)

        angebot = engine.calculate(gewerk, m)
        # RLT currently has no zuschlaege override (uses Gewerk default)
        assert len(angebot.zuschlaege) == 0

    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_confidence_typical(self, mock_standort):
        gewerk = get_gewerk("rlt")
        engine = PricingEngine()
        m = _hyg(anzahl_pruefbereiche_hyg=2, adresse_lat=48.14, adresse_lon=11.58)

        angebot = engine.calculate(gewerk, m)
        assert angebot.confidence == 1.0

    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_angebot_dict_structure(self, mock_standort):
        gewerk = get_gewerk("rlt")
        engine = PricingEngine()
        m = _gar(stellplaetze=50, adresse_lat=48.14, adresse_lon=11.58)

        d = engine.calculate(gewerk, m).to_dict()
        assert set(d["breakdown"].keys()) == {"grund", "pruef", "reise", "bericht", "subtotal"}
        assert d["lpv_referenz"] == "B05 Kap. 2"


# ──────────────────────────────────────────────────────────────
# 8. Golden reference — pinned scenarios from sample reports
# ──────────────────────────────────────────────────────────────

class TestRLTGoldenReference:
    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_sample_hyg_muenchen_9000m3h(self, mock_standort):
        """From sample: RLT A1 Altbau, 9.000 m³/h, VDI 6022, München."""
        gewerk = get_gewerk("rlt")
        engine = PricingEngine()
        m = RLTMerkmale(
            variant=RLTVariant.HYGIENE,
            nennvolumenstrom_m3h=9000,
            filterklasse_aul=FilterklasseISO.EPM2_5_65,
            waermerueckgewinnung=True,
            umluftbetrieb=False,
            anzahl_pruefbereiche_hyg=1,
            adresse_ort="München",
            adresse_plz="80333",
            adresse_lat=48.14,
            adresse_lon=11.58,
            hersteller="Huber & Ranner GmbH",
            baujahr=2012,
        )

        angebot = engine.calculate(gewerk, m)
        assert angebot.breakdown.pruef == 1 * HYG_STUNDEN_PRO_BEREICH * stundensatz("schwierig") + 1 * HYG_LABOR_PAUSCHALE
        assert angebot.total > 0

    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_sample_garage_muenchen_24sp_2vent(self, mock_standort):
        """From sample: Garage 600m², 24 Stellplätze, 2 Ventilatoren, Baurecht."""
        gewerk = get_gewerk("rlt")
        engine = PricingEngine()
        m = RLTMerkmale(
            variant=RLTVariant.GARAGE,
            flaeche_m2=600,
            stellplaetze=24,
            garagentyp=GaragentTyp.MITTEL,
            anzahl_ventilatoren=2,
            baurechtlich=True,
            adresse_ort="München",
            adresse_plz="81241",
            adresse_lat=48.14,
            adresse_lon=11.52,
        )

        angebot = engine.calculate(gewerk, m)
        assert angebot.breakdown.pruef == GARAGE_GRUNDPREIS_KLEIN + 2 * RLT_VENTILATOR_STK
        assert angebot.total > 0


# ──────────────────────────────────────────────────────────────
# 9. LPV constants integrity
# ──────────────────────────────────────────────────────────────

class TestRLTZuschlaege:
    def test_no_zuschlaege_default(self):
        assert rlt_zuschlaege(_hyg()) == []

    def test_nicht_vereinsmitglied(self):
        z = rlt_zuschlaege(_hyg(vereinsmitglied=False))
        assert len(z) == 1
        assert z[0][1] == 0.20

    def test_eilzuschlag(self):
        z = rlt_zuschlaege(_hyg(eilzuschlag=True))
        assert len(z) == 1
        assert z[0][1] == 0.25

    def test_erstpruefung(self):
        z = rlt_zuschlaege(_hyg(erstpruefung=True))
        assert len(z) == 1
        assert z[0][1] == 1.00

    def test_all_stacked(self):
        z = rlt_zuschlaege(_hyg(vereinsmitglied=False, eilzuschlag=True, erstpruefung=True))
        assert len(z) == 3


class TestRLTValidateRanges:
    def test_typical_hyg(self):
        conf, _ = rlt_validate_ranges(_hyg(anzahl_pruefbereiche_hyg=3))
        assert conf == 1.0

    def test_hyg_too_many_bereiche(self):
        conf, _ = rlt_validate_ranges(_hyg(anzahl_pruefbereiche_hyg=10))
        assert conf < 1.0

    def test_hyg_high_volumenstrom(self):
        conf, _ = rlt_validate_ranges(_hyg(nennvolumenstrom_m3h=100000))
        assert conf < 1.0

    def test_typical_garage(self):
        conf, _ = rlt_validate_ranges(_gar(stellplaetze=50))
        assert conf == 1.0

    def test_garage_too_many_stellplaetze(self):
        conf, _ = rlt_validate_ranges(_gar(stellplaetze=500))
        assert conf < 1.0


class TestRLTConstants:
    def test_hyg_stundensatz_level(self):
        assert stundensatz("schwierig") == 208.00

    def test_hyg_labor_pauschale(self):
        assert HYG_LABOR_PAUSCHALE == 180.00

    def test_garage_grundpreise_ordering(self):
        assert GARAGE_GRUNDPREIS_KLEIN < GARAGE_GRUNDPREIS_MITTEL < GARAGE_GRUNDPREIS_GROSS

    def test_rlt_grundpreise_ordering(self):
        assert RLT_GRUNDPREIS_BIS_10K < RLT_GRUNDPREIS_BIS_50K < RLT_GRUNDPREIS_GROSS

    def test_ventilator_preis(self):
        assert RLT_VENTILATOR_STK == 170.00

    def test_bsk_preis(self):
        assert RLT_BSK_STK == 40.00
