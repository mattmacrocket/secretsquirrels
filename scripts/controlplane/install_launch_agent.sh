#!/usr/bin/env bash
set -euo pipefail

LABEL="${CONTROLPANE_LAUNCHD_LABEL:-com.squirrelops.controlplane}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd -P)"
START_SCRIPT="${SCRIPT_DIR}/start_dev.sh"
PLIST_DIR="${HOME}/Library/LaunchAgents"
PLIST_PATH="${PLIST_DIR}/${LABEL}.plist"
UID_VALUE="$(id -u)"

API_PORT="${CONTROLPANE_API_PORT:-8199}"
DASHBOARD_PORT="${CONTROLPANE_DASHBOARD_PORT:-4317}"
PYTHON_BIN_VALUE="${PYTHON_BIN:-$(command -v python3 || true)}"
NPM_BIN_VALUE="${NPM_BIN:-$(command -v npm || true)}"
NODE_BIN_VALUE="${NODE_BIN:-$(command -v node || true)}"

if [[ -z "${PYTHON_BIN_VALUE}" ]]; then
  echo "ERROR: python3 not found; set PYTHON_BIN before installing launch agent." >&2
  exit 1
fi

if [[ -z "${NPM_BIN_VALUE}" ]]; then
  echo "ERROR: npm not found; set NPM_BIN before installing launch agent." >&2
  exit 1
fi

if [[ -z "${NODE_BIN_VALUE}" ]]; then
  echo "ERROR: node not found; set NODE_BIN before installing launch agent." >&2
  exit 1
fi

PATH_VALUE="${PATH:-/usr/bin:/bin:/usr/sbin:/sbin}"
PATH_VALUE="$(dirname "${PYTHON_BIN_VALUE}"):${PATH_VALUE}"
PATH_VALUE="$(dirname "${NPM_BIN_VALUE}"):${PATH_VALUE}"
PATH_VALUE="$(dirname "${NODE_BIN_VALUE}"):${PATH_VALUE}"

mkdir -p "${PLIST_DIR}"

cat > "${PLIST_PATH}" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>

  <key>ProgramArguments</key>
  <array>
    <string>${START_SCRIPT}</string>
  </array>

  <key>WorkingDirectory</key>
  <string>${REPO_ROOT}</string>

  <key>EnvironmentVariables</key>
  <dict>
    <key>CONTROLPANE_API_PORT</key>
    <string>${API_PORT}</string>
    <key>CONTROLPANE_DASHBOARD_PORT</key>
    <string>${DASHBOARD_PORT}</string>
    <key>PYTHON_BIN</key>
    <string>${PYTHON_BIN_VALUE}</string>
    <key>NPM_BIN</key>
    <string>${NPM_BIN_VALUE}</string>
    <key>NODE_BIN</key>
    <string>${NODE_BIN_VALUE}</string>
    <key>PATH</key>
    <string>${PATH_VALUE}</string>
  </dict>

  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>

  <key>StandardOutPath</key>
  <string>/tmp/squirrelops-controlplane.launchd.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/squirrelops-controlplane.launchd.err.log</string>
</dict>
</plist>
PLIST

launchctl bootout "gui/${UID_VALUE}/${LABEL}" >/dev/null 2>&1 || true
launchctl bootstrap "gui/${UID_VALUE}" "${PLIST_PATH}"
launchctl enable "gui/${UID_VALUE}/${LABEL}"
launchctl kickstart -k "gui/${UID_VALUE}/${LABEL}"

echo "Installed launch agent: ${LABEL}"
echo "Plist: ${PLIST_PATH}"
echo "Dashboard: http://127.0.0.1:${DASHBOARD_PORT}"
echo "API: http://127.0.0.1:${API_PORT}"
