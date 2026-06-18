"""A5 — Hotel-Referenzkurve (Motel-One-Zimmer-Staffel).

Pfeifer/Pausch 17.06: Hotel → Zimmer-Staffel (Motel-One-Liste 2025) statt
NBG-m²-Fallback. Schließt die Hotel→NBG-Lücke (T06, T13).
"""

from unittest.mock import patch

from products.dguv_v3.merkmale import DGUVMerkmale, GebaeudeNutzungDGUV
from products.dguv_v3.referenzpreise import (
    lookup_referenzpreis,
    _hotel_zimmer_staffel,
    M2_PRO_ZIMMER,
)
from engine.pricing_engine import PricingEngine
from engine.gewerk import get_gewerk
import products.dguv_v3  # noqa: F401


def _mock(lat, lon):
    return {"id": "MUC", "name": "München", "plz": "80686",
            "adresse": "Westendstraße 199", "distance_km": 30.0,
            "duration_min": 25.0, "routing": "test_mock"}


class TestHotelStaffelWerte:
    def test_bands_aus_motel_one_liste(self):
        # Zimmer = m²/30; Werte aus Liste 2.3b (Wiederholung)
        assert _hotel_zimmer_staffel(90 * M2_PRO_ZIMMER)["pruefkosten"] == 2069.0
        assert _hotel_zimmer_staffel(260 * M2_PRO_ZIMMER)["pruefkosten"] == 3160.0
        assert _hotel_zimmer_staffel(560 * M2_PRO_ZIMMER)["pruefkosten"] == 4815.0

    def test_zimmer_aus_flaeche(self):
        ref = _hotel_zimmer_staffel(6000)  # 200 Zimmer
        assert ref["zimmer"] == 200
        assert ref["pruefkosten"] == 3160.0  # ≤260-Band

    def test_ueber_560_zimmer_kein_listenwert(self):
        assert _hotel_zimmer_staffel(600 * M2_PRO_ZIMMER) is None


class TestHotelRouting:
    def test_hotel_enum_routet_zimmer_staffel(self):
        ref = lookup_referenzpreis(GebaeudeNutzungDGUV.HOTEL, 3000)  # 100 Zimmer
        assert ref is not None
        assert ref["referenz_typ"] == "hotel_zimmer_staffel"
        assert ref["pruefkosten"] == 2566.0  # ≤160-Band

    def test_chat_motel_routet_staffel(self):
        ref = lookup_referenzpreis(
            GebaeudeNutzungDGUV.SONSTIGE, 3000, nutzung_str="Motel"
        )
        assert ref is not None
        assert ref["referenz_typ"] == "hotel_zimmer_staffel"


class TestHotelEndToEnd:
    def test_t13_zimmer_basiert_nicht_nbg(self):
        # T13-Profil (Motel One München, ~200 Zimmer). Vor A5: NBG ~5161€.
        # Nach A5: Zimmer-Referenz 3160€ + Grund/Reise/Bericht → sane Größenordnung.
        m = DGUVMerkmale(
            nutzung=GebaeudeNutzungDGUV.HOTEL,
            gesamtflaeche_m2=6000,
            adresse_lat=48.14, adresse_lon=11.57,
        )
        with patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock):
            angebot = PricingEngine().calculate(get_gewerk("dguv_v3"), m)
        # Prüfkosten = Zimmer-Referenz (3160), nicht NBG-Degression
        assert abs(angebot.breakdown.pruef - 3160.0) < 1.0, angebot.breakdown.pruef
        # Doc-Range echte Motel-One-Prüfung ≈ 1.500–4.700 € (+ Grund/Reise/Bericht)
        assert 3000 < angebot.total < 5500, f"T13 total {angebot.total:.0f}€"
