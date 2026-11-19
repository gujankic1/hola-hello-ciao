from sqlalchemy.orm import Session

from hola_hello_ciao.core.errors import NotFoundError
from hola_hello_ciao.features.sensors import repository
from hola_hello_ciao.features.sensors.schemas import SensorCreate, SensorRead


def create_sensor(session: Session, new_sensor: SensorCreate) -> SensorRead:
    sensor = repository.add(session, new_sensor.name)
    return SensorRead.model_validate(sensor)


def get_sensor(session: Session, sensor_id: int) -> SensorRead:
    sensor = repository.get(session, sensor_id)
    if sensor is None:
        raise NotFoundError(f"Sensor {sensor_id} not found")
    return SensorRead.model_validate(sensor)


def ensure_sensors_exist(session: Session, sensor_ids: list[int]) -> None:
    """Raise NotFoundError naming every unknown id, in the order they were given."""
    existing_ids = repository.find_existing_ids(session, sensor_ids)
    missing_ids = [sensor_id for sensor_id in sensor_ids if sensor_id not in existing_ids]
    if missing_ids:
        raise NotFoundError(f"Sensors not found: {', '.join(map(str, missing_ids))}")


def list_sensors(session: Session) -> list[SensorRead]:
    return [SensorRead.model_validate(sensor) for sensor in repository.list_all(session)]
