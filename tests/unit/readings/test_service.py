from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from hola_hello_ciao.core.errors import ConflictError, NotFoundError
from hola_hello_ciao.readings.metrics import Metric
from hola_hello_ciao.readings.models import Reading
from hola_hello_ciao.readings.schemas import ReadingCreate
from hola_hello_ciao.readings.service import ingest

TS = datetime(2026, 11, 17, 10, 0, tzinfo=UTC)


def stored(session: Session) -> list[tuple[str, float]]:
    return [(r.metric, r.value) for r in session.scalars(select(Reading).order_by(Reading.id))]


def test_ingest_persists_rows_and_echoes_input(session: Session, sensor_id: int) -> None:
    ts = TS
    data = ReadingCreate(metrics={Metric.TEMPERATURE: 1.5}, recorded_at=ts)

    result = ingest(session, sensor_id, data)

    assert result.sensor_id == sensor_id
    assert result.recorded_at == ts
    rows = list(session.scalars(select(Reading)))
    assert [(r.sensor_id, r.metric, r.value) for r in rows] == [(sensor_id, "temperature", 1.5)]


def test_ingest_unknown_sensor_raises_not_found(session: Session) -> None:
    with pytest.raises(NotFoundError):
        ingest(session, 999, ReadingCreate(metrics={Metric.TEMPERATURE: 1}, recorded_at=TS))


def test_exact_retry_stores_nothing_new(session: Session, sensor_id: int) -> None:
    data = ReadingCreate(metrics={Metric.TEMPERATURE: 1.5}, recorded_at=TS)
    ingest(session, sensor_id, data)

    result = ingest(session, sensor_id, data)

    assert result.metrics == {Metric.TEMPERATURE: 1.5}
    assert stored(session) == [("temperature", 1.5)]


def test_retry_with_an_extra_metric_stores_only_the_new_one(
    session: Session, sensor_id: int
) -> None:
    ingest(session, sensor_id, ReadingCreate(metrics={Metric.TEMPERATURE: 1.5}, recorded_at=TS))

    ingest(
        session,
        sensor_id,
        ReadingCreate(metrics={Metric.TEMPERATURE: 1.5, Metric.HUMIDITY: 40}, recorded_at=TS),
    )

    assert stored(session) == [("temperature", 1.5), ("humidity", 40.0)]


def test_different_value_for_existing_key_conflicts_and_stores_nothing(
    session: Session, sensor_id: int
) -> None:
    ingest(session, sensor_id, ReadingCreate(metrics={Metric.TEMPERATURE: 1.5}, recorded_at=TS))

    with pytest.raises(ConflictError, match="temperature"):
        ingest(
            session,
            sensor_id,
            ReadingCreate(metrics={Metric.TEMPERATURE: 9.9, Metric.HUMIDITY: 40}, recorded_at=TS),
        )
    assert stored(session) == [("temperature", 1.5)]  # humidity not stored either


def test_same_instant_in_another_offset_is_the_same_reading(
    session: Session, sensor_id: int
) -> None:
    ingest(session, sensor_id, ReadingCreate(metrics={Metric.TEMPERATURE: 1.5}, recorded_at=TS))

    with pytest.raises(ConflictError):
        ingest(
            session,
            sensor_id,
            ReadingCreate.model_validate(
                {"metrics": {"temperature": 2.0}, "recorded_at": "2026-11-17T12:00:00+02:00"}
            ),
        )
