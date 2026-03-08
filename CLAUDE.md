# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Shadowsocks VPN management service with a FastAPI backend and Vue 3 frontend. Users can create/manage access keys that each spawn individual `ss-server` (shadowsocks-libev) processes. Traffic is counted via iptables rules per port.

## Development Commands

### Backend (Python 3.14, uv)

```bash
cd backend

# Install dependencies
uv sync

# Run dev server (requires postgres running)
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Database migrations
uv run alembic upgrade head          # apply migrations
uv run alembic revision --autogenerate -m "description"  # create migration
uv run alembic downgrade -1          # rollback one migration
```

### Frontend (Node.js, npm)

```bash
cd frontend

# Install dependencies
npm install

# Dev server (proxies /api to localhost:8000)
npm run dev

# Type check
npm run type-check

# Production build
npm run build
```

### Infrastructure

```bash
# Start postgres + redis (required for local dev)
docker compose up db redis -d

# Full stack via Docker
docker compose up --build
```

## Architecture

### Backend (`backend/app/`)

The backend is a **FastAPI async application** running on uvicorn. Key components:

- **`main.py`** — App entry point. On startup, restores all active SS instances from DB and starts background services (`TrafficMonitor`, `SpeedTracker`). On shutdown, stops all SS instances.

- **`services/shadowsocks.py`** — `ShadowsocksManager` singleton (`ss_manager`). Manages spawning/stopping individual `ss-server` subprocesses per port. Also manages iptables rules for per-port traffic counting. Configs written to `SS_CONFIG_DIR` (default `/etc/shadowsocks-libev/users`).

- **`services/traffic_monitor.py`** — Background async task (60s interval). Reads cumulative iptables byte counters via `iptables -L -v -n -x`, calculates deltas, writes to DB. Suspends keys when user traffic limit is exceeded.

- **`services/speed_tracker.py`** — Background async task. Publishes real-time speed data to Redis pub/sub channel `speed_updates`.

- **`api/websocket.py`** — WebSocket endpoint `/api/ws/speed/{key_id}` subscribes to Redis `speed_updates` and streams per-key speed metrics to clients.

- **`api/deps.py`** — FastAPI dependency injection: `get_current_active_user`, `get_admin_user` (JWT Bearer auth).

- **`models/`** — SQLAlchemy ORM models: `User` (plans: free/basic/pro), `Server`, `AccessKey` (port, password, method, traffic counters), `TrafficLog`.

- **`utils/crypto.py`** — JWT access/refresh token creation and verification (PyJWT + bcrypt). Access tokens expire in 30 min, refresh tokens in 7 days.

- **`utils/ss_url.py`** — Generates `ss://` URIs and base64-encoded QR codes for client apps.

- **`migration/`** — Alembic migrations with async engine (`asyncpg`).

### Plan limits

```python
PLAN_KEY_LIMITS = {
    PlanType.free: 1,
    PlanType.basic: 3,
    PlanType.pro: 10,
}
```

### Frontend (`frontend/src/`)

Vue 3 SPA with Pinia and Vue Router.

- **`api/client.ts`** — Fetch wrapper with proactive JWT refresh (checks expiry before each request) and reactive refresh on 401. Deduplicates concurrent refresh calls via a shared `refreshPromise`.

- **`stores/auth.ts`** — Pinia auth store. Schedules token refresh timer (fires 2 min before expiry). `init()` is called by the router guard on first navigation.

- **`router/index.ts`** — Two routes: `/` (Dashboard) and `/login`. Navigation guard calls `authStore.init()` once, then redirects unauthenticated users to `/login`.

- **`utils/token.ts`** — localStorage-based token storage helpers + JWT expiry parsing.

- **`views/DashboardView.vue`** — Main dashboard: displays keys, server selector, traffic stats, speed monitor.

- **`components/`** — `KeyCard.vue`, `KeysList.vue`, `ServerSelect.vue`, `TrafficStats.vue`, `SpeedMonitor.vue` (WebSocket-based), `ProfileCard.vue`.

### API Endpoints

All prefixed with `/api`:

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Register → returns access+refresh tokens |
| POST | `/auth/login` | Login |
| GET | `/auth/me` | Current user |
| POST | `/auth/refresh` | Refresh tokens |
| GET | `/keys/my` | List active keys |
| POST | `/keys/create` | Create key (spawns SS process) |
| DELETE | `/keys/{id}` | Deactivate key (stops SS process) |
| POST | `/keys/{id}/regenerate` | Regenerate password |
| GET | `/servers/` | List active servers |
| GET | `/traffic/stats` | Traffic stats |
| WS | `/ws/speed/{key_id}` | Real-time speed stream |

### Agent Node Architecture (`backend/agent/`)

A standalone FastAPI service for deploying VPN on remote nodes. Exposes a minimal HTTP API consumed by `RemoteAgentBackend`:

- **`main.py`** — Starts/stops `ss-server` subprocesses and manages iptables rules. Endpoints:
  - `POST /instances` — Start a shadowsocks instance on a port
  - `DELETE /instances/{port}` — Stop an instance
  - `GET /traffic` — Per-port byte counters (same iptables parsing as local)
  - `GET /health` — Active instance count
  - `GET /info` — Public IP (via ipify)
- **`auth.py`** — Token auth via `X-Agent-Token` request header
- **`Dockerfile`** — Separate image for deployment on remote nodes

### Server Backend Protocol (`backend/app/services/server_backend.py`)

`ServerBackend` is a `Protocol` with two implementations:

- **`LocalBackend`** — Delegates to the local `ss_manager` singleton
- **`RemoteAgentBackend`** — Calls a remote agent over HTTP (httpx), passing `X-Agent-Token`

`get_backend(server)` returns `LocalBackend` when `server.is_local` is true, otherwise `RemoteAgentBackend(server.agent_url, server.agent_token)`. The `Server` model has `agent_url` and `agent_token` fields (added in the second migration).

### Configuration

Backend reads from `backend/.env`. Required vars (no defaults):
```
POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB
REDIS_URL               # e.g. redis://localhost:6379
SECRET_KEY              # JWT signing key (change in production!)
ADMIN_EMAIL             # bootstrapped admin account email
ADMIN_PASSWORD          # bootstrapped admin account password
LOCAL_SERVER_NAME       # display name for the local server
LOCAL_SERVER_COUNTRY    # country code for the local server
```

Optional (have defaults):
```
SS_BINARY_PATH      # default: /usr/bin/ss-server
SS_CONFIG_DIR       # default: /etc/shadowsocks-libev/users
SS_METHOD           # default: chacha20-ietf-poly1305
PORT_RANGE_START/END # default: 10001–60000
CORS_ORIGINS        # comma-separated; default: localhost:5173,localhost:3000
```

### No Tests or Linting

There is no test suite (no pytest, vitest) and no linter configured (no ruff, eslint). Run the app manually to verify changes.

### Production Requirements

The backend container runs with `privileged: true` and `network_mode: host` because it needs to:
1. Execute `ss-server` subprocesses
2. Manage iptables rules for traffic accounting

The `shadowsocks-libev` and `iptables` binaries must be present in the container (see `Dockerfile`).