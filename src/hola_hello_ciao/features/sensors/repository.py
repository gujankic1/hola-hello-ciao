from sqlalchemy import select
from sqlalchemy.orm import Session

from hola_hello_ciao.core.db import storage_errors
from hola_hello_ciao.features.sensors.models import Sensor


class SensorRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, name: str | None) -> Sensor:
        with storage_errors(self._session, "Could not store the sensor"):
            sensor = Sensor(name=name)
            self._session.add(sensor)
            self._session.commit()
            return sensor

    def get(self, sensor_id: int) -> Sensor | None:
        with storage_errors(self._session, "Could not load the sensor"):
            return self._session.get(Sensor, sensor_id)

    def find_existing_ids(self, sensor_ids: list[int]) -> set[int]:
        """The subset of sensor_ids that exist, in one query."""
        with storage_errors(self._session, "Could not load the sensors"):
            query = select(Sensor.id).where(Sensor.id.in_(sensor_ids))
            return set(self._session.scalars(query))

    def list_all(self) -> list[Sensor]:
        with storage_errors(self._session, "Could not load the sensors"):
            return list(self._session.scalars(select(Sensor).order_by(Sensor.id)))
