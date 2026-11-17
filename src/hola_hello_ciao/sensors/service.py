from sqlalchemy.orm import Session

from hola_hello_ciao.core.errors import NotFoundError
from hola_hello_ciao.sensors import repository
from hola_hello_ciao.sensors.schemas import SensorCreate, SensorRead


def create_sensor(session: Session, data: SensorCreate) -> SensorRead:
    sensor = repository.add(session, data.name)
    return SensorRead(id=sensor.id, name=sensor.name)


def get_sensor(session: Session, sensor_id: int) -> SensorRead:
    sensor = repository.get(session, sensor_id)
    if sensor is None:
        raise NotFoundError(f"Sensor {sensor_id} not found")
    return SensorRead(id=sensor.id, name=sensor.name)
