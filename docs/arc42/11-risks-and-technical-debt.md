# 11. Risks and technical debt

Known gaps, accepted for a proof of concept, with the fix and when it becomes necessary. Ordered by how likely each is to matter first.

## Risks

| # | Risk | Impact | Mitigation, and when |
|---|---|---|---|
| R1 | **Query cost grows with stored data.** Aggregates are computed from raw rows. Each query seeks the index once per sensor, so cost grows with sensors × window. | At 13M rows, an all-sensor query takes 25 ms for 1 day and about 0.8 s for 31 days (measured below). Readings are never deleted, so this only grows. | When long all-sensor queries get too slow: (1) a `WITHOUT ROWID` table keyed by `(sensor_id, metric, recorded_at)` (on 2.16M rows: file 222 → 104 MB, queries about 2x faster); (2) hourly or daily rollups maintained on ingest, then retention of raw readings; (3) PostgreSQL + TimescaleDB. |
| R2 | **One process, one writer, one host.** | No high availability: a host failure means downtime. Throughput is capped by one process; overlapping slow queries can hold all 15 pooled connections, so other requests wait and fail after 30 s. | When availability or load requires it: rollups (R1) so no query holds a connection for long, a pool sized to the 40-thread request pool, then PostgreSQL (ADR-001). |
| R3 | **No authentication.** Anyone who can reach the API can register sensors, write readings and query them. | Data pollution or disclosure. | Before any deployment beyond a trusted network: API keys per sensor and per client, checked in a FastAPI dependency; HTTPS at the edge. |
| R4 | **Implausible values are accepted.** Values only need to be finite, and `recorded_at` may lie far in the future. | One faulty sensor skews statistics. | When the first faulty sensor shows up: per-metric value ranges (ADR-005 alternatives) and a limit on future timestamps. |
| R5 | **No backups.** Out of scope for the PoC. | Data loss on disk failure. | Before holding data that matters: scheduled `sqlite3 .backup` (or Litestream) to off-host storage, with a tested restore. |

### R1 measurement

Synthetic data on an Apple M3 Max laptop, warm page cache, best of 3 runs: 100 sensors, 5 metrics, a reading every 5 minutes for 90 days (12.96M rows, 1.3 GB), querying 2 metrics. A rough indication, not a benchmark.

| Query | Full index scan (before) | Seek per sensor (current) |
|---|---|---|
| 1 sensor, 31 days | 8 ms | 8 ms |
| 10 sensors, 31 days | 78 ms | 78 ms |
| All sensors, 1 day | 1,158 ms | 25 ms |
| All sensors, 31 days | 1,920 ms | 795 ms |

Filtering on `sensor_id IN (SELECT id FROM sensors)` lets SQLite seek the index per sensor. An extra `(metric, recorded_at)` index performed about the same but grew the file by 44%, so it was rejected.

## Technical debt

| Item | Why it is acceptable now | Fix |
|---|---|---|
| No structured logging, request IDs or metrics | Uvicorn's access log and tracebacks are enough for a PoC. | JSON logging with a request ID; request and ingest metrics. |
| `/health` does not check the database | A broken database still shows up as 500s on real calls. | A readiness check that runs `SELECT 1`. |
| No CI pipeline | The checks run locally before each commit. | A GitHub Actions workflow running the test and lint commands. |
| `GET /sensors` is not paginated | A PoC has few sensors. | Cursor pagination on `id`. |
