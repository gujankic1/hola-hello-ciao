from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from hola_hello_ciao.core.errors import NotFoundError
from hola_hello_ciao.readings.metrics import Metric
from hola_hello_ciao.sensors.models import Sensor
from hola_hello_ciao.statistics.schemas import Stat, StatisticsQuery
from hola_hello_ciao.statistics.service import query
from tests.conftest import AddReading

T0 = datetime(2026, 11, 1, tzinfo=UTC)


def make(**kwargs: object) -> StatisticsQuery:
    return StatisticsQuery.model_validate(kwargs)


def test_each_stat_is_computed(session: Session, add_reading: AddReading, sensor_id: int) -> None:
    for value in (10, 20, 60):
        add_reading(sensor_id, Metric.TEMPERATURE, value, T0 + timedelta(hours=1))
    metrics = [{"name": "temperature", "stat": s.value} for s in Stat]

    response = query(
        session,
        make(sensor_ids=[sensor_id], metrics=metrics, **{"from": T0, "to": T0 + timedelta(days=2)}),
    )

    assert {r.stat: r.value for r in response.results} == {
        Stat.MIN: 10,
        Stat.MAX: 60,
        Stat.SUM: 90,
        Stat.AVG: 30,
    }
    assert {r.count for r in response.results} == {3}


def test_default_window_is_last_24_hours(
    session: Session, add_reading: AddReading, sensor_id: int
) -> None:
    now = datetime.now(UTC)
    add_reading(sensor_id, Metric.TEMPERATURE, 1, now - timedelta(hours=23))
    add_reading(sensor_id, Metric.TEMPERATURE, 100, now - timedelta(hours=25))

    response = query(session, make(metrics=[{"name": "temperature", "stat": "sum"}]))

    assert response.to - response.from_ == timedelta(hours=24)
    assert abs(response.to - now) < timedelta(seconds=10)
    assert [r.value for r in response.results] == [1]


def test_only_to_given_uses_24_hours_before_it(session: Session, sensor_id: int) -> None:
    response = query(session, make(metrics=[{"name": "temperature", "stat": "avg"}], to=T0))

    assert response.from_ == T0 - timedelta(hours=24)


def test_explicit_sensor_without_data_yields_null_value(session: Session, sensor_id: int) -> None:
    response = query(
        session, make(sensor_ids=[sensor_id], metrics=[{"name": "humidity", "stat": "avg"}])
    )

    (result,) = response.results
    assert (result.sensor_id, result.value, result.count) == (sensor_id, None, 0)


def test_all_sensors_lists_only_sensors_with_data_sorted(
    session: Session, add_reading: AddReading, sensor_id: int
) -> None:
    other = Sensor(name="other")
    silent = Sensor(name="silent")
    session.add_all([other, silent])
    session.commit()
    now = datetime.now(UTC)
    add_reading(other.id, Metric.TEMPERATURE, 2, now)
    add_reading(sensor_id, Metric.TEMPERATURE, 1, now)

    response = query(session, make(metrics=[{"name": "temperature", "stat": "avg"}]))

    assert [r.sensor_id for r in response.results] == sorted([sensor_id, other.id])


def test_unknown_sensor_raises_not_found(session: Session, sensor_id: int) -> None:
    with pytest.raises(NotFoundError):
        query(
            session,
            make(sensor_ids=[sensor_id, 999], metrics=[{"name": "temperature", "stat": "avg"}]),
        )
