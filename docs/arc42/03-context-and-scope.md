# 3. Context and scope

```
 Sensors / clients ──HTTP/JSON──> [ Weather Sensor Metrics API ] ──> SQLite file
 (report readings, query stats)
```

| Partner | Interaction |
|---|---|
| Operators / provisioning | `POST /api/v1/sensors` to register a sensor |
| Sensors (or any HTTP client) | `POST /api/v1/sensors/{id}/readings` to report metric values |
| API consumers | `POST /api/v1/readings/statistics` aggregate query |
| SQLite database | Only datastore; local file, owned by the API |

Endpoint design: [ADR-004](09-architecture-decisions.md).

**Out of scope for now:** authentication, UI, streaming/batch ingestion, sensor listing/lookup endpoints.
