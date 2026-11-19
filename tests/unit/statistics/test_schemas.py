from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from hola_hello_ciao.features.statistics.schemas import MAX_SENSOR_IDS, StatisticsQuery

METRICS = [{"name": "temperature", "stat": "avg"}]
T0 = datetime(2026, 11, 1, tzinfo=UTC)


def make(**kwargs: object) -> StatisticsQuery:
    return StatisticsQuery.model_validate({"metrics": METRICS, **kwargs})


def test_minimal_query_defaults_to_all_sensors_and_no_window() -> None:
    q = make()

    assert q.sensor_ids is None
    assert q.from_ is None and q.to is None


@pytest.mark.parametrize("delta", [timedelta(days=1), timedelta(days=31), timedelta(days=7)])
def test_window_bounds_are_inclusive(delta: timedelta) -> None:
    q = make(**{"from": T0, "to": T0 + delta})

    assert q.to == T0 + delta


@pytest.mark.parametrize(
    "delta",
    [timedelta(hours=23, minutes=59), timedelta(days=31, seconds=1)],
)
def test_window_outside_one_day_to_31_days_is_rejected(delta: timedelta) -> None:
    with pytest.raises(ValidationError, match="between 1 day and 31 days"):
        make(**{"from": T0, "to": T0 + delta})


@pytest.mark.parametrize("delta", [timedelta(0), timedelta(days=-2)])
def test_from_not_before_to_is_rejected(delta: timedelta) -> None:
    with pytest.raises(ValidationError, match="'from' must be before 'to'"):
        make(**{"from": T0, "to": T0 + delta})


def test_from_without_to_is_rejected() -> None:
    with pytest.raises(ValidationError, match="'to' is required"):
        make(**{"from": T0})


def test_to_without_from_is_allowed() -> None:
    assert make(to=T0).from_ is None


def test_naive_datetimes_are_treated_as_utc() -> None:
    q = make(**{"from": "2026-11-01T00:00:00", "to": "2026-11-03T02:00:00+02:00"})

    assert q.from_ == T0
    assert q.to == datetime(2026, 11, 3, tzinfo=UTC)


@pytest.mark.parametrize(
    "payload",
    [
        {"metrics": []},
        {"metrics": [{"name": "temprature", "stat": "avg"}]},  # unknown metric
        {"metrics": [{"name": "temperature", "stat": "median"}]},  # unknown stat
        {"metrics": METRICS + METRICS},  # duplicate pair
        {"metrics": METRICS, "sensor_ids": []},
        {"metrics": METRICS, "sensor_ids": [0]},  # ids start at 1
        {"metrics": METRICS, "sensor_ids": [2**63]},  # beyond SQLite INTEGER
        {"metrics": METRICS, "sensor_ids": list(range(1, MAX_SENSOR_IDS + 2))},  # too many
    ],
)
def test_invalid_queries_are_rejected(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        StatisticsQuery.model_validate(payload)


def test_same_metric_with_different_stats_is_allowed() -> None:
    q = make(metrics=METRICS + [{"name": "temperature", "stat": "max"}])

    assert len(q.metrics) == 2


def test_duplicate_sensor_ids_are_rejected() -> None:
    with pytest.raises(ValidationError, match="duplicate sensor id"):
        make(sensor_ids=[2, 1, 2])


def test_up_to_max_sensor_ids_are_allowed() -> None:
    q = make(sensor_ids=list(range(1, MAX_SENSOR_IDS + 1)))

    assert q.sensor_ids is not None
    assert len(q.sensor_ids) == MAX_SENSOR_IDS
