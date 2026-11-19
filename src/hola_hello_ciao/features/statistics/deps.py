from typing import Annotated

from fastapi import Depends

from hola_hello_ciao.core.deps import SessionDep
from hola_hello_ciao.features.sensors.deps import SensorServiceDep
from hola_hello_ciao.features.statistics.repository import StatisticsRepository
from hola_hello_ciao.features.statistics.service import StatisticsService


def get_statistics_service(
    session: SessionDep, sensor_service: SensorServiceDep
) -> StatisticsService:
    return StatisticsService(StatisticsRepository(session), sensor_service)


StatisticsServiceDep = Annotated[StatisticsService, Depends(get_statistics_service)]
