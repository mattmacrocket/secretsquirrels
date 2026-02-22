#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd -P)"
APP_DIR="${REPO_ROOT}/apps/controlplane-api"
VENV_DIR="${APP_DIR}/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"
HOST="${CONTROLPANE_API_HOST:-127.0.0.1}"
PORT="${CONTROLPANE_API_PORT:-8199}"

if [[ ! -d "${VENV_DIR}" ]]; then
  echo "[controlplane-api] creating virtualenv at ${VENV_DIR}"
  "${PYTHON_BIN}" -m venv "${VENV_DIR}"
fi

# shellcheck disable=SC1090
source "${VENV_DIR}/bin/activate"

if [[ "${CONTROLPANE_API_SKIP_INSTALL:-0}" != "1" ]]; then
  echo "[controlplane-api] installing requirements"
  pip install -r "${APP_DIR}/requirements.txt"
fi

cd "${APP_DIR}"
echo "[controlplane-api] starting on http://${HOST}:${PORT}"
exec uvicorn main:app --host "${HOST}" --port "${PORT}" --reload
