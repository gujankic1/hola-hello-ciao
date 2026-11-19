from datetime import UTC, datetime

from hola_hello_ciao.features.statistics.experimental_nlp_parser_utils import parse_statistics_query
from hola_hello_ciao.features.statistics.schemas import NlpStatisticsResponse
from hola_hello_ciao.features.statistics.service import StatisticsService


class ExperimentalNlpStatisticsService:
    """Answers an English sentence as an aggregate query (experimental, ADR-009)."""

    def __init__(self, statistics_service: StatisticsService) -> None:
        self._statistics_service = statistics_service

    def compute_statistics(self, sentence: str) -> NlpStatisticsResponse:
        """Read the sentence as a query and answer it like `StatisticsService`; InvalidQueryError
        if it cannot be read."""
        query = parse_statistics_query(sentence, datetime.now(UTC))
        response = self._statistics_service.compute_statistics(query)
        return NlpStatisticsResponse(
            from_=response.from_, to=response.to, sensors=response.sensors, interpreted_query=query
        )
