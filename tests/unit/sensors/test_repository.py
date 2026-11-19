import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from hola_hello_ciao.core.errors import StorageError
from hola_hello_ciao.features.sensors import repository
from hola_hello_ciao.features.sensors.models import Sensor


def test_add_then_get_returns_the_sensor(session: Session) -> None:
    sensor = repository.add(session, "roof-station")

    fetched = repository.get(session, sensor.id)

    assert fetched is not None
    assert (fetched.id, fetched.name) == (sensor.id, "roof-station")


def test_get_unknown_id_returns_none(session: Session) -> None:
    assert repository.get(session, 999) is None


def test_add_raises_storage_error_when_write_fails(session: Session, engine: Engine) -> None:
    Sensor.__table__.drop(engine)

    with pytest.raises(StorageError, match="Could not store the sensor"):
        repository.add(session, "roof-station")


def test_get_raises_storage_error_when_read_fails(session: Session, engine: Engine) -> None:
    Sensor.__table__.drop(engine)

    with pytest.raises(StorageError, match="Could not load the sensor"):
        repository.get(session, 1)


def test_existing_ids_returns_only_known_ids(session: Session) -> None:
    sensor = repository.add(session, "roof-station")

    assert repository.existing_ids(session, [sensor.id, 999]) == {sensor.id}


def test_existing_ids_raises_storage_error_when_read_fails(
    session: Session, engine: Engine
) -> None:
    Sensor.__table__.drop(engine)

    with pytest.raises(StorageError, match="Could not load the sensors"):
        repository.existing_ids(session, [1])


def test_list_all_returns_sensors_ordered_by_id(session: Session) -> None:
    first = repository.add(session, "a")
    second = repository.add(session, None)

    assert [s.id for s in repository.list_all(session)] == [first.id, second.id]


def test_list_all_raises_storage_error(session: Session, engine: Engine) -> None:
    Sensor.__table__.drop(engine)

    with pytest.raises(StorageError, match="Could not load the sensors"):
        repository.list_all(session)
