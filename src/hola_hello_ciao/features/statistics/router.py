from fastapi import APIRouter

from hola_hello_ciao.core.errors import error_responses
from hola_hello_ciao.features.statistics.deps import StatisticsServiceDep
from hola_hello_ciao.features.statistics.schemas import StatisticsQuery, StatisticsResponse

router = APIRouter(
    prefix="/readings/aggregate", tags=["statistics"], responses=error_responses(500)
)


@router.post(
    "", status_code=200, response_model=StatisticsResponse, responses=error_responses(404, 422)
)
def query_statistics(
    query: StatisticsQuery, statistics_service: StatisticsServiceDep
) -> StatisticsResponse:
    return statistics_service.compute_statistics(query)
