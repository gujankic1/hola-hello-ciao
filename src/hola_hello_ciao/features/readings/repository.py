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

    def add_many_unless_conflicting(
        self, sensor_id: int, value_by_metric: dict[Metric, float], recorded_at: datetime
    ) -> list[Metric]:
        """Store one row per metric, all or nothing; return the metrics that conflict.

        recorded_at must be UTC; it is stored naive. A metric already stored with the same
        value is skipped, so a retry stores nothing new. If any metric is already stored with a
        different value, nothing from this call is stored and those metrics are returned.

        The insert and the read-back run in one transaction. The INSERT takes SQLite's write
        lock and holds it until commit or rollback, so no other request can write in between:
        concurrent calls with different values cannot both succeed (ADR-003).
        """
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
        stored_values_query = select(Reading.metric, Reading.value).where(
            Reading.sensor_id == sensor_id,
            Reading.metric.in_([metric.value for metric in value_by_metric]),
            Reading.recorded_at == recorded_at_naive_utc,
        )
        with storage_errors(self._session, "Could not store the reading"):
            self._session.execute(insert(Reading).values(rows).on_conflict_do_nothing())
            stored_value_by_metric = {
                Metric(metric): value
                for metric, value in self._session.execute(stored_values_query)
            }
            conflicting_metrics = [
                metric
                for metric, value in value_by_metric.items()
                if stored_value_by_metric[metric] != value
            ]
            if conflicting_metrics:
                self._session.rollback()
            else:
                self._session.commit()
            return conflicting_metrics
