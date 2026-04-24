"""Validation: compare engine output vs golden set (realne ceny TÜV).

Usage:
    from engine.validator import run_validation
    report = run_validation(gewerk_id="blitzschutz", sample=50)
    print(report.summary())
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean, median
import random

from engine.gewerk import Gewerk, get_gewerk
from engine.pricing_engine import PricingEngine


@dataclass
class ValidationItem:
    anlage_reference: str
    calculated_price: float
    expected_price: float
    delta_pct: float
    within_5pct: bool
    within_10pct: bool
    within_20pct: bool


@dataclass
class ValidationReport:
    gewerk_id: str
    sample_size: int
    total_tested: int
    match_5pct: int
    match_10pct: int
    match_20pct: int
    avg_delta_pct: float
    median_delta_pct: float
    outliers: list[ValidationItem] = field(default_factory=list)

    @property
    def match_rate_5(self) -> float:
        return self.match_5pct / self.total_tested if self.total_tested else 0.0

    @property
    def match_rate_10(self) -> float:
        return self.match_10pct / self.total_tested if self.total_tested else 0.0

    @property
    def match_rate_20(self) -> float:
        return self.match_20pct / self.total_tested if self.total_tested else 0.0

    def summary(self) -> str:
        return (
            f"[{self.gewerk_id}] n={self.total_tested} · "
            f"±5%: {self.match_rate_5:.0%} · "
            f"±10%: {self.match_rate_10:.0%} · "
            f"±20%: {self.match_rate_20:.0%} · "
            f"avg Δ: {self.avg_delta_pct:.1f}% · "
            f"median Δ: {self.median_delta_pct:.1f}%"
        )


def run_validation(
    gewerk_id: str,
    sample: int | None = None,
    outlier_threshold_pct: float = 20.0,
) -> ValidationReport:
    """Walidacja Gewerk przeciwko golden set."""
    gewerk = get_gewerk(gewerk_id)
    engine = PricingEngine()
    golden = gewerk.golden_set()

    if sample and len(golden) > sample:
        golden = random.sample(golden, sample)

    items: list[ValidationItem] = []
    deltas: list[float] = []

    for (merkmale, expected_price, reference) in golden:
        try:
            angebot = engine.calculate(gewerk, merkmale)
            calc = angebot.total
        except Exception as e:
            # Count as miss (outlier)
            items.append(ValidationItem(
                anlage_reference=reference,
                calculated_price=0.0,
                expected_price=expected_price,
                delta_pct=float("inf"),
                within_5pct=False, within_10pct=False, within_20pct=False,
            ))
            continue

        delta_pct = 0.0 if expected_price == 0 else abs(calc - expected_price) / expected_price * 100
        deltas.append(delta_pct)

        items.append(ValidationItem(
            anlage_reference=reference,
            calculated_price=calc,
            expected_price=expected_price,
            delta_pct=delta_pct,
            within_5pct=delta_pct <= 5,
            within_10pct=delta_pct <= 10,
            within_20pct=delta_pct <= 20,
        ))

    outliers = sorted(
        [i for i in items if i.delta_pct > outlier_threshold_pct],
        key=lambda i: -i.delta_pct,
    )[:10]

    return ValidationReport(
        gewerk_id=gewerk_id,
        sample_size=sample or len(items),
        total_tested=len(items),
        match_5pct=sum(1 for i in items if i.within_5pct),
        match_10pct=sum(1 for i in items if i.within_10pct),
        match_20pct=sum(1 for i in items if i.within_20pct),
        avg_delta_pct=mean(deltas) if deltas else 0.0,
        median_delta_pct=median(deltas) if deltas else 0.0,
        outliers=outliers,
    )
