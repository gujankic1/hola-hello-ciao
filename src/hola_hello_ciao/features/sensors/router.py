from fastapi import APIRouter

from hola_hello_ciao.core.deps import SessionDep
from hola_hello_ciao.features.sensors import service
from hola_hello_ciao.features.sensors.schemas import SensorCreate, SensorId, SensorRead

router = APIRouter(prefix="/sensors", tags=["sensors"])


@router.post("", status_code=201, response_model=SensorRead)
def create_sensor(new_sensor: SensorCreate, session: SessionDep) -> SensorRead:
    return service.create_sensor(session, new_sensor)


@router.get("", status_code=200, response_model=list[SensorRead])
def list_sensors(session: SessionDep) -> list[SensorRead]:
    return service.list_sensors(session)


@router.get("/{sensor_id}", status_code=200, response_model=SensorRead)
def get_sensor(sensor_id: SensorId, session: SessionDep) -> SensorRead:
    return service.get_sensor(session, sensor_id)
