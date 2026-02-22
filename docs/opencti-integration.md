# OpenCTI Integration Guide

This guide walks through deploying an OpenCTI threat intelligence platform instance on macOS using Docker, ingesting the MITRE ATT&CK knowledge base, and then connecting the ClownPeanuts TAXII2 feed as a live intelligence source. The deployment is split into two phases so that you can bring up and validate the core platform before adding the ClownPeanuts connector.

All of the Docker Compose definitions, environment templates, and helper scripts referenced in this guide live in this repository:

- **`harness/opencti/docker-compose.yml`** — Docker Compose service definitions (8 services total, plus 1 profile-gated).
- **`harness/opencti/opencti.env.example`** — Environment variable template with blank secrets that are auto-generated on first run.
- **`scripts/opencti/start_stack.sh`** — Lifecycle management script for the OpenCTI stack (start, stop, logs, status).
- **`scripts/opencti/check_clownpeanuts_taxii.sh`** — Connectivity and health checks for the ClownPeanuts TAXII2 API.

## Prerequisites

### Docker Desktop

Docker Desktop must be installed and running on your Mac. The OpenCTI stack runs entirely in containers — there is nothing to install on the host beyond Docker itself.

Make sure Docker Compose v2 is available (it ships with modern Docker Desktop). You can verify with:

```bash
docker compose version
```

### Shell Utilities

The `start_stack.sh` script uses a few standard utilities to auto-generate secrets and UUIDs. These are all present on a default macOS installation:

- **`curl`** — Used by the TAXII check script to probe HTTP endpoints.
- **`uuidgen`** — Generates UUIDs for OpenCTI connector identifiers.
- **`openssl`** — Generates random hex tokens for passwords and API keys.

### Local Checkouts

This guide assumes the following repositories are cloned locally:

- `/Users/matt/code/squirrelops` — This orchestration repository.
- `/Users/matt/code/clownpeanuts` — The ClownPeanuts runtime repository (needed for Phase 2).

If you have not cloned these yet, follow the [macOS User Guide](user-guide-macos.md) first.

## Architecture Overview

The full stack consists of eight Docker services (nine when the TAXII2 connector is active):

| Service | Purpose |
|---|---|
| **Redis** | In-memory cache and message broker backend for OpenCTI. |
| **Elasticsearch** | Primary data store for all threat intelligence objects. Runs in single-node mode with ML and security features disabled for local development. |
| **MinIO** | S3-compatible object storage used by OpenCTI for file artifacts (reports, exports, etc.). |
| **RabbitMQ** | AMQP message broker that coordinates work between the OpenCTI platform, workers, and connectors. |
| **OpenCTI Platform** | The core web application. Exposes the UI and GraphQL API on port 8080 (configurable via `OPENCTI_PORT`). |
| **OpenCTI Worker** | Background worker that processes ingestion and enrichment tasks from the RabbitMQ queue. |
| **Default Datasets Connector** | Ingests OpenCTI's built-in reference datasets: marking definitions (TLP), identity objects, and geographic locations. |
| **MITRE ATT&CK Connector** | Ingests the MITRE ATT&CK framework (techniques, tactics, mitigations, groups, software) as STIX objects. Refreshes on a configurable interval. |

In Phase 2, a ninth service is added:

| Service | Purpose |
|---|---|
| **TAXII2 Connector** | Polls the ClownPeanuts TAXII2 API for STIX bundles and ingests them into OpenCTI. Creates indicators, observables, attack patterns, and relationships. |

The TAXII2 connector is gated behind a Docker Compose profile called `clownpeanuts`. It only starts when that profile is explicitly activated (which `start_stack.sh phase2` does for you).

## Phase 1: OpenCTI + MITRE ATT&CK

### Starting the Core Stack

From the SquirrelOps directory, run:

```bash
./scripts/opencti/start_stack.sh phase1
```

On the first run, the script performs several setup steps automatically:

1. **Creates the environment file** — Copies `harness/opencti/opencti.env.example` to `harness/opencti/.env` if the `.env` file does not already exist.
2. **Generates missing secrets** — Scans the `.env` file for blank values and auto-populates them:
   - `OPENCTI_ADMIN_PASSWORD` — Random 48-character hex token.
   - `OPENCTI_ADMIN_TOKEN` — Random UUID (used as the API bearer token).
   - `OPENCTI_HEALTHCHECK_ACCESS_KEY` — Random hex token for the health endpoint.
   - `MINIO_ROOT_PASSWORD` — Random hex token.
   - `RABBITMQ_DEFAULT_PASS` — Random hex token.
   - `CONNECTOR_OPENCTI_ID`, `CONNECTOR_MITRE_ID`, `CONNECTOR_TAXII2_ID` — Random UUIDs used as connector instance identifiers.
3. **Starts the services** — Brings up Redis, Elasticsearch, MinIO, RabbitMQ, the OpenCTI platform, the worker, the default datasets connector, and the MITRE ATT&CK connector.
4. **Prints access details** — Displays the URL, admin email, admin password, and API token so you can log in immediately.

### Accessing the Platform

Once the stack is running, open OpenCTI in your browser:

- **URL:** `http://localhost:8080` (or whatever port `OPENCTI_PORT` is set to in `.env`)
- **Credentials:** Printed in the terminal output from `start_stack.sh`. The default admin email is `admin@opencti.local`.

The first startup takes a few minutes as Elasticsearch initializes its indices and the MITRE connector begins ingesting the ATT&CK dataset. You can monitor progress in the connector status.

### Checking Service Status

To see which containers are running and their health status:

```bash
./scripts/opencti/start_stack.sh ps
```

### MITRE Compatibility Profile

The default `.env` template pins the MITRE ATT&CK data sources to specific versions and disables some datasets to avoid known import failures with certain OpenCTI/connector version combinations:

- **Enterprise ATT&CK** — Pinned to version `17.1` via `MITRE_ENTERPRISE_FILE_URL`.
- **Mobile ATT&CK** — Pinned to version `17.1` via `MITRE_MOBILE_ATTACK_FILE_URL`.
- **ICS ATT&CK** — Disabled (`MITRE_ICS_ATTACK_FILE_URL=false`).
- **CAPEC** — Disabled (`MITRE_CAPEC_FILE_URL=false`).

This configuration gets the core Enterprise and Mobile technique libraries loaded quickly and reliably. If you need ICS techniques or CAPEC attack patterns, update those values in `harness/opencti/.env` to point to the appropriate STIX JSON URLs from the [mitre-attack/attack-stix-data](https://github.com/mitre-attack/attack-stix-data) repository, then re-run:

```bash
./scripts/opencti/start_stack.sh phase1
```

### Triggering a MITRE Refresh

The MITRE ATT&CK connector runs on a configurable interval (default: every 7 days, set by `MITRE_INTERVAL_DAYS` in `.env`). If you want to trigger an immediate refresh after the initial ingest:

1. Open the OpenCTI UI.
2. Navigate to **Data Management > Ingestion > Connectors**.
3. Find the **MITRE ATT&CK** connector and click **Refresh**.

## Phase 2: ClownPeanuts STIX/TAXII Feed

Phase 2 adds the ClownPeanuts TAXII2 connector to the running stack. This connector polls the ClownPeanuts API for STIX threat intelligence bundles over the TAXII2 protocol and ingests them into OpenCTI.

### Step 1: Start the ClownPeanuts API

The ClownPeanuts TAXII2 endpoints are served by the ClownPeanuts application itself. You need to start the ClownPeanuts API on your host machine before the Docker-based connector can reach it.

From the ClownPeanuts checkout:

```bash
cd /Users/matt/code/clownpeanuts
./.venv/bin/clownpeanuts api --config ./config/clownpeanuts.yml --host 127.0.0.1 --port 8099 --start-services
```

This starts the ClownPeanuts API server on port 8099. The `--start-services` flag also launches any background services that ClownPeanuts depends on (e.g., its own data pipeline).

Leave this running in a separate terminal.

### Step 2: Verify the TAXII2 Endpoints

Before enabling the connector in Docker, confirm that the ClownPeanuts TAXII2 API is responding correctly. From the SquirrelOps directory:

```bash
./scripts/opencti/check_clownpeanuts_taxii.sh http://127.0.0.1:8099
```

The script takes an optional first argument for the base URL (defaults to `http://127.0.0.1:8099`) and an optional second argument for the collection ID (defaults to `clownpeanuts-intel`). It makes six sequential HTTP requests to verify the API:

1. `GET /health` — General API health check.
2. `GET /taxii2/` — TAXII2 discovery document (advertises the API root).
3. `GET /taxii2/api/` — TAXII2 API root metadata.
4. `GET /taxii2/api/collections` — List of available STIX collections.
5. `GET /taxii2/api/collections/{collection}/manifest?limit=1` — Collection manifest (confirms the collection exists and has content).
6. `GET /taxii2/api/collections/{collection}/objects?limit=1` — Fetches a single STIX object from the collection (confirms objects are available for ingestion).

If all six checks pass, the script prints `ClownPeanuts TAXII checks passed.` and exits with code 0. If any request fails, the script exits immediately with a non-zero code, indicating which step failed.

### Step 3: Enable the TAXII2 Connector

Once the ClownPeanuts API is confirmed healthy, activate Phase 2:

```bash
./scripts/opencti/start_stack.sh phase2
```

This command starts all the Phase 1 services (if not already running) and additionally starts the `connector-taxii2` service using the `clownpeanuts` Docker Compose profile.

The connector is pre-configured to reach the ClownPeanuts API at `http://host.docker.internal:8099/taxii2/`. The `host.docker.internal` hostname is a Docker Desktop feature that resolves to the host machine's network interface, allowing the container to reach services running directly on your Mac.

If ClownPeanuts is running on a different host or port, update the `CLOWNPEANUTS_TAXII_DISCOVERY_URL` value in `harness/opencti/.env` and re-run:

```bash
./scripts/opencti/start_stack.sh phase2
```

### Step 4: Validate Connector Activity

Tail the Docker logs to confirm the TAXII2 connector is polling and ingesting successfully:

```bash
./scripts/opencti/start_stack.sh logs
```

This follows the last 200 lines of logs across all services. Look for log entries from the TAXII2 connector indicating successful collection polling and object creation.

You can also verify connector health in the OpenCTI UI:

1. Navigate to **Data Management > Ingestion > Connectors**.
2. Find the **ClownPeanuts TAXII2** connector.
3. Check its health status and run history. A healthy connector will show recent successful runs and a growing count of ingested objects.

### What the TAXII2 Connector Creates

When the connector ingests STIX bundles from ClownPeanuts, it creates the following object types in OpenCTI:

- **Indicators** — Observable-based detection indicators (e.g., malicious IP addresses, domains, file hashes).
- **Attack Patterns** — MITRE ATT&CK techniques referenced by the intelligence.
- **Relationships** — Links between indicators, attack patterns, and other objects.
- **IPv4 Addresses** — Observable objects for IP-based indicators.

All ingested objects are automatically tagged with the label `clownpeanuts` and attributed to the author `ClownPeanuts TAXII Feed` for easy filtering and provenance tracking within OpenCTI.

## Runtime Controls

The `start_stack.sh` script provides several subcommands for managing the stack lifecycle:

| Command | Description |
|---|---|
| `phase1` | Start the core OpenCTI stack (Redis, Elasticsearch, MinIO, RabbitMQ, OpenCTI, Worker, Default Datasets connector, MITRE connector). Prints login credentials. |
| `phase2` | Start everything from Phase 1, plus the ClownPeanuts TAXII2 connector. Prints login credentials. |
| `ps` | Show the status of all containers, including those in the `clownpeanuts` profile. |
| `logs` | Tail the last 200 lines of logs across all services and follow new output. Press Ctrl+C to stop following. |
| `down` | Stop and remove all containers, including those in the `clownpeanuts` profile. Named volumes (data) are preserved. |

## Environment Variables

The environment file at `harness/opencti/.env` (created automatically from `opencti.env.example`) controls the stack's configuration. Most values are auto-generated on first run and do not need to be changed. The key settings you might want to adjust are:

| Variable | Default | Description |
|---|---|---|
| `OPENCTI_VERSION` | `6.9.20` | OpenCTI Docker image tag. Change this to upgrade or downgrade the platform version. |
| `OPENCTI_PORT` | `8080` | Host port that the OpenCTI web UI is exposed on. |
| `OPENCTI_ADMIN_EMAIL` | `admin@opencti.local` | Admin account email address for login. |
| `ELASTIC_MEMORY_SIZE` | `4G` | JVM heap size for Elasticsearch. Increase this if you are ingesting large volumes of data or see Elasticsearch memory pressure warnings. |
| `MITRE_INTERVAL_DAYS` | `7` | How often (in days) the MITRE ATT&CK connector re-ingests the full ATT&CK dataset. |
| `MITRE_ENTERPRISE_FILE_URL` | ATT&CK 17.1 Enterprise JSON | URL to the Enterprise ATT&CK STIX bundle. Set to `false` to disable. |
| `MITRE_MOBILE_ATTACK_FILE_URL` | ATT&CK 17.1 Mobile JSON | URL to the Mobile ATT&CK STIX bundle. Set to `false` to disable. |
| `MITRE_ICS_ATTACK_FILE_URL` | `false` (disabled) | URL to the ICS ATT&CK STIX bundle. Disabled by default for compatibility. |
| `MITRE_CAPEC_FILE_URL` | `false` (disabled) | URL to the CAPEC STIX bundle. Disabled by default for compatibility. |
| `CONNECTOR_TAXII2_DURATION_PERIOD` | `PT60M` | How often the TAXII2 connector polls ClownPeanuts for new STIX bundles. Uses ISO 8601 duration format (e.g., `PT60M` = every 60 minutes, `PT15M` = every 15 minutes). |
| `TAXII2_INITIAL_HISTORY_HOURS` | `168` | On the connector's first run, how many hours of historical data to request from the TAXII2 API. The default of 168 hours (7 days) means the connector will backfill the last week of intelligence on its initial sync. |
| `TAXII2_VERIFY_SSL` | `false` | Whether the TAXII2 connector verifies SSL certificates when connecting to ClownPeanuts. Set to `false` for local development where ClownPeanuts runs on plain HTTP. |
| `CLOWNPEANUTS_TAXII_DISCOVERY_URL` | `http://host.docker.internal:8099/taxii2/` | The TAXII2 discovery URL that the connector polls. `host.docker.internal` resolves to the macOS host from inside Docker containers. Change this if ClownPeanuts runs on a different host or port. |
| `TAXII2_AUTHOR_NAME` | `ClownPeanuts TAXII Feed` | The author name attributed to all objects ingested from the TAXII2 feed. |

## Troubleshooting

### OpenCTI UI is not loading

The platform can take 2-3 minutes to start on first boot while Elasticsearch creates its indices. Check the health status:

```bash
./scripts/opencti/start_stack.sh ps
```

Look at the `opencti` service's health status. If it shows `starting`, give it more time. If it shows `unhealthy`, check the logs:

```bash
./scripts/opencti/start_stack.sh logs
```

### Elasticsearch out of memory

If Elasticsearch crashes or shows memory-related errors, increase the `ELASTIC_MEMORY_SIZE` value in `harness/opencti/.env`. The default of `4G` is suitable for light use. For larger deployments or if you run many other Docker containers, you may need `6G` or `8G`. After changing the value, restart the stack:

```bash
./scripts/opencti/start_stack.sh down
./scripts/opencti/start_stack.sh phase1
```

Also make sure Docker Desktop itself has enough memory allocated. Open Docker Desktop preferences and check that the memory limit is at least 2 GB above your `ELASTIC_MEMORY_SIZE` setting to leave room for the other services.

### TAXII2 connector cannot reach ClownPeanuts

If the TAXII2 connector logs show connection errors to the ClownPeanuts API, verify:

1. The ClownPeanuts API is actually running on your host (`curl http://127.0.0.1:8099/health`).
2. The `CLOWNPEANUTS_TAXII_DISCOVERY_URL` in `.env` uses `host.docker.internal` (not `localhost` or `127.0.0.1`, which would resolve to the container itself rather than the host).
3. Docker Desktop's network settings allow containers to reach the host. The `host.docker.internal` hostname is a Docker Desktop feature and should work out of the box on macOS.

### MITRE connector import failures

If the MITRE connector shows errors during ingest, it may be a compatibility issue between the ATT&CK data version and your OpenCTI version. The default configuration pins ATT&CK to version 17.1 and disables ICS and CAPEC specifically to avoid known issues. If you have changed the MITRE URLs to point to newer data or re-enabled ICS/CAPEC and are seeing failures, try reverting to the default pinned URLs from `opencti.env.example`.

### Regenerating secrets

If you need to regenerate passwords, tokens, or UUIDs, delete the `harness/opencti/.env` file and re-run the start script. It will create a fresh `.env` from the template and generate all new secrets:

```bash
rm harness/opencti/.env
./scripts/opencti/start_stack.sh phase1
```

Note that changing the admin password or token will require you to use the new credentials to log in. Changing connector IDs may cause OpenCTI to treat the connectors as new instances.

### Resetting all data

To completely reset the OpenCTI installation (removing all ingested data), stop the stack and delete the Docker volumes:

```bash
./scripts/opencti/start_stack.sh down
docker volume rm $(docker volume ls -q | grep opencti)
```

Then restart with `phase1`. The MITRE and default dataset connectors will re-ingest their data from scratch.
