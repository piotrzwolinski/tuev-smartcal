"""Geocoding via Nominatim (OSM) with two-level cache.

For each address (ort + plz + strasse) returns (lat, lon) or None.
Cache: in-memory + disk (JSON) — Nominatim has rate-limit 1 req/s and requires User-Agent.
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

# Warm cache for most common TÜV SÜD IS Süd cities (instant response, no HTTP).
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


_PLZ2_CENTROIDS = {
    "01": (51.05, 13.74), "02": (51.15, 14.97), "03": (51.75, 12.30), "04": (51.34, 12.38),
    "06": (51.48, 11.97), "07": (50.93, 11.59), "08": (50.72, 12.49), "09": (50.83, 12.92),
    "10": (52.52, 13.40), "12": (52.47, 13.43), "13": (52.57, 13.33), "14": (52.39, 13.07),
    "15": (52.35, 14.05), "16": (52.89, 13.29), "17": (53.63, 13.26), "18": (54.08, 12.13),
    "19": (53.63, 11.41), "20": (53.55, 10.00), "21": (53.47, 9.98), "22": (53.57, 10.05),
    "23": (53.87, 10.69), "24": (54.32, 10.14), "25": (53.87, 9.48), "26": (53.15, 8.22),
    "27": (53.08, 8.81), "28": (53.08, 8.81), "29": (52.97, 10.25), "30": (52.37, 9.74),
    "31": (52.16, 9.95), "32": (52.02, 8.53), "33": (51.93, 8.38), "34": (51.32, 9.50),
    "35": (50.81, 8.77), "36": (50.67, 9.68), "37": (51.53, 9.94), "38": (52.26, 10.52),
    "39": (52.13, 11.63), "40": (51.23, 6.78), "41": (51.16, 6.44), "42": (51.27, 7.20),
    "44": (51.51, 7.47), "45": (51.45, 7.01), "46": (51.63, 6.76), "47": (51.43, 6.76),
    "48": (51.96, 7.63), "49": (52.28, 8.04), "50": (50.94, 6.96), "51": (50.93, 7.12),
    "52": (50.78, 6.08), "53": (50.73, 7.10), "54": (49.76, 6.64), "55": (49.99, 8.27),
    "56": (50.36, 7.60), "57": (50.87, 7.95), "58": (51.38, 7.60), "59": (51.66, 7.82),
    "60": (50.11, 8.68), "61": (50.22, 8.62), "63": (50.00, 8.97), "64": (49.87, 8.65),
    "65": (50.08, 8.24), "66": (49.23, 7.00), "67": (49.44, 8.44), "68": (49.49, 8.47),
    "69": (49.41, 8.69), "70": (48.78, 9.18), "71": (48.73, 9.12), "72": (48.49, 9.06),
    "73": (48.62, 9.45), "74": (49.14, 9.22), "75": (48.89, 8.70), "76": (49.00, 8.40),
    "77": (48.45, 8.07), "78": (47.77, 8.93), "79": (47.99, 7.85), "80": (48.14, 11.58),
    "81": (48.12, 11.60), "82": (48.04, 11.49), "83": (47.85, 12.13), "84": (48.44, 12.27),
    "85": (48.40, 11.74), "86": (48.37, 10.90), "87": (47.73, 10.32), "88": (47.66, 9.48),
    "89": (48.40, 10.00), "90": (49.45, 11.08), "91": (49.47, 11.08), "92": (49.42, 11.86),
    "93": (49.01, 12.10), "94": (48.57, 13.45), "95": (50.32, 11.91), "96": (50.09, 10.88),
    "97": (49.79, 9.94), "98": (50.68, 10.93), "99": (50.98, 11.03),
}


def _plz_centroid_fallback(plz: str) -> Optional[tuple[float, float]]:
    """Approximate PLZ location from 2-digit prefix centroids."""
    prefix = plz[:2]
    return _PLZ2_CENTROIDS.get(prefix)


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
    """Nominatim lookup: structured without country (global), then freeform fallback.

    No hard-coded country — TÜV also serves clients in PL/AT/CH/NL.
    Nominatim ranking typically returns the correct top-result (largest city with that name).
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
    """Return (lat, lon) for address or None.

    Order: warm cache (city) → disk cache → Nominatim → disk fallback.
    """
    if not ort or not ort.strip():
        if plz and plz.strip():
            plz_clean = plz.strip().zfill(5)
            hit = _nominatim_request({"postalcode": plz_clean, "country": "de"})
            if hit:
                return hit
            hit = _plz_centroid_fallback(plz_clean)
            if hit:
                return hit
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
