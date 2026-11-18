from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

from hola_hello_ciao.readings.metrics import Metric

Value = Annotated[float, Field(allow_inf_nan=False)]


class ReadingCreate(BaseModel):
    metrics: Annotated[dict[Metric, Value], Field(min_length=1)]
    recorded_at: datetime  # part of the reading's identity: (sensor, metric, recorded_at)

    @field_validator("recorded_at")
    @classmethod
    def _to_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class ReadingCreated(BaseModel):
    sensor_id: int
    recorded_at: datetime
    metrics: dict[Metric, float]
