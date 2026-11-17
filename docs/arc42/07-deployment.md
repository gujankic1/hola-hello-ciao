# 7. Deployment

> Single process on one host confirmed 2026-11-17. The concrete host/provider is still open.

```
 Client ──HTTPS──> [ Reverse proxy / PaaS edge ] ──> [ Uvicorn + FastAPI ] ──> /data/app.db (SQLite, durable local disk)
```

- One Uvicorn process (a single instance writes to SQLite).
- Database on durable local disk (e.g. `/data`); path set via `DATABASE_PATH`.
- Backups: periodic `sqlite3 .backup` copy of the database file to off-host storage.
- Configuration: environment variables only.
- Scaling: vertical. Horizontal scaling requires revisiting ADR-001.
