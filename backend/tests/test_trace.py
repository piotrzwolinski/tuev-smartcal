"""Phase 3b — Trace-Tests für die konsolidierte Engine.

Prüft den Trace-Kontrakt: gefüllt, summen-konsistent, keine Fabrikation
(jeder Geld-Schritt hat Quelle+Knoten), Schema-stabil, Prüfart-Coverage.
"""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.pricing_engine import PricingEngine
from engine.gewerk import get_gewerk
from products.dguv_v3.merkmale import (
    DGUVMerkmale, GebaeudeNutzungDGUV as N, Installationskategorie as K,
    Pruefart as P, NutzungsMixEintrag,
)
import products.dguv_v3  # noqa
import products.blitzschutz  # noqa

SCHEMA = {"step", "source", "value", "node_id", "ref"}
META_STEPS = {"prueftage", "confidence", "cross_sell", "branchenvergleich", "kalibrierung"}
# step-Typ → breakdown-Block
BLOCK = {"grundkosten": "grund", "tagegeld": "grund", "pruefkosten": "pruef",
         "reisekosten": "reise", "bericht": "bericht"}

_STANDORT = {"id": "MUC", "name": "München", "crm_nl": "0MUC", "plz": "80686",
             "adresse": "x", "distance_km": 25, "duration_min": 22, "routing": "mock"}

CASES = {
    "dguv_ortsfest": DGUVMerkmale(nutzung=N.BUEROGEBAEUDE, gesamtflaeche_m2=3000,
                                  primary_installationskategorie=K.KAT_2, anzahl_verteilungen_uv=2,
                                  adresse_lat=48.1, adresse_lon=11.5, adresse_plz="80331"),
    "vds": DGUVMerkmale(nutzung=N.INDUSTRIE, pruefart=P.VDS, gesamtflaeche_m2=20000,
                        anzahl_verteilungen_uv=45, primary_installationskategorie=K.KAT_3,
                        adresse_lat=48.1, adresse_lon=11.5, adresse_plz="80331"),
    "ma560": DGUVMerkmale(nutzung=N.INDUSTRIE, pruefart=P.DGUV_ORTSVERAENDERLICH,
                          anzahl_betriebsmittel=114, adresse_lat=48.1, adresse_lon=11.5, adresse_plz="80331"),
    "kleinauftrag": DGUVMerkmale(nutzung=N.SONSTIGE, anzahl_verteilungen_nshv=1,
                                 adresse_lat=48.1, adresse_lon=11.5, adresse_plz="80331"),
    "kombi": DGUVMerkmale(nutzung=N.KRANKENHAUS, pruefart=P.DGUV_PLUS_VDS, gesamtflaeche_m2=18000,
                          nutzungs_mix=[NutzungsMixEintrag(nutzung="Allg", anteil=0.7, kategorie=K.KAT_2),
                                        NutzungsMixEintrag(nutzung="OP", anteil=0.3, kategorie=K.KAT_7)],
                          adresse_lat=48.1, adresse_lon=11.5, adresse_plz="80331"),
}


@pytest.fixture(scope="module", autouse=True)
def _graph():
    from products.dguv_v3.graph_schema import load_dguv_graph
    load_dguv_graph()


def _calc(m):
    g = get_gewerk("dguv_v3")
    with patch("common.pricing_primitives.find_nearest_standort", return_value=_STANDORT):
        return PricingEngine().calculate(g, m)


@pytest.mark.parametrize("name", list(CASES))
def test_trace_not_empty(name):
    a = _calc(CASES[name])
    assert len(a.provenance) > 0, f"{name}: Trace leer"


@pytest.mark.parametrize("name", list(CASES))
def test_trace_schema(name):
    a = _calc(CASES[name])
    for s in a.provenance:
        assert set(s.keys()) == SCHEMA, f"{name}: Schema {set(s.keys())}"


@pytest.mark.parametrize("name", list(CASES))
def test_trace_sum_per_block(name):
    a = _calc(CASES[name])
    sums = {"grund": 0.0, "pruef": 0.0, "reise": 0.0, "bericht": 0.0}
    for s in a.provenance:
        blk = BLOCK.get(s["step"])
        if blk and isinstance(s["value"], (int, float)):
            sums[blk] += s["value"]
    bd = a.breakdown
    for blk, want in (("grund", bd.grund), ("pruef", bd.pruef), ("reise", bd.reise), ("bericht", bd.bericht)):
        assert abs(sums[blk] - want) < 0.5, f"{name}: Σ{blk}={sums[blk]:.2f} != breakdown {want:.2f}"


@pytest.mark.parametrize("name", list(CASES))
def test_trace_no_fabrication(name):
    """Jeder Geld-Schritt hat Quelle UND Knoten (Synapse §3 — kein erfundenes ref)."""
    a = _calc(CASES[name])
    for s in a.provenance:
        if s["step"] in META_STEPS:
            continue
        if isinstance(s["value"], (int, float)) and abs(s["value"]) > 0:
            assert s["ref"], f"{name}: Geld-Schritt ohne ref: {s['source']}"
            assert s["node_id"], f"{name}: Geld-Schritt ohne node_id: {s['source']}"


def test_pruefart_coverage():
    """Genau die in Prod fehlenden Pfade tauchen im Trace auf."""
    nodes = lambda m: {s["node_id"] for s in _calc(m).provenance}
    assert "BM_PREIS" in nodes(CASES["ma560"]), "MA560: BM-Schritt fehlt"
    assert "KLEINAUFTRAG" in nodes(CASES["kleinauftrag"]), "Kleinauftrag-Schritt fehlt"
    assert "VDS_KOMBI" in nodes(CASES["kombi"]), "Kombi-Faktor-Schritt fehlt"
    assert "VDS_2871" in nodes(CASES["vds"]), "VdS-Grundpreis-Schritt fehlt"
