from pydantic import BaseModel, ConfigDict, field_validator


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
