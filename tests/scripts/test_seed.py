import random
from datetime import datetime, timedelta

import pytest
from seed import DATASETS, DatasetSpec, floor_to, generate_readings, seed
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from hola_hello_ciao.features.readings.models import Reading
from hola_hello_ciao.features.sensors.models import Sensor
from hola_hello_ciao.features.shared.metrics import Metric

END = datetime(2026, 11, 18, 12, 0)
SPEC = DatasetSpec(sensors=2, interval=timedelta(minutes=30), window=timedelta(days=2))


def rows(spec: DatasetSpec = SPEC, seed_value: int = 1) -> list[dict[str, object]]:
    sensor_ids = list(range(1, spec.sensors + 1))
    return list(generate_readings(spec, sensor_ids, END, random.Random(seed_value)))


def test_generates_one_row_per_sensor_metric_and_interval() -> None:
    result = rows()

    assert len(result) == SPEC.total_readings == 2 * 96 * len(Metric)
    keys = {(r["sensor_id"], r["metric"], r["recorded_at"]) for r in result}
    assert len(keys) == len(result)


def test_same_seed_gives_same_rows() -> None:
    assert rows(seed_value=7) == rows(seed_value=7)
    assert rows(seed_value=7) != rows(seed_value=8)


def test_timestamps_end_at_end_and_sit_on_the_interval_grid() -> None:
    times = sorted({r["recorded_at"] for r in rows()})

    assert times[-1] == END
    assert times[0] == END - (SPEC.points_per_sensor - 1) * SPEC.interval
    assert all(b - a == SPEC.interval for a, b in zip(times, times[1:], strict=False))


@pytest.mark.parametrize(
    ("metric", "low", "high"),
    [
        (Metric.TEMPERATURE, -20, 40),
        (Metric.HUMIDITY, 30, 95),
        (Metric.WIND_SPEED, 0, 60),
        (Metric.PRESSURE, 950, 1070),
        (Metric.RAINFALL, 0, 50),
    ],
)
def test_values_are_plausible(metric: Metric, low: float, high: float) -> None:
    values = [r["value"] for r in rows() if r["metric"] == metric.value]

    assert all(low <= v <= high for v in values)


def test_floor_to_rounds_down_to_the_interval() -> None:
    assert floor_to(datetime(2026, 11, 18, 10, 47, 13), timedelta(minutes=30)) == datetime(
        2026, 11, 18, 10, 30
    )


def test_seed_stores_sensors_and_readings(session: Session) -> None:
    spec = DATASETS["small"]

    result = seed(session, spec, END)

    assert result.sensors == spec.sensors
    assert result.readings == spec.total_readings
    assert session.scalar(select(func.count()).select_from(Sensor)) == spec.sensors
    assert session.scalar(select(func.count()).select_from(Reading)) == spec.total_readings
    assert session.scalar(select(func.max(Reading.recorded_at))) == END
