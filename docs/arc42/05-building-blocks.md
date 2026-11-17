# 5. Building blocks

See [ADR-002](09-architecture-decisions.md). Features: `sensors` (registry) and `readings` (ingest; depends on `sensors.service.get_sensor` for the 404 check). Every feature has a `repository`; services never call the `Session` API directly. Create folders only when needed.

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
  main.py        # app factory, lifespan, router registration
  core/
    config.py    # Settings (pydantic-settings), cached get_settings()
    db.py        # engine, PRAGMAs (WAL, foreign keys), storage_errors helper
    deps.py      # shared dependencies (get_session, get_settings)
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

FastAPI `Depends` wires the chain `get_settings` / `get_session` → service → endpoint. Tests replace providers via `app.dependency_overrides` with a temporary SQLite file.
