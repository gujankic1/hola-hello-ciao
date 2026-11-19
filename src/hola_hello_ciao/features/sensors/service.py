from sqlalchemy.orm import Session

from hola_hello_ciao.core.errors import NotFoundError
from hola_hello_ciao.features.sensors import repository
from hola_hello_ciao.features.sensors.schemas import SensorCreate, SensorRead


def create_sensor(session: Session, data: SensorCreate) -> SensorRead:
    sensor = repository.add(session, data.name)
    return SensorRead.model_validate(sensor)


def get_sensor(session: Session, sensor_id: int) -> SensorRead:
    sensor = repository.get(session, sensor_id)
    if sensor is None:
        raise NotFoundError(f"Sensor {sensor_id} not found")
    return SensorRead.model_validate(sensor)


def ensure_sensors_exist(session: Session, sensor_ids: list[int]) -> None:
    """NotFoundError naming every unknown id."""
    found = repository.existing_ids(session, sensor_ids)
    missing = [i for i in sensor_ids if i not in found]
    if missing:
        raise NotFoundError(f"Sensors not found: {', '.join(map(str, missing))}")


def list_sensors(session: Session) -> list[SensorRead]:
    return [SensorRead.model_validate(s) for s in repository.list_all(session)]
