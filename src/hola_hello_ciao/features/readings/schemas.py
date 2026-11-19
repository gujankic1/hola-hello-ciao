from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field
from pydantic.config import JsonDict

from hola_hello_ciao.core.types import UtcDatetime
from hola_hello_ciao.features.shared.metrics import Metric

MetricValue = Annotated[float, Field(allow_inf_nan=False)]

# Shown in Swagger as the example body; keep it valid input.
_METRICS_EXAMPLE: JsonDict = {"temperature": 21.5, "humidity": 40.0, "wind_speed": 3.2}
_RECORDED_AT_EXAMPLE = "2026-11-17T10:00:00Z"


class ReadingCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [{"metrics": _METRICS_EXAMPLE, "recorded_at": _RECORDED_AT_EXAMPLE}]
        },
    )

    metrics: Annotated[dict[Metric, MetricValue], Field(min_length=1)]
    recorded_at: UtcDatetime  # part of the reading's identity: (sensor, metric, recorded_at)


class ReadingCreated(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"sensor_id": 1, "recorded_at": _RECORDED_AT_EXAMPLE, "metrics": _METRICS_EXAMPLE}
            ]
        }
    )

    sensor_id: int
    recorded_at: datetime
    metrics: dict[Metric, float]
