import httpx
import pytest
import respx

from app.errors import NoRoute
from app.providers.routing import fetch_routes
from tests.conftest import load

ORS_URL = "https://api.openrouteservice.org/v2/directions/driving-hgv/geojson"
OSRM_RE = r"https://router\.project-osrm\.org/route/v1/driving/.*"
LA = (-118.2436596, 34.0522265)
PHX = (-112.0741410, 33.4484367)


def enable_ors(monkeypatch):
    monkeypatch.setenv("FC_ORS_API_KEY", "test-key")
    from app.config import settings

    settings.cache_clear()


@respx.mock
async def test_ors_returns_alternatives_with_step_timing(monkeypatch):
    enable_ors(monkeypatch)
    respx.post(ORS_URL).mock(return_value=httpx.Response(200, json=load("ors_trips.json")))
    routes, notes = await fetch_routes(LA, PHX)

    assert len(routes) == 3
    first = routes[0]
    assert first.provider == "openrouteservice"
    assert first.profile == "driving-hgv"
    assert first.timing == "steps"
    assert first.cum_seconds[-1] == pytest.approx(first.duration_s, rel=0.01)
    assert first.cum_seconds == sorted(first.cum_seconds)
    assert notes == []


@respx.mock
async def test_osrm_fallback_parses_segment_annotations():
    respx.get(url__regex=OSRM_RE).mock(return_value=httpx.Response(200, json=load("osrm_trips.json")))
    routes, notes = await fetch_routes(LA, PHX)

    assert len(routes) == 2
    assert all(route.provider == "osrm" for route in routes)
    assert routes[0].timing == "segments"
    assert routes[0].cum_seconds[-1] == pytest.approx(routes[0].duration_s, rel=0.01)
    assert any("OSRM" in note for note in notes)


@respx.mock
async def test_duplicate_geometries_are_collapsed():
    payload = load("osrm_trips.json")
    payload["routes"].append(payload["routes"][0])
    respx.get(url__regex=OSRM_RE).mock(return_value=httpx.Response(200, json=payload))
    routes, notes = await fetch_routes(LA, PHX)
    assert len(routes) == 2
    assert any("duplicates were not invented" in note for note in notes)


@respx.mock
async def test_ors_failure_falls_back_to_osrm(monkeypatch):
    enable_ors(monkeypatch)
    respx.post(ORS_URL).mock(return_value=httpx.Response(500))
    respx.get(url__regex=OSRM_RE).mock(return_value=httpx.Response(200, json=load("osrm_trips.json")))

    routes, notes = await fetch_routes(LA, PHX)
    assert routes and routes[0].provider == "osrm"
    assert any("ORS" in note for note in notes)


@respx.mock
async def test_all_providers_failing_raises_no_route(monkeypatch):
    enable_ors(monkeypatch)
    respx.post(ORS_URL).mock(return_value=httpx.Response(503))
    respx.get(url__regex=OSRM_RE).mock(return_value=httpx.Response(503))
    with pytest.raises(NoRoute):
        await fetch_routes(LA, PHX)


@respx.mock
async def test_routes_are_cached():
    mock = respx.get(url__regex=OSRM_RE).mock(return_value=httpx.Response(200, json=load("osrm_trips.json")))
    await fetch_routes(LA, PHX)
    await fetch_routes(LA, PHX)
    assert mock.call_count == 1
