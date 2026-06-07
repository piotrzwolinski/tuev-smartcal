"""DGUV V3 Kalibrierungsschicht — multi-source pricing calibration.

Each Kalibrierungspunkt has full provenance (_quelle, _typ, _gewicht).
Weighted aggregation produces calibrated rates + confidence bands.
"""

from dataclasses import dataclass, field
from enum import Enum


class QuellenTyp(str, Enum):
    REGEL = "regel"
    AUSSCHREIBUNG = "ausschreibung"
    GROSSKUNDE = "grosskunde"
    FAKTURA = "faktura"
    STATISTIK = "statistik"
    FACHEXPERTE = "fachexperte"


QUELLEN_GEWICHT = {
    QuellenTyp.REGEL: 1.0,
    QuellenTyp.AUSSCHREIBUNG: 0.85,
    QuellenTyp.GROSSKUNDE: 0.7,
    QuellenTyp.FAKTURA: 0.9,
    QuellenTyp.STATISTIK: 0.6,
    QuellenTyp.FACHEXPERTE: 0.8,
}


@dataclass
class Kalibrierungspunkt:
    id: str
    gebaeudetyp: str
    preis: float
    pruefgrundlage: str
    flaeche_m2: float | None = None
    installationskategorie: int = 2
    anzahl_uv: int | None = None
    quelle: str = ""
    typ: QuellenTyp = QuellenTyp.REGEL
    gewicht: float | None = None
    stand: str = ""

    @property
    def effective_gewicht(self) -> float:
        if self.gewicht is not None:
            return self.gewicht
        return QUELLEN_GEWICHT.get(self.typ, 0.5)

    @property
    def implied_rate_10m2(self) -> float | None:
        if self.flaeche_m2 is None or self.flaeche_m2 <= 0:
            return None
        pruef_only = self.preis - 250.0
        if pruef_only <= 0:
            return None
        return round(pruef_only / (self.flaeche_m2 / 10.0), 2)

    @property
    def implied_rate_per_uv(self) -> float | None:
        if self.anzahl_uv is None or self.anzahl_uv <= 0:
            return None
        return round(self.preis / self.anzahl_uv, 2)

    def to_graph_properties(self) -> dict:
        props = {
            "id": self.id,
            "gebaeudetyp": self.gebaeudetyp,
            "preis": self.preis,
            "pruefgrundlage": self.pruefgrundlage,
            "installationskategorie": self.installationskategorie,
            "_quelle": self.quelle,
            "_typ": self.typ.value,
            "_gewicht": self.effective_gewicht,
            "_stand": self.stand,
        }
        if self.flaeche_m2 is not None:
            props["flaeche_m2"] = self.flaeche_m2
        if self.anzahl_uv is not None:
            props["anzahl_uv"] = self.anzahl_uv
        if self.implied_rate_10m2 is not None:
            props["implied_rate_10m2"] = self.implied_rate_10m2
        if self.implied_rate_per_uv is not None:
            props["implied_rate_per_uv"] = self.implied_rate_per_uv
        return props


@dataclass
class KalibrierungResult:
    basis_rate: float
    kalibriert_rate: float
    range_min: float
    range_max: float
    confidence: float
    quellen: list[dict] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════
# DEKA ground truth — 3 Bürogebäude München (M. Pfeiffer 01.06)
# ═══════════════════════════════════════════════════════════════

DEKA_PUNKTE = [
    Kalibrierungspunkt(
        id="KP_DEKA_BARTH",
        gebaeudetyp="Bürogebäude",
        flaeche_m2=8000,
        preis=9733.0,
        pruefgrundlage="VdS",
        installationskategorie=2,
        anzahl_uv=51,
        quelle="DEKA Preismatrix Barthstr 12-22 (EQ 3268262)",
        typ=QuellenTyp.GROSSKUNDE,
        stand="2026-06-01",
    ),
    Kalibrierungspunkt(
        id="KP_DEKA_L84",
        gebaeudetyp="Bürogebäude",
        flaeche_m2=12000,
        preis=15078.0,
        pruefgrundlage="kombiniert",
        installationskategorie=2,
        anzahl_uv=61,
        quelle="DEKA Preismatrix Landsberger 84-90 (EQ 3256171)",
        typ=QuellenTyp.GROSSKUNDE,
        stand="2026-06-01",
    ),
    Kalibrierungspunkt(
        id="KP_DEKA_L94",
        gebaeudetyp="Bürogebäude",
        flaeche_m2=4000,
        preis=5255.0,
        pruefgrundlage="DGUV",
        installationskategorie=2,
        anzahl_uv=25,
        quelle="DEKA Preismatrix Landsberger 94-98 (EQ 3256175)",
        typ=QuellenTyp.GROSSKUNDE,
        stand="2026-06-01",
    ),
]

# ═══════════════════════════════════════════════════════════════
# Gersthofen ground truth — Ausschreibung 2025 (25 Gebäude)
# Only UV counts, no m² — can compute €/UV but not €/m²
# ═══════════════════════════════════════════════════════════════

GERSTHOFEN_PUNKTE = [
    Kalibrierungspunkt(
        id="KP_GERST_RATHAUS", gebaeudetyp="Verwaltungsgebäude",
        preis=7996.0, pruefgrundlage="DGUV", anzahl_uv=24,
        quelle="Ausschreibung Gersthofen 2025 — Rathaus",
        typ=QuellenTyp.AUSSCHREIBUNG, stand="2025",
    ),
    Kalibrierungspunkt(
        id="KP_GERST_PESTALOZZI", gebaeudetyp="Schule",
        preis=3992.80, pruefgrundlage="DGUV", anzahl_uv=10,
        quelle="Ausschreibung Gersthofen 2025 — Pestalozzischule",
        typ=QuellenTyp.AUSSCHREIBUNG, stand="2025",
    ),
    Kalibrierungspunkt(
        id="KP_GERST_ANNAPROLL", gebaeudetyp="Schule",
        preis=5386.0, pruefgrundlage="DGUV", anzahl_uv=14,
        quelle="Ausschreibung Gersthofen 2025 — Anna-Pröll-Mittelschule",
        typ=QuellenTyp.AUSSCHREIBUNG, stand="2025",
    ),
    Kalibrierungspunkt(
        id="KP_GERST_MUSEUM", gebaeudetyp="Museum",
        preis=3627.20, pruefgrundlage="DGUV", anzahl_uv=9,
        quelle="Ausschreibung Gersthofen 2025 — Ballonmuseum/Bücherei",
        typ=QuellenTyp.AUSSCHREIBUNG, stand="2025",
    ),
]

ALL_PUNKTE = DEKA_PUNKTE + GERSTHOFEN_PUNKTE


def kalibriere_rate(
    basis_rate: float,
    punkte: list[Kalibrierungspunkt],
) -> KalibrierungResult:
    relevant = [p for p in punkte if p.implied_rate_10m2 is not None]

    quellen = [{"name": "Kalkulationshilfen NBG", "typ": "regel", "rate": basis_rate, "gewicht": 1.0}]

    if not relevant:
        return KalibrierungResult(
            basis_rate=basis_rate,
            kalibriert_rate=basis_rate,
            range_min=basis_rate,
            range_max=basis_rate,
            confidence=0.5,
            quellen=quellen,
        )

    for p in relevant:
        quellen.append({
            "name": p.quelle,
            "typ": p.typ.value,
            "rate": p.implied_rate_10m2,
            "gewicht": p.effective_gewicht,
        })

    total_weight = 1.0 + sum(p.effective_gewicht for p in relevant)
    kalibriert = (basis_rate * 1.0 + sum(p.implied_rate_10m2 * p.effective_gewicht for p in relevant)) / total_weight

    all_rates = [basis_rate] + [p.implied_rate_10m2 for p in relevant]
    range_min = min(all_rates)
    range_max = max(all_rates)

    spread = (range_max - range_min) / max(kalibriert, 1.0)
    n_sources = 1 + len(relevant)
    agreement_factor = max(0.3, 1.0 - spread)
    volume_factor = min(1.0, 0.5 + n_sources * 0.1)
    confidence = round(min(1.0, agreement_factor * volume_factor), 2)

    return KalibrierungResult(
        basis_rate=basis_rate,
        kalibriert_rate=round(kalibriert, 2),
        range_min=round(range_min, 2),
        range_max=round(range_max, 2),
        confidence=confidence,
        quellen=quellen,
    )


def get_kalibrierung_for_trace(
    basis_rate: float,
    gebaeudetyp: str | None = None,
    pruefgrundlage: str | None = None,
) -> KalibrierungResult:
    punkte = ALL_PUNKTE
    if gebaeudetyp:
        gt_lower = gebaeudetyp.lower()
        filtered = [p for p in punkte if gt_lower in p.gebaeudetyp.lower()]
        if filtered:
            punkte = filtered
    if pruefgrundlage:
        pg_lower = pruefgrundlage.lower()
        filtered = [p for p in punkte if pg_lower in p.pruefgrundlage.lower()]
        if filtered:
            punkte = filtered
    return kalibriere_rate(basis_rate, punkte)
