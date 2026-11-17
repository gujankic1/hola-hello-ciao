from datetime import UTC, datetime

from sqlalchemy.orm import Session

from hola_hello_ciao.readings import repository
from hola_hello_ciao.readings.schemas import ReadingCreate, ReadingCreated
from hola_hello_ciao.sensors.service import get_sensor


def ingest(session: Session, sensor_id: int, data: ReadingCreate) -> ReadingCreated:
    """Store one row per metric; NotFoundError if the sensor is unknown."""
    sensor = get_sensor(session, sensor_id)
    recorded_at = data.recorded_at or datetime.now(UTC)
    repository.add_many(session, sensor.id, data.metrics, recorded_at)
    return ReadingCreated(sensor_id=sensor.id, recorded_at=recorded_at, metrics=data.metrics)
