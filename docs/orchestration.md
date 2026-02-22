# Orchestration Overview

## Purpose

`squirrelops` coordinates the multi-repository agent workspace.

Detailed implementation snapshot:

- `docs/current-state.md`

## Responsibilities

1. Define canonical repository mapping and verification keys.
2. Provide bootstrap and update scripts for managed repositories.
3. Provide a smoke harness to validate required runtime entrypoints.
4. Run cross-repo smoke checks in CI on every push.
5. Maintain shared orchestration documentation.
6. Host the shared control-plane applications (`apps/controlplane-dashboard`, `apps/controlplane-api`) and adapter contracts.
7. Provide orchestration action execution state for control-plane UX (`data/controlplane/actions-state.json`).

## Boundaries

- Product runtime implementation, packaging, and runtime-specific tests belong in each runtime repository.
- Workspace-level coordination, integration checks, operator control-plane, and operational standards belong here.
- Optional integrations must not become required for baseline bootstrap/smoke/control-plane workflows.

## Managed Repositories

- `pingting` (runtime)
- `clownpeanuts` (runtime)
- `squirrelops` (orchestration)

Current required baseline is the three repositories above.

## Standard Workflow

```bash
./scripts/bootstrap_repos.sh
./scripts/update_repos.sh
./harness/smoke.sh
```

## Security Contract

- `config/projects.yaml` is the source of truth for runtime repository mapping.
- `BASE_DIR` must resolve under `ALLOWED_BASE_ROOTS`.
- Runtime repository owners must be in `ALLOWED_GITHUB_ORGS`.
- HTTPS auth uses `GIT_ASKPASS` with token environment variables (`GH_ACCESS_TOKEN` or `GITHUB_TOKEN`).
- Git operations run with configurable hard timeouts when `timeout` or `gtimeout` is available.

## CI Contract

Workflows `.github/workflows/cross-repo-smoke.yml` and `.github/workflows/controlplane-smoke.yml` must pass on every push.

Smoke assertions are defined in `config/projects.yaml` via `verification_key` for each runtime repo.
