"""Trace-Capture — Modul NEBEN der Engine, ändert sie NICHT.

Ruft nur die öffentliche API `PricingEngine.calculate()` auf und liest den
`provenance`-Trace, den die Engine ohnehin emittiert. Dumpt pro Fall ein JSON
nach viz/out/<id>.json — Input für den HTML-Renderer (render_tree.py).

KEINE Änderung an engine/ oder products/. Read-only Konsument.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.graph_pricing_engine import GraphPricingEngine
from engine.gewerk import get_gewerk
from products.dguv_v3.merkmale import (
    DGUVMerkmale, GebaeudeNutzungDGUV, Installationskategorie, Pruefart,
)
import products.dguv_v3  # noqa: register
import products.blitzschutz  # noqa: register

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)

# München-Koordinaten (Warm-Cache, kein Netzwerk), PLZ für Standort-Lookup
MUC = dict(adresse_lat=48.1351, adresse_lon=11.5075, adresse_plz="80331", adresse_ort="München")

CASES = {
    "buero_3000": {
        "titel": "Bürogebäude München, 3.000 m², 2 UV",
        "merkmale": DGUVMerkmale(
            nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE,
            pruefart=Pruefart.DGUV_ORTSFEST,
            gesamtflaeche_m2=3000,
            primary_installationskategorie=Installationskategorie.KAT_2,
            anzahl_verteilungen_uv=2,
            **MUC,
        ),
    },
    "apleona_kombi": {
        "titel": "Apleona-Typ: DGUV+VdS kombi, 26.000 m², 37 UV (T08)",
        "merkmale": DGUVMerkmale(
            nutzung=GebaeudeNutzungDGUV.INDUSTRIE,
            pruefart=Pruefart.DGUV_PLUS_VDS,
            gesamtflaeche_m2=26000,
            primary_installationskategorie=Installationskategorie.KAT_3,
            anzahl_verteilungen_uv=37,
            vds_pruefung=True,
            **MUC,
        ),
    },
    "hotel_gap": {
        "titel": "Hotel München, 3.600 m² (Routing-Lücke → NBG-Fallback)",
        "merkmale": DGUVMerkmale(
            nutzung=GebaeudeNutzungDGUV.HOTEL if hasattr(GebaeudeNutzungDGUV, "HOTEL")
            else GebaeudeNutzungDGUV.BUEROGEBAEUDE,
            pruefart=Pruefart.DGUV_ORTSFEST,
            gesamtflaeche_m2=3600,
            primary_installationskategorie=Installationskategorie.KAT_2,
            anzahl_verteilungen_uv=3,
            **MUC,
        ),
    },
}


def capture(case_id: str, titel: str, merkmale: DGUVMerkmale) -> dict:
    gewerk = get_gewerk("dguv_v3")
    engine = GraphPricingEngine(gewerk.graph_name)   # gleicher Pfad wie Produktion
    angebot = engine.calculate(gewerk, merkmale)
    data = {
        "id": case_id,
        "titel": titel,
        "inputs": merkmale.model_dump(exclude_none=True),
        "total": round(angebot.total, 2),
        "breakdown": angebot.breakdown.to_dict(),
        "confidence": round(angebot.confidence, 3),
        "confidence_reason": angebot.confidence_reason,
        # DAS ist der Trace, den die Engine bereits emittiert — wir lesen ihn nur:
        "provenance": engine.provenance,
    }
    (OUT / f"{case_id}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return data


if __name__ == "__main__":
    for cid, c in CASES.items():
        try:
            d = capture(cid, c["titel"], c["merkmale"])
            print(f"{cid}: total={d['total']:.0f}€, {len(d['provenance'])} trace-steps → out/{cid}.json")
        except Exception as e:
            print(f"{cid}: FEHLER {type(e).__name__}: {e}")
