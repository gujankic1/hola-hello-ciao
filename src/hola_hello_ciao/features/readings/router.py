from fastapi import APIRouter

from hola_hello_ciao.core.errors import error_responses
from hola_hello_ciao.features.readings.deps import ReadingServiceDep
from hola_hello_ciao.features.readings.schemas import ReadingCreate, ReadingCreated
from hola_hello_ciao.features.sensors.schemas import SensorId

router = APIRouter(
    prefix="/sensors/{sensor_id}/readings", tags=["readings"], responses=error_responses(500)
)


@router.post(
    "", status_code=201, response_model=ReadingCreated, responses=error_responses(404, 409, 422)
)
def create_reading(
    sensor_id: SensorId, reading: ReadingCreate, service: ReadingServiceDep
) -> ReadingCreated:
    return service.ingest_reading(sensor_id, reading)
