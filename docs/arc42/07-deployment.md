# 7. Deployment

```
 Client ──HTTPS──> [ Reverse proxy / PaaS edge ] ──> [ Uvicorn + FastAPI ] ──> /data/app.db (SQLite, durable local disk)
```

- One Uvicorn process (a single instance writes to SQLite).
- Database on durable local disk (e.g. `/data`); path set via `DATABASE_PATH`.
- Backups: not set up; out of scope for the PoC (chapter 11, risks).
- Configuration: environment variables only.
- Scaling: vertical. Horizontal scaling requires revisiting ADR-001.
