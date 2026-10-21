"""Generates static provider fixtures for the FleetCast test suite."""

import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).parent
R = 3958.761


def write(name: str, data) -> None:
    (HERE / name).write_text(json.dumps(data, indent=1))
    print("wrote", name)


def miles(a, b) -> float:
    lon1, lat1 = map(math.radians, a)
    lon2, lat2 = map(math.radians, b)
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def nominatim() -> None:
    write(
        "nominatim_la.json",
        [
            {
                "display_name": "Los Angeles, Los Angeles County, California, United States",
                "lat": "34.0522265",
                "lon": "-118.2436596",
            }
        ],
    )
    write(
        "nominatim_phx.json",
        [
            {
                "display_name": "Phoenix, Maricopa County, Arizona, United States",
                "lat": "33.4484367",
                "lon": "-112.0741410",
            }
        ],
    )
    write(
        "nominatim_suggest.json",
        [
            {"display_name": "Los Angeles, California, United States", "lat": 34.05, "lon": -118.24},
            {
                "display_name": "Los Angeles International Airport, California, United States",
                "lat": 33.94,
                "lon": -118.41,
            },
            {"display_name": "East Los Angeles, California, United States", "lat": 34.02, "lon": -118.17},
            {"display_name": "Los Alamos, New Mexico, United States", "lat": 35.89, "lon": -106.30},
        ],
    )


def ors() -> None:
    south = [
        [-118.2437, 34.0522],
        [-117.3700, 33.9800],
        [-116.5400, 33.9200],
        [-115.7200, 33.6600],
        [-114.6000, 33.6100],
        [-113.7600, 33.4300],
        [-113.0000, 33.4500],
        [-112.0740, 33.4484],
    ]
    north = [[lon, lat + 0.55] for lon, lat in south]
    west = [[lon - 0.35, lat - 0.15] for lon, lat in south]

    def feature(coords, speed):
        segments = [miles(coords[i], coords[i + 1]) for i in range(len(coords) - 1)]
        total = sum(segments)
        duration = total / speed * 3600
        steps = []
        chunk = max(1, (len(coords) - 1) // 3)
        for start in range(0, len(coords) - 1, chunk):
            end = min(start + chunk, len(coords) - 1)
            span = sum(segments[start:end])
            steps.append(
                {
                    "distance": round(span * 1609.344, 1),
                    "duration": round(span / speed * 3600, 1),
                    "way_points": [start, end],
                }
            )
        return {
            "type": "Feature",
            "properties": {
                "summary": {"distance": round(total * 1609.344, 1), "duration": round(duration, 1)},
                "segments": [{"distance": round(total * 1609.344, 1), "duration": round(duration, 1), "steps": steps}],
            },
            "geometry": {"type": "LineString", "coordinates": coords},
        }

    write(
        "ors_trips.json",
        {"type": "FeatureCollection", "features": [feature(south, 62), feature(north, 58), feature(west, 55)]},
    )


def osrm() -> None:
    base = [
        [-118.2437, 34.0522],
        [-117.3200, 33.9900],
        [-116.4100, 33.8200],
        [-115.5600, 33.6100],
        [-114.7200, 33.5900],
        [-113.7500, 33.4200],
        [-112.8500, 33.4800],
        [-112.0740, 33.4484],
    ]
    alt = [[lon, lat + 0.35] for lon, lat in base]

    def route(coords, speed):
        segs = [miles(coords[i], coords[i + 1]) for i in range(len(coords) - 1)]
        total = sum(segs)
        duration = total / speed * 3600
        return {
            "distance": round(total * 1609.344, 1),
            "duration": round(duration, 1),
            "geometry": {"type": "LineString", "coordinates": coords},
            "legs": [
                {
                    "annotation": {
                        "distance": [round(s * 1609.344, 1) for s in segs],
                        "duration": [round(s / speed * 3600, 1) for s in segs],
                    }
                }
            ],
        }

    write("osrm_trips.json", {"code": "Ok", "routes": [route(base, 64), route(alt, 60)]})


def meteo() -> None:
    start = datetime(2026, 2, 3, 0, 0, tzinfo=UTC)
    times = [(start + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(12)]

    def loc(lat, lon, wind, rain, snow_cm, temp, codes):
        return {
            "latitude": lat,
            "longitude": lon,
            "utc_offset_seconds": 0,
            "timezone": "GMT",
            "hourly_units": {
                "temperature_2m": "°C",
                "rain": "inch",
                "snowfall": "cm",
                "wind_speed_10m": "mph",
            },
            "hourly": {
                "time": times,
                "temperature_2m": temp,
                "precipitation": [round(r + s / 7, 3) for r, s in zip(rain, snow_cm, strict=True)],
                "rain": rain,
                "snowfall": snow_cm,
                "wind_speed_10m": wind,
                "wind_gusts_10m": [round(w * 1.3, 1) for w in wind],
                "weather_code": codes,
            },
        }

    write(
        "meteo_stops.json",
        [
            loc(
                34.05,
                -118.24,
                [8, 14, 22, 31, 44, 57, 18, 11, 9, 8, 8, 8],
                [0, 0, 0.04, 0.12, 0.30, 0.80, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 2.54, 6.35, 10.16, 12.70, 0, 0],
                [21, 20, 19, 18, 17, 16, 2, 0, -1, -2, 4, 9],
                [0, 1, 2, 61, 63, 95, 71, 73, 75, 85, 3, 1],
            ),
            loc(
                33.45,
                -112.07,
                [6] * 12,
                [0] * 12,
                [0] * 12,
                [24] * 12,
                [0] * 12,
            ),
        ],
    )

    start72 = datetime(2026, 2, 3, 0, 0, tzinfo=UTC)
    times72 = [(start72 + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(72)]
    wind72 = [round(8 + 34 * (0.5 - 0.5 * math.cos(2 * math.pi * i / 48)), 1) for i in range(72)]
    rain72 = [round(0.16 * max(0.0, math.sin(2 * math.pi * (i - 8) / 48)), 3) for i in range(72)]

    def loc72(lat, lon, mult):
        return {
            "latitude": lat,
            "longitude": lon,
            "utc_offset_seconds": 0,
            "timezone": "GMT",
            "hourly_units": {"snowfall": "cm", "rain": "inch", "wind_speed_10m": "mph"},
            "hourly": {
                "time": times72,
                "temperature_2m": [18.0] * 72,
                "precipitation": rain72,
                "rain": [round(r * mult, 3) for r in rain72],
                "snowfall": [0.0] * 72,
                "wind_speed_10m": [round(w * mult, 1) for w in wind72],
                "wind_gusts_10m": [round(w * 1.35 * mult, 1) for w in wind72],
                "weather_code": [61 if r > 0.05 else 2 for r in rain72],
            },
        }

    write(
        "meteo_corridor.json",
        [loc72(34.05, -118.24, 1.0), loc72(33.75, -115.2, 0.8), loc72(33.45, -112.07, 0.5)],
    )


if __name__ == "__main__":
    nominatim()
    ors()
    osrm()
    meteo()
