from datetime import UTC, datetime, timedelta
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from hola_hello_ciao.readings.metrics import Metric
from hola_hello_ciao.sensors.schemas import SensorId

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


class StatisticsQuery(BaseModel):
    """sensor_ids omitted = all sensors. Window: see ADR-004 (default last 24 h)."""

    model_config = ConfigDict(populate_by_name=True)

    sensor_ids: list[SensorId] | None = Field(default=None, min_length=1, max_length=MAX_SENSOR_IDS)
    metrics: list[MetricStat] = Field(min_length=1)
    from_: datetime | None = Field(default=None, alias="from")
    to: datetime | None = None

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

    @field_validator("from_", "to")
    @classmethod
    def _to_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def _check_window(self) -> "StatisticsQuery":
        if self.from_ is not None and self.to is None:
            raise ValueError("'to' is required when 'from' is given")
        if self.from_ is not None and self.to is not None:
            if not MIN_RANGE <= self.to - self.from_ <= MAX_RANGE:
                raise ValueError("date range must be between 1 day and 31 days")
        return self


class StatisticsResult(BaseModel):
    sensor_id: int
    metric: Metric
    stat: Stat
    value: float | None  # null: no readings in the window
    count: int


class StatisticsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_: datetime = Field(alias="from")
    to: datetime
    results: list[StatisticsResult]
