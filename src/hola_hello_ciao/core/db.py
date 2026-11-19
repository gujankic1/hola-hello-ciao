from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session

from hola_hello_ciao.core.errors import StorageError


class Base(DeclarativeBase):
    pass


def sqlite_url(database_path: str) -> str:
    return f"sqlite:///{database_path}"


def create_db_engine(database_path: str) -> Engine:
    """Create a SQLite engine with foreign keys and WAL enabled on every connection."""
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        sqlite_url(database_path),
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _set_pragmas(dbapi_connection: Any, _record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    return engine


@contextmanager
def storage_errors(session: Session, message: str) -> Generator[None, None, None]:
    """Roll back and re-raise database failures as StorageError with a specific message."""
    try:
        yield
    except SQLAlchemyError as exc:
        session.rollback()
        raise StorageError(message) from exc
