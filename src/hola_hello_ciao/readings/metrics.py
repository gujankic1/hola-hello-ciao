from enum import StrEnum


class Metric(StrEnum):
    """Closed set of metrics a sensor may report (ADR-005). Stored as plain strings."""

    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    WIND_SPEED = "wind_speed"
    PRESSURE = "pressure"
    RAINFALL = "rainfall"
