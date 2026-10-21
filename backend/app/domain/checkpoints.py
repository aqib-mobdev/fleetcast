from dataclasses import dataclass
from datetime import datetime, timedelta

from app.domain.geo import cumulative_miles, point_at, value_at


@dataclass(frozen=True)
class Stop:
    index: int
    mile: float
    lon: float
    lat: float
    eta: datetime


def stops_for(
    points: list[tuple[float, float]],
    cum_miles: list[float],
    cum_seconds: list[float],
    interval_mi: int,
    depart_at: datetime,
) -> list[Stop]:
    total = cum_miles[-1]
    marks = [0.0]
    step = float(interval_mi)
    cursor = step
    while cursor < total - 0.01:
        marks.append(cursor)
        cursor += step
    marks.append(total)

    stops: list[Stop] = []
    for index, mile in enumerate(marks):
        lon, lat = point_at(points, cum_miles, mile)
        eta = depart_at + timedelta(seconds=value_at(cum_miles, cum_seconds, mile))
        stops.append(Stop(index=index, mile=round(mile, 2), lon=lon, lat=lat, eta=eta))
    return stops


def interpolate_miles(points: list[tuple[float, float]]) -> list[float]:
    return cumulative_miles(points)
