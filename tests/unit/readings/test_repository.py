from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier

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


def stored_rows(session: Session) -> list[tuple[str, float]]:
    return [
        (row.metric, row.value) for row in session.scalars(select(Reading).order_by(Reading.id))
    ]


def test_stores_one_row_per_metric_as_naive_utc(
    repository: ReadingRepository, session: Session, sensor_id: int
) -> None:
    conflicts = repository.add_many_unless_conflicting(
        sensor_id, {Metric.TEMPERATURE: 1.5, Metric.HUMIDITY: 40.0}, TS
    )

    assert conflicts == []
    rows = list(session.scalars(select(Reading).order_by(Reading.id)))
    assert [(row.sensor_id, row.metric, row.value) for row in rows] == [
        (sensor_id, "temperature", 1.5),
        (sensor_id, "humidity", 40.0),
    ]
    assert {row.recorded_at for row in rows} == {datetime(2026, 11, 17, 10, 0)}


def test_raises_storage_error_and_stays_usable(
    repository: ReadingRepository, session: Session, engine: Engine, sensor_id: int
) -> None:
    Reading.__table__.drop(engine)

    with pytest.raises(StorageError, match="Could not store the reading"):
        repository.add_many_unless_conflicting(sensor_id, {Metric.TEMPERATURE: 1}, TS)
    assert session.in_transaction() is False  # rolled back


def test_same_value_is_skipped_and_new_metrics_are_stored(
    repository: ReadingRepository, session: Session, sensor_id: int
) -> None:
    repository.add_many_unless_conflicting(sensor_id, {Metric.TEMPERATURE: 1.5}, TS)

    conflicts = repository.add_many_unless_conflicting(
        sensor_id, {Metric.TEMPERATURE: 1.5, Metric.HUMIDITY: 40}, TS
    )

    assert conflicts == []
    assert stored_rows(session) == [("temperature", 1.5), ("humidity", 40.0)]


def test_different_value_is_returned_and_nothing_from_the_call_is_stored(
    repository: ReadingRepository, session: Session, sensor_id: int
) -> None:
    repository.add_many_unless_conflicting(sensor_id, {Metric.TEMPERATURE: 1.5}, TS)

    conflicts = repository.add_many_unless_conflicting(
        sensor_id, {Metric.TEMPERATURE: 9.9, Metric.HUMIDITY: 40}, TS
    )

    assert conflicts == [Metric.TEMPERATURE]
    assert session.in_transaction() is False  # rolled back
    assert stored_rows(session) == [("temperature", 1.5)]  # humidity too


def test_other_timestamps_do_not_conflict(
    repository: ReadingRepository, session: Session, sensor_id: int
) -> None:
    repository.add_many_unless_conflicting(sensor_id, {Metric.TEMPERATURE: 1.5}, TS)

    conflicts = repository.add_many_unless_conflicting(
        sensor_id, {Metric.TEMPERATURE: 9.9}, TS.replace(minute=1)
    )

    assert conflicts == []
    assert stored_rows(session) == [("temperature", 1.5), ("temperature", 9.9)]


def test_concurrent_calls_with_different_values_let_exactly_one_win(
    engine: Engine, session: Session, sensor_id: int
) -> None:
    # Each worker has its own session and connection, like concurrent requests.
    workers = 8
    start_together = Barrier(workers)

    def add(value: float) -> list[Metric]:
        with Session(engine) as worker_session:
            start_together.wait()
            return ReadingRepository(worker_session).add_many_unless_conflicting(
                sensor_id, {Metric.TEMPERATURE: value}, TS
            )

    values = [float(value) for value in range(workers)]
    with ThreadPoolExecutor(workers) as pool:
        conflicts_by_worker = list(pool.map(add, values))

    (winning_value,) = [
        value for value, conflicts in zip(values, conflicts_by_worker, strict=True) if not conflicts
    ]
    assert stored_rows(session) == [("temperature", winning_value)]
