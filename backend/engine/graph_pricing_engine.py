"""DEPRECATED — auf PricingEngine konsolidiert (Branch engine-consolidation).

Die eigenständige Reimplementierung von calculate() (eigene _pruef_dguv,
_calc_grundkosten, _calc_reisekosten) wurde entfernt. Sie war die Quelle der
Engine-Divergenz: ihr fehlten MA560-per-Device, Kleinauftrag und Referenz-primär,
und sie enthielt den _calc_dguv_addons `NameError: cost` (CLAUDE.md §5).

Diese Klasse bleibt als dünner Rückwärtskompatibilitäts-Adapter: gleiche Signatur
(graph_name), gleiches Verhalten wie PricingEngine — korrekte Zahlen + Trace
(`provenance`), aus EINER Logik-Quelle (pricing_rules/primitives).
"""
from __future__ import annotations

from pydantic import BaseModel

from engine.gewerk import Gewerk, Angebot
from engine.pricing_engine import PricingEngine


class GraphPricingEngine:
    """Adapter auf PricingEngine. `graph_name` wird akzeptiert (Rückwärtskompat),
    aber nicht mehr für eine separate Berechnung genutzt — die Werte liest
    pricing_rules ohnehin aus demselben Graph (graph_reader)."""

    def __init__(self, graph_name: str | None = None, *args, **kwargs):
        self.graph_name = graph_name
        self._engine = PricingEngine()
        self.provenance: list[dict] = []

    def calculate(self, gewerk: Gewerk, merkmale: BaseModel) -> Angebot:
        angebot = self._engine.calculate(gewerk, merkmale)
        self.provenance = angebot.provenance
        return angebot
