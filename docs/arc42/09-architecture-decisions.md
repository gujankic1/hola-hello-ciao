# 9. Architecture decisions

Each ADR records a significant decision and why it was made. When the reasoning changes, the ADR is updated in place.

## ADR-001: FastAPI with SQLite

*Accepted, 2026-11-17*

**Context.** A small API that is quick to build, easy to run and easy to maintain, with no need for multi-node scale or heavy concurrent writes.

**Decision.** Python + FastAPI for the API, SQLite as the datastore.

**Reasons**

- FastAPI derives validation and OpenAPI docs from type hints, which gives a lot of correctness for little code; the owner already knows it well.
- The data is relational and integrity matters (foreign keys, unique keys, transactions), and aggregate queries are natural in SQL.
- SQLite has zero operations: no server to run or secure, one file, full SQL, fast for read-heavy, moderate-write workloads.

**Consequences**

- One writer: one app instance on durable local disk, no horizontal scaling (chapter 11, R2).
- If it is outgrown, move to PostgreSQL; SQLAlchemy and Alembic keep that path cheap.

**Alternatives**

- **PostgreSQL:** more capable, but a server to operate for no current benefit.
- **Document or key-value stores:** schema flexibility and horizontal scale we don't need, at the cost of integrity and joins.
- **Flask / Django:** Flask lacks built-in validation; Django is heavier than a small API needs.

## ADR-002: Layered, feature-based structure with sync endpoints

*Accepted, 2026-11-17*

**Context.** HTTP, business logic and persistence should stay separate, small and testable.

**Decision**

- Layers with one-way dependencies: `router` → `service` → `repository`. Services never import FastAPI; only repositories touch the ORM.
- Business code lives under `features/`, one folder per feature (`sensors`, `readings`, `statistics`), each with its own router, schemas, service and repository. Technical infrastructure lives in `core/`.
- `features/shared/` holds business vocabulary used by two or more features (today: `Metric`). It has no tables, endpoints, services or repositories, and imports no feature. Models stay with the feature that owns the table.
- FastAPI `Depends` injects the DB session. Services are plain functions that take the session; they are not injected.
- Endpoints are synchronous (`def`) with the synchronous SQLite driver.

**Reasons**

- Logic is testable without HTTP, and persistence can change independently.
- Feature folders keep related code together; `features/` vs `core/` shows what is business and what is infrastructure.
- A shared business term gets a neutral home instead of living in one feature that others import it from.
- `Depends` is built in and lets integration tests swap in a temporary database. Service tests patch the module-level repository instead (ADR-007). Injecting services would add a class and a provider per feature for no gain: they have one dependency, no state and one implementation.
- Blocking SQLite calls inside `async def` would stall the event loop. Async would not help with SQLite anyway: there is still one writer, and async SQLite drivers use a thread.

**Consequences**

- A few small files per feature.
- Revisit service injection if a service needs two or more collaborators besides the session (e.g. a message broker and a cache), and async if the database moves to PostgreSQL.

## ADR-003: One row per metric value, idempotent by sensor, metric and time

*Accepted, 2026-11-17*

**Context.** Sensors report several metrics at once, and queries aggregate chosen metrics per sensor over a time range. Sensors on flaky networks retry.

**Decision**

- Store one row per metric value: `readings(sensor_id, metric, value, recorded_at)`, with `(sensor_id, metric, recorded_at)` unique. One ingest call writes its rows in one transaction.
- `recorded_at` is required and identifies a reading. Re-sending a stored value succeeds without a duplicate; a different value for a stored reading returns 409 and stores nothing from that call.

**Reasons**

- Adding a metric needs no schema change, and aggregation is one generic `GROUP BY` query. The unique index also serves that query.
- Without a natural key, a retry would be stored twice and skew `sum`, `avg` and `count`. The server's receive time differs between retries, so the sensor's own timestamp is the key.
- 409 rather than overwriting: a changed value for the same instant is more likely a bug than a correction.

**Consequences**

- More rows than a wide table; fine at this scale.
- Sensors must send `recorded_at`.

## ADR-004: REST resource design

*Accepted, 2026-11-17*

**Context.** The brief needs ingest per sensor, and aggregate queries over one, several or all sensors, several metrics, a statistic per metric and a 1-day to 1-month window (default: last 24 hours).

**Decision**

| Endpoint (under `/api/v1`) | Purpose |
|---|---|
| `POST /sensors`, `GET /sensors`, `GET /sensors/{id}` | Register, list and fetch sensors |
| `POST /sensors/{id}/readings` | Ingest metric values for one sensor |
| `POST /readings/aggregate` | Aggregate query |

- **Sensors are registered first;** ingest for an unknown sensor returns 404. The sensor ID is in the path, so path and body cannot disagree.
- **The aggregate query is collection-level,** because one query spans many sensors. It uses `POST` with a typed body, because sensors, per-metric statistics and a window are structured input. The path names the operation: `POST` on a noun such as `/readings/statistics` reads as "create statistics".
- **Results are per sensor and metric,** never pooled across sensors. The window is `[from, to)`; "one month" means 31 days. A requested sensor without readings gets `null`; when querying all sensors, only sensors with data appear.
- **No per-reading endpoint:** one ingest call becomes several rows (ADR-003), so there is no single reading entity worth an ID.

**Alternatives for the query**

- **`GET /statistics?sensor_id=...&metric=...&stat=...`:** cacheable, but repeated list parameters and a different statistic per metric get awkward.
- **`GET /sensors/{id}/statistics` plus a global variant:** two endpoints for one capability.
- **`POST /statistics/queries` (query as a resource):** over-engineered for an immediate result.

**Consequences**

- A read-only `POST` is not cacheable; an accepted, common trade-off (e.g. Elasticsearch `_search`).
- One ingest call reports for one sensor only.

## ADR-005: Closed set of metrics

*Accepted, 2026-11-17*

**Context.** Free-text metric names let typos and junk keys from a faulty sensor become metrics that queries then have to cope with.

**Decision.** Metric names are a closed enum (`temperature`, `humidity`, `wind_speed`, `pressure`, `rainfall`), shared by ingest and the aggregate query. Unknown names return 422. The column stays a plain string.

**Reasons.** Bad input is rejected at the boundary, the allowed values appear in the API docs, and there is no extra table or configuration.

**Consequences.** Adding a metric is a code change and a deploy. There are no per-metric units or value ranges (chapter 11, R4).

**Alternatives**

- **Allow-list in configuration:** no deploy for new metrics, but invisible in the API docs.
- **Metric registry table:** allows units and ranges, but needs management endpoints; too much for a PoC.

## ADR-006: Dev tooling in `scripts/`, outside the package

*Accepted, 2026-11-18*

**Context.** Trying the API meant starting from an empty database and hand-writing ingest calls. We want one-line start commands with sample data, without seeding code in the application.

**Decision.** A root-level `scripts/` folder holds `dev.py` (`serve` and `seed` commands) and `seed.py` (datasets `small`, `medium`, `large`), run with `uv run scripts/dev.py`. Seeding bulk-inserts through the ORM models, not through services or the API.

**Reasons**

- Nothing under `src/` knows about seeding, and nothing extra ships.
- No new dependency: `argparse`, Alembic's command API and `uvicorn.run`.
- Bulk insert loads 2.16M rows in about 15 s; one API call per reading would take minutes.

**Consequences.** Seed data bypasses ingest validation; it is generated in the repo and trusted. Tests in `tests/scripts/` catch it if a model change breaks seeding.

**Alternatives**

- **`[project.scripts]` entry point:** a short command name, but the code would have to live in the application package.
- **A task runner (make, just, poethepoet):** an extra tool, and seeding logic still needs a home.
- **Seeding through the API:** exercises validation, but is far too slow for the large dataset.

## ADR-007: Service unit tests mock their collaborators

*Accepted, 2026-11-19*

**Context.** Service tests ran through the real repositories on a temporary SQLite file, so a query bug also failed them.

**Decision.** Service tests replace the feature's `repository` module and other features' service functions with `create_autospec` mocks via `monkeypatch`, and pass a stand-in `fake_session`. Repository and integration tests keep the real database.

**Reasons**

- A service test fails only for the service's own logic, and any repository result is one line to set up.
- Autospec fails a test when a mocked function is called with the wrong arguments or no longer exists.
- The database is the repository's boundary; mocking the `Session` would not test the SQL.
- No new dependency.

**Consequences.** Only integration tests check that the layers fit together. Changing a repository signature means updating service tests. Routers stay thin and get no unit tests.

**Alternatives**

- **Real database at every level:** catches wiring bugs, but the tests are not unit tests.
- **`pytest-mock`:** an extra dependency for what `monkeypatch` and `create_autospec` already do.
