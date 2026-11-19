from fastapi import APIRouter

from hola_hello_ciao.core.deps import SessionDep
from hola_hello_ciao.readings import service
from hola_hello_ciao.readings.schemas import ReadingCreate, ReadingCreated
from hola_hello_ciao.sensors.schemas import SensorId

router = APIRouter(prefix="/sensors/{sensor_id}/readings", tags=["readings"])


@router.post("", status_code=201, response_model=ReadingCreated)
def create_reading(
    sensor_id: SensorId, payload: ReadingCreate, session: SessionDep
) -> ReadingCreated:
    return service.ingest(session, sensor_id, payload)
