# Control Plane API

`apps/controlplane-api` is the aggregator API for the multi-product operator dashboard.

It exposes:

- `/overview/summary`: cross-repo health for ClownPeanuts, PingTing, and orchestration state.
- `/sentry/summary`: PingTing status snapshot (`?refresh=true` forces CLI refresh).
- `/sentry/findings`: recent PingTing findings from SQLite (`limit`, `severity`, and inclusion flags).
- `/sentry/runs`: recent PingTing agent run history from SQLite (`limit`, `agent`, `status`).
- `/orchestration/summary`: managed repo and workflow status from SquirrelOps.
- `/orchestration/actions/bootstrap`: executes `scripts/bootstrap_repos.sh` against workspace repos.
- `/orchestration/actions/smoke`: executes `harness/smoke.sh` against workspace repos.
- `/orchestration/actions/update`: executes `scripts/update_repos.sh` against workspace repos.
- `/deception/{path}`: HTTP proxy path to the ClownPeanuts API.
- `/deception/ws/events`: websocket relay for ClownPeanuts event stream.
- `/deception/ws/theater/live`: websocket relay for ClownPeanuts theater stream.

## Run locally

```bash
cd apps/controlplane-api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

The API listens on `http://127.0.0.1:8199` by default.

Container image build (from repository root):

```bash
docker build -f apps/controlplane-api/Dockerfile -t squirrelops-controlplane-api .
```

## Environment variables

- `CONTROLPLANE_WORKSPACE_ROOT` (default: `/Users/matt/code`)
- `CONTROLPLANE_PROJECTS_CONFIG` (default: `config/projects.yaml`)
- `CLOWNPEANUTS_API_BASE` (default: `http://127.0.0.1:8099`)
- `CLOWNPEANUTS_API_TOKEN` (optional)
- `CLOWNPEANUTS_WS_EVENTS_URL` (default: `ws://127.0.0.1:8099/ws/events`)
- `CLOWNPEANUTS_WS_THEATER_URL` (default: `ws://127.0.0.1:8099/ws/theater/live`)
- `CLOWNPEANUTS_WS_TOKEN` (optional, defaults to `CLOWNPEANUTS_API_TOKEN` when set)
- `PINGTING_REPO_PATH` (default: `$CONTROLPLANE_WORKSPACE_ROOT/pingting`)
- `PINGTING_STATUS_PATH` (default: `$PINGTING_REPO_PATH/data/status.json`)
- `PINGTING_CONFIG_PATH` (default: `$PINGTING_REPO_PATH/config/pingting.yaml`)
- `PINGTING_PYTHON_BIN` (optional explicit Python executable)
- `PINGTING_STATUS_MAX_AGE_SECONDS` (default: `120`)
- `PINGTING_STATUS_TIMEOUT_SECONDS` (default: `20`)
- `CONTROLPANE_API_AUTH_TOKEN` (optional shared API token)
- `CONTROLPANE_CORS_ALLOW_ORIGINS` (comma-separated origins)
- `CONTROLPANE_ACTION_TIMEOUT_SECONDS` (default: `900`)
- `CONTROLPANE_BOOTSTRAP_SCRIPT_PATH` (default: `scripts/bootstrap_repos.sh`)
