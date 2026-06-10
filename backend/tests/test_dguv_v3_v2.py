"""DGUV V3 PRD v2.1 Tests — Graph Integrity + E2E + Guardrails + Regression."""

import pytest
from products.dguv_v3.merkmale import (
    DGUVMerkmale,
    GebaeudeNutzungDGUV,
    Installationskategorie,
    Reifegrad,
    NutzungsMixEintrag,
)
from products.dguv_v3.pricing_rules import (
    PREIS_PER_10M2,
    REIFEGRAD_FAKTOR,
    VOLLERFASSUNG_FAKTOR,
    PREISSTEIGERUNG,
    DGUV_GRUNDPREIS_ANLAGE,
    DEGRESSION_DGUV,
    flaechenkosten_degressiv,
    dguv_pruefkosten,
    dguv_estimate_pruef_tage,
    dguv_choose_bericht_typ,
    dguv_zuschlaege,
    dguv_validate_ranges,
    dguv_referenzpreis,
    dguv_referenzpreis_vergleich,
    TYPICAL_KAT,
    UMRECHNUNG_M2,
    resolve_mix_kategorie,
)


# ══════════════════════════════════════════════════════════════
# B1+B2: Calibrated Pricing (Kalkulationshilfen NBG)
# ══════════════════════════════════════════════════════════════

class TestCalibratedPricing:
    def test_kat1_preis_1_00(self):
        assert PREIS_PER_10M2[Installationskategorie.KAT_1] == 1.00

    def test_kat2_preis_3_10(self):
        assert PREIS_PER_10M2[Installationskategorie.KAT_2] == 3.10

    def test_kat3_preis_5_00(self):
        assert PREIS_PER_10M2[Installationskategorie.KAT_3] == 5.00

    def test_kat4_preis_5_40(self):
        assert PREIS_PER_10M2[Installationskategorie.KAT_4] == 5.40

    def test_kat6_exists(self):
        assert Installationskategorie.KAT_6 in PREIS_PER_10M2

    def test_preise_steigen_mit_kategorie(self):
        p = PREIS_PER_10M2
        assert p[Installationskategorie.KAT_1] < p[Installationskategorie.KAT_2] < p[Installationskategorie.KAT_3] <= p[Installationskategorie.KAT_4]

    def test_buero_1000m2_kat2(self):
        m = DGUVMerkmale(nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE, gesamtflaeche_m2=1000, primary_installationskategorie=Installationskategorie.KAT_2)
        cost = dguv_pruefkosten(m)
        # Degression v2: 250 + degressiv(1000, 3.10) = 250 + 248 = 498
        expected_pruef = DGUV_GRUNDPREIS_ANLAGE + flaechenkosten_degressiv(1000, 3.10, DEGRESSION_DGUV)
        assert cost == expected_pruef

    def test_supermarkt_2000m2_kat3(self):
        m = DGUVMerkmale(nutzung=GebaeudeNutzungDGUV.VERKAUFSSTAETTE, gesamtflaeche_m2=2000, primary_installationskategorie=Installationskategorie.KAT_3)
        cost = dguv_pruefkosten(m)
        # Degression v2: 250 + degressiv(2000, 5.00) = 250 + 800 = 1050
        expected_pruef = DGUV_GRUNDPREIS_ANLAGE + flaechenkosten_degressiv(2000, 5.00, DEGRESSION_DGUV)
        assert cost == expected_pruef


# ══════════════════════════════════════════════════════════════
# B3: Gebäudetyp → Kategorie Mapping
# ══════════════════════════════════════════════════════════════

class TestGebaeudetypMapping:
    def test_buero_kat2(self):
        assert TYPICAL_KAT[GebaeudeNutzungDGUV.BUEROGEBAEUDE] == Installationskategorie.KAT_2

    def test_schule_kat2(self):
        assert TYPICAL_KAT[GebaeudeNutzungDGUV.SCHULE] == Installationskategorie.KAT_2

    def test_hotel_kat2(self):
        assert TYPICAL_KAT[GebaeudeNutzungDGUV.HOTEL] == Installationskategorie.KAT_2

    def test_industrie_kat3(self):
        assert TYPICAL_KAT[GebaeudeNutzungDGUV.INDUSTRIE] == Installationskategorie.KAT_3

    def test_supermarkt_kat3(self):
        assert TYPICAL_KAT[GebaeudeNutzungDGUV.VERKAUFSSTAETTE] == Installationskategorie.KAT_3

    def test_tiefgarage_kat1(self):
        assert TYPICAL_KAT[GebaeudeNutzungDGUV.TIEFGARAGE] == Installationskategorie.KAT_1


# ══════════════════════════════════════════════════════════════
# A3: Nutzungs-Mix
# ══════════════════════════════════════════════════════════════

class TestNutzungsMix:
    def test_mischnutzung_30_50_20(self):
        m = DGUVMerkmale(
            nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE,
            gesamtflaeche_m2=5000,
            nutzungs_mix=[
                NutzungsMixEintrag(nutzung="Büro", anteil=0.30, kategorie=Installationskategorie.KAT_2),
                NutzungsMixEintrag(nutzung="Logistik", anteil=0.50, kategorie=Installationskategorie.KAT_2),
                NutzungsMixEintrag(nutzung="Produktion", anteil=0.20, kategorie=Installationskategorie.KAT_3),
            ],
        )
        cost = dguv_pruefkosten(m)
        # Degression v2: each mix zone degressed independently
        expected = DGUV_GRUNDPREIS_ANLAGE + (
            flaechenkosten_degressiv(5000 * 0.30, 3.10, DEGRESSION_DGUV)
            + flaechenkosten_degressiv(5000 * 0.50, 3.10, DEGRESSION_DGUV)
            + flaechenkosten_degressiv(5000 * 0.20, 5.00, DEGRESSION_DGUV)
        )
        assert cost == pytest.approx(expected, rel=0.01)

    def test_reine_nutzung_ohne_mix(self):
        m = DGUVMerkmale(nutzung=GebaeudeNutzungDGUV.SCHULE, gesamtflaeche_m2=3000, primary_installationskategorie=Installationskategorie.KAT_2)
        cost = dguv_pruefkosten(m)
        # Degression v2: 250 + degressiv(3000, 3.10)
        expected = DGUV_GRUNDPREIS_ANLAGE + flaechenkosten_degressiv(3000, 3.10, DEGRESSION_DGUV)
        assert cost == expected

    def test_mix_normalisierung(self):
        m = DGUVMerkmale(
            nutzung=GebaeudeNutzungDGUV.INDUSTRIE,
            gesamtflaeche_m2=1000,
            nutzungs_mix=[
                NutzungsMixEintrag(nutzung="Büro", anteil=0.30),
                NutzungsMixEintrag(nutzung="Lager", anteil=0.50),
                NutzungsMixEintrag(nutzung="Produktion", anteil=0.30),
            ],
        )
        total_anteil = sum(e.anteil for e in m.nutzungs_mix)
        assert total_anteil == pytest.approx(1.0, abs=0.02)

    def test_resolve_mix_kategorie_buero(self):
        assert resolve_mix_kategorie("Büro") == Installationskategorie.KAT_2

    def test_resolve_mix_kategorie_produktion(self):
        assert resolve_mix_kategorie("Produktion") == Installationskategorie.KAT_3

    def test_resolve_mix_kategorie_technik(self):
        assert resolve_mix_kategorie("nshv") == Installationskategorie.KAT_6


# ══════════════════════════════════════════════════════════════
# B4: Reifegrad
# ══════════════════════════════════════════════════════════════

class TestReifegrad:
    def _base(self, rg: Reifegrad) -> float:
        m = DGUVMerkmale(nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE, gesamtflaeche_m2=1000, primary_installationskategorie=Installationskategorie.KAT_2, reifegrad=rg)
        return dguv_pruefkosten(m)

    def test_reifegrad_1_teurer(self):
        assert self._base(Reifegrad.RG_1) > self._base(Reifegrad.RG_3)

    def test_reifegrad_4_billiger(self):
        assert self._base(Reifegrad.RG_4) < self._base(Reifegrad.RG_3)

    def test_reifegrad_3_default(self):
        m = DGUVMerkmale(nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE, gesamtflaeche_m2=1000, primary_installationskategorie=Installationskategorie.KAT_2)
        assert m.reifegrad == Reifegrad.RG_3

    def test_reifegrad_1_faktor_1_25(self):
        assert REIFEGRAD_FAKTOR[Reifegrad.RG_1] == 1.25

    def test_reifegrad_4_faktor_0_80(self):
        assert REIFEGRAD_FAKTOR[Reifegrad.RG_4] == 0.80

    def test_reifegrad_multiplikator_applied(self):
        base = self._base(Reifegrad.RG_3)
        rg1 = self._base(Reifegrad.RG_1)
        assert rg1 == pytest.approx(base * 1.25, rel=0.01)


# ══════════════════════════════════════════════════════════════
# B5: Dokumentationsumfang
# ══════════════════════════════════════════════════════════════

class TestDokumentation:
    def test_vollerfassung_30_prozent_zuschlag(self):
        m_standard = DGUVMerkmale(nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE, gesamtflaeche_m2=1000, primary_installationskategorie=Installationskategorie.KAT_2, vollerfassung=False)
        m_voll = DGUVMerkmale(nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE, gesamtflaeche_m2=1000, primary_installationskategorie=Installationskategorie.KAT_2, vollerfassung=True)
        assert dguv_pruefkosten(m_voll) == pytest.approx(dguv_pruefkosten(m_standard) * 1.30, rel=0.01)

    def test_standard_kein_zuschlag(self):
        m = DGUVMerkmale(nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE, gesamtflaeche_m2=1000, primary_installationskategorie=Installationskategorie.KAT_2, vollerfassung=False)
        base = DGUV_GRUNDPREIS_ANLAGE + flaechenkosten_degressiv(1000, 3.10, DEGRESSION_DGUV)
        assert dguv_pruefkosten(m) == base

    def test_default_keine_vollerfassung(self):
        m = DGUVMerkmale(nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE, gesamtflaeche_m2=1000)
        assert m.vollerfassung is False


# ══════════════════════════════════════════════════════════════
# B6+B7+B8: Referenzpreis-Logik
# ══════════════════════════════════════════════════════════════

class TestReferenzpreis:
    def test_fortschreibung_2023(self):
        m = DGUVMerkmale(nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE, gesamtflaeche_m2=1000, referenzpreis_jahr=2023, referenzpreis_betrag=4200.0)
        ref = dguv_referenzpreis(m)
        assert ref is not None
        assert ref["fortgeschrieben_2026"] == pytest.approx(4200 * 1.148, rel=0.01)

    def test_fortschreibung_2020(self):
        m = DGUVMerkmale(nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE, gesamtflaeche_m2=1000, referenzpreis_jahr=2020, referenzpreis_betrag=3000.0)
        ref = dguv_referenzpreis(m)
        assert ref["fortgeschrieben_2026"] == pytest.approx(3000 * 1.282, rel=0.01)

    def test_kein_referenzpreis(self):
        m = DGUVMerkmale(nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE, gesamtflaeche_m2=1000)
        assert dguv_referenzpreis(m) is None

    def test_referenzpreis_warnung_bei_abweichung(self):
        m = DGUVMerkmale(nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE, gesamtflaeche_m2=1000, referenzpreis_jahr=2023, referenzpreis_betrag=4200.0)
        ref = dguv_referenzpreis(m)
        vergleich = dguv_referenzpreis_vergleich(2400.0, ref)
        assert vergleich["warnung"] is True
        assert vergleich["warnung_text"] is not None

    def test_referenzpreis_keine_warnung(self):
        m = DGUVMerkmale(nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE, gesamtflaeche_m2=1000, referenzpreis_jahr=2023, referenzpreis_betrag=4200.0)
        ref = dguv_referenzpreis(m)
        vergleich = dguv_referenzpreis_vergleich(4500.0, ref)
        assert vergleich["warnung"] is False

    def test_referenzpreis_jahr_2026_keine_steigerung(self):
        m = DGUVMerkmale(nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE, gesamtflaeche_m2=1000, referenzpreis_jahr=2026, referenzpreis_betrag=5000.0)
        ref = dguv_referenzpreis(m)
        assert ref["fortgeschrieben_2026"] == 5000.0

    def test_steigerungstabelle_6_eintraege(self):
        assert len(PREISSTEIGERUNG) >= 6
        assert 2020 in PREISSTEIGERUNG
        assert 2025 in PREISSTEIGERUNG


# ══════════════════════════════════════════════════════════════
# A2: Umrechnung Kundenmerkmal → m²
# ══════════════════════════════════════════════════════════════

class TestUmrechnung:
    def test_zimmer_faktor_30(self):
        assert UMRECHNUNG_M2["zimmer"] == 30.0

    def test_betten_faktor_50(self):
        assert UMRECHNUNG_M2["betten"] == 50.0

    def test_klassenraeume_faktor_70(self):
        assert UMRECHNUNG_M2["klassenraeume"] == 70.0

    def test_stellplaetze_faktor_25(self):
        assert UMRECHNUNG_M2["stellplaetze"] == 25.0


# ══════════════════════════════════════════════════════════════
# Confidence / Validation
# ══════════════════════════════════════════════════════════════

class TestConfidence:
    def test_alle_angaben_hohe_confidence(self):
        m = DGUVMerkmale(
            nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE, gesamtflaeche_m2=2000,
            primary_installationskategorie=Installationskategorie.KAT_2,
            anzahl_verteilungen_uv=10, anzahl_verteilungen_hv=2,
        )
        conf, _ = dguv_validate_ranges(m)
        assert conf >= 0.9

    def test_keine_verteilungen_leichte_strafe(self):
        m = DGUVMerkmale(nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE, gesamtflaeche_m2=2000, primary_installationskategorie=Installationskategorie.KAT_2)
        conf, reason = dguv_validate_ranges(m)
        assert conf < 1.0
        assert "Verteilungen" in reason

    def test_flaeche_unter_typisch(self):
        m = DGUVMerkmale(nutzung=GebaeudeNutzungDGUV.KRANKENHAUS, gesamtflaeche_m2=100, primary_installationskategorie=Installationskategorie.KAT_2)
        conf, _ = dguv_validate_ranges(m)
        assert conf < 0.9


# ══════════════════════════════════════════════════════════════
# Numerische Stabilität
# ══════════════════════════════════════════════════════════════

class TestNumerisch:
    def test_identischer_input_identischer_output(self):
        m = DGUVMerkmale(nutzung=GebaeudeNutzungDGUV.SCHULE, gesamtflaeche_m2=3000, primary_installationskategorie=Installationskategorie.KAT_2, reifegrad=Reifegrad.RG_3)
        assert dguv_pruefkosten(m) == dguv_pruefkosten(m)

    def test_euro_rounding(self):
        m = DGUVMerkmale(nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE, gesamtflaeche_m2=333, primary_installationskategorie=Installationskategorie.KAT_2)
        cost = dguv_pruefkosten(m)
        assert cost == round(cost, 2)


# ══════════════════════════════════════════════════════════════
# Demo-Szenarien E2E (pricing only, no chat)
# ══════════════════════════════════════════════════════════════

class TestDemoSzenarien:
    def test_demo_verwaltung_mischnutzung(self):
        """Szenario 1: Verwaltungsgebäude 5000m², 60/30/10 Mix, Rg3."""
        m = DGUVMerkmale(
            nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE,
            gesamtflaeche_m2=5000,
            nutzungs_mix=[
                NutzungsMixEintrag(nutzung="Büro", anteil=0.60, kategorie=Installationskategorie.KAT_2),
                NutzungsMixEintrag(nutzung="Lager", anteil=0.30, kategorie=Installationskategorie.KAT_1),
                NutzungsMixEintrag(nutzung="Technikraum", anteil=0.10, kategorie=Installationskategorie.KAT_4),
            ],
            reifegrad=Reifegrad.RG_3,
            vollerfassung=False,
            referenzpreis_jahr=2023,
            referenzpreis_betrag=4200.0,
        )
        cost = dguv_pruefkosten(m)
        assert cost > 1000
        assert cost < 5000

        ref = dguv_referenzpreis(m)
        assert ref is not None
        vergleich = dguv_referenzpreis_vergleich(cost, ref)
        assert "abweichung_prozent" in vergleich

    def test_demo_hotel_kundenperspektive(self):
        """Szenario 2: Hotel 120 Zimmer → 3600m²."""
        flaeche = 120 * UMRECHNUNG_M2["zimmer"]  # 3600
        m = DGUVMerkmale(
            nutzung=GebaeudeNutzungDGUV.HOTEL,
            gesamtflaeche_m2=flaeche,
            primary_installationskategorie=Installationskategorie.KAT_2,
        )
        cost = dguv_pruefkosten(m)
        assert 800 < cost < 3000

    def test_demo_schule_simple(self):
        """Szenario 3: Schule 3000m²."""
        m = DGUVMerkmale(
            nutzung=GebaeudeNutzungDGUV.SCHULE,
            gesamtflaeche_m2=3000,
            primary_installationskategorie=Installationskategorie.KAT_2,
        )
        cost = dguv_pruefkosten(m)
        # Degression v2: 250 + degressiv(3000, 3.10)
        expected = DGUV_GRUNDPREIS_ANLAGE + flaechenkosten_degressiv(3000, 3.10, DEGRESSION_DGUV)
        assert cost == expected

    def test_demo_reifegrad_4_abschlag(self):
        """Rg4 = 20% billiger als Rg3."""
        m3 = DGUVMerkmale(nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE, gesamtflaeche_m2=2000, primary_installationskategorie=Installationskategorie.KAT_2, reifegrad=Reifegrad.RG_3)
        m4 = DGUVMerkmale(nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE, gesamtflaeche_m2=2000, primary_installationskategorie=Installationskategorie.KAT_2, reifegrad=Reifegrad.RG_4)
        assert dguv_pruefkosten(m4) == pytest.approx(dguv_pruefkosten(m3) * 0.80, rel=0.01)
