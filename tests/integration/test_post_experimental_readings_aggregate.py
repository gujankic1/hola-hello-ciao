from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from hola_hello_ciao.features.shared.metrics import Metric
from tests.conftest import AddReading

URL = "/api/experimental/readings/aggregate"


def test_sentence_is_answered_and_its_reading_echoed(
    client: TestClient, add_reading: AddReading, sensor_id: int
) -> None:
    now = datetime.now(UTC)
    for days_ago, temperature, wind_speed in [(1, 10, 3), (3, 20, 9), (6, 30, 5), (10, 99, 99)]:
        at = now - timedelta(days=days_ago)
        add_reading(sensor_id, Metric.TEMPERATURE, temperature, at)
        add_reading(sensor_id, Metric.WIND_SPEED, wind_speed, at)

    response = client.post(
        URL, json={"query": f"Average temperature and max wind for sensor {sensor_id} last week"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["sensors"] == [
        {
            "sensor_id": sensor_id,
            "results": [
                {"metric": "temperature", "stat": "avg", "value": 20.0, "count": 3},
                {"metric": "wind_speed", "stat": "max", "value": 9.0, "count": 3},
            ],
        }
    ]
    interpreted = body["interpreted_query"]
    assert interpreted["sensor_ids"] == [sensor_id]
    assert interpreted["metrics"] == [
        {"name": "temperature", "stat": "avg"},
        {"name": "wind_speed", "stat": "max"},
    ]
    assert (interpreted["from"], interpreted["to"]) == (body["from"], body["to"])


def test_unknown_sensor_returns_404(client: TestClient) -> None:
    response = client.post(URL, json={"query": "average temperature for sensor 999"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.parametrize(
    "query",
    [
        "temperature last week",  # no statistic
        "what's the weather like",  # no metric
        "average temperature in the last 2 months",  # longer than 31 days
    ],
)
def test_unreadable_sentence_returns_422_invalid_query(client: TestClient, query: str) -> None:
    response = client.post(URL, json={"query": query})

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "invalid_query"
    assert error["message"]


@pytest.mark.parametrize(
    "payload",
    [{}, {"query": ""}, {"query": "x" * 501}, {"query": "average temperature", "extra": 1}],
)
def test_invalid_body_returns_422_validation_error(
    client: TestClient, payload: dict[str, object]
) -> None:
    response = client.post(URL, json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_v1_route_does_not_accept_sentences(client: TestClient) -> None:
    response = client.post("/api/v1/readings/aggregate", json={"query": "average temperature"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
