import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from hola_hello_ciao.sensors.models import Sensor

URL = "/api/v1/sensors"


def all_sensors(engine: Engine) -> list[Sensor]:
    with Session(engine) as session:
        return list(session.scalars(select(Sensor).order_by(Sensor.id)))


def test_create_sensor(client: TestClient, engine: Engine) -> None:
    response = client.post(URL, json={"name": "  roof-station "})

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "roof-station"
    assert [(s.id, s.name) for s in all_sensors(engine)] == [(body["id"], "roof-station")]


def test_create_sensor_without_name(client: TestClient) -> None:
    response = client.post(URL, json={})

    assert response.status_code == 201
    assert response.json()["name"] is None


def test_sensor_ids_are_distinct(client: TestClient) -> None:
    first = client.post(URL, json={}).json()["id"]
    second = client.post(URL, json={}).json()["id"]

    assert first != second


@pytest.mark.parametrize("payload", [{"name": "   "}, {"name": 5}])
def test_invalid_sensor_is_rejected(
    client: TestClient, engine: Engine, payload: dict[str, object]
) -> None:
    response = client.post(URL, json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert all_sensors(engine) == []


def test_storage_failure_returns_error_shape(client: TestClient, engine: Engine) -> None:
    Sensor.__table__.drop(engine)

    response = client.post(URL, json={"name": "roof-station"})

    assert response.status_code == 500
    assert response.json()["error"] == {
        "code": "storage_error",
        "message": "Could not store the sensor",
    }
