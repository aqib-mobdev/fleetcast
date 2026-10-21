from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class AnalyzeBody(BaseModel):
    origin: str = Field(min_length=2, max_length=200)
    destination: str = Field(min_length=2, max_length=200)
    depart_at: datetime
    load_lbs: int = Field(ge=0, le=80_000)
    interval_mi: Literal[10, 25, 50] = 25

    @field_validator("depart_at")
    @classmethod
    def validate_depart_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        now = datetime.now(UTC)
        if value < now - timedelta(minutes=5):
            raise ValueError("depart_at must not be in the past")
        if value > now + timedelta(days=15):
            raise ValueError("depart_at is beyond the 15-day forecast horizon")
        return value
