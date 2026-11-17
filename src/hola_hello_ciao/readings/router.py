from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from hola_hello_ciao.core.deps import get_session
from hola_hello_ciao.readings import service
from hola_hello_ciao.readings.schemas import ReadingCreate, ReadingCreated

router = APIRouter(prefix="/sensors/{sensor_id}/readings", tags=["readings"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.post("", status_code=201, response_model=ReadingCreated)
def create_reading(sensor_id: int, payload: ReadingCreate, session: SessionDep) -> ReadingCreated:
    return service.ingest(session, sensor_id, payload)
