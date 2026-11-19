from datetime import UTC, datetime, timedelta
from unittest.mock import NonCallableMagicMock, create_autospec

import pytest

from hola_hello_ciao.core.errors import InvalidQueryError
from hola_hello_ciao.features.statistics.experimental_nlp_statistics_service import (
    ExperimentalNlpStatisticsService,
)
from hola_hello_ciao.features.statistics.schemas import (
    SensorStatistics,
    StatisticsQuery,
    StatisticsResponse,
)
from hola_hello_ciao.features.statistics.service import StatisticsService

T0 = datetime(2026, 11, 1, tzinfo=UTC)
T1 = T0 + timedelta(days=2)


@pytest.fixture
def statistics_service() -> NonCallableMagicMock:
    return create_autospec(StatisticsService, instance=True)


@pytest.fixture
def service(statistics_service: NonCallableMagicMock) -> ExperimentalNlpStatisticsService:
    return ExperimentalNlpStatisticsService(statistics_service)


def test_sentence_is_answered_as_the_query_it_reads_as_and_echoed(
    service: ExperimentalNlpStatisticsService, statistics_service: NonCallableMagicMock
) -> None:
    statistics_response = StatisticsResponse(
        from_=T0, to=T1, sensors=[SensorStatistics(sensor_id=1, results=[])]
    )
    statistics_service.compute_statistics.return_value = statistics_response
    expected_query = StatisticsQuery.model_validate(
        {
            "sensor_ids": [1],
            "metrics": [{"name": "temperature", "stat": "avg"}],
            "from": T0,
            "to": T1,
        }
    )

    response = service.compute_statistics(
        "average temperature for sensor 1 between 2026-11-01 and 2026-11-03"
    )

    statistics_service.compute_statistics.assert_called_once_with(expected_query)
    assert response.interpreted_query == expected_query
    assert (response.from_, response.to, response.sensors) == (T0, T1, statistics_response.sensors)


def test_unreadable_sentence_raises_before_querying(
    service: ExperimentalNlpStatisticsService, statistics_service: NonCallableMagicMock
) -> None:
    with pytest.raises(InvalidQueryError):
        service.compute_statistics("temperature please")

    statistics_service.compute_statistics.assert_not_called()
