from hola_hello_ciao.core.errors import NotFoundError
from hola_hello_ciao.features.sensors.repository import SensorRepository
from hola_hello_ciao.features.sensors.schemas import SensorCreate, SensorRead


class SensorService:
    def __init__(self, repository: SensorRepository) -> None:
        self._repository = repository

    def create_sensor(self, new_sensor: SensorCreate) -> SensorRead:
        return SensorRead.model_validate(self._repository.add(new_sensor.name))

    def get_sensor(self, sensor_id: int) -> SensorRead:
        sensor = self._repository.get(sensor_id)
        if sensor is None:
            raise NotFoundError(f"Sensor {sensor_id} not found")
        return SensorRead.model_validate(sensor)

    def ensure_sensors_exist(self, sensor_ids: list[int]) -> None:
        """Raise NotFoundError naming every unknown id, in the order they were given."""
        existing_ids = self._repository.find_existing_ids(sensor_ids)
        missing_ids = [sensor_id for sensor_id in sensor_ids if sensor_id not in existing_ids]
        if missing_ids:
            raise NotFoundError(f"Sensors not found: {', '.join(map(str, missing_ids))}")

    def list_sensors(self) -> list[SensorRead]:
        return [SensorRead.model_validate(sensor) for sensor in self._repository.list_all()]
