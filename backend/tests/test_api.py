from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx

from tests.conftest import load, meteo_handler, nominatim_handler

NOMINATIM_RE = r"https://nominatim\.openstreetmap\.org/search.*"
OSRM_RE = r"https://router\.project-osrm\.org/route/v1/driving/.*"
METEO_RE = r"https://api\.open-meteo\.com/v1/forecast.*"


def mock_sources(storm: bool = False, severe: bool = False):
    respx.get(url__regex=NOMINATIM_RE).mock(side_effect=nominatim_handler())
    respx.get(url__regex=OSRM_RE).mock(return_value=httpx.Response(200, json=load("osrm_trips.json")))
    respx.get(url__regex=METEO_RE).mock(side_effect=meteo_handler(storm=storm, severe=severe))


async def test_health(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "fleetcast"
    assert "openrouteservice" in body["providers"]


@respx.mock
async def test_places_autocomplete(client):
    respx.get(url__regex=NOMINATIM_RE).mock(return_value=httpx.Response(200, json=load("nominatim_suggest.json")))
    response = await client.get("/api/places", params={"q": "Los Ang"})
    assert response.status_code == 200
    places = response.json()["places"]
    assert len(places) == 4
    assert places[0]["label"].startswith("Los Angeles")


async def test_places_requires_three_characters(client):
    response = await client.get("/api/places", params={"q": "LA"})
    assert response.status_code == 200
    assert response.json()["places"] == []


@respx.mock
async def test_analyze_happy_path(client, trip_body):
    mock_sources()
    response = await client.post("/api/trips/analyze", json=trip_body)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["trip"]["id"]
    assert len(body["routes"]) == 2
    assert {route["key"] for route in body["routes"]} == {"A", "B"}

    route = body["routes"][0]
    assert route["provider"] == "osrm"
    assert route["stops"][0]["mile"] == 0
    assert route["stops"][-1]["mile"] == pytest.approx(route["distance_mi"], abs=0.1)
    assert len(route["segments"]) == len(route["stops"]) - 1
    assert route["stops"][0]["weather"]["available"] is True

    ledger = route["ledger"]
    total = (
        ledger["clear_mi"]
        + ledger["caution_mi"]
        + ledger["warning_mi"]
        + ledger["severe_mi"]
        + ledger["no_go_mi"]
        + ledger["unrated_mi"]
    )
    assert total == ledger["total_mi"]

    assert body["verdict"]["safe"] is True
    assert body["verdict"]["route"] in {"A", "B"}


@respx.mock
async def test_analyze_storm_returns_unsafe_verdict(client, trip_body):
    mock_sources(severe=True)
    response = await client.post("/api/trips/analyze", json=trip_body)
    assert response.status_code == 200
    verdict = response.json()["verdict"]
    assert verdict["safe"] is False
    assert verdict["route"] is None
    assert verdict["fallback"]


@respx.mock
async def test_analyze_weather_failure_marks_unrated(client, trip_body):
    mock_sources()
    respx.get(url__regex=METEO_RE).mock(return_value=httpx.Response(500))
    response = await client.post("/api/trips/analyze", json=trip_body)
    assert response.status_code == 200
    body = response.json()
    assert any("Weather" in alert for alert in body["alerts"])
    assert body["routes"][0]["stops"][0]["risk"]["rated"] is False
    assert body["verdict"]["safe"] is False


async def test_analyze_validation(client, trip_body):
    response = await client.post("/api/trips/analyze", json={"origin": "LA"})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "invalid_body"

    for patch in (
        {"load_lbs": 90_000},
        {"interval_mi": 15},
        {"depart_at": (datetime.now(UTC) - timedelta(hours=2)).isoformat()},
    ):
        response = await client.post("/api/trips/analyze", json={**trip_body, **patch})
        assert response.status_code == 422, patch


@respx.mock
async def test_place_not_found(client, trip_body):
    respx.get(url__regex=NOMINATIM_RE).mock(return_value=httpx.Response(200, json=[]))
    response = await client.post("/api/trips/analyze", json=trip_body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "place_not_found"


@respx.mock
async def test_corridor_lifecycle(client, trip_body):
    mock_sources()
    analysis = (await client.post("/api/trips/analyze", json=trip_body)).json()
    trip_id = analysis["trip"]["id"]

    response = await client.get(f"/api/trips/{trip_id}/corridor", params={"route": "A"})
    assert response.status_code == 200, response.text
    heat = response.json()
    assert len(heat["hours"]) == 49
    assert heat["samples"]
    assert all(len(sample["levels"]) == 49 for sample in heat["samples"])

    missing_route = await client.get(f"/api/trips/{trip_id}/corridor", params={"route": "Z"})
    assert missing_route.status_code == 404

    expired = await client.get("/api/trips/missing/corridor", params={"route": "A"})
    assert expired.status_code == 404
    assert expired.json()["error"]["code"] == "trip_expired"
