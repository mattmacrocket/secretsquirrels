# SquirrelOps

SquirrelOps is the orchestration layer for a multi-repository agent workspace. It provides the scripts, configuration, and test harnesses needed to bootstrap, update, and verify runtime repositories, and now also hosts the shared operator control-plane applications.

The two runtime repositories managed by this orchestration layer are:

- **PingTing** — [github.com/mattmacrocket/pingting](https://github.com/mattmacrocket/pingting)
- **ClownPeanuts** — [github.com/mattmacrocket/clownpeanuts](https://github.com/mattmacrocket/clownpeanuts)

## Optional Integration Boundary

Optional integrations are additive and must not be required for baseline operation.

Baseline required set remains:

- `squirrelops` (control-plane/orchestration)
- `clownpeanuts` (deception runtime)
- `pingting` (sentry runtime)

Bootstrap, update, smoke, CI, and control-plane startup are expected to work with only the baseline set above.

### Required Integrations

- **SquirrelOps** — The central orchestration and control-plane layer. SquirrelOps manages the lifecycle of the runtime repositories, runs health checks, and hosts the operator dashboard and aggregation API that bring everything together in one interface.

- **ClownPeanuts** — The deception runtime responsible for deploying and managing decoy assets, canary tokens, and threat-intelligence feeds. ClownPeanuts publishes real-time events and theater visualizations that the control-plane relays to operators through the dashboard. It also exposes a TAXII 2 endpoint for sharing structured threat data with external platforms.

- **PingTing** — The sentry runtime that continuously monitors the environment for security-relevant findings and anomalies. PingTing produces structured alerts and run reports that the control-plane surfaces in the Sentry tab, giving operators a single view of detection activity across the workspace.

### Optional Integrations

- **OpenCTI** — A threat-intelligence platform that aggregates, correlates, and visualizes indicators from multiple sources. When deployed alongside SquirrelOps, OpenCTI ingests ClownPeanuts deception data through its TAXII connector, allowing analysts to explore relationships between deception events and broader threat activity.

- **MITRE ATT&CK** — An industry-standard framework of adversary tactics and techniques maintained by MITRE. When enabled within OpenCTI, the ATT&CK connector imports the full technique catalog so that deception findings and intelligence from ClownPeanuts can be mapped to recognized adversary behaviors.

## What This Repository Contains

- **`config/projects.yaml`** — The single source of truth for which repositories are managed, their Git URLs, their roles, and the file paths used to verify a successful checkout (called "verification keys").
- **`scripts/bootstrap_repos.sh`** — Clones each managed runtime repository if it is not already present, or fetches and fast-forward-merges if it is. Runs all repositories in parallel.
- **`scripts/update_repos.sh`** — Fetches and fast-forward-merges each managed runtime repository that already exists locally. Skips any that have not been cloned yet. Runs in parallel.
- **`scripts/lib/common.sh`** — Shared shell library used by all scripts. Handles YAML parsing, URL normalization, directory validation, clone protocol selection, timeout wrappers, and the ephemeral `GIT_ASKPASS` credential helper.
- **`harness/smoke.sh`** — Smoke test that verifies each managed repository has a valid `.git` directory and that its verification key file exists on disk.
- **`harness/opencti/`** — Docker Compose stack and environment template for running OpenCTI with MITRE ATT&CK and ClownPeanuts TAXII connectors.
- **`scripts/opencti/`** — Helper scripts for starting the OpenCTI stack and checking ClownPeanuts TAXII endpoint availability.
- **`apps/controlplane-dashboard`** — Next.js operator interface with Overview, Deception, Theater, Sentry, and Orchestration tabs.
- **`apps/controlplane-api`** — FastAPI aggregator API for ClownPeanuts + PingTing + orchestration status/actions.
- **`adapters/clownpeanuts`** — Adapter layer for ClownPeanuts API proxying.
- **`adapters/pingting`** — Adapter layer for PingTing status ingestion.
- **`.github/workflows/cross-repo-smoke.yml`** — CI workflow that clones all managed repos and runs the smoke harness on every push.
- **`docs/`** — Guides and reference documentation, including a macOS setup guide and an OpenCTI integration playbook.

## Quick Start

Clone this repository, bootstrap the runtime repos, and run the smoke test:

```bash
git clone git@github.com:mattmacrocket/squirrelops.git
cd squirrelops
./scripts/bootstrap_repos.sh
./harness/smoke.sh
```

The bootstrap script will clone PingTing and ClownPeanuts into sibling directories alongside SquirrelOps (by default, under `/Users/matt/code`). The smoke test confirms that each repository was cloned successfully and contains its expected entry-point file.

For a step-by-step walkthrough of setting up the workspace on macOS, including prerequisites and authentication options, see **[docs/user-guide-macos.md](docs/user-guide-macos.md)**.

For deploying the OpenCTI threat intelligence platform with MITRE ATT&CK and ClownPeanuts TAXII feeds, see **[docs/opencti-integration.md](docs/opencti-integration.md)**.

For a detailed implementation snapshot of orchestration + control-plane behavior, see **[docs/current-state.md](docs/current-state.md)**.

### Running The Control Plane

The shared dashboard/API run from this repository:

```bash
# run both (foreground supervisor)
./scripts/controlplane/start_dev.sh
```

Or run each service independently:

```bash
# API
./scripts/controlplane/start_api.sh

# Dashboard (new shell)
./scripts/controlplane/start_dashboard.sh
```

Dashboard port can be overridden when needed:

```bash
CONTROLPANE_DASHBOARD_PORT=4519 ./scripts/controlplane/start_dashboard.sh
```

### Start On Boot (macOS)

Install a user `launchd` agent so the control-plane comes up automatically at login:

```bash
./scripts/controlplane/install_launch_agent.sh
```

Default launch-agent behavior:

- label: `com.squirrelops.controlplane`
- dashboard port: `4317`
- API port: `8199`
- log files: `/tmp/squirrelops-controlplane.launchd.log` and `/tmp/squirrelops-controlplane.launchd.err.log`

To remove boot startup:

```bash
./scripts/controlplane/uninstall_launch_agent.sh
```

Optional API verification:

```bash
./harness/controlplane-smoke.sh
```

### Docker Compose (Control Plane)

Run dashboard + API together:

```bash
docker compose -f docker-compose.controlplane.yml up --build
```

Notes:

- This compose file expects runtime repos at `/Users/matt/code`.
- ClownPeanuts API is expected on host `:8099`.
- PingTing data is read from `/Users/matt/code/pingting`.

Default local endpoints:

- Dashboard: `http://127.0.0.1:4317`
- Control-plane API: `http://127.0.0.1:8199`
- ClownPeanuts API upstream: `http://127.0.0.1:8099`
- Control-plane websocket relays: `ws://127.0.0.1:8199/deception/ws/events` and `ws://127.0.0.1:8199/deception/ws/theater/live`

### Using a Custom Base Directory

By default, all scripts assume the runtime repositories live under `/Users/matt/code`. You can override this by passing a directory as the first argument:

```bash
./scripts/bootstrap_repos.sh /Users/matt/work
./scripts/update_repos.sh /Users/matt/work
./harness/smoke.sh /Users/matt/work
```

The directory you specify must be within one of the allowed base roots (see "Security Controls" below), or the script will refuse to proceed.

## Security Controls

Several guardrails are built into the scripts to prevent accidental operations on unexpected paths or repositories:

- **Directory validation** — Every script validates that the requested base directory falls within `ALLOWED_BASE_ROOTS` before doing anything. This prevents the scripts from being tricked into cloning into or modifying files in arbitrary locations. The default allowed root is `/Users/matt/code`; in CI, `$RUNNER_TEMP` is also allowed.

- **Owner validation** — When constructing or verifying a Git remote URL, the scripts check that the GitHub owner (organization or user) is in the `ALLOWED_GITHUB_ORGS` list. The default is `mattmacrocket`. This prevents the scripts from operating on repositories owned by unexpected parties.

- **Remote verification** — Before updating an existing checkout, the scripts parse the current Git remote URL and compare the owner/repo slug against what `config/projects.yaml` declares. If they do not match, the operation is aborted. This catches situations where a directory exists at the expected path but points to a different repository.

- **Ephemeral credential helper** — When using HTTPS cloning with a token, the scripts create a temporary `GIT_ASKPASS` script (with `chmod 700`) that supplies the token to Git's credential prompt. The token is never embedded in the clone URL itself. The temporary script is cleaned up automatically on exit via a shell trap.

- **Non-interactive Git** — All Git operations run with `GIT_TERMINAL_PROMPT=0`, which prevents Git from opening an interactive password prompt. If credentials are missing or wrong, the operation fails immediately rather than hanging.

- **Configurable timeouts** — Clone, fetch, and pull operations are wrapped in hard timeouts (using GNU `timeout` on Linux or `gtimeout` from coreutils on macOS). If a timeout binary is not available, the operations run without a hard limit but a warning is printed.

## Script Configuration

The bootstrap and update scripts are configured through environment variables. None of these are required for typical local use — the defaults work out of the box for SSH-based cloning on macOS.

| Variable | Default | Description |
|---|---|---|
| `PROJECTS_CONFIG` | `./config/projects.yaml` | Path to the YAML file that defines managed repositories. |
| `CLONE_PROTOCOL` | Auto-detected: `https` in CI, `ssh` locally | Whether to clone via SSH (`git@github.com:...`) or HTTPS (`https://github.com/...`). Only `ssh` and `https` are accepted. |
| `GH_ACCESS_TOKEN` | *(none)* | GitHub personal access token for authenticated HTTPS operations. `GITHUB_TOKEN` is also accepted. Only relevant when `CLONE_PROTOCOL=https`. |
| `ALLOWED_BASE_ROOTS` | `/Users/matt/code` (plus `$RUNNER_TEMP` in CI) | Comma-separated list of directory prefixes that the scripts are allowed to operate in. |
| `ALLOWED_GITHUB_ORGS` | `mattmacrocket` | Comma-separated list of GitHub owners/organizations that managed repositories are allowed to belong to. |
| `GIT_CLONE_TIMEOUT_SEC` | `300` | Hard timeout in seconds for `git clone` operations. |
| `GIT_FETCH_TIMEOUT_SEC` | `120` | Hard timeout in seconds for `git fetch` operations. |
| `GIT_PULL_TIMEOUT_SEC` | `120` | Hard timeout in seconds for `git pull` operations. |

## Continuous Integration

The CI workflows run on every push to any branch, as well as on manual dispatch:

- `.github/workflows/cross-repo-smoke.yml` validates runtime repository wiring.
- `.github/workflows/controlplane-smoke.yml` validates control-plane API/dashboard build and script syntax.

The cross-repo smoke workflow performs two steps:

1. **Bootstrap** — Clones all managed runtime repositories into a temporary directory (`$RUNNER_TEMP/agent-repos`) using HTTPS with an access token from the `CROSS_REPO_PAT` repository secret.
2. **Smoke test** — Runs `./harness/smoke.sh` against the same temporary directory to verify that all repositories were cloned successfully and contain their expected verification key files.

The job has a 10-minute timeout and requests only `contents: read` permissions.

To enable CI for private runtime repositories, create a repository secret named `CROSS_REPO_PAT` containing a GitHub personal access token with read access to:

- `mattmacrocket/pingting`
- `mattmacrocket/clownpeanuts`

## Repository Layout

```text
config/
  projects.yaml               # managed repository definitions
adapters/
  clownpeanuts/               # ClownPeanuts adapter
  pingting/                   # PingTing adapter
apps/
  controlplane-dashboard/     # Next.js dashboard
  controlplane-api/           # FastAPI aggregation API
docker-compose.controlplane.yml # dashboard + API compose stack
docs/
  current-state.md             # detailed implementation snapshot for orchestration + control-plane
  opencti-integration.md       # OpenCTI + MITRE + ClownPeanuts playbook
  orchestration.md             # orchestration layer design notes
  repo-map.md                  # canonical path and verification key reference
  user-guide-macos.md          # step-by-step macOS setup guide
harness/
  controlplane-smoke.sh          # smoke test for control-plane API endpoints
  opencti/
    docker-compose.yml         # OpenCTI stack (8 services)
    opencti.env.example        # environment template (secrets auto-generated)
  smoke.sh                     # smoke test for runtime repo verification
scripts/
  bootstrap_repos.sh           # clone or update all managed repos
  controlplane/
    install_launch_agent.sh   # install launchd agent for boot/login startup
    start_api.sh               # run control-plane API dev server
    start_dashboard.sh         # run control-plane dashboard dev server
    start_dev.sh               # run API + dashboard together
    uninstall_launch_agent.sh # remove launchd boot/login startup agent
  opencti/
    check_clownpeanuts_taxii.sh  # TAXII2 endpoint health checks
    start_stack.sh               # OpenCTI stack lifecycle management
  update_repos.sh              # update (fetch + pull) existing repos
  lib/
    common.sh                  # shared shell library
.github/workflows/
  cross-repo-smoke.yml         # CI: bootstrap + smoke on every push
```

## License Choice

SquirrelOps is source-available under `PolyForm Noncommercial 1.0.0`.

- Allowed: personal use, research, educational use, and other noncommercial use.
- Not allowed without separate permission: commercial use, resale, paid hosting, or repackaging for commercial advantage.

If you need commercial rights, open an issue in this repository to request a separate commercial license.

## License

This repository is licensed under `PolyForm Noncommercial 1.0.0`. See `LICENSE`.

## Trademark Policy

Use of project names and logos is governed by `TRADEMARK_POLICY.md`.
