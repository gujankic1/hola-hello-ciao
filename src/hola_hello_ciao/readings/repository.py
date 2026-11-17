from datetime import datetime

from sqlalchemy.orm import Session

from hola_hello_ciao.core.db import storage_errors
from hola_hello_ciao.readings.metrics import Metric
from hola_hello_ciao.readings.models import Reading


def add_many(
    session: Session, sensor_id: int, metrics: dict[Metric, float], recorded_at: datetime
) -> None:
    """Store one row per metric in one transaction. recorded_at must be UTC; stored naive."""
    naive_utc = recorded_at.replace(tzinfo=None)
    with storage_errors(session, "Could not store the reading"):
        session.add_all(
            Reading(sensor_id=sensor_id, metric=metric.value, value=value, recorded_at=naive_utc)
            for metric, value in metrics.items()
        )
        session.commit()
