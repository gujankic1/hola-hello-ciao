from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from hola_hello_ciao.core.errors import NotFoundError
from hola_hello_ciao.readings.models import Reading
from hola_hello_ciao.readings.schemas import ReadingCreate
from hola_hello_ciao.readings.service import ingest


def test_ingest_persists_rows_and_echoes_input(session: Session, sensor_id: int) -> None:
    ts = datetime(2026, 11, 17, 10, 0, tzinfo=UTC)
    data = ReadingCreate(metrics={"temperature": 1.5}, recorded_at=ts)

    result = ingest(session, sensor_id, data)

    assert result.sensor_id == sensor_id
    assert result.recorded_at == ts
    rows = list(session.scalars(select(Reading)))
    assert [(r.sensor_id, r.metric, r.value) for r in rows] == [(sensor_id, "temperature", 1.5)]


def test_ingest_unknown_sensor_raises_not_found(session: Session) -> None:
    with pytest.raises(NotFoundError):
        ingest(session, 999, ReadingCreate(metrics={"temperature": 1}))
