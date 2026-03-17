# Web UI + FastAPI API for Polymarket Trading Bot

## Context

The trading bot runs as a CLI worker with no web interface. To monitor opportunities, view P&L, adjust settings, and control the bot remotely, we need a web UI. This also enables deployment as a proper web app on Dokku/Coolify instead of a headless worker.

**Decisions made:**
- FastAPI API server (separate process from bot worker)
- React/Next.js SPA in `web/` directory (monorepo)
- Single-user JWT auth for now (multi-tenant later)
- Shared SQLite (WAL mode) for process communication
- Herokuish deployment (Procfile with `web` + `worker`)

> **Note: Database strategy for multi-user**
> When multi-user/multi-tenant support is implemented, migrate from SQLite to **PostgreSQL**.
> SQLite's single-writer limitation makes it unsuitable for concurrent writes from multiple users.
> PostgreSQL provides connection pooling, row-level locking, and horizontal scaling.
> Phase 1 (single-user) uses SQLite; the multi-user phase must include a Postgres migration.

---

## Architecture

```
Next.js SPA (web/)  →  FastAPI API (src/polymarket_trades/api/)  →  SQLite  ←  Bot Worker (scheduler)
     |                         |                                                    |
  static build              Container + use cases                           existing scan/execute loop
  served by FastAPI         (same DI as CLI)                                writes bot_status each cycle
```

Two OS processes:
- **`web`**: FastAPI serves the API + Next.js static build
- **`worker`**: existing bot scheduler (unchanged except status reporting)

---

## Phase 1: API Backend

### 1.1 New dependencies (`pyproject.toml`)

```
"fastapi>=0.115",
"uvicorn[standard]>=0.32",
"python-jose[cryptography]>=3.3",
"bcrypt>=4.0",
"python-multipart>=0.0.12",
```

### 1.2 New SQLite migration

Create `src/polymarket_trades/infrastructure/persistence/migrations/002_api_tables.sql`:

```sql
INSERT OR IGNORE INTO schema_version (version) VALUES (2);

CREATE TABLE IF NOT EXISTS bot_status (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    state TEXT NOT NULL DEFAULT 'STOPPED',
    last_cycle_at TEXT,
    last_scan_opportunities INTEGER DEFAULT 0,
    last_scan_resolved INTEGER DEFAULT 0,
    started_at TEXT,
    pid INTEGER
);
INSERT OR IGNORE INTO bot_status (id) VALUES (1);

CREATE TABLE IF NOT EXISTS runtime_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_opportunities_detected_at ON opportunities(detected_at);
CREATE INDEX IF NOT EXISTS idx_positions_mode_status ON positions(mode, status);
CREATE INDEX IF NOT EXISTS idx_positions_created_at ON positions(created_at);
```

### 1.3 Domain port extensions (minimal changes)

**`src/polymarket_trades/domain/ports/position_tracker.py`** — add:
- `get_positions_paginated(limit, offset, status?, mode?) -> list[Position]`
- `get_position_by_id(id: UUID) -> Position | None`
- `count_positions(status?, mode?) -> int`

**`src/polymarket_trades/domain/ports/opportunity_store.py`** — add:
- `list_recent(limit, offset, strategy_type?) -> list[Opportunity]`

**New `src/polymarket_trades/domain/ports/bot_status.py`**:
- `get_status() -> BotStatus`
- `update_status(BotStatus) -> None`
- `request_action(BotAction) -> None`
- `check_pending_action() -> BotAction | None`

### 1.4 Infrastructure implementations

- `src/polymarket_trades/infrastructure/persistence/sqlite_bot_status.py` — implements `BotStatusPort`
- Extend `sqlite_position_tracker.py` with new paginated/count methods
- Extend `sqlite_opportunity_store.py` with `list_recent`
- Enable WAL mode + busy_timeout in `migrator.py` or `container.py`

### 1.5 API server structure

```
src/polymarket_trades/api/
├── __init__.py
├── app.py              # create_app() factory, lifespan, CORS, static mount
├── deps.py             # get_container() FastAPI dependency
├── auth.py             # JWT encode/decode, password verify, get_current_user dep
├── schemas.py          # Pydantic response/request models
└── routers/
    ├── __init__.py
    ├── auth.py         # POST /api/auth/login, GET /api/auth/me
    ├── dashboard.py    # GET /api/dashboard
    ├── positions.py    # GET /api/positions, GET /api/positions/{id}
    ├── opportunities.py # GET /api/opportunities
    ├── trades.py       # GET /api/trades/history, GET /api/trades/export (CSV)
    ├── bot.py          # GET /api/bot/status, POST /api/bot/scan|stop|start
    └── settings.py     # GET /api/settings, PATCH /api/settings
```

**Key pattern:** Each router gets `Container` via `Depends(get_container)` and calls existing use cases. Same pattern as CLI.

### 1.6 Auth

- JWT with `python-jose`, bcrypt for password hashing
- New settings: `API_JWT_SECRET`, `API_ADMIN_EMAIL`, `API_ADMIN_PASSWORD_HASH`
- `POST /api/auth/login` → validates credentials → returns JWT
- All other routes require `Authorization: Bearer <token>`
- Single-user: admin creds from env vars. Multi-tenant later: add `users` table.

### 1.7 Bot status coordination

The bot worker writes its status to `bot_status` table each cycle. The API reads it.

**Bot control from API:**
- **Stop**: API writes `STOP_REQUESTED` → bot checks at top of each loop iteration, exits gracefully
- **Scan**: API writes `SCAN_REQUESTED` → bot picks up, runs scan, resets flag
- **Start**: bot auto-restarts via process manager (Dokku). API just reports status.

Modify `src/polymarket_trades/application/scheduler.py` to:
1. Write bot status at start/end of each cycle
2. Check for pending actions before sleeping

### 1.8 Settings live-reload

- `PATCH /api/settings` writes to `runtime_settings` table
- Bot reads `runtime_settings` at start of each cycle, merges with env defaults
- No restart needed for config changes

### 1.9 New settings fields

Add to `src/polymarket_trades/infrastructure/config/settings.py`:
```python
api_jwt_secret: str = ""
api_admin_email: str = "admin@local"
api_admin_password_hash: str = ""
api_jwt_expiry_hours: int = 24
cors_origins: str = "http://localhost:3000"
```

### 1.10 Procfile

```
web: uv run uvicorn polymarket_trades.api.app:create_app --factory --host 0.0.0.0 --port $PORT
worker: uv run python -m polymarket_trades run --dry-run
```

---

## Phase 2: Next.js Frontend

### 2.1 Initialize

```
web/
├── package.json
├── next.config.ts        # output: 'export' for static build
├── tsconfig.json
└── src/
    ├── app/              # App Router
    │   ├── layout.tsx    # Root layout with sidebar
    │   ├── page.tsx      # Dashboard
    │   ├── login/page.tsx
    │   ├── positions/page.tsx
    │   ├── opportunities/page.tsx
    │   ├── history/page.tsx
    │   └── settings/page.tsx
    ├── components/
    │   ├── ui/           # shadcn/ui primitives
    │   ├── dashboard/    # Summary cards, P&L chart
    │   ├── positions/    # Position table
    │   └── layout/       # Sidebar, header, auth guard
    └── lib/
        ├── api.ts        # Typed fetch wrapper
        ├── auth.ts       # Token storage, auth context
        └── types.ts      # TypeScript types matching API schemas
```

### 2.2 Key dependencies

`next`, `react`, `typescript`, `tailwindcss`, `@tanstack/react-query`, `recharts`, `date-fns`, `shadcn/ui`

### 2.3 Pages

| Page | Purpose |
|------|---------|
| `/login` | Email + password form |
| `/` (dashboard) | Summary cards (P&L, positions, capital), strategy breakdown chart, recent opportunities |
| `/positions` | Filterable table of all positions (open/closed, paper/live) |
| `/opportunities` | Recent opportunity scans with strategy type, expected profit |
| `/history` | Resolved trades with P&L, CSV export button |
| `/settings` | Edit thresholds, capital, strategy toggles. Bot start/stop/scan buttons. |

### 2.4 Static build + serving

- `next.config.ts`: `output: 'export'` for static HTML/JS/CSS
- Built at deploy time, output to `web/out/`
- FastAPI serves via `app.mount("/", StaticFiles(directory="web/out", html=True))`
- Client-side routing works via `html=True` fallback

---

## Phase 3: Integration

### 3.1 SQLite WAL mode

Add to connection setup in `build_container()`:
```python
await db.execute("PRAGMA journal_mode=WAL")
await db.execute("PRAGMA busy_timeout=5000")
```

### 3.2 Build pipeline

For herokuish deploy:
1. Python buildpack installs Python deps via `uv sync`
2. Node buildpack (or build script) runs `cd web && npm install && npm run build`
3. Static output lands in `web/out/`
4. FastAPI serves it

Add to `justfile`:
```
build-web:
    cd web && npm install && npm run build

dev-api:
    uv run uvicorn polymarket_trades.api.app:create_app --factory --reload --port 8000

dev-web:
    cd web && npm run dev
```

---

## Critical files to modify

| File | Change |
|------|--------|
| `pyproject.toml` | Add FastAPI, uvicorn, jose, bcrypt deps |
| `src/polymarket_trades/infrastructure/config/settings.py` | Add API auth + CORS settings |
| `src/polymarket_trades/domain/ports/position_tracker.py` | Add paginated/count methods |
| `src/polymarket_trades/domain/ports/opportunity_store.py` | Add `list_recent` |
| `src/polymarket_trades/infrastructure/persistence/sqlite_position_tracker.py` | Implement new methods |
| `src/polymarket_trades/infrastructure/persistence/sqlite_opportunity_store.py` | Implement `list_recent` |
| `src/polymarket_trades/application/scheduler.py` | Write bot_status, check pending actions |
| `src/polymarket_trades/application/container.py` | Wire BotStatusPort, WAL mode |
| `Procfile` | Add `web` process |
| `justfile` | Add dev-api, dev-web, build-web commands |

## New files to create

| File | Purpose |
|------|--------|
| `src/polymarket_trades/infrastructure/persistence/migrations/002_api_tables.sql` | bot_status + runtime_settings tables |
| `src/polymarket_trades/domain/ports/bot_status.py` | BotStatusPort interface |
| `src/polymarket_trades/infrastructure/persistence/sqlite_bot_status.py` | SQLite implementation |
| `src/polymarket_trades/api/` (entire directory) | FastAPI app, routers, auth, schemas |
| `web/` (entire directory) | Next.js SPA |

---

## Verification

1. `uv run pytest` — all existing 162 tests pass (no regressions)
2. `uv run uvicorn polymarket_trades.api.app:create_app --factory --port 8000` — API starts
3. `curl http://localhost:8000/api/auth/login -d '{"email":"admin@local","password":"test"}' -H 'Content-Type: application/json'` — returns JWT
4. `curl http://localhost:8000/api/dashboard -H 'Authorization: Bearer <token>'` — returns dashboard data
5. `curl http://localhost:8000/api/bot/status -H 'Authorization: Bearer <token>'` — returns bot state
6. `cd web && npm run dev` — frontend loads at localhost:3000, login works, dashboard shows data
7. `cd web && npm run build` — static export succeeds
8. `curl http://localhost:8000/` — serves the built SPA
9. Deploy to Dokku: `git push dokku main` — both `web` and `worker` processes start

## Implementation order

1. Port extensions + SQLite implementations + migration (backend foundation)
2. API app factory + auth + deps (API skeleton)
3. API routers one by one (dashboard → positions → opportunities → trades → bot → settings)
4. Scheduler modifications (bot status reporting + action checking)
5. API tests
6. Next.js init + auth flow
7. Dashboard page
8. Remaining pages (positions, opportunities, history, settings)
9. Static build + FastAPI serving
10. Integration testing + deploy
