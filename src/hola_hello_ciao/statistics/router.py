from fastapi import APIRouter

from hola_hello_ciao.core.deps import SessionDep
from hola_hello_ciao.statistics import service
from hola_hello_ciao.statistics.schemas import StatisticsQuery, StatisticsResponse

router = APIRouter(prefix="/readings/aggregate", tags=["statistics"])


@router.post("", status_code=200, response_model=StatisticsResponse)
def query_statistics(payload: StatisticsQuery, session: SessionDep) -> StatisticsResponse:
    return service.query(session, payload)
