#!/usr/bin/env bash
set -euo pipefail

LABEL="${CONTROLPANE_LAUNCHD_LABEL:-com.squirrelops.controlplane}"
PLIST_PATH="${HOME}/Library/LaunchAgents/${LABEL}.plist"
UID_VALUE="$(id -u)"

launchctl bootout "gui/${UID_VALUE}/${LABEL}" >/dev/null 2>&1 || true
launchctl disable "gui/${UID_VALUE}/${LABEL}" >/dev/null 2>&1 || true
rm -f "${PLIST_PATH}"

echo "Uninstalled launch agent: ${LABEL}"
echo "Removed plist: ${PLIST_PATH}"
