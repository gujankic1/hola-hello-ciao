from fastapi import APIRouter

from hola_hello_ciao.features.statistics.deps import StatisticsServiceDep
from hola_hello_ciao.features.statistics.schemas import StatisticsQuery, StatisticsResponse

router = APIRouter(prefix="/readings/aggregate", tags=["statistics"])


@router.post("", status_code=200, response_model=StatisticsResponse)
def query_statistics(query: StatisticsQuery, service: StatisticsServiceDep) -> StatisticsResponse:
    return service.compute_statistics(query)
