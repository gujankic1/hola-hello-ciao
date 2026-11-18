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
- **Dependency injection via FastAPI `Depends`** (no extra DI framework) for the DB session and settings. Services are plain module functions that take the session; they are not injected.
- **Synchronous endpoints** (`def`, not `async def`) with the synchronous SQLite driver.
- Every feature has a `repository`; services call it and never use the `Session` API directly (they only pass the session through).
- **Error handling:** repositories translate database errors into a `StorageError` with an operation-specific message (`core.db.storage_errors`, which also rolls back). A global `SQLAlchemyError` handler remains as a fallback with a generic message.

### Reasons

- Separation keeps logic testable without HTTP and lets persistence change independently.
- Feature folders keep related code together and scale better than one folder per layer.
- `Depends` is built in and enables test overrides (`app.dependency_overrides`) with a temporary SQLite file, no mocking library needed.
- Services have a single dependency (the session), no state and no alternative implementations, and routes are not tested in isolation, so injecting services would add a class and provider per feature for no benefit.
- Blocking SQLite calls inside `async def` would stall the event loop; sync endpoints run in FastAPI's threadpool and are correct and simple.

### Consequences

- Slight boilerplate per feature (several small files).
- Sync-only data access; if async is ever needed, revisit with a new ADR (e.g. async driver).
- Discipline needed to keep routers thin and keep FastAPI types out of services.
- Revisit service injection only if a service needs two or more collaborators besides the session (e.g. a message broker and a cache); a `Depends` provider then keeps routes to one `service` parameter.

## ADR-003: Long-format `readings` table (one row per metric value)

- **Status:** accepted
- **Date:** 2026-11-17

### Context

Sensors report different metrics (temperature, humidity, wind speed, ...) and new ones may appear. Queries aggregate chosen metrics per sensor over a time range.

### Decision

Store one row per metric value: `readings(id, sensor_id, metric, value, recorded_at)`, where `sensor_id` references `sensors(id)` (see ADR-004), with `(sensor_id, metric, recorded_at)` unique. One ingest call with several metrics writes several rows in one transaction. Timestamps are stored as naive UTC.

`recorded_at` is required and identifies a reading, which makes ingest idempotent: values already stored with the same value are skipped (a retry returns 201 again), and a different value for an existing key returns 409 and stores nothing from that call.

### Reasons

- New metrics need no schema change or migration.
- Aggregation is one generic query (`WHERE` sensor/metric/time, `GROUP BY` metric with `MIN/MAX/SUM/AVG`).
- The unique index serves the expected query shape.
- Sensors retry on flaky networks; without a natural key, a retry would be stored twice and skew `sum`, `avg` and `count`. The server's receive time differs between retries, so the sensor's own timestamp is the key.
- 409 instead of overwriting: a changed value for the same instant is more likely a bug than a correction, and should not silently replace good data.

### Consequences

- More rows than a wide table (one per metric per reading); acceptable at PoC scale.
- Sensors must send `recorded_at`; there is no server-time default. Two readings of one metric at the same microsecond cannot both be stored.
- No per-metric typing, units or range checks yet; add a metric registry if needed.
- Metric names were free text originally; superseded by ADR-005 (closed enum).

## ADR-004: REST resource design (sensor-scoped ingest, collection-level statistics)

- **Status:** accepted
- **Date:** 2026-11-17

### Context

The brief needs (1) ingest of new metric values per sensor and (2) aggregate queries across one, several or all sensors, several metrics, a statistic per metric (min/max/sum/avg) and a date range (1 day to 1 month, default last 24 h). We want a resource-oriented REST API that can grow gradually.

### Decision

Resources and endpoints (all under `/api/v1`):

| Endpoint | Purpose | Status |
|---|---|---|
| `POST /sensors` | Register a sensor | done |
| `POST /sensors/{sensor_id}/readings` | Ingest metric values for a sensor; 404 if the sensor does not exist | done |
| `GET /sensors`, `GET /sensors/{sensor_id}` | List (by id, no paging) / fetch sensors; 404 for an unknown id | done |
| `GET /sensors/{sensor_id}/readings` | Raw readings of one sensor (time filter, paging) | optional, later |
| `POST /readings/statistics` | Aggregate query (body: sensors, metrics + statistic, from/to) | done |
| `GET /health` | Liveness | done |

Rules:

- **No implicit sensor creation.** Sensors must be registered first; ingest for an unknown sensor returns 404 (`not_found`).
- **The sensor ID is in the path** for ingest, not in the body, so path and body can never disagree and ID validation happens before the body is read.
- **Statistics live at collection level** (`/readings/statistics`), because a query spans many sensors; a per-sensor path would only cover one case and force a second endpoint.
- **Statistics use POST with a body.** Sensors, per-metric statistics and a range are structured input; a typed body validates cleanly. Shape: `{"sensor_ids": [1, 2] (omitted = all), "metrics": [{"name": "temperature", "stat": "avg"}], "from": ..., "to": ...}`; default window last 24 h; range must be between 1 day and 1 month.
- **Statistics semantics.** `metrics[].name` and `stat` (`min|max|sum|avg`) are enums. Window: neither `from` nor `to` = last 24 h ending now; only `to` = the 24 h before it; only `from` = 422; both = length from 1 day to 31 days inclusive ("one month" = 31 days). Naive datetimes are UTC; the window is `[from, to)`; the response echoes the resolved `from`/`to`. Results are per sensor and metric (`sensor_id, metric, stat, value, count`), never pooled across sensors. `value` is `null` for an explicitly requested sensor with no readings in the window; with all sensors only sensors that have data appear. Unknown `sensor_ids` return 404 naming every missing ID (checked in one query); empty lists, duplicate sensor IDs and duplicate metric/stat pairs return 422.
- **No `GET /sensors/{id}/readings/{reading_id}`.** With ADR-003 one ingest call becomes several rows, so there is no single "reading" entity worth an ID, and the brief has no need to fetch, update or delete one value. If ever needed, storage would split into `readings` (event) and `reading_values` (metric/value).

### Alternatives considered for the statistics query

| | Shape | Why not chosen |
|---|---|---|
| B | `GET /statistics?sensor_id=1&metric=temperature&stat=avg&...` | Pure REST and cacheable, but repeated list params and a different statistic per metric get awkward |
| C | `GET /sensors/{id}/statistics?...` plus a global variant | Two endpoints for one capability; multi-sensor case still needs another |
| D | `POST /statistics/queries` (query as a resource) | Over-engineered for a PoC; "create" semantics for an immediate result confuse readers |

### Consequences

- POST for a read-only query is not cacheable and not self-evidently safe; accepted trade-off (common pattern, e.g. Elasticsearch `_search`).
- A sensors table and `POST /sensors` are needed before ingest is usable.
- One ingest call cannot report for several sensors (no batching across sensors).

## ADR-005: Closed set of metrics (enum)

- **Status:** accepted
- **Date:** 2026-11-17
- **Supersedes:** the free-text metric names consequence of ADR-003

### Context

Ingest accepted any metric name, so typos or arbitrary keys from a misbehaving sensor created junk metrics that statistics queries would then have to cope with.

### Decision

Metric names are a closed `Metric` enum in `readings/metrics.py`: `temperature`, `humidity`, `wind_speed`, `pressure`, `rainfall`. Ingest rejects unknown names with 422 (`validation_error`), and the statistics query uses the same enum. The column stays a plain string, so no migration is needed.

### Reasons

- Bad input is rejected at the boundary and the allowed values appear in the OpenAPI schema.
- Simplest option: no extra table, endpoints or configuration.

### Consequences

- Adding a metric is a code change and a deploy.
- Still no per-metric units or value-range checks.
- Rows written before this ADR keep whatever names they have.

### Alternatives considered

- **Configurable allow-list (env var):** no deploy for new metrics, but validated at runtime and invisible in OpenAPI.
- **Metric registry table:** enables units and ranges but needs a migration and management endpoints; overkill for the PoC.
