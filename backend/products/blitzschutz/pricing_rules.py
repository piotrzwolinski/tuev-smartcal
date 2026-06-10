"""Blitzschutz pricing rules — LPV B04 §8.1 (Äußerer Blitzschutz).

Primary cost driver: Anzahl Messstellen × 33€ (bis 10 MS).
Ab 10 MS: "besondere Vereinbarung" — Phase 1 nutzt heuristische Staffeln,
validiert gegen 325 Anlagen aus Blitzschutz_StV.xlsx (M2.4).
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

# Heuristische Staffeln (zu validieren gegen StV 325 Anlagen)
# Ab 10 MS wird es "komplex", Preis pro MS sinkt leicht
STAFFEL = [
    # (min_ms, max_ms, preis_pro_ms_ueber_schwelle)
    (11, 20, 30.00),
    (21, 40, 28.00),
    (41, 100, 26.00),
    (101, 500, 24.00),
]


BSK_ABSTAND = {
    Schutzklasse.I: 10,
    Schutzklasse.II: 10,
    Schutzklasse.III: 15,
    Schutzklasse.IV: 20,
}


def estimate_ableitungen(m: BlitzschutzMerkmale) -> tuple[int, bool]:
    """Estimate Ableitungen from m² + Schutzklasse when not provided.

    Returns (anzahl, was_estimated).
    """
    if m.anzahl_ableitungen is not None:
        return m.anzahl_ableitungen, False

    if m.gesamtflaeche_m2:
        import math
        side = math.sqrt(m.gesamtflaeche_m2)
        umfang = side * 4
        abstand = BSK_ABSTAND.get(m.schutzklasse, 15)
        estimated = max(4, int(round(umfang / abstand)))
    else:
        lo, hi = TYPICAL_RANGES.get(m.nutzung, (3, 60))
        estimated = (lo + hi) // 2

    return estimated, True


def blitz_pruefkosten(m: BlitzschutzMerkmale) -> float:
    """Prüfkosten = sum(MS × preis_pro_ms) wg Staffeln."""
    n, _ = estimate_ableitungen(m)

    if n <= SCHWELLE_VEREINBARUNG:
        return n * PREIS_PRO_MESSSTELLE

    # Base: erste 10 MS × 33€
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
    """Geschätzte Prüftage nach Anzahl Messstellen.

    Heuristik aus 99 Berichten EG Nürnberg Q1/2025:
    ~15 Messstellen/Tag für durchschnittliches Objekt.
    """
    n, _ = estimate_ableitungen(m)
    if n <= 10:
        return 0.5
    if n <= 30:
        return 1.0
    if n <= 60:
        return 2.0
    if n <= 100:
        return 3.0
    return max(3.0, n / 40)  # große Objekte: 40 MS/Tag


def blitz_choose_bericht_typ(m: BlitzschutzMerkmale) -> str:
    """LPV Teil A §5: klein (≤10 MS) / standard (≤40 MS) / komplex (>40 MS)."""
    n, _ = estimate_ableitungen(m)
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

# Typische Bereiche Anzahl Ableitungen pro Gebäudetyp (aus 99 Berichten + Sampling)
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

# Typische Schutzklasse pro Gebäudetyp (aus 99 Berichten)
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
    """Veit-angle: bei untypischen Merkmalen Confidence senken.

    Validiert 2026-04-16 gegen 316 Anlagen Stadtwerke Augsburg StV:
    - LPV-konform bei TS ≤ 15 (Δ <3%)
    - Ab 25 TS: realer Ausschreibungs-Preis kann 30-50% unter LPV-Nominal liegen
      (Stadtwerke haben aggressiven Bieter-Rabatt durchgesetzt)
    """
    reasons = []
    confidence = 1.0

    n, was_estimated = estimate_ableitungen(m)

    if was_estimated:
        confidence *= 0.65
        reasons.append(
            f"Ableitungen geschätzt ({n}) aus Gebäudefläche/Typ — bitte Anzahl Messstellen angeben für präzisere Kalkulation"
        )

    # Check Anzahl Ableitungen vs typical range
    lo, hi = TYPICAL_RANGES.get(m.nutzung, (3, 200))
    if n < lo:
        confidence *= 0.8
        reasons.append(
            f"Anzahl Ableitungen ({n}) unter dem typischen Bereich "
            f"für {m.nutzung.value} (typisch {lo}-{hi})"
        )
    elif n > hi * 1.5:
        confidence *= 0.7
        reasons.append(
            f"Anzahl Ableitungen ({n}) deutlich über dem typischen Bereich "
            f"für {m.nutzung.value} (typisch {lo}-{hi}) — Sonderfall?"
        )

    # Check Schutzklasse vs typical
    typical_sk = TYPICAL_SCHUTZKLASSE.get(m.nutzung)
    if m.schutzklasse is None:
        confidence *= 0.75
        fallback = typical_sk.value if typical_sk else "III"
        reasons.append(
            f"Schutzklasse nicht im Bericht — fallback auf typische für {m.nutzung.value} ({fallback})"
        )
    elif typical_sk and m.schutzklasse != typical_sk:
        confidence *= 0.9
        reasons.append(
            f"Schutzklasse {m.schutzklasse.value} untypisch für {m.nutzung.value} "
            f"(typisch {typical_sk.value})"
        )

    # Ausschreibung-discount warning (LPV-validated 2026-04-16, n=316 Anlagen Augsburg)
    if n > 25:
        confidence *= 0.85
        reasons.append(
            f"⚠ {n} Trennstellen >25 — in realen Ausschreibungen "
            f"(Bieter-Wettbewerb) kann ein Rabatt von 30-50% vs LPV-Nominal gelten "
            f"(aus Augsburg-StV: ~12-22€/TS statt 33€/TS bei großen Objekten)"
        )

    reason = " · ".join(reasons) if reasons else "Alle Merkmale im typischen Bereich"
    return confidence, reason
