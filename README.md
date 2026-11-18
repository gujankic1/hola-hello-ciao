# hola-hello-ciao

Weather Sensor Metrics API: receives readings from sensors (temperature, humidity, wind speed, ...) and answers aggregate queries (min/max/sum/avg) over them. Built with FastAPI and SQLite.

> **Status:** complete for the brief. Registering sensors, ingesting readings and the statistics query work end to end.

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

Register a sensor, then report readings for it. `recorded_at` is required; values without an offset are taken as UTC:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/sensors \
  -H 'Content-Type: application/json' -d '{"name": "roof-station"}'
# -> {"id": 1, "name": "roof-station"}

curl -X POST http://127.0.0.1:8000/api/v1/sensors/1/readings \
  -H 'Content-Type: application/json' \
  -d '{"metrics": {"temperature": 21.5, "humidity": 40}, "recorded_at": "2026-11-17T10:00:00Z"}'
```

Ingest is idempotent per sensor, metric and `recorded_at`: retrying the same call stores nothing new and returns 201 again, while a different value for an existing reading returns 409 and stores nothing from that call ([ADR-003](docs/arc42/09-architecture-decisions.md)).

Allowed metrics: `temperature`, `humidity`, `wind_speed`, `pressure`, `rainfall`; any other name is rejected with 422 ([ADR-005](docs/arc42/09-architecture-decisions.md)).

Query statistics (min, max, sum or avg per metric): average temperature and humidity of sensor 1 over a window. Omit `sensor_ids` for all sensors (at most 1000 IDs per query); omit `from`/`to` for the last 24 h; a window must be 1 day to 31 days (`from` and `to` together, or `to` alone):

```bash
curl -X POST http://127.0.0.1:8000/api/v1/readings/statistics \
  -H 'Content-Type: application/json' \
  -d '{"sensor_ids": [1], "from": "2026-11-10T00:00:00Z", "to": "2026-11-17T00:00:00Z",
       "metrics": [{"name": "temperature", "stat": "avg"}, {"name": "humidity", "stat": "avg"}]}'
# -> {"from": ..., "to": ..., "results": [{"sensor_id": 1, "metric": "temperature", "stat": "avg", "value": 21.2, "count": 14}, ...]}
```

Results are per sensor and metric; `value` is `null` when there are no readings in the window.

List or fetch sensors with `GET /api/v1/sensors` and `GET /api/v1/sensors/{id}` (404 if unknown; the list is not paginated).

Reporting for an unknown sensor returns 404; sensors are never created implicitly.
Errors share one shape: `{"error": {"code": "...", "message": "...", "details": [...]}}`, including unexpected failures (500, no internals exposed); routing errors (unknown path or method) keep FastAPI's default `{"detail": ...}`.
Sensor IDs outside 1 to 2^63-1 are rejected with 422.
`GET /health` returns `{"status": "ok"}`.

## Test

```bash
uv run pytest                    # all
uv run pytest tests/unit         # unit tests, by feature (no HTTP)
uv run pytest tests/integration  # one file per route, through the HTTP API
uv run ruff check . && uv run ruff format --check . && uv run mypy
```

## Approach and trade-offs

- One FastAPI app, one SQLite file, one process: the simplest thing that meets the brief.
- Readings are stored one row per metric value ([ADR-003](docs/arc42/09-architecture-decisions.md)); metric names are a closed enum ([ADR-005](docs/arc42/09-architecture-decisions.md)).
- Layered by feature (router → service → DB), see [ADR-002](docs/arc42/09-architecture-decisions.md).
- REST design: sensor-scoped ingest, collection-level `POST /readings/statistics` for queries ([ADR-004](docs/arc42/09-architecture-decisions.md)).

## Known limitations and next steps

Full list with triggers and mitigations: [arc42 chapter 11](docs/arc42/11-risks-and-technical-debt.md). In the order I would tackle them:

1. **Authentication.** There is none yet; API keys per sensor and per client would be the first step.
2. **Query cost at scale.** At about 13M rows, queries over all sensors take 1–2 s, while queries for named sensors stay in milliseconds. Fixes: an extra index, then pre-aggregated rollups, then PostgreSQL/TimescaleDB if one host is no longer enough.
3. **Plausibility checks.** Add per-metric value ranges and reject future timestamps.
4. **Operations.** Add structured logging, a database readiness check, CI, scheduled backups and a retention policy.

## Documentation

- [Architecture (arc42)](docs/arc42/README.md): what we build and why
- [AGENTS.md](AGENTS.md): working mode, stack and conventions for AI agents and contributors
