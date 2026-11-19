from fastapi import APIRouter

from hola_hello_ciao.core.errors import error_responses
from hola_hello_ciao.features.statistics.deps import (
    ExperimentalNlpStatisticsServiceDep,
    StatisticsServiceDep,
)
from hola_hello_ciao.features.statistics.schemas import (
    NlpQuery,
    NlpStatisticsResponse,
    StatisticsQuery,
    StatisticsResponse,
)

router = APIRouter(
    prefix="/readings/aggregate", tags=["statistics"], responses=error_responses(500)
)
# Mounted under /api/experimental: no stability guarantee (ADR-009).
experimental_router = APIRouter(
    prefix="/readings/aggregate", tags=["experimental"], responses=error_responses(500)
)


@router.post(
    "", status_code=200, response_model=StatisticsResponse, responses=error_responses(404, 422)
)
def query_statistics(
    query: StatisticsQuery, statistics_service: StatisticsServiceDep
) -> StatisticsResponse:
    return statistics_service.compute_statistics(query)


@experimental_router.post(
    "",
    status_code=200,
    response_model=NlpStatisticsResponse,
    responses=error_responses(404, 422),
)
def query_statistics_from_text(
    nlp_query: NlpQuery, experimental_nlp_statistics_service: ExperimentalNlpStatisticsServiceDep
) -> NlpStatisticsResponse:
    """Experimental, may change or disappear without notice. The sentence names statistics
    (min, max, sum, avg) before metrics, and optionally sensors and a time range; the response
    shows how it was read."""
    return experimental_nlp_statistics_service.compute_statistics(nlp_query.query)
