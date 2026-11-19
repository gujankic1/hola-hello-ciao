from unittest.mock import NonCallableMagicMock, create_autospec

import pytest
from sqlalchemy.orm import Session


@pytest.fixture
def fake_session() -> NonCallableMagicMock:
    """Stand-in for the Session a service only passes through to its collaborators."""
    return create_autospec(Session, instance=True)
