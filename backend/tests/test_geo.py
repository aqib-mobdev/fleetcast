import pytest

from app.domain.geo import (
    cumulative_miles,
    haversine_mi,
    line_distance,
    point_at,
    sample_line,
    shift,
    slice_route,
    value_at,
)


def line_of_miles(miles: float) -> list[tuple[float, float]]:
    per_deg = 69.0546
    steps = int(miles)
    return [(-118.0, 34.0 + miles / per_deg * i / steps) for i in range(steps + 1)]


def test_haversine_la_to_phoenix():
    distance = haversine_mi((-118.2437, 34.0522), (-112.0740, 33.4484))
    assert 320 < distance < 380


def test_cumulative_and_total():
    points = line_of_miles(100)
    cum = cumulative_miles(points)
    assert cum[0] == 0
    assert cum[-1] == pytest.approx(100, abs=0.2)
    assert cum == sorted(cum)


def test_point_at_interpolates_along_line():
    points = [(-118.0, 34.0), (-117.0, 34.0)]
    cum = cumulative_miles(points)
    lon, lat = point_at(points, cum, cum[-1] / 2)
    assert lon == pytest.approx(-117.5, abs=1e-4)
    assert lat == pytest.approx(34.0, abs=1e-6)


def test_value_at_interpolates_timing():
    assert value_at([0, 100], [0, 3600], 25) == pytest.approx(900)
    assert value_at([0, 100], [0, 3600], 0) == 0
    assert value_at([0, 100], [0, 3600], 100) == 3600


def test_slice_route_keeps_endpoints():
    points = line_of_miles(50)
    cum = cumulative_miles(points)
    part = slice_route(points, cum, 10, 20)
    assert part[0] == point_at(points, cum, 10)
    assert part[-1] == point_at(points, cum, 20)


def test_sample_line_returns_fixed_count():
    points = line_of_miles(80)
    samples = sample_line(points, 24)
    assert len(samples) == 24
    assert samples[0] == points[0]
    assert samples[-1] == pytest.approx(points[-1], abs=1e-5)


def test_line_distance_detects_identical_and_offset():
    base = line_of_miles(40)
    assert line_distance(sample_line(base, 20), sample_line(base, 20)) < 0.01
    shifted = [(lon, lat + 0.25) for lon, lat in base]
    assert line_distance(sample_line(base, 20), sample_line(shifted, 20)) > 10


def test_shift_moves_north_and_east():
    lon, lat = shift((-118.0, 34.0), 0.0, 10)
    assert lat > 34.0
    assert lon == pytest.approx(-118.0, abs=1e-6)

    lon2, lat2 = shift((-118.0, 34.0), 1.5708, 10)
    assert lon2 > -118.0
    assert lat2 == pytest.approx(34.0, abs=1e-6)
