from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, NonCallableMagicMock, create_autospec

import pytest

from hola_hello_ciao.core.errors import NotFoundError
from hola_hello_ciao.features.shared.metrics import Metric
from hola_hello_ciao.features.statistics import repository, service
from hola_hello_ciao.features.statistics.repository import Aggregate
from hola_hello_ciao.features.statistics.schemas import Stat, StatisticsQuery

T0 = datetime(2026, 11, 1, tzinfo=UTC)
T1 = T0 + timedelta(days=2)
TEMP_AVG = {"name": "temperature", "stat": "avg"}


@pytest.fixture
def repo(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = create_autospec(repository)
    mock.aggregate.return_value = []
    monkeypatch.setattr(service, "repository", mock)
    return mock


@pytest.fixture
def ensure_sensors_exist(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = create_autospec(service.ensure_sensors_exist)
    monkeypatch.setattr(service, "ensure_sensors_exist", mock)
    return mock


def make(**kwargs: object) -> StatisticsQuery:
    return StatisticsQuery.model_validate(kwargs)


def agg(sensor_id: int, metric: str = "temperature", n: int = 3) -> Aggregate:
    return Aggregate(sensor_id, metric, min=10, max=60, sum=90, avg=30, n=n)


@pytest.mark.usefixtures("ensure_sensors_exist")
def test_each_stat_is_picked_from_the_aggregate(
    repo: MagicMock, fake_session: NonCallableMagicMock
) -> None:
    repo.aggregate.return_value = [agg(1)]
    metrics = [{"name": "temperature", "stat": s.value} for s in Stat]

    response = service.query(
        fake_session, make(sensor_ids=[1], metrics=metrics, **{"from": T0, "to": T1})
    )

    repo.aggregate.assert_called_once_with(fake_session, [1], [Metric.TEMPERATURE] * 4, T0, T1)
    assert {r.stat: r.value for r in response.results} == {
        Stat.MIN: 10,
        Stat.MAX: 60,
        Stat.SUM: 90,
        Stat.AVG: 30,
    }
    assert {r.count for r in response.results} == {3}
    assert (response.from_, response.to) == (T0, T1)


def test_default_window_is_last_24_hours(
    repo: MagicMock, fake_session: NonCallableMagicMock
) -> None:
    response = service.query(fake_session, make(metrics=[TEMP_AVG]))

    assert response.to - response.from_ == timedelta(hours=24)
    assert abs(response.to - datetime.now(UTC)) < timedelta(seconds=10)
    _, _, _, start, end = repo.aggregate.call_args.args
    assert (start, end) == (response.from_, response.to)


def test_only_to_given_uses_24_hours_before_it(
    repo: MagicMock, fake_session: NonCallableMagicMock
) -> None:
    response = service.query(fake_session, make(metrics=[TEMP_AVG], to=T0))

    assert response.from_ == T0 - timedelta(hours=24)


@pytest.mark.usefixtures("ensure_sensors_exist")
def test_requested_sensor_without_data_yields_null_value(
    repo: MagicMock, fake_session: NonCallableMagicMock
) -> None:
    repo.aggregate.return_value = [agg(1, "temperature")]

    response = service.query(
        fake_session, make(sensor_ids=[1, 2], metrics=[{"name": "humidity", "stat": "avg"}])
    )

    assert [(r.sensor_id, r.value, r.count) for r in response.results] == [
        (1, None, 0),
        (2, None, 0),
    ]


def test_all_sensors_lists_only_sensors_with_data_sorted_and_skips_existence_check(
    repo: MagicMock, ensure_sensors_exist: MagicMock, fake_session: NonCallableMagicMock
) -> None:
    repo.aggregate.return_value = [agg(9), agg(2)]

    response = service.query(fake_session, make(metrics=[TEMP_AVG]))

    assert [r.sensor_id for r in response.results] == [2, 9]
    assert repo.aggregate.call_args.args[1] is None
    ensure_sensors_exist.assert_not_called()


def test_unknown_sensor_raises_not_found_before_querying(
    repo: MagicMock, ensure_sensors_exist: MagicMock, fake_session: NonCallableMagicMock
) -> None:
    ensure_sensors_exist.side_effect = NotFoundError("Sensors not found: 999")

    with pytest.raises(NotFoundError):
        service.query(fake_session, make(sensor_ids=[1, 999], metrics=[TEMP_AVG]))

    ensure_sensors_exist.assert_called_once_with(fake_session, [1, 999])
    repo.aggregate.assert_not_called()
