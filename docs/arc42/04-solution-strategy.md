# 4. Solution strategy

| Goal | Approach |
|---|---|
| Simplicity | Monolith: one FastAPI app, one SQLite file, one process |
| Maintainability | Type hints + Pydantic models at the boundary; thin routers, logic in testable functions; `ruff` + `pytest` |
| Low operating cost | No external services; embedded database; env-based config |
| Evolvability | Decisions recorded as ADRs; migrations via Alembic once a schema exists |

Layering (planned): `api` (routers, schemas) → `core` (logic) → `db` (access, migrations).
