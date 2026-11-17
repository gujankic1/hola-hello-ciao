# hola-hello-ciao

A small web API built with FastAPI and SQLite.

> **Status:** early setup. Structure and documentation only; no application code yet.

## Stack

- Python 3.12+, [FastAPI](https://fastapi.tiangolo.com/)
- SQLite (single file)
- `uv` for environment and dependency management

Why this stack: [ADR-001](docs/arc42/09-architecture-decisions.md).

## Getting started

Not yet available — the project is not scaffolded. Planned:

```bash
uv sync
uv run fastapi dev
uv run pytest
```

## Documentation

- [Architecture (arc42)](docs/arc42/README.md) — what we build and why
- [AGENTS.md](AGENTS.md) — working mode, stack, and conventions for AI agents and contributors
