from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from hola_hello_ciao.core.db import Base


class Reading(Base):
    """One metric value reported by a sensor. recorded_at is stored as naive UTC."""

    __tablename__ = "readings"
    __table_args__ = (
        Index("ix_readings_sensor_metric_time", "sensor_id", "metric", "recorded_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sensor_id: Mapped[int] = mapped_column(ForeignKey("sensors.id"))
    metric: Mapped[str] = mapped_column(String)
    value: Mapped[float] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column(DateTime)
