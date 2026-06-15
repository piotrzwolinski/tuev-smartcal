"""Trace-Sink für die konsolidierte Pricing-Engine (Synapse §3).

Die Pricing-Logik (`pricing_rules`, `pricing_primitives`) ruft `emit(...)` an ihren
Wert-Ermittlungspunkten. Ist ein Trace-Kontext aktiv (gesetzt von `PricingEngine.calculate`
via `with Trace() as t:`), wird der Schritt gesammelt — sonst **No-op**. Dadurch bleiben
die Logik-Funktionen außerhalb von `calculate` reine Zahl-Funktionen (bestehende Unit-Tests
unverändert), und der Trace entsteht aus genau der Berechnung, die wirklich lief
(„der Trace kann nicht lügen").

Schema je Schritt == heutige `GraphPricingEngine.provenance` (Frontend-Kontrakt):
    {step, source, value, node_id, ref}
"""
from __future__ import annotations

import contextvars

_TRACE: contextvars.ContextVar["Trace | None"] = contextvars.ContextVar("smartcal_trace", default=None)


class Trace:
    """Sammelt Trace-Schritte innerhalb eines `with`-Blocks (ContextVar-basiert,
    threadsicher und async-sicher — kein globaler Zustand)."""

    def __init__(self) -> None:
        self.steps: list[dict] = []
        self._token = None

    def __enter__(self) -> "Trace":
        self._token = _TRACE.set(self)
        return self

    def __exit__(self, *exc) -> None:
        if self._token is not None:
            _TRACE.reset(self._token)
            self._token = None


def emit(step: str, source: str, value, node_id: str = "", ref: str = "") -> None:
    """Einen Trace-Schritt anhängen — No-op, wenn kein Trace-Kontext aktiv ist."""
    t = _TRACE.get()
    if t is not None:
        t.steps.append({
            "step": step,
            "source": source,
            "value": value,
            "node_id": node_id,
            "ref": ref,
        })


def active() -> bool:
    """True, wenn gerade ein Trace gesammelt wird (für teure source-String-Konstruktion)."""
    return _TRACE.get() is not None
