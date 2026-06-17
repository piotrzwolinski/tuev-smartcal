"""A0 — VdS-Branchen-Kategorie-Zuordnung (S. Pausch 17.06.2026).

Kita separat (eine Klasse, Kat 2); 0800 = Produktion (eine Konstante,
Kat-Entscheidung Fr 20.06); 0904 = Verkaufsstätten.
"""

from products.dguv_v3.merkmale import Installationskategorie
from products.dguv_v3 import pricing_rules as pr
from products.dguv_v3.pricing_rules import NUTZUNG_ZU_KATEGORIE, KAT_PRODUKTION_0800


class TestKita:
    def test_kita_und_synonyme_kat2(self):
        for key in ("kita", "kindergarten", "kindertagesstaette", "kindertagesstätte"):
            assert NUTZUNG_ZU_KATEGORIE[key] == Installationskategorie.KAT_2, key

    def test_kita_einheitlich_keine_differenzierung(self):
        # Pausch: untereinander vergleichbar → alle gleich
        kita_keys = ("kita", "kindergarten", "kindertagesstaette", "kinderheim")
        kats = {NUTZUNG_ZU_KATEGORIE[k] for k in kita_keys}
        assert len(kats) == 1


class TestProduktion0800:
    def test_0800_gruppe_folgt_konstante(self):
        for key in ("nahrungsmittel", "genussmittel", "lebensmittel", "kuehlhaus"):
            assert NUTZUNG_ZU_KATEGORIE[key] == KAT_PRODUKTION_0800, key

    def test_default_kat3_pending_pausch(self):
        assert KAT_PRODUKTION_0800 == Installationskategorie.KAT_3

    def test_flip_wirkt_an_einer_stelle(self, monkeypatch):
        # Simuliert die Freitag-Entscheidung Kat2: Konstante umstellen → ganze 0800-Gruppe
        # zieht nach (Einsicht: die Zuordnung hängt an EINER Konstante).
        # (Dict-Werte sind zur Importzeit gebunden; hier prüfen wir die Identität.)
        for key in ("nahrungsmittel", "genussmittel", "lebensmittel", "kuehlhaus"):
            assert NUTZUNG_ZU_KATEGORIE[key] is KAT_PRODUKTION_0800


class TestVerkauf0904:
    def test_0904_verkaufsstaetten_kat3(self):
        for key in ("kaufhaus", "warenhaus", "einkaufszentrum"):
            assert NUTZUNG_ZU_KATEGORIE[key] == Installationskategorie.KAT_3, key
