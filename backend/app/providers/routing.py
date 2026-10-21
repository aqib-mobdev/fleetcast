from dataclasses import dataclass, field

from app.cache import store
from app.config import settings
from app.domain.geo import KM_PER_MI, cumulative_miles, line_distance, sample_line
from app.errors import NoRoute, UpstreamError
from app.providers.http import make_client

DEDUPE_MILES = 0.25


@dataclass
class Route:
    coords: list[tuple[float, float]]
    distance_mi: float
    duration_s: float
    cum_miles: list[float]
    cum_seconds: list[float]
    provider: str
    profile: str
    timing: str
    notes: list[str] = field(default_factory=list)


def _constant_timing(cum: list[float], duration_s: float) -> list[float]:
    total = cum[-1] if cum else 0.0
    if total <= 0:
        return [0.0] * len(cum)
    return [m / total * duration_s for m in cum]


def _ors_timing(cum: list[float], steps: list[dict]) -> list[float]:
    seconds = [0.0] * len(cum)
    elapsed = 0.0
    cursor = 0
    for step in steps:
        marks = step.get("way_points") or [cursor, cursor]
        start, end = int(marks[0]), int(marks[-1])
        end = max(start, end)
        duration = float(step.get("duration") or 0.0)
        span = cum[end] - cum[start] if end < len(cum) else 0.0
        for i in range(start + 1, min(end + 1, len(cum))):
            seconds[i] = elapsed + (duration * (cum[i] - cum[start]) / span if span > 0 else duration)
        elapsed += duration
        cursor = max(cursor, end)
    for i in range(cursor + 1, len(cum)):
        seconds[i] = elapsed
    return seconds


def _from_ors_feature(feature: dict) -> Route | None:
    try:
        coords = [(float(lon), float(lat)) for lon, lat in feature["geometry"]["coordinates"]]
        props = feature["properties"]
        distance_mi = float(props["summary"]["distance"]) / 1000.0 / KM_PER_MI
        duration_s = float(props["summary"]["duration"])
        steps = [s for seg in props.get("segments", []) for s in seg.get("steps", [])]
    except (KeyError, TypeError, ValueError):
        return None
    if len(coords) < 2:
        return None
    cum = cumulative_miles(coords)
    seconds = _ors_timing(cum, steps) if steps else _constant_timing(cum, duration_s)
    return Route(
        coords=coords,
        distance_mi=distance_mi,
        duration_s=duration_s,
        cum_miles=cum,
        cum_seconds=seconds,
        provider="openrouteservice",
        profile="driving-hgv",
        timing="steps" if steps else "constant_speed",
    )


def _from_osrm_route(raw: dict) -> Route | None:
    try:
        coords = [(float(lon), float(lat)) for lon, lat in raw["geometry"]["coordinates"]]
        distance_mi = float(raw["distance"]) / 1000.0 / KM_PER_MI
        duration_s = float(raw["duration"])
        annotations = [leg.get("annotation", {}) for leg in raw.get("legs", [])]
    except (KeyError, TypeError, ValueError):
        return None
    if len(coords) < 2:
        return None
    cum = cumulative_miles(coords)
    durations: list[float] = []
    for ann in annotations:
        durations.extend(float(x) for x in ann.get("duration", []))
    if len(durations) == len(coords) - 1:
        seconds = [0.0]
        for value in durations:
            seconds.append(seconds[-1] + value)
        timing = "segments"
    else:
        seconds = _constant_timing(cum, duration_s)
        timing = "constant_speed"
    return Route(
        coords=coords,
        distance_mi=distance_mi,
        duration_s=duration_s,
        cum_miles=cum,
        cum_seconds=seconds,
        provider="osrm",
        profile="driving",
        timing=timing,
    )


async def _ors(origin: tuple[float, float], dest: tuple[float, float], alternatives: bool) -> list[Route]:
    cfg = settings()
    if not cfg.ors_api_key:
        raise UpstreamError("ors_unconfigured", "ORS key is not configured.")
    body: dict = {
        "coordinates": [[origin[0], origin[1]], [dest[0], dest[1]]],
        "units": "m",
    }
    if alternatives:
        body["alternative_routes"] = {
            "target_count": cfg.alternatives,
            "share_factor": 0.6,
            "weight_factor": 1.6,
        }
    try:
        async with make_client() as client:
            response = await client.post(
                f"{cfg.openrouteservice_base_url}/v2/directions/driving-hgv/geojson",
                json=body,
                headers={"Authorization": cfg.ors_api_key},
            )
    except Exception as exc:
        raise UpstreamError("routing_unavailable", f"ORS request failed: {exc}") from exc
    if response.status_code != 200:
        raise UpstreamError("routing_rejected", f"ORS rejected the request ({response.status_code}).")
    routes = [r for r in (_from_ors_feature(f) for f in response.json().get("features", [])) if r]
    if not routes:
        raise UpstreamError("routing_empty", "ORS returned no usable routes.")
    return routes


async def _osrm(origin: tuple[float, float], dest: tuple[float, float]) -> list[Route]:
    cfg = settings()
    url = (
        f"{cfg.osrm_base_url}/route/v1/driving/"
        f"{origin[0]:.6f},{origin[1]:.6f};{dest[0]:.6f},{dest[1]:.6f}"
    )
    try:
        async with make_client() as client:
            response = await client.get(
                url,
                params={
                    "overview": "full",
                    "geometries": "geojson",
                    "alternatives": "3",
                    "annotations": "duration,distance",
                },
            )
    except Exception as exc:
        raise UpstreamError("routing_unavailable", f"OSRM request failed: {exc}") from exc
    if response.status_code != 200:
        raise UpstreamError("routing_rejected", "OSRM could not route this pair.")
    payload = response.json()
    if payload.get("code") != "Ok":
        raise UpstreamError("routing_rejected", "OSRM could not route this pair.")
    routes = [r for r in (_from_osrm_route(raw) for raw in payload.get("routes", [])) if r]
    if not routes:
        raise UpstreamError("routing_empty", "OSRM returned no usable routes.")
    return routes


def _distinct(routes: list[Route]) -> list[Route]:
    kept: list[Route] = []
    shapes: list[list[tuple[float, float]]] = []
    for route in routes:
        shape = sample_line(route.coords, 48)
        if any(line_distance(shape, other) < DEDUPE_MILES for other in shapes):
            continue
        kept.append(route)
        shapes.append(shape)
    return kept


async def fetch_routes(origin: tuple[float, float], dest: tuple[float, float]) -> tuple[list[Route], list[str]]:
    cfg = settings()
    key = f"routes:{origin[0]:.4f},{origin[1]:.4f}:{dest[0]:.4f},{dest[1]:.4f}"
    cached = store.get(key)
    if cached is not None:
        return cached

    notes: list[str] = []
    routes: list[Route] = []

    if cfg.ors_api_key:
        try:
            routes = await _ors(origin, dest, alternatives=True)
        except UpstreamError as exc:
            notes.append(f"ORS alternatives unavailable: {exc.message}")
            try:
                routes = await _ors(origin, dest, alternatives=False)
                notes.append("Used a single ORS route for this corridor.")
            except UpstreamError as exc2:
                notes.append(f"ORS single-route attempt failed: {exc2.message}")

    if not routes:
        try:
            routes = await _osrm(origin, dest)
            notes.append("Routes come from the OSRM demo server (car profile, not truck-legal).")
        except UpstreamError as exc:
            raise NoRoute(exc.message) from exc

    distinct = _distinct(routes)[: cfg.alternatives]
    if len(distinct) < cfg.alternatives:
        notes.append(
            f"Only {len(distinct)} distinct route(s) returned; duplicates were not invented."
        )

    store.set(key, (distinct, notes), cfg.route_ttl_s)
    return distinct, notes
