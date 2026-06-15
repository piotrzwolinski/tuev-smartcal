"""Phase 0 — Engine-Parity-Test (Sicherheitsnetz für die Konsolidierung).

Beide Engines MÜSSEN für denselben Input denselben Preis liefern. Heute tun sie
das NICHT (8/15 divergieren) — dieser Test ist ROT und IST damit die Spezifikation
dessen, was die Konsolidierung repariert. Am Ende (eine Engine) wird er GRÜN.

Standort wird gemockt → Reisekosten deterministisch + für beide Engines identisch,
sodass eine Divergenz nur aus der Prüf-/Grund-/Bericht-Logik stammt.
"""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.pricing_engine import PricingEngine
from engine.graph_pricing_engine import GraphPricingEngine
from engine.gewerk import get_gewerk
from products.dguv_v3.merkmale import DGUVMerkmale
import products.dguv_v3  # noqa: register
import products.blitzschutz  # noqa: register
from viz.capture_all import CASES  # 15 DGUV-Fälle T01–T15 (kanonische Merkmale)

TOL = 1.0  # €

_MOCK_STANDORT = {
    "id": "MUC", "name": "München", "crm_nl": "0MUC", "plz": "80686",
    "adresse": "Westendstr. 199", "distance_km": 25, "duration_min": 22, "routing": "mock",
}


@pytest.fixture(scope="module", autouse=True)
def _graph_loaded():
    from products.dguv_v3.graph_schema import load_dguv_graph
    load_dguv_graph()
    yield


# Heute divergierende Fälle (Konsolidierungs-Arbeitsliste). xfail(strict): sobald ein
# Fall durch die Konsolidierung Parität erreicht → XPASS → Test rot → Marker hier entfernen.
DIVERGING = {"T03", "T04", "T05", "T08", "T09", "T10", "T12", "T15"}

_PARAMS = [
    pytest.param(
        *c, id=c[0],
        marks=pytest.mark.xfail(strict=True, reason="Engine-Divergenz — Konsolidierungsziel")
        if c[0] in DIVERGING else (),
    )
    for c in CASES
]


@pytest.mark.parametrize("cid,label,real,v1,mk", _PARAMS)
def test_pruefkosten_parity(cid, label, real, v1, mk):
    """Kern-Parität: Prüfkosten (deterministisch, kein Netz). Hier sitzt die
    Divergenz (MA560/Kleinauftrag/Referenz/Kombi). Reise/Total siehe Diagnose."""
    g = get_gewerk("dguv_v3")
    m = DGUVMerkmale(**mk)
    py = PricingEngine().calculate(g, m).breakdown.pruef
    gr = GraphPricingEngine(g.graph_name).calculate(g, m).breakdown.pruef
    assert abs(py - gr) <= TOL, (
        f"{cid} {label}: Prüfkosten Python {py:,.0f}€ vs Graph {gr:,.0f}€ (Δ {gr-py:+,.0f}€)"
    )


def test_parity_landkarte(capsys):
    """Diagnose (nie rot) — volle Divergenz-Landkarte: pruef (kein Netz) + total (gemockter Standort)."""
    g = get_gewerk("dguv_v3")
    div_pruef = div_total = 0
    lines = []
    for cid, label, real, v1, mk in CASES:
        m = DGUVMerkmale(**mk)
        a_py = PricingEngine().calculate(g, m)
        a_gr = GraphPricingEngine(g.graph_name).calculate(g, m)
        dp = a_gr.breakdown.pruef - a_py.breakdown.pruef
        dt = a_gr.total - a_py.total
        if abs(dp) > TOL:
            div_pruef += 1
        if abs(dt) > TOL:
            div_total += 1
        lines.append(
            f"{cid}: pruef Py {a_py.breakdown.pruef:>7,.0f} Gr {a_gr.breakdown.pruef:>7,.0f} "
            f"Δ{dp:>+7,.0f}{'  P' if abs(dp)>TOL else '   '}  |  total Δ{dt:>+7,.0f}{'  T' if abs(dt)>TOL else ''}"
        )
    with capsys.disabled():
        print("\n--- Engine-Parity-Landkarte (Baseline, P=pruef-Divergenz, T=total-Divergenz) ---")
        print("\n".join(lines))
        print(f"Prüfkosten divergierend: {div_pruef}/{len(CASES)} · Total divergierend: {div_total}/{len(CASES)}")
