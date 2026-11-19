from enum import StrEnum


class Metric(StrEnum):
    """A metric a sensor can report; any other name is rejected."""

    # Closed set (ADR-005); stored as plain strings. Docstrings here end up in OpenAPI.

    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    WIND_SPEED = "wind_speed"
    PRESSURE = "pressure"
    RAINFALL = "rainfall"
