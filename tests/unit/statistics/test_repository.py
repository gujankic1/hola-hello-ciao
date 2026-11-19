from datetime import datetime

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from hola_hello_ciao.core.errors import StorageError
from hola_hello_ciao.features.readings.models import Reading
from hola_hello_ciao.features.sensors.models import Sensor
from hola_hello_ciao.features.shared.metrics import Metric
from hola_hello_ciao.features.statistics import repository
from tests.conftest import AddReading

START = datetime(2026, 11, 1)
END = datetime(2026, 11, 2)


def test_aggregates_per_sensor_and_metric(
    session: Session, add_reading: AddReading, sensor_id: int
) -> None:
    for hour, value in [(10, 10), (11, 20), (12, 60)]:
        add_reading(sensor_id, Metric.TEMPERATURE, value, datetime(2026, 11, 1, hour))
    add_reading(sensor_id, Metric.HUMIDITY, 5, datetime(2026, 11, 1, 12))

    rows = repository.aggregate(session, [sensor_id], [Metric.TEMPERATURE], START, END)

    assert rows == [repository.Aggregate(sensor_id, "temperature", 10, 60, 90, 30, 3)]


def test_window_is_inclusive_start_exclusive_end(
    session: Session, add_reading: AddReading, sensor_id: int
) -> None:
    add_reading(sensor_id, Metric.TEMPERATURE, 1, START)  # included
    add_reading(sensor_id, Metric.TEMPERATURE, 100, END)  # excluded
    add_reading(sensor_id, Metric.TEMPERATURE, 100, datetime(2026, 10, 31, 23, 59))  # before

    (row,) = repository.aggregate(session, None, [Metric.TEMPERATURE], START, END)

    assert row.reading_count == 1 and row.sum == 1


def test_none_means_all_sensors_and_list_filters(
    session: Session, add_reading: AddReading, sensor_id: int
) -> None:
    other = Sensor(name="other")
    session.add(other)
    session.commit()
    add_reading(sensor_id, Metric.TEMPERATURE, 1, START)
    add_reading(other.id, Metric.TEMPERATURE, 2, START)

    everyone = repository.aggregate(session, None, [Metric.TEMPERATURE], START, END)
    only_other = repository.aggregate(session, [other.id], [Metric.TEMPERATURE], START, END)

    assert {r.sensor_id for r in everyone} == {sensor_id, other.id}
    assert [r.sensor_id for r in only_other] == [other.id]


def test_raises_storage_error(session: Session, engine: Engine) -> None:
    Reading.__table__.drop(engine)

    with pytest.raises(StorageError, match="Could not load statistics"):
        repository.aggregate(session, None, [Metric.TEMPERATURE], START, END)
