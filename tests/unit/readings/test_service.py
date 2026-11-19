from datetime import UTC, datetime
from unittest.mock import NonCallableMagicMock, create_autospec

import pytest

from hola_hello_ciao.core.errors import ConflictError, NotFoundError
from hola_hello_ciao.features.readings.repository import ReadingRepository
from hola_hello_ciao.features.readings.schemas import ReadingCreate, ReadingCreated
from hola_hello_ciao.features.readings.service import ReadingService
from hola_hello_ciao.features.sensors.schemas import SensorRead
from hola_hello_ciao.features.sensors.service import SensorService
from hola_hello_ciao.features.shared.metrics import Metric

TS = datetime(2026, 11, 17, 10, 0, tzinfo=UTC)
SENSOR_ID = 7


@pytest.fixture
def repository() -> NonCallableMagicMock:
    mock = create_autospec(ReadingRepository, instance=True)
    mock.find_stored_values.return_value = {}
    return mock


@pytest.fixture
def sensor_service() -> NonCallableMagicMock:
    mock = create_autospec(SensorService, instance=True)
    mock.get_sensor.return_value = SensorRead(id=SENSOR_ID, name=None)
    return mock


@pytest.fixture
def service(
    repository: NonCallableMagicMock, sensor_service: NonCallableMagicMock
) -> ReadingService:
    return ReadingService(repository, sensor_service)


def reading(**metrics: float) -> ReadingCreate:
    return ReadingCreate(metrics={Metric(m): v for m, v in metrics.items()}, recorded_at=TS)


def test_ingest_stores_every_metric_and_echoes_input(
    service: ReadingService, repository: NonCallableMagicMock
) -> None:
    result = service.ingest_reading(SENSOR_ID, reading(temperature=1.5, humidity=40))

    repository.find_stored_values.assert_called_once_with(
        SENSOR_ID, [Metric.TEMPERATURE, Metric.HUMIDITY], TS
    )
    repository.add_many.assert_called_once_with(
        SENSOR_ID, {Metric.TEMPERATURE: 1.5, Metric.HUMIDITY: 40}, TS
    )
    assert result == ReadingCreated(
        sensor_id=SENSOR_ID,
        recorded_at=TS,
        metrics={Metric.TEMPERATURE: 1.5, Metric.HUMIDITY: 40},
    )


def test_ingest_unknown_sensor_raises_not_found_and_touches_no_storage(
    service: ReadingService, repository: NonCallableMagicMock, sensor_service: NonCallableMagicMock
) -> None:
    sensor_service.get_sensor.side_effect = NotFoundError("Sensor 999 not found")

    with pytest.raises(NotFoundError):
        service.ingest_reading(999, reading(temperature=1))

    sensor_service.get_sensor.assert_called_once_with(999)
    repository.find_stored_values.assert_not_called()
    repository.add_many.assert_not_called()


def test_exact_retry_succeeds_and_stores_nothing_new(
    service: ReadingService, repository: NonCallableMagicMock
) -> None:
    repository.find_stored_values.return_value = {Metric.TEMPERATURE: 1.5}

    result = service.ingest_reading(SENSOR_ID, reading(temperature=1.5))

    assert result.metrics == {Metric.TEMPERATURE: 1.5}
    repository.add_many.assert_called_once_with(SENSOR_ID, {}, TS)


def test_retry_with_an_extra_metric_stores_only_the_new_one(
    service: ReadingService, repository: NonCallableMagicMock
) -> None:
    repository.find_stored_values.return_value = {Metric.TEMPERATURE: 1.5}

    service.ingest_reading(SENSOR_ID, reading(temperature=1.5, humidity=40))

    repository.add_many.assert_called_once_with(SENSOR_ID, {Metric.HUMIDITY: 40}, TS)


def test_different_value_for_existing_key_conflicts_and_stores_nothing(
    service: ReadingService, repository: NonCallableMagicMock
) -> None:
    repository.find_stored_values.return_value = {Metric.TEMPERATURE: 1.5, Metric.HUMIDITY: 30}

    with pytest.raises(ConflictError, match="for: humidity, temperature$"):
        service.ingest_reading(SENSOR_ID, reading(temperature=9.9, humidity=40))

    repository.add_many.assert_not_called()
