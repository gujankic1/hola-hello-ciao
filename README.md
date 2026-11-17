# hola-hello-ciao

Weather Sensor Metrics API: receives readings from sensors (temperature, humidity, wind speed, ...) and will answer aggregate queries (min/max/sum/avg) over them. Built with FastAPI and SQLite.

> **Status:** slice 1. Registering sensors and ingesting readings work end to end; the statistics query is next.

## Stack

Python 3.12+, [FastAPI](https://fastapi.tiangolo.com/), SQLAlchemy 2 + Alembic, SQLite, `uv`. Why: [ADR-001](docs/arc42/09-architecture-decisions.md).

## Run

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run alembic upgrade head   # creates ./data/app.db
uv run fastapi dev            # http://127.0.0.1:8000  (interactive docs at /docs)
```

The database path can be changed with `DATABASE_PATH` (see `.env.example`).

## API

Endpoint design and planned endpoints: [ADR-004](docs/arc42/09-architecture-decisions.md).

Register a sensor, then report readings for it (`recorded_at` is optional and defaults to now, UTC):

```bash
curl -X POST http://127.0.0.1:8000/api/v1/sensors \
  -H 'Content-Type: application/json' -d '{"name": "roof-station"}'
# -> {"id": 1, "name": "roof-station"}

curl -X POST http://127.0.0.1:8000/api/v1/sensors/1/readings \
  -H 'Content-Type: application/json' \
  -d '{"metrics": {"temperature": 21.5, "humidity": 40}}'
```

Allowed metrics: `temperature`, `humidity`, `wind_speed`, `pressure`, `rainfall`; any other name is rejected with 422 ([ADR-005](docs/arc42/09-architecture-decisions.md)).

Reporting for an unknown sensor returns 404; sensors are never created implicitly.
Errors share one shape: `{"error": {"code": "...", "message": "...", "details": [...]}}`.
`GET /health` returns `{"status": "ok"}`.

## Test

```bash
uv run pytest                    # all
uv run pytest tests/unit         # unit tests, by feature (no HTTP)
uv run pytest tests/integration  # one file per route, through the HTTP API
uv run ruff check . && uv run mypy
```

## Approach and trade-offs

- One FastAPI app, one SQLite file, one process: the simplest thing that meets the brief.
- Readings are stored one row per metric value ([ADR-003](docs/arc42/09-architecture-decisions.md)); metric names are a closed enum ([ADR-005](docs/arc42/09-architecture-decisions.md)).
- Layered by feature (router → service → DB), see [ADR-002](docs/arc42/09-architecture-decisions.md).
- REST design: sensor-scoped ingest, collection-level `POST /readings/statistics` for queries ([ADR-004](docs/arc42/09-architecture-decisions.md)).
- Not yet done: the statistics endpoint (sensors, metrics, statistic, 1 day to 1 month range), sensor listing/lookup, authentication, Docker.

## Documentation

- [Architecture (arc42)](docs/arc42/README.md): what we build and why
- [AGENTS.md](AGENTS.md): working mode, stack and conventions for AI agents and contributors
