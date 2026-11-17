from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from hola_hello_ciao.core.db import Base, create_db_engine
from hola_hello_ciao.core.deps import get_session
from hola_hello_ciao.main import create_app
from hola_hello_ciao.readings.metrics import Metric
from hola_hello_ciao.readings.models import Reading
from hola_hello_ciao.sensors.models import Sensor


@pytest.fixture
def engine(tmp_path: Path) -> Iterator[Engine]:
    engine = create_db_engine(str(tmp_path / "test.db"))
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    with Session(engine) as session:
        yield session


@pytest.fixture
def client(engine: Engine) -> Iterator[TestClient]:
    app = create_app()

    def override_session() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as client:
        yield client


@pytest.fixture
def sensor_id(session: Session) -> int:
    sensor = Sensor(name="test-sensor")
    session.add(sensor)
    session.commit()
    return sensor.id


AddReading = Callable[[int, Metric, float, datetime], None]


@pytest.fixture
def add_reading(session: Session) -> AddReading:
    """Insert one committed reading; aware datetimes are stored as naive UTC."""

    def add(sensor_id: int, metric: Metric, value: float, at: datetime) -> None:
        if at.tzinfo is not None:
            at = at.astimezone(UTC).replace(tzinfo=None)
        session.add(Reading(sensor_id=sensor_id, metric=metric.value, value=value, recorded_at=at))
        session.commit()

    return add
