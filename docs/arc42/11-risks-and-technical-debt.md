# 11. Risks and technical debt

Known gaps, accepted for a proof of concept, with what would trigger a fix and what the fix is. Ordered by how likely each is to matter first.

## Risks

| # | Risk | Impact | Trigger to act | Mitigation path |
|---|---|---|---|---|
| R1 | **Query cost grows with stored data.** Statistics are computed on the fly from raw rows. Every query seeks the index once per sensor (also when querying all sensors), so cost grows with sensors × window, not with all stored data. | Measured below: at 13M rows, all-sensor queries take 25 ms for 1 day and about 0.8 s for 31 days; named sensors stay in milliseconds. | All-sensor long-window latency above target, or retention beyond a few months at fleet scale. | See the options below. In order: (1) `WITHOUT ROWID` readings table. (2) Pre-aggregated hourly or daily rollups maintained on ingest. (3) A time-series store (PostgreSQL + TimescaleDB). |
| R2 | **One writer, one host.** SQLite allows one writer, and the database lives on one machine's disk. | No horizontal scaling and no high availability; a host failure means downtime until restore. Write throughput is bounded by one process. | Availability requirements, or more ingest than one process can handle. | Migrate to PostgreSQL (ADR-001); SQLAlchemy and Alembic keep that cheap. |
| R3 | **No authentication or authorisation.** Anyone who can reach the API can register sensors, write readings and read statistics. | Data pollution or disclosure if exposed. | Any deployment beyond a trusted network. | API keys per sensor for ingest and per client for queries, checked in a FastAPI dependency; HTTPS at the edge. |
| R4 | **Implausible values are accepted.** Values only need to be finite, and `recorded_at` may be far in the future. Two readings near `1e308` overflow `sum` to infinity, which is returned as `null` with a non-zero `count`. | Wrong or confusing statistics from one faulty sensor. | First faulty sensor in the field. | Per-metric value ranges and units (a metric registry, ADR-005 alternatives); reject `recorded_at` beyond a small clock-skew allowance. |
| R5 | **Unbounded growth.** Readings are never deleted. | Disk use and query cost (R1) grow forever. | Disk usage, or queries slowing down. | Retention policy: delete or archive raw readings older than the longest query window (31 days) once rollups exist. |
| R6 | **Backups are manual.** Chapter 7 describes `sqlite3 .backup`, but nothing runs it. | Data loss on disk failure. | Before holding any data that matters. | Scheduled `.backup` (or Litestream) to off-host storage, with a tested restore. |
| R7 | **Concurrency limits of one process.** Requests run in 40 threads but share 15 database connections (SQLAlchemy's default pool), and Python work runs one thread at a time (ADR-002). | Throughput is capped by one process. Many overlapping slow queries (R1) can hold every connection, so other requests, ingest included, wait and fail after 30 s. | Sustained high request rates, or slow queries that overlap. | (1) Batch ingest endpoint: many readings per request and transaction. (2) Rollups (R1), so no query holds a connection for long. (3) Pool size matched to the thread pool (`pool_size=40, max_overflow=0`): requests queue instead of failing, no extra capacity. (4) PostgreSQL with more than one process. |

### R1 measurement

Synthetic load on an Apple M3 Max laptop with a warm page cache: 100 sensors, 5 metrics, one reading every 5 minutes for 90 days, which is 12.96M rows and a 1.3 GB database file. The query asks for 2 metrics and calls the real `statistics.repository.aggregate`; best of 3 runs. This is a rough indication from one run, not a benchmark suite.

| Query | Full index scan (all sensors unconstrained) | Seek per sensor (current) | Rejected: extra `(metric, recorded_at)` index |
|---|---|---|---|
| 1 sensor, 31 days | 8 ms | 8 ms | 8 ms |
| 10 sensors, 31 days | 78 ms | 78 ms | 72 ms |
| All sensors, 1 day | 1,158 ms | 25 ms | 25 ms |
| All sensors, 31 days | 1,920 ms | 795 ms | 720 ms |

The extra-index column is from an earlier run on the same data shape. Long all-sensor windows still read every matching row, which is what rollups (mitigation 2) remove. With the `large` seed dataset (2.16M rows), the 1-day all-sensor query takes 5 ms and the 31-day one 117 ms.

The extra index was rejected: seeking per sensor (`sensor_id IN (SELECT id FROM sensors)`) gives about the same result without growing the file by 44%.

### R1 options, not built

| Option | Gain | Cost / trade-off | Trigger |
|---|---|---|---|
| `readings` as `WITHOUT ROWID`, primary key `(sensor_id, metric, recorded_at)` | Measured on 2.16M rows: file 222 → 104 MB, queries about 2x faster. | Table-rebuild migration. The unused surrogate `id` goes; the natural key (ADR-003) identifies a reading, and an id can be added back by another rebuild. Secondary indexes then carry the 3-column key. | Disk size, or index-bound latency on named sensors. |
| Hourly or daily rollups maintained on ingest | Long windows read a fraction of the rows (1/12 for 5-minute data rolled up hourly). | A second write per ingest, keeping rollups consistent with idempotent re-ingest, an extra table. | All-sensor 31-day queries above target latency. |
| Retention of raw readings (R5) | Bounds table size, and with it query and backup cost. | Raw data older than the longest window (31 days) is lost or archived; needs rollups first. | Disk growth. |
| `PRAGMA optimize` on a schedule or at connection close | Better plans for new query shapes; `ANALYZE` alone already enables skip-scan for this query. | Plans depend on fresh statistics. | More query shapes than the statistics query. |
| PostgreSQL + TimescaleDB (supersedes ADR-001) | Hypertables, continuous aggregates, parallel scans, more than one writer. | A separate server to run. | Beyond one host. |
| `PRAGMA synchronous=NORMAL` (ingest) | Raw commits about 1.8x faster in WAL mode. | An OS crash or power cut can lose the last acknowledged writes (no corruption). Database time per ingest call is already under 0.1 ms, so HTTP dominates. | Ingest becomes write-bound. |

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
