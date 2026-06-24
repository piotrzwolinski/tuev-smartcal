"""F1 — _strip_hallucinated_reifegrad (Bug S. Pausch 22.06 'Kalkulation negativ').

Haiku halluziniert reifegrad=1 (×1,25) obwohl Kunde nichts zum Zustand sagt →
562 € wurde 702,50 €. Strip entfernt reifegrad ohne Zustand-Erwähnung → Default RG_3.
"""
from products.dguv_v3.chat import _strip_hallucinated_reifegrad


class TestStripReifegrad:
    def test_supermarkt_ohne_zustand_strippt(self):
        # Der gemeldete negativ-Fall: kein Zustand genannt → reifegrad raus
        p = {"reifegrad": 1, "nutzung": "verkaufsstaette"}
        _strip_hallucinated_reifegrad(p, "DGUV Prüfung, Supermarkt 840 m² Verkaufsfläche, in 73433")
        assert "reifegrad" not in p

    def test_mit_zustand_behaelt(self):
        p = {"reifegrad": 2}
        _strip_hallucinated_reifegrad(p, "Büro 2000 m², Zustand 2 (Nachholbedarf)")
        assert p["reifegrad"] == 2

    def test_mit_reifegrad_wort_behaelt(self):
        p = {"reifegrad": 4}
        _strip_hallucinated_reifegrad(p, "Halle, Reifegrad 4, sehr gut gepflegt")
        assert p["reifegrad"] == 4

    def test_zustand_in_session_history_behaelt(self):
        p = {"reifegrad": 1}
        hist = [{"role": "user", "content": "der Zustand ist ungeordnet"}]
        _strip_hallucinated_reifegrad(p, "und noch die PLZ 80331", hist)
        assert p["reifegrad"] == 1

    def test_kein_reifegrad_im_params_noop(self):
        p = {"nutzung": "buerogebaeude"}
        _strip_hallucinated_reifegrad(p, "Büro ohne alles")
        assert "reifegrad" not in p
