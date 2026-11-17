from pydantic import BaseModel, field_validator


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
    id: int
    name: str | None
