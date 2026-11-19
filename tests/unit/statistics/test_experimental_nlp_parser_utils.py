from datetime import UTC, datetime, timedelta

import pytest

from hola_hello_ciao.core.errors import InvalidQueryError
from hola_hello_ciao.features.shared.metrics import Metric
from hola_hello_ciao.features.statistics.experimental_nlp_parser_utils import parse_statistics_query
from hola_hello_ciao.features.statistics.schemas import Stat, StatisticsQuery

NOW = datetime(2026, 11, 19, 15, 30, tzinfo=UTC)


def parse(text: str) -> StatisticsQuery:
    return parse_statistics_query(text, NOW)


def metric_stat_pairs(query: StatisticsQuery) -> list[tuple[Metric, Stat]]:
    return [(metric_stat.name, metric_stat.stat) for metric_stat in query.metrics]


def test_plain_query_means_all_sensors_and_default_window() -> None:
    query = parse("average temperature")

    assert metric_stat_pairs(query) == [(Metric.TEMPERATURE, Stat.AVG)]
    assert query.sensor_ids is None
    assert (query.from_, query.to) == (None, None)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "min and max temperature",
            [(Metric.TEMPERATURE, Stat.MIN), (Metric.TEMPERATURE, Stat.MAX)],
        ),
        (
            "average temperature and humidity",
            [(Metric.TEMPERATURE, Stat.AVG), (Metric.HUMIDITY, Stat.AVG)],
        ),
        (
            "average temperature and max wind speed",
            [(Metric.TEMPERATURE, Stat.AVG), (Metric.WIND_SPEED, Stat.MAX)],
        ),
        ("What was the Total RAINFALL?", [(Metric.RAINFALL, Stat.SUM)]),
        ("mean precipitation", [(Metric.RAINFALL, Stat.AVG)]),
        ("peak windspeed", [(Metric.WIND_SPEED, Stat.MAX)]),
        ("lowest pressure", [(Metric.PRESSURE, Stat.MIN)]),
        ("avg temp and average temperature", [(Metric.TEMPERATURE, Stat.AVG)]),
    ],
)
def test_statistics_pair_with_the_metrics_after_them(
    text: str, expected: list[tuple[Metric, Stat]]
) -> None:
    assert metric_stat_pairs(parse(text)) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("average temperature for sensor 3", [3]),
        ("average temperature for sensor #3", [3]),
        ("average temperature for sensors 5, 1, and 2", [5, 1, 2]),
        ("average temperature for sensors 1 and 2 & 4", [1, 2, 4]),
        ("average temperature for sensor 1 and sensor 2", [1, 2]),
        ("average temperature for sensor 2 and 2", [2]),
        ("average temperature for all sensors", None),
        ("max temperature in the last 3 days", None),  # the 3 is a duration, not a sensor
    ],
)
def test_sensors(text: str, expected: list[int] | None) -> None:
    assert parse(text).sensor_ids == expected


@pytest.mark.parametrize(
    ("phrase", "expected_from", "expected_to"),
    [
        ("last 3 days", NOW - timedelta(days=3), NOW),
        ("in the past 2 weeks", NOW - timedelta(weeks=2), NOW),
        ("over the last 48 hours", NOW - timedelta(hours=48), NOW),
        ("last week", NOW - timedelta(weeks=1), NOW),
        ("last month", NOW - timedelta(days=31), NOW),
        ("past day", NOW - timedelta(days=1), NOW),
        ("yesterday", datetime(2026, 11, 18, tzinfo=UTC), datetime(2026, 11, 19, tzinfo=UTC)),
        ("since 2026-11-10", datetime(2026, 11, 10, tzinfo=UTC), NOW),
        (
            "between 2026-11-01 and 2026-11-05",
            datetime(2026, 11, 1, tzinfo=UTC),
            datetime(2026, 11, 5, tzinfo=UTC),
        ),
        (
            "from 2026-11-01T06:00Z to 2026-11-03 06:00+01:00",
            datetime(2026, 11, 1, 6, tzinfo=UTC),
            datetime(2026, 11, 3, 5, tzinfo=UTC),
        ),
    ],
)
def test_time_windows(phrase: str, expected_from: datetime, expected_to: datetime) -> None:
    query = parse(f"average temperature {phrase}")

    assert (query.from_, query.to) == (expected_from, expected_to)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("hello there", "No metric recognised"),
        ("temperature last week", "No statistic given for temperature"),
        ("median temperature", "No statistic given for temperature"),
        ("average temperature and max", "Statistic max is not followed by a metric"),
        ("avg temp in the last 6 hours", "date range must be between 1 day and 31 days"),
        ("avg temp in the last 2 months", "date range must be between 1 day and 31 days"),
        ("avg temp between 2026-11-05 and 2026-11-01", "'from' must be before 'to'"),
        ("avg temp in the last 99999999999999 weeks", "Time range too long"),
        ("avg temp since 2026-13-01", "Invalid date: 2026-13-01"),
        ("avg temp yesterday and last week", "More than one time range given"),
        ("avg temp for all sensors and sensor 1", "Both 'all sensors' and specific sensors"),
        ("avg temp for sensor 0", "sensor_ids: "),
    ],
)
def test_unreadable_text_raises_invalid_query(text: str, message: str) -> None:
    with pytest.raises(InvalidQueryError, match=message):
        parse(text)
