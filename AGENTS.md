# AGENTS.md

Guidance for AI coding agents (and humans) working in this repository.
Keep this file short and accurate. If reality and this file disagree, fix the file.

## Project

`hola-hello-ciao` — Weather Sensor Metrics API: receives sensor readings and (later) answers aggregate queries (min/max/sum/avg). Requirements: [arc42 chapter 1](docs/arc42/01-introduction-and-goals.md). Built as a take-home PoC: keep scope small, be able to explain every dependency and decision.
Architecture and decisions: see [docs/arc42/](docs/arc42/README.md).

## Working mode

- **Small, incremental changes.** One concern per change. Prefer the simplest thing that works.
- **Plan before large work.** For anything touching more than a few files or adding a dependency, state the plan first and get agreement.
- **Ask when ambiguous.** Don't guess at requirements; ask one focused question.
- **Docs travel with code.** Every change that affects architecture, a decision, or how to run the project updates the relevant arc42 file or README in the same change.
- **Record decisions.** A significant technical choice (stack, library, data model, infra) gets an ADR in `docs/arc42/09-architecture-decisions.md`.
- **Tests with code.** New behaviour ships with tests. Don't mark work done without running them.
- **No surprises.** Don't commit, push, delete data, or change infra unless asked. Never commit secrets.
- **Report honestly.** State what was run, what passed, what was not verified.

## Target tech stack

| Concern | Choice |
|---|---|
| Language | Python 3.12+ |
| Web framework | FastAPI (served by Uvicorn) |
| Database | SQLite (single file, WAL mode) |
| Data access | SQLAlchemy 2.x, synchronous (ADR-002) |
| Validation / config | Pydantic v2, `pydantic-settings` |
| Migrations | Alembic (`migrations/`; keep models and migrations in sync, enforced by `tests/unit/core/test_migrations.py`) |
| Packaging / env | `uv` (`pyproject.toml`, lockfile committed) |
| Tests | `pytest`, `httpx` test client |
| Lint / format / types | `ruff` (lint + format), `mypy` or `pyright` |

Do not add dependencies outside this list without an ADR or explicit approval.

## Target infrastructure

- **Single process:** one Uvicorn process; no orchestrator.
- **One host** (small VM or PaaS with persistent volume) — SQLite requires local, durable disk.
- SQLite file lives on durable local disk (`DATABASE_PATH`). Backups are out of scope for the PoC (arc42 chapter 11).
- Config via environment variables only (12-factor). `.env` for local dev, never committed; keep `.env.example` current.
- **Scaling constraint:** one writer instance. Horizontal scaling means revisiting ADR-001.

## Repository layout (target)

```
.
├── AGENTS.md
├── README.md
├── docs/arc42/          # architecture documentation
├── src/hola_hello_ciao/ # application package (main.py, core/, features/<feature>/, features/shared/)
├── scripts/             # dev tooling (start commands, seed data); not packaged, ADR-006
├── tests/
│   ├── unit/<feature>/         # service/schema tests, no HTTP
│   ├── integration/            # one file per route, through the HTTP API
│   └── scripts/                # tests for scripts/
└── pyproject.toml
```

Only create directories when there is something to put in them.

## Architecture rules (ADR-002)

- **Layers, one-way:** `router` → `service` → `repository`. Routers handle HTTP only; services hold business logic and never import FastAPI; only repositories touch SQL/ORM.
- **Feature folders:** each feature in `features/` has `router.py`, `schemas.py`, `service.py` and `repository.py`; services call repositories, never the `Session` API directly. Shared infra lives in `core/` (`config`, `db`, `deps`, `errors`, `types`).
- **`features/shared/`:** only business vocabulary (enums, value types, constants) used by two or more features. No tables, endpoints, services or repositories, and no imports from features. ORM models stay in the feature that owns the table.
- **Dependency injection with `Depends`** (`Annotated[X, Depends(get_x)]`) for the DB session (and settings when an endpoint needs them); services are plain functions taking the session. No other DI framework. Integration tests override via `app.dependency_overrides` with a temporary SQLite file.
- **Sync endpoints:** use `def`, not `async def`, with the sync SQLite driver. Never run blocking calls inside `async def`.
- **App setup:** app factory in `main.py`, `lifespan` for startup/shutdown (not `on_event`), one `APIRouter` per feature, version prefix `/api/v1`, a `/health` endpoint.
- **Schemas:** separate Pydantic models for input and output; set `response_model` and explicit status codes.
- **Errors:** raise domain exceptions mapped by exception handlers in `core/errors.py`, with one consistent error shape. Repositories wrap DB calls in `storage_errors(session, "<specific message>")` (rollback + `StorageError`); the global `SQLAlchemyError` handler is only a fallback with a generic message; a catch-all `Exception` handler returns a generic 500 in the same shape.
- **Run with a single worker** (SQLite single writer).

## Conventions

- **Tests are sorted by level, then feature:**
  - `tests/unit/<feature>/test_<module>.py` mirrors `src/hola_hello_ciao/features/<feature>/` and tests services/repositories/schemas directly, without HTTP.
  - Unit tests test one unit (ADR-007): service tests replace the feature's `repository` module and other features' service functions with `create_autospec` mocks via `monkeypatch`, and pass `fake_session` (`tests/unit/conftest.py`). Repository tests use the real temp SQLite file. Integration tests use no mocks. Routers get no unit tests.
  - `tests/integration/test_<method>_<route>.py` has one file per route, named after it (`/sensors/{sensor_id}/readings` -> `test_post_sensors_readings.py`), and calls the app through `TestClient`.
  - Shared fixtures (temp SQLite file, `session`, `client`, `sensor_id`) live in `tests/conftest.py`. Every test directory has an `__init__.py` (same file names recur across features).
- Descriptive names, also for loop and comprehension variables (`for aggregate in aggregates`, not `for a in ...`); only `i`/`j` counters and `e` for exceptions stay short. Inline one-liners; extract a function only for logic worth naming.
- Type-hint all public functions. Routers stay thin; logic lives in services that are testable without HTTP.
- Request/response bodies are Pydantic models; never return raw DB rows.
- Use parameterised queries / ORM only. No string-built SQL.
- Enable `PRAGMA foreign_keys=ON` and `journal_mode=WAL` on every connection.
- Settings come from one `Settings` object; no `os.environ` reads scattered in code.
- Commit messages: imperative mood, subject ≤ 72 chars, explain *why* in the body.

## Commands

```bash
uv sync                                               # install
uv run alembic upgrade head                           # create/upgrade the SQLite schema
uv run fastapi dev                                    # run locally (http://127.0.0.1:8000/docs)
uv run scripts/dev.py serve [--seed small|medium|large] [--reset]  # migrate (+ seed) + run
uv run scripts/dev.py seed small|medium|large [--reset]            # migrate + seed only
uv run pytest                                         # all tests
uv run pytest tests/unit                              # unit tests only
uv run pytest tests/integration                       # integration tests only
uv run ruff check . && uv run ruff format --check .   # lint + format check
uv run mypy                                           # type check
```

## Definition of done

1. Code works and tests pass locally.
2. Lint/format/type checks clean.
3. Docs (README / arc42 / ADR) updated where affected.
4. No secrets, no stray `.db` files, no unrelated changes.
