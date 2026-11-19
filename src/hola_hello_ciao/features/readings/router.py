from fastapi import APIRouter

from hola_hello_ciao.features.readings.deps import ReadingServiceDep
from hola_hello_ciao.features.readings.schemas import ReadingCreate, ReadingCreated
from hola_hello_ciao.features.sensors.schemas import SensorId

router = APIRouter(prefix="/sensors/{sensor_id}/readings", tags=["readings"])


@router.post("", status_code=201, response_model=ReadingCreated)
def create_reading(
    sensor_id: SensorId, reading: ReadingCreate, service: ReadingServiceDep
) -> ReadingCreated:
    return service.ingest_reading(sensor_id, reading)
