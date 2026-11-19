from collections.abc import Iterator
from pathlib import Path

import dev
import pytest
from seed import DATASETS
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from hola_hello_ciao.core.config import get_settings
from hola_hello_ciao.core.db import create_db_engine
from hola_hello_ciao.features.readings.models import Reading


@pytest.fixture
def database_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    path = str(tmp_path / "dev.db")
    monkeypatch.setenv("DATABASE_PATH", path)
    get_settings.cache_clear()
    yield path
    get_settings.cache_clear()


def count_readings(database_path: str) -> int | None:
    engine = create_db_engine(database_path)
    with Session(engine) as session:
        count = session.scalar(select(func.count()).select_from(Reading))
    engine.dispose()
    return count


def test_parses_serve_with_seed_and_reset() -> None:
    args = dev.build_parser().parse_args(["serve", "--seed", "small", "--reset", "--no-reload"])

    assert (args.command, args.seed, args.reset, args.reload) == ("serve", "small", True, False)


def test_serve_defaults_to_no_seed_and_reload() -> None:
    args = dev.build_parser().parse_args(["serve"])

    assert (args.seed, args.reset, args.reload, args.port) == (None, False, True, 8000)


def test_rejects_unknown_dataset() -> None:
    with pytest.raises(SystemExit):
        dev.build_parser().parse_args(["seed", "huge"])


def test_seed_migrates_and_seeds_an_empty_database(database_path: str) -> None:
    dev.main(["seed", "small"])

    assert count_readings(database_path) == DATASETS["small"].total_readings


def test_seed_refuses_a_database_that_has_sensors(database_path: str) -> None:
    dev.main(["seed", "small"])

    with pytest.raises(SystemExit, match="--reset"):
        dev.main(["seed", "small"])


def test_reset_starts_from_scratch(database_path: str) -> None:
    dev.main(["seed", "small"])

    dev.main(["seed", "small", "--reset"])

    assert count_readings(database_path) == DATASETS["small"].total_readings


def test_reset_db_deletes_side_files(tmp_path: Path) -> None:
    db = tmp_path / "x.db"
    for path in (db, tmp_path / "x.db-wal", tmp_path / "x.db-shm"):
        path.touch()

    deleted = dev.reset_db(str(db))

    assert len(deleted) == 3
    assert not any(tmp_path.iterdir())
