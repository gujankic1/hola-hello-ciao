from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from hola_hello_ciao.core.db import storage_errors
from hola_hello_ciao.readings.metrics import Metric
from hola_hello_ciao.readings.models import Reading


def find_values(
    session: Session, sensor_id: int, metrics: list[Metric], recorded_at: datetime
) -> dict[Metric, float]:
    """Already stored values for these metrics at exactly recorded_at (UTC)."""
    query = select(Reading.metric, Reading.value).where(
        Reading.sensor_id == sensor_id,
        Reading.metric.in_([m.value for m in metrics]),
        Reading.recorded_at == recorded_at.replace(tzinfo=None),
    )
    with storage_errors(session, "Could not load existing readings"):
        return {Metric(metric): value for metric, value in session.execute(query)}


def add_many(
    session: Session, sensor_id: int, metrics: dict[Metric, float], recorded_at: datetime
) -> None:
    """Store one row per metric in one transaction. recorded_at must be UTC; stored naive.

    Rows whose (sensor_id, metric, recorded_at) already exists are skipped, so a concurrent
    retry of the same request cannot fail or store a duplicate.
    """
    if not metrics:
        return
    naive_utc = recorded_at.replace(tzinfo=None)
    rows = [
        {"sensor_id": sensor_id, "metric": m.value, "value": v, "recorded_at": naive_utc}
        for m, v in metrics.items()
    ]
    with storage_errors(session, "Could not store the reading"):
        session.execute(insert(Reading).values(rows).on_conflict_do_nothing())
        session.commit()
