from datetime import UTC, datetime

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from hola_hello_ciao.core.errors import StorageError
from hola_hello_ciao.features.readings.models import Reading
from hola_hello_ciao.features.readings.repository import ReadingRepository
from hola_hello_ciao.features.shared.metrics import Metric

TS = datetime(2026, 11, 17, 10, 0, tzinfo=UTC)


@pytest.fixture
def repository(session: Session) -> ReadingRepository:
    return ReadingRepository(session)


def test_add_many_stores_one_row_per_metric_as_naive_utc(
    repository: ReadingRepository, session: Session, sensor_id: int
) -> None:
    repository.add_many(sensor_id, {Metric.TEMPERATURE: 1.5, Metric.HUMIDITY: 40.0}, TS)

    rows = list(session.scalars(select(Reading).order_by(Reading.id)))
    assert [(row.sensor_id, row.metric, row.value) for row in rows] == [
        (sensor_id, "temperature", 1.5),
        (sensor_id, "humidity", 40.0),
    ]
    assert {row.recorded_at for row in rows} == {datetime(2026, 11, 17, 10, 0)}


def test_add_many_raises_storage_error_and_stays_usable(
    repository: ReadingRepository, session: Session, engine: Engine, sensor_id: int
) -> None:
    Reading.__table__.drop(engine)

    with pytest.raises(StorageError, match="Could not store the reading"):
        repository.add_many(sensor_id, {Metric.TEMPERATURE: 1}, datetime.now(UTC))
    assert session.in_transaction() is False  # rolled back


def test_add_many_skips_rows_that_already_exist(
    repository: ReadingRepository, session: Session, sensor_id: int
) -> None:
    repository.add_many(sensor_id, {Metric.TEMPERATURE: 1.5}, TS)

    repository.add_many(sensor_id, {Metric.TEMPERATURE: 9.9, Metric.HUMIDITY: 40}, TS)

    rows = list(session.scalars(select(Reading).order_by(Reading.id)))
    assert [(row.metric, row.value) for row in rows] == [("temperature", 1.5), ("humidity", 40.0)]


def test_find_values_returns_only_exact_matches(
    repository: ReadingRepository, sensor_id: int
) -> None:
    repository.add_many(sensor_id, {Metric.TEMPERATURE: 1.5, Metric.HUMIDITY: 40}, TS)

    found = repository.find_stored_values(sensor_id, [Metric.TEMPERATURE, Metric.WIND_SPEED], TS)

    assert found == {Metric.TEMPERATURE: 1.5}
    assert (
        repository.find_stored_values(sensor_id, [Metric.TEMPERATURE], TS.replace(minute=1)) == {}
    )
