# 2. Constraints

| Constraint | Type | Notes |
|---|---|---|
| Python 3.12+ with FastAPI | Technical | See ADR-001 |
| SQLite as the only datastore | Technical | See ADR-001; implies a single writer instance |
| Single host with persistent disk | Infrastructure | See chapter 7 |
| Config via environment variables | Organisational | No secrets in the repository |
| Docs maintained alongside code | Organisational | See [AGENTS.md](../../AGENTS.md) |
