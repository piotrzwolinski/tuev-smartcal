"""DGUV V3 ortsfeste elektrische Anlagen — Phase 1 product.

Covers MA507 (10,096 reports) — ortsfeste elektrische Anlagen, cyclic DGUV V3/V4 check.
Phase 2: extend with MA501 (Ex-Bereich), MA510 (Sonderbau + ZB+NEA+USV), MA560 (ortsveränderliche).

Norma: DIN VDE 0105-100/A1 + DGUV V3/V4 + BetrSichV
LPV referenz: B04 Kap. 2 (250€ Grundpreis + 1-5€/10m² per Installationskategorie)
Golden set: Gersthofen (1,393 pozycji LV) + Audi 059E-2025 Ausschreibung

Veit-benchmark: "Wenn wir das geschafft haben, dann wissen wir, es funktioniert."
"""

from engine.gewerk import Gewerk, register_gewerk
from products.dguv_v3.merkmale import DGUVMerkmale
from products.dguv_v3.pricing_rules import (
    dguv_pruefkosten,
    dispatch_pruefkosten,
    dguv_estimate_pruef_tage,
    dguv_choose_bericht_typ,
    dguv_zuschlaege,
    dguv_validate_ranges,
    dguv_referenzpreis,
    dguv_referenzpreis_vergleich,
    is_kleinauftrag,
    kleinauftrag_pruefkosten,
    kleinauftrag_grundkosten,
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
        return dispatch_pruefkosten(merkmale)

    def grundkosten_override(self, merkmale):
        from products.dguv_v3.merkmale import Pruefart
        if getattr(merkmale, "pruefart", None) == Pruefart.DGUV_ORTSVERAENDERLICH:
            return 0.0
        if is_kleinauftrag(merkmale):
            return kleinauftrag_grundkosten(merkmale)
        return None

    def reise_inklusive(self, merkmale):
        """MA560 ortsveränderlich: Reise ist in der all-inclusive Grundpauschale enthalten
        (Rate kalibriert gegen reale Auftragspreise T04/T10 ohne separate Reisekosten)."""
        from products.dguv_v3.merkmale import Pruefart
        return getattr(merkmale, "pruefart", None) == Pruefart.DGUV_ORTSVERAENDERLICH

    def estimate_pruef_tage(self, merkmale):
        return dguv_estimate_pruef_tage(merkmale)

    def choose_bericht_typ(self, merkmale):
        return dguv_choose_bericht_typ(merkmale)

    def zuschlaege(self, merkmale):
        return dguv_zuschlaege(merkmale)

    def zusatzleistungen(self, merkmale):
        """PV-Anlagen + Ladesäulen-Addons (portiert aus GraphPricingEngine._calc_dguv_addons,
        ohne den fehlerhaften VdS-Kombi-Zweig — Kombi läuft über pruefart-Dispatch)."""
        from common.trace import emit
        addons = []
        pv_kwp = getattr(merkmale, "pv_kwp", None)
        if pv_kwp and pv_kwp > 0:
            from products.dguv_v3.zusatzleistungen import pv_preis_vds, pv_preis_din
            pv_norm = getattr(merkmale, "pv_norm", "din")
            pv = pv_preis_vds(pv_kwp) if pv_norm == "vds" else pv_preis_din(pv_kwp)
            addons.append({"name": f"PV-Anlage ({pv_kwp:.0f} kWp, {pv_norm.upper()})",
                           "positionen": pv["positionen"], "preis": round(pv["preis"], 2), "quelle": pv["_quelle"]})
            emit("zusatzleistung", f"PV {pv_norm.upper()} {pv_kwp:.0f} kWp", round(pv["preis"], 2), "PV_ADDON", pv["_quelle"])
        for ls in (getattr(merkmale, "ladesaeulen", None) or []):
            if isinstance(ls, dict) and ls.get("anzahl", 0) > 0:
                from products.dguv_v3.zusatzleistungen import ladesaeulen_preis
                r = ladesaeulen_preis(ls.get("typ", "wallbox"), ls.get("anschluesse", 1), ls["anzahl"])
                addons.append({"name": f"Ladesäulen ({ls['anzahl']}× {ls.get('typ', 'wallbox').upper()})",
                               "positionen": r["positionen"], "preis": round(r["preis"], 2), "quelle": r["_quelle"]})
                emit("zusatzleistung", f"Ladesäulen {ls['anzahl']}× {ls.get('typ', 'wallbox')}", round(r["preis"], 2), "LS_ADDON", r["_quelle"])
        return addons

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
