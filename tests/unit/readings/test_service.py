from datetime import UTC, datetime
from unittest.mock import MagicMock, NonCallableMagicMock, create_autospec

import pytest

from hola_hello_ciao.core.errors import ConflictError, NotFoundError
from hola_hello_ciao.readings import repository, service
from hola_hello_ciao.readings.metrics import Metric
from hola_hello_ciao.readings.schemas import ReadingCreate, ReadingCreated
from hola_hello_ciao.sensors.schemas import SensorRead

TS = datetime(2026, 11, 17, 10, 0, tzinfo=UTC)
SENSOR_ID = 7


@pytest.fixture
def repo(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = create_autospec(repository)
    mock.find_values.return_value = {}
    monkeypatch.setattr(service, "repository", mock)
    return mock


@pytest.fixture
def get_sensor(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = create_autospec(service.get_sensor, return_value=SensorRead(id=SENSOR_ID, name=None))
    monkeypatch.setattr(service, "get_sensor", mock)
    return mock


def reading(**metrics: float) -> ReadingCreate:
    return ReadingCreate(metrics={Metric(m): v for m, v in metrics.items()}, recorded_at=TS)


@pytest.mark.usefixtures("get_sensor")
def test_ingest_stores_every_metric_and_echoes_input(
    repo: MagicMock, fake_session: NonCallableMagicMock
) -> None:
    result = service.ingest(fake_session, SENSOR_ID, reading(temperature=1.5, humidity=40))

    repo.find_values.assert_called_once_with(
        fake_session, SENSOR_ID, [Metric.TEMPERATURE, Metric.HUMIDITY], TS
    )
    repo.add_many.assert_called_once_with(
        fake_session, SENSOR_ID, {Metric.TEMPERATURE: 1.5, Metric.HUMIDITY: 40}, TS
    )
    assert result == ReadingCreated(
        sensor_id=SENSOR_ID,
        recorded_at=TS,
        metrics={Metric.TEMPERATURE: 1.5, Metric.HUMIDITY: 40},
    )


def test_ingest_unknown_sensor_raises_not_found_and_touches_no_storage(
    repo: MagicMock, get_sensor: MagicMock, fake_session: NonCallableMagicMock
) -> None:
    get_sensor.side_effect = NotFoundError("Sensor 999 not found")

    with pytest.raises(NotFoundError):
        service.ingest(fake_session, 999, reading(temperature=1))

    get_sensor.assert_called_once_with(fake_session, 999)
    repo.find_values.assert_not_called()
    repo.add_many.assert_not_called()


@pytest.mark.usefixtures("get_sensor")
def test_exact_retry_succeeds_and_stores_nothing_new(
    repo: MagicMock, fake_session: NonCallableMagicMock
) -> None:
    repo.find_values.return_value = {Metric.TEMPERATURE: 1.5}

    result = service.ingest(fake_session, SENSOR_ID, reading(temperature=1.5))

    assert result.metrics == {Metric.TEMPERATURE: 1.5}
    repo.add_many.assert_called_once_with(fake_session, SENSOR_ID, {}, TS)


@pytest.mark.usefixtures("get_sensor")
def test_retry_with_an_extra_metric_stores_only_the_new_one(
    repo: MagicMock, fake_session: NonCallableMagicMock
) -> None:
    repo.find_values.return_value = {Metric.TEMPERATURE: 1.5}

    service.ingest(fake_session, SENSOR_ID, reading(temperature=1.5, humidity=40))

    repo.add_many.assert_called_once_with(fake_session, SENSOR_ID, {Metric.HUMIDITY: 40}, TS)


@pytest.mark.usefixtures("get_sensor")
def test_different_value_for_existing_key_conflicts_and_stores_nothing(
    repo: MagicMock, fake_session: NonCallableMagicMock
) -> None:
    repo.find_values.return_value = {Metric.TEMPERATURE: 1.5, Metric.HUMIDITY: 30}

    with pytest.raises(ConflictError, match="for: humidity, temperature$"):
        service.ingest(fake_session, SENSOR_ID, reading(temperature=9.9, humidity=40))

    repo.add_many.assert_not_called()
