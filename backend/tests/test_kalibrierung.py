"""Kalibrierung tests — deterministic, no DB/LLM/network.

Covers:
  - Kalibrierungspunkt provenance + implied rates
  - DEKA ground truth (3 Bürogebäude München)
  - Gersthofen ground truth (25 Gebäude, UV-only)
  - Multi-source weighted aggregation
  - Confidence scoring
  - Graph node serialization

Data sources:
  - DEKA Preismatrix (M. Pfeiffer 01.06.2026): Barthstr, Landsberger 84-90, 94-98
  - Ausschreibung Gersthofen 2025: 25 kommunale Gebäude
  - Kalkulationshilfen NBG 2026: Kat 2 = 3.10€/10m²
"""

import pytest

from products.dguv_v3.kalibrierung import (
    Kalibrierungspunkt,
    KalibrierungResult,
    QuellenTyp,
    QUELLEN_GEWICHT,
    DEKA_PUNKTE,
    GERSTHOFEN_PUNKTE,
    ALL_PUNKTE,
    kalibriere_rate,
    get_kalibrierung_for_trace,
)
from products.dguv_v3.pricing_rules import PREIS_PER_10M2
from products.dguv_v3.merkmale import Installationskategorie


# ──────────────────────────────────────────────────────────────
# 1. QuellenTyp — weight hierarchy
# ──────────────────────────────────────────────────────────────

class TestQuellenGewicht:
    def test_regel_highest(self):
        assert QUELLEN_GEWICHT[QuellenTyp.REGEL] == 1.0

    def test_faktura_high(self):
        assert QUELLEN_GEWICHT[QuellenTyp.FAKTURA] == 0.9

    def test_ausschreibung_mid(self):
        assert QUELLEN_GEWICHT[QuellenTyp.AUSSCHREIBUNG] == 0.85

    def test_grosskunde_discounted(self):
        assert QUELLEN_GEWICHT[QuellenTyp.GROSSKUNDE] == 0.7

    def test_statistik_lowest(self):
        assert QUELLEN_GEWICHT[QuellenTyp.STATISTIK] == 0.6

    def test_ordering(self):
        order = [QuellenTyp.REGEL, QuellenTyp.FAKTURA, QuellenTyp.AUSSCHREIBUNG,
                 QuellenTyp.FACHEXPERTE, QuellenTyp.GROSSKUNDE, QuellenTyp.STATISTIK]
        weights = [QUELLEN_GEWICHT[t] for t in order]
        assert weights == sorted(weights, reverse=True)


# ──────────────────────────────────────────────────────────────
# 2. Kalibrierungspunkt — provenance + implied rates
# ──────────────────────────────────────────────────────────────

class TestKalibrierungspunkt:
    def test_implied_rate_basic(self):
        kp = Kalibrierungspunkt(
            id="TEST", gebaeudetyp="Büro", preis=1050.0,
            pruefgrundlage="DGUV", flaeche_m2=1000,
        )
        # (1050 - 250) / (1000/10) = 800 / 100 = 8.0
        assert kp.implied_rate_10m2 == 8.0

    def test_implied_rate_subtracts_grundpreis(self):
        kp = Kalibrierungspunkt(
            id="TEST", gebaeudetyp="Büro", preis=250.0,
            pruefgrundlage="DGUV", flaeche_m2=1000,
        )
        # 250 - 250 = 0 → None (no rate derivable)
        assert kp.implied_rate_10m2 is None

    def test_implied_rate_no_flaeche(self):
        kp = Kalibrierungspunkt(
            id="TEST", gebaeudetyp="Büro", preis=5000.0,
            pruefgrundlage="DGUV",
        )
        assert kp.implied_rate_10m2 is None

    def test_implied_rate_per_uv(self):
        kp = Kalibrierungspunkt(
            id="TEST", gebaeudetyp="Büro", preis=5000.0,
            pruefgrundlage="DGUV", anzahl_uv=20,
        )
        assert kp.implied_rate_per_uv == 250.0

    def test_implied_rate_per_uv_none(self):
        kp = Kalibrierungspunkt(
            id="TEST", gebaeudetyp="Büro", preis=5000.0,
            pruefgrundlage="DGUV",
        )
        assert kp.implied_rate_per_uv is None

    def test_effective_gewicht_default(self):
        kp = Kalibrierungspunkt(
            id="TEST", gebaeudetyp="Büro", preis=1000.0,
            pruefgrundlage="DGUV", typ=QuellenTyp.GROSSKUNDE,
        )
        assert kp.effective_gewicht == 0.7

    def test_effective_gewicht_override(self):
        kp = Kalibrierungspunkt(
            id="TEST", gebaeudetyp="Büro", preis=1000.0,
            pruefgrundlage="DGUV", typ=QuellenTyp.GROSSKUNDE,
            gewicht=0.95,
        )
        assert kp.effective_gewicht == 0.95


# ──────────────────────────────────────────────────────────────
# 3. DEKA ground truth — 3 Bürogebäude München
# ──────────────────────────────────────────────────────────────

class TestDEKAPunkte:
    def test_count(self):
        assert len(DEKA_PUNKTE) == 3

    def test_all_buerogebaeude(self):
        for p in DEKA_PUNKTE:
            assert p.gebaeudetyp == "Bürogebäude"

    def test_all_grosskunde(self):
        for p in DEKA_PUNKTE:
            assert p.typ == QuellenTyp.GROSSKUNDE

    def test_all_gewicht_0_7(self):
        for p in DEKA_PUNKTE:
            assert p.effective_gewicht == 0.7

    def test_barthstr_price(self):
        barth = next(p for p in DEKA_PUNKTE if "BARTH" in p.id)
        assert barth.preis == 9733.0
        assert barth.flaeche_m2 == 8000
        assert barth.pruefgrundlage == "VdS"

    def test_landsberger_84_price(self):
        l84 = next(p for p in DEKA_PUNKTE if "L84" in p.id)
        assert l84.preis == 15078.0
        assert l84.flaeche_m2 == 12000
        assert l84.pruefgrundlage == "kombiniert"

    def test_landsberger_94_price(self):
        l94 = next(p for p in DEKA_PUNKTE if "L94" in p.id)
        assert l94.preis == 5255.0
        assert l94.flaeche_m2 == 4000
        assert l94.pruefgrundlage == "DGUV"

    def test_barthstr_implied_rate(self):
        barth = next(p for p in DEKA_PUNKTE if "BARTH" in p.id)
        # (9733 - 250) / (8000/10) = 9483 / 800 = 11.85
        assert barth.implied_rate_10m2 == 11.85

    def test_l94_implied_rate(self):
        l94 = next(p for p in DEKA_PUNKTE if "L94" in p.id)
        # (5255 - 250) / (4000/10) = 5005 / 400 = 12.51
        assert l94.implied_rate_10m2 == 12.51

    def test_all_have_provenance(self):
        for p in DEKA_PUNKTE:
            assert "DEKA" in p.quelle
            assert p.stand == "2026-06-01"
            assert p.id.startswith("KP_DEKA_")

    def test_deka_rates_far_above_kalkulationshilfen(self):
        kat2_rate = PREIS_PER_10M2[Installationskategorie.KAT_2]  # 3.10
        for p in DEKA_PUNKTE:
            assert p.implied_rate_10m2 > kat2_rate * 3, (
                f"{p.id}: implied {p.implied_rate_10m2} should be >3× Kalkulationshilfen {kat2_rate}"
            )

    def test_deka_implied_uv_rate_consistent(self):
        rates = [p.implied_rate_per_uv for p in DEKA_PUNKTE]
        assert all(r is not None for r in rates)
        avg = sum(rates) / len(rates)
        for r in rates:
            assert abs(r - avg) / avg < 0.40, f"UV rate {r} too far from avg {avg}"


# ──────────────────────────────────────────────────────────────
# 4. Gersthofen ground truth — UV-only (no m²)
# ──────────────────────────────────────────────────────────────

class TestGersthofenPunkte:
    def test_count(self):
        assert len(GERSTHOFEN_PUNKTE) == 4

    def test_all_ausschreibung(self):
        for p in GERSTHOFEN_PUNKTE:
            assert p.typ == QuellenTyp.AUSSCHREIBUNG

    def test_no_flaeche(self):
        for p in GERSTHOFEN_PUNKTE:
            assert p.flaeche_m2 is None

    def test_no_implied_m2_rate(self):
        for p in GERSTHOFEN_PUNKTE:
            assert p.implied_rate_10m2 is None

    def test_has_uv_rate(self):
        for p in GERSTHOFEN_PUNKTE:
            assert p.implied_rate_per_uv is not None

    def test_rathaus_uv_rate(self):
        rathaus = next(p for p in GERSTHOFEN_PUNKTE if "RATHAUS" in p.id)
        # 7996 / 24 = 333.17
        assert rathaus.implied_rate_per_uv == 333.17

    def test_uv_rates_consistent(self):
        rates = [p.implied_rate_per_uv for p in GERSTHOFEN_PUNKTE]
        avg = sum(rates) / len(rates)
        for r in rates:
            assert abs(r - avg) / avg < 0.25, f"UV rate {r} too far from avg {avg}"


# ──────────────────────────────────────────────────────────────
# 5. kalibriere_rate — weighted aggregation
# ──────────────────────────────────────────────────────────────

class TestKalibrierung:
    def test_no_punkte_returns_basis(self):
        result = kalibriere_rate(3.10, [])
        assert result.kalibriert_rate == 3.10
        assert result.basis_rate == 3.10
        assert result.range_min == 3.10
        assert result.range_max == 3.10

    def test_no_punkte_low_confidence(self):
        result = kalibriere_rate(3.10, [])
        assert result.confidence == 0.5

    def test_single_punkt_shifts_rate(self):
        kp = Kalibrierungspunkt(
            id="T1", gebaeudetyp="Büro", preis=1050.0,
            pruefgrundlage="DGUV", flaeche_m2=1000,
            typ=QuellenTyp.GROSSKUNDE,
        )
        result = kalibriere_rate(3.10, [kp])
        # Basis 3.10 (w=1.0) + implied 8.0 (w=0.7) → (3.10+5.6)/1.7 = 5.12
        assert result.kalibriert_rate == pytest.approx(5.12, abs=0.01)

    def test_kalibriert_between_min_max(self):
        result = kalibriere_rate(3.10, DEKA_PUNKTE)
        assert result.range_min <= result.kalibriert_rate <= result.range_max

    def test_basis_always_in_range(self):
        result = kalibriere_rate(3.10, DEKA_PUNKTE)
        assert result.range_min <= result.basis_rate

    def test_deka_shifts_rate_up(self):
        result = kalibriere_rate(3.10, DEKA_PUNKTE)
        assert result.kalibriert_rate > 3.10

    def test_deka_rate_reasonable(self):
        result = kalibriere_rate(3.10, DEKA_PUNKTE)
        assert 5.0 < result.kalibriert_rate < 12.0

    def test_higher_weight_stronger_pull(self):
        kp_low = Kalibrierungspunkt(
            id="T1", gebaeudetyp="Büro", preis=1050.0,
            pruefgrundlage="DGUV", flaeche_m2=1000,
            typ=QuellenTyp.STATISTIK,  # 0.6
        )
        kp_high = Kalibrierungspunkt(
            id="T2", gebaeudetyp="Büro", preis=1050.0,
            pruefgrundlage="DGUV", flaeche_m2=1000,
            typ=QuellenTyp.FAKTURA,  # 0.9
        )
        r_low = kalibriere_rate(3.10, [kp_low])
        r_high = kalibriere_rate(3.10, [kp_high])
        # Higher weight pulls harder toward 8.0
        assert r_high.kalibriert_rate > r_low.kalibriert_rate

    def test_gersthofen_no_m2_no_shift(self):
        result = kalibriere_rate(3.10, GERSTHOFEN_PUNKTE)
        # All Gersthofen have no flaeche_m2 → no implied_rate_10m2 → no shift
        assert result.kalibriert_rate == 3.10

    def test_mixed_sources_uses_only_m2(self):
        result = kalibriere_rate(3.10, ALL_PUNKTE)
        # Only DEKA has m² → same as DEKA-only
        result_deka = kalibriere_rate(3.10, DEKA_PUNKTE)
        assert result.kalibriert_rate == result_deka.kalibriert_rate


# ──────────────────────────────────────────────────────────────
# 6. Confidence scoring
# ──────────────────────────────────────────────────────────────

class TestConfidence:
    def test_no_data_low(self):
        result = kalibriere_rate(3.10, [])
        assert result.confidence == 0.5

    def test_agreeing_sources_higher(self):
        kp1 = Kalibrierungspunkt(
            id="T1", gebaeudetyp="Büro", preis=560.0,
            pruefgrundlage="DGUV", flaeche_m2=1000,
            typ=QuellenTyp.FAKTURA,
        )
        kp2 = Kalibrierungspunkt(
            id="T2", gebaeudetyp="Büro", preis=570.0,
            pruefgrundlage="DGUV", flaeche_m2=1000,
            typ=QuellenTyp.AUSSCHREIBUNG,
        )
        result = kalibriere_rate(3.10, [kp1, kp2])
        assert result.confidence > 0.5

    def test_conflicting_sources_lower(self):
        kp1 = Kalibrierungspunkt(
            id="T1", gebaeudetyp="Büro", preis=550.0,
            pruefgrundlage="DGUV", flaeche_m2=1000,
            typ=QuellenTyp.FAKTURA,
        )
        kp2 = Kalibrierungspunkt(
            id="T2", gebaeudetyp="Büro", preis=5050.0,
            pruefgrundlage="DGUV", flaeche_m2=1000,
            typ=QuellenTyp.GROSSKUNDE,
        )
        result = kalibriere_rate(3.10, [kp1, kp2])
        r_agree = kalibriere_rate(3.10, [kp1])
        assert result.confidence < r_agree.confidence

    def test_more_sources_higher_volume_factor(self):
        base = Kalibrierungspunkt(
            id="T", gebaeudetyp="Büro", preis=560.0,
            pruefgrundlage="DGUV", flaeche_m2=1000,
            typ=QuellenTyp.FAKTURA,
        )
        r1 = kalibriere_rate(3.10, [base])
        many = [
            Kalibrierungspunkt(
                id=f"T{i}", gebaeudetyp="Büro", preis=555.0 + i,
                pruefgrundlage="DGUV", flaeche_m2=1000,
                typ=QuellenTyp.FAKTURA,
            )
            for i in range(5)
        ]
        r5 = kalibriere_rate(3.10, many)
        assert r5.confidence >= r1.confidence

    def test_confidence_capped_at_1(self):
        kps = [
            Kalibrierungspunkt(
                id=f"T{i}", gebaeudetyp="Büro", preis=281.0,
                pruefgrundlage="DGUV", flaeche_m2=1000,
                typ=QuellenTyp.REGEL,
            )
            for i in range(10)
        ]
        result = kalibriere_rate(3.10, kps)
        assert result.confidence <= 1.0


# ──────────────────────────────────────────────────────────────
# 7. Provenance in quellen list
# ──────────────────────────────────────────────────────────────

class TestProvenance:
    def test_always_includes_kalkulationshilfen(self):
        result = kalibriere_rate(3.10, DEKA_PUNKTE)
        names = [q["name"] for q in result.quellen]
        assert "Kalkulationshilfen NBG" in names

    def test_includes_all_relevant_sources(self):
        result = kalibriere_rate(3.10, DEKA_PUNKTE)
        # 1 basis + 3 DEKA = 4
        assert len(result.quellen) == 4

    def test_quellen_have_typ(self):
        result = kalibriere_rate(3.10, DEKA_PUNKTE)
        for q in result.quellen:
            assert "typ" in q

    def test_quellen_have_rate(self):
        result = kalibriere_rate(3.10, DEKA_PUNKTE)
        for q in result.quellen:
            assert "rate" in q
            assert q["rate"] > 0

    def test_quellen_have_gewicht(self):
        result = kalibriere_rate(3.10, DEKA_PUNKTE)
        for q in result.quellen:
            assert "gewicht" in q


# ──────────────────────────────────────────────────────────────
# 8. Graph node serialization
# ──────────────────────────────────────────────────────────────

class TestGraphProperties:
    def test_required_fields(self):
        kp = DEKA_PUNKTE[0]
        props = kp.to_graph_properties()
        assert "id" in props
        assert "_quelle" in props
        assert "_typ" in props
        assert "_gewicht" in props
        assert "_stand" in props

    def test_optional_flaeche(self):
        with_m2 = DEKA_PUNKTE[0].to_graph_properties()
        assert "flaeche_m2" in with_m2
        assert "implied_rate_10m2" in with_m2

        without_m2 = GERSTHOFEN_PUNKTE[0].to_graph_properties()
        assert "flaeche_m2" not in without_m2
        assert "implied_rate_10m2" not in without_m2

    def test_optional_uv(self):
        with_uv = DEKA_PUNKTE[0].to_graph_properties()
        assert "anzahl_uv" in with_uv
        assert "implied_rate_per_uv" in with_uv

    def test_quelle_preserved(self):
        props = DEKA_PUNKTE[0].to_graph_properties()
        assert "DEKA" in props["_quelle"]

    def test_gewicht_matches_typ(self):
        props = DEKA_PUNKTE[0].to_graph_properties()
        assert props["_gewicht"] == QUELLEN_GEWICHT[QuellenTyp.GROSSKUNDE]


# ──────────────────────────────────────────────────────────────
# 9. get_kalibrierung_for_trace — filtered lookup
# ──────────────────────────────────────────────────────────────

class TestTraceIntegration:
    def test_buero_uses_deka(self):
        result = get_kalibrierung_for_trace(3.10, gebaeudetyp="Bürogebäude")
        assert result.kalibriert_rate > 3.10
        deka_sources = [q for q in result.quellen if "DEKA" in q.get("name", "")]
        assert len(deka_sources) == 3

    def test_schule_uses_gersthofen_only(self):
        result = get_kalibrierung_for_trace(3.10, gebaeudetyp="Schule")
        # Gersthofen Schulen have no m² → no shift
        assert result.kalibriert_rate == 3.10

    def test_unknown_type_uses_all(self):
        result = get_kalibrierung_for_trace(3.10, gebaeudetyp="Flughafen")
        # No match → falls back to ALL_PUNKTE (DEKA has m²)
        result_all = get_kalibrierung_for_trace(3.10)
        assert result.kalibriert_rate == result_all.kalibriert_rate

    def test_dguv_filter(self):
        result = get_kalibrierung_for_trace(
            3.10, gebaeudetyp="Bürogebäude", pruefgrundlage="DGUV"
        )
        dguv_sources = [q for q in result.quellen if q["typ"] == "grosskunde"]
        # Only L94 is DGUV
        assert len(dguv_sources) == 1

    def test_vds_filter(self):
        result = get_kalibrierung_for_trace(
            3.10, gebaeudetyp="Bürogebäude", pruefgrundlage="VdS"
        )
        vds_sources = [q for q in result.quellen if q["typ"] == "grosskunde"]
        # Only Barthstr is VdS
        assert len(vds_sources) == 1

    def test_result_always_has_basis(self):
        result = get_kalibrierung_for_trace(3.10, gebaeudetyp="Schule")
        assert result.basis_rate == 3.10


# ──────────────────────────────────────────────────────────────
# 10. Cross-validation: DEKA vs Gersthofen €/UV rates
# ──────────────────────────────────────────────────────────────

class TestCrossValidation:
    def test_deka_uv_rates_exist(self):
        for p in DEKA_PUNKTE:
            assert p.implied_rate_per_uv is not None

    def test_gersthofen_uv_rates_exist(self):
        for p in GERSTHOFEN_PUNKTE:
            assert p.implied_rate_per_uv is not None

    def test_deka_vs_gersthofen_uv_same_ballpark(self):
        deka_avg = sum(p.implied_rate_per_uv for p in DEKA_PUNKTE) / len(DEKA_PUNKTE)
        gerst_avg = sum(p.implied_rate_per_uv for p in GERSTHOFEN_PUNKTE) / len(GERSTHOFEN_PUNKTE)
        ratio = deka_avg / gerst_avg
        # DEKA = Großkunde (discounted), Gersthofen = Ausschreibung
        # Expect DEKA cheaper per UV, so ratio < 1.0
        # But accept wide range since different building types
        assert 0.3 < ratio < 3.0, (
            f"DEKA avg {deka_avg:.0f}€/UV vs Gersthofen avg {gerst_avg:.0f}€/UV — "
            f"ratio {ratio:.2f} outside expected range"
        )

    def test_kalkulationshilfen_vs_deka_gap_documented(self):
        """The gap between Kalkulationshilfen and DEKA is a known issue.
        This test documents it — NOT a bug, but a calibration opportunity."""
        kat2_rate = PREIS_PER_10M2[Installationskategorie.KAT_2]  # 3.10
        deka_rates = [p.implied_rate_10m2 for p in DEKA_PUNKTE]
        deka_avg = sum(deka_rates) / len(deka_rates)
        gap = deka_avg / kat2_rate
        # DEKA implies ~4× the Kalkulationshilfen rate
        assert gap > 2.0, "DEKA should be significantly above Kalkulationshilfen"
        assert gap < 10.0, "Gap shouldn't be absurdly large"
