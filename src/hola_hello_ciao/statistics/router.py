from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from hola_hello_ciao.core.deps import get_session
from hola_hello_ciao.statistics import service
from hola_hello_ciao.statistics.schemas import StatisticsQuery, StatisticsResponse

router = APIRouter(prefix="/readings/aggregate", tags=["statistics"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.post("", status_code=200, response_model=StatisticsResponse)
def query_statistics(payload: StatisticsQuery, session: SessionDep) -> StatisticsResponse:
    return service.query(session, payload)
