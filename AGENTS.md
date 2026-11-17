# AGENTS.md

Guidance for AI coding agents (and humans) working in this repository.
Keep this file short and accurate. If reality and this file disagree, fix the file.

## Project

`hola-hello-ciao` — a small web API. Purpose and scope: see [README.md](README.md).
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
| Data access | Synchronous (see ADR-002). SQLAlchemy 2.x or plain `sqlite3` — decide when the first table is needed |
| Validation / config | Pydantic v2, `pydantic-settings` |
| Migrations | Alembic (once a schema exists) |
| Packaging / env | `uv` (`pyproject.toml`, lockfile committed) |
| Tests | `pytest`, `httpx` test client |
| Lint / format / types | `ruff` (lint + format), `mypy` or `pyright` |

Do not add dependencies outside this list without an ADR or explicit approval.

## Target infrastructure

> Confirmed 2026-11-17. Provider/host still open; update here and in arc42 chapter 7 when chosen.

- **Single container** (Docker) running one Uvicorn process; no orchestrator.
- **One host** (small VM or PaaS with persistent volume) — SQLite requires local, durable disk.
- SQLite file lives on a mounted volume (`DATABASE_PATH`), backed up by copying the file (`sqlite3 .backup`).
- Config via environment variables only (12-factor). `.env` for local dev, never committed; keep `.env.example` current.
- **Scaling constraint:** one writer instance. Horizontal scaling means revisiting ADR-001.

## Repository layout (target)

```
.
├── AGENTS.md
├── README.md
├── docs/arc42/          # architecture documentation
├── src/hola_hello_ciao/ # application package (main.py, core/, one folder per feature)
├── tests/
└── pyproject.toml
```

Only create directories when there is something to put in them. Full layout: [arc42 chapter 5](docs/arc42/05-building-blocks.md).

## Architecture rules (ADR-002)

- **Layers, one-way:** `router` → `service` → `repository`. Routers handle HTTP only; services hold business logic and never import FastAPI; only repositories touch SQL/ORM.
- **Feature folders:** each feature has `router.py`, `schemas.py`, `service.py` and, when queries need sharing, `repository.py`. Shared infra lives in `core/` (`config`, `db`, `deps`, `errors`).
- **Dependency injection with `Depends`** (`Annotated[X, Depends(get_x)]`) for settings, DB session and services. No other DI framework. Tests override via `app.dependency_overrides` with a temporary SQLite file.
- **Sync endpoints:** use `def`, not `async def`, with the sync SQLite driver. Never run blocking calls inside `async def`.
- **App setup:** app factory in `main.py`, `lifespan` for startup/shutdown (not `on_event`), one `APIRouter` per feature, version prefix `/api/v1`, a `/health` endpoint.
- **Schemas:** separate Pydantic models for input and output; set `response_model` and explicit status codes.
- **Errors:** raise domain exceptions mapped by exception handlers in `core/errors.py`, with one consistent error shape.
- **Run with a single worker** (SQLite single writer).

## Conventions

- Type-hint all public functions. Routers stay thin; logic lives in services that are testable without HTTP.
- Request/response bodies are Pydantic models; never return raw DB rows.
- Use parameterised queries / ORM only. No string-built SQL.
- Enable `PRAGMA foreign_keys=ON` and `journal_mode=WAL` on every connection.
- Settings come from one `Settings` object; no `os.environ` reads scattered in code.
- Commit messages: imperative mood, subject ≤ 72 chars, explain *why* in the body.

## Commands

> To be filled in once the project is scaffolded. Expected:

```bash
uv sync                          # install
uv run fastapi dev               # run locally
uv run pytest                    # test
uv run ruff check . && uv run ruff format --check .   # lint
```

## Definition of done

1. Code works and tests pass locally.
2. Lint/format/type checks clean.
3. Docs (README / arc42 / ADR) updated where affected.
4. No secrets, no stray `.db` files, no unrelated changes.
