import math
import uuid
from datetime import UTC, datetime, timedelta

from app.cache import store
from app.config import settings
from app.domain import checkpoints, exposure, geo, recommend, risk
from app.domain.severity import Level
from app.errors import DomainError
from app.providers import geocode, routing, weather

ROUTE_KEYS = "ABCDEFGH"


def _forecast_days(depart: datetime, max_seconds: float) -> int | None:
    now = datetime.now(UTC)
    lead_h = max(0.0, (depart - now).total_seconds() / 3600.0)
    horizon_h = lead_h + max_seconds / 3600.0 + 6.0
    limit = settings().max_forecast_days * 24
    if horizon_h > limit:
        return None
    return max(2, min(math.ceil(horizon_h / 24.0), settings().max_forecast_days))


async def analyze(body) -> dict:
    cfg = settings()
    origin = await geocode.locate(body.origin, "origin")
    destination = await geocode.locate(body.destination, "destination")
    if (origin.lat, origin.lon) == (destination.lat, destination.lon):
        raise DomainError("same_place", "Origin and destination resolve to the same point.", status=422)

    depart = body.depart_at.astimezone(UTC)
    routes, alerts = await routing.fetch_routes((origin.lon, origin.lat), (destination.lon, destination.lat))
    routes = routes[: cfg.alternatives]

    stops_by_route = {
        ROUTE_KEYS[i]: checkpoints.stops_for(
            route.coords, route.cum_miles, route.cum_seconds, body.interval_mi, depart
        )
        for i, route in enumerate(routes)
    }

    max_duration = max(route.duration_s for route in routes)
    days = _forecast_days(depart, max_duration)
    forecast_by_point: dict[tuple[float, float], weather.Forecast] = {}

    if days is None:
        alerts.append("Trip extends beyond the forecast horizon; weather is unrated.")
    else:
        unique: list[tuple[float, float]] = []
        seen: set[tuple[float, float]] = set()
        for stops in stops_by_route.values():
            for stop in stops:
                key = (round(stop.lat, 4), round(stop.lon, 4))
                if key not in seen:
                    seen.add(key)
                    unique.append(key)
        try:
            forecasts = await weather.fetch(unique, days)
            forecast_by_point = dict(zip(unique, forecasts, strict=True))
            for forecast in forecasts:
                for note in forecast.unit_notes:
                    if note not in alerts:
                        alerts.append(note)
        except DomainError as exc:
            alerts.append(f"{exc.message} Weather is unrated where data is missing.")

    route_payloads = []
    ledgers: dict[str, exposure.Ledger] = {}
    minutes: dict[str, float] = {}

    for i, route in enumerate(routes):
        key = ROUTE_KEYS[i]
        stops = stops_by_route[key]
        levels: list[Level | None] = []
        stop_payloads = []

        for stop in stops:
            forecast = forecast_by_point.get((round(stop.lat, 4), round(stop.lon, 4)))
            current = (
                weather.sample(forecast, stop.eta)
                if forecast is not None
                else weather.WeatherNow(available=False, at=stop.eta, reason="no forecast for this point")
            )
            verdict = risk.evaluate(current.wind_mph, current.rain_in_hr, current.snow_in_hr, body.load_lbs)
            levels.append(verdict.level if verdict.rated else None)
            stop_payloads.append(
                {
                    "n": stop.index,
                    "mile": stop.mile,
                    "lat": round(stop.lat, 6),
                    "lon": round(stop.lon, 6),
                    "eta": stop.eta.isoformat(),
                    "weather": current.payload(),
                    "risk": {
                        "code": verdict.level.code,
                        "label": verdict.level.label,
                        "score": int(verdict.level),
                        "rated": verdict.rated,
                        "complete": verdict.complete,
                        "wind": None if verdict.wind is None else verdict.wind.code,
                        "rain": None if verdict.rain is None else verdict.rain.code,
                        "snow": None if verdict.snow is None else verdict.snow.code,
                        "override": verdict.override,
                    },
                }
            )

        ledger = exposure.ledger_for(
            [stop.mile for stop in stops], levels, route.cum_miles[-1]
        )
        ledgers[key] = ledger
        minutes[key] = route.duration_s / 60.0

        segments = []
        for left, right, a, b in zip(stops, stops[1:], levels, levels[1:], strict=False):
            segment_level = max(a, b) if a is not None and b is not None else None
            path = geo.slice_route(route.coords, route.cum_miles, left.mile, right.mile)
            segments.append(
                {
                    "from_mi": left.mile,
                    "to_mi": right.mile,
                    "code": None if segment_level is None else segment_level.code,
                    "path": [[round(lon, 6), round(lat, 6)] for lon, lat in path],
                }
            )

        notes = list(route.notes)
        if ledger.unrated_mi > 0:
            notes.append(f"{ledger.unrated_mi:.1f} mi could not be rated.")

        route_payloads.append(
            {
                "key": key,
                "provider": route.provider,
                "profile": route.profile,
                "timing": route.timing,
                "distance_mi": round(route.distance_mi, 1),
                "duration_min": round(route.duration_s / 60.0, 1),
                "depart_at": depart.isoformat(),
                "arrive_at": (depart + timedelta(seconds=route.duration_s)).isoformat(),
                "stops": stop_payloads,
                "segments": segments,
                "ledger": ledger.payload(),
                "notes": notes,
            }
        )

    verdict = recommend.decide(ledgers, minutes)
    if any(ledger.unrated_mi > 0 for ledger in ledgers.values()):
        alerts.append("Some segments are unrated; they are excluded from averages, not treated as safe.")

    trip_id = uuid.uuid4().hex
    store.set(
        f"trip:{trip_id}",
        {
            "origin": {
                "query": body.origin,
                "label": origin.label,
                "lat": origin.lat,
                "lon": origin.lon,
            },
            "destination": {
                "query": body.destination,
                "label": destination.label,
                "lat": destination.lat,
                "lon": destination.lon,
            },
            "depart_at": depart.isoformat(),
            "load_lbs": body.load_lbs,
            "interval_mi": body.interval_mi,
            "routes": {
                ROUTE_KEYS[i]: {
                    "coords": route.coords,
                    "cum_miles": route.cum_miles,
                    "cum_seconds": route.cum_seconds,
                }
                for i, route in enumerate(routes)
            },
        },
        cfg.trip_ttl_s,
    )

    return {
        "trip": {
            "id": trip_id,
            "origin": {
                "query": body.origin,
                "label": origin.label,
                "lat": origin.lat,
                "lon": origin.lon,
            },
            "destination": {
                "query": body.destination,
                "label": destination.label,
                "lat": destination.lat,
                "lon": destination.lon,
            },
            "depart_at": depart.isoformat(),
            "load_lbs": body.load_lbs,
            "interval_mi": body.interval_mi,
            "generated_at": datetime.now(UTC).isoformat(),
        },
        "routes": route_payloads,
        "verdict": verdict.payload(),
        "alerts": alerts,
    }
