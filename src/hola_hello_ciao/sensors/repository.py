from sqlalchemy.orm import Session

from hola_hello_ciao.core.db import storage_errors
from hola_hello_ciao.sensors.models import Sensor


def add(session: Session, name: str | None) -> Sensor:
    with storage_errors(session, "Could not store the sensor"):
        sensor = Sensor(name=name)
        session.add(sensor)
        session.commit()
        return sensor


def get(session: Session, sensor_id: int) -> Sensor | None:
    with storage_errors(session, "Could not load the sensor"):
        return session.get(Sensor, sensor_id)
