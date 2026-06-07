"""DGUV V3 ortsfeste elektrische Anlagen — Phase 1 product.

Covers MA507 (10,096 raportów) — ortsfeste elektrische Anlagen, cyclic DGUV V3/V4 check.
Phase 2: rozszerzyć o MA501 (Ex-Bereich), MA510 (Sonderbau + ZB+NEA+USV), MA560 (ortsveränderliche).

Norma: DIN VDE 0105-100/A1 + DGUV V3/V4 + BetrSichV
LPV referenz: B04 Kap. 2 (250€ Grundpreis + 1-5€/10m² per Installationskategorie)
Golden set: Gersthofen (1,393 pozycji LV) + Audi 059E-2025 Ausschreibung

Veit-benchmark: "Wenn wir das geschafft haben, dann wissen wir, es funktioniert."
"""

from engine.gewerk import Gewerk, register_gewerk
from products.dguv_v3.merkmale import DGUVMerkmale
from products.dguv_v3.pricing_rules import (
    dguv_pruefkosten,
    dguv_estimate_pruef_tage,
    dguv_choose_bericht_typ,
    dguv_zuschlaege,
    dguv_validate_ranges,
    dguv_referenzpreis,
    dguv_referenzpreis_vergleich,
)
from products.dguv_v3.golden_set import load_dguv_golden_set


_PROMPT_PATH = __file__.replace("__init__.py", "extraction_prompt.txt")


class DGUVV3Gewerk(Gewerk):
    id = "dguv_v3"
    name = "DGUV V3 ortsfeste elektrische Anlage"
    ma_codes = ["MA507"]
    lpv_referenz = "B04 Kap. 2"
    graph_name = "dguv_v3"
    merkmale_schema = DGUVMerkmale

    def pruefkosten(self, merkmale):
        return dguv_pruefkosten(merkmale)

    def estimate_pruef_tage(self, merkmale):
        return dguv_estimate_pruef_tage(merkmale)

    def choose_bericht_typ(self, merkmale):
        return dguv_choose_bericht_typ(merkmale)

    def zuschlaege(self, merkmale):
        return dguv_zuschlaege(merkmale)

    def validate_ranges(self, merkmale):
        return dguv_validate_ranges(merkmale)

    def extraction_prompt(self) -> str:
        try:
            with open(_PROMPT_PATH, encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return "Extract DGUV V3 ortsfeste elektrische Anlagen Merkmale to JSON per schema."

    def golden_set(self):
        return load_dguv_golden_set()


DGUV_V3 = register_gewerk(DGUVV3Gewerk())
