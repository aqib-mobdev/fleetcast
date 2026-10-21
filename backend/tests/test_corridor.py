from datetime import UTC, datetime

import respx

from app.cache import store
from app.domain.geo import cumulative_miles
from app.services import corridor
from tests.conftest import meteo_handler

METEO_RE = r"https://api\.open-meteo\.com/v1/forecast.*"


def seed_trip(load_lbs: int) -> str:
    points = [(-118.0, 34.0 + i * 0.02) for i in range(90)]
    cum = cumulative_miles(points)
    store.set(
        "trip:testtrip",
        {
            "origin": {"query": "LA", "label": "LA", "lat": 34.0, "lon": -118.0},
            "destination": {"query": "PHX", "label": "PHX", "lat": 35.8, "lon": -118.0},
            "depart_at": datetime.now(UTC).isoformat(),
            "load_lbs": load_lbs,
            "interval_mi": 25,
            "routes": {
                "A": {"coords": points, "cum_miles": cum, "cum_seconds": [m / 60 * 3600 for m in cum]},
            },
        },
        600,
    )
    return "testtrip"


@respx.mock
async def test_corridor_has_49_slots_and_lattice():
    respx.get(url__regex=METEO_RE).mock(side_effect=meteo_handler(storm=True))
    trip_id = seed_trip(10_000)
    payload = await corridor.corridor(trip_id, "A")

    assert len(payload["hours"]) == 49
    assert len(payload["samples"]) > 10
    offsets = {sample["offset_mi"] for sample in payload["samples"]}
    assert offsets == {0.0, -12.0, 12.0, -24.0, 24.0}
    for sample in payload["samples"]:
        assert len(sample["levels"]) == 49
        assert len(sample["values"]) == 49


@respx.mock
async def test_slots_change_over_time():
    respx.get(url__regex=METEO_RE).mock(side_effect=meteo_handler(storm=True))
    payload = await corridor.corridor(seed_trip(10_000), "A")
    per_slot = {sample["levels"][0] for sample in payload["samples"]}
    assert "clear" in per_slot or "caution" in per_slot
    later = {sample["levels"][18] for sample in payload["samples"]}
    assert later != per_slot


@respx.mock
async def test_load_changes_heat_levels():
    respx.get(url__regex=METEO_RE).mock(side_effect=meteo_handler(storm=True))
    light = await corridor.corridor(seed_trip(5_000), "A")
    store.clear()
    heavy = await corridor.corridor(seed_trip(45_000), "A")

    def worst_count(payload):
        return sum(
            sample["levels"].count("no_go") + sample["levels"].count("severe")
            for sample in payload["samples"]
        )

    assert worst_count(heavy) > worst_count(light)


@respx.mock
async def test_corridor_is_cached():
    mock = respx.get(url__regex=METEO_RE).mock(side_effect=meteo_handler(storm=False))
    trip_id = seed_trip(20_000)
    await corridor.corridor(trip_id, "A")
    await corridor.corridor(trip_id, "A")
    assert mock.call_count == 1
