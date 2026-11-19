from typing import Annotated

from fastapi import Depends

from hola_hello_ciao.core.deps import SessionDep
from hola_hello_ciao.features.readings.repository import ReadingRepository
from hola_hello_ciao.features.readings.service import ReadingService
from hola_hello_ciao.features.sensors.deps import SensorServiceDep


def get_reading_service(session: SessionDep, sensor_service: SensorServiceDep) -> ReadingService:
    return ReadingService(ReadingRepository(session), sensor_service)


ReadingServiceDep = Annotated[ReadingService, Depends(get_reading_service)]
