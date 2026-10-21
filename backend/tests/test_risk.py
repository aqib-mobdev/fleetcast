import pytest

from app.domain.risk import evaluate, grade_rain, grade_snow, grade_wind
from app.domain.severity import Level as L


@pytest.mark.parametrize(
    "mph,level",
    [
        (0, L.CLEAR),
        (24.99, L.CLEAR),
        (25.0, L.CAUTION),
        (34.99, L.CAUTION),
        (35.0, L.WARNING),
        (44.99, L.WARNING),
        (45.0, L.SEVERE),
        (54.99, L.SEVERE),
        (55.0, L.NO_GO),
        (70.0, L.NO_GO),
    ],
)
def test_wind_bands(mph, level):
    assert grade_wind(mph) is level


@pytest.mark.parametrize(
    "rate,level",
    [
        (0.0, L.CLEAR),
        (0.099, L.CLEAR),
        (0.10, L.CAUTION),
        (0.249, L.CAUTION),
        (0.25, L.WARNING),
        (0.499, L.WARNING),
        (0.50, L.SEVERE),
        (1.00, L.SEVERE),
        (1.001, L.NO_GO),
        (4.0, L.NO_GO),
    ],
)
def test_rain_bands(rate, level):
    assert grade_rain(rate) is level


@pytest.mark.parametrize(
    "rate,level",
    [
        (0.0, L.CLEAR),
        (0.49, L.CLEAR),
        (0.50, L.CAUTION),
        (0.999, L.CAUTION),
        (1.00, L.WARNING),
        (1.999, L.WARNING),
        (2.00, L.SEVERE),
        (3.00, L.SEVERE),
        (3.001, L.NO_GO),
        (8.0, L.NO_GO),
    ],
)
def test_snow_bands(rate, level):
    assert grade_snow(rate) is level


def test_heavy_load_closes_45_to_54_wind():
    assert evaluate(50.0, 0.0, 0.0, 30_001).level is L.NO_GO
    assert evaluate(45.0, 0.0, 0.0, 45_000).level is L.NO_GO
    assert evaluate(50.0, 0.0, 0.0, 30_000).level is L.SEVERE


def test_very_heavy_load_escalates_35_to_44_wind():
    assert evaluate(40.0, 0.0, 0.0, 40_001).level is L.SEVERE
    assert evaluate(35.0, 0.0, 0.0, 60_000).level is L.SEVERE
    assert evaluate(40.0, 0.0, 0.0, 40_000).level is L.WARNING
    assert evaluate(34.9, 0.0, 0.0, 80_000).level is L.CAUTION


def test_55_mph_is_no_go_for_empty_truck():
    assert evaluate(55.0, 0.0, 0.0, 0).level is L.NO_GO


def test_highest_dimension_wins():
    result = evaluate(30.0, 0.9, 0.0, 0)
    assert result.level is L.SEVERE
    assert result.wind is L.CAUTION
    result = evaluate(58.0, 0.1, 1.5, 0)
    assert result.level is L.NO_GO


def test_unrated_when_everything_missing():
    result = evaluate(None, None, None, 20_000)
    assert result.rated is False
    assert result.complete is False


def test_partial_data_is_rated_but_incomplete():
    result = evaluate(50.0, None, None, 35_000)
    assert result.rated is True
    assert result.complete is False
    assert result.level is L.NO_GO
    assert result.override is not None


def test_override_requires_wind_data():
    result = evaluate(None, 0.3, None, 80_000)
    assert result.level is L.WARNING
    assert result.override is None
