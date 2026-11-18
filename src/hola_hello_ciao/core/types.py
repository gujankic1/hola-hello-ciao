from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator


def _to_utc(value: datetime) -> datetime:
    """Offsets are converted to UTC; naive datetimes are taken as UTC."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


# Every datetime the API accepts; services can rely on it being timezone-aware UTC.
UtcDatetime = Annotated[datetime, AfterValidator(_to_utc)]
