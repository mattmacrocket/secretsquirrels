#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd -P)"
APP_DIR="${REPO_ROOT}/apps/controlplane-dashboard"
NPM_BIN="${NPM_BIN:-npm}"
NODE_BIN="${NODE_BIN:-}"
PORT="${CONTROLPANE_DASHBOARD_PORT:-4317}"

if [[ -z "${NODE_BIN}" ]]; then
  NODE_BIN="$(command -v node || true)"
fi

if [[ -z "${NODE_BIN}" ]]; then
  npm_dir="$(dirname "${NPM_BIN}")"
  if [[ -x "${npm_dir}/node" ]]; then
    NODE_BIN="${npm_dir}/node"
  fi
fi

if [[ -z "${NODE_BIN}" ]]; then
  echo "[controlplane-dashboard] ERROR: node binary not found. Set NODE_BIN or ensure node is on PATH." >&2
  exit 1
fi

# Ensure npm shebang (#!/usr/bin/env node) can resolve node under launchd.
export PATH="$(dirname "${NODE_BIN}"):${PATH}"

cd "${APP_DIR}"
if [[ ! -d "${APP_DIR}/node_modules" ]]; then
  echo "[controlplane-dashboard] installing npm dependencies"
  "${NPM_BIN}" install
fi

echo "[controlplane-dashboard] starting dev server on http://127.0.0.1:${PORT}"
exec "${NPM_BIN}" run dev -- --port "${PORT}"
