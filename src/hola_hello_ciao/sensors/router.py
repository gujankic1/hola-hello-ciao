from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from hola_hello_ciao.core.deps import get_session
from hola_hello_ciao.sensors import service
from hola_hello_ciao.sensors.schemas import SensorCreate, SensorRead

router = APIRouter(prefix="/sensors", tags=["sensors"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.post("", status_code=201, response_model=SensorRead)
def create_sensor(payload: SensorCreate, session: SessionDep) -> SensorRead:
    return service.create_sensor(session, payload)


@router.get("", status_code=200, response_model=list[SensorRead])
def list_sensors(session: SessionDep) -> list[SensorRead]:
    return service.list_sensors(session)


@router.get("/{sensor_id}", status_code=200, response_model=SensorRead)
def get_sensor(sensor_id: int, session: SessionDep) -> SensorRead:
    return service.get_sensor(session, sensor_id)
