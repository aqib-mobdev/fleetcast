import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient, Response

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str):
    return json.loads((FIXTURES / name).read_text())


def _cycle(values: list, hours: int) -> list:
    return [values[i % len(values)] for i in range(hours)]


def make_meteo_entry(template: dict, lat: float, lon: float, hours: int, start: datetime) -> dict:
    hourly = template["hourly"]
    times = [(start + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(hours)]
    return {
        "latitude": lat,
        "longitude": lon,
        "utc_offset_seconds": 0,
        "timezone": "GMT",
        "hourly_units": template["hourly_units"],
        "hourly": {
            "time": times,
            **{key: _cycle(values, hours) for key, values in hourly.items() if key != "time"},
        },
    }


def meteo_handler(storm: bool = False, hours: int = 72, severe: bool = False):
    templates = load("meteo_stops.json")
    calm = templates[1]
    stormy = templates[0]
    if severe:
        stormy = copy_of(stormy)
        stormy["hourly"]["wind_speed_10m"] = [58.0] * 12
        stormy["hourly"]["rain"] = [1.2] * 12
        stormy["hourly"]["snowfall"] = [5.0] * 12

    def handler(request) -> Response:
        params = request.url.params
        lats = str(params.get("latitude", "")).split(",")
        lons = str(params.get("longitude", "")).split(",")
        start = datetime.now(UTC).replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
        entries = []
        for lat, lon in zip(lats, lons, strict=True):
            template = stormy if (storm or severe) else calm
            entries.append(make_meteo_entry(template, float(lat), float(lon), hours, start))
        return Response(200, json=entries)

    return handler


def nominatim_handler():
    la = load("nominatim_la.json")
    phx = load("nominatim_phx.json")

    def handler(request) -> Response:
        query = str(request.url.params.get("q", "")).lower()
        payload = phx if "phoenix" in query else la
        return Response(200, json=payload)

    return handler


@pytest.fixture(autouse=True)
def fresh_state(monkeypatch):
    from app.cache import store
    from app.config import settings
    from app.providers import geocode

    store.clear()
    settings.cache_clear()
    monkeypatch.setattr(geocode, "_MIN_GAP_S", 0.0)
    geocode._last_call = 0.0
    yield
    store.clear()


@pytest.fixture
async def client():
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


@pytest.fixture
def trip_body():
    return {
        "origin": "Los Angeles, CA",
        "destination": "Phoenix, AZ",
        "depart_at": (datetime.now(UTC) + timedelta(minutes=10)).isoformat(),
        "load_lbs": 34_000,
        "interval_mi": 50,
    }


def copy_of(data):
    return deepcopy(data)
