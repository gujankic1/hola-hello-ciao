from datetime import UTC, datetime

import pytest
from pydantic import TypeAdapter

from hola_hello_ciao.core.types import UtcDatetime

adapter = TypeAdapter(UtcDatetime)


@pytest.mark.parametrize(
    "raw",
    [
        "2026-11-17T10:00:00Z",
        "2026-11-17T12:00:00+02:00",  # offset converted
        "2026-11-17T10:00:00",  # naive taken as UTC
    ],
)
def test_values_become_aware_utc(raw: str) -> None:
    value = adapter.validate_python(raw)

    assert value == datetime(2026, 11, 17, 10, 0, tzinfo=UTC)
    assert value.tzinfo is UTC
