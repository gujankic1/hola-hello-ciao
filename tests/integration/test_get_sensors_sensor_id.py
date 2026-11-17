import pytest
from fastapi.testclient import TestClient

URL = "/api/v1/sensors"


def test_get_sensor(client: TestClient) -> None:
    created = client.post(URL, json={"name": "roof"}).json()

    response = client.get(f"{URL}/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_unknown_sensor_returns_404(client: TestClient) -> None:
    response = client.get(f"{URL}/999")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.parametrize("sensor_id", ["abc", 0, 2**63])  # 2**63 overflows SQLite INTEGER
def test_invalid_sensor_id_is_rejected(client: TestClient, sensor_id: object) -> None:
    response = client.get(f"{URL}/{sensor_id}")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
