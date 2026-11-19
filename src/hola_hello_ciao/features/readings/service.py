from sqlalchemy.orm import Session

from hola_hello_ciao.core.errors import ConflictError
from hola_hello_ciao.features.readings import repository
from hola_hello_ciao.features.readings.schemas import ReadingCreate, ReadingCreated
from hola_hello_ciao.features.sensors.service import get_sensor


def ingest_reading(session: Session, sensor_id: int, reading: ReadingCreate) -> ReadingCreated:
    """Store one row per metric, idempotently per (sensor, metric, recorded_at).

    Values already stored with the same value are skipped (a retry succeeds). A different
    value for an existing key raises ConflictError and stores nothing from this call.
    NotFoundError if the sensor is unknown.
    """
    sensor = get_sensor(session, sensor_id)
    stored_value_by_metric = repository.find_stored_values(
        session, sensor.id, list(reading.metrics), reading.recorded_at
    )
    conflicting_metric_names = sorted(
        metric.value
        for metric, stored_value in stored_value_by_metric.items()
        if stored_value != reading.metrics[metric]
    )
    if conflicting_metric_names:
        raise ConflictError(
            f"Sensor {sensor.id} already has different values at "
            f"{reading.recorded_at.isoformat()} for: {', '.join(conflicting_metric_names)}"
        )

    new_value_by_metric = {
        metric: value
        for metric, value in reading.metrics.items()
        if metric not in stored_value_by_metric
    }
    repository.add_many(session, sensor.id, new_value_by_metric, reading.recorded_at)
    return ReadingCreated(
        sensor_id=sensor.id, recorded_at=reading.recorded_at, metrics=reading.metrics
    )
