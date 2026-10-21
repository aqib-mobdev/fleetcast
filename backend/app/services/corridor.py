import hashlib
import math
from datetime import UTC, datetime

from app.cache import store
from app.config import settings
from app.domain import risk
from app.domain.geo import cumulative_miles, point_at, shift
from app.providers import weather

SPACING_MI = 18.0
LANES_MI = (0.0, -12.0, 12.0, -24.0, 24.0)
MAX_SAMPLES = 96


def _lattice(points: list[tuple[float, float]], cum: list[float]) -> list[dict]:
    total = cum[-1]
    spare = max(2, MAX_SAMPLES // len(LANES_MI))
    count = max(2, min(int(total // SPACING_MI) + 1, spare))
    step = total / (count - 1)
    samples = []
    for i in range(count):
        anchor = step * i
        lon, lat = point_at(points, cum, anchor)
        ahead = point_at(points, cum, min(anchor + 0.6, total))
        behind = point_at(points, cum, max(anchor - 0.6, 0.0))
        heading = math.atan2(ahead[1] - behind[1], ahead[0] - behind[0])
        for offset in LANES_MI:
            if offset == 0:
                ox, oy = lon, lat
            else:
                bearing = heading + (math.pi / 2 if offset > 0 else -math.pi / 2)
                ox, oy = shift((lon, lat), bearing, abs(offset))
            samples.append({"lat": round(oy, 5), "lon": round(ox, 5), "mile": round(anchor, 1), "offset_mi": offset})
    return samples[:MAX_SAMPLES]


def _cache_key(points: list[tuple[float, float]], load_lbs: int) -> str:
    digest = hashlib.sha1(
        str([[round(lon, 4), round(lat, 4)] for lon, lat in points] + [load_lbs]).encode()
    ).hexdigest()
    return f"heat:{digest}"


async def build(points: list[tuple[float, float]], load_lbs: int, route_key: str = "A") -> dict:
    cfg = settings()
    cached = store.get(_cache_key(points, load_lbs))
    if cached is not None:
        return {**cached, "route": route_key}

    cum = cumulative_miles(points)
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
            verdict = risk.evaluate(wind, rain, snow, load_lbs)
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
        "route": route_key,
        "load_lbs": load_lbs,
        "start_utc": hours[0].isoformat(),
        "hours": [h.isoformat() for h in hours],
        "samples": out,
        "notes": [
            "Heat is interpolated between corridor samples, not a point observation.",
            "Each slot uses its own forecast hour; checkpoint risk uses each stop's ETA.",
        ],
    }
    store.set(_cache_key(points, load_lbs), payload, cfg.weather_ttl_s)
    return payload
