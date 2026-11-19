from types import SimpleNamespace
from unittest.mock import MagicMock, NonCallableMagicMock, create_autospec

import pytest

from hola_hello_ciao.core.errors import NotFoundError
from hola_hello_ciao.features.sensors import repository, service
from hola_hello_ciao.features.sensors.schemas import SensorCreate, SensorRead


@pytest.fixture
def repo(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = create_autospec(repository)
    monkeypatch.setattr(service, "repository", mock)
    return mock


def row(id: int, name: str | None = None) -> SimpleNamespace:
    """Looks like a Sensor ORM row to SensorRead.model_validate."""
    return SimpleNamespace(id=id, name=name)


def test_create_sensor_stores_name_and_returns_it(
    repo: MagicMock, fake_session: NonCallableMagicMock
) -> None:
    repo.add.return_value = row(7, "roof-station")

    result = service.create_sensor(fake_session, SensorCreate(name="roof-station"))

    repo.add.assert_called_once_with(fake_session, "roof-station")
    assert result == SensorRead(id=7, name="roof-station")


def test_get_sensor_returns_the_stored_sensor(
    repo: MagicMock, fake_session: NonCallableMagicMock
) -> None:
    repo.get.return_value = row(7, "roof-station")

    assert service.get_sensor(fake_session, 7) == SensorRead(id=7, name="roof-station")
    repo.get.assert_called_once_with(fake_session, 7)


def test_get_sensor_unknown_id_raises_not_found(
    repo: MagicMock, fake_session: NonCallableMagicMock
) -> None:
    repo.get.return_value = None

    with pytest.raises(NotFoundError, match="Sensor 999 not found"):
        service.get_sensor(fake_session, 999)


def test_ensure_sensors_exist_passes_for_known_ids(
    repo: MagicMock, fake_session: NonCallableMagicMock
) -> None:
    repo.find_existing_ids.return_value = {1, 2}

    service.ensure_sensors_exist(fake_session, [1, 2])

    repo.find_existing_ids.assert_called_once_with(fake_session, [1, 2])


def test_ensure_sensors_exist_names_every_missing_id_in_request_order(
    repo: MagicMock, fake_session: NonCallableMagicMock
) -> None:
    repo.find_existing_ids.return_value = {5}

    with pytest.raises(NotFoundError, match="Sensors not found: 999, 998"):
        service.ensure_sensors_exist(fake_session, [999, 5, 998])


def test_list_sensors_returns_every_stored_sensor(
    repo: MagicMock, fake_session: NonCallableMagicMock
) -> None:
    repo.list_all.return_value = [row(1, "a"), row(2)]

    assert service.list_sensors(fake_session) == [
        SensorRead(id=1, name="a"),
        SensorRead(id=2, name=None),
    ]
