# TODO

## Planned

- [ ] **Web UI + FastAPI API** — Add web dashboard and REST API for monitoring, P&L, settings, and bot control. Plan: [`plans/web-ui-fastapi.md`](plans/web-ui-fastapi.md)
  - Phase 1: FastAPI backend (auth, routers, bot status coordination)
  - Phase 2: Next.js SPA frontend (dashboard, positions, opportunities, history, settings)
  - Phase 3: Integration (WAL mode, static build serving, Procfile deployment)
  - **Future: migrate SQLite → PostgreSQL when implementing multi-user/multi-tenant**
