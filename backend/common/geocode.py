"""Geocoding via Nominatim (OSM) z dwupoziomowym cache.

Dla każdego adresu (ort + plz + strasse) zwraca (lat, lon) lub None.
Cache: in-memory + disk (JSON) — Nominatim ma rate-limit 1 req/s i wymaga User-Agent.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Optional

import requests

_CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache"
_CACHE_FILE = _CACHE_DIR / "geocode.json"
_LOCK = threading.Lock()
_LAST_CALL = 0.0
_MIN_INTERVAL = 1.1  # Nominatim ToS: max 1 req/s

# Warm cache dla najczęstszych miast TÜV SÜD IS Süd (natychmiastowa odpowiedź, bez HTTP).
_WARM_CACHE: dict[str, tuple[float, float]] = {
    "muenchen": (48.1351, 11.5075), "münchen": (48.1351, 11.5075), "munich": (48.1351, 11.5075),
    "nuernberg": (49.4521, 11.0767), "nürnberg": (49.4521, 11.0767),
    "augsburg": (48.3668, 10.8865),
    "wuerzburg": (49.7913, 9.9534), "würzburg": (49.7913, 9.9534),
    "regensburg": (49.0134, 12.1016),
    "hamburg": (53.5511, 9.9937),
    "berlin": (52.52, 13.3349),
    "leipzig": (51.3397, 12.3731),
    "mannheim": (49.4875, 8.466),
    "essen": (51.4556, 7.0116),
    "stuttgart": (48.6636, 9.2176),
    "frankfurt": (50.1109, 8.6821),
    "koeln": (50.9375, 6.9603), "köln": (50.9375, 6.9603),
    "duesseldorf": (51.2277, 6.7735), "düsseldorf": (51.2277, 6.7735),
    "bremen": (53.0793, 8.8017),
    "hannover": (52.3759, 9.732),
    "dresden": (51.0504, 13.7373),
}

_disk_cache: dict[str, tuple[float, float]] | None = None


def _load_disk_cache() -> dict[str, tuple[float, float]]:
    global _disk_cache
    if _disk_cache is not None:
        return _disk_cache
    if _CACHE_FILE.exists():
        try:
            raw = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
            _disk_cache = {k: tuple(v) for k, v in raw.items()}
        except Exception:
            _disk_cache = {}
    else:
        _disk_cache = {}
    return _disk_cache


def _save_disk_cache() -> None:
    if _disk_cache is None:
        return
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _CACHE_FILE.write_text(
        json.dumps({k: list(v) for k, v in _disk_cache.items()}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _cache_key(ort: str, plz: Optional[str], strasse: Optional[str]) -> str:
    parts = [p.strip().lower() for p in (strasse or "", plz or "", ort) if p and p.strip()]
    return "|".join(parts)


def _nominatim_request(params: dict) -> Optional[tuple[float, float]]:
    """Rate-limited Nominatim GET."""
    global _LAST_CALL
    with _LOCK:
        wait = _MIN_INTERVAL - (time.time() - _LAST_CALL)
        if wait > 0:
            time.sleep(wait)
        _LAST_CALL = time.time()

    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={**params, "format": "json", "limit": 1},
            headers={"User-Agent": "SmartCal-TÜV/1.0 (piotr@minglabs)"},
            timeout=6,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        if not data:
            return None
        return (float(data[0]["lat"]), float(data[0]["lon"]))
    except Exception:
        return None


def _nominatim_lookup(ort: str, plz: Optional[str], strasse: Optional[str]) -> Optional[tuple[float, float]]:
    """Szuka na Nominatim: najpierw structured bez country (globalnie), potem freeform fallback.

    Bez hard-coded country — TÜV obsługuje także klientów w PL/AT/CH/NL.
    Nominatim ranking daje top-result zwykle poprawnie (największe miasto o tej nazwie).
    """
    structured = {"city": ort}
    if plz:
        structured["postalcode"] = plz
    if strasse:
        structured["street"] = strasse

    hit = _nominatim_request(structured)
    if hit:
        return hit

    # Fallback 1: structured bez straße (czasem jej nie ma w OSM)
    if strasse:
        hit = _nominatim_request({"city": ort, **({"postalcode": plz} if plz else {})})
        if hit:
            return hit

    # Fallback 2: freeform q=<wszystkie komponenty>
    q = " ".join(p for p in (strasse, plz, ort) if p)
    return _nominatim_request({"q": q})


def geocode(
    ort: Optional[str],
    plz: Optional[str] = None,
    strasse: Optional[str] = None,
) -> Optional[tuple[float, float]]:
    """Zwróć (lat, lon) dla adresu lub None.

    Kolejność: warm cache (miasto) → disk cache → Nominatim → disk fallback.
    """
    if not ort or not ort.strip():
        return None

    ort_key = ort.strip().lower()

    if not plz and not strasse:
        hit = _WARM_CACHE.get(ort_key)
        if hit:
            return hit

    disk = _load_disk_cache()
    key = _cache_key(ort, plz, strasse)
    hit = disk.get(key)
    if hit:
        return hit

    coords = _nominatim_lookup(ort.strip(), plz, strasse)
    if coords:
        disk[key] = coords
        _save_disk_cache()
        return coords

    if ort_key in _WARM_CACHE:
        return _WARM_CACHE[ort_key]

    return None
