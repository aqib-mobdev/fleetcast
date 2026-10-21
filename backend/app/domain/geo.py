import math

EARTH_RADIUS_MI = 3958.761
KM_PER_MI = 1.609344
KM_PER_DEG = 111.195


def haversine_mi(a: tuple[float, float], b: tuple[float, float]) -> float:
    lon1, lat1 = a
    lon2, lat2 = b
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_MI * math.asin(math.sqrt(h))


def cumulative_miles(points: list[tuple[float, float]]) -> list[float]:
    out = [0.0]
    for i in range(1, len(points)):
        out.append(out[-1] + haversine_mi(points[i - 1], points[i]))
    return out


def point_at(points: list[tuple[float, float]], cum: list[float], target: float) -> tuple[float, float]:
    if target <= 0:
        return points[0]
    if target >= cum[-1]:
        return points[-1]
    lo, hi = 0, len(cum) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if cum[mid] <= target:
            lo = mid
        else:
            hi = mid
    span = cum[hi] - cum[lo]
    ratio = 0.0 if span <= 0 else (target - cum[lo]) / span
    return (
        points[lo][0] + (points[hi][0] - points[lo][0]) * ratio,
        points[lo][1] + (points[hi][1] - points[lo][1]) * ratio,
    )


def value_at(cum: list[float], values: list[float], target: float) -> float:
    if target <= 0:
        return values[0]
    if target >= cum[-1]:
        return values[-1]
    lo, hi = 0, len(cum) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if cum[mid] <= target:
            lo = mid
        else:
            hi = mid
    span = cum[hi] - cum[lo]
    if span <= 0:
        return values[lo]
    return values[lo] + (values[hi] - values[lo]) * (target - cum[lo]) / span


def slice_route(
    points: list[tuple[float, float]], cum: list[float], start: float, end: float
) -> list[tuple[float, float]]:
    end = min(end, cum[-1])
    head = point_at(points, cum, start)
    tail = point_at(points, cum, end)
    inner = [p for i, p in enumerate(points) if start < cum[i] < end]
    return [head, *inner, tail]


def sample_line(points: list[tuple[float, float]], count: int) -> list[tuple[float, float]]:
    cum = cumulative_miles(points)
    total = cum[-1]
    if total <= 0:
        return [points[0]] * count
    return [point_at(points, cum, total * i / (count - 1)) for i in range(count)]


def line_distance(a: list[tuple[float, float]], b: list[tuple[float, float]]) -> float:
    return sum(haversine_mi(x, y) for x, y in zip(a, b, strict=True)) / len(a)


def shift(point: tuple[float, float], bearing_rad: float, miles: float) -> tuple[float, float]:
    """Move a point by a distance in miles along a bearing (radians)."""
    lon, lat = point
    dlat = (miles / 69.0) * math.cos(bearing_rad)
    dlon = (miles / (69.0 * max(0.2, math.cos(math.radians(lat))))) * math.sin(bearing_rad)
    return (lon + dlon, lat + dlat)
