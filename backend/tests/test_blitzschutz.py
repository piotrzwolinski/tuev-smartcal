"""Blitzschutz regression tests — deterministic, no DB/LLM/network.

Covers:
  1. pricing_rules: pruefkosten Staffeln, pruef_tage, bericht_typ
  2. zuschlaege: Vereinsmitglied, Eilzuschlag, Erstprüfung
  3. validate_ranges: confidence scoring per Nutzung + Schutzklasse
  4. merkmale: Pydantic validation (enum, field limits, breite/laenge swap)
  5. PricingEngine: end-to-end Angebot (mocked Reisekosten)
  6. golden reference: "Bürogebäude Nürnberg 12 TS" known-good result
"""

import pytest
from unittest.mock import patch

from products.blitzschutz.merkmale import (
    BlitzschutzMerkmale,
    Schutzklasse,
    GebaeudeNutzung,
    Bauart,
    ArtPruefung,
)
from products.blitzschutz.pricing_rules import (
    blitz_pruefkosten,
    blitz_estimate_pruef_tage,
    blitz_choose_bericht_typ,
    blitz_zuschlaege,
    blitz_validate_ranges,
    PREIS_PRO_MESSSTELLE,
    STAFFEL,
)
from engine.pricing_engine import PricingEngine
from common.pricing_primitives import (
    GRUNDKOSTEN_AUFTRAGSVERWALTUNG,
    GRUNDKOSTEN_ORDNUNGSPRUEFUNG,
    PRUEFMITTEL_PRO_TAG_SV,
    BERICHT_KLEIN,
    BERICHT_STANDARD,
    BERICHT_KOMPLEX,
    ZUSCHLAG_NICHT_VEREINSMITGLIED,
    ZUSCHLAG_EILZUSCHLAG,
    ZUSCHLAG_ERSTPRUEFUNG,
)

# Ensure Blitzschutz gewerk is registered
import products.blitzschutz  # noqa: F401
from engine.gewerk import get_gewerk


def _make(n: int, **kw) -> BlitzschutzMerkmale:
    defaults = dict(nutzung=GebaeudeNutzung.BUERO, anzahl_ableitungen=n)
    defaults.update(kw)
    return BlitzschutzMerkmale(**defaults)


# ──────────────────────────────────────────────────────────────
# 1. Prüfkosten — Staffel logic
# ──────────────────────────────────────────────────────────────

class TestPruefkosten:
    def test_under_threshold(self):
        assert blitz_pruefkosten(_make(1)) == 33.00
        assert blitz_pruefkosten(_make(10)) == 330.00

    def test_at_threshold_boundary(self):
        assert blitz_pruefkosten(_make(10)) == 10 * 33.00
        cost_11 = blitz_pruefkosten(_make(11))
        assert cost_11 == 10 * 33 + 1 * 30.00

    def test_staffel_2(self):
        # 20 MS: 10×33 + 10×30
        assert blitz_pruefkosten(_make(20)) == 330 + 300

    def test_staffel_3(self):
        # 40 MS: 10×33 + 10×30 + 20×28
        assert blitz_pruefkosten(_make(40)) == 330 + 300 + 560

    def test_staffel_4(self):
        # 100 MS: 10×33 + 10×30 + 20×28 + 60×26
        assert blitz_pruefkosten(_make(100)) == 330 + 300 + 560 + 1560

    def test_staffel_5_large(self):
        # 200 MS: 10×33 + 10×30 + 20×28 + 60×26 + 100×24
        assert blitz_pruefkosten(_make(200)) == 330 + 300 + 560 + 1560 + 2400

    def test_single_messstelle(self):
        assert blitz_pruefkosten(_make(1)) == 33.00

    def test_monotonically_increasing(self):
        prev = 0
        for n in [1, 5, 10, 15, 30, 50, 100, 200, 500]:
            cost = blitz_pruefkosten(_make(n))
            assert cost > prev, f"Cost should increase: n={n}, cost={cost}, prev={prev}"
            prev = cost


# ──────────────────────────────────────────────────────────────
# 2. Prüftage estimation
# ──────────────────────────────────────────────────────────────

class TestPruefTage:
    def test_small(self):
        assert blitz_estimate_pruef_tage(_make(5)) == 0.5

    def test_medium(self):
        assert blitz_estimate_pruef_tage(_make(20)) == 1.0

    def test_large(self):
        assert blitz_estimate_pruef_tage(_make(50)) == 2.0

    def test_very_large(self):
        assert blitz_estimate_pruef_tage(_make(80)) == 3.0

    def test_formula_kicks_in(self):
        # >100: max(3.0, n/40)
        assert blitz_estimate_pruef_tage(_make(200)) == 5.0
        assert blitz_estimate_pruef_tage(_make(400)) == 10.0

    def test_boundary_10(self):
        assert blitz_estimate_pruef_tage(_make(10)) == 0.5

    def test_boundary_30(self):
        assert blitz_estimate_pruef_tage(_make(30)) == 1.0

    def test_boundary_60(self):
        assert blitz_estimate_pruef_tage(_make(60)) == 2.0

    def test_boundary_100(self):
        assert blitz_estimate_pruef_tage(_make(100)) == 3.0


# ──────────────────────────────────────────────────────────────
# 3. Berichtstyp selection
# ──────────────────────────────────────────────────────────────

class TestBerichtstyp:
    def test_klein(self):
        assert blitz_choose_bericht_typ(_make(1)) == "klein"
        assert blitz_choose_bericht_typ(_make(10)) == "klein"

    def test_standard(self):
        assert blitz_choose_bericht_typ(_make(11)) == "standard"
        assert blitz_choose_bericht_typ(_make(40)) == "standard"

    def test_komplex(self):
        assert blitz_choose_bericht_typ(_make(41)) == "komplex"
        assert blitz_choose_bericht_typ(_make(200)) == "komplex"


# ──────────────────────────────────────────────────────────────
# 4. Zuschläge
# ──────────────────────────────────────────────────────────────

class TestZuschlaege:
    def test_no_zuschlaege_default(self):
        m = _make(10)
        assert blitz_zuschlaege(m) == []

    def test_nicht_vereinsmitglied(self):
        m = _make(10, vereinsmitglied=False)
        z = blitz_zuschlaege(m)
        assert len(z) == 1
        assert z[0][1] == ZUSCHLAG_NICHT_VEREINSMITGLIED

    def test_eilzuschlag(self):
        m = _make(10, eilzuschlag=True)
        z = blitz_zuschlaege(m)
        assert len(z) == 1
        assert z[0][1] == ZUSCHLAG_EILZUSCHLAG

    def test_erstpruefung(self):
        m = _make(10, erstpruefung=True)
        z = blitz_zuschlaege(m)
        assert len(z) == 1
        assert z[0][1] == ZUSCHLAG_ERSTPRUEFUNG

    def test_all_zuschlaege_stacked(self):
        m = _make(10, vereinsmitglied=False, eilzuschlag=True, erstpruefung=True)
        z = blitz_zuschlaege(m)
        assert len(z) == 3
        percents = {p for _, p in z}
        assert percents == {0.20, 0.25, 1.00}


# ──────────────────────────────────────────────────────────────
# 5. Confidence / Validate ranges
# ──────────────────────────────────────────────────────────────

class TestValidateRanges:
    def test_typical_buero(self):
        m = _make(15, nutzung=GebaeudeNutzung.BUERO, schutzklasse=Schutzklasse.III)
        conf, reason = blitz_validate_ranges(m)
        assert conf == 1.0
        assert "typisch" in reason.lower() or "alle" in reason.lower()

    def test_below_typical_range(self):
        m = _make(2, nutzung=GebaeudeNutzung.BUERO, schutzklasse=Schutzklasse.III)
        conf, _ = blitz_validate_ranges(m)
        assert conf < 1.0

    def test_above_typical_range(self):
        # Büro typical max=28, so 28*1.5=42. 50 > 42 → penalty
        m = _make(50, nutzung=GebaeudeNutzung.BUERO, schutzklasse=Schutzklasse.III)
        conf, _ = blitz_validate_ranges(m)
        assert conf < 1.0

    def test_schutzklasse_mismatch(self):
        # Büro typically SK III, giving SK I should reduce confidence
        m = _make(15, nutzung=GebaeudeNutzung.BUERO, schutzklasse=Schutzklasse.I)
        conf, _ = blitz_validate_ranges(m)
        assert conf < 1.0

    def test_missing_schutzklasse(self):
        m = _make(15, nutzung=GebaeudeNutzung.BUERO, schutzklasse=None)
        conf, reason = blitz_validate_ranges(m)
        assert conf < 1.0
        assert "fallback" in reason.lower() or "schutzklasse" in reason.lower()

    def test_large_ms_ausschreibung_warning(self):
        m = _make(30, nutzung=GebaeudeNutzung.INDUSTRIE, schutzklasse=Schutzklasse.III)
        conf, reason = blitz_validate_ranges(m)
        assert conf < 1.0
        assert "rabatt" in reason.lower() or "ausschreibung" in reason.lower()

    def test_krankenhaus_typical(self):
        m = _make(80, nutzung=GebaeudeNutzung.KRANKENHAUS, schutzklasse=Schutzklasse.II)
        conf, reason = blitz_validate_ranges(m)
        # >25 TS → Ausschreibung warning, but range is OK
        assert conf <= 1.0


# ──────────────────────────────────────────────────────────────
# 6. Merkmale — Pydantic validation
# ──────────────────────────────────────────────────────────────

class TestMerkmale:
    def test_minimal_valid(self):
        m = _make(10)
        assert m.anzahl_ableitungen == 10
        assert m.nutzung == GebaeudeNutzung.BUERO

    def test_all_defaults(self):
        m = _make(10)
        assert m.vereinsmitglied is True
        assert m.eilzuschlag is False
        assert m.erstpruefung is False
        assert m.baurechtlich is False
        assert m.art_pruefung == ArtPruefung.WP
        assert m.potentialausgleich_vorhanden is True
        assert m.ueberspannungsschutz_vorhanden is False

    def test_enum_values(self):
        for n in GebaeudeNutzung:
            m = _make(10, nutzung=n)
            assert m.nutzung == n

    def test_invalid_nutzung_rejected(self):
        with pytest.raises(Exception):
            _make(10, nutzung="flughafen")

    def test_anzahl_ableitungen_min(self):
        with pytest.raises(Exception):
            _make(0)

    def test_anzahl_ableitungen_max(self):
        with pytest.raises(Exception):
            _make(501)

    def test_breite_swapped_to_laenge(self):
        m = BlitzschutzMerkmale(
            nutzung=GebaeudeNutzung.BUERO,
            anzahl_ableitungen=10,
            laenge_m=20,
            breite_m=30,  # > laenge → should swap
        )
        assert m.breite_m == 20  # swapped to laenge value

    def test_schutzklasse_optional(self):
        m = _make(10, schutzklasse=None)
        assert m.schutzklasse is None

    def test_all_schutzklassen(self):
        for sk in Schutzklasse:
            m = _make(10, schutzklasse=sk)
            assert m.schutzklasse == sk

    def test_adresse_fields_optional(self):
        m = _make(10)
        assert m.adresse_ort is None
        assert m.adresse_plz is None
        assert m.adresse_strasse is None
        assert m.adresse_lat is None
        assert m.adresse_lon is None


# ──────────────────────────────────────────────────────────────
# 7. PricingEngine — end-to-end (mocked Reisekosten)
# ──────────────────────────────────────────────────────────────

def _mock_find_nearest(lat, lon):
    return {
        "id": "NBG", "name": "Nürnberg", "plz": "90431",
        "adresse": "Edisonstraße 15",
        "distance_km": 25.0, "duration_min": 20.0,
        "routing": "test_mock",
    }


class TestPricingEngine:
    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_simple_buero_12ts(self, mock_standort):
        gewerk = get_gewerk("blitzschutz")
        engine = PricingEngine()
        m = _make(12, adresse_lat=49.45, adresse_lon=11.08)

        angebot = engine.calculate(gewerk, m)

        assert angebot.total > 0
        assert angebot.breakdown.pruef == blitz_pruefkosten(m)
        assert angebot.breakdown.bericht == BERICHT_STANDARD  # 12 MS → standard
        assert angebot.confidence > 0
        assert angebot.gewerk == gewerk.name
        assert angebot.lpv_referenz == "B04 §8.1"
        assert len(angebot.zuschlaege) == 0
        assert len(angebot.warnings) > 0  # at least Standort info

    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_grundkosten_without_baurechtlich(self, mock_standort):
        gewerk = get_gewerk("blitzschutz")
        engine = PricingEngine()
        m = _make(5, adresse_lat=49.45, adresse_lon=11.08)

        angebot = engine.calculate(gewerk, m)

        # Grund = Pauschale(256) + Prüfmittel(49×0.5 Tage) + Tagegeld(0 for 4h)
        pruef_tage = 0.5
        expected_grund = GRUNDKOSTEN_AUFTRAGSVERWALTUNG + PRUEFMITTEL_PRO_TAG_SV * pruef_tage + 0  # tagegeld(4h) = 0
        assert abs(angebot.breakdown.grund - expected_grund) < 0.01

    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_grundkosten_with_baurechtlich(self, mock_standort):
        gewerk = get_gewerk("blitzschutz")
        engine = PricingEngine()
        m = _make(5, baurechtlich=True, adresse_lat=49.45, adresse_lon=11.08)

        angebot = engine.calculate(gewerk, m)

        pruef_tage = 0.5
        expected_grund = (
            GRUNDKOSTEN_AUFTRAGSVERWALTUNG
            + GRUNDKOSTEN_ORDNUNGSPRUEFUNG
            + PRUEFMITTEL_PRO_TAG_SV * pruef_tage
            + 0  # tagegeld(4h) = 0
        )
        assert abs(angebot.breakdown.grund - expected_grund) < 0.01

    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_bericht_klein(self, mock_standort):
        gewerk = get_gewerk("blitzschutz")
        engine = PricingEngine()
        m = _make(8, adresse_lat=49.45, adresse_lon=11.08)

        angebot = engine.calculate(gewerk, m)
        assert angebot.breakdown.bericht == BERICHT_KLEIN

    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_bericht_komplex(self, mock_standort):
        gewerk = get_gewerk("blitzschutz")
        engine = PricingEngine()
        m = _make(50, adresse_lat=49.45, adresse_lon=11.08)

        angebot = engine.calculate(gewerk, m)
        assert angebot.breakdown.bericht == BERICHT_KOMPLEX

    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_zuschlaege_applied_to_total(self, mock_standort):
        gewerk = get_gewerk("blitzschutz")
        engine = PricingEngine()
        m = _make(10, vereinsmitglied=False, adresse_lat=49.45, adresse_lon=11.08)

        angebot = engine.calculate(gewerk, m)

        # Total should be subtotal × (1 + 0.20)
        expected_total = angebot.breakdown.subtotal * (1 + ZUSCHLAG_NICHT_VEREINSMITGLIED)
        assert abs(angebot.total - expected_total) < 0.01
        assert len(angebot.zuschlaege) == 1

    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_multiple_zuschlaege_compound(self, mock_standort):
        gewerk = get_gewerk("blitzschutz")
        engine = PricingEngine()
        m = _make(10, vereinsmitglied=False, eilzuschlag=True, adresse_lat=49.45, adresse_lon=11.08)

        angebot = engine.calculate(gewerk, m)
        assert len(angebot.zuschlaege) == 2

        # Zuschläge are compounding: first +20%, then +25% on new total
        subtotal = angebot.breakdown.subtotal
        after_first = subtotal * (1 + 0.20)
        after_second = after_first * (1 + 0.25)
        assert abs(angebot.total - after_second) < 0.01

    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_reisekosten_calculated(self, mock_standort):
        gewerk = get_gewerk("blitzschutz")
        engine = PricingEngine()
        m = _make(10, adresse_lat=49.45, adresse_lon=11.08)

        angebot = engine.calculate(gewerk, m)
        assert angebot.breakdown.reise > 0

    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_no_coords_no_reisekosten(self, mock_standort):
        gewerk = get_gewerk("blitzschutz")
        engine = PricingEngine()
        m = _make(10)  # no lat/lon

        angebot = engine.calculate(gewerk, m)
        assert angebot.breakdown.reise == 0
        assert any("koordinaten" in w.lower() or "adresse" in w.lower() for w in angebot.warnings)

    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_angebot_to_dict_structure(self, mock_standort):
        gewerk = get_gewerk("blitzschutz")
        engine = PricingEngine()
        m = _make(20, adresse_lat=49.45, adresse_lon=11.08)

        d = engine.calculate(gewerk, m).to_dict()
        assert "total" in d
        assert "breakdown" in d
        assert set(d["breakdown"].keys()) == {"grund", "pruef", "reise", "bericht", "subtotal"}
        assert "zuschlaege" in d
        assert "confidence" in d
        assert "warnings" in d
        assert "lpv_referenz" in d


# ──────────────────────────────────────────────────────────────
# 8. Golden reference — known-good scenario
# ──────────────────────────────────────────────────────────────

class TestGoldenReference:
    """Pin known-good outputs so refactoring doesn't silently change pricing."""

    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_buero_nuernberg_12ts(self, mock_standort):
        """Bürogebäude Nürnberg, 12 TS, Schutzklasse III, wiederkehrend, Vereinsmitglied."""
        gewerk = get_gewerk("blitzschutz")
        engine = PricingEngine()

        m = BlitzschutzMerkmale(
            nutzung=GebaeudeNutzung.BUERO,
            anzahl_ableitungen=12,
            schutzklasse=Schutzklasse.III,
            adresse_ort="Nürnberg",
            adresse_plz="90431",
            adresse_lat=49.4440,
            adresse_lon=11.0250,
            vereinsmitglied=True,
            erstpruefung=False,
            eilzuschlag=False,
            baurechtlich=False,
        )

        angebot = engine.calculate(gewerk, m)

        # Prüfkosten: 10×33 + 2×30 = 390
        assert angebot.breakdown.pruef == 390.00

        # Bericht: 12 MS → standard (380€)
        assert angebot.breakdown.bericht == 380.00

        # Prüftage: 12 → 1.0
        # Grund: 256 + 49×1.0 + tagegeld(8h)=25 = 330
        assert abs(angebot.breakdown.grund - 330.00) < 0.01

        # No Zuschläge
        assert len(angebot.zuschlaege) == 0

        # Confidence: typical range + typical SK → only >25 TS warning shouldn't apply
        assert angebot.confidence == 1.0

    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_schule_wuerzburg_35ts_erstpruefung(self, mock_standort):
        """Schule, 35 TS, Erstprüfung, kein Vereinsmitglied — scenario from chat.py example."""
        gewerk = get_gewerk("blitzschutz")
        engine = PricingEngine()

        m = BlitzschutzMerkmale(
            nutzung=GebaeudeNutzung.SCHULE,
            anzahl_ableitungen=35,
            schutzklasse=Schutzklasse.III,
            adresse_ort="Würzburg",
            adresse_lat=49.7830,
            adresse_lon=9.9400,
            vereinsmitglied=False,
            erstpruefung=True,
            eilzuschlag=False,
        )

        angebot = engine.calculate(gewerk, m)

        # Prüfkosten: 10×33 + 10×30 + 15×28 = 330+300+420 = 1050
        assert angebot.breakdown.pruef == 1050.00

        # Bericht: 35 → standard (380)
        assert angebot.breakdown.bericht == 380.00

        # 2 Zuschläge: Nicht-Vereinsmitglied + Erstprüfung
        assert len(angebot.zuschlaege) == 2

        # Total > subtotal (zuschläge add up)
        assert angebot.total > angebot.breakdown.subtotal

    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_krankenhaus_180ts(self, mock_standort):
        """Krankenhaus, 180 TS — edge of typical range, max Staffel."""
        gewerk = get_gewerk("blitzschutz")
        engine = PricingEngine()

        m = BlitzschutzMerkmale(
            nutzung=GebaeudeNutzung.KRANKENHAUS,
            anzahl_ableitungen=180,
            schutzklasse=Schutzklasse.II,
            adresse_lat=48.14,
            adresse_lon=11.58,
        )

        angebot = engine.calculate(gewerk, m)

        # Prüfkosten: 10×33 + 10×30 + 20×28 + 60×26 + 80×24 = 330+300+560+1560+1920 = 4670
        assert angebot.breakdown.pruef == 4670.00

        # Bericht: 180 → komplex
        assert angebot.breakdown.bericht == BERICHT_KOMPLEX

        # Prüftage: 180 → max(3, 180/40) = 4.5
        assert blitz_estimate_pruef_tage(m) == 4.5

    @patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_find_nearest)
    def test_single_messstelle_wohnung(self, mock_standort):
        """Wohngebäude, 1 TS — smallest possible Anlage."""
        gewerk = get_gewerk("blitzschutz")
        engine = PricingEngine()

        m = BlitzschutzMerkmale(
            nutzung=GebaeudeNutzung.WOHNUNG,
            anzahl_ableitungen=1,
            schutzklasse=Schutzklasse.IV,
            adresse_lat=48.14,
            adresse_lon=11.58,
        )

        angebot = engine.calculate(gewerk, m)

        assert angebot.breakdown.pruef == 33.00
        assert angebot.breakdown.bericht == BERICHT_KLEIN
        assert angebot.total > 0


# ──────────────────────────────────────────────────────────────
# 9. Staffel constants integrity
# ──────────────────────────────────────────────────────────────

class TestStaffelIntegrity:
    def test_staffeln_contiguous(self):
        """Staffeln should cover ranges without gaps."""
        for i in range(len(STAFFEL) - 1):
            assert STAFFEL[i][1] + 1 == STAFFEL[i + 1][0], \
                f"Gap between Staffel {i} (bis={STAFFEL[i][1]}) and {i+1} (von={STAFFEL[i+1][0]})"

    def test_staffeln_decreasing_rates(self):
        """Larger volumes should have lower per-MS rates."""
        for i in range(len(STAFFEL) - 1):
            assert STAFFEL[i][2] >= STAFFEL[i + 1][2], \
                f"Rate should decrease: Staffel {i} ({STAFFEL[i][2]}) vs {i+1} ({STAFFEL[i+1][2]})"

    def test_first_staffel_below_lpv_rate(self):
        """First Staffel rate should be ≤ LPV base rate (volume discount)."""
        assert STAFFEL[0][2] <= PREIS_PRO_MESSSTELLE

    def test_lpv_rate_constant(self):
        assert PREIS_PRO_MESSSTELLE == 33.00


# ──────────────────────────────────────────────────────────────
# 10. Pricing primitives (shared across Gewerke)
# ──────────────────────────────────────────────────────────────

class TestPricingPrimitives:
    def test_grundkosten_values(self):
        assert GRUNDKOSTEN_AUFTRAGSVERWALTUNG == 256.00
        assert GRUNDKOSTEN_ORDNUNGSPRUEFUNG == 242.00
        assert PRUEFMITTEL_PRO_TAG_SV == 49.00

    def test_bericht_values(self):
        assert BERICHT_KLEIN == 119.00
        assert BERICHT_STANDARD == 380.00
        assert BERICHT_KOMPLEX == 550.00

    def test_zuschlag_values(self):
        assert ZUSCHLAG_NICHT_VEREINSMITGLIED == 0.20
        assert ZUSCHLAG_EILZUSCHLAG == 0.25
        assert ZUSCHLAG_ERSTPRUEFUNG == 1.00
