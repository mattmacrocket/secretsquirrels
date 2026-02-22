# SquirrelOps Agent Instructions

This repository is orchestration-first, with control-plane applications.

## Scope

Use this repo for:

- Cross-repo documentation
- Integration/smoke harnesses
- Shared operational scripts
- Workspace topology and dependency coordination
- Control-plane dashboard/API code under `apps/controlplane-*`

Do not add product runtime agent code for PingTing/ClownPeanuts here.

## Runtime Repos

- `/Users/matt/code/pingting`
- `/Users/matt/code/clownpeanuts`

## Execution Rule

If work involves runtime behavior, implement in the corresponding runtime repo, then update orchestration docs/scripts here only as needed.

## Validation Rule

Before finishing orchestration changes, run:

```bash
./harness/smoke.sh
```

Any change that affects repository wiring should keep `.github/workflows/cross-repo-smoke.yml` passing.
