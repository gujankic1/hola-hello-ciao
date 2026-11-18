# 5. Building blocks

See [ADR-002](09-architecture-decisions.md). Features: `sensors` (registry), `readings` (ingest; owns the `Metric` enum) and `statistics` (aggregate query; reads the `readings` table via its own repository). Both depend on `sensors.service` for the 404 check (`get_sensor`, `ensure_sensors_exist`). Every feature has a `repository`; services never call the `Session` API directly. Create folders only when needed.

## Level 1: layers

```
 HTTP ──> api (router, schemas) ──> service (logic) ──> repository (SQL/ORM) ──> SQLite
```

| Layer | Responsibility | Must not |
|---|---|---|
| api | Parse/validate requests, status codes, auth, response models | Contain business rules or SQL |
| service | Business rules, orchestration | Import FastAPI or know about HTTP |
| repository | Queries and persistence | Contain business rules |

Dependencies point one way only (api → service → repository).

## Level 2: package layout

```
src/hola_hello_ciao/
  main.py        # app factory, error handlers, router registration, /health
  core/
    config.py    # Settings (pydantic-settings), cached get_settings()
    db.py        # engine, PRAGMAs (WAL, foreign keys), storage_errors helper
    deps.py      # shared dependencies (cached engine, get_session)
    errors.py    # domain exceptions + exception handlers
  <feature>/     # one folder per feature
    router.py    # APIRouter, endpoints
    schemas.py   # Pydantic request/response models
    service.py   # business logic
    repository.py  # data access; translates DB errors to StorageError
tests/
  conftest.py    # shared fixtures, dependency overrides with a temp SQLite file
  unit/<feature>/         # mirrors the package; services, repositories and schemas without HTTP
  integration/            # one file per route (test_post_sensors_readings.py), via TestClient
```

## Dependency injection

Endpoints receive a request-scoped `Session` via `Depends(get_session)`; `get_session` uses the cached engine built from `get_settings()`. Services are plain module functions that take the session, not injected objects (ADR-002). Tests replace `get_session` via `app.dependency_overrides` with a temporary SQLite file. There is no `lifespan` yet, because nothing needs startup or shutdown work.
