"""Blitzschutz — Phase 1 primary product.

Covers MA570 (umfassende Prüfung, non-Baurecht, non-Ex).
Phase 2: rozszerzyć o MA572 (Baurecht Sonderbau), MA574 (wiederkehrend), MA555 (Ex-Schutz).

Norma: DIN EN 62305-1/-3 + Beiblatt 3 (Oktober 2012)
LPV referenz: B04 §8.1 (Äußerer Blitzschutz — 33€/Messstelle)
Golden set: 325 Anlagen z Blitzschutz_StV.xlsx
"""

from engine.gewerk import Gewerk, register_gewerk
from products.blitzschutz.merkmale import BlitzschutzMerkmale
from products.blitzschutz.pricing_rules import (
    blitz_pruefkosten,
    blitz_estimate_pruef_tage,
    blitz_choose_bericht_typ,
    blitz_zuschlaege,
    blitz_validate_ranges,
)
from products.blitzschutz.golden_set import load_blitzschutz_golden_set

_PROMPT_PATH = __file__.replace("__init__.py", "extraction_prompt.txt")


class BlitzschutzGewerk(Gewerk):
    id = "blitzschutz"
    name = "Blitzschutz äußerer (umfassende Prüfung)"
    ma_codes = ["MA570"]
    lpv_referenz = "B04 §8.1"
    graph_name = "blitzschutz"
    merkmale_schema = BlitzschutzMerkmale

    def pruefkosten(self, merkmale):
        return blitz_pruefkosten(merkmale)

    def estimate_pruef_tage(self, merkmale):
        return blitz_estimate_pruef_tage(merkmale)

    def choose_bericht_typ(self, merkmale):
        return blitz_choose_bericht_typ(merkmale)

    def zuschlaege(self, merkmale):
        return blitz_zuschlaege(merkmale)

    def validate_ranges(self, merkmale):
        return blitz_validate_ranges(merkmale)

    def extraction_prompt(self) -> str:
        try:
            with open(_PROMPT_PATH, encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return "Extract Blitzschutz Prüfbericht Merkmale to JSON per schema."

    def golden_set(self):
        return load_blitzschutz_golden_set()


# Register on import
BLITZSCHUTZ = register_gewerk(BlitzschutzGewerk())
