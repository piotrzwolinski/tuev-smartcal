"""Gewerk base class — product-agnostic Kalkulator core.

Gewerk maps:
- Blitzschutz → MA570 (Phase 1) + MA572/574/555 (Phase 2)
- RLT        → MA419-HYG + MA419-WPBA (Phase 1)
- DGUV V3    → MA507 (Phase 1) + MA501/560 (Phase 2)
- ... (kolejne 8 produktów w Phase 2)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, TypeVar

from pydantic import BaseModel


# ──────────────────────────────────────────────────────────────
# Output types
# ──────────────────────────────────────────────────────────────

@dataclass
class Breakdown:
    """Structured price breakdown per LPV Teil A blocks."""
    grund: float = 0.0          # Grundkosten (Pauschale + Prüfmittel)
    pruef: float = 0.0          # Prüfkosten (per-Gewerk rules)
    reise: float = 0.0          # Reisekosten (km + Reisezeit + Tagegeld)
    bericht: float = 0.0        # Berichterstellung

    @property
    def subtotal(self) -> float:
        return self.grund + self.pruef + self.reise + self.bericht

    def to_dict(self) -> dict:
        return {
            "grund": round(self.grund, 2),
            "pruef": round(self.pruef, 2),
            "reise": round(self.reise, 2),
            "bericht": round(self.bericht, 2),
            "subtotal": round(self.subtotal, 2),
        }


@dataclass
class ZuschlagApplied:
    name: str
    percent: float
    amount: float


@dataclass
class SimilarAnlage:
    anlage_id: str
    merkmale_summary: str
    historical_price: float
    similarity_score: float


@dataclass
class Angebot:
    """Komplette Kalkulacja dla pojedynczej Anfrage."""
    gewerk: str
    total: float
    breakdown: Breakdown
    zuschlaege: list[ZuschlagApplied] = field(default_factory=list)
    confidence: float = 1.0           # [0,1] — Veit-angle signal
    confidence_reason: str = ""
    similar: list[SimilarAnlage] = field(default_factory=list)
    lpv_referenz: str = ""
    warnings: list[str] = field(default_factory=list)
    referenzpreis: dict | None = None
    zusatzleistungen: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "gewerk": self.gewerk,
            "total": round(self.total, 2),
            "breakdown": self.breakdown.to_dict(),
            "zuschlaege": [
                {"name": z.name, "percent": z.percent, "amount": round(z.amount, 2)}
                for z in self.zuschlaege
            ],
            "confidence": round(self.confidence, 3),
            "confidence_reason": self.confidence_reason,
            "similar": [
                {"anlage_id": s.anlage_id, "summary": s.merkmale_summary,
                 "price": s.historical_price, "similarity": round(s.similarity_score, 3)}
                for s in self.similar
            ],
            "lpv_referenz": self.lpv_referenz,
            "warnings": self.warnings,
            "referenzpreis": self.referenzpreis,
            "zusatzleistungen": self.zusatzleistungen,
        }


# ──────────────────────────────────────────────────────────────
# Gewerk base class (contract for per-product modules)
# ──────────────────────────────────────────────────────────────

M = TypeVar("M", bound=BaseModel)


class Gewerk(ABC):
    """Base class — każdy produkt (products/<name>/__init__.py) implementuje."""

    # Metadata (override in subclass)
    id: str                      # "blitzschutz" | "rlt" | "dguv_v3"
    name: str                    # "Blitzschutz äußerer"
    ma_codes: list[str]          # ["MA570"] — który MA-code z dataset
    lpv_referenz: str            # "B04 §8.1"
    graph_name: str              # FalkorDB graph name (izolowany per produkt)

    # Overridable — per-Gewerk logic
    merkmale_schema: type[BaseModel]  # Pydantic class

    @abstractmethod
    def pruefkosten(self, merkmale: BaseModel) -> float:
        """LPV Teil B-specific Prüfkosten. Main pricing logic per Gewerk."""
        ...

    @abstractmethod
    def estimate_pruef_tage(self, merkmale: BaseModel) -> float:
        """Ile Prüftage potrzebnych (dla Grundkosten + Tagegeld)."""
        ...

    @abstractmethod
    def choose_bericht_typ(self, merkmale: BaseModel) -> str:
        """Returns 'klein' | 'standard' | 'komplex'."""
        ...

    @abstractmethod
    def extraction_prompt(self) -> str:
        """System prompt dla LLM dla ekstrakcji Merkmale z PDF."""
        ...

    @abstractmethod
    def golden_set(self) -> list[tuple[BaseModel, float, str]]:
        """Loader: list[(merkmale, real_price, source_reference)]."""
        ...

    # Optional overrides
    def zuschlaege(self, merkmale: BaseModel) -> list[tuple[str, float]]:
        """Zuschläge (name, percent). Default: none."""
        return []

    def validate_ranges(self, merkmale: BaseModel) -> tuple[float, str]:
        """Confidence [0,1] + reason. Default: always confident."""
        return 1.0, ""


# ──────────────────────────────────────────────────────────────
# Registry
# ──────────────────────────────────────────────────────────────

_REGISTRY: dict[str, Gewerk] = {}


def register_gewerk(gewerk: Gewerk) -> Gewerk:
    _REGISTRY[gewerk.id] = gewerk
    return gewerk


def get_gewerk(gewerk_id: str) -> Gewerk:
    if gewerk_id not in _REGISTRY:
        raise KeyError(f"Unknown gewerk: {gewerk_id}. Registered: {list(_REGISTRY.keys())}")
    return _REGISTRY[gewerk_id]


def list_gewerke() -> list[dict]:
    return [
        {"id": g.id, "name": g.name, "ma_codes": g.ma_codes,
         "lpv_referenz": g.lpv_referenz, "graph_name": g.graph_name}
        for g in _REGISTRY.values()
    ]
