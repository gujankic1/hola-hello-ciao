from datetime import UTC, datetime

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from hola_hello_ciao.core.errors import StorageError
from hola_hello_ciao.features.readings import repository
from hola_hello_ciao.features.readings.models import Reading
from hola_hello_ciao.features.shared.metrics import Metric


def test_add_many_stores_one_row_per_metric_as_naive_utc(session: Session, sensor_id: int) -> None:
    ts = datetime(2026, 11, 17, 10, 0, tzinfo=UTC)

    repository.add_many(session, sensor_id, {Metric.TEMPERATURE: 1.5, Metric.HUMIDITY: 40.0}, ts)

    rows = list(session.scalars(select(Reading).order_by(Reading.id)))
    assert [(r.sensor_id, r.metric, r.value) for r in rows] == [
        (sensor_id, "temperature", 1.5),
        (sensor_id, "humidity", 40.0),
    ]
    assert {r.recorded_at for r in rows} == {datetime(2026, 11, 17, 10, 0)}


def test_add_many_raises_storage_error_and_stays_usable(
    session: Session, engine: Engine, sensor_id: int
) -> None:
    Reading.__table__.drop(engine)

    with pytest.raises(StorageError, match="Could not store the reading"):
        repository.add_many(session, sensor_id, {Metric.TEMPERATURE: 1}, datetime.now(UTC))
    assert session.in_transaction() is False  # rolled back


def test_add_many_skips_rows_that_already_exist(session: Session, sensor_id: int) -> None:
    ts = datetime(2026, 11, 17, 10, 0, tzinfo=UTC)
    repository.add_many(session, sensor_id, {Metric.TEMPERATURE: 1.5}, ts)

    repository.add_many(session, sensor_id, {Metric.TEMPERATURE: 9.9, Metric.HUMIDITY: 40}, ts)

    rows = list(session.scalars(select(Reading).order_by(Reading.id)))
    assert [(r.metric, r.value) for r in rows] == [("temperature", 1.5), ("humidity", 40.0)]


def test_find_values_returns_only_exact_matches(session: Session, sensor_id: int) -> None:
    ts = datetime(2026, 11, 17, 10, 0, tzinfo=UTC)
    repository.add_many(session, sensor_id, {Metric.TEMPERATURE: 1.5, Metric.HUMIDITY: 40}, ts)

    found = repository.find_stored_values(
        session, sensor_id, [Metric.TEMPERATURE, Metric.WIND_SPEED], ts
    )

    assert found == {Metric.TEMPERATURE: 1.5}
    assert (
        repository.find_stored_values(
            session, sensor_id, [Metric.TEMPERATURE], ts.replace(minute=1)
        )
        == {}
    )
