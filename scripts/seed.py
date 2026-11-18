"""Synthetic seed data for local development. Not part of the application package.

Writes through the ORM models directly (bulk insert), bypassing services and ingest
validation on purpose: the data is generated here and trusted (ADR-006).
"""

import math
import random
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import islice
from typing import Any

from sqlalchemy import insert
from sqlalchemy.orm import Session

from hola_hello_ciao.readings.metrics import Metric
from hola_hello_ciao.readings.models import Reading
from hola_hello_ciao.sensors.models import Sensor

BATCH_SIZE = 10_000


@dataclass(frozen=True)
class DatasetSpec:
    sensors: int
    interval: timedelta
    window: timedelta
    seed: int = 42

    @property
    def points_per_sensor(self) -> int:
        return self.window // self.interval

    @property
    def total_readings(self) -> int:
        return self.sensors * self.points_per_sensor * len(Metric)


DATASETS: dict[str, DatasetSpec] = {
    "small": DatasetSpec(sensors=3, interval=timedelta(hours=1), window=timedelta(days=7)),
    "medium": DatasetSpec(sensors=20, interval=timedelta(minutes=30), window=timedelta(days=30)),
    "large": DatasetSpec(sensors=100, interval=timedelta(minutes=30), window=timedelta(days=90)),
}


@dataclass(frozen=True)
class SeedResult:
    sensors: int
    readings: int


def floor_to(at: datetime, interval: timedelta) -> datetime:
    """Floor a naive datetime to a multiple of interval since midnight."""
    midnight = at.replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight + ((at - midnight) // interval) * interval


def generate_readings(
    spec: DatasetSpec, sensor_ids: list[int], end: datetime, rng: random.Random
) -> Iterator[dict[str, Any]]:
    """Yield one row dict per metric value; timestamps are naive UTC, the last one is end."""
    start = end - (spec.points_per_sensor - 1) * spec.interval
    for sensor_id in sensor_ids:
        base_temp = rng.uniform(5.0, 15.0)
        pressure = rng.uniform(1005.0, 1020.0)
        raining = False
        for i in range(spec.points_per_sensor):
            at = start + i * spec.interval
            hour = at.hour + at.minute / 60
            # Daily cycle peaking mid-afternoon.
            temperature = base_temp + 6.0 * math.sin(2 * math.pi * (hour - 9) / 24)
            temperature += rng.gauss(0, 0.8)
            # Rain comes in spells: a small chance to start, a larger chance to stop.
            raining = rng.random() < (0.8 if raining else 0.03)
            rainfall = round(rng.expovariate(1 / 1.5), 1) if raining else 0.0
            humidity = 70 - 2.5 * (temperature - base_temp) + (15 if raining else 0)
            humidity = min(95.0, max(30.0, humidity + rng.gauss(0, 4)))
            # Mean-reverting random walk around standard pressure.
            pressure += rng.gauss(0, 0.4) + 0.02 * (1013.0 - pressure)
            values = {
                Metric.TEMPERATURE: round(temperature, 1),
                Metric.HUMIDITY: round(humidity, 1),
                Metric.WIND_SPEED: round(rng.gammavariate(2.0, 2.0), 1),
                Metric.PRESSURE: round(pressure, 1),
                Metric.RAINFALL: rainfall,
            }
            for metric, value in values.items():
                yield {
                    "sensor_id": sensor_id,
                    "metric": metric.value,
                    "value": value,
                    "recorded_at": at,
                }


def seed(session: Session, spec: DatasetSpec, end: datetime) -> SeedResult:
    """Create spec.sensors sensors and their readings up to end (naive UTC), in batches."""
    sensors = [Sensor(name=f"station-{n:03d}") for n in range(1, spec.sensors + 1)]
    session.add_all(sensors)
    session.commit()
    rows = generate_readings(spec, [s.id for s in sensors], end, random.Random(spec.seed))
    readings = 0
    while batch := list(islice(rows, BATCH_SIZE)):
        session.execute(insert(Reading), batch)
        session.commit()
        readings += len(batch)
    return SeedResult(sensors=len(sensors), readings=readings)
