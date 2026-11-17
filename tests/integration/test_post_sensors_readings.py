from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from hola_hello_ciao.readings.models import Reading


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


def test_post_reading_defaults_recorded_at_to_now(
    client: TestClient, engine: Engine, sensor_id: int
) -> None:
    before = datetime.now(UTC).replace(tzinfo=None)  # stored as naive UTC
    response = client.post(url(sensor_id), json={"metrics": {"wind_speed": 3.2}})

    assert response.status_code == 201
    (row,) = all_rows(engine)
    assert abs(row.recorded_at - before) < timedelta(seconds=10)


def test_unknown_sensor_returns_404_and_stores_nothing(client: TestClient, engine: Engine) -> None:
    response = client.post(url(999), json={"metrics": {"temperature": 1}})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert all_rows(engine) == []


def test_non_integer_sensor_id_is_rejected(client: TestClient) -> None:
    response = client.post(url("abc"), json={"metrics": {"temperature": 1}})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.parametrize(
    "payload",
    [
        {},  # missing metrics
        {"metrics": {}},  # empty metrics
        {"metrics": {"temperature": "warm"}},  # non-numeric value
        {"metrics": {"  ": 1}},  # blank metric name
        {"metrics": {"temperature": 1}, "recorded_at": "yesterday"},
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
    Reading.__table__.drop(engine)  # sensor lookup still works; the ingest write fails

    response = client.post(url(sensor_id), json={"metrics": {"temperature": 1}})

    assert response.status_code == 500
    assert response.json()["error"] == {
        "code": "storage_error",
        "message": "Could not store the reading",
    }
