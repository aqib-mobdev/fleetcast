import respx

from app.domain.geo import cumulative_miles
from app.services import corridor
from tests.conftest import meteo_handler

METEO_RE = r"https://api\.open-meteo\.com/v1/forecast.*"


def route_points():
    points = [(-118.0, 34.0 + i * 0.02) for i in range(90)]
    return points, cumulative_miles(points)


@respx.mock
async def test_corridor_has_49_slots_and_lattice():
    respx.get(url__regex=METEO_RE).mock(side_effect=meteo_handler(storm=True))
    points, _ = route_points()
    payload = await corridor.build(points, 10_000, "A")

    assert payload["route"] == "A"
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
    points, _ = route_points()
    payload = await corridor.build(points, 10_000, "A")
    early = {sample["levels"][0] for sample in payload["samples"]}
    later = {sample["levels"][18] for sample in payload["samples"]}
    assert "clear" in early or "caution" in early
    assert later != early


@respx.mock
async def test_load_changes_heat_levels():
    respx.get(url__regex=METEO_RE).mock(side_effect=meteo_handler(storm=True))
    points, _ = route_points()
    light = await corridor.build(points, 5_000, "A")
    heavy = await corridor.build(points, 45_000, "A")

    def worst_count(payload):
        return sum(
            sample["levels"].count("no_go") + sample["levels"].count("severe")
            for sample in payload["samples"]
        )

    assert worst_count(heavy) > worst_count(light)


@respx.mock
async def test_corridor_is_cached():
    mock = respx.get(url__regex=METEO_RE).mock(side_effect=meteo_handler(storm=False))
    points, _ = route_points()
    await corridor.build(points, 20_000, "A")
    await corridor.build(points, 20_000, "B")
    assert mock.call_count == 1
