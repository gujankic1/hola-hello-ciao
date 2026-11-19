from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from hola_hello_ciao.features.readings.models import Reading
from hola_hello_ciao.features.shared.metrics import Metric

TS = "2026-11-17T10:00:00Z"


def url(sensor_id: object) -> str:
    return f"/api/v1/sensors/{sensor_id}/readings"


def all_rows(engine: Engine) -> list[Reading]:
    with Session(engine) as session:
        return list(session.scalars(select(Reading).order_by(Reading.id)))


def test_post_reading_stores_one_row_per_metric(
    client: TestClient, engine: Engine, sensor_id: int
) -> None:
    response = client.post(
        url(sensor_id),
        json={
            "metrics": {"temperature": 21.5, "humidity": 40},
            "recorded_at": "2026-11-17T12:00:00+02:00",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["sensor_id"] == sensor_id
    assert body["metrics"] == {"temperature": 21.5, "humidity": 40.0}

    rows = all_rows(engine)
    assert [(r.sensor_id, r.metric, r.value) for r in rows] == [
        (sensor_id, "temperature", 21.5),
        (sensor_id, "humidity", 40.0),
    ]
    # +02:00 offset is normalised to UTC
    assert {r.recorded_at for r in rows} == {datetime(2026, 11, 17, 10, 0)}


@pytest.mark.parametrize("metric", [m.value for m in Metric])
def test_every_known_metric_is_accepted(client: TestClient, sensor_id: int, metric: str) -> None:
    response = client.post(url(sensor_id), json={"metrics": {metric: 1.5}, "recorded_at": TS})

    assert response.status_code == 201


def test_unknown_sensor_returns_404_and_stores_nothing(client: TestClient, engine: Engine) -> None:
    response = client.post(url(999), json={"metrics": {"temperature": 1}, "recorded_at": TS})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert all_rows(engine) == []


@pytest.mark.parametrize("sensor_id", ["abc", 0, 2**63])  # 2**63 overflows SQLite INTEGER
def test_invalid_sensor_id_is_rejected(client: TestClient, sensor_id: object) -> None:
    response = client.post(url(sensor_id), json={"metrics": {"temperature": 1}, "recorded_at": TS})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.parametrize(
    "payload",
    [
        {"recorded_at": TS},  # missing metrics
        {"metrics": {}, "recorded_at": TS},  # empty metrics
        {"metrics": {"temperature": "warm"}, "recorded_at": TS},  # non-numeric value
        {"metrics": {"  ": 1}, "recorded_at": TS},  # blank metric name
        {"metrics": {"temprature": 1}, "recorded_at": TS},  # unknown metric (typo)
        {"metrics": {"temperature": 1, "bogus": 2}, "recorded_at": TS},  # one bad key
        {"metrics": {"temperature": 1}},  # missing recorded_at
        {"metrics": {"temperature": 1}, "recorded_at": "yesterday"},
        {"metrics": {"temperature": 1}, "recorded_at": TS, "unit": "C"},  # unknown field
    ],
)
def test_invalid_payload_is_rejected_and_nothing_stored(
    client: TestClient, engine: Engine, sensor_id: int, payload: dict[str, object]
) -> None:
    response = client.post(url(sensor_id), json=payload)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["details"]
    assert all_rows(engine) == []


def test_storage_failure_returns_error_shape(
    client: TestClient, engine: Engine, sensor_id: int
) -> None:
    Reading.__table__.drop(engine)  # sensor lookup still works; reading access fails

    response = client.post(url(sensor_id), json={"metrics": {"temperature": 1}, "recorded_at": TS})

    assert response.status_code == 500
    assert response.json()["error"] == {
        "code": "storage_error",
        "message": "Could not store the reading",
    }


def test_exact_retry_returns_201_and_stores_no_duplicate(
    client: TestClient, engine: Engine, sensor_id: int
) -> None:
    payload = {"metrics": {"temperature": 21.5}, "recorded_at": TS}

    first = client.post(url(sensor_id), json=payload)
    retry = client.post(url(sensor_id), json=payload)

    assert (first.status_code, retry.status_code) == (201, 201)
    assert retry.json() == first.json()
    assert len(all_rows(engine)) == 1


def test_different_value_at_same_time_returns_409_and_stores_nothing_from_the_call(
    client: TestClient, engine: Engine, sensor_id: int
) -> None:
    client.post(url(sensor_id), json={"metrics": {"temperature": 21.5}, "recorded_at": TS})

    response = client.post(
        url(sensor_id), json={"metrics": {"temperature": 22.0, "humidity": 40}, "recorded_at": TS}
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"
    assert [(row.metric, row.value) for row in all_rows(engine)] == [("temperature", 21.5)]
