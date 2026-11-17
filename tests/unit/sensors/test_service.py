import pytest
from sqlalchemy.orm import Session

from hola_hello_ciao.core.errors import NotFoundError
from hola_hello_ciao.sensors.schemas import SensorCreate
from hola_hello_ciao.sensors.service import create_sensor, get_sensor


def test_create_sensor_persists_and_can_be_fetched(session: Session) -> None:
    sensor = create_sensor(session, SensorCreate(name="roof-station"))

    fetched = get_sensor(session, sensor.id)

    assert fetched.id == sensor.id
    assert fetched.name == "roof-station"


def test_get_sensor_unknown_id_raises_not_found(session: Session) -> None:
    with pytest.raises(NotFoundError):
        get_sensor(session, 999)
