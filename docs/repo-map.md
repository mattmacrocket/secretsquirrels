# Repo Map

## Canonical Paths

- `/Users/matt/code/secretsquirrels` - umbrella orchestration
- `/Users/matt/code/pingting` - Pingting runtime
- `/Users/matt/code/clownpeanuts` - ClownPeanuts runtime
- `/Users/matt/code/secretsquirrels/apps/controlplane-dashboard` - shared operator UI
- `/Users/matt/code/secretsquirrels/apps/controlplane-api` - shared control-plane API

## Config Source of Truth

Runtime repository metadata lives in `config/projects.yaml`:

- `name` - local directory name under the base directory
- `repo` - canonical GitHub remote URL
- `role` - repository type (`runtime`)
- `verification_key` - file required by the smoke harness
- `dashboard` - UI tab/route mapping metadata for control-plane rendering
- `capabilities` - product capability flags used by operator surfaces

For full operational behavior and endpoint inventory, see:

- `docs/current-state.md`

## Runtime Verification Keys

Current smoke checks require:

- `pingting`: `pingting/main.py`
- `clownpeanuts`: `clownpeanuts/cli.py`

These checks are executed by `harness/smoke.sh` and by `.github/workflows/cross-repo-smoke.yml`.
