# hola-hello-ciao

Weather Sensor Metrics API: sensors report readings (temperature, humidity, wind speed, pressure, rainfall), and clients query aggregates over them (min, max, sum, average). Built with FastAPI and SQLite.

## Run

Requires [uv](https://docs.astral.sh/uv/); it installs a suitable Python (3.12+) if none is present.

```bash
uv sync
uv run scripts/dev.py serve --seed small   # create the database, add sample data, start the server
```

Then open the interactive API docs: **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**. Every endpoint can be tried from there.

Without sample data, using the standard tools directly:

```bash
uv run alembic upgrade head   # create or upgrade the database (./data/app.db)
uv run fastapi dev            # start the server with reload
```

The database location is set with `DATABASE_PATH` (see `.env.example`).

### Dev commands

```bash
uv run scripts/dev.py serve [--seed small|medium|large] [--reset] [--host H] [--port P] [--no-reload]
uv run scripts/dev.py seed small|medium|large [--reset]
```

Both migrate the database first. Seeding refuses a database that already has sensors; `--reset` deletes it first. Sample data is synthetic and ends at the current time, so the default "last 24 hours" query returns results.

| Dataset | Sensors | Interval | History | Readings |
|---|---|---|---|---|
| `small` | 3 | 1 h | 7 days | 2,520 |
| `medium` | 20 | 30 min | 30 days | 144,000 |
| `large` | 100 | 30 min | 90 days | 2,160,000 |

## What the API does

Three resources, all under `/api/v1`:

| Endpoint | Purpose |
|---|---|
| `POST /sensors`, `GET /sensors`, `GET /sensors/{id}` | Register, list and fetch sensors |
| `POST /sensors/{id}/readings` | Report metric values a sensor measured at one point in time |
| `POST /readings/aggregate` | Query a statistic per metric over a time window, for some or all sensors |
| `GET /health` | Liveness check |

How it behaves:

- **Sensors are registered first.** Readings for an unknown sensor are rejected (404); sensors are never created implicitly.
- **Readings** carry one or more metrics from a fixed set and the time they were measured (`recorded_at`, in UTC; values without an offset are taken as UTC). Reporting is idempotent: sending the same reading again changes nothing, and a different value for an already stored reading is rejected (409).
- **Aggregates** return one result per sensor and metric: `min`, `max`, `sum` or `avg`, plus the number of readings used. Leave out the sensors to query all of them. The window defaults to the last 24 hours and can be 1 to 31 days. A sensor with no readings in the window gets `null`.
- **Errors** share one JSON shape, `{"error": {"code", "message", "details"}}`, with standard status codes (404, 409, 422, 500).

Design decisions behind this: [architecture decisions](docs/arc42/09-architecture-decisions.md).

## Test

```bash
uv run pytest                                                      # all tests
uv run ruff check . && uv run ruff format --check . && uv run mypy  # lint, format, types
```

## Documentation

- [Architecture (arc42)](docs/arc42/README.md): approach, decisions, trade-offs, risks and next steps
- [AGENTS.md](AGENTS.md): conventions for contributors and AI agents
