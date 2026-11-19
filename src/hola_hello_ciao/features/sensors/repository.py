from sqlalchemy import select
from sqlalchemy.orm import Session

from hola_hello_ciao.core.db import storage_errors
from hola_hello_ciao.features.sensors.models import Sensor


def add(session: Session, name: str | None) -> Sensor:
    with storage_errors(session, "Could not store the sensor"):
        sensor = Sensor(name=name)
        session.add(sensor)
        session.commit()
        return sensor


def get(session: Session, sensor_id: int) -> Sensor | None:
    with storage_errors(session, "Could not load the sensor"):
        return session.get(Sensor, sensor_id)


def find_existing_ids(session: Session, sensor_ids: list[int]) -> set[int]:
    """The subset of sensor_ids that exist, in one query."""
    with storage_errors(session, "Could not load the sensors"):
        return set(session.scalars(select(Sensor.id).where(Sensor.id.in_(sensor_ids))))


def list_all(session: Session) -> list[Sensor]:
    with storage_errors(session, "Could not load the sensors"):
        return list(session.scalars(select(Sensor).order_by(Sensor.id)))
