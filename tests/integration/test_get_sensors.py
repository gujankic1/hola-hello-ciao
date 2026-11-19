from fastapi.testclient import TestClient
from sqlalchemy import Engine

from hola_hello_ciao.features.sensors.models import Sensor

URL = "/api/v1/sensors"


def test_list_is_empty_without_sensors(client: TestClient) -> None:
    response = client.get(URL)

    assert response.status_code == 200
    assert response.json() == []


def test_list_returns_registered_sensors_in_id_order(client: TestClient) -> None:
    a = client.post(URL, json={"name": "roof"}).json()
    b = client.post(URL, json={}).json()

    response = client.get(URL)

    assert response.status_code == 200
    assert response.json() == [a, b]


def test_storage_failure_returns_error_shape(client: TestClient, engine: Engine) -> None:
    Sensor.__table__.drop(engine)

    response = client.get(URL)

    assert response.status_code == 500
    assert response.json()["error"] == {
        "code": "storage_error",
        "message": "Could not load the sensors",
    }
