from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from hola_hello_ciao.core.db import Base, create_db_engine
from hola_hello_ciao.core.deps import get_session
from hola_hello_ciao.main import create_app
from hola_hello_ciao.readings import models as readings_models  # noqa: F401
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
