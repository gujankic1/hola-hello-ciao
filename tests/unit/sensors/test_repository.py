import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from hola_hello_ciao.core.errors import StorageError
from hola_hello_ciao.features.sensors.models import Sensor
from hola_hello_ciao.features.sensors.repository import SensorRepository


@pytest.fixture
def repository(session: Session) -> SensorRepository:
    return SensorRepository(session)


def test_add_then_get_returns_the_sensor(repository: SensorRepository) -> None:
    sensor = repository.add("roof-station")

    fetched = repository.get(sensor.id)

    assert fetched is not None
    assert (fetched.id, fetched.name) == (sensor.id, "roof-station")


def test_get_unknown_id_returns_none(repository: SensorRepository) -> None:
    assert repository.get(999) is None


def test_add_raises_storage_error_when_write_fails(
    repository: SensorRepository, engine: Engine
) -> None:
    Sensor.__table__.drop(engine)

    with pytest.raises(StorageError, match="Could not store the sensor"):
        repository.add("roof-station")


def test_get_raises_storage_error_when_read_fails(
    repository: SensorRepository, engine: Engine
) -> None:
    Sensor.__table__.drop(engine)

    with pytest.raises(StorageError, match="Could not load the sensor"):
        repository.get(1)


def test_existing_ids_returns_only_known_ids(repository: SensorRepository) -> None:
    sensor = repository.add("roof-station")

    assert repository.find_existing_ids([sensor.id, 999]) == {sensor.id}


def test_existing_ids_raises_storage_error_when_read_fails(
    repository: SensorRepository, engine: Engine
) -> None:
    Sensor.__table__.drop(engine)

    with pytest.raises(StorageError, match="Could not load the sensors"):
        repository.find_existing_ids([1])


def test_list_all_returns_sensors_ordered_by_id(repository: SensorRepository) -> None:
    first = repository.add("a")
    second = repository.add(None)

    assert [sensor.id for sensor in repository.list_all()] == [first.id, second.id]


def test_list_all_raises_storage_error(repository: SensorRepository, engine: Engine) -> None:
    Sensor.__table__.drop(engine)

    with pytest.raises(StorageError, match="Could not load the sensors"):
        repository.list_all()
