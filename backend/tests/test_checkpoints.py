from datetime import UTC, datetime

import pytest

from app.domain.checkpoints import stops_for
from app.domain.geo import cumulative_miles


def route_with_timing(miles: float, seconds: float):
    per_deg = 69.0546
    steps = int(miles)
    points = [(-118.0, 34.0 + miles / per_deg * i / steps) for i in range(steps + 1)]
    cum = cumulative_miles(points)
    if cum[-1] != miles:
        factor = miles / cum[-1]
        cum = [value * factor for value in cum]
    timings = [value / cum[-1] * seconds for value in cum]
    return points, cum, timings


DEPART = datetime(2026, 3, 2, 14, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    "interval,miles",
    [
        (10, [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]),
        (25, [0, 25, 50, 75, 100]),
        (50, [0, 50, 100]),
        (60, [0, 60, 100]),
    ],
)
def test_stop_placement(interval, miles):
    points, cum, timings = route_with_timing(100, 7200)
    stops = stops_for(points, cum, timings, interval, DEPART)
    assert [stop.mile for stop in stops] == pytest.approx(miles, abs=0.01)


def test_origin_and_destination_always_present():
    points, cum, timings = route_with_timing(35, 2400)
    stops = stops_for(points, cum, timings, 50, DEPART)
    assert len(stops) == 2
    assert stops[0].mile == 0
    assert stops[-1].mile == pytest.approx(35, abs=0.1)


def test_eta_uses_provider_timing_not_constant_speed():
    points, cum, _timings = route_with_timing(100, 5400)
    warped = [value**0.5 / (cum[-1] ** 0.5) * 5400 for value in cum]
    stops = stops_for(points, cum, warped, 50, DEPART)
    expected = DEPART.timestamp() + 5400 * 0.5**0.5
    midpoint = next(stop for stop in stops if abs(stop.mile - 50) < 0.5)
    assert midpoint.eta.timestamp() == pytest.approx(expected, abs=2)
    assert stops[-1].eta.timestamp() == pytest.approx(DEPART.timestamp() + 5400, abs=2)


def test_stops_are_monotonic():
    points, cum, timings = route_with_timing(240, 4 * 3600)
    stops = stops_for(points, cum, timings, 10, DEPART)
    assert [stop.mile for stop in stops] == sorted(stop.mile for stop in stops)
    assert [stop.eta for stop in stops] == sorted(stop.eta for stop in stops)
