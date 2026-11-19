from hola_hello_ciao.core.errors import ConflictError
from hola_hello_ciao.features.readings.repository import ReadingRepository
from hola_hello_ciao.features.readings.schemas import ReadingCreate, ReadingCreated
from hola_hello_ciao.features.sensors.service import SensorService


class ReadingService:
    def __init__(self, repository: ReadingRepository, sensor_service: SensorService) -> None:
        self._repository = repository
        self._sensor_service = sensor_service

    def ingest_reading(self, sensor_id: int, reading: ReadingCreate) -> ReadingCreated:
        """Store one row per metric, idempotently per (sensor, metric, recorded_at).

        Values already stored with the same value are skipped (a retry succeeds). A different
        value for an existing key raises ConflictError and stores nothing from this call.
        NotFoundError if the sensor is unknown.
        """
        sensor = self._sensor_service.get_sensor(sensor_id)
        conflicting_metrics = self._repository.add_many_unless_conflicting(
            sensor.id, reading.metrics, reading.recorded_at
        )
        if conflicting_metrics:
            conflicting_metric_names = sorted(metric.value for metric in conflicting_metrics)
            raise ConflictError(
                f"Sensor {sensor.id} already has different values at "
                f"{reading.recorded_at.isoformat()} for: {', '.join(conflicting_metric_names)}"
            )
        return ReadingCreated(
            sensor_id=sensor.id, recorded_at=reading.recorded_at, metrics=reading.metrics
        )
