from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from hola_hello_ciao.core.db import Base


class Sensor(Base):
    __tablename__ = "sensors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str | None] = mapped_column(String)
