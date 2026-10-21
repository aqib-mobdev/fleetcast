from dataclasses import dataclass

from app.domain.severity import Level


@dataclass(frozen=True)
class Band:
    below: float
    level: Level


WIND_BANDS = (
    Band(25.0, Level.CLEAR),
    Band(35.0, Level.CAUTION),
    Band(45.0, Level.WARNING),
    Band(55.0, Level.SEVERE),
)
RAIN_BANDS = (
    Band(0.10, Level.CLEAR),
    Band(0.25, Level.CAUTION),
    Band(0.50, Level.WARNING),
)
SNOW_BANDS = (
    Band(0.50, Level.CLEAR),
    Band(1.00, Level.CAUTION),
    Band(2.00, Level.WARNING),
)

HEAVY_LOAD_LBS = 30_000
VERY_HEAVY_LOAD_LBS = 40_000


def _banded(value: float, bands: tuple[Band, ...], ceiling: float) -> Level:
    for band in bands:
        if value < band.below:
            return band.level
    return Level.SEVERE if value <= ceiling else Level.NO_GO


def grade_wind(mph: float) -> Level:
    if mph >= 55.0:
        return Level.NO_GO
    for band in WIND_BANDS:
        if mph < band.below:
            return band.level
    return Level.SEVERE


def grade_rain(inches_per_hour: float) -> Level:
    return _banded(inches_per_hour, RAIN_BANDS, ceiling=1.00)


def grade_snow(inches_per_hour: float) -> Level:
    return _banded(inches_per_hour, SNOW_BANDS, ceiling=3.00)


def load_override(wind_mph: float | None, load_lbs: int, level: Level) -> tuple[Level, str | None]:
    if wind_mph is None:
        return level, None
    if wind_mph >= 55.0:
        return Level.NO_GO, "Wind at or above 55 mph closes the route for every load."
    if 45.0 <= wind_mph < 55.0 and load_lbs > HEAVY_LOAD_LBS:
        return Level.NO_GO, "45-54 mph wind with a load above 30,000 lb is a No-Go."
    if 35.0 <= wind_mph < 45.0 and load_lbs > VERY_HEAVY_LOAD_LBS:
        return max(level, Level.SEVERE), "35-44 mph wind with a load above 40,000 lb is at least Severe."
    return level, None


@dataclass(frozen=True)
class Assessment:
    level: Level
    wind: Level | None
    rain: Level | None
    snow: Level | None
    override: str | None
    complete: bool
    rated: bool


def evaluate(
    wind_mph: float | None,
    rain_in_hr: float | None,
    snow_in_hr: float | None,
    load_lbs: int,
) -> Assessment:
    wind = grade_wind(wind_mph) if wind_mph is not None else None
    rain = grade_rain(rain_in_hr) if rain_in_hr is not None else None
    snow = grade_snow(snow_in_hr) if snow_in_hr is not None else None

    known = [level for level in (wind, rain, snow) if level is not None]
    if not known:
        return Assessment(Level.CLEAR, None, None, None, None, complete=False, rated=False)

    level, override = load_override(wind_mph, load_lbs, max(known))
    return Assessment(
        level=level,
        wind=wind,
        rain=rain,
        snow=snow,
        override=override,
        complete=wind is not None and rain is not None and snow is not None,
        rated=True,
    )
