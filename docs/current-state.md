# SquirrelOps Current State

Snapshot date: 2026-02-21

This document is the detailed implementation snapshot for the orchestration and control-plane work currently living in `squirrelops`. It is intentionally specific to what is implemented in code today.

## 1. Repository role and boundaries

`squirrelops` is now both:

1. The multi-repo orchestration layer for the workspace.
2. The shared control-plane host for operator-facing dashboard/API surfaces.

Product-specific runtime behavior still belongs in runtime repositories:

- `/Users/matt/code/clownpeanuts`
- `/Users/matt/code/pingting`

Optional integrations are intentionally out-of-band and are not part of the current required workspace contract.

`squirrelops` owns the cross-product coordination layer:

- workspace repo mapping and verification
- bootstrap/update/smoke actions
- shared dashboard and aggregator API
- adapters that translate runtime data into control-plane friendly payloads

Compatibility requirement:

- control-plane/runtime workflows remain valid with only SquirrelOps + ClownPeanuts + PingTing present.

## 2. Canonical workspace model

The source of truth remains:

- `/Users/matt/code/squirrelops/config/projects.yaml`

Current runtime entries:

- `pingting` (`role: runtime`, verification key `pingting/main.py`)
- `clownpeanuts` (`role: runtime`, verification key `clownpeanuts/cli.py`)

Current control-plane metadata in config includes:

- tab/route metadata per project (`dashboard.tab`, `dashboard.route`)
- capability flags per project (`capabilities.*`)
- orchestration control-plane defaults under `orchestration.controlplane`

## 3. Control-plane implementation inventory

### 3.1 Dashboard app

Path:

- `/Users/matt/code/squirrelops/apps/controlplane-dashboard`

Runtime stack:

- Next.js `14.2.12`
- React `18.3.1`
- TypeScript `5.5.4`

Current primary routes:

- `/` -> redirects to `/overview`
- `/overview`
- `/deception`
- `/deception/theater`
- `/deception/theater/replay/[sessionId]`
- `/sentry`
- `/orchestration`

Legacy compatibility routes still present:

- `/theater`
- `/theater/replay/[sessionId]`

Current navigation model (header nav + responsive menu):

- Overview
- Deception
- Theater
- Sentry
- Orchestration
- Active-route emphasis highlights the current section.
- On tighter widths, links collapse behind a menu trigger.
- Repository URL is rendered in the page footer.

Polling/refresh behavior in the current UI:

- `Overview`: 15s interval
- `Orchestration`: 15s interval
- `Sentry`: 20s interval
- `Deception`: operator-selectable refresh interval (5s/10s/15s/30s), default 15s, plus websocket stream for live events
- `Theater`: websocket live stream for theater updates plus fallback polling/action ledger polling

### 3.2 Aggregator API

Path:

- `/Users/matt/code/squirrelops/apps/controlplane-api`

Runtime stack:

- FastAPI `0.115.0`
- Uvicorn `0.30.6`
- HTTPX `0.27.2`

Current implemented HTTP routes:

- `GET /health`
- `GET /overview/summary`
- `GET /sentry/summary`
- `GET /sentry/findings`
- `GET /sentry/runs`
- `GET /orchestration/summary`
- `POST /orchestration/actions/smoke`
- `POST /orchestration/actions/bootstrap`
- `POST /orchestration/actions/update`
- `ANY /deception/{target_path:path}` (HTTP proxy into ClownPeanuts API)

Current implemented websocket routes:

- `WS /deception/ws/events`
- `WS /deception/ws/theater/live`

### 3.3 Adapter layers

Paths:

- `/Users/matt/code/squirrelops/adapters/clownpeanuts`
- `/Users/matt/code/squirrelops/adapters/pingting`

Current behavior:

- `ClownPeanutsAdapter`:
  - HTTP status fetch (`/status`)
  - generic HTTP proxy helper with optional bearer forwarding
- `PingTingAdapter`:
  - loads `status` from file first (`data/status.json`) with staleness awareness
  - falls back to `python -m pingting status --json` when file is missing/stale/forced refresh
  - reads recent findings directly from PingTing SQLite (`data/pingting.db`)
  - reads recent agent runs directly from PingTing SQLite (`data/pingting.db`)

## 4. API auth, CORS, and websocket token handling

Current auth model is optional and token-based.

When `CONTROLPANE_API_AUTH_TOKEN` is unset:

- API routes are unauthenticated.

When `CONTROLPANE_API_AUTH_TOKEN` is set:

- HTTP requests require matching token from one of:
  - `Authorization: Bearer <token>`
  - `X-API-Key: <token>`
  - `?token=<token>` query parameter
- `OPTIONS` and `/health` are exempt.
- websocket routes require matching token from:
  - bearer header
  - `X-API-Key`
  - query token keys (`token`, `api_key`, `access_token`)

CORS behavior:

- enabled when `CONTROLPANE_CORS_ALLOW_ORIGINS` resolves to non-empty list
- `allow_credentials=False`
- `allow_methods=["*"]`
- `allow_headers=["*"]`

## 5. Current data flow

### 5.1 Overview tab

`GET /overview/summary` currently aggregates:

- ClownPeanuts runtime status (`/status`)
- PingTing status summary (highlights + freshness)
- PingTing recent findings subset (5 rows, not acknowledged)
- orchestration repo/action summary

Overall health (`overall_ok`) currently evaluates:

- deception upstream reachable
- sentry summary successful
- no missing runtime repos in orchestration summary

### 5.2 Sentry tab

Backed by:

- `GET /sentry/summary`
- `GET /sentry/findings`
- `GET /sentry/runs`

Current filter support surfaced in UI:

- findings: severity + acknowledged inclusion + learning inclusion
- runs: agent + run status
- explicit status refresh (`?refresh=true`) wired to "Force refresh"

### 5.3 Deception tab

Current behavior:

- uses control-plane API as default base, then proxies to ClownPeanuts
- shows live event stream freshness and snapshot freshness separately
- maintains reconnect countdown state for websocket interruption scenarios
- includes operator actions currently wired to ClownPeanuts endpoints through proxy (for example alert test and intel rotation triggers)

### 5.4 Theater tab

Current behavior:

- consumes theater live websocket relay (`/deception/ws/theater/live`)
- supports fallback polling when stream is unavailable
- fetches theater action ledger and session replay detail through proxied ClownPeanuts endpoints
- supports recommendation application/label actions and session bookmarking UX

### 5.5 Orchestration tab

Backed by:

- `GET /orchestration/summary`
- `POST /orchestration/actions/{bootstrap|smoke|update}`

Current action execution model:

- action scripts run via subprocess with timeout
- trimmed combined stdout/stderr is returned in API payload
- last action results are persisted to:
  - `/Users/matt/code/squirrelops/data/controlplane/actions-state.json`

## 6. Scripted local/dev operations

Control-plane dev scripts:

- `/Users/matt/code/squirrelops/scripts/controlplane/start_api.sh`
- `/Users/matt/code/squirrelops/scripts/controlplane/start_dashboard.sh`
- `/Users/matt/code/squirrelops/scripts/controlplane/start_dev.sh`
- `/Users/matt/code/squirrelops/scripts/controlplane/install_launch_agent.sh`
- `/Users/matt/code/squirrelops/scripts/controlplane/uninstall_launch_agent.sh`

Current behavior:

- API script creates app-local virtualenv if absent and installs requirements (unless skip flag set)
- API defaults to `http://127.0.0.1:8199`
- dashboard script installs `node_modules` if absent
- dashboard dev script defaults to `http://127.0.0.1:4317`
- combined script runs both services and logs to `/tmp/controlplane-api.log` and `/tmp/controlplane-dashboard.log`
- macOS boot/login startup is supported via launchd install/uninstall helper scripts

Smoke harness:

- `/Users/matt/code/squirrelops/harness/controlplane-smoke.sh`

Current checks:

- `/health`
- `/overview/summary`
- `/sentry/summary`
- `/sentry/findings?limit=1`
- `/orchestration/summary`

## 7. Containerized control-plane state

Compose file:

- `/Users/matt/code/squirrelops/docker-compose.controlplane.yml`

Current default assumptions in compose:

- workspace root bind mount: `/Users/matt/code`
- ClownPeanuts upstream reachable from container via `host.docker.internal:8099`
- PingTing repo/data mounted/read from `/Users/matt/code/pingting`
- published ports:
  - dashboard `4317`
  - API `8199`

## 8. CI coverage in this repository

Current workflows:

- `/Users/matt/code/squirrelops/.github/workflows/cross-repo-smoke.yml`
- `/Users/matt/code/squirrelops/.github/workflows/controlplane-smoke.yml`

Current CI responsibilities:

- validate runtime repo bootstrap + smoke
- validate control-plane API endpoint self-checks
- validate control-plane dashboard build
- syntax-check control-plane scripts and harness

## 9. Control-plane compatibility state

Current compatibility posture:

- shared dashboard/control-plane runs from `squirrelops`
- route aliases remain available for theater compatibility (`/theater`, `/theater/replay/[sessionId]`)
- ClownPeanuts-local dashboard remains supported for runtime-focused development and compatibility

## 10. Known current constraints

These are implementation-shape constraints, not defects:

- PingTing integration is read-oriented in control-plane today (status/findings/runs), not full PingTing command orchestration.
- ClownPeanuts integration is adapter/proxy oriented; control-plane currently depends on ClownPeanuts API availability for Deception/Theater surfaces.
- Action execution state is local-file based (`actions-state.json`), not distributed/shared across multiple control-plane nodes.

## 11. Related docs

- `/Users/matt/code/squirrelops/README.md`
- `/Users/matt/code/squirrelops/docs/orchestration.md`
- `/Users/matt/code/squirrelops/docs/repo-map.md`
