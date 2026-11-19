# 8. Cross-cutting concepts

Rules that apply across all features. Code links point to where each rule is enforced.

## Time

- **UTC everywhere.** Incoming datetimes with an offset are converted to UTC; naive datetimes are taken as UTC. One shared type, `UtcDatetime` (`core/types.py`), applies this to ingest and queries alike.
- **Stored as naive UTC.** SQLite has no time-zone type. SQLAlchemy writes a fixed-width `YYYY-MM-DD HH:MM:SS.ffffff` string, so text comparison is chronological and the `recorded_at` index serves range filters.
- **"Now" is the server clock.** It is the default end of the statistics window, and relative times in natural-language queries ("last week") count back from it (ADR-009). Ingest has no default: sensors send `recorded_at`, which identifies a reading (ADR-003).
- **Windows are half-open, `[from, to)`.** Adjacent windows never count a reading twice. The response echoes the resolved `from`/`to`, so clients see which window a default produced.

## Validation

All input is validated at the HTTP boundary by Pydantic schemas; services can assume valid data. One exception: the experimental natural-language query is only checked for length there, and the service validates the `StatisticsQuery` the parser builds from it (ADR-009).

| Input | Rule | Response |
|---|---|---|
| Unknown fields | Rejected on every input model (`extra="forbid"`), so a typo such as `sensor_id` for `sensor_ids` cannot silently widen a query to all sensors | 422 |
| Metric names, statistics | Closed enums (`Metric`, `Stat`; ADR-005) | 422 |
| Metric values | Finite floats (no `NaN`/`Infinity`) | 422 |
| `recorded_at` | Required; ISO 8601 or Unix time, no offset = UTC | 422 |
| Sensor IDs (path and body) | `SensorId`: integer from 1 to 2^63-1, the SQLite rowid range | 422 |
| `sensor_ids` list | 1 to 1000 items, no duplicates | 422 |
| Statistics window | 1 to 31 days inclusive; `from` needs `to` and must be before it (ADR-004) | 422 |
| Natural-language query | 1 to 500 characters; must name a metric, with a statistic before it, and read as a valid statistics query (ADR-009) | 422 |
| Unknown sensor | Checked in the service against the database | 404 |

One ingest call is all-or-nothing: one bad metric rejects the call, and all metrics are written in one transaction.

## Errors

One shape for every error the API produces: `{"error": {"code", "message", "details"?}}`, defined by the `ErrorResponse` model in `core/errors.py`, which also builds every error body. Exception handlers are invisible to OpenAPI, so each route declares the error statuses it can return with `responses=error_responses(...)`, and each router declares 500; declaring 422 also replaces FastAPI's default `HTTPValidationError`, a shape this API never returns.

| Code | Status | Raised by |
|---|---|---|
| `validation_error` | 422 | Pydantic, via the `RequestValidationError` handler; `details` lists each field |
| `invalid_query` | 422 | Natural-language parser (`InvalidQueryError`): text that cannot be read as a query, with a message saying why |
| `not_found` | 404 | Services (`NotFoundError`) |
| `conflict` | 409 | Ingest service (`ConflictError`): a different value for an existing reading |
| `storage_error` | 500 | Repositories via `storage_errors(...)`, with an operation-specific message; a generic `SQLAlchemyError` handler is the fallback |
| `internal_error` | 500 | Catch-all `Exception` handler; generic message, nothing internal leaked |

Routing errors (unknown path or method) keep FastAPI's default `{"detail": ...}`; they are client mistakes during development, not runtime failures.

## Persistence and transactions

- One SQLAlchemy `Session` per request (`core/deps.py`), injected with `Depends` into the repositories; services only see repositories (ADR-008).
- Repositories own the transaction: they commit on success, and `storage_errors` rolls back on failure.
- Ingest's idempotency check (ADR-003) is one atomic step in the repository: `INSERT … ON CONFLICT DO NOTHING`, then the stored values are read back in the same transaction, which is rolled back if any of them differs. The INSERT holds SQLite's write lock until commit, so concurrent requests cannot interleave. Checking *before* inserting was not enough: concurrent calls with different values all saw no row, the later inserts were skipped, and their clients still got 201. The comparison therefore lives in the repository, inside the transaction; the service turns the conflicting metrics into a 409.
- Every connection sets two `PRAGMA`s (`core/db.py`):
  - `foreign_keys=ON` (off by default in SQLite, per connection): the database rejects a reading for an unknown sensor, backing up the service's 404 check.
  - `journal_mode=WAL`: readers see a snapshot and never block on the writer, or the other way round; there is still one writer at a time. The `-wal`/`-shm` files are part of the database, so a backup must use `sqlite3 .backup`, not a file copy.
- Endpoints are sync (`def`) and run in parallel in FastAPI's pool of 40 threads; SQLite releases the GIL while it works. One Uvicorn worker is the single writer: a second write waits up to 5 s rather than failing, and an ingest write takes well under 1 ms (ADR-001, ADR-002). Limits: chapter 11, R2.
- The schema is owned by Alembic migrations; a test fails if models and migrations drift (`tests/unit/core/test_migrations.py`).

## Configuration

One `Settings` object (`core/config.py`) reads environment variables, with `.env` for local development. The only setting today is `DATABASE_PATH`.
