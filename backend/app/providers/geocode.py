import asyncio
import hashlib
import time
from dataclasses import dataclass

from app.cache import store
from app.config import settings
from app.errors import PlaceNotFound, UpstreamError
from app.providers.http import make_client

_lock = asyncio.Lock()
_last_call = 0.0
_MIN_GAP_S = 1.05


@dataclass(frozen=True)
class Place:
    label: str
    lat: float
    lon: float


async def _throttle() -> None:
    global _last_call
    async with _lock:
        wait = _MIN_GAP_S - (time.monotonic() - _last_call)
        if wait > 0:
            await asyncio.sleep(wait)
        _last_call = time.monotonic()


async def _search(query: str, limit: int) -> list[Place]:
    cfg = settings()
    await _throttle()
    try:
        async with make_client() as client:
            response = await client.get(
                f"{cfg.nominatim_base_url}/search",
                params={"q": query, "format": "jsonv2", "limit": limit, "addressdetails": 0},
            )
        response.raise_for_status()
        rows = response.json()
    except Exception as exc:
        raise UpstreamError("geocoder_unavailable", f"Geocoding failed: {exc}") from exc

    places = []
    for row in rows:
        try:
            places.append(Place(label=row["display_name"], lat=float(row["lat"]), lon=float(row["lon"])))
        except (KeyError, TypeError, ValueError):
            continue
    return places


async def locate(query: str, field: str) -> Place:
    key = "geo:" + hashlib.sha1(query.strip().lower().encode()).hexdigest()
    cached = store.get(key)
    if cached is not None:
        return cached
    results = await _search(query.strip(), 1)
    if not results:
        raise PlaceNotFound(field, query)
    place = results[0]
    store.set(key, place, settings().geocode_ttl_s)
    return place


async def suggest(query: str, limit: int = 5) -> list[Place]:
    text = query.strip()
    if len(text) < 3:
        return []
    key = "sug:" + hashlib.sha1(f"{text.lower()}:{limit}".encode()).hexdigest()
    cached = store.get(key)
    if cached is not None:
        return cached
    places = await _search(text, limit)
    store.set(key, places, settings().geocode_ttl_s)
    return places
