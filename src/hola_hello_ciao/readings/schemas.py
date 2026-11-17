from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

Value = Annotated[float, Field(allow_inf_nan=False)]


class ReadingCreate(BaseModel):
    metrics: dict[str, Value]
    recorded_at: datetime | None = None

    @field_validator("metrics")
    @classmethod
    def _check_metrics(cls, metrics: dict[str, float]) -> dict[str, float]:
        if not metrics:
            raise ValueError("metrics must not be empty")
        cleaned: dict[str, float] = {}
        for name, value in metrics.items():
            name = name.strip()
            if not name:
                raise ValueError("metric names must not be blank")
            if name in cleaned:
                raise ValueError(f"duplicate metric name: {name}")
            cleaned[name] = value
        return cleaned

    @field_validator("recorded_at")
    @classmethod
    def _to_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class ReadingCreated(BaseModel):
    sensor_id: int
    recorded_at: datetime
    metrics: dict[str, float]
