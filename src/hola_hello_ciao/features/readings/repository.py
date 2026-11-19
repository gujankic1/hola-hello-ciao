from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from hola_hello_ciao.core.db import storage_errors
from hola_hello_ciao.features.readings.models import Reading
from hola_hello_ciao.features.shared.metrics import Metric


class ReadingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_stored_values(
        self, sensor_id: int, metrics: list[Metric], recorded_at: datetime
    ) -> dict[Metric, float]:
        """Already stored values for these metrics at exactly recorded_at (UTC)."""
        query = select(Reading.metric, Reading.value).where(
            Reading.sensor_id == sensor_id,
            Reading.metric.in_([metric.value for metric in metrics]),
            Reading.recorded_at == recorded_at.replace(tzinfo=None),
        )
        with storage_errors(self._session, "Could not load existing readings"):
            return {Metric(metric): value for metric, value in self._session.execute(query)}

    def add_many(
        self, sensor_id: int, value_by_metric: dict[Metric, float], recorded_at: datetime
    ) -> None:
        """Store one row per metric in one transaction. recorded_at must be UTC; stored naive.

        Rows whose (sensor_id, metric, recorded_at) already exists are skipped, so a concurrent
        retry of the same request cannot fail or store a duplicate.
        """
        if not value_by_metric:
            return
        recorded_at_naive_utc = recorded_at.replace(tzinfo=None)
        rows = [
            {
                "sensor_id": sensor_id,
                "metric": metric.value,
                "value": value,
                "recorded_at": recorded_at_naive_utc,
            }
            for metric, value in value_by_metric.items()
        ]
        with storage_errors(self._session, "Could not store the reading"):
            self._session.execute(insert(Reading).values(rows).on_conflict_do_nothing())
            self._session.commit()
