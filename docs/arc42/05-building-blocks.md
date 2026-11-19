# 5. Building blocks

See [ADR-002](09-architecture-decisions.md). Features: `sensors` (registry), `readings` (ingest; owns the `Metric` enum) and `statistics` (aggregate query; its own repository reads the `readings` table and uses `sensors` to filter by sensor). Both depend on `sensors.service` for the 404 check (`get_sensor`, `ensure_sensors_exist`). Every feature has a `repository`; services never call the `Session` API directly. Create folders only when needed.

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

Endpoints receive a request-scoped `Session` via `Depends(get_session)`; `get_session` uses the cached engine built from `get_settings()`. Services are plain module functions that take the session, not injected objects (ADR-002). Tests replace `get_session` via `app.dependency_overrides` with a temporary SQLite file. There is no `lifespan` yet, because nothing needs startup or shutdown work.
