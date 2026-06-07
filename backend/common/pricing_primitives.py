"""LPV Teil A shared pricing primitives.

Wspólne dla wszystkich Gewerke (Blitzschutz, RLT, DGUV V3, etc.):
- Stundensätze (Innendienst / Außendienst / Reise)
- Reisekosten (km + Tagegeld)
- Berichterstellung (Pauschalen)
- Zuschläge (Vereinsmitglied, Eilzuschlag, Sondertermin)

Źródło: LPV 2025/2026 Teil A, §4–§11 (PDF w ~/Desktop/TUEV/LP_00_2026_Gesamt (1).pdf)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Literal


# ──────────────────────────────────────────────────────────────
# Stundensätze (LPV Teil A §4.2)
# ──────────────────────────────────────────────────────────────

STUNDENSATZ_EINFACH = 180.00       # einfache Sachverhalte
STUNDENSATZ_SCHWIERIG = 208.00     # schwierige Sachverhalte
STUNDENSATZ_KOMPLEX = 239.00       # komplexe Sachverhalte
STUNDENSATZ_BESONDERS = 265.00     # besondere Sachverhalte
STUNDENSATZ_SYSTEMANALYSE = 320.00 # Systemanalysen

StundensatzLevel = Literal["einfach", "schwierig", "komplex", "besonders", "systemanalyse"]

_STUNDENSATZ = {
    "einfach": STUNDENSATZ_EINFACH,
    "schwierig": STUNDENSATZ_SCHWIERIG,
    "komplex": STUNDENSATZ_KOMPLEX,
    "besonders": STUNDENSATZ_BESONDERS,
    "systemanalyse": STUNDENSATZ_SYSTEMANALYSE,
}


def stundensatz(level: StundensatzLevel = "einfach") -> float:
    return _STUNDENSATZ[level]


# ──────────────────────────────────────────────────────────────
# Reisekosten (LPV Teil A §4.3)
# ──────────────────────────────────────────────────────────────

KILOMETERGELD_PKW = 1.10
KILOMETERGELD_LKW = 1.20


def kilometergeld(km: float, vehicle: Literal["pkw", "lkw"] = "pkw") -> float:
    rate = KILOMETERGELD_PKW if vehicle == "pkw" else KILOMETERGELD_LKW
    return km * rate


def tagegeld(hours: float) -> float:
    """LPV Teil A §4.3: 6€ (6-8h) / 25€ (8-14h) / 30€ (14-24h)."""
    if hours < 6:
        return 0.0
    if hours < 8:
        return 6.00
    if hours < 14:
        return 25.00
    return 30.00


# ──────────────────────────────────────────────────────────────
# Grundkosten (shared across Gewerke)
# ──────────────────────────────────────────────────────────────

GRUNDKOSTEN_AUFTRAGSVERWALTUNG = 256.00  # Pauschale Auftragsanlage/Verwaltung
GRUNDKOSTEN_ORDNUNGSPRUEFUNG = 242.00    # nur baurechtlich
PRUEFMITTEL_PRO_TAG_SV = 49.00           # Energie + Prüfmittelpauschale


def grundkosten_pauschal(include_ordnungspruefung: bool = False) -> float:
    base = GRUNDKOSTEN_AUFTRAGSVERWALTUNG
    if include_ordnungspruefung:
        base += GRUNDKOSTEN_ORDNUNGSPRUEFUNG
    return base


# ──────────────────────────────────────────────────────────────
# Berichterstellung (LPV Teil A §5)
# ──────────────────────────────────────────────────────────────

BERICHT_KLEIN = 119.00      # Kleine Anlagen
BERICHT_STANDARD = 380.00   # ≤10 Seiten
BERICHT_KOMPLEX = 550.00    # Komplex


class BerichtTyp(str, Enum):
    KLEIN = "klein"
    STANDARD = "standard"
    KOMPLEX = "komplex"


_BERICHT_PREIS = {
    BerichtTyp.KLEIN: BERICHT_KLEIN,
    BerichtTyp.STANDARD: BERICHT_STANDARD,
    BerichtTyp.KOMPLEX: BERICHT_KOMPLEX,
}


def berichtskosten(typ: BerichtTyp) -> float:
    return _BERICHT_PREIS[typ]


# ──────────────────────────────────────────────────────────────
# Zuschläge (LPV Teil A §11, §12, §13)
# ──────────────────────────────────────────────────────────────

ZUSCHLAG_NICHT_VEREINSMITGLIED = 0.20  # +20% (Audi-logic)
ZUSCHLAG_EINZELPRUEFUNG = 0.20          # bis +20% (ohne Rahmenvertrag)
ZUSCHLAG_ERSTPRUEFUNG = 1.00            # bis +100% (Erstprüfung vs WP)
ZUSCHLAG_EILZUSCHLAG = 0.25             # bis +25% (Sondertermin)
ZUSCHLAG_EILZUSCHLAG_MAX = 1.00         # bis +100% (bevorzugt)
ZUSCHLAG_AUSSERHALB_DIENSTZEIT = 1.00   # bis +100% (außerhalb normaler Dienstzeit)


@dataclass
class Zuschlag:
    name: str
    percent: float
    reason: str = ""


# ──────────────────────────────────────────────────────────────
# TÜV SÜD IS Niederlassungen (z Veit-Mail + LPV Teil C)
# ──────────────────────────────────────────────────────────────

# Źródło: E-Mail Stefan Veit (IS-EG1-AUG/SV), 14.08.2025 — dokładne adresy
# Koordynaty: geocoded z adresów (Google Maps precision)
TUEV_NIEDERLASSUNGEN = [
    {"id": "AUG", "name": "Augsburg", "plz": "86199", "adresse": "Oskar-von-Miller-Straße 17", "lat": 48.3543, "lon": 10.8735},
    {"id": "BER", "name": "Berlin", "plz": "13509", "adresse": "Wittestraße 30, Haus LM", "lat": 52.5785, "lon": 13.3195},
    {"id": "DAR", "name": "Darmstadt", "plz": "64285", "adresse": "Rüdesheimer Straße 119", "lat": 49.8590, "lon": 8.6365},
    {"id": "DRE", "name": "Dresden", "plz": "01159", "adresse": "Drescherhäuser 5 D", "lat": 51.0580, "lon": 13.6940},
    {"id": "ESS", "name": "Essen", "plz": "45145", "adresse": "Kruppstraße 82-100", "lat": 51.4470, "lon": 6.9880},
    {"id": "FIL", "name": "Filderstadt", "plz": "70794", "adresse": "Gottlieb-Daimler-Straße 7", "lat": 48.6560, "lon": 9.2200},
    {"id": "FRE", "name": "Freiburg", "plz": "79108", "adresse": "Hermann-Mitsch-Straße 36 A", "lat": 48.0200, "lon": 7.8340},
    {"id": "HAM", "name": "Hamburg", "plz": "22525", "adresse": "Syltsterstraße 2", "lat": 53.5740, "lon": 9.9270},
    {"id": "HAN", "name": "Hannover", "plz": "30419", "adresse": "Göttinger Landstraße 10", "lat": 52.3870, "lon": 9.7100},
    {"id": "HEI", "name": "Heilbronn", "plz": "74076", "adresse": "Heiner-Daimler-Straße 9", "lat": 49.1380, "lon": 9.2230},
    {"id": "HOF", "name": "Hof", "plz": "95032", "adresse": "Erfreudenstraße 75", "lat": 50.3100, "lon": 11.9250},
    {"id": "KAR", "name": "Karlsruhe", "plz": "76199", "adresse": "Am Rüppurer Schloß 1", "lat": 48.9870, "lon": 8.3990},
    {"id": "LEI", "name": "Leipzig", "plz": "04159", "adresse": "Weserstraße 2", "lat": 51.3680, "lon": 12.3410},
    {"id": "MAN", "name": "Mannheim", "plz": "68167", "adresse": "Dudenstraße 28", "lat": 49.4930, "lon": 8.4800},
    {"id": "MUC", "name": "München", "plz": "80686", "adresse": "Westendstraße 199", "lat": 48.1420, "lon": 11.5170},
    {"id": "NBG", "name": "Nürnberg", "plz": "90431", "adresse": "Edisonstraße 15", "lat": 49.4440, "lon": 11.0250},
    {"id": "RAV", "name": "Ravensburg", "plz": "88214", "adresse": "Rudolfstraße 15", "lat": 47.7820, "lon": 9.6120},
    {"id": "RGB", "name": "Regensburg", "plz": "93051", "adresse": "Friedenstraße 6", "lat": 49.0100, "lon": 12.0840},
    {"id": "ROS", "name": "Rostock", "plz": "18069", "adresse": "Krusensternweg 2", "lat": 54.0810, "lon": 12.1070},
    {"id": "SBR", "name": "St. Ingbert", "plz": "66386", "adresse": "Am Alten Forsthaus 1", "lat": 49.2770, "lon": 7.1150},
    {"id": "TRT", "name": "Trostberg", "plz": "83308", "adresse": "Gabelsbergerstraße 5", "lat": 48.0260, "lon": 12.5450},
    {"id": "ULM", "name": "Ulm", "plz": "89079", "adresse": "Berlinger Straße 17", "lat": 48.3780, "lon": 9.9590},
    {"id": "WZB", "name": "Würzburg", "plz": "97080", "adresse": "Petrinstraße 33 A", "lat": 49.7830, "lon": 9.9400},
]


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine (Luftlinie) — fallback gdy OSRM nicht erreichbar."""
    from math import radians, sin, cos, asin, sqrt
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * 6371 * asin(sqrt(a))


def _osrm_route(lat1: float, lon1: float, lat2: float, lon2: float) -> dict | None:
    """OSRM driving distance + duration (free, no API key).

    Returns: {"distance_km": float, "duration_min": float} or None on failure.
    Veit-Spec: Fahrstrecke, nicht Luftlinie.
    """
    try:
        import requests
        url = (
            f"http://router.project-osrm.org/route/v1/driving/"
            f"{lon1},{lat1};{lon2},{lat2}?overview=false"
        )
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            route = r.json()["routes"][0]
            return {
                "distance_km": route["distance"] / 1000,
                "duration_min": route["duration"] / 60,
            }
    except Exception:
        pass
    return None


_CRM_TO_STANDORT_ID = {
    "0AUG": "AUG", "0BER": "BER", "0DRE": "DRE", "0ESS": "ESS",
    "0FRE": "FRE", "0HAM": "HAM", "0HOF": "HOF", "0KAR": "KAR",
    "0LEI": "LEI", "0MAN": "MAN", "0MUC": "MUC", "0NBG": "NBG",
    "0RAV": "RAV", "0RGB": "RGB", "0SBR": "SBR", "0TRT": "TRT",
    "0ULM": "ULM", "0WZB": "WZB",
    "0STG": "FIL",  # Stuttgart-Filderstadt → Filderstadt
    "0HBR": "HEI",  # Heilbronn CRM code
    "0CHE": "DRE",  # Chemnitz → Dresden (closest we have)
    "0JEN": "LEI",  # Jena → Leipzig (closest we have)
    "0KLT": "SBR",  # Kaiserslautern → St. Ingbert (closest we have)
    # HESE = TÜV Hessen (separate company) → no mapping, fallback to nearest
}

_STANDORT_BY_ID = {s["id"]: s for s in TUEV_NIEDERLASSUNGEN}

_PLZ_NL_CACHE: dict[str, str | None] = {}
_PLZ_NL_LOADED = False


def _load_plz_nl():
    global _PLZ_NL_LOADED
    if _PLZ_NL_LOADED:
        return
    _PLZ_NL_LOADED = True
    from pathlib import Path
    import json as _json

    json_path = Path(__file__).parent.parent / "data" / "plz_nl_crm.json"
    if not json_path.exists():
        return
    try:
        with open(json_path) as f:
            plz_nl_raw = _json.load(f)
        for plz, crm_nl in plz_nl_raw.items():
            standort_id = _CRM_TO_STANDORT_ID.get(crm_nl)
            _PLZ_NL_CACHE[plz] = standort_id  # None for HESE etc.
    except Exception:
        pass


def _find_by_plz(plz: str) -> dict | None:
    """CRM PLZ→NL lookup. Returns Standort dict or None."""
    _load_plz_nl()
    plz_norm = plz.strip().zfill(5)
    if plz_norm not in _PLZ_NL_CACHE:
        return None
    standort_id = _PLZ_NL_CACHE[plz_norm]
    if standort_id is None:
        return None  # HESE etc. — no TÜV SÜD NL
    return _STANDORT_BY_ID.get(standort_id)


def _route_to_standort(lat: float, lon: float, standort: dict) -> dict:
    """Calculate route from (lat, lon) to a specific Standort."""
    route = _osrm_route(lat, lon, standort["lat"], standort["lon"])
    if route:
        return {**standort, "distance_km": route["distance_km"],
                "duration_min": route["duration_min"], "routing": "osrm"}
    km = _haversine_km(lat, lon, standort["lat"], standort["lon"])
    return {**standort, "distance_km": km, "duration_min": km / 80 * 60,
            "routing": "haversine_fallback"}


def find_nearest_standort(lat: float, lon: float, plz: str | None = None) -> dict:
    """Return zuständige TÜV Niederlassung with Fahrstrecke.

    Priority: CRM PLZ→NL mapping → fallback to nearest by distance.
    If CRM maps to unknown NL (e.g. TÜV Hessen), falls back with warning.
    """
    # 1. Try CRM lookup
    if plz:
        crm_standort = _find_by_plz(plz)
        if crm_standort:
            result = _route_to_standort(lat, lon, crm_standort)
            result["zuordnung"] = "crm"
            return result

        # PLZ exists in CRM but maps to non-TÜV-SÜD NL
        _load_plz_nl()
        plz_norm = plz.strip().zfill(5)
        if plz_norm in _PLZ_NL_CACHE and _PLZ_NL_CACHE[plz_norm] is None:
            # Fallback to nearest, but flag it
            result = _find_nearest_by_distance(lat, lon)
            result["zuordnung"] = "fallback"
            result["zuordnung_warnung"] = (
                f"PLZ {plz} ist lt. CRM nicht im TÜV SÜD IS-Gebiet "
                f"(ggf. TÜV Hessen oder andere Gesellschaft). "
                f"Nächster TÜV SÜD Standort als Fallback verwendet."
            )
            return result

    # 2. Fallback: nearest by distance
    result = _find_nearest_by_distance(lat, lon)
    result["zuordnung"] = "nearest"
    return result


def _find_nearest_by_distance(lat: float, lon: float) -> dict:
    candidates = sorted(
        TUEV_NIEDERLASSUNGEN,
        key=lambda s: _haversine_km(lat, lon, s["lat"], s["lon"]),
    )[:3]

    best = None
    best_km = float("inf")
    for c in candidates:
        entry = _route_to_standort(lat, lon, c)
        if entry["distance_km"] < best_km:
            best_km = entry["distance_km"]
            best = entry

    return best or {**candidates[0], "distance_km": 0, "routing": "error"}
