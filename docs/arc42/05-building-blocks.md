# 5. Building blocks

See [ADR-002](09-architecture-decisions.md). Features live in `features/`: `sensors` (registry), `readings` (ingest) and `statistics` (aggregate query; its own repository reads the `readings` table and uses `sensors` to filter by sensor; for the experimental endpoint, `ExperimentalNlpStatisticsService` reads an English sentence as a query with `experimental_nlp_parser_utils.py` and has `StatisticsService` answer it, ADR-009; how the sentence is parsed, step by step and pattern by pattern, is documented in that module). Both get `SensorService` injected for the 404 check (`get_sensor`, `ensure_sensors_exist`). `features/shared/` holds the `Metric` enum, used by `readings` and `statistics`. Every feature has a `repository` and a `deps.py` with its providers; services never see the `Session`. Create folders only when needed.

## Layers

```
 HTTP ──> api (router, schemas) ──> service (logic) ──> repository (SQL/ORM) ──> SQLite
```

| Layer | Responsibility | Must not |
|---|---|---|
| api | Parse/validate requests, status codes, auth, response models | Contain business rules or SQL |
| service | Business rules, orchestration | Import FastAPI or know about HTTP |
| repository | Queries and persistence | Contain business rules |

Dependencies point one way only (api → service → repository).

## Dependency injection

Constructor injection, wired with `Depends` (ADR-008). Repositories take the request-scoped `Session`; services take their repository and other features' services; routers take the service via an alias from the feature's `deps.py` (e.g. `SensorServiceDep`). `get_session` uses the cached engine built from `get_settings()`, and FastAPI caches it per request, so every layer shares one session and transaction:

```
get_session ──> SensorRepository ──> SensorService ──┬──> sensors router
            ──> ReadingRepository ───────────────────┼──> ReadingService ──> readings router
            ──> StatisticsRepository ────────────────┴──> StatisticsService ──┬──> statistics router (v1)
                                                                             └──> ExperimentalNlpStatisticsService ──> statistics router (experimental)
```

Integration tests replace `get_session` via `app.dependency_overrides` with a temporary SQLite file; service unit tests pass `create_autospec` mocks to the service's constructor (ADR-007, ADR-008). There is no `lifespan` yet, because nothing needs startup or shutdown work.
