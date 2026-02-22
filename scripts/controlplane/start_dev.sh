#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
API_SCRIPT="${SCRIPT_DIR}/start_api.sh"
DASHBOARD_SCRIPT="${SCRIPT_DIR}/start_dashboard.sh"

API_LOG="${CONTROLPANE_API_LOG:-/tmp/controlplane-api.log}"
DASHBOARD_LOG="${CONTROLPANE_DASHBOARD_LOG:-/tmp/controlplane-dashboard.log}"

"${API_SCRIPT}" >"${API_LOG}" 2>&1 &
API_PID=$!
"${DASHBOARD_SCRIPT}" >"${DASHBOARD_LOG}" 2>&1 &
DASHBOARD_PID=$!

cleanup() {
  kill "${API_PID}" "${DASHBOARD_PID}" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

echo "[controlplane] api pid=${API_PID} log=${API_LOG}"
echo "[controlplane] dashboard pid=${DASHBOARD_PID} log=${DASHBOARD_LOG}"
echo "[controlplane] ctrl+c to stop"

wait "${API_PID}" "${DASHBOARD_PID}"
