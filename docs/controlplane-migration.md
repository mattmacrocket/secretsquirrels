# Control-Plane Migration (ClownPeanuts -> SecretSquirrels)

## Decision

The shared dashboard/control-plane now lives in `secretsquirrels`:

- `apps/controlplane-dashboard` (Next.js UI)
- `apps/controlplane-api` (aggregator API)
- `adapters/clownpeanuts`
- `adapters/pingting`

Current implementation snapshot:

- `docs/current-state.md`

## Why

- Avoid coupling multi-product operator UX to ClownPeanuts release cycles.
- Keep orchestration and cross-product UI/API in the umbrella repository.
- Scale cleanly when a third product adapter is added.

## Migration Mechanics

- Dashboard source was imported from `clownpeanuts/dashboard` with `git subtree` so commit history is preserved.
- ClownPeanuts-local dashboard can continue running during cutover.
- The new dashboard defaults to control-plane API calls via `NEXT_PUBLIC_CONTROLPANE_API`.
- Deception websocket streams are relayed through `apps/controlplane-api` (`/deception/ws/events`, `/deception/ws/theater/live`).

## Current Status

As of 2026-02-21, the following are implemented and in active use from `secretsquirrels`:

- Shared Next.js control-plane dashboard with Overview, Deception, Theater, Sentry, and Orchestration operator surfaces.
- Shared FastAPI control-plane API with PingTing summary/findings/runs aggregation and orchestration action endpoints.
- ClownPeanuts HTTP proxy + websocket relay integration (`/deception/*` and `/deception/ws/*`).
- Orchestration actions persisted to local state (`data/controlplane/actions-state.json`) and rendered in UI.
- Legacy theater route aliases retained in dashboard for compatibility while cutover hardens.

## UI Model

- `Overview` tab: cross-repo posture and health.
- `Deception` tab: ClownPeanuts operational views.
- `Theater` tab: live session theater + replay drilldown workflows.
- `Sentry` tab: PingTing status and findings posture.
- `Orchestration` tab: repo state + bootstrap/smoke/update workflow actions.

## Cutover Plan

1. Start `apps/controlplane-api` and `apps/controlplane-dashboard` in SecretSquirrels.
   - Shortcut: `./scripts/controlplane/start_dev.sh`
   - API smoke: `./harness/controlplane-smoke.sh`
   - Container option: `docker compose -f docker-compose.controlplane.yml up --build`
2. Validate parity for Deception views against existing ClownPeanuts dashboard.
3. Validate Sentry and Orchestration tabs in operator workflows.
4. Keep ClownPeanuts-local dashboard available until parity sign-off.
5. Deprecate ClownPeanuts-local dashboard after operators switch to SecretSquirrels control-plane.

## Environment Variables

Dashboard:

- `NEXT_PUBLIC_CONTROLPANE_API` (default: `http://127.0.0.1:8199`)
- `NEXT_PUBLIC_CONTROLPANE_WS` (default: `ws://127.0.0.1:8199`)
- `NEXT_PUBLIC_CONTROLPANE_API_TOKEN` (optional)
- `NEXT_PUBLIC_DECEPTION_WS` / `NEXT_PUBLIC_DECEPTION_WS_THEATER` (optional websocket override)
- `NEXT_PUBLIC_CLOWNPEANUTS_WS` / `NEXT_PUBLIC_CLOWNPEANUTS_WS_THEATER` (legacy direct websocket overrides)

Control-plane API:

- `CLOWNPEANUTS_API_BASE`
- `CLOWNPEANUTS_API_TOKEN`
- `CLOWNPEANUTS_WS_EVENTS_URL`
- `CLOWNPEANUTS_WS_THEATER_URL`
- `CLOWNPEANUTS_WS_TOKEN`
- `PINGTING_REPO_PATH`
- `PINGTING_STATUS_PATH`
- `PINGTING_CONFIG_PATH`
- `CONTROLPANE_API_AUTH_TOKEN`
