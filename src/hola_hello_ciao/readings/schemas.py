from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field

from hola_hello_ciao.core.types import UtcDatetime
from hola_hello_ciao.readings.metrics import Metric

Value = Annotated[float, Field(allow_inf_nan=False)]


class ReadingCreate(BaseModel):
    metrics: Annotated[dict[Metric, Value], Field(min_length=1)]
    recorded_at: UtcDatetime  # part of the reading's identity: (sensor, metric, recorded_at)


class ReadingCreated(BaseModel):
    sensor_id: int
    recorded_at: datetime
    metrics: dict[Metric, float]
