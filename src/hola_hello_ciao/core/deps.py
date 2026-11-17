from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from hola_hello_ciao.core.config import get_settings
from hola_hello_ciao.core.db import create_db_engine


@lru_cache
def get_engine() -> Engine:
    return create_db_engine(get_settings().database_path)


def get_session() -> Iterator[Session]:
    """One session per request."""
    with Session(get_engine()) as session:
        yield session
