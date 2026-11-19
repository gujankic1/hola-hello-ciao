from datetime import datetime, timedelta
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.config import JsonDict

from hola_hello_ciao.core.types import UtcDatetime
from hola_hello_ciao.features.sensors.schemas import SensorId
from hola_hello_ciao.features.shared.metrics import Metric

MIN_RANGE = timedelta(days=1)
MAX_RANGE = timedelta(days=31)  # "one month" (ADR-004)
DEFAULT_RANGE = timedelta(hours=24)
# Each id becomes a bound SQL parameter; stay far below SQLite's limit (32766). Omit
# sensor_ids to query all sensors.
MAX_SENSOR_IDS = 1000


class Stat(StrEnum):
    MIN = "min"
    MAX = "max"
    SUM = "sum"
    AVG = "avg"


class MetricStat(BaseModel):
    name: Metric
    stat: Stat


# Shown in Swagger as the example body; keep it valid input.
# No window, so "Try it out" covers the last 24 h and works against seeded data.
_QUERY_EXAMPLE: JsonDict = {
    "sensor_ids": [1, 2],
    "metrics": [{"name": "temperature", "stat": "avg"}, {"name": "wind_speed", "stat": "max"}],
}
# FastAPI strips nulls from the served schema, so no null values here (see `value`).
_RESPONSE_EXAMPLE: JsonDict = {
    "from": "2026-11-16T10:00:00Z",
    "to": "2026-11-17T10:00:00Z",
    "sensors": [
        {
            "sensor_id": 1,
            "results": [
                {"metric": "temperature", "stat": "avg", "value": 11.5, "count": 24},
                {"metric": "wind_speed", "stat": "max", "value": 9.8, "count": 24},
            ],
        },
        {
            "sensor_id": 2,
            "results": [
                {"metric": "temperature", "stat": "avg", "value": 9.0, "count": 24},
                {"metric": "wind_speed", "stat": "max", "value": 7.4, "count": 24},
            ],
        },
    ],
}


class StatisticsQuery(BaseModel):
    """Omit `sensor_ids` to query all sensors. Omit `from` and `to` for the last 24 hours, or
    give only `to` for the 24 hours before it. A window must be 1 to 31 days."""

    # Window rules: ADR-004. Docstrings here end up in OpenAPI.

    model_config = ConfigDict(
        populate_by_name=True, json_schema_extra={"examples": [_QUERY_EXAMPLE]}
    )

    sensor_ids: list[SensorId] | None = Field(default=None, min_length=1, max_length=MAX_SENSOR_IDS)
    metrics: list[MetricStat] = Field(min_length=1)
    from_: UtcDatetime | None = Field(default=None, alias="from")
    to: UtcDatetime | None = None

    @field_validator("sensor_ids")
    @classmethod
    def _no_duplicate_sensor_ids(cls, ids: list[int] | None) -> list[int] | None:
        if ids is not None and len(set(ids)) != len(ids):
            raise ValueError("duplicate sensor id")
        return ids

    @field_validator("metrics")
    @classmethod
    def _no_duplicate_pairs(cls, metrics: list[MetricStat]) -> list[MetricStat]:
        pairs = [(m.name, m.stat) for m in metrics]
        if len(set(pairs)) != len(pairs):
            raise ValueError("duplicate metric/stat pair")
        return metrics

    @model_validator(mode="after")
    def _check_window(self) -> "StatisticsQuery":
        if self.from_ is not None and self.to is None:
            raise ValueError("'to' is required when 'from' is given")
        if self.from_ is not None and self.to is not None:
            if self.from_ >= self.to:
                raise ValueError("'from' must be before 'to'")
            if not MIN_RANGE <= self.to - self.from_ <= MAX_RANGE:
                raise ValueError("date range must be between 1 day and 31 days")
        return self


class StatisticsResult(BaseModel):
    metric: Metric
    stat: Stat
    value: float | None = Field(description="`null` when the sensor has no readings in the window")
    count: int


class SensorStatistics(BaseModel):
    """One requested statistic per metric, in the order the query lists them."""

    sensor_id: int
    results: list[StatisticsResult]


class StatisticsResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True, json_schema_extra={"examples": [_RESPONSE_EXAMPLE]}
    )

    from_: datetime = Field(alias="from")
    to: datetime
    sensors: list[SensorStatistics] = Field(
        description="In the order of `sensor_ids`; when querying all sensors, sorted by `sensor_id`"
    )
