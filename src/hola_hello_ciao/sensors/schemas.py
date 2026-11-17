from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

# A sensor ID as clients may send it: SQLite rowids start at 1 and are signed 64-bit, so
# anything outside this range cannot exist and would crash the driver (OverflowError).
MAX_SENSOR_ID = 2**63 - 1
SensorId = Annotated[int, Field(ge=1, le=MAX_SENSOR_ID)]


class SensorCreate(BaseModel):
    name: str | None = None

    @field_validator("name")
    @classmethod
    def _check_name(cls, name: str | None) -> str | None:
        if name is None:
            return None
        name = name.strip()
        if not name:
            raise ValueError("name must not be blank")
        return name


class SensorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str | None
