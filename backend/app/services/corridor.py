import math
from datetime import UTC, datetime

from app.cache import store
from app.config import settings
from app.domain import risk
from app.domain.geo import point_at, shift
from app.errors import DomainError, TripExpired
from app.providers import weather

SPACING_MI = 18.0
LANES_MI = (0.0, -12.0, 12.0, -24.0, 24.0)
MAX_SAMPLES = 96


def _lattice(points, cum) -> list[dict]:
    total = cum[-1]
    spare = max(2, MAX_SAMPLES // len(LANES_MI))
    count = max(2, min(int(total // SPACING_MI) + 1, spare))
    step = total / (count - 1)
    samples = []
    for i in range(count):
        tone = step * i
        lon, lat = point_at(points, cum, tone)
        ahead = point_at(points, cum, min(tone + 0.6, total))
        behind = point_at(points, cum, max(tone - 0.6, 0.0))
        heading = math.atan2(ahead[1] - behind[1], ahead[0] - behind[0])
        for offset in LANES_MI:
            if offset == 0:
                ox, oy = lon, lat
            else:
                ox, oy = shift((lon, lat), heading + (1.5708 if offset > 0 else -1.5708), abs(offset))
            samples.append({"lat": round(oy, 5), "lon": round(ox, 5), "mile": round(tone, 1), "offset_mi": offset})
    return samples[:MAX_SAMPLES]


async def corridor(trip_id: str, route_key: str) -> dict:
    trip = store.get(f"trip:{trip_id}")
    if trip is None:
        raise TripExpired()
    route = trip["routes"].get(route_key)
    if route is None:
        raise DomainError("route_not_found", f"Route '{route_key}' does not exist for this trip.", status=404)

    cache_key = f"heat:{trip_id}:{route_key}"
    cached = store.get(cache_key)
    if cached is not None:
        return cached

    cfg = settings()
    points = [tuple(p) for p in route["coords"]]
    cum = route["cum_miles"]
    samples = _lattice(points, cum)
    forecasts = await weather.fetch([(s["lat"], s["lon"]) for s in samples], 3)

    base = forecasts[0].times[0]
    now_hour = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    start = max(0, int((now_hour - base).total_seconds() // 3600))
    start = min(start, max(0, len(forecasts[0].times) - (cfg.heatmap_hours + 1)))
    slots = min(cfg.heatmap_hours + 1, len(forecasts[0].times) - start)
    hours = [forecasts[0].times[start + i] for i in range(slots)]

    out = []
    for sample, forecast in zip(samples, forecasts, strict=True):
        levels, values = [], []
        for i in range(slots):
            wind = forecast.wind_mph[start + i]
            rain = forecast.rain_in_hr[start + i]
            snow = forecast.snow_in_hr[start + i]
            verdict = risk.evaluate(wind, rain, snow, trip["load_lbs"])
            levels.append(verdict.level.code if verdict.rated else "unrated")
            values.append(
                {
                    "wind_mph": None if wind is None else round(wind, 1),
                    "rain_in_hr": None if rain is None else round(rain, 3),
                    "snow_in_hr": None if snow is None else round(snow, 3),
                }
            )
        out.append({**sample, "levels": levels, "values": values})

    payload = {
        "trip_id": trip_id,
        "route": route_key,
        "load_lbs": trip["load_lbs"],
        "start_utc": hours[0].isoformat(),
        "hours": [h.isoformat() for h in hours],
        "samples": out,
        "notes": [
            "Heat is interpolated between corridor samples, not a point observation.",
            "Each slot uses its own forecast hour; checkpoint risk uses each stop's ETA.",
        ],
    }
    store.set(cache_key, payload, cfg.weather_ttl_s)
    return payload
