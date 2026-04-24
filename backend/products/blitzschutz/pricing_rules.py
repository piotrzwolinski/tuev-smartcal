"""Blitzschutz pricing rules — LPV B04 §8.1 (Äußerer Blitzschutz).

Primary cost driver: Anzahl Messstellen × 33€ (bis 10 MS).
Powyżej 10 MS: "besondere Vereinbarung" — w Phase 1 implementujemy Staffeln heurystyczne,
walidujemy przeciwko 325 Anlagen w Blitzschutz_StV.xlsx w M2.4.
"""

from products.blitzschutz.merkmale import (
    BlitzschutzMerkmale,
    Schutzklasse,
    GebaeudeNutzung,
)
from common.pricing_primitives import (
    ZUSCHLAG_NICHT_VEREINSMITGLIED,
    ZUSCHLAG_EILZUSCHLAG,
    ZUSCHLAG_ERSTPRUEFUNG,
)


# ──────────────────────────────────────────────────────────────
# LPV B04 §8.1 — Äußerer Blitzschutz
# ──────────────────────────────────────────────────────────────

PREIS_PRO_MESSSTELLE = 33.00   # €/Stück (LPV B04 §8.1)
SCHWELLE_VEREINBARUNG = 10     # > 10 MS = individuell

# Staffeln heurystyczne (do walidacji na StV 325 Anlagen)
# Idea: powyżej 10 MS staje się "komplex", cena per-MS maleje nieco
STAFFEL = [
    # (min_ms, max_ms, preis_pro_ms_ueber_schwelle)
    (11, 20, 30.00),
    (21, 40, 28.00),
    (41, 100, 26.00),
    (101, 500, 24.00),
]


def blitz_pruefkosten(m: BlitzschutzMerkmale) -> float:
    """Prüfkosten = sum(MS × preis_pro_ms) wg Staffeln."""
    n = m.anzahl_ableitungen

    if n <= SCHWELLE_VEREINBARUNG:
        return n * PREIS_PRO_MESSSTELLE

    # Base: 10 pierwszych MS × 33€
    cost = SCHWELLE_VEREINBARUNG * PREIS_PRO_MESSSTELLE
    remaining = n - SCHWELLE_VEREINBARUNG

    for (start, end, rate) in STAFFEL:
        if remaining <= 0:
            break
        band_size = end - start + 1
        in_band = min(remaining, band_size)
        cost += in_band * rate
        remaining -= in_band

    return cost


def blitz_estimate_pruef_tage(m: BlitzschutzMerkmale) -> float:
    """Ile Prüftage wg Anzahl Messstellen.

    Heurystyka z 99 Berichte EG Nürnberg Q1/2025:
    ~15 Messstellen/dzień dla średniego obiektu.
    """
    n = m.anzahl_ableitungen
    if n <= 10:
        return 0.5
    if n <= 30:
        return 1.0
    if n <= 60:
        return 2.0
    if n <= 100:
        return 3.0
    return max(3.0, n / 40)  # duże obiekty: 40 MS/dzień


def blitz_choose_bericht_typ(m: BlitzschutzMerkmale) -> str:
    """LPV Teil A §5: klein (≤10 MS) / standard (≤40 MS) / komplex (>40 MS)."""
    n = m.anzahl_ableitungen
    if n <= 10:
        return "klein"
    if n <= 40:
        return "standard"
    return "komplex"


def blitz_zuschlaege(m: BlitzschutzMerkmale) -> list[tuple[str, float]]:
    """Zuschläge per LPV Teil A §11-§13."""
    z = []
    if not m.vereinsmitglied:
        z.append(("Nicht-Vereinsmitglied (Audi-logic)", ZUSCHLAG_NICHT_VEREINSMITGLIED))
    if m.eilzuschlag:
        z.append(("Eilzuschlag / Sondertermin", ZUSCHLAG_EILZUSCHLAG))
    if m.erstpruefung:
        z.append(("Erstprüfung vs WP", ZUSCHLAG_ERSTPRUEFUNG))
    return z


# ──────────────────────────────────────────────────────────────
# Confidence scoring (Veit-angle Risk Score)
# ──────────────────────────────────────────────────────────────

# Typowe zakresy Anzahl Ableitungen per Gebäudetyp (z 99 Berichte + sampling)
TYPICAL_RANGES = {
    GebaeudeNutzung.SCHULE:      (6, 35),
    GebaeudeNutzung.BUERO:       (6, 28),
    GebaeudeNutzung.INDUSTRIE:   (12, 60),
    GebaeudeNutzung.WOHNUNG:     (3, 12),
    GebaeudeNutzung.HOTEL:       (8, 30),
    GebaeudeNutzung.MUSEUM:      (18, 48),
    GebaeudeNutzung.KRANKENHAUS: (30, 180),
    GebaeudeNutzung.LAGER:       (6, 40),
    GebaeudeNutzung.GARAGE:      (4, 20),
    GebaeudeNutzung.SONSTIGE:    (3, 60),
}

# Typowa Schutzklasse per Gebäudetyp (z 99 Berichte)
TYPICAL_SCHUTZKLASSE = {
    GebaeudeNutzung.KRANKENHAUS: Schutzklasse.II,
    GebaeudeNutzung.MUSEUM:      Schutzklasse.II,
    GebaeudeNutzung.INDUSTRIE:   Schutzklasse.III,
    GebaeudeNutzung.BUERO:       Schutzklasse.III,
    GebaeudeNutzung.SCHULE:      Schutzklasse.III,
    GebaeudeNutzung.HOTEL:       Schutzklasse.III,
    GebaeudeNutzung.WOHNUNG:     Schutzklasse.IV,
    GebaeudeNutzung.LAGER:       Schutzklasse.IV,
}


def blitz_validate_ranges(m: BlitzschutzMerkmale) -> tuple[float, str]:
    """Veit-angle: jeśli Merkmale są nietypowe → flag confidence down.

    Validated 2026-04-16 przeciwko 316 Anlagen Stadtwerke Augsburg StV:
    - LPV-conform dla TS ≤ 15 (Δ <3%)
    - Powyżej 25 TS: real Ausschreibungs-Preis może być 30-50% niższy niż LPV nominal
      (Stadtwerke wyciągnęli agresywny Bieter-rabatt)
    """
    reasons = []
    confidence = 1.0

    # Check Anzahl Ableitungen vs typical range
    lo, hi = TYPICAL_RANGES.get(m.nutzung, (3, 200))
    if m.anzahl_ableitungen < lo:
        confidence *= 0.8
        reasons.append(
            f"Anzahl Ableitungen ({m.anzahl_ableitungen}) niższa niż typowa "
            f"dla {m.nutzung.value} (typisch {lo}-{hi})"
        )
    elif m.anzahl_ableitungen > hi * 1.5:
        confidence *= 0.7
        reasons.append(
            f"Anzahl Ableitungen ({m.anzahl_ableitungen}) znacznie wyższa niż typowa "
            f"dla {m.nutzung.value} (typisch {lo}-{hi}) — edge case?"
        )

    # Check Schutzklasse vs typical
    typical_sk = TYPICAL_SCHUTZKLASSE.get(m.nutzung)
    if m.schutzklasse is None:
        # Sachverständiger nie wypełnił / PDF nie zawiera — fallback do typowej dla Nutzung
        confidence *= 0.75
        fallback = typical_sk.value if typical_sk else "III"
        reasons.append(
            f"Schutzklasse nicht im Bericht — fallback auf typische für {m.nutzung.value} ({fallback})"
        )
    elif typical_sk and m.schutzklasse != typical_sk:
        confidence *= 0.9
        reasons.append(
            f"Schutzklasse {m.schutzklasse.value} nietypowa dla {m.nutzung.value} "
            f"(typisch {typical_sk.value})"
        )

    # Ausschreibung-discount warning (LPV-validated 2026-04-16, n=316 Anlagen Augsburg)
    if m.anzahl_ableitungen > 25:
        confidence *= 0.85
        reasons.append(
            f"⚠ {m.anzahl_ableitungen} Trennstellen >25 — w realnych Ausschreibungen "
            f"(Bieter-Wettbewerb) może obowiązywać rabatt 30-50% vs LPV nominal "
            f"(z Augsburg-StV: ~12-22€/TS zamiast 33€/TS dla dużych obiektów)"
        )

    reason = " · ".join(reasons) if reasons else "Alle Merkmale w typowych zakresach"
    return confidence, reason
