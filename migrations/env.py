from alembic import context

from hola_hello_ciao.core.config import get_settings
from hola_hello_ciao.core.db import Base, create_db_engine, sqlite_url
from hola_hello_ciao.readings import models as readings_models  # noqa: F401
from hola_hello_ciao.sensors import models as sensors_models  # noqa: F401

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=sqlite_url(get_settings().database_path),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_db_engine(get_settings().database_path)
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                render_as_batch=True,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()  # a leaked connection would linger in the caller's process


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
