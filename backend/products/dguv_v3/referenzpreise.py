"""Referenzpreis-Lookup per Nutzungstyp — Prio 1 vor NBG Kalkulationshilfen.

v4: Power-law regression aus 367 Augsburg-Gebäuden statt flat €/m².
    price = a × m²^b  (log-log fitted per Nutzungstyp)

S. Pausch Mail 10.06.2026:
"Bitte diese Excel-Tabellen vor der Nürnberger Liste bevorzugen."
"Über Art der Nutzung und den m² bessere Ergebnisse erzielen."

Datenquellen:
- Augsburg: 367 Anlagen mit BGF + DGUV-Preis + VdS-Preis
- Gersthofen: 40 Gebäude mit per-UV Preisaufstellung (validates)
"""

from __future__ import annotations

import math

from products.dguv_v3.merkmale import GebaeudeNutzungDGUV


AUGSBURG_REGRESSION: dict[str, dict] = {
    # max_m2: approximate largest building in training data; beyond → NBG fallback
    "kindergarten": {"a": 122.16, "b": 0.2967, "n": 64, "r2": 0.54, "max_m2": 4000},
    "schule":       {"a": 38.66,  "b": 0.5042, "n": 63, "r2": 0.48, "max_m2": 20000},
    "buerogebaeude":{"a": 7.39,   "b": 0.7346, "n": 22, "r2": 0.91, "max_m2": 15000},
    "verwaltung":   {"a": 28.61,  "b": 0.5470, "n": 6,  "r2": 0.78, "max_m2": 8000},
    "museum_kultur":{"a": 125.82, "b": 0.3128, "n": 16, "r2": 0.57, "max_m2": 5000},
    "sport":        {"a": 139.69, "b": 0.3135, "n": 23, "r2": 0.44, "max_m2": 10000},
    "werkstatt":    {"a": 77.21,  "b": 0.3499, "n": 18, "r2": 0.77, "max_m2": 10000},
    "versorgung":   {"a": 81.51,  "b": 0.3281, "n": 41, "r2": 0.37, "max_m2": 15000},
    "lager":        {"a": 217.59, "b": 0.1950, "n": 19, "r2": 0.37, "max_m2": 5000},
    "versammlungsstaette": {"a": 400.11, "b": 0.1329, "n": 10, "r2": 0.15, "max_m2": 8000},
    "altenheim":    {"a": 13.77,  "b": 0.6385, "n": 8,  "r2": 0.90, "max_m2": 8000},
    "_all":         {"a": 76.22,  "b": 0.3915, "n": 367, "r2": 0.61, "max_m2": 50000},
}


# ── Einzelhandel/Verkaufsstätten: REWE-Rahmenvertrag-Staffel (flat pro m²-Band) ──
# S. Pausch 17.06.2026: "Wir nehmen die REWE-Liste als Referenz für ALLE
# Einzelhandelsprojekte." Quelle: REWE-Liste 2022 (Wiederholungsprüfung).
# Niveau-Caveat: Rahmenvertrag-Preise (RV) liegen unter LPV-Listenpreis;
# > 5.000 m² hat keinen Listenwert → NBG-Fallback.
EINZELHANDEL_STAFFEL_M2: list[tuple[float, float]] = [
    (2000.0, 562.0),    # ≤ 2.000 m²
    (5000.0, 848.0),    # 2.001 – 5.000 m²
]

# Chat-Nutzungsbegriffe, die auf die Einzelhandels-Staffel routen (VdS 0904)
_EINZELHANDEL_CHAT: set[str] = {
    "verkaufsstaette", "verkaufsstätte", "einzelhandel", "supermarkt",
    "discounter", "rewe", "edeka", "aldi", "lidl", "penny", "netto",
    "kaufhaus", "warenhaus", "laden", "markt", "drogerie", "lebensmittelmarkt",
}


def _einzelhandel_staffel(flaeche_m2: float) -> dict | None:
    """REWE-Liste-Staffel (Pausch 17.06): flat pro m²-Band für alle Einzelhandel.
    > 5.000 m² → None (kein Listenwert, Caller nutzt NBG-Fallback)."""
    if flaeche_m2 <= 0:
        return None
    for grenze, preis in EINZELHANDEL_STAFFEL_M2:
        if flaeche_m2 <= grenze:
            return {
                "pruefkosten": preis,
                "quelle": "REWE-Liste (RV)",
                "referenz_typ": "einzelhandel_staffel",
                "eur_per_m2": round(preis / flaeche_m2, 4),
                "n_referenzen": 1,  # Listenpreis (Rahmenvertrag), keine Stichprobe
                "confidence_boost": 1.03,
            }
    return None


_NUTZUNG_TO_REFERENZ: dict[GebaeudeNutzungDGUV, str] = {
    GebaeudeNutzungDGUV.BUEROGEBAEUDE: "buerogebaeude",
    GebaeudeNutzungDGUV.SCHULE: "schule",
    GebaeudeNutzungDGUV.VERSAMMLUNGSSTAETTE: "versammlungsstaette",
    GebaeudeNutzungDGUV.INDUSTRIE: "werkstatt",
    GebaeudeNutzungDGUV.SERVICE_CENTER: "verwaltung",
    GebaeudeNutzungDGUV.SENIORENTREFF: "altenheim",
    # Pausch: Garagen → LPV (NBG fallback)
    # Pausch: Hotels/Möbelhäuser/Baumärkte → TODO, NBG fallback
}

_CHAT_NUTZUNG_TO_REFERENZ: dict[str, str] = {
    "schule": "schule",
    "grundschule": "schule",
    "mittelschule": "schule",
    "gymnasium": "schule",
    "berufsschule": "schule",
    "realschule": "schule",
    "fachoberschule": "schule",
    "wirtschaftsschule": "schule",
    "kindergarten": "kindergarten",
    "kindertagesstaette": "kindergarten",
    "kita": "kindergarten",
    "kinderkrippe": "kindergarten",
    "hort": "kindergarten",
    "kinderhaus": "kindergarten",
    "verwaltung": "verwaltung",
    "rathaus": "verwaltung",
    "amt": "verwaltung",
    "landratsamt": "verwaltung",
    "buerogebaeude": "buerogebaeude",
    "buero": "buerogebaeude",
    "museum": "museum_kultur",
    "bibliothek": "museum_kultur",
    "musikschule": "museum_kultur",
    "kulturamt": "museum_kultur",
    "turnhalle": "sport",
    "sporthalle": "sport",
    "sportstaette": "sport",
    "schwimmbad": "sport",
    "stadion": "sport",
    "eissporthalle": "sport",
    "werkstatt": "werkstatt",
    "bauhof": "werkstatt",
    "betriebshof": "werkstatt",
    "lager": "lager",
    "logistik": "lager",
    "depot": "lager",
    "versammlungsstaette": "versammlungsstaette",
    "stadthalle": "versammlungsstaette",
    "kongress": "versammlungsstaette",
    "kongresshalle": "versammlungsstaette",
    "versorgung": "versorgung",
    "stadtwerke": "versorgung",
    "wasserwerk": "versorgung",
    "klaerwerk": "versorgung",
    "altenheim": "altenheim",
    "seniorenheim": "altenheim",
    "seniorentreff": "altenheim",
}


def _power_law(a: float, b: float, m2: float) -> float:
    if m2 <= 0:
        return 0.0
    return a * math.pow(m2, b)


def lookup_referenzpreis(
    nutzung: GebaeudeNutzungDGUV,
    flaeche_m2: float,
    nutzung_str: str | None = None,
) -> dict | None:
    """Prio-1-Lookup: Referenzpreis via Augsburg power-law regression.

    price = a × m²^b  (per Nutzungstyp, fitted from 367 buildings).
    Returns None if no regression available → caller uses NBG fallback.
    """
    # Prio 0: Einzelhandel/Verkaufsstätten → REWE-Staffel (Pausch 17.06)
    is_retail = nutzung == GebaeudeNutzungDGUV.VERKAUFSSTAETTE
    if not is_retail and nutzung_str:
        is_retail = nutzung_str.lower().strip() in _EINZELHANDEL_CHAT
    if is_retail:
        staffel = _einzelhandel_staffel(flaeche_m2)
        if staffel is not None:
            return staffel
        # > 5.000 m² Einzelhandel → kein Listenwert, weiter zu NBG-Fallback (None)
        return None

    ref_key = None

    if nutzung_str:
        ref_key = _CHAT_NUTZUNG_TO_REFERENZ.get(nutzung_str.lower().strip())

    if ref_key is None:
        ref_key = _NUTZUNG_TO_REFERENZ.get(nutzung)

    if ref_key is None or ref_key not in AUGSBURG_REGRESSION:
        return None

    reg = AUGSBURG_REGRESSION[ref_key]

    if flaeche_m2 > reg.get("max_m2", 50000):
        return None

    pruefkosten = _power_law(reg["a"], reg["b"], flaeche_m2)

    return {
        "pruefkosten": round(pruefkosten, 2),
        "quelle": "Augsburg",
        "referenz_typ": ref_key,
        "eur_per_m2": round(pruefkosten / flaeche_m2, 4) if flaeche_m2 > 0 else 0,
        "n_referenzen": reg["n"],
        "confidence_boost": 1.05 if reg["n"] >= 10 else 1.02,
    }
