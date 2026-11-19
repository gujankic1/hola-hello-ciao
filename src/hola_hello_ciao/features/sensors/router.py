from fastapi import APIRouter

from hola_hello_ciao.core.errors import error_responses
from hola_hello_ciao.features.sensors.deps import SensorServiceDep
from hola_hello_ciao.features.sensors.schemas import SensorCreate, SensorId, SensorRead

router = APIRouter(prefix="/sensors", tags=["sensors"], responses=error_responses(500))


@router.post("", status_code=201, response_model=SensorRead, responses=error_responses(422))
def create_sensor(new_sensor: SensorCreate, sensor_service: SensorServiceDep) -> SensorRead:
    return sensor_service.create_sensor(new_sensor)


@router.get("", status_code=200, response_model=list[SensorRead])
def list_sensors(sensor_service: SensorServiceDep) -> list[SensorRead]:
    return sensor_service.list_sensors()


@router.get(
    "/{sensor_id}", status_code=200, response_model=SensorRead, responses=error_responses(404, 422)
)
def get_sensor(sensor_id: SensorId, sensor_service: SensorServiceDep) -> SensorRead:
    return sensor_service.get_sensor(sensor_id)
