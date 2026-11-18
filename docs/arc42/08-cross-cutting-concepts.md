# 8. Cross-cutting concepts

Rules that apply across all features. Code links point to where each rule is enforced.

## Time

- **UTC everywhere.** Incoming datetimes with an offset are converted to UTC; naive datetimes are taken as UTC. One shared type, `UtcDatetime` (`core/types.py`), applies this to ingest and queries alike.
- **Stored as naive UTC.** SQLite has no time-zone type. SQLAlchemy writes a fixed-width `YYYY-MM-DD HH:MM:SS.ffffff` string, so text comparison is chronological and the `recorded_at` index serves range filters.
- **"Now" is the server clock.** It is the default end of the statistics window. Ingest has no default: sensors send `recorded_at`, which identifies a reading (ADR-003).
- **Windows are half-open, `[from, to)`.** Adjacent windows never count a reading twice. The response echoes the resolved `from`/`to`, so clients see which window a default produced.

## Validation

All input is validated at the HTTP boundary by Pydantic schemas; services can assume valid data.

| Input | Rule | Response |
|---|---|---|
| Metric names, statistics | Closed enums (`Metric`, `Stat`; ADR-005) | 422 |
| Metric values | Finite floats (no `NaN`/`Infinity`) | 422 |
| `recorded_at` | Required; ISO 8601 or Unix time, no offset = UTC | 422 |
| Sensor IDs (path and body) | `SensorId`: integer from 1 to 2^63-1, the SQLite rowid range | 422 |
| `sensor_ids` list | 1 to 1000 items, no duplicates | 422 |
| Statistics window | 1 to 31 days inclusive; `from` needs `to` (ADR-004) | 422 |
| Unknown sensor | Checked in the service against the database | 404 |

One ingest call is all-or-nothing: one bad metric rejects the call, and all metrics are written in one transaction.

## Errors

One shape for every error the API produces: `{"error": {"code", "message", "details"?}}` (`core/errors.py`).

| Code | Status | Raised by |
|---|---|---|
| `validation_error` | 422 | Pydantic, via the `RequestValidationError` handler; `details` lists each field |
| `not_found` | 404 | Services (`NotFoundError`) |
| `conflict` | 409 | Ingest service (`ConflictError`): a different value for an existing reading |
| `storage_error` | 500 | Repositories via `storage_errors(...)`, with an operation-specific message; a generic `SQLAlchemyError` handler is the fallback |
| `internal_error` | 500 | Catch-all `Exception` handler; generic message, nothing internal leaked |

Routing errors (unknown path or method) keep FastAPI's default `{"detail": ...}`; they are client mistakes during development, not runtime failures.

## Persistence and transactions

- One SQLAlchemy `Session` per request (`core/deps.py`), injected with `Depends`; services pass it to repositories.
- Repositories own the transaction: they commit on success, and `storage_errors` rolls back on failure.
- Every connection enables `PRAGMA foreign_keys=ON` and `journal_mode=WAL` (`core/db.py`).
- Endpoints are sync (`def`) and run in FastAPI's threadpool; one Uvicorn worker is the single SQLite writer (ADR-001, ADR-002).
- The schema is owned by Alembic migrations; a test fails if models and migrations drift (`tests/unit/core/test_migrations.py`).

## Configuration

One `Settings` object (`core/config.py`) reads environment variables, with `.env` for local development. The only setting today is `DATABASE_PATH`.
