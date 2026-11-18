from sqlalchemy.orm import Session

from hola_hello_ciao.core.errors import ConflictError
from hola_hello_ciao.readings import repository
from hola_hello_ciao.readings.schemas import ReadingCreate, ReadingCreated
from hola_hello_ciao.sensors.service import get_sensor


def ingest(session: Session, sensor_id: int, data: ReadingCreate) -> ReadingCreated:
    """Store one row per metric, idempotently per (sensor, metric, recorded_at).

    Values already stored with the same value are skipped (a retry succeeds). A different
    value for an existing key raises ConflictError and stores nothing from this call.
    NotFoundError if the sensor is unknown.
    """
    sensor = get_sensor(session, sensor_id)
    existing = repository.find_values(session, sensor.id, list(data.metrics), data.recorded_at)
    conflicts = sorted(m.value for m, v in existing.items() if v != data.metrics[m])
    if conflicts:
        raise ConflictError(
            f"Sensor {sensor.id} already has different values at "
            f"{data.recorded_at.isoformat()} for: {', '.join(conflicts)}"
        )
    new = {m: v for m, v in data.metrics.items() if m not in existing}
    repository.add_many(session, sensor.id, new, data.recorded_at)
    return ReadingCreated(sensor_id=sensor.id, recorded_at=data.recorded_at, metrics=data.metrics)
