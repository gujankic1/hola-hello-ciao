"""Local development commands. Not part of the application package (ADR-006).

uv run scripts/dev.py serve [--seed small|medium|large] [--reset]
uv run scripts/dev.py seed small|medium|large [--reset]
"""

import argparse
import time
from datetime import UTC, datetime
from pathlib import Path

import uvicorn
from alembic import command
from alembic.config import Config
from seed import DATASETS, floor_to, seed
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from hola_hello_ciao.core.config import get_settings
from hola_hello_ciao.core.db import create_db_engine
from hola_hello_ciao.sensors.models import Sensor

ROOT = Path(__file__).resolve().parent.parent


def reset_db(database_path: str) -> list[Path]:
    """Delete the SQLite file and its WAL/SHM side files; return what was deleted."""
    deleted = []
    for suffix in ("", "-wal", "-shm"):
        path = Path(database_path + suffix)
        if path.exists():
            path.unlink()
            deleted.append(path)
    return deleted


def migrate() -> None:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    command.upgrade(config, "head")


def seed_dataset(database_path: str, size: str) -> None:
    """Seed an empty database; SystemExit if it already has sensors."""
    spec = DATASETS[size]
    engine = create_db_engine(database_path)
    try:
        with Session(engine) as session:
            if session.scalar(select(func.count()).select_from(Sensor)):
                raise SystemExit(
                    f"{database_path} already has sensors; use --reset to start from scratch"
                )
            print(f"Seeding '{size}': {spec.sensors} sensors, ~{spec.total_readings:,} readings")
            started = time.perf_counter()
            end = floor_to(datetime.now(UTC).replace(tzinfo=None), spec.interval)
            result = seed(session, spec, end)
            elapsed = time.perf_counter() - started
    finally:
        engine.dispose()
    print(f"Seeded {result.sensors} sensors, {result.readings:,} readings in {elapsed:.1f}s")


def prepare(reset: bool, size: str | None) -> None:
    database_path = get_settings().database_path
    if reset:
        for path in reset_db(database_path):
            print(f"Deleted {path}")
    migrate()
    if size is not None:
        seed_dataset(database_path, size)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dev.py", description="Local development commands.")
    commands = parser.add_subparsers(dest="command", required=True)

    serve = commands.add_parser("serve", help="migrate, optionally seed, run the dev server")
    serve.add_argument("--seed", choices=DATASETS, help="seed this dataset first")
    serve.add_argument("--reset", action="store_true", help="delete the database first")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--no-reload", dest="reload", action="store_false")

    seed_cmd = commands.add_parser("seed", help="migrate and seed, no server")
    seed_cmd.add_argument("size", choices=DATASETS)
    seed_cmd.add_argument("--reset", action="store_true", help="delete the database first")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.command == "seed":
        prepare(args.reset, args.size)
        return
    prepare(args.reset, args.seed)
    uvicorn.run(
        "hola_hello_ciao.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        reload_dirs=[str(ROOT / "src")] if args.reload else None,
        workers=1,
    )


if __name__ == "__main__":
    main()
