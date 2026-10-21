import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.cache import store
from app.config import settings
from app.errors import UpstreamError
from app.providers.http import make_client

HOURLY_FIELDS = (
    "temperature_2m",
    "precipitation",
    "rain",
    "snowfall",
    "wind_speed_10m",
    "wind_gusts_10m",
    "weather_code",
)

WMO = {
    0: "Clear sky",
    1: "Mostly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Heavy drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    66: "Freezing rain",
    67: "Heavy freezing rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Rain showers",
    81: "Heavy showers",
    82: "Violent showers",
    85: "Snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Storm with hail",
    99: "Severe hailstorm",
}

CM_PER_INCH = 2.54


@dataclass
class Forecast:
    times: list[datetime]
    wind_mph: list[float | None]
    gust_mph: list[float | None]
    rain_in_hr: list[float | None]
    snow_in_hr: list[float | None]
    temp_c: list[float | None]
    codes: list[int | None]
    unit_notes: list[str] = field(default_factory=list)


@dataclass
class WeatherNow:
    available: bool
    at: datetime
    wind_mph: float | None = None
    gust_mph: float | None = None
    rain_in_hr: float | None = None
    snow_in_hr: float | None = None
    temp_f: float | None = None
    code: int | None = None
    condition: str | None = None
    interpolated: bool = False
    reason: str | None = None

    def payload(self) -> dict:
        return {
            "available": self.available,
            "at": self.at.isoformat(),
            "wind_mph": None if self.wind_mph is None else round(self.wind_mph, 1),
            "gust_mph": None if self.gust_mph is None else round(self.gust_mph, 1),
            "rain_in_hr": None if self.rain_in_hr is None else round(self.rain_in_hr, 3),
            "snow_in_hr": None if self.snow_in_hr is None else round(self.snow_in_hr, 3),
            "temp_f": None if self.temp_f is None else round(self.temp_f, 1),
            "code": self.code,
            "condition": self.condition,
            "interpolated": self.interpolated,
            "reason": self.reason,
            "source": "open-meteo" if self.available else None,
        }


def _times(raw: list[str]) -> list[datetime]:
    values = []
    for item in raw:
        stamp = datetime.fromisoformat(item)
        values.append(stamp.replace(tzinfo=UTC) if stamp.tzinfo is None else stamp.astimezone(UTC))
    return values


def _series(hourly: dict, units: dict, name: str) -> list[float | None]:
    values = hourly.get(name) or []
    if name == "snowfall":
        unit = str(units.get("snowfall", "cm")).lower()
        if unit in ("cm", "centimeters"):
            return [None if v is None else float(v) / CM_PER_INCH for v in values]
    return [None if v is None else float(v) for v in values]


def _normalize(entry: dict) -> Forecast:
    hourly = entry.get("hourly") or {}
    units = entry.get("hourly_units") or {}
    notes = []
    snow_unit = str(units.get("snowfall", "cm")).lower()
    if snow_unit in ("cm", "centimeters"):
        notes.append("snowfall converted from cm to in/hr")
    return Forecast(
        times=_times(hourly.get("time") or []),
        wind_mph=_series(hourly, units, "wind_speed_10m"),
        gust_mph=_series(hourly, units, "wind_gusts_10m"),
        rain_in_hr=_series(hourly, units, "rain"),
        snow_in_hr=_series(hourly, units, "snowfall"),
        temp_c=_series(hourly, units, "temperature_2m"),
        codes=[None if v is None else int(v) for v in hourly.get("weather_code") or []],
        unit_notes=notes,
    )


async def fetch(points: list[tuple[float, float]], days: int) -> list[Forecast]:
    if not points:
        return []
    cfg = settings()
    days = max(1, min(days, cfg.max_forecast_days))
    key = "wx:" + hashlib.sha1(
        str([[round(lat, 4), round(lon, 4)] for lat, lon in points] + [days]).encode()
    ).hexdigest()
    cached = store.get(key)
    if cached is not None:
        return cached

    params = {
        "latitude": ",".join(f"{lat:.4f}" for lat, _ in points),
        "longitude": ",".join(f"{lon:.4f}" for _, lon in points),
        "hourly": ",".join(HOURLY_FIELDS),
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "GMT",
        "forecast_days": days,
    }
    try:
        async with make_client() as client:
            response = await client.get(f"{cfg.open_meteo_base_url}/forecast", params=params)
        if response.status_code != 200:
            raise UpstreamError("weather_unavailable", f"Open-Meteo returned {response.status_code}.")
        payload = response.json()
    except UpstreamError:
        raise
    except Exception as exc:
        raise UpstreamError("weather_unavailable", f"Forecast request failed: {exc}") from exc

    entries = payload if isinstance(payload, list) else [payload]
    if len(entries) != len(points):
        raise UpstreamError("weather_incomplete", "Forecast response did not match requested points.")
    forecasts = [_normalize(entry) for entry in entries]
    store.set(key, forecasts, cfg.weather_ttl_s)
    return forecasts


def sample(forecast: Forecast, at: datetime) -> WeatherNow:
    if not forecast.times:
        return WeatherNow(available=False, at=at, reason="no forecast data")

    at = at if at.tzinfo else at.replace(tzinfo=UTC)
    at = at.astimezone(UTC)
    if at < forecast.times[0]:
        return WeatherNow(available=False, at=at, reason="ETA before the forecast window")
    if at > forecast.times[-1]:
        return WeatherNow(available=False, at=at, reason="ETA beyond the forecast horizon")

    lo, hi = 0, len(forecast.times) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if forecast.times[mid] <= at:
            lo = mid
        else:
            hi = mid
    span = (forecast.times[hi] - forecast.times[lo]).total_seconds()
    ratio = 0.0 if span <= 0 else (at - forecast.times[lo]).total_seconds() / span
    ratio = max(0.0, min(1.0, ratio))

    def mix(values: list[float | None]) -> float | None:
        a, b = values[lo], values[hi]
        if a is None:
            return b
        if b is None:
            return a
        return a + (b - a) * ratio

    nearest = lo if ratio < 0.5 else hi
    code = forecast.codes[nearest] if nearest < len(forecast.codes) else None
    temp_c = mix(forecast.temp_c)
    return WeatherNow(
        available=True,
        at=at,
        wind_mph=mix(forecast.wind_mph),
        gust_mph=mix(forecast.gust_mph),
        rain_in_hr=mix(forecast.rain_in_hr),
        snow_in_hr=mix(forecast.snow_in_hr),
        temp_f=None if temp_c is None else temp_c * 9 / 5 + 32,
        code=code,
        condition=WMO.get(code) if code is not None else None,
        interpolated=ratio > 0,
    )
