from typing import Annotated

from fastapi import Depends

from hola_hello_ciao.core.deps import SessionDep
from hola_hello_ciao.features.sensors.repository import SensorRepository
from hola_hello_ciao.features.sensors.service import SensorService


def get_sensor_service(session: SessionDep) -> SensorService:
    return SensorService(SensorRepository(session))


SensorServiceDep = Annotated[SensorService, Depends(get_sensor_service)]
