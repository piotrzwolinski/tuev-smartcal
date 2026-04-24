"""RLT-Anlage — Phase 1 product.

Covers 2 sub-warianty MA419:
- MA419-HYG: Hygieneinspektion VDI 6022 (862 raportów)
- MA419-WPBA: Garagenlüftung Baurecht BayBO+GaStellV+VDI 2053 (8,150 raportów)

Phase 1 UI: jeden produkt RLT, auto-detection sub-wariantu z Anfrage.

Norma: VDI 6022 Blatt 1 / BayBO + GaStellV + VDI 2053
LPV referenz: B05 Kap. 2 (Grundpreis 600/780€ + Ventilatoren 170€ + BSK 40€/St.)
Golden set: Vorlage Kalkulation GT RLT + GT Hygiene sheets + MUC Preistool VDI 6022 (80×11)
"""

from engine.gewerk import Gewerk, register_gewerk
from products.rlt.merkmale import RLTMerkmale
from products.rlt.pricing_rules import (
    rlt_pruefkosten,
    rlt_estimate_pruef_tage,
    rlt_choose_bericht_typ,
)
from products.rlt.golden_set import load_rlt_golden_set


class RLTGewerk(Gewerk):
    id = "rlt"
    name = "RLT-Anlage (Hygiene VDI 6022 + Garagenlüftung)"
    ma_codes = ["MA419"]
    lpv_referenz = "B05 Kap. 2"
    graph_name = "rlt"
    merkmale_schema = RLTMerkmale

    def pruefkosten(self, merkmale):
        return rlt_pruefkosten(merkmale)

    def estimate_pruef_tage(self, merkmale):
        return rlt_estimate_pruef_tage(merkmale)

    def choose_bericht_typ(self, merkmale):
        return rlt_choose_bericht_typ(merkmale)

    def extraction_prompt(self) -> str:
        # TODO M3.3 (KW18): pełny prompt
        return "Extract RLT (VDI 6022 / Garagenlüftung) Merkmale to JSON per schema."

    def golden_set(self):
        return load_rlt_golden_set()


RLT = register_gewerk(RLTGewerk())
