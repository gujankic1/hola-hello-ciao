from types import SimpleNamespace
from unittest.mock import NonCallableMagicMock, create_autospec

import pytest

from hola_hello_ciao.core.errors import NotFoundError
from hola_hello_ciao.features.sensors.repository import SensorRepository
from hola_hello_ciao.features.sensors.schemas import SensorCreate, SensorRead
from hola_hello_ciao.features.sensors.service import SensorService


@pytest.fixture
def repository() -> NonCallableMagicMock:
    return create_autospec(SensorRepository, instance=True)


@pytest.fixture
def service(repository: NonCallableMagicMock) -> SensorService:
    return SensorService(repository)


def row(id: int, name: str | None = None) -> SimpleNamespace:
    """Looks like a Sensor ORM row to SensorRead.model_validate."""
    return SimpleNamespace(id=id, name=name)


def test_create_sensor_stores_name_and_returns_it(
    service: SensorService, repository: NonCallableMagicMock
) -> None:
    repository.add.return_value = row(7, "roof-station")

    result = service.create_sensor(SensorCreate(name="roof-station"))

    repository.add.assert_called_once_with("roof-station")
    assert result == SensorRead(id=7, name="roof-station")


def test_get_sensor_returns_the_stored_sensor(
    service: SensorService, repository: NonCallableMagicMock
) -> None:
    repository.get.return_value = row(7, "roof-station")

    assert service.get_sensor(7) == SensorRead(id=7, name="roof-station")
    repository.get.assert_called_once_with(7)


def test_get_sensor_unknown_id_raises_not_found(
    service: SensorService, repository: NonCallableMagicMock
) -> None:
    repository.get.return_value = None

    with pytest.raises(NotFoundError, match="Sensor 999 not found"):
        service.get_sensor(999)


def test_ensure_sensors_exist_passes_for_known_ids(
    service: SensorService, repository: NonCallableMagicMock
) -> None:
    repository.find_existing_ids.return_value = {1, 2}

    service.ensure_sensors_exist([1, 2])

    repository.find_existing_ids.assert_called_once_with([1, 2])


def test_ensure_sensors_exist_names_every_missing_id_in_request_order(
    service: SensorService, repository: NonCallableMagicMock
) -> None:
    repository.find_existing_ids.return_value = {5}

    with pytest.raises(NotFoundError, match="Sensors not found: 999, 998"):
        service.ensure_sensors_exist([999, 5, 998])


def test_list_sensors_returns_every_stored_sensor(
    service: SensorService, repository: NonCallableMagicMock
) -> None:
    repository.list_all.return_value = [row(1, "a"), row(2)]

    assert service.list_sensors() == [
        SensorRead(id=1, name="a"),
        SensorRead(id=2, name=None),
    ]
