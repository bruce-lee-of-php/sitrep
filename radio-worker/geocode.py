"""Forward geocoding via Nominatim.

Mirrors the reverse-geocode proxy pattern in backend/main.py (httpx + a
User-Agent), but hits the /search endpoint to turn a place phrase into
coordinates. Respects the Nominatim usage policy: a set User-Agent and a
minimum interval between requests (~1/s).
"""
from __future__ import annotations

import time
from typing import Optional, Tuple

import httpx

import config

_last_request_ts = 0.0


def _throttle() -> None:
    global _last_request_ts
    elapsed = time.monotonic() - _last_request_ts
    wait = config.NOMINATIM_MIN_INTERVAL - elapsed
    if wait > 0:
        time.sleep(wait)
    _last_request_ts = time.monotonic()


def geocode(location_text: str) -> Optional[Tuple[float, float]]:
    """Return (lat, lon) for a place phrase, or None if not confidently found."""
    if not location_text or not location_text.strip():
        return None

    query = location_text.strip()
    if config.GEOCODE_REGION_HINT and config.GEOCODE_REGION_HINT.lower() not in query.lower():
        query = f"{query}, {config.GEOCODE_REGION_HINT}"

    params = {"q": query, "format": "jsonv2", "limit": 1}
    if config.NOMINATIM_VIEWBOX:
        params["viewbox"] = config.NOMINATIM_VIEWBOX
        if config.NOMINATIM_BOUNDED:
            params["bounded"] = 1

    headers = {"User-Agent": config.NOMINATIM_USER_AGENT}

    _throttle()
    try:
        resp = httpx.get(config.NOMINATIM_URL, params=params, headers=headers, timeout=15.0)
        resp.raise_for_status()
        results = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        print(f"[geocode] request failed for {query!r}: {exc}", flush=True)
        return None

    if not results:
        return None

    top = results[0]
    try:
        return float(top["lat"]), float(top["lon"])
    except (KeyError, TypeError, ValueError):
        return None
