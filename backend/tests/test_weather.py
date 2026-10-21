from datetime import timedelta

from app.providers.weather import _normalize, sample
from tests.conftest import load


def forecast(index: int = 0):
    return _normalize(load("meteo_stops.json")[index])


def test_snowfall_converts_cm_to_inches():
    data = forecast()
    assert data.snow_in_hr[6] == 1.0          # 2.54 cm
    assert data.snow_in_hr[8] == 4.0          # 10.16 cm
    assert data.unit_notes


def test_wind_and_rain_units_pass_through():
    data = forecast()
    assert data.wind_mph[5] == 57
    assert data.rain_in_hr[5] == 0.8


def test_sample_interpolates_between_hours():
    data = forecast()
    moment = data.times[1] + timedelta(minutes=30)
    now = sample(data, moment)
    assert now.available
    assert now.wind_mph == 18
    assert now.rain_in_hr == 0.02
    assert now.interpolated is True


def test_sample_before_window_is_unavailable():
    data = forecast()
    now = sample(data, data.times[0] - timedelta(hours=2))
    assert now.available is False
    assert "before" in now.reason


def test_sample_after_horizon_is_unavailable():
    data = forecast()
    now = sample(data, data.times[-1] + timedelta(hours=1))
    assert now.available is False
    assert "beyond" in now.reason


def test_temperature_is_fahrenheit():
    data = forecast()
    now = sample(data, data.times[0])
    assert now.temp_f == 69.8  # 21 C


def test_condition_comes_from_nearest_hour():
    data = forecast()
    now = sample(data, data.times[5] + timedelta(minutes=5))
    assert now.code == 95
    assert now.condition == "Thunderstorm"


def test_gap_stays_missing():
    data = forecast()
    data.wind_mph[2] = None
    data.wind_mph[3] = None
    now = sample(data, data.times[2] + timedelta(minutes=30))
    assert now.wind_mph is None


def test_payload_rounding_and_source():
    data = forecast()
    now = sample(data, data.times[3])
    payload = now.payload()
    assert payload["source"] == "open-meteo"
    assert payload["wind_mph"] == 31
    assert payload["available"] is True
