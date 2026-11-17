# 5. Building blocks

See [ADR-002](09-architecture-decisions.md). Layout is planned; create folders only when needed.

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
    db.py        # engine, session factory, PRAGMAs (WAL, foreign keys)
    deps.py      # shared dependencies (get_session, get_settings)
    errors.py    # domain exceptions + exception handlers
  <feature>/     # one folder per feature
    router.py    # APIRouter, endpoints
    schemas.py   # Pydantic request/response models
    service.py   # business logic
    repository.py  # data access (optional at first)
tests/           # mirrors the package; uses dependency overrides
```

## Dependency injection

FastAPI `Depends` wires the chain `get_settings` / `get_session` → service → endpoint. Tests replace providers via `app.dependency_overrides` with a temporary SQLite file.
