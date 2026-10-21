from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="FC_", extra="ignore")

    ors_api_key: str = ""
    openrouteservice_base_url: str = "https://api.openrouteservice.org"
    osrm_base_url: str = "https://router.project-osrm.org"
    open_meteo_base_url: str = "https://api.open-meteo.com/v1"
    nominatim_base_url: str = "https://nominatim.openstreetmap.org"
    user_agent: str = "fleetcast/1.0"
    cors_origins: str = "http://localhost:5174,http://127.0.0.1:5174"

    request_timeout_s: float = 15.0
    geocode_ttl_s: int = 86_400
    route_ttl_s: int = 3_600
    weather_ttl_s: int = 1_800
    trip_ttl_s: int = 21_600

    alternatives: int = 3
    max_forecast_days: int = 16
    heatmap_hours: int = 48


@lru_cache
def settings() -> Settings:
    return Settings()
