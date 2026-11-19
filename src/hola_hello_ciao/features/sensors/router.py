from fastapi import APIRouter

from hola_hello_ciao.features.sensors.deps import SensorServiceDep
from hola_hello_ciao.features.sensors.schemas import SensorCreate, SensorId, SensorRead

router = APIRouter(prefix="/sensors", tags=["sensors"])


@router.post("", status_code=201, response_model=SensorRead)
def create_sensor(new_sensor: SensorCreate, service: SensorServiceDep) -> SensorRead:
    return service.create_sensor(new_sensor)


@router.get("", status_code=200, response_model=list[SensorRead])
def list_sensors(service: SensorServiceDep) -> list[SensorRead]:
    return service.list_sensors()


@router.get("/{sensor_id}", status_code=200, response_model=SensorRead)
def get_sensor(sensor_id: SensorId, service: SensorServiceDep) -> SensorRead:
    return service.get_sensor(sensor_id)
