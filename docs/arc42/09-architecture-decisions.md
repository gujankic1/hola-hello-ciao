# 9. Architecture decisions

Append-only log. To change a decision, add a new ADR that supersedes the old one.

## ADR-001: FastAPI with SQLite

- **Status:** accepted
- **Date:** 2026-11-17

### Context

We need a small web API that is quick to build, easy to operate and easy to maintain, with no requirement yet for multi-node scale or heavy concurrent writes.

### Decision

Use **Python + FastAPI** for the API and **SQLite** as the datastore.

### Reasons

- **FastAPI:** type-hint-driven validation (Pydantic) and automatic OpenAPI docs give a lot of correctness for little code; async-capable; large ecosystem and well-understood by AI tooling.
- **Team experience:** the owner already has hands-on experience with FastAPI, which lowers risk and speeds up delivery.
- **Relational over non-relational:** we expect structured, interrelated data where integrity matters (foreign keys, constraints, transactions) and queries we can't fully predict yet; SQL handles ad-hoc queries, joins and schema evolution (migrations) well. A document/key-value store would trade that for schema flexibility and horizontal scale, neither of which we need, and would push integrity checks into application code.
- **SQLite as the relational engine:** zero-ops (no server to run, secure or pay for), a single file that is trivial to back up and copy, fast for read-heavy and moderate-write workloads, and full SQL.
- **Together:** one process and one file keep deployment, local development and testing trivial, matching our top quality goal of simplicity.

### Consequences

- Single writer: run one app instance on durable local disk; no horizontal scaling of writes.
- Need WAL mode and foreign keys enabled on every connection.
- If we outgrow it (multi-instance, high write concurrency), migrate to PostgreSQL. Using SQLAlchemy and Alembic keeps that path cheap.

### Alternatives considered

- **PostgreSQL:** more capable but adds a server to operate; unjustified at this stage.
- **Document / key-value stores (e.g. MongoDB, Redis):** flexible schemas and easy horizontal scaling, but weaker integrity guarantees and joins; our data is expected to be relational and scale is not a driver.
- **Flask / Django:** Flask lacks built-in validation and typing; Django is heavier than needed for a small API.

## ADR-002: Layered, feature-based structure with FastAPI dependency injection

- **Status:** accepted
- **Date:** 2026-11-17

### Context

We need a code structure that keeps HTTP concerns, business logic and persistence separate, stays small, and is easy to test.

### Decision

- **Layers, one-way dependencies:** `api` (router + schemas) → `service` (business logic) → `repository` (DB access). Services contain no FastAPI imports.
- **Organised by feature**, not by layer: each feature folder holds its own `router.py`, `schemas.py`, `service.py`, `repository.py`.
- **Dependency injection via FastAPI `Depends`** (no extra DI framework) for DB session, settings and services.
- **Synchronous endpoints** (`def`, not `async def`) with the synchronous SQLite driver.
- Introduce a `repository` only when queries need sharing; until then services may use the session directly.

### Reasons

- Separation keeps logic testable without HTTP and lets persistence change independently.
- Feature folders keep related code together and scale better than one folder per layer.
- `Depends` is built in and enables test overrides (`app.dependency_overrides`) with a temporary SQLite file, no mocking library needed.
- Blocking SQLite calls inside `async def` would stall the event loop; sync endpoints run in FastAPI's threadpool and are correct and simple.

### Consequences

- Slight boilerplate per feature (several small files).
- Sync-only data access; if async is ever needed, revisit with a new ADR (e.g. async driver).
- Discipline needed to keep routers thin and keep FastAPI types out of services.
