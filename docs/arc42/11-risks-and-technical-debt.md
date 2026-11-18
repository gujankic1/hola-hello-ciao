# 11. Risks and technical debt

Known gaps, accepted for a proof of concept, with what would trigger a fix and what the fix is. Ordered by how likely each is to matter first.

## Risks

| # | Risk | Impact | Trigger to act | Mitigation path |
|---|---|---|---|---|
| R1 | **Query cost grows with stored data.** Statistics are computed on the fly from raw rows. Queries for named sensors use the index well; a query for all sensors reads the whole index and filters by metric and time. | Measured below: all-sensor queries take 1–2 s at 13M rows, named sensors stay in milliseconds. | Query latency above target, or retention beyond a few months at fleet scale. | (1) An index led by `(metric, recorded_at)` for all-sensor queries. (2) Pre-aggregated hourly or daily rollups maintained on ingest. (3) A time-series store (PostgreSQL + TimescaleDB). |
| R2 | **One writer, one host.** SQLite allows one writer, and the database lives on one machine's disk. | No horizontal scaling and no high availability; a host failure means downtime until restore. Write throughput is bounded by one process. | Availability requirements, or more ingest than one process can handle. | Migrate to PostgreSQL (ADR-001); SQLAlchemy and Alembic keep that cheap. |
| R3 | **No authentication or authorisation.** Anyone who can reach the API can register sensors, write readings and read statistics. | Data pollution or disclosure if exposed. | Any deployment beyond a trusted network. | API keys per sensor for ingest and per client for queries, checked in a FastAPI dependency; HTTPS at the edge. |
| R4 | **Implausible values are accepted.** Values only need to be finite, and `recorded_at` may be far in the future. Two readings near `1e308` overflow `sum` to infinity, which is returned as `null` with a non-zero `count`. | Wrong or confusing statistics from one faulty sensor. | First faulty sensor in the field. | Per-metric value ranges and units (a metric registry, ADR-005 alternatives); reject `recorded_at` beyond a small clock-skew allowance. |
| R5 | **Unbounded growth.** Readings are never deleted. | Disk use and query cost (R1) grow forever. | Disk usage, or queries slowing down. | Retention policy: delete or archive raw readings older than the longest query window (31 days) once rollups exist. |
| R6 | **Backups are manual.** Chapter 7 describes `sqlite3 .backup`, but nothing runs it. | Data loss on disk failure. | Before holding any data that matters. | Scheduled `.backup` (or Litestream) to off-host storage, with a tested restore. |

### R1 measurement

Synthetic load on an Apple M3 Max laptop with a warm page cache: 100 sensors, 5 metrics, one reading every 5 minutes for 90 days, which is 12.96M rows and a 1.1 GB database file. The query asks for 2 metrics and calls the real `statistics.repository.aggregate`. This is a rough indication from one run, not a benchmark suite.

| Query | Current index | Plus `(metric, recorded_at)` index |
|---|---|---|
| 1 sensor, 31 days | 7 ms | 8 ms |
| 10 sensors, 31 days | 72 ms | 72 ms |
| All sensors, 1 day | 1,130 ms | 25 ms |
| All sensors, 31 days | 1,810 ms | 720 ms |

The extra index fixes short all-sensor windows but grows the file by about 44%. Long all-sensor windows still read every matching row, which is what rollups (mitigation 2) remove.

## Technical debt

| Item | Why it is acceptable now | Fix |
|---|---|---|
| No logging setup, no request IDs or metrics | Uvicorn's access log and tracebacks are enough to debug a PoC. | Structured JSON logging with a request ID middleware; metrics (request rate, latency, ingest volume). |
| `/health` does not check the database | Liveness only; a broken database surfaces as 500s on real calls. | A readiness check that runs `SELECT 1`. |
| No CI pipeline | Checks are run locally before each commit. | A GitHub Actions workflow running the four commands from the README. |
| No container image or `.python-version` | `uv` pins dependencies via `uv.lock`; Python 3.12+ is declared in `pyproject.toml`. | A Dockerfile and a pinned Python version once a host is chosen (chapter 7). |
| `GET /sensors` has no pagination | The PoC expects few sensors. | Cursor pagination on `id`. |
| Adding a metric needs a deploy | Deliberate (ADR-005): the enum shows in OpenAPI and rejects typos. | A metric registry table, if metrics change often. |
| Migrations are run by hand | One explicit step (`alembic upgrade head`) keeps startup simple and predictable. | Run migrations as a release step in the deploy pipeline. |
