# 7. Deployment

> Single container on one host confirmed 2026-11-17. The concrete host/provider is still open.

```
 Client ──HTTPS──> [ Reverse proxy / PaaS edge ] ──> [ Container: Uvicorn + FastAPI ] ──> /data/app.db (SQLite, mounted volume)
```

- One container, one Uvicorn process (a single instance writes to SQLite).
- Persistent volume mounted at `/data`; path set via `DATABASE_PATH`.
- Backups: periodic `sqlite3 .backup` copy of the database file to off-host storage.
- Configuration: environment variables only.
- Scaling: vertical. Horizontal scaling requires revisiting ADR-001.
