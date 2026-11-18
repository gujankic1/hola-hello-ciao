from datetime import datetime
from typing import NamedTuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from hola_hello_ciao.core.db import storage_errors
from hola_hello_ciao.readings.metrics import Metric
from hola_hello_ciao.readings.models import Reading
from hola_hello_ciao.sensors.models import Sensor


class Aggregate(NamedTuple):
    sensor_id: int
    metric: str
    min: float
    max: float
    sum: float
    avg: float
    n: int


def aggregate(
    session: Session,
    sensor_ids: list[int] | None,
    metrics: list[Metric],
    start: datetime,
    end: datetime,
) -> list[Aggregate]:
    """Aggregates per (sensor, metric) over [start, end), UTC. sensor_ids None = all."""
    query = (
        select(
            Reading.sensor_id,
            Reading.metric,
            func.min(Reading.value),
            func.max(Reading.value),
            func.sum(Reading.value),
            func.avg(Reading.value),
            func.count(),
        )
        .where(
            Reading.metric.in_([m.value for m in metrics]),
            Reading.recorded_at >= start.replace(tzinfo=None),
            Reading.recorded_at < end.replace(tzinfo=None),
        )
        .group_by(Reading.sensor_id, Reading.metric)
    )
    # Always constrain sensor_id, the index's leading column: SQLite then seeks one index
    # range per sensor instead of scanning the whole index (chapter 11, R1).
    query = query.where(
        Reading.sensor_id.in_(select(Sensor.id) if sensor_ids is None else sensor_ids)
    )
    with storage_errors(session, "Could not load statistics"):
        return [Aggregate(*row) for row in session.execute(query)]
