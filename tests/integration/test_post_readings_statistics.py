from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from hola_hello_ciao.readings.metrics import Metric
from tests.conftest import AddReading

URL = "/api/v1/readings/statistics"


def test_average_temperature_and_humidity_for_sensor_in_last_week(
    client: TestClient, add_reading: AddReading, sensor_id: int
) -> None:
    now = datetime.now(UTC)
    for days_ago, temp, hum in [(1, 10, 40), (3, 20, 60), (6, 30, 50), (10, 99, 99)]:
        at = now - timedelta(days=days_ago)
        add_reading(sensor_id, Metric.TEMPERATURE, temp, at)
        add_reading(sensor_id, Metric.HUMIDITY, hum, at)

    response = client.post(
        URL,
        json={
            "sensor_ids": [sensor_id],
            "metrics": [
                {"name": "temperature", "stat": "avg"},
                {"name": "humidity", "stat": "avg"},
            ],
            "from": (now - timedelta(days=7)).isoformat(),
            "to": now.isoformat(),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert {"from", "to"} <= body.keys()
    assert body["results"] == [
        {"sensor_id": sensor_id, "metric": "temperature", "stat": "avg", "value": 20.0, "count": 3},
        {"sensor_id": sensor_id, "metric": "humidity", "stat": "avg", "value": 50.0, "count": 3},
    ]


def test_defaults_to_all_sensors_and_last_24_hours(
    client: TestClient, add_reading: AddReading, sensor_id: int
) -> None:
    add_reading(sensor_id, Metric.TEMPERATURE, 5, datetime.now(UTC) - timedelta(hours=1))

    response = client.post(URL, json={"metrics": [{"name": "temperature", "stat": "max"}]})

    assert response.status_code == 200
    assert [r["value"] for r in response.json()["results"]] == [5.0]


def test_unknown_sensor_returns_404(client: TestClient) -> None:
    response = client.post(
        URL, json={"sensor_ids": [999], "metrics": [{"name": "temperature", "stat": "avg"}]}
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.parametrize(
    "payload",
    [
        {},  # no metrics
        {"metrics": [{"name": "temperature", "stat": "median"}]},
        {"metrics": [{"name": "bogus", "stat": "avg"}]},
        {"metrics": [{"name": "temperature", "stat": "avg"}], "sensor_ids": []},
        {"metrics": [{"name": "temperature", "stat": "avg"}], "sensor_ids": [1, 1]},
        {"metrics": [{"name": "temperature", "stat": "avg"}], "from": "2026-11-01T00:00:00Z"},
        {
            "metrics": [{"name": "temperature", "stat": "avg"}],
            "from": "2026-11-01T00:00:00Z",
            "to": "2026-11-01T12:00:00Z",  # shorter than 1 day
        },
        {
            "metrics": [{"name": "temperature", "stat": "avg"}],
            "from": "2026-10-01T00:00:00Z",
            "to": "2026-11-17T00:00:00Z",  # longer than 31 days
        },
    ],
)
def test_invalid_query_returns_422(client: TestClient, payload: dict[str, object]) -> None:
    response = client.post(URL, json=payload)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["details"]
