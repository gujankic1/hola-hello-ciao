from datetime import UTC, datetime, timedelta
from unittest.mock import NonCallableMagicMock, create_autospec

import pytest

from hola_hello_ciao.core.errors import NotFoundError
from hola_hello_ciao.features.sensors.service import SensorService
from hola_hello_ciao.features.shared.metrics import Metric
from hola_hello_ciao.features.statistics.repository import Aggregate, StatisticsRepository
from hola_hello_ciao.features.statistics.schemas import Stat, StatisticsQuery
from hola_hello_ciao.features.statistics.service import StatisticsService

T0 = datetime(2026, 11, 1, tzinfo=UTC)
T1 = T0 + timedelta(days=2)
TEMP_AVG = {"name": "temperature", "stat": "avg"}


@pytest.fixture
def repository() -> NonCallableMagicMock:
    mock = create_autospec(StatisticsRepository, instance=True)
    mock.aggregate_readings.return_value = []
    return mock


@pytest.fixture
def sensor_service() -> NonCallableMagicMock:
    return create_autospec(SensorService, instance=True)


@pytest.fixture
def service(
    repository: NonCallableMagicMock, sensor_service: NonCallableMagicMock
) -> StatisticsService:
    return StatisticsService(repository, sensor_service)


def make(**kwargs: object) -> StatisticsQuery:
    return StatisticsQuery.model_validate(kwargs)


def agg(sensor_id: int, metric: str = "temperature", n: int = 3) -> Aggregate:
    return Aggregate(sensor_id, metric, min=10, max=60, sum=90, avg=30, reading_count=n)


def test_each_stat_is_picked_from_the_aggregate(
    service: StatisticsService, repository: NonCallableMagicMock
) -> None:
    repository.aggregate_readings.return_value = [agg(1)]
    metrics = [{"name": "temperature", "stat": s.value} for s in Stat]

    response = service.compute_statistics(
        make(sensor_ids=[1], metrics=metrics, **{"from": T0, "to": T1})
    )

    repository.aggregate_readings.assert_called_once_with([1], [Metric.TEMPERATURE] * 4, T0, T1)
    (sensor,) = response.sensors
    assert {r.stat: r.value for r in sensor.results} == {
        Stat.MIN: 10,
        Stat.MAX: 60,
        Stat.SUM: 90,
        Stat.AVG: 30,
    }
    assert {r.count for r in sensor.results} == {3}
    assert (response.from_, response.to) == (T0, T1)


def test_default_window_is_last_24_hours(
    service: StatisticsService, repository: NonCallableMagicMock
) -> None:
    response = service.compute_statistics(make(metrics=[TEMP_AVG]))

    assert response.to - response.from_ == timedelta(hours=24)
    assert abs(response.to - datetime.now(UTC)) < timedelta(seconds=10)
    _, _, start, end = repository.aggregate_readings.call_args.args
    assert (start, end) == (response.from_, response.to)


def test_only_to_given_uses_24_hours_before_it(
    service: StatisticsService, repository: NonCallableMagicMock
) -> None:
    response = service.compute_statistics(make(metrics=[TEMP_AVG], to=T0))

    assert response.from_ == T0 - timedelta(hours=24)


def test_requested_sensor_without_data_yields_null_value(
    service: StatisticsService, repository: NonCallableMagicMock
) -> None:
    repository.aggregate_readings.return_value = [agg(1, "temperature")]

    response = service.compute_statistics(
        make(sensor_ids=[1, 2], metrics=[{"name": "humidity", "stat": "avg"}])
    )

    assert [(s.sensor_id, [(r.value, r.count) for r in s.results]) for s in response.sensors] == [
        (1, [(None, 0)]),
        (2, [(None, 0)]),
    ]


def test_results_are_grouped_per_sensor_in_request_order(
    service: StatisticsService, repository: NonCallableMagicMock
) -> None:
    repository.aggregate_readings.return_value = [agg(1, "humidity"), agg(5), agg(1)]
    metrics = [TEMP_AVG, {"name": "humidity", "stat": "max"}]

    response = service.compute_statistics(make(sensor_ids=[5, 1], metrics=metrics))

    assert [
        (s.sensor_id, [(r.metric, r.stat, r.value) for r in s.results]) for s in response.sensors
    ] == [
        (5, [(Metric.TEMPERATURE, Stat.AVG, 30), (Metric.HUMIDITY, Stat.MAX, None)]),
        (1, [(Metric.TEMPERATURE, Stat.AVG, 30), (Metric.HUMIDITY, Stat.MAX, 60)]),
    ]


def test_all_sensors_lists_only_sensors_with_data_sorted_and_skips_existence_check(
    service: StatisticsService,
    repository: NonCallableMagicMock,
    sensor_service: NonCallableMagicMock,
) -> None:
    repository.aggregate_readings.return_value = [agg(9), agg(2)]

    response = service.compute_statistics(make(metrics=[TEMP_AVG]))

    assert [s.sensor_id for s in response.sensors] == [2, 9]
    assert repository.aggregate_readings.call_args.args[0] is None
    sensor_service.ensure_sensors_exist.assert_not_called()


def test_unknown_sensor_raises_not_found_before_querying(
    service: StatisticsService,
    repository: NonCallableMagicMock,
    sensor_service: NonCallableMagicMock,
) -> None:
    sensor_service.ensure_sensors_exist.side_effect = NotFoundError("Sensors not found: 999")

    with pytest.raises(NotFoundError):
        service.compute_statistics(make(sensor_ids=[1, 999], metrics=[TEMP_AVG]))

    sensor_service.ensure_sensors_exist.assert_called_once_with([1, 999])
    repository.aggregate_readings.assert_not_called()
