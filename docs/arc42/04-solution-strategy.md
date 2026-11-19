# 4. Solution strategy

| Goal | Approach |
|---|---|
| Simplicity | Monolith: one FastAPI app, one SQLite file, one process |
| Maintainability | Type hints + Pydantic models at the boundary; thin routers, logic in testable functions; `ruff` + `pytest` |
| Low operating cost | No external services; embedded database; env-based config |
| Evolvability | Decisions recorded as ADRs; schema changes via Alembic migrations, checked against the models in tests |

Layering: per feature, `router` → `service` → `repository` ([ADR-002](09-architecture-decisions.md), [ADR-008](09-architecture-decisions.md), [chapter 5](05-building-blocks.md)).
